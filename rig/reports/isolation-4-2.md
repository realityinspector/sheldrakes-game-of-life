# Rig report: isolation-4-2

No effect detected. Estimated effect +0.18% (95% CI -0.12% to +0.50%), Holm p = 0.0875. An effect of +0.39% or more would have been detected with about 80% power under the Holm decision.

| | |
|---|---|
| Primary T1 (block-locked) | effect +0.18%, 95% CI -0.12% to +0.50%, p 0.0875, Holm 0.0875 |
| Secondary T2 (cumulative dose) | mean correlation -0.0580, p 0.0180, Holm 0.0359 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.22% / +0.39% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head a89422b08c3eec6e… |
| Commitment | ea0ebeb08a8efbb5… (verified at reveal) |
| Protocol / code hash | bb9d541d192e155a… / 88087ad2a561ad44… (code re-hashed at reveal) |
| Code | 33657833c46c |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 37794.6 | 37757.8 | 0.10% |
| blinker | 12 | 38754.7 | 38622.7 | 0.34% |
| beehive | 12 | 19727.3 | 19696.8 | 0.15% |
| loaf | 12 | 6735.8 | 6751.1 | -0.23% |
| boat | 12 | 6384.3 | 6347.0 | 0.59% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
