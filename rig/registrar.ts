/**
 * Registrar: the only server that knows the assignment. It
 *  - draws the balanced block order from OS entropy and publishes only its SHA-256
 *    commitment before anything runs, together with a hash of the rig's code,
 *  - hands the trainer its own target one block at a time and accepts "done" only for
 *    that block,
 *  - gives the tester only "go", then a beacon after the tester has committed to its raw
 *    bytes (so a tester cannot grind its soups), and accepts a result only for that block,
 *  - keeps strict order: train b, then test b, then train b + 1,
 *  - writes every event to a hash-chained log that stays private until the reveal, and
 *  - reveals and scores only when every block is in, after checking that the code on disk
 *    still has the hash it had at commit.
 *
 * Nothing it serves before the reveal depends on the assignment except the commitment,
 * whose 256-bit nonce makes it unguessable.
 *
 * Env: PORT, RIG_DATA_DIR, RIG_ADMIN_TOKEN, RIG_TRAINER_TOKEN, RIG_TESTER_TOKEN, RIG_ROOT.
 */
import { randomBytes, randomInt } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { analyze, type Report } from "./analysis.ts";
import {
  CODE_FILES,
  ChainLog,
  bearer,
  canonical,
  env,
  serve,
  sameToken,
  sha256hex,
  validateProtocol,
  type Protocol,
} from "./common.ts";

type Block = {
  handedAt?: string;
  trained?: { occurrences: number; trainingHash: string; overran: boolean; at: string };
  commit?: { bytesHash: string; beacon: string; at: string };
  tested?: { counts: Record<string, number>; leakExtra: number; at: string };
};

type Session = {
  id: string;
  protocol: Protocol;
  protocolHash: string;
  codeHash: string;
  assignment: string[];
  nonce: string;
  commitment: string;
  blocks: Block[];
  revealed?: { report: Report; at: string };
};

const dataDir = env("RIG_DATA_DIR");
mkdirSync(dataDir, { recursive: true, mode: 0o700 });
const root = env("RIG_ROOT");
const admin = env("RIG_ADMIN_TOKEN");
const trainerToken = env("RIG_TRAINER_TOKEN");
const testerToken = env("RIG_TESTER_TOKEN");
const log = new ChainLog(join(dataDir, "log.jsonl"));
const sessions = new Map<string, Session>();

/** SHA-256 over the rig's code files as they are on disk now. */
function codeHash(): string {
  return sha256hex(CODE_FILES.map((f) => `${f}\n${sha256hex(readFileSync(join(root, f)))}`).join("\n"));
}

function fail(message: string, status = 400): never {
  throw Object.assign(new Error(message), { status });
}

function need(req: Parameters<typeof bearer>[0], expected: string) {
  if (!sameToken(bearer(req), expected)) fail("forbidden", 403);
}

function session(id: unknown): Session {
  return sessions.get(String(id)) ?? fail("no such session", 404);
}

/** Balanced order: each form exactly blocks / K times, shuffled with OS entropy. */
function drawAssignment(forms: string[], blocks: number): string[] {
  const order: string[] = [];
  for (let i = 0; i < blocks / forms.length; i++) order.push(...forms);
  for (let i = order.length - 1; i > 0; i--) {
    const j = randomInt(i + 1);
    [order[i], order[j]] = [order[j], order[i]];
  }
  return order;
}

/** The block the tester is working on: the first untested one. */
function currentTestBlock(s: Session): number {
  return s.blocks.findIndex((b) => !b.tested);
}

const guarded =
  (fn: (req: Parameters<typeof bearer>[0], body: any, url: URL) => unknown) =>
  async (req: Parameters<typeof bearer>[0], body: unknown) => {
    try {
      return { json: await fn(req, body, new URL(req.url ?? "/", "http://x")) };
    } catch (error) {
      const e = error as Error & { status?: number };
      return { status: e.status ?? 400, json: { error: e.message } };
    }
  };

