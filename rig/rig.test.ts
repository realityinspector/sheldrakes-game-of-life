import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mulberry32 } from "../src/sim/protocol.ts";
import { analyze, type BlockCounts } from "./analysis.ts";
import { spawn, type ChildProcess } from "node:child_process";
import { fileURLToPath } from "node:url";
import {
  ChainLog,
  FORM_IDS,
  call,
  canonical,
  countForms,
  mixWithBeacon,
  sha256hex,
  sleep,
  stampLattice,
  testBlock,
  testSoup,
  token,
  validateProtocol,
  type Protocol,
} from "./common.ts";

const FORMS = ["block", "blinker", "beehive", "loaf", "boat"];
const RATES = [1650, 1950, 980, 355, 365];

function poisson(lambda: number, rng: () => number): number {
  // Normal approximation is fine at these sizes.
  const u = Math.max(1e-12, rng());
  const v = rng();
  return Math.max(0, Math.round(lambda + Math.sqrt(lambda) * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)));
}

function simulate(seed: number, blocks: number, effect: number): BlockCounts[] {
  const rng = mulberry32(seed);
  const order: string[] = [];
  for (let i = 0; i < blocks / FORMS.length; i++) order.push(...FORMS);
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  return order.map((target, block) => ({
    block,
    target,
    counts: Object.fromEntries(FORMS.map((f, k) => [f, poisson(RATES[k] * (f === target ? 1 + effect : 1), rng)])),
  }));
}

describe("rig analysis", () => {
  it("holds its false-positive rate under the null", () => {
    let hits = 0;
    const runs = 300;
    for (let s = 1; s <= runs; s++) {
      if (analyze(FORMS, simulate(s, 30, 0), { permutations: 400, bootstrap: 50, alpha: 0.05, seed: s }).t1.p < 0.05) hits++;
    }
    // Binomial(300, 0.05): mean 15, sd 3.8.
    assert.ok(hits >= 4 && hits <= 27, `false positives ${hits}/300`);
  });

  it("detects a real block-locked effect and estimates its size", () => {
    const r = analyze(FORMS, simulate(7, 60, 0.05), { permutations: 2000, bootstrap: 500, alpha: 0.05, seed: 7 });
    assert.ok(r.detected);
    assert.ok(r.t1.effect > 0.03 && r.t1.effect < 0.07, `effect ${r.t1.effect}`);
    assert.ok(r.t1.ci[0] < 0.05 && r.t1.ci[1] > 0.05);
    assert.ok(r.t1.mde80 > 0 && r.t1.mde80 < 0.05);
  });

  it("applies Holm across the two hypotheses", () => {
    const r = analyze(FORMS, simulate(3, 30, 0), { permutations: 500, bootstrap: 50, alpha: 0.05, seed: 3 });
    const [lo, hi] = [Math.min(r.t1.p, r.t2.p), Math.max(r.t1.p, r.t2.p)];
    const adjLo = Math.min(1, 2 * lo);
    assert.equal(Math.min(r.holm.t1, r.holm.t2), adjLo);
    assert.equal(Math.max(r.holm.t1, r.holm.t2), Math.min(1, Math.max(adjLo, hi)));
  });

  it("is deterministic for a seed", () => {
    const data = simulate(11, 20, 0.02);
    const opts = { permutations: 300, bootstrap: 100, alpha: 0.05, seed: 99 };
    assert.deepEqual(analyze(FORMS, data, opts), analyze(FORMS, data, opts));
  });
});

describe("rig mechanics", () => {
  it("a hash-chained log detects any edit", () => {
    const file = join(mkdtempSync(join(tmpdir(), "rig-")), "log.jsonl");
    const log = new ChainLog(file);
    log.append("commit", { a: 1 });
    log.append("tested", { b: 2 });
    assert.equal(ChainLog.verify(file).ok, true);
    writeFileSync(file, readFileSync(file, "utf8").replace('"b":2', '"b":3'));
    assert.equal(ChainLog.verify(file).ok, false);
  });

  it("the tester's computation replays exactly from its bytes", () => {
    const bytes = new Uint8Array(128).map((_, i) => (i * 73 + 41) & 255);
    const spec = { soups: 1, size: 32, generations: 120 };
    assert.equal(canonical(testSoup(bytes, spec, FORMS)), canonical(testSoup(bytes, spec, FORMS)));
  });

  it("the trainer's lattice really holds the target form", () => {
    for (const form of FORMS) {
      const grid = stampLattice(form, 64, 8);
      assert.equal(countForms(grid, 64, [form])[form], 64, form);
      assert.ok(FORM_IDS[form] > 0);
    }
  });

  it("rejects unbalanced or leaky-by-mistake protocols", () => {
    const base: Protocol = JSON.parse(readFileSync(new URL("./protocols/isolation-2.json", import.meta.url), "utf8"));
    assert.equal(validateProtocol(base), null);
    assert.equal(base.leak.relative, 0, "the confirmatory protocol must not leak");
    assert.notEqual(validateProtocol({ ...base, blocks: base.blocks + 1 }), null);
    assert.notEqual(validateProtocol({ ...base, forms: ["block", "block"] }), null);
  });
});

