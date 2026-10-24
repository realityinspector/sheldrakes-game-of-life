# Sheldrake's morphic laboratory

A playable web successor to the Python simulation that used to live in this repository. It is a toy morphic field inside Conway's Game of Life, not a claim that morphic resonance is real.

Four boards share one seed and B3/S23. Control is never modified. The field consults one neighbourhood per 32 cells each generation and may overwrite a cell after consulting crystals. The yoked null writes the same number of flips at random. The scrambled null keeps the machinery, permutes the picture, and is rate-matched to write the same number of cells. Specificity is facilitation of the trained forms minus facilitation of four comparison still lifes, counted by an object census in which every form is named by its shape (translation, rotation and reflection removed). Seeds for a confirmatory batch come from a hash of the frozen configuration.

A mega run keeps going while the page is open. An armed recipe with a single-seed gap of 0.20 or wider is screened on 16 seeds of its own (the field must lead both nulls on at least 11); only a recipe that holds up is frozen for a 64-seed sign test against both nulls. Every stage of the k-th attempt in a run must clear α = 0.05 · 6/(π²k²), so a false Specific or a false Learned anywhere in the run stays under 0.05. If the sign test passes, a naive retest (innate forms off, coupling 0, empty archive, same target forms) and then a dose curve (0, 1, 10, 100 training seeds; the same 64 test seeds at every dose; Page's trend test). A miss does not end the walk. Nothing this program can print is morphic resonance: turn the field off and the boards lock.

`rig/` holds the test that could detect a real effect: three servers (registrar, trainer, tester), OS entropy, a sealed assignment, a pre-registered randomization test and a positive control. See `rig/README.md` and `rig/reports/`.

```bash
npm install
npm run dev
npm test          # simulation, batch workflow and rig tests
npm run rig -- rig/protocols/positive-control-2pct.json
npm run typecheck
```

`npm run test:platform` runs the hosting template's own tests. They expect the builder sandbox's untracked `.grok/` directory and fail without it.

The rules are in `src/sim/protocol.ts`; `ANALYSIS_VERSION` is hashed into every confirmatory row and changes whenever scoring does. The method page (`/method`) states what each level is allowed to mean.

The earlier Python sources remain in the git history, before commit 582bbb4.
