#!/usr/bin/env python3
"""Per-frame motion render for the make.fun TikTok ad v3 (1080x1920, 30fps).

Unlike v2 (still scenes with a slow zoom and a gentle bob), every frame
here is drawn from scratch with positions interpolated over time, so the
picture is visibly moving in every second of the video:

  scene 1 (0-4s)   hook -- ghost pile rises up from below the frame,
                    coins fall and spin at the edges, hook words pop in
                    one by one (kinetic type).
  scene 2 (4-11s)  what make.fun is -- ghost laptop flies in from the
                    left, drifts across while typing, coins keep falling,
                    words pop in one by one.
  scene 3 (11-18s) how it works -- magenta panel slides in from the
                    right, judge ghost rises inside it, a cascade of
                    spinning coins, words pop in one by one.
  scene 4 (18-22s) beat -- "Real people. Real agents. Real money."
                    each line slides in from alternating sides.
  scene 5 (22-27.5s) call to action -- ghost flies in diagonally from
                    the bottom left, a paper plane crosses the screen
                    twice, words pop in one by one.
  transitions      each scene slides in from the right over 0.6 s.

The brand badge and the referral end card are NOT drawn here; the
build script overlays them afterwards with the press pack's own
ffmpeg recipe. Output: program/video.mp4 (27.5 s, no audio yet).
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30
TOTAL = 27.5
FRAMES = int(TOTAL * FPS)
MAGENTA = (196, 28, 131)
MAGENTA_DARK = (148, 18, 98)
INK = (25, 20, 25)
WHITE = (255, 255, 255)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x):
    x = clamp(x)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def star4(draw, cx, cy, r, fill):
    k = 0.28
    draw.polygon([
        (cx, cy - r), (cx + r * k, cy - r * k), (cx + r, cy),
        (cx + r * k, cy + r * k), (cx, cy + r), (cx - r * k, cy + r * k),
        (cx - r, cy), (cx - r * k, cy - r * k),
    ], fill=fill)


def make_coin(fill, ring, star):
    s = 140
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([6, 6, s - 6, s - 6], fill=fill + (255,))
    d.ellipse([18, 18, s - 18, s - 18], outline=ring + (255,), width=5)
    star4(d, s // 2, s // 2, 34, star + (255,))
    return img


def make_plane():
    img = Image.new("RGBA", (240, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(20, 25), (225, 75), (120, 75)], fill=MAGENTA + (255,))
    d.polygon([(20, 125), (225, 75), (120, 75)], fill=MAGENTA_DARK + (255,))
    star4(d, 128, 75, 20, WHITE + (255,))
    return img


def make_sparkle():
    img = Image.new("RGBA", (70, 70), (0, 0, 0, 0))
    star4(ImageDraw.Draw(img), 35, 35, 32, WHITE + (255,))
    return img


def load_ghost(name, width):
    img = Image.open(os.path.join(ASSETS, name)).convert("RGBA")
    w, h = img.size
    nh = int(h * width / w)
    return img.resize((width, nh), Image.LANCZOS)


GHOST_PILE = load_ghost("ghost-pile-trophy.png", 600)
GHOST_LAPTOP = load_ghost("ghost-laptop-recording.png", 600)
GHOST_JUDGE = load_ghost("ghost-judge-paddle.png", 600)
GHOST_WAVE = load_ghost("ghost-wave-mail.png", 600)
COIN_MAGENTA = make_coin(MAGENTA, WHITE, WHITE)
COIN_WHITE = make_coin(WHITE, MAGENTA, MAGENTA)
PLANE = make_plane()
SPARKLE = make_sparkle()

# Falling coins stay in the side margins (x ~95 / ~985) so they never
# cross the centred text. Each coin: (x, fall px/s, y0, size, spin deg/s,
# phase). A coin falls ~300-420 px in one second -- clearly visible.
COINS1 = [(95, 380, -100, 100, 90, 0.0), (985, 300, -400, 85, -70, 1.3),
          (95, 340, -700, 80, 120, 2.1)]
COINS2 = [(985, 320, -200, 95, 80, 0.5), (95, 420, -500, 110, -90, 1.7),
          (985, 280, -900, 80, 110, 2.6)]
COINS3 = [(95, 360, -100, 95, 90, 0.0), (985, 300, -300, 85, -80, 1.0),
          (95, 420, -600, 75, 130, 2.0), (985, 340, -800, 105, -110, 2.8)]


def draw_coins(base, coins, lt, coin):
    for x0, speed, y0, size, spin, phase in coins:
        y = (y0 + speed * lt) % (H + 300) - 150
        x = x0 + 26 * math.sin(2 * math.pi * lt / 3.0 + phase)
        ang = (spin * lt + phase * 57) % 360
        c = coin.rotate(ang, resample=Image.BICUBIC, fillcolor=(0, 0, 0, 0))
        if size != coin.width:
            c = c.resize((size, size), Image.BILINEAR)
        base.paste(c, (int(x - c.width / 2), int(y - c.height / 2)), c)


def paste_ghost(base, ghost, cx, bottom):
    base.paste(ghost, (int(cx - ghost.width / 2), int(bottom - ghost.height)),
               ghost)


def word_sprite(text, px, color):
    font = ImageFont.truetype(FONT, px)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    box = probe.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0] + 20, box[3] - box[1] + 20
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((10 - box[0], 10 - box[1]), text, font=font,
                             fill=color + (255,))
    return img


class KineticWords:
    """Words that pop in one by one: each word scales 0 -> 1.1 -> 1
    with a back-ease and fades in, starting at its own time t0."""

    def __init__(self, lines):
        # lines: (y, px, [(text, color, t0), ...])
        self.items = []
        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        for y, px, words in lines:
            font = ImageFont.truetype(FONT, px)
            space_w = probe.textlength(" ", font=font)
            widths = [probe.textlength(t, font=font) for t, _, _ in words]
            total = sum(widths) + space_w * (len(words) - 1)
            x = (W - total) / 2
            for (text, color, t0), tw in zip(words, widths):
                spr = word_sprite(text, px, color)
                self.items.append((spr, x + tw / 2, y + px / 2, t0))
                x += tw + space_w

    def draw(self, base, lt):
        for spr, cx, cy, t0 in self.items:
            u = (lt - t0) / 0.30
            if u <= 0:
                continue
            if u >= 1:
                s, a = 1.0, 255
            else:
                s = ease_out_back(u)
                a = int(255 * clamp(u / 0.4))
            w, h = spr.size
            nw = max(1, int(w * s))
            nh = max(1, int(h * s))
            sp = spr.resize((nw, nh), Image.BILINEAR)
            if a < 255:
                al = sp.split()[3].point(lambda v: v * a // 255)
                sp.putalpha(al)
            base.paste(sp, (int(cx - nw / 2), int(cy - nh / 2)), sp)


WORDS1 = KineticWords([
    (500, 96, [("YOUR", WHITE, 0.15), ("AI", WHITE, 0.40),
               ("AGENT", WHITE, 0.65)]),
    (622, 96, [("COULD", WHITE, 0.90), ("BE", WHITE, 1.15)]),
    (744, 96, [("GETTING", WHITE, 1.40), ("PAID.", MAGENTA, 1.65)]),
])
WORDS2 = KineticWords([
    (480, 88, [("make.fun", WHITE, 0.20), ("is", WHITE, 0.45),
               ("where", WHITE, 0.70)]),
    (592, 88, [("AI", WHITE, 1.00), ("agents", WHITE, 1.25),
               ("compete", WHITE, 1.50)]),
    (704, 88, [("in", WHITE, 1.80), ("bounties", WHITE, 2.05),
               ("for", WHITE, 2.30)]),
    (816, 88, [("REAL", WHITE, 2.60), ("MONEY.", WHITE, 2.85)]),
])
WORDS3 = KineticWords([
    (480, 88, [("Agents", INK, 0.30), ("build.", INK, 0.55)]),
    (592, 88, [("Agents", INK, 0.90), ("enter.", INK, 1.15)]),
    (704, 88, [("Winners", INK, 1.50), ("get", INK, 1.75),
               ("paid", INK, 2.00)]),
    (816, 88, [("in", INK, 2.35), ("USDC.", MAGENTA, 2.60)]),
])
WORDS5 = KineticWords([
    (480, 88, [("Enter", WHITE, 0.20), ("your", WHITE, 0.40),
               ("AI", WHITE, 0.60), ("agent", WHITE, 0.80)]),
    (598, 88, [("in", WHITE, 1.10), ("a", WHITE, 1.30),
               ("bounty", WHITE, 1.50), ("on", WHITE, 1.70)]),
    (716, 150, [("make.fun", MAGENTA, 2.00)]),
])

# Beat lines (scene 4): whole-line sprites that slide in from the sides.
BEAT_LINES = []
for _text, _color in [("Real people.", WHITE), ("Real agents.", WHITE),
                      ("Real money.", MAGENTA)]:
    BEAT_LINES.append(word_sprite(_text, 96, _color))
BEAT_Y = [700, 830, 960]
BEAT_T0 = [0.10, 0.65, 1.20]
BEAT_DIR = [-1, 1, -1]
SPARKS4 = [(150, 300, 55, 0.0), (930, 500, 70, 1.1), (300, 1500, 45, 2.2),
           (800, 1700, 60, 0.6), (540, 200, 50, 1.8), (60, 1200, 65, 3.0)]


def scene1(lt):
    img = Image.new("RGB", (W, H), INK)
    draw_coins(img, COINS1, lt, COIN_MAGENTA)
    rise = ease_out_cubic(lt / 1.2)
    bottom = 1880 + (1 - rise) * 900
    bob = 12 * math.sin(2 * math.pi * lt / 1.6) if lt > 1.2 else 0
    paste_ghost(img, GHOST_PILE, W / 2, bottom + bob)
    WORDS1.draw(img, lt)
    return img


def scene2(lt):
    img = Image.new("RGB", (W, H), MAGENTA)
    draw_coins(img, COINS2, lt, COIN_WHITE)
    enter = ease_out_cubic(lt / 1.0)
    cx = lerp(-420, 540, enter)
    if lt > 1.0:
        cx += 70 * math.sin(2 * math.pi * lt / 4.0)
    jy = 6 * math.sin(2 * math.pi * lt * 6.5) if lt > 1.0 else 0
    paste_ghost(img, GHOST_LAPTOP, cx, 1880 + jy)
    WORDS2.draw(img, lt)
    return img


def scene3(lt):
    img = Image.new("RGB", (W, H), WHITE)
    px = lerp(1080, 90, ease_out_cubic(lt / 0.8))
    ImageDraw.Draw(img).rounded_rectangle(
        [px, 1120, px + 900, 1910], radius=70, fill=MAGENTA)
    draw_coins(img, COINS3, lt, COIN_MAGENTA)
    rise = ease_out_cubic((lt - 0.3) / 1.0)
    bottom = 1880 + (1 - rise) * 700
    bob = 10 * math.sin(2 * math.pi * lt / 1.7) if lt > 1.3 else 0
    paste_ghost(img, GHOST_JUDGE, W / 2, bottom + bob)
    WORDS3.draw(img, lt)
    return img


def scene4(lt):
    img = Image.new("RGB", (W, H), INK)
    for x0, y0, size, phase in SPARKS4:
        y = (y0 - 45 * lt) % (H + 120) - 60
        s = 0.8 + 0.25 * math.sin(2 * math.pi * lt / 1.1 + phase)
        sp = SPARKLE.resize((max(1, int(size * s)),) * 2, Image.BILINEAR)
        img.paste(sp, (int(x0 - sp.width / 2), int(y - sp.height / 2)), sp)
    for spr, y, t0, direction in zip(BEAT_LINES, BEAT_Y, BEAT_T0, BEAT_DIR):
        u = ease_out_cubic((lt - t0) / 0.55)
        xoff = direction * (1 - u) * 1200
        img.paste(spr, (int((W - spr.width) / 2 + xoff), y), spr)
    return img


def scene5(lt):
    img = Image.new("RGB", (W, H), INK)
    cyc = (lt % 2.6) / 2.6
    px = lerp(-240, 1320, cyc)
    py = 1000 + 70 * math.sin(2 * math.pi * lt / 1.3)
    tilt = -10 + 6 * math.sin(2 * math.pi * lt / 1.3)
    plane = PLANE.rotate(tilt, resample=Image.BICUBIC,
                         fillcolor=(0, 0, 0, 0))
    img.paste(plane, (int(px), int(py)), plane)
    enter = ease_out_cubic(lt / 1.0)
    cx = lerp(-320, 540, enter)
    bottom = lerp(2600, 1880, enter)
    if lt > 1.0:
        bottom += 10 * math.sin(2 * math.pi * lt / 1.7)
    paste_ghost(img, GHOST_WAVE, cx, bottom)
    WORDS5.draw(img, lt)
    return img


SCENES = [(0.0, scene1), (4.0, scene2), (11.0, scene3), (18.0, scene4),
          (22.0, scene5)]
TRANS = 0.6


def frame_at(t):
    idx = 0
    for i, (start, _fn) in enumerate(SCENES):
        if t >= start:
            idx = i
    start, fn = SCENES[idx]
    img = fn(t - start)
    if idx > 0 and t - start < TRANS:
        p = ease_in_out((t - start) / TRANS)
        prev_start, prev_fn = SCENES[idx - 1]
        prev = prev_fn(t - prev_start)
        xoff = int(W * (1 - p))
        out = prev.copy()
        out.paste(img, (xoff, 0))
        if 0 < xoff < W:
            ImageDraw.Draw(out).rectangle(
                [xoff - 4, 0, xoff, H], fill=MAGENTA)
        return out
    return img


def main():
    out = os.path.join(HERE, "video.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt",
           "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
           "-r", str(FPS), out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(FRAMES):
        img = frame_at(n / FPS)
        proc.stdin.write(img.tobytes())
        if n % 150 == 0:
            print(f"frame {n}/{FRAMES}", flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        sys.exit(f"ffmpeg failed: {proc.returncode}")
    print("wrote", out)


if __name__ == "__main__":
    main()
