# Pre-registration: census of the tester's raw bytes (existing data, never scored)

Written and pushed before any raw-byte soup was run.

## The flaw this corrects

In rig/2 the tester committed to its raw bytes and then XORed them with a keystream derived
from the registrar's beacon. That stops a tester which somehow knew the target from
selecting its bytes. It has a side effect: **XOR with an independent uniform keystream gives
a uniform result whatever the raw bytes were.** So the soups that were actually run, and
every census reported for isolation-2, isolation-3 and isolation-4-1…6, could not show any
bias in the tester's own entropy. They could only show an influence that acts jointly on the
tester's bytes and the registrar's beacon.

How much this actually covered before:
- **Pattern counts.** `rawbits` checked the trained pattern in the raw bytes and found nothing.
- **Census.** Not checked. Only isolation-1 and the first positive control, which ran
  without a beacon, had their census run on raw bytes.

The raw bytes of every rig/2 session were kept. Running them through Conway with no beacon
mix gives a census that has never been looked at. It is also statistically independent of
the reported one, because the keystream was independent and uniform.

## Analysis

The analysis is `explore/rawcensus.py`, using the lenses in `explore/confirm.py` and fixed
seeds. The raw soups come from `RAW=1 explore/replay.ts`.

- **R1, primary.** Stouffer of z(lag0|log300|ivw) over isolation-4-1…6, one-sided up.
- **R2, primary.** Q = Σ z(T1)² over isolation-4-1…6, upper tail.
- Holm across R1 and R2, α = 0.05.
- **R3, secondary.** R1's lens pooled over isolation-2, isolation-3 and isolation-4-1…6.

Sensitivity is the same as isolation-4, because raw and mixed soups are statistically
identical. That means about 0.31% per session for the ivw lens, and about 0.13% pooled. No
positive control is possible: the declared leak acted on the reported counts, not on bytes.

## Prediction

Mine is that R1 and R2 are not supported. The alternative is that an influence on the
tester's entropy shows up here, having been invisible before.

## Outcome (appended after scoring)

All eight rig/2 isolation sessions were replayed from their raw bytes: 7.32 million soups.

| Test | Result | Holm |
|---|---|---|
| R1, constant lift on raw soups (isolation-4-1…6) | Z +0.22, p 0.42 | 0.83 |
| R2, dispersion of T1 on raw soups | Q 0.40 on 6 df, upper-tail p 0.999 | 0.999 |
| R3, lift over all eight rig/2 sessions (secondary) | Z +0.77, p 0.22 | n/a |

Neither primary test is supported. The blind spot the beacon created hid nothing at this
sensitivity.

The six raw-soup T1 z-scores were +0.19, +0.00, −0.34, +0.00, +0.50 and +0.02. An
independent re-computation gives the same values. That is unusually quiet: a lower-tail p of
about 0.001, a direction nobody predicted and nothing pre-registered. We have computed dozens
of tail statistics across these analyses, so one this extreme in some tail is not surprising.
Anyone who wants to treat it as a lead should pre-register the lower tail on fresh sessions.
