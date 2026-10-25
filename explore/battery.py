"""Lens battery over the rig sessions, calibrated so that looking at many lenses is paid for.

Every lens is a statistic of (assignment, tester data). Within a session the assignment was
a uniform shuffle of a balanced list, so re-shuffling it gives that lens's exact null. Each
lens's per-session statistic is turned into a normal score by its rank among P shuffles;
sessions are combined by Stouffer. Westfall-Young max-T across *all* lenses gives a
family-wise p that already accounts for every lens tried (the "flashing" itself).

Lens = dose kernel (how training at block b' should show up at block b) x response (what the
receiver measures) x weighting. Plus Fourier lenses on the indicator/response cross-spectrum
and a cross-session dispersion family (sum of squared per-session z).
"""
import json, os, sys
import numpy as np
from scipy.signal import lfilter
from scipy.special import ndtri
from load import load, NAMED

OUT = os.path.join(os.path.dirname(__file__), ".out")
P = int(os.environ.get("PERMS", 20000))
SEED = 20261025

SESSIONS = os.environ.get("SESSIONS", "isolation-1,isolation-2,isolation-3,positive-control-2pct,positive-control-2pct-v2").split(",")
RELATIVES = {"loaf": ["beehive"], "beehive": ["loaf"], "pond": ["beehive", "loaf"], "ship": ["boat"], "tub": ["boat"]}


def kernels(I):
    """I: (P,B,F) indicator of the trained form. Returns name -> dose (P,B,F)."""
    P_, B, F = I.shape
    out = {"lag0": I}
    for k in (1, 2, 3):
        D = np.zeros_like(I); D[:, k:] = I[:, :-k]; out[f"lag{k}"] = D
    for k in (1, 2):
        D = np.zeros_like(I); D[:, :-k] = I[:, k:]; out[f"lead{k}"] = D
    for tau in (2, 5, 15):
        out[f"exp{tau}"] = lfilter([1.0], [1.0, -np.exp(-1.0 / tau)], I, axis=1)
    out["cum"] = np.cumsum(I, axis=1)
    t = np.arange(B, dtype=float); t = (t - t.mean()) / t.std()
    out["growth"] = I * t[None, :, None]
    return out


def logit(x):
    x = np.clip(x, 0.5, None)
    return np.log(x) - np.log1p(-x / 1000.0) - np.log(1000.0) * 0  # presence share logit (n=1000 soups)


def responses(d, rb):
    forms = d["meta"]["forms"]
    cols = [NAMED.index(f) for f in forms]
    tot, allobj, pop = d["tot"], d["allobj"], d["pop"]
    L = {g: np.log(tot[i][:, cols] + 0.5) for i, g in enumerate((100, 200, 300))}
    R = {
        "log300": L[300], "log200": L[200], "log100": L[100],
        "rel300": L[300] - np.log(allobj[2])[:, None],
        "comp300": L[300] - L[300].mean(axis=1, keepdims=True),
        "accel": L[100] - L[300],
    }
    X = np.column_stack([np.ones(len(L[300])), np.log(allobj[2]), np.log(pop[2]), d["d0"]])
    beta, *_ = np.linalg.lstsq(X, L[300], rcond=None)
    R["resid300"] = L[300] - X @ beta
    pr = d["pres"][2][:, cols] / d["per"].shape[1]
    pr = np.clip(pr, 1e-3, 1 - 1e-3)
    R["pres300"] = np.log(pr / (1 - pr))
    R["rank300"] = np.argsort(np.argsort(L[300], axis=0), axis=0).astype(float)
    per = d["per"][:, :, cols].astype(float)  # (B, soups, F)
    q90 = np.quantile(per.reshape(-1, len(cols)), 0.9, axis=0)
    R["tail300"] = (per > q90[None, None, :]).mean(axis=1)
    if rb is not None:
        rcols = [list(rb["named"]).index(f) for f in forms]
        R["rawbits"] = np.log(rb["raw"][:, rcols] + 0.5)
        R["mixbits"] = np.log(rb["mixed"][:, rcols] + 0.5)
    return R


