"""Pre-registered: the census of the tester's RAW bytes (docs/prereg/raw-census.md).

In rig/2 the soups were raw ⊕ beacon keystream. XOR with an independent uniform keystream
makes the result uniform whatever the raw bytes were, so the reported census could not show
any bias in the tester's own entropy. Here the raw bytes are run through Conway themselves
(explore/replay.ts with RAW=1) and scored with the isolation-4 lenses.

R1 (primary): Stouffer of z(lag0|log300|ivw) on raw-soup counts over isolation-4-1..6, one-sided up.
R2 (primary): Q = sum_s z(T1)^2 on raw-soup counts over isolation-4-1..6, upper tail. Holm over R1, R2.
R3 (secondary): R1's lens pooled over every rig/2 isolation session (isolation-2, -3, -4-1..6).
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import confirm  # noqa: E402

SEED = 20261025_2
PRIMARY = [f"isolation-4-{i}" for i in range(1, 7)]
ALL = ["isolation-2", "isolation-3"] + PRIMARY


def raw_counts(label):
    meta = json.load(open(os.path.join(HERE, ".out", f"raw-{label}.meta.json")))
    forms = meta["forms"]
    ids = [meta["formIds"][f] for f in forms]
    C, a = [], []
    for line in open(os.path.join(HERE, ".out", f"raw-{label}.jsonl")):
        r = json.loads(line)
        tot = dict.fromkeys(ids, 0)
        for s in r["soups"]:
            c = s[6]
            for k in range(0, len(c), 2):
                if c[k] in tot:
                    tot[c[k]] += c[k + 1]
        C.append([tot[i] for i in ids])
        a.append(forms.index(r["target"]))
    return forms, np.array(a), np.array(C, dtype=float)


def main():
    rng = np.random.default_rng(SEED)
    z1, z2, per = {}, {}, {}
    for label in ALL:
        forms, a, C = raw_counts(label)
        A = confirm.shuffles(a, rng)
        I = confirm.indicator(A, len(forms))
        z1[label] = confirm.lens_lag0_ivw(I, C)
        z2[label] = confirm.lens_t1(A, I, C)
        per[label] = dict(lag0_ivw=float(z1[label][0]), t1=float(z2[label][0]))
    R1 = np.sum([z1[l] for l in PRIMARY], axis=0) / np.sqrt(len(PRIMARY))
    R2 = np.sum([z2[l] ** 2 for l in PRIMARY], axis=0)
    R3 = np.sum([z1[l] for l in ALL], axis=0) / np.sqrt(len(ALL))
    p = [confirm.p_upper(R1), confirm.p_upper(R2)]
    h = confirm.holm(p)
    out = dict(per_session=per,
               R1=dict(Z=float(R1[0]), p=p[0], holm=h[0], supported=h[0] < 0.05),
               R2=dict(Q=float(R2[0]), df=len(PRIMARY), p=p[1], holm=h[1], supported=h[1] < 0.05),
               R3=dict(Z=float(R3[0]), p=confirm.p_upper(R3), sessions=ALL))
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, "results", "raw-census.result.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
