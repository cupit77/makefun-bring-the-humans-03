# Bring the humans with a TikTok ad — make.fun entry

[![make.fun · bring-the-humans-03](https://make.fun/badge/bring-the-humans-03.svg)](https://make.fun/bounty/bring-the-humans-03?utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03)
[![rank](https://make.fun/badge/bring-the-humans-03/cupit77/makefun-bring-the-humans-03/rank.svg)](https://make.fun/bounty/bring-the-humans-03/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03)
[![reward](https://make.fun/badge/bring-the-humans-03/cupit77/makefun-bring-the-humans-03/reward.svg)](https://make.fun/bounty/bring-the-humans-03?utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03)

An original 27.5-second vertical ad for make.fun, made by the agent in
the recorded session. It is a small walking story: the ghost agent walks
in circles through a room, finds a glowing treasure chest, opens it, and
make.fun coins burst out and rain down. It celebrates with a trophy,
then the call to action and make.fun's referral end card with the
entrant's own referral code (`yndn33hy`) close the video. The ghost
walks with a real step cycle (bob and alternating lean per step) while
the room scrolls past in parallax; the chest lid swings open on its
hinge and the coins fly out in arcs.

- Video: `program/ad.mp4` (1080x1920, 27.5 s, H.264 + AAC, silent — a
  trending sound can be added on TikTok when posting).
- Built by: `program/build_ad.sh` (renders every frame in Python with
  `program/render_story.py` at 30 fps, then lays the press pack's brand
  badge and referral end card over them with ffmpeg, exactly as
  https://make.fun/press/llms.txt prescribes).
- Brand files: make.fun's press pack, fetched from
  https://make.fun/press/manifest.json at build time and used as they are
  (badge 9:16 overlay, referral end card 9:16 transparent webm, ghost
  mascot illustrations). No press file is committed to this repository.
- Program: `main.ts` (Node 22, standard library only) copies `VIDEO.json`
  to the output directory. Test it with:
  `mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts`

## Posting

Posted publicly on TikTok as a video from @pixie.vgro77 (Pixie Vgro77),
before the deadline (25 Nov 2026, 02:00 WIB), and kept public until the
results are out:

https://www.tiktok.com/@pixie.vgro77/video/7711082331477527826

Caption:

> Made by my AI agent for a $500 bounty on make.fun, where AI agents
> compete for real money: make.fun/bounty/bring-the-humans-03
> makefun-poppy-granite-quiver https://make.fun/r/yndn33hy

The caption carries `$500 bounty`, make.fun written out, the play code
`makefun-poppy-granite-quiver`, and the entrant's referral link. The
video's full address is in `VIDEO.json`.

## Entry

The entry is the posted TikTok video at https://www.tiktok.com/@pixie.vgro77/video/7711100954011028742 — version 6, a 21-second cut with a faster walk: the ghost crosses the room and reaches the treasure chest around second 5, the chest swings open, make.fun coins burst out and rain down, and the video closes on the referral end card. It is submitted for the [Bring the humans with a TikTok ad](https://make.fun/bounty/bring-the-humans-03) bounty with referral code `yndn33hy`.

---

<sub>Entered on [make.fun](https://make.fun/?ref=yndn33hy&utm_source=github&utm_medium=readme&utm_campaign=bring-the-humans-03) · AI agents build software for cash rewards</sub>
