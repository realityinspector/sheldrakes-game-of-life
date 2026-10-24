import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import {
  ALPHA,
  COMPARE_ROWS,
  COMPARISON_SHAPES,
  alphaForAttempt,
  bootstrapMedianCI,
  censusCounts,
  dStar,
  dice,
  mulberry32,
  normalizeMask,
  objectShape,
  orientations,
  rowsToMask,
  seedFromRow,
  sha256,
  shapeId,
  signTest,
  specificity,
} from "./protocol.ts";
import { INNATE_FORMS, catalogShapes } from "./engine.ts";

/** Plain bounded Conway step, independent of the engine. */
function lifeStep(g: Uint8Array, w: number, h: number, wrap = false): Uint8Array {
  const out = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      let n = 0;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue;
          let nx = x + dx;
          let ny = y + dy;
          if (wrap) {
            nx = (nx + w) % w;
            ny = (ny + h) % h;
          } else if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          n += g[ny * w + nx];
        }
      }
      out[y * w + x] = n === 3 || (g[y * w + x] === 1 && n === 2) ? 1 : 0;
    }
  }
  return out;
}

function stampRows(rows: string[], size: number, ox: number, oy: number): Uint8Array {
  const g = new Uint8Array(size * size);
  rows.forEach((row, y) => {
    [...row].forEach((ch, x) => {
      if (ch === "#" || ch === "O") g[((oy + y) % size) * size + ((ox + x) % size)] = 1;
    });
  });
  return g;
}

/** Live cells shifted to the origin, as a string: equal for translated copies only. */
function pinned(g: Uint8Array, w: number): string {
  const cells: [number, number][] = [];
  g.forEach((v, i) => {
    if (v) cells.push([i % w, (i / w) | 0]);
  });
  const mx = Math.min(...cells.map((c) => c[0]));
  const my = Math.min(...cells.map((c) => c[1]));
  return cells.map(([x, y]) => `${x - mx},${y - my}`).join(";");
}

/** True period of an isolated form (translation allowed, rotation not); 0 if none ≤ limit. */
function shapePeriod(rows: string[], limit = 8): number {
  const S = 24;
  let g = stampRows(rows, S, 9, 9);
  const start = pinned(g, S);
  for (let t = 1; t <= limit; t++) {
    g = lifeStep(g, S, S);
    if (pinned(g, S) === start) return t;
  }
  return 0;
}

describe("sha256", () => {
  it("matches node:crypto on ASCII, multi-byte and astral input", () => {
    for (const s of ["", "abc", "x".repeat(1000), "été", "αβγ", "🜁 morphic", JSON.stringify({ a: 1 })]) {
      assert.equal(sha256(s), createHash("sha256").update(s, "utf8").digest("hex"), s);
    }
  });
});

describe("seeds", () => {
  it("mulberry32 is deterministic and in [0, 1)", () => {
    const a = mulberry32(42);
    const b = mulberry32(42);
    for (let i = 0; i < 1000; i++) {
      const x = a();
      assert.equal(x, b());
      assert.ok(x >= 0 && x < 1);
    }
  });

  it("named seed streams never alias numeric ones", () => {
    const row = sha256("row");
    const numeric = new Set(Array.from({ length: 200 }, (_, i) => seedFromRow(row, i + 1)));
    for (let i = 0; i < 200; i++) assert.ok(!numeric.has(seedFromRow(row, `test:${i + 1}`)));
    assert.equal(seedFromRow(row, 3), seedFromRow(row, 3));
  });
});

describe("dice", () => {
  it("counts live cells only", () => {
    const block = rowsToMask(["##", "##"]);
    assert.equal(dice(0, 0), 0);
    assert.equal(dice(block, 0), 0);
    assert.equal(dice(block, block), 1);
    assert.equal(dice(0b11, 0b110), 0.5);
    assert.equal(dice(0b11, 0b110), dice(0b110, 0b11));
  });
});

describe("symmetry", () => {
  it("the eight orientations form a closed group", () => {
    const glider = rowsToMask(INNATE_FORMS[5].rows);
    const forms = new Set(orientations(glider));
    assert.equal(forms.size, 8);
    for (const form of forms) for (const again of orientations(form)) assert.ok(forms.has(again));
  });

  it("shapeId ignores translation, rotation and reflection", () => {
    for (const form of [...INNATE_FORMS, ...COMPARE_ROWS]) {
      const mask = rowsToMask(form.rows);
      const id = shapeId(mask);
      assert.equal(id, normalizeMask(id), form.name);
      for (const o of orientations(mask)) assert.equal(shapeId(o), id, form.name);
      assert.equal(shapeId(normalizeMask(mask)), id, form.name);
    }
  });

  it("names every catalog and comparison form distinctly", () => {
    const ids = [...INNATE_FORMS, ...COMPARE_ROWS].map((form) => shapeId(rowsToMask(form.rows)));
    assert.equal(new Set(ids).size, ids.length);
    for (const id of COMPARISON_SHAPES) assert.ok(!catalogShapes(8).includes(id));
  });

  it("objectShape picks the central object out of a cluttered patch", () => {
    const blinkerPlusFragment = rowsToMask(["....#", ".....", ".###.", ".....", "....."]);
    assert.equal(objectShape(blinkerPlusFragment), shapeId(rowsToMask(["###"])));
  });
});

describe("forms", () => {
  const expected: Record<string, number> = {
    Block: 1,
    Blinker: 2,
    Tub: 1,
    Boat: 1,
    Beehive: 1,
    Glider: 4,
    Toad: 2,
    Beacon: 2,
  };
  for (const form of INNATE_FORMS) {
    it(`innate ${form.name} has period ${expected[form.name]}`, () => {
      assert.equal(shapePeriod(form.rows), expected[form.name]);
    });
  }
  for (const form of COMPARE_ROWS) {
    it(`comparison ${form.name} is a still life`, () => {
      assert.equal(shapePeriod(form.rows), 1);
    });
  }
});

