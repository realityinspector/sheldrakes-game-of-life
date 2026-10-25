"""Pre-registered analysis for the human-in-the-loop rig (docs/prereg/h1.md).

  python3 rig/h1/analyze.py <sid>   score one session (needs the reveal, drawer output, and the page log)
  python3 rig/h1/analyze.py series  pool every scored session

Per source s (rdseed, urandom), h_i = draws that landed on candidate i during the whole
drawer window (from "go" to its end).
  D = mean over trained i of log(h_i + 0.5) - mean over untrained i of log(h_i + 0.5)
Primary: one-sided exact p over all C(12,6) = 924 ways to pick the trained six, and Holm
across the two sources.
Secondary, no Holm claim:
  hold: for each trained puzzle, its hits while the human held its numbers, relative to the
        untrained candidates in the same seconds (null: the six hold windows assigned to a
        random ordered six of the twelve candidates, 20000 draws).
  after: D restricted to draws after the human finished.
Series: Stouffer over sessions of z = Phi^-1(1 - mid-p), mid-p = p - 1/(2*924), per source; Holm across sources.
"""
import glob, json, math, os, sys
from itertools import combinations
import numpy as np
from scipy.special import ndtri

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = ["rdseed", "urandom"]
SEED = 1_2026_1025


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - k) * ps[i]))
        adj[i] = run
    return adj


def chunks(sid, source):
    rows = [json.loads(l) for l in open(os.path.join(HERE, ".data", sid, f"{source}.jsonl")) if l.strip()]
    t0 = np.array([r["t0"] for r in rows]); t1 = np.array([r["t1"] for r in rows])
    H = np.array([r["hits"] for r in rows], dtype=float)  # (chunks, 12) in pool order
    draws = np.array([r["draws"] for r in rows], dtype=float)
    return t0, t1, H, draws


def d_stat(h, trained_mask):
    lh = np.log(h + 0.5)
    return lh[trained_mask].mean() - lh[~trained_mask].mean()


def score(sid):
    pub = json.load(open(os.path.join(HERE, "sessions", f"{sid}.json")))
    if "revealed" not in pub:
        raise SystemExit("reveal the session first")
    pool = [c["index"] for c in pub["pool"]]
    order = pub["revealed"]["order"]
    tmask = np.array([i in order for i in pool])
    log = json.load(open(os.path.join(HERE, ".data", sid, "log.json")))
    splits = [np.isin(np.arange(12), c) for c in combinations(range(12), 6)]
    rng = np.random.default_rng(SEED)
    out = {"sid": sid, "trained": order, "sources": {}}
    for s in SOURCES:
        t0, t1, H, draws = chunks(sid, s)
        h = H.sum(axis=0)
        D = d_stat(h, tmask)
        null = np.array([d_stat(h, m) for m in splits])
        p = float((null >= D - 1e-15).mean())
        se = math.sqrt((1 / (h[tmask] + 0.5)).sum() / 36 + (1 / (h[~tmask] + 0.5)).sum() / 36)
        res = {"draws": float(draws.sum()), "seconds": float(t1[-1] - t0[0]), "hits_per_candidate_mean": float(h.mean()),
               "D": float(D), "lift_pct": 100 * math.expm1(D), "p": p, "se_pct": 100 * se,
               "mde80_pct": 100 * (1.6449 + 0.8416) * se}
        # hold windows
        events = [e for e in log.get("events", []) if e.get("holdStart") and e.get("holdEnd")]
        if events:
            def hold_stat(labels):
                vals = []
                for e, lab in zip(events, labels):
                    w = np.clip(np.minimum(t1, e["holdEnd"] / 1000) - np.maximum(t0, e["holdStart"] / 1000), 0, None) / (t1 - t0)
                    if w.sum() == 0:
                        continue
                    hk = (H[:, lab] * w).sum()
                    others = [j for j in range(12) if j not in labels]
                    base = (H[:, others] * w[:, None]).sum(axis=0).mean()
                    vals.append(math.log((hk + 0.5) / (base + 0.5)))
                return float(np.mean(vals)) if vals else float("nan")
            obs_labels = [pool.index(e["index"]) for e in events]
            obs = hold_stat(obs_labels)
            nul = [hold_stat(list(rng.choice(12, size=len(events), replace=False))) for _ in range(20000)]
            res["hold"] = {"windows": len(events), "stat": obs, "lift_pct": 100 * math.expm1(obs),
                           "p": float((1 + sum(v >= obs - 1e-15 for v in nul)) / (1 + len(nul)))}
        done = log.get("completedAt")
        if done:
            after = t0 >= done / 1000
            if after.any():
                ha = H[after].sum(axis=0)
                Da = d_stat(ha, tmask)
                pa = float((np.array([d_stat(ha, m) for m in splits]) >= Da - 1e-15).mean())
                res["after"] = {"seconds": float((t1[after] - t0[after]).sum()), "D": float(Da), "lift_pct": 100 * math.expm1(Da), "p": pa}
        out["sources"][s] = res
    adj = holm([out["sources"][s]["p"] for s in SOURCES])
    for s, a in zip(SOURCES, adj):
        out["sources"][s]["holm"] = a
    out["detected"] = any(a < 0.05 for a in adj)
    json.dump(out, open(os.path.join(HERE, "results", f"{sid}.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


def series():
    rows = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(HERE, "results", "h1-*.json")))]
    out = {"sessions": [r["sid"] for r in rows], "sources": {}}
    ps = []
    for s in SOURCES:
        z = [float(ndtri(1 - min(1 - 1e-9, max(1e-9, r["sources"][s]["p"] - 0.5 / 924)))) for r in rows]
        Z = sum(z) / math.sqrt(len(z))
        p = float(0.5 * math.erfc(Z / math.sqrt(2)))
        out["sources"][s] = {"z": z, "Z": Z, "p": p}
        ps.append(p)
    for s, a in zip(SOURCES, holm(ps)):
        out["sources"][s]["holm"] = a
    json.dump(out, open(os.path.join(HERE, "results", "series.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    series() if sys.argv[1] == "series" else score(sys.argv[1])
