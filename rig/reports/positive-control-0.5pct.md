# Rig report: positive-control-0.5pct (POSITIVE CONTROL: deliberate channel)

Positive control: the deliberate +0.5% channel was detected (Holm p = 0.00476). The rig can see an effect of this size.

| | |
|---|---|
| Primary T1 (block-locked) | effect +0.35%, 95% CI +0.11% to +0.59%, p 0.00238, Holm 0.00476 |
| Secondary T2 (cumulative dose) | mean correlation 0.0809, p 0.641, Holm 0.641 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.20% / +0.35% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head 2a6beb5ea192b21e… |
| Commitment | cd4b5354357637c6… (verified at reveal) |
| Protocol / code hash | f6201c6a8752f51d… / 88087ad2a561ad44… (code re-hashed at reveal) |
| Code | 33657833c46c |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 37934.1 | 37793.1 | 0.37% |
| blinker | 12 | 38646.2 | 38590.8 | 0.14% |
| beehive | 12 | 19729.1 | 19708.1 | 0.11% |
| loaf | 12 | 6799.7 | 6761.3 | 0.57% |
| boat | 12 | 6366.1 | 6329.8 | 0.57% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
