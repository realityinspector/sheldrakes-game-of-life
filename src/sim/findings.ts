import type { HabitCandidate, PresetId, RunSnapshot } from "./engine.ts";

export const RULES = {
  driftGens: 40,
  driftDeadline: 80,
  driftMean: 0.08,
  crowdGens: 80,
  crowdDeadline: 140,
  crowdRatio: 1.12,
  settleGens: 80,
  settleDeadline: 160,
  settleRatio: 0.65,
  settleMinDiverge: 0.05,
  settleMinControl: 4,
  loudGens: 40,
  loudAbove: 0.12,
  measuredGens: 50,
  measuredLo: 0.01,
  measuredHi: 0.12,
  quietGens: 60,
  quietBelow: 0.01,
  quietMinStrength: 0.2,
  habitCalls: 6,
  habitRate: 0.6,
  window: 80,
} as const;

const WINDOW = RULES.window;

export type FindingKind =
  | "drift"
  | "drift-no"
  | "crowd-up"
  | "crowd-flat"
  | "settled"
  | "settled-no"
  | "measured"
  | "quiet"
  | "loud"
  | "habit"
  | "armed"
  | "unarmed"
  | "off"
  | "dstar"
  | "gap";

export type Finding = {
  id: string;
  kind: FindingKind;
  claim: string;
  detail: string;
  seed: number;
  preset: PresetId;
  generation: number;
  filedAt: number;
  times: number;
  evidence: Record<string, number>;
  mask?: number;
  name?: string;
};

export type Trial = {
  id: string;
  at: number;
  reason: "checkpoint" | "close";
  seed: number;
  preset: PresetId;
  generation: number;
  fieldStrength: number;
  threshold: number;
  coupling: number;
  meanInfluence: number;
  meanDiverge: number;
  dStar?: number;
  gap?: number;
  level?: string;
  maxPopM: number;
  maxPopC: number;
  popM: number;
  popC: number;
  habits: number;
};

export type Book = {
  version: 1;
  findings: Finding[];
  trials: Trial[];
  runKey: string;
  filedThisRun: string[];
};

export type ReviewMode = "checkpoint" | "close";

export type FreshFinding = { finding: Finding; repeat: boolean };

export type Question = {
  id: string;
  title: string;
  rule: string;
  stake: string;
  state: "open" | "filed";
  meter: number;
  reading: string;
};

export type ResonanceVerdict = "off" | "unarmed" | "armed" | "loud" | "window";

export type ResonanceChip = {
  id: string;
  label: string;
  value: string;
  hint: string;
  tone: "paid" | "ready" | "short" | "miss" | "note";
};

export type Resonance = {
  verdict: ResonanceVerdict;
  title: string;
  line: string;
  meter: number;
  thisRun: number;
  ledger: number;
  chips: ResonanceChip[];
};

const KEY = "sheldrake.findings.v1";

export function emptyBook(): Book {
  return { version: 1, findings: [], trials: [], runKey: "", filedThisRun: [] };
}

export function loadBook(): Book {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return emptyBook();
    const parsed = JSON.parse(raw) as Book;
    if (!parsed || parsed.version !== 1 || !Array.isArray(parsed.findings)) return emptyBook();
    return {
      version: 1,
      findings: parsed.findings.filter((item) => item && typeof item.id === "string" && item.claim),
      trials: Array.isArray(parsed.trials) ? parsed.trials.filter((item) => item && item.id) : [],
      runKey: typeof parsed.runKey === "string" ? parsed.runKey : "",
      filedThisRun: Array.isArray(parsed.filedThisRun) ? parsed.filedThisRun : [],
    };
  } catch {
    return emptyBook();
  }
}

export function saveBook(book: Book) {
  try {
    localStorage.setItem(KEY, JSON.stringify(book));
  } catch {
    /* quota — the live run still files in memory */
  }
}

export function review(
  book: Book,
  snap: RunSnapshot,
  mode: ReviewMode,
): { book: Book; fresh: FreshFinding[] } {
  const next: Book = {
    version: 1,
    findings: book.findings.map((item) => ({ ...item, evidence: { ...item.evidence } })),
    trials: book.trials.slice(),
    runKey: book.runKey,
    filedThisRun: book.filedThisRun.slice(),
  };
  const key = String(snap.runId);
  if (next.runKey !== key) {
    next.runKey = key;
    next.filedThisRun = [];
  }

  const fresh: FreshFinding[] = [];
  const file = (
    id: string,
    kind: FindingKind,
    claim: string,
    detail: string,
    evidence: Record<string, number>,
    extra?: { mask?: number; name?: string },
  ) => {
    if (next.filedThisRun.includes(id)) {
      const prior = next.findings.find((item) => item.id === id);
      if (prior) {
        prior.detail = detail;
        prior.generation = snap.gen;
        prior.seed = snap.seed;
        prior.preset = snap.preset;
        prior.evidence = evidence;
      }
      return;
    }
    next.filedThisRun.push(id);
    const existing = next.findings.find((item) => item.id === id);
    if (existing) {
      existing.times += 1;
      existing.detail = detail;
      existing.generation = snap.gen;
      existing.seed = snap.seed;
      existing.preset = snap.preset;
      existing.evidence = evidence;
      existing.filedAt = Date.now();
      fresh.push({ finding: existing, repeat: true });
      return;
    }
    const created: Finding = {
      id,
      kind,
      claim,
      detail,
      seed: snap.seed,
      preset: snap.preset,
      generation: snap.gen,
      filedAt: Date.now(),
      times: 1,
      evidence,
      mask: extra?.mask,
      name: extra?.name,
    };
    next.findings.unshift(created);
    fresh.push({ finding: created, repeat: false });
  };

  const mean = snap.dStar;
  const influence = snap.meanInfluence;
  const ratio = snap.maxPopM / Math.max(1, snap.maxPopC);

  if (snap.gen >= RULES.crowdGens && ratio >= RULES.crowdRatio) {
    file(
      "crowd-up",
      "crowd-up",
      "Memory raised the crowd.",
      `Peak field population ${snap.maxPopM} versus control ${snap.maxPopC} (${ratio.toFixed(2)}×) by generation ${snap.gen}.`,
      { maxPopM: snap.maxPopM, maxPopC: snap.maxPopC, ratio: round(ratio) },
    );
  } else if (snap.gen >= RULES.crowdDeadline && !next.filedThisRun.includes("crowd-up")) {
    file(
      "crowd-flat",
      "crowd-flat",
      "Memory did not raise the crowd.",
      `Peak field population ${snap.maxPopM} versus control ${snap.maxPopC} (${ratio.toFixed(2)}×) at generation ${snap.gen}. A lift needs ${RULES.crowdRatio.toFixed(2)}×.`,
      { maxPopM: snap.maxPopM, maxPopC: snap.maxPopC, ratio: round(ratio) },
    );
  }

  if (snap.gen >= RULES.settleGens && settled(snap)) {
    file(
      "settled",
      "settled",
      "Memory settled early.",
      `Late population swing was ${Math.round(snap.settleM)} on the field and ${Math.round(snap.settleC)} on the control. D* at that point was ${snap.dStar.toFixed(2)}, which is not a score.`,
      { settleM: round(snap.settleM), settleC: round(snap.settleC), meanDiverge: round(mean) },
    );
  } else if (snap.gen >= RULES.settleDeadline && !next.filedThisRun.includes("settled")) {
    file(
      "settled-no",
      "settled-no",
      "Memory did not settle early.",
      `Field swing ${Math.round(snap.settleM)} versus control ${Math.round(snap.settleC)} at generation ${snap.gen}. No premature calm.`,
      { settleM: round(snap.settleM), settleC: round(snap.settleC) },
    );
  }

  if (snap.gen >= WINDOW && !next.filedThisRun.includes("level")) {
    const level = snap.level;
    file(
      "level",
      level,
      levelClaim(level),
      levelDetail(snap),
      {
        meanInfluence: round(influence),
        dStar: round(snap.dStar),
        gap: round(snap.gap),
        generations: snap.gen,
      },
    );
  }

  if (snap.gen >= WINDOW && !next.filedThisRun.includes("dstar")) {
    file(
      "dstar",
      "dstar",
      "D* is on the record, and it is not a score.",
      `D* is ${snap.dStar.toFixed(2)} at generation ${snap.gen}. First effective flip at ${snap.firstFlipGen < 0 ? "none" : `generation ${snap.firstFlipGen}`}. D* first reached 0.5 at ${snap.halfDStarGen < 0 ? "not yet" : `generation ${snap.halfDStarGen}`}.`,
      { dStar: round(snap.dStar), firstFlip: snap.firstFlipGen, halfDStar: snap.halfDStarGen },
    );
  }

  for (const habit of snap.habits) {
    const calls = habit.activations;
    if (calls < RULES.habitCalls) continue;
    const rate = habit.successes / calls;
    if (rate < RULES.habitRate) continue;
    file(
      `habit:${habit.mask}`,
      "habit",
      `${habit.name} earned a place in memory.`,
      `${habit.name} was right ${pct(rate)} of ${calls} calls and is kept for later runs.`,
      { rate: round(rate), activations: calls, strength: round(habit.strength) },
      { mask: habit.mask, name: habit.name },
    );
  }

  if (mode === "checkpoint" || mode === "close") {
    const id = `${snap.seed}:${snap.preset}:${snap.gen}:${mode}`;
    if (snap.gen >= 15 && !next.trials.some((trial) => trial.id === id)) {
      next.trials.unshift({
        id,
        at: Date.now(),
        reason: mode,
        seed: snap.seed,
        preset: snap.preset,
        generation: snap.gen,
        fieldStrength: round(snap.fieldStrength),
        threshold: round(snap.similarityThreshold),
        coupling: round(snap.coupling),
        meanInfluence: round(influence),
        meanDiverge: round(snap.meanDiverge),
        dStar: round(snap.dStar),
        gap: round(snap.gap),
        level: snap.level,
        maxPopM: snap.maxPopM,
        maxPopC: snap.maxPopC,
        popM: snap.popM,
        popC: snap.popC,
        habits: snap.habits.length,
      });
    }
  }

  if (next.findings.length > 80) next.findings.length = 80;
  if (next.trials.length > 200) next.trials.length = 200;
  return { book: next, fresh };
}

export function questions(snap: RunSnapshot, filed: string[]): Question[] {
  const rate = snap.meanInfluence;
  const ratio = snap.maxPopM / Math.max(1, snap.maxPopC);
  const levelFiled = filed.includes("level");
  const crowdFiled = filed.includes("crowd-up") || filed.includes("crowd-flat");
  const settleFiled = filed.includes("settled") || filed.includes("settled-no");
  const habitCount = filed.filter((id) => id.startsWith("habit:")).length;
  const best = bestHabit(snap.habits);
  const band =
    snap.level === "loud"
      ? "above 12% — loud"
      : snap.level === "armed"
        ? "inside 1–12%"
        : snap.level === "off"
          ? "field under 0.20 and silent"
          : "under 1%";

  return [
    {
      id: "level",
      title: "Is the memory term the right size?",
      stake: "level",
      rule: "Scored once, at generation 80. Armed means 1–12% of consulted occupied neighborhoods were rewritten. That says the table is writing. It is not a finding of resonance. Loud, above 12%, means the table is replacing Conway.",
      state: levelFiled ? "filed" : "open",
      meter: levelFiled ? 1 : Math.min(1, snap.gen / WINDOW),
      reading: snap.provisional
        ? `Window open. ${pct(rate)} of consulted neighborhoods · ${band}.`
        : `${labelLevel(snap.level)}. ${pct(rate)} of consulted neighborhoods.`,
    },
    {
      id: "dstar",
      title: "How far did the field leave the control?",
      stake: "note",
      rule: "D* divides raw disagreement by the disagreement expected of two unrelated boards at those densities. 1 means as different as chance. It is recorded, including the generation of the first flip and the generation D* first reaches 0.5. It is not a pass.",
      state: filed.includes("dstar") ? "filed" : "open",
      meter: Math.max(0, Math.min(1, snap.dStar)),
      reading: `D* ${snap.dStar.toFixed(2)} · raw disagreement ${pct(snap.meanDiverge)} · board-wide flips ${pct(snap.boardShare)}.`,
    },
    {
      id: "crowd",
      title: "Did memory raise the crowd?",
      stake: "note",
      rule: `Noted, not scored. The field's peak population reaching ${RULES.crowdRatio.toFixed(2)}× the control after generation ${RULES.crowdGens} is a side effect.`,
      state: crowdFiled ? "filed" : "open",
      meter: crowdFiled ? 1 : Math.min(snap.gen / RULES.crowdGens, ratio / RULES.crowdRatio),
      reading: `Peak field ${snap.maxPopM} / control ${snap.maxPopC} (${ratio.toFixed(2)}×).`,
    },
    {
      id: "settle",
      title: "Did memory settle early?",
      stake: "note",
      rule: "Noted, not scored. Early calm is a late swing under 65% of the control. It does not pay.",
      state: settleFiled ? "filed" : "open",
      meter: settleFiled ? 1 : Math.min(1, snap.gen / RULES.settleGens),
      reading:
        snap.settleC === 0
          ? "Not enough generations yet to measure swing."
          : `Field swing ${Math.round(snap.settleM)} · control swing ${Math.round(snap.settleC)}.`,
    },
    {
      id: "gap",
      title: "Does the remembered shape beat the nulls?",
      stake: "illustration",
      rule: "One seed cannot say Specific. The gap is field specificity minus the better of yoked and scrambled. Specific needs that gap positive on a pre-registered batch, both comparisons, sign test α = 0.05. Run it from the Sweep tab.",
      state: "open",
      meter: Math.max(0, Math.min(1, (snap.gap + 0.2) / 0.4)),
      reading: `Gap ${snap.gap.toFixed(3)} · field ${snap.specField.toFixed(3)} · yoked ${snap.specYoked.toFixed(3)} · scrambled ${snap.specScrambled.toFixed(3)}.`,
    },
    {
      id: "habit",
      title: "Is the table growing?",
      stake: "kept",
      rule: "Kept, not scored. A learned crystal is filed when it is right at least 60% of the time across 6 or more calls. A growing table is not a form that arrived from outside the table.",
      state: habitCount > 0 ? "filed" : "open",
      meter: habitCount > 0 ? 1 : best.meter,
      reading: habitCount > 0 ? `${habitCount} kept. ${best.reading}` : best.reading,
    },
  ];
}

