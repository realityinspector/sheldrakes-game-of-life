import { Download, Trash2 } from "lucide-react";
import type { Book, FindingKind, Question, ResonanceChip } from "@/sim/findings";
import {
  exportDocument,
  findingsCsv,
  ledgerDigest,
  questions,
  scoreResonance,
  trialsCsv,
} from "@/sim/findings";
import type { RunSnapshot } from "@/sim/engine";
import { PATCH_CELLS } from "@/sim/engine";

export function ResonanceBanner({ book, snap }: { book: Book; snap: RunSnapshot | null }) {
  const filed = snap && book.runKey === String(snap.runId) ? book.filedThisRun : [];
  const score = scoreResonance(book, snap, filed);
  const titleColor =
    score.verdict === "armed"
      ? "text-life"
      : score.verdict === "loud"
        ? "text-amber"
        : score.verdict === "off"
          ? "text-mist"
          : "text-bone";
  const barColor =
    score.verdict === "armed" ? "bg-life" : score.verdict === "loud" ? "bg-amber" : "bg-mist";

  return (
    <section
      className="rounded-lab border border-line bg-panel px-3 py-3"
      aria-label="What this run shows"
    >
      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
        <div className="min-w-0">
          <h2 className="font-display text-lg leading-tight italic">
            What this run is allowed to say
          </h2>
          <p
            className={`mt-1 font-display text-4xl leading-none italic ${titleColor}`}
            aria-live="polite"
          >
            {score.title}
          </p>
        </div>
        <div className="text-right">
          <p className="font-display text-2xl leading-none text-mist italic">Demonstration</p>
          <p className="mt-1 text-xs text-mist">one seed, not a batch</p>
          <p className="text-xs text-bone tabular-nums">{score.ledger} armed runs on the ledger</p>
        </div>
      </div>
      <p className="mt-2 text-xs text-pretty text-mist">
        Armed means the table rewrote 1–12% of the neighborhoods it read. That is the old Yes, and
        it is not morphic resonance. Specific and Learned are scored only on a frozen batch, in
        Sweep.
      </p>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line">
        <div
          className={`h-full ${barColor}`}
          style={{ width: `${Math.round(Math.max(0, Math.min(1, score.meter)) * 100)}%` }}
        />
      </div>
      <p className="mt-2 text-sm text-pretty text-bone">{score.line}</p>
      <ul className="mt-3 grid grid-cols-3 gap-2">
        {score.chips.map((chip) => (
          <Chip key={chip.id} chip={chip} />
        ))}
      </ul>
    </section>
  );
}

