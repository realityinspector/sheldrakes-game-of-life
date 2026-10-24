/**
 * Registrar: the only server that knows the assignment. It
 *  - draws the balanced block order from OS entropy and publishes only its SHA-256
 *    commitment before anything runs,
 *  - tells the trainer its own target, one block at a time,
 *  - tells the tester only "go" (never the target, unless the protocol is a declared
 *    positive control with a leak),
 *  - keeps strict order: train b, then test b, then train b + 1,
 *  - writes every event to a hash-chained log, and
 *  - reveals and scores only when every block is in.
 *
 * Env: PORT, RIG_DATA_DIR, RIG_ADMIN_TOKEN, RIG_TRAINER_TOKEN, RIG_TESTER_TOKEN.
 */
import { randomBytes, randomInt } from "node:crypto";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { analyze, type Report } from "./analysis.ts";
import {
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
  trained?: { occurrences: number; trainingHash: string; at: string };
  tested?: { counts: Record<string, number>; leakExtra: number; entropyHash: string; at: string };
};

type Session = {
  id: string;
  protocol: Protocol;
  protocolHash: string;
  analysisHash: string;
  assignment: string[];
  nonce: string;
  commitment: string;
  blocks: Block[];
  revealed?: { report: Report; at: string };
};

const dataDir = env("RIG_DATA_DIR");
mkdirSync(dataDir, { recursive: true });
const admin = env("RIG_ADMIN_TOKEN");
const trainerToken = env("RIG_TRAINER_TOKEN");
const testerToken = env("RIG_TESTER_TOKEN");
const log = new ChainLog(join(dataDir, "log.jsonl"));
const analysisSource = readFileSync(fileURLToPath(new URL("./analysis.ts", import.meta.url)));
const sessions = new Map<string, Session>();

function need(req: Parameters<typeof bearer>[0], expected: string) {
  if (!sameToken(bearer(req), expected)) throw Object.assign(new Error("forbidden"), { status: 403 });
}

function session(id: unknown): Session {
  const s = sessions.get(String(id));
  if (!s) throw new Error("no such session");
  return s;
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
    "GET /health": async () => ({ json: { ok: true, log: log.headHash } }),

    "POST /session": guarded((req, body: { protocol: Protocol }) => {
      need(req, admin);
      const protocol = body.protocol;
      const problem = validateProtocol(protocol);
      if (problem) throw new Error(problem);
      const assignment = drawAssignment(protocol.forms, protocol.blocks);
      const nonce = randomBytes(32).toString("hex");
      const s: Session = {
        id: randomBytes(8).toString("hex"),
        protocol,
        protocolHash: sha256hex(canonical(protocol)),
        analysisHash: sha256hex(analysisSource),
        assignment,
        nonce,
        commitment: sha256hex(canonical({ assignment, nonce })),
        blocks: protocol.blocks ? Array.from({ length: protocol.blocks }, () => ({})) : [],
      };
      sessions.set(s.id, s);
      log.append("commit", {
        session: s.id,
        protocolHash: s.protocolHash,
        analysisHash: s.analysisHash,
        commitment: s.commitment,
        leak: protocol.leak.relative,
        label: protocol.label,
      });
      return { session: s.id, protocolHash: s.protocolHash, analysisHash: s.analysisHash, commitment: s.commitment };
    }),

    "GET /status": guarded((_req, _body, url) => {
      const s = session(url.searchParams.get("session"));
      return {
        session: s.id,
        blocks: s.blocks.length,
        trained: s.blocks.filter((b) => b.trained).length,
        tested: s.blocks.filter((b) => b.tested).length,
        commitment: s.commitment,
        revealed: !!s.revealed,
        log: log.headHash,
      };
    }),

    "GET /trainer/next": guarded((req, _body, url) => {
      need(req, trainerToken);
      const s = session(url.searchParams.get("session"));
      const b = s.blocks.findIndex((x) => !x.trained);
      if (b < 0) return { done: true };
      // Strict alternation: block b trains only after block b - 1 has been tested.
      if (b > 0 && !s.blocks[b - 1].tested) return { wait: true };
      return { block: b, target: s.assignment[b], spec: s.protocol.trainer };
    }),

    "POST /trainer/done": guarded((req, body: { session: string; block: number; occurrences: number; trainingHash: string }) => {
      need(req, trainerToken);
      const s = session(body.session);
      const block = s.blocks[body.block];
      if (!block || block.trained) throw new Error("bad block");
      block.trained = { occurrences: body.occurrences, trainingHash: String(body.trainingHash), at: new Date().toISOString() };
      log.append("trained", { session: s.id, block: body.block, occurrences: body.occurrences, trainingHash: body.trainingHash });
      return { ok: true };
    }),

    "GET /tester/next": guarded((req, _body, url) => {
      need(req, testerToken);
      const s = session(url.searchParams.get("session"));
      const b = s.blocks.findIndex((x) => !x.tested);
      if (b < 0) return { done: true };
      if (!s.blocks[b].trained) return { wait: true };
      const go: Record<string, unknown> = { block: b, spec: s.protocol.tester, forms: s.protocol.forms };
      // Declared positive control only: a deliberate channel of known size.
      if (s.protocol.leak.relative > 0) go.leak = { target: s.assignment[b], relative: s.protocol.leak.relative };
      return go;
    }),

    "POST /tester/result": guarded(
      (req, body: { session: string; block: number; counts: Record<string, number>; leakExtra: number; entropyHash: string }) => {
        need(req, testerToken);
        const s = session(body.session);
        const block = s.blocks[body.block];
        if (!block || !block.trained || block.tested) throw new Error("bad block");
        for (const f of s.protocol.forms) {
          if (!Number.isInteger(body.counts?.[f]) || body.counts[f] < 0) throw new Error(`bad count for ${f}`);
        }
        const leakExtra = s.protocol.leak.relative > 0 ? Math.max(0, Math.floor(body.leakExtra ?? 0)) : 0;
        block.tested = { counts: body.counts, leakExtra, entropyHash: String(body.entropyHash), at: new Date().toISOString() };
        log.append("tested", { session: s.id, block: body.block, counts: body.counts, leakExtra, entropyHash: body.entropyHash });
        return { ok: true };
      },
    ),

    "POST /reveal": guarded((req, body: { session: string }) => {
      need(req, admin);
      const s = session(body.session);
      if (s.revealed) return reportFor(s);
      if (s.blocks.some((b) => !b.tested)) throw new Error("not every block has a result");
      if (sha256hex(canonical({ assignment: s.assignment, nonce: s.nonce })) !== s.commitment) {
        throw new Error("commitment does not match the assignment");
      }
      if (sha256hex(analysisSource) !== s.analysisHash) throw new Error("analysis code changed since the commitment");
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
      log.append("reveal", { session: s.id, assignment: s.assignment, nonce: s.nonce, t1: report.t1, t2: report.t2, holm: report.holm });
      writeFileSync(join(dataDir, `session-${s.id}.json`), JSON.stringify(reportFor(s), null, 2));
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
    analysisHash: s.analysisHash,
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
