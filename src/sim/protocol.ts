/** Published rules for the morphic laboratory. Analysis version is hashed into every confirmatory row. */

export const ANALYSIS_VERSION = "2026-10-23.dice8";

export const PATCH = 5;
export const PATCH_CELLS = 25;
export const CENTER_BIT = 12;
export const CENTER3 =
  (1 << 6) | (1 << 7) | (1 << 8) | (1 << 11) | (1 << 12) | (1 << 13) | (1 << 16) | (1 << 17) | (1 << 18);

export const WINDOW_GENS = 80;
export const SAMPLES_PER_GEN = 8;
export const ARMED_LO = 0.01;
export const ARMED_HI = 0.12;
export const FIELD_OFF = 0.2;
export const ECHO_PERSIST = 0.85;
export const ECHO_RECUR = 0.75;
export const ECHO_MEMORY = 16;
export const ACCEPT_CAP = 0.8;
export const CENSUS_EVERY = 10;
export const CENSUS_UNTIL = 300;

export type LevelName = "off" | "unarmed" | "armed" | "loud";

export function pop25(n: number): number {
  let c = 0;
  let x = n;
  while (x) {
    x &= x - 1;
    c++;
  }
  return c;
}

/** Live cells only. Empty-against-anything is 0, including empty-against-empty. */
export function dice(a: number, b: number): number {
  const pa = pop25(a);
  const pb = pop25(b);
  if (pa === 0 || pb === 0) return 0;
  return (2 * pop25(a & b)) / (pa + pb);
}

type Op = (x: number, y: number) => [number, number];

const ORIENT_OPS: Op[] = [
  (x, y) => [x, y],
  (x, y) => [y, 4 - x],
  (x, y) => [4 - x, 4 - y],
  (x, y) => [4 - y, x],
  (x, y) => [4 - x, y],
  (x, y) => [y, x],
  (x, y) => [x, 4 - y],
  (x, y) => [4 - y, 4 - x],
];

export function transformMask(mask: number, op: Op): number {
  let out = 0;
  for (let y = 0; y < PATCH; y++) {
    for (let x = 0; x < PATCH; x++) {
      if ((mask & (1 << (y * PATCH + x))) === 0) continue;
      const [nx, ny] = op(x, y);
      out |= 1 << (ny * PATCH + nx);
    }
  }
  return out;
}

export function orientations(mask: number): number[] {
  return ORIENT_OPS.map((op) => transformMask(mask, op));
}

export function orbitOf(mask: number): number {
  let best = mask >>> 0;
  for (const form of orientations(mask)) if ((form >>> 0) < best) best = form >>> 0;
  return best;
}

export function bestDice(patch: number, forms: number[]): { score: number; index: number } {
  let score = 0;
  let index = 0;
  for (let i = 0; i < forms.length; i++) {
    const next = dice(patch, forms[i]);
    if (next > score) {
      score = next;
      index = i;
    }
  }
  return { score, index };
}

export function eligible(mask: number): boolean {
  return pop25(mask) >= 3 && pop25(mask & CENTER3) >= 1;
}

export function rowsToMask(rows: string[]): number {
  let mask = 0;
  let bit = 0;
  for (let y = 0; y < PATCH; y++) {
    const row = rows[y] ?? "";
    for (let x = 0; x < PATCH; x++) {
      const ch = row[x];
      if (ch === "#" || ch === "O") mask |= 1 << bit;
      bit++;
    }
  }
  return mask;
}

const COMPARE_ROWS: { name: string; rows: string[] }[] = [
  { name: "Loaf", rows: [".....", ".##..", "#..#.", ".#.#.", "..#.."] },
  { name: "Pond", rows: [".....", ".##..", "#..#.", "#..#.", ".##.."] },
  { name: "Ship", rows: [".....", "##...", "#.#..", ".##..", "....."] },
  { name: "Long boat", rows: [".....", ".#...", "#.#..", ".##..", ".#..."] },
];

export const COMPARISON_ORBITS: number[] = COMPARE_ROWS.map((form) => orbitOf(rowsToMask(form.rows)));