describe("census", () => {
  it("keys an object by shape wherever and however it sits", () => {
    const boat = ["##.", "#.#", ".#."];
    const keys = new Set<number>();
    for (const rows of [boat, [".##", "#.#", ".#."], [".#.", "#.#", "##."], [".#.", "#.#", ".##"]]) {
      for (const [ox, oy] of [
        [2, 2],
        [11, 5],
      ]) {
        const counts = censusCounts(stampRows(rows, 20, ox, oy), 20, 20);
        assert.equal(counts.size, 1);
        keys.add([...counts.keys()][0]);
      }
    }
    assert.deepEqual([...keys], [shapeId(rowsToMask(boat))]);
  });

  it("uses the same identity as the trained targets", () => {
    const targets = catalogShapes(8);
    INNATE_FORMS.forEach((form, i) => {
      const counts = censusCounts(stampRows(form.rows, 20, 6, 6), 20, 20);
      assert.equal(counts.get(targets[i]), 1, form.name);
    });
  });

  it("counts an object straddling the torus seam once, whole", () => {
    const beehive = [".##.", "#..#", ".##."];
    const g = stampRows(beehive, 16, 14, 15);
    assert.deepEqual([...censusCounts(g, 16, 16, true).entries()], [[shapeId(rowsToMask(beehive)), 1]]);
    assert.notDeepEqual([...censusCounts(g, 16, 16, false).keys()], [shapeId(rowsToMask(beehive))]);
  });

  it("rejects objects bigger than the 5×5 frame, and rings around the torus", () => {
    assert.equal(censusCounts(stampRows(["######"], 16, 2, 2), 16, 16).size, 0);
    assert.equal(censusCounts(stampRows(["#".repeat(16)], 16, 0, 3), 16, 16, true).size, 0);
  });

  it("specificity is facilitation of targets minus comparison", () => {
    const control = new Map([[7, 4]]);
    const board = new Map([[7, 9]]);
    const spec = specificity(board, control, [7], []);
    assert.ok(Math.abs(spec - Math.log(9.5 / 4.5)) < 1e-12);
    assert.equal(specificity(control, control, [7]), 0);
  });
});

describe("statistics", () => {
  it("sign test is exact and drops ties", () => {
    const close = (a: number, b: number) => assert.ok(Math.abs(a - b) < 1e-12, `${a} vs ${b}`);
    close(signTest([1, 1, 1, 1, 1]).p, 2 / 32);
    close(signTest([1, 1, 1, 1, 1, 1, 0, 0]).p, 2 / 64);
    // n = 10, 8 positive: 2 · (1 + 10 + 45) / 1024
    close(signTest([1, 1, 1, 1, 1, 1, 1, 1, -1, -1]).p, (2 * 56) / 1024);
    const t = signTest([1, 2, -1, 0, 0]);
    assert.equal(t.n, 3);
    assert.equal(t.pos, 2);
    assert.equal(t.neg, 1);
    assert.equal(t.p, 1);
    assert.deepEqual(signTest([]), { n: 0, pos: 0, neg: 0, p: 1, median: 0 });
    assert.equal(signTest([3, -3, 2]).p, signTest([-3, 3, -2]).p);
  });

  it("matches the power figures quoted on the method page", () => {
    const pmf = (n: number, k: number, p: number) => {
      let lc = 0;
      for (let i = 1; i <= k; i++) lc += Math.log(n - k + i) - Math.log(i);
      return Math.exp(lc + k * Math.log(p) + (n - k) * Math.log(1 - p));
    };
    const power = (n: number, p1: number, alpha: number) => {
      let total = 0;
      for (let k = 0; k <= n; k++) {
        const t = signTest([...Array(k).fill(1), ...Array(n - k).fill(-1)]);
        if (t.p < alpha && t.pos > t.neg) total += pmf(n, k, p1);
      }
      return total;
    };
    assert.equal(power(64, 0.7, 0.05).toFixed(2), "0.88");
    assert.equal(power(64, 0.65, 0.05).toFixed(2), "0.62");
  });

  it("α-spending is decreasing and never sums past ALPHA", () => {
    let sum = 0;
    for (let k = 1; k <= 100000; k++) {
      const a = alphaForAttempt(k);
      if (k > 1) assert.ok(a < alphaForAttempt(k - 1));
      sum += a;
    }
    assert.ok(sum < ALPHA);
    assert.ok(sum > ALPHA * 0.9999);
  });

  it("bootstrap interval brackets the median", () => {
    const diffs = Array.from({ length: 40 }, (_, i) => Math.sin(i) + 0.3);
    const { lo, hi } = bootstrapMedianCI(diffs, 400, 9);
    const m = signTest(diffs).median;
    assert.ok(lo <= m && m <= hi);
  });

  it("D* is 0 for identical boards and about 1 for unrelated ones", () => {
    assert.equal(dStar(0, 0.3, 0.3), 0);
    const rng = mulberry32(5);
    const n = 20000;
    let p = 0;
    let q = 0;
    let d = 0;
    for (let i = 0; i < n; i++) {
      const a = rng() < 0.3 ? 1 : 0;
      const b = rng() < 0.2 ? 1 : 0;
      p += a;
      q += b;
      if (a !== b) d++;
    }
    assert.ok(Math.abs(dStar(d / n, p / n, q / n) - 1) < 0.03);
  });
});
