import type { ReactNode } from "react";
import { LabBrand } from "@/components/lab-nav";

export function MethodPage() {
  return (
    <main className="min-h-dvh bg-ink px-3 py-3 text-bone md:px-5 md:py-4">
      <header className="flex shrink-0 flex-wrap items-end justify-between gap-3">
        <LabBrand titleAsHeading={false} />
      </header>

      <article className="mx-auto mt-6 max-w-3xl pb-16">
        <p className="text-xs tracking-widest text-mist uppercase">Method</p>
        <h1 className="mt-1 font-display text-4xl leading-tight font-medium italic">
          What a result is allowed to mean
        </h1>
        <p className="mt-4 text-lg leading-relaxed text-pretty text-bone">
          This laboratory does not detect morphic resonance. It runs Conway’s Game of Life from one
          seed on four boards. One board may consult a table of remembered forms and overwrite
          cells. One never overwrites. Two overwrite at the same rate without the table’s content.
          A result is a statement about the table, and it comes in levels. Armed: the table is
          writing cells. Specific: what it writes depends on what it remembers. Learned: what it
          remembers came from history, not from what was installed. There is a further claim this
          program cannot make. The last section says why.
        </p>

        <Section title="Why the old score was retired">
          <p>
            The old Yes needed the board at least 8% different from the control and memory
            overwriting 1–12% of occupied neighborhoods. The first condition did not measure
            memory. Life on a 48 by 48 torus is chaotic. In a check of 100 random soups, flipping
            one cell at generation 0 left the boards a median 18% apart at generation 80, and at
            least 8% apart in 99 of 100. Two unrelated boards at that density are about 18% apart
            by chance. Divergence saturates from a single cell. What it records is timing: one flip
            at generation 40 crossed 8% in 44 of 100 runs, and one flip at generation 60 crossed it
            in none. On a small pattern on an empty board the bar fails the other way: 8% is 184
            cells, more than most presets ever hold. One threshold, two meaningless outcomes.
          </p>
          <p>
            The old Yes was the influence band alone. It survives below as Armed. Raw disagreement
            is kept as D*, and D* is not a pass.
          </p>
        </Section>

        <Section title="The boards">
          <p>
            The live boards are 48 by 48 unless a sweep recipe says otherwise. All four start from
            the same seed and the same pattern, and all obey the same rule: a dead cell is born
            with three neighbors, a live cell survives with two or three. Soup and glider flocks
            wrap at the edges. The other patterns do not, unless Wrap is turned on.
          </p>
          <p>
            <strong className="font-medium text-bone">Control.</strong> Conway only. It never reads
            the random stream.
          </p>
          <p>
            <strong className="font-medium text-bone">Field.</strong> Conway, then the memory pass.
          </p>
          <p>
            <strong className="font-medium text-bone">Yoked.</strong> Conway, then exactly as many
            flips as Field made on that generation, at positions drawn from Yoked’s own occupied
            neighborhoods.
          </p>
          <p>
            <strong className="font-medium text-bone">Scrambled.</strong> The same memory pass as
            Field, with every crystal’s cells permuted inside its 5×5 frame. Live count is kept,
            and the same permutation is applied to the mask it expects next. One permutation is
            drawn from the run seed and applied to every crystal in the field’s table, including
            echoes learned mid-run. Strength and recency are copied from the field’s table, so the
            null keeps the machinery and loses the shape.
          </p>
          <p>
            A cell is binary, so a remembered form can do one thing to it: flip it or leave it.
            Everything a form contributes arrives through where its flips land. Yoked asks whether
            Field’s flips land anywhere special. Scrambled asks whether that comes from the forms
            themselves or from the matching machinery. Field will make more of the forms it
            remembers than Control does. That is what the code is for. The contrast that can
            surprise is Field against Yoked and Scrambled, never Field against Control.
          </p>
          <p>
            Each memory pass draws from named streams derived from the seed: one for patch
            sampling, one for acceptance, one for Yoked positions. Every generation the field
            draws 48 candidate sites, each with its coin, whatever the boards hold. Field and
            Scrambled each consult their own first eight eligible sites from that one list, so
            identical boards make identical draws, their difference is mask content rather than
            luck, and neither board’s sampling depends on the other board’s cells. Control reads
            none. The initial pattern uses a fourth stream, and only at generation 0.
          </p>
        </Section>

        <Section title="The memory term">
          <p>
            A crystal is a 5×5 mask, the mask it expects next, and a strength. Eight are innate:
            block, blinker, tub, boat, beehive, glider, toad, beacon. Innate forms can be switched
            off. Others are echoes, or forms carried in from the archive on this device. Echoes are
            observed on every consulted patch whether or not any crystal matched it, so a table
            that starts empty still learns from the board. The
            Past-run coupling slider is how hard those old forms are allowed to push. A later run
            is not independent until the archive is empty and coupling is 0.
          </p>
          <p>
            Eight times a generation the field samples a patch. A patch is eligible only if it
            holds at least 3 live cells and its center 3×3 holds at least one. The choice is made
            on those samples, not on every cell. Eight writes cannot be 1% of a 48×48 board, so
            the Armed rate below is the share of consulted occupied neighborhoods, not the share of
            the whole grid. The board-wide share is recorded beside it and is not the bar.
          </p>
          <p>
            Similarity counts live cells only: Dice overlap, 2|A∩B| / (|A| + |B|), best of the
            eight rotations and reflections, and 0 when either patch is empty. The old Hamming
            score mostly counted dead cells that agreed. An empty patch could look like a blinker.
            A patch is kept as an echo when its Dice against its own next step is at least 0.85, or
            when a patch with Dice at least 0.75 against it was seen in the last 16 generations.
            Those echo floors are constants, published here, not sliders.
          </p>
          <p>
            Census identity is stricter than a near-miss. An isolated object that fits in 5×5 is
            named by its shape: shifted into the corner of its bounding box, then the minimum
            mask over the eight symmetries, so a boat is the same boat wherever it sits and
            whichever way it faces. Trained and comparison forms are named the same way, which is
            what lets the census count them. On a torus an object is followed across the edge and
            counted once. A near-miss is not the same form. A dense soup fuses into one blob and the census stays empty. That is a property
            of the soup, not a quiet field.
          </p>
          <p>
            A crystal is eligible only if its score clears the Similarity slider. Among those, one
            winner is chosen. The winner is the highest clearance^Sharpen × strength × recency.
            Its claim on the center cell is accepted with a probability built from how far it
            cleared the bar, its strength, how recently it was seen, and the Field strength
            slider, and never above 0.8. Sharpen only picks the winner; it is not in that
            probability. A cell is written at most once a generation. An accepted claim that changes the cell is an
            effective flip, drawn in amber. A claim that agrees with Conway is logged and not
            counted.
          </p>
          <p>
            Strength is a Beta posterior on how often the expected-next mask is right, decaying
            toward the prior each generation the crystal goes unseen. It is scored against what
            Conway would have done to the patch before any overwrite, never against the board after
            the field has written into it. Scored after the write, a crystal grades its own work.
            Calls and echoes are folded in at the end of the generation, so during a pass Field
            and Scrambled read the same table. An echo nudges strength; it is not counted as a
            correct call.
          </p>
          <p>None of this is hidden. It is a table in the same process, read by address and written into the next grid.</p>
        </Section>

        <Section title="What is measured">
          <p>
            <strong className="font-medium text-bone">Effective flips.</strong> A cell whose output
            differs from Conway applied to that board’s own previous state. The rate that can arm
            the run is those flips divided by the occupied neighborhoods the field actually
            consulted.
          </p>
          <p>
            <strong className="font-medium text-bone">Census.</strong> Every 10 generations, from 10
            through 300, each board’s isolated objects are counted by form. For form X on board B,
            n(X, B) is that count. Facilitation is ln[(n(X, B) + 0.5) / (n(X, Control) + 0.5)].
            Trained forms are the shapes of the crystals in the table at generation 0. If the table
            starts empty, they are the innate forms it would have held, so innate off changes what
            the field knows, not what it is scored on. A frozen recipe fixes its trained forms at
            the confirm stage, and the naive retest and every dose are scored on those same forms.
            Comparison forms are loaf, pond, ship, and long boat, and are never trained forms. Specificity is mean facilitation over trained forms minus
            mean facilitation over comparison forms. The gap on one seed is field specificity minus
            the better null. One seed is an illustration of the gap, not a test.
          </p>
          <p>
            <strong className="font-medium text-bone">Divergence, descriptive only.</strong> D*(t) =
            H(t) / [p(1 − q) + q(1 − p)], where H is the share of cells that disagree with Control
            and p, q are the two densities. D* of 1 means the boards are as different as two
            unrelated boards. The ledger records the generation of the first effective flip and the
            generation D* first reaches 0.5. Neither is a pass condition.
          </p>
        </Section>

        <aside className="mt-8 rounded-lab border border-amber bg-panel px-4 py-4">
          <p className="text-xs tracking-widest text-amber uppercase">The result</p>
          <p className="mt-2 font-display text-2xl leading-snug italic">
            Scored once, over a fixed window. Never at the first generation a number looks good.
          </p>
        </aside>

        <Section title="Levels">
          <p>
            <strong className="font-medium text-bone">Off.</strong> Field strength under 0.20 and no
            effective flips in generations 1–80. The test was never switched on.
          </p>
          <p>
            <strong className="font-medium text-bone">Unarmed.</strong> The window closed and the
            consulted flip rate stayed under 1%. The term did not write enough.
          </p>
          <p>
            <strong className="font-medium text-bone">Armed.</strong> The mean flip rate over
            generations 1–80 is between 1% and 12% of consulted occupied neighborhoods. This is the
            old Yes. It says the memory term is alive and the right size, and nothing more.
          </p>
          <p>
            <strong className="font-medium text-bone">Loud.</strong> Above 12%. Higher levels are
            still computed, and flagged: at that rate the field is replacing Conway, not biasing it.
          </p>
          <p>
            <strong className="font-medium text-bone">Specific.</strong> Across a batch, paired by
            seed, Field’s specificity exceeds Yoked’s and exceeds Scrambled’s. Direction fixed in
            advance. Exact paired sign test, two-sided, ties dropped, α = 0.05 for one
            pre-registered batch, and more non-tied seeds have to favor the field than oppose it.
            Both comparisons must pass. A bootstrap 95% interval sits beside the median of the
            non-tied differences. A mega run that tests recipe after recipe spends its 0.05: the
            k-th attempt must clear 0.05 · 6 / (π² k²), about 0.030, then 0.0076, then 0.0034, so
            all attempts together cannot exceed 0.05. This is still a fact about the table.
          </p>
          <p>
            <strong className="font-medium text-bone">Learned.</strong> Specific on a frozen recipe,
            then Specific again with innate forms off, an empty archive, and coupling at 0. Only
            then a dose curve: that naive rule trains on 0, 1, 10, and 100 seeds, and the same 16
            test seeds, none of them ever a training seed, are scored after each dose on the frozen
            recipe’s trained forms. Mean field specificity has to rise strictly
            with that count. If the frozen coupling is 0, archive import does nothing, so those dose
            tests run at coupling 0.25 and say so. A mega run does this only after an armed
            illustration clears the gap bar. It does not round one seed up to Learned. Even a rising
            curve is the table learning, not morphic resonance. If the curve was not run, or does
            not rise, Learned is not reached.
          </p>
          <p>
            A batch is 8, 16, 32, or 64 seeds. 64 is the published size. A paired sign test on 64
            seeds at α = 0.05 has about 88% power to detect a 70/30 split and about 62% for 65/35.
            At a mega run’s first α of 0.030 those are about 82% and 52%; by the fifth attempt,
            about 43% and 15%. Spending α is the price of a walk that does not stop. A single run
            is a demonstration, not a result. Seeds are derived from a SHA-256 of the frozen
            configuration, the archive, the thresholds, and the analysis version, so the hand does
            not pick them.
          </p>
        </Section>

        <Section title="Freezing, and the ledger">
          <p>
            Before a confirmatory batch starts, the ledger’s first row is that hash. Any stop before
            the seed list finishes marks the batch void. Painting a board, turning Lock off, moving
            a slider, or reseeding after generation 0 marks a live run exploratory. Exploratory
            runs are kept and shown. They are never entered as Specific.
          </p>
          <p>
            Boards in the confirmatory record are also labeled with random codes. The census is
            computed on the real arms, and the key that says which code was Field is appended only
            beside the finished scores. Replay of the same first row is deterministic: the same
            seeds, the same streams, the same rule.
          </p>
          <p>
            Crowd, early settling, and kept forms are still recorded, because a long run should
            leave a trail. They are not the score. Kept forms show that the table is growing. They
            do not show that a form arrived from outside the table.
          </p>
        </Section>

        <Section title="Other factors, including leaks">
          <p>
            Even as a model, a result can come from something other than “a learned form pulled the
            present.” These are the channels, and what now closes each.
          </p>
          <ol className="mt-3 grid gap-3">
            <Factor n="1" title="The overwrite itself" body="Any flips split Conway histories. Closed for Specific by Yoked: the field has to beat the same number of random flips." />
            <Factor n="2" title="The matching machinery" body="Matching still has rates, recency, and strength when the picture is nonsense. Closed for Specific by Scrambled, which keeps the machinery and removes the content." />
            <Factor n="3" title="Innate priors" body="Eight Conway habits can be present on generation 0. Closed for Learned, which is not offered while innate forms are on. Open for Specific, which may be innate habits alone and is reported that way." />
            <Factor n="4" title="The archive on this device" body="The archive’s contents are in the hash. Naive means empty archive, coupling 0, and innate forms off. Ignore archive on a sweep does that for the walk. It does not make the walk confirmatory." />
            <Factor n="5" title="Self-confirming strength" body="Closed by scoring strength against the Conway successor before the overwrite." />
            <Factor n="6" title="Dead cells counted as agreement" body="Closed by live-cell Dice and the eligibility floor. Empty against empty is 0." />
            <Factor n="7" title="Divergence that saturates from one cell" body="Closed by retiring divergence as a criterion. D* stays on the chart." />
            <Factor n="8" title="The experimenter’s hand" body="Painting a board, or turning Lock off, is logged and marks the run exploratory." />
            <Factor n="9" title="Choices made after seeing the board" body="A confirmatory batch freezes the configuration, and its seeds come from the hash." />
            <Factor n="10" title="Stopping when it looks good" body="Armed is scored once, at generation 80. A sweep that stops early is marked short, and a batch that stops early is void." />
            <Factor n="11" title="A scorer with no blind" body="Narrowed by coded arm names. Not closed: the same program, by the same author, writes the cells and the scorer." />
            <Factor n="12" title="Walking every knob" body="A mega run does not march the sliders from zero. It sorts clusters toward the armed band, bounces between patterns, and after a card scores it fans out to every parameter within one sweep step. When that pass runs out, it keeps combing the rest of the grid, then starts another pass from a new seed. One illustration seed is not a 64-seed batch. Every armed gap of 0.20 or wider gets its own 64-seed sign test; recipes that differ only in a knob the run ignores are one recipe. A miss does not end the walk, and it does not raise the gap bar so that weaker armed recipes are skipped. It does lower the α the next sign test must clear, so a walk that keeps testing cannot buy a false win. The walk stays open until a batch wins — Specific, then the naive retest and the dose curve — or until you stop it. Stopping before a seed list finishes voids that batch. None of this is morphic resonance. Old pictures are dropped." />
          </ol>
          <p>
            One channel that does not leak: the control’s Conway step never reads the random stream.
            Memory passes do, through separate streams. They cannot touch the classical board. They
            can change which echoes a field learns, so batches are comparable only when they share a
            first row.
          </p>
        </Section>

        <Section title="What certainty would require">
          <p>There are two claims, and they do not have the same bar.</p>
          <p>
            <strong className="font-medium text-bone">Certain the stored forms did it.</strong> Field
            strength 0: Field equals Control for the whole run. Innate off with an empty archive
            and coupling 0 is not enough, because the empty table learns echoes from the board. Specific passes against Yoked and Scrambled, on derived seeds, with a
            frozen configuration. Learned passes the dose curve on disjoint seeds. The same first
            row replays to the same scores.
          </p>
          <p>
            <strong className="font-medium text-bone">Certain it is morphic resonance.</strong> The
            test system holds no copy of the trained form. No table, no file, no model, and no
            person who saw the training. Learning and test never exchange bits. Shared code, a
            shared seed, a shared clock, and a shared experimenter are channels. Sham training and
            scrambled labels are pre-registered, run in more than one place, and scored by people
            who do not know which arm was trained. The trained form is facilitated and a form that
            was never trained is not. A form that has occurred many times biases more than a form
            that has occurred once. Habits installed before any run fail this. The effect is still
            there after every store you can find has been removed.
          </p>
          <p>
            Every level above measures the table. Learned is the strongest thing this program could
            say, and it would still say the table learned. Morphic resonance, in the sense this
            laboratory is named for, is a bias with no local signal carrying the form. The residue
            that would count is whatever remains after the table is gone. In this program that
            residue is zero: turn the field off and the boards lock together. That is how the model
            is known to be a model.
          </p>
          <p>
            The ledger exports the claims and the trial rows. A confirmatory batch shows its first
            row and the code key beside the scores. Those files document the runs of this model.
            They are not evidence that a form became more likely somewhere that had never stored it.
          </p>
        </Section>
      </article>
    </main>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-8">
      <h2 className="font-display text-2xl italic">{title}</h2>
      <div className="mt-3 grid gap-3 text-sm leading-relaxed text-pretty text-mist">{children}</div>
    </section>
  );
}

function Factor({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <li className="grid grid-cols-[2.5rem_1fr] gap-3 rounded-lg border border-line bg-panel-2 px-3 py-3">
      <span className="font-display text-2xl leading-none text-amber italic">{n}</span>
      <div>
        <p className="text-bone">{title}</p>
        <p className="mt-1 text-mist">{body}</p>
      </div>
    </li>
  );
}