await serve(
  {
    "GET /health": async () => ({ json: { ok: true } }),

    "POST /session": guarded((req, body: { protocol: Protocol }) => {
      need(req, admin);
      const protocol = body.protocol;
      const problem = validateProtocol(protocol);
      if (problem) fail(problem);
      const assignment = drawAssignment(protocol.forms, protocol.blocks);
      const nonce = randomBytes(32).toString("hex");
      const s: Session = {
        id: randomBytes(8).toString("hex"),
        protocol,
        protocolHash: sha256hex(canonical(protocol)),
        codeHash: codeHash(),
        assignment,
        nonce,
        commitment: sha256hex(canonical({ assignment, nonce })),
        blocks: Array.from({ length: protocol.blocks }, () => ({})),
      };
      sessions.set(s.id, s);
      log.append("commit", {
        session: s.id,
        protocolHash: s.protocolHash,
        codeHash: s.codeHash,
        commitment: s.commitment,
        leak: protocol.leak.relative,
        label: protocol.label,
      });
      return { session: s.id, protocolHash: s.protocolHash, codeHash: s.codeHash, commitment: s.commitment };
    }),

    // Public: progress and the commitment only. The log head is withheld until the reveal.
    "GET /status": guarded((_req, _body, url) => {
      const s = session(url.searchParams.get("session"));
      return {
        session: s.id,
        blocks: s.blocks.length,
        trained: s.blocks.filter((b) => b.trained).length,
        tested: s.blocks.filter((b) => b.tested).length,
        commitment: s.commitment,
        revealed: !!s.revealed,
        log: s.revealed ? log.headHash : undefined,
      };
    }),

    "GET /trainer/next": guarded((req, _body, url) => {
      need(req, trainerToken);
      const s = session(url.searchParams.get("session"));
      const b = s.blocks.findIndex((x) => !x.trained);
      if (b < 0) return { done: true };
      // Strict alternation: block b trains only after block b - 1 has been tested.
      if (b > 0 && !s.blocks[b - 1].tested) return { wait: true };
      s.blocks[b].handedAt ??= new Date().toISOString();
      return { block: b, target: s.assignment[b], spec: s.protocol.trainer };
    }),

    "POST /trainer/done": guarded(
      (req, body: { session: string; block: number; occurrences: number; trainingHash: string; overran: boolean }) => {
        need(req, trainerToken);
        const s = session(body.session);
        const b = s.blocks.findIndex((x) => !x.trained);
        if (body.block !== b || !s.blocks[b]?.handedAt) fail("that block was not handed out");
        if (!Number.isInteger(body.occurrences) || body.occurrences < 0) fail("bad occurrences");
        if (!/^[0-9a-f]{64}$/.test(String(body.trainingHash))) fail("bad training hash");
        s.blocks[b].trained = {
          occurrences: body.occurrences,
          trainingHash: body.trainingHash,
          overran: !!body.overran,
          at: new Date().toISOString(),
        };
        log.append("trained", {
          session: s.id,
          block: b,
          occurrences: body.occurrences,
          trainingHash: body.trainingHash,
          overran: !!body.overran,
        });
        return { ok: true };
      },
    ),

    "GET /tester/next": guarded((req, _body, url) => {
      need(req, testerToken);
      const s = session(url.searchParams.get("session"));
      const b = currentTestBlock(s);
      if (b < 0) return { done: true };
      if (!s.blocks[b].trained) return { wait: true };
      const go: Record<string, unknown> = { block: b, spec: s.protocol.tester, forms: s.protocol.forms };
      // Declared positive control only: a deliberate channel of known size.
      if (s.protocol.leak.relative > 0) go.leak = { target: s.assignment[b], relative: s.protocol.leak.relative };
      return go;
    }),

    "POST /tester/commit": guarded((req, body: { session: string; block: number; bytesHash: string }) => {
      need(req, testerToken);
      const s = session(body.session);
      const b = currentTestBlock(s);
      if (body.block !== b || !s.blocks[b]?.trained) fail("not the block under test");
      if (s.blocks[b].commit) fail("already committed");
      if (!/^[0-9a-f]{64}$/.test(String(body.bytesHash))) fail("bad bytes hash");
      const beacon = randomBytes(32).toString("hex");
      s.blocks[b].commit = { bytesHash: body.bytesHash, beacon, at: new Date().toISOString() };
      log.append("committed", { session: s.id, block: b, bytesHash: body.bytesHash, beacon });
      return { beacon };
    }),

    "POST /tester/result": guarded(
      (req, body: { session: string; block: number; counts: Record<string, number>; leakExtra: number }) => {
        need(req, testerToken);
        const s = session(body.session);
        const b = currentTestBlock(s);
        if (body.block !== b || !s.blocks[b]?.commit) fail("not the committed block under test");
        for (const f of s.protocol.forms) {
          if (!Number.isInteger(body.counts?.[f]) || body.counts[f] < 0) fail(`bad count for ${f}`);
        }
        const leakExtra = s.protocol.leak.relative > 0 ? Math.max(0, Math.floor(body.leakExtra ?? 0)) : 0;
        const counts = Object.fromEntries(s.protocol.forms.map((f) => [f, body.counts[f]]));
        s.blocks[b].tested = { counts, leakExtra, at: new Date().toISOString() };
        log.append("tested", { session: s.id, block: b, counts, leakExtra });
        return { ok: true };
      },
    ),

    "POST /reveal": guarded((req, body: { session: string }) => {
      need(req, admin);
      const s = session(body.session);
      if (s.revealed) return reportFor(s);
      if (s.blocks.some((b) => !b.tested)) fail("not every block has a result");
      if (sha256hex(canonical({ assignment: s.assignment, nonce: s.nonce })) !== s.commitment) {
        fail("commitment does not match the assignment");
      }
      if (codeHash() !== s.codeHash) fail("rig code on disk changed since the commitment");
      const rows = s.blocks.map((b, i) => {
        const counts = { ...b.tested!.counts };
        counts[s.assignment[i]] += b.tested!.leakExtra;
        return { block: i, target: s.assignment[i], counts };
      });
      const report = analyze(s.protocol.forms, rows, {
        permutations: s.protocol.analysis.permutations,
        bootstrap: s.protocol.analysis.bootstrap,
        alpha: s.protocol.analysis.alpha,
        seed: Number.parseInt(s.nonce.slice(0, 8), 16),
      });
      s.revealed = { report, at: new Date().toISOString() };
      log.append("reveal", {
        session: s.id,
        assignment: s.assignment,
        nonce: s.nonce,
        t1: report.t1,
        t2: report.t2,
        holm: report.holm,
      });
      writeFileSync(join(dataDir, `session-${s.id}.json`), JSON.stringify(reportFor(s), null, 2), { mode: 0o600 });
      return reportFor(s);
    }),
  },
  Number(env("PORT")),
  process.env.RIG_HOST ?? "127.0.0.1",
);

function reportFor(s: Session) {
  return {
    session: s.id,
    protocol: s.protocol,
    protocolHash: s.protocolHash,
    codeHash: s.codeHash,
    commitment: s.commitment,
    assignment: s.assignment,
    nonce: s.nonce,
    blocks: s.blocks,
    report: s.revealed?.report,
    revealedAt: s.revealed?.at,
    logHead: log.headHash,
  };
}

console.log(`registrar listening on ${env("PORT")}`);
