import type { LatticeDim } from "./sweep.ts";
import type { PresetId } from "./engine.ts";
import { mulberry32 } from "./protocol.ts";

export type MegaPhase = "scout" | "fan" | "grid";

const PRESET_SCORE: Record<string, number> = {
  garden: 36,
  gliders: 28,
  rpen: 26,
  acorn: 24,
  pulsar: 16,
  gun: 14,
  soup: 6,
};

const FIXED_KEYS = ["preset", "fieldStrength", "similarityThreshold", "cells", "innate"];
const INNER_CAP = 9;
const HOT_CAP = 240;
const FAN_QUIET_LIMIT = 28;
const BITSET_MAX = 8_000_000;

type Cluster = {
  base: number[];
  free: { dim: number; order: number[] }[];
  inner: number;
  innerLimit: number;
  score: number;
  preset: string;
};

/**
 * Orders a mega run so it does not grind the lattice from the low end of every slider.
 * Clusters are scored toward the armed band, bounced across patterns, and a score
 * (armed, or a gap over the nulls) fans out across every parameter within one step.
 */
export class MegaSearch {
  readonly total: bigint;
  readonly lengths: number[];
  readonly sampled: boolean;
  phase: MegaPhase = "scout";
  focus = "sorting clusters";
  hits = 0;
  private readonly dims: LatticeDim[];
  private readonly visited: Uint8Array | null;
  private readonly visitedKeys: Set<string> | null;
  private readonly clusters: Cluster[] = [];
  private readonly buckets: number[][] = [];
  private hot: { key: string; digits: number[]; score: number }[] = [];
  private pending = new Set<string>();
  private depth = 0;
  private rr = 0;
  private fanQuiet = 0;
  private maxDepth = 0;
  private bestGap = 0;
  private readonly rng: () => number;
  private gridMisses = 0;

  constructor(dims: LatticeDim[], salt = 1) {
    this.dims = dims;
    this.lengths = dims.map((dim) => Math.max(1, dim.values.length));
    let total = 1n;
    for (const n of this.lengths) total *= BigInt(n);
    this.total = total;
    const useBits = total > 0n && total <= BigInt(BITSET_MAX);
    this.visited = useBits ? new Uint8Array(Number(total)) : null;
    this.visitedKeys = useBits ? null : new Set();
    const built = buildClusters(dims);
    this.sampled = built.sampled;
    this.clusters = built.clusters;
    this.buckets = built.buckets;
    this.maxDepth = this.clusters.reduce((max, cluster) => Math.max(max, cluster.innerLimit), 0);
    this.rng = mulberry32((salt >>> 0) || 1);
    const lead = this.clusters[this.buckets[0]?.[0] ?? 0];
    if (lead) this.focus = `scout · ${labelOf(dims, lead.base)}`;
  }

  next(): number[] | null {
    for (let hop = 0; hop < 200_000; hop++) {
      if (this.hot.length > 0 && this.fanQuiet < FAN_QUIET_LIMIT) {
        const item = this.hot.pop();
        if (!item) return null;
        this.pending.delete(item.key);
        if (!this.mark(item.digits)) continue;
        this.phase = "fan";
        this.focus = `fan · ${labelOf(this.dims, item.digits)}`;
        return item.digits;
      }
      if (this.fanQuiet >= FAN_QUIET_LIMIT) {
        this.hot = [];
        this.pending.clear();
        this.fanQuiet = 0;
        this.phase = "scout";
      }
      const cluster = this.takeCluster();
      if (!cluster) {
        if (this.hot.length > 0) {
          this.fanQuiet = 0;
          continue;
        }
        const sampled = this.sampleUnvisited();
        if (sampled) return sampled;
        return null;
      }
      const digits = inflate(cluster, cluster.inner);
      cluster.inner += 1;
      if (!this.mark(digits)) continue;
      this.phase = "scout";
      this.focus = `scout · ${labelOf(this.dims, digits)}`;
      return digits;
    }
    return null;
  }

