/**
 * Runs the three rig servers as separate processes, each with its own data directory and
 * its own secret, drives one session, reveals it, audits every block, and writes a report.
 * When started as root it also runs each server as its own system user with a private
 * (0700) data directory, so the tester cannot read the trainer's or registrar's files.
 *
 *   node --experimental-strip-types rig/run-local.ts rig/protocols/<name>.json
 *
 * For a run on separate machines, start registrar.ts, trainer.ts and tester.ts on three
 * hosts with the same env variables this script sets, and use the registrar's HTTP API.
 */
import { spawn, execSync, type ChildProcess } from "node:child_process";
import { chmodSync, chownSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:net";
import { cpus, platform, release } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { ChainLog, call, canonical, sha256hex, sleep, testBlock, token, type Protocol } from "./common.ts";
import type { Report } from "./analysis.ts";

const here = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = join(here, "..");
const protocolPath = process.argv[2];
if (!protocolPath) throw new Error("usage: run-local.ts <protocol.json>");
const protocolText = readFileSync(protocolPath, "utf8");
const protocol = JSON.parse(protocolText) as Protocol;
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const root = join(here, ".data", `${protocol.label}-${stamp}`);
const reportsDir = process.env.RIG_REPORTS_DIR ?? join(here, "reports");
const tokens = { admin: token(), trainer: token(), tester: token() };
const children: ChildProcess[] = [];

type Role = "registrar" | "trainer" | "tester";
const ROLES: Role[] = ["registrar", "trainer", "tester"];

/** As root, one system user per role; otherwise everyone runs as the current user. */
function users(): Record<Role, { uid: number; gid: number } | null> {
  const none = { registrar: null, trainer: null, tester: null };
  if (process.getuid?.() !== 0 || process.env.RIG_SAME_USER === "1") return none;
  const out: Record<Role, { uid: number; gid: number } | null> = { ...none };
  for (const role of ROLES) {
    const name = `rig-${role}`;
    try {
      execSync(`id -u ${name}`, { stdio: "ignore" });
    } catch {
      execSync(`useradd --system --no-create-home --shell /usr/sbin/nologin ${name}`, { stdio: "ignore" });
    }
    out[role] = {
      uid: Number(execSync(`id -u ${name}`).toString().trim()),
      gid: Number(execSync(`id -g ${name}`).toString().trim()),
    };
  }
  return out;
}

async function freePort(): Promise<number> {
  return new Promise((resolve) => {
    const s = createServer();
    s.listen(0, "127.0.0.1", () => {
      const port = (s.address() as { port: number }).port;
      s.close(() => resolve(port));
    });
  });
}

function start(role: Role, user: { uid: number; gid: number } | null, envVars: Record<string, string>) {
  const child = spawn(process.execPath, ["--experimental-strip-types", "--no-warnings", join(here, `${role}.ts`)], {
    env: { PATH: process.env.PATH ?? "", RIG_LINGER_MS: "600000", ...envVars },
    stdio: ["ignore", "inherit", "inherit"],
    ...(user ? { uid: user.uid, gid: user.gid } : {}),
  });
  child.on("exit", (code) => {
    if (code) console.error(`${role} exited with ${code}`);
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

const who = users();
const ports = { registrar: await freePort(), trainer: await freePort(), tester: await freePort() };
const registrar = `http://127.0.0.1:${ports.registrar}`;
const dirs = { registrar: join(root, "registrar"), trainer: join(root, "trainer"), tester: join(root, "tester") };
mkdirSync(root, { recursive: true });
for (const role of ROLES) {
  mkdirSync(dirs[role], { recursive: true });
  chmodSync(dirs[role], 0o700);
  const user = who[role];
  if (user) chownSync(dirs[role], user.uid, user.gid);
}

try {
  // Each process gets only its own secret.
  start("registrar", who.registrar, {
    PORT: String(ports.registrar),
    RIG_DATA_DIR: dirs.registrar,
    RIG_ROOT: repoRoot,
    RIG_ADMIN_TOKEN: tokens.admin,
    RIG_TRAINER_TOKEN: tokens.trainer,
    RIG_TESTER_TOKEN: tokens.tester,
  });
  await waitHealthy(registrar);
  const opened = await call<{ session: string; commitment: string; protocolHash: string; codeHash: string }>(
    `${registrar}/session`,
    { token: tokens.admin, body: { protocol } },
  );
  console.log(`session ${opened.session} · commitment ${opened.commitment} · code ${opened.codeHash.slice(0, 16)}`);
  start("trainer", who.trainer, {
    PORT: String(ports.trainer),
    RIG_DATA_DIR: dirs.trainer,
    RIG_REGISTRAR_URL: registrar,
    RIG_TRAINER_TOKEN: tokens.trainer,
    RIG_SESSION: opened.session,
  });
  start("tester", who.tester, {
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
    blocks: {
      trained: { trainingHash: string; occurrences: number; overran: boolean };
      commit: { bytesHash: string; beacon: string };
      tested: { counts: Record<string, number> };
    }[];
    report: Report;
    logHead: string;
    protocolHash: string;
    codeHash: string;
    commitment: string;
    nonce: string;
  }>(`${registrar}/reveal`, { token: tokens.admin, body: { session: opened.session } });

  // Audit every block: replay the tester's counts from its committed bytes and the beacon,
  // and check the trainer's sealed record against the hash it reported.
  const audits: { block: number; testerReplay: boolean; bytesHash: boolean; trainerTarget: boolean; trainerHash: boolean }[] = [];
  for (let block = 0; block < protocol.blocks; block++) {
    const b = revealed.blocks[block];
    const tester = await call<{ bytes: string }>(`http://127.0.0.1:${ports.tester}/audit/${block}`);
    const raw = Buffer.from(tester.bytes, "base64");
    const replay = testBlock(raw, b.commit.beacon, protocol.tester, protocol.forms);
    const trainer = await call<Record<string, unknown>>(`http://127.0.0.1:${ports.trainer}/audit/${block}`);
    audits.push({
      block,
      testerReplay: canonical(replay) === canonical(b.tested.counts),
      bytesHash: sha256hex(raw) === b.commit.bytesHash,
      trainerTarget: trainer.target === revealed.assignment[block],
      trainerHash: sha256hex(canonical(trainer)) === b.trained.trainingHash,
    });
  }
  const chain = ChainLog.verify(join(dirs.registrar, "log.jsonl"));
  const occurrences = revealed.blocks.reduce((s, b) => s + b.trained.occurrences, 0);
  const overran = revealed.blocks.filter((b) => b.trained.overran).length;

  const gitHead = (() => {
    try {
      return execSync("git rev-parse HEAD", { cwd: here }).toString().trim();
    } catch {
      return "unknown";
    }
  })();
  const separateUsers = ROLES.every((role) => who[role] !== null);
  const out = {
    label: protocol.label,
    positiveControl: protocol.leak.relative > 0,
    leakRelative: protocol.leak.relative,
    protocolFile: protocolPath,
    protocolFileSha256: sha256hex(protocolText),
    protocolHash: revealed.protocolHash,
    codeHash: revealed.codeHash,
    commitment: revealed.commitment,
    nonce: revealed.nonce,
    logHead: revealed.logHead,
    logChainValid: chain.ok,
    logEntries: chain.entries,
    gitHead,
    environment: {
      topology: separateUsers
        ? "three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only"
        : "three processes on one host as one user; separate data dirs and secrets; HTTP only",
      entropy: "node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon",
      node: process.version,
      platform: `${platform()} ${release()}`,
      cpu: cpus()[0]?.model ?? "unknown",
    },
    seconds: Math.round((Date.now() - t0) / 1000),
    trainingOccurrences: occurrences,
    blocksOverran: overran,
    audits,
    report: revealed.report,
    assignment: revealed.assignment,
    blocks: revealed.blocks,
  };
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
  audits: { testerReplay: boolean; bytesHash: boolean; trainerTarget: boolean; trainerHash: boolean }[];
  logChainValid: boolean;
  blocksOverran: number;
  [k: string]: unknown;
}): string {
  const r = o.report;
  const allAudits = o.audits.every((a) => a.testerReplay && a.bytesHash && a.trainerTarget && a.trainerHash);
  const ci = `95% CI ${pct(r.t1.ci[0])} to ${pct(r.t1.ci[1])}`;
  const ciNote =
    !o.positiveControl && !r.detected && r.t1.ci[1] < 0
      ? " The interval lies below zero: the trained form was, if anything, under-represented. That is the wrong direction for the hypothesis and was not pre-registered; read two-sided it is the kind of result chance gives a few times in a hundred."
      : "";
  const verdict = o.positiveControl
    ? r.detected
      ? `Positive control: the deliberate +${(o.leakRelative * 100).toFixed(1)}% channel was detected (Holm p = ${r.holm.t1.toPrecision(3)}). The rig can see an effect of this size.`
      : `Positive control FAILED: the deliberate +${(o.leakRelative * 100).toFixed(1)}% channel was not detected (Holm p = ${r.holm.t1.toPrecision(3)}). The rig is not sensitive enough at this size.`
    : r.detected
      ? `Anomaly: trained forms were over-represented in the isolated tester (effect ${pct(r.t1.effect)}, ${ci}, Holm p = ${r.holm.t1.toPrecision(3)}). Not a claim yet: it needs replication on physically separate machines with independent entropy.`
      : `No effect detected. Estimated effect ${pct(r.t1.effect)} (${ci}), Holm p = ${r.holm.t1.toPrecision(3)}. An effect of ${pct(r.t1.mde80)} or more would have been detected with about 80% power under the Holm decision.${ciNote}`;
  const rows = r.perForm
    .map((f) => `| ${f.form} | ${f.timesTrained} | ${f.trained.toFixed(1)} | ${f.untrained.toFixed(1)} | ${((f.ratio - 1) * 100).toFixed(2)}% |`)
    .join("\n");
  return `# Rig report: ${o.label}${o.positiveControl ? " (POSITIVE CONTROL: deliberate channel)" : ""}

${verdict}

| | |
|---|---|
| Primary T1 (block-locked) | effect ${pct(r.t1.effect)}, ${ci}, p ${r.t1.p.toPrecision(3)}, Holm ${r.holm.t1.toPrecision(3)} |
| Secondary T2 (cumulative dose) | mean correlation ${r.t2.stat.toFixed(4)}, p ${r.t2.p.toPrecision(3)}, Holm ${r.holm.t2.toPrecision(3)} |
| Null 95th percentile / 80%-power MDE (Holm) | ${pct(r.t1.nullQ95)} / ${pct(r.t1.mde80)} |
| Blocks · α | ${r.blocks} · ${r.alpha} |
| Training occurrences | ${o.trainingOccurrences} |
| Blocks that overran the fixed training time | ${o.blocksOverran} |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | ${allAudits ? "all passed" : "FAILED"} on all ${o.audits.length} blocks |
| Log chain | ${o.logChainValid ? "valid" : "BROKEN"}, head ${String(o.logHead).slice(0, 16)}… |
| Commitment | ${String(o.commitment).slice(0, 16)}… (verified at reveal) |
| Protocol / code hash | ${String(o.protocolHash).slice(0, 16)}… / ${String(o.codeHash).slice(0, 16)}… (code re-hashed at reveal) |
| Code | ${String(o.gitHead).slice(0, 12)} |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
${rows}

Topology: ${(o.environment as { topology: string }).topology}. Entropy: ${(o.environment as { entropy: string }).entropy}.
`;
}
