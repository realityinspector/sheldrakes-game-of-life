/**
 * Tester: pure Conway, no field, no table, no knowledge of the target. For each block
 * it draws fresh soups from OS entropy (crypto.randomBytes, one bit per cell), runs
 * them, and counts every candidate form. It keeps the raw bytes so anyone can replay
 * its counts exactly (GET /audit/<block>).
 *
 * The only way it is ever told the target is a declared positive-control protocol
 * (leak.relative > 0), where it deliberately inflates that count by a known fraction.
 *
 * Env: PORT, RIG_DATA_DIR, RIG_REGISTRAR_URL, RIG_TESTER_TOKEN, RIG_SESSION.
 */
import { randomBytes } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { call, env, serve, sha256hex, sleep, testSoup, type TesterSpec } from "./common.ts";

const registrar = env("RIG_REGISTRAR_URL");
const tokenValue = env("RIG_TESTER_TOKEN");
const sessionId = env("RIG_SESSION");
const dataDir = env("RIG_DATA_DIR");
mkdirSync(dataDir, { recursive: true });

const server = await serve(
  {
    "GET /health": async () => ({ json: { ok: true } }),
    "GET /audit/*": async (req) => {
      const block = Number(new URL(req.url ?? "/", "http://x").pathname.split("/").pop());
      const file = join(dataDir, `block-${block}.bin`);
      if (!existsSync(file)) return { status: 404, json: { error: "no such block" } };
      return { json: { block, bytes: readFileSync(file).toString("base64") } };
    },
  },
  Number(env("PORT")),
  process.env.RIG_HOST ?? "127.0.0.1",
);
console.log(`tester listening on ${env("PORT")}`);

type Go = {
  done?: boolean;
  wait?: boolean;
  block?: number;
  spec?: TesterSpec;
  forms?: string[];
  leak?: { target: string; relative: number };
};

for (;;) {
  const go = await call<Go>(`${registrar}/tester/next?session=${sessionId}`, { token: tokenValue });
  if (go.done) break;
  if (go.wait || go.block === undefined || !go.spec || !go.forms) {
    await sleep(25);
    continue;
  }
  const { spec, forms } = go;
  const perSoup = (spec.size * spec.size) / 8;
  const all = Buffer.alloc(perSoup * spec.soups);
  const counts: Record<string, number> = Object.fromEntries(forms.map((f) => [f, 0]));
  for (let i = 0; i < spec.soups; i++) {
    const bytes = randomBytes(perSoup);
    bytes.copy(all, i * perSoup);
    const c = testSoup(bytes, spec, forms);
    for (const f of forms) counts[f] += c[f];
  }
  let leakExtra = 0;
  if (go.leak) {
    // Positive control: each counted target object is duplicated with probability `relative`.
    const draws = randomBytes(4 * counts[go.leak.target]);
    for (let k = 0; k < counts[go.leak.target]; k++) if (draws.readUInt32LE(4 * k) / 2 ** 32 < go.leak.relative) leakExtra++;
  }
  writeFileSync(join(dataDir, `block-${go.block}.bin`), all);
  await call(`${registrar}/tester/result`, {
    token: tokenValue,
    body: { session: sessionId, block: go.block, counts, leakExtra, entropyHash: sha256hex(all) },
  });
}

for (let i = 0; i < 2400; i++) {
  const status = await call<{ revealed: boolean }>(`${registrar}/status?session=${sessionId}`).catch(() => ({ revealed: true }));
  if (status.revealed) break;
  await sleep(250);
}
await sleep(Number(process.env.RIG_LINGER_MS ?? 0));
server.close();
