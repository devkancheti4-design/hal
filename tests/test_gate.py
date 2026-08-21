import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from driftguard import Grammar, StreamGate, Drifted, violation

DOCS = [{"name": "search", "arguments": {"q": "x", "limit": 5}},
        {"name": "read", "arguments": {"path": "a", "opts": {"deep": True}}},
        {"name": "list", "arguments": {"tags": ["a", "b"]}}]

def test_kernel_total():
    assert all(violation(a, b) == (a & ~b & 0xFF)
               for a in range(256) for b in range(256))

def test_legal_passes():
    g = Grammar().learn(DOCS)
    for d in DOCS:
        gate = StreamGate(g)
        s = json.dumps(d)
        for i in range(0, len(s), 3): gate.feed(s[i:i+3])
        gate.close()
        assert gate.ok()

def test_illegal_cut_midstream():
    """Corrupt OUTSIDE a string. A comma inside "search" just makes "sear,ch",
    which is still a valid VALUE token -- that corrupts the text, not the
    grammar, and the gate is right to pass it."""
    g = Grammar().learn(DOCS)
    s = json.dumps(DOCS[0])
    i = s.index(": ") + 2                      # right after a colon
    bad = s[:i] + "," + s[i:]
    gate = StreamGate(g); fed = 0
    try:
        for i in range(0, len(bad), 3): gate.feed(bad[i:i+3]); fed = i + 3
        gate.close(); assert False, "should have cut"
    except Drifted:
        assert fed < len(bad), "cut must happen before the stream ends"

def test_chunk_size_invariant():
    g = Grammar().learn(DOCS)
    s = json.dumps(DOCS[1])
    for cs in (1, 2, 3, 5, 8, 13, 100):
        gate = StreamGate(g)
        for i in range(0, len(s), cs): gate.feed(s[i:i+cs])
        gate.close()
        assert gate.ok(), "chunk size %d wrongly cut a legal stream" % cs

if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_"): f(); print("  PASS %s" % n)
    print("\nall tests pass")
