/**
 * Runs the three rig servers as separate processes with separate data directories and
 * separate secrets, drives one session, reveals it, audits it, and writes a report.
 *
 *   node --experimental-strip-types rig/run-local.ts rig/protocols/<name>.json
 *
 * For a run on separate machines, start registrar.ts, trainer.ts and tester.ts on three
 * hosts with the same env variables this script sets, and use the registrar's HTTP API.
 */
import { spawn, execSync, type ChildProcess } from "node:child_process";
import { randomInt } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:net";
import { cpus, platform, release } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { ChainLog, call, canonical, sha256hex, sleep, testSoup, token, type Protocol } from "./common.ts";
import type { Report } from "./analysis.ts";

const here = fileURLToPath(new URL(".", import.meta.url));
const protocolPath = process.argv[2];
if (!protocolPath) throw new Error("usage: run-local.ts <protocol.json>");
const protocolText = readFileSync(protocolPath, "utf8");
const protocol = JSON.parse(protocolText) as Protocol;
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const root = join(here, ".data", `${protocol.label}-${stamp}`);
const tokens = { admin: token(), trainer: token(), tester: token() };
const children: ChildProcess[] = [];

async function freePort(): Promise<number> {
  return new Promise((resolve) => {
    const s = createServer();
    s.listen(0, "127.0.0.1", () => {
      const port = (s.address() as { port: number }).port;
      s.close(() => resolve(port));
    });
  });
}

function start(name: string, envVars: Record<string, string>) {
  const child = spawn(process.execPath, ["--experimental-strip-types", "--no-warnings", join(here, `${name}.ts`)], {
    env: { PATH: process.env.PATH ?? "", RIG_LINGER_MS: "600000", ...envVars },
    stdio: ["ignore", "inherit", "inherit"],
  });
  child.on("exit", (code) => {
    if (code) console.error(`${name} exited with ${code}`);
  });
  children.push(child);
}

async function waitHealthy(url: string) {
  for (let i = 0; i < 200; i++) {
    try {
      await call(`${url}/health`);
      return;
    } catch {
      await sleep(50);
    }
  }
  throw new Error(`${url} did not come up`);
}

const ports = { registrar: await freePort(), trainer: await freePort(), tester: await freePort() };
const registrar = `http://127.0.0.1:${ports.registrar}`;
const dirs = { registrar: join(root, "registrar"), trainer: join(root, "trainer"), tester: join(root, "tester") };
for (const d of Object.values(dirs)) mkdirSync(d, { recursive: true });

try {
  // Each process gets only its own secret.
  start("registrar", {
    PORT: String(ports.registrar),
    RIG_DATA_DIR: dirs.registrar,
    RIG_ADMIN_TOKEN: tokens.admin,
    RIG_TRAINER_TOKEN: tokens.trainer,
    RIG_TESTER_TOKEN: tokens.tester,
  });
  await waitHealthy(registrar);
  const opened = await call<{ session: string; commitment: string; protocolHash: string; analysisHash: string }>(
    `${registrar}/session`,
    { token: tokens.admin, body: { protocol } },
  );
  console.log(`session ${opened.session} · commitment ${opened.commitment} · protocol ${opened.protocolHash.slice(0, 16)}`);
  start("trainer", {
    PORT: String(ports.trainer),
    RIG_DATA_DIR: dirs.trainer,
    RIG_REGISTRAR_URL: registrar,
    RIG_TRAINER_TOKEN: tokens.trainer,
    RIG_SESSION: opened.session,
  });
  start("tester", {
    PORT: String(ports.tester),
    RIG_DATA_DIR: dirs.tester,
    RIG_REGISTRAR_URL: registrar,
    RIG_TESTER_TOKEN: tokens.tester,
    RIG_SESSION: opened.session,
  });

  const t0 = Date.now();
  let lastShown = -1;
  for (;;) {
    const st = await call<{ tested: number; blocks: number }>(`${registrar}/status?session=${opened.session}`);
    if (st.tested !== lastShown && (st.tested % 10 === 0 || st.tested === st.blocks)) {
      console.log(`  ${st.tested}/${st.blocks} blocks · ${((Date.now() - t0) / 1000).toFixed(0)}s`);
      lastShown = st.tested;
    }
    if (st.tested === st.blocks) break;
    await sleep(500);
  }

  const revealed = await call<{
    assignment: string[];
    blocks: { trained: { trainingHash: string; occurrences: number }; tested: { counts: Record<string, number>; entropyHash: string } }[];
    report: Report;
    logHead: string;
    protocolHash: string;
    analysisHash: string;
    commitment: string;
    nonce: string;
  }>(`${registrar}/reveal`, { token: tokens.admin, body: { session: opened.session } });

  // Audit: replay the tester's counts from its raw entropy, and check the trainer's records.
  const audits: { block: number; testerReplay: boolean; entropyHash: boolean; trainerTarget: boolean; trainerHash: boolean }[] = [];
  for (const block of [...new Set(Array.from({ length: 4 }, () => randomInt(protocol.blocks)))]) {
    const tester = await call<{ bytes: string }>(`http://127.0.0.1:${ports.tester}/audit/${block}`);
    const bytes = Buffer.from(tester.bytes, "base64");
    const per = (protocol.tester.size * protocol.tester.size) / 8;
    const replay: Record<string, number> = Object.fromEntries(protocol.forms.map((f) => [f, 0]));
    for (let i = 0; i < protocol.tester.soups; i++) {
      const c = testSoup(bytes.subarray(i * per, (i + 1) * per), protocol.tester, protocol.forms);
      for (const f of protocol.forms) replay[f] += c[f];
    }
    const trainer = await call<Record<string, unknown>>(`http://127.0.0.1:${ports.trainer}/audit/${block}`);
    audits.push({
      block,
      testerReplay: canonical(replay) === canonical(revealed.blocks[block].tested.counts),
      entropyHash: sha256hex(bytes) === revealed.blocks[block].tested.entropyHash,
      trainerTarget: trainer.target === revealed.assignment[block],
      trainerHash: sha256hex(canonical(trainer)) === revealed.blocks[block].trained.trainingHash,
    });
  }
  const chain = ChainLog.verify(join(dirs.registrar, "log.jsonl"));
  const occurrences = revealed.blocks.reduce((s, b) => s + b.trained.occurrences, 0);

  const gitHead = (() => {
    try {
      return execSync("git rev-parse HEAD", { cwd: here }).toString().trim();
    } catch {
      return "unknown";
    }
  })();
  const out = {
    label: protocol.label,
    positiveControl: protocol.leak.relative > 0,
    leakRelative: protocol.leak.relative,
    protocolFile: protocolPath,
    protocolFileSha256: sha256hex(protocolText),
    protocolHash: revealed.protocolHash,
    analysisHash: revealed.analysisHash,
    commitment: revealed.commitment,
    nonce: revealed.nonce,
    logHead: revealed.logHead,
    logChainValid: chain.ok,
    logEntries: chain.entries,
    gitHead,
    environment: {
      topology: "three processes on one host (separate data dirs, separate secrets, HTTP only)",
      entropy: "node:crypto randomBytes (OS CSPRNG)",
      node: process.version,
      platform: `${platform()} ${release()}`,
      cpu: cpus()[0]?.model ?? "unknown",
    },
    seconds: Math.round((Date.now() - t0) / 1000),
    trainingOccurrences: occurrences,
    audits,
    report: revealed.report,
    assignment: revealed.assignment,
    blocks: revealed.blocks,
  };
  const reportsDir = join(here, "reports");
  mkdirSync(reportsDir, { recursive: true });
  const base = join(reportsDir, `${protocol.label}`);
  writeFileSync(`${base}.json`, JSON.stringify(out, null, 2));
  writeFileSync(`${base}.md`, markdown(out));
  console.log(markdown(out));
} finally {
  for (const child of children) child.kill();
}

