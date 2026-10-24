/**
 * Pre-registered analysis for the isolation rig. Its SHA-256 is committed in the
 * registrar's log before any block runs, so it cannot be edited after seeing data.
 *
 * Design: every block trains exactly one of K forms (balanced, order drawn from OS
 * entropy and sealed). The tester counts all K forms in every block without knowing
 * which one was trained. Under the null hypothesis the counts do not depend on the
 * assignment, so re-drawing the assignment gives an exact randomization test.
 *
 * T1 (primary, block-locked): mean over blocks of log((n[b, target] + ½) / (u[target] + ½)),
 *   where u[f] is form f's mean count over the blocks in which f was not trained.
 *   Positive when trained forms are over-represented in the very block that trained
 *   them; exp(T1) − 1 estimates the relative increase.
 * T2 (secondary, cumulative dose): mean over forms of the correlation, across blocks,
 *   between how many times the form has been trained so far and log(n[b, f] + ½).
 *   Positive when a form becomes more common as its training accumulates.
 * One-sided p = (1 + #{T* ≥ T}) / (B + 1); Holm across T1 and T2.
 */
import { mulberry32 } from "../src/sim/protocol.ts";

export type BlockCounts = { block: number; target: string; counts: Record<string, number> };

export type Report = {
  blocks: number;
  forms: string[];
  t1: { stat: number; p: number; effect: number; ci: [number, number]; nullQ95: number; mde80: number };
  t2: { stat: number; p: number };
  holm: { t1: number; t2: number };
  alpha: number;
  detected: boolean;
  perForm: { form: string; trained: number; untrained: number; ratio: number; timesTrained: number }[];
};

export function analyze(
  forms: string[],
  rows: BlockCounts[],
  opts: { permutations: number; bootstrap: number; alpha: number; seed: number },
): Report {
  const blocks = rows.slice().sort((a, b) => a.block - b.block);
  const counts = blocks.map((row) => forms.map((f) => row.counts[f] ?? 0));
  const targetIdx = blocks.map((row) => forms.indexOf(row.target));
  if (targetIdx.some((i) => i < 0)) throw new Error("a block's target is not one of the forms");
  const logs = counts.map((c) => c.map((n) => Math.log(n + 0.5)));

  /** Block-locked statistic for an assignment, against each form's untrained-block mean. */
  const t1For = (rows: number[], targets: number[]) => {
    const sum = forms.map(() => 0);
    const k = forms.map(() => 0);
    rows.forEach((b, i) => {
      for (let f = 0; f < forms.length; f++) {
        if (targets[i] === f) continue;
        sum[f] += counts[b][f];
        k[f] += 1;
      }
    });
    const u = sum.map((s, f) => (k[f] ? s / k[f] : 0));
    return mean(rows.map((b, i) => Math.log((counts[b][targets[i]] + 0.5) / (u[targets[i]] + 0.5))));
  };
  const all = blocks.map((_, b) => b);
  const t1 = (targets: number[]) => t1For(all, targets);
  const t2 = (targets: number[]) => {
    const dose = forms.map(() => 0);
    const doses: number[][] = [];
    targets.forEach((t) => {
      dose[t] += 1;
      doses.push(dose.slice());
    });
    return mean(forms.map((_, f) => pearson(doses.map((d) => d[f]), logs.map((row) => row[f]))));
  };

  const observed1 = t1(targetIdx);
  const observed2 = t2(targetIdx);
  const rng = mulberry32(opts.seed >>> 0 || 1);
  const perm = targetIdx.slice();
  const null1: number[] = [];
  let ge1 = 0;
  let ge2 = 0;
  for (let i = 0; i < opts.permutations; i++) {
    shuffle(perm, rng);
    const s1 = t1(perm);
    null1.push(s1);
    if (s1 >= observed1 - 1e-12) ge1++;
    if (t2(perm) >= observed2 - 1e-12) ge2++;
  }
  const p1 = (1 + ge1) / (opts.permutations + 1);
  const p2 = (1 + ge2) / (opts.permutations + 1);
  null1.sort((a, b) => a - b);
  const q95 = null1[Math.min(null1.length - 1, Math.floor(0.95 * null1.length))] ?? 0;
  const sd = Math.sqrt(mean(null1.map((v) => v * v)) - mean(null1) ** 2);

  // Percentile bootstrap over blocks for the size of the block-locked effect.
  const boot: number[] = [];
  for (let i = 0; i < opts.bootstrap; i++) {
    const pick = blocks.map(() => Math.floor(rng() * blocks.length));
    boot.push(t1For(pick, pick.map((b) => targetIdx[b])));
  }
  boot.sort((a, b) => a - b);
  const lo = boot[Math.floor(0.025 * (boot.length - 1))] ?? observed1;
  const hi = boot[Math.ceil(0.975 * (boot.length - 1))] ?? observed1;

  const holm = holm2(p1, p2);
  return {
    blocks: blocks.length,
    forms,
    t1: {
      stat: observed1,
      p: p1,
      effect: Math.expm1(observed1),
      ci: [Math.expm1(lo), Math.expm1(hi)],
      nullQ95: Math.expm1(q95),
      // 80% power for the decision actually used: Holm's worst case tests T1 at α/2, so
      // z(1 − α/2) + z(0.8) null standard deviations (2.80 at α = 0.05).
      mde80: Math.expm1((normalQuantile(1 - opts.alpha / 2) + 0.8416212335729143) * sd),
    },
    t2: { stat: observed2, p: p2 },
    holm,
    alpha: opts.alpha,
    detected: holm.t1 < opts.alpha,
    perForm: forms.map((form, f) => {
      const trained = counts.filter((_, b) => targetIdx[b] === f).map((c) => c[f]);
      const untrained = counts.filter((_, b) => targetIdx[b] !== f).map((c) => c[f]);
      const a = mean(trained);
      const u = mean(untrained);
      return { form, trained: a, untrained: u, ratio: u > 0 ? a / u : NaN, timesTrained: trained.length };
    }),
  };
}

/** Inverse standard normal CDF (Acklam's rational approximation; error about 1e-9). */
function normalQuantile(p: number): number {
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239];
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572];
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416];
  const lo = 0.02425;
  if (p < lo) {
    const q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p > 1 - lo) return -normalQuantile(1 - p);
  const q = p - 0.5;
  const r = q * q;
  return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

function holm2(p1: number, p2: number): { t1: number; t2: number } {
  const [lo, hi] = p1 <= p2 ? [p1, p2] : [p2, p1];
  const a = Math.min(1, 2 * lo);
  const b = Math.min(1, Math.max(a, hi));
  return p1 <= p2 ? { t1: a, t2: b } : { t1: b, t2: a };
}

function mean(xs: number[]): number {
  if (xs.length === 0) return 0;
  let s = 0;
  for (const x of xs) s += x;
  return s / xs.length;
}

function pearson(x: number[], y: number[]): number {
  const mx = mean(x);
  const my = mean(y);
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (let i = 0; i < x.length; i++) {
    sxy += (x[i] - mx) * (y[i] - my);
    sxx += (x[i] - mx) ** 2;
    syy += (y[i] - my) ** 2;
  }
  return sxx > 0 && syy > 0 ? sxy / Math.sqrt(sxx * syy) : 0;
}

function shuffle(a: number[], rng: () => number) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    const t = a[i];
    a[i] = a[j];
    a[j] = t;
  }
}
