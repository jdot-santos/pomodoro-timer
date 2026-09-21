import argparse
import logging
import pathlib
import sys
import time
from typing import Any

import simpleaudio as sa
from pynput import keyboard

BASE_DIR = pathlib.Path(__file__).resolve().parent

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

        if timer_type == "work" or timer_type == "w":
            logger.info("\nTime's up! Take a break.\n")
        elif timer_type == "break" or timer_type == "b":
            logger.info("\nBreak is over, get back to work!\n")
        elif timer_type == "journal" or timer_type == "j":
            logger.info("\nJournaling complete\n")
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
