/**
 * Replay one rig session's tester from its committed raw bytes and the registrar's beacons,
 * keeping far more than the tester did: per soup, the full census at generations 100, 200 and
 * 300, the live population at each, and the initial density. The generation-300 counts of the
 * session's forms must equal what the tester reported, or the replay aborts.
 *
 * Usage: node --experimental-strip-types explore/replay.ts <session dir> <out.jsonl>
 */
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { FORM_IDS, mixWithBeacon } from "../rig/common.ts";
import { bitStep, cellsFromRows, rowsFromBytes } from "../rig/bitlife.ts";
import { censusCounts } from "../src/sim/protocol.ts";

const [dir, out] = process.argv.slice(2);
const regDir = join(dir, "registrar");
const sessionFile = readdirSync(regDir).find((f) => f.startsWith("session-"));
if (!sessionFile) throw new Error("no session file");
const s = JSON.parse(readFileSync(join(regDir, sessionFile), "utf8"));
const { protocol, assignment, blocks } = s;
const spec = protocol.tester;
const size = spec.size;
const per = (size * size) / 8;
const STOPS = [100, 200, 300];
if (spec.generations !== 300 || size !== 32) throw new Error("expected 32 x 32 soups run 300 generations");

const flat = (m: Map<number, number>) => {
  const a: number[] = [];
  for (const [k, v] of m) a.push(k, v);
  return a;
};

const lines: string[] = [];
const t0 = Date.now();
for (let b = 0; b < blocks.length; b++) {
  const raw = readFileSync(join(dir, "tester", `block-${b}.bin`));
  const beacon: string | undefined = blocks[b].commit?.beacon; // rig/1 had no beacon
  const soups: unknown[] = [];
  const sum: Record<string, number> = Object.fromEntries(protocol.forms.map((f: string) => [f, 0]));
  for (let i = 0; i < spec.soups; i++) {
    const bytes = raw.subarray(i * per, (i + 1) * per);
    let a: Uint32Array = rowsFromBytes(beacon ? mixWithBeacon(bytes, beacon, i) : bytes);
    let bb: Uint32Array = new Uint32Array(32);
    let d0 = 0;
    for (let y = 0; y < 32; y++) for (let x = 0; x < 32; x++) d0 += (a[y] >>> x) & 1;
    const rec: unknown[] = [d0];
    for (let g = 1; g <= 300; g++) {
      bitStep(a, bb);
      const t = a;
      a = bb;
      bb = t;
      if (STOPS.includes(g)) {
        const cells = cellsFromRows(a);
        let pop = 0;
        for (let k = 0; k < cells.length; k++) pop += cells[k];
        const c = censusCounts(cells, size, size, true);
        rec.push(pop, flat(c));
        if (g === 300) for (const f of protocol.forms) sum[f] += c.get(FORM_IDS[f]) ?? 0;
      }
    }
    soups.push(rec);
  }
  for (const f of protocol.forms) {
    if (sum[f] !== blocks[b].tested.counts[f]) throw new Error(`block ${b} ${f}: replay ${sum[f]} != recorded ${blocks[b].tested.counts[f]}`);
  }
  lines.push(JSON.stringify({ block: b, target: assignment[b], leakExtra: blocks[b].tested.leakExtra ?? 0, recorded: blocks[b].tested.counts, soups }));
  if (b % 10 === 9) console.log(`${protocol.label} block ${b + 1}/${blocks.length} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
writeFileSync(out, lines.join("\n") + "\n");
writeFileSync(out.replace(/\.jsonl$/, ".meta.json"), JSON.stringify({ label: protocol.label, protocol, assignment, forms: protocol.forms, formIds: FORM_IDS, blocks: blocks.map((x: { handedAt: string; trained: unknown; commit: unknown; tested: unknown }) => ({ handedAt: x.handedAt, trained: x.trained, commitAt: (x.commit as { at: string } | undefined)?.at ?? null, testedAt: (x.tested as { at: string }).at })), report: s.report }));
console.log(`${protocol.label} done, all ${blocks.length} blocks match the recorded counts`);
