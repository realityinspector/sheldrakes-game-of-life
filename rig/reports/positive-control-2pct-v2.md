# Rig report: positive-control-2pct-v2 (POSITIVE CONTROL: deliberate channel)

Positive control: the deliberate +2.0% channel was detected (Holm p = 0.0105). The rig can see an effect of this size.

| | |
|---|---|
| Primary T1 (block-locked) | effect +1.49%, 95% CI +0.27% to +2.72%, p 0.00524, Holm 0.0105 |
| Secondary T2 (cumulative dose) | mean correlation -0.0165, p 0.458, Holm 0.458 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.93% / +1.74% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head 91359b26f25bbf9b… |
| Commitment | 91212b66b4a64864… (verified at reveal) |
| Protocol / code hash | fb8931ba4d9e6675… / 8eff00bfe68b6f2f… (code re-hashed at reveal) |
| Code | 8fb0ef2f81fc |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 1940.3 | 1903.8 | 1.91% |
| blinker | 12 | 1985.8 | 1930.8 | 2.85% |
| beehive | 12 | 1000.7 | 988.4 | 1.24% |
| loaf | 12 | 345.9 | 340.5 | 1.59% |
| boat | 12 | 319.8 | 319.0 | 0.27% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
