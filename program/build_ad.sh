#!/usr/bin/env bash
# Build the make.fun TikTok ad (bring-the-humans-03) with ffmpeg.
#
# What it does:
#   1. Fetches the press pack's files from make.fun's manifest (brand badge
#      9:16 overlay, referral end card 9:16 transparent webm, four ghost
#      mascot illustrations) and JetBrains Mono Bold for the referral code,
#      verifying the card and badge against the manifest's sha256.
#   2. Renders the four ad scenes with program/render_scenes.py.
#   3. Builds one animated clip per scene (30 fps): the background
#      slowly zooms, the ghost bobs, the text slides up and fades in;
#      the five clips are joined with 0.7 s crossfades (27.5 s total)
#      and a silent audio track (a trending sound can be added on
#      TikTok when the video is posted).
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

# One animated clip per scene (30 fps): background zoom (1.00 -> 1.12),
# ghost bobbing on a sine, text sliding up 46 px and fading in.
# With a ghost: $1=scene base name $2=ghost file $3=ghost width
# $4=ghost bottom $5=duration s $6=frames $7=out. Without a ghost
# (scene 5): $2="" and $3/$4 are ignored.
mkclip() {
  local name="$1" ghost="$2" gw="$3" gb="$4" dur="$5" frames="$6" out="$7"
  local bg="$SCENES/${name}_bg.png" txt="$SCENES/${name}_text.png"
  local zoom="[0:v]zoompan=z='min(1+0.0012*on,1.12)':d=$frames:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,setsar=1[bg]"
  local fadein="[1:v]fade=t=in:st=0:d=0.45:alpha=1[txt]"
  if [ -n "$ghost" ]; then
    ffmpeg -v error -y \
      -framerate 30 -loop 1 -i "$bg" \
      -framerate 30 -loop 1 -t "$dur" -i "$txt" \
      -framerate 30 -loop 1 -t "$dur" -i "$ASSETS/$ghost" \
      -filter_complex "
        $zoom;
        [2:v]scale=$gw:-2[ghost];
        [bg][ghost]overlay=x=(W-w)/2:y='$gb-h+14*sin(2*PI*t/1.8)'[b2];
        $fadein;
        [b2][txt]overlay=x=0:y='46*max(0,1-t/0.55)'[v]" \
      -map '[v]' -frames:v "$frames" -c:v libx264 -pix_fmt yuv420p "$DIR/$out"
  else
    ffmpeg -v error -y \
      -framerate 30 -loop 1 -i "$bg" \
      -framerate 30 -loop 1 -t "$dur" -i "$txt" \
      -filter_complex "
        $zoom;
        $fadein;
        [bg][txt]overlay=x=0:y='46*max(0,1-t/0.55)'[v]" \
      -map '[v]' -frames:v "$frames" -c:v libx264 -pix_fmt yuv420p "$DIR/$out"
  fi
}

# Clip durations (s): 4 + 7 + 7 + 4 + 8.3 = 30.3; four 0.7 s
# crossfades bring the total to 27.5 s.
mkclip scene1 ghost-pile-trophy.png 600 1880 4 120 clip1.mp4
mkclip scene2 ghost-laptop-recording.png 600 1880 7 210 clip2.mp4
mkclip scene3 ghost-judge-paddle.png 600 1880 7 210 clip3.mp4
mkclip scene5 "" 0 0 4 120 clip5.mp4
mkclip scene4 ghost-wave-mail.png 600 1880 8.3 249 clip4.mp4

ffmpeg -v error -y -i "$DIR/clip1.mp4" -i "$DIR/clip2.mp4" -i "$DIR/clip3.mp4" \
  -i "$DIR/clip5.mp4" -i "$DIR/clip4.mp4" -filter_complex "
    [0:v][1:v]xfade=transition=fade:duration=0.7:offset=3.3[x1];
    [x1][2:v]xfade=transition=fade:duration=0.7:offset=9.6[x2];
    [x2][3:v]xfade=transition=fade:duration=0.7:offset=15.9[x3];
    [x3][4:v]xfade=transition=fade:duration=0.7:offset=19.2[v]" \
  -map '[v]' -c:v libx264 -pix_fmt yuv420p "$DIR/video.mp4"
ffmpeg -v error -y -i "$DIR/video.mp4" \
  -f lavfi -i anullsrc=r=44100:cl=stereo -t 27.5 \
  -map 0:v -map 1:a -c:v copy -c:a aac -shortest "$DIR/base.mp4"

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

rm -f "$DIR/clip1.mp4" "$DIR/clip2.mp4" "$DIR/clip3.mp4" "$DIR/clip5.mp4" \
  "$DIR/clip4.mp4" "$DIR/video.mp4" "$DIR/base.mp4"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,codec_name,duration \
  -of default=noprint_wrappers=1 "$DIR/ad.mp4"
sha256sum "$DIR/ad.mp4"
