# CONCEPTS.md — the "why" behind modelfit, with examples

This project was built fast. This document exists so you *own the design*, not just
the code — every concept below carries a real, worked example (most captured from
the tool itself). Read it once and you can extend, defend, and teach the whole
thing.

---

## 1. The one idea: two dials, not one

Picking a model is not a single "smarter ↔ dumber" slider. It's **two independent
dials plus a constraint**:

- **Model** (Haiku → Sonnet → Opus) = knowledge and judgement.
- **Effort** (how long it thinks before answering) = deliberation.
- **Speed / cost** = the constraint you optimise inside.

The one diagnostic that makes this usable: **the shape of the failure tells you
which dial to turn.**
- Wrong because it *missed a constraint or contradicted itself* → turn up **effort**
  (cheap).
- Wrong because it *used the wrong API or made a shallow call* → turn up the
  **model** (costs more).

Everyone else collapses this into "hard task → big model", which is why they
overpay. Un-collapsing it is the entire point of the project.

### Example — same kind of ask, opposite dials

```
$ modelfit advise "fix this retry so it never sleeps after the last attempt"
  scores : effort 5, model 0  → EFFORT
  why    : "never" (+2, a condition to carry), "after" (+2, steps depend on order)
  verdict: Turn up EFFORT, not the model — the cost is holding conditions in mind.

$ modelfit advise "review this IAM policy and explain the security risks"
  scores : effort 1, model 2  → MODEL
  why    : "review","security","risks" (+2, a call you can't derive from the prompt)
  verdict: Turn up the MODEL, not effort — more thinking time does not supply knowledge.
```

Both start with a verb and a noun. The *difficulty* lives in different places, and
the tool names which.

---

## 2. The shape of the whole thing: 2 halves, 4 commands, 3 modes

It feels bigger than it is. There are **two halves**, exposed as **four commands**,
and one command has **three execution modes**.

**The two halves answer different questions:**
- `advise` **predicts** — guesses a task's shape *before* you run anything, to coach
  you. Fast, free, fallible.
- `run` **measures** — actually executes tasks and *proves* which model is
  cheapest-that-works. Slow, costs tokens, ground truth.

That predict-vs-measure split is the spine.

| Command | Half | What it does |
|---|---|---|
| `advise` | predict | Reads a task's wording, names its shape, recommends model+effort, explains why, states confidence. |
| `lessons` | predict | Reflects your own history back at you — what your tasks tend to be. |
| `eval` | predict | Turns the advisor on itself and reports its own accuracy. |
| `run` | measure | Runs tasks across the model×effort grid, scores deterministically, reports cost-per-solved. |

**`run` has three execution modes:**
- `--mock` (default) — a deterministic *simulation*. No API, no tokens, free. Proves
  the tool *works*; the numbers are illustrative, **not** evidence about models.
- `--real` — genuine Anthropic API calls. Real tokens, real money, real evidence.
- `--via-cli` — shells out to the `claude`/`codex` CLI so no API key is stored;
  real output, rougher cost/effort accounting.

The trap to avoid: treating `--mock` numbers as truth. Mock proves the machinery;
only `--real` / `--via-cli` say anything about the models.

---

## 3. `advise` — walked through, one example per quadrant

You type a task. Five regexes read the *wording* (negation, sequencing,
judgement-words, breadth, requirement-count). Each fires or not and bumps two
integer scores — **effort-need** and **model-need**. The scores bucket the task
into one of four **quadrants**, each with a fixed recommendation.

The load-bearing design decision: **it never calls an LLM to decide.** That looks
like a limitation; it's the core. Using a model to rate difficulty means paying for
and waiting on a model call just to decide whether to make a model call — and you
get a non-reproducible answer that can't explain itself. Staying deterministic
makes it instant, free, reproducible, and — the whole point — able to **show its
reasoning**, which a black box can't. You can only *teach* with a glass box.

### NEITHER — boilerplate

```
$ modelfit advise "add a docstring to this function"
  scores : effort 1, model 0 → NEITHER
  start  : haiku-4-5 at effort off
  verdict: Nothing to turn up — start cheapest, escalate only if it actually fails.
```
Lesson: recall/boilerplate. A cheap model at no extra effort is correct; paying
more buys nothing.

### EFFORT — reasoning to work out

```
$ modelfit advise "fix this retry so it never sleeps after the last attempt"
  scores : effort 5, model 0 → EFFORT
  start  : sonnet-5 at effort low  →  escalate to sonnet @ high effort
```
Lesson: the hard part is holding conditions straight. A mid model with more
thinking beats a big model answering off the cuff.

