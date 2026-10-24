import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  DEFAULT_CONFIG,
  MorphicLab,
  catalogShapes,
  type FieldConfig,
  type PresetId,
} from "./engine.ts";
import { COMPARISON_SHAPES, WINDOW_GENS, censusCounts, eligible } from "./protocol.ts";

function lab(
  config: Partial<FieldConfig> = {},
  seed = 4242,
  preset: PresetId = "soup",
  cells = 32,
) {
  return new MorphicLab(cells, [], { ...DEFAULT_CONFIG, ...config, cells }, seed, preset);
}

function conway(src: Uint8Array, w: number, wrap: boolean): Uint8Array {
  const out = new Uint8Array(src.length);
  for (let y = 0; y < w; y++) {
    for (let x = 0; x < w; x++) {
      let n = 0;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue;
          let nx = x + dx;
          let ny = y + dy;
          if (wrap) {
            nx = (nx + w) % w;
            ny = (ny + w) % w;
          } else if (nx < 0 || ny < 0 || nx >= w || ny >= w) continue;
          n += src[ny * w + nx];
        }
      }
      out[y * w + x] = n === 3 || (src[y * w + x] === 1 && n === 2) ? 1 : 0;
    }
  }
  return out;
}

const count = (g: Uint8Array) => g.reduce((s, v) => s + v, 0);

describe("boards", () => {
  for (const preset of ["soup", "garden", "gun"] as PresetId[]) {
    it(`control is plain Conway (${preset})`, () => {
      const l = lab({}, 7, preset);
      const wrap = l.config.wrap;
      for (let t = 0; t < 60; t++) {
        const expected = conway(l.control, l.w, wrap);
        l.step();
        assert.deepEqual(l.control, expected, `generation ${t + 1}`);
      }
    });
  }

  it("with the field off, all four boards lock together", () => {
    const l = lab({ fieldStrength: 0 });
    for (let t = 0; t < 100; t++) l.step();
    assert.deepEqual(l.field, l.control);
    assert.deepEqual(l.yoked, l.control);
    assert.deepEqual(l.scrambled, l.control);
    assert.equal(l.snapshot().level, "off");
  });

  it("is deterministic for a seed", () => {
    const a = lab({}, 99);
    const b = lab({}, 99);
    for (let t = 0; t < 80; t++) {
      a.step();
      b.step();
    }
    assert.deepEqual(a.field, b.field);
    assert.deepEqual(a.yoked, b.yoked);
    assert.deepEqual(a.scrambled, b.scrambled);
    assert.deepEqual(a.snapshot(), b.snapshot());
  });

  it("Field never depends on the Scrambled board", () => {
    const plain = lab({}, 4242);
    const poked = lab({}, 4242);
    poked.brush = "paint";
    for (let k = 0; k < 40; k++) poked.paint("scrambled", (k * 7) % 32, (k * 11) % 32, false);
    for (let t = 0; t < 80; t++) {
      plain.step();
      poked.step();
    }
    assert.deepEqual(poked.field, plain.field);
    assert.deepEqual(poked.yoked, plain.yoked);
    assert.notDeepEqual(poked.scrambled, plain.scrambled);
  });

  for (const [preset, cells] of [
    ["soup", 32],
    ["rpen", 64],
    ["gliders", 64],
    ["pulsar", 64],
  ] as [PresetId, number][]) {
    it(`effective flips are exactly the cells that differ from Conway, and Yoked copies the count (${preset} ${cells}²)`, () => {
      const l = lab({ fieldStrength: 1, similarityThreshold: 0.5 }, 11, preset, cells);
      let flips = 0;
      for (let t = 0; t < 80; t++) {
        const conwayF = conway(l.field, l.w, l.config.wrap);
        const conwayY = conway(l.yoked, l.w, l.config.wrap);
        l.step();
        for (let i = 0; i < l.field.length; i++) {
          assert.equal(l.field[i] !== conwayF[i], l.influenced[i] === 1);
          assert.equal(l.yoked[i] !== conwayY[i], l.influencedY[i] === 1);
        }
        assert.equal(count(l.influencedY), count(l.influenced));
        flips += count(l.influenced);
      }
      assert.ok(flips > 0, "the field should write at this setting");
    });
  }

  it("consults each site at most once a generation", () => {
    // 16² soup repeats a candidate site in about a fifth of generations.
    const l = lab({ fieldStrength: 1, similarityThreshold: 0.5 }, 21, "soup", 16);
    const r = l as any;
    const w = l.w;
    const packAt = (g: Uint8Array, x: number, y: number) => {
      let mask = 0;
      let bit = 0;
      for (let dy = -2; dy <= 2; dy++) {
        for (let dx = -2; dx <= 2; dx++) {
          if (g[((y + dy + w) % w) * w + ((x + dx + w) % w)]) mask |= 1 << bit;
          bit++;
        }
      }
      return mask;
    };
    let repeats = 0;
    for (let t = 0; t < WINDOW_GENS; t++) {
      const before = l.field.slice();
      const consultedBefore = r.windowConsulted;
      l.step();
      const seen = new Set<number>();
      let expected = 0;
      for (let k = 0; k < r.candX.length && expected < l.samples; k++) {
        const site = r.candY[k] * w + r.candX[k];
        if (seen.has(site)) {
          repeats++;
          continue;
        }
        seen.add(site);
        if (eligible(packAt(before, r.candX[k], r.candY[k]))) expected++;
      }
      assert.equal(r.windowConsulted - consultedBefore, expected, `generation ${t + 1}`);
    }
    assert.ok(repeats > 0, "this board should repeat some candidate sites");
  });
});

