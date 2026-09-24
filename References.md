# References & prior work

`modelfit` is a deliberately transparent instantiation of ideas that are
well-established in the literature. This file records what it builds on, and —
just as importantly — where it diverges, so the lineage is explicit and the
novelty is honestly scoped.

## What rests on what

| modelfit design choice | Grounded in | Result it leans on |
|---|---|---|
| **Start cheap, escalate only on failure** (`run` cascade) | FrugalGPT | An LLM *cascade* can match the strongest single model at a large fraction of the cost. |
| **Most tasks don't need the frontier model; route by difficulty** (`advise` premise) | RouteLLM | Routing simpler queries to cheaper models cuts cost >2× without sacrificing quality. |
| **Effort/thinking is a *separate* lever whose payoff depends on difficulty** (the second dial) | Snell et al. | Test-time compute helps more or less depending on prompt difficulty; a smaller model given more thinking can beat a much larger one. |
| **Estimate the task's shape before spending** | Snell et al. | They classify tasks into difficulty levels to allocate compute — modelfit does the analogous step *deterministically* from wording. |
| **Measure in human-time; long self-directed work is the hard quadrant; reliability needs repeats** (`--trials`, BOTH) | METR | Capability is measured as the human task-length a model completes at a given success rate; the metric is defined at X% reliability precisely because models don't reliably finish all tasks of a given length. |
| **When the signal is weak, hedge / abstain rather than commit** (confidence + blind-spot) | Cascades with early abstention; classical selective prediction | Abstention can be added to a cascade as a final layer without hurting performance. |

## Where modelfit diverges (the honest novelty)

The works above almost all use **learned or model-driven** routers and difficulty
classifiers. `modelfit`'s contribution is not the concept but the **instantiation**:

- The `advise` router is **deterministic and transparent** — regex signals over
  wording, not a trained model — so it can *show its reasoning* and never calls an
  LLM to decide which LLM to use.
- It is **pedagogical**: the goal is to teach a human the two-dial judgement, not
  to route silently. It states its confidence and is explicit about its blind
  spots (wording cannot carry hidden difficulty such as crypto or concurrency).
- It reports **cost-per-solved on your own tasks**, via deterministic verifiers,
  rather than quality judged by another model.

Cite the papers below for the **principles**. Do **not** cite them as endorsement
of modelfit's specific heuristic — the accuracy of that heuristic is whatever
`modelfit eval` reports on a given labelled set, and that claim stands on its own.

## BibTeX

```bibtex
@inproceedings{ong2025routellm,
  title     = {Route{LLM}: Learning to Route {LLM}s with Preference Data},
  author    = {Ong, Isaac and Almahairi, Amjad and Wu, Vincent and
               Chiang, Wei-Lin and Wu, Tianhao and Gonzalez, Joseph E. and
               Kadous, M. Waleed and Stoica, Ion},
  booktitle = {The Thirteenth International Conference on Learning Representations (ICLR)},
  year      = {2025},
  eprint    = {2406.18665},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  url       = {https://arxiv.org/abs/2406.18665}
}

@article{chen2023frugalgpt,
  title   = {Frugal{GPT}: How to Use Large Language Models While Reducing Cost
             and Improving Performance},
  author  = {Chen, Lingjiao and Zaharia, Matei and Zou, James},
  journal = {arXiv preprint arXiv:2305.05176},
  year    = {2023},
  url     = {https://arxiv.org/abs/2305.05176}
}

@inproceedings{snell2025scaling,
  title     = {Scaling {LLM} Test-Time Compute Optimally can be More Effective
               than Scaling Model Parameters},
  author    = {Snell, Charlie and Lee, Jaehoon and Xu, Kelvin and Kumar, Aviral},
  booktitle = {The Thirteenth International Conference on Learning Representations (ICLR)},
  year      = {2025},
  eprint    = {2408.03314},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  url       = {https://arxiv.org/abs/2408.03314}
}

@article{kwa2025measuring,
  title   = {Measuring AI Ability to Complete Long Software Tasks},
  author  = {Kwa, Thomas and West, Ben and Becker, Joel and Deng, Amy and
             Garcia, Katharyn and Hasin, Max and Jawhar, Sami and
             Kinniment, Megan and Rush, Nate and Von Arx, Sydney and
             Barnes, Elizabeth and Chan, Lawrence and others},
  journal = {arXiv preprint arXiv:2503.14499},
  year    = {2025},
  url     = {https://arxiv.org/abs/2503.14499}
}

@article{jung2025abstention,
  title   = {Cost-Saving LLM Cascades with Early Abstention},
  author  = {Jung, Aron and others},
  journal = {arXiv preprint arXiv:2502.09054},
  year    = {2025},
  url     = {https://arxiv.org/abs/2502.09054}
}
```

## Notes

- Verify author lists and venues against the arXiv abstract pages before
  publishing — some (e.g. the abstention paper's full author list, and any
  camera-ready venue) may have changed since these entries were compiled.
- FrugalGPT descends from the pre-LLM **FrugalML** (Chen, Zaharia, Zou, NeurIPS
  2020); the "more deliberation helps reasoning" idea traces to **Chain-of-Thought
  Prompting** (Wei et al., arXiv:2201.11903). Add these if you want the fuller
  lineage.