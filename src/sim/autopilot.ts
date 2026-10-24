import { DEFAULT_CONFIG, type FieldConfig, type PresetId } from "./engine.ts";
import { suggestNextSweep, type SweepSuggestion } from "@/lib/suggest-sweep";
import type { AxisKey, SeekGoal, SweepMode, SweepRunner } from "./sweep.ts";

export type CampaignPlan = {
  name: string;
  mode: SweepMode;
  goal: SeekGoal;
  preset: PresetId;
  generations: number;
  granularity: number;
  seedCount: number;
  axes: AxisKey[];
  sweepSize: boolean;
  sweepInnate: boolean;
  limit: number;
  baseline: FieldConfig;
  why: string;
};

export type CampaignRecord = {
  name: string;
  reading: string;
  specific: boolean | null;
  seeds: number;
  preset: PresetId;
  config: FieldConfig;
};

function garden(patch: Partial<FieldConfig> = {}): FieldConfig {
  return {
    ...DEFAULT_CONFIG,
    fieldStrength: 0.84,
    similarityThreshold: 0.52,
    coupling: 0,
    innate: true,
    density: 0.22,
    cells: 32,
    crystalCount: 12,
    temporalDecay: 0.06,
    influenceExponent: 1.5,
    speed: 12,
    wrap: false,
    ...patch,
  };
}

export class Autopilot {
  on = false;
  busy = false;
  index = 0;
  grokCalls = 0;
  reason = "";
  grokStatus = "";
  campaign = "";
  log: CampaignRecord[] = [];
  best: FieldConfig = garden();

  reset() {
    this.on = false;
    this.busy = false;
    this.index = 0;
    this.grokCalls = 0;
    this.reason = "";
    this.grokStatus = "";
    this.campaign = "";
    this.log = [];
    this.best = garden();
  }

  first(): CampaignPlan {
    this.reset();
    this.on = true;
    const plan = this.playbook(0);
    this.campaign = plan.name;
    return plan;
  }

  capture(runner: SweepRunner, name: string): CampaignRecord {
    const cards = runner.cards;
    const confirm = runner.confirm;
    const armed = cards.filter((card) => card.level.startsWith("armed")).length;
    const loud = cards.filter((card) => card.level.startsWith("loud")).length;
    const bestGap = cards.reduce((best, card) => Math.max(best, card.gap), 0);
    const config = runner.adopted();
    this.best = config;
    let reading: string;
    let specific: boolean | null = null;
    if (runner.mode === "confirm" && confirm) {
      specific = confirm.specific;
      if (confirm.voided) reading = "stopped early";
      else if (confirm.specific && confirm.seeds >= 64) reading = "Specific on 64 seeds";
      else if (confirm.specific) reading = `short batch passed (${confirm.seeds} seeds)`;
      else reading = `did not beat both nulls (${confirm.seeds} seeds)`;
    } else {
      reading = `${armed} armed, ${loud} loud, best gap ${bestGap.toFixed(2)}`;
    }
    return { name, reading, specific, seeds: confirm?.seeds ?? 0, preset: runner.preset, config };
  }

  async advance(runner: SweepRunner) {
    if (this.busy || !this.on || runner.status !== "done") return;
    this.busy = true;
    try {
      const record = this.capture(runner, this.campaign || "Sweep");
      this.log.push(record);
      const decision = this.decide(record);
      if ("stop" in decision) {
        this.on = false;
        this.reason = decision.stop;
        this.campaign = "";
        return;
      }
      let plan: CampaignPlan;
      if ("grok" in decision) {
        this.grokCalls += 1;
        const response = await suggestNextSweep({ data: { journal: this.journal() } });
        if (response.ok) {
          plan = this.planFromGrok(response.plan);
          this.grokStatus = response.plan.note;
        } else {
          this.grokStatus = response.error;
          plan = this.fallback();
        }
      } else {
        plan = decision.plan;
      }
      this.campaign = plan.name;
      this.reason = plan.why;
      const savedSeed = 1000 + Math.floor(Math.random() * 80000);
      runner.setPlan({
        mode: plan.mode,
        goal: plan.goal,
        generations: plan.generations,
        granularity: plan.granularity,
        seedCount: plan.seedCount,
        axes: plan.axes,
        sweepSize: plan.sweepSize,
        sweepInnate: plan.sweepInnate,
        ignoreArchive: true,
        preset: plan.preset,
        baseline: plan.baseline,
        archive: [],
        seed: savedSeed,
        limit: plan.limit,
      });
      runner.start();
    } finally {
      this.busy = false;
    }
  }

  decide(record: CampaignRecord): { plan: CampaignPlan } | { grok: true } | { stop: string } {
    if (record.specific && record.seeds >= 64) {
      return {
        stop: "The published 64-seed batch was Specific. Autopilot stops. Morphic resonance was not found — the result measures the table.",
      };
    }
    if (record.specific && record.seeds >= 16) {
      return { plan: this.confirmPlan(record.config, record.preset, 64, "Published 64-seed freeze") };
    }
    this.index += 1;
    if ((this.index === 4 || this.index === 7) && this.grokCalls < 2) return { grok: true };
    if (this.index > 8) {
      return {
        stop: "Autopilot finished the playbook without a 64-seed Specific result. Morphic resonance was not found.",
      };
    }
    return { plan: this.playbook(this.index) };
  }

  planFromGrok(suggestion: SweepSuggestion): CampaignPlan {
    const baseline = garden({
      fieldStrength: suggestion.fieldStrength,
      similarityThreshold: suggestion.similarityThreshold,
      coupling: suggestion.coupling,
      innate: suggestion.innate,
      cells: suggestion.cells,
      density: suggestion.density,
    });
    this.best = baseline;
    return this.confirmPlan(baseline, suggestion.preset, 16, "Grok's freeze");
  }

  fallback(): CampaignPlan {
    return this.playbook(Math.min(this.index, 8));
  }

  journal(): string {
    const lines = this.log.map((item) => `${item.name}: ${item.reading} (preset ${item.preset})`);
    return `Campaigns so far:\n${lines.join("\n")}\nBest field strength ${this.best.fieldStrength}, similarity ${this.best.similarityThreshold}, cells ${this.best.cells}, innate ${this.best.innate}.`;
  }

  private confirmPlan(config: FieldConfig, preset: PresetId, seeds: number, name: string): CampaignPlan {
    return {
      name,
      mode: "confirm",
      goal: "gap",
      preset,
      generations: 80,
      granularity: 25,
      seedCount: seeds,
      axes: [],
      sweepSize: false,
      sweepInnate: false,
      limit: seeds,
      baseline: { ...config, coupling: 0 },
      why:
        seeds >= 64
          ? "A shorter batch favored the field. This is the published seed list."
          : "Freeze one recipe and test the shape against both nulls.",
    };
  }

  private playbook(index: number): CampaignPlan {
    const best = this.best;
    if (index <= 0) {
      return {
        name: "Arm a still garden",
        mode: "seek",
        goal: "armed",
        preset: "garden",
        generations: 80,
        granularity: 25,
        seedCount: 8,
        axes: ["fieldStrength", "similarityThreshold"],
        sweepSize: true,
        sweepInnate: false,
        limit: 8,
        baseline: garden(),
        why: "Isolated still lifes can be counted. First get the table writing in the 1–12% band.",
      };
    }
    if (index === 1) {
      return {
        name: "Widen the garden gap",
        mode: "seek",
        goal: "gap",
        preset: "garden",
        generations: 80,
        granularity: 25,
        seedCount: 8,
        axes: ["similarityThreshold", "fieldStrength", "crystalCount"],
        sweepSize: true,
        sweepInnate: false,
        limit: 8,
        baseline: best,
        why: "Stay near the recipe that armed, and walk toward a larger specificity gap.",
      };
    }
    if (index === 2) {
      return this.confirmPlan(best, "garden", 16, "Freeze the garden");
    }
    if (index === 3) {
      return this.confirmPlan(garden({ ...best, innate: false, coupling: 0 }), "garden", 16, "Garden with innate forms off");
    }
    if (index === 4) {
      return this.confirmPlan(
        garden({ ...best, similarityThreshold: 0.48, innate: true, coupling: 0 }),
        "acorn",
        16,
        "Acorn, a different seed pattern",
      );
    }
    if (index === 5) {
      return {
        name: "Glider flock",
        mode: "seek",
        goal: "gap",
        preset: "gliders",
        generations: 80,
        granularity: 25,
        seedCount: 8,
        axes: ["similarityThreshold", "fieldStrength"],
        sweepSize: true,
        sweepInnate: false,
        limit: 8,
        baseline: garden({ ...best, cells: 40, innate: true }),
        why: "Gliders move. A different census, same question.",
      };
    }
    if (index === 6) {
      return this.confirmPlan(this.best, "gliders", 16, "Freeze the gliders");
    }
    if (index === 7) {
      return this.confirmPlan(garden({ ...best, cells: 28, coupling: 0 }), "pulsar", 16, "Pulsar, in case the census was the wrong one");
    }
    return {
      name: "Small R-pentomino",
      mode: "seek",
      goal: "armed",
      preset: "rpen",
      generations: 80,
      granularity: 25,
      seedCount: 8,
      axes: ["fieldStrength", "similarityThreshold"],
      sweepSize: false,
      sweepInnate: true,
      limit: 8,
      baseline: garden({ cells: 24, similarityThreshold: 0.48, fieldStrength: 0.9 }),
      why: "Last local try: a small board, where eight samples a generation can actually move the rate.",
    };
  }
}