export function classifyLevel(
  fieldStrength: number,
  flipRate: number,
  anyFlips: boolean,
  gen: number,
): { name: LevelName; provisional: boolean } {
  const provisional = gen < WINDOW_GENS;
  if (fieldStrength < FIELD_OFF && !anyFlips) return { name: "off", provisional };
  if (flipRate > ARMED_HI) return { name: "loud", provisional };
  if (flipRate >= ARMED_LO) return { name: "armed", provisional };
  return { name: "unarmed", provisional };
}

export function facilitation(nBoard: number, nControl: number): number {
  return Math.log((nBoard + 0.5) / (nControl + 0.5));
}

export function specificity(
  board: Map<number, number>,
  control: Map<number, number>,
  trained: number[],
  comparison: number[] = COMPARISON_ORBITS,
): number {
  const mean = (ids: number[]) => {
    if (ids.length === 0) return 0;
    let sum = 0;
    for (const id of ids) sum += facilitation(board.get(id) ?? 0, control.get(id) ?? 0);
    return sum / ids.length;
  };
  return mean(trained) - mean(comparison);
}

export function mergeCounts(into: Map<number, number>, add: Map<number, number>) {
  for (const [key, value] of add) into.set(key, (into.get(key) ?? 0) + value);
}

/** Isolated objects that fit in a 5×5, keyed by symmetry orbit. A fused soup contributes nothing. */
export function censusCounts(grid: Uint8Array, w: number, h: number): Map<number, number> {
  const seen = new Uint8Array(grid.length);
  const counts = new Map<number, number>();
  const stack: number[] = [];
  for (let i = 0; i < grid.length; i++) {
    if (!grid[i] || seen[i]) continue;
    stack.length = 0;
    stack.push(i);
    seen[i] = 1;
    let minX = w;
    let minY = h;
    let maxX = 0;
    let maxY = 0;
    const cells: number[] = [];
    while (stack.length) {
      const cur = stack.pop() as number;
      const x = cur % w;
      const y = (cur / w) | 0;
      cells.push(cur);
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          if (dx === 0 && dy === 0) continue;
          const nx = x + dx;
          const ny = y + dy;
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          const ni = ny * w + nx;
          if (!grid[ni] || seen[ni]) continue;
          seen[ni] = 1;
          stack.push(ni);
        }
      }
    }
    const bw = maxX - minX + 1;
    const bh = maxY - minY + 1;
    if (bw > 5 || bh > 5 || cells.length > 16) continue;
    let mask = 0;
    for (const cur of cells) {
      const x = (cur % w) - minX;
      const y = ((cur / w) | 0) - minY;
      mask |= 1 << (y * 5 + x);
    }
    const id = orbitOf(mask);
    counts.set(id, (counts.get(id) ?? 0) + 1);
  }
  return counts;
}

export function dStar(disagreeShare: number, p: number, q: number): number {
  const denom = p * (1 - q) + q * (1 - p);
  if (denom < 1e-9) return 0;
  return disagreeShare / denom;
}

export function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = values.slice().sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function logChoose(n: number, k: number): number {
  let s = 0;
  const kk = Math.min(k, n - k);
  for (let i = 1; i <= kk; i++) s += Math.log(n - kk + i) - Math.log(i);
  return s;
}

/** Two-sided sign test. Ties are dropped. α for Specific is 0.05, fixed in advance. */
export function signTest(diffs: number[]): { n: number; pos: number; neg: number; p: number; median: number } {
  const nz = diffs.filter((value) => value !== 0);
  const pos = nz.filter((value) => value > 0).length;
  const n = nz.length;
  if (n === 0) return { n: 0, pos: 0, neg: 0, p: 1, median: 0 };
  const k = Math.min(pos, n - pos);
  let acc = 0;
  for (let i = 0; i <= k; i++) acc += Math.exp(logChoose(n, i) - n * Math.LN2);
  return { n, pos, neg: n - pos, p: Math.min(1, 2 * acc), median: median(nz) };
}

export function bootstrapMedianCI(diffs: number[], iters = 400, seed = 1): { lo: number; hi: number } {
  const nz = diffs.filter((value) => value !== 0);
  if (nz.length === 0) return { lo: 0, hi: 0 };
  const rng = mulberry32(seed);
  const stats: number[] = [];
  for (let i = 0; i < iters; i++) {
    const sample: number[] = [];
    for (let j = 0; j < nz.length; j++) sample.push(nz[Math.floor(rng() * nz.length)]);
    stats.push(median(sample));
  }
  stats.sort((a, b) => a - b);
  const lo = stats[Math.max(0, Math.floor(0.025 * (stats.length - 1)))];
  const hi = stats[Math.min(stats.length - 1, Math.ceil(0.975 * (stats.length - 1)))];
  return { lo, hi };
}

