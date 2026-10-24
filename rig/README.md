# Isolation rig

The web lab cannot test morphic resonance: its "memory" is a table in the same process
that writes the cells. This rig is a test that could detect a real effect if one
exists. The process that measures has no copy of the trained form, no table, and no way
to learn which form was trained.

## Question

A form is made to occur hundreds of thousands of times in one process (the trainer). Is
that form then over-represented among the forms that arise in another, isolated process
(the tester)? The tester runs pure Conway on random soups drawn from OS entropy, without
being told which form was trained.

- **T1 (primary, block-locked).** Within a block, the trained form's count compared
  with that form's mean count in the blocks where it was not trained.
- **T2 (secondary, cumulative dose).** Within each form, the correlation between how
  many times it has been trained so far and its count.

Both tests are exact, one-sided randomization tests on the sealed balanced assignment,
with Holm correction across the two at α = 0.05. The analysis code is hashed into the
log before any block runs, so it can't be changed after the data are in.

## Three servers

| Server | Knows | Never sees |
|---|---|---|
| **Registrar** (`registrar.ts`) | The assignment (which form each block trains). It draws the assignment from OS entropy and publishes only `sha256(assignment ‖ nonce)` before anything runs. It enforces train b → test b → train b+1 and keeps an append-only, hash-chained log. It reveals and scores only after every block is in. | — |
| **Trainer** (`trainer.ts`) | Its own target, one block at a time. It stamps a lattice of non-interacting copies and runs them under Conway. Its audit records are sealed until the reveal. | The tester. |
| **Tester** (`tester.ts`) | Only "go" for block b. It runs soups from `crypto.randomBytes`, one bit per cell, under plain B3/S23 and counts every candidate form. It keeps the raw bytes so anyone can replay its counts. | The target, the trainer and the table. It imports no morphic code. |

Each server holds only its own bearer token. The tester's token can't reach the
trainer's endpoints, and the registrar returns no assignment to the tester. Every
block gets the same amount of training work, so block timing doesn't reveal the
target.

## Positive control

A protocol with `leak.relative > 0` is a declared channel: the registrar tells the
tester the target, and the tester inflates that count by the given fraction. The leak
value is part of the hashed protocol and is printed at the top of the report. Run the
positive control first to show the rig can see an effect of that size. A real run
always has `leak.relative = 0`. A test enforces this for `protocols/isolation-1.json`.

## Running it

```bash
npm run rig -- rig/protocols/positive-control-2pct.json   # sensitivity check
npm run rig -- rig/protocols/isolation-1.json             # the pre-registered run
```

The runner starts three processes with separate data directories and secrets, drives
one session, reveals it, and then audits it. The audit replays the tester's counts from
its stored entropy, checks the entropy hashes, checks the trainer's targets and hashes,
and verifies the log chain. Reports go to `rig/reports/`. Raw data stays in
`rig/.data/`, which is git-ignored.

**On separate machines.** Start each server on its own host with `RIG_HOST=0.0.0.0` and
the env variables listed at the top of each file. The trainer and the tester need
`RIG_REGISTRAR_URL`. Then call the registrar's `POST /session`, wait for `GET /status`
to show every block tested, and call `POST /reveal`.

## Pre-registration

Commit and push the protocol file before running it. The report records
`protocolFileSha256`, `protocolHash` and `analysisHash`, so anyone can check them
against the git history.

## What a result can mean

- **Null.** No effect larger than the reported 80%-power minimum detectable effect, for
  these forms, this training dose, and this entropy source.
- **Positive.** An anomaly that needs replication before anyone calls it anything:
  - on physically separate machines,
  - with independent hardware entropy,
  - with other people running the tester.

  A positive here would be evidence about this rig, not yet about morphic resonance.

## Known limits

- **One host.** Locally, the three processes share a kernel. The OS CSPRNG's output
  carries no statistically usable trace of what other processes do, but separate
  machines remove the question.
- **Entropy source.** `/dev/urandom` is a CSPRNG seeded from hardware noise. It is not a
  raw physical source. A raw hardware RNG would be a stricter test.
- **Carryover.** Every form is trained repeatedly, so any lasting effect from earlier
  blocks shows up in all forms. That pushes T1 toward the null. T2 is the dose-response
  check.
- **Scope.** Whether bit patterns in a computer are "forms" in Sheldrake's sense is part
  of what is being tested, not something the rig assumes.
