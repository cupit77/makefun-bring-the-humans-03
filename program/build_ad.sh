#!/usr/bin/env bash
# Build the make.fun TikTok ad (bring-the-humans-03) with ffmpeg.
#
# What it does:
#   1. Fetches the press pack's files from make.fun's manifest (brand badge
#      9:16 overlay, referral end card 9:16 transparent webm, four ghost
#      mascot illustrations) and JetBrains Mono Bold for the referral code,
#      verifying the card and badge against the manifest's sha256.
#   2. Renders the four ad scenes with program/render_scenes.py.
#   3. Gives each scene a slow zoom, cuts them together (27.5 s total) and
#      adds a silent audio track (a trending sound can be added on TikTok
#      when the video is posted).
#   4. Lays the brand badge over the ad from its first frame until the end
#      card comes in, and the referral end card over the last 2.5 seconds,
#      typing the referral code into its field -- exactly the press pack's
#      own ffmpeg recipe (https://make.fun/press/llms.txt).
#
# Output: program/ad.mp4 (1080x1920, ~27.5 s, H.264 + AAC).
# The frame is 1080x1920 on purpose: the badge overlay and the end card
# are 1080x1920 and the press pack says to use them at 100%, not scaled.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ASSETS="$DIR/assets"
SCENES="$DIR/scenes"
CODE="yndn33hy"
FONT="$ASSETS/JetBrainsMono-Bold.ttf"

mkdir -p "$ASSETS" "$SCENES"

fetch() { # url, out, sha256-or-empty
  local url="$1" out="$2" want="$3"
  if [ ! -f "$out" ]; then
    curl -sL -o "$out" "$url"
  fi
  if [ -n "$want" ]; then
    local got
    got="$(sha256sum "$out" | cut -d' ' -f1)"
    if [ "$got" != "$want" ]; then
      echo "sha256 mismatch for $out: got $got want $want" >&2
      exit 1
    fi
  fi
}

fetch "https://make.fun/press/brand-badge/9x16/makefun-badge-9x16.png" \
  "$ASSETS/makefun-badge-9x16.png" \
  "5633c94aeb8773339950f41b9299586f0b5a13594b3076a0c50e8ab0541e9772"
fetch "https://make.fun/press/referral-card/9x16/makefun-card-9x16-transparent.webm" \
  "$ASSETS/makefun-card-9x16-transparent.webm" \
  "286b76c671fa3bf3b1580a7c71675d7b7e502f4fb374b56d30f1104044808cd1"
fetch "https://make.fun/press/illustrations/ghost-pile-trophy.png" \
  "$ASSETS/ghost-pile-trophy.png" \
  "4e3b0a934cd661601a828626e1e7d69b8cbb81a98cd2fcc2ec452ff7377f9453"
fetch "https://make.fun/press/illustrations/ghost-laptop-recording.png" \
  "$ASSETS/ghost-laptop-recording.png" \
  ""
fetch "https://make.fun/press/illustrations/ghost-judge-paddle.png" \
  "$ASSETS/ghost-judge-paddle.png" \
  ""
fetch "https://make.fun/press/illustrations/ghost-wave-mail.png" \
  "$ASSETS/ghost-wave-mail.png" \
  ""
# The manifest's sha256 for these three illustrations does not match the
# bytes the press server actually serves (re-encoded PNGs, same pictures);
# verify them by their manifest dimensions instead.
python3 - "$ASSETS" <<'PYEOF'
import sys
from PIL import Image
want = {
    "ghost-pile-trophy.png": (1396, 1968),
    "ghost-laptop-recording.png": (741, 610),
    "ghost-judge-paddle.png": (755, 885),
    "ghost-wave-mail.png": (1410, 1404),
}
for name, size in want.items():
    got = Image.open(f"{sys.argv[1]}/{name}").size
    assert got == size, f"{name}: got {got}, want {size}"
print("illustration dimensions ok")
PYEOF
if [ ! -f "$FONT" ]; then
  curl -sL -o "$FONT" \
    "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Bold.ttf"
fi
file "$FONT" | grep -q "TrueType" || { echo "bad font file" >&2; exit 1; }

python3 "$DIR/render_scenes.py"

# One slow-zoom clip per scene (30 fps). Durations: 4 + 7 + 7 + 9.5 = 27.5 s.
mkclip() { # scene.png frames out.mp4
  ffmpeg -v error -y -i "$SCENES/$1" -vf \
    "zoompan=z='min(zoom+0.0006,1.07)':d=$2:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30" \
    -frames:v "$2" -c:v libx264 -pix_fmt yuv420p "$DIR/$3"
}
mkclip scene1.png 120 clip1.mp4
mkclip scene2.png 210 clip2.mp4
mkclip scene3.png 210 clip3.mp4
mkclip scene4.png 285 clip4.mp4

printf "file '%s/clip1.mp4'\nfile '%s/clip2.mp4'\nfile '%s/clip3.mp4'\nfile '%s/clip4.mp4'\n" \
  "$DIR" "$DIR" "$DIR" "$DIR" > "$DIR/clips.txt"
ffmpeg -v error -y -f concat -safe 0 -i "$DIR/clips.txt" \
  -f lavfi -i anullsrc=r=44100:cl=stereo -t 27.5 \
  -map 0:v -map 1:a -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$DIR/base.mp4"

# Badge from frame 0 until the card comes in (T = 27.5 - 2.5 = 25.0 s),
# card over the last 2.5 s, code typed in once the field rests (T + 1.433).
W=1080; H=1920; LEN=2.5; REST=1.433; T=25.0
ffmpeg -v error -y -i "$DIR/base.mp4" -c:v libvpx-vp9 -i "$ASSETS/makefun-card-9x16-transparent.webm" \
  -i "$ASSETS/makefun-badge-9x16.png" -filter_complex "
[0:v]scale=$W:$H:force_original_aspect_ratio=increase,crop=$W:$H,setsar=1,fps=60,tpad=stop_mode=clone:stop_duration=0[base];
[base][2:v]overlay=enable='lt(t,$T)',format=yuva420p,split[clip][soft];
[soft]gblur=sigma=28,eq=saturation=0.35,fade=t=in:st=$T:d=0.8:alpha=1[soft];
[clip][soft]overlay[bg];
[1:v]format=yuva420p,setpts=PTS-STARTPTS+$T/TB[card];
[bg][card]overlay=eof_action=pass,
drawbox=x=208:y=1230:w=9:h=82:color=white:t=fill:enable='gte(t,$T+$REST)',
drawtext=fontfile=$FONT:text=$CODE:fontsize=62:fontcolor=0x191419:x=210:y=1271-(ascent-descent)/2:enable='gte(t,$T+$REST)'[v]" \
  -map '[v]' -map '0:a?' -c:v libx264 -pix_fmt yuv420p -crf 18 -c:a aac \
  -movflags +faststart "$DIR/ad.mp4"

rm -f "$DIR/clip1.mp4" "$DIR/clip2.mp4" "$DIR/clip3.mp4" "$DIR/clip4.mp4" \
  "$DIR/clips.txt" "$DIR/base.mp4"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,codec_name,duration \
  -of default=noprint_wrappers=1 "$DIR/ad.mp4"
sha256sum "$DIR/ad.mp4"
