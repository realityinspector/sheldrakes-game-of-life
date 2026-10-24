import type { ConfirmResult, MegaState, SweepCard } from "./sweep.ts";
import { formatCount } from "./sweep.ts";

export type HistoryLine = {
  name: string;
  reading: string;
  specific: boolean | null;
};

export type Verdict = {
  resonance: "no" | "not-yet";
  title: string;
  line: string;
  detail: string;
  chips: { label: string; value: string; hint: string }[];
};

export function interpret(input: {
  cards: Pick<SweepCard, "level" | "gap" | "flipRate">[];
  confirm: ConfirmResult | null;
  history: HistoryLine[];
  running: boolean;
  autopilot: boolean;
  campaign: string;
  reason: string;
  mega?: MegaState | null;
}): Verdict {
  if (input.mega) return readMega(input.mega);

  const armed = input.cards.filter((card) => card.level.startsWith("armed")).length;
  const loud = input.cards.filter((card) => card.level.startsWith("loud")).length;
  const unarmed = input.cards.filter(
    (card) => card.level.startsWith("unarmed") || card.level.startsWith("off"),
  ).length;
  const bestGap = input.cards.reduce(
    (best, card) => Math.max(best, card.gap),
    Number.NEGATIVE_INFINITY,
  );
  const gapText = input.cards.length && Number.isFinite(bestGap) ? bestGap.toFixed(2) : "—";
  const passedShort = input.history.some(
    (item) => item.specific === true && !item.reading.includes("64"),
  );
  const passedPublished = input.history.some(
    (item) => item.reading.includes("64") && item.specific === true,
  );
  const confirm = input.confirm;
  const published = !!confirm && !confirm.voided && confirm.specific && confirm.seeds >= 64;
  const shortPass = !!confirm && !confirm.voided && confirm.specific && confirm.seeds < 64;
  const failedConfirm = !!confirm && !confirm.voided && !confirm.specific;
  const anySpecific = published || passedPublished;

  const unanswered = input.cards.length === 0 && input.history.length === 0;
  const resonanceValue =
    unanswered || (input.running && !anySpecific && !published && !failedConfirm)
      ? "Not yet"
      : "No";
  const chips = [
    {
      label: "Resonance",
      value: resonanceValue,
      hint: anySpecific || published ? "table only" : "not detected",
    },
    {
      label: "Specific",
      value:
        anySpecific || published
          ? "Yes"
          : shortPass || passedShort
            ? "Short"
            : failedConfirm
              ? "No"
              : "Not run",
      hint: anySpecific || published ? "64 seeds" : "needs both nulls",
    },
    {
      label: "Armed",
      value: String(armed),
      hint: loud ? `${loud} loud` : `${unarmed} quiet`,
    },
    {
      label: "Best gap",
      value: gapText,
      hint: "field minus nulls",
    },
  ];

  if (input.cards.length === 0 && input.history.length === 0) {
    return {
      resonance: "not-yet",
      title: "Not yet",
      line: "Morphic resonance has not been tested.",
      detail:
        "A recipe card cannot answer it. Armed only means the table is writing. Autopilot changes the kind of sweep, freezes the best recipe, and scores it against both nulls. Even a Specific batch is not morphic resonance: the forms are still inside the program. Turn the field off and the boards lock.",
      chips,
    };
  }

  if (input.running && input.autopilot) {
    return {
      resonance: "not-yet",
      title: "Not yet",
      line: `Autopilot is running “${input.campaign}”. Morphic resonance has not been found.`,
      detail:
        "It will keep changing the sweep — garden, gliders, innate off, a frozen batch — until a 64-seed test is Specific or the playbook runs out. Specific would still be a fact about the table, not a field that remains when the table is gone.",
      chips,
    };
  }

  if (published || anySpecific) {
    return {
      resonance: "no",
      title: "No",
      line: "Specific, and that is not morphic resonance.",
      detail: `${input.reason || "A 64-seed batch beat both nulls."} The remembered shape did the work. The table is in the same process as the test, so nothing was detected that exists when the table does not. Learned was not reached: there is no dose curve, and a later run is not independent while coupling or the archive is on.`,
      chips,
    };
  }

  if (shortPass || passedShort) {
    return {
      resonance: "no",
      title: "No",
      line: "A short batch favored the field. That is not morphic resonance, and it is not the published test.",
      detail:
        "Fewer than 64 seeds passed the sign test. Autopilot promotes that recipe to a 64-seed freeze before it will even call the result Specific. Specific would still measure the table.",
      chips,
    };
  }

  if (failedConfirm) {
    return {
      resonance: "no",
      title: "No",
      line: "The frozen batch did not find morphic resonance.",
      detail: `Field specificity did not reliably beat both the yoked null and the scrambled null (${confirm?.seeds ?? 0} seeds). ${
        loud > armed
          ? "Much of the walk was loud: the table was replacing Conway, which does not count."
          : armed > 0
            ? "Some cards were armed, so the table can write, but the shape did not beat a contentless disturbance."
            : "The term barely wrote, so there was no memory effect to mistake for a field."
      } ${input.reason}`,
      chips,
    };
  }

  if (armed === 0 && loud === 0) {
    return {
      resonance: "not-yet",
      title: "Not yet",
      line: "Nothing here is morphic resonance. The table never reached the armed band.",
      detail:
        "Flips stayed under 1% of the neighborhoods the field read, so the memory term was not alive. A quiet walk cannot be promoted into a finding. Lower similarity, raise field strength, or let autopilot try a garden of isolated forms.",
      chips,
    };
  }

  if (loud > 0 && armed === 0) {
    return {
      resonance: "no",
      title: "No",
      line: "Loud is the table replacing Conway, not morphic resonance.",
      detail:
        "Effective flips ran past 12% of consulted neighborhoods. The old score would have paid that. This one does not. Autopilot looks for the armed band, then asks whether the shape beat both nulls.",
      chips,
    };
  }

  return {
    resonance: "not-yet",
    title: "Not yet",
    line:
      armed > 0
        ? `Armed on ${armed} ${armed === 1 ? "card" : "cards"}. That is not morphic resonance.`
        : "These cards do not show morphic resonance.",
    detail: `The table is writing at a measured rate. Best specificity gap on this walk is ${gapText}. A gap on one seed is an illustration. Morphic resonance is only even approachable after a frozen batch, and a Specific result would still be the table. ${input.reason}`,
    chips,
  };
}