describe("beacon", () => {
  it("changes the soups, and replays exactly", () => {
    const raw = new Uint8Array(128 * 3).map((_, i) => (i * 37 + 11) & 255);
    const spec = { soups: 3, size: 32, generations: 60 };
    const a = testBlock(raw, "aa", spec, FORMS);
    assert.deepEqual(testBlock(raw, "aa", spec, FORMS), a);
    assert.notDeepEqual(mixWithBeacon(raw.subarray(0, 128), "aa", 0), mixWithBeacon(raw.subarray(0, 128), "bb", 0));
    assert.notDeepEqual(mixWithBeacon(raw.subarray(0, 128), "aa", 0), mixWithBeacon(raw.subarray(0, 128), "aa", 1));
  });
});

describe("registrar channels", () => {
  it("withholds the log head, enforces order, and gives the tester nothing but go and a beacon", async () => {
    const here = fileURLToPath(new URL(".", import.meta.url));
    const tokens = { admin: token(), trainer: token(), tester: token() };
    const port = 30000 + Math.floor(Math.random() * 20000);
    const url = `http://127.0.0.1:${port}`;
    const child: ChildProcess = spawn(process.execPath, ["--experimental-strip-types", "--no-warnings", join(here, "registrar.ts")], {
      env: {
        PATH: process.env.PATH ?? "",
        PORT: String(port),
        RIG_DATA_DIR: mkdtempSync(join(tmpdir(), "rig-reg-")),
        RIG_ROOT: join(here, ".."),
        RIG_ADMIN_TOKEN: tokens.admin,
        RIG_TRAINER_TOKEN: tokens.trainer,
        RIG_TESTER_TOKEN: tokens.tester,
      },
      stdio: "ignore",
    });
    try {
      for (let i = 0; i < 100; i++) {
        try {
          await call(`${url}/health`);
          break;
        } catch {
          await sleep(50);
        }
      }
      const protocol: Protocol = JSON.parse(readFileSync(new URL("./protocols/smoke.json", import.meta.url), "utf8"));
      const opened = await call<{ session: string }>(`${url}/session`, { token: tokens.admin, body: { protocol } });
      const q = `?session=${opened.session}`;
      const status = await call<Record<string, unknown>>(`${url}/status${q}`);
      assert.equal(status.log, undefined, "no log head before the reveal");
      await assert.rejects(call(`${url}/trainer/next${q}`, { token: tokens.tester }), /403/);
      await assert.rejects(
        call(`${url}/trainer/done`, { token: tokens.trainer, body: { session: opened.session, block: 0, occurrences: 1, trainingHash: "0".repeat(64) } }),
        /not handed out/,
      );
      const next = await call<{ block: number; target: string }>(`${url}/trainer/next${q}`, { token: tokens.trainer });
      assert.equal(next.block, 0);
      await assert.rejects(
        call(`${url}/trainer/done`, { token: tokens.trainer, body: { session: opened.session, block: 1, occurrences: 1, trainingHash: "0".repeat(64) } }),
        /not handed out/,
      );
      await call(`${url}/trainer/done`, { token: tokens.trainer, body: { session: opened.session, block: 0, occurrences: 5, trainingHash: sha256hex("x") } });
      const go = await call<Record<string, unknown>>(`${url}/tester/next${q}`, { token: tokens.tester });
      assert.equal(go.block, 0);
      // "go" is the block, the spec, and every candidate form in protocol order: nothing that varies with the target.
      assert.deepEqual(Object.keys(go).sort(), ["block", "forms", "spec"]);
      assert.deepEqual(go.forms, protocol.forms);
      const counts = Object.fromEntries(protocol.forms.map((f) => [f, 1]));
      await assert.rejects(
        call(`${url}/tester/result`, { token: tokens.tester, body: { session: opened.session, block: 0, counts } }),
        /committed/,
      );
      const { beacon } = await call<{ beacon: string }>(`${url}/tester/commit`, {
        token: tokens.tester,
        body: { session: opened.session, block: 0, bytesHash: sha256hex("bytes") },
      });
      assert.match(beacon, /^[0-9a-f]{64}$/);
      await assert.rejects(
        call(`${url}/tester/commit`, { token: tokens.tester, body: { session: opened.session, block: 0, bytesHash: sha256hex("other") } }),
        /already committed/,
      );
      await call(`${url}/tester/result`, { token: tokens.tester, body: { session: opened.session, block: 0, counts } });
      await assert.rejects(call(`${url}/reveal`, { token: tokens.tester, body: { session: opened.session } }), /403/);
    } finally {
      child.kill();
    }
  });
});
