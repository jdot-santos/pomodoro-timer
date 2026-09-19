---
status: implemented
created: 2026-08-03
---

# Spec: Happy-Path Unit Tests for Pure Logic Functions

## Scope

This repo currently has **zero tests** (flagged as a TODO in README.md). This spec covers
the first slice of coverage: the two functions in `pomodoro_timer.py` that are pure
logic — no threads, no file I/O, no audio playback, no blocking sleeps. Everything else
(`run_pomodoro`, `play_completed_sound`, `main`) touches real I/O (`pynput` keyboard
listener, `simpleaudio` playback, `time.sleep`) and is explicitly out of scope for this
pass — it would need mocking and is a separate follow-up.

Functions under test:
- `update_progress_bar(progress, total, bar_length=50)`
- `get_arguments()`

Test runner: `pytest`, executed via `poetry run pytest` (pytest is already a dev
dependency in `pyproject.toml`). Tests live in a new `tests/` directory at repo root,
following standard `pytest` discovery (`test_*.py`).

## 1. `update_progress_bar(progress, total, bar_length=50)`

### Inputs
- `progress`: int, seconds elapsed so far (0 to `total`)
- `total`: int, total seconds for the session
- `bar_length`: int, width of the bar in characters (default 50)

### Outputs
- No return value. Writes a `\r`-prefixed progress string to `sys.stdout` and flushes it.
- Format: `\rProgress: [{'#' * filled}{padding}] {percent}%`
  - `filled = int(fraction * bar_length)` hashes
  - `percent = int(fraction * 100)`
  - `fraction = progress / total`

### Edge cases
- `progress == 0`: 0% bar, all padding, no `#` characters.
- `progress == total`: 100% bar, fully filled with `#`.
- `progress` at a mid-point (e.g. half of `total`): bar roughly half-filled; percent
  should truncate (not round) — e.g. 33.9% renders as `33%`.

### Failure modes
- `total == 0`: division by zero (`fraction = progress / total`). Not currently guarded
  in the implementation — this happy-path spec does **not** require fixing that, just
  documenting it as known-uncovered (see Step 4 review).

### Happy-path test coverage for this spec
- Given a normal in-progress value (e.g. `progress=25, total=100`), the printed output
  contains the correctly-filled bar and `25%`.
- Given `progress == total`, output shows a fully-filled bar and `100%`.
- Given `progress == 0`, output shows an empty bar and `0%`.

Tests will capture `sys.stdout` (via `capsys`) and assert on the exact written string.

## 2. `get_arguments()`

### Inputs
- Command-line arguments via `sys.argv`, parsed with `argparse`.
- Flags: `--duration` / `--d` (int), `--type` / `--t` (str, choices: `work`, `w`,
  `break`, `b`, `journal`, `j`).

### Outputs
- Returns an `argparse.Namespace` with `.duration` and `.type` populated from argv.

### Edge cases
- Short-form flags (`--d`, `--t`) parse identically to long-form (`--duration`, `--type`).
- Each valid `--type` choice (`work`, `w`, `break`, `b`, `journal`, `j`) is accepted.

### Failure modes
- Out of scope for this happy-path spec (invalid `--type` choice, missing required
  args causing `None` downstream) — these are known gaps noted in `ONBOARDING.md` and
  will need dedicated failure-mode tests in a follow-up, not this pass.

### Happy-path test coverage for this spec
- Given `--duration 25 --type work`, returns a namespace with `duration=25`,
  `type="work"`.
- Given the short-form equivalents `--d 5 --t b`, returns `duration=5`, `type="b"`.

Tests will monkeypatch `sys.argv` before calling `get_arguments()`.

## Out of scope (explicitly, for this spec)

- `run_pomodoro` (keyboard listener thread, real-time countdown, pause loop)
- `play_completed_sound` (file I/O, `simpleaudio` playback)
- `main` (entry point wiring the above together)
- Any failure-mode/edge-case tests for `get_arguments` beyond what's listed above
  (invalid type, missing duration, etc.)
