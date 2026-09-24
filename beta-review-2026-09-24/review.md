**modelfit: first-use beta review — 24 September 2026**

The strongest result from this session is a trust problem: the advisor confidently sends alphabetical sorting to high effort, while more consequential work gets advice the user must correct themselves. The useful part is the explicit model-versus-effort distinction and the proposed escalation sequence. Those benefits currently suit a developer who will challenge the recommendation and measure outcomes.

This is a simulated four-persona usability review based on commands I actually executed, not interviews with four people. I ran **30 advice invocations: 28 succeeded, one hit the execution environment's filesystem restriction, and one intentionally tried an unsupported budget flag**. Each persona completed seven successful advice calls covering five different tasks; two calls repeated one task with `--short` and `--explain`. I also ran `lessons` once and `run --mock` twice.

I used the installed CLI at `/Users/dapindersingh/.local/bin/modelfit`. I did not open Python source, CLAUDE.md, or Concepts.md, change the implementation, or run a real model. The first failed command printed a traceback; I used only the permission error as evidence, not its incidental source snippets. The excerpts below are exact substrings of captured output. Complete commands, exit codes, and unabridged output are in [transcript.md](transcript.md), with machine-readable captures in [transcript.json](transcript.json).

The requested outcome-recording test used **one deliberately synthetic `fail` at `low` effort**, solely to exercise that feature. It is not a measured model failure. The tool appended advice calls to its normal local history and wrote its normal reports. I did not clear existing history: `lessons` reported 21 asks after the developer's seven successful calls, so its counts include 14 pre-existing asks.

**Developer — terminal first; docs only when stuck**

I went straight to a simple coding task. The first attempt printed a recommendation and then failed:

```text
PermissionError: [Errno 1] Operation not permitted: '/Users/dapindersingh/.modelfit/history.json'
```

I initially wondered whether the recommendation had failed too. After the execution environment granted access to the normal history file, the identical command succeeded. This is a conditional handling problem, not evidence that normal installations cannot write history.

I typed (D1-retry):

```sh
modelfit advise 'Write a Python function that takes a list of integers and returns the even ones.'
```

I saw this excerpt:

```text
START       haiku-4-5 / no extra thinking
CONFIDENCE  low (just a guess — see below)
```

My reaction: an even-number filter gets a tentative recommendation and a long warning. The start is readable, but I already have to decide how much weight to put on it. I checked `modelfit advise --help` after the failure to understand the output and available controls.

I typed (D2):

```sh
modelfit advise 'Fix an intermittent bug where two workers process the same payment webhook at once and charge the customer twice. Keep retries safe.'
```

I saw this excerpt:

```text
WHY         your wording has "once" → order matters
```

My reaction: I said two workers act at once. That is simultaneous execution, not an ordered sequence. The explanation makes me trust this recommendation less.

I typed (D3):

```sh
modelfit advise 'Review the list of service names and return it sorted alphabetically.'
```

I saw this excerpt:

```text
START       sonnet-5 / high effort
IF NEEDED   switch to opus-4-8 at low effort before raising effort
CONFIDENCE  high (clear read of your wording)

WHY         your wording has "review" → needs judgement the prompt doesn't provide
```

My reaction: seriously? Alphabetical sorting needs judgement because I used “review”? This is where I would stop treating `advise` as a reliable selector.

I typed (D4):

```sh
modelfit advise 'Check that our AES-GCM helper never reuses a nonce, even when several workers restart at the same time.'
```

I saw this excerpt:

```text
WHY         your wording has "never" → a condition must stay true
```

My reaction: it noticed a constraint, but the reason tells me nothing about nonce reuse or concurrent restarts. I cannot infer that low effort is appropriate from this explanation.

I typed (D5):

```sh
modelfit advise 'Design a migration from a synchronous REST API to an event-driven service. Compare failure modes, preserve backwards compatibility, and give me a staged rollout and rollback plan.'
```

I saw this excerpt:

```text
START       opus-4-8 / high effort
IF NEEDED   have a human review it — don't ship unattended
```

My reaction: this direction feels proportionate to a migration, and an explicit human-review endpoint is useful. That is a plausible starting plan, not proof of model suitability.

I typed (D6):

```sh
modelfit advise 'Fix an intermittent bug where two workers process the same payment webhook at once and charge the customer twice. Keep retries safe.' --short
```

I saw this excerpt:

```text
sonnet-5/low → escalate if needed  [medium]
```

My reaction: I can scan that quickly, but “escalate” has lost the precise instruction to raise effort before switching models. That was the useful part.

I typed (D7):

```sh
modelfit advise 'Fix an intermittent bug where two workers process the same payment webhook at once and charge the customer twice. Keep retries safe.' --explain --outcome fail --used-effort low
```

I saw this excerpt:

```text
  - ordered / multi-step wording ("once") → effort +2 — state has to survive from one step to the next
```

My reaction: the detailed view confirms the wrong reading of “at once.” The transparency is genuinely useful for debugging the recommendation. I attached the synthetic failure requested for this review; I did not actually run a payment fix.

I then typed `modelfit lessons` (D-lessons). It printed:

```text
  - Calibration: 0/1 recorded outcomes passed at the advised start config (1/21 asks have a recorded outcome; the rest are not counted either way).
```

My reaction: the denominator is explicit, which is good. But that is one test entry inside shared history, not an accuracy result. I understand the purpose by now: suggest a starting model/effort, then separately benchmark real tasks. I would stop trusting the advisor at D3, but might keep evaluating the benchmark half. **Verdict: adopt only experimentally, using measured results to overrule advice.**

**Business analyst — reads the README and follows its first runnable example**

I read `README.md` first. It said:

```text
**Who this is for:** developers calling Claude programmatically — direct
API/SDK calls, or an agent CLI (`claude`, `codex`) that exposes its own effort
flag.
```

My reaction: I use browser chat and Excel. This is already telling me I am outside its audience. I would probably stop here without an engineer helping; for the review I continued with the installed tool.

I followed the first no-key example literally: `modelfit run --mock` (B-mock). Among the output:

```text
  EFFORT   -> sonnet-5       effort=high  pass=100%  $0.1522/solved
```

My reaction: cost per successful task is a useful way to compare spending. But what kind of business task is “EFFORT,” and what counts as solved? I read `reports/report.md` (B-report), which helped associate rows with failure types. I know from the README that this is a demonstration; I cannot use these figures as a budget estimate. The command also printed:

```text
Wrote reports/report.md, results.csv (install matplotlib for the chart)
```

I expected the chart promised in the quick start. I am not comfortable deciding how to install an extra plotting package into this tool's environment.

I typed (B1):

```sh
modelfit advise 'Add up sales by region in my spreadsheet and show the totals.'
```

I saw this excerpt:

```text
START       haiku-4-5 / no extra thinking
CONFIDENCE  low (just a guess — see below)
```

My reaction: I expected a clear choice for a basic spreadsheet total. “Just a guess” leaves me unsure whether I should act on it.

I typed (B2):

```sh
modelfit advise "Write a two-paragraph summary of this month's sales for my boss."
```

I saw this excerpt:

```text
START       haiku-4-5 / no extra thinking
```

My reaction: this looks like the same answer and warning as the totals task. I understand that it recommends a model; it does not actually write my summary.

I typed (B3):

```sh
modelfit advise 'Match the London and New York transaction times in my spreadsheet for the week the clocks change.'
```

I saw this excerpt:

```text
BLIND SPOT      Nothing in the wording signals difficulty. That is this tool's blind spot:
```

My reaction: the whole difficulty is matching two cities during a clock change. The warning names timezones later, but I have to override the prominent start recommendation myself.

I typed (B4):

```sh
modelfit advise 'Make the SQL behind my sales dashboard faster; it takes twenty minutes to open.'
```

I saw this excerpt:

```text
START       haiku-4-5 / no extra thinking
```

My reaction: the warning explicitly lists SQL tuning, yet the start is still the cheapest option. I have to reread the paragraph to find the alternative.

I typed (B5):

```sh
modelfit advise 'Explain why revenue fell even though we sold more units, separate price, volume and product-mix effects, and recommend what the sales team should do next.'
```

I saw this excerpt:

```text
START       opus-4-8 / high effort
IF NEEDED   have a human review it — don't ship unattended
```

My reaction: checking a revenue explanation before using it is sensible. “Ship” sounds like software language; I want to know how to apply this choice to my reporting workflow.

I typed (B6):

```sh
modelfit advise 'Explain why revenue fell even though we sold more units, separate price, volume and product-mix effects, and recommend what the sales team should do next.' --short
```

I saw this excerpt:

