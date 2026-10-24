# Rig report: isolation-1

No effect detected. Estimated effect -1.45% (95% CI -2.64% to -0.20%), Holm p = 0.983. An effect of +1.61% or more would have been detected with about 80% power.

| | |
|---|---|
| Primary T1 (block-locked) | effect -1.45%, CI -2.64% to -0.20%, p 0.983, Holm 0.983 |
| Secondary T2 (cumulative dose) | mean correlation 0.0184, p 0.169, Holm 0.337 |
| Null 95th percentile / 80%-power MDE | +0.97% / +1.61% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Audits (tester replay, entropy hash, trainer target, trainer hash) | all passed on 4 blocks |
| Log chain | valid, head b100e98bd4c9a763… |
| Commitment | 3fc73dc0cc07cf32… (verified at reveal) |
| Protocol / analysis hash | b759c4e4876d3743… / 01dff4c7cdf89569… |
| Code | e3010f263993 |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 1890.0 | 1882.0 | 0.43% |
| blinker | 12 | 1917.0 | 1937.4 | -1.05% |
| beehive | 12 | 988.3 | 987.6 | 0.08% |
| loaf | 12 | 331.5 | 338.4 | -2.04% |
| boat | 12 | 307.5 | 320.9 | -4.17% |

Topology: three processes on one host (separate data dirs, separate secrets, HTTP only). Entropy: node:crypto randomBytes (OS CSPRNG).