export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function mixSeed(seed: number, salt: number): number {
  let x = (seed ^ salt) >>> 0;
  x = Math.imul(x ^ (x >>> 16), 0x7feb352d);
  x = Math.imul(x ^ (x >>> 15), 0x846ca68b);
  return (x ^ (x >>> 16)) >>> 0;
}

export function permutation(seed: number): number[] {
  const rng = mulberry32(mixSeed(seed, 0x5c5a1117));
  const order = Array.from({ length: PATCH_CELLS }, (_, index) => index);
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    const swap = order[i];
    order[i] = order[j];
    order[j] = swap;
  }
  let moved = false;
  for (let i = 0; i < order.length; i++) if (order[i] !== i) moved = true;
  if (!moved) {
    const swap = order[0];
    order[0] = order[1];
    order[1] = swap;
  }
  return order;
}

export function permuteMask(mask: number, order: number[]): number {
  let out = 0;
  for (let i = 0; i < PATCH_CELLS; i++) {
    if (mask & (1 << i)) out |= 1 << order[i];
  }
  return out;
}

export function sha256(message: string): string {
  const bytes: number[] = [];
  for (let i = 0; i < message.length; i++) {
    const code = message.charCodeAt(i);
    if (code < 0x80) bytes.push(code);
    else if (code < 0x800) bytes.push(0xc0 | (code >> 6), 0x80 | (code & 0x3f));
    else bytes.push(0xe0 | (code >> 12), 0x80 | ((code >> 6) & 0x3f), 0x80 | (code & 0x3f));
  }
  const bitLen = bytes.length * 8;
  bytes.push(0x80);
  while (bytes.length % 64 !== 56) bytes.push(0);
  const hi = Math.floor(bitLen / 0x100000000);
  const lo = bitLen >>> 0;
  for (let i = 3; i >= 0; i--) bytes.push((hi >>> (i * 8)) & 0xff);
  for (let i = 3; i >= 0; i--) bytes.push((lo >>> (i * 8)) & 0xff);

  const k = new Uint32Array(64);
  const hash = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ]);
  const prime = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ];
  for (let i = 0; i < 64; i++) k[i] = prime[i];

  const w = new Uint32Array(64);
  const rotr = (value: number, shift: number) => (value >>> shift) | (value << (32 - shift));
  for (let offset = 0; offset < bytes.length; offset += 64) {
    for (let i = 0; i < 16; i++) {
      const j = offset + i * 4;
      w[i] = ((bytes[j] << 24) | (bytes[j + 1] << 16) | (bytes[j + 2] << 8) | bytes[j + 3]) >>> 0;
    }
    for (let i = 16; i < 64; i++) {
      const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
      const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }
    let a = hash[0];
    let b = hash[1];
    let c = hash[2];
    let d = hash[3];
    let e = hash[4];
    let f = hash[5];
    let g = hash[6];
    let h = hash[7];
    for (let i = 0; i < 64; i++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const t1 = (h + S1 + ch + k[i] + w[i]) >>> 0;
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (S0 + maj) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + t1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (t1 + t2) >>> 0;
    }
    hash[0] = (hash[0] + a) >>> 0;
    hash[1] = (hash[1] + b) >>> 0;
    hash[2] = (hash[2] + c) >>> 0;
    hash[3] = (hash[3] + d) >>> 0;
    hash[4] = (hash[4] + e) >>> 0;
    hash[5] = (hash[5] + f) >>> 0;
    hash[6] = (hash[6] + g) >>> 0;
    hash[7] = (hash[7] + h) >>> 0;
  }
  let hex = "";
  for (const word of hash) hex += word.toString(16).padStart(8, "0");
  return hex;
}

export function seedFromRow(rowHex: string, index: number): number {
  const hex = sha256(`${rowHex}:${index}`);
  const value = Number.parseInt(hex.slice(0, 8), 16) >>> 0;
  return value || 1;
}