```text
opus-4-8/high → escalate if needed  [medium]
```

My reaction: escalate to whom or to what? The full view gave me a human-review instruction; this version removes it.

I typed (B7):

```sh
modelfit advise 'Explain why revenue fell even though we sold more units, separate price, volume and product-mix effects, and recommend what the sales team should do next.' --explain
```

I saw this excerpt:

```text
Turn up BOTH and keep a human in the loop. Long, self-directed work needs a more capable model and more thinking time, and the diff still needs review.
```

My reaction: I do not know what “the diff” means for my sales explanation. The scores and labels do not help me choose a setting in the chat product I use.

By the end I understand the broad purpose: help programmers choose and test AI settings. The cost-per-solved idea is the useful moment, but the recommendation is not directly usable in my existing tools. I would have quit at the audience statement, and the missing-chart setup would be a second exit. **Verdict: need a developer to explain and operate it; no independent adoption.**

**Project manager — skims and evaluates whether the team should bother**

I skimmed only the opening 40 lines of the README (P-skim). The promise was:

```text
**Stop guessing which model to use. Measure it.**
```

My reaction: fine, show me whether this saves the team time or money. I would delegate the commands, not maintain this myself. For this session I acted as the person requesting and reviewing each quick trial.

I typed (P1):

```sh
modelfit advise 'Turn these meeting notes into a short list of actions with an owner and due date for each.'
```

I saw this excerpt:

```text
CONFIDENCE  low (just a guess — see below)
```

My reaction: meeting actions are routine. I do not want to spend the saved minute interpreting a warning about crypto.

I typed (P2):

```sh
modelfit advise 'Draft a polite reminder that the status update is due Friday.'
```

I saw this excerpt:

```text
START       haiku-4-5 / no extra thinking
```

My reaction: that is a simple enough answer, but the repeated uncertainty gives me little reason to add a new step before drafting a reminder.

I typed (P3):

```sh
modelfit advise 'Review this list of attendees and put the names in alphabetical order.'
```

I saw this excerpt:

```text
WHY         your wording has "review" → needs judgement the prompt doesn't provide
```

My reaction: no, I want names alphabetized. If this adds thinking cost to that request, I am not ready to recommend it to the team. This is my quit point.

I typed (P4):

```sh
modelfit advise 'Build a recovery plan for a delayed launch across engineering, legal and marketing, identify dependencies, and recommend what to cut to keep the date.'
```

I saw this excerpt:

```text
WHY         your wording has "recommend" and "across" → needs judgement the prompt doesn't
            provide; spans a lot of code, self-directed; 3 requirements to track at
            once
```

My reaction: what code? These are departments. The explicit human-review instruction above this was useful, but this explanation sounds copied from a software workflow.

I typed (P5):

```sh
modelfit advise 'Schedule the same 9 am London status call for our New York team every Monday through March and April.'
```

I saw this excerpt:

```text
START       haiku-4-5 / no extra thinking
```

My reaction: the awkward part is London and New York changing clocks on different dates. Again, the generic warning hands the actual decision back to the person requesting help.

I typed (P6):

```sh
modelfit advise 'Build a recovery plan for a delayed launch across engineering, legal and marketing, identify dependencies, and recommend what to cut to keep the date.' --short
```

I saw this excerpt:

```text
opus-4-8/high → escalate if needed  [medium]
```

My reaction: I would forward that one line to a colleague, but it omits that the next step was a human review. The compact view changes what the team takes away.

I typed (P7):

```sh
modelfit advise 'Build a recovery plan for a delayed launch across engineering, legal and marketing, identify dependencies, and recommend what to cut to keep the date.' --explain
```

I saw this excerpt:

```text
  scores     : effort 4 (baseline 1 + signals), model 4
```

My reaction: those numbers are not a delivery date, cost estimate, or success rate. I am impatient with the extra classifier detail; it does not answer whether onboarding pays off.

The human checkpoint on the launch plan is sensible, but there was no compelling adoption moment for me. I now understand that this is engineering tooling, and that the advice I tried is not itself a measurement. I would need a developer to show benchmark results on our tasks before sponsoring it. **Verdict: ignore for my own work; consider a small engineering pilot only with relevant evidence.**

**Student — guesses a budget flag, then tries to work out what the numbers mean**

I started with a spending limit. I typed (S-budget):

