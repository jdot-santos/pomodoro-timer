---
status: implemented
created: 2026-08-03
---

# Spec: Required CLI Argument Validation

## Problem

`get_arguments()` in `pomodoro_timer.py` defines `--duration`/`--d` and `--type`/`--t`
without `required=True` and without defaults. If either is omitted, `argparse` happily
returns `None` for that field. `main()` passes that straight into `run_pomodoro()`,
which does `duration * 60` — `None * 60` raises an unhandled `TypeError` with a raw
Python traceback instead of a clear usage message.

Flagged in `ONBOARDING.md` under "Riskiest / most fragile parts" (`pomodoro_timer.py:93-105`).

## Inputs

- Command-line invocation of `pomodoro-timer` (or `python pomodoro_timer.py`) with any
  combination of `--duration`/`--d` and `--type`/`--t` present, absent, or malformed.

## Outputs

- **Both flags present and valid**: `get_arguments()` returns a `Namespace` with
  `duration` (int) and `type` (one of `work`, `w`, `break`, `b`, `journal`, `j`) — same
  as current behavior, unchanged.
- **Either flag missing**: `argparse` itself exits the process with status code `2` and
  prints a usage message to stderr identifying the missing argument (this is standard
  `argparse` behavior once `required=True` is set — no custom code needed beyond the
  flag).

## Edge cases

- Only `--duration` provided, `--type` missing → argparse error naming `--type` as
  required, exit code 2.
- Only `--type` provided, `--duration` missing → argparse error naming `--duration` as
  required, exit code 2.
- Neither provided → argparse error naming both as required, exit code 2.
- Both provided with valid values → parses normally (regression check — this must keep
  working exactly as today).
- `--type` provided with an invalid choice (e.g. `--type nap`) → already handled today
  by argparse's `choices=`; out of scope for this change but should keep working
  (regression check).

## Failure modes

- Missing required arg → `SystemExit(2)` raised by `argparse` internally, process exits
  with a usage message. This replaces the current failure mode (`None` propagating into
  `run_pomodoro`, raising `TypeError` deep in the call stack with a confusing
  traceback).
- No new exception handling is being added in application code — `required=True` moves
  the failure to argparse's existing, well-tested validation path.

## Non-goals

- Not adding defaults for `--duration`/`--type` (there's no sensible default duration or
  type for this tool — missing input should hard-fail, not silently pick a value).
- Not touching the `choices=` validation on `--type` (already correct).
- Not addressing any of the other risks listed in `ONBOARDING.md` (WAV path resolution,
  the `paused` global, platform lock-in, logger setup) — those are separate follow-ups.

## Pull Request

**Branch:** `js/add-tests` → `main`

### Title

Add pytest coverage and require --duration/--type CLI flags

### Description

This PR covers two related pieces of work done via TDD, bundled into one branch:

**1. Console script + initial pytest coverage**
- Registers `pomodoro-timer` as a Poetry script entry point (`pyproject.toml`) and
  updates the README usage examples to `poetry run pomodoro-timer` instead of
  `poetry shell` / `poetry run python pomodoro_timer.py`.
- Adds the first pytest coverage this repo has ever had: happy-path tests for the two
  pure-logic functions in `pomodoro_timer.py` — `update_progress_bar()` and
  `get_arguments()`.

**2. Require `--duration` and `--type` CLI flags**
- Fixes a bug flagged in `ONBOARDING.md`'s risk assessment: `--duration` and `--type`
  were not marked `required=True`, so omitting either let `None` flow into
  `run_pomodoro()`, raising an unhandled `TypeError` (`None * 60`) with a raw traceback
  instead of a usage message.
- Adds `required=True` to both flags in `get_arguments()` so argparse now fails fast
  with a proper usage error (exit code 2) when either is missing.
- Adds test coverage for: missing `--duration`, missing `--type`, missing both, and a
  non-integer `--duration` value (the last one was a pre-existing argparse behavior,
  confirmed via test rather than newly implemented).

Specs: [`docs/specs/happy-path-tests.md`](happy-path-tests.md),
[`docs/specs/required-args-validation.md`](required-args-validation.md)

### Test plan
- [x] `poetry run pytest tests/ -v` — all tests pass
- [x] `poetry run pre-commit run --all-files` — black/mypy/flake8/isort all pass
- [ ] Manual smoke test: `poetry run pomodoro-timer` with no flags exits with a usage
      error instead of crashing
