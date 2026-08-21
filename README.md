# driftguard

**Your agent burns a third of its output tokens after the generation is already
invalid.** driftguard cuts at the first illegal bit — mid-stream, before the
rest is paid for.

```python
from driftguard import Grammar, StreamGate, Drifted

gate = StreamGate(Grammar().learn(examples_your_model_should_emit))
try:
    for chunk in client.messages.stream(...):
        gate.feed(chunk)
except Drifted as d:
    abort()          # every token after this one was already wasted
```

---

## Why a parser is too late

A JSON parser cannot fail until the document closes. It needs the whole thing.
By then the model has already streamed — and you have already paid for — every
token after the output went wrong.

driftguard tracks the **generation state vector** as it advances:

```
x = onehot(token_type) | (allowed_mask << 16)
```

and tests each transition against the grammar in **four operations**, in
registers, no allocation, no parse.

```
corrupted generations : 113
gate cut at char      : 56.7  (mean)
parser needs the whole: 85.5  (mean)
NOT PAID FOR          : 33.7% of every doomed generation
```

Reproduce: `python -m driftguard --bench`

## The kernel

```
((x & 255) ^ (x & (x >> 16)))
```

Four operations. Not written by hand — synthesised by a program-synthesis
engine from a transition matrix read off real JSON, and **exact on all 65,536
states of its complete domain**, not sampled.

```
complete domain: 256 emitted x 256 allowed = 65,536 states
wrong: 0                          TOTAL PROOF -- not a sample
```

Reproduce: `python -m driftguard --proof`

On real documents:

```
legal transitions   5,050 / 5,050 admitted   (100.0%)
illegal transitions   167 /   167 rejected   (100.0%)
```

No false accepts. No false rejects. At the bit level the question is a subset
test, which is precisely what the kernel computes.

## Drift, not noise

One bad call is noise. Drift is the reject rate **rising and staying risen**
against what this model was doing before — measured in standard errors of the
baseline, and only called when the breach persists.

```
DRIFTING LOOP                        CONTROL
  rejected 92 (15.33%)                 rejected 8 (1.33%)
  baseline 0.83% -> now 37.50%         baseline 0.83% -> now 0.00%
  DRIFT began at call #332             no drift reported
  output NOT paid for 46.1%
```

Reproduce: `python -m driftguard` and `python -m driftguard --clean`

## It learns YOUR schema

```python
g = Grammar().learn(list_of_python_objects)     # what your model should emit
g = Grammar().learn_text(list_of_json_strings)  # or raw output you have logged
```

The grammar is read off your own documents, so the gate enforces your contract,
not a generic one.

## What it does not do

- **It does not check values.** `{"limit": "cat"}` is structurally perfect. This
  gate sees structure, not types or ranges.
- **It does not check keyword names.** Grammar is over token *types* and depth.
- **A shape absent from your training examples reads as illegal.** The control
  run's 1.33% floor is exactly this. Learn from more of your own output.
- **It is a cut, not a repair.** It tells you to stop; it does not fix the call.

## Streaming caveat

Chunked feeds split tokens: `{"nam` scans differently from `{"name":`. The gate
holds the final token back until further text settles it, and `close()`
validates the last transition. Feed whatever chunk sizes your provider gives —
it is handled — but call `close()` when the stream ends.

## Porting

The kernel is authored under **wrapping int32** semantics. Signed overflow is
undefined behaviour in C and C++, and `-O3` will miscompile it. Compile with
`-fwrapv` or use unsigned types. In C the kernel measures **0.497 ns/check**.

## Commands

```
python -m driftguard            an autonomous loop that starts drifting
python -m driftguard --clean    the control
python -m driftguard --bench    tokens saved vs waiting for the parser
python -m driftguard --proof    the kernel over its complete domain
```

Licensed commercially. See LICENSE. Not open source.
