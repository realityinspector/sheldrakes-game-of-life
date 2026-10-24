import {
  ACCEPT_CAP,
  ANALYSIS_VERSION,
  CANDIDATES_PER_SAMPLE,
  CENSUS_EVERY,
  CENSUS_UNTIL,
  CENTER_BIT,
  COMPARISON_SHAPES,
  ECHO_BOOST,
  ECHO_MEMORY,
  ECHO_PERSIST,
  ECHO_RECUR,
  PATCH,
  PATCH_CELLS,
  samplesFor,
  SAMPLES_PER_GEN,
  WINDOW_GENS,
  bestDice,
  censusCounts,
  classifyLevel,
  dice,
  dStar,
  eligible,
  mergeCounts,
  mixSeed,
  mulberry32,
  objectShape,
  orbitOf,
  orientations,
  permutation,
  permuteMask,
  rowsToMask,
  specificity,
  type LevelName,
} from "./protocol.ts";

export type { LevelName };
export { ANALYSIS_VERSION, PATCH, PATCH_CELLS, WINDOW_GENS };

export type Origin = "innate" | "observed" | "resonant";
export type BoardId = "control" | "field" | "yoked" | "scrambled";

export type ArchiveEntry = {
  name: string;
  mask: number;
  nextMask: number;
  strength: number;
  nextCenter: number;
};

export type FieldConfig = {
  fieldStrength: number;
  temporalDecay: number;
  similarityThreshold: number;
  influenceExponent: number;
  crystalCount: number;
  coupling: number;
  density: number;
  wrap: boolean;
  speed: number;
  innate: boolean;
  cells: number;
};

export type PresetId = "soup" | "rpen" | "acorn" | "gliders" | "pulsar" | "garden" | "gun";

export type HabitCandidate = {
  name: string;
  mask: number;
  nextMask: number;
  nextCenter: number;
  strength: number;
  activations: number;
  successes: number;
  origin: Origin;
};

export type RunSnapshot = {
  gen: number;
  seed: number;
  preset: PresetId;
  runId: number;
  samples: number;
  fieldStrength: number;
  temporalDecay: number;
  similarityThreshold: number;
  coupling: number;
  innate: boolean;
  exploratory: boolean;
  meanInfluence: number;
  meanDiverge: number;
  dStar: number;
  boardShare: number;
  /** Effective flips in generations 1–80 on Field, Yoked and Scrambled. Nulls should match Field. */
  flipsField: number;
  flipsYoked: number;
  flipsScrambled: number;
  gap: number;
  specField: number;
  specYoked: number;
  specScrambled: number;
  level: LevelName;
  provisional: boolean;
  firstFlipGen: number;
  halfDStarGen: number;
  maxPopC: number;
  maxPopM: number;
  popC: number;
  popM: number;
  popY: number;
  popS: number;
  settleC: number;
  settleM: number;
  habits: HabitCandidate[];
};

export type Hud = {
  gen: number;
  popC: number;
  popM: number;
  popY: number;
  popS: number;
  influence: number;
  meanInfluence: number;
  diverge: number;
  dStar: number;
  gap: number;
  level: LevelName;
  provisional: boolean;
  exploratory: boolean;
  seed: number;
  playing: boolean;
  archiveCount: number;
};

export type CrystalView = {
  id: number;
  name: string;
  strength: number;
  age: number;
  origin: Origin;
  mask: number;
  activations: number;
  successes: number;
};

type Crystal = {
  id: number;
  name: string;
  mask: number;
  nextMask: number;
  nextCenter: number;
  forms: number[];
  nextForms: number[];
  strength: number;
  alpha: number;
  beta: number;
  age: number;
  activations: number;
  successes: number;
  origin: Origin;
  /** Calls and correct calls this generation; folded into alpha/beta in learn(). */
  act: number;
  succ: number;
  /** Echo sightings this generation; folded into alpha in learn(). */
  echoes: number;
  /** Seen this generation (called or echoed). Unseen crystals age and decay. */
  touched: boolean;
};

export type LabOptions = {
  /**
   * Pre-registered target shapes (shapeIds) for specificity. When omitted the targets
   * are the forms in the table at generation 0, or, if the table starts empty, the
   * innate catalog it would have held. A ladder passes the confirm stage's targets to
   * its naive and dose stages so every stage scores the same endpoint.
   */
  targets?: number[];
};

type Choice = {
  crystal: Crystal;
  sim: number;
  ori: number;
  clearance: number;
  time: number;
};

export const DEFAULT_CONFIG: FieldConfig = {
  fieldStrength: 0.72,
  temporalDecay: 0.08,
  similarityThreshold: 0.55,
  influenceExponent: 2,
  crystalCount: 14,
  coupling: 0.45,
  density: 0.3,
  wrap: true,
  speed: 12,
  innate: true,
  cells: 48,
};

/** Extra sites Scrambled may consult per generation to match Field's flip count. */
export const SCRAMBLE_EXTRA = 512;
/** Scrambled gathers this many writable sites per flip it owes, then writes the best-scoring ones. */
export const SCRAMBLE_POOL = 4;

/** The eight installed habits, in seeding order. Periods are checked in the tests. */
export const INNATE_FORMS: { name: string; rows: string[] }[] = [
  { name: "Block", rows: [".....", "..##.", "..##.", ".....", "....."] },
  { name: "Blinker", rows: [".....", ".....", ".###.", ".....", "....."] },
  { name: "Tub", rows: [".....", "..#..", ".#.#.", "..#..", "....."] },
  { name: "Boat", rows: [".....", ".##..", ".#.#.", "..#..", "....."] },
  { name: "Beehive", rows: [".....", "..##.", ".#..#", "..##.", "....."] },
  { name: "Glider", rows: [".#...", "..#..", "###..", ".....", "....."] },
  { name: "Toad", rows: [".....", "..###", ".###.", ".....", "....."] },
  { name: "Beacon", rows: ["##...", "##...", "..##.", "..##.", "....."] },
];

/** Soup and glider flocks run on a torus; every other preset has dead edges. */
export function presetWraps(preset: PresetId): boolean {
  return preset === "soup" || preset === "gliders";
}

/** Shapes of the innate habits a table of this capacity would be seeded with. */
export function catalogShapes(crystalCount: number): number[] {
  const cap = Math.max(0, Math.round(crystalCount));
  return INNATE_FORMS.slice(0, cap).map((form) => objectShape(rowsToMask(form.rows)));
}

