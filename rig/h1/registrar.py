"""Registrar for the human-in-the-loop rig (rig/h1).

  python3 rig/h1/registrar.py new            open a session: draw its pool and its sealed assignment
  python3 rig/h1/registrar.py reveal <sid>   publish the sealed assignment and check it against the commitment

A session pool is 12 puzzles. Each one is three different numbers from 1 to 15, given by their
sum and product; 439 of the 455 triples are pinned down uniquely by those two clues. No
triple is ever reused across sessions. From OS entropy the registrar draws which 6 of the 12
the human works on, and in what order. What it publishes before the session:
  rig/h1/sessions/<sid>.json  pool (all 12 candidates, unlabelled), commitment, protocol hash
What it keeps sealed until the reveal (root-only, 0600):
  rig/h1/.private/<sid>.json  trained set, order, nonce
The human's page gets only the 6 trained puzzles. The blind drawers get only the 12
candidates.
"""
import glob, hashlib, json, os, secrets, sys, time
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(HERE, "sessions")
PRIV = os.path.join(HERE, ".private")
N_POOL, N_TRAINED = 12, 6
TRIPLES = list(combinations(range(1, 16), 3))  # index i <-> TRIPLES[i], N = 455


def clue(t):
    return sum(t), t[0] * t[1] * t[2]


CLUES = {}
for i, t in enumerate(TRIPLES):
    CLUES.setdefault(clue(t), []).append(i)
UNIQUE = [i for i, t in enumerate(TRIPLES) if len(CLUES[clue(t)]) == 1]


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def protocol_hash():
    files = ["rig/h1/registrar.py", "rig/h1/drawer.c", "rig/h1/analyze.py", "docs/prereg/h1.md"]
    root = os.path.dirname(os.path.dirname(HERE))
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode() + b"\0" + open(os.path.join(root, f), "rb").read() + b"\0")
    return h.hexdigest()


def used():
    out = set()
    for f in glob.glob(os.path.join(PUB, "*.json")):
        out |= {c["index"] for c in json.load(open(f))["pool"]}
    return out


def new():
    os.makedirs(PUB, exist_ok=True)
    os.makedirs(PRIV, mode=0o700, exist_ok=True)
    free = [i for i in UNIQUE if i not in used()]
    if len(free) < N_POOL:
        raise SystemExit("no unused puzzles left")
    rnd = secrets.SystemRandom()
    pool = sorted(rnd.sample(free, N_POOL))
    trained = rnd.sample(pool, N_TRAINED)  # random subset, already in random order
    sid = "h1-" + time.strftime("%Y%m%d-%H%M%S", time.gmtime()) + "-" + secrets.token_hex(2)
    nonce = secrets.token_hex(32)
    sealed = {"sid": sid, "pool": pool, "order": trained, "nonce": nonce}
    commitment = hashlib.sha256(canonical(sealed).encode()).hexdigest()
    pub = {
        "sid": sid,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "N": len(TRIPLES),
        "pool": [{"index": i, "triple": TRIPLES[i]} for i in pool],
        "trained_count": N_TRAINED,
        "commitment": commitment,
        "protocol_sha256": protocol_hash(),
    }
    json.dump(pub, open(os.path.join(PUB, f"{sid}.json"), "w"), indent=1)
    path = os.path.join(PRIV, f"{sid}.json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(sealed, fh)
    # What the human's page receives: the trained puzzles only, in order.
    page = {
        "sid": sid,
        "status": "open",
        "holdSeconds": 60,
        "puzzles": [{"pid": f"p{k + 1}", "index": i, "sum": clue(TRIPLES[i])[0], "product": clue(TRIPLES[i])[1],
                     "answer": list(TRIPLES[i])} for k, i in enumerate(trained)],
    }
    json.dump(page, open(os.path.join(PRIV, f"{sid}.page.json"), "w"))
    os.chmod(os.path.join(PRIV, f"{sid}.page.json"), 0o600)
    print(json.dumps({"sid": sid, "commitment": commitment, "pool": pool}))


def reveal(sid):
    sealed = json.load(open(os.path.join(PRIV, f"{sid}.json")))
    pub = json.load(open(os.path.join(PUB, f"{sid}.json")))
    ok = hashlib.sha256(canonical(sealed).encode()).hexdigest() == pub["commitment"]
    if not ok:
        raise SystemExit("commitment does not match the sealed assignment")
    pub["revealed"] = {"order": sealed["order"], "nonce": sealed["nonce"]}
    json.dump(pub, open(os.path.join(PUB, f"{sid}.json"), "w"), indent=1)
    print(json.dumps({"sid": sid, "commitment_ok": ok, "trained": sealed["order"]}))


if __name__ == "__main__":
    if sys.argv[1:2] == ["new"]:
        new()
    elif sys.argv[1:2] == ["reveal"]:
        reveal(sys.argv[2])
    else:
        raise SystemExit(__doc__)
