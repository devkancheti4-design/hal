"""driftguard live.

    python -m driftguard            an autonomous loop that starts drifting
    python -m driftguard --clean    a loop that never drifts (control)
    python -m driftguard --bench    tokens saved vs waiting for the parser
    python -m driftguard --proof    the kernel over its complete domain
"""
import argparse, json, random, statistics, sys, time
from . import Grammar, StreamGate, Drifted, Monitor, violation, VIOLATION, tokenise, TYPES


def _corpus(n=300, seed=1):
    rnd = random.Random(seed)
    names = ["query", "path", "limit", "mode", "filters", "tags", "opts", "id"]
    def val(d):
        r = rnd.random()
        if d < 3 and r < .22: return {rnd.choice(names): val(d+1) for _ in range(rnd.randint(1,3))}
        if d < 3 and r < .38: return [val(d+1) for _ in range(rnd.randint(1,3))]
        return rnd.choice([1, "s", True, None, 3.5])
    return [{"name": rnd.choice(names),
             "arguments": {rnd.choice(names): val(1) for _ in range(rnd.randint(1,4))}}
            for _ in range(n)]


def _emit(doc, corrupt_at=None):
    """The text a model streams out, optionally corrupted mid-generation."""
    s = json.dumps(doc)
    if corrupt_at is None: return s
    i = max(2, min(len(s) - 2, corrupt_at))
    return s[:i] + random.choice([",", ":", "}", "]"]) + s[i:]


def loop(drift_at=None, total=600, seed=7):
    rnd = random.Random(seed)
    docs = _corpus(400, seed)
    g = Grammar().learn(docs[:200])
    mon = Monitor(baseline_n=120, window=40, sigma=3.0, persist=30)
    tty = sys.stdout.isatty()
    print("driftguard — autonomous loop, %d legal transitions learned\n" % len(g))
    saved = []
    for i in range(total):
        doc = rnd.choice(docs[200:])
        degrading = drift_at is not None and i >= drift_at
        p_bad = 0.02 if not degrading else min(0.7, 0.02 + (i - drift_at) / 200.0)
        text = _emit(doc, rnd.randrange(5, max(6, len(json.dumps(doc)) - 3))
                     if rnd.random() < p_bad else None)
        gate = StreamGate(g)
        fed = 0
        try:
            for k in range(0, len(text), 4):
                gate.feed(text[k:k+4]); fed = min(k + 4, len(text))
            gate.close()
            mon.record(True)
        except Drifted:
            mon.record(False, reason="grammar")
            saved.append(1 - fed / len(text))
        if i % 4 == 0 or i == total - 1:
            line = mon.render()
            if tty: sys.stdout.write("\r\x1b[2K" + line); sys.stdout.flush()
            elif i % 100 == 0 or i == total - 1: print(line)
        if tty: time.sleep(0.004)
    if tty: print()
    print(mon.report())
    if saved:
        print("  stream cut early    %d times" % len(saved))
        print("  output NOT paid for %.1f%% of each cut generation (mean)"
              % (100 * statistics.mean(saved)))


def bench():
    rnd = random.Random(3)
    docs = _corpus(500, 3)
    g = Grammar().learn(docs[:250])
    gaps = []
    for doc in docs[250:]:
        s = json.dumps(doc)
        if len(s) < 24: continue
        text = _emit(doc, rnd.randrange(5, len(s) - 3))
        gate = StreamGate(g); fed = None
        try:
            for k in range(0, len(text), 2): gate.feed(text[k:k+2])
            gate.close()
            continue
        except Drifted:
            fed = min(k + 2, len(text))
        try: json.loads(text); continue
        except Exception: pass
        gaps.append((fed, len(text)))
    cut = statistics.mean(f for f, _ in gaps)
    full = statistics.mean(t for _, t in gaps)
    print("tokens saved vs waiting for the parser\n")
    print("  corrupted generations : %d" % len(gaps))
    print("  gate cut at char      : %.1f (mean)" % cut)
    print("  parser needs the whole: %.1f (mean)" % full)
    print("  NOT PAID FOR          : %.1f%% of every doomed generation"
          % (100 * (1 - cut / full)))


def proof():
    bad = sum(1 for a in range(256) for b in range(256)
              if violation(a, b) != (a & ~b & 0xFF))
    print("KERNEL  %s\n" % VIOLATION)
    print("  complete domain: 256 emitted x 256 allowed = 65,536 states")
    print("  wrong: %d" % bad)
    print("\n  %s" % ("TOTAL PROOF -- not a sample" if bad == 0 else "FAILED"))
    return 0 if bad == 0 else 1


def main():
    ap = argparse.ArgumentParser(prog="driftguard")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--bench", action="store_true")
    ap.add_argument("--proof", action="store_true")
    ap.add_argument("--calls", type=int, default=600)
    a = ap.parse_args()
    if a.proof: raise SystemExit(proof())
    if a.bench: return bench()
    loop(drift_at=None if a.clean else 260, total=a.calls)


if __name__ == "__main__":
    main()
