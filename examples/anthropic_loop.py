"""Guard a live Anthropic streaming tool call.

    pip install anthropic
    export ANTHROPIC_API_KEY=...
    python examples/anthropic_loop.py
"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from driftguard import Grammar, StreamGate, Drifted, Monitor

# 1. Teach it the shape your tools actually emit.
SHAPES = [
    {"name": "search", "arguments": {"query": "x", "limit": 5}},
    {"name": "read_file", "arguments": {"path": "a.py"}},
    {"name": "write_file", "arguments": {"path": "a.py", "content": "x"}},
    {"name": "run", "arguments": {"cmd": "ls", "opts": {"timeout": 30}}},
]
GRAMMAR = Grammar().learn(SHAPES)
MON = Monitor(baseline_n=100, window=40, persist=30)


def guarded_stream(client, **kw):
    """Yield chunks; raise Drifted the moment the tool call leaves the grammar."""
    gate = StreamGate(GRAMMAR)
    try:
        with client.messages.stream(**kw) as s:
            for text in s.text_stream:
                gate.feed(text)
                yield text
        gate.close()
        MON.record(True)
    except Drifted as d:
        MON.record(False, reason="grammar")
        raise                      # caller aborts; the rest is never generated


if __name__ == "__main__":
    try:
        from anthropic import Anthropic
    except ImportError:
        print("pip install anthropic"); raise SystemExit(1)
    client = Anthropic()
    try:
        for chunk in guarded_stream(
            client,
            model="claude-opus-5",
            max_tokens=512,
            messages=[{"role": "user",
                       "content": "Emit ONLY a JSON tool call: "
                                  '{"name": ..., "arguments": {...}}'}],
        ):
            print(chunk, end="", flush=True)
        print("\n\nstream accepted")
    except Drifted as d:
        print("\n\nCUT: %s" % d)
    print(MON.render())