  observe(digits: number[], level: string, gap: number) {
    const armed = level.startsWith("armed");
    const loud = level.startsWith("loud");
    const gapHit = gap > 0.05;
    const scored = armed || gapHit;
    const fromFan = this.phase === "fan";
    if (fromFan) {
      if (scored) this.fanQuiet = 0;
      else this.fanQuiet += 1;
    }
    if (scored) this.hits += 1;
    const betterGap = gap > this.bestGap + 0.02 && gapHit;
    if (betterGap) this.bestGap = gap;
    // Fan once from a new cluster. Cards already inside a fan do not open another
    // ball unless the gap over the nulls actually improves — otherwise one armed
    // pocket would be ground forever and the other patterns would never run.
    const shouldFan = (!fromFan && (scored || loud)) || betterGap;
    if (!shouldFan) return;
    this.enqueueNeighborhood(digits, scored);
    this.phase = "fan";
    this.fanQuiet = 0;
    this.focus = `${betterGap ? "drill" : scored ? "fan" : "edge"} · ${labelOf(this.dims, digits)}`;
  }

  private sampleUnvisited(): number[] | null {
    const n = this.visited ? this.visited.length : 0;
    if (!this.visited || n === 0) return null;
    const emit = (index: number): number[] | null => {
      if (this.visited?.[index]) return null;
      const digits = indexToDigits(index, this.lengths);
      if (!this.mark(digits)) return null;
      if (this.strengthOff(digits)) return null;
      this.phase = "grid";
      this.gridMisses = 0;
      this.focus = `open grid · ${labelOf(this.dims, digits)}`;
      return digits;
    };
    for (let i = 0; i < 48; i++) {
      const found = emit(Math.floor(this.rng() * n));
      if (found) return found;
    }
    const start = Math.floor(this.rng() * n);
    for (let i = 0; i < 2500; i++) {
      const found = emit((start + i) % n);
      if (found) return found;
    }
    this.gridMisses += 1;
    return null;
  }

  private strengthOff(digits: number[]): boolean {
    const dim = this.dims.findIndex((item) => item.key === "fieldStrength");
    if (dim < 0) return false;
    return Number(this.dims[dim].values[digits[dim]]) < 0.2;
  }

  private takeCluster(): Cluster | null {
    const buckets = this.buckets;
    const n = buckets.length;
    if (n === 0) return null;
    while (this.depth < this.maxDepth) {
      for (let k = 0; k < n; k++) {
        const b = (this.rr + k) % n;
        const list = buckets[b];
        for (let i = 0; i < list.length; i++) {
          const cluster = this.clusters[list[i]];
          if (cluster.inner === this.depth && cluster.inner < cluster.innerLimit) {
            this.rr = (b + 1) % n;
            return cluster;
          }
        }
      }
      this.depth += 1;
    }
    return null;
  }

  private enqueueNeighborhood(center: number[], strong: boolean) {
    const add = (digits: number[]) => {
      const key = digits.join(",");
      if (this.pending.has(key) || this.already(digits)) return;
      this.pending.add(key);
      const score = scoreDigits(this.dims, digits) + (strong ? 1000 : 200);
      const row = { key, digits, score };
      let lo = 0;
      let hi = this.hot.length;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (this.hot[mid].score < score) lo = mid + 1;
        else hi = mid;
      }
      this.hot.splice(lo, 0, row);
    };
    const presetDim = this.dims.findIndex((dim) => dim.key === "preset");
    const strengthDim = this.dims.findIndex((dim) => dim.key === "fieldStrength");
    const simDim = this.dims.findIndex((dim) => dim.key === "similarityThreshold");
    for (let d = 0; d < center.length; d++) {
      if (d === presetDim) {
        for (let v = 0; v < this.lengths[d]; v++) {
          if (v === center[d]) continue;
          const next = center.slice();
          next[d] = v;
          add(next);
        }
        continue;
      }
      for (const delta of [-1, 1]) {
        const v = center[d] + delta;
        if (v < 0 || v >= this.lengths[d]) continue;
        const next = center.slice();
        next[d] = v;
        add(next);
      }
    }
    if (strong && strengthDim >= 0 && simDim >= 0) {
      for (let ds = -1; ds <= 1; ds++) {
        for (let dm = -1; dm <= 1; dm++) {
          if (ds === 0 && dm === 0) continue;
          const base = center.slice();
          if (!shift(base, strengthDim, ds, this.lengths) || !shift(base, simDim, dm, this.lengths)) continue;
          add(base.slice());
          for (const dim of this.dims.keys()) {
            if (dim === strengthDim || dim === simDim || dim === presetDim) continue;
            for (const delta of [-1, 1]) {
              const next = base.slice();
              if (!shift(next, dim, delta, this.lengths)) continue;
              add(next);
            }
          }
        }
      }
    }
    if (this.hot.length > HOT_CAP) {
      const dropped = this.hot.splice(0, this.hot.length - HOT_CAP);
      for (const item of dropped) this.pending.delete(item.key);
    }
  }

  private mark(digits: number[]): boolean {
    if (this.visited) {
      const index = digitsToIndex(digits, this.lengths);
      if (index < 0 || index >= this.visited.length || this.visited[index]) return false;
      this.visited[index] = 1;
      return true;
    }
    const key = digits.join(",");
    if (this.visitedKeys?.has(key)) return false;
    if (this.visitedKeys && this.visitedKeys.size < 200_000) this.visitedKeys.add(key);
    return true;
  }

  private already(digits: number[]): boolean {
    if (this.visited) {
      const index = digitsToIndex(digits, this.lengths);
      return index >= 0 && index < this.visited.length && this.visited[index] === 1;
    }
    return this.visitedKeys?.has(digits.join(",")) ?? false;
  }
}

