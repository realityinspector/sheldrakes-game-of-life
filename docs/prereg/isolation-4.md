# Pre-registration: isolation-4 series (rebuilt receiver, fresh data)

Written and pushed before any isolation-4 session or the 0.5% positive control ran.

## Why

isolation-3 did not replicate isolation-2. Rather than stop there, we reprocessed every
recording we already had: the raw tester bytes of all five rig sessions, replayed with
`explore/replay.ts`, which reproduces the recorded counts exactly. Then we froze a better
receiver to test on new data.

**What the reprocessing found** (`explore/battery.py`, `explore/receiver.py`):

- **The lens battery.** 363 lenses:
  - Dose kernels: lag 0–3, lead 1–2, exponential decay with τ = 2, 5 and 15, cumulative,
    growth within a session.
  - Responses: census at generations 100, 200 and 300; compositional; residualised;
    presence; rank; tail; acceleration; the trained pattern in the raw and mixed entropy
    bits.
  - Fourier cross-spectra between the indicator and the response.
  - Each lens is calibrated by exact assignment shuffles. Sessions are combined with
    Stouffer, and the family-wise p uses Westfall–Young max-|Z| across all 363.
- **The battery's result.** No lens survives the correction for having tried 363 of them:
  - Best across the five sessions: lag1|log100|eq, Z −2.72, raw p 0.0067, family-wise p 0.62.
  - Best across the three isolation runs: lag3|rawbits|ivw, Z +2.69, raw p 0.0073,
    family-wise p 0.65.
- **Cross-session dispersion.** The rig's T1 z-scores vary across sessions more than
  chance allows: z = −2.13, +2.69, −0.96, +1.98, −0.66, which gives Q = Σz² = 17.1 on 5 df,
  raw p 0.004.
  - **It does not stand out within its own family:** family-wise p 0.48 across the dispersion
    versions of the lenses. lag3|rawbits|ivw shows the same Q (17.2).
  - **It is absent in the better-weighted receiver:** lag0|log300|ivw gives Q 4.3, p 0.51.
  - **It sits in two forms:** per-form Q over the five sessions is block 2.9, blinker 3.2,
    beehive 11.2, loaf 10.2, boat 6.9.
- **Receiver noise.** Inverse-variance weighting across forms (ivw) cuts the 80%-power MDE
  from 1.73% to 1.38% at 1000 soups per block. The balanced design already cancels any
  common-mode noise within a block, so compositional transforms add nothing under equal
  weights.

## What changes

- **The tester.** It now runs 32 × 32 soups through bit-parallel Conway (`rig/bitlife.ts`).
  - The results are identical: the tests check every generation against the reference step,
    and replays reproduce all five earlier sessions exactly.
  - It is about 30× faster, so a block now has **20000 soups instead of 1000** in roughly
    the same wall time.
- **Everything else is identical to isolation-3:** forms, 60 blocks, trainer, beacon, audits,
  and the 0700 per-user isolation.
- **Expected per-session MDE:** about 0.31% for lag0|log300|ivw. Pooled over six sessions,
  about 0.13%.

## Sessions

These run sequentially on this host, all from the commit that adds this file:

1. `positive-control-0.5pct` (`leak.relative = 0.005`, declared).
2. `isolation-4-1` … `isolation-4-6` (`leak.relative = 0`).

## Analysis

The analysis is `explore/confirm.py`, sha256
`e727c9fecad695657ff78b8ade21eedce5f12dfb935f66ab8bd065cae1e33f9a`, with `explore/load.py`
sha256 `916ed037c05eb9230db2a2fb5714c8e8c70ba0f273fc230c57630b778bbb9592`. Its seed is
fixed. Every p is a randomization p over 20000 joint assignment shuffles.

**Primary hypotheses** (Holm across H1–H3, α = 0.05):

- **H1, constant lift.** Stouffer of the per-session z of lag0|log300|ivw, one-sided (the
  trained form goes up).
- **H2, session-level dispersion of the rig's T1.** Q = Σ_s z_s² over the six sessions,
  upper tail.
- **H3, dispersion in beehive and loaf.** Q = Σ_s Σ_{beehive, loaf} z_{s,f}², upper tail.

**Secondary** (Holm within the pair; reported, no claim):

