"""driftguard live.

    driftguard              an autonomous loop that starts degrading
    driftguard --clean      the control: the same loop, never degrading
    driftguard --proof      the structural kernel over its complete domain

Both arms use REAL text and identical thresholds. On-task documents are prose
docstrings from the standard library; the drift arm gradually substitutes
source code -- a genuine distribution shift, not injected noise.
"""
import argparse, inspect, random, statistics, sys, time
from . import AgentWatch, violation, VIOLATION

TASK = ("Explain in prose what this library component does, what its arguments "
        "mean, and when a caller should reach for it rather than an alternative.")


def _corpora():
    """(on_task, off_task) -- real text, no dependencies."""
    import collections, itertools, functools, json, re, os, textwrap, string, difflib
    mods = (collections, itertools, functools, json, re, os, textwrap, string, difflib)
    on, off = [], []
    for m in mods:
        for n in dir(m):
            o = getattr(m, n, None)
            d = inspect.getdoc(o) if o is not None else None
            if d and len(d) > 200: on.append(d[:700])            # prose
            try:
                s = inspect.getsource(o)
                if len(s) > 200: off.append(s[:700])             # source code
            except Exception:
                pass
    return on, off


def loop(drift_at=None, total=700, seed=11):
    on, off = _corpora()
    if len(on) < 40 or len(off) < 20:
        print("not enough sample text on this interpreter"); return
    rnd = random.Random(seed)
    w = AgentWatch(task=TASK, baseline_n=150, window=40, sigma=3.0, persist=25)
    tty = sys.stdout.isatty()
    print("driftguard — autonomous loop, %d on-task / %d off-task real documents\n"
          % (len(on), len(off)))
    rels, divs = [], []
    for i in range(total):
        if drift_at is None or i < drift_at:
            out = on[i % len(on)]
        else:
            p = min(1.0, (i - drift_at) / 120.0)
            out = off[i % len(off)] if rnd.random() < p else on[i % len(on)]
        w.observe(out)
        rels.append(w.last["relevance"]); divs.append(w.last["self_divergence"])
        if i % 5 == 0 or i == total - 1:
            line = w.render()
            if tty: sys.stdout.write("\r\x1b[2K" + line); sys.stdout.flush()
            elif i % 100 == 0 or i == total - 1: print(line)
        if tty: time.sleep(0.003)
    if tty: print()
    print(w.report())
    if drift_at is not None and w.drift_started_at:
        print("\n  true onset #%d, called at #%d -- latency %d calls"
              % (drift_at, w.drift_started_at, w.drift_started_at - drift_at))
    print("""
  NOTE. This demo ships with no dependencies, so its two distributions are
  stdlib docstrings vs stdlib source -- which are CLOSER to each other than a
  real task and a real derailment. Separation here is ~1.6x and latency is
  correspondingly long. The README's 27-call figure was measured on film
  reviews vs source (2.6x separation). Treat this as a working demo of the
  mechanism, not as the benchmark.""")
    n = len(rels)
    print("\n  %-24s %-12s %s" % ("phase", "relevance", "self-divergence"))
    for lo, hi, lab in ((0, 150, "baseline"), (150, n//2, "mid-run"),
                        (n//2, 3*n//4, "later"), (3*n//4, n, "final quarter")):
        if hi > lo:
            print("  %-24s %-12.4f %.4f"
                  % (lab, statistics.mean(rels[lo:hi]), statistics.mean(divs[lo:hi])))


def proof():
    bad = sum(1 for a in range(256) for b in range(256)
              if violation(a, b) != (a & ~b & 0xFF))
    print("STRUCTURAL KERNEL  %s\n" % VIOLATION)
    print("  complete domain: 256 emitted x 256 allowed = 65,536 states")
    print("  wrong: %d\n" % bad)
    print("  %s" % ("TOTAL PROOF -- not a sample" if bad == 0 else "FAILED"))
    print("\n  (included in the package; not the product -- see README)")
    return 0 if bad == 0 else 1


def main():
    ap = argparse.ArgumentParser(prog="driftguard")
    ap.add_argument("--clean", action="store_true", help="the control")
    ap.add_argument("--proof", action="store_true")
    ap.add_argument("--calls", type=int, default=700)
    a = ap.parse_args()
    if a.proof: raise SystemExit(proof())
    loop(drift_at=None if a.clean else 300, total=a.calls)


if __name__ == "__main__":
    main()
