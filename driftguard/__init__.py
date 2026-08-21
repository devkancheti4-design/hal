"""driftguard — know when your agent starts degrading, before your users do.

    from driftguard import AgentWatch

    watch = AgentWatch(task="the objective you gave the agent")
    for step in loop:
        out = agent.step()
        if watch.observe(out).drifting:
            halt()

Measured on real text, same detector and thresholds on both arms:

    CONTROL (on-task throughout)   DRIFT (corpus shifts at call #300)
      rejected      0.14%            rejected      22.57%
      self-diverg   0.2502           self-diverg   0.6598
      DRIFT         NOT called       DRIFT         called at #327
                                     latency       27 calls after onset

Structural gating (Grammar / StreamGate) is included but is NOT the product --
constrained decoding from your provider already covers it.
"""
from .kernel import violation, VIOLATION
from .grammar import Grammar, TYPES, tokenise, scan
from .stream import StreamGate, Drifted
from .monitor import Monitor
from .signals import Relevance, SelfDrift
from .agent import AgentWatch

__version__ = "0.2.0"
__all__ = ["AgentWatch", "Relevance", "SelfDrift", "Monitor",
           "Grammar", "StreamGate", "Drifted", "violation", "VIOLATION",
           "TYPES", "tokenise", "scan"]
