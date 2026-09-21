# Pomodoro Timer

## Features

- configurable pomodoro timer
- ability to pause the timer and continue using the F1 key
- 3 modes with 3 different sounds when complete: break, work, and journal
- a 60-second micro-break reminder after work and journal sessions of 20 minutes
  or more — see `docs/specs/micro-break-suggestion.md` for why the floor exists

## Development

This uses [Poetry](https://python-poetry.org/) for dependency management

### Setup

```bash
poetry install        # install dependencies
poetry run pre-commit install   # install the git hooks — a fresh clone has none
```

Without that second command the hooks never run locally. CI still catches everything, but you find out after pushing instead of before.

### Common Commands

```bash
poetry run pomodoro-timer --d 25 --t work
poetry run pomodoro-timer --d 5 --t b # 5 minute break
poetry run pomodoro-timer --d 5 --t j # 5 minute journal session
```

### Checking lint, types, and tests locally

The toolchain is **Ruff** (lint + format, replacing black/flake8/isort) and **mypy** (types). Both run through pre-commit; versions are pinned in `.pre-commit-config.yaml`.

**Run everything — this is exactly what CI runs:**

```bash
poetry run pre-commit run --all-files
poetry run pytest -q
```

Clean output looks like:

```
ruff check...............................................................Passed
ruff format..............................................................Passed
mypy.....................................................................Passed
```

**Run one tool:**

```bash
poetry run pre-commit run ruff-check --all-files    # lint only
poetry run pre-commit run ruff-format --all-files   # formatting only
poetry run pre-commit run mypy --all-files          # types only
```

**Run one tool against one file** — use this while iterating:

```bash
poetry run pre-commit run mypy --files pomodoro_timer.py
poetry run pre-commit run ruff-check --files tests/test_pomodoro_timer.py
```

#### Three things that will confuse you six months from now

**1. `poetry run ruff` and `poetry run mypy` don't work.** Neither tool is a Poetry dependency — pre-commit installs them into its own isolated virtualenvs. Everything has to go through `pre-commit run`. This is a deliberate tradeoff: pre-commit owns tool versions so CI and local hooks can't drift apart. The reasoning is in `docs/specs/ci-pipeline-and-branch-protection.md`.

**2. "Failed" sometimes means "fixed it for you."** `ruff-check --fix` and `ruff-format` rewrite files in place, and pre-commit reports any hook that modified a file as **Failed**. Run it again and it passes. Check `git diff` to see what changed. On `git commit` this shows up as a failed first commit — re-`git add`, re-commit.

**3. The blake2 traceback is noise, not a failure.** `pytest` prints a `ValueError: unsupported hash type blake2s` from pyenv's OpenSSL before the results. Tests still pass. To silence it:

```bash
poetry run pytest -q 2>&1 | grep -v "blake2\|hashlib"
```

### CI

`.github/workflows/ci.yml` runs the same two commands on every PR and on pushes to `main`, on a macOS runner — `pyobjc` is macOS-only, so `poetry install` fails on Linux.

⚠️ The job is named `ci`, and **that exact string is the required status check on `main`**. Renaming the job — or adding a matrix, which turns it into `ci (3.12)` — blocks every PR until branch protection is updated to match.

## Links
* [freesound.org - where I get my wav files](https://freesound.org/)
* [List of available keyboard keys](https://github.com/moses-palmer/pynput/blob/master/lib/pynput/keyboard/_darwin.py#L155)

## TODOs

Tracked as [GitHub issues](https://github.com/jdot-santos/pomodoro-timer/issues).

* Package the `.wav` files as real package data (`pyproject.toml` include +
  `importlib.resources`) so `pip install` works from outside a repo checkout,
  not just an editable install run from the repo root
* Add real end-to-end audio verification (manual QA checklist or automated
  smoke test) — every automated test stubs `simpleaudio.WaveObject`, so no
  test actually confirms a `.wav` file plays correctly