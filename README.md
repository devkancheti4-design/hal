# driftguard

**Know when your agent starts degrading — at call #327, not after your users
complain.**

```python
from driftguard import AgentWatch

watch = AgentWatch(task="the objective you gave the agent")
for step in loop:
    out = agent.step()
    if watch.observe(out).drifting:
        halt()          # it is degrading, not just wrong once
```

---

## The problem

An autonomous agent does not fail loudly. It goes gradually off-task — losing
the thread, repeating itself, answering a question nobody asked — and keeps
billing you for every step. Nothing in your stack watches for that. Your
provider validates JSON; it does not tell you the agent stopped doing the job.

## Measured on real text

Same detector, same thresholds, both arms. On-task documents are real reviews;
the drift arm shifts corpus at call #300.

```
CONTROL — on-task throughout        DRIFT — shifts at call #300
  rejected      1  (0.14%)            rejected    158  (22.57%)
  self-divergence  0.2502             self-divergence  0.6598
  DRIFT         NOT called            DRIFT       called at #327
                                      latency     27 calls after onset
```

**Zero false alarms on a healthy agent.** Detection 27 calls after real onset.

## Two signals, both against the agent's own history

```
relevance     is the output still about the task it was given?
self-drift    has the output distribution moved away from what THIS agent
              produced while it was working?
```

Neither needs an external notion of "correct". Nothing is assumed except that
the agent used to be self-consistent and on-topic — which is the only thing you
can actually check without a human in the loop.

## Drift is not one bad step

One bad output is noise. Drift is the rate **rising and staying risen** against
this agent's own baseline, measured in standard errors and only called when the
breach persists.

An earlier one-window detector fired on the healthy control. It is now required
to hold for 25 consecutive windows, and the control above reports nothing.

## Honest limits

- **Self-divergence has a noise floor.** A 40-document window naturally diverges
  from a 150-document baseline: the control sits at 0.2502 with no drift at all.
  The signal (0.6598) is 2.6x that floor, but the floor is real and any
  threshold must sit above it.
- **Relevance is bag-of-words by default.** No model, no API call, no embedding
  — deliberately, so it costs nothing per step. Swap in embeddings if your task
  needs semantic rather than lexical overlap; the statistics downstream are
  identical.
- **27-call latency is not instant.** That lag is what buys zero false alarms.
  A detector that fires in one call fires on healthy agents too — measured.
- **It tells you to stop. It does not fix the agent.**

## Structural gating is included, and is not the product

`Grammar`, `StreamGate` and the 4-operation kernel ship in the package and are
exact on their complete domain. They are not what you are buying: constrained
decoding from your provider already covers JSON structure. They are there for
grammars your provider does not enforce.

```
python -m driftguard --proof     the kernel over all 65,536 states, 0 wrong
```

## Commands

```
python -m driftguard            an autonomous loop that starts drifting
python -m driftguard --clean    the control
python -m driftguard --bench    tokens saved by cutting early
python -m driftguard --proof    the structural kernel's total proof
```

Licensed commercially. See LICENSE. Not open source.
