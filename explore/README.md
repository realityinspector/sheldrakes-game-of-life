# Receiver work: reprocessing the rig's recordings

The rig keeps every byte the tester drew, so any session can be reprocessed with a
different "receiver" long after it ran. This folder holds that work.

| File | What it does |
|---|---|
| `replay.ts` | Replays a session's tester from its committed bytes and beacons. Per soup it records the full census at generations 100, 200 and 300, the population, and the initial density. It aborts unless the generation-300 counts equal what the tester reported. |
| `rawbits.py` | Counts exact copies of each form's cell pattern in the soups' initial bits, both the raw entropy and after the beacon mix. This tests whether training biases the entropy itself. |
| `load.py` | Compacts a replay into numpy arrays. |
| `battery.py` | Scores 363 lenses: dose kernels × responses × weighting, Fourier cross-spectra, and cross-form relatives. Each is calibrated by exact assignment shuffles, sessions are combined with Stouffer, and Westfall–Young max-\|Z\| gives a family-wise p that pays for every lens tried. Also scores a dispersion family, Σ z² across sessions. |
| `receiver.py` | Noise figure (80%-power MDE) of each receiver, from shuffle spread and a synthetic injected lift. It uses only the noise, so choosing a receiver with it does not spend the data. |
| `confirm.py` | The frozen, pre-registered analysis of the isolation-4 series (`docs/prereg/isolation-4.md`). |
| `run-isolation-4.sh` | Runs that series and scores it. |
| `results/` | Battery output for the five earlier sessions and the isolation-4 series. |

Intermediate data (`.out/`) is git-ignored. To regenerate it from `rig/.data/`, run
`replay.ts` and `rawbits.py` per session, then the Python scripts with `explore/` as the
working directory.
