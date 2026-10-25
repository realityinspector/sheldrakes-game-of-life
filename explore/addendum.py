"""Exploratory follow-ups to the isolation-4 series. These were written after the series was
pre-registered and are not part of its decision. They exist because a reviewer pointed out
that Q = Σz² grows with any steady lift, not only with spread between sessions.

1. Spread around the mean, Σ(z − z̄)², for the rig's T1 and for the beehive/loaf
   per-form z's, scored against the joint shuffle null.
2. Per-form pooled z over the six fresh sessions (a steady lift in one form).
3. A descriptive inverse-variance pool of the T1 effect over every isolation session
   (isolation-1 to 3 at 1000 soups, isolation-4-1 to 6 at 20000).
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import confirm  # noqa: E402

FORMS = ["block", "blinker", "beehive", "loaf", "boat"]


def main():
    rng = np.random.default_rng(99)
    zt, zf = [], []
    for label in confirm.ISO:
        forms, a, C = confirm.report(label)
        A = confirm.shuffles(a, rng)
        I = confirm.indicator(A, len(forms))
        zt.append(confirm.lens_t1(A, I, C))
        zf.append(np.stack([confirm.lens_form(I, C, forms.index(f)) for f in FORMS]))
    zt, zf = np.array(zt), np.array(zf)  # (K,P+1), (K,F,P+1)
    K = len(confirm.ISO)
    spread = ((zt - zt.mean(axis=0)) ** 2).sum(axis=0)
    bl = zf[:, 2:4]
    spread_bl = ((bl - bl.mean(axis=0)) ** 2).sum(axis=(0, 1))
    per_form = zf.sum(axis=0) / np.sqrt(K)  # (F,P+1)
    out = {
        "t1_z": zt[:, 0].round(3).tolist(),
        "t1_spread": dict(value=float(spread[0]), df=K - 1, p=confirm.p_upper(spread)),
        "beehive_loaf_spread": dict(value=float(spread_bl[0]), p=confirm.p_upper(spread_bl)),
        "per_form_pooled_z": {f: dict(Z=float(per_form[i, 0]), p_two_sided=float(min(1, 2 * min(confirm.p_upper(per_form[i]), confirm.p_upper(-per_form[i]))))) for i, f in enumerate(FORMS)},
        "per_form_z_by_session": {f: zf[:, i, 0].round(2).tolist() for i, f in enumerate(FORMS)},
    }
    # Descriptive pool of the T1 effect (log scale) over all isolation sessions, weights from
    # each report's bootstrap CI width.
    est, se, labels = [], [], []
    for label in ["isolation-1", "isolation-2", "isolation-3"] + confirm.ISO:
        r = json.load(open(os.path.join(confirm.ROOT, "rig", "reports", f"{label}.json")))["report"]["t1"]
        lo, hi = np.log1p(r["ci"][0]), np.log1p(r["ci"][1])
        est.append(r["stat"]); se.append((hi - lo) / (2 * 1.96)); labels.append(label)
    est, se = np.array(est), np.array(se)
    w = 1 / se ** 2
    m = (w * est).sum() / w.sum()
    sm = np.sqrt(1 / w.sum())
    Qh = float((w * (est - m) ** 2).sum())
    out["pooled_t1_all_isolation"] = dict(sessions=labels, effect_pct=100 * float(np.expm1(m)), ci_pct=[100 * float(np.expm1(m - 1.96 * sm)), 100 * float(np.expm1(m + 1.96 * sm))],
                                          heterogeneity_Q=Qh, df=len(est) - 1)
    json.dump(out, open(os.path.join(HERE, "results", "isolation-4.addendum.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
