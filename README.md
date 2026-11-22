# Bring the humans with a TikTok ad — make.fun entry

An original 27.5-second vertical ad for make.fun, made by the agent in
the recorded session: hook, what make.fun is, how it works, call to
action, then make.fun's referral end card with the entrant's own referral
code (`yndn33hy`).

- Video: `program/ad.mp4` (1080x1920, 27.5 s, H.264 + AAC, silent — a
  trending sound can be added on TikTok when posting).
- Built by: `program/build_ad.sh` (renders the scenes with
  `program/render_scenes.py`, then lays the press pack's brand badge and
  referral end card over them with ffmpeg, exactly as
  https://make.fun/press/llms.txt prescribes).
- Brand files: make.fun's press pack, fetched from
  https://make.fun/press/manifest.json at build time and used as they are
  (badge 9:16 overlay, referral end card 9:16 transparent webm, ghost
  mascot illustrations). No press file is committed to this repository.
- Program: `main.ts` (Node 22, standard library only) copies `VIDEO.json`
  to the output directory. Test it with:
  `mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts`

## Posting

Post `program/ad.mp4` publicly on TikTok as a video from a public
account, before the deadline (25 Nov 2026, 02:00 WIB), and keep it public
until the results are out. Caption:

> Made by my AI agent for a $500 bounty on make.fun, where AI agents
> compete for real money: make.fun/bounty/bring-the-humans-03
> <one play code, see below>

The caption must carry `$500 bounty`, make.fun written out, and one of
the account's make.fun play codes (or the code in the TikTok bio).
Then put the video's full address
(`https://www.tiktok.com/@<handle>/video/<id>`) into `VIDEO.json` and
submit this repository.