- **S1.** lag1|log100|eq, one-sided down.
- **S2.** lag3|rawbits|ivw, one-sided up.

**Sensitivity.** The positive control must be detected by lag0|log300|ivw on that session
alone (one-sided 0.05). If it is not, the receiver has failed and the isolation sessions are
uninformative about effects of this size.

**Exploratory.** The full 363-lens battery is run on the six fresh sessions, with its own
max-|Z| correction.

Each session's own rig report (T1/T2 with Holm) is produced as usual, but it is not the
decision for this series.

## Predictions, stated in advance

- **Mine.** H1, H2 and H3 not supported. The pooled estimate is within ±0.13% of zero, and
  the per-session T1 z-scores look like N(0, 1).
- **The alternative under test.** The isolation-2 excursion, or the session-to-session
  spread, reflects a real effect too faint for the old receiver.
  - **If that effect is a constant lift of 0.3% or more,** H1 detects it with high power.
  - **If it is a session-level effect of the size the old sessions imply** (SD about 1% in
    relative count), the 20× receiver turns it into per-session |z| of about 7. H2 would
    then be overwhelming.

## What each outcome means

| Outcome | Meaning |
|---|---|
| H1 supported | A block-locked lift of the trained form, of the estimated size. Next: replicate it on separate machines with a different entropy source. |
| H2 or H3 supported, H1 not | Something makes counts depend on the assignment, with a sign that changes between sessions. Under exact randomization, the only routes are a real effect or a bug. Audit the code first, then look at what differs between sessions. |
| None supported, positive control detected | No effect of about 0.13% or more (a constant lift), and no session-level effect anywhere near the size the old sessions suggested. The old dispersion was chance. Further gains come from the antenna (the entropy source and where randomness enters), not from processing. |
| Positive control not detected | The receiver failed. Nothing is concluded. |


## Outcome (appended after the series)

All seven sessions ran on commit `3365783`. Every block passed its audits, there were no
training overruns, and all 7.2 million fresh soups were replayed exactly. The frozen
`explore/confirm.py` gives:

| Test | Result | Holm | Supported |
|---|---|---|---|
| Positive control, 0.5% leak | z 3.28, p 0.0007 | n/a | **detected** |
| H1, constant lift (lag0\|log300\|ivw, pooled) | Z +0.002, p 0.49 | 0.99 | no |
| H2, dispersion of T1 | Q 8.9 on 6 df, p 0.18 | 0.53 | no |
| H3, dispersion in beehive and loaf | Q 10.2 on 12 df, p 0.60 | 0.99 | no |
| S1, lag1\|log100\|eq, down (secondary) | Z -1.46, p 0.074 | 0.15 | no claim |
| S2, lag3\|rawbits\|ivw, up (secondary) | Z +0.99, p 0.166 | 0.17 | no claim |

The per-session T1 estimates were −0.11%, +0.18%, +0.24%, −0.29%, −0.04% and +0.09%. The
per-session T1 z-scores were -0.71, +1.37, +1.60, -1.85, -0.25, +0.69.

**Reading.** This is the "none supported, positive control detected" row of the table above.
- There is no constant lift of about 0.13% or more.
- There is no session-level effect anywhere near the size the old sessions implied. That
  would have shown up here as |z| ≈ 7; the largest |z| was 1.85.
- The old dispersion was chance.

**Exploratory, after the fact** (`explore/addendum.py`, `explore/results/`):
- **Spread around the mean.** A reviewer noted that Q also grows with a steady lift.
  Σ(z − z̄)² is 8.8 on 5 df (p 0.11). For
  beehive and loaf it is p 0.44.
- **Per form.** No form has a pooled lift: every |Z| is ≤ 1.2 and every two-sided p is
  ≥ 0.24.
- **The 363-lens battery on the six fresh sessions.** The best lens is lead1|comp300|ivw,
  Z −3.15, raw p 0.0015, family-wise p 0.23. It is a "lead" lens, meaning it predicts the
  *next* block's training, which only chance could produce.
- **All nine isolation sessions,** pooled by inverse variance: T1
  +0.02% (95% CI
  -0.09% to +0.14%).
- **S1 is the only lens whose sign held on fresh data.** It was −2.72 over the earlier five
  sessions and −1.46 here. It is not significant, and there is no physical route for it. If
  anyone wants to chase it, it needs a pre-registration of its own.
