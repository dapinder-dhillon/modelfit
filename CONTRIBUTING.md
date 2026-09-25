# Contributing

## Setup

```bash
poetry install --with dev --extras all
```

## Before opening a PR

```bash
poetry run pytest
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy modelfit
```

All four also run in CI on every push and pull request.

## The one rule

Every verifier must be deterministic and machine-checkable — no LLM-as-judge,
no semantic-similarity scoring, no network calls inside a verifier. That
discipline is what makes this tool's numbers trustworthy.

`verify_python_callable` runs model-generated code in a subprocess with a
timeout. Keep that boundary, and isolate further (container, nsjail, seccomp)
before running anything untrusted or in CI. Read the README's "How it works"
section before adding tasks, verifiers, or providers.
