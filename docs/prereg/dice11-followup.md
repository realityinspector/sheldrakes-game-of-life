# Pre-registration: dice11 follow-up ladder

Written and pushed while the dice11 confirmatory mega run (code `f39661d`, illustration seed
derived from that commit hash) was still running, before its final attempt sealed.

## Why

The dice11 mega run spends α as 0.05·6/(π²k²) per attempt. Its 16-seed screen let many
recipes through, so by the time glider-flock recipes reached a 64-seed test (attempts 9, 11,
14, 15) their α was 1–4 × 10⁻⁴, and they missed despite p ≈ 10⁻³ against Yoked. The mega run's
result stands as recorded. This document fixes, in advance, one follow-up test that uses the
mega run only for selection.

## Selection rule (fixed now)

Among the attempts the dice11 mega run sealed, take those where the field led on more
non-tied seeds than it trailed against **both** nulls. Choose the one with the smallest
`max(p_yoked, p_scrambled)`; ties go to the earlier attempt. If none qualifies, there is no
follow-up. No other recipe from that run will be tested.

## Test

`SweepRunner.startLadder()` on the chosen recipe and its preset, protocol `dice11`, at the
code of the commit that adds this file:

1. 64-seed paired sign test against Yoked and against Scrambled, both at α = 0.05.
2. If Specific: naive retest (innate off, coupling 0, empty archive, same target forms),
   64 seeds, both nulls at α = 0.05.
3. If that passes: dose curve, 0/1/10/100 training seeds, the same 64 test seeds at every
   dose, Page's trend test one-sided at α = 0.05.

Learned requires all three, so a false Learned has probability at most 0.05. Seeds come
from the ladder's own first-row hash (it carries `single: true`), so none is a mega-run
seed. A miss at any stage ends it. The result is reported whatever it is.

This is the second confirmatory family in this program, after the dice11 mega run.
Neither can show morphic resonance: both measure the table.