def rank_z(S):
    """S: (P+1,) statistic, index 0 observed. Normal scores of ranks (upper tail = large S)."""
    r = np.argsort(np.argsort(S, kind="stable"), kind="stable") + 1  # 1..P+1
    return ndtri((r - 0.5) / len(S))


def session_lenses(d, rb, A):
    """A: (P+1,B) assignments (row 0 observed). Returns lens -> (z (P+1,), directional?)."""
    forms = d["meta"]["forms"]
    F = len(forms)
    B = A.shape[1]
    I = np.zeros((A.shape[0], B, F), dtype=np.float32)
    np.put_along_axis(I, A[:, :, None], 1.0, axis=2)
    K = kernels(I)
    R = responses(d, rb)
    Fi = np.fft.rfft(I - I.mean(axis=1, keepdims=True), axis=1)  # (P,K,F)
    lenses = {}
    for rname, Y in R.items():
        Yc = Y - Y.mean(axis=0, keepdims=True)
        var = Yc.var(axis=0)
        for wname, w in (("eq", np.ones(F)), ("ivw", 1.0 / np.where(var > 0, var, np.inf))):
            Wy = Yc * w[None, :]
            for kname, D in K.items():
                S = np.einsum("pbf,bf->p", D, Wy, optimize=True)
                lenses[f"{kname}|{rname}|{wname}"] = (rank_z(S), True)
            # Fourier: cross-spectrum of indicator and response.
            Fy = np.fft.rfft(Wy, axis=0)  # (K,F)
            X = np.einsum("pkf,kf->pk", Fi, np.conj(Fy))[:, 1:]  # drop DC
            pw = np.abs(X) ** 2
            pz = (pw - pw[1:].mean(axis=0)) / pw[1:].std(axis=0)
            lenses[f"specmax|{rname}|{wname}"] = (rank_z(pz.max(axis=1)), False)
            nk = X.shape[1]
            lenses[f"speclow|{rname}|{wname}"] = (rank_z(X[:, : nk // 6].real.sum(axis=1)), True)
            lenses[f"spechigh|{rname}|{wname}"] = (rank_z(X[:, -nk // 3 :].real.sum(axis=1)), True)
            lenses[f"specmag|{rname}|{wname}"] = (rank_z(np.abs(X).sum(axis=1)), False)
    # Exact T1 as the rig computes it (log of count vs the form's untrained-block mean).
    C = d["tot"][2][:, [NAMED.index(f) for f in forms]]
    tgt = C[np.arange(B)[None, :], A]  # (P+1,B)
    sumall = C.sum(axis=0)
    cnt_tr = I.sum(axis=1)  # (P+1,F) times trained (12 each)
    sum_tr = np.einsum("pbf,bf->pf", I, C)
    u = (sumall[None, :] - sum_tr) / (B - cnt_tr)
    uT = np.take_along_axis(u, A, axis=1)
    lenses["T1 (rig)"] = (rank_z(np.log((tgt + 0.5) / (uT + 0.5)).mean(axis=1)), True)
    # Cross-form generalization: does training a form raise its near relatives?
    ids = [NAMED.index(g) for g in RELATIVES]
    Yg = np.log(d["tot"][2][:, ids] + 0.5)
    Yg = Yg - Yg.mean(axis=0)
    Dg = np.zeros((A.shape[0], B, len(RELATIVES)), dtype=np.float32)
    for j, (g, rel) in enumerate(RELATIVES.items()):
        for r in rel:
            if r in forms:
                Dg[:, :, j] += I[:, :, forms.index(r)]
    lenses["relatives|log300|eq"] = (rank_z(np.einsum("pbf,bf->p", Dg, Yg)), True)
    gv = Yg.var(axis=0)
    lenses["relatives|log300|ivw"] = (rank_z(np.einsum("pbf,bf->p", Dg, Yg / np.where(gv > 0, gv, np.inf))), True)
    return lenses


def main():
    rng = np.random.default_rng(SEED)
    per_session = {}
    for s in SESSIONS:
        d = load(os.path.join(OUT, f"{s}.jsonl"))
        rbp = os.path.join(OUT, f"{s}.rawbits.npz")
        rb = np.load(rbp) if os.path.exists(rbp) else None
        forms = d["meta"]["forms"]
        a = np.array([forms.index(t) for t in d["target"]])
        A = np.vstack([a, rng.permuted(np.tile(a, (P, 1)), axis=1)])
        per_session[s] = session_lenses(d, rb, A)
        print(f"{s}: {len(per_session[s])} lenses", file=sys.stderr)
    results = {}
    for subset_name, subset in (("all", SESSIONS), ("first3", SESSIONS[:3])):
        names = sorted(set.intersection(*[set(per_session[s]) for s in subset]))
        Zc, Q, direc = [], [], []
        for n in names:
            zs = np.stack([per_session[s][n][0] for s in subset])  # (S,P+1)
            Zc.append(zs.sum(axis=0) / np.sqrt(len(subset)))
            Q.append((zs ** 2).sum(axis=0))
            direc.append(per_session[subset[0]][n][1])
        Zc, Q, direc = np.array(Zc), np.array(Q), np.array(direc)
        T = np.where(direc[:, None], np.abs(Zc), Zc)  # evidence statistic per lens per draw
        Mx = T[:, 1:].max(axis=0)
        adj = np.array([(1 + (Mx >= T[i, 0]).sum()) / (P + 1) for i in range(len(names))])
        raw = np.array([(1 + (T[i, 1:] >= T[i, 0]).sum()) / (P + 1) for i in range(len(names))])
        # dispersion family (directional lenses only)
        dn = [i for i in range(len(names)) if direc[i]]
        Qm = Q[dn][:, 1:].max(axis=0)
        qadj = {names[i]: float((1 + (Qm >= Q[i, 0]).sum()) / (P + 1)) for i in dn}
        qraw = {names[i]: float((1 + (Q[i, 1:] >= Q[i, 0]).sum()) / (P + 1)) for i in dn}
        rows = []
        for i, n in enumerate(names):
            rows.append(dict(lens=n, Z=float(Zc[i, 0]), raw_p=float(raw[i]), fw_p=float(adj[i]),
                             per_session=[float(per_session[s][n][0][0]) for s in subset],
                             Q=float(Q[i, 0]) if direc[i] else None, Q_raw_p=qraw.get(n), Q_fw_p=qadj.get(n)))
        rows.sort(key=lambda r: r["raw_p"])
        results[subset_name] = dict(sessions=subset, lenses=len(names), perms=P, rows=rows,
                                    expected_min_raw_p=1.0 / len(names))
    json.dump(results, open(os.path.join(OUT, "battery.json"), "w"), indent=1)
    for k, v in results.items():
        print(f"\n== {k}: {v['lenses']} lenses, {P} shuffles per session")
        for r in v["rows"][:15]:
            print(f"{r['lens']:<28} Z {r['Z']:+.2f}  raw p {r['raw_p']:.4f}  family-wise p {r['fw_p']:.3f}  z/session {' '.join(f'{z:+.2f}' for z in r['per_session'])}")
        qs = sorted([r for r in v["rows"] if r["Q"] is not None], key=lambda r: r["Q_raw_p"])[:8]
        print("-- dispersion (sum of z^2 across sessions)")
        for r in qs:
            print(f"{r['lens']:<28} Q {r['Q']:.1f}  raw p {r['Q_raw_p']:.4f}  family-wise p {r['Q_fw_p']:.3f}")


if __name__ == "__main__":
    main()
