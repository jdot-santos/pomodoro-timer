"""Happy-path tests for pure-logic functions in pomodoro_timer.py.

Scope per docs/specs/happy-path-tests.md: only update_progress_bar() and
get_arguments(). run_pomodoro, play_completed_sound, and main() touch real
I/O (keyboard listener, audio playback) and are out of scope here.

TestRequiredArgumentValidation covers docs/specs/required-args-validation.md:
--duration and --type must be required argparse flags.

TestPlayCompletedSoundPathResolution covers docs/specs/wav-asset-path-resolution.md:
WAV asset paths must resolve relative to the module's own location, not the
process's current working directory.

TestMainEndToEnd exercises the real wiring of main() -> run_pomodoro() ->
play_completed_sound(), with only the true hardware/timing boundaries
stubbed (the pynput keyboard listener, audio playback) -- everything else
(argument parsing, the countdown loop, the type dispatch) runs for real.
"""

import logging
import pathlib
from collections.abc import Callable

import pytest

import pomodoro_timer


class TestUpdateProgressBar:
    def test_mid_progress_renders_partial_bar_and_percent(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pomodoro_timer.update_progress_bar(progress=25, total=100)

        captured = capsys.readouterr()
        assert (
            captured.out
            == "\rProgress: [############                                      ] 25%"
        )

    def test_full_progress_renders_completely_filled_bar(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pomodoro_timer.update_progress_bar(progress=100, total=100)

        captured = capsys.readouterr()
        assert (
            captured.out
            == "\rProgress: [##################################################] 100%"
        )

    def test_zero_progress_renders_empty_bar(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        pomodoro_timer.update_progress_bar(progress=0, total=100)

        captured = capsys.readouterr()
        assert (
            captured.out
            == "\rProgress: [                                                  ] 0%"
        )


class TestGetArguments:
    def test_long_form_flags_parse_work_session(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "sys.argv", ["pomodoro-timer", "--duration", "25", "--type", "work"]
        )

        args = pomodoro_timer.get_arguments()

        assert args.duration == 25
        assert args.type == "work"

    def test_short_form_flags_parse_break_session(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.argv", ["pomodoro-timer", "--d", "5", "--t", "b"])

        args = pomodoro_timer.get_arguments()

        assert args.duration == 5
        assert args.type == "b"


class TestRequiredArgumentValidation:
    def test_missing_duration_exits_with_usage_error(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.argv", ["pomodoro-timer", "--type", "work"])

        with pytest.raises(SystemExit) as exc_info:
            pomodoro_timer.get_arguments()

        assert exc_info.value.code == 2
        assert "--duration" in capsys.readouterr().err

    def test_missing_type_exits_with_usage_error(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.argv", ["pomodoro-timer", "--duration", "25"])

        with pytest.raises(SystemExit) as exc_info:
            pomodoro_timer.get_arguments()

        assert exc_info.value.code == 2
        assert "--type" in capsys.readouterr().err

    def test_missing_both_required_args_exits_with_usage_error(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr("sys.argv", ["pomodoro-timer"])

        with pytest.raises(SystemExit) as exc_info:
            pomodoro_timer.get_arguments()

        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "--duration" in err
        assert "--type" in err


class TestArgumentTypeValidation:
    def test_non_integer_duration_exits_with_usage_error(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            "sys.argv", ["pomodoro-timer", "--duration", "abc", "--type", "work"]
        )

        with pytest.raises(SystemExit) as exc_info:
            pomodoro_timer.get_arguments()

        assert exc_info.value.code == 2
        assert "--duration" in capsys.readouterr().err


def _stub_from_wave_file(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace sa.WaveObject.from_wave_file with a no-op stub that records the
    path it was called with, instead of touching the real filesystem/audio
    device. Returns the list of recorded paths.
    """
    recorded_paths: list[str] = []

    class _StubPlayObject:
        def wait_done(self) -> None:
            pass

    class _StubWaveObject:
        def play(self) -> "_StubPlayObject":
            return _StubPlayObject()

    def fake_from_wave_file(path: str) -> "_StubWaveObject":
        recorded_paths.append(path)
        return _StubWaveObject()

    monkeypatch.setattr(
        pomodoro_timer.sa.WaveObject, "from_wave_file", fake_from_wave_file
    )
    return recorded_paths


def _expected_wav_path(filename: str) -> str:
    module_dir = pathlib.Path(pomodoro_timer.__file__).resolve().parent
    return str(module_dir / filename)


class TestPlayCompletedSoundPathResolution:
    def test_work_type_resolves_absolute_path_to_correct_wav(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.play_completed_sound("work")

        assert recorded_paths == [_expected_wav_path("loopdilla-drum-loop.wav")]

    def test_break_type_resolves_absolute_path_to_correct_wav(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.play_completed_sound("break")

        assert recorded_paths == [_expected_wav_path("tabla_loop.wav")]

    def test_journal_type_resolves_absolute_path_to_correct_wav(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.play_completed_sound("journal")

        assert recorded_paths == [_expected_wav_path("gong-with-flute.wav")]

    def test_short_form_aliases_resolve_to_same_files_as_long_form(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.play_completed_sound("w")
        pomodoro_timer.play_completed_sound("b")
        pomodoro_timer.play_completed_sound("j")

        assert recorded_paths == [
            _expected_wav_path("loopdilla-drum-loop.wav"),
            _expected_wav_path("tabla_loop.wav"),
            _expected_wav_path("gong-with-flute.wav"),
        ]

    def test_resolves_correct_path_regardless_of_current_working_directory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        recorded_paths = _stub_from_wave_file(monkeypatch)
        monkeypatch.chdir(tmp_path)

        pomodoro_timer.play_completed_sound("work")

        assert recorded_paths == [_expected_wav_path("loopdilla-drum-loop.wav")]


class TestPlayCompletedSoundUnknownType:
    def test_unknown_timer_type_logs_error_and_exits_without_playing_sound(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        recorded_paths = _stub_from_wave_file(monkeypatch)
        caplog.set_level(logging.ERROR, logger="pomodoro_timer")

        with pytest.raises(SystemExit) as exc_info:
            pomodoro_timer.play_completed_sound("nap")

        assert exc_info.value.code == 0
        assert "Unknown type used" in caplog.text
        assert recorded_paths == []


class _StubKeyboardListener:
    """Stands in for pynput.keyboard.Listener so tests don't install a real
    OS-level keyboard hook (which also needs macOS Accessibility permission).
    """

    def __init__(self, on_press: object = None) -> None:
        self.on_press = on_press

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


class TestMainEndToEnd:
    def test_main_wires_args_through_run_pomodoro_to_play_completed_sound(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "sys.argv", ["pomodoro-timer", "--duration", "0", "--type", "work"]
        )
        monkeypatch.setattr(pomodoro_timer.keyboard, "Listener", _StubKeyboardListener)
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.main()

        assert recorded_paths == [_expected_wav_path("loopdilla-drum-loop.wav")]

    def test_main_passes_break_type_through_to_correct_sound(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.argv", ["pomodoro-timer", "--d", "0", "--t", "b"])
        monkeypatch.setattr(pomodoro_timer.keyboard, "Listener", _StubKeyboardListener)
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.main()

        assert recorded_paths == [_expected_wav_path("tabla_loop.wav")]


class _FakeClock:
    """Replaces time.monotonic and time.sleep so a 25-minute session runs
    instantly and deterministically.

    sleep() advances the clock instead of blocking. `overshoot` adds extra
    time to every sleep, simulating the real behaviour that time.sleep
    guarantees a *minimum* duration -- which is the whole cause of the drift
    in docs/specs/wall-clock-timer.md.

    on_sleep, if set, runs after each sleep and can flip pomodoro_timer.paused
    to simulate the keyboard listener thread.
    """

    def __init__(self, overshoot: float = 0.0, max_sleeps: int = 100_000) -> None:
        self.now = 1000.0
        self.start = 1000.0
        self.overshoot = overshoot
        self.sleeps: list[float] = []
        self.max_sleeps = max_sleeps
        self.on_sleep: Callable[[_FakeClock], None] | None = None
        self.pause_started = 0.0

    @property
    def elapsed(self) -> float:
        return self.now - self.start

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        # Guard: a wrong implementation can loop forever, and a hung test
        # suite is far worse to debug than a failing assertion.
        assert len(self.sleeps) <= self.max_sleeps, (
            f"exceeded {self.max_sleeps} sleeps -- implementation is not terminating"
        )
        self.now += seconds + self.overshoot
        if self.on_sleep is not None:
            self.on_sleep(self)


def _install_clock(monkeypatch: pytest.MonkeyPatch, clock: _FakeClock) -> None:
    """Point the module at the fake clock and stub the keyboard listener."""
    monkeypatch.setattr(pomodoro_timer.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(pomodoro_timer.time, "sleep", clock.sleep)
    monkeypatch.setattr(pomodoro_timer.keyboard, "Listener", _StubKeyboardListener)
    monkeypatch.setattr(pomodoro_timer, "paused", False)


def _pause_once(at: float, for_seconds: float) -> Callable[[_FakeClock], None]:
    """Build an on_sleep hook that pauses exactly once.

    Pauses when the session reaches `at` seconds elapsed, holds for
    `for_seconds`, then releases and never fires again. The one-shot guard
    matters: without it the hook re-pauses the moment it releases.
    """
    started: list[float] = []
    done: list[bool] = []

    def hook(clock: _FakeClock) -> None:
        if done:
            return
        if not started:
            if clock.elapsed >= at:
                pomodoro_timer.paused = True
                started.append(clock.now)
        elif clock.now - started[0] >= for_seconds:
            pomodoro_timer.paused = False
            done.append(True)

    return hook


class TestRunPomodoroTiming:
    """Covers docs/specs/wall-clock-timer.md -- the countdown must measure
    elapsed time rather than counting iterations.
    """

    def test_session_lasts_the_requested_duration(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        clock = _FakeClock()
        _install_clock(monkeypatch, clock)

        pomodoro_timer.run_pomodoro(25, "work")

        assert clock.elapsed == pytest.approx(25 * 60, abs=1)

    def test_slow_ticks_do_not_extend_the_session(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Every sleep overruns by 100ms, as a real time.sleep does by some
        # margin. Counting iterations turns 1500 ticks into 1650 seconds;
        # measuring elapsed time still ends at 1500.
        clock = _FakeClock(overshoot=0.1)
        _install_clock(monkeypatch, clock)

        pomodoro_timer.run_pomodoro(25, "work")

        assert clock.elapsed == pytest.approx(25 * 60, abs=1)

    def test_final_progress_bar_reaches_one_hundred_percent(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        clock = _FakeClock()
        _install_clock(monkeypatch, clock)

        pomodoro_timer.run_pomodoro(1, "work")

        bars = [
            line for line in capsys.readouterr().out.split("\r") if "Progress" in line
        ]
        assert bars, "expected at least one progress bar render"
        assert "100%" in bars[-1]

    def test_paused_time_does_not_count_toward_the_session(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        clock = _FakeClock()
        _install_clock(monkeypatch, clock)

        clock.on_sleep = _pause_once(at=60.0, for_seconds=10.0)

        pomodoro_timer.run_pomodoro(5, "work")

        # 5 minutes of work plus a 10-second pause that should not be counted.
        assert clock.elapsed == pytest.approx(5 * 60 + 10, abs=1.5)

    def test_session_cannot_complete_while_still_paused(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        clock = _FakeClock()
        _install_clock(monkeypatch, clock)

        # Pause with 10 seconds left and hold well past the natural end.
        clock.on_sleep = _pause_once(at=50.0, for_seconds=60.0)

        pomodoro_timer.run_pomodoro(1, "work")

        # A 60-second session paused for 60 seconds takes about 120 seconds,
        # and must not have completed at the 60-second mark.
        assert clock.elapsed == pytest.approx(120, abs=2)

    def test_zero_duration_returns_without_sleeping_or_rendering(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        clock = _FakeClock()
        _install_clock(monkeypatch, clock)

        pomodoro_timer.run_pomodoro(0, "work")

        assert clock.sleeps == []
        assert clock.elapsed == 0
        assert "Progress" not in capsys.readouterr().out

    def test_zero_duration_exits_immediately_even_if_already_paused(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # There is no session to pause, so a pause flag set before the call
        # must not hold a zero-length session open.
        clock = _FakeClock()
        _install_clock(monkeypatch, clock)
        monkeypatch.setattr(pomodoro_timer, "paused", True)

        pomodoro_timer.run_pomodoro(0, "work")

        assert clock.sleeps == []
        assert clock.elapsed == 0
        assert "Progress" not in capsys.readouterr().out
