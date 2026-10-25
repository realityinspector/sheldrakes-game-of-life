# Rig report: isolation-4-6

No effect detected. Estimated effect +0.09% (95% CI -0.16% to +0.34%), Holm p = 0.448. An effect of +0.40% or more would have been detected with about 80% power under the Holm decision.

| | |
|---|---|
| Primary T1 (block-locked) | effect +0.09%, 95% CI -0.16% to +0.34%, p 0.247, Holm 0.448 |
| Secondary T2 (cumulative dose) | mean correlation 0.0651, p 0.224, Holm 0.448 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.23% / +0.40% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head e965b58f5d0fb60f… |
| Commitment | eac4803e5418e225… (verified at reveal) |
| Protocol / code hash | 49834ee56c6416d7… / 88087ad2a561ad44… (code re-hashed at reveal) |
| Code | 33657833c46c |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 37867.0 | 37805.9 | 0.16% |
| blinker | 12 | 38611.7 | 38646.8 | -0.09% |
| beehive | 12 | 19680.6 | 19745.4 | -0.33% |
| loaf | 12 | 6767.8 | 6743.6 | 0.36% |
| boat | 12 | 6353.8 | 6329.7 | 0.38% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