/** Deduplicated, non-empty targets with every comparison shape removed. */
function cleanTargets(shapes: number[]): number[] {
  const out: number[] = [];
  for (const id of shapes) {
    if (id === 0 || COMPARISON_SHAPES.includes(id) || out.includes(id)) continue;
    out.push(id);
  }
  return out;
}

const GLIDER = [".#.", "..#", "###"];
const GLIDER_NW = ["###", "#..", ".#."];
const GLIDER_NE = ["###", "..#", ".#."];
const GLIDER_SW = [".#.", "#..", "###"];

const GUN = [
  "........................O",
  "......................O.O",
  "............OO......OO............OO",
  "...........O...O....OO............OO",
  "OO........O.....O...OO",
  "OO........O...O.OO....O.O",
  "..........O.....O.......O",
  "...........O...O",
  "............OO",
];

const PULSAR = [
  "..OOO...OOO..",
  ".............",
  "O....O.O....O",
  "O....O.O....O",
  "O....O.O....O",
  "..OOO...OOO..",
  ".............",
  "..OOO...OOO..",
  "O....O.O....O",
  "O....O.O....O",
  "O....O.O....O",
  ".............",
  "..OOO...OOO..",
];

const ACORN = [".#.....", "...#...", "##..###"];
const RPEN = [".##", "##.", ".#."];

function evolveMask(mask: number): { next: number; center: number } {
  const g = new Uint8Array(PATCH_CELLS);
  for (let i = 0; i < PATCH_CELLS; i++) if (mask & (1 << i)) g[i] = 1;
  const next = new Uint8Array(PATCH_CELLS);
  for (let y = 0; y < PATCH; y++) {
    for (let x = 0; x < PATCH; x++) {
      let n = 0;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          if (dx === 0 && dy === 0) continue;
          const nx = x + dx;
          const ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= PATCH || ny >= PATCH) continue;
          n += g[ny * PATCH + nx];
        }
      }
      const alive = g[y * PATCH + x];
      if (n === 3 || (alive && n === 2)) next[y * PATCH + x] = 1;
    }
  }
  let nextMask = 0;
  for (let i = 0; i < PATCH_CELLS; i++) if (next[i]) nextMask |= 1 << i;
  return { next: nextMask, center: next[CENTER_BIT] };
}

function makeCrystal(
  id: number,
  name: string,
  mask: number,
  nextMask: number,
  nextCenter: number,
  strength: number,
  origin: Origin,
  age: number,
): Crystal {
  const alpha = 2 + strength * 10;
  const beta = 2 + (1 - strength) * 10;
  return {
    id,
    name,
    mask,
    nextMask,
    nextCenter,
    forms: orientations(mask),
    nextForms: orientations(nextMask),
    strength: alpha / (alpha + beta),
    alpha,
    beta,
    age,
    activations: 0,
    successes: 0,
    origin,
    act: 0,
    succ: 0,
    echoes: 0,
    touched: false,
  };
}

function stamp(g: Uint8Array, w: number, h: number, rows: string[], ox: number, oy: number) {
  for (let y = 0; y < rows.length; y++) {
    const row = rows[y];
    for (let x = 0; x < row.length; x++) {
      const ch = row[x];
      if (ch !== "#" && ch !== "O") continue;
      const X = ox + x;
      const Y = oy + y;
      if (X < 0 || Y < 0 || X >= w || Y >= h) continue;
      g[Y * w + X] = 1;
    }
  }
}

function centerStamp(g: Uint8Array, w: number, h: number, rows: string[]) {
  const pw = rows.reduce((m, r) => Math.max(m, r.length), 0);
  stamp(g, w, h, rows, Math.floor((w - pw) / 2), Math.floor((h - rows.length) / 2));
}

export class MorphicLab {
  readonly w: number;
  readonly h: number;
  control: Uint8Array;
  field: Uint8Array;
  yoked: Uint8Array;
  scrambled: Uint8Array;
  influenced: Uint8Array;
  influencedY: Uint8Array;
  influencedS: Uint8Array;
  glow: Float32Array;
  config: FieldConfig;
  crystals: Crystal[] = [];
  gen = 0;
  seed = 1;
  runId = 0;
  preset: PresetId = "soup";
  playing = true;
  brush: "paint" | "erase" = "paint";
  mirror = true;
  exploratory = false;
  archive: ArchiveEntry[] = [];
  history: {
    gen: number;
    popC: number;
    popM: number;
    influence: number;
    diverge: number;
    dStar: number;
    gap: number;
  }[] = [];
  /** Target shapes (shapeIds) whose facilitation counts as specificity. */
  trained: number[] = [];
  perm: number[] = [];

  private nextC: Uint8Array;
  private nextF: Uint8Array;
  private nextY: Uint8Array;
  private nextS: Uint8Array;
  /** Field's Conway successor before any overwrite; crystals are scored against this. */
  private conwayF: Uint8Array;
  /** Eligible patches the field consults each generation (scales with board area). */
  readonly samples: number;
  private readonly candidates: number;
  private candX: Int32Array;
  private candY: Int32Array;
  private candCoin: Float64Array;
  private siteStamp: Int32Array;
  private siteEpoch = 0;
  private siteStampS: Int32Array;
  private siteEpochS = 0;
  private tracedGen = -1;
  private tracedCount = 0;
  private rngScramble: () => number = Math.random;
  private windowFlipsY = 0;
  private windowFlipsS = 0;
  private yokePool: Int32Array;
  private pendingEchoes: { mask: number; nextMask: number }[] = [];
  private targetOverride: number[] | null = null;
  private rngInit: () => number = Math.random;
  private rngPatch: () => number = Math.random;
  private rngAccept: () => number = Math.random;
  private rngYoke: () => number = Math.random;
  private nextId = 1;
  private echo = 1;
  private traces: { mask: number; forms: number[]; gen: number }[] = [];
  private censusC = new Map<number, number>();
  private censusF = new Map<number, number>();
  private censusY = new Map<number, number>();
  private censusS = new Map<number, number>();
  private popC = 0;
  private popM = 0;
  private popY = 0;
  private popS = 0;
  private influenceRate = 0;
  private divergeRate = 0;
  private dStarNow = 0;
  private gapNow = 0;
  private specF = 0;
  private specY = 0;
  private specS = 0;
  private windowFlips = 0;
  private windowConsulted = 0;
  private windowOccupied = 0;
  private firstFlipGen = -1;
  private halfDStarGen = -1;
  private maxPopC = 0;
  private maxPopM = 0;
  private saveEvery = 0;