### MODEL — needs knowledge

```
$ modelfit advise "review this IAM policy and explain the security risks"
  scores : effort 1, model 2 → MODEL
  start  : sonnet-5 at effort high  →  escalate to opus @ low effort
```
Lesson: the hard part is knowing what's correct. A stronger model earns its price;
grinding effort won't conjure knowledge.

### BOTH (shown here as a live hedge) — long, multi-step, self-directed

```
$ modelfit advise "refactor the entire tagging module across the codebase and update all call sites"
  scores : effort 2, model 1 → EFFORT (confidence: medium)
  start  : sonnet-5 at effort low
  second option: could also be BOTH (opus-4-8 at effort high)
    how to tell: if it fails on both counts at once — conditions dropped *and*
    wrong choices made — treat it as BOTH: big model, high effort, read the diff.
```
Note this is a genuinely imperfect call: milder wording ("update all call sites"
rather than "never… then…") kept the effort score low, so it lands EFFORT and
*hedges* to BOTH rather than committing. That's the tool being honest about a
borderline case, not confidently wrong.

---

## 4. Confidence, hedging, and the blind spot

The scores don't just pick a quadrant — they set a **confidence**, and that governs
how the tool speaks:
- **high** — signals agree and there are enough of them → commit to one pick.
- **medium** — signals lean but not cleanly → show the top *two* options side by side.
- **low** — little or nothing fired → treat it as a guess, and if *nothing* fired,
  warn about the blind spot.

The blind spot is the honest heart of the tool. "No signal fired" does **not** mean
"easy" — it means *the words can't see it*, which could be genuinely trivial or
hard-in-a-way-the-wording-hides.

### Example — two identical-looking outputs, for opposite reasons

```
$ modelfit advise "add a docstring to this function"          # genuinely trivial
$ modelfit advise "implement RS256 JWT signature verification" # secretly a security minefield
```
Both score effort 1, model 0, and both print **low confidence + blind-spot warning**:
> Nothing in the wording signals difficulty, which is exactly where this tool is
> weakest. Plain phrasing hides hard knowledge: crypto, SQL tuning, timezones/DST,
> concurrency. If that's the subject matter, override this and start higher.

The tool cannot tell these two apart — and *says so* instead of bluffing. A tool
that knows the shape of its own ignorance is more trustworthy than one that always
answers.

---

## 5. `run` — where guessing becomes knowing

`run` executes each task across a grid of model×effort, scores every result with a
**deterministic verifier** (tests pass / exact match / required findings present),
and reports **cost-per-solved-task** plus a Pareto frontier.

Three design decisions carry this half.

**(a) The verifier is the trust anchor.** "Correct" must be something a machine can
prove, or the whole measurement is vibes in a lab coat. Example verifier for a code
task:
```python
fixture = {"callable": "backoff_delays",
           "tests": ["assert backoff_delays(4) == [1, 2, 4]",
                     "assert backoff_delays(1) == []"]}
```
The generated code runs in a subprocess; pass = exit 0. No model judges quality.

**(b) Cost-per-SOLVED, never cost-per-token.** A cheap model that fails isn't cheap
— you pay for the failed attempt *and* the retry. Worked example over 10 tasks:

| Strategy | Spend | Solved | Cost per solved |
|---|---|---|---|
| Haiku only ($0.001/try) | $0.010 | 6/10 | **$0.0017** (if 60% is acceptable) |
| Opus only ($0.02/try) | $0.20 | 10/10 | **$0.02** |
| Cascade: Haiku first, escalate the 4 failures to Opus | $0.010 + 4×$0.02 = **$0.09** | 10/10 | **$0.009** |

The cascade solves everything at half the all-Opus cost. *That* arithmetic is why
"cheap-first, verify, escalate" wins, and why the headline metric is per-solved.

**(c) Repeat each cell (`--trials`), because one run is a coin flip.** Reliability
only shows up over repetition. A model that's 50% reliable and one that's 90%
reliable look identical on a single run; over 8 trials they're 4/8 vs 7/8 —
visibly different. (This is exactly why METR measures capability at a *success
rate*, not a yes/no.)

---

## 6. `lessons` and `eval` — the self-aware loop

These make it a *learning* tool, not a calculator.

