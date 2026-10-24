import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Layers, Pause, Play, RotateCcw, Sparkles, Square } from "lucide-react";
import { Bar, BarChart, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LabBrand } from "@/components/lab-nav";
import { Autopilot } from "@/sim/autopilot";
import { DEFAULT_CONFIG, type FieldConfig, type PresetId } from "@/sim/engine";
import { interpret } from "@/sim/interpret";
import { loadLab, saveLab } from "@/sim/storage";
import {
  AXES,
  SweepRunner,
  formatCount,
  megaLattice,
  type AxisKey,
  type DoseCurve,
  type MegaState,
  type SeekGoal,
  type SweepCard,
  type SweepMode,
} from "@/sim/sweep";

const PRESETS: { id: PresetId; label: string }[] = [
  { id: "soup", label: "Primordial soup" },
  { id: "garden", label: "Still garden" },
  { id: "gliders", label: "Glider flock" },
  { id: "rpen", label: "R-pentomino" },
  { id: "acorn", label: "Acorn" },
  { id: "pulsar", label: "Pulsar" },
  { id: "gun", label: "Gosper gun" },
];

const chartTip = {
  background: "#0c1210",
  border: "1px solid #2c3b34",
  borderRadius: 10,
  color: "#f3ecdc",
};

export function SweepPage() {
  const navigate = useNavigate();
  const runnerRef = useRef<SweepRunner | null>(null);
  const pilotRef = useRef<Autopilot | null>(null);
  const runnerEpoch = useRef(0);
  if (runnerEpoch.current !== 5 || !runnerRef.current || !pilotRef.current) {
    runnerEpoch.current = 5;
    runnerRef.current = new SweepRunner();
    pilotRef.current = new Autopilot();
  }
  const runner = runnerRef.current;
  const pilot = pilotRef.current;
  const [mode, setMode] = useState<SweepMode>("seek");
  const [goal, setGoal] = useState<SeekGoal>("armed");
  const [generations, setGenerations] = useState(80);
  const [granularity, setGranularity] = useState(25);
  const [seedCount, setSeedCount] = useState(16);
  const [axes, setAxes] = useState<AxisKey[]>(["fieldStrength", "similarityThreshold", "density"]);
  const [sweepSize, setSweepSize] = useState(true);
  const [sweepInnate, setSweepInnate] = useState(false);
  const [ignoreArchive, setIgnoreArchive] = useState(true);
  const [preset, setPreset] = useState<PresetId>("soup");
  const [view, setView] = useState(0);
  const paintAt = useRef(0);
  const megaCount = useMemo(() => megaLattice(granularity).total, [granularity]);

  useEffect(() => {
    let raf = 0;
    let dead = false;
    const frame = (now: number) => {
      if (dead) return;
      const current = runnerRef.current;
      const auto = pilotRef.current;
      if (current && current.status === "running") {
        const mega = current.mode === "mega";
        current.tick(mega ? 480 : 10, mega ? now + 12 : undefined);
        const due = !mega || current.status !== "running" || now - paintAt.current > 300;
        if (due) {
          paintAt.current = now;
          setView((n) => n + 1);
        }
      } else if (auto && current && auto.on && !auto.busy && current.status === "done" && current.mode !== "mega") {
        void auto.advance(current).then(() => {
          if (!dead) setView((n) => n + 1);
        });
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => {
      dead = true;
      cancelAnimationFrame(raf);
    };
  }, []);

  const status = runner.status;
  const locked = status === "running" || status === "paused";
  const cards = runner.cards;
  const mega = runner.mega;
  const showCharts = !mega && cards.length > 0 && status !== "running";

  function applyPlan() {
    const saved = loadLab();
    const baseline: FieldConfig = {
      ...DEFAULT_CONFIG,
      ...saved.settings,
      cells: saved.settings.cells ?? 48,
    };
    runner.setPlan({
      mode: mode === "mega" ? "seek" : mode,
      goal,
      generations,
      granularity,
      seedCount,
      axes,
      sweepSize,
      sweepInnate,
      ignoreArchive,
      preset,
      baseline,
      archive: saved.archive,
      seed: 1000 + Math.floor(Math.random() * 80000),
    });
  }

  function start() {
    pilot.on = false;
    applyPlan();
    runner.start();
    setView((n) => n + 1);
  }

  function stopAll() {
    pilot.on = false;
    runner.stop();
    setView((n) => n + 1);
  }

  function launchAutopilot() {
    const plan = pilot.first();
    const saved = loadLab();
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
      archive: saved.archive,
      seed: 1000 + Math.floor(Math.random() * 80000),
      limit: plan.limit,
    });
    runner.start();
    setView((n) => n + 1);
  }

  function launchMega() {
    pilot.on = false;
    applyPlan();
    runner.startMega();
    setView((n) => n + 1);
  }

  function restart() {
    pilot.on = false;
    const wasMega = runner.mode === "mega" || runner.mega !== null;
    applyPlan();
    if (wasMega) runner.startMega();
    else runner.restart();
    setView((n) => n + 1);
  }

  function toggleAxis(key: AxisKey) {
    setAxes((current) => (current.includes(key) ? current.filter((item) => item !== key) : [...current, key]));
  }

  function openCard(card: SweepCard) {
    const saved = loadLab();
    saveLab(ignoreArchive ? [] : saved.archive, card.config);
    void navigate({ to: "/" });
  }

  const highlightIds = new Set(mega?.highlights.map((card) => card.id) ?? []);
  const latest = mega?.recent.filter((card) => !highlightIds.has(card.id)) ?? [];

  return (
    <main className="min-h-dvh bg-ink px-3 py-3 text-bone md:px-5 md:py-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <LabBrand />
      </header>

      <section className="mx-auto mt-4 max-w-6xl">
        <p className="text-xs tracking-widest text-mist uppercase">Sweep</p>
        <h1 className="mt-1 font-display text-4xl leading-tight font-medium italic">Recipe walk</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-pretty text-mist">
          Each card is one configuration. The reading under the title says whether any of it is morphic
          resonance. Autopilot changes the kind of sweep. Mega run stays open until a batch wins:
          a 64-seed sign test, then the naive retest and the dose curve. A miss does not end it, and
          neither does finishing a pass. It stays on this page until you stop it.
        </p>

        <VerdictBanner
          cards={cards}
          confirm={runner.confirm}
          history={mega ? [] : pilot.log}
          running={status === "running" || status === "paused"}
          autopilot={pilot.on}
          campaign={pilot.campaign}
          reason={pilot.reason}
          grokStatus={pilot.grokStatus}
          mega={mega}
        />

        <div className="mt-4 flex flex-wrap gap-2">
          <Choice pressed={mode === "seek" && runner.mode !== "mega"} onClick={() => setMode("seek")} label="Goal seek" disabled={locked} />
          <Choice pressed={mode === "grid" && runner.mode !== "mega"} onClick={() => setMode("grid")} label="Grid" disabled={locked} />
          <Choice
            pressed={mode === "confirm" && runner.mode !== "mega"}
            onClick={() => setMode("confirm")}
            label="Confirmatory"
            disabled={locked}
          />
          {runner.mode === "mega" ? <Choice pressed label="Mega run" disabled onClick={() => undefined} /> : null}
        </div>

        <div className="mt-4 grid gap-3 rounded-lab border border-line bg-panel p-3 md:grid-cols-2">
          <div className="flex flex-col gap-3">
            {mode === "seek" ? (
              <label className="flex flex-col gap-1 text-xs text-mist">
                Walk toward
                <select
                  className="h-11 rounded-full border border-line bg-ink px-3 text-sm text-bone"
                  value={goal}
                  disabled={locked}
                  onChange={(event) => setGoal(event.target.value as SeekGoal)}
                >
                  <option value="armed">The armed band (1–12% flips)</option>
                  <option value="gap">A wider specificity gap</option>
                </select>
              </label>
            ) : null}
            <label className="flex flex-col gap-1 text-xs text-mist">
              Pattern
              <select
                className="h-11 rounded-full border border-line bg-ink px-3 text-sm text-bone"
                value={preset}
                disabled={locked}
                onChange={(event) => setPreset(event.target.value as PresetId)}
              >
                {PRESETS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <Range
              label="Generations per card"
              min={20}
              max={300}
              step={10}
              value={generations}
              display={String(generations)}
              disabled={locked}
              onChange={setGenerations}
            />
            {mode !== "confirm" ? (
              <Range
                label="Sweep step"
                min={1}
                max={25}
                step={1}
                value={granularity}
                display={`${granularity}% of each slider`}
                disabled={locked}
                onChange={setGranularity}
              />
            ) : (
              <div>
                <p className="text-xs text-mist">Seeds, derived from the hash. 64 is the published size.</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {[8, 16, 32, 64].map((count) => (
                    <Choice
                      key={count}
                      pressed={seedCount === count}
                      label={String(count)}
                      disabled={locked}
                      onClick={() => setSeedCount(count)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
          <div>
            <p className="text-xs text-mist">
              {mode === "confirm"
                ? "The batch freezes the sliders as they are now. It does not walk them."
                : "Axes in the walk. At 1% a full factorial is huge, so the grid falls back to one axis at a time, capped at 36 cards. Mega run ignores these toggles: it sorts every slider toward a score, then fans out."}
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              {AXES.map((axis) => (
                <Choice
                  key={axis.key}
                  pressed={axes.includes(axis.key)}
                  label={axis.label}
                  disabled={locked || mode === "confirm"}
                  onClick={() => toggleAxis(axis.key)}
                />
              ))}
              <Choice
                pressed={sweepSize}
                label="Board size"
                disabled={locked || mode === "confirm"}
                onClick={() => setSweepSize((value) => !value)}
              />
              <Choice
                pressed={sweepInnate}
                label="Innate on/off"
                disabled={locked || mode === "confirm"}
                onClick={() => setSweepInnate((value) => !value)}
              />
              <Choice
                pressed={ignoreArchive}
                label="Ignore archive"
                disabled={locked}
                onClick={() => setIgnoreArchive((value) => !value)}
              />
            </div>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {status === "running" ? (
            <button
              type="button"
              className="inline-flex h-11 items-center gap-2 rounded-full bg-amber px-4 text-sm font-medium text-ink"
              onClick={() => {
                runner.pause();
                setView((n) => n + 1);
              }}
            >
              <Pause className="size-4" /> Pause
            </button>
          ) : status === "paused" ? (
            <button
              type="button"
              className="inline-flex h-11 items-center gap-2 rounded-full bg-amber px-4 text-sm font-medium text-ink"
              onClick={() => {
                runner.resume();
                setView((n) => n + 1);
              }}
            >
              <Play className="size-4" /> Resume
            </button>
          ) : (
            <button
              type="button"
              className="inline-flex h-11 items-center gap-2 rounded-full bg-amber px-4 text-sm font-medium text-ink"
              onClick={start}
            >
              <Play className="size-4" /> Start
            </button>
          )}
          <button
            type="button"
            className="inline-flex h-11 items-center gap-2 rounded-full border border-amber bg-ink px-3 text-sm text-amber disabled:opacity-40"
            disabled={locked}
            onClick={launchAutopilot}
          >
            <Sparkles className="size-4" /> Autopilot
          </button>
          <button
            type="button"
            className="inline-flex h-11 items-center gap-2 rounded-full border border-amber bg-ink px-3 text-sm text-amber disabled:opacity-40"
            disabled={locked}
            onClick={launchMega}
          >
            <Layers className="size-4" /> Mega run
          </button>
          <button
            type="button"
            className="inline-flex h-11 items-center gap-2 rounded-full border border-line bg-panel-2 px-3 text-sm text-bone disabled:opacity-40"
            disabled={status === "idle" && !pilot.on}
            onClick={stopAll}
          >
            <Square className="size-4" /> Stop
          </button>
          <button
            type="button"
            className="inline-flex h-11 items-center gap-2 rounded-full border border-line bg-panel-2 px-3 text-sm text-bone"
            onClick={restart}
          >
            <RotateCcw className="size-4" /> Restart
          </button>
          <p className="text-sm text-mist tabular-nums" data-sweep-progress="">
            {mega ? megaProgress(mega) : `${cards.length}${runner.planned ? ` / ${runner.planned}` : ""} cards`}
            {status === "running" && !mega && runner.currentLabel
              ? ` · ${pilot.on ? pilot.campaign : runner.currentLabel} · gen ${runner.gen}`
              : status === "running" && mega
                ? ` · gen ${runner.gen}`
                : pilot.on
                  ? ` · ${pilot.campaign || "autopilot"}`
                  : ""}
          </p>
        </div>
        <p className="mt-2 text-sm text-pretty text-bone">{runner.note}</p>
        {!mega && status === "idle" ? (
          <p className="mt-1 text-xs text-mist tabular-nums">
            Mega run at {granularity}% sorts {formatCount(megaCount)} configurations toward the armed band. A wide armed gap freezes that recipe for a 64-seed sign test, then a naive retest and a dose curve. None of that is morphic resonance.
          </p>
        ) : null}
        {mega && mega.focus ? <p className="mt-1 line-clamp-3 text-xs text-mist">{mega.focus}</p> : null}
        <span className="sr-only">{view}</span>

        {mega?.proof ? (
          <ConfirmBlock result={mega.proof} kicker="64-seed sign test" />
        ) : runner.confirm ? (
          <ConfirmBlock result={runner.confirm} />
        ) : null}
        {mega?.naive ? <ConfirmBlock result={mega.naive} kicker="Naive retest · innate off · coupling 0" /> : null}
        {mega?.dose ? <DoseBlock dose={mega.dose} /> : null}

        {showCharts ? <Charts cards={cards} /> : null}
        {mega && mega.done > 0n ? <MegaCharts tally={mega.tally} trace={mega.trace} /> : null}

        {mega ? (
          <div className="mt-4 grid gap-4">
            <CardGrid title="Widest gaps kept" cards={mega.highlights} onOpen={openCard} />
            <CardGrid title="Latest" cards={latest} onOpen={openCard} />
            <p className="text-xs text-mist">
              Older pictures are dropped. The tally above counts every configuration, not just the cards still on screen.
            </p>
          </div>
        ) : (
          <div className="mt-4">
            <CardGrid cards={cards} onOpen={openCard} />
          </div>
        )}
      </section>
    </main>
  );
}

function megaProgress(mega: MegaState): string {
  if (mega.stage === "confirm") return `64-seed sign test · ${mega.ladderDone}/${mega.ladderTotal}`;
  if (mega.stage === "naive") return `Naive 64 · innate off · ${mega.ladderDone}/${mega.ladderTotal}`;
  if (mega.stage === "dose") return `Dose curve · ${mega.ladderDone}/${mega.ladderTotal}`;
  if (mega.stage === "done") {
    // "done" is also where a stop during the ladder lands; only a learned dose curve won.
    return mega.dose?.learned
      ? `Won the ladder · ${formatCount(mega.done)} illustration tries`
      : `Stopped · ${formatCount(mega.done)} illustration tries`;
  }
  const hunt = mega.queued > 0 ? ` · ${mega.queued} waiting for a 64-seed test` : mega.trials > 0 ? " · still open" : "";
  const motion = mega.phase === "fan" ? "fanning out" : mega.phase === "grid" ? "combing the grid" : "bouncing";
  return `${formatCount(mega.done)} tried · ${mega.hits} scored · ${motion}${hunt}`;
}

function CardGrid({
  title,
  cards,
  onOpen,
}: {
  title?: string;
  cards: SweepCard[];
  onOpen: (card: SweepCard) => void;
}) {
  if (title && cards.length === 0) return null;
  return (
    <div>
      {title ? <h2 className="font-display text-2xl italic">{title}</h2> : null}
      <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <article key={card.id} className="overflow-hidden rounded-lab border border-line bg-panel">
            {card.image ? (
              <img src={card.image} alt="" className="h-24 w-full bg-ink object-contain" />
            ) : (
              <div className="h-24 bg-ink" />
            )}
            <div className="p-3">
              <div className="flex items-baseline justify-between gap-2">
                <h3 className="font-display text-2xl leading-none italic capitalize">{card.level}</h3>
                <p className="text-xs text-mist tabular-nums">#{card.id}</p>
              </div>
              <p className="mt-1 line-clamp-3 text-sm text-bone">{card.label}</p>
              <p className="mt-1 text-xs text-mist tabular-nums">
                flips {pct(card.flipRate)} · D* {card.dStar.toFixed(2)} · gap {card.gap.toFixed(2)} · {card.cells}² · seed {card.seed}
              </p>
              <button
                type="button"
                className="mt-2 h-10 rounded-full border border-line px-3 text-sm text-bone"
                onClick={() => onOpen(card)}
              >
                Open in the lab
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function VerdictBanner({
  cards,
  confirm,
  history,
  running,
  autopilot,
  campaign,
  reason,
  grokStatus,
  mega,
}: {
  cards: SweepCard[];
  confirm: SweepRunner["confirm"];
  history: { name: string; reading: string; specific: boolean | null }[];
  running: boolean;
  autopilot: boolean;
  campaign: string;
  reason: string;
  grokStatus: string;
  mega: MegaState | null;
}) {
  const verdict = interpret({
    cards,
    confirm,
    history,
    running: running && autopilot,
    autopilot,
    campaign,
    reason,
    mega,
  });
  const tone = verdict.resonance === "no" ? "text-mist" : "text-bone";
  return (
    <section className="mt-4 rounded-lab border border-line bg-panel px-4 py-4" aria-label="Did this find morphic resonance?">
      <p className="text-xs tracking-widest text-mist uppercase">Did this find morphic resonance?</p>
      <p className={`mt-1 font-display text-5xl leading-none italic ${tone}`}>{verdict.title}</p>
      <p className="mt-3 text-base text-pretty text-bone">{verdict.line}</p>
      <p className="mt-2 text-sm leading-relaxed text-pretty text-mist">{verdict.detail}</p>
      {grokStatus && !mega ? <p className="mt-2 text-sm text-pretty text-amber">{grokStatus}</p> : null}
      <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {verdict.chips.map((chip) => (
          <li key={chip.label} className="rounded-lg border border-line bg-ink px-2 py-2">
            <p className="text-xs tracking-wide text-mist uppercase">{chip.label}</p>
            <p className="text-base leading-tight break-all text-bone tabular-nums">{chip.value}</p>
            <p className="text-xs break-all text-mist">{chip.hint}</p>
          </li>
        ))}
      </ul>
      {history.length > 0 ? (
        <ol className="mt-3 grid gap-1 text-sm text-mist">
          {history.map((item, index) => (
            <li key={`${item.name}-${index}`} className="flex flex-wrap justify-between gap-2 border-t border-line py-1">
              <span className="text-bone">{item.name}</span>
              <span className="tabular-nums">{item.reading}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

function ConfirmBlock({
  result,
  kicker,
}: {
  result: NonNullable<SweepRunner["confirm"]>;
  kicker?: string;
}) {
  return (
    <aside className="mt-4 rounded-lab border border-amber bg-panel px-4 py-4">
      {kicker ? <p className="text-xs tracking-widest text-mist uppercase">{kicker}</p> : null}
      <p className="text-xs tracking-widest text-amber uppercase">
        {result.voided ? "Stopped early" : result.specific ? "Specific" : "Not specific"}
      </p>
      <p className="mt-2 font-display text-2xl leading-snug italic">
        {result.voided
          ? "The batch stopped before the seed list finished."
          : result.specific
            ? "The field beat both nulls. That is still the table."
            : "The field did not beat both nulls."}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-pretty text-mist">
        {result.seeds} seeds. Yoked {result.yoked.pos} favoring the field, {result.yoked.neg} against ({result.yoked.n} non-ties), p{" "}
        {result.yoked.p < 0.001 ? "< 0.001" : result.yoked.p.toFixed(3)}, median {result.yoked.median.toFixed(3)} (CI{" "}
        {result.yoked.lo.toFixed(3)} to {result.yoked.hi.toFixed(3)}). Scrambled {result.scrambled.pos} favoring the
        field, {result.scrambled.neg} against ({result.scrambled.n} non-ties), p {result.scrambled.p < 0.001 ? "< 0.001" : result.scrambled.p.toFixed(3)},
        median {result.scrambled.median.toFixed(3)} (CI {result.scrambled.lo.toFixed(3)} to {result.scrambled.hi.toFixed(3)}
        ). Ties are dropped, and medians are of the non-tied differences. Both must pass an exact two-sided sign test at α ={" "}
        {formatAlpha(result.alpha)}
        {result.alpha < 0.05 ? " (this run's share of 0.05, spent across its attempts)" : ""}, with more seeds favoring the field than
        against it.
      </p>
      <p className="mt-2 text-sm text-pretty text-bone">{result.learnedReason}</p>
      <p className="mt-2 text-xs break-all text-mist">
        First row {result.row.slice(0, 16)}… · codes ash = {result.key.ash}, birch = {result.key.birch}, cedar ={" "}
        {result.key.cedar}. The key is appended after the scores.
      </p>
    </aside>
  );
}

function DoseBlock({ dose }: { dose: DoseCurve }) {
  return (
    <aside className="mt-4 rounded-lab border border-line bg-panel px-4 py-4">
      <p className="text-xs tracking-widest text-mist uppercase">
        {dose.learned ? "Learned · still the table" : "Dose curve · Learned not reached"}
      </p>
      <p className="mt-2 text-sm text-pretty text-bone">{dose.reason}</p>
      {dose.points.length > 0 ? (
        <p className="mt-2 text-sm text-mist tabular-nums">
          Coupling {dose.coupling.toFixed(2)}.{" "}
          {dose.points.map((point) => `dose ${point.dose}: spec ${point.spec.toFixed(3)}, gap ${point.gap.toFixed(3)}`).join(" · ")}
        </p>
      ) : null}
    </aside>
  );
}

function Charts({ cards }: { cards: SweepCard[] }) {
  const levels = [
    { name: "Off", count: cards.filter((card) => card.level.startsWith("off")).length },
    { name: "Unarmed", count: cards.filter((card) => card.level.startsWith("unarmed")).length },
    { name: "Armed", count: cards.filter((card) => card.level.startsWith("armed")).length },
    { name: "Loud", count: cards.filter((card) => card.level.startsWith("loud")).length },
  ];
  const series = cards.map((card) => ({
    i: card.id,
    flips: Math.round(card.flipRate * 1000) / 10,
    gap: Math.round(card.gap * 1000) / 1000,
    dStar: Math.round(card.dStar * 100) / 100,
  }));
  return (
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      <LevelChart caption="Levels" levels={levels} />
      <figure className="rounded-lab border border-line bg-panel p-3">
        <figcaption className="font-display text-lg italic">Flips and gap along the walk</figcaption>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series}>
              <XAxis dataKey="i" stroke="#8d978f" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#8d978f" fontSize={12} width={32} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={chartTip} />
              <Line type="monotone" dataKey="flips" name="flips %" stroke="#3dba86" dot={false} strokeWidth={1.75} isAnimationActive={false} />
              <Line type="monotone" dataKey="gap" name="gap" stroke="#e39a3c" dot={false} strokeWidth={1.75} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </figure>
    </div>
  );
}

function MegaCharts({
  tally,
  trace,
}: {
  tally: MegaState["tally"];
  trace: MegaState["trace"];
}) {
  const levels = [
    { name: "Off", count: tally.off },
    { name: "Unarmed", count: tally.unarmed },
    { name: "Armed", count: tally.armed },
    { name: "Loud", count: tally.loud },
  ];
  const series = trace.map((point, index) => ({
    i: index + 1,
    flips: Math.round(point.rate * 1000) / 10,
    gap: point.gap,
  }));
  return (
    <div className="mt-4 grid gap-3 md:grid-cols-2">
      <LevelChart caption="Tries so far" levels={levels} wide />
      <figure className="rounded-lab border border-line bg-panel p-3">
        <figcaption className="font-display text-lg italic">Recent flips and gap</figcaption>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series}>
              <XAxis dataKey="i" stroke="#8d978f" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#8d978f" fontSize={12} width={32} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={chartTip} />
              <Line type="monotone" dataKey="flips" name="flips %" stroke="#3dba86" dot={false} strokeWidth={1.75} isAnimationActive={false} />
              <Line type="monotone" dataKey="gap" name="gap" stroke="#e39a3c" dot={false} strokeWidth={1.75} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </figure>
    </div>
  );
}

function LevelChart({
  caption,
  levels,
  wide,
}: {
  caption: string;
  levels: { name: string; count: number }[];
  wide?: boolean;
}) {
  return (
    <figure className="rounded-lab border border-line bg-panel p-3">
      <figcaption className="font-display text-lg italic">{caption}</figcaption>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={levels}>
            <XAxis dataKey="name" stroke="#8d978f" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis
              allowDecimals={false}
              stroke="#8d978f"
              fontSize={12}
              width={wide ? 52 : 28}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip contentStyle={chartTip} />
            <Bar dataKey="count" fill="#e39a3c" radius={4} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}

function Choice({
  pressed,
  label,
  onClick,
  disabled,
}: {
  pressed: boolean;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex h-10 items-center rounded-full border px-3 text-sm disabled:opacity-40 ${
        pressed ? "border-life bg-panel-2 text-bone" : "border-line bg-ink text-mist"
      }`}
    >
      {label}
    </button>
  );
}

function Range({
  label,
  min,
  max,
  step,
  value,
  display,
  disabled,
  onChange,
}: {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  display: string;
  disabled?: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-mist">
      <span className="flex items-baseline justify-between gap-3">
        <span>{label}</span>
        <span className="text-bone tabular-nums">{display}</span>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(Number(event.target.value))}
        className="h-11 accent-amber"
      />
    </label>
  );
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function formatAlpha(alpha: number) {
  return alpha >= 0.01 ? alpha.toFixed(3) : alpha.toPrecision(2);
}
