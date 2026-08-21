"""Live drift monitor — a terminal graph of a model's structural reject rate.

DRIFT is not "the model made a mistake". One bad call is noise. Drift is the
reject rate RISING and STAYING risen relative to what this model was doing
before -- the signal that generation quality has degraded.

Detection: a rolling window against an established baseline, flagged only when
the deviation exceeds a threshold expressed in standard errors of the baseline
rate, so a quiet model and a busy one are held to the same statistical bar.
"""
import collections, math, os, shutil, sys, time

_BLOCKS = " ▁▂▃▄▅▆▇█"
_RESET, _DIM, _BOLD = "\x1b[0m", "\x1b[2m", "\x1b[1m"
_GREEN, _YELLOW, _RED, _CYAN = "\x1b[32m", "\x1b[33m", "\x1b[31m", "\x1b[36m"


def _colour():
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


class Monitor:
    """Records verdicts, draws a sparkline, and calls drift when it is real.

    baseline_n   how many calls establish "normal" before drift can be called
    window       rolling window the current rate is measured over
    sigma        how many standard errors above baseline counts as drift
    """

    def __init__(self, baseline_n=200, window=50, sigma=3.0, buckets=60, persist=40):
        self.baseline_n, self.window, self.sigma = baseline_n, window, sigma
        self.persist = persist          # consecutive breaches before drift is called
        self._breach = 0
        self.recent = collections.deque(maxlen=window)
        self.history = collections.deque(maxlen=buckets)
        self.n = self.rejects = self.unverifiable = 0
        self.baseline_rate = None
        self._base_rej = 0
        self.reasons = collections.Counter()
        self.drifting = False
        self.drift_started_at = None
        self.t0 = time.time()

    def record(self, ok, name="?", reason=None):
        self.n += 1
        if ok is None:
            self.unverifiable += 1
            self.recent.append(0)
        else:
            self.recent.append(0 if ok else 1)
            if not ok:
                self.rejects += 1
                if reason: self.reasons[reason.split(":")[0]] += 1
        if self.n <= self.baseline_n:
            if ok is False: self._base_rej += 1
            if self.n == self.baseline_n:
                self.baseline_rate = self._base_rej / self.baseline_n
        self.history.append(self.rate)
        self._check_drift()

    @property
    def rate(self):
        return sum(self.recent) / len(self.recent) if self.recent else 0.0

    def _check_drift(self):
        if self.baseline_rate is None or len(self.recent) < self.window:
            return
        p = max(self.baseline_rate, 1.0 / self.baseline_n)   # never divide by zero
        se = math.sqrt(p * (1 - p) / self.window)
        over = (self.rate - self.baseline_rate) > self.sigma * se
        # DRIFT IS SUSTAINED, NOT MOMENTARY. One unlucky window is noise: at a
        # 2% baseline over 50 calls, 5 rejects trips the sigma test by chance,
        # which is exactly the false positive the clean control produced.
        # Require the breach to hold for `persist` consecutive checks.
        self._breach = self._breach + 1 if over else 0
        was = self.drifting
        self.drifting = self._breach >= self.persist
        if self.drifting and not was:
            self.drift_started_at = self.n - self.persist

    def sparkline(self, width=None):
        if not self.history: return ""
        w = width or min(len(self.history), shutil.get_terminal_size((80, 24)).columns - 34)
        h = list(self.history)[-w:]
        top = max(max(h), 0.05)
        return "".join(_BLOCKS[min(8, int(v / top * 8))] for v in h)

    def render(self):
        c = _colour()
        g, y, r, d, b, cy, z = (_GREEN, _YELLOW, _RED, _DIM, _BOLD, _CYAN, _RESET) if c else ("",)*7
        rate = self.rate
        if self.baseline_rate is None:
            state, col = "calibrating", cy
        elif self.drifting:
            state, col = "DRIFTING", r
        elif self._breach:
            state, col = "elevated", y
        else:
            state, col = "steady", g
        base = "--" if self.baseline_rate is None else "%4.1f%%" % (100*self.baseline_rate)
        line = ("%s%s%s %s%-11s%s  now %s%5.1f%%%s  base %s  n=%-6d %s" %
                (d, "reject", z, col + b, state, z, col, 100*rate, z, base, self.n,
                 col + self.sparkline() + z))
        return line

    def report(self):
        out = ["", "%s%sdrift report%s" % (_BOLD if _colour() else "", "", _RESET if _colour() else "")]
        out.append("  calls checked      %d" % self.n)
        out.append("  rejected           %d (%.2f%%)" % (self.rejects, 100.0*self.rejects/max(1,self.n)))
        out.append("  unverifiable       %d" % self.unverifiable)
        if self.baseline_rate is not None:
            out.append("  baseline rate      %.2f%% (first %d calls)" % (100*self.baseline_rate, self.baseline_n))
            out.append("  current rate       %.2f%% (last %d)" % (100*self.rate, len(self.recent)))
        if self.drift_started_at:
            out.append("  DRIFT began at call #%d" % self.drift_started_at)
        if self.reasons:
            out.append("  causes:")
            for k, v in self.reasons.most_common():
                out.append("    %-12s %d" % (k, v))
        return "\n".join(out)