  constructor(
    size: number,
    archive: ArchiveEntry[] = [],
    config?: Partial<FieldConfig>,
    seed?: number,
    preset?: PresetId,
    options: LabOptions = {},
  ) {
    const n = clamp(Math.round(size), 16, 96);
    this.w = n;
    this.h = n;
    const cells = n * n;
    this.targetOverride = options.targets ? options.targets.slice() : null;
    this.control = new Uint8Array(cells);
    this.field = new Uint8Array(cells);
    this.yoked = new Uint8Array(cells);
    this.scrambled = new Uint8Array(cells);
    this.nextC = new Uint8Array(cells);
    this.nextF = new Uint8Array(cells);
    this.nextY = new Uint8Array(cells);
    this.nextS = new Uint8Array(cells);
    this.conwayF = new Uint8Array(cells);
    this.samples = samplesFor(cells);
    this.candidates = this.samples * CANDIDATES_PER_SAMPLE;
    this.candX = new Int32Array(this.candidates);
    this.candY = new Int32Array(this.candidates);
    this.candCoin = new Float64Array(this.candidates);
    this.siteStamp = new Int32Array(cells);
    this.siteStampS = new Int32Array(cells);
    this.yokePool = new Int32Array(cells);
    this.influenced = new Uint8Array(cells);
    this.influencedY = new Uint8Array(cells);
    this.influencedS = new Uint8Array(cells);
    this.glow = new Float32Array(cells);
    this.config = { ...DEFAULT_CONFIG, ...config, cells: n };
    // Own copy: a batch hands the same archive to every seed, and no run may edit it.
    this.archive = archive.map((entry) => ({ ...entry }));
    if (preset) this.preset = preset;
    const initial = seed ?? (Math.floor(Math.random() * 90000) + 1000) >>> 0;
    this.reseed(this.preset, initial);
  }

  hud(): Hud {
    const level = this.levelNow();
    return {
      gen: this.gen,
      popC: this.popC,
      popM: this.popM,
      popY: this.popY,
      popS: this.popS,
      influence: this.influenceRate,
      meanInfluence: this.flipRate(),
      diverge: this.divergeRate,
      dStar: this.dStarNow,
      gap: this.gapNow,
      level: level.name,
      provisional: level.provisional,
      exploratory: this.exploratory,
      seed: this.seed,
      playing: this.playing,
      archiveCount: this.archive.length,
    };
  }

  crystalViews(): CrystalView[] {
    return this.crystals
      .slice()
      .sort((a, b) => b.strength - a.strength)
      .map((c) => ({
        id: c.id,
        name: c.name,
        strength: c.strength,
        age: c.age,
        origin: c.origin,
        mask: c.mask,
        activations: c.activations,
        successes: c.successes,
      }));
  }

  toArchive(): ArchiveEntry[] {
    const learned = this.crystals
      .filter((c) => c.origin !== "innate")
      .sort((a, b) => b.strength - a.strength)
      .slice(0, 24);
    const merged = new Map<number, ArchiveEntry>();
    for (const entry of this.archive) merged.set(entry.mask, entry);
    for (const c of learned) {
      merged.set(c.mask, {
        name: c.name,
        mask: c.mask,
        nextMask: c.nextMask,
        strength: c.strength,
        nextCenter: c.nextCenter,
      });
    }
    return [...merged.values()].sort((a, b) => b.strength - a.strength).slice(0, 24);
  }

  remember(entry: ArchiveEntry) {
    const existing = this.archive.find((item) => item.mask === entry.mask);
    if (existing) {
      if (entry.strength > existing.strength) existing.strength = entry.strength;
      return;
    }
    this.archive.push({ ...entry });
    this.archive.sort((a, b) => b.strength - a.strength);
    if (this.archive.length > 24) this.archive.length = 24;
  }

  snapshot(): RunSnapshot {
    const tail = this.history.slice(-24);
    const level = this.levelNow();
    return {
      gen: this.gen,
      seed: this.seed,
      preset: this.preset,
      runId: this.runId,
      samples: this.gen,
      fieldStrength: this.config.fieldStrength,
      temporalDecay: this.config.temporalDecay,
      similarityThreshold: this.config.similarityThreshold,
      coupling: this.config.coupling,
      innate: this.config.innate,
      exploratory: this.exploratory,
      meanInfluence: this.flipRate(),
      meanDiverge: this.divergeRate,
      dStar: this.dStarNow,
      boardShare: this.windowOccupied ? this.windowFlips / this.windowOccupied : 0,
      flipsField: this.windowFlips,
      flipsYoked: this.windowFlipsY,
      flipsScrambled: this.windowFlipsS,
      gap: this.gapNow,
      specField: this.specF,
      specYoked: this.specY,
      specScrambled: this.specS,
      level: level.name,
      provisional: level.provisional,
      firstFlipGen: this.firstFlipGen,
      halfDStarGen: this.halfDStarGen,
      maxPopC: this.maxPopC,
      maxPopM: this.maxPopM,
      popC: this.popC,
      popM: this.popM,
      popY: this.popY,
      popS: this.popS,
      settleC: stdev(tail.map((point) => point.popC)),
      settleM: stdev(tail.map((point) => point.popM)),
      habits: this.crystals
        .filter((crystal) => crystal.origin !== "innate")
        .map((crystal) => ({
          name: crystal.name,
          mask: crystal.mask,
          nextMask: crystal.nextMask,
          nextCenter: crystal.nextCenter,
          strength: crystal.strength,
          activations: crystal.activations,
          successes: crystal.successes,
          origin: crystal.origin,
        })),
    };
  }

  setConfig(patch: Partial<FieldConfig>) {
    const scientific = Object.keys(patch).some((key) => key !== "speed" && key !== "cells");
    if (this.gen > 0 && scientific) this.exploratory = true;
    this.config = { ...this.config, ...patch, cells: this.w };
    if (patch.crystalCount !== undefined || patch.coupling !== undefined) {
      this.trimCrystals();
      this.importResonance();
      // Still generation 0: the table changed before anything ran, so the targets follow it.
      if (this.gen === 0) this.captureTrained();
    }
  }