**`lessons`** reads your local history and reflects your pattern back. Real output:
```
=== Lessons from your own advice history ===
  - Shapes you have asked about (8 total): NEITHER 4, EFFORT 2, MODEL 2.
  - Most of your asks look routine — your default config should be the cheap one.
  - 4/8 verdicts were low confidence — the wording carried no signal. Double-check those by hand.
  - Calibration: 3/3 recorded outcomes passed at the advised start config.
  - Standing lesson: the advisor reads wording, not meaning. When it says low confidence, believe it.
```

**`eval`** turns the tool on itself and publishes its own accuracy. Real output:
```
=== Advisor self-eval (deterministic, exact quadrant match) ===
  overall     : 0.60  (12/20)
  clear       : 1.00  (10/10)  — does the mechanism work?
  adversarial : 0.20  (2/10)  — how far wording is from meaning
--- misses (kept on purpose; this is the error bar) ---
  [adversarial] said NEITHER, truth MODEL: Optimise this SQL query.
      Index and query-plan knowledge, four plain words. No signal fires.
```
Read those two numbers correctly: **clear 1.00** means the *mechanism* works — when
the words carry the signal, it classifies perfectly. **adversarial 0.20** measures
*how far wording is from meaning* — the ceiling of any word-based approach. A tool
that hands you its own error bar is doing something almost nothing in this space
does.

---

## 7. The newcomer journey — and what compounds

**Day one:** they type `advise "some task"` and get a verdict *with reasoning*. The
benefit isn't the pick — it's the *why*.

**After ten tasks:** they've absorbed the two-dial habit without a lecture — they
start noticing "this is a constraint problem, that's effort not model." The tool
installs judgement by demonstration.

**What compounds:**
- `lessons` calibrates to *their* work, so advice gets personal.
- `eval` lets them tune the tool safely: change a rule → rerun eval → keep it only
  if accuracy holds. (The tool's own discipline, applied to the tool.)
- `run`, once they've measured real tasks, turns every future "which model?" from
  an argument into a lookup.

**The beautiful part:** the tool's success condition is making itself unnecessary.
The better it teaches, the less you need it — until you run the diagnostic in your
head and only reach for the tool to onboard the next person or settle a dispute
with measured numbers. A good coach works themselves out of a job.

---

## 8. What it honestly solves (and what it doesn't)

Be precise, because credibility depends on it.

It does **not** "pick models better than everyone." For pure measurement,
**promptfoo / DeepEval** are more mature; for routing, **trained classifiers**
(RouteLLM, commercial routers) beat a regex on accuracy. On their home turf, this
loses.

What it *does* solve, and what's genuinely uncrowded:
- It makes model-selection reasoning **legible and teachable** — output aimed at a
  human's understanding, not a silent route.
- It replaces "Opus *feels* smarter" with either an **inspectable rationale** or a
  **measured number**.
- It's **honest about its own limits** (confidence + blind spot + a published error
  bar), which the commercial routers never surface because hiding the decision is
  their product.

Position it as a **transparent coach / teaching artifact**, not "use this instead of
promptfoo." On the first framing it's distinctive; on the second it's redundant.

---

## 9. Five transferable principles (the part that outlives this project)

Each applies far beyond model selection.

1. **Keep the non-deterministic thing out of the decision.** Use the LLM only where
   nothing deterministic can do the job; let deterministic code own the verdict.
   *Example:* the advisor classifies with regexes and never calls a model — same
   input, same answer, always explainable. (Same pattern as OpsLens: deterministic
   detection, LLM confined to explanation.)

2. **"Correct" must be machine-checkable or your measurement is fiction.**
   *Example:* the verifier runs generated code against `assert`s in a subprocess —
   pass = exit 0. If the only judge were a gut feeling, `run` would prove nothing.

3. **Guaranteeing by checking beats guessing.** A cascade (try cheap → verify →
   escalate) *checks* instead of betting, so it can't silently misroute.
   *Example:* the $0.009/solved cascade in §5 beats both fixed strategies precisely
   because it verifies each step rather than predicting.

4. **A system that says "I don't know" is more trustworthy than one that always
   answers.** *Example:* the JWT task gets low confidence + a blind-spot warning
   rather than a false "easy" — which is why you can trust its *high*-confidence
   calls.

5. **Capability is a vector, not a scalar.** Stop thinking "smarter/dumber", start
   thinking "better at *this*, worse at *that*", and both the hype and the decision
   paralysis dissolve. *Example:* the same "review vs fix" pair in §1 needs opposite
   dials — one number could never capture that.

That last principle is the entire project, compressed.