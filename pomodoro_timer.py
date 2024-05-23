import argparse
import time
import sys
import simpleaudio as sa

from pynput import keyboard

paused = False


def update_progress_bar(progress, total, bar_length=50):
    fraction = progress / total
    arrow = int(fraction * bar_length - 1) * '#' + '>'
    padding = (bar_length - len(arrow)) * ' '
    sys.stdout.write(f"\rProgress: [{'#' * int(fraction * bar_length)}{padding}] {int(fraction * 100)}%")
    sys.stdout.flush()


def on_press(key):
    global paused
    # list of keys can be found
    # https://github.com/moses-palmer/pynput/blob/master/lib/pynput/keyboard/_darwin.py#L155
    if key == keyboard.Key.f1:
        paused = not paused
        if paused:
            print("\nPaused. Press spacebar to resume.")
        else:
            print("\nResumed, grind on!")


def run_pomodoro(duration, timer_type):
    total_seconds = duration * 60
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    try:
        for second in range(total_seconds, 0, -1):
            while paused:
                time.sleep(0.1)
            update_progress_bar(total_seconds - second, total_seconds)
            time.sleep(1)
        listener.stop()

        if timer_type == "work" or timer_type == "w":
            sys.stdout.write("\nTime's up! Take a break.\n")
        elif timer_type == "break" or timer_type == "b":
            sys.stdout.write("\nBreak is over, get back to work!\n")
        elif timer_type == "journal" or timer_type == "j":
            sys.stdout.write("\nJournaling complete\n")
    except KeyboardInterrupt:
        listener.stop()
        sys.stdout.write('\nPomodoro interrupted.\n')
        sys.exit(0)


def play_completed_sound(timer_type):
    if timer_type == "work" or timer_type == "w":
        filename = "loopdilla-drum-loop.wav"
    elif timer_type == "break" or timer_type == "b":
        filename = "tabla_loop.wav"
    elif timer_type == "journal" or timer_type == "j":
        filename = "gong-with-flute.wav"
    else:
        sys.stdout.write("Unknown type used, will not play a sound")
        sys.exit(0)
    wave_obj = sa.WaveObject.from_wave_file(filename)

    play_obj = wave_obj.play()
    play_obj.wait_done()  # Wait until sound has finished playing


def main():
    args = get_arguments()
    print(f"Starting Pomodoro for {args.duration} minutes.")
    run_pomodoro(args.duration, args.type)
    play_completed_sound(args.type)


def get_arguments():
    parser = argparse.ArgumentParser(description="Pomodoro Timer")
    parser.add_argument('--duration', '--d', type=int, help='Duration of the Pomodoro session in minutes')
    parser.add_argument('--type', '--t', type=str, choices=["work", "w", "break", "b", "journal", "j"],
                        help='Type of timer. Options are "work" or "break"')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
