# CLAUDE.md — agent guide for `modelfit`

## What this is
`modelfit` is a benchmark you point at **your own** tasks to decide which
model + effort combination is the cheapest one that reliably passes them. It
exists to replace the generic advice *"use a bigger model for complex tasks"*
with a measured, defensible answer.

The mental model — carry it into every change:
- **Two dials, not one.** `model` (talent/knowledge) and `effort` (deliberation)
  are independent axes. Turning up effort fixes *"didn't think it through"*;
  turning up model fixes *"didn't know"*.
- **The headline metric is cost per SOLVED task**, never cost per token.
- **Scoring is deterministic.** A run counts as solved only when a machine can
  prove it. This is the load-bearing property of the whole tool.

## The one rule that protects this tool
**Never introduce model-graded / LLM-as-judge / semantic-similarity scoring.**
Every verifier must be a deterministic, machine-checkable assertion (tests pass,
exact/structural match, required items present). The moment "did it pass" depends
on another model's opinion, the results stop being evidence and the tool is
worthless. If a task can't be checked deterministically, reshape the task until
it can — that discipline *is* the product, not a limitation of it.

## Architecture (where things live)
Data flows: `tasks` → `runner` (sweeps model × effort × trials) → `verifiers`
(deterministic pass/fail) → `score` (aggregate) → `report` (artifact).

| File | Responsibility |
|---|---|
| `modelfit/tasks.py` | Task definitions, quadrant tags, ground-truth fixtures. **The file you edit to make it yours.** |
| `modelfit/verifiers.py` | Deterministic checks. `verify_json_equals`, `verify_finding_set`, `verify_python_callable`. |
| `modelfit/providers.py` | The two dials: `MODELS` (tiers), `EFFORT_BUDGETS`, `PRICING`, `call_real` (Anthropic), `call_mock` (deterministic). |
| `modelfit/runner.py` | Sweeps the grid, repeats each cell `--trials` times, caches results additively. |
| `modelfit/score.py` | `by_config`, `pareto`, `per_quadrant` — cost-per-solved and the per-task-type winner. |
| `modelfit/report.py` | Writes `report.md`, `results.csv`, `pareto.png`. |
| `modelfit/cli.py` | `python -m modelfit.cli run`. |

## Commands
```bash
python -m modelfit.cli run --mock                 # deterministic offline demo, no key
python -m modelfit.cli run --real --models ...     # real Anthropic calls (needs ANTHROPIC_API_KEY)
python -m modelfit.cli run --mock --trials 20      # more repeats = tighter reliability estimate
```
Outputs land in `reports/`. There is no test suite yet; if you add one, prefer
`pytest`, and test the verifiers hardest (they are the trust anchor).

## Non-negotiable invariants
Each rule is followed by the failure it prevents.

1. **Verifiers stay deterministic and offline.** No LLM judge, no fuzzy scoring,
   no network call inside a verifier. → keeps results reproducible and defensible.
2. **The mock stays deterministic.** Pass/fail comes only from `_stable_unit`
   (hash-thresholded). No unseeded `random`. Same inputs → identical report. →
   the demo must be stable enough to show people.
3. **The cache is additive.** Key includes the trial index; never rewrite or
   delete existing cells. Adding a model/effort/trial computes only new cells. →
   reruns stay cheap and nothing is silently destroyed.
4. **The two dials stay separate.** `model` and `effort` are distinct axes
   everywhere — do not collapse them into a single "level". → collapsing them
   reintroduces the exact confusion the tool exists to remove.
5. **Cost per SOLVED task is the primary metric.** Do not "simplify" the report
   to token price or per-call cost. → a cheap model that fails is not cheap.
6. **Pricing is placeholder.** Keep the warning comment in `providers.PRICING`;
   never present computed dollar figures as authoritative. → prices change; the
   method is the durable part, the numbers are not.
7. **Quadrant discipline.** Every task is tagged `NEITHER | EFFORT | MODEL | BOTH`.
   The per-quadrant recommendation depends on it. → an untagged task breaks the
   central teaching table.
8. **Keep the sandbox boundary.** `verify_python_callable` runs generated code in
   a subprocess with a timeout. Do not switch to in-process `exec`/`eval` and do
   not remove the timeout. → generated code is untrusted.

## Adding a task (the most common change)
1. Pick the quadrant honestly (what would this task's failure blame — thinking or
   knowledge? both? neither?).
2. Write a self-contained `prompt`.
3. Choose a verifier and supply a `fixture` that makes the pass condition
   machine-checkable and singular. Reuse an existing verifier where possible; add
   a new one to `verifiers.REGISTRY` only if genuinely needed, and keep it
   deterministic.
4. Append the `Task` to `ALL_TASKS`.

A task without a deterministic check does not get merged. If you can't express
"correct" as an assertion, that's a signal the task is underspecified — fix that
first.

## Conventions
- Python 3.12, standard library first. Dataclasses + type hints throughout.
- No web frameworks, no ORM, no config framework. Keep it a small, readable tool.
- `matplotlib` is optional and import-guarded (chart is a nicety, not a
  dependency). `anthropic` is imported lazily and only used under `--real`.
- Docstrings should teach the thesis, not just describe the function — the code
  is part of the argument.

## Don't
- Don't add an LLM judge or semantic-similarity scorer anywhere.
- Don't add a task without a deterministic verifier.
- Don't hardcode "current" model prices as fact.
- Don't make the mock non-deterministic.
- Don't merge `model` and `effort` into one dial.
- Don't add heavy dependencies to shave a few lines.
- Don't rewrite the cache destructively.

## When unsure
Prefer the additive change. Keep every output defensible to a sceptic who says
"just use the biggest model at high effort" — the report should be able to answer
that with numbers, for these tasks.
