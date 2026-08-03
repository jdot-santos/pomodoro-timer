"""Happy-path tests for pure-logic functions in pomodoro_timer.py.

Scope per docs/specs/happy-path-tests.md: only update_progress_bar() and
get_arguments(). run_pomodoro, play_completed_sound, and main() touch real
I/O (keyboard listener, audio playback) and are out of scope here.

TestRequiredArgumentValidation covers docs/specs/required-args-validation.md:
--duration and --type must be required argparse flags.
"""

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
            == "\rProgress: [                                                 ] 0%"
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
