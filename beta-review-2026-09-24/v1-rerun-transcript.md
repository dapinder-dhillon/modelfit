modelfit v1 rerun — captured terminal output

Commands were run from /Users/dapindersingh/SINGH-Workspace/modelfit. Output is the returned terminal stream; stdout and stderr were not separated. Exit codes are recorded. I did not open Python source files or internal design documents.

### D1 — Developer

Command:
```sh
modelfit advise 'Write a Python function that takes a list of integers and returns the even ones.'
```

Exit code: 1

Output (verbatim):
````text

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
Traceback (most recent call last):
  File "/Users/dapindersingh/.local/bin/modelfit", line 6, in <module>
    sys.exit(main())
             ~~~~^^
  File "/Users/dapindersingh/SINGH-Workspace/modelfit/modelfit/cli.py", line 408, in main
    return handler(args, ap)
  File "/Users/dapindersingh/SINGH-Workspace/modelfit/modelfit/cli.py", line 282, in _cmd_advise
    log = history.record(est, outcome=args.outcome, used_effort=args.used_effort)
  File "/Users/dapindersingh/SINGH-Workspace/modelfit/modelfit/history.py", line 81, in record
    target.write_text(json.dumps(entries, indent=2))
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/pathlib/__init__.py", line 809, in write_text
    with self.open(mode='w', encoding=encoding, errors=errors, newline=newline) as f:
         ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/homebrew/Cellar/python@3.14/3.14.5/Frameworks/Python.framework/Versions/3.14/lib/python3.14/pathlib/__init__.py", line 771, in open
    return io.open(self, mode, buffering, encoding, errors, newline)
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted: '/Users/dapindersingh/.modelfit/history.json'
````

### D1-retry — Developer

Command:
```sh
modelfit advise 'Write a Python function that takes a list of integers and returns the even ones.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_write_a_python_function_that_takes.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### D-help — Developer

Command:
```sh
modelfit advise --help
```

Exit code: 0

Output (verbatim):
````text
usage: modelfit advise [-h] [--short | --explain] [--out OUT] [--chart CHART]
                       [--outcome {pass,fail}] [--used-effort {off,low,high}]
                       text

positional arguments:
  text                  the task, in the words you'd actually use

options:
  -h, --help            show this help message and exit
  --short, --compact    one line: model/effort, escalation, confidence -- for
                        repeat use
  --explain             full signal-by-signal breakdown and raw scores -- for
                        debugging the classifier
  --out OUT             markdown path (default: reports/advice_*.md)
  --chart CHART         chart path (default: reports/advice_*.png)
  --outcome {pass,fail}
                        record what actually happened at the advised start
                        (feeds `lessons`)
  --used-effort {off,low,high}
                        the effort you actually used, recorded alongside the
                        outcome
````

### D2 — Developer

Command:
```sh
modelfit advise 'Fix an intermittent bug where two workers process the same payment webhook at once and charge the customer twice. Keep retries safe.'
```

Exit code: 0

Output (verbatim):
````text

START       sonnet-5 / high effort
IF NEEDED   switch to opus-4-8, same high effort
SIGNAL      high (clear read of your wording)

WHY         your wording has "at once" → needs real domain expertise, not just more thinking
Wrote reports/advice_fix_an_intermittent_bug_where_two.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json
````

### D3 — Developer

Command:
```sh
modelfit advise 'Review the list of service names and return it sorted alphabetically.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_review_the_list_of_service_names.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### D4 — Developer

Command:
```sh
modelfit advise 'Check that our AES-GCM helper never reuses a nonce, even when several workers restart at the same time.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_check_that_our_aes_gcm_helper.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       sonnet-5 / high effort
IF NEEDED   switch to opus-4-8, same high effort
SIGNAL      medium (could be read another way)

WHY         your wording has "never", "aes" and "nonce" → a condition must stay true; needs real
            domain expertise, not just more thinking

SECOND OPINION  could be BOTH instead. If it drops conditions and makes wrong choices, treat it
                as BOTH: use a bigger model, high effort, and review the result
                yourself.
````

### D5 — Developer

Command:
```sh
modelfit advise 'Design a migration from a synchronous REST API to an event-driven service. Compare failure modes, preserve backwards compatibility, and give me a staged rollout and rollback plan.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_design_a_migration_from_a_synchronous.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       opus-4-8 / high effort
IF NEEDED   have a human review it — don't use it unattended
SIGNAL      medium (could be read another way)

WHY         your wording has "design" and "migration" → needs judgement the prompt doesn't
            provide; spans a lot of ground, self-directed; 3 requirements to track
            at once