describe("table", () => {
  it("an empty table learns echoes and can write", () => {
    const l = lab(
      { innate: false, coupling: 0, fieldStrength: 0.9, similarityThreshold: 0.5 },
      777,
    );
    assert.equal(l.crystals.length, 0);
    for (let t = 0; t < 80; t++) l.step();
    assert.ok(l.crystals.length > 0);
    assert.ok(l.crystals.every((c) => c.origin === "observed"));
    assert.ok(l.snapshot().meanInfluence > 0);
  });

  it("strength is always the Beta posterior mean", () => {
    const l = lab({ fieldStrength: 0.9, similarityThreshold: 0.5 }, 3);
    for (let t = 0; t < 120; t++) {
      l.step();
      for (const c of l.crystals as any[]) {
        assert.ok(Math.abs(c.strength - c.alpha / (c.alpha + c.beta)) < 1e-12);
        assert.ok(c.alpha >= 2 - 1e-9 && c.alpha <= 40 && c.beta >= 2 - 1e-9 && c.beta <= 40);
        assert.ok(c.successes <= c.activations);
      }
    }
  });

  it("a run never edits the archive it was handed", () => {
    const archive = [
      { name: "Echo", mask: 0b111 << 11, nextMask: 0b100001 << 7, strength: 0.7, nextCenter: 1 },
    ];
    const frozen = JSON.stringify(archive);
    const l = new MorphicLab(
      32,
      archive,
      { ...DEFAULT_CONFIG, coupling: 0.8, cells: 32 },
      5,
      "soup",
    );
    for (let t = 0; t < 60; t++) l.step();
    l.remember({ name: "x", mask: 99, nextMask: 99, strength: 1, nextCenter: 0 });
    assert.equal(JSON.stringify(archive), frozen);
  });
});

describe("targets", () => {
  it("are the installed forms, in census identity", () => {
    const l = lab({ innate: true, crystalCount: 14 });
    assert.deepEqual(l.targets(), catalogShapes(14));
    assert.ok(l.targets().every((id) => !COMPARISON_SHAPES.includes(id)));
  });

  it("fall back to the catalog when the table starts empty", () => {
    assert.deepEqual(lab({ innate: false, crystalCount: 14 }).targets(), catalogShapes(14));
    assert.deepEqual(lab({ innate: false, crystalCount: 6 }).targets(), catalogShapes(6));
  });

  it("honour a pre-registered override", () => {
    const l = new MorphicLab(32, [], { ...DEFAULT_CONFIG, cells: 32 }, 1, "soup", {
      targets: [7, 99, 7],
    });
    assert.deepEqual(l.targets(), [7, 99]);
  });

  it("are counted by the census when present", () => {
    const l = lab({}, 1, "garden");
    for (let t = 0; t < 30; t++) l.step();
    const keys = new Set(censusCounts(l.control, l.w, l.h, l.config.wrap).keys());
    // The garden stamps blocks, a blinker, tubs and a beehive, all of them innate targets.
    // (It also stamps a ship, a comparison form, so comparison counts start above zero.)
    assert.ok(l.targets().filter((id) => keys.has(id)).length >= 3);
  });
});

describe("rate-matched Scrambled", () => {
  // Floor: the share of Field's flips Scrambled must match. A sparse board can leave the
  // permuted table nowhere it would change a cell, even after sweeping every site.
  for (const [preset, cells, floor] of [
    ["soup", 48, 0.95],
    ["gliders", 28, 0.9],
    ["rpen", 64, 0.7],
  ] as [PresetId, number, number][]) {
    it(`writes as many cells as Field, each a real departure from Conway (${preset} ${cells}²)`, () => {
      const l = lab({ fieldStrength: 1, similarityThreshold: 0.6 }, 31, preset, cells);
      let field = 0;
      let scrambled = 0;
      for (let t = 0; t < 80; t++) {
        const conwayS = conway(l.scrambled, l.w, l.config.wrap);
        l.step();
        const f = count(l.influenced);
        const s = count(l.influencedS);
        assert.ok(s <= f, `generation ${t + 1}: scrambled ${s} > field ${f}`);
        for (let i = 0; i < l.scrambled.length; i++)
          assert.equal(l.scrambled[i] !== conwayS[i], l.influencedS[i] === 1);
        field += f;
        scrambled += s;
      }
      assert.ok(field > 0);
      assert.ok(scrambled >= floor * field, `scrambled ${scrambled} vs field ${field}`);
      const snap = l.snapshot();
      assert.equal(snap.flipsField, field);
      assert.equal(snap.flipsScrambled, scrambled);
    });
  }
});

describe("Scrambled writes both ways", () => {
  it("adds and deletes cells in proportion to Field, on every seed", () => {
    // With the centre permuted away, some seeds made Scrambled delete-only or add-only.
    for (let seed = 1; seed <= 10; seed++) {
      const l = lab({ fieldStrength: 1, similarityThreshold: 0.6 }, 1000 + seed, "soup", 48);
      let fBirth = 0;
      let fTotal = 0;
      let sBirth = 0;
      let sTotal = 0;
      for (let t = 0; t < 80; t++) {
        l.step();
        for (let i = 0; i < l.field.length; i++) {
          if (l.influenced[i]) {
            fTotal++;
            fBirth += l.field[i];
          }
          if (l.influencedS[i]) {
            sTotal++;
            sBirth += l.scrambled[i];
          }
        }
      }
      assert.ok(sTotal > 20 && fTotal > 20, `seed ${seed}: too few flips`);
      const fShare = fBirth / fTotal;
      const sShare = sBirth / sTotal;
      assert.ok(sShare > 0.05 && sShare < 0.95, `seed ${seed}: scrambled births ${sBirth}/${sTotal}`);
      assert.ok(Math.abs(sShare - fShare) < 0.45, `seed ${seed}: field ${fShare} vs scrambled ${sShare}`);
    }
  });
});
