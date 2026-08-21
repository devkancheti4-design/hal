"""AgentWatch — the one call you add to an autonomous loop.

    watch = AgentWatch(task="the objective you gave the agent")
    for step in loop:
        out = agent.step()
        if watch.observe(out).drifting:
            halt()                       # it is degrading, not just wrong once

Two signals, both measured against the agent's OWN history:

  relevance     is the output still about the task?
  self-drift    has the output distribution moved away from what this agent
                produced while it was working?

Neither needs a notion of "correct". Nothing is assumed except that the agent
used to be self-consistent and on-topic.
"""
from .signals import Relevance, SelfDrift
from .monitor import Monitor


class AgentWatch:
    def __init__(self, task, baseline_n=150, window=40, sigma=3.0, persist=25,
                 min_relevance=0.02):
        self.rel = Relevance(task)
        self.sd = SelfDrift(baseline_n=baseline_n, window=window)
        self.mon = Monitor(baseline_n=baseline_n, window=window,
                           sigma=sigma, persist=persist)
        self.min_relevance = min_relevance
        self.last = None

    def observe(self, output):
        r = self.rel.score(output)
        self.sd.observe(output)
        self.mon.record(r >= self.min_relevance, reason="relevance")
        self.last = {"relevance": r, "self_divergence": self.sd.divergence()}
        return self

    @property
    def drifting(self):
        return self.mon.drifting

    @property
    def drift_started_at(self):
        return self.mon.drift_started_at

    def render(self):
        return self.mon.render()

    def report(self):
        s = self.mon.report()
        if self.last:
            s += "\n  relevance          %.4f" % self.last["relevance"]
            s += "\n  self-divergence    %.4f" % self.last["self_divergence"]
        return s
