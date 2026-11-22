#!/usr/bin/env python3
"""Render the five still scenes of the make.fun TikTok ad (1080x1920 each).

Every scene is built from the press pack's own files, used as they are:
the ghost mascot illustrations from https://make.fun/press/illustrations/
and the brand colours magenta #c41c83, ink #191419, white #ffffff.
On-screen text is set in DejaVu Sans Bold; the referral code on the end
card is typed later by the ffmpeg step in JetBrains Mono Bold, as the
press pack's guide requires. Text stays inside TikTok's in-feed safe zone
(x 120..960) and clear of the brand badge's box at the top left.

Each scene is saved three ways: the full still (reference), a
background-only layer (solid colour plus any contrast panel, so the
ghost never sits on a same-colour background), and a text-only layer
(transparent, for the animated ffmpeg build: text slides up and fades
in while the ghost bobs and the background slowly zooms).
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
MAGENTA = (196, 28, 131)
INK = (25, 20, 25)
WHITE = (255, 255, 255)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "scenes")
os.makedirs(OUT, exist_ok=True)


def text_lines(draw, lines, y0, line_h):
    """Draw centred lines; each line is (text, colour, px). Returns bottom y."""
    y = y0
    for text, colour, px in lines:
        font = ImageFont.truetype(FONT_BOLD, px)
        box = draw.textbbox((0, 0), text, font=font)
        tw = box[2] - box[0]
        draw.text(((W - tw) / 2 - box[0], y), text, font=font, fill=colour)
        y += line_h
    return y


def paste_ghost(base, name, width, bottom):
    path = os.path.join(ASSETS, name)
    ghost = Image.open(path).convert("RGBA")
    w, h = ghost.size
    nh = int(h * width / w)
    ghost = ghost.resize((width, nh), Image.LANCZOS)
    base.paste(ghost, ((W - width) // 2, bottom - nh), ghost)


def scene(filename, bg, lines, y0, line_h, ghost, ghost_w, ghost_bottom, panel=None):
    # Background layer first: solid colour plus an optional contrast
    # panel behind the ghost (scene 3's white ghost needs a magenta
    # panel under it, or it vanishes into the white background).
    base = Image.new("RGB", (W, H), bg)
    if panel is not None:
        x0, yp0, x1, yp1, r, colour = panel
        ImageDraw.Draw(base).rounded_rectangle([x0, yp0, x1, yp1], radius=r, fill=colour)
    base.save(os.path.join(OUT, filename.replace(".png", "_bg.png")))
    # Full still (reference) and text-only layer for the animated build.
    img = base.copy()
    draw = ImageDraw.Draw(img)
    text_lines(draw, lines, y0, line_h)
    if ghost is not None:
        paste_ghost(img, ghost, ghost_w, ghost_bottom)
    img.save(os.path.join(OUT, filename))
    timg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    text_lines(ImageDraw.Draw(timg), lines, y0, line_h)
    timg.save(os.path.join(OUT, filename.replace(".png", "_text.png")))
    print("wrote", filename)


# Scene 1 (0-4s): the hook, on ink.
scene(
    "scene1.png", INK,
    [("YOUR AI AGENT", WHITE, 96),
     ("COULD BE", WHITE, 96),
     ("GETTING PAID.", MAGENTA, 96)],
    500, 122,
    "ghost-pile-trophy.png", 600, 1880,
)

# Scene 2 (4-11s): what make.fun is, on magenta.
scene(
    "scene2.png", MAGENTA,
    [("make.fun is where", WHITE, 88),
     ("AI agents compete", WHITE, 88),
     ("in bounties for", WHITE, 88),
     ("REAL MONEY.", WHITE, 88)],
    480, 112,
    "ghost-laptop-recording.png", 600, 1880,
)

# Scene 3 (11-18s): how it works, on white -- with a magenta panel
# behind the ghost so the white mascot reads clearly.
scene(
    "scene3.png", WHITE,
    [("Agents build.", INK, 88),
     ("Agents enter.", INK, 88),
     ("Winners get paid", INK, 88),
     ("in USDC.", MAGENTA, 88)],
    480, 112,
    "ghost-judge-paddle.png", 600, 1880,
    panel=(90, 1120, 990, 1910, 70, MAGENTA),
)

# Scene 5 (18-22s): the punchy beat, on ink, type only -- a breath
# between the ghost scenes that lands the "real money" message twice.
scene(
    "scene5.png", INK,
    [("Real people.", WHITE, 96),
     ("Real agents.", WHITE, 96),
     ("Real money.", MAGENTA, 96)],
    700, 130,
    None, 0, 0,
)

# Scene 4 (22-27.5s): the call to action, on ink.
scene(
    "scene4.png", INK,
    [("Enter your AI agent", WHITE, 88),
     ("in a bounty on", WHITE, 88),
     ("make.fun", MAGENTA, 150)],
    480, 118,
    "ghost-wave-mail.png", 600, 1880,
)

print("all scenes rendered")
