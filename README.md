# modelfit

[![CI](https://github.com/dapinder-dhillon/modelfit/actions/workflows/ci.yml/badge.svg)](https://github.com/dapinder-dhillon/modelfit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

**Stop guessing which model to use. Measure it.**

Most model-selection advice is one sentence: *"use a bigger model for complex
tasks, otherwise a cheaper one."* It's useless because it never says how you'd
*know*, and because it treats model choice as a single dial. It isn't.

There are **two independent dials plus a constraint**:

| Dial | What you're buying | Fixes the failure... |
|---|---|---|
| **Model** (Haiku→Sonnet→Opus→Fable) | raw talent / knowledge / judgement | *"it didn't know"* |
| **Effort** (off→low→high thinking budget) | how long it deliberates before answering | *"it didn't think it through"* |
| **Speed / cost** | the constraint you optimise inside | — |

The trick that replaces the generic advice: **the shape of the failure tells you
which dial to turn.** Wrong because it missed a constraint or contradicted itself
→ turn up *effort* (cheap). Wrong because it used the wrong API or showed shallow
judgement → turn up the *model*.

`modelfit` proves this with data. It runs a set of tasks across the whole
**model × effort** grid, scores every run with a **deterministic** verifier
(tests pass / exact match / required findings present — no model-graded
fuzziness), and reports **cost-per-*solved*-task**, a Pareto frontier, and a
per-task-type recommendation.

## Install

Requires Python 3.12+ and [Poetry](https://python-poetry.org/).

```bash
poetry install --extras all      # anthropic (for --real) + matplotlib (for the chart)
```

## Run it (no API key needed)

```bash
poetry run modelfit run --mock
```

This produces `reports/report.md`, `reports/results.csv`, and
`reports/pareto.png`. The mock is deterministic and encodes the thesis, so the
sample report visibly shows effort winning one task type and model winning
another.

## Run it for real

```bash
poetry install --extras real
export ANTHROPIC_API_KEY=sk-...
poetry run modelfit run --real --models claude-haiku-4-5 claude-sonnet-5 claude-opus-4-8
```

Effort maps to Anthropic's `thinking` budget (`off`/`low`/`high`). The same idea
is `reasoning_effort` on OpenAI — swap the adapter in `providers.py`.

## Development

```bash
poetry install --with dev --extras all
poetry run pytest                  # test suite (verifiers get the heaviest coverage)
poetry run ruff check .            # lint
poetry run ruff format --check .   # format check
poetry run mypy modelfit           # types
```

CI (`.github/workflows/ci.yml`) runs all four on every push and PR.

## Make it yours (this is the actual point)

The bundled tasks in `tasks/` are toys chosen to span four quadrants. **Delete
them** and drop in ~20 real tasks from your backlog instead — no Python
required, each is just a YAML file:

```yaml
# tasks/my_real_task.yaml
id: my_real_task
quadrant: EFFORT              # NEITHER | EFFORT | MODEL | BOTH
prompt: |
  Whatever you'd actually ask a model to do.
verifier: verify_python_callable
fixture:
  callable: some_function
  tests:
    - "assert some_function(1) == 2"
```

Pick a verifier and give it a deterministic `fixture`:

- code tasks → a few `assert`s run in a subprocess (`verify_python_callable`)
- structured output → exact/structural compare (`verify_json_equals`)
- judgement tasks → constrain the model to a fixed vocabulary and check the
  required items appear (`verify_finding_set`)

`modelfit run` loads every `*.yaml` in `tasks/` automatically (point elsewhere
with `--tasks <dir>`). Once the tasks are yours, the recommendation is yours —
and defensible to anyone who says "just use the big one." If you need a
genuinely new *kind* of check, that's the one place Python is still required:
add a verifier to `modelfit/verifiers.py`.

## Layout

```
tasks/*.yaml     # your tasks: id, quadrant, prompt, verifier, fixture  <- edit this
modelfit/
  tasks.py       # Task dataclass + load_tasks(): reads and validates tasks/*.yaml
  verifiers.py   # deterministic pass/fail checks
  providers.py   # model tiers, effort→budget, pricing, real call + mock
  runner.py      # sweeps the grid, caches results additively
  score.py       # cost-per-solved, Pareto frontier, per-quadrant winner
  report.py      # markdown + CSV + Pareto PNG
  cli.py         # `python -m modelfit.cli run`
```

## Honest caveats

- **Pricing in `providers.py` is placeholder — confirm current numbers yourself.**
- `verify_python_callable` executes generated code in a subprocess with a
  timeout. Fine for a local experiment on models you chose; isolate properly
  (container / nsjail) for anything untrusted or CI.
- The mock's pass rates are illustrative. Only `--real` numbers are evidence.
