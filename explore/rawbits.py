"""Count exact copies of each named form's cell pattern in the soups' initial bits.

This is the most direct lens on the antenna: if training biases the entropy itself toward
the trained form, its pattern should be over-represented in the raw bytes, before Conway
runs. Counted on the torus, every D4 orientation, exact match inside the bounding box
(surroundings ignored). Two versions: the tester's raw bytes (before the beacon) and the
soup actually run (raw XOR beacon keystream; identical for rig/1, which had no beacon).
"""
import glob, hashlib, json, os, sys
import numpy as np

ROWS = {
    "block": ["##", "##"], "blinker": ["###"], "beehive": [".##.", "#..#", ".##."],
    "loaf": [".##.", "#..#", ".#.#", "..#."], "boat": ["##.", "#.#", ".#."],
    "ship": ["##.", "#.#", ".##"], "tub": [".#.", "#.#", ".#."], "pond": [".##.", "#..#", "#..#", ".##."],
}
NAMED = list(ROWS)


def orients(rows):
    a = np.array([[c == "#" for c in r] for r in rows], dtype=np.uint8)
    seen, out = set(), []
    for k in range(4):
        for m in (np.rot90(a, k), np.fliplr(np.rot90(a, k))):
            key = (m.shape, m.tobytes())
            if key not in seen:
                seen.add(key)
                out.append(m)
    return out


PATS = {n: orients(r) for n, r in ROWS.items()}


def soups_from(raw, n, size):
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8), bitorder="little")
    return bits.reshape(n, size, size)


def mix(raw, beacon, n, per):
    out = bytearray(len(raw))
    for i in range(n):
        base = i * per
        for blk in range(per // 32):
            ks = hashlib.sha256(f"{beacon}:{i}:{blk}".encode()).digest()
            o = base + blk * 32
            out[o:o + 32] = bytes(x ^ y for x, y in zip(raw[o:o + 32], ks))
    return bytes(out)


def count(soups):
    sh = {}
    for y in range(4):
        for x in range(4):
            v = np.roll(np.roll(soups, -y, axis=1), -x, axis=2).astype(bool)
            sh[(y, x)] = (v, ~v)
    res = []
    for n in NAMED:
        tot = 0
        for m in PATS[n]:
            h, w = m.shape
            hit = None
            for y in range(h):
                for x in range(w):
                    t = sh[(y, x)][0 if m[y, x] else 1]
                    hit = t.copy() if hit is None else (hit & t)
            tot += int(hit.sum())
        res.append(tot)
    return res


def main(sessdir, out):
    sess = json.load(open(glob.glob(os.path.join(sessdir, "registrar", "session-*.json"))[0]))
    spec = sess["protocol"]["tester"]
    n, size = spec["soups"], spec["size"]
    per = size * size // 8
    raw_c, mix_c = [], []
    for b, blk in enumerate(sess["blocks"]):
        raw = open(os.path.join(sessdir, "tester", f"block-{b}.bin"), "rb").read()
        rc = count(soups_from(raw, n, size))
        beacon = (blk.get("commit") or {}).get("beacon")
        mc = count(soups_from(mix(raw, beacon, n, per), n, size)) if beacon else rc
        raw_c.append(rc)
        mix_c.append(mc)
    np.savez(out, raw=np.array(raw_c), mixed=np.array(mix_c), named=np.array(NAMED))
    print(out, "done")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
