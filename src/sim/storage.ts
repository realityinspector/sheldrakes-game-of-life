import type { ArchiveEntry, FieldConfig } from "@/sim/engine";

const KEY = "sheldrake.morphic.v1";

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
    const archive = parsed.archive.filter(
      (e) => e && typeof e.mask === "number" && typeof e.nextMask === "number",
    );
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
