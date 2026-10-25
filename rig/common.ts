/**
 * Shared, table-free pieces of the isolation rig: the candidate forms, a plain Conway
 * step, the census, hashing, a hash-chained log, and small HTTP helpers.
 *
 * Nothing here knows which form is being trained. The tester imports only this file and
 * src/sim/protocol.ts (pure geometry and hashing); it never imports the morphic engine.
 */
import { createHash, randomBytes, timingSafeEqual } from "node:crypto";
import { appendFileSync, existsSync, readFileSync } from "node:fs";
import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { censusCounts, rowsToMask, shapeId } from "../src/sim/protocol.ts";
import { bitSoupCensus } from "./bitlife.ts";

export const RIG_VERSION = "sheldrake-rig/2";

/** Every form the rig can train or count. A protocol picks a subset by name. */
export const FORM_ROWS: Record<string, string[]> = {
  block: ["##", "##"],
  blinker: ["###"],
  beehive: [".##.", "#..#", ".##."],
  loaf: [".##.", "#..#", ".#.#", "..#."],
  boat: ["##.", "#.#", ".#."],
  ship: ["##.", "#.#", ".##"],
  tub: [".#.", "#.#", ".#."],
  pond: [".##.", "#..#", "#..#", ".##."],
};

export const FORM_IDS: Record<string, number> = Object.fromEntries(
  Object.entries(FORM_ROWS).map(([name, rows]) => [name, shapeId(rowsToMask(rows))]),
);

export type TesterSpec = { soups: number; size: number; generations: number };
export type TrainerSpec = {
  boards: number;
  size: number;
  spacing: number;
  generations: number;
  censusEvery: number;
  /** Every block takes at least this long, so the tester cannot time which form was trained. */
  blockMillis: number;
};

export type Protocol = {
  rig: typeof RIG_VERSION;
  label: string;
  hypothesis: string;
  forms: string[];
  blocks: number;
  tester: TesterSpec;
  trainer: TrainerSpec;
  analysis: { permutations: number; bootstrap: number; alpha: number };
  /** Positive control only: the registrar tells the tester the target and the tester inflates its count. */
  leak: { relative: number };
};

export function validateProtocol(p: Protocol): string | null {
  if (p.rig !== RIG_VERSION) return `rig must be ${RIG_VERSION}`;
  if (!Array.isArray(p.forms) || p.forms.length < 2) return "need at least two forms";
  if (new Set(p.forms).size !== p.forms.length) return "forms must be distinct";
  for (const f of p.forms) if (!(f in FORM_ROWS)) return `unknown form ${f}`;
  if (!Number.isInteger(p.blocks) || p.blocks < p.forms.length || p.blocks % p.forms.length !== 0) {
    return "blocks must be a positive multiple of the number of forms (balanced design)";
  }
  if (p.tester.size % 8 !== 0) return "tester size must be a multiple of 8 (one entropy bit per cell)";
  if (!(p.leak.relative >= 0 && p.leak.relative < 1)) return "leak.relative must be in [0, 1)";
  if (!(p.trainer.blockMillis > 0)) return "trainer.blockMillis must be positive";
  return null;
}

/** Files whose bytes define a run. Hashed at commit and again at reveal. */
export const CODE_FILES = [
  "rig/common.ts",
  "rig/analysis.ts",
  "rig/registrar.ts",
  "rig/trainer.ts",
  "rig/tester.ts",
  "rig/bitlife.ts",
  "src/sim/protocol.ts",
];

// ---------------------------------------------------------------- hashing

export function sha256hex(data: string | Uint8Array): string {
  return createHash("sha256").update(data).digest("hex");
}

/** JSON with object keys sorted at every level, so equal values hash equally. */
export function canonical(value: unknown): string {
  return JSON.stringify(sortKeys(value));
}

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      out[key] = sortKeys((value as Record<string, unknown>)[key]);
    }
    return out;
  }
  return value;
}

export function token(): string {
  return randomBytes(32).toString("hex");
}

