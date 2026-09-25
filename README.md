<div align="center">

# modelfit

**Stop guessing which model to use. Measure it.**

[![CI](https://github.com/dapinder-dhillon/modelfit/actions/workflows/ci.yml/badge.svg)](https://github.com/dapinder-dhillon/modelfit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

</div>

---

Most model-selection advice is one sentence: *"use a bigger model for complex
tasks, otherwise a cheaper one."* It's useless because it never says how you'd
*know*, and because it treats model choice as a single dial. It isn't.

<img src="media/demo.gif" alt="modelfit advise, default then --short then --explain, then modelfit eval" width="80%" />

**Who this is for:** anyone who picks an AI model, whether in a desktop app, a
CLI, or code. `advise` only needs a terminal: run it on your task, then set the
model (and effort, if your app has that setting) wherever you actually ask.
Every app lets you choose the model, but not all expose a thinking or effort
setting; where yours doesn't, act on the model half. `run`, which measures
models on your own tasks, needs API or CLI access.

## See the two dials in practice

A payment bug involving two workers calls for domain expertise:

```
$ modelfit advise "Fix an intermittent bug where two workers process the same payment webhook at once and charge the customer twice. Keep retries safe."

START       Anthropic  claude-sonnet-5 / high effort
            OpenAI     gpt-6-sol / high effort
IF NEEDED   switch to claude-opus-5-5 (Anthropic) or gpt-6-astra (OpenAI), same high effort
SIGNAL      high (clear read of your wording)

WHY         your wording has "at once" → needs real domain expertise, not just more thinking
```

Storing passwords reads like routine CRUD — the wording gives no hint that
hashing and salting are the actual problem, so the tool says so instead of
guessing:

```
$ modelfit advise "Store user passwords in the users table."

START       Anthropic  claude-haiku-4-5 / no extra thinking
            OpenAI     gpt-6-luna / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with claude-sonnet-5 (Anthropic) or gpt-6-sol
                (OpenAI) at high effort yourself instead of the suggestion
                above.
```

A codebase-wide refactor is broad enough that the tool won't commit to a single
answer — it shows the runner-up instead of guessing which one is right:

```
$ modelfit advise "Refactor the entire tagging module across the codebase and update all call sites."

START       Anthropic  claude-sonnet-5 / low effort
            OpenAI     gpt-6-sol / low effort
IF NEEDED   raise effort to high before switching model
SIGNAL      medium (could be read another way)

WHY         your wording has "refactor" and "entire" → spans a lot of ground, self-directed

SECOND OPINION  could be BOTH instead. If it drops conditions and makes wrong choices, treat it
                as BOTH: use a bigger model, high effort, and review the result
                yourself.
```

Only interested in one vendor? `--vendor anthropic` or `--vendor openai` shows
just that one:

```
$ modelfit advise "Review this IAM policy and explain the security risks." --vendor openai

START       gpt-6-sol / high effort
IF NEEDED   switch to gpt-6-astra, same high effort
SIGNAL      high (clear read of your wording)

WHY         your wording has "review" and "security" → needs judgement the prompt doesn't
            provide
```

`advise` runs locally and makes no model call. It reads the wording of a task,
so its suggestion is a starting point, not a measured chance of success.
`SIGNAL` describes how clearly the wording matched its rules. The verdict itself
is a model *tier* (small, mid or large) plus an effort level — nothing in a
task's wording says which vendor you use — and each vendor's model for that tier
is shown alongside. Tiers line up only roughly across vendors; `run` is how you
find out which one is actually cheaper for your tasks.

To find out what works for your project, replace the bundled examples with
representative tasks and verifiers. `run --mock` demonstrates the report with
synthetic results; `run --real` and `run --via-cli` make model calls to measure
your tasks.

## Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
3. [Usage](#usage)
4. [Updating](#updating)
5. [Uninstall](#uninstall)
6. [How it works](#how-it-works)
7. [Developing](#developing)
8. [License](#license)

## Requirements

- Python 3.12+
- [pipx](https://pipx.pypa.io/) (recommended) or `pip`
- For `--real`: an `ANTHROPIC_API_KEY`
- For `--via-cli`: the `claude` and/or `codex` CLI, already installed and logged in
- For charts (`run`'s Pareto PNG, `advise`'s projection PNG): the `chart` extra (`matplotlib`)

## Installation

```bash
pipx install git+https://github.com/dapinder-dhillon/modelfit.git
```

That puts `modelfit` on your `PATH` — enough for `run --mock`, `run --via-cli`,
and `advise`. For the `--real` API mode or the Pareto/projection charts, install
with the extras instead:

```bash
pip install "modelfit[all] @ git+https://github.com/dapinder-dhillon/modelfit.git"
```

Extras are scoped if you only need one: `modelfit[real]` (Anthropic SDK only)
or `modelfit[chart]` (matplotlib only).

Contributing, or want `--via-cli`'s source alongside it? Clone the repo and use
[Poetry](https://python-poetry.org/) instead:

```bash
git clone https://github.com/dapinder-dhillon/modelfit.git
cd modelfit
poetry install --with dev --extras all
```

## Usage

modelfit has two halves, exposed as four commands. The halves answer different
questions:

- **`advise` predicts.** It guesses a task's shape before you run anything, to
  coach you. Fast, free, fallible.
- **`run` measures.** It actually runs your tasks and proves which model and
  effort is cheapest-that-works. Slower, costs tokens, ground truth.

| Command | Half | What it does |
|---|---|---|
| `advise` | predict | Reads a task's wording, names its shape, recommends a model tier and effort (with the Claude and OpenAI model for it), explains why, and says how clearly the wording matched. |
| `lessons` | predict | Reflects your own advice history back at you: what your tasks tend to be. |
| `eval` | predict | Turns the advisor on itself and reports its own accuracy. |
| `run` | measure | Runs tasks across the model × effort grid, checks every answer deterministically, and reports cost per solved task. |

```bash
modelfit advise "<task text>"                    # default: leads with the action
modelfit advise "<task text>" --short             # one line, for the 50th call today
modelfit advise "<task text>" --explain           # signal-by-signal breakdown, raw scores
modelfit advise "<task text>" --vendor openai     # one vendor's models only (default: both)
modelfit advise "<task text>" --outcome pass --used-effort low   # record what happened
modelfit advise "<task text>" --out FILE --chart FILE            # write paths (default: reports/advice_*)
```

It also writes `reports/advice_<slug>.md` and a projection chart, and appends
the call to `~/.modelfit/history.json` (local file, nothing leaves your
machine) — that bookkeeping line prints to stderr, so
`modelfit advise "..." > out.txt` captures only the recommendation.

```bash
modelfit lessons     # your shape distribution + calibration from YOUR recorded outcomes
modelfit eval        # the advisor grades itself: overall / clear / adversarial accuracy
```

### `run` — measure it for real

It has three execution modes:

- **`--mock`** (default): a deterministic simulation. No API, no tokens, free.
  It proves the tool works; the numbers are illustrative, **not** evidence
  about models.
- **`--real`**: real Anthropic API calls. Real tokens, real money, real evidence.
- **`--via-cli`**: runs through a `claude` or `codex` CLI you're already logged
  into, so modelfit never stores an API key. Effort and cost show as `n/a`
  wherever the CLI can't control or report them, never faked.

The trap to avoid: treating `--mock` numbers as truth. Mock proves the
machinery; only `--real` and `--via-cli` say anything about the models.

```bash
modelfit run --mock                                          # free, deterministic, no key
modelfit run --real --models claude-haiku-4-5 claude-sonnet-5 # needs ANTHROPIC_API_KEY
modelfit run --via-cli claude --models claude-haiku-4-5       # shells out to a logged-in CLI
modelfit run --via-cli codex --models gpt-5.1 --efforts off low
```

- **Effort isn't always controllable.** `claude -p --effort` has no off/none
  level, so requesting `off` there can't be pinned — the report shows that run's
  effort as `n/a`, never a number implying control that wasn't there. `codex`'s
  `model_reasoning_effort` does have a `none` level, so `off` **is** controlled
  there.
- **Cost isn't always knowable.** When the CLI reports a cost or token usage,
  it's used (falling back to the same placeholder `PRICING` table the other
  modes use if only token counts came back). When it reports neither,
  `cost_usd` is `None` and the report shows `$/solved` as `n/a` rather than
  inventing a number.
- **It's directional, not precise.** The CLI may inject its own system prompt,
  tools, or context you don't control, so "same task in" is less tightly
  controlled than the SDK path — the report says so once, up top.

All tool use is disabled for the call itself (`--tools ""` for claude,
`--sandbox read-only --ask-for-approval never` for codex) — a benchmark run is
one completion, not an agentic turn that should be touching your filesystem.

Effort maps to Anthropic's `thinking` budget (`off`/`low`/`high`). The same
idea is `reasoning_effort` on OpenAI — swap the adapter in `providers.py`.

## Updating

There's no version pin to bump — it's installed straight from git, so a fresh
install picks up whatever is on `main`. The reliable way to force that refresh:

```bash
pipx install --force git+https://github.com/dapinder-dhillon/modelfit.git
```

(`pip install --upgrade --force-reinstall "modelfit[all] @ git+https://..."`
if you installed with `pip` instead.) Plain `pipx upgrade modelfit` may also
pick up new commits, since there's no version number to compare against — but
`--force` is the one that's guaranteed to.

## Uninstall

```bash
pipx uninstall modelfit
```

(or `pip uninstall modelfit`.) This doesn't touch anything it wrote alongside
itself — `~/.modelfit/history.json`, or any `reports/`/`cache/` directories in
projects where you ran it — those are plain files, remove them yourself if you
want them gone too.

## How it works

`modelfit advise` scans your task description for wording that suggests
constraints, ordered steps, domain expertise, breadth, or several
requirements. Fixed rules turn those signals into a suggested model tier and
effort level, shown as the matching Claude and OpenAI model. The output shows
the wording it used, so you can challenge its reasoning.

The advisor runs locally and makes no model call. It cannot understand
unstated difficulty: a short request may hide a hard SQL, security, or
timezone problem. Treat its answer as a starting point.

`modelfit run` answers a different question by testing models on tasks you
supply and checking their answers with verifiers. Mock results are synthetic
examples; real and CLI runs make model calls.

## Developing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT © [Dapinder Singh](https://github.com/dapinder-dhillon)