```sh
modelfit advise 'Explain Python list comprehensions with one small example.' --budget 0.01
```

It printed:

```text
usage: modelfit [-h] {run,advise,lessons,eval} ...
modelfit: error: unrecognized arguments: --budget 0.01
```

My reaction: I guessed wrong. I opened `modelfit advise --help` (S-help); there is no budget option in that help. The error is understandable, but I still cannot express my actual priority: keep this under a cent.

I typed (S1):

```sh
modelfit advise 'Explain Python list comprehensions with one small example.'
```

I saw this excerpt:

```text
START       haiku-4-5 / no extra thinking
CONFIDENCE  low (just a guess — see below)
```

My reaction: that sounds cheap, but I cannot see a price. “Low” here is confidence, not spending; I had to reread the label.

I typed (S2):

```sh
modelfit advise 'Turn these lecture notes into ten flashcards for my biology quiz.'
```

I saw this excerpt:

```text
START       haiku-4-5 / no extra thinking
```

My reaction: fine for flashcards, probably. The same technical warning is more text than the useful recommendation.

I typed (S3):

```sh
modelfit advise 'Help me prove that every finite integral domain is a field, explaining each step without assuming the theorem.'
```

I saw this excerpt:

```text
WHY         your wording has "without" and "step" → a condition must stay true; order matters
```

My reaction: this at least recognizes that I want a careful sequence. Trying more effort before paying for a bigger model is the first practical idea I can use.

I typed (S4):

```sh
modelfit advise 'Make my SQL query faster. It joins three tables for my coursework and takes five minutes.'
```

I saw this excerpt:

```text
START       haiku-4-5 / no extra thinking
```

My reaction: I asked about SQL, and the warning tells me SQL tuning is a blind spot. Why is the first line still pointing me somewhere else?

I typed (S5):

```sh
modelfit advise 'Compare three papers on antibiotic resistance, explain why their findings disagree, and help me defend a thesis for my final-year essay.'
```

I saw this excerpt:

```text
START       sonnet-5 / high effort
IF NEEDED   switch to opus-4-8 at low effort before raising effort
CONFIDENCE  high (clear read of your wording)
```

My reaction: a stronger starting point for comparing papers makes intuitive sense. I still do not know the cost of that next step.

I typed (S6):

```sh
modelfit advise 'Make my SQL query faster. It joins three tables for my coursework and takes five minutes.' --short
```

I saw this excerpt:

```text
haiku-4-5/off  [low]
```

My reaction: “off” looks like a setting; “[low]” could look like another setting if I had not just read the longer version. The SQL warning has vanished.

I typed (S7):

```sh
modelfit advise 'Make my SQL query faster. It joins three tables for my coursework and takes five minutes.' --explain
```

I saw this excerpt:

```text
  If that's the subject matter, start with sonnet-5 at high effort yourself instead.

Nothing needs turning up. Start with the cheapest config and escalate only if it fails.
```

My reaction: these are opposite directions for my SQL task, two lines apart. I would close the terminal here if this were not a review.

I then checked `modelfit run --help` (S-run-help). It described the flag as:

```text
  --mock                deterministic offline demo (default)
```

That reassured me this example would not spend my budget. I typed `modelfit run --mock` (S-mock) and saw both of these lines in different sections:

```text
  NEITHER  -> haiku-4-5      effort=off   pass=100%  $0.0006/solved
```

```text
  haiku-4-5      effort=off   pass= 22%  $0.0026/solved
```

My reaction: first 100%, then 22% for the same configuration? I reread the headings. One is within a task type and the other is aggregate; the denominator should be visible without decoding that distinction. Dollars per solved task is a clever framing, but these demo figures are not a personal spending forecast.

By the end I understand it recommends starting settings and can benchmark task sets. I would need help turning my coursework into something it can score. **Verdict: need an explanation first; might try the offline demo, would not base a budget on it.**

**Cross-persona comparison**

The developer got the most value. The explicit order of escalation and the signal breakdown were actionable for someone who understands models, effort controls, and verifiable tasks. The transparency also made it possible to spot a bad reading immediately. This does not establish that the recommendations improve performance.

The business analyst was the most confused overall. The README explicitly excludes their usual browser-chat workflow, and understanding the conceptual distinction still does not give them a place to apply the settings. This is partly a deliberate audience boundary, not automatically a product defect. If the intended audience stays developers, do not prioritize an Excel-user onboarding flow over fixing wrong or contradictory advice.

