"""DRIFT SIGNALS. Not structure -- structure is a commodity.

Two questions a provider's constrained decoder does NOT answer:

  RELEVANCE     is the output still about the task it was given?
  SELF-DRIFT    has the output distribution moved away from what THIS agent
                was producing when it was working?

Both are measured against the agent's own history, so no external notion of
"correct" is needed, and both feed the same standard-error statistics already
built -- a deviation is only called when it persists.
"""
import collections, math, re

_W = re.compile(r"[a-z0-9_]+")

def toks(s):
    return _W.findall(s.lower())


class Relevance:
    """Cosine of output against the task statement, over token counts.

    Cheap on purpose: no model, no API call, no embedding. A real deployment
    can swap in embeddings; the statistic downstream is identical.
    """
    def __init__(self, task):
        self.q = collections.Counter(toks(task))
        self._qn = math.sqrt(sum(v*v for v in self.q.values())) or 1.0

    def score(self, out):
        d = collections.Counter(toks(out))
        if not d: return 0.0
        dot = sum(v * d.get(k, 0) for k, v in self.q.items())
        dn = math.sqrt(sum(v*v for v in d.values())) or 1.0
        return dot / (self._qn * dn)


class SelfDrift:
    """Jensen-Shannon divergence of recent output from this agent's baseline.

    The baseline is whatever the agent produced while it was working. Nothing
    external is assumed to be correct -- only that the agent used to be
    self-consistent and now is not.
    """
    def __init__(self, baseline_n=120, window=40):
        self.baseline_n, self.window = baseline_n, window
        self.base = collections.Counter()
        self.base_docs = 0
        self.recent = collections.deque(maxlen=window)

    def observe(self, out):
        t = toks(out)
        self.recent.append(collections.Counter(t))
        if self.base_docs < self.baseline_n:
            self.base.update(t); self.base_docs += 1

    @property
    def ready(self):
        return self.base_docs >= self.baseline_n and len(self.recent) >= self.window

    def divergence(self):
        if not self.ready: return 0.0
        cur = collections.Counter()
        for c in self.recent: cur.update(c)
        keys = set(self.base) | set(cur)
        bt = sum(self.base.values()) or 1
        ct = sum(cur.values()) or 1
        js = 0.0
        for k in keys:
            p = self.base.get(k, 0) / bt
            q = cur.get(k, 0) / ct
            m = (p + q) / 2
            if p: js += 0.5 * p * math.log(p / m, 2)
            if q: js += 0.5 * q * math.log(q / m, 2)
        return max(0.0, min(1.0, js))