export function pointsFor(kind: FindingKind): number {
  void kind;
  return 0;
}

export function scoreResonance(book: Book, snap: RunSnapshot | null, _filed: string[]): Resonance {
  const armedRuns = book.findings.find((item) => item.kind === "armed")?.times ?? 0;
  if (!snap) {
    return {
      verdict: "window",
      title: "Window open",
      line: "Waiting for the run.",
      meter: 0,
      thisRun: 0,
      ledger: armedRuns,
      chips: [
        { id: "flips", label: "Flips", value: "—", hint: "consulted", tone: "short" },
        { id: "dstar", label: "D*", value: "—", hint: "not a score", tone: "note" },
        { id: "gap", label: "Gap", value: "—", hint: "one seed", tone: "note" },
      ],
    };
  }

  const verdict: ResonanceVerdict = snap.provisional && snap.level !== "off" ? "window" : snap.level;
  const title =
    verdict === "window" ? "Window open" : verdict === "armed" ? "Armed" : verdict === "loud" ? "Loud" : verdict === "off" ? "Off" : "Unarmed";
  const rate = snap.meanInfluence;
  let line: string;
  if (verdict === "off") {
    line = "Field strength is under 0.20 and nothing was rewritten. The test was never switched on.";
  } else if (verdict === "window") {
    line = `Scored at generation 80, not before. So far ${pct(rate)} of consulted neighborhoods were rewritten. This seed is a demonstration.`;
  } else if (verdict === "armed") {
    line = `The table rewrote ${pct(rate)} of the neighborhoods it read. The term is alive and the right size. That is not morphic resonance.`;
  } else if (verdict === "loud") {
    line = `The table rewrote ${pct(rate)} of the neighborhoods it read. Above 12% it is replacing Conway, not biasing it.`;
  } else {
    line = `The table rewrote ${pct(rate)} of the neighborhoods it read. Under 1% the term is not armed. The rate is among the eight patches read each generation, not the whole board.`;
  }
  if (snap.exploratory) line += " This run was touched after generation 0, so it cannot enter a confirmatory ledger.";

  return {
    verdict,
    title,
    line,
    meter: verdict === "window" ? Math.min(1, snap.gen / WINDOW) : verdict === "off" ? 0 : Math.min(1, rate / 0.12),
    thisRun: 0,
    ledger: armedRuns,
    chips: [
      {
        id: "flips",
        label: "Flips",
        value: pct(rate),
        hint: verdict === "armed" ? "1–12%" : verdict === "loud" ? "above 12%" : "of consulted",
        tone: verdict === "armed" ? "ready" : verdict === "loud" ? "paid" : "short",
      },
      { id: "dstar", label: "D*", value: snap.dStar.toFixed(2), hint: "descriptive only", tone: "note" },
      { id: "gap", label: "Gap", value: snap.gap.toFixed(2), hint: "not a batch", tone: "note" },
    ],
  };
}