All four personas hit the same underlying question: **why should I follow the prominent start recommendation when the explanation either misses the actual task or tells me to choose something else?** All four also lost concrete next steps or qualifications in `--short`. These are the cross-persona fixes to prioritize.

The analyst's discomfort installing the optional plotting dependency was the clearest issue specific to the least technical persona. Jargon was not confined to that persona: the manager rejected developer language, and the student had to decode task-type labels and the two pass-rate scopes. The manager was the quickest to decide the extra step was not worth it; the student cared most about missing budget controls and whether cost figures were real.

Only now, after the raw reactions, the deliberately challenging probes were: simultaneous payment handling and crypto (D2/D4), false “review” triggers on sorting (D3/P3), clock changes (B3/P5), and SQL performance (B4/S4/S6/S7). This is not an accuracy score or a claim that a particular model would fail. No model actually solved these tasks during this test.

**Prioritized findings — fix the first five before expanding the feature list**

| Issue | Who hit it | Exact quote from output | Severity (blocks understanding / annoying / minor) | Suggested fix |
|---|---|---|---|---|
| 1. A superficial word creates a confident, expensive recommendation for trivial sorting. | Developer, PM (D3/P3). | `CONFIDENCE  high (clear read of your wording)` (D3) | blocks understanding | Make confidence distinguish a wording match from confidence in the recommendation. Handle explicit mechanical operations such as sorting before broad judgement words; preserve the real task context. |
| 2. Hidden-difficulty warnings and the final instruction contradict the start recommendation. | All four; most explicit in the student's SQL explanation (S7). | `Nothing needs turning up. Start with the cheapest config and escalate only if it fails.` (S7) | blocks understanding | Produce one consistent action across START, warning, and conclusion. When the task explicitly names a listed blind spot, surface that limitation and an appropriate cautious starting path; do not finish by declaring that nothing needs turning up. |
| 3. Compact mode drops the reason, specific escalation, and sometimes the caution entirely. | All four comparisons (D6, B6, P6, S6). | `haiku-4-5/off  [low]` (S6) | blocks understanding | Keep a compact caution marker and the actual next action. Label confidence. For high-effort recommendations whose next step is a human review, say that rather than generic escalation. |
| 4. Mock cost/performance reports look more authoritative than the evidence permits. | Analyst and student (B-mock/B-report/S-mock). | `What the failure shape tells you to turn — read straight off the data.` (B-report) | blocks understanding | Put 'illustrative synthetic results; placeholder costs; not measured model performance' beside the numbers in both terminal and exported report. Keep MOCK, but do not rely on that word alone. Label per-type versus aggregate rates. |
| 5. Generic explanations assert software-specific facts about non-code work. | Analyst and PM (B7, P4/P7). | `spans a lot of code, self-directed` (P4) | annoying | Use task-neutral descriptions unless the task mentions code. Replace 'the diff' and 'ship' for non-code work; do not interpret 'across departments' as code breadth. |
| 6. The budget-minded user cannot state a spending limit in advise. | Student (S-budget). | `modelfit: error: unrecognized arguments: --budget 0.01` (S-budget) | annoying | Explain that advice itself is offline and does not price or execute the task. Consider a budget preference only if it can be honored; point to measurement for task-specific costs. |
| 7. The no-key quick start promises a chart that the installed base package cannot produce. | Analyst (B-mock). | `Wrote reports/report.md, results.csv (install matplotlib for the chart)` (B-mock) | minor | Say charts are optional in the quick-start promise. Give one installation command that matches how the tool was installed, with no need to guess the environment. |
| 8. An unwritable history file turns a displayed recommendation into a traceback and failure exit. | Developer's initial sandboxed launch only (D1). | `PermissionError: [Errno 1] Operation not permitted: '/Users/dapindersingh/.modelfit/history.json'` (D1) | annoying | Handle history-write failure concisely and offer a no-history route. Preserve usable advice where possible. Do not treat this environment restriction as a normal-installation failure. |

The first five are ranked by their effect on interpreting or trusting the product, not by how much console text they generate. The mock was clearly named as a mock, and the README disclosed its illustrative nature and placeholder pricing; finding 4 is about carrying those limitations into the report people will actually read or share. The missing chart was not a crash, and the history failure recovered after permission was granted. No recommendation here claims to be validated by real model performance.
