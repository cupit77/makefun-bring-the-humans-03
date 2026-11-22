// Entry program for bring-the-humans-03 (Node 22, standard library only).
// Its only job is to hand VIDEO.json to the grader: it reads the file from
// the repository root and writes it to the output directory unchanged.
// The video itself is the entry. It was made by the agent in the recorded
// session (see program/build_ad.sh), posted publicly on TikTok, and its full
// address is what VIDEO.json names. Nothing written here is scored.
//
// Local run:
//   mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts

import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const botDir = process.env.MAKEFUN_BOT_DIR ?? '/bot';
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';

const src = join(botDir, 'VIDEO.json');
const dst = join(outDir, 'VIDEO.json');

let raw;
try {
  raw = readFileSync(src);
} catch (err) {
  console.error(`cannot read VIDEO.json from ${src}: ${(err as Error).message}`);
  process.exit(1);
}

let parsed;
try {
  parsed = JSON.parse(raw.toString('utf8'));
} catch (err) {
  console.error(`VIDEO.json is not valid JSON: ${(err as Error).message}`);
  process.exit(1);
}

if (typeof parsed.url !== 'string' || parsed.url.length === 0) {
  console.error('VIDEO.json has no url string');
  process.exit(1);
}

// Warnings only: the gate refuses a placeholder or oversized VIDEO.json,
// but the copy itself must still succeed so the entry can be tested.
if (raw.length > 16384) {
  console.warn(`warning: VIDEO.json is ${raw.length} bytes (gate cap 16384)`);
}
const tiktokShape = /^https:\/\/(www\.|m\.)?tiktok\.com\/@[^/]+\/video\/\d+/;
if (!tiktokShape.test(parsed.url)) {
  console.warn(`warning: url is not a TikTok video address yet: ${parsed.url}`);
}

mkdirSync(outDir, { recursive: true });
writeFileSync(dst, raw);
console.log(`wrote ${dst} (${raw.length} bytes)`);