  touch() {
    if (this.gen > 0) this.exploratory = true;
  }

  clearMemory() {
    this.archive = [];
    this.crystals = this.crystals.filter((c) => c.origin === "innate");
    this.captureTrained();
  }

  reseed(preset: PresetId, seed: number) {
    this.runId += 1;
    this.preset = preset;
    this.seed = seed >>> 0;
    this.exploratory = false;
    this.rngInit = mulberry32(this.seed);
    this.rngPatch = mulberry32(mixSeed(this.seed, 0xa11ce));
    this.rngAccept = mulberry32(mixSeed(this.seed, 0xacce97));
    this.rngYoke = mulberry32(mixSeed(this.seed, 0x70ce11));
    this.rngScramble = mulberry32(mixSeed(this.seed, 0x5c3a3b1e));
    this.perm = permutation(this.seed);
    this.gen = 0;
    this.history = [];
    this.traces = [];
    this.tracedGen = -1;
    this.pendingEchoes = [];
    this.saveEvery = 0;
    this.censusC.clear();
    this.censusF.clear();
    this.censusY.clear();
    this.censusS.clear();
    this.influenced.fill(0);
    this.influencedY.fill(0);
    this.influencedS.fill(0);
    this.glow.fill(0);
    this.windowFlips = 0;
    this.windowFlipsY = 0;
    this.windowFlipsS = 0;
    this.windowConsulted = 0;
    this.windowOccupied = 0;
    this.firstFlipGen = -1;
    this.halfDStarGen = -1;
    this.influenceRate = 0;
    this.maxPopC = 0;
    this.maxPopM = 0;
    this.control.fill(0);
    this.field.fill(0);
    this.yoked.fill(0);
    this.scrambled.fill(0);
    this.echo = 1;
    this.config.wrap = presetWraps(preset);
    this.paintPreset(this.field);
    this.control.set(this.field);
    this.yoked.set(this.field);
    this.scrambled.set(this.field);
    this.crystals = [];
    this.seedInnate();
    this.importResonance();
    this.captureTrained();
    this.recount();
    this.refreshSpecificity();
    this.pushHistory();
  }

  randomize() {
    this.reseed(this.preset, (Math.floor(Math.random() * 900000) + 1) >>> 0);
  }

  clearBoards() {
    this.runId += 1;
    // The learned table, the random streams and the targets carry over, and the board
    // will be hand-drawn, so this run cannot be replayed from a seed.
    this.exploratory = true;
    this.control.fill(0);
    this.field.fill(0);
    this.yoked.fill(0);
    this.scrambled.fill(0);
    this.influenced.fill(0);
    this.influencedY.fill(0);
    this.influencedS.fill(0);
    this.glow.fill(0);
    this.gen = 0;
    this.history = [];
    this.traces = [];
    this.tracedGen = -1;
    this.pendingEchoes = [];
    this.windowFlips = 0;
    this.windowFlipsY = 0;
    this.windowFlipsS = 0;
    this.windowConsulted = 0;
    this.windowOccupied = 0;
    this.firstFlipGen = -1;
    this.halfDStarGen = -1;
    this.influenceRate = 0;
    this.maxPopC = 0;
    this.maxPopM = 0;
    this.censusC.clear();
    this.censusF.clear();
    this.censusY.clear();
    this.censusS.clear();
    this.recount();
    this.refreshSpecificity();
    this.pushHistory();
  }

  paint(which: BoardId, x: number, y: number, mirror: boolean) {
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return;
    if (this.gen > 0) this.exploratory = true;
    const value = this.brush === "erase" ? 0 : 1;
    const write = (g: Uint8Array) => {
      g[y * this.w + x] = value;
    };
    if (mirror) {
      write(this.control);
      write(this.field);
      write(this.yoked);
      write(this.scrambled);
    } else if (which === "control") write(this.control);
    else if (which === "yoked") write(this.yoked);
    else if (which === "scrambled") write(this.scrambled);
    else write(this.field);
    this.recount();
  }

