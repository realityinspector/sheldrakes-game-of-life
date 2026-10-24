import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_CONFIG, type FieldConfig } from "./engine.ts";
import { ALPHA, alphaForAttempt, sha256 } from "./protocol.ts";
import { SweepRunner, ladderSeed, makeConfirmResult, megaLattice } from "./sweep.ts";

const small: FieldConfig = {
  ...DEFAULT_CONFIG,
  cells: 16,
  fieldStrength: 0.84,
  similarityThreshold: 0.52,
  coupling: 0,
  innate: true,
};

function confirmRunner(seeds: number) {
  const runner = new SweepRunner();
  runner.setPlan({
    mode: "confirm",
    goal: "gap",
    generations: 40,
    granularity: 25,
    seedCount: seeds,
    axes: [],
    sweepSize: false,
    sweepInnate: false,
    ignoreArchive: true,
    preset: "garden",
    baseline: small,
    archive: [],
    seed: 1,
  });
  runner.start();
  for (let guard = 0; runner.status === "running" && guard < 100000; guard++) runner.tick(1000);
  return runner;
}

describe("confirmatory batch", () => {
  it("runs every planned seed and replays to the same scores from the same first row", () => {
    const a = confirmRunner(6);
    const b = confirmRunner(6);
    assert.equal(a.status, "done");
    assert.ok(a.confirm);
    assert.equal(a.confirm.seeds, 6);
    assert.equal(a.confirm.alpha, ALPHA);
    assert.equal(a.confirm.row, b.confirm?.row);
    assert.deepEqual(
      a.cards.map((c) => [c.seed, c.specField, c.specYoked, c.specScrambled]),
      b.cards.map((c) => [c.seed, c.specField, c.specYoked, c.specScrambled]),
    );
    assert.equal(new Set(a.cards.map((c) => c.seed)).size, 6);
  });

  it("is not voided by pressing Stop after it finished", () => {
    const runner = confirmRunner(4);
    const before = runner.confirm;
    runner.stop();
    assert.equal(runner.status, "done");
    assert.equal(runner.confirm, before);
    assert.equal(runner.confirm?.voided, false);
  });

  it("is void when stopped early", () => {
    const runner = new SweepRunner();
    runner.setPlan({
      mode: "confirm",
      goal: "gap",
      generations: 40,
      granularity: 25,
      seedCount: 8,
      axes: [],
      sweepSize: false,
      sweepInnate: false,
      ignoreArchive: true,
      preset: "garden",
      baseline: small,
      archive: [],
      seed: 1,
    });
    runner.start();
    runner.tick(100);
    runner.stop();
    assert.equal(runner.confirm?.voided, true);
    assert.equal(runner.confirm?.specific, false);
  });
});

describe("sealing", () => {
  const row = sha256("seal");
  const split = (pos: number, neg: number) => [...Array(pos).fill(0.1), ...Array(neg).fill(-0.1)];

  it("needs both nulls, every seed, and the field's direction", () => {
    const strong = split(64, 0);
    assert.equal(makeConfirmResult(row, strong, strong, 64, false, "").specific, true);
    assert.equal(makeConfirmResult(row, strong, split(32, 32), 64, false, "").specific, false);
    assert.equal(makeConfirmResult(row, split(0, 64), strong, 64, false, "").specific, false);
    assert.equal(
      makeConfirmResult(row, strong.slice(1), strong.slice(1), 64, false, "").specific,
      false,
    );
    assert.equal(makeConfirmResult(row, strong, strong, 64, true, "").specific, false);
  });

  it("applies the spent α, not a flat 0.05", () => {
    // 42 of 64: two-sided p ≈ 0.016 — passes the first attempt's α ≈ 0.030, not the fifth's ≈ 0.0012.
    const diffs = split(42, 22);
    assert.equal(
      makeConfirmResult(row, diffs, diffs, 64, false, "", alphaForAttempt(1)).specific,
      true,
    );
    assert.equal(
      makeConfirmResult(row, diffs, diffs, 64, false, "", alphaForAttempt(5)).specific,
      false,
    );
  });
});

describe("dose seeds", () => {
  it("keep training and test seeds apart, and reuse the test seeds at every dose", () => {
    const row = sha256("dose");
    const doses = [0, 1, 10, 100];
    const train = new Set<number>();
    const tests: number[][] = [];
    doses.forEach((dose, cursor) => {
      for (let index = 0; index < dose; index++) {
        train.add(
          ladderSeed({ mode: "dose", phase: "train", row, doses, doseCursor: cursor, index }),
        );
      }
      tests.push(
        Array.from({ length: 16 }, (_, index) =>
          ladderSeed({ mode: "dose", phase: "test", row, doses, doseCursor: cursor, index }),
        ),
      );
    });
    assert.equal(train.size, 111);
    for (const list of tests) {
      assert.deepEqual(list, tests[0]);
      for (const seed of list) assert.ok(!train.has(seed));
    }
  });
});