export function FindingsPanel({
  book,
  snap,
  notice,
  onClear,
}: {
  book: Book;
  snap: RunSnapshot | null;
  notice: string | null;
  onClear: () => void;
}) {
  const filed = book.filedThisRun;
  const sameRun = snap ? book.runKey === String(snap.runId) : false;
  const filedNow = sameRun ? filed : [];
  const liveRows = snap ? questions(snap, filedNow) : PLACEHOLDER;

  return (
    <section className="rounded-lab border border-line bg-panel p-3" aria-label="Evidence">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="max-w-3xl">
          <h2 className="font-display text-lg italic">Evidence</h2>
          <p className="mt-1 text-sm text-pretty text-mist">
            Armed is a fact about the table. Crowd, settle, D*, and kept forms are written down so a
            long run still leaves a trail. Specific is not decided on this page.
          </p>
        </div>
        <p className="text-sm text-bone tabular-nums">
          {book.findings.length} claims · {book.trials.length} trials
        </p>
      </div>
      <p className="mt-3 text-sm text-pretty text-bone">{ledgerDigest(book)}</p>

      {notice ? <p className="mt-3 text-sm text-amber">{notice}</p> : null}

      <ul className="mt-3 grid gap-2 md:grid-cols-2">
        {liveRows.map((question) => (
          <li key={question.id} className="rounded-lg border border-line bg-panel-2 px-3 py-2">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-sm text-bone">{question.title}</h3>
              <span className="flex shrink-0 items-baseline gap-2">
                <span
                  className={`text-xs tabular-nums ${
                    question.stake.startsWith("+") ? "text-amber" : "text-mist"
                  }`}
                >
                  {question.stake}
                </span>
                <span
                  className={`text-xs tracking-wide uppercase ${
                    question.state === "filed" ? "text-amber" : "text-mist"
                  }`}
                >
                  {question.state === "filed" ? "Filed" : "Watching"}
                </span>
              </span>
            </div>
            <p className="mt-1 text-xs text-pretty text-mist">{question.rule}</p>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-line">
              <div
                className={`h-full ${question.state === "filed" ? "bg-amber" : "bg-life"}`}
                style={{ width: `${Math.round(Math.max(0, Math.min(1, question.meter)) * 100)}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-bone tabular-nums">{question.reading}</p>
          </li>
        ))}
      </ul>

      <div className="mt-4">
        <h3 className="text-sm text-bone">Ledger</h3>
        {book.findings.length === 0 ? (
          <p className="mt-1 text-sm text-mist">
            Nothing filed yet. At generation 80 the run records Armed, Loud, Unarmed, or Off. A miss
            is not a detection either way. Specific waits for a frozen batch.
          </p>
        ) : (
          <ul className="lab-scroll mt-1 max-h-64 overflow-y-auto">
            {book.findings.map((finding) => (
              <li key={finding.id} className="flex gap-3 border-t border-line py-2">
                {finding.mask != null ? <Glyph mask={finding.mask} /> : null}
                <div className="min-w-0">
                  <p className="text-sm text-bone">{finding.claim}</p>
                  <p className="text-sm text-pretty text-mist">{finding.detail}</p>
                  <p className="text-xs text-mist tabular-nums">
                    {scoredLabel(finding.kind, finding.times)} · seen in {finding.times}{" "}
                    {finding.times === 1 ? "run" : "runs"} · seed {finding.seed} · generation{" "}
                    {finding.generation}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {book.trials.length > 0 ? (
        <div className="mt-4">
          <h3 className="text-sm text-bone">Recent trials</h3>
          <div className="lab-scroll mt-1 overflow-x-auto">
            <table className="w-full min-w-[36rem] text-left text-xs text-mist tabular-nums">
              <thead>
                <tr className="text-bone">
                  <th className="py-1 pr-3 font-normal">Gen</th>
                  <th className="py-1 pr-3 font-normal">Why</th>
                  <th className="py-1 pr-3 font-normal">Seed</th>
                  <th className="py-1 pr-3 font-normal">Pattern</th>
                  <th className="py-1 pr-3 font-normal">Diverge</th>
                  <th className="py-1 pr-3 font-normal">Influence</th>
                  <th className="py-1 pr-3 font-normal">Field peak</th>
                  <th className="py-1 font-normal">Control peak</th>
                </tr>
              </thead>
              <tbody>
                {book.trials.slice(0, 8).map((trial) => (
                  <tr key={trial.id} className="border-t border-line">
                    <td className="py-1 pr-3">{trial.generation}</td>
                    <td className="py-1 pr-3">{trial.reason}</td>
                    <td className="py-1 pr-3">{trial.seed}</td>
                    <td className="py-1 pr-3">{trial.preset}</td>
                    <td className="py-1 pr-3">{(trial.meanDiverge * 100).toFixed(1)}%</td>
                    <td className="py-1 pr-3">{(trial.meanInfluence * 100).toFixed(1)}%</td>
                    <td className="py-1 pr-3">{trial.maxPopM}</td>
                    <td className="py-1">{trial.maxPopC}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="inline-flex h-11 items-center gap-2 rounded-full border border-line bg-panel-2 px-3 text-sm text-bone"
          onClick={() =>
            download(
              "sheldrake-findings.json",
              JSON.stringify(exportDocument(book), null, 2),
              "application/json",
            )
          }
        >
          <Download className="size-4" />
          Export JSON
        </button>
        <button
          type="button"
          className="inline-flex h-11 items-center gap-2 rounded-full border border-line bg-panel-2 px-3 text-sm text-bone"
          onClick={() => download("sheldrake-findings.csv", findingsCsv(book), "text/csv")}
        >
          <Download className="size-4" />
          Export findings
        </button>
        <button
          type="button"
          className="inline-flex h-11 items-center gap-2 rounded-full border border-line bg-panel-2 px-3 text-sm text-bone"
          onClick={() => download("sheldrake-trials.csv", trialsCsv(book), "text/csv")}
        >
          <Download className="size-4" />
          Export trials
        </button>
        <button
          type="button"
          className="inline-flex h-11 items-center gap-2 rounded-full border border-line bg-ink px-3 text-sm text-mist"
          onClick={onClear}
        >
          <Trash2 className="size-4" />
          Clear ledger
        </button>
      </div>
      <p className="mt-2 text-xs text-mist">
        Clear ledger drops filed claims and trials on this device. It does not wipe the crystal
        archive. Forget past runs, under the chart, does the opposite.
      </p>
    </section>
  );
}

const PLACEHOLDER: Question[] = [
  {
    id: "level",
    title: "Is the memory term the right size?",
    stake: "level",
    rule: "Scored once, at generation 80. Armed is 1–12% of consulted neighborhoods. It is not resonance.",
    state: "open",
    meter: 0,
    reading: "Waiting for the run.",
  },
  {
    id: "dstar",
    title: "How far did the field leave the control?",
    stake: "note",
    rule: "D* is descriptive. It is not a pass.",
    state: "open",
    meter: 0,
    reading: "Waiting for the run.",
  },
  {
    id: "crowd",
    title: "Did memory raise the crowd?",
    stake: "note",
    rule: "Noted, not scored.",
    state: "open",
    meter: 0,
    reading: "Waiting for the run.",
  },
  {
    id: "gap",
    title: "Does the remembered shape beat the nulls?",
    stake: "illustration",
    rule: "One seed cannot say Specific.",
    state: "open",
    meter: 0,
    reading: "Waiting for the run.",
  },
];

function Chip({ chip }: { chip: ResonanceChip }) {
  const valueColor =
    chip.tone === "paid"
      ? "text-amber"
      : chip.tone === "ready"
        ? "text-life"
        : chip.tone === "miss"
          ? "text-mist"
          : "text-bone";
  return (
    <li
      className={`rounded-lg border px-2 py-1.5 ${
        chip.tone === "paid" || chip.tone === "ready" ? "border-amber bg-ink" : "border-line bg-ink"
      }`}
    >
      <p className="text-xs tracking-wide text-mist uppercase">{chip.label}</p>
      <p className={`text-sm tabular-nums ${valueColor}`}>{chip.value}</p>
      <p className="text-xs text-mist">{chip.hint}</p>
    </li>
  );
}

function Glyph({ mask }: { mask: number }) {
  const cells = [];
  for (let i = 0; i < PATCH_CELLS; i++) {
    cells.push(<span key={i} className={(mask & (1 << i)) !== 0 ? "bg-life" : "bg-ink"} />);
  }
  return (
    <div className="grid size-10 shrink-0 grid-cols-5 gap-px" aria-hidden="true">
      {cells}
    </div>
  );
}

function scoredLabel(kind: FindingKind, times: number): string {
  void times;
  if (kind === "armed" || kind === "loud" || kind === "unarmed" || kind === "off")
    return "Level, not resonance";
  return "Not a score";
}

function download(filename: string, body: string, mime: string) {
  const blob = new Blob([body], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
