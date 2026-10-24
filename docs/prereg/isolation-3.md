# Pre-registration: isolation-3 (replication of the isolation-2 anomaly)

Written and pushed after isolation-2 was revealed and before isolation-3 runs.

## Background

- `isolation-1` (rig/1): T1 −1.45%, 95% CI −2.64% to −0.20%, one-sided p 0.983.
- `isolation-2` (rig/2, the hardened rig): T1 +1.58%, 95% CI +0.44% to +2.76%, one-sided
  p 0.0032, Holm 0.0065. It crossed the pre-registered threshold, so its own report labels it
  an anomaly that needs replication.

Checks run after isolation-2 found no artifact:
- both runs had leak 0;
- every block's counts replay from the tester's committed bytes and the beacon;
- no single block drives the effect: dropping any one leaves p ≤ 0.009.

A descriptive Stouffer combination of the two runs' one-sided T1 p-values gives z 0.43,
p 0.33. That combination was not pre-registered.

## Test

`rig/protocols/isolation-3.json` is identical to `isolation-2.json` apart from the label and
the hypothesis text. It runs with the code of the commit that adds this file, using the same
rig/2 servers, users and audits.

**Primary criterion.** isolation-3's T1 has Holm-adjusted p < 0.05 in the pre-registered
(positive) direction. If it does, the isolation-2 anomaly counts as replicated *on one host*.
The next step is then a run on physically separate machines. It is still not a claim of
morphic resonance.

If it does not, the isolation-2 anomaly is treated as chance and no further replication of
it is run on this host.

**Secondary (descriptive, no decision attached).** Stouffer's combination of the one-sided T1
p-values of isolation-1, -2 and -3.

Expected power: about 75% against a true effect of +1.58%, given the reported 80%-power
minimum detectable effect of about 1.75%.

## Outcome (appended after the run)

isolation-3 (code `ba43eb6`, unchanged during the run): T1 −0.70%, 95% CI −1.94% to +0.56%,
one-sided p 0.835, Holm 1.00. Every block was audited and passed, and the code hash was
re-verified at the reveal. **The primary criterion was not met.** Per this pre-registration,
the isolation-2 anomaly is treated as chance, and it will not be replicated again on this host.

The secondary, descriptive combination is Stouffer's over isolation-1, -2 and -3, using the
one-sided T1 p-values (z = −2.12, +2.72, −0.97). It gives z −0.21, one-sided p 0.58. The three
estimates (−1.45%, +1.58%, −0.70%) scatter around zero.
