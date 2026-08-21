"""The transition matrix. Learned from real documents, never hand-written.

A grammar is a map (current_token_type, depth) -> mask of legal next types.
`learn()` reads it off whatever your model is actually supposed to emit, so the
gate enforces YOUR schema, not a generic one.
"""
TYPES = ("LBRACE", "RBRACE", "LBRACK", "RBRACK", "KEY", "COLON", "COMMA", "VALUE")
T = {t: i for i, t in enumerate(TYPES)}
_PUNCT = {"{": "LBRACE", "}": "RBRACE", "[": "LBRACK", "]": "RBRACK",
          ":": "COLON", ",": "COMMA"}


def tokenise(obj, depth=0):
    """Token stream for a Python object, exactly as a generator emits it."""
    if isinstance(obj, dict):
        yield ("LBRACE", depth)
        first = True
        for k, v in obj.items():
            if not first: yield ("COMMA", depth + 1)
            first = False
            yield ("KEY", depth + 1); yield ("COLON", depth + 1)
            yield from tokenise(v, depth + 1)
        yield ("RBRACE", depth)
    elif isinstance(obj, list):
        yield ("LBRACK", depth)
        for i, v in enumerate(obj):
            if i: yield ("COMMA", depth + 1)
            yield from tokenise(v, depth + 1)
        yield ("RBRACK", depth)
    else:
        yield ("VALUE", depth)


def scan(text):
    """Tokenise raw JSON text incrementally, as a stream arrives."""
    i, n, depth = 0, len(text), 0
    while i < n:
        c = text[i]
        if c in " \t\r\n": i += 1; continue
        if c in "{[":
            yield (_PUNCT[c], depth); depth += 1; i += 1; continue
        if c in "}]":
            depth = max(0, depth - 1); yield (_PUNCT[c], depth); i += 1; continue
        if c in ":,":
            yield (_PUNCT[c], depth); i += 1; continue
        if c == '"':
            j = i + 1
            while j < n and (text[j] != '"' or text[j-1] == "\\"): j += 1
            k = j + 1
            while k < n and text[k] in " \t\r\n": k += 1
            yield ("KEY" if k < n and text[k] == ":" else "VALUE", depth)
            i = j + 1; continue
        j = i
        while j < n and text[j] not in ' \t\r\n{}[],:"': j += 1
        if j > i: yield ("VALUE", depth)
        i = max(j, i + 1)


class Grammar:
    """Legal transitions, learned from documents you supply."""

    def __init__(self):
        self.mask = {}

    def learn(self, docs):
        """docs: python objects your model is supposed to produce."""
        for d in docs:
            toks = list(tokenise(d))
            for (a, da), (b, _) in zip(toks, toks[1:]):
                k = (T[a], min(da, 15))
                self.mask[k] = self.mask.get(k, 0) | (1 << T[b])
        return self

    def learn_text(self, texts):
        """texts: raw JSON strings your model is supposed to produce."""
        for t in texts:
            toks = list(scan(t))
            for (a, da), (b, _) in zip(toks, toks[1:]):
                k = (T[a], min(da, 15))
                self.mask[k] = self.mask.get(k, 0) | (1 << T[b])
        return self

    def allowed(self, tok_type, depth):
        return self.mask.get((T[tok_type], min(depth, 15)), 0)

    def __len__(self):
        return sum(bin(v).count("1") for v in self.mask.values())