SECOND OPINION  could be EFFORT instead. If it contradicts itself or drops one of your
                conditions, it needs more thinking time. Raise effort before
                switching to a bigger model.
````

### D6 — Developer

Command:
```sh
modelfit advise 'Fix an intermittent bug where two workers process the same payment webhook at once and charge the customer twice. Keep retries safe.' --short
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_fix_an_intermittent_bug_where_two.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json
sonnet-5/high → escalate if needed  [high]
````

### D7 — Developer

Command:
```sh
modelfit advise 'Fix an intermittent bug where two workers process the same payment webhook at once and charge the customer twice. Keep retries safe.' --explain
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_fix_an_intermittent_bug_where_two.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

=== MODEL — knowledge / judgement — a call you can't derive from the prompt ===
  lever      : the MODEL
  signal     : high (Several signals point the same way, so confidence is high.)
  scores     : effort 1 (baseline 1 + signals), model 2

--- why (signals that fired) ---
  - names a documented blind-spot domain ("at once") → model +2 — crypto/SQL/timezone/concurrency topics need real expertise, not just more thinking

--- start here ---
  sonnet-5 at high effort
  if it fails: switch to opus-4-8, same high effort

Turn up the MODEL, not effort. This task needs more knowledge or judgement; more thinking time will not add either.
````

### B-readme — Business analyst

Command:
```sh
cat README.md
```

Exit code: 0

Output (verbatim):
````text
# modelfit

