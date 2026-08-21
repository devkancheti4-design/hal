"""StreamGate — feed it a model's output as it arrives; it cuts on the first
illegal transition, mid-generation, before the rest is paid for.
"""
from .kernel import violation
from .grammar import Grammar, TYPES, T, scan


class Drifted(Exception):
    """Raised the moment the generation state leaves the legal space."""
    def __init__(self, at, frm, to, depth, allowed):
        self.at, self.frm, self.to, self.depth = at, frm, to, depth
        self.allowed = [TYPES[i] for i in range(8) if allowed >> i & 1]
        super().__init__(
            "token %d: %s at depth %d cannot follow %s -- grammar allows %s"
            % (at, to, depth, frm, ",".join(self.allowed) or "nothing"))


class StreamGate:
    """Consume a generation stream, reject the instant it leaves the grammar.

        g = StreamGate(grammar)
        for chunk in client.stream(...):
            g.feed(chunk)          # raises Drifted on the first bad transition
    """

    def __init__(self, grammar, on_reject=None):
        self.g = grammar
        self.on_reject = on_reject
        self.reset()

    def reset(self):
        self._buf = ""
        self._done = 0
        self.n = 0
        self.rejected = None

    def feed(self, chunk, final=False):
        """Feed a chunk of raw text. Raises Drifted on the first illegal move.

        A streamed chunk can split a token: `{"nam` scans as one thing and
        `{"name":` as another. So the LAST token of the buffer is never treated
        as settled until more text arrives (or final=True), and transitions are
        validated only between tokens that can no longer change.
        """
        self._buf += chunk
        toks = list(scan(self._buf))
        settled = len(toks) if final else max(0, len(toks) - 1)
        for i in range(max(1, self._done), settled):
            self._check(i, toks)
        self._done = max(self._done, settled)
        self.n = settled
        return self

    def close(self):
        """No more text. Validate the final transition too."""
        return self.feed("", final=True)

    def _check(self, i, toks):
        pt, pd = toks[i-1]
        t, d = toks[i]
        allowed = self.g.allowed(pt, pd)
        if violation(1 << T[t], allowed):              # THE AUTHORED KERNEL
            self.rejected = Drifted(i, pt, t, d, allowed)
            if self.on_reject: self.on_reject(self.rejected)
            raise self.rejected

    def ok(self):
        return self.rejected is None
