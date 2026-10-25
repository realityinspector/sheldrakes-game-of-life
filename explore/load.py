"""Turn a replay .jsonl into compact numpy arrays (cached as .npz next to it).

Per block: totals over the 1000 soups for every common shape at generations 100/200/300,
soups containing each shape, live population, and initial density. Per soup: counts of the
eight named forms at generation 300.
"""
import json, sys, os
import numpy as np

NAMED = ["block", "blinker", "beehive", "loaf", "boat", "ship", "tub", "pond"]
GENS = [100, 200, 300]
TOPK = 40


def load(path):
    cache = path.replace(".jsonl", ".npz")
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(path):
        z = np.load(cache, allow_pickle=True)
        return {k: z[k] for k in z.files} | {"meta": json.loads(str(z["meta_json"]))}
    meta = json.load(open(path.replace(".jsonl", ".meta.json")))
    fid = meta["formIds"]
    named_ids = [fid[n] for n in NAMED]
    rows = [json.loads(l) for l in open(path)]
    B = len(rows)
    nsoup = len(rows[0]["soups"])
    # first pass: shape frequencies at gen 300
    freq = {}
    for r in rows:
        for s in r["soups"]:
            c = s[6]
            for k in range(0, len(c), 2):
                freq[c[k]] = freq.get(c[k], 0) + c[k + 1]
    top = sorted(freq, key=lambda k: -freq[k])[:TOPK]
    ids = list(dict.fromkeys(named_ids + top))
    col = {k: j for j, k in enumerate(ids)}
    G = len(ids)
    tot = np.zeros((len(GENS), B, G))      # summed counts
    pres = np.zeros((len(GENS), B, G))     # soups containing >= 1
    allobj = np.zeros((len(GENS), B))      # all objects
    pop = np.zeros((len(GENS), B))
    d0 = np.zeros(B)
    per = np.zeros((B, nsoup, len(NAMED)), dtype=np.int16)
    perpop = np.zeros((B, nsoup, len(GENS)), dtype=np.int16)
    perd0 = np.zeros((B, nsoup), dtype=np.int16)
    target = []
    for b, r in enumerate(rows):
        target.append(r["target"])
        for i, s in enumerate(r["soups"]):
            d0[b] += s[0]
            perd0[b, i] = s[0]
            for gi in range(3):
                p, c = s[1 + 2 * gi], s[2 + 2 * gi]
                pop[gi, b] += p
                perpop[b, i, gi] = p
                for k in range(0, len(c), 2):
                    allobj[gi, b] += c[k + 1]
                    j = col.get(c[k])
                    if j is not None:
                        tot[gi, b, j] += c[k + 1]
                        pres[gi, b, j] += 1
                        if gi == 2 and j < len(NAMED):
                            per[b, i, j] = c[k + 1]
        rec = r["recorded"]
        for f, name in enumerate(meta["forms"]):
            assert tot[2, b, NAMED.index(name)] == rec[name], (b, name)
    out = dict(tot=tot, pres=pres, allobj=allobj, pop=pop, d0=d0, per=per, perpop=perpop, perd0=perd0,
               ids=np.array(ids), target=np.array(target), meta_json=json.dumps(meta))
    np.savez_compressed(cache, **out)
    out["meta"] = meta
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        d = load(p)
        print(p, d["tot"].shape, "ok")