export function exportDocument(book: Book) {
  return {
    lab: "Sheldrake",
    note: "This laboratory does not score morphic resonance. Armed means the table rewrote 1–12% of the neighborhoods it consulted over generations 1–80. Loud is above 12%. Off is a field under 0.20 that never wrote. Unarmed is everything else. D*, crowd, settle, and kept forms are a trail, not a score. Specific and Learned are batch results and are not awarded here.",
    summary: ledgerDigest(book),
    armedRuns: book.findings.find((item) => item.kind === "armed")?.times ?? 0,
    rules: {
      armed: "Mean share of consulted occupied neighborhoods rewritten, generations 1–80, is between 1% and 12%.",
      loud: "That share is above 12%.",
      off: "Field strength under 0.20 and no effective flips in generations 1–80.",
      dStar: "Descriptive. Not a pass condition.",
      habit: `A learned form is kept when it is right ≥ ${RULES.habitRate} across ≥ ${RULES.habitCalls} calls`,
      specific:
        "Batch only. Field specificity exceeds yoked and scrambled, paired exact sign test, two-sided, α = 0.05 for one pre-registered batch. A mega run spends α = 0.05·6/(π²k²) on its k-th attempt, so all attempts together stay under 0.05.",
    },
    exportedAt: new Date().toISOString(),
    findings: book.findings,
    trials: book.trials,
  };
}

export function ledgerDigest(book: Book): string {
  if (book.findings.length === 0 && book.trials.length === 0) {
    return "Nothing filed yet. A single seed can reach Armed. It cannot reach Specific.";
  }
  const times = (kind: string) => book.findings.filter((item) => item.kind === kind).reduce((sum, item) => sum + item.times, 0);
  const habits = book.findings.filter((item) => item.kind === "habit");
  const kept =
    habits.length === 0
      ? "No form has earned a permanent place yet."
      : `${habits.length} ${habits.length === 1 ? "form" : "forms"} kept: ${habits
          .slice(0, 8)
          .map((item) => item.name ?? "echo")
          .join(", ")}.`;
  return [
    `Levels on the ledger: armed ${times("armed")}, loud ${times("loud")}, unarmed ${times("unarmed")}, off ${times("off")}.`,
    "None of those is a detection of morphic resonance.",
    `The crowd rose in ${times("crowd-up")} and stayed flat in ${times("crowd-flat")}.`,
    `Early settle: ${times("settled")} yes, ${times("settled-no")} no.`,
    kept,
    `${book.trials.length} trial ${book.trials.length === 1 ? "row" : "rows"} in the log.`,
  ].join(" ");
}