[![CI](https://github.com/dapinder-dhillon/modelfit/actions/workflows/ci.yml/badge.svg)](https://github.com/dapinder-dhillon/modelfit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

<img src="media/demo.gif" alt="modelfit advise, then modelfit run --mock" width="80%" />

**Stop guessing which model to use. Measure it.**

Most model-selection advice is one sentence: *"use a bigger model for complex
tasks, otherwise a cheaper one."* It's useless because it never says how you'd
*know*, and because it treats model choice as a single dial. It isn't.

**Who this is for:** developers calling Claude programmatically — direct
API/SDK calls, or an agent CLI (`claude`, `codex`) that exposes its own effort
flag. "Effort" here is Anthropic's `thinking` parameter (or a CLI's own
reasoning-effort flag) — a real, settable dial in code, but **not** something
Claude Desktop or claude.ai chat expose to you. If you're chatting with Claude
through either of those, there's no lever in that UI for this tool's
recommendations to turn — they're not for you (yet).

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

Requires Python 3.12+.

```bash
pipx install git+https://github.com/dapinder-dhillon/modelfit.git
```

That puts `modelfit` on your `PATH` — enough for `run --mock`, `run --via-cli`,
and `advise`. For the `--real` API mode or the Pareto/projection charts, install
with the extras instead:

```bash
pip install "modelfit[all] @ git+https://github.com/dapinder-dhillon/modelfit.git"
```

Contributing, or want `--via-cli`'s source alongside it? Clone and use
[Poetry](https://python-poetry.org/) instead — see [Development](#development).

## Run it (no API key needed)

```bash
modelfit run --mock
```

This produces `reports/report.md`, `reports/results.csv`, and
`reports/pareto.png`. The mock is deterministic and encodes the thesis, so the
sample report visibly shows effort winning one task type and model winning
another.

## Run it for real

```bash
pip install "modelfit[real] @ git+https://github.com/dapinder-dhillon/modelfit.git"
export ANTHROPIC_API_KEY=sk-...
modelfit run --real --models claude-haiku-4-5 claude-sonnet-5 claude-opus-4-8
```

Effort maps to Anthropic's `thinking` budget (`off`/`low`/`high`). The same idea
is `reasoning_effort` on OpenAI — swap the adapter in `providers.py`.

## Run it through a CLI you're already logged into

A third mode shells out to an already-authenticated agent CLI (`claude -p` or
`codex exec`) instead of the SDK, so auth lives wherever that CLI already
logged in — **no API key is read or stored by modelfit.**

```bash
modelfit run --via-cli claude --models claude-haiku-4-5 claude-sonnet-5
modelfit run --via-cli codex --models gpt-5.1 --efforts off low
```

This spends real quota, so it asks first:

```
About to make 12 real CLI calls via claude. Continue? [y/N]
```

Pass `--yes` to skip the prompt in a script. For `codex`, pass `--models` with
GPT ids — the `--models` default is Anthropic's own table, which only makes
sense for `claude`.

**This mode degrades honestly instead of faking precision:**

- **Effort isn't always controllable.** `claude -p --effort` has no off/none
  level, so requesting `off` there can't be pinned — the report shows that run's
  effort as `n/a`, never a number implying control that wasn't there. `codex`'s
  `model_reasoning_effort` does have a `none` level, so `off` **is** controlled
  there.
- **Cost isn't always knowable.** When the CLI reports a cost or token usage, it's
  used (falling back to the same placeholder `PRICING` table the other modes use
  if only token counts came back). When it reports neither, `cost_usd` is `None`
  and the report shows `$/solved` as `n/a` rather than inventing a number.
- **It's directional, not precise.** The CLI may inject its own system prompt,
  tools, or context you don't control, so "same task in" is less tightly
  controlled than the SDK path — the report says so once, up top.

All tool use is disabled for the call itself (`--tools ""` for claude,
`--sandbox read-only --ask-for-approval never` for codex) — a benchmark run is
one completion, not an agentic turn that should be touching your filesystem.

## Before you spend anything: `advise`

Measuring is the answer, but it isn't the *first* question. The first question is
"I have this one task in front of me — where do I start?" That's what `advise`
is for: it reads the **wording** of a task and says which dial to reach for.

```bash
modelfit advise "Fix this retry helper so it never sleeps after the final attempt."
```

```
START       sonnet-5 / low effort
IF NEEDED   raise effort to high before switching model
CONFIDENCE  high

WHY         "never", "after" → a condition to hold; order matters
```

Leads with the action, not the classifier's internals — but the WHY line and
any hedge/blind-spot warning are never hidden behind a flag; those are the
honesty guarantees, not decoration. Two other views:

```bash
modelfit advise "<task>" --short     # one line, for the 50th call today
modelfit advise "<task>" --explain   # signal-by-signal breakdown, raw scores
```

It also writes `reports/advice_<slug>.md` and a projection chart, and appends the
call to `~/.modelfit/history.json` (local file, nothing leaves your machine) —
that bookkeeping line prints to stderr, so `modelfit advise "..." > out.txt`
captures only the recommendation. Record what actually happened and it feeds back:

```bash
modelfit advise "<task>" --outcome pass --used-effort low
modelfit lessons     # your shape distribution + calibration from YOUR outcomes
```

### What `advise` is, honestly

- **It reads words, not meaning.** "Optimise this SQL query" is six plain words
  hiding real knowledge. It will call that NEITHER, and be wrong.
- **No LLM is involved in the decision.** Deterministic regexes only — same text
  in, same verdict out. An advisor that asked a model which model to use would be
  circular, and would break the same rule the verifiers live by.
- **It states its confidence and hedges.** Conflicting signals lower confidence
  and print the runner-up quadrant plus how to tell the two apart from the
  *failure* shape.
- **Silence is not evidence of ease.** When nothing fires it does *not* say
  "easy" — it says so, keeps confidence low, and names the blind spots (crypto,
  SQL tuning, timezones/DST, concurrency).
- **`lessons` counts only outcomes you recorded.** Never inferred.

It's a second opinion to argue with, not an oracle. `modelfit run` is the evidence.

### It grades itself

```bash
modelfit eval
```

Labelled cases live in `eval/advisor_cases.yaml` (data, same as tasks), split
into *clear* wording and *adversarial* wording, and both numbers are printed:

```
  overall     : 0.60  (12/20)
  clear       : 1.00  (10/10)  — does the mechanism work?
  adversarial : 0.20  (2/10)   — how far wording is from meaning
```

The adversarial number is *meant* to be poor, and the misses are listed in full.
That gap is the caveat made measurable; blending it into one headline accuracy
would be the dishonest version of this tool.

## Development

```bash
git clone https://github.com/dapinder-dhillon/modelfit.git
cd modelfit
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
tasks/*.yaml             # your tasks: id, quadrant, prompt, verifier, fixture  <- edit this
eval/advisor_cases.yaml  # labelled cases the advisor grades itself against
modelfit/
  tasks.py          # Task dataclass + load_tasks(): reads and validates tasks/*.yaml
  verifiers.py      # deterministic pass/fail checks
  providers.py      # model tiers, effort→budget, pricing, real call, mock, CLI-mode adapter
  runner.py         # sweeps the grid, caches results additively
  score.py          # cost-per-solved, Pareto frontier, per-quadrant winner
  report.py         # markdown + CSV + Pareto PNG
  advisor.py        # estimate(): regex signals -> quadrant + plan + confidence
  advice_report.py  # the written verdict for one task
  project.py        # projected pass-rate vs cost chart for one task
  history.py        # ~/.modelfit/history.json + lessons()
  evalset.py        # loads eval/advisor_cases.yaml, scores the advisor
  cli.py            # `run` | `advise` | `lessons` | `eval`
```

## Honest caveats

- **Pricing in `providers.py` is placeholder — confirm current numbers yourself.**
- `verify_python_callable` executes generated code in a subprocess with a
  timeout. Fine for a local experiment on models you chose; isolate properly
  (container / nsjail) for anything untrusted or CI.
- The mock's pass rates are illustrative. Only `--real`/`--via-cli` numbers are evidence.
- `--via-cli` is directional, not precise: the CLI may inject its own system
  prompt/tools/context, effort isn't controllable on every agent for every
  level, and cost is `n/a` whenever the CLI didn't report usage. See "Run it
  through a CLI you're already logged into" above.
- `advise` is a heuristic over wording, not a measurement. It is deterministic and
  it explains itself, but it cannot see difficulty the words don't carry — see its
  own adversarial score in `modelfit eval`. The projection chart it draws is
  modelled from the shape, not measured.
````

### B-mock — Business analyst

Command:
```sh
modelfit run --mock
```

Exit code: 0

Output (verbatim):
````text
Running 5 tasks x 4 models x 3 efforts x 8 trials in MOCK mode...

(mock mode: illustrative synthetic results, not measured model performance — see --real / --via-cli)

=== Recommendation by task type ===
  NEITHER  -> haiku-4-5      effort=off   pass=100%  $0.0006/solved
  EFFORT   -> sonnet-5       effort=high  pass=100%  $0.1522/solved
  MODEL    -> fable-5        effort=low   pass=100%  $0.1072/solved
  BOTH     -> opus-4-8       effort=high  pass= 88%  $0.2899/solved

=== Cost-efficiency frontier (rational choices only) ===
  haiku-4-5      effort=off   pass= 22%  $0.0026/solved
  sonnet-5       effort=off   pass= 35%  $0.0062/solved
  opus-4-8       effort=off   pass= 55%  $0.0066/solved
  sonnet-5       effort=low   pass= 57%  $0.0559/solved
  opus-4-8       effort=low   pass= 78%  $0.0692/solved
  opus-4-8       effort=high  pass= 90%  $0.2818/solved

Wrote reports/report.md, results.csv (install matplotlib for the chart)
````

### B1 — Business analyst

Command:
```sh
modelfit advise 'Add up sales by region in my spreadsheet and show the totals.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_add_up_sales_by_region_in.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### B2 — Business analyst

Command:
```sh
modelfit advise "Write a two-paragraph summary of this month's sales for my boss."
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_write_a_two_paragraph_summary_of.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### B3 — Business analyst

Command:
```sh
modelfit advise 'Match the London and New York transaction times in my spreadsheet for the week the clocks change.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_match_the_london_and_new_york.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### B4 — Business analyst

Command:
```sh
modelfit advise 'Make the SQL behind my sales dashboard faster; it takes twenty minutes to open.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_make_the_sql_behind_my_sales.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       sonnet-5 / high effort
IF NEEDED   switch to opus-4-8, same high effort
SIGNAL      high (clear read of your wording)

WHY         your wording has "sql" → needs real domain expertise, not just more thinking
````

### B5 — Business analyst

Command:
```sh
modelfit advise 'Explain why revenue fell even though we sold more units, separate price, volume and product-mix effects, and recommend what the sales team should do next.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_explain_why_revenue_fell_even_though.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       opus-4-8 / high effort
IF NEEDED   have a human review it — don't use it unattended
SIGNAL      medium (could be read another way)

WHY         your wording has "next", "why" and "recommend" → order matters; needs judgement the
            prompt doesn't provide; 3 requirements to track at once

SECOND OPINION  could be EFFORT instead. If it contradicts itself or drops one of your
                conditions, it needs more thinking time. Raise effort before
                switching to a bigger model.
````

### B6 — Business analyst

Command:
```sh
modelfit advise 'Explain why revenue fell even though we sold more units, separate price, volume and product-mix effects, and recommend what the sales team should do next.' --short
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_explain_why_revenue_fell_even_though.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json
opus-4-8/high → human review if it fails  [medium]
````

### B7 — Business analyst

Command:
```sh
modelfit advise 'Explain why revenue fell even though we sold more units, separate price, volume and product-mix effects, and recommend what the sales team should do next.' --explain
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_explain_why_revenue_fell_even_though.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

=== BOTH — long, multi-step, self-directed change over a wide surface ===
  lever      : BOTH — plus human review
  signal     : medium (The signals lean one way, but another result is still plausible.)
  scores     : effort 5 (baseline 1 + signals), model 3

--- why (signals that fired) ---
  - ordered / multi-step wording ("next") → effort +2 — state has to survive from one step to the next
  - judgement / knowledge wording ("why", "recommend") → model +2 — asks for a call that cannot be derived from the prompt alone
  - 3 separate requirements to satisfy at once → effort +2, model +1 — each one is another thing to not drop

--- start here ---
  opus-4-8 at high effort
  if it fails: have a human review it — don't use it unattended

--- not fully sure: second option ---
  could also be EFFORT (sonnet-5 at low effort)
  how to tell : If it contradicts itself or drops one of your conditions, it needs more thinking time. Raise effort before switching to a bigger model.

Turn up BOTH and keep a human in the loop. Long, self-directed work needs a more capable model and more thinking time, and the result still needs review.
````

### B-report — Business analyst

Command:
```sh
cat reports/report.md
```

Exit code: 0

Output (verbatim):
````text
# modelfit report

_Mode: **mock**. Cost is per **solved** task, not per token._

> **Mock mode:** every number below is an illustrative synthetic result from a deterministic formula, not a measured outcome from any real model. It proves the tool's machinery works; it is not evidence about which model is actually best. Run `--real` or `--via-cli` for numbers you can act on.

## The verdict, by task type

What the failure shape tells you to turn — read straight off the data.

| Task type | Use this model | Effort | Pass rate | $/solved | Why |
|---|---|---|---|---|---|
| NEITHER | `haiku-4-5` | off | 100% | $0.00056 | recall/boilerplate — cheapest config already wins |
| EFFORT | `sonnet-5` | high | 100% | $0.1522 | logic to work out — **effort** carried it, not the model |
| MODEL | `fable-5` | low | 100% | $0.1072 | needs knowledge/judgement — **model** carried it, not effort |
| BOTH | `opus-4-8` | high | 88% | $0.2899 | long multi-step — needs a strong model **and** high effort |

## Cost-efficiency frontier

Only configs on the frontier are ever rational — everything else is beaten on both quality and cost. `*` marks the frontier.

| Model | Effort | Pass rate | Total cost | $/solved | Frontier |
|---|---|---|---|---|---|
| `opus-4-8` | high | 90% | $10.1444 | $0.2818 | * |
| `fable-5` | high | 90% | $20.2888 | $0.5636 |  |
| `opus-4-8` | low | 78% | $2.1444 | $0.0692 | * |
| `fable-5` | low | 78% | $4.2888 | $0.1383 |  |
| `sonnet-5` | high | 70% | $6.0866 | $0.2174 |  |
| `sonnet-5` | low | 57% | $1.2866 | $0.0559 | * |
| `opus-4-8` | off | 55% | $0.1444 | $0.00656 | * |
| `haiku-4-5` | high | 55% | $1.6231 | $0.0738 |  |
| `fable-5` | off | 52% | $0.2888 | $0.0138 |  |
| `haiku-4-5` | low | 45% | $0.3431 | $0.0191 |  |
| `sonnet-5` | off | 35% | $0.0866 | $0.00619 | * |
| `haiku-4-5` | off | 22% | $0.0231 | $0.00257 | * |

## How to read this

- Look **down a quadrant**, not at one global 'best model'. The winner changes by task type — that's the whole point.
- If a cheap model at **high effort** matches a big model, your bottleneck was deliberation, not knowledge. Don't pay for capability you don't need.
- The only place 'just use the best model at high effort' is correct is the **BOTH** row — long, self-directed, multi-step work.
- Now delete the toy tasks and drop in ~20 real ones from your backlog. The recommendation becomes yours, and defensible.
````

### P-skim — Project manager

Command:
```sh
sed -n '1,40p' README.md
```

Exit code: 0

Output (verbatim):
````text
# modelfit

[![CI](https://github.com/dapinder-dhillon/modelfit/actions/workflows/ci.yml/badge.svg)](https://github.com/dapinder-dhillon/modelfit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

<img src="media/demo.gif" alt="modelfit advise, then modelfit run --mock" width="80%" />

**Stop guessing which model to use. Measure it.**

Most model-selection advice is one sentence: *"use a bigger model for complex
tasks, otherwise a cheaper one."* It's useless because it never says how you'd
*know*, and because it treats model choice as a single dial. It isn't.

**Who this is for:** developers calling Claude programmatically — direct
API/SDK calls, or an agent CLI (`claude`, `codex`) that exposes its own effort
flag. "Effort" here is Anthropic's `thinking` parameter (or a CLI's own
reasoning-effort flag) — a real, settable dial in code, but **not** something
Claude Desktop or claude.ai chat expose to you. If you're chatting with Claude
through either of those, there's no lever in that UI for this tool's
recommendations to turn — they're not for you (yet).

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
````

### P1 — Project manager

Command:
```sh
modelfit advise 'Turn these meeting notes into a short list of actions with an owner and due date for each.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_turn_these_meeting_notes_into_a.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### P2 — Project manager

Command:
```sh
modelfit advise 'Draft a polite reminder that the status update is due Friday.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_draft_a_polite_reminder_that_the.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### P3 — Project manager

Command:
```sh
modelfit advise 'Review this list of attendees and put the names in alphabetical order.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_review_this_list_of_attendees_and.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### P4 — Project manager

Command:
```sh
modelfit advise 'Build a recovery plan for a delayed launch across engineering, legal and marketing, identify dependencies, and recommend what to cut to keep the date.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_build_a_recovery_plan_for_a.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       opus-4-8 / high effort
IF NEEDED   have a human review it — don't use it unattended
SIGNAL      medium (could be read another way)

WHY         your wording has "recommend" and "across" → needs judgement the prompt doesn't
            provide; spans a lot of ground, self-directed; 3 requirements to track
            at once

SECOND OPINION  could be EFFORT instead. If it contradicts itself or drops one of your
                conditions, it needs more thinking time. Raise effort before
                switching to a bigger model.
````

### P5 — Project manager

Command:
```sh
modelfit advise 'Schedule the same 9 am London status call for our New York team every Monday through March and April.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_schedule_the_same_9_am_london.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### P6 — Project manager

Command:
```sh
modelfit advise 'Build a recovery plan for a delayed launch across engineering, legal and marketing, identify dependencies, and recommend what to cut to keep the date.' --short
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_build_a_recovery_plan_for_a.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json
opus-4-8/high → human review if it fails  [medium]
````

### P7 — Project manager

Command:
```sh
modelfit advise 'Build a recovery plan for a delayed launch across engineering, legal and marketing, identify dependencies, and recommend what to cut to keep the date.' --explain
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_build_a_recovery_plan_for_a.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

=== BOTH — long, multi-step, self-directed change over a wide surface ===
  lever      : BOTH — plus human review
  signal     : medium (The signals lean one way, but another result is still plausible.)
  scores     : effort 4 (baseline 1 + signals), model 4

--- why (signals that fired) ---
  - judgement / knowledge wording ("recommend") → model +2 — asks for a call that cannot be derived from the prompt alone
  - breadth / self-directed wording ("across") → effort +1, model +1 — the surface to change was never enumerated for it
  - 3 separate requirements to satisfy at once → effort +2, model +1 — each one is another thing to not drop

--- start here ---
  opus-4-8 at high effort
  if it fails: have a human review it — don't use it unattended

--- not fully sure: second option ---
  could also be EFFORT (sonnet-5 at low effort)
  how to tell : If it contradicts itself or drops one of your conditions, it needs more thinking time. Raise effort before switching to a bigger model.

Turn up BOTH and keep a human in the loop. Long, self-directed work needs a more capable model and more thinking time, and the result still needs review.
````

### S-budget — Student

Command:
```sh
modelfit advise 'Explain Python list comprehensions with one small example.' --budget 0.01
```

Exit code: 2

Output (verbatim):
````text
usage: modelfit [-h] {run,advise,lessons,eval} ...
modelfit: error: unrecognized arguments: --budget 0.01
````

### S-help — Student

Command:
```sh
modelfit advise --help
```

Exit code: 0

Output (verbatim):
````text
usage: modelfit advise [-h] [--short | --explain] [--out OUT] [--chart CHART]
                       [--outcome {pass,fail}] [--used-effort {off,low,high}]
                       text

positional arguments:
  text                  the task, in the words you'd actually use

options:
  -h, --help            show this help message and exit
  --short, --compact    one line: model/effort, escalation, confidence -- for
                        repeat use
  --explain             full signal-by-signal breakdown and raw scores -- for
                        debugging the classifier
  --out OUT             markdown path (default: reports/advice_*.md)
  --chart CHART         chart path (default: reports/advice_*.png)
  --outcome {pass,fail}
                        record what actually happened at the advised start
                        (feeds `lessons`)
  --used-effort {off,low,high}
                        the effort you actually used, recorded alongside the
                        outcome
````

### S1 — Student

Command:
```sh
modelfit advise 'Explain Python list comprehensions with one small example.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_explain_python_list_comprehensions_with_one.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### S2 — Student

Command:
```sh
modelfit advise 'Turn these lecture notes into ten flashcards for my biology quiz.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_turn_these_lecture_notes_into_ten.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       haiku-4-5 / no extra thinking
SIGNAL      low (just a guess — see below)

BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
                crypto, SQL tuning, timezones / DST, concurrency can all look
                simple from the wording alone. If this task is actually one of
                those, start with sonnet-5 at high effort yourself instead of
                the suggestion above.
````

### S3 — Student

Command:
```sh
modelfit advise 'Help me prove that every finite integral domain is a field, explaining each step without assuming the theorem.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_help_me_prove_that_every_finite.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       sonnet-5 / low effort
IF NEEDED   raise effort to high before switching model
SIGNAL      high (clear read of your wording)

WHY         your wording has "without" and "step" → a condition must stay true; order matters
````

### S4 — Student

Command:
```sh
modelfit advise 'Make my SQL query faster. It joins three tables for my coursework and takes five minutes.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_make_my_sql_query_faster_it.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       sonnet-5 / high effort
IF NEEDED   switch to opus-4-8, same high effort
SIGNAL      high (clear read of your wording)

WHY         your wording has "sql" and "query" → needs real domain expertise, not just more
            thinking
````

### S5 — Student

Command:
```sh
modelfit advise 'Compare three papers on antibiotic resistance, explain why their findings disagree, and help me defend a thesis for my final-year essay.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_compare_three_papers_on_antibiotic_resistance.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       sonnet-5 / high effort
IF NEEDED   switch to opus-4-8, same high effort
SIGNAL      medium (could be read another way)

WHY         your wording has "why" → needs judgement the prompt doesn't provide

SECOND OPINION  could be NEITHER instead. If the cheapest config passes first time, the wording
                made the task look harder than it was. Use the cheap config.
````

### S6 — Student

Command:
```sh
modelfit advise 'Make my SQL query faster. It joins three tables for my coursework and takes five minutes.' --short
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_make_my_sql_query_faster_it.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json
sonnet-5/high → escalate if needed  [high]
````

### S7 — Student

Command:
```sh
modelfit advise 'Make my SQL query faster. It joins three tables for my coursework and takes five minutes.' --explain
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_make_my_sql_query_faster_it.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

=== MODEL — knowledge / judgement — a call you can't derive from the prompt ===
  lever      : the MODEL
  signal     : high (Several signals point the same way, so confidence is high.)
  scores     : effort 1 (baseline 1 + signals), model 2

--- why (signals that fired) ---
  - names a documented blind-spot domain ("sql", "query") → model +2 — crypto/SQL/timezone/concurrency topics need real expertise, not just more thinking

--- start here ---
  sonnet-5 at high effort
  if it fails: switch to opus-4-8, same high effort

Turn up the MODEL, not effort. This task needs more knowledge or judgement; more thinking time will not add either.
````

### S-run-help — Student

Command:
```sh
modelfit run --help
```

Exit code: 0

Output (verbatim):
````text
usage: modelfit run [-h] [--mock | --real | --via-cli {claude,codex}]
                    [--models MODELS [MODELS ...]]
                    [--efforts EFFORTS [EFFORTS ...]] [--trials TRIALS]
                    [--out OUT] [--tasks TASKS] [--no-cache] [--yes]

options:
  -h, --help            show this help message and exit
  --mock                deterministic offline demo (default)
  --real                call the Anthropic API
  --via-cli {claude,codex}
                        run via an already-authenticated agent CLI (spends
                        real quota; no API key stored here). For codex, pass
                        --models with GPT ids, not the Anthropic MODELS table.
  --models MODELS [MODELS ...]
  --efforts EFFORTS [EFFORTS ...]
  --trials TRIALS       repeats per cell (reliability estimate). default: 8
                        mock, 1 real/cli
  --out OUT
  --tasks TASKS         directory of *.yaml task files
  --no-cache
  --yes                 skip the spend confirmation for --via-cli
````

### S-mock — Student

Command:
```sh
modelfit run --mock
```

Exit code: 0

Output (verbatim):
````text
Running 5 tasks x 4 models x 3 efforts x 8 trials in MOCK mode...

(mock mode: illustrative synthetic results, not measured model performance — see --real / --via-cli)

=== Recommendation by task type ===
  NEITHER  -> haiku-4-5      effort=off   pass=100%  $0.0006/solved
  EFFORT   -> sonnet-5       effort=high  pass=100%  $0.1522/solved
  MODEL    -> fable-5        effort=low   pass=100%  $0.1072/solved
  BOTH     -> opus-4-8       effort=high  pass= 88%  $0.2899/solved

=== Cost-efficiency frontier (rational choices only) ===
  haiku-4-5      effort=off   pass= 22%  $0.0026/solved
  sonnet-5       effort=off   pass= 35%  $0.0062/solved
  opus-4-8       effort=off   pass= 55%  $0.0066/solved
  sonnet-5       effort=low   pass= 57%  $0.0559/solved
  opus-4-8       effort=low   pass= 78%  $0.0692/solved
  opus-4-8       effort=high  pass= 90%  $0.2818/solved

Wrote reports/report.md, results.csv (install matplotlib for the chart)
````

### D-eval — Release check

Command:
```sh
modelfit eval
```

Exit code: 0

Output (verbatim):
````text

=== Advisor self-eval (deterministic, exact quadrant match) ===
  overall     : 0.83  (19/23)
  clear       : 1.00  (11/11)  — does the mechanism work?
  adversarial : 0.67  (8/12)  — how far wording is from meaning

--- misses (kept on purpose; this is the error bar) ---
  [adversarial] said NEITHER, truth MODEL: Store user passwords in the users table.
      Still a genuine miss, on purpose. "Password" alone isn't specific enough to add as a domain word without risking false positives on ordinary CRUD tasks that happen to touch a users table — unlike "sql"/"jwt"/"thread", which are nearly always genuine domain markers. The real content here (hashing, salting, cost factors) never gets said.
  [adversarial] said NEITHER, truth EFFORT: Add a retry with exponential backoff and jitter.
      The off-by-one on the final attempt and the jitter bounds are real deliberation, but nothing in the sentence says so.
  [adversarial] said EFFORT, truth NEITHER: Return the list without duplicates.
      FALSE TRIGGER — "without" is a preposition here, not a constraint. The advisor over-reads it as EFFORT.
  [adversarial] said NEITHER, truth MODEL: Review this code and sort out the deployment issue.
      A NEW miss, introduced by the fix above that discounts "review" next to a mechanical verb (see "review the array"). "Sort out" is idiomatic for "resolve", not literal sorting, but the regex can't tell the difference from "sort" in "sort the list" -- so "review" gets wrongly discounted here too, and no signal fires at all. Kept in on purpose: fixing one false positive on a word ("review") that only ever means one of two things (filler vs. judgement) introduces a new false negative on a *different* word ("sort") that also means one of two things (literal vs. idiomatic). That trade is honest to show, not something to hide by deleting the case.

The adversarial number is meant to be poor. A word-reader cannot see difficulty that the words don't carry —
that gap is the caveat, so it is printed, not blended away.

````

### D3-short-check — Release check

Command:
```sh
modelfit advise 'Review the list of service names and return it sorted alphabetically.' --short
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_review_the_list_of_service_names.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json
haiku-4-5/off  [low — blind spot]
````

### README-SQL — Documentation check

Command:
```sh
modelfit advise 'Optimise this SQL query'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_optimise_this_sql_query.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       sonnet-5 / high effort
IF NEEDED   switch to opus-4-8, same high effort
SIGNAL      high (clear read of your wording)

WHY         your wording has "sql" and "query" → needs real domain expertise, not just more
            thinking
````

### README-example — Documentation check

Command:
```sh
modelfit advise 'Fix this retry helper so it never sleeps after the final attempt.'
```

Exit code: 0

Output (verbatim):
````text
Wrote reports/advice_fix_this_retry_helper_so_it.md (install matplotlib for the chart); logged to /Users/dapindersingh/.modelfit/history.json

START       sonnet-5 / low effort
IF NEEDED   raise effort to high before switching model
SIGNAL      high (clear read of your wording)

WHY         your wording has "never" and "after" → a condition must stay true; order matters
````

### lessons — Release check

Command:
```sh
modelfit lessons
```

Exit code: 0

Output (verbatim):
````text

=== Lessons from your own advice history ===
  - Shapes you have asked about (86 total): NEITHER 36, MODEL 21, BOTH 19, EFFORT 10.
  - Most of your asks look routine — your default config should be the cheap one.
  - 36/86 verdicts were low confidence — the wording carried no signal. Those are the ones to double-check by hand, not to trust.
  - Calibration: 0/1 recorded outcomes passed at the advised start config (1/86 asks have a recorded outcome; the rest are not counted either way).
  - Recorded failures at the advised start, by shape: EFFORT (1). If one shape dominates, the plan for that shape starts too low.
  - Standing lesson: the advisor reads wording, not meaning. When it says low confidence, believe it — crypto, SQL tuning, timezone/DST and concurrency work all look boring in a one-line prompt.

````

