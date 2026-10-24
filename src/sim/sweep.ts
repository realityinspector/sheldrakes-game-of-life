import {
  DEFAULT_CONFIG,
  MorphicLab,
  presetWraps,
  snapshotBoards,
  type ArchiveEntry,
  type FieldConfig,
  type PresetId,
} from "./engine.ts";
import type { MegaPhase } from "./mega-search.ts";
import { MegaSearch } from "./mega-search.ts";
import {
  ALPHA,
  ANALYSIS_VERSION,
  WINDOW_GENS,
  alphaForAttempt,
  bootstrapMedianCI,
  mulberry32,
  seedFromRow,
  sha256,
  signTest,
} from "./protocol.ts";

export type AxisKey =
  | "fieldStrength"
  | "temporalDecay"
  | "similarityThreshold"
  | "influenceExponent"
  | "coupling"
  | "density"
  | "crystalCount";

export type SweepMode = "seek" | "grid" | "confirm" | "mega";
export type SeekGoal = "armed" | "gap";

export type SweepCard = {
  id: number;
  label: string;
  level: string;
  provisional: boolean;
  flipRate: number;
  dStar: number;
  gap: number;
  specField: number;
  specYoked: number;
  specScrambled: number;
  gen: number;
  seed: number;
  cells: number;
  image: string;
  goal: number;
  config: FieldConfig;
};

export type ArmTest = {
  n: number;
  pos: number;
  neg: number;
  p: number;
  median: number;
  lo: number;
  hi: number;
};

export type ConfirmResult = {
  row: string;
  seeds: number;
  /** Two-sided level each comparison had to clear. Smaller than 0.05 on later mega attempts. */
  alpha: number;
  yoked: ArmTest;
  scrambled: ArmTest;
  specific: boolean;
  learnedReason: string;
  key: { ash: string; birch: string; cedar: string };
  voided: boolean;
};

export type DosePoint = { dose: number; gap: number; spec: number };

export type DoseCurve = {
  coupling: number;
  points: DosePoint[];
  rising: boolean;
  /** Paired sign test of dose 100 against dose 0 on the shared test seeds, once sealed. */
  trend: { pos: number; neg: number; p: number } | null;
  /** Level the trend test had to clear: the same α as the attempt's sign test. */
  alpha: number;
  learned: boolean;
  reason: string;
};

export type MegaStage = "search" | "confirm" | "naive" | "dose" | "done";

/** One sealed 64-seed attempt of a mega run, kept after later attempts replace `proof`. */
export type SealedAttempt = {
  attempt: number;
  alpha: number;
  label: string;
  specific: boolean;
  /** Naive retest outcome; null while not run. */
  naive: boolean | null;
  /** Dose-curve outcome; null while not run. */
  learned: boolean | null;
};

const PUBLISHED_SEEDS = 64;
const DOSE_TESTS = 16;
const DOSE_LIST = [0, 1, 10, 100];
const PROMOTE_GAP = 0.2;

type Candidate = {
  key: string;
  config: FieldConfig;
  preset: PresetId;
  gap: number;
  label: string;
};

type LadderMode = "confirm" | "naive" | "dose";

type Ladder = {
  mode: LadderMode;
  config: FieldConfig;
  /** The frozen recipe the ladder started from, carried unchanged into naive and dose. */
  source: FieldConfig;
  preset: PresetId;
  row: string;
  /** Pre-registered target shapes, fixed at the confirm stage and reused by every stage. */
  targets: number[];
  /** Level this stage's sign tests must clear. */
  alpha: number;
  index: number;
  total: number;
  diffsY: number[];
  diffsS: number[];
  specSum: number;
  gapSum: number;
  doseCursor: number;
  doses: number[];
  phase: "train" | "test";
  trainArchive: ArchiveEntry[];
  testCoupling: number;
  couplingSubstituted: boolean;
  points: DosePoint[];
  /** Field specificity per test seed at the current dose, in test-seed order. */
  seedSpecs: number[];
  /** seedSpecs for every sealed dose, paired by test seed. */
  specsByDose: number[][];
};

type AxisDef = { key: AxisKey; label: string; min: number; max: number; integer?: boolean };

export const AXES: AxisDef[] = [
  { key: "fieldStrength", label: "Field strength", min: 0, max: 1 },
  { key: "temporalDecay", label: "Temporal decay", min: 0, max: 0.4 },
  { key: "similarityThreshold", label: "Similarity", min: 0.4, max: 0.92 },
  { key: "influenceExponent", label: "Sharpen", min: 1, max: 4 },
  { key: "coupling", label: "Coupling", min: 0, max: 1 },
  { key: "density", label: "Soup density", min: 0.05, max: 0.55 },
  { key: "crystalCount", label: "Crystals", min: 6, max: 18, integer: true },
];

const CARD_CAP = 36;

export function axisValues(min: number, max: number, granPct: number, integer = false): number[] {
  const span = max - min;
  const raw = span * (granPct / 100);
  const step = integer ? Math.max(1, Math.round(raw)) : Math.max(0.001, raw);
  const values: number[] = [];
  for (let v = min; v <= max + step * 0.2; v += step) {
    const clamped = Math.min(max, Math.max(min, v));
    const n = integer ? Math.round(clamped) : Math.round(clamped * 1000) / 1000;
    if (!values.includes(n)) values.push(n);
    if (n >= max) break;
  }
  const last = integer ? Math.round(max) : Math.round(max * 1000) / 1000;
  if (values[values.length - 1] !== last) values.push(last);
  return values;
}

export function sizeValues(granPct: number): number[] {
  const step = Math.max(2, Math.round(((64 - 16) * granPct) / 100 / 2) * 2);
  const values: number[] = [];
  for (let n = 16; n <= 64; n += step) values.push(n);
  if (values[values.length - 1] !== 64) values.push(64);
  return [...new Set(values)];
}

const PRESET_ORDER: PresetId[] = ["soup", "garden", "gliders", "rpen", "acorn", "pulsar", "gun"];

const PRESET_LABEL: Record<PresetId, string> = {
  soup: "soup",
  garden: "garden",
  gliders: "gliders",
  rpen: "R-pentomino",
  acorn: "acorn",
  pulsar: "pulsar",
  gun: "gun",
};

export type LatticeDim = { key: string; values: (number | boolean | PresetId)[] };

export type MegaTally = {
  off: number;
  unarmed: number;
  armed: number;
  loud: number;
  bestGap: number;
  bestLabel: string;
};

export type MegaState = {
  on: boolean;
  done: bigint;
  total: bigint;
  tally: MegaTally;
  trace: { gap: number; rate: number }[];
  highlights: SweepCard[];
  recent: SweepCard[];
  phase: MegaPhase;
  hits: number;
  focus: string;
  stage: MegaStage;
  ladderDone: number;
  ladderTotal: number;
  proof: ConfirmResult | null;
  naive: ConfirmResult | null;
  dose: DoseCurve | null;
  frozen: string;
  trials: number;
  /** α the open (or next) 64-seed sign test must clear; see alphaForAttempt. */
  alpha: number;
  /** Every sealed attempt in this run, oldest first. Each Specific stays valid under α-spending. */
  sealed: SealedAttempt[];
  nextBar: number;
  queued: number;
};

/**
 * The mega walk's grid. Coupling is not an axis: the walk, the 64-seed test and the
 * naive retest all run with an empty archive, where coupling does nothing, so walking it
 * would only split one experiment into several "recipes" that each spend a test. It is
 * held at the baseline and only matters to the dose stage.
 */
export function megaLattice(granPct: number): { dims: LatticeDim[]; total: bigint } {
  const dims: LatticeDim[] = AXES.filter((axis) => axis.key !== "coupling").map((axis) => ({
    key: axis.key,
    values: axisValues(axis.min, axis.max, granPct, axis.integer),
  }));
  dims.push({ key: "cells", values: sizeValues(granPct) });
  dims.push({ key: "innate", values: [true, false] });
  dims.push({ key: "preset", values: PRESET_ORDER });
  let total = 1n;
  for (const dim of dims) total *= BigInt(Math.max(0, dim.values.length));
  return { dims, total };
}