export function findingsCsv(book: Book): string {
  const header = [
    "claim",
    "kind",
    "points",
    "scored",
    "times",
    "detail",
    "seed",
    "preset",
    "generation",
    "name",
    "mask",
    "filedAt",
  ];
  const lines = book.findings.map((finding) =>
    [
      csv(finding.claim),
      finding.kind,
      pointsFor(finding.kind),
      pointsFor(finding.kind) * finding.times,
      finding.times,
      csv(finding.detail),
      finding.seed,
      finding.preset,
      finding.generation,
      csv(finding.name ?? ""),
      finding.mask ?? "",
      new Date(finding.filedAt).toISOString(),
    ].join(","),
  );
  return [header.join(","), ...lines].join("\n");
}

export function trialsCsv(book: Book): string {
  const header = [
    "at",
    "reason",
    "seed",
    "preset",
    "generation",
    "fieldStrength",
    "threshold",
    "coupling",
    "meanInfluence",
    "meanDiverge",
    "maxPopField",
    "maxPopControl",
    "finalField",
    "finalControl",
    "learnedForms",
  ];
  const lines = book.trials.map((trial) =>
    [
      new Date(trial.at).toISOString(),
      trial.reason,
      trial.seed,
      trial.preset,
      trial.generation,
      trial.fieldStrength,
      trial.threshold,
      trial.coupling,
      trial.meanInfluence,
      trial.meanDiverge,
      trial.maxPopM,
      trial.maxPopC,
      trial.popM,
      trial.popC,
      trial.habits,
    ].join(","),
  );
  return [header.join(","), ...lines].join("\n");
}

function csv(value: string): string {
  if (/[",\n]/.test(value)) return `"${value.replaceAll('"', '""')}"`;
  return value;
}

function settled(snap: RunSnapshot): boolean {
  return (
    snap.settleC >= RULES.settleMinControl &&
    snap.settleM <= snap.settleC * RULES.settleRatio &&
    snap.meanDiverge >= RULES.settleMinDiverge
  );
}

function labelLevel(level: RunSnapshot["level"]): string {
  if (level === "armed") return "Armed";
  if (level === "loud") return "Loud";
  if (level === "off") return "Off";
  return "Unarmed";
}

function levelClaim(level: RunSnapshot["level"]): string {
  if (level === "armed") return "Armed. The table is writing, and that is not resonance.";
  if (level === "loud") return "Loud. The table is replacing Conway.";
  if (level === "off") return "Off. The test was never switched on.";
  return "Unarmed. The table did not write enough.";
}

function levelDetail(snap: RunSnapshot): string {
  return `${labelLevel(snap.level)} at generation ${snap.gen}. ${pct(snap.meanInfluence)} of consulted neighborhoods rewritten, D* ${snap.dStar.toFixed(2)}, gap ${snap.gap.toFixed(3)} (seed ${snap.seed}). A single seed is a demonstration.`;
}

function bestHabit(habits: HabitCandidate[]): { meter: number; reading: string } {
  let meter = 0;
  let reading = "No learned form yet.";
  for (const habit of habits) {
    const rate = habit.activations ? habit.successes / habit.activations : 0;
    const score = Math.min(habit.activations / RULES.habitCalls, rate / RULES.habitRate);
    if (score >= meter) {
      meter = score;
      reading = `${habit.name}: ${habit.activations} calls, ${pct(rate)} right`;
    }
  }
  return { meter: Math.max(0, Math.min(1, meter)), reading };
}

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function round(n: number): number {
  return Math.round(n * 1000) / 1000;
}
