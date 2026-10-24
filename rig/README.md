# Isolation rig

The web lab cannot test morphic resonance: its "memory" is a table in the same process
that writes the cells. This rig is a test that could detect a real effect if one exists.
The process that measures has no copy of the trained form, no table, and no channel the
rig provides for learning which form was trained.

## Question

A form is made to occur hundreds of thousands of times in one process (the trainer). Is
that form then over-represented among the forms that arise in another, isolated process
(the tester)? The tester runs pure Conway on random soups drawn from OS entropy, without
being told which form was trained.

- **T1 (primary, block-locked).** The trained form's count in its own block, compared with
  that form's mean count in the blocks where it was not trained.
- **T2 (secondary, cumulative dose).** Within each form, the correlation between how many
  times it has been trained so far and its count.

Both are exact, one-sided randomization tests on the sealed balanced assignment, with
Holm across the two at α = 0.05. The reported minimum detectable effect is for 80% power
under Holm's worst case (T1 at α/2).

## Three servers (rig/2)

| Server | Knows | Never sees |
|---|---|---|
| **Registrar** (`registrar.ts`) | The assignment. Drawn from OS entropy; only `sha256(assignment ‖ 256-bit nonce)` and a hash of the rig's code are published before anything runs. Enforces train b → test b → train b+1 and accepts results only for the block it handed out. Keeps a hash-chained log that is not served until the reveal. Re-hashes the code at the reveal and refuses to score if it changed. | — |
| **Trainer** (`trainer.ts`) | Its own target, one block at a time. Stamps a lattice of non-interacting copies and runs them under Conway. Every block is padded to a fixed duration, so timing doesn't reveal the form; a block that overruns is flagged. Each record carries a random salt, so its hash can't be brute-forced back to the target. Records are sealed until the reveal. | The tester. |
| **Tester** (`tester.ts`) | Only "go" for block b: the block number, the spec, and the full list of candidate forms. It draws raw bytes from `crypto.randomBytes`, commits to their hash, then receives a registrar beacon and turns bytes ⊕ beacon keystream into soups (one bit per cell). It runs plain B3/S23 and counts every candidate form. It keeps the raw bytes so anyone can replay its counts. | The target, the trainer, the table. It imports no morphic code. |

Each server holds only its own bearer token. Run locally as root, `run-local.ts` starts
each server as its own system user (`rig-registrar`, `rig-trainer`, `rig-tester`) with a
private 0700 data directory. The tester's user cannot read the trainer's records or the
registrar's log. The commit-then-beacon step means that even a tester that somehow learned
the target could not keep drawing bytes until its soups favoured it.

## Positive control

A protocol with `leak.relative > 0` is a declared channel: the registrar tells the tester
the target, and the tester inflates that count by the given fraction. The leak value is
part of the hashed protocol and is printed at the top of the report. Run the positive
control first to show the rig can see an effect of that size. A real run always has
`leak.relative = 0`, and a test enforces this for the isolation protocols.

## Running it

```bash
npm run rig -- rig/protocols/positive-control-2pct-v2.json   # sensitivity check
npm run rig -- rig/protocols/isolation-2.json                # the pre-registered run
```

The runner drives one session, reveals it, and audits **every** block:
- it replays the tester's counts from its committed bytes and the beacon;
- it checks the bytes against the hash the tester committed;
- it checks each trainer record against the hash it reported.

Reports go to `rig/reports/`. Raw data stays in `rig/.data/`, which is git-ignored.

**On separate machines.** Start each server on its own host with `RIG_HOST=0.0.0.0` and
the env variables listed at the top of each file (the registrar also needs `RIG_ROOT`,
the repository root, to hash the code). Then call the registrar's `POST /session`, wait
for `GET /status` to show every block tested, and call `POST /reveal`.

## Pre-registration

Commit and push the protocol file before running it. The report records
`protocolFileSha256`, `protocolHash` and `codeHash`, so anyone can check them against the
git history.

## Results so far

| Run | Rig | Result |
|---|---|---|
| `positive-control-2pct` | 1 | Deliberate +2% leak detected, estimate +3.2%, Holm p 4e-5 |
| `isolation-1` | 1 | No effect: −1.45% (CI −2.64% to −0.20%), Holm p 0.98, MDE about 1.6% |

The rig/2 runs are listed in `rig/reports/` once they have run. isolation-1's interval
lies just below zero. That is the wrong direction for the hypothesis, wasn't
pre-registered, and is the kind of result chance gives a few times in a hundred.

An independent review of rig/1 found channels the rig itself provided, all closed in
rig/2:
- an unauthenticated log head that let the target be recovered from training-record
  hashes;
- world-readable data files;
- training time that varied with the form;
- a code hash that couldn't fail.

The honest rig/1 tester used none of them, so isolation-1's counts are unaffected. Its
isolation claim was stronger than its design.

## What a result can mean

- **Null.** No effect larger than the reported minimum detectable effect, for these forms,
  this training dose, this entropy source, and this topology.
- **Positive.** An anomaly that needs replication before anyone calls it anything:
  - on physically separate machines,
  - with independent hardware entropy,
  - with other people running the tester.

  A positive here would be evidence about this rig, not yet about morphic resonance.

## Known limits

- **One host.** Locally, the three servers share a kernel and a machine, and root can read
  everything. The OS CSPRNG's output carries no statistically usable trace of what other
  processes do, but separate machines remove the question.
- **Entropy source.** `/dev/urandom` is a CSPRNG seeded from hardware noise. It is not a
  raw physical source. A raw hardware RNG would be a stricter test.
- **Carryover.** Every form is trained repeatedly, so any lasting effect from earlier
  blocks shows up in all forms. That pushes T1 toward the null. T2 is the dose-response
  check.
- **Scope.** Whether bit patterns in a computer are "forms" in Sheldrake's sense is part of
  what is being tested, not something the rig assumes.
