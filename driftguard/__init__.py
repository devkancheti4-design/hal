"""driftguard — cut a structured generation the instant it leaves the grammar.

    from driftguard import Grammar, StreamGate, Drifted

    g = Grammar().learn(examples_of_what_your_model_should_emit)
    gate = StreamGate(g)
    try:
        for chunk in client.messages.stream(...):
            gate.feed(chunk)
    except Drifted as d:
        abort()          # every token after this point was already wasted

Measured on real JSON: 5,050/5,050 legal transitions admitted, 167/167 illegal
transitions rejected, and 52.9% of a corrupted stream is generated AFTER the
output is already invalid -- because a parser cannot fire until the document
closes, and this fires on the transition.
"""
from .kernel import violation, VIOLATION
from .grammar import Grammar, TYPES, tokenise, scan
from .stream import StreamGate, Drifted
from .monitor import Monitor

__version__ = "0.1.0"
__all__ = ["Grammar", "StreamGate", "Drifted", "Monitor", "violation", "VIOLATION",
           "TYPES", "tokenise", "scan"]