export function formatCount(n: bigint): string {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function emptyTally(): MegaTally {
  return {
    off: 0,
    unarmed: 0,
    armed: 0,
    loud: 0,
    bestGap: Number.NEGATIVE_INFINITY,
    bestLabel: "",
  };
}

function round3(n: number): number {
  return Math.round(n * 1000) / 1000;
}

function normalize(config: FieldConfig): FieldConfig {
  return {
    ...config,
    fieldStrength: round3(config.fieldStrength),
    temporalDecay: round3(config.temporalDecay),
    similarityThreshold: round3(config.similarityThreshold),
    influenceExponent: round3(config.influenceExponent),
    crystalCount: Math.round(config.crystalCount),
    coupling: round3(config.coupling),
    density: round3(config.density),
    speed: Math.round(config.speed),
    cells: Math.round(config.cells),
    innate: Boolean(config.innate),
    wrap: Boolean(config.wrap),
  };
}

/**
 * The recipe a batch actually runs. Wrap follows the preset (the engine enforces it),
 * and density only paints soup, so for every other preset it is pinned. Two recipes
 * that differ only in an inert knob are the same experiment and get the same key.
 */
function canonicalFrozen(config: FieldConfig, preset: PresetId): FieldConfig {
  return normalize({
    ...config,
    wrap: presetWraps(preset),
    density: preset === "soup" ? config.density : DEFAULT_CONFIG.density,
  });
}

function frozenKey(config: FieldConfig, preset: PresetId): string {
  return `${configKey(canonicalFrozen(config, preset), 0)}:${preset}`;
}

/** Targets a frozen recipe is scored on. They depend on the table at generation 0, not the seed. */
function targetsFor(config: FieldConfig, preset: PresetId, archive: ArchiveEntry[]): number[] {
  return new MorphicLab(config.cells, archive, config, 1, preset).targets();
}

function configKey(config: FieldConfig, seed: number): string {
  const c = normalize(config);
  return [
    seed,
    c.cells,
    c.fieldStrength,
    c.temporalDecay,
    c.similarityThreshold,
    c.influenceExponent,
    c.crystalCount,
    c.coupling,
    c.density,
    c.innate ? 1 : 0,
    c.wrap ? 1 : 0,
  ].join(":");
}

function differs(config: FieldConfig, base: FieldConfig): string {
  const bits: string[] = [];
  const c = normalize(config);
  const b = normalize(base);
  if (c.fieldStrength !== b.fieldStrength) bits.push(`strength ${c.fieldStrength.toFixed(2)}`);
  if (c.temporalDecay !== b.temporalDecay) bits.push(`decay ${c.temporalDecay.toFixed(3)}`);
  if (c.similarityThreshold !== b.similarityThreshold)
    bits.push(`sim ${c.similarityThreshold.toFixed(2)}`);
  if (c.influenceExponent !== b.influenceExponent)
    bits.push(`sharpen ${c.influenceExponent.toFixed(1)}`);
  if (c.coupling !== b.coupling) bits.push(`coupling ${c.coupling.toFixed(2)}`);
  if (c.density !== b.density) bits.push(`density ${c.density.toFixed(2)}`);
  if (c.crystalCount !== b.crystalCount) bits.push(`${c.crystalCount} crystals`);
  if (c.cells !== b.cells) bits.push(`${c.cells}²`);
  if (c.innate !== b.innate) bits.push(c.innate ? "innate on" : "innate off");
  return bits.join(" · ");
}

function goalScore(rate: number, gap: number, goal: SeekGoal): number {
  if (goal === "gap") return gap;
  if (rate >= 0.01 && rate <= 0.12) return 2 - Math.abs(rate - 0.06) / 0.06;
  if (rate > 0.12) return 0.35 - Math.min(0.35, (rate - 0.12) * 2);
  return (rate / 0.01) * 0.5;
}

type Recipe = { config: FieldConfig; seed: number; label: string };

export class SweepRunner {
  status: "idle" | "running" | "paused" | "done" | "stopped" = "idle";
  cards: SweepCard[] = [];
  note = "Pick a walk, then start. Nothing here is a confirmatory result until you run that batch.";
  mode: SweepMode = "seek";
  goal: SeekGoal = "armed";
  generations = 80;
  granularity = 25;
  seedCount = 16;
  axes: AxisKey[] = ["fieldStrength", "similarityThreshold", "density"];
  sweepSize = true;
  sweepInnate = false;
  ignoreArchive = true;
  preset: PresetId = "soup";
  confirm: ConfirmResult | null = null;
  planned = 0;
  gen = 0;
  currentLabel = "";
  factorial = 0;
  limit = CARD_CAP;
  mega: MegaState | null = null;

  private queue: Recipe[] = [];
  private seen = new Set<string>();
  private lab: MorphicLab | null = null;
  private recipe: Recipe | null = null;
  private nextId = 1;
  private baseline: FieldConfig = { ...DEFAULT_CONFIG };
  private archive: ArchiveEntry[] = [];
  private illustrationSeed = 1;
  private bestGoal = -Infinity;
  private bestConfig: FieldConfig | null = null;
  private expandedFrom = "";
  private diffsY: number[] = [];
  private diffsS: number[] = [];
  private row = "";
  private megaDims: LatticeDim[] = [];
  private megaDigits: number[] = [];
  private megaSearch: MegaSearch | null = null;
  private bestPreset: PresetId = "garden";
  private bestGen = 0;
  private bestLabel = "";
  private ladder: Ladder | null = null;
  /** Confirmatory attempts opened in this mega run; the k-th spends alphaForAttempt(k). */
  private confirmAttempts = 0;
  private testedKeys = new Set<string>();
  private candidates: Candidate[] = [];
  private pass = 1;

  setPlan(plan: {
    mode: SweepMode;
    goal: SeekGoal;
    generations: number;
    granularity: number;
    seedCount: number;
    axes: AxisKey[];
    sweepSize: boolean;
    sweepInnate: boolean;
    ignoreArchive: boolean;
    preset: PresetId;
    baseline: FieldConfig;
    archive: ArchiveEntry[];
    seed: number;
    limit?: number;
  }) {
    this.mode = plan.mode;
    this.goal = plan.goal;
    this.generations = Math.max(20, Math.min(300, Math.round(plan.generations)));
    this.granularity = Math.max(1, Math.min(25, Math.round(plan.granularity)));
    this.seedCount = plan.seedCount;
    this.axes = plan.axes;
    this.sweepSize = plan.sweepSize;
    this.sweepInnate = plan.sweepInnate;
    this.ignoreArchive = plan.ignoreArchive;
    this.preset = plan.preset;
    this.limit = Math.max(4, Math.min(CARD_CAP, plan.limit ?? CARD_CAP));
    this.baseline = normalize({ ...plan.baseline, cells: plan.baseline.cells || 48 });
    this.archive = plan.archive;
    this.illustrationSeed = plan.seed >>> 0 || 1;
  }

  start() {
    this.dropMegaImages();
    this.mega = null;
    this.megaDims = [];
    this.megaDigits = [];
    this.megaSearch = null;
    this.cards = [];
    this.confirm = null;
    this.queue = [];
    this.seen.clear();
    this.lab = null;
    this.recipe = null;
    this.bestGoal = -Infinity;
    this.bestConfig = null;
    this.bestPreset = "garden";
    this.bestGen = 0;
    this.bestLabel = "";
    this.ladder = null;
    this.confirmAttempts = 0;
    this.testedKeys.clear();
    this.candidates = [];
    this.pass = 1;
    this.expandedFrom = "";
    this.diffsY = [];
    this.diffsS = [];
    this.gen = 0;
    this.status = "running";
    let base = this.baseline;
    if (this.mode === "confirm") {
      // Hash the recipe the seeds will actually run (wrap and inert density pinned).
      base = canonicalFrozen(base, this.preset);
      const archive = this.ignoreArchive ? [] : this.archive;
      const payload = JSON.stringify({
        version: ANALYSIS_VERSION,
        config: base,
        preset: this.preset,
        generations: this.generations,
        seeds: this.seedCount,
        archive: archive.map((entry) => ({
          mask: entry.mask,
          next: entry.nextMask,
          strength: round3(entry.strength),
        })),
      });
      this.row = sha256(payload);
      for (let i = 1; i <= this.seedCount; i++) {
        this.enqueue(base, seedFromRow(this.row, i), `Seed ${i}`);
      }
      this.planned = this.queue.length;
      this.factorial = this.seedCount;
      this.note = `Confirmatory batch. ${this.seedCount} seeds derived from the first row. Sliders are frozen.`;
    } else if (this.mode === "grid") {
      const built = buildGrid(base, this.axes, this.granularity, this.sweepSize, this.sweepInnate);
      this.factorial = built.product;
      for (const item of built.recipes)
        this.enqueue(item.config, this.illustrationSeed, item.label);
      this.planned = this.queue.length;
      this.note =
        built.product > built.recipes.length
          ? `A full factorial is ${built.product} cards. This walk runs ${built.recipes.length}, one axis at a time, so the page stays responsive.`
          : `Grid of ${built.recipes.length} recipes at a ${this.granularity}% step. Exploratory.`;
    } else {
      this.enqueue(base, this.illustrationSeed, "Start");
      this.planned = this.limit;
      this.factorial = this.limit;
      this.note = `Goal seek toward ${this.goal === "armed" ? "the armed band" : "a wider specificity gap"}. Step is ${this.granularity}% of each slider. Exploratory.`;
    }
  }

  startMega() {
    this.dropMegaImages();
    const lattice = megaLattice(this.granularity);
    const search = new MegaSearch(lattice.dims);
    this.cards = [];
    this.confirm = null;
    this.queue = [];
    this.seen.clear();
    this.lab = null;
    this.recipe = null;
    this.bestGoal = -Infinity;
    this.bestConfig = null;
    this.bestPreset = "garden";
    this.bestGen = 0;
    this.bestLabel = "";
    this.ladder = null;
    this.confirmAttempts = 0;
    this.testedKeys.clear();
    this.candidates = [];
    this.pass = 1;
    this.expandedFrom = "";
    this.diffsY = [];
    this.diffsS = [];
    this.gen = 0;
    this.planned = 0;
    this.factorial = 0;
    this.mode = "mega";
    this.ignoreArchive = true;
    this.megaDims = lattice.dims;
    this.megaDigits = [];
    this.megaSearch = search;
    this.mega = {
      on: true,
      done: 0n,
      total: lattice.total,
      tally: emptyTally(),
      trace: [],
      highlights: [],
      recent: [],
      phase: search.phase,
      hits: 0,
      focus: search.focus,
      stage: "search",
      ladderDone: 0,
      ladderTotal: 0,
      proof: null,
      naive: null,
      dose: null,
      frozen: "",
      trials: 0,
      alpha: alphaForAttempt(1),
      sealed: [],
      nextBar: PROMOTE_GAP,
      queued: 0,
    };
    this.status = "running";
    this.currentLabel = "";
    const ladderNote =
      "Every card runs to generation 80. An armed gap of 0.20 spends a 64-seed sign test. A miss does not end the walk, and running out of clusters does not end it either. It keeps going until a batch wins — Specific, then the naive retest and the dose curve — or until you stop it. Even that is not morphic resonance.";
    this.note = search.sampled
      ? `Mega run. The ${formatCount(lattice.total)}-cell grid at ${this.granularity}% is too fine to walk in order. It bounces the highest-scoring clusters of each pattern, then fans out around anything that scores. ${ladderNote}`
      : `Mega run. ${formatCount(lattice.total)} configurations exist at a ${this.granularity}% step. Clusters are sorted toward the armed band and the run bounces between patterns. A score fans out one step. ${ladderNote}`;
  }

  pause() {
    if (this.status === "running") this.status = "paused";
  }

  resume() {
    if (this.status === "paused") this.status = "running";
  }

  stop() {
    // A finished or already-stopped run has nothing open to void.
    if (this.status === "idle" || this.status === "done" || this.status === "stopped") return;
    this.status = "stopped";
    this.lab = null;
    this.queue = [];
    if (this.ladder && this.mega) {
      this.voidLadder();
      return;
    }
    if (this.mega) {
      this.mega.on = false;
      const sealed =
        this.mega.trials > 0
          ? ` ${this.mega.trials} published ${this.mega.trials === 1 ? "batch had" : "batches had"} already sealed.`
          : " The 64-seed sign test had not started.";
      this.note = `Stopped after ${formatCount(this.mega.done)} tries.${sealed} The reading at the top is the result. Loud is the table replacing Conway, not a finding.`;
      return;
    }
    if (this.mode === "confirm") this.sealConfirm(true);
    this.note = `Stopped at ${this.cards.length} ${this.cards.length === 1 ? "card" : "cards"}.`;
  }

  restart() {
    this.start();
  }

  tick(maxGens: number, deadline?: number) {
    if (this.status !== "running") return;
    let budget = maxGens;
    let stepped = 0;
    while (budget > 0 && this.status === "running") {
      if (deadline !== undefined && stepped > 0 && performance.now() >= deadline) return;
      if (!this.lab) {
        const more = this.mode === "mega" ? this.beginMega() : this.beginNext();
        if (!more) {
          this.status = "done";
          if (this.mega) {
            this.mega.on = false;
            if (this.mega.stage === "search") {
              this.mega.focus = "done";
              const covered = this.mega.done >= this.mega.total && this.mega.total > 0n;
              this.note = covered
                ? `Cluster search finished the grid (${formatCount(this.mega.done)} tries) before any armed gap was wide enough to freeze. The reading at the top is the result.`
                : `Cluster search finished after ${formatCount(this.mega.done)} tries. The reading at the top is the result.`;
            }
          } else if (this.mode === "confirm") this.sealConfirm(false);
          else this.note = `Finished ${this.cards.length} cards.`;
          return;
        }
      }
      const lab = this.lab;
      if (!lab) return;
      const target = this.mode === "mega" ? WINDOW_GENS : this.generations;
      const room = target - lab.gen;
      const chunk = this.mode === "mega" ? 8 : room;
      const step = Math.min(budget, room, chunk);
      for (let i = 0; i < step; i++) lab.step();
      budget -= step;
      stepped += step;
      this.gen = lab.gen;
      if (lab.gen >= target) {
        if (this.mode === "mega" && this.ladder) this.finishLadderSeed();
        else if (this.mode === "mega") this.finishMega();
        else this.finishCard();
      }
    }
  }

  private beginNext(): boolean {
    if (this.queue.length === 0) {
      if (this.mode !== "seek") return false;
      if (this.cards.length >= this.limit || !this.bestConfig) return false;
      const key = configKey(this.bestConfig, this.illustrationSeed);
      if (key === this.expandedFrom) return false;
      this.expandedFrom = key;
      const neighbors = neighborConfigs(
        this.bestConfig,
        this.axes,
        this.granularity,
        this.sweepSize,
        this.sweepInnate,
      );
      let added = 0;
      for (const config of neighbors) {
        if (this.cards.length + this.queue.length >= this.limit) break;
        const label = differs(config, this.baseline) || "neighbor";
        if (this.enqueue(config, this.illustrationSeed, label)) added++;
      }
      if (!added) return false;
    }
    const next = this.queue.shift();
    if (!next) return false;
    this.recipe = next;
    this.currentLabel = next.label;
    const archive = this.ignoreArchive ? [] : this.archive;
    this.lab = new MorphicLab(next.config.cells, archive, next.config, next.seed, this.preset);
    this.lab.playing = false;
    this.gen = 0;
    return true;
  }

  private finishCard() {
    const lab = this.lab;
    const recipe = this.recipe;
    if (!lab || !recipe) return;
    const snap = lab.snapshot();
    const goal = goalScore(snap.meanInfluence, snap.gap, this.goal);
    if (this.mode === "seek" && (this.bestConfig === null || goal > this.bestGoal)) {
      this.bestGoal = goal;
      this.bestConfig = recipe.config;
    }
    if (this.mode === "confirm") {
      this.diffsY.push(snap.specField - snap.specYoked);
      this.diffsS.push(snap.specField - snap.specScrambled);
    }
    this.cards.push({
      id: this.cards.length + 1,
      label: recipe.label,
      level: snap.provisional ? `${snap.level} · short` : snap.level,
      provisional: snap.provisional,
      flipRate: snap.meanInfluence,
      dStar: snap.dStar,
      gap: snap.gap,
      specField: snap.specField,
      specYoked: snap.specYoked,
      specScrambled: snap.specScrambled,
      gen: snap.gen,
      seed: snap.seed,
      cells: lab.w,
      image: snapshotBoards(lab),
      goal,
      config: { ...recipe.config },
    });
    this.lab = null;
    this.recipe = null;
  }

  adopted(): FieldConfig {
    return { ...(this.bestConfig ?? this.baseline) };
  }

  private beginMega(): boolean {
    const mega = this.mega;
    const search = this.megaSearch;
    if (!mega || !mega.on || !search) return false;
    if (this.ladder) return this.spawnLadderLab();
    if (this.shouldPromote()) {
      this.openConfirm();
      return this.spawnLadderLab();
    }
    let digits = search.next();
    let active: MegaSearch = search;
    if (!digits) {
      this.openNextPass();
      const restarted = this.megaSearch;
      digits = restarted?.next() ?? null;
      if (!digits || !restarted) return false;
      active = restarted;
    }
    this.megaDigits = digits;
    mega.phase = active.phase;
    mega.hits = active.hits;
    mega.focus = active.focus;
    const config: FieldConfig = { ...this.baseline };
    let preset: PresetId = this.preset;
    const bits: string[] = [];
    for (let d = 0; d < this.megaDims.length; d++) {
      const dim = this.megaDims[d];
      const value = dim.values[this.megaDigits[d]];
      switch (dim.key) {
        case "preset":
          preset = value as PresetId;
          bits.push(PRESET_LABEL[preset]);
          break;
        case "innate":
          config.innate = Boolean(value);
          bits.push(config.innate ? "innate on" : "innate off");
          break;
        case "cells":
          config.cells = Number(value);
          bits.push(`${config.cells}²`);
          break;
        case "fieldStrength":
          config.fieldStrength = Number(value);
          bits.push(`strength ${config.fieldStrength.toFixed(2)}`);
          break;
        case "temporalDecay":
          config.temporalDecay = Number(value);
          bits.push(`decay ${config.temporalDecay.toFixed(3)}`);
          break;
        case "similarityThreshold":
          config.similarityThreshold = Number(value);
          bits.push(`sim ${config.similarityThreshold.toFixed(2)}`);
          break;
        case "influenceExponent":
          config.influenceExponent = Number(value);
          bits.push(`sharpen ${config.influenceExponent.toFixed(2)}`);
          break;
        case "coupling":
          config.coupling = Number(value);
          bits.push(`coupling ${config.coupling.toFixed(2)}`);
          break;
        case "density":
          config.density = Number(value);
          bits.push(`density ${config.density.toFixed(2)}`);
          break;
        case "crystalCount":
          config.crystalCount = Number(value);
          bits.push(`${config.crystalCount} crystals`);
          break;
        default:
          break;
      }
    }
    const normalized = normalize(config);
    this.preset = preset;
    const label = bits.join(" · ");
    this.recipe = { config: normalized, seed: this.illustrationSeed, label };
    this.currentLabel = label;
    this.lab = new MorphicLab(normalized.cells, [], normalized, this.illustrationSeed, preset);
    this.lab.playing = false;
    this.gen = 0;
    return true;
  }

  private finishMega() {
    const lab = this.lab;
    const recipe = this.recipe;
    const mega = this.mega;
    if (!lab || !recipe || !mega) return;
    const snap = lab.snapshot();
    const level = snap.provisional ? `${snap.level} · short` : snap.level;
    if (level.startsWith("armed")) mega.tally.armed += 1;
    else if (level.startsWith("loud")) mega.tally.loud += 1;
    else if (level.startsWith("unarmed")) mega.tally.unarmed += 1;
    else mega.tally.off += 1;
    const armedCard = level.startsWith("armed");
    const improved = snap.gap > mega.tally.bestGap;
    if (improved) {
      mega.tally.bestGap = snap.gap;
      mega.tally.bestLabel = recipe.label;
    }
    if (armedCard && snap.gen >= WINDOW_GENS && snap.gap > this.bestGoal) {
      this.bestGoal = snap.gap;
      this.bestGen = snap.gen;
      this.bestPreset = this.preset;
      this.bestLabel = recipe.label;
      this.bestConfig = canonicalFrozen(recipe.config, this.preset);
    }
    if (armedCard && snap.gen >= WINDOW_GENS && snap.gap >= PROMOTE_GAP) {
      this.rememberCandidate(
        canonicalFrozen(recipe.config, this.preset),
        this.preset,
        snap.gap,
        recipe.label,
      );
    }
    mega.done += 1n;
    mega.trace.push({
      gap: Math.round(snap.gap * 1000) / 1000,
      rate: Math.round(snap.meanInfluence * 1000) / 1000,
    });
    if (mega.trace.length > 160) mega.trace.shift();
    const scored = level.startsWith("armed") || snap.gap > 0.05;
    const takePicture = scored || improved || mega.done % 6n === 1n;
    const card: SweepCard = {
      id: this.nextId++,
      label: recipe.label,
      level,
      provisional: snap.provisional,
      flipRate: snap.meanInfluence,
      dStar: snap.dStar,
      gap: snap.gap,
      specField: snap.specField,
      specYoked: snap.specYoked,
      specScrambled: snap.specScrambled,
      gen: snap.gen,
      seed: snap.seed,
      cells: lab.w,
      image: takePicture ? snapshotBoards(lab) : "",
      goal: snap.gap,
      config: { ...recipe.config },
    };
    mega.recent.push(card);
    if (scored || improved) {
      mega.highlights.push(card);
      const rank = (item: SweepCard) => item.gap + (item.level.startsWith("armed") ? 2 : 0);
      mega.highlights.sort((a, b) => rank(b) - rank(a));
      while (mega.highlights.length > 8) {
        const dropped = mega.highlights.pop();
        if (dropped && !mega.recent.includes(dropped)) dropped.image = "";
      }
    }
    while (mega.recent.length > 12) {
      const dropped = mega.recent.shift();
      if (dropped && !mega.highlights.includes(dropped)) dropped.image = "";
    }
    this.cards = dedupeCards(mega.highlights, mega.recent);
    this.lab = null;
    this.recipe = null;
    this.megaSearch?.observe(this.megaDigits, level, snap.gap);
    if (this.megaSearch) {
      mega.phase = this.megaSearch.phase;
      mega.hits = this.megaSearch.hits;
      mega.focus = this.megaSearch.focus;
    }
  }

  private shouldPromote(): boolean {
    return !this.ladder && !!this.mega && this.nextCandidate() !== null;
  }

  private nextCandidate(): Candidate | null {
    for (const candidate of this.candidates) {
      if (candidate.gap < PROMOTE_GAP) continue;
      if (this.testedKeys.has(candidate.key)) continue;
      return candidate;
    }
    return null;
  }

  private rememberCandidate(config: FieldConfig, preset: PresetId, gap: number, label: string) {
    if (gap < PROMOTE_GAP) return;
    const key = frozenKey(config, preset);
    if (this.testedKeys.has(key)) return;
    const existing = this.candidates.find((candidate) => candidate.key === key);
    if (existing) {
      if (gap > existing.gap) {
        existing.gap = gap;
        existing.label = label;
        existing.config = config;
      }
    } else {
      this.candidates.push({ key, config, preset, gap, label });
    }
    this.candidates.sort((a, b) => b.gap - a.gap);
    if (this.candidates.length > 32) this.candidates.length = 32;
    this.syncQueue();
  }

  private syncQueue() {
    if (!this.mega) return;
    this.mega.queued = this.candidates.length;
    this.mega.nextBar = PROMOTE_GAP;
  }

  private openNextPass() {
    const finished = this.pass;
    this.pass += 1;
    this.illustrationSeed =
      (Math.imul(this.illustrationSeed || 1, 1664525) + 1013904223) >>> 0 || 1;
    const search = new MegaSearch(
      this.megaDims,
      (this.illustrationSeed ^ Math.imul(this.pass, 0x9e3779b9)) >>> 0,
    );
    this.megaSearch = search;
    if (this.mega) {
      this.mega.on = true;
      this.mega.stage = "search";
      this.mega.phase = search.phase;
      this.mega.hits = search.hits;
      this.mega.focus = search.focus;
    }
    this.note = `Pass ${finished} ran out of new recipes. Pass ${this.pass} is starting from seed ${this.illustrationSeed}. Recipes that already failed a 64-seed test stay failed. The walk keeps going until a batch wins, or until you stop it. Not morphic resonance.`;
  }

  private openConfirm() {
    const candidate = this.nextCandidate();
    const mega = this.mega;
    if (!candidate || !mega) return;
    this.candidates = this.candidates.filter((item) => item.key !== candidate.key);
    this.syncQueue();
    this.confirmAttempts += 1;
    this.testedKeys.add(candidate.key);
    this.bestConfig = candidate.config;
    this.bestPreset = candidate.preset;
    this.bestLabel = candidate.label;
    this.bestGoal = candidate.gap;
    const preset = candidate.preset;
    const alpha = alphaForAttempt(this.confirmAttempts);
    const targets = targetsFor(candidate.config, preset, []);
    const row = rowHash("confirm", candidate.config, preset, {
      seeds: PUBLISHED_SEEDS,
      archive: [],
      attempt: this.confirmAttempts,
      alpha,
      targets,
    });
    this.ladder = freshLadder(
      "confirm",
      candidate.config,
      candidate.config,
      preset,
      row,
      PUBLISHED_SEEDS,
      targets,
      alpha,
    );
    mega.stage = "confirm";
    mega.alpha = alpha;
    mega.frozen = this.bestLabel;
    mega.ladderDone = 0;
    mega.ladderTotal = PUBLISHED_SEEDS;
    mega.focus = `64-seed sign test · 0/${PUBLISHED_SEEDS} · ${PRESET_LABEL[preset]}`;
    mega.naive = null;
    mega.dose = null;
    this.note = `Sign test ${this.confirmAttempts}, at α = ${formatAlpha(alpha)} (each further attempt in this run spends less, so all of them together stay under ${ALPHA}). Illustration frozen (armed gap ${this.bestGoal.toFixed(2)}). ${this.bestLabel}. Published 64-seed batch at generation ${WINDOW_GENS}, empty archive, seeds from the first-row hash — not seed ${this.illustrationSeed}. A miss returns to the search. This is not morphic resonance.`;
  }

  private spawnLadderLab(): boolean {
    const ladder = this.ladder;
    const mega = this.mega;
    if (!ladder || !mega) return false;
    const world = ladderWorld(ladder);
    const seed = ladderSeed(ladder);
    this.preset = ladder.preset;
    const label = mega.focus;
    this.recipe = { config: world.config, seed, label };
    this.currentLabel = label;
    this.lab = new MorphicLab(
      world.config.cells,
      world.archive,
      world.config,
      seed,
      ladder.preset,
      {
        targets: ladder.targets,
      },
    );
    this.lab.playing = false;
    this.gen = 0;
    return true;
  }

  private finishLadderSeed() {
    const lab = this.lab;
    const ladder = this.ladder;
    const mega = this.mega;
    if (!lab || !ladder || !mega) return;
    const training = ladder.mode === "dose" && ladder.phase === "train";
    if (training) {
      ladder.trainArchive = mergeArchive(ladder.trainArchive, lab.toArchive());
    } else {
      const snap = lab.snapshot();
      ladder.diffsY.push(snap.specField - snap.specYoked);
      ladder.diffsS.push(snap.specField - snap.specScrambled);
      ladder.specSum += snap.specField;
      if (ladder.mode === "dose") ladder.seedSpecs.push(snap.specField);
      ladder.gapSum += snap.gap;
    }
    this.lab = null;
    this.recipe = null;
    ladder.index += 1;
    mega.ladderDone = ladder.index;
    mega.ladderTotal = ladder.total;
    if (training) {
      mega.focus = doseFocus(ladder);
      if (ladder.index >= ladder.total) this.beginDoseTests();
      return;
    }
    if (ladder.index < ladder.total) {
      mega.focus = ladder.mode === "dose" ? doseFocus(ladder) : stageFocus(ladder);
      return;
    }
    if (ladder.mode === "confirm") this.sealConfirmLadder();
    else if (ladder.mode === "naive") this.sealNaiveLadder();
    else this.sealDosePoint();
  }

  private sealConfirmLadder() {
    const ladder = this.ladder;
    const mega = this.mega;
    if (!ladder || !mega) return;
    const result = makeConfirmResult(
      ladder.row,
      ladder.diffsY,
      ladder.diffsS,
      PUBLISHED_SEEDS,
      false,
      "The 64-seed sign test is sealed. Naive and the dose curve have not changed this sentence yet.",
      ladder.alpha,
    );
    result.learnedReason = result.specific
      ? "Specific on the frozen recipe. A naive retest is next: innate off, coupling 0, empty archive, 64 new seeds. This is not morphic resonance."
      : "The frozen recipe did not replicate. Field facilitation did not beat both nulls on 64 derived seeds. The naive retest and the dose curve were not run. This is not morphic resonance.";
    mega.proof = result;
    this.confirm = result;
    mega.trials += 1;
    mega.sealed.push({
      attempt: this.confirmAttempts,
      alpha: ladder.alpha,
      label: mega.frozen,
      specific: result.specific,
      naive: null,
      learned: null,
    });
    mega.alpha = alphaForAttempt(this.confirmAttempts + 1);
    mega.ladderDone = PUBLISHED_SEEDS;
    if (!result.specific) {
      this.resumeSearch(
        `Sign test ${mega.trials} did not replicate (armed gap ${this.bestGoal.toFixed(2)}). Both nulls were not beaten, so it is not Specific. The walk is still going. This is not morphic resonance.`,
      );
      return;
    }
    this.openNaive();
  }

  private openNaive() {
    const ladder = this.ladder;
    const mega = this.mega;
    if (!ladder || !mega) return;
    const config = normalize({ ...ladder.config, innate: false, coupling: 0 });
    const row = rowHash("naive", config, ladder.preset, {
      seeds: PUBLISHED_SEEDS,
      archive: [],
      targets: ladder.targets,
      from: ladder.row,
    });
    // Same α as the attempt's sign test: with every stage of attempt k at α_k, a false
    // Specific or a false Learned anywhere in the run stays under ALPHA.
    this.ladder = freshLadder(
      "naive",
      config,
      ladder.source,
      ladder.preset,
      row,
      PUBLISHED_SEEDS,
      ladder.targets,
      ladder.alpha,
    );
    mega.stage = "naive";
    mega.ladderDone = 0;
    mega.ladderTotal = PUBLISHED_SEEDS;
    mega.focus = `Naive 64 · innate off · coupling 0 · 0/${PUBLISHED_SEEDS}`;
    this.note =
      "The 64-seed test beat both nulls. That is still the table. Naive retest now: same recipe, innate forms off, coupling 0, empty archive, a new first row, scored on the same target forms. The table starts empty and can only learn echoes from the board. If this fails, the gap depended on habits that were already in the program.";
  }

  private sealNaiveLadder() {
    const ladder = this.ladder;
    const mega = this.mega;
    if (!ladder || !mega) return;
    const result = makeConfirmResult(
      ladder.row,
      ladder.diffsY,
      ladder.diffsS,
      PUBLISHED_SEEDS,
      false,
      "Naive retest: innate off, coupling 0, empty archive.",
      ladder.alpha,
    );
    result.learnedReason = result.specific
      ? "Naive retest passed with innate forms off, coupling 0, and an empty archive. The dose curve is next. This is not morphic resonance."
      : "Naive retest failed. Innate forms were off, coupling was 0, and the archive was empty. The illustration’s gap was not shown without those habits. Learned was not reached. This is not morphic resonance.";
    mega.naive = result;
    if (mega.proof) mega.proof.learnedReason = result.learnedReason;
    const sealed = mega.sealed[mega.sealed.length - 1];
    if (sealed) sealed.naive = result.specific;
    if (!result.specific) {
      this.resumeSearch(
        `Sign test ${mega.trials} was Specific, and the naive retest was not. Learned was not reached. The walk resumed. This is not morphic resonance.`,
      );
      return;
    }
    this.openDose();
  }

  private openDose() {
    const ladder = this.ladder;
    const mega = this.mega;
    if (!ladder || !mega) return;
    const frozenCoupling = ladder.source.coupling;
    const substituted = frozenCoupling <= 0.001;
    const testCoupling = substituted ? 0.25 : frozenCoupling;
    const config = normalize({ ...ladder.config, innate: false, coupling: 0 });
    const row = rowHash("dose", config, ladder.preset, {
      doses: DOSE_LIST,
      tests: DOSE_TESTS,
      testCoupling,
      targets: ladder.targets,
      from: ladder.row,
    });
    const first = DOSE_LIST[0];
    this.ladder = {
      ...freshLadder(
        "dose",
        config,
        ladder.source,
        ladder.preset,
        row,
        first === 0 ? DOSE_TESTS : first,
        ladder.targets,
        ladder.alpha,
      ),
      doseCursor: 0,
      doses: DOSE_LIST,
      phase: first === 0 ? "test" : "train",
      trainArchive: [],
      testCoupling,
      couplingSubstituted: substituted,
      points: [],
    };
    mega.stage = "dose";
    mega.ladderDone = 0;
    mega.ladderTotal = this.ladder.total;
    mega.focus = doseFocus(this.ladder);
    const why = substituted
      ? `Frozen coupling was ${frozenCoupling.toFixed(2)}, and coupling at 0 makes archive import a no-op, so dose tests use coupling ${testCoupling.toFixed(2)}.`
      : `Dose tests import the trained archive at the frozen coupling ${testCoupling.toFixed(2)}.`;
    mega.dose = {
      coupling: testCoupling,
      points: [],
      rising: false,
      trend: null,
      alpha: ladder.alpha,
      learned: false,
      reason: `Dose curve is running. Every dose is scored on the same ${DOSE_TESTS} test seeds, and no training seed is ever a test seed. ${why} Learned requires mean field specificity to rise strictly from dose 0 to 1 to 10 to 100, and dose 100 to beat dose 0 on the paired test seeds (exact sign test at α = ${formatAlpha(ladder.alpha)}). This is not morphic resonance.`,
    };
    this.note = mega.dose.reason;
  }

  private beginDoseTests() {
    const ladder = this.ladder;
    const mega = this.mega;
    if (!ladder || !mega) return;
    ladder.phase = "test";
    ladder.index = 0;
    ladder.total = DOSE_TESTS;
    ladder.specSum = 0;
    ladder.gapSum = 0;
    ladder.diffsY = [];
    ladder.diffsS = [];
    mega.ladderDone = 0;
    mega.ladderTotal = DOSE_TESTS;
    mega.focus = doseFocus(ladder);
  }

  private sealDosePoint() {
    const ladder = this.ladder;
    const mega = this.mega;
    if (!ladder || !mega || ladder.total === 0) return;
    const dose = ladder.doses[ladder.doseCursor] ?? 0;
    ladder.points.push({
      dose,
      spec: ladder.specSum / ladder.total,
      gap: ladder.gapSum / ladder.total,
    });
    ladder.specsByDose.push(ladder.seedSpecs);
    ladder.seedSpecs = [];
    const partial = doseReason(ladder, false);
    mega.dose = {
      coupling: ladder.testCoupling,
      points: ladder.points.map((point) => ({ ...point })),
      rising: false,
      trend: null,
      alpha: ladder.alpha,
      learned: false,
      reason: partial,
    };
    ladder.doseCursor += 1;
    if (ladder.doseCursor >= ladder.doses.length) {
      this.sealDoseCurve();
      return;
    }
    const next = ladder.doses[ladder.doseCursor];
    ladder.trainArchive = [];
    ladder.specSum = 0;
    ladder.gapSum = 0;
    ladder.diffsY = [];
    ladder.diffsS = [];
    ladder.index = 0;
    ladder.phase = next === 0 ? "test" : "train";
    ladder.total = next === 0 ? DOSE_TESTS : next;
    mega.ladderDone = 0;
    mega.ladderTotal = ladder.total;
    mega.focus = doseFocus(ladder);
    mega.stage = "dose";
  }

  private sealDoseCurve() {
    const ladder = this.ladder;
    const mega = this.mega;
    if (!ladder || !mega) return;
    const rising = curveRises(ladder.points);
    const trend = doseTrend(ladder);
    const trendPasses = trend.p < ladder.alpha && trend.pos > trend.neg;
    const learned = !!(mega.proof?.specific && mega.naive?.specific && rising && trendPasses);
    const reason = doseReason(ladder, learned, trend);
    mega.dose = {
      coupling: ladder.testCoupling,
      points: ladder.points.map((point) => ({ ...point })),
      rising,
      trend: { pos: trend.pos, neg: trend.neg, p: trend.p },
      alpha: ladder.alpha,
      learned,
      reason,
    };
    if (mega.proof) mega.proof.learnedReason = reason;
    const sealed = mega.sealed[mega.sealed.length - 1];
    if (sealed) sealed.learned = learned;
    if (learned) {
      this.endLadder(reason);
      return;
    }
    this.resumeSearch(`${reason} The walk resumed.`);
  }

  private resumeSearch(note: string) {
    const mega = this.mega;
    this.ladder = null;
    this.lab = null;
    this.recipe = null;
    if (mega) {
      mega.on = true;
      mega.stage = "search";
      mega.ladderDone = 0;
      mega.ladderTotal = 0;
      mega.nextBar = PROMOTE_GAP;
      mega.queued = this.candidates.length;
      if (this.megaSearch) {
        mega.phase = this.megaSearch.phase;
        mega.hits = this.megaSearch.hits;
        mega.focus = this.megaSearch.focus;
      }
    }
    this.status = "running";
    const waiting = this.candidates.length;
    const next =
      waiting > 0
        ? `${waiting} other armed ${waiting === 1 ? "recipe is" : "recipes are"} already waiting for a 64-seed test.`
        : `The next armed recipe at gap ${PROMOTE_GAP.toFixed(2)} or wider gets its own 64-seed test.`;
    this.note = `${note} The walk stays open until a batch wins, or until you stop it. ${next} Not morphic resonance.`;
  }

  private endLadder(note: string) {
    const mega = this.mega;
    this.ladder = null;
    this.lab = null;
    this.recipe = null;
    if (mega) {
      mega.on = false;
      mega.stage = "done";
      mega.focus = "ladder done";
      if (mega.ladderTotal > 0) mega.ladderDone = mega.ladderTotal;
    }
    this.note = note;
  }

  private voidLadder() {
    const ladder = this.ladder;
    const mega = this.mega;
    if (!ladder || !mega) return;
    const expected = ladder.mode === "dose" ? DOSE_TESTS : PUBLISHED_SEEDS;
    if (ladder.mode === "confirm" || ladder.mode === "naive") {
      const result = makeConfirmResult(
        ladder.row,
        ladder.diffsY,
        ladder.diffsS,
        expected,
        true,
        ladder.mode === "confirm"
          ? "Stopped before the 64 seeds finished. The batch is void. Naive and the dose curve were not run."
          : "Stopped before the naive 64 finished. That retest is void. Learned was not reached.",
        ladder.alpha,
      );
      if (ladder.mode === "confirm") {
        mega.proof = result;
        this.confirm = result;
      } else {
        mega.naive = result;
        if (mega.proof) {
          mega.proof.learnedReason =
            "The 64-seed test had already sealed. The naive retest was stopped early and is void, so Learned was not reached. This is not morphic resonance.";
        }
      }
    } else {
      mega.dose = {
        coupling: ladder.testCoupling,
        points: ladder.points.map((point) => ({ ...point })),
        rising: false,
        trend: null,
        alpha: ladder.alpha,
        learned: false,
        reason:
          "Stopped before the dose curve finished. The open dose is void. Learned was not reached. This is not morphic resonance.",
      };
      if (mega.proof) mega.proof.learnedReason = mega.dose.reason;
    }
    this.ladder = null;
    mega.on = false;
    mega.stage = "done";
    mega.focus = "stopped during the ladder";
    this.note = `Stopped during the ${ladder.mode} stage. An unfinished batch is void. The reading at the top is the result. Nothing here is morphic resonance.`;
  }

  private dropMegaImages() {
    if (!this.mega) return;
    for (const card of this.mega.highlights) card.image = "";
    for (const card of this.mega.recent) card.image = "";
    this.mega.highlights = [];
    this.mega.recent = [];
    this.mega.trace = [];
    this.mega.on = false;
  }

  private enqueue(config: FieldConfig, seed: number, label: string): boolean {
    const normalized = normalize(config);
    const key = configKey(normalized, seed);
    if (this.seen.has(key)) return false;
    this.seen.add(key);
    this.queue.push({ config: normalized, seed, label });
    return true;
  }

  private sealConfirm(voided: boolean) {
    const base = this.baseline;
    const archiveEmpty = this.ignoreArchive || this.archive.length === 0;
    const learnedReason =
      base.innate || !archiveEmpty || base.coupling > 0
        ? "Learned was not attempted. It needs innate forms off, an empty archive, coupling at 0, and a dose curve on seeds that are not these test seeds."
        : "The switches for Learned are set, but the dose curve — forms placed 0, 1, 10, and 100 times on disjoint training seeds — was not run. Learned is not reached.";
    this.confirm = makeConfirmResult(
      this.row,
      this.diffsY,
      this.diffsS,
      this.seedCount,
      voided,
      learnedReason,
      ALPHA,
    );
  }
}

function formatAlpha(alpha: number): string {
  return alpha >= 0.01 ? alpha.toFixed(3) : alpha.toPrecision(2);
}

function freshLadder(
  mode: LadderMode,
  config: FieldConfig,
  source: FieldConfig,
  preset: PresetId,
  row: string,
  total: number,
  targets: number[],
  alpha: number,
): Ladder {
  return {
    mode,
    config,
    source,
    preset,
    row,
    targets: targets.slice(),
    alpha,
    index: 0,
    total,
    diffsY: [],
    diffsS: [],
    specSum: 0,
    gapSum: 0,
    doseCursor: 0,
    doses: DOSE_LIST,
    phase: "test",
    trainArchive: [],
    testCoupling: config.coupling,
    couplingSubstituted: false,
    points: [],
    seedSpecs: [],
    specsByDose: [],
  };
}

/**
 * Seeds for a ladder stage. Confirm and naive use seeds 1…N of their own first row.
 * The dose stage keeps training and testing in separate named streams, so no training
 * seed can ever be a test seed, and scores every dose on the same test seeds (a paired
 * comparison across doses rather than four unrelated samples).
 */
export function ladderSeed(
  ladder: Pick<Ladder, "mode" | "phase" | "row" | "doses" | "doseCursor" | "index">,
): number {
  if (ladder.mode === "dose" && ladder.phase === "train") {
    const dose = ladder.doses[ladder.doseCursor] ?? 0;
    return seedFromRow(ladder.row, `train:${dose}:${ladder.index}`);
  }
  if (ladder.mode === "dose") return seedFromRow(ladder.row, `test:${ladder.index + 1}`);
  return seedFromRow(ladder.row, ladder.index + 1);
}

function ladderWorld(ladder: Ladder): { config: FieldConfig; archive: ArchiveEntry[] } {
  if (ladder.mode === "dose" && ladder.phase === "train") {
    return { config: normalize({ ...ladder.config, innate: false, coupling: 0 }), archive: [] };
  }
  if (ladder.mode === "dose") {
    return {
      config: normalize({ ...ladder.config, innate: false, coupling: ladder.testCoupling }),
      archive: ladder.trainArchive.map((entry) => ({ ...entry })),
    };
  }
  if (ladder.mode === "naive") {
    return { config: normalize({ ...ladder.config, innate: false, coupling: 0 }), archive: [] };
  }
  return { config: ladder.config, archive: [] };
}

function mergeArchive(into: ArchiveEntry[], extra: ArchiveEntry[]): ArchiveEntry[] {
  const merged = new Map<number, ArchiveEntry>();
  for (const entry of into) merged.set(entry.mask, { ...entry });
  for (const entry of extra) {
    const prev = merged.get(entry.mask);
    if (!prev || entry.strength > prev.strength) merged.set(entry.mask, { ...entry });
  }
  return [...merged.values()].sort((a, b) => b.strength - a.strength).slice(0, 24);
}

function rowHash(stage: string, config: FieldConfig, preset: PresetId, extra: unknown): string {
  return sha256(
    JSON.stringify({
      version: ANALYSIS_VERSION,
      stage,
      generations: WINDOW_GENS,
      preset,
      config: {
        fieldStrength: config.fieldStrength,
        temporalDecay: config.temporalDecay,
        similarityThreshold: config.similarityThreshold,
        influenceExponent: config.influenceExponent,
        coupling: config.coupling,
        density: config.density,
        crystalCount: config.crystalCount,
        cells: config.cells,
        innate: config.innate,
        wrap: config.wrap,
      },
      extra,
    }),
  );
}

function stageFocus(ladder: Ladder): string {
  if (ladder.mode === "naive")
    return `Naive 64 · innate off · coupling 0 · ${ladder.index}/${ladder.total}`;
  return `64-seed sign test · ${ladder.index}/${ladder.total} · ${PRESET_LABEL[ladder.preset]}`;
}

function doseFocus(ladder: Ladder): string {
  const dose = ladder.doses[ladder.doseCursor] ?? 0;
  const kind = ladder.phase === "train" ? "training" : "test";
  return `Dose ${dose} · ${kind} ${ladder.index}/${ladder.total}`;
}

/**
 * Dose 100 against dose 0, paired by test seed. A strict rise of four means happens about
 * 1 time in 24 with no dose effect at all, whatever α is, so Learned also needs this test.
 */
function doseTrend(ladder: Ladder): ReturnType<typeof signTest> {
  const low = ladder.specsByDose[0] ?? [];
  const high = ladder.specsByDose[ladder.specsByDose.length - 1] ?? [];
  const n = Math.min(low.length, high.length);
  const diffs: number[] = [];
  for (let i = 0; i < n; i++) diffs.push(high[i] - low[i]);
  return signTest(diffs);
}

function curveRises(points: DosePoint[]): boolean {
  if (points.length !== 4) return false;
  return (
    points[0].spec < points[1].spec &&
    points[1].spec < points[2].spec &&
    points[2].spec < points[3].spec
  );
}

function doseReason(ladder: Ladder, learned: boolean, trend?: ReturnType<typeof signTest>): string {
  const specs = ladder.points.map((point) => `${point.dose}→${point.spec.toFixed(3)}`).join(", ");
  const couplingNote = ladder.couplingSubstituted
    ? `Frozen coupling was 0, which makes archive import a no-op, so these dose tests used coupling ${ladder.testCoupling.toFixed(2)}.`
    : `Dose tests used coupling ${ladder.testCoupling.toFixed(2)}.`;
  const head = specs ? `Mean field specificity by dose: ${specs}. ` : "";
  const trendNote = trend
    ? ` Dose 100 against dose 0 on the paired test seeds: ${trend.pos} up, ${trend.neg} down, p ${trend.p < 0.001 ? "< 0.001" : trend.p.toFixed(3)} (needed α = ${formatAlpha(ladder.alpha)}).`
    : "";
  if (learned) {
    return `${head}${couplingNote}${trendNote} Both 64-seed tests were Specific, mean field specificity rose strictly with dose, and dose 100 beat dose 0 seed for seed. Learned, for this table, was reached. That is the table learning. It is not morphic resonance. Turn the field off and the boards lock.`;
  }
  if (ladder.points.length < 4) {
    return `${head}${couplingNote} The dose curve is not finished. Learned was not reached. This is not morphic resonance.`;
  }
  const rising = curveRises(ladder.points);
  const why = rising
    ? "Mean field specificity rose strictly, but dose 100 did not beat dose 0 on the paired seeds at the attempt's α."
    : "Mean field specificity did not rise strictly across doses 0, 1, 10, and 100.";
  return `${head}${couplingNote}${trendNote} ${why} Learned was not reached. This is not morphic resonance.`;
}

/**
 * Seal a paired batch. Specific needs every planned seed, and for each null an exact
 * two-sided sign test below `alpha` with more non-tied seeds favouring the field.
 * Requiring both nulls (an intersection–union test) keeps the overall level at `alpha`.
 */
export function makeConfirmResult(
  row: string,
  diffsY: number[],
  diffsS: number[],
  expected: number,
  voided: boolean,
  learnedReason: string,
  alpha: number = ALPHA,
): ConfirmResult {
  const yokedTest = signTest(diffsY);
  const scrambledTest = signTest(diffsS);
  const yokedCi = bootstrapMedianCI(diffsY, 400, 3);
  const scrambledCi = bootstrapMedianCI(diffsS, 400, 4);
  const favours = (test: ReturnType<typeof signTest>) =>
    test.p < alpha && test.pos > test.neg && test.median > 0;
  const specific =
    !voided &&
    diffsY.length === expected &&
    diffsS.length === expected &&
    expected > 0 &&
    favours(yokedTest) &&
    favours(scrambledTest);
  const arms = ["field", "yoked", "scrambled"];
  const rng = mulberry32(Number.parseInt(row.slice(0, 8), 16) || 1);
  for (let i = arms.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    const swap = arms[i];
    arms[i] = arms[j];
    arms[j] = swap;
  }
  return {
    row,
    seeds: diffsY.length,
    alpha,
    yoked: { ...yokedTest, lo: yokedCi.lo, hi: yokedCi.hi },
    scrambled: { ...scrambledTest, lo: scrambledCi.lo, hi: scrambledCi.hi },
    specific,
    learnedReason,
    key: { ash: arms[0], birch: arms[1], cedar: arms[2] },
    voided,
  };
}

function dedupeCards(highlights: SweepCard[], recent: SweepCard[]): SweepCard[] {
  const seen = new Set<number>();
  const out: SweepCard[] = [];
  for (const card of [...highlights, ...recent]) {
    if (seen.has(card.id)) continue;
    seen.add(card.id);
    out.push(card);
  }
  return out;
}

function thin<T>(values: T[], count: number): T[] {
  if (values.length <= count) return values;
  const out: T[] = [];
  for (let i = 0; i < count; i++) {
    const idx = Math.round((i * (values.length - 1)) / Math.max(1, count - 1));
    out.push(values[idx]);
  }
  return [...new Set(out)];
}

function buildGrid(
  base: FieldConfig,
  axes: AxisKey[],
  gran: number,
  sweepSize: boolean,
  sweepInnate: boolean,
): { product: number; recipes: { config: FieldConfig; label: string }[] } {
  const dims: { key: string; values: (number | boolean)[] }[] = [];
  for (const key of axes) {
    const axis = AXES.find((item) => item.key === key);
    if (!axis) continue;
    dims.push({ key, values: axisValues(axis.min, axis.max, gran, axis.integer) });
  }
  if (sweepSize) dims.push({ key: "cells", values: sizeValues(gran) });
  if (sweepInnate) dims.push({ key: "innate", values: [true, false] });
  const product = dims.reduce((prod, dim) => prod * Math.max(1, dim.values.length), 1);
  if (dims.length > 0 && product <= CARD_CAP) {
    let rows: FieldConfig[] = [base];
    for (const dim of dims) {
      const next: FieldConfig[] = [];
      for (const config of rows) {
        for (const value of dim.values) next.push(normalize({ ...config, [dim.key]: value }));
      }
      rows = next;
    }
    return {
      product,
      recipes: rows.map((config) => ({ config, label: differs(config, base) || "baseline" })),
    };
  }
  const recipes: { config: FieldConfig; label: string }[] = [{ config: base, label: "baseline" }];
  const room = Math.max(1, dims.length);
  const per = Math.max(1, Math.floor((CARD_CAP - 1) / room));
  for (const dim of dims) {
    for (const value of thin(dim.values, per)) {
      if (recipes.length >= CARD_CAP) break;
      const config = normalize({ ...base, [dim.key]: value });
      if (configKey(config, 0) === configKey(base, 0)) continue;
      recipes.push({ config, label: differs(config, base) || dim.key });
    }
  }
  return { product, recipes };
}

function neighborConfigs(
  config: FieldConfig,
  axes: AxisKey[],
  gran: number,
  sweepSize: boolean,
  sweepInnate: boolean,
): FieldConfig[] {
  const out: FieldConfig[] = [];
  const push = (patch: Partial<FieldConfig>) => {
    out.push(normalize({ ...config, ...patch }));
  };
  for (const key of axes) {
    const axis = AXES.find((item) => item.key === key);
    if (!axis) continue;
    const values = axisValues(axis.min, axis.max, gran, axis.integer);
    const current = config[key] as number;
    let index = 0;
    let best = Infinity;
    values.forEach((value, i) => {
      const distance = Math.abs(value - current);
      if (distance < best) {
        best = distance;
        index = i;
      }
    });
    if (index > 0) push({ [key]: values[index - 1] });
    if (index < values.length - 1) push({ [key]: values[index + 1] });
  }
  if (sweepSize) {
    const sizes = sizeValues(gran);
    let index = 0;
    let best = Infinity;
    sizes.forEach((value, i) => {
      const distance = Math.abs(value - config.cells);
      if (distance < best) {
        best = distance;
        index = i;
      }
    });
    if (index > 0) push({ cells: sizes[index - 1] });
    if (index < sizes.length - 1) push({ cells: sizes[index + 1] });
  }
  if (sweepInnate) push({ innate: !config.innate });
  return out;
}
