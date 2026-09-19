---
status: implemented
created: 2026-08-04
---

# Spec: Resolve WAV Asset Paths Relative to Module Location

## Problem

`play_completed_sound()` in `pomodoro_timer.py` (`:67-81`) passes bare relative
filenames (e.g. `"loopdilla-drum-loop.wav"`) to
`simpleaudio.WaveObject.from_wave_file()`. That call resolves the path relative to the
process's **current working directory**, not relative to `pomodoro_timer.py`'s own
location on disk. The tool only works today because Poetry does an editable install for
local dev, so cwd (repo root, where you `poetry run pomodoro-timer` from) happens to
equal the module's location (also repo root, where the `.wav` files live). Running the
installed script from any other directory raises a file-not-found error.

Flagged in `ONBOARDING.md` under "Riskiest / most fragile parts" (`pomodoro_timer.py:69-73`)
as "the single biggest thing that'll bite a new user or anyone trying to
`pip install`/distribute this outside the repo."

## Inputs

- `timer_type`: one of `work`, `w`, `break`, `b`, `journal`, `j` (already validated
  upstream by `get_arguments()`'s `choices=`), or an unrecognized value.
- Implicit input: the process's current working directory at invocation time (this is
  exactly what's being removed as a dependency).

## Outputs

- Same behavior as today: the correct `.wav` file plays to completion
  (`play_obj.wait_done()` still blocks), for a given `timer_type`.
- The only change is *how* the file path is computed: relative to
  `pathlib.Path(__file__).resolve().parent` (the directory containing
  `pomodoro_timer.py`) instead of relative to `os.getcwd()`.

## Edge cases

- Invoking `poetry run pomodoro-timer --d 1 --t work` from the repo root — must keep
  working exactly as today (regression check).
- Invoking the installed `pomodoro-timer` script from a directory **other than** the
  repo root (e.g. `cd /tmp && poetry run pomodoro-timer --d 1 --t work` from within an
  activated env, or via an absolute path to the script) — must now succeed instead of
  raising a file-not-found error. This is the actual bug being fixed.
- Each of the three valid `timer_type` values (`work`/`w`, `break`/`b`, `journal`/`j`)
  must resolve to its correct, distinct `.wav` file — regression check on the
  mapping itself, not just the path resolution.
- Symlinked invocation (e.g. `pomodoro-timer` symlinked into a `bin/` directory) —
  `.resolve()` follows the symlink back to the real module location, so the wav files
  are still found relative to the actual repo checkout, not the symlink's directory.
  Intentional, not a regression.

## Failure modes

- Unrecognized `timer_type` reaching `play_completed_sound()` — unchanged:
  `logger.error("Unknown type used, will not play a sound")` then `raise SystemExit(0)`.
  (In practice `get_arguments()`'s `choices=` should prevent this from ever happening via
  the CLI, but `play_completed_sound()` is a standalone function and this fallback stays
  as-is.)
- `simpleaudio.WaveObject.from_wave_file()`'s exact accepted argument type
  (`str` vs. `pathlib.Path`) needs verification against the installed `simpleaudio`
  version — pass `str(path)` defensively rather than assuming `Path` is accepted
  directly.

## Known limitation: this does not solve `pip install` from PyPI

This refactor fixes "run from any directory **within a repo checkout**," not
"`pip install` and run from anywhere." The `.wav` files aren't declared as package data
in `pyproject.toml`, so a real (non-editable) PyPI-style install still wouldn't bundle
them — `Path(__file__).parent` would point at an installed-package directory with no
`.wav` files in it. Full fix for that is a separate, bigger change:
- declare the `.wav` files as included package data (`[tool.poetry.include]` or
  equivalent) in `pyproject.toml`, and
- switch from `sa.WaveObject.from_wave_file(path)` reading a filesystem path to
  `importlib.resources` reading the bundled package data.

Treating this as out of scope for the current refactor unless explicitly requested as a
follow-up.

## Non-goals

- **Not** changing the `timer_type` → filename mapping, the `if`/`elif` structure, or
  the unknown-type error handling — only how each filename is turned into a path.
- **Not** changing `play_completed_sound()`'s signature or any other function
  (`run_pomodoro`, `get_arguments`, `main`, `on_press`, `update_progress_bar`).

## Test coverage note

`play_completed_sound()` currently has zero test coverage (it was explicitly deferred
as real I/O in `docs/specs/happy-path-tests.md`'s non-goals). This change can be
verified either by:
- A new test that mocks `sa.WaveObject.from_wave_file` and asserts it's called with the
  correct absolute path for each `timer_type`, and/or
- A manual smoke test: run all three timer types and confirm each plays the correct
  sound, both from the repo root and from a different working directory.