export function sameToken(a: string, b: string): boolean {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

// ---------------------------------------------------------------- Conway

/** One B3/S23 step on a torus. */
export function lifeStep(src: Uint8Array, dst: Uint8Array, w: number, h: number) {
  for (let y = 0; y < h; y++) {
    const ym = ((y - 1 + h) % h) * w;
    const y0 = y * w;
    const yp = ((y + 1) % h) * w;
    for (let x = 0; x < w; x++) {
      const xm = (x - 1 + w) % w;
      const xp = (x + 1) % w;
      const n =
        src[ym + xm] + src[ym + x] + src[ym + xp] + src[y0 + xm] + src[y0 + xp] + src[yp + xm] + src[yp + x] + src[yp + xp];
      dst[y0 + x] = n === 3 || (n === 2 && src[y0 + x] === 1) ? 1 : 0;
    }
  }
}

/** Run `generations` steps; returns the final grid (one of the two buffers). */
export function evolve(grid: Uint8Array, w: number, h: number, generations: number): Uint8Array {
  let a: Uint8Array = grid;
  let b: Uint8Array = new Uint8Array(grid.length);
  for (let g = 0; g < generations; g++) {
    lifeStep(a, b, w, h);
    const t = a;
    a = b;
    b = t;
  }
  return a;
}

/**
 * The registrar's beacon, expanded into a keystream and XORed into the tester's bytes for soup
 * `index`. The tester commits to its bytes before it sees the beacon, so it cannot keep
 * drawing until it likes a soup: it cannot predict the soup its bytes will become.
 */
export function mixWithBeacon(raw: Uint8Array, beacon: string, index: number): Uint8Array {
  const out = new Uint8Array(raw.length);
  let block = 0;
  let stream = new Uint8Array(0);
  for (let k = 0; k < raw.length; k++) {
    if (k % 32 === 0) stream = createHash("sha256").update(`${beacon}:${index}:${block++}`).digest();
    out[k] = raw[k] ^ stream[k % 32];
  }
  return out;
}

/** A soup with one entropy bit per cell (density 1/2). */
export function soupFromBytes(bytes: Uint8Array, size: number): Uint8Array {
  const grid = new Uint8Array(size * size);
  for (let k = 0; k < grid.length; k++) grid[k] = (bytes[k >> 3] >> (k & 7)) & 1;
  return grid;
}

/** Census of the named forms on a torus grid. */
export function countForms(grid: Uint8Array, size: number, forms: string[]): Record<string, number> {
  const census = censusCounts(grid, size, size, true);
  const out: Record<string, number> = {};
  for (const name of forms) out[name] = census.get(FORM_IDS[name]) ?? 0;
  return out;
}

/**
 * The tester's whole computation for one soup: bytes in, form counts out. Pure and replayable.
 * 32 × 32 soups take the bit-parallel path (identical results, checked in the tests).
 */
export function testSoup(bytes: Uint8Array, spec: TesterSpec, forms: string[]): Record<string, number> {
  if (spec.size === 32) {
    const census = bitSoupCensus(bytes, spec.generations);
    const out: Record<string, number> = {};
    for (const name of forms) out[name] = census.get(FORM_IDS[name]) ?? 0;
    return out;
  }
  return countForms(evolve(soupFromBytes(bytes, spec.size), spec.size, spec.size, spec.generations), spec.size, forms);
}

/** Counts for a whole block: each soup's raw bytes mixed with the beacon, then run. */
export function testBlock(raw: Uint8Array, beacon: string, spec: TesterSpec, forms: string[]): Record<string, number> {
  const per = (spec.size * spec.size) / 8;
  const counts: Record<string, number> = Object.fromEntries(forms.map((f) => [f, 0]));
  for (let i = 0; i < spec.soups; i++) {
    const c = testSoup(mixWithBeacon(raw.subarray(i * per, (i + 1) * per), beacon, i), spec, forms);
    for (const f of forms) counts[f] += c[f];
  }
  return counts;
}

/** Stamp a form on a regular lattice so copies never interact. */
export function stampLattice(form: string, size: number, spacing: number): Uint8Array {
  const grid = new Uint8Array(size * size);
  const rows = FORM_ROWS[form];
  for (let oy = 0; oy + spacing <= size; oy += spacing) {
    for (let ox = 0; ox + spacing <= size; ox += spacing) {
      rows.forEach((row, y) => {
        for (let x = 0; x < row.length; x++) if (row[x] === "#") grid[(oy + 2 + y) * size + ox + 2 + x] = 1;
      });
    }
  }
  return grid;
}

// ---------------------------------------------------------------- hash-chained log

export type LogEntry = { seq: number; at: string; type: string; data: unknown; prev: string; hash: string };

/** Append-only JSONL log; each entry's hash covers the previous hash, so edits are detectable. */
export class ChainLog {
  private head = "0".repeat(64);
  private seq = 0;
  private readonly file: string;
  constructor(file: string) {
    this.file = file;
    if (existsSync(file)) {
      for (const line of readFileSync(file, "utf8").split("\n")) {
        if (!line.trim()) continue;
        const entry = JSON.parse(line) as LogEntry;
        this.head = entry.hash;
        this.seq = entry.seq + 1;
      }
    }
  }
  append(type: string, data: unknown): LogEntry {
    const body = { seq: this.seq, at: new Date().toISOString(), type, data, prev: this.head };
    const hash = sha256hex(this.head + canonical(body));
    const entry = { ...body, hash };
    appendFileSync(this.file, JSON.stringify(entry) + "\n", { mode: 0o600 });
    this.head = hash;
    this.seq += 1;
    return entry;
  }
  get headHash() {
    return this.head;
  }
  static verify(file: string): { ok: boolean; entries: number; head: string } {
    let head = "0".repeat(64);
    let n = 0;
    for (const line of readFileSync(file, "utf8").split("\n")) {
      if (!line.trim()) continue;
      const { hash, ...body } = JSON.parse(line) as LogEntry;
      if (body.prev !== head || sha256hex(head + canonical(body)) !== hash) return { ok: false, entries: n, head };
      head = hash;
      n++;
    }
    return { ok: true, entries: n, head };
  }
}

// ---------------------------------------------------------------- HTTP

export type Handler = (req: IncomingMessage, body: unknown) => Promise<{ status?: number; json: unknown }>;

export function serve(routes: Record<string, Handler>, port: number, host = "127.0.0.1"): Promise<Server> {
  const server = createServer(async (req: IncomingMessage, res: ServerResponse) => {
    try {
      const url = new URL(req.url ?? "/", "http://x");
      const key = `${req.method} ${url.pathname}`;
      const route = routes[key] ?? Object.entries(routes).find(([k]) => matchPrefix(k, key))?.[1];
      if (!route) return send(res, 404, { error: "not found" });
      const chunks: Buffer[] = [];
      for await (const chunk of req) chunks.push(chunk as Buffer);
      const raw = Buffer.concat(chunks).toString("utf8");
      const body = raw ? JSON.parse(raw) : null;
      const out = await route(req, body);
      send(res, out.status ?? 200, out.json);
    } catch (error) {
      send(res, 500, { error: String((error as Error)?.message ?? error) });
    }
  });
  return new Promise((resolve) => server.listen(port, host, () => resolve(server)));
}

/** "GET /audit/*" matches "GET /audit/7". */
function matchPrefix(pattern: string, key: string): boolean {
  return pattern.endsWith("/*") && key.startsWith(pattern.slice(0, -1));
}

function send(res: ServerResponse, status: number, json: unknown) {
  const text = JSON.stringify(json);
  res.writeHead(status, { "content-type": "application/json", "content-length": Buffer.byteLength(text) });
  res.end(text);
}

export function bearer(req: IncomingMessage): string {
  const header = req.headers.authorization ?? "";
  return header.startsWith("Bearer ") ? header.slice(7) : "";
}

export async function call<T>(url: string, init: { method?: string; token?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(url, {
    method: init.method ?? (init.body === undefined ? "GET" : "POST"),
    headers: {
      "content-type": "application/json",
      ...(init.token ? { authorization: `Bearer ${init.token}` } : {}),
    },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  const json = (await res.json()) as T & { error?: string };
  if (!res.ok) throw new Error(`${res.status} ${url}: ${json.error ?? "error"}`);
  return json;
}

export function env(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`missing ${name}`);
  return value;
}

export const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
