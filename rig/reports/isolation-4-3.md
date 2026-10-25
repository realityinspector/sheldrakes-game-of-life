# Rig report: isolation-4-3

No effect detected. Estimated effect +0.24% (95% CI -0.04% to +0.53%), Holm p = 0.107. An effect of +0.42% or more would have been detected with about 80% power under the Holm decision.

| | |
|---|---|
| Primary T1 (block-locked) | effect +0.24%, 95% CI -0.04% to +0.53%, p 0.0535, Holm 0.107 |
| Secondary T2 (cumulative dose) | mean correlation -0.0737, p 0.541, Holm 0.541 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.24% / +0.42% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head 67fa64a264ca7c03… |
| Commitment | bb927f1a3c284ab1… (verified at reveal) |
| Protocol / code hash | 7332837edadf8ddf… / 88087ad2a561ad44… (code re-hashed at reveal) |
| Code | 33657833c46c |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 37797.3 | 37745.7 | 0.14% |
| blinker | 12 | 38633.5 | 38618.9 | 0.04% |
| beehive | 12 | 19738.3 | 19699.3 | 0.20% |
| loaf | 12 | 6748.3 | 6726.3 | 0.33% |
| boat | 12 | 6371.9 | 6339.5 | 0.51% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
