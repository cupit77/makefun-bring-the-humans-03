#!/usr/bin/env python3
"""Per-frame story render for the make.fun TikTok ad v4 (1080x1920, 30fps).

Ahmad's direction: the ghost WALKS through a room, FINDS a treasure
chest, OPENS it, and inside are make.fun coins. The character must move
like it is really walking -- so the walk is built from a step cycle
(vertical bob per step + alternating lean) while the room scrolls past
with parallax, instead of a ghost sliding over a still picture.

  scene 1 (0-7s)     the walk -- ghost walks in from the left across a
                      room (door, window, picture, table, rug scroll by
                      with parallax); the chest comes into view at the
                      right. "My AI agent was walking in circles."
  scene 2 (7-12s)    the find -- ghost walks up to the glowing chest and
                      stops; it hops when it spots it.
                      "Then it found a chest."
  scene 3 (12-18s)   the open -- the chest lid swings open on its hinge,
                      light pours out, make.fun coins burst out in arcs
                      and rain down. "Inside: make.fun coins. make.fun is
                      where AI agents compete for REAL MONEY."
  scene 4 (18-22.5s) the payoff -- ghost pile with trophy rises amid
                      falling coins in the same room.
                      "Agents build. Agents enter. Winners get paid in
                      USDC."
  scene 5 (22.5-27.5s) call to action -- ghost flies in, paper plane
                      crosses the screen.
                      "Enter your AI agent in a bounty on make.fun"
  end card           (25-27.5s) referral card, overlaid by the build
                      script, not drawn here.

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
GOLD = (212, 175, 55)
WALL = (48, 33, 56)
FLOOR = (64, 42, 28)
FLOOR_DARK = (50, 32, 20)
WOOD = (122, 74, 33)
WOOD_DARK = (88, 52, 22)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
FLOOR_Y = 1500


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


GHOST_WAVE = load_ghost("ghost-wave-mail.png", 420)
GHOST_PILE = load_ghost("ghost-pile-trophy.png", 600)
COIN_MAGENTA = make_coin(MAGENTA, WHITE, WHITE)
COIN_WHITE = make_coin(WHITE, MAGENTA, MAGENTA)
PLANE = make_plane()
SPARKLE = make_sparkle()


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


def paste_ghost_walk(base, ghost, cx, bottom, t, freq=1.5):
    # A real step cycle: one vertical bob per step plus a lean that
    # alternates left/right with each step. At freq=1.5 steps/s the
    # ghost bobs ~16 px and tilts +/-4 degrees -- clearly a walk,
    # not a slide.
    bob = -16 * abs(math.sin(math.pi * freq * t))
    tilt = 4.0 * math.sin(2 * math.pi * freq * t)
    g = ghost.rotate(tilt, resample=Image.BICUBIC, expand=False,
                     fillcolor=(0, 0, 0, 0))
    base.paste(g, (int(cx - g.width / 2), int(bottom + bob - g.height)), g)


def paste_ghost_idle(base, ghost, cx, bottom, t, lean=0.0):
    bob = 7 * math.sin(2 * math.pi * t / 1.8)
    g = ghost.rotate(lean, resample=Image.BICUBIC, expand=False,
                     fillcolor=(0, 0, 0, 0))
    base.paste(g, (int(cx - g.width / 2), int(bottom + bob - g.height)), g)


def draw_shadow(base, cx, y=1884, rx=150):
    ImageDraw.Draw(base).ellipse([cx - rx, y - 12, cx + rx, y + 12],
                                 fill=(20, 10, 8))


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


# ---- the room (original shapes; two parallax layers) ----

def draw_window(d, x, y):
    if x + 320 < 0 or x > W:
        return
    d.rectangle([x, y, x + 320, y + 460], fill=(52, 36, 24))
    d.rectangle([x + 16, y + 16, x + 304, y + 444], fill=(16, 24, 54))
    d.ellipse([x + 200, y + 60, x + 260, y + 120], fill=(235, 230, 200))
    for sx, sy in [(x + 60, y + 90), (x + 120, y + 180), (x + 230, y + 220),
                   (x + 90, y + 300)]:
        star4(d, sx, sy, 12, (255, 255, 255))
    d.line([x + 160, y + 16, x + 160, y + 444], fill=(52, 36, 24), width=10)
    d.line([x + 16, y + 230, x + 304, y + 230], fill=(52, 36, 24), width=10)


def draw_picture(d, x, y):
    if x + 220 < 0 or x > W:
        return
    d.rectangle([x, y, x + 220, y + 220], fill=GOLD)
    d.rectangle([x + 14, y + 14, x + 206, y + 206], fill=INK)
    star4(d, x + 110, y + 110, 46, MAGENTA)


def draw_door(d, x):
    if x + 280 < 0 or x > W:
        return
    d.rounded_rectangle([x, 780, x + 280, FLOOR_Y], radius=36, fill=WOOD)
    d.rectangle([x + 28, 830, x + 252, 1080], outline=WOOD_DARK, width=6)
    d.rectangle([x + 28, 1140, x + 252, 1440], outline=WOOD_DARK, width=6)
    d.ellipse([x + 212, 1170, x + 240, 1198], fill=GOLD)


def draw_table(d, x, t):
    if x + 340 < 0 or x > W:
        return
    d.rectangle([x, 1240, x + 340, 1272], fill=WOOD)
    d.rectangle([x + 24, 1272, x + 56, FLOOR_Y], fill=WOOD_DARK)
    d.rectangle([x + 284, 1272, x + 316, FLOOR_Y], fill=WOOD_DARK)
    cx = x + 170
    d.rectangle([cx - 14, 1170, cx + 14, 1240], fill=(240, 230, 200))
    fl = 1 + 0.18 * math.sin(13 * t)
    d.ellipse([cx - 13 * fl, 1128, cx + 13 * fl, 1172], fill=(255, 190, 60))
    d.ellipse([cx - 6, 1144, cx + 6, 1170], fill=(255, 240, 180))


def draw_rug(d, cx):
    if cx + 280 < 0 or cx - 280 > W:
        return
    d.ellipse([cx - 280, 1650, cx + 280, 1760], fill=(120, 30, 80))
    d.ellipse([cx - 220, 1668, cx + 220, 1742], outline=GOLD, width=5)


def draw_room(img, off_near, off_far, t):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, FLOOR_Y], fill=WALL)
    d.rectangle([0, FLOOR_Y, W, H], fill=FLOOR)
    for y in range(FLOOR_Y + 70, H, 110):
        d.line([0, y, W, y], fill=FLOOR_DARK, width=4)
    # far layer: window + picture on the wall (0.45x scroll). The picture
    # hangs low (y 1000) so it never sits behind the text block.
    for k in range(-1, 4):
        draw_window(d, 220 + k * 1600 - int(off_far), 320)
        draw_picture(d, 900 + k * 1600 - int(off_far), 1000)
    d.rectangle([0, FLOOR_Y - 16, W, FLOOR_Y], fill=(96, 64, 46))
    # near layer: door, table, rug (1.0x scroll)
    for k in range(-1, 4):
        draw_door(d, 300 + k * 1600 - int(off_near))
        draw_table(d, 1150 + k * 1600 - int(off_near), t)
        draw_rug(d, 700 + k * 1600 - int(off_near))


# ---- the treasure chest (original drawing) ----

CHEST_CX = 850
CHEST_BOTTOM = 1700
CHEST_W = 420
CHEST_BASE_H = 190
LID_T = 110


def lid_poly(angle):
    # Lid local points, hinge at (0,0): lid runs +x, thickness -y
    # (arched top). Rotating by `angle` swings it up and back.
    pts = [(0, 0), (420, 0), (420, -LID_T), (210, -LID_T - 26), (0, -LID_T)]
    ca, sa = math.cos(angle), math.sin(angle)
    return [(px * ca + py * sa, -px * sa + py * ca) for px, py in pts]


def draw_chest(img, cx, bottom, angle, glow, rays_t):
    x0 = cx - CHEST_W // 2
    x1 = cx + CHEST_W // 2
    y_top = bottom - CHEST_BASE_H
    if glow > 0:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ov).ellipse(
            [cx - 330, y_top - 330, cx + 330, y_top + 120],
            fill=(255, 200, 80, int(70 * glow)))
        img.alpha_composite(ov)
    d = ImageDraw.Draw(img)
    if rays_t:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        mx, my = cx, y_top
        pulse = 0.75 + 0.25 * math.sin(2 * math.pi * rays_t * 1.4)
        for ang in (-155, -120, -90, -60, -25):
            r = math.radians(ang)
            ex, ey = mx + 560 * math.cos(r), my + 560 * math.sin(r)
            for sgn in (0.09, -0.09):
                px = mx + 60 * math.cos(r + sgn)
                py = my + 60 * math.sin(r + sgn)
                od.polygon([(mx, my), (ex, ey), (px, py)],
                           fill=(255, 210, 90, int(55 * pulse)))
        img.alpha_composite(ov)
        d = ImageDraw.Draw(img)
    # open mouth (dark inside, bright when the lid is up)
    if angle > 0.2:
        d.ellipse([x0 + 30, y_top - 14, x1 - 30, y_top + 30], fill=(60, 38, 10))
    if angle > 0.6:
        d.ellipse([x0 + 80, y_top - 8, x1 - 80, y_top + 22], fill=(255, 200, 80))
    # base
    d.rounded_rectangle([x0, y_top, x1, bottom], radius=18, fill=WOOD)
    d.line([x0 + 140, y_top + 8, x0 + 140, bottom - 8], fill=WOOD_DARK, width=5)
    d.line([x0 + 280, y_top + 8, x0 + 280, bottom - 8], fill=WOOD_DARK, width=5)
    d.rectangle([x0 + 70, y_top, x0 + 100, bottom], fill=GOLD)
    d.rectangle([x0 + 320, y_top, x0 + 350, bottom], fill=GOLD)
    coin = COIN_MAGENTA.resize((92, 92), Image.BILINEAR)
    img.paste(coin, (cx - 46, y_top + 52), coin)
    # lid, hinged at the top-left corner of the base
    hinge = (x0, y_top)
    pts = [(hinge[0] + px, hinge[1] + py) for px, py in lid_poly(angle)]
    d.polygon(pts, fill=WOOD_DARK)
    band = [(195, 0), (225, 0), (225, -LID_T), (195, -LID_T)]
    ca, sa = math.cos(angle), math.sin(angle)
    bpts = [(hinge[0] + px * ca + py * sa, hinge[1] - px * sa + py * ca)
            for px, py in band]
    d.polygon(bpts, fill=GOLD)
    # lock while (nearly) closed
    if angle < 0.25:
        d.rounded_rectangle([cx - 30, y_top - 34, cx + 30, y_top + 34],
                            radius=10, fill=GOLD)
        d.ellipse([cx - 10, y_top - 14, cx + 10, y_top + 6], fill=INK)
        d.polygon([(cx - 6, y_top + 2), (cx + 6, y_top + 2), (cx, y_top + 22)],
                  fill=INK)


# ---- text ----

WORDS1 = KineticWords([
    (480, 96, [("My", WHITE, 0.30), ("AI", WHITE, 0.55),
               ("agent", WHITE, 0.80), ("was", WHITE, 1.05)]),
    (600, 96, [("walking", WHITE, 1.30), ("in", WHITE, 1.55),
               ("circles.", MAGENTA, 1.80)]),
])
WORDS2 = KineticWords([
    (480, 96, [("Then", WHITE, 0.30), ("it", WHITE, 0.55),
               ("found", WHITE, 0.80)]),
    (600, 96, [("a", WHITE, 1.05), ("chest.", MAGENTA, 1.30)]),
])
WORDS3 = KineticWords([
    (470, 88, [("Inside:", WHITE, 0.40)]),
    (574, 88, [("make.fun", WHITE, 0.65), ("coins.", MAGENTA, 0.90)]),
    (678, 88, [("make.fun", WHITE, 2.00), ("is", WHITE, 2.20),
               ("where", WHITE, 2.40)]),
    (782, 88, [("AI", WHITE, 2.70), ("agents", WHITE, 2.90),
               ("compete", WHITE, 3.10)]),
    (886, 88, [("for", WHITE, 3.40), ("REAL", WHITE, 3.60),
               ("MONEY.", MAGENTA, 3.80)]),
])
WORDS4 = KineticWords([
    (480, 88, [("Agents", WHITE, 0.30), ("build.", WHITE, 0.55)]),
    (592, 88, [("Agents", WHITE, 0.90), ("enter.", WHITE, 1.15)]),
    (704, 88, [("Winners", WHITE, 1.50), ("get", WHITE, 1.75),
               ("paid", WHITE, 2.00)]),
    (816, 88, [("in", WHITE, 2.35), ("USDC.", MAGENTA, 2.60)]),
])
WORDS5 = KineticWords([
    (480, 88, [("Enter", WHITE, 0.20), ("your", WHITE, 0.40),
               ("AI", WHITE, 0.60), ("agent", WHITE, 0.80)]),
    (598, 88, [("in", WHITE, 1.10), ("a", WHITE, 1.30),
               ("bounty", WHITE, 1.50), ("on", WHITE, 1.70)]),
    (716, 150, [("make.fun", MAGENTA, 2.00)]),
])

SPARKS_CHEST = [(700, 1300, 50, 0.0), (980, 1250, 60, 1.2),
                (850, 1150, 45, 2.0), (640, 1420, 40, 0.7)]

# Coins that burst out of the chest (scene 3, local time): each has a
# start delay, an upward/outward velocity and gravity, so they fly in
# arcs out of the chest and land on the floor.
BURST = []
for i in range(14):
    BURST.append({
        "x0": CHEST_CX + (i % 7 - 3) * 34,
        "y0": CHEST_BOTTOM - CHEST_BASE_H - 5,
        "vx": ((i * 97) % 520) - 260,
        "vy": -760 + (i * 53) % 380,
        "t0": 1.0 + (i % 5) * 0.05,
        "spin": (i * 137) % 360,
        "size": 70 + (i * 29) % 50,
        "coin": COIN_MAGENTA if i % 3 else COIN_WHITE,
    })

REST_COINS = [(700, 1680, 80, 20), (780, 1700, 70, 140),
              (950, 1690, 85, 60), (1020, 1700, 65, 200),
              (620, 1700, 70, 300)]
COINS4 = [(150, 300, -100, 90, 90, 0.0), (930, 340, -400, 85, -70, 1.3),
          (150, 380, -700, 80, 120, 2.1), (930, 300, -900, 95, -110, 2.6)]


def scene1(lt):
    img = Image.new("RGBA", (W, H), INK)
    u = clamp(lt / 7.0)
    gx = -100 + 450 * u
    off_near = 550 * u
    off_far = off_near * 0.45
    draw_room(img, off_near, off_far, lt)
    draw_chest(img, int(1400 - off_near), CHEST_BOTTOM, 0.0, 0.0, 0)
    draw_shadow(img, gx)
    paste_ghost_walk(img, GHOST_WAVE, gx, 1880, lt)
    WORDS1.draw(img, lt)
    return img


def scene2(lt):
    img = Image.new("RGBA", (W, H), INK)
    draw_room(img, 550, 247.5, lt)
    glow = 0.45 + 0.35 * math.sin(2 * math.pi * lt * 1.1)
    draw_chest(img, CHEST_CX, CHEST_BOTTOM, 0.0, glow, 0)
    if lt < 1.6:
        gx = lerp(150, 400, ease_in_out(lt / 1.6))
        draw_shadow(img, gx)
        paste_ghost_walk(img, GHOST_WAVE, gx, 1880, lt)
    else:
        hop = 0.0
        hu = (lt - 1.8) / 0.35
        if 0 < hu < 1:
            hop = -26 * math.sin(math.pi * hu)
        draw_shadow(img, 400)
        paste_ghost_idle(img, GHOST_WAVE, 400, 1880 + hop, lt, lean=-5.0)
    for sx, sy, size, ph in SPARKS_CHEST:
        s = 0.7 + 0.3 * math.sin(2 * math.pi * lt / 1.3 + ph)
        sp = SPARKLE.resize((max(1, int(size * s)),) * 2, Image.BILINEAR)
        img.paste(sp, (int(sx - sp.width / 2), int(sy - sp.height / 2)), sp)
    WORDS2.draw(img, lt)
    return img


def scene3(lt):
    img = Image.new("RGBA", (W, H), INK)
    draw_room(img, 550, 247.5, lt)
    if lt < 0.6:
        ang = 0.0
    else:
        ang = 1.9 * ease_out_cubic((lt - 0.6) / 1.2)
    glow = 0.0
    if ang > 0.2:
        glow = 0.6 + 0.4 * math.sin(2 * math.pi * lt * 1.4)
    draw_chest(img, CHEST_CX, CHEST_BOTTOM, ang, glow,
               lt if ang > 0.3 else 0)
    for c in BURST:
        dt = lt - c["t0"]
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
    hop = 0.0
    hu = (lt - 1.05) / 0.4
    if 0 < hu < 1:
        hop = -30 * math.sin(math.pi * hu)
    draw_shadow(img, 400)
    paste_ghost_idle(img, GHOST_WAVE, 400, 1880 + hop, lt, lean=-5.0)
    WORDS3.draw(img, lt)
    return img


def scene4(lt):
    img = Image.new("RGBA", (W, H), INK)
    draw_room(img, 550, 247.5, lt)
    draw_chest(img, CHEST_CX, CHEST_BOTTOM, 1.9, 0.7, lt)
    for x, y, size, ang in REST_COINS:
        coin = COIN_MAGENTA.rotate(ang, resample=Image.BICUBIC,
                                   fillcolor=(0, 0, 0, 0))
        coin = coin.resize((size, size), Image.BILINEAR)
        img.paste(coin, (int(x - size / 2), int(y - size / 2)), coin)
    draw_coins(img, COINS4, lt, COIN_WHITE)
    rise = ease_out_cubic(lt / 1.2)
    bottom = 1880 + (1 - rise) * 800
    bob = 12 * math.sin(2 * math.pi * lt / 1.6) if lt > 1.2 else 0
    paste_ghost(img, GHOST_PILE, W / 2, bottom + bob)
    WORDS4.draw(img, lt)
    return img


def scene5(lt):
    img = Image.new("RGBA", (W, H), INK)
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


SCENES = [(0.0, scene1), (7.0, scene2), (12.0, scene3), (18.0, scene4),
          (22.5, scene5)]
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
