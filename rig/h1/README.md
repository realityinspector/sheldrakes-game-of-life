# rig/h1: a human in the loop

A person solves six number puzzles and holds each answer in mind for a minute. Meanwhile,
two blind drawers count how often uniform random search over 455 possible answers lands on
each of the session's twelve candidates. The drawers use the CPU's hardware noise source
(RDSEED) and the kernel CSPRNG. Which six of the twelve the person works on is drawn from OS
entropy and sealed before the session. The full protocol and analysis are in
`docs/prereg/h1.md`.

| File | Role |
|---|---|
| `registrar.py` | `new` opens a session: it publishes the pool and a commitment, and seals the assignment in `.private/`. `reveal <sid>` opens the seal and checks it against the commitment. |
| `drawer.c` | Blind counter for one entropy source. It is given only the candidates. |
| `run-session.sh` | Runs both drawers as `rig-tester` for 30 minutes from "go". |
| `page/hold-the-numbers.html` | The person's page, published as an artifact. It gets only the six trained puzzles. |
| `analyze.py` | Scores one session, or the whole series. |
| `sessions/`, `results/` | Public session files (pool and commitment, plus the assignment after the reveal) and their scores. |

## Sessions

| Session | Human | Trained lift, rdseed (MDE) | Trained lift, urandom (MDE) | Hold windows (rdseed / urandom) | Verdict |
|---|---|---|---|---|---|
| `h1-20261025-173905-7dee` | 6/6 solved first try, every hold complete | −0.027% (0.033%), p 0.94 | +0.0003% (0.006%), p 0.44 | +0.04% p 0.21 / −0.01% p 0.85 | not detected |

The series is scored with `analyze.py series` and is read as a result only from the fifth
session on.
