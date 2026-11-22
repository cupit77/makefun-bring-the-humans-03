#!/usr/bin/env python3
"""Per-frame render for the make.fun TikTok ad v6 (1080x1920, 30fps).

v6 = v5 retimed faster. Ahmad's direction: "percepat gerakannya" --
v5's walk took ~10 s to cross the room at ~50 px/s and the ghost was
half out of frame for the first 3 s. v6 keeps the same single
continuous shot in one room (no slides, no hard cuts) but the ghost
walks in fast, reaches the chest around 5 s, and the beats after the
chest opens are tightened so the whole ad is ~21 s.

  0-5s     the walk -- ghost walks in fast from the left, room scrolls
            past with parallax, chest comes into view; camera eases
            to a stop. "walking in circles..."
  5-7s     the find -- ghost stops at the glowing chest, hops.
            "then it found a chest"
  7-10s    the open -- lid swings open, light pours out, coins burst
            in arcs and rain down, ghost jumps.
            "inside: make.fun coins"
  10-12.4s "where agents compete" / "for real money" (two lines --
            the 7f2d021 fix: one line at 52 px was 1119 px wide and
            clipped both edges, so it stays split in two)
  12-15s   the payoff -- coins rain, ghost hops joyfully, a golden
            trophy rises out of the chest. "winners get paid in USDC"
  15.5-17.5s the call -- paper plane glides across the same room,
            ghost drifts after it. "enter your agent in a bounty on
            make.fun"
  18.5-21s  end card (referral card, overlaid by the build script, not
            drawn here -- exactly as in v4/v5).

The brand badge and the referral end card are NOT drawn here; the
build script overlays them afterwards with the press pack's own
ffmpeg recipe. Output: program/video.mp4 (21.0 s, no audio yet).
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import render_story as R

W, H = R.W, R.H
FPS = R.FPS
TOTAL = 21.0
FRAMES = int(TOTAL * FPS)
MAGENTA = R.MAGENTA
WHITE = R.WHITE
GOLD = R.GOLD
INK = R.INK
FONT = R.FONT

HERE = os.path.dirname(os.path.abspath(__file__))
FLOOR_Y = R.FLOOR_Y
CHEST_WORLD_X = 1400  # chest's fixed place in the room, world coords
CHEST_BOTTOM = R.CHEST_BOTTOM

GHOST = R.GHOST_WAVE
COIN_MAGENTA = R.COIN_MAGENTA
COIN_WHITE = R.COIN_WHITE
SPARKLE = R.SPARKLE
PLANE = R.PLANE


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_cubic(x):
    return R.ease_out_cubic(x)


def ease_in_out(x):
    return R.ease_in_out(x)


# ---- camera: one continuous glide, then a stop (never a cut) ----

def walk_w(t):
    """Walk progress 0..1 over the first 5 s: fast in (ease-out, so
    the ghost is clearly visible within ~1 s), easing out to a stop
    at the chest with no sudden brake and never a jump."""
    u = clamp(t / 5.0)
    return 1 - (1 - u) * (1 - u)


def off_near(t):
    return 550.0 * walk_w(min(t, 5.0))


def off_far(t):
    return off_near(t) * 0.45


# ---- ghost: one ghost the whole shot, step cycle tied to distance ----

def paste_ghost(base, cx, bottom, bob=0.0, tilt=0.0):
    g = GHOST.rotate(tilt, resample=Image.BICUBIC, expand=False,
                     fillcolor=(0, 0, 0, 0))
    base.paste(g, (int(cx - g.width / 2), int(bottom + bob - g.height)), g)


def ghost_pose(t):
    """(cx, bottom, bob, tilt) for the single ghost at time t."""
    if t < 5.0:
        w = walk_w(t)
        steps = 15.0 * w
        bob = -16 * abs(math.sin(math.pi * steps))
        tilt = 4.0 * math.sin(2 * math.pi * steps)
        return -100 + 500 * w, 1880, bob, tilt
    # stopped at the chest: gentle idle bob, leaning toward it
    bob = 7 * math.sin(2 * math.pi * t / 1.8)
    for t0, dur, amp in ((5.4, 0.5, 26), (8.1, 0.4, 30),
                         (12.6, 0.4, 34), (14.0, 0.4, 34)):
        u = (t - t0) / dur
        if 0 < u < 1:
            bob -= amp * math.sin(math.pi * u)
    return 400, 1880, bob, -5.0


# ---- trophy: a small golden cup that rises out of the chest ----

def draw_trophy(img, cx, bottom, scale=1.0):
    s = scale
    d = ImageDraw.Draw(img)
    cup_w, cup_h = int(120 * s), int(110 * s)
    stem_w, stem_h = int(26 * s), int(70 * s)
    base_w, base_h = int(130 * s), int(30 * s)
    top = bottom - stem_h - cup_h
    d.polygon([(cx - cup_w // 2, top), (cx + cup_w // 2, top),
               (cx + cup_w // 2 - 14, top + cup_h),
               (cx - cup_w // 2 + 14, top + cup_h)], fill=GOLD)
    d.arc([cx - cup_w // 2 - 34, top + 6, cx - cup_w // 2 + 34, top + 66],
          start=90, end=270, fill=GOLD, width=int(14 * s))
    d.arc([cx + cup_w // 2 - 34, top + 6, cx + cup_w // 2 + 34, top + 66],
          start=270, end=90, fill=GOLD, width=int(14 * s))
    d.rectangle([cx - stem_w // 2, top + cup_h, cx + stem_w // 2,
                 top + cup_h + stem_h], fill=GOLD)
    d.rectangle([cx - base_w // 2, bottom - base_h, cx + base_w // 2,
                 bottom], fill=GOLD)
    R.star4(d, cx, top + cup_h // 2, int(26 * s), WHITE)


# ---- coins that burst out of the chest (absolute times) ----

BURST = []
for i in range(16):
    BURST.append({
        "x0": 850 + (i % 8 - 3.5) * 36,
        "y0": CHEST_BOTTOM - 190 - 5,
        "vx": ((i * 97) % 560) - 280,
        "vy": -780 + (i * 53) % 380,
        "t0": 7.8 + (i % 5) * 0.05,
        "spin": (i * 137) % 360,
        "size": 70 + (i * 29) % 50,
        "coin": COIN_MAGENTA if i % 3 else COIN_WHITE,
    })

RAIN = [(150, 300, -100, 90, 90, 0.0), (930, 340, -400, 85, -70, 1.3),
        (150, 380, -700, 80, 120, 2.1), (930, 300, -900, 95, -110, 2.6),
        (540, 260, -1400, 88, 60, 0.6), (60, 320, -1700, 80, -90, 1.8)]


def draw_burst(img, t):
    for c in BURST:
        dt = t - c["t0"]
        if dt < 0:
            continue
        x = c["x0"] + c["vx"] * dt
        y = c["y0"] + c["vy"] * dt + 0.5 * 1500 * dt * dt
        floor_y = 1700 - c["size"] / 2
        if y > floor_y:
            y = floor_y
        x = max(60, min(1020, x))
        a = (c["spin"] + 300 * dt) % 360
        coin = c["coin"].rotate(a, resample=Image.BICUBIC,
                                fillcolor=(0, 0, 0, 0))
        coin = coin.resize((c["size"], c["size"]), Image.BILINEAR)
        img.paste(coin, (int(x - coin.width / 2), int(y - coin.height / 2)),
                  coin)


def draw_rain(img, t):
    R.draw_coins(img, RAIN, t - 12.0, COIN_WHITE)


# ---- one small fading line at a time, never a card ----

def line_sprite(segs, px):
    font = ImageFont.truetype(FONT, px)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    widths = [probe.textlength(s, font=font) for s, _ in segs]
    total = sum(widths)
    box = probe.textbbox((0, 0), "Ag", font=font)
    h = box[3] - box[1] + 16
    img = Image.new("RGBA", (int(total) + 16, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 8
    for (text, color), tw in zip(segs, widths):
        d.text((x, 8 - box[1]), text, font=font, fill=color + (255,))
        x += tw
    return img


class SoftLine:
    """A single caption line that fades in, holds, fades out."""

    def __init__(self, t0, t1, y, px, segs):
        self.spr = line_sprite(segs, px)
        self.cx = W / 2
        self.cy = y
        self.t0 = t0
        self.t1 = t1

    def draw(self, base, t):
        a = clamp(min((t - self.t0) / 0.5, (self.t1 - t) / 0.5), 0.0, 1.0)
        if a <= 0:
            return
        sp = self.spr
        if a < 1.0:
            sp = sp.copy()
            al = sp.split()[3].point(lambda v: int(v * a))
            sp.putalpha(al)
        base.paste(sp, (int(self.cx - sp.width / 2),
                        int(self.cy - sp.height / 2)), sp)


CAPTION = [
    SoftLine(1.0, 4.0, 560, 58, [("walking in circles...", WHITE)]),
    SoftLine(5.3, 6.8, 560, 58,
             [("then it found a ", WHITE), ("chest", MAGENTA)]),
    SoftLine(8.2, 10.2, 560, 58,
             [("inside: make.fun ", WHITE), ("coins", MAGENTA)]),
    SoftLine(10.4, 12.4, 520, 58,
             [("where agents compete", WHITE)]),
    SoftLine(10.4, 12.4, 600, 58,
             [("for real money", WHITE)]),
    SoftLine(12.8, 15.0, 560, 58,
             [("winners get paid in ", WHITE), ("USDC", MAGENTA)]),
    SoftLine(15.7, 18.3, 520, 56, [("enter your agent", WHITE)]),
    SoftLine(15.7, 18.3, 600, 56,
             [("in a bounty on ", WHITE), ("make.fun", MAGENTA)]),
]


def lid_angle(t):
    if t < 7.0:
        return 0.0
    return 1.9 * ease_out_cubic((t - 7.0) / 1.0)


def frame_at(t):
    img = Image.new("RGBA", (W, H), INK)
    on = off_near(t)
    R.draw_room(img, on, off_far(t), t)
    chest_x = int(CHEST_WORLD_X - on)
    ang = lid_angle(t)
    glow = 0.0
    if t >= 5.0:
        glow = 0.45 + 0.35 * math.sin(2 * math.pi * t * 1.1)
    if ang > 0.2:
        glow = 0.6 + 0.4 * math.sin(2 * math.pi * t * 1.4)
    R.draw_chest(img, chest_x, CHEST_BOTTOM, ang, glow,
                 t if ang > 0.3 else 0)
    # trophy rises out of the chest during the payoff
    if t >= 12.5:
        rise = ease_out_cubic((t - 12.5) / 1.2)
        bottom = 1640 - 200 * rise
        draw_trophy(img, chest_x, int(bottom), scale=1.0)
        if rise > 0.3:
            s = 0.7 + 0.3 * math.sin(2 * math.pi * t / 1.3)
            sp = SPARKLE.resize((max(1, int(56 * s)),) * 2, Image.BILINEAR)
            img.paste(sp, (int(chest_x - sp.width / 2),
                           int(bottom - 260 - sp.height / 2)), sp)
    draw_burst(img, t)
    if t >= 12.0:
        draw_rain(img, t)
    # ghost, one continuous presence
    gx, gbottom, bob, tilt = ghost_pose(t)
    R.draw_shadow(img, gx)
    paste_ghost(img, gx, gbottom, bob, tilt)
    # paper plane glides across the same room for the call
    if 15.5 <= t < 17.5:
        u = (t - 15.5) / 2.0
        px = lerp(-240, 1320, u)
        py = 1000 + 70 * math.sin(2 * math.pi * t / 1.3)
        plane = PLANE.rotate(-10 + 6 * math.sin(2 * math.pi * t / 1.3),
                             resample=Image.BICUBIC,
                             fillcolor=(0, 0, 0, 0))
        img.paste(plane, (int(px), int(py)), plane)
    for line in CAPTION:
        line.draw(img, t)
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
        proc.stdin.write(img.convert("RGB").tobytes())
        if n % 150 == 0:
            print(f"frame {n}/{FRAMES}", flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        sys.exit(f"ffmpeg failed: {proc.returncode}")
    print("wrote", out)


if __name__ == "__main__":
    main()