  step() {
    const { w, h } = this;
    const wrap = this.config.wrap;
    const inWindow = this.gen < WINDOW_GENS;
    const occF = this.conwayInto(this.field, this.nextF, wrap);
    this.conwayInto(this.control, this.nextC, wrap);
    this.conwayInto(this.yoked, this.nextY, wrap);
    this.conwayInto(this.scrambled, this.nextS, wrap);
    this.conwayF.set(this.nextF);
    this.influenced.fill(0);
    this.influencedY.fill(0);
    this.influencedS.fill(0);

    let fieldFlips = 0;
    let scrambledFlips = 0;
    let consulted = 0;
    if (this.config.fieldStrength > 0.001) {
      // One list of candidate sites and coins per generation, drawn whatever the boards
      // hold. Field consults its first `samples` eligible sites from it; Scrambled
      // walks the same list (then its own stream) until it has made as many effective
      // flips as Field. Identical boards make identical draws, and Field's sampling never
      // depends on the Scrambled board.
      for (let k = 0; k < this.candidates; k++) {
        this.candX[k] = Math.floor(this.rngPatch() * w);
        this.candY[k] = Math.floor(this.rngPatch() * h);
        this.candCoin[k] = this.rngAccept();
      }
      // Both boards read the table as it stood at the start of the generation:
      // scoring and echoes are folded in by learn(), after the pass.
      const twins = this.twins();
      let takenF = 0;
      // Monotone across runs, so a stamp left by an earlier run can never match.
      const stamp = ++this.siteEpoch;
      for (let k = 0; k < this.candidates && takenF < this.samples; k++) {
        const x = this.candX[k];
        const y = this.candY[k];
        const coin = this.candCoin[k];
        // Sites are drawn with replacement; a repeat is skipped so no site is consulted,
        // scored, echoed or tossed twice in one generation.
        const site = y * w + x;
        if (this.siteStamp[site] === stamp) continue;
        this.siteStamp[site] = stamp;
        if (takenF < this.samples) {
          const patchF = this.pack(this.field, x, y);
          if (eligible(patchF)) {
            takenF++;
            consulted++;
            const conwayPatch = this.pack(this.conwayF, x, y);
            const choice = this.choose(patchF, this.crystals);
            fieldFlips += this.apply(choice, coin, this.nextF, this.influenced, x, y, conwayPatch);
            // Observation does not need a table: an empty table can still learn echoes.
            this.considerEcho(patchF, conwayPatch);
          }
        }
      }
      scrambledFlips = this.scrambledPass(fieldFlips, twins);
    }

    let yokedFlips = 0;
    if (fieldFlips > 0) {
      // Exactly fieldFlips distinct cells, uniform over Yoked's own eligible neighbourhoods
      // (fewer only if Yoked has fewer eligible cells than that). Rejection sampling with a
      // try cap ran out on sparse boards and left Yoked well short of Field.
      let pool = 0;
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          if (eligible(this.pack(this.yoked, x, y))) this.yokePool[pool++] = y * w + x;
        }
      }
      const take = Math.min(fieldFlips, pool);
      for (let i = 0; i < take; i++) {
        const j = i + Math.floor(this.rngYoke() * (pool - i));
        const idx = this.yokePool[j];
        this.yokePool[j] = this.yokePool[i];
        this.yokePool[i] = idx;
        this.nextY[idx] ^= 1;
        this.influencedY[idx] = 1;
      }
      yokedFlips = take;
    }

    this.swap();
    this.learn();
    this.gen++;
    this.influenceRate = consulted ? fieldFlips / consulted : 0;
    if (inWindow) {
      this.windowFlips += fieldFlips;
      this.windowFlipsY += yokedFlips;
      this.windowFlipsS += scrambledFlips;
      this.windowConsulted += consulted;
      this.windowOccupied += occF;
    }
    if (fieldFlips > 0 && this.firstFlipGen < 0) this.firstFlipGen = this.gen;
    this.recount();
    if (this.dStarNow >= 0.5 && this.halfDStarGen < 0) this.halfDStarGen = this.gen;
    if (this.gen % CENSUS_EVERY === 0 && this.gen <= CENSUS_UNTIL) this.takeCensus();
    else this.refreshSpecificity();
    this.pushHistory();
    this.saveEvery++;
    if (this.saveEvery >= 24) {
      this.saveEvery = 0;
      this.archive = this.toArchive();
    }
  }

  /**
   * Scrambled's memory pass, rate-matched to Field. It consults eligible sites (the shared
   * candidate list first, then its own stream) and, at each, finds its best permuted
   * crystal by Field's ranking (Diceᵉ × strength × recency) with the similarity bar at
   * zero. It then writes the predicted centre at the `target` best-scoring sites where that
   * prediction differs from Conway. The permutation keeps the centre cell, so a scrambled
   * crystal predicts the same centre as its real one. Permuted shapes rarely clear Field's similarity bar,
   * so with the bar kept the null fired about a third as often, and "Field beats
   * Scrambled" partly meant "Field wrote more cells". This keeps the machinery and the
   * count, and removes the content.
   */
  private scrambledPass(target: number, twins: Crystal[]): number {
    if (target <= 0 || twins.length === 0) return 0;
    const { w, h } = this;
    const stamp = ++this.siteEpochS;
    const decay = this.config.temporalDecay;
    const sharpen = this.config.influenceExponent;
    const found: { idx: number; score: number; value: number }[] = [];
    const want = target * SCRAMBLE_POOL;
    const visit = (x: number, y: number) => {
      const site = y * w + x;
      if (this.siteStampS[site] === stamp) return;
      this.siteStampS[site] = stamp;
      const patch = this.pack(this.scrambled, x, y);
      if (!eligible(patch)) return;
      let best = -1;
      let value = 0;
      for (const twin of twins) {
        // Field's ranking, clearanceᵉ × strength × recency, with the similarity bar at zero.
        const score =
          Math.pow(bestDice(patch, twin.forms).score, sharpen) *
          twin.strength *
          Math.exp(-decay * twin.age);
        if (score > best) {
          best = score;
          value = twin.nextCenter;
        }
      }
      if (best > 0 && value !== this.nextS[site]) found.push({ idx: site, score: best, value });
    };
    for (let k = 0; k < this.candidates && found.length < want; k++)
      visit(this.candX[k], this.candY[k]);
    for (let k = 0; k < SCRAMBLE_EXTRA && found.length < want; k++) {
      visit(Math.floor(this.rngScramble() * w), Math.floor(this.rngScramble() * h));
    }
    if (found.length < target) {
      // Sparse board: sweep every remaining site once, from a random start.
      const n = w * h;
      const start = Math.floor(this.rngScramble() * n);
      for (let k = 0; k < n && found.length < target; k++) {
        const site = (start + k) % n;
        visit(site % w, (site / w) | 0);
      }
    }
    // Stable on ties: earlier-consulted sites win.
    found.sort((a, b) => b.score - a.score);
    const take = Math.min(target, found.length);
    for (let i = 0; i < take; i++) {
      this.nextS[found[i].idx] = found[i].value;
      this.influencedS[found[i].idx] = 1;
    }
    return take;
  }

  private flipRate(): number {
    return this.windowConsulted ? this.windowFlips / this.windowConsulted : 0;
  }

  private levelNow() {
    return classifyLevel(
      this.config.fieldStrength,
      this.flipRate(),
      this.windowFlips > 0,
      this.gen,
    );
  }

  private swap() {
    let tmp = this.control;
    this.control = this.nextC;
    this.nextC = tmp;
    tmp = this.field;
    this.field = this.nextF;
    this.nextF = tmp;
    tmp = this.yoked;
    this.yoked = this.nextY;
    this.nextY = tmp;
    tmp = this.scrambled;
    this.scrambled = this.nextS;
    this.nextS = tmp;
  }

  private choose(patch: number, crystals: Crystal[]): Choice | null {
    const threshold = this.config.similarityThreshold;
    let best: Choice | null = null;
    let bestScore = 0;
    for (const crystal of crystals) {
      const hit = bestDice(patch, crystal.forms);
      if (hit.score < threshold) continue;
      const time = Math.exp(-this.config.temporalDecay * crystal.age);
      const clearance = (hit.score - threshold) / Math.max(0.05, 1 - threshold);
      const sharp = Math.pow(Math.min(1, Math.max(0, clearance)), this.config.influenceExponent);
      const score = sharp * crystal.strength * time;
      if (!best || score > bestScore) {
        bestScore = score;
        best = { crystal, sim: hit.score, ori: hit.index, clearance: Math.min(1, clearance), time };
      }
    }
    return best;
  }

  /**
   * Offer the chosen crystal's claim on the centre cell. With `conwayPatch` (Field only)
   * the call is also scored: right when the crystal's expected next mask matches what
   * Conway produced from this patch before any overwrite. Returns 1 for an effective flip.
   */
  private apply(
    choice: Choice | null,
    coin: number,
    next: Uint8Array,
    influenced: Uint8Array,
    x: number,
    y: number,
    conwayPatch: number | null,
  ): number {
    if (!choice) return 0;
    const crystal = choice.crystal;
    if (conwayPatch !== null) {
      const expected = crystal.nextForms[choice.ori];
      if (dice(conwayPatch, expected) >= this.config.similarityThreshold) crystal.succ++;
      crystal.act++;
      crystal.touched = true;
    }
    const idx = y * this.w + x;
    // One write per cell per generation, so an effective flip is exactly a cell whose
    // output differs from Conway and the count Yoked copies is a count of cells.
    if (influenced[idx]) return 0;
    const predicted = crystal.nextCenter;
    if (predicted === next[idx]) return 0;
    const p = Math.min(
      ACCEPT_CAP,
      choice.clearance * crystal.strength * choice.time * this.config.fieldStrength,
    );
    if (coin >= p) return 0;
    next[idx] = predicted;
    influenced[idx] = 1;
    if (conwayPatch !== null) this.glow[idx] = 1;
    return 1;
  }

  /**
   * A consulted Field patch becomes an echo when it persists into its own Conway
   * successor (Dice ≥ ECHO_PERSIST) or recurs from an earlier generation within
   * ECHO_MEMORY (Dice ≥ ECHO_RECUR). Echoes are queued and folded in by learn().
   */
  private considerEcho(mask: number, nextMask: number) {
    const persisted = dice(mask, nextMask) >= ECHO_PERSIST;
    let recurred = false;
    for (let i = this.traces.length - 1; i >= 0; i--) {
      const trace = this.traces[i];
      if (this.gen - trace.gen > ECHO_MEMORY) break;
      // Recurrence means seen in an earlier generation, not a neighbouring sample now.
      if (trace.gen === this.gen) continue;
      if (bestDice(mask, trace.forms).score >= ECHO_RECUR) {
        recurred = true;
        break;
      }
    }
    // Recurrence memory keeps the first SAMPLES_PER_GEN consulted patches of each generation,
    // so "seen in the last ECHO_MEMORY generations" means the same on every board size.
    if (this.tracedGen !== this.gen) {
      this.tracedGen = this.gen;
      this.tracedCount = 0;
    }
    if (this.tracedCount < SAMPLES_PER_GEN) {
      this.tracedCount++;
      this.traces.push({ mask, forms: orientations(mask), gen: this.gen });
      if (this.traces.length > 240) this.traces.splice(0, 80);
    }
    if (persisted || recurred) this.pendingEchoes.push({ mask, nextMask });
  }

  /**
   * End-of-generation bookkeeping. Calls update the Beta posterior (alpha += right,
   * beta += wrong); echoes add ECHO_BOOST to alpha; crystals not seen this generation
   * age and decay toward the Beta(2, 2) prior. Strength is always alpha / (alpha + beta).
   */
  private learn() {
    for (const echo of this.pendingEchoes) {
      const orbit = orbitOf(echo.mask);
      const known = this.crystals.find(
        (c) => orbitOf(c.mask) === orbit || bestDice(echo.mask, c.forms).score >= 0.92,
      );
      if (known) {
        known.echoes += 1;
        known.touched = true;
      } else {
        this.addObserved(echo.mask, echo.nextMask);
      }
    }
    this.pendingEchoes = [];
    const fade = 1 - Math.min(0.5, this.config.temporalDecay);
    for (const crystal of this.crystals) {
      if (crystal.act > 0) {
        crystal.alpha = Math.min(40, crystal.alpha + crystal.succ);
        crystal.beta = Math.min(40, crystal.beta + (crystal.act - crystal.succ));
        crystal.activations += crystal.act;
        crystal.successes += crystal.succ;
      }
      if (crystal.echoes > 0)
        crystal.alpha = Math.min(40, crystal.alpha + ECHO_BOOST * crystal.echoes);
      if (crystal.touched) {
        crystal.age = 0;
      } else {
        crystal.age += 1;
        crystal.alpha = 2 + (crystal.alpha - 2) * fade;
        crystal.beta = 2 + (crystal.beta - 2) * fade;
      }
      crystal.strength = crystal.alpha / (crystal.alpha + crystal.beta);
      crystal.act = 0;
      crystal.succ = 0;
      crystal.echoes = 0;
      crystal.touched = false;
    }
    this.crystals = this.crystals.filter(
      (c) => c.origin === "innate" || c.strength > 0.08 || c.age < 48,
    );
    this.trimCrystals();
  }

  private addObserved(mask: number, nextMask: number) {
    const cap = this.config.crystalCount;
    if (this.crystals.length >= cap) {
      let weakest: Crystal | null = null;
      for (const c of this.crystals) {
        if (c.origin === "innate") continue;
        if (!weakest || c.strength < weakest.strength) weakest = c;
      }
      if (!weakest || weakest.strength > 0.55) return;
      this.crystals = this.crystals.filter((c) => c !== weakest);
    }
    const center = (nextMask >> CENTER_BIT) & 1;
    this.crystals.push(
      makeCrystal(
        this.nextId++,
        `Echo ${this.echo++}`,
        mask,
        nextMask,
        center,
        0.42,
        "observed",
        0,
      ),
    );
  }

  private seedInnate() {
    if (!this.config.innate) return;
    for (const form of INNATE_FORMS) {
      if (this.crystals.length >= Math.round(this.config.crystalCount)) break;
      const mask = rowsToMask(form.rows);
      const evolved = evolveMask(mask);
      this.crystals.push(
        makeCrystal(
          this.nextId++,
          form.name,
          mask,
          evolved.next,
          evolved.center,
          0.58,
          "innate",
          0,
        ),
      );
    }
  }

  private importResonance() {
    const coupling = this.config.coupling;
    this.crystals = this.crystals.filter((c) => c.origin !== "resonant");
    if (coupling <= 0.001) return;
    for (const entry of this.archive) {
      if (this.crystals.length >= this.config.crystalCount) break;
      if (
        this.crystals.some(
          (c) => c.mask === entry.mask || bestDice(entry.mask, c.forms).score > 0.92,
        )
      ) {
        continue;
      }
      this.crystals.push(
        makeCrystal(
          this.nextId++,
          entry.name,
          entry.mask,
          entry.nextMask,
          entry.nextCenter,
          clamp(entry.strength * coupling, 0.12, 0.92),
          "resonant",
          2,
        ),
      );
    }
  }

  /** Target shapes for this run. See LabOptions.targets. */
  targets(): number[] {
    return this.trained.slice();
  }

  private captureTrained() {
    const fromTable = cleanTargets(this.crystals.map((c) => objectShape(c.mask)));
    const fallback = cleanTargets(catalogShapes(this.config.crystalCount));
    const override = this.targetOverride ? cleanTargets(this.targetOverride) : [];
    this.trained = override.length ? override : fromTable.length ? fromTable : fallback;
  }

  private twins(): Crystal[] {
    return this.crystals.map((c) => {
      const mask = permuteMask(c.mask, this.perm);
      const nextMask = permuteMask(c.nextMask, this.perm);
      const nextCenter = (nextMask >> CENTER_BIT) & 1;
      return {
        ...c,
        mask,
        nextMask,
        nextCenter,
        forms: orientations(mask),
        nextForms: orientations(nextMask),
        name: `${c.name} · scrambled`,
        act: 0,
        succ: 0,
        echoes: 0,
        touched: false,
      };
    });
  }

  private trimCrystals() {
    const cap = Math.round(this.config.crystalCount);
    if (this.crystals.length <= cap) return;
    const ranked = this.crystals.slice().sort((a, b) => {
      if (a.origin === "innate" && b.origin !== "innate") return -1;
      if (b.origin === "innate" && a.origin !== "innate") return 1;
      return b.strength - a.strength;
    });
    const keep = new Set(ranked.slice(0, cap));
    this.crystals = this.crystals.filter((c) => keep.has(c));
  }

  private takeCensus() {
    const wrap = this.config.wrap;
    mergeCounts(this.censusC, censusCounts(this.control, this.w, this.h, wrap));
    mergeCounts(this.censusF, censusCounts(this.field, this.w, this.h, wrap));
    mergeCounts(this.censusY, censusCounts(this.yoked, this.w, this.h, wrap));
    mergeCounts(this.censusS, censusCounts(this.scrambled, this.w, this.h, wrap));
    this.refreshSpecificity();
  }

  private refreshSpecificity() {
    this.specF = specificity(this.censusF, this.censusC, this.trained);
    this.specY = specificity(this.censusY, this.censusC, this.trained);
    this.specS = specificity(this.censusS, this.censusC, this.trained);
    this.gapNow = this.specF - Math.max(this.specY, this.specS);
  }

  private paintPreset(g: Uint8Array) {
    const { w, h } = this;
    if (this.preset === "soup") {
      const d = this.config.density;
      for (let i = 0; i < g.length; i++) g[i] = this.rngInit() < d ? 1 : 0;
      return;
    }
    if (this.preset === "rpen") return centerStamp(g, w, h, RPEN);
    if (this.preset === "acorn") return centerStamp(g, w, h, ACORN);
    if (this.preset === "pulsar") return centerStamp(g, w, h, PULSAR);
    if (this.preset === "gun") return stamp(g, w, h, GUN, 2, Math.floor(h / 2) - 4);
    if (this.preset === "gliders") {
      stamp(g, w, h, GLIDER, 3, 3);
      stamp(g, w, h, GLIDER_NW, w - 8, 3);
      stamp(g, w, h, GLIDER_SW, 4, h - 8);
      stamp(g, w, h, GLIDER_NE, w - 9, h - 8);
      stamp(g, w, h, GLIDER, Math.floor(w / 2), 4);
      stamp(g, w, h, GLIDER_SW, Math.floor(w / 2), h - 8);
      return;
    }
    stamp(g, w, h, ["##", "##"], 4, 4);
    stamp(g, w, h, ["##", "##"], w - 7, 5);
    stamp(g, w, h, ["###"], 8, Math.floor(h / 2));
    stamp(g, w, h, [".#.", "#.#", ".#."], w - 14, h - 12);
    stamp(g, w, h, ["..##.", ".#..#", "..##."], Math.floor(w / 2) - 2, 4);
    stamp(g, w, h, [".#.", "#.#", ".#."], 6, h - 10);
    stamp(g, w, h, ["##.", "#.#", ".##"], Math.floor(w / 2), Math.floor(h / 2));
    stamp(g, w, h, ["##", "##"], w - 8, h - 7);
    stamp(g, w, h, GLIDER, Math.floor(w / 2) - 8, Math.floor(h / 2) + 6);
  }

  private conwayInto(src: Uint8Array, dst: Uint8Array, wrap: boolean): number {
    const { w, h } = this;
    let occupied = 0;
    for (let y = 0; y < h; y++) {
      const ym = y === 0 ? (wrap ? h - 1 : -1) : y - 1;
      const yp = y === h - 1 ? (wrap ? 0 : -1) : y + 1;
      for (let x = 0; x < w; x++) {
        const xm = x === 0 ? (wrap ? w - 1 : -1) : x - 1;
        const xp = x === w - 1 ? (wrap ? 0 : -1) : x + 1;
        let n = 0;
        if (ym >= 0) {
          if (xm >= 0) n += src[ym * w + xm];
          n += src[ym * w + x];
          if (xp >= 0) n += src[ym * w + xp];
        }
        if (xm >= 0) n += src[y * w + xm];
        if (xp >= 0) n += src[y * w + xp];
        if (yp >= 0) {
          if (xm >= 0) n += src[yp * w + xm];
          n += src[yp * w + x];
          if (xp >= 0) n += src[yp * w + xp];
        }
        const alive = src[y * w + x];
        if (alive || n > 0) occupied++;
        dst[y * w + x] = n === 3 || (alive && n === 2) ? 1 : 0;
      }
    }
    return occupied;
  }

  private pack(g: Uint8Array, x: number, y: number): number {
    const { w, h } = this;
    const wrap = this.config.wrap;
    let mask = 0;
    let bit = 0;
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -2; dx <= 2; dx++) {
        let nx = x + dx;
        let ny = y + dy;
        if (wrap) {
          nx = (nx + w) % w;
          ny = (ny + h) % h;
        } else if (nx < 0 || ny < 0 || nx >= w || ny >= h) {
          bit++;
          continue;
        }
        if (g[ny * w + nx]) mask |= 1 << bit;
        bit++;
      }
    }
    return mask;
  }

  private recount() {
    let c = 0;
    let m = 0;
    let y = 0;
    let s = 0;
    let d = 0;
    const n = this.control.length;
    for (let i = 0; i < n; i++) {
      c += this.control[i];
      m += this.field[i];
      y += this.yoked[i];
      s += this.scrambled[i];
      if (this.control[i] !== this.field[i]) d++;
    }
    this.popC = c;
    this.popM = m;
    this.popY = y;
    this.popS = s;
    this.divergeRate = d / n;
    this.dStarNow = dStar(this.divergeRate, c / n, m / n);
    if (c > this.maxPopC) this.maxPopC = c;
    if (m > this.maxPopM) this.maxPopM = m;
  }

  private pushHistory() {
    this.history.push({
      gen: this.gen,
      popC: this.popC,
      popM: this.popM,
      influence: this.flipRate(),
      diverge: this.divergeRate,
      dStar: this.dStarNow,
      gap: this.gapNow,
    });
    if (this.history.length > 180) this.history.shift();
  }
}

