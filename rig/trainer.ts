/**
 * Trainer: asks the registrar for its target one block at a time and makes that form
 * occur many times (a lattice of non-interacting copies run under Conway). It never
 * talks to the tester. Its per-block records are served for audit only after the
 * registrar has revealed the session, so it cannot be used as a side channel.
 *
 * Env: PORT, RIG_DATA_DIR, RIG_REGISTRAR_URL, RIG_TRAINER_TOKEN, RIG_SESSION.
 */
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import {
  FORM_IDS,
  call,
  canonical,
  env,
  lifeStep,
  serve,
  sha256hex,
  sleep,
  stampLattice,
  type TrainerSpec,
} from "./common.ts";
import { censusCounts } from "../src/sim/protocol.ts";

const registrar = env("RIG_REGISTRAR_URL");
const tokenValue = env("RIG_TRAINER_TOKEN");
const sessionId = env("RIG_SESSION");
const dataDir = env("RIG_DATA_DIR");
mkdirSync(dataDir, { recursive: true });

/** Occurrences = Σ over boards and census points of (copies of the target present) × censusEvery. */
function train(target: string, spec: TrainerSpec): { occurrences: number; perBoard: number[] } {
  const perBoard: number[] = [];
  for (let i = 0; i < spec.boards; i++) {
    let a: Uint8Array = stampLattice(target, spec.size, spec.spacing);
    let b: Uint8Array = new Uint8Array(a.length);
    let seen = 0;
    for (let g = 1; g <= spec.generations; g++) {
      lifeStep(a, b, spec.size, spec.size);
      const t = a;
      a = b;
      b = t;
      if (g % spec.censusEvery === 0) seen += (censusCounts(a, spec.size, spec.size, true).get(FORM_IDS[target]) ?? 0) * spec.censusEvery;
    }
    perBoard.push(seen);
  }
  return { occurrences: perBoard.reduce((s, v) => s + v, 0), perBoard };
}

const server = await serve(
  {
    "GET /health": async () => ({ json: { ok: true } }),
    "GET /audit/*": async (req) => {
      const url = new URL(req.url ?? "/", "http://x");
      const block = Number(url.pathname.split("/").pop());
      const status = await call<{ revealed: boolean }>(`${registrar}/status?session=${sessionId}`);
      if (!status.revealed) return { status: 403, json: { error: "sealed until the registrar reveals" } };
      const file = join(dataDir, `block-${block}.json`);
      if (!existsSync(file)) return { status: 404, json: { error: "no such block" } };
      return { json: JSON.parse(readFileSync(file, "utf8")) };
    },
  },
  Number(env("PORT")),
  process.env.RIG_HOST ?? "127.0.0.1",
);
console.log(`trainer listening on ${env("PORT")}`);

for (;;) {
  const next = await call<{ done?: boolean; wait?: boolean; block?: number; target?: string; spec?: TrainerSpec }>(
    `${registrar}/trainer/next?session=${sessionId}`,
    { token: tokenValue },
  );
  if (next.done) break;
  if (next.wait || next.block === undefined || !next.target || !next.spec) {
    await sleep(25);
    continue;
  }
  const started = new Date().toISOString();
  const result = train(next.target, next.spec);
  const record = { block: next.block, target: next.target, spec: next.spec, started, finished: new Date().toISOString(), ...result };
  writeFileSync(join(dataDir, `block-${next.block}.json`), JSON.stringify(record));
  await call(`${registrar}/trainer/done`, {
    token: tokenValue,
    body: { session: sessionId, block: next.block, occurrences: result.occurrences, trainingHash: sha256hex(canonical(record)) },
  });
}

// Stay up for audit until the registrar has revealed, then exit.
for (let i = 0; i < 2400; i++) {
  const status = await call<{ revealed: boolean }>(`${registrar}/status?session=${sessionId}`).catch(() => ({ revealed: true }));
  if (status.revealed) break;
  await sleep(250);
}
await sleep(Number(process.env.RIG_LINGER_MS ?? 0));
server.close();
