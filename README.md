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
poetry shell # once in shell, you can run your normal python commands
poetry run python pomodoro_timer.py --d 25 --t work # if not in shell, then run poetry like so
poetry run python pomodoro_timer.py --d 5 --t b # 5 minute break
poetry run python pomodoro_timer.py --d 5 --t j # 5 minute journal session
poetry run pre-commit run --all-files
```

## Links
* [freesound.org - where I get my wav files](https://freesound.org/)
* [List of available keyboard keys](https://github.com/moses-palmer/pynput/blob/master/lib/pynput/keyboard/_darwin.py#L155)

## TODOs
* Add unit tests