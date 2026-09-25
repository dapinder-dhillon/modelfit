from __future__ import annotations

from pathlib import Path

import pytest

from modelfit import advice_report, advisor
from modelfit.cli import _print_compact, _print_explain, _print_short, main

_TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"

# Blind-spot cases from more than one angle: the classic zero-signal task, and
# one where a strong signal ALSO happens to fire alongside it, to make sure the
# warning isn't only reachable through the single most obvious path.
_BLIND_SPOT_TEXTS = [
    "Write a hello world script.",
    "Add a .gitignore file for a Node project.",
]


def test_every_view_shows_the_blind_spot_when_the_estimate_has_it(capsys):
    """A flag on the Estimate object proves nothing about what a person actually
    sees -- each rendering path has to be checked directly, not assumed to
    inherit the flag correctly. (This is exactly the kind of gap that let an
    earlier --short build ship without the warning at all.)"""
    for text in _BLIND_SPOT_TEXTS:
        est = advisor.estimate(text)
        assert est.hidden_knowledge_warning, f"{text!r} was expected to hit the blind spot"

        _print_compact(est)
        compact_out = capsys.readouterr().out
        assert "BLIND SPOT" in compact_out, f"compact view dropped the warning for {text!r}"

        _print_short(est)
        short_out = capsys.readouterr().out
        assert "blind spot" in short_out, f"--short dropped the warning for {text!r}"

        _print_explain(est)
        explain_out = capsys.readouterr().out
        assert "blind spot" in explain_out, f"--explain dropped the warning for {text!r}"

        report_text = advice_report.render(est)
        assert "Blind spot" in report_text, f"the .md report dropped the warning for {text!r}"


def test_unknown_model_exits_with_clear_error(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["run", "--mock", "--models", "bogus-model", "--no-cache"])
    assert exc.value.code == 2
    assert "unknown model" in capsys.readouterr().err


def test_unknown_effort_exits_with_clear_error(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["run", "--mock", "--efforts", "medium", "--no-cache"])
    assert exc.value.code == 2
    assert "unknown effort" in capsys.readouterr().err


def test_missing_tasks_dir_exits_with_clear_error(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["run", "--mock", "--no-cache", "--tasks", str(tmp_path / "nope")])
    assert exc.value.code == 2
    assert "no *.yaml task files found" in capsys.readouterr().err


def test_advise_default_leads_with_the_action(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELFIT_HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    rc = main(["advise", "Fix this retry helper so it never sleeps after the final attempt."])
    out, err = capsys.readouterr()
    assert rc == 0
    assert "START" in out
    assert "claude-sonnet-5 / low effort" in out
    assert "gpt-6-sol / low effort" in out
    assert "IF NEEDED" in out
    assert "SIGNAL" in out
    assert "WHY" in out
    # the classifier's raw scores/full prose are debug detail, not the default
    assert "scores" not in out
    assert "why (signals that fired)" not in out
    # bookkeeping is stderr, not stdout, so piping `advise "..." > file` stays clean
    assert "Wrote" in err
    assert "Wrote" not in out
    assert list((tmp_path / "reports").glob("advice_*.md"))
    assert (tmp_path / "home" / "history.json").exists()


def test_advise_on_plain_wording_warns_instead_of_claiming_easy(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELFIT_HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    rc = main(["advise", "Add a .gitignore file for a Node project.", "--outcome", "pass"])
    out, err = capsys.readouterr()
    assert rc == 0
    assert "SIGNAL" in out and "low" in out
    assert "BLIND SPOT" in out
    assert "Recorded outcome: pass" in err


def test_advise_short_is_one_line(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELFIT_HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    task = "Fix this retry helper so it never sleeps after the final attempt."
    rc = main(["advise", task, "--short"])
    out = capsys.readouterr().out
    assert rc == 0
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 1
    assert "claude-sonnet-5 or gpt-6-sol @ low" in lines[0]
    assert "[high]" in lines[0]


def test_advise_shows_every_vendor_by_default_and_one_with_vendor(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELFIT_HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    task = "Review this IAM policy and explain the security risks."

    assert main(["advise", task]) == 0
    both = capsys.readouterr().out
    assert "claude-sonnet-5 / high effort" in both
    assert "gpt-6-sol / high effort" in both
    assert "claude-opus-5-5 (Anthropic) or gpt-6-astra (OpenAI)" in both

    assert main(["advise", task, "--vendor", "openai"]) == 0
    one = capsys.readouterr().out
    assert "gpt-6-sol / high effort" in one
    assert "switch to gpt-6-astra, same high effort" in one
    assert "claude" not in one


_ONE_PER_PATH = [
    "Add a .gitignore file for a Node project.",  # blind spot; runner-up MODEL
    "Fix this retry helper so it never sleeps after the final attempt.",  # EFFORT
    "Review this IAM policy and explain the security risks.",  # MODEL; escalation names a tier
    "Review this configuration.",  # hedged MODEL
    "Refactor the entire codebase so no module imports the legacy client, then update all "
    "call sites and the tests.",  # BOTH
]


@pytest.mark.parametrize("vendor", [None, "anthropic", "openai"])
def test_no_view_leaks_an_unfilled_tier_placeholder(vendor, capsys):
    """Plans name a tier as `{large}`; every rendering path must fill it in.
    Checked per view for the same reason as the blind-spot test above."""
    for text in _ONE_PER_PATH:
        est = advisor.estimate(text)
        _print_compact(est, vendor)
        _print_short(est, vendor)
        _print_explain(est, vendor)
        rendered = capsys.readouterr().out + advice_report.render(est, vendor=vendor)
        assert "{" not in rendered, f"unfilled placeholder for {text!r} (vendor={vendor})"


def test_advise_explain_has_the_full_breakdown(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELFIT_HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    task = "Fix this retry helper so it never sleeps after the final attempt."
    rc = main(["advise", task, "--explain"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "why (signals that fired)" in out
    assert "start here" in out
    assert "scores" in out
    assert "baseline 1 + signals" in out  # explains the score so it's checkable, not just asserted


def test_advise_short_and_explain_are_mutually_exclusive():
    with pytest.raises(SystemExit) as exc:
        main(["advise", "x", "--short", "--explain"])
    assert exc.value.code == 2


def test_lessons_reads_only_recorded_outcomes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MODELFIT_HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    main(["advise", "Optimise this SQL query."])
    assert main(["lessons"]) == 0
    assert "0 outcomes recorded" in capsys.readouterr().out


def test_eval_prints_both_splits(capsys):
    assert main(["eval"]) == 0
    out = capsys.readouterr().out
    assert "clear" in out and "adversarial" in out
    assert "misses" in out


def test_valid_mock_run_writes_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = main(
        [
            "run",
            "--mock",
            "--no-cache",
            "--models",
            "claude-haiku-4-5",
            "--efforts",
            "off",
            "--trials",
            "1",
            "--tasks",
            str(_TASKS_DIR),
            "--out",
            str(tmp_path / "out"),
        ]
    )
    assert rc == 0
    assert (tmp_path / "out" / "report.md").exists()
    assert (tmp_path / "out" / "results.csv").exists()
