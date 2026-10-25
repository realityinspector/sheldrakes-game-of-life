/**
 * Bit-parallel Conway for the tester's 32 × 32 torus: one Uint32 per row, bit x = cell x,
 * the eight neighbours summed with carry-save adders. It computes exactly what
 * `lifeStep` computes (the tests check every generation against it on random soups), only
 * several times faster, so the tester can run more soups per block in the same time.
 */
import { censusCounts } from "../src/sim/protocol.ts";

const rotL = (r: number) => ((r << 1) | (r >>> 31)) >>> 0; // bit x gets cell x - 1
const rotR = (r: number) => ((r >>> 1) | (r << 31)) >>> 0; // bit x gets cell x + 1

/** Rows of a 32 × 32 soup from 128 bytes, matching `soupFromBytes` (cell k = bit k & 7 of byte k >> 3). */
export function rowsFromBytes(bytes: Uint8Array, rows: Uint32Array = new Uint32Array(32)): Uint32Array {
  for (let y = 0; y < 32; y++) {
    const o = 4 * y;
    rows[y] = (bytes[o] | (bytes[o + 1] << 8) | (bytes[o + 2] << 16) | (bytes[o + 3] << 24)) >>> 0;
  }
  return rows;
}

/** One B3/S23 step on the 32 × 32 torus. */
export function bitStep(src: Uint32Array, dst: Uint32Array) {
  for (let y = 0; y < 32; y++) {
    const up = src[(y + 31) & 31];
    const mid = src[y];
    const dn = src[(y + 1) & 31];
    const a = rotL(up);
    const c = rotR(up);
    const d = rotL(mid);
    const e = rotR(mid);
    const f = rotL(dn);
    const h = rotR(dn);
    // three full adders + one half adder on the eight neighbour planes
    const s1 = a ^ up ^ c;
    const c1 = (a & up) | (c & (a ^ up));
    const s2 = d ^ e ^ f;
    const c2 = (d & e) | (f & (d ^ e));
    const s3 = dn ^ h;
    const c3 = dn & h;
    const ones = s1 ^ s2 ^ s3;
    const k2 = (s1 & s2) | (s3 & (s1 ^ s2)); // carry into the twos
    const t = c1 ^ c2 ^ c3;
    const u = (c1 & c2) | (c3 & (c1 ^ c2)); // fours from the carries
    const twos = t ^ k2;
    const k4 = t & k2;
    const four = u | k4; // any weight >= 4 (u ^ k4 for exactly 4, u & k4 for 8; both disqualify)
    dst[y] = (twos & ~four & (ones | mid)) >>> 0;
  }
}

/** Cells (0/1 per cell, row-major) for the census. */
export function cellsFromRows(rows: Uint32Array, out: Uint8Array = new Uint8Array(1024)): Uint8Array {
  for (let y = 0; y < 32; y++) {
    const r = rows[y];
    for (let x = 0; x < 32; x++) out[y * 32 + x] = (r >>> x) & 1;
  }
  return out;
}

/** Run a 32 × 32 soup for `generations` steps and return its census. */
export function bitSoupCensus(bytes: Uint8Array, generations: number): Map<number, number> {
  let a: Uint32Array = rowsFromBytes(bytes);
  let b: Uint32Array = new Uint32Array(32);
  for (let g = 0; g < generations; g++) {
    bitStep(a, b);
    const t = a;
    a = b;
    b = t;
  }
  return censusCounts(cellsFromRows(a), 32, 32, true);
}
