# Rig report: isolation-4-4

No effect detected. Estimated effect -0.29% (95% CI -0.61% to +0.02%), Holm p = 1.00. An effect of +0.42% or more would have been detected with about 80% power under the Holm decision.

| | |
|---|---|
| Primary T1 (block-locked) | effect -0.29%, 95% CI -0.61% to +0.02%, p 0.969, Holm 1.00 |
| Secondary T2 (cumulative dose) | mean correlation -0.0718, p 0.653, Holm 1.00 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.25% / +0.42% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head 4ed69263160cc3f6… |
| Commitment | bc9125a2a6e331bf… (verified at reveal) |
| Protocol / code hash | 376cb185cf1f616d… / 88087ad2a561ad44… (code re-hashed at reveal) |
| Code | 33657833c46c |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 37791.8 | 37846.3 | -0.14% |
| blinker | 12 | 38504.8 | 38666.3 | -0.42% |
| beehive | 12 | 19694.2 | 19729.0 | -0.18% |
| loaf | 12 | 6743.4 | 6754.5 | -0.16% |
| boat | 12 | 6307.8 | 6339.7 | -0.50% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
