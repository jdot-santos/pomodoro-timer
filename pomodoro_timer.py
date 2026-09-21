import argparse
import logging
import pathlib
import sys
import time
from typing import Any

import simpleaudio as sa
from pynput import keyboard

BASE_DIR = pathlib.Path(__file__).resolve().parent

# Micro-breaks are meant to land every 30 minutes, so a session shorter than
# this would nudge more often than intended -- and a prompt that fires when it
# shouldn't is a prompt you learn to skip.
MICRO_BREAK_MIN_MINUTES = 20
MICRO_BREAK_REMINDER = (
    "  60-second micro-break — stand up and move.\n  Log it:  /micro-break <letter>"
)

paused = False
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)

# Set a formatter that does not add a newline character
logger.addHandler(stream_handler)


def update_progress_bar(progress: float, total: float, bar_length: int = 50) -> None:
    fraction = progress / total
    filled = int(fraction * bar_length)
    padding = (bar_length - filled) * " "
    message = f"\rProgress: [{'#' * filled}{padding}] {int(fraction * 100)}%"
    sys.stdout.write(message)
    sys.stdout.flush()


def on_press(key: Any) -> None:
    global paused
    # list of keys can be found
    # https://github.com/moses-palmer/pynput/blob/master/lib/pynput/keyboard/_darwin.py#L155
    if key == keyboard.Key.f1:
        paused = not paused
        if paused:
            logger.info("\nPaused. Press F1 to resume.")
        else:
            logger.info("\nResumed, grind on!")


def run_pomodoro(duration: int, timer_type: str) -> None:
    total_seconds = duration * 60
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    try:
        # Elapsed time comes from the clock, never from counting iterations:
        # time.sleep only guarantees a minimum, so 1500 ticks of "one second"
        # always add up to more than 25 minutes. monotonic rather than time()
        # because it cannot jump backwards on an NTP or DST adjustment.
        started_at = time.monotonic()
        paused_seconds = 0.0

        while True:
            elapsed = time.monotonic() - started_at - paused_seconds
            remaining = total_seconds - elapsed
            # Expiry is checked before the pause below, on purpose: once the
            # time has been served it is owed, so a pause arriving at that
            # instant does not hold a finished session open.
            if remaining <= 0:
                break

            update_progress_bar(elapsed, total_seconds)

            if paused:
                paused_at = time.monotonic()
                while paused:
                    time.sleep(0.1)
                paused_seconds += time.monotonic() - paused_at
                continue

            # Clamp so the last tick lands on the end rather than past it.
            time.sleep(min(1.0, remaining))

        if total_seconds:
            update_progress_bar(total_seconds, total_seconds)
        listener.stop()

        # Who gets reminded is decided here, not branch by branch below: a
        # timer type added later reminds by default, and excluding one is an
        # edit to this condition rather than a line someone forgets to add.
        # Break timers are the exclusion -- a break timer *is* the break.
        reminder = (
            f"\n{MICRO_BREAK_REMINDER}\n"
            if duration >= MICRO_BREAK_MIN_MINUTES and timer_type not in ("break", "b")
            else ""
        )

        if timer_type == "work" or timer_type == "w":
            logger.info(f"\nTime's up! Take a break.\n{reminder}")
        elif timer_type == "break" or timer_type == "b":
            logger.info(f"\nBreak is over, get back to work!\n{reminder}")
        elif timer_type == "journal" or timer_type == "j":
            logger.info(f"\nJournaling complete\n{reminder}")
    except KeyboardInterrupt:
        listener.stop()
        logger.error("\nPomodoro interrupted.\n")
        raise SystemExit(0) from None


def play_completed_sound(timer_type: str) -> None:
    if timer_type == "work" or timer_type == "w":
        filename = "loopdilla-drum-loop.wav"
    elif timer_type == "break" or timer_type == "b":
        filename = "tabla_loop.wav"
    elif timer_type == "journal" or timer_type == "j":
        filename = "gong-with-flute.wav"
    else:
        logger.error("Unknown type used, will not play a sound")
        raise SystemExit(0)

    wave_obj = sa.WaveObject.from_wave_file(str(BASE_DIR / filename))

    play_obj = wave_obj.play()
    play_obj.wait_done()  # Wait until sound has finished playing


def main() -> None:
    args = get_arguments()
    logger.info(f"Starting Pomodoro for {args.duration} minutes.")
    run_pomodoro(args.duration, args.type)
    play_completed_sound(args.type)


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pomodoro Timer")
    parser.add_argument(
        "--duration",
        "--d",
        type=int,
        required=True,
        help="Duration of the Pomodoro session in minutes",
    )
    parser.add_argument(
        "--type",
        "--t",
        type=str,
        choices=["work", "w", "break", "b", "journal", "j"],
        required=True,
        help='Type of timer. Options are "work" or "break"',
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
