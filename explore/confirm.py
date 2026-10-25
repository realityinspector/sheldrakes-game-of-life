"""Pre-registered analysis of the isolation-4 series (docs/prereg/isolation-4.md).

Frozen before any isolation-4 session ran; its SHA-256 is in the pre-registration.

Per session s and lens L, the statistic is standardised by its own assignment-shuffle null
(z = (S - mean) / sd over PERMS shuffles of the sealed balanced assignment). Pooled and
dispersion statistics are scored against the joint shuffle null (each session shuffled
independently, draw j paired across sessions), so every p is a randomization p.

Primary (Holm across H1-H3, alpha 0.05):
  H1  constant lift, improved receiver: Stouffer of z(lag0|log300|ivw), one-sided (up).
  H2  session-level dispersion of the rig's own T1: Q = sum_s z(T1)^2, upper tail.
  H3  dispersion concentrated in beehive and loaf: Q = sum_s sum_{beehive,loaf} z(form)^2.
Secondary (Holm within, reported, no claim):
  S1  lag1|log100|eq, one-sided (down): the strongest lens over the five earlier sessions.
  S2  lag3|rawbits|ivw, one-sided (up): the strongest lens over the three earlier isolation runs.
Sensitivity: the 0.5% positive control, lens lag0|log300|ivw on that session alone, one-sided.

Usage: python3 explore/confirm.py   (after the seven sessions; needs rig/reports/<label>.json,
and for S1/S2 the replay + rawbits outputs in explore/.out/)
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from load import load, NAMED  # noqa: E402

PERMS = 20000
SEED = 4_2026_1025
ISO = [f"isolation-4-{i}" for i in range(1, 7)]
PC = "positive-control-0.5pct"
ALPHA = 0.05


def report(label):
    r = json.load(open(os.path.join(ROOT, "rig", "reports", f"{label}.json")))
    forms = r["report"]["forms"]
    C = np.array([[b["tested"]["counts"][f] for f in forms] for b in r["blocks"]], dtype=float)
    a = np.array([forms.index(t) for t in r["assignment"]])
    leak = np.array([b["tested"].get("leakExtra", 0) for b in r["blocks"]], dtype=float)
    C[np.arange(len(a)), a] += leak  # exactly what the registrar scores
    return forms, a, C


def shuffles(a, rng):
    return np.vstack([a, rng.permuted(np.tile(a, (PERMS, 1)), axis=1)])


def indicator(A, F):
    I = np.zeros((A.shape[0], A.shape[1], F))
    np.put_along_axis(I, A[:, :, None], 1.0, axis=2)
    return I


def std(S):
    return (S - S[1:].mean()) / S[1:].std()


def lens_lag0_ivw(I, C):
    Y = np.log(C + 0.5)
    Yc = Y - Y.mean(axis=0)
    return std(np.einsum("pbf,bf->p", I, Yc / Yc.var(axis=0)))


def lens_t1(A, I, C):
    B = C.shape[0]
    tgt = C[np.arange(B)[None, :], A]
    u = (C.sum(axis=0)[None, :] - np.einsum("pbf,bf->pf", I, C)) / (B - I.sum(axis=1))
    return std(np.log((tgt + 0.5) / (np.take_along_axis(u, A, axis=1) + 0.5)).mean(axis=1))


def lens_form(I, C, f):
    Y = np.log(C[:, f] + 0.5)
    return std((I[:, :, f] * (Y - Y.mean())[None, :]).sum(axis=1))


def lens_kernel(I, Y, lag, weights):
    D = np.zeros_like(I)
    D[:, lag:] = I[:, : I.shape[1] - lag] if lag else I
    Yc = Y - Y.mean(axis=0)
    w = 1 / Yc.var(axis=0) if weights == "ivw" else np.ones(Y.shape[1])
    return std(np.einsum("pbf,bf->p", D, Yc * w))


def p_upper(T):
    return float((1 + (T[1:] >= T[0]).sum()) / (len(T)))


def holm(ps):
    order = np.argsort(ps)
    adj = np.empty(len(ps))
    run = 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - k) * ps[i]))
        adj[i] = run
    return adj.tolist()


def main():
    rng = np.random.default_rng(SEED)
    z1, z2, z3, zs1, zs2, per = [], [], [], [], [], {}
    for label in ISO:
        forms, a, C = report(label)
        A = shuffles(a, rng)
        I = indicator(A, len(forms))
        z1.append(lens_lag0_ivw(I, C))
        z2.append(lens_t1(A, I, C))
        z3.append(np.stack([lens_form(I, C, forms.index(f)) for f in ("beehive", "loaf")]))
        d = load(os.path.join(HERE, ".out", f"{label}.jsonl")) if os.path.exists(os.path.join(HERE, ".out", f"{label}.jsonl")) else None
        if d is not None:
            cols = [NAMED.index(f) for f in forms]
            zs1.append(-lens_kernel(I, np.log(d["tot"][0][:, cols] + 0.5), 1, "eq"))
            rb = np.load(os.path.join(HERE, ".out", f"{label}.rawbits.npz"))
            rcols = [list(rb["named"]).index(f) for f in forms]
            zs2.append(lens_kernel(I, np.log(rb["raw"][:, rcols] + 0.5), 3, "ivw"))
        per[label] = dict(lag0_ivw=float(z1[-1][0]), t1=float(z2[-1][0]), beehive=float(z3[-1][0][0]), loaf=float(z3[-1][1][0]),
                          t1_effect_pct=None)
        r = json.load(open(os.path.join(ROOT, "rig", "reports", f"{label}.json")))
        per[label]["t1_effect_pct"] = 100 * r["report"]["t1"]["effect"]
        per[label]["t1_mde80_pct"] = 100 * r["report"]["t1"]["mde80"]
    K = len(ISO)
    H1 = np.sum(z1, axis=0) / np.sqrt(K)
    H2 = np.sum(np.square(z2), axis=0)
    H3 = np.sum(np.square(z3), axis=(0, 1))
    p = [p_upper(H1), p_upper(H2), p_upper(H3)]
    out = dict(sessions=ISO, perms=PERMS, per_session=per,
               H1=dict(Z=float(H1[0]), p=p[0]), H2=dict(Q=float(H2[0]), df=K, p=p[1]),
               H3=dict(Q=float(H3[0]), df=2 * K, p=p[2]))
    for k, h in zip(("H1", "H2", "H3"), holm(p)):
        out[k]["holm"] = h
        out[k]["supported"] = h < ALPHA
    if len(zs1) == K:
        S1 = np.sum(zs1, axis=0) / np.sqrt(K)
        S2 = np.sum(zs2, axis=0) / np.sqrt(K)
        sp = [p_upper(S1), p_upper(S2)]
        sh = holm(sp)
        out["S1"] = dict(Z=float(-S1[0]), p=sp[0], holm=sh[0])
        out["S2"] = dict(Z=float(S2[0]), p=sp[1], holm=sh[1])
    forms, a, C = report(PC)
    A = shuffles(a, rng)
    zpc = lens_lag0_ivw(indicator(A, len(forms)), C)
    out["positive_control"] = dict(label=PC, z=float(zpc[0]), p=p_upper(zpc), detected=p_upper(zpc) < ALPHA)
    json.dump(out, open(os.path.join(HERE, "isolation-4.result.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