describe("mega ladder", () => {
  it("walks the dose stage on the confirm targets and leaves the curve sealed", () => {
    const runner = new SweepRunner();
    runner.setPlan({
      mode: "seek",
      goal: "gap",
      generations: 80,
      granularity: 25,
      seedCount: 16,
      axes: [],
      sweepSize: false,
      sweepInnate: false,
      ignoreArchive: true,
      preset: "garden",
      baseline: small,
      archive: [],
      seed: 1,
    });
    runner.startMega();
    const r = runner as any;
    const frozen = { ...small, wrap: false, coupling: 0.5 };
    const targets = [7, 99];
    // Stand in a sealed, Specific confirm + naive pair so the ladder opens the dose stage.
    r.mega.proof = { specific: true, learnedReason: "" };
    r.mega.naive = { specific: true };
    r.ladder = {
      mode: "naive",
      config: { ...frozen, innate: false, coupling: 0 },
      source: frozen,
      preset: "garden",
      row: sha256("naive"),
      targets,
      alpha: alphaForAttempt(3),
      index: 64,
      total: 64,
      diffsY: [],
      diffsS: [],
      specSum: 0,
      gapSum: 0,
      doseCursor: 0,
      doses: [0, 1, 10, 100],
      phase: "test",
      trainArchive: [],
      testCoupling: 0,
      couplingSubstituted: false,
      points: [],
    };
    r.openDose();
    assert.equal(r.ladder.mode, "dose");
    assert.equal(r.ladder.testCoupling, 0.5);
    assert.equal(r.ladder.alpha, alphaForAttempt(3));
    const runs: { phase: string; dose: number; seed: number }[] = [];
    let lastLab: unknown = null;
    for (let guard = 0; guard < 200000 && r.mega.stage === "dose"; guard++) {
      runner.tick(1);
      if (r.lab && r.lab !== lastLab) {
        lastLab = r.lab;
        assert.deepEqual(r.lab.targets(), targets);
        runs.push({
          phase: r.ladder.phase,
          dose: r.ladder.doses[r.ladder.doseCursor],
          seed: r.lab.seed,
        });
      }
    }
    assert.notEqual(r.mega.stage, "dose");
    assert.equal(r.mega.dose.points.length, 4);
    assert.equal(r.mega.dose.alpha, alphaForAttempt(3));
    assert.ok(r.mega.dose.trend);
    assert.equal(r.mega.dose.trend.n, 64);
    if (r.mega.dose.learned)
      assert.ok(r.mega.dose.trend.z > 0 && r.mega.dose.trend.p < alphaForAttempt(3));
    const train = runs.filter((run) => run.phase === "train");
    const test = runs.filter((run) => run.phase === "test");
    assert.equal(train.length, 111);
    assert.equal(test.length, 4 * 64);
    const trainSeeds = new Set(train.map((run) => run.seed));
    assert.ok(test.every((run) => !trainSeeds.has(run.seed)));
    const byDose = (dose: number) => test.filter((run) => run.dose === dose).map((run) => run.seed);
    for (const dose of [1, 10, 100]) assert.deepEqual(byDose(dose), byDose(0));
  });
});

describe("mega lattice", () => {
  it("does not walk coupling, which is inert with an empty archive", () => {
    const { dims } = megaLattice(25);
    assert.ok(!dims.some((dim) => dim.key === "coupling"));
  });
});

describe("mega screen", () => {
  it("screens a candidate on its own seeds before any α is spent", () => {
    const runner = new SweepRunner();
    runner.setPlan({
      mode: "seek",
      goal: "gap",
      generations: 80,
      granularity: 25,
      seedCount: 16,
      axes: [],
      sweepSize: false,
      sweepInnate: false,
      ignoreArchive: true,
      preset: "garden",
      baseline: small,
      archive: [],
      seed: 1,
    });
    runner.startMega();
    const r = runner as any;
    r.rememberCandidate({ ...small, wrap: false }, "garden", 0.5, "test recipe");
    const seeds: number[] = [];
    let last: unknown = null;
    for (let guard = 0; guard < 100000; guard++) {
      runner.tick(1);
      if (r.lab && r.lab !== last) {
        last = r.lab;
        if (r.ladder?.mode === "screen") seeds.push(r.lab.seed);
      }
      if (r.mega.screened > 0) break;
    }
    assert.equal(r.mega.screened, 1);
    assert.equal(seeds.length, 16);
    assert.equal(new Set(seeds).size, 16);
    const s = r.mega.lastScreen;
    assert.equal(s.passed, s.yoked >= 11 && s.scrambled >= 11);
    if (s.passed) {
      assert.equal(r.ladder.mode, "confirm");
      assert.equal(r.confirmAttempts, 1);
      // Screen seeds are never confirm seeds.
      for (let i = 0; i < 64; i++)
        assert.ok(!seeds.includes(ladderSeed({ ...r.ladder, index: i })));
    } else {
      assert.equal(r.confirmAttempts, 0, "a failed screen spends no α");
      assert.equal(r.mega.stage, "search");
    }
  });
});

describe("single-recipe ladder", () => {
  it("tests one frozen recipe at the full α and ends on the first miss or on Learned", () => {
    const runner = new SweepRunner();
    runner.setPlan({
      mode: "confirm",
      goal: "gap",
      generations: 80,
      granularity: 25,
      seedCount: 64,
      axes: [],
      sweepSize: false,
      sweepInnate: false,
      ignoreArchive: true,
      preset: "garden",
      baseline: small,
      archive: [],
      seed: 1,
    });
    runner.startLadder();
    const r = runner as any;
    assert.equal(runner.isSingleLadder, true);
    assert.equal(r.ladder.mode, "confirm");
    assert.equal(r.ladder.alpha, ALPHA);
    for (let guard = 0; guard < 2_000_000 && runner.status === "running"; guard++)
      runner.tick(4000);
    assert.equal(runner.status, "done");
    const m = r.mega;
    assert.equal(m.sealed.length, 1);
    assert.equal(m.sealed[0].alpha, ALPHA);
    assert.equal(m.screened, 0, "no screen in a single pre-registered ladder");
    if (!m.proof.specific) assert.equal(m.naive, null);
    if (m.dose?.trend) assert.equal(m.dose.alpha, ALPHA);
  });
});
