import type { ArchiveEntry, FieldConfig } from "./engine.ts";
import { CENTER_BIT, PATCH_CELLS } from "./protocol.ts";

const KEY = "sheldrake.morphic.v1";
const FULL_PATCH = (1 << PATCH_CELLS) - 1;

type Saved = {
  version: 1;
  archive: ArchiveEntry[];
  settings: Partial<FieldConfig>;
};

export function loadLab(): { archive: ArchiveEntry[]; settings: Partial<FieldConfig> } {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { archive: [], settings: {} };
    const parsed = JSON.parse(raw) as Saved;
    if (!parsed || parsed.version !== 1 || !Array.isArray(parsed.archive)) {
      return { archive: [], settings: {} };
    }
    const archive = parsed.archive
      .filter(
        (e) =>
          e &&
          Number.isInteger(e.mask) &&
          Number.isInteger(e.nextMask) &&
          typeof e.strength === "number" &&
          Number.isFinite(e.strength),
      )
      .map((e) => {
        const mask = e.mask & FULL_PATCH;
        const nextMask = e.nextMask & FULL_PATCH;
        return {
          name: typeof e.name === "string" ? e.name : "Echo",
          mask,
          nextMask,
          strength: Math.max(0, Math.min(1, e.strength)),
          // Derived, so never trusted from storage.
          nextCenter: (nextMask >> CENTER_BIT) & 1,
        };
      })
      .filter((e) => e.mask !== 0);
    return { archive, settings: parsed.settings ?? {} };
  } catch {
    return { archive: [], settings: {} };
  }
}

export function saveLab(archive: ArchiveEntry[], settings: FieldConfig) {
  try {
    const payload: Saved = { version: 1, archive, settings };
    localStorage.setItem(KEY, JSON.stringify(payload));
  } catch {
    /* private mode / quota — the run still works */
  }
}