function pct(x: number, digits = 2) {
  return `${x >= 0 ? "+" : ""}${(x * 100).toFixed(digits)}%`;
}

function markdown(o: {
  label: string;
  positiveControl: boolean;
  leakRelative: number;
  report: Report;
  audits: { testerReplay: boolean; entropyHash: boolean; trainerTarget: boolean; trainerHash: boolean }[];
  logChainValid: boolean;
  [k: string]: unknown;
}): string {
  const r = o.report;
  const allAudits = o.audits.every((a) => a.testerReplay && a.entropyHash && a.trainerTarget && a.trainerHash);
  const verdict = o.positiveControl
    ? r.detected
      ? `Positive control: the deliberate +${(o.leakRelative * 100).toFixed(1)}% channel was detected (Holm p = ${r.holm.t1.toPrecision(3)}). The rig can see an effect of this size.`
      : `Positive control FAILED: the deliberate +${(o.leakRelative * 100).toFixed(1)}% channel was not detected (Holm p = ${r.holm.t1.toPrecision(3)}). The rig is not sensitive enough at this size.`
    : r.detected
      ? `Anomaly: trained forms were over-represented in the isolated tester (effect ${pct(r.t1.effect)}, Holm p = ${r.holm.t1.toPrecision(3)}). Not a claim yet: it needs replication on physically separate machines with independent entropy.`
      : `No effect detected. Estimated effect ${pct(r.t1.effect)} (95% CI ${pct(r.t1.ci[0])} to ${pct(r.t1.ci[1])}), Holm p = ${r.holm.t1.toPrecision(3)}. An effect of ${pct(r.t1.mde80)} or more would have been detected with about 80% power.`;
  const rows = r.perForm
    .map((f) => `| ${f.form} | ${f.timesTrained} | ${f.trained.toFixed(1)} | ${f.untrained.toFixed(1)} | ${((f.ratio - 1) * 100).toFixed(2)}% |`)
    .join("\n");
  return `# Rig report: ${o.label}${o.positiveControl ? " (POSITIVE CONTROL: deliberate channel)" : ""}

${verdict}

| | |
|---|---|
| Primary T1 (block-locked) | effect ${pct(r.t1.effect)}, CI ${pct(r.t1.ci[0])} to ${pct(r.t1.ci[1])}, p ${r.t1.p.toPrecision(3)}, Holm ${r.holm.t1.toPrecision(3)} |
| Secondary T2 (cumulative dose) | mean correlation ${r.t2.stat.toFixed(4)}, p ${r.t2.p.toPrecision(3)}, Holm ${r.holm.t2.toPrecision(3)} |
| Null 95th percentile / 80%-power MDE | ${pct(r.t1.nullQ95)} / ${pct(r.t1.mde80)} |
| Blocks · α | ${r.blocks} · ${r.alpha} |
| Training occurrences | ${o.trainingOccurrences} |
| Audits (tester replay, entropy hash, trainer target, trainer hash) | ${allAudits ? "all passed" : "FAILED"} on ${o.audits.length} blocks |
| Log chain | ${o.logChainValid ? "valid" : "BROKEN"}, head ${String(o.logHead).slice(0, 16)}… |
| Commitment | ${String(o.commitment).slice(0, 16)}… (verified at reveal) |
| Protocol / analysis hash | ${String(o.protocolHash).slice(0, 16)}… / ${String(o.analysisHash).slice(0, 16)}… |
| Code | ${String(o.gitHead).slice(0, 12)} |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
${rows}

Topology: ${(o.environment as { topology: string }).topology}. Entropy: ${(o.environment as { entropy: string }).entropy}.
`;
}
