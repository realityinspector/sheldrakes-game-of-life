# Rig report: positive-control-2pct (POSITIVE CONTROL: deliberate channel)

Positive control: the deliberate +2.0% channel was detected (Holm p = 0.0000400). The rig can see an effect of this size.

| | |
|---|---|
| Primary T1 (block-locked) | effect +3.17%, CI +1.97% to +4.37%, p 0.0000200, Holm 0.0000400 |
| Secondary T2 (cumulative dose) | mean correlation 0.0749, p 0.0247, Holm 0.0247 |
| Null 95th percentile / 80%-power MDE | +0.96% / +1.59% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Audits (tester replay, entropy hash, trainer target, trainer hash) | all passed on 4 blocks |
| Log chain | valid, head 2c3f864e3026b168… |
| Commitment | d8095f7dfb39420f… (verified at reveal) |
| Protocol / analysis hash | 100e667ccca1e760… / 01dff4c7cdf89569… |
| Code | e3010f263993 |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 1902.3 | 1884.0 | 0.97% |
| blinker | 12 | 1965.0 | 1923.0 | 2.18% |
| beehive | 12 | 1022.0 | 976.0 | 4.71% |
| loaf | 12 | 345.8 | 330.7 | 4.55% |
| boat | 12 | 327.3 | 315.3 | 3.81% |

Topology: three processes on one host (separate data dirs, separate secrets, HTTP only). Entropy: node:crypto randomBytes (OS CSPRNG).
