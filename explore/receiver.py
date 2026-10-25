"""Noise figure of each receiver: the smallest constant relative lift on the trained form's
counts that a block-locked (lag-0) lens would detect with 80% power at two-sided 0.05,
measured per session from (a) the lens's spread over assignment shuffles and (b) its response
to a synthetic lift injected into the trained blocks. Choosing a receiver by this number uses
only the noise, not the observed signal, so it does not spend the data.
"""
import copy, os, sys
import numpy as np
from load import load, NAMED
from battery import responses, SESSIONS, OUT

P = 4000
DELTA = 0.01


def inject(d, delta):
    e = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in d.items()}
    forms = d["meta"]["forms"]
    for b, t in enumerate(d["target"]):
        j = NAMED.index(t)
        for g in range(3):
            add = e["tot"][g][b, j] * delta
            e["tot"][g][b, j] += add
            e["allobj"][g][b] += add
            n = d["per"].shape[1]
            p = e["pres"][g][b, j] / n
            lam = -np.log(max(1e-9, 1 - p))
            e["pres"][g][b, j] = n * (1 - np.exp(-lam * (1 + delta)))
    return e


def main():
    rng = np.random.default_rng(7)
    table = {}
    for s in SESSIONS:
        d = load(os.path.join(OUT, f"{s}.jsonl"))
        forms = d["meta"]["forms"]
        a = np.array([forms.index(t) for t in d["target"]])
        A = rng.permuted(np.tile(a, (P, 1)), axis=1)
        B, F = len(a), len(forms)
        I = np.zeros((P, B, F)); np.put_along_axis(I, A[:, :, None], 1.0, axis=2)
        Iobs = np.zeros((B, F)); Iobs[np.arange(B), a] = 1
        R0 = responses(d, None)
        R1 = responses(inject(d, DELTA), None)
        for rname in R0:
            if rname == "tail300":
                continue
            Y0 = R0[rname] - R0[rname].mean(axis=0)
            Y1 = R1[rname] - R1[rname].mean(axis=0)
            var = Y0.var(axis=0)
            for wname, w in (("eq", np.ones(F)), ("ivw", 1 / var)):
                S = np.einsum("pbf,bf->p", I, Y0 * w)
                slope = ((Iobs * (Y1 - Y0) * w).sum()) / DELTA
                mde = 2.8016 * S.std() / slope if slope > 0 else np.inf
                table.setdefault(f"{rname}|{wname}", []).append(mde)
    rows = sorted(table.items(), key=lambda kv: np.median(kv[1]))
    print(f"{'receiver':<18} median MDE   per session ({', '.join(SESSIONS)})")
    for k, v in rows:
        print(f"{k:<18} {100*np.median(v):6.2f}%    " + "  ".join(f"{100*x:5.2f}" for x in v))


if __name__ == "__main__":
    main()
