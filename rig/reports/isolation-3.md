# Rig report: isolation-3

No effect detected. Estimated effect -0.70% (95% CI -1.94% to +0.56%), Holm p = 1.00. An effect of +1.79% or more would have been detected with about 80% power under the Holm decision.

| | |
|---|---|
| Primary T1 (block-locked) | effect -0.70%, 95% CI -1.94% to +0.56%, p 0.835, Holm 1.00 |
| Secondary T2 (cumulative dose) | mean correlation -0.0336, p 0.804, Holm 1.00 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.96% / +1.79% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head 96984b3c45ea9d07… |
| Commitment | c865de6ee40172c5… (verified at reveal) |
| Protocol / code hash | f2deb295aac357b8… / 8eff00bfe68b6f2f… (code re-hashed at reveal) |
| Code | ba43eb619523 |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 1884.9 | 1894.0 | -0.48% |
| blinker | 12 | 1940.6 | 1925.7 | 0.77% |
| beehive | 12 | 985.4 | 992.4 | -0.71% |
| loaf | 12 | 334.3 | 339.3 | -1.48% |
| boat | 12 | 314.3 | 318.0 | -1.17% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