/** Specific results from earlier attempts, which later failures do not undo. */
function earlierSpecific(mega: MegaState): string {
  const wins = (mega.sealed ?? []).filter(
    (item) => item.specific && item !== mega.sealed[mega.sealed.length - 1],
  );
  if (wins.length === 0) return "";
  const parts = wins.map((item) => {
    const next =
      item.learned === true
        ? "Learned was reached"
        : item.learned === false
          ? "the dose curve did not show learning"
          : item.naive === false
            ? "its naive retest failed"
            : "its naive retest did not finish";
    return `sign test ${item.attempt} (α ${alphaText(item.alpha)}) was Specific and ${next}`;
  });
  return ` Earlier in this run, ${parts.join("; ")}. A later miss does not undo that; it is still the table.`;
}

function alphaText(alpha: number | undefined): string {
  const a = alpha ?? 0.05;
  return a >= 0.01 ? a.toFixed(3) : a.toPrecision(2);
}

function count(n: number): string {
  return Math.max(0, Math.round(n)).toLocaleString("en-US");
}

function readMega(mega: MegaState): Verdict {
  const stage = mega.stage ?? "search";
  const armed = mega.tally.armed;
  const loud = mega.tally.loud;
  const quiet = mega.tally.unarmed + mega.tally.off;
  const gap = mega.tally.bestGap;
  const gapOk = Number.isFinite(gap);
  const gapText = gapOk ? gap.toFixed(2) : "—";
  const going = mega.on;
  const proof = mega.proof;
  const naive = mega.naive;
  const dose = mega.dose;
  const loudNote =
    loud > 0
      ? `${count(loud)} loud ${loud === 1 ? "card is" : "cards are"} the table replacing Conway. Loud is not a finding and does not add proof.`
      : "No card was loud.";
  const armedNote =
    armed > 0
      ? `${count(armed)} armed ${armed === 1 ? "card means" : "cards mean"} the memory term was writing inside the 1–12% band. Writing is required and is not morphic resonance.`
      : "No card was armed, so the memory term did not stay in the band where a memory effect could even be discussed.";
  const frozen = mega.frozen ? ` Frozen recipe: ${mega.frozen}.` : "";

  if (stage === "confirm" && going) {
    return megaVerdict(
      true,
      "Not yet",
      `Morphic resonance has not been found. Proof: the 64-seed sign test is running (${mega.ladderDone}/${mega.ladderTotal || 64}). Extent: still an illustration until that batch seals.`,
      `The best armed recipe was frozen and is being scored at generation 80 on seeds derived from the first-row hash, not the illustration seed.${frozen} Both nulls have to pass at α = ${alphaText(mega.alpha)}, this attempt's share of 0.05: every attempt in the run spends less, so a run that keeps testing cannot buy a false win. Even a Specific batch would measure the table. ${loudNote}`,
      "Running",
      "64 seeds, open",
      `${mega.ladderDone}/${mega.ladderTotal || 64}`,
      "not sealed",
      loud,
    );
  }

  if (stage === "naive" && going) {
    return megaVerdict(
      true,
      "Not yet",
      "The 64-seed test beat both nulls. That is still the table, not morphic resonance. The naive retest is running.",
      `Naive means innate forms off, coupling 0, and an empty archive, on 64 new seeds (${mega.ladderDone}/${mega.ladderTotal || 64}).${frozen} If this fails, the gap depended on habits that were already in the program. Learned has not been reached.`,
      "Specific",
      "naive still open",
      `${mega.ladderDone}/${mega.ladderTotal || 64}`,
      "innate off",
      loud,
    );
  }

  if (stage === "dose" && going) {
    const soFar = dose?.points.length
      ? ` So far ${dose.points.map((point) => `${point.dose}→${point.spec.toFixed(3)}`).join(", ")}.`
      : "";
    return megaVerdict(
      true,
      "Not yet",
      "Both 64-seed tests passed. That is still the table. The dose curve is running, and Learned is not reached until facilitation rises with dose.",
      `${dose?.reason ?? "Dose curve is running."}${soFar} Learned requires mean field specificity to rise strictly across 0, 1, 10, and 100. A rising curve would still be the table.`,
      "Specific",
      "dose not sealed",
      `${mega.ladderDone}/${mega.ladderTotal || 1}`,
      "curve open",
      loud,
    );
  }

  if (proof?.voided && !going) {
    return megaVerdict(
      false,
      "No",
      "Morphic resonance was not found. Proof: void. The 64-seed batch was stopped before the seed list finished.",
      `An unfinished batch is not a result.${frozen} ${loudNote} Extent of proof: none.`,
      "Void",
      "stopped early",
      "None",
      "batch void",
      loud,
    );
  }

  const bar = Number.isFinite(mega.nextBar) ? mega.nextBar.toFixed(2) : "0.20";

  const earlier = earlierSpecific(mega);

  if (going && stage === "search" && proof && !proof.specific) {
    const waiting =
      mega.queued > 0
        ? ` ${mega.queued} other armed ${mega.queued === 1 ? "recipe is" : "recipes are"} still waiting for a 64-seed test.`
        : " Any other armed recipe at gap 0.20 or wider still gets its own test.";
    return megaVerdict(
      true,
      "Not yet",
      `Morphic resonance has not been found. Proof: no. Sign test ${mega.trials || 1} failed, and the search is still going.`,
      `That 64-seed batch did not beat both nulls, so it was not Specific. The walk did not end.${waiting} It keeps going until a batch wins, or until you stop it. The next attempt must clear α = ${alphaText(mega.alpha)}.${earlier}${frozen} ${armedNote} ${loudNote}`,
      earlier ? "Earlier" : "No",
      earlier ? "an earlier 64 was Specific" : "last 64 failed",
      "Still open",
      "miss is not the end",
      loud,
    );
  }

  if (going && stage === "search" && proof?.specific && naive && !naive.specific && !naive.voided) {
    return megaVerdict(
      true,
      "Not yet",
      "Specific on one recipe, and that is not morphic resonance. The naive retest failed, so the search resumed.",
      `The published batch beat both nulls. With innate forms off, coupling 0, and an empty archive, it did not. Learned was not reached. The walk is still going, and the next published batch waits for an armed gap of at least ${bar}.${frozen}`,
      "Specific",
      "not naive",
      bar,
      "search resumed",
      loud,
    );
  }

  if (going && stage === "search" && proof?.specific && naive?.specific && dose && !dose.learned) {
    const curve = dose.points.length
      ? dose.points.map((point) => `${point.dose}→${point.spec.toFixed(3)}`).join(", ")
      : "no finished doses";
    return megaVerdict(
      true,
      "Not yet",
      "Learned was not reached. The dose curve did not rise, and the search resumed. That is not morphic resonance.",
      `Both 64-seed tests were Specific. The dose curve did not rise strictly (${curve}). ${dose.reason} The next published batch waits for an armed gap of at least ${bar}.`,
      "Specific",
      "dose flat",
      bar,
      "search resumed",
      loud,
    );
  }

  if (proof && !proof.specific) {
    return megaVerdict(
      false,
      "No",
      "Morphic resonance was not found. Proof: no. The frozen recipe failed the 64-seed sign test.",
      `Tried ${formatCount(mega.done)} illustration ${mega.done === 1n ? "card" : "cards"}, then ${proof.seeds} derived seeds. The field did not beat both the yoked null and the scrambled null. The naive retest and the dose curve were not run.${earlier}${frozen} ${armedNote} ${loudNote} Extent: an illustration that did not replicate.`,
      earlier ? "Earlier" : "No",
      earlier ? "an earlier 64 was Specific" : "64 seeds, failed",
      "Not replicated",
      "one seed, then a miss",
      loud,
    );
  }

  if (proof?.specific && naive?.voided) {
    return megaVerdict(
      false,
      "No",
      "Specific on the sealed 64, and that is not morphic resonance. The naive retest was stopped early and is void.",
      `The published batch beat both nulls. The retest with innate forms off was not finished, so Learned was not reached.${frozen} ${proof.learnedReason}`,
      "Specific",
      "naive void",
      "Not naive",
      "retest stopped",
      loud,
    );
  }

  if (proof?.specific && naive && !naive.specific && !naive.voided) {
    return megaVerdict(
      false,
      "No",
      "Specific, and that is not morphic resonance. The naive retest failed.",
      `The frozen recipe beat both nulls on 64 seeds. With innate forms off, coupling 0, and an empty archive, it did not. The gap was not shown without those habits. Learned was not reached.${frozen} ${loudNote}`,
      "Specific",
      "not naive",
      "Innate",
      "gap needed habits",
      loud,
    );
  }

  if (proof?.specific && naive?.specific && dose?.learned) {
    const curve = dose.points.map((point) => `${point.dose}→${point.spec.toFixed(3)}`).join(", ");
    return megaVerdict(
      false,
      "No",
      "Learned, and that is not morphic resonance.",
      `Both 64-seed tests were Specific, and mean field specificity rose with dose (${curve}). Coupling on the dose tests was ${dose.coupling.toFixed(2)}. ${dose.reason} The residue after the table is gone is still zero.`,
      "Learned",
      "still the table",
      "Dose rose",
      "not a field outside",
      loud,
    );
  }

  if (proof?.specific && naive?.specific && dose && !dose.learned && !going) {
    const stopped = dose.reason.startsWith("Stopped");
    const curve = dose.points.length
      ? dose.points.map((point) => `${point.dose}→${point.spec.toFixed(3)}`).join(", ")
      : "no finished doses";
    return megaVerdict(
      false,
      "No",
      stopped
        ? "Specific twice, and that is not morphic resonance. The dose curve was stopped early and is void."
        : "Specific twice, and that is not morphic resonance. Learned was not reached.",
      stopped
        ? `The frozen recipe and the naive retest both beat both nulls. ${dose.reason}`
        : `The frozen recipe and the naive retest both beat both nulls. The dose curve did not rise strictly (${curve}). ${dose.reason}`,
      "Specific",
      stopped ? "dose void" : "dose flat",
      "Not learned",
      stopped ? "curve stopped" : "curve did not rise",
      loud,
    );
  }

  if (proof?.specific && !naive && !going) {
    return megaVerdict(
      false,
      "No",
      "Specific, and that is not morphic resonance. The run stopped before the naive retest.",
      `${proof.learnedReason}${frozen}`,
      "Specific",
      "naive not run",
      "64 seeds",
      "table only",
      loud,
    );
  }

  const illustrated = gapOk && gap > 0.05;
  const writes = armed > 0;
  const where = mega.tally.bestLabel ? ` on ${mega.tally.bestLabel}` : "";
  let proofValue = "No";
  let proofHint = "one seed is not a test";
  let extent = "None";
  let extentHint = "nothing earned";
  let line: string;
  let detail: string;

  if (mega.done === 0n && !proof) {
    proofValue = "—";
    proofHint = "no cards yet";
    extent = "—";
    extentHint = "not tested";
    line = going
      ? "Morphic resonance has not been tested. There is no proof yet, and no extent to report."
      : "Morphic resonance was not tested. There is no proof, and no extent to report.";
    detail =
      "No recipe finished. An armed gap wide enough will freeze that recipe for a 64-seed sign test. None of that is a form arriving from outside the program.";
  } else if (!writes && !illustrated) {
    extentHint = loud ? `${count(loud)} loud, not a finding` : `${count(quiet)} quiet`;
    line = going
      ? "So far morphic resonance has not been found. Proof: none. Extent: nothing — the table has not written in the armed band, and it has not beaten the nulls."
      : "Morphic resonance was not found. Proof: none. Extent: nothing — the table did not write in the armed band, and it did not beat the nulls.";
    detail = `Tried ${formatCount(mega.done)} on one shared seed. ${loudNote} ${quiet > 0 ? `${count(quiet)} were quiet. ` : ""}A quiet or loud walk cannot be promoted into a field. The 64-seed sign test has not started.`;
  } else if (!illustrated) {
    extent = "Writes only";
    extentHint = `${count(armed)} armed, nulls not beaten`;
    line = going
      ? "So far morphic resonance has not been found. Proof: none. Extent: the table can write, and the shape has not beaten the nulls."
      : "Morphic resonance was not found. Proof: none. Extent: the table can write. The shape did not beat the nulls.";
    detail = `Tried ${formatCount(mega.done)} on one shared seed. ${armedNote} ${loudNote} The best gap is ${gapText}${where}. The 64-seed sign test starts from an armed card once its gap reaches 0.20. A smaller gap keeps searching. It has not started.`;
  } else {
    extent = gapText;
    extentHint = "one seed, unreplicated";
    line = going
      ? `So far morphic resonance has not been found. Proof: no. Extent: one unreplicated seed, gap ${gapText}.`
      : `Morphic resonance was not found. Proof: no. Extent: one unreplicated seed, gap ${gapText}.`;
    detail = `Tried ${formatCount(mega.done)} on one shared seed. ${armedNote} ${loudNote} The best gap is ${gapText}${where}: field facilitation minus the worse null, on that single recipe. One seed cannot be Specific. The run freezes the best armed card — not a loud one — once that gap reaches 0.20, and then runs the 64-seed sign test. A smaller gap keeps searching. That test still measures the table. It has not sealed.`;
  }

  return megaVerdict(
    going,
    going ? "Not yet" : "No",
    line,
    detail,
    proofValue,
    proofHint,
    extent,
    extentHint,
    loud,
  );
}

function megaVerdict(
  going: boolean,
  title: string,
  line: string,
  detail: string,
  proof: string,
  proofHint: string,
  extent: string,
  extentHint: string,
  loud: number,
): Verdict {
  return {
    resonance: going ? "not-yet" : "no",
    title,
    line,
    detail,
    chips: [
      { label: "Resonance", value: going ? "Not yet" : "No", hint: "not found" },
      { label: "Proof", value: proof, hint: proofHint },
      { label: "Extent", value: extent, hint: extentHint },
      { label: "Loud", value: count(loud), hint: "not a finding" },
    ],
  };
}
