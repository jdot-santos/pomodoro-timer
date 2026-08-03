"""Happy-path tests for pure-logic functions in pomodoro_timer.py.

Scope per docs/specs/happy-path-tests.md: only update_progress_bar() and
get_arguments(). run_pomodoro, play_completed_sound, and main() touch real
I/O (keyboard listener, audio playback) and are out of scope here.
"""

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
