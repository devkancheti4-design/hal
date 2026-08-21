"""The authored kernel. Four operations, proven over its complete domain.

    VIOLATION(x) = ((x & 255) ^ (x & (x >> 16)))

x packs the ONE-HOT token type a generator just emitted in its low byte, and
the mask of types the grammar allows next in bits 16..23. The result is the
offending bits; zero means the transition is legal.

Not written by hand. Authored by a program-synthesis engine from a transition
matrix read off real JSON, and exact on all 65,536 (emitted, allowed) states.
It is `A & ~B` reached WITHOUT a NOT, because the operator set the engine was
given did not contain one.

PORTING: authored under wrapping int32 semantics. Signed overflow is undefined
behaviour in C/C++/Rust-release. Compile with -fwrapv or use unsigned types.
"""
VIOLATION = "((x & 255) ^ (x & (x >> 16)))"
_C = compile(VIOLATION, "<driftguard>", "eval")
M32 = 0xFFFFFFFF


def _s32(v):
    v &= M32
    return v - (1 << 32) if v >> 31 else v


def violation(emitted_onehot, allowed_mask):
    """Offending bits. 0 == legal transition. Four operations."""
    x = _s32((emitted_onehot & 0xFF) | ((allowed_mask & 0xFF) << 16))
    return _s32(eval(_C, {"__builtins__": {}}, {"x": x})) & 0xFF