function stdev(values: number[]): number {
  if (values.length < 8) return 0;
  let mean = 0;
  for (const value of values) mean += value;
  mean /= values.length;
  let acc = 0;
  for (const value of values) {
    const d = value - mean;
    acc += d * d;
  }
  return Math.sqrt(acc / values.length);
}

function clamp(n: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, n));
}

export const PAL = {
  ink: "#0c1210",
  dead: "#14211c",
  life: "#3dba86",
  lifeHot: "#d7ffe9",
  amber: "#e39a3c",
  amberHot: "#ffe2b8",
  bone: "#f3ecdc",
  mist: "#8d978f",
};

export function drawBoard(
  ctx: CanvasRenderingContext2D,
  lab: MorphicLab,
  which: BoardId,
  cssW: number,
  cssH: number,
) {
  ctx.clearRect(0, 0, cssW, cssH);
  const n = lab.w;
  const side = Math.floor(Math.min(cssW, cssH));
  if (side < 8) return;
  const ox = Math.floor((cssW - side) / 2);
  const oy = Math.floor((cssH - side) / 2);
  const cell = side / n;
  ctx.fillStyle = PAL.ink;
  ctx.fillRect(ox, oy, side, side);

  const grid =
    which === "control"
      ? lab.control
      : which === "yoked"
        ? lab.yoked
        : which === "scrambled"
          ? lab.scrambled
          : lab.field;
  const marks =
    which === "field"
      ? lab.influenced
      : which === "yoked"
        ? lab.influencedY
        : which === "scrambled"
          ? lab.influencedS
          : null;
  const inset = cell >= 9 ? cell * 0.1 : cell >= 6 ? 0.6 : 0.25;
  const size = cell - inset * 2;
  const radius = Math.min(3.5, size * 0.22);
  const round = size >= 6;

  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const i = y * n + x;
      const px = ox + x * cell + inset;
      const py = oy + y * cell + inset;
      const alive = grid[i] === 1;
      const overridden = marks !== null && marks[i] === 1;
      if (!alive) {
        if (which === "field" && lab.glow[i] > 0.05) {
          ctx.globalAlpha = lab.glow[i] * 0.4;
          ctx.fillStyle = PAL.amber;
          fillShape(ctx, px, py, size, size, radius, round);
          ctx.globalAlpha = 1;
        } else if (cell >= 7) {
          ctx.fillStyle = PAL.dead;
          fillShape(ctx, px, py, size, size, radius, round);
        }
        continue;
      }
      ctx.fillStyle = overridden ? PAL.amber : which === "control" ? PAL.mist : PAL.life;
      fillShape(ctx, px, py, size, size, radius, round);
      if (size >= 8) {
        ctx.globalAlpha = 0.7;
        ctx.fillStyle = overridden ? PAL.amberHot : PAL.lifeHot;
        ctx.fillRect(px + size * 0.2, py + size * 0.18, size * 0.28, size * 0.18);
        ctx.globalAlpha = 1;
      }
    }
  }

  if (which === "field") {
    const glow = lab.glow;
    for (let i = 0; i < glow.length; i++) {
      if (glow[i] > 0.02) glow[i] *= 0.9;
      else glow[i] = 0;
    }
  }
}

