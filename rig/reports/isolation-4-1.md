# Rig report: isolation-4-1

No effect detected. Estimated effect -0.11% (95% CI -0.41% to +0.20%), Holm p = 1.00. An effect of +0.41% or more would have been detected with about 80% power under the Holm decision.

| | |
|---|---|
| Primary T1 (block-locked) | effect -0.11%, 95% CI -0.41% to +0.20%, p 0.757, Holm 1.00 |
| Secondary T2 (cumulative dose) | mean correlation 0.1472, p 0.750, Holm 1.00 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.23% / +0.41% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head eb0c68d0c441a989… |
| Commitment | ab4b9b5d6b0efe8e… (verified at reveal) |
| Protocol / code hash | d3328699700dbfb2… / 88087ad2a561ad44… (code re-hashed at reveal) |
| Code | 33657833c46c |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 37748.8 | 37785.1 | -0.10% |
| blinker | 12 | 38586.6 | 38701.5 | -0.30% |
| beehive | 12 | 19648.8 | 19711.5 | -0.32% |
| loaf | 12 | 6748.8 | 6746.8 | 0.03% |
| boat | 12 | 6344.3 | 6333.0 | 0.18% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
