# Rig report: isolation-2

Anomaly: trained forms were over-represented in the isolated tester (effect +1.58%, 95% CI +0.44% to +2.76%, Holm p = 0.00648). Not a claim yet: it needs replication on physically separate machines with independent entropy.

| | |
|---|---|
| Primary T1 (block-locked) | effect +1.58%, 95% CI +0.44% to +2.76%, p 0.00324, Holm 0.00648 |
| Secondary T2 (cumulative dose) | mean correlation 0.0928, p 0.212, Holm 0.212 |
| Null 95th percentile / 80%-power MDE (Holm) | +0.92% / +1.75% |
| Blocks · α | 60 · 0.05 |
| Training occurrences | 49152000 |
| Blocks that overran the fixed training time | 0 |
| Audits (tester replay from committed bytes + beacon, bytes hash, trainer target, trainer hash) | all passed on all 60 blocks |
| Log chain | valid, head bdf2afe63d20afaa… |
| Commitment | 07f05d2116e81440… (verified at reveal) |
| Protocol / code hash | 8206ba4636cc3512… / 8eff00bfe68b6f2f… (code re-hashed at reveal) |
| Code | 61ca574877c5 |

| Form | Times trained | Mean count when trained | Mean count otherwise | Difference |
|---|---|---|---|---|
| block | 12 | 1894.8 | 1887.9 | 0.36% |
| blinker | 12 | 1930.7 | 1943.4 | -0.65% |
| beehive | 12 | 1010.5 | 984.6 | 2.63% |
| loaf | 12 | 352.0 | 337.0 | 4.44% |
| boat | 12 | 321.8 | 316.9 | 1.54% |

Topology: three processes on one host, each as its own system user with a private 0700 data dir; separate secrets; HTTP only. Entropy: node:crypto randomBytes (OS CSPRNG), committed before mixing with a registrar beacon.