function fillShape(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
  round: boolean,
) {
  ctx.beginPath();
  if (round && typeof ctx.roundRect === "function") ctx.roundRect(x, y, w, h, r);
  else ctx.rect(x, y, w, h);
  ctx.fill();
}

export function cellFromPointer(
  canvas: HTMLCanvasElement,
  clientX: number,
  clientY: number,
  n: number,
): { x: number; y: number } | null {
  const rect = canvas.getBoundingClientRect();
  const lx = clientX - rect.left;
  const ly = clientY - rect.top;
  const side = Math.min(rect.width, rect.height);
  const ox = (rect.width - side) / 2;
  const oy = (rect.height - side) / 2;
  const gx = lx - ox;
  const gy = ly - oy;
  if (gx < 0 || gy < 0 || gx >= side || gy >= side) return null;
  return {
    x: Math.min(n - 1, Math.floor((gx / side) * n)),
    y: Math.min(n - 1, Math.floor((gy / side) * n)),
  };
}

let shotCanvas: HTMLCanvasElement | null = null;

export function snapshotBoards(lab: MorphicLab): string {
  if (typeof document === "undefined") return "";
  const tile = 72;
  if (!shotCanvas) {
    shotCanvas = document.createElement("canvas");
    shotCanvas.width = tile * 4;
    shotCanvas.height = tile;
  }
  const ctx = shotCanvas.getContext("2d");
  if (!ctx) return "";
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, shotCanvas.width, shotCanvas.height);
  const boards: BoardId[] = ["control", "field", "yoked", "scrambled"];
  for (let i = 0; i < boards.length; i++) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(i * tile, 0, tile, tile);
    ctx.clip();
    ctx.translate(i * tile, 0);
    drawBoard(ctx, lab, boards[i], tile, tile);
    ctx.restore();
  }
  return shotCanvas.toDataURL("image/jpeg", 0.62);
}