export function scoreDigits(dims: LatticeDim[], digits: number[]): number {
  let score = 0;
  for (let i = 0; i < dims.length; i++) score += prefer(dims[i].key, dims[i].values[digits[i]]);
  return score;
}

function prefer(key: string, value: number | boolean | PresetId | undefined): number {
  if (value === undefined) return 0;
  if (key === "preset") return PRESET_SCORE[String(value)] ?? 0;
  if (key === "innate") return value ? 8 : 3;
  if (key === "cells") return 18 - Math.abs(Number(value) - 32) / 4;
  if (key === "fieldStrength") {
    const x = Number(value);
    if (x < 0.2) return -80;
    return 42 * Math.exp(-((x - 0.78) ** 2) / 0.08);
  }
  if (key === "similarityThreshold") {
    const x = Number(value);
    return 28 * Math.exp(-((x - 0.56) ** 2) / 0.02);
  }
  if (key === "temporalDecay") {
    const x = Number(value);
    return 10 * Math.exp(-(x * x) / 0.02);
  }
  if (key === "influenceExponent") {
    const x = Number(value);
    return 8 * Math.exp(-((x - 1.7) ** 2) / 0.8);
  }
  if (key === "coupling") {
    const x = Number(value);
    return 8 * Math.exp(-(x * x) / 0.15);
  }
  if (key === "density") {
    const x = Number(value);
    return 6 * Math.exp(-((x - 0.22) ** 2) / 0.02);
  }
  if (key === "crystalCount") {
    const x = Number(value);
    return 6 * Math.exp(-((x - 12) ** 2) / 18);
  }
  return 0;
}

function buildClusters(dims: LatticeDim[]): { clusters: Cluster[]; buckets: number[][]; sampled: boolean } {
  const fixed = FIXED_KEYS.map((key) => dims.findIndex((dim) => dim.key === key)).filter((index) => index >= 0);
  const freeIdx = dims.map((_, index) => index).filter((index) => !fixed.includes(index));
  let product = 1;
  for (const index of fixed) product *= dims[index].values.length;
  const sampled = product > 2500;
  const combos = sampled ? sampleFixed(dims, fixed) : enumerateFixed(dims, fixed);
  const free = freeIdx.map((dim) => ({
    dim,
    order: sortOrder(dims[dim]),
  }));
  const spread = free.reduce((prod, dim) => prod * Math.max(1, dim.order.length), 1);
  const innerLimit = Math.min(spread, INNER_CAP);
  const clusters: Cluster[] = [];
  for (const combo of combos) {
    const strengthDim = dims.findIndex((dim) => dim.key === "fieldStrength");
    if (strengthDim >= 0 && Number(dims[strengthDim].values[combo[strengthDim]]) < 0.2) continue;
    const base = combo.slice();
    for (const dim of free) base[dim.dim] = dim.order[0] ?? 0;
    const presetDim = dims.findIndex((dim) => dim.key === "preset");
    const preset = presetDim >= 0 ? String(dims[presetDim].values[base[presetDim]]) : "soup";
    clusters.push({
      base,
      free,
      inner: 0,
      innerLimit,
      score: scoreDigits(dims, base),
      preset,
    });
  }
  clusters.sort((a, b) => b.score - a.score);
  const presetOrder = Object.entries(PRESET_SCORE)
    .sort((a, b) => b[1] - a[1])
    .map(([name]) => name);
  const buckets: number[][] = presetOrder.map(() => []);
  for (let i = 0; i < clusters.length; i++) {
    const slot = presetOrder.indexOf(clusters[i].preset);
    buckets[slot >= 0 ? slot : buckets.length - 1].push(i);
  }
  for (const bucket of buckets) bucket.sort((a, b) => clusters[b].score - clusters[a].score);
  return { clusters, buckets: buckets.filter((bucket) => bucket.length > 0), sampled };
}

