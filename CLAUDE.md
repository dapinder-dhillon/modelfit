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
Two flows, deliberately separate.

**Measure** (the evidence): `tasks/*.yaml` → `tasks.py` (loads + validates) →
`runner` (sweeps model × effort × trials) → `verifiers` (deterministic pass/fail)
→ `score` (aggregate) → `report` (artifact).

**Advise** (the cheap first guess): task wording → `advisor.estimate` (regex
signals only) → `advice_report` + `project` (artifacts) → `history` (local log,
`lessons`). Graded by `evalset` against `eval/advisor_cases.yaml`.

| File | Responsibility |
|---|---|
| `tasks/*.yaml` | One task per file: id, quadrant tag, prompt, verifier name, fixture. **What you edit to make it yours — no Python required.** |
| `modelfit/tasks.py` | `Task` dataclass + `load_tasks(directory)`: reads and validates the YAML files above. |
| `modelfit/verifiers.py` | Deterministic checks. `verify_json_equals`, `verify_finding_set`, `verify_python_callable`. |
| `modelfit/providers.py` | The two dials: `MODELS` (tiers), `EFFORT_BUDGETS`, `PRICING`, `call_real` (Anthropic), `call_mock` (deterministic), `call_cli` (shells out to `claude`/`codex`, degrades honestly). |
| `modelfit/runner.py` | Sweeps the grid, repeats each cell `--trials` times, caches results additively. |
| `modelfit/score.py` | `by_config`, `pareto`, `per_quadrant` — cost-per-solved and the per-task-type winner. |
| `modelfit/report.py` | Writes `report.md`, `results.csv`, `pareto.png`. |
| `modelfit/advisor.py` | `estimate(text)` → quadrant, plan, reasons, confidence, runner-up. Regex signals **only**. |
| `modelfit/advice_report.py` | The written verdict for one advised task (`render` / `write`). |
| `modelfit/project.py` | Projected pass-rate vs cost chart for one task; reuses `providers._pass_probability`. Optional matplotlib. |
| `modelfit/history.py` | Appends each `advise` call to `~/.modelfit/history.json` (`MODELFIT_HOME` overrides); `lessons()`. |
| `eval/advisor_cases.yaml` | Labelled advisor cases: `task`, `truth`, `adversarial`, `note`. Data, like tasks. |
| `modelfit/evalset.py` | Loads those cases and scores the advisor (overall / clear / adversarial + misses). |
| `modelfit/cli.py` | `run`, `advise`, `lessons`, `eval`. |

## Commands
```bash
python -m modelfit.cli run --mock                  # deterministic offline demo, no key
python -m modelfit.cli run --real --models ...     # real Anthropic calls (needs ANTHROPIC_API_KEY)
python -m modelfit.cli run --via-cli claude ...    # shells out to an already-logged-in claude CLI
python -m modelfit.cli run --via-cli codex --models gpt-5.1 ...  # or codex; needs GPT model ids
python -m modelfit.cli run --mock --trials 20      # more repeats = tighter reliability estimate
python -m modelfit.cli run --mock --tasks my_tasks # point at a different tasks/ directory

python -m modelfit.cli advise "<task text>"        # which dial to turn, and why
python -m modelfit.cli advise "<task>" --outcome pass --used-effort low
python -m modelfit.cli lessons                     # shape distribution + recorded calibration
python -m modelfit.cli eval                        # grade the advisor: overall/clear/adversarial
```
Outputs land in `reports/`. Tests live in `tests/` (pytest); test the
verifiers hardest — they are the trust anchor.

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
9. **The advisor never calls an LLM.** It classifies from wording with
   deterministic regexes; same text in, same verdict out. → an advisor that asked
   a model which model to use is circular, and breaks rule 1 by another door.
10. **Every verdict prints WHY.** `estimate()` always returns non-empty `reasons`
    naming the signals that fired. → an unexplained score is not arguable, and
    arguing with it is how you find the wording it misread.
11. **Silence is not evidence of ease.** When no signal fires, keep confidence
    LOW and emit the blind-spot warning; never report "confident / easy". → the
    hardest tasks (crypto, SQL tuning, timezones, concurrency) look plainest.
12. **Hedge when unsure.** Weak or conflicting signals → lower confidence plus a
    runner-up quadrant and a `distinguish_hint`. → a heuristic that hides its
    uncertainty is worse than no heuristic.
13. **`lessons` counts only recorded outcomes.** Never infer whether a
    recommendation worked. → an inferred pass rate is exactly the soft number
    this project exists to avoid.
14. **Both eval splits stay published.** `modelfit eval` prints clear *and*
    adversarial accuracy, and lists the misses. Don't delete failing adversarial
    cases and don't blend the two into one number. → the gap is the caveat.
15. **CLI mode never fakes what it can't control.** If an agent CLI can't pin the
    requested effort level, `call_cli` reports that run's effort as `"n/a"`, not
    the requested value. → a fabricated effort number would look like evidence
    the tool controlled a dial it didn't.
16. **CLI mode never fakes what it can't measure.** If the CLI doesn't report
    token usage or a cost, `Result.cost_usd` is `None` and the report renders
    `$/solved` as `n/a` — it does not fall back to guessing. → an invented cost
    figure defeats the whole cost-per-solved metric.
17. **No API key touches CLI mode.** `call_cli` shells out to a CLI that is
    already authenticated; modelfit never reads, stores, or forwards a key for
    this path. → the entire point of this mode is auth living somewhere else.

## Adding a task (the most common change)
1. Pick the quadrant honestly (what would this task's failure blame — thinking or
   knowledge? both? neither?).
2. Write a self-contained `prompt`.
3. Choose a verifier and supply a `fixture` that makes the pass condition
   machine-checkable and singular. Reuse an existing verifier where possible; add
   a new one to `verifiers.REGISTRY` only if genuinely needed, and keep it
   deterministic.
4. Create `tasks/<id>.yaml` with `id`, `quadrant`, `prompt`, `verifier`, `fixture`
   (`max_tokens` optional). No Python required — `load_tasks` validates it.

A task without a deterministic check does not get merged. If you can't express
"correct" as an assertion, that's a signal the task is underspecified — fix that
first.

## Touching the advisor
Adding or changing a regex signal changes every past verdict, so:
1. Say in one sentence which dial the signal implies and why. If you can't, it
   isn't a signal.
2. Add labelled cases to `eval/advisor_cases.yaml` — including the ones it gets
   wrong, tagged `adversarial: true` with a `note` saying why.
3. Run `modelfit eval` before and after. **Clear** accuracy is the bar (tests
   assert ≥ 0.70). **Adversarial** accuracy is expected to be poor; if it jumps
   to match clear accuracy, suspect the eval set went soft rather than the
   advisor got smart.
4. Never tune by deleting inconvenient cases.

## Conventions
- Python 3.12, standard library first except `pyyaml` (task files) and the
  import-guarded optionals below. Dataclasses + type hints throughout.
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
- Don't let the advisor call a model, or let it claim confidence it hasn't earned.
- Don't present `advise` output as evidence — it reads words, `run` measures.
- Don't rewrite history destructively; `record` appends.
- Don't let `call_cli` pretend it pinned an effort level or knows a cost it
  doesn't — report `"n/a"`/`None`, never a guess dressed up as a number.
- Don't have modelfit read, store, or forward an API key for CLI mode — that's
  the one thing this mode exists to avoid.

## When unsure
Prefer the additive change. Keep every output defensible to a sceptic who says
"just use the biggest model at high effort" — the report should be able to answer
that with numbers, for these tasks.
