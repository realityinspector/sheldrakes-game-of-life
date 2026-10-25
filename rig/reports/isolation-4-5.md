# Rig report: isolation-4-5

No effect detected. Estimated effect -0.04% (95% CI -0.30% to +0.22%), Holm p = 0.655. An effect of +0.36% or more would have been detected with about 80% power under the Holm decision.

| | |
|---|---|
| Primary T1 (block-locked) | effect -0.04%, 95% CI -0.30% to +0.22%, p 0.596, Holm 0.655 |
| Secondary T2 (cumulative dose) | mean correlation -0.1004, p 0.328, Holm 0.655 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.21% / +0.36% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head 4433933c2105eb9d… |
| Commitment | 17ca0ec115edfcfe… (verified at reveal) |
| Protocol / code hash | d5a6ce84e08e4b6b… / 88087ad2a561ad44… (code re-hashed at reveal) |
| Code | 33657833c46c |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 37758.8 | 37828.1 | -0.18% |
| blinker | 12 | 38688.3 | 38635.9 | 0.14% |
| beehive | 12 | 19768.9 | 19684.8 | 0.43% |
| loaf | 12 | 6718.0 | 6756.3 | -0.57% |
| boat | 12 | 6337.3 | 6335.7 | 0.03% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
