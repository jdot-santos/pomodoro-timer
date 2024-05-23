# Pomodoro Timer

## Features

- configurable pomodoro timer
- ability to pause the timer and continue using the Spacebar
- 3 modes with 3 different sounds when complete: break, work, and journal

## Development

This uses [Poetry](https://python-poetry.org/) for dependency management

### Common Commands

```bash
poetry install # install dependencies
poetry shell # once in shell, you can run your normal python commands
poetry run python pomodoro_timer.py --d 25 --t work # if not in shell, then run poetry like so
poetry run python pomodoro_timer.py --d 5 --t b # 5 minute break
poetry run python pomodoro_timer.py --d 5 --t j # 5 minute journal session
```

## Links
* [freesound.org - where I get my wav files](https://freesound.org/)

## TODOs
* Add proper logging
* Add unit tests
* Add pre-commit