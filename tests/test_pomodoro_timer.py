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

import pytest

import pomodoro_timer


class TestUpdateProgressBar:
    def test_mid_progress_renders_partial_bar_and_percent(self, capsys):
        pomodoro_timer.update_progress_bar(progress=25, total=100)

        captured = capsys.readouterr()
        assert (
            captured.out
            == "\rProgress: [############                                      ] 25%"
        )

    def test_full_progress_renders_completely_filled_bar(self, capsys):
        pomodoro_timer.update_progress_bar(progress=100, total=100)

        captured = capsys.readouterr()
        assert (
            captured.out
            == "\rProgress: [##################################################] 100%"
        )

    def test_zero_progress_renders_empty_bar(self, capsys):
        pomodoro_timer.update_progress_bar(progress=0, total=100)

        captured = capsys.readouterr()
        assert (
            captured.out
            == "\rProgress: [                                                  ] 0%"
        )


class TestGetArguments:
    def test_long_form_flags_parse_work_session(self, monkeypatch):
        monkeypatch.setattr(
            "sys.argv", ["pomodoro-timer", "--duration", "25", "--type", "work"]
        )

        args = pomodoro_timer.get_arguments()

        assert args.duration == 25
        assert args.type == "work"

    def test_short_form_flags_parse_break_session(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["pomodoro-timer", "--d", "5", "--t", "b"])

        args = pomodoro_timer.get_arguments()

        assert args.duration == 5
        assert args.type == "b"


class TestRequiredArgumentValidation:
    def test_missing_duration_exits_with_usage_error(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["pomodoro-timer", "--type", "work"])

        with pytest.raises(SystemExit) as exc_info:
            pomodoro_timer.get_arguments()

        assert exc_info.value.code == 2
        assert "--duration" in capsys.readouterr().err

    def test_missing_type_exits_with_usage_error(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["pomodoro-timer", "--duration", "25"])

        with pytest.raises(SystemExit) as exc_info:
            pomodoro_timer.get_arguments()

        assert exc_info.value.code == 2
        assert "--type" in capsys.readouterr().err

    def test_missing_both_required_args_exits_with_usage_error(
        self, monkeypatch, capsys
    ):
        monkeypatch.setattr("sys.argv", ["pomodoro-timer"])

        with pytest.raises(SystemExit) as exc_info:
            pomodoro_timer.get_arguments()

        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "--duration" in err
        assert "--type" in err


class TestArgumentTypeValidation:
    def test_non_integer_duration_exits_with_usage_error(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv", ["pomodoro-timer", "--duration", "abc", "--type", "work"]
        )

        with pytest.raises(SystemExit) as exc_info:
            pomodoro_timer.get_arguments()

        assert exc_info.value.code == 2
        assert "--duration" in capsys.readouterr().err


def _stub_from_wave_file(monkeypatch):
    """Replace sa.WaveObject.from_wave_file with a no-op stub that records the
    path it was called with, instead of touching the real filesystem/audio
    device. Returns the list of recorded paths.
    """
    recorded_paths = []

    class _StubPlayObject:
        def wait_done(self):
            pass

    class _StubWaveObject:
        def play(self):
            return _StubPlayObject()

    def fake_from_wave_file(path):
        recorded_paths.append(path)
        return _StubWaveObject()

    monkeypatch.setattr(
        pomodoro_timer.sa.WaveObject, "from_wave_file", fake_from_wave_file
    )
    return recorded_paths


def _expected_wav_path(filename):
    module_dir = pathlib.Path(pomodoro_timer.__file__).resolve().parent
    return str(module_dir / filename)


class TestPlayCompletedSoundPathResolution:
    def test_work_type_resolves_absolute_path_to_correct_wav(self, monkeypatch):
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.play_completed_sound("work")

        assert recorded_paths == [_expected_wav_path("loopdilla-drum-loop.wav")]

    def test_break_type_resolves_absolute_path_to_correct_wav(self, monkeypatch):
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.play_completed_sound("break")

        assert recorded_paths == [_expected_wav_path("tabla_loop.wav")]

    def test_journal_type_resolves_absolute_path_to_correct_wav(self, monkeypatch):
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.play_completed_sound("journal")

        assert recorded_paths == [_expected_wav_path("gong-with-flute.wav")]

    def test_short_form_aliases_resolve_to_same_files_as_long_form(self, monkeypatch):
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
        self, monkeypatch, tmp_path
    ):
        recorded_paths = _stub_from_wave_file(monkeypatch)
        monkeypatch.chdir(tmp_path)

        pomodoro_timer.play_completed_sound("work")

        assert recorded_paths == [_expected_wav_path("loopdilla-drum-loop.wav")]


class TestPlayCompletedSoundUnknownType:
    def test_unknown_timer_type_logs_error_and_exits_without_playing_sound(
        self, monkeypatch, caplog
    ):
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

    def __init__(self, on_press=None):
        self.on_press = on_press

    def start(self):
        pass

    def stop(self):
        pass


class TestMainEndToEnd:
    def test_main_wires_args_through_run_pomodoro_to_play_completed_sound(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            "sys.argv", ["pomodoro-timer", "--duration", "0", "--type", "work"]
        )
        monkeypatch.setattr(pomodoro_timer.keyboard, "Listener", _StubKeyboardListener)
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.main()

        assert recorded_paths == [_expected_wav_path("loopdilla-drum-loop.wav")]

    def test_main_passes_break_type_through_to_correct_sound(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["pomodoro-timer", "--d", "0", "--t", "b"])
        monkeypatch.setattr(pomodoro_timer.keyboard, "Listener", _StubKeyboardListener)
        recorded_paths = _stub_from_wave_file(monkeypatch)

        pomodoro_timer.main()

        assert recorded_paths == [_expected_wav_path("tabla_loop.wav")]