function enumerateFixed(dims: LatticeDim[], fixed: number[]): number[][] {
  let rows: number[][] = [dims.map(() => 0)];
  for (const dim of fixed) {
    const next: number[][] = [];
    for (const row of rows) {
      for (let v = 0; v < dims[dim].values.length; v++) {
        const copy = row.slice();
        copy[dim] = v;
        next.push(copy);
      }
    }
    rows = next;
  }
  return rows;
}

function sampleFixed(dims: LatticeDim[], fixed: number[]): number[][] {
  const picks = fixed.map((dim) => {
    const key = dims[dim].key;
    const order = sortOrder(dims[dim]);
    const keep = key === "preset" || key === "innate" ? order.length : key === "fieldStrength" ? 4 : key === "cells" ? 2 : 3;
    return { dim, values: order.slice(0, keep) };
  });
  let rows: number[][] = [dims.map(() => 0)];
  for (const pick of picks) {
    const next: number[][] = [];
    for (const row of rows) {
      for (const value of pick.values) {
        const copy = row.slice();
        copy[pick.dim] = value;
        next.push(copy);
      }
    }
    rows = next;
  }
  return rows;
}

function sortOrder(dim: LatticeDim): number[] {
  const order = dim.values.map((_, index) => index);
  order.sort((a, b) => prefer(dim.key, dim.values[b]) - prefer(dim.key, dim.values[a]));
  return order;
}

function inflate(cluster: Cluster, inner: number): number[] {
  const digits = cluster.base.slice();
  let x = inner;
  for (let i = cluster.free.length - 1; i >= 0; i--) {
    const order = cluster.free[i].order;
    const len = Math.max(1, order.length);
    digits[cluster.free[i].dim] = order[x % len] ?? order[0] ?? 0;
    x = Math.floor(x / len);
  }
  return digits;
}

function shift(digits: number[], dim: number, delta: number, lengths: number[]): boolean {
  if (dim < 0 || delta === 0) return delta === 0 ? true : false;
  const v = digits[dim] + delta;
  if (v < 0 || v >= lengths[dim]) return false;
  digits[dim] = v;
  return true;
}

function digitsToIndex(digits: number[], lengths: number[]): number {
  let x = 0;
  for (let i = 0; i < digits.length; i++) x = x * lengths[i] + digits[i];
  return x;
}

function indexToDigits(index: number, lengths: number[]): number[] {
  const digits = new Array<number>(lengths.length);
  let x = index;
  for (let i = lengths.length - 1; i >= 0; i--) {
    const len = Math.max(1, lengths[i]);
    digits[i] = x % len;
    x = Math.floor(x / len);
  }
  return digits;
}

function labelOf(dims: LatticeDim[], digits: number[]): string {
  const bits: string[] = [];
  for (let i = 0; i < dims.length; i++) {
    const key = dims[i].key;
    const value = dims[i].values[digits[i]];
    if (key === "preset") bits.push(String(value));
    else if (key === "fieldStrength") bits.push(`strength ${Number(value).toFixed(2)}`);
    else if (key === "similarityThreshold") bits.push(`sim ${Number(value).toFixed(2)}`);
  }
  return bits.join(" · ");
}
