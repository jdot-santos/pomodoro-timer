# Pomodoro Timer

## Features

- configurable pomodoro timer
- ability to pause the timer and continue using the F1 key
- 3 modes with 3 different sounds when complete: break, work, and journal

## Development

This uses [Poetry](https://python-poetry.org/) for dependency management

### Common Commands

```bash
poetry install # install dependencies
poetry run pomodoro-timer --d 25 --t work
poetry run pomodoro-timer --d 5 --t b # 5 minute break
poetry run pomodoro-timer --d 5 --t j # 5 minute journal session
poetry run pre-commit run --all-files
```

## Links
* [freesound.org - where I get my wav files](https://freesound.org/)
* [List of available keyboard keys](https://github.com/moses-palmer/pynput/blob/master/lib/pynput/keyboard/_darwin.py#L155)

## TODOs
* Add a CI pipeline (e.g. GitHub Actions) that runs on PRs: pytest, pre-commit
  (black/mypy/flake8/isort), and any other checks a PR should gate on
* Package the `.wav` files as real package data (`pyproject.toml` include +
  `importlib.resources`) so `pip install` works from outside a repo checkout,
  not just an editable install run from the repo root
* Add real end-to-end audio verification (manual QA checklist or automated
  smoke test) — every automated test stubs `simpleaudio.WaveObject`, so no
  test actually confirms a `.wav` file plays correctly