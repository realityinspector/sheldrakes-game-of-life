import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { Eraser, Link2, Pause, Pencil, Play, Shuffle, SkipForward, Trash2 } from "lucide-react";
import * as Slider from "@radix-ui/react-slider";
import { Area, AreaChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import {
  cellFromPointer,
  DEFAULT_CONFIG,
  drawBoard,
  MorphicLab,
  PATCH_CELLS,
  type BoardId,
  type CrystalView,
  type FieldConfig,
  type Hud,
  type PresetId,
  type RunSnapshot,
} from "@/sim/engine";
import { FindingsPanel, ResonanceBanner } from "@/components/findings-panel";
import { LabBrand } from "@/components/lab-nav";
import { emptyBook, loadBook, review, saveBook, type Book, type ReviewMode } from "@/sim/findings";
import { loadLab, saveLab } from "@/sim/storage";

const PRESETS: { id: PresetId; label: string }[] = [
  { id: "soup", label: "Primordial soup" },
  { id: "rpen", label: "R-pentomino" },
  { id: "acorn", label: "Acorn" },
  { id: "gliders", label: "Glider flock" },
  { id: "pulsar", label: "Pulsar" },
  { id: "garden", label: "Still garden" },
  { id: "gun", label: "Gosper gun" },
];

const EMPTY_HUD: Hud = {
  gen: 0,
  popC: 0,
  popM: 0,
  popY: 0,
  popS: 0,
  influence: 0,
  meanInfluence: 0,
  diverge: 0,
  dStar: 0,
  gap: 0,
  level: "unarmed",
  provisional: true,
  exploratory: false,
  seed: 0,
  playing: true,
  archiveCount: 0,
};

export function Laboratory() {
  const fieldRef = useRef<HTMLCanvasElement>(null);
  const controlRef = useRef<HTMLCanvasElement>(null);
  const yokedRef = useRef<HTMLCanvasElement>(null);
  const scrambledRef = useRef<HTMLCanvasElement>(null);
  const labRef = useRef<MorphicLab | null>(null);
  const [hud, setHud] = useState<Hud>(EMPTY_HUD);
  const [crystals, setCrystals] = useState<CrystalView[]>([]);
  const [history, setHistory] = useState<MorphicLab["history"]>([]);
  const [config, setConfig] = useState<FieldConfig>(DEFAULT_CONFIG);
  const [preset, setPreset] = useState<PresetId>("soup");
  const [brush, setBrush] = useState<"paint" | "erase">("paint");
  const [mirror, setMirror] = useState(true);
  const [ready, setReady] = useState(false);
  const [book, setBook] = useState<Book>(emptyBook);
  const [snap, setSnap] = useState<RunSnapshot | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const bookRef = useRef<Book>(emptyBook());
  const reviewedGen = useRef(0);
  const commitRef = useRef<(lab: MorphicLab, mode: ReviewMode) => void>(() => {});

  useEffect(() => {
    const saved = loadLab();
    const storedBook = loadBook();
    bookRef.current = storedBook;
    setBook(storedBook);
    const size = Math.max(16, Math.min(96, Math.round(saved.settings.cells ?? 48)));
    const lab = new MorphicLab(size, saved.archive, {
      ...DEFAULT_CONFIG,
      ...saved.settings,
      cells: size,
    });
    labRef.current = lab;
    publish(lab);

    let raf = 0;
    let last = performance.now();
    let acc = 0;
    let hudAcc = 0;
    let dead = false;

    const frame = (now: number) => {
      if (dead) return;
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const current = labRef.current;
      if (!current) return;
      if (current.playing) {
        acc += dt;
        const interval = 1 / current.config.speed;
        let guard = 0;
        while (acc >= interval && guard++ < 4) {
          current.step();
          acc -= interval;
        }
        if (guard >= 4) acc = 0;
      }
      paintCanvas(fieldRef.current, current, "field");
      paintCanvas(controlRef.current, current, "control");
      paintCanvas(yokedRef.current, current, "yoked");
      paintCanvas(scrambledRef.current, current, "scrambled");
      hudAcc += dt;
      if (hudAcc > 0.18) {
        hudAcc = 0;
        setHud(current.hud());
        setCrystals(current.crystalViews());
        setHistory(current.history.slice(-120));
        setSnap(current.snapshot());
        if (current.gen >= reviewedGen.current + 50) {
          reviewedGen.current = current.gen - (current.gen % 50);
          commitRef.current(current, "checkpoint");
        }
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    const onKey = (event: KeyboardEvent) => {
      const target = event.target;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement
      ) {
        return;
      }
      const current = labRef.current;
      if (!current) return;
      if (event.code === "Space") {
        event.preventDefault();
        current.playing = !current.playing;
        publish(current);
      } else if (event.key === "." || event.key === "n" || event.key === "N") {
        current.playing = false;
        current.step();
        publish(current);
      } else if (event.key === "r" || event.key === "R") {
        if (current.gen >= 20) commitRef.current(current, "close");
        current.randomize();
        reviewedGen.current = 0;
        publish(current);
      } else if (event.key === "c" || event.key === "C") {
        if (current.gen >= 20) commitRef.current(current, "close");
        current.clearBoards();
        reviewedGen.current = 0;
        publish(current);
      }
    };
    window.addEventListener("keydown", onKey);
    const timer = window.setInterval(() => {
      const current = labRef.current;
      if (current) saveLab(current.toArchive(), { ...current.config, cells: current.w });
    }, 2500);

    return () => {
      dead = true;
      cancelAnimationFrame(raf);
      window.removeEventListener("keydown", onKey);
      window.clearInterval(timer);
      const current = labRef.current;
      if (current) saveLab(current.toArchive(), { ...current.config, cells: current.w });
    };
  }, []);

  function publish(lab: MorphicLab) {
    setHud(lab.hud());
    setCrystals(lab.crystalViews());
    setHistory(lab.history.slice(-120));
    setSnap(lab.snapshot());
    setConfig({ ...lab.config, cells: lab.w });
    setPreset(lab.preset);
    setBrush(lab.brush);
    setMirror(lab.mirror);
    setReady(true);
  }

  commitRef.current = (lab, mode) => {
    const shot = lab.snapshot();
    const result = review(bookRef.current, shot, mode);
    bookRef.current = result.book;
    saveBook(result.book);
    setBook(result.book);
    for (const item of result.fresh) {
      if (item.finding.kind !== "habit" || item.finding.mask == null) continue;
      const habit = shot.habits.find((candidate) => candidate.mask === item.finding.mask);
      if (!habit) continue;
      lab.remember({
        name: habit.name,
        mask: habit.mask,
        nextMask: habit.nextMask,
        nextCenter: habit.nextCenter,
        strength: habit.strength,
      });
    }
    if (result.fresh.length > 0) setNotice(result.fresh[0].finding.claim);
    saveLab(lab.toArchive(), { ...lab.config, cells: lab.w });
  };

  function restart(action: (lab: MorphicLab) => void) {
    const lab = labRef.current;
    if (!lab) return;
    if (lab.gen >= 20) commitRef.current(lab, "close");
    action(lab);
    reviewedGen.current = 0;
    publish(lab);
  }

  function patchConfig(patch: Partial<FieldConfig>) {
    const lab = labRef.current;
    if (!lab) return;
    lab.setConfig(patch);
    setConfig({ ...lab.config, cells: lab.w });
    saveLab(lab.toArchive(), { ...lab.config, cells: lab.w });
  }

  function paintAt(canvas: HTMLCanvasElement, which: BoardId, clientX: number, clientY: number) {
    const lab = labRef.current;
    if (!lab) return;
    const cell = cellFromPointer(canvas, clientX, clientY, lab.w);
    if (!cell) return;
    lab.paint(which, cell.x, cell.y, mirror);
    setHud(lab.hud());
  }

  return (
    <main className="flex min-h-dvh flex-col gap-3 bg-ink px-3 py-3 text-bone md:px-5 md:py-4">
      <header className="flex shrink-0 flex-wrap items-end justify-between gap-3">
        <LabBrand />
        <dl className="grid grid-cols-2 gap-x-5 gap-y-1 sm:grid-cols-4">
          <Stat label="Generation" value={ready ? String(hud.gen) : "—"} />
          <Stat label="D*" value={ready ? hud.dStar.toFixed(2) : "—"} />
          <Stat label="Flips" value={ready ? pct(hud.meanInfluence) : "—"} emphasis />
          <Stat label="Gap" value={ready ? hud.gap.toFixed(2) : "—"} />
        </dl>
      </header>

      <ResonanceBanner book={book} snap={snap} />

      <section className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Board
          title="Field"
          hint="Memory may overwrite the center"
          pop={ready ? hud.popM : 0}
          canvasRef={fieldRef}
          onPaint={(canvas, x, y) => paintAt(canvas, "field", x, y)}
        />
        <Board
          title="Control"
          hint="Conway only. Never reads the coins"
          pop={ready ? hud.popC : 0}
          canvasRef={controlRef}
          onPaint={(canvas, x, y) => paintAt(canvas, "control", x, y)}
        />
        <Board
          title="Yoked"
          hint="Same number of flips, random places"
          pop={ready ? hud.popY : 0}
          canvasRef={yokedRef}
          onPaint={(canvas, x, y) => paintAt(canvas, "yoked", x, y)}
        />
        <Board
          title="Scrambled"
          hint="Same table, cells permuted"
          pop={ready ? hud.popS : 0}
          canvasRef={scrambledRef}
          onPaint={(canvas, x, y) => paintAt(canvas, "scrambled", x, y)}
        />
      </section>

      <section className="shrink-0" aria-label="Memory crystals">
        <div className="mb-2 flex items-baseline justify-between gap-3">
          <h2 className="font-display text-lg italic">Crystals</h2>
          <p className="text-xs text-mist">
            {crystals.length} remembered forms
            {hud.archiveCount ? ` · ${hud.archiveCount} carried from earlier runs` : ""}
            {hud.exploratory ? " · exploratory" : ""}
          </p>
        </div>
        <div className="lab-scroll flex gap-2 overflow-x-auto pb-1">
          {crystals.length === 0 ? (
            <p className="text-sm text-mist">The field has not crystallized a form yet.</p>
          ) : (
            crystals.map((crystal) => <CrystalChip key={crystal.id} crystal={crystal} />)
          )}
        </div>
      </section>

      <FindingsPanel
        book={book}
        snap={snap}
        notice={notice}
        onClear={() => {
          const cleared = emptyBook();
          bookRef.current = cleared;
          reviewedGen.current = labRef.current?.gen ?? 0;
          saveBook(cleared);
          setBook(cleared);
          setNotice(null);
        }}
      />

      <section className="grid shrink-0 gap-3 rounded-lab border border-line bg-panel p-3 md:grid-cols-[minmax(0,1.3fr)_minmax(0,0.7fr)]">
        <div className="flex min-w-0 flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="inline-flex h-11 items-center gap-2 rounded-full bg-amber px-4 text-sm font-medium text-ink"
              onClick={() => {
                const lab = labRef.current;
                if (!lab) return;
                lab.playing = !lab.playing;
                setHud(lab.hud());
              }}
            >
              {hud.playing ? <Pause className="size-4" /> : <Play className="size-4" />}
              {hud.playing ? "Pause" : "Play"}
            </button>
            <button
              type="button"
              className="inline-flex h-11 items-center gap-2 rounded-full border border-line bg-panel-2 px-3 text-sm text-bone"
              onClick={() => {
                const lab = labRef.current;
                if (!lab) return;
                lab.playing = false;
                lab.step();
                publish(lab);
              }}
            >
              <SkipForward className="size-4" />
              Step
            </button>
            <button
              type="button"
              className="inline-flex h-11 items-center gap-2 rounded-full border border-line bg-panel-2 px-3 text-sm text-bone"
              onClick={() => restart((lab) => lab.randomize())}
            >
              <Shuffle className="size-4" />
              New seed
            </button>
            <label className="inline-flex h-11 items-center">
              <span className="sr-only">Starting pattern</span>
              <select
                className="h-11 rounded-full border border-line bg-ink px-3 text-sm text-bone"
                value={preset}
                onChange={(event) => {
                  const next = event.target.value as PresetId;
                  restart((lab) => lab.reseed(next, lab.seed));
                }}
              >
                {PRESETS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <Toggle
                pressed={brush === "paint"}
                onClick={() => {
                  const lab = labRef.current;
                  if (!lab) return;
                  lab.brush = "paint";
                  setBrush("paint");
                }}
                label="Paint"
                icon={<Pencil className="size-4" />}
              />
              <Toggle
                pressed={brush === "erase"}
                onClick={() => {
                  const lab = labRef.current;
                  if (!lab) return;
                  lab.brush = "erase";
                  setBrush("erase");
                }}
                label="Erase"
                icon={<Eraser className="size-4" />}
              />
              <Toggle
                pressed={mirror}
                onClick={() => {
                  const lab = labRef.current;
                  if (!lab) return;
                  lab.mirror = !lab.mirror;
                  if (!lab.mirror) lab.touch();
                  setMirror(lab.mirror);
                  setHud(lab.hud());
                }}
                label="Lock boards"
                icon={<Link2 className="size-4" />}
              />
              <Toggle
                pressed={config.innate}
                onClick={() =>
                  restart((lab) => {
                    lab.setConfig({ innate: !lab.config.innate });
                    lab.reseed(lab.preset, lab.seed);
                  })
                }
                label="Innate"
              />
              <Toggle
                pressed={config.wrap}
                onClick={() => patchConfig({ wrap: !config.wrap })}
                label="Wrap"
              />
            </div>
          </div>

          <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
            <FieldSlider
              label="Field strength"
              value={config.fieldStrength}
              min={0}
              max={1}
              step={0.01}
              display={config.fieldStrength.toFixed(2)}
              onChange={(value) => patchConfig({ fieldStrength: value })}
            />
            <FieldSlider
              label="Temporal decay"
              value={config.temporalDecay}
              min={0}
              max={0.4}
              step={0.005}
              display={config.temporalDecay.toFixed(3)}
              onChange={(value) => patchConfig({ temporalDecay: value })}
            />
            <FieldSlider
              label="Similarity"
              value={config.similarityThreshold}
              min={0.4}
              max={0.92}
              step={0.01}
              display={config.similarityThreshold.toFixed(2)}
              onChange={(value) => patchConfig({ similarityThreshold: value })}
            />
            <FieldSlider
              label="Past-run coupling"
              value={config.coupling}
              min={0}
              max={1}
              step={0.01}
              display={config.coupling.toFixed(2)}
              onChange={(value) => patchConfig({ coupling: value })}
            />
            <FieldSlider
              label="Sharpen"
              value={config.influenceExponent}
              min={1}
              max={4}
              step={0.1}
              display={config.influenceExponent.toFixed(1)}
              onChange={(value) => patchConfig({ influenceExponent: value })}
            />
            <FieldSlider
              label="Soup density"
              value={config.density}
              min={0.05}
              max={0.55}
              step={0.01}
              display={config.density.toFixed(2)}
              onChange={(value) => patchConfig({ density: value })}
            />
            <FieldSlider
              label="Speed"
              value={config.speed}
              min={1}
              max={30}
              step={1}
              display={`${Math.round(config.speed)} /s`}
              onChange={(value) => patchConfig({ speed: value })}
            />
            <FieldSlider
              label="Crystal capacity"
              value={config.crystalCount}
              min={6}
              max={18}
              step={1}
              display={String(Math.round(config.crystalCount))}
              onChange={(value) => patchConfig({ crystalCount: Math.round(value) })}
            />
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-2">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg italic">Populations</h2>
            <p className="text-xs text-mist tabular-nums">
              seed {ready ? hud.seed : "—"} · {ready ? `${labRef.current?.w ?? 48}²` : ""}
            </p>
          </div>
          <div className="h-28 min-w-0">
            {ready && history.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={history} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
                  <YAxis hide domain={[0, "auto"]} />
                  <Tooltip
                    cursor={{ stroke: "var(--color-line)" }}
                    contentStyle={{
                      background: "var(--color-ink)",
                      border: "1px solid var(--color-line)",
                      borderRadius: 10,
                      color: "var(--color-bone)",
                      fontSize: 12,
                    }}
                    formatter={(value, name) => [
                      typeof value === "number" ? Math.round(value) : value,
                      name === "popM" ? "Field" : "Control",
                    ]}
                    labelFormatter={(label) => `Generation ${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="popC"
                    name="popC"
                    stroke="var(--color-mist)"
                    fill="transparent"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="popM"
                    name="popM"
                    stroke="var(--color-life)"
                    fill="var(--color-life)"
                    fillOpacity={0.16}
                    strokeWidth={1.75}
                    dot={false}
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="grid h-full place-items-center text-sm text-mist">
                The trace appears as generations pass.
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-mist">
            <span className="inline-flex items-center gap-2">
              <i className="inline-block size-2 rounded-full bg-life" /> Field
              <i className="ml-2 inline-block size-2 rounded-full bg-mist" /> Control
              <i className="ml-2 inline-block size-2 rounded-full bg-amber" /> Override
            </span>
            <button
              type="button"
              className="inline-flex h-9 items-center gap-1.5 text-mist"
              onClick={() => {
                const lab = labRef.current;
                if (!lab) return;
                lab.clearMemory();
                saveLab([], { ...lab.config, cells: lab.w });
                publish(lab);
              }}
            >
              <Trash2 className="size-4" />
              Forget past runs
            </button>
          </div>
        </div>
      </section>

      <details className="shrink-0 rounded-lab border border-line bg-panel px-3 py-2 text-sm text-mist">
        <summary className="cursor-pointer py-1 text-bone">Field notes</summary>
        <div className="grid gap-2 pt-2 pb-1 leading-relaxed text-pretty md:grid-cols-2">
          <p>
            Four boards start from one seed and obey Conway’s rule. Control never reads the random
            stream. The field may overwrite a cell after consulting crystals. Yoked makes the same
            number of flips in random occupied neighborhoods. Scrambled uses the same table with
            every crystal’s cells permuted. Amber is an effective flip.
          </p>
          <p>
            A run on this page is a demonstration. Armed means the table is writing at the right
            size. It is not a finding that morphic resonance happened. Specific needs the batch in
            Sweep. Drag a board to paint. Unlocking the boards, or moving a slider after generation
            0, marks the run exploratory. Space plays, period steps, R reseeds.
          </p>
        </div>
      </details>
    </main>
  );
}

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function Stat({ label, value, emphasis }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <div className="min-w-16">
      <dt className="text-xs tracking-wide text-mist uppercase">{label}</dt>
      <dd className={`text-lg leading-tight tabular-nums ${emphasis ? "text-amber" : "text-bone"}`}>
        {value}
      </dd>
    </div>
  );
}

function Board({
  title,
  hint,
  pop,
  canvasRef,
  onPaint,
}: {
  title: string;
  hint: string;
  pop: number;
  canvasRef: RefObject<HTMLCanvasElement | null>;
  onPaint: (canvas: HTMLCanvasElement, x: number, y: number) => void;
}) {
  return (
    <article className="flex h-72 flex-col overflow-hidden rounded-lab border border-line bg-panel md:h-[34vh] md:min-h-64">
      <header className="flex items-baseline justify-between gap-3 px-3 py-2">
        <div className="min-w-0">
          <h2 className="font-display text-xl leading-none italic">{title}</h2>
          <p className="mt-1 truncate text-xs text-mist">{hint}</p>
        </div>
        <p className="text-sm text-bone tabular-nums">{pop}</p>
      </header>
      <div className="relative min-h-0 flex-1 bg-ink">
        <canvas
          ref={canvasRef}
          className="absolute inset-0 h-full w-full touch-none"
          onPointerDown={(event) => {
            event.currentTarget.setPointerCapture(event.pointerId);
            onPaint(event.currentTarget, event.clientX, event.clientY);
          }}
          onPointerMove={(event) => {
            if (event.buttons !== 1) return;
            onPaint(event.currentTarget, event.clientX, event.clientY);
          }}
        />
      </div>
    </article>
  );
}

function CrystalChip({ crystal }: { crystal: CrystalView }) {
  const cells = [];
  for (let i = 0; i < PATCH_CELLS; i++) {
    const on = (crystal.mask & (1 << i)) !== 0;
    cells.push(<span key={i} className={on ? "bg-life" : "bg-ink"} />);
  }
  const origin =
    crystal.origin === "innate" ? "Innate" : crystal.origin === "resonant" ? "Carried" : "Echo";
  return (
    <article className="flex w-40 shrink-0 items-center gap-2 rounded-lg border border-line bg-panel-2 p-2">
      <div className="grid size-12 shrink-0 grid-cols-5 gap-px" aria-hidden="true">
        {cells}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-bone">{crystal.name}</p>
        <p className="text-xs tracking-wide text-mist uppercase">{origin}</p>
        <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-line">
          <div
            className="h-full bg-amber"
            style={{ width: `${Math.round(crystal.strength * 100)}%` }}
          />
        </div>
      </div>
    </article>
  );
}

function Toggle({
  pressed,
  onClick,
  label,
  icon,
}: {
  pressed: boolean;
  onClick: () => void;
  label: string;
  icon?: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`inline-flex h-11 items-center gap-1.5 rounded-full border px-3 text-sm ${
        pressed ? "border-life bg-panel-2 text-bone" : "border-line bg-ink text-mist"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function FieldSlider({
  label,
  value,
  min,
  max,
  step,
  display,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  display: string;
  onChange: (value: number) => void;
}) {
  const [live, setLive] = useState(false);
  useEffect(() => {
    setLive(true);
  }, []);
  return (
    <label className="flex flex-col gap-1.5">
      <span className="flex items-baseline justify-between gap-3 text-xs text-mist">
        <span>{label}</span>
        <span className="text-bone tabular-nums">{display}</span>
      </span>
      {live ? (
        <Slider.Root
          className="relative flex h-11 touch-none items-center"
          min={min}
          max={max}
          step={step}
          value={[value]}
          onValueChange={([next]) => onChange(next)}
        >
          <Slider.Track className="relative h-1 grow rounded-full bg-line">
            <Slider.Range className="absolute h-full rounded-full bg-amber" />
          </Slider.Track>
          <Slider.Thumb
            className="block size-5 rounded-full border border-line bg-bone shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-amber"
            aria-label={label}
          />
        </Slider.Root>
      ) : (
        <div className="relative flex h-11 items-center" aria-hidden="true">
          <div className="h-1 w-full rounded-full bg-line" />
        </div>
      )}
    </label>
  );
}

function paintCanvas(canvas: HTMLCanvasElement | null, lab: MorphicLab, which: BoardId) {
  if (!canvas) return;
  const cssW = canvas.clientWidth;
  const cssH = canvas.clientHeight;
  if (cssW < 2 || cssH < 2) return;
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const bw = Math.max(1, Math.floor(cssW * dpr));
  const bh = Math.max(1, Math.floor(cssH * dpr));
  if (canvas.width !== bw || canvas.height !== bh) {
    canvas.width = bw;
    canvas.height = bh;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  drawBoard(ctx, lab, which, cssW, cssH);
}
