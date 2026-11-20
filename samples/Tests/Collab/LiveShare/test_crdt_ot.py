"""Unit fuzz: OT transform properties, Jupiter link, SharedText CRDT convergence (3 replicas, Arabic/emoji)."""
import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..")))
from radide.collab import ot  # noqa: E402
from radide.collab.textdoc import SharedText  # noqa: E402

ALPHA = "abc xyz مرحبا بالعالم é😀\n"


def rand_ops(rng, text, k=None):
    ops = []
    for _ in range(k or rng.randint(1, 3)):
        if text and rng.random() < 0.45:
            p = rng.randrange(len(text))
            n = rng.randint(1, min(5, len(text) - p))
            ops.append(("d", p, n))
        else:
            p = rng.randint(0, len(text))
            s = "".join(rng.choice(ALPHA) for _ in range(rng.randint(1, 4)))
            ops.append(("i", p, s))
        text = ot.apply(text, ops[-1:])
    return ops


def test_tp1(rng, n=3000):
    for _ in range(n):
        s = "".join(rng.choice(ALPHA) for _ in range(rng.randint(0, 20)))
        A, B = rand_ops(rng, s), rand_ops(rng, s)
        a2, b2 = ot.xform(A, B, True)
        assert ot.apply(ot.apply(s, A), b2) == ot.apply(ot.apply(s, B), a2), (s, A, B)


def test_jupiter(rng, rounds=400):
    for _ in range(rounds):
        base = "hello مرحبا"
        S, C = ot.Jupiter(True), ot.Jupiter(False)
        ts, tc = base, base
        to_c, to_s = [], []
        for _step in range(rng.randint(5, 40)):
            r = rng.random()
            if r < 0.3:
                ops = rand_ops(rng, ts); ts = ot.apply(ts, ops); to_c.append(S.generate(ops))
            elif r < 0.6:
                ops = rand_ops(rng, tc); tc = ot.apply(tc, ops); to_s.append(C.generate(ops))
            elif r < 0.8 and to_c:
                tc = ot.apply(tc, C.receive(to_c.pop(0)))
            elif to_s:
                ts = ot.apply(ts, S.receive(to_s.pop(0)))
        while to_c or to_s:
            if to_c:
                tc = ot.apply(tc, C.receive(to_c.pop(0)))
            if to_s:
                ts = ot.apply(ts, S.receive(to_s.pop(0)))
        assert ts == tc, (ts, tc)


def test_crdt(rng, rounds=200):
    for _ in range(rounds):
        a = SharedText.new("بداية النص start 😀\n")
        b, c = SharedText.from_state(a.state()), SharedText.from_state(a.state())
        reps = [a, b, c]
        queues = {i: [] for i in range(3)}
        for _step in range(rng.randint(5, 30)):
            i = rng.randrange(3)
            r = reps[i]
            if rng.random() < 0.6:
                ops = rand_ops(rng, r.value())
                expect = ot.apply(r.value(), ops)
                upd = r.local(ops)
                assert r.value() == expect == str(r.text)
                for j in range(3):
                    if j != i and upd:
                        queues[j].append(upd)
            elif queues[i]:
                k = rng.randrange(len(queues[i]))            # out of order delivery
                before = r.value()
                ops = r.remote(queues[i].pop(k))
                assert ot.apply(before, ops) == r.value() == str(r.text)
        for i in range(3):
            while queues[i]:
                before = reps[i].value()
                ops = reps[i].remote(queues[i].pop())
                assert ot.apply(before, ops) == reps[i].value()
        for _pass in range(2):                       # Yjs sync step 1/2 (what the session does periodically)
            for x in reps:
                for y in reps:
                    if x is not y:
                        before = y.value()
                        ops = y.remote(x.missing_for(y.state_vector()))
                        assert ot.apply(before, ops) == y.value()
        assert a.value() == b.value() == c.value(), [x.value() for x in reps]


if __name__ == "__main__":
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
    test_tp1(rng); print("TP1 ok")
    test_jupiter(rng); print("Jupiter ok")
    test_crdt(rng); print("CRDT ok")
