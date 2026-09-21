---
status: implemented
created: 2026-09-21
---

# Spec: Anchor the Countdown to the Wall Clock

Tracked as issue #5. Blocks the micro-break mode (#11).

## Problem

`run_pomodoro()` counts iterations, not time:

```python
for second in range(total_seconds, 0, -1):
    while paused:
        time.sleep(0.1)
    update_progress_bar(total_seconds - second, total_seconds)
    time.sleep(1)
```

Each pass sleeps a flat second and then does work — the pause check, the progress-bar render, the write to stdout. `time.sleep` guarantees a *minimum*, never an exact duration. So every iteration takes slightly more than a second and a "25 minute" session always runs long. Nothing anywhere measures elapsed time.

The error scales with duration. It is seconds on one pomodoro and minutes across an 8-hour micro-break loop, which is why #11 is blocked on this.

## Inputs

- `duration` — minutes, an integer from the CLI
- `timer_type` — one of `work`/`w`, `break`/`b`, `journal`/`j`
- The `paused` global, flipped from the keyboard listener thread at any moment

## Outputs

- A progress bar written to stdout roughly once per second
- A completion message chosen by `timer_type`
- A session whose **unpaused** duration matches `duration` minutes against the wall clock

## Behavior

### Time comes from a monotonic clock

Elapsed time derives from `time.monotonic()`, never from counting iterations. `monotonic` rather than `time.time()` because it cannot jump backwards — a wall-clock adjustment mid-session (NTP, DST, a manual clock change) must not lengthen or shorten a running timer.

Each tick recomputes remaining time from the clock. An individual tick arriving late is therefore self-correcting: the next render shows the true remaining time rather than compounding the lateness.

### Paused time does not count

A 25-minute session means 25 minutes of unpaused work. Pausing for 10 minutes pushes the end time out by 10 minutes.

Accumulated pause duration is tracked and subtracted from elapsed time. The alternative — counting paused time — was rejected because it makes the F1 pause nearly pointless: pausing would just mean missing part of your own session.

**No cap on pause length.** A session left paused stays paused indefinitely. Capping it was considered and rejected as a new configurable value and a new behavior to explain, for a case that resolves itself when the user returns.

### The progress bar reaches 100%

Progress derives from elapsed time, so the final render is 100% rather than the current `(total-1)/total`. This falls out of the rewrite — deriving progress from a clock rather than a loop index lands on 100% naturally, and writing extra code to *avoid* it would be preserving something that reads as a bug. Same family as the 0% off-by-one fixed in #3.

### Duration 0 exits immediately

`--duration 0` must return without rendering or sleeping, exactly as the empty `range(0, 0, -1)` does today. `TestMainEndToEnd` (`tests/test_pomodoro_timer.py:229`) depends on this to exercise real wiring without waiting, and that test must keep passing unchanged.

## Edge cases

- **A tick that takes longer than its interval** — a slow terminal, a suspended laptop, the process descheduled. Remaining time is recomputed from the clock, so the next render is correct rather than accumulating the delay.
- **Pause spanning the natural end of the session.** If the timer would have expired during a pause, it must not complete while still paused — the remaining time is owed once the user resumes.
- **Pause toggled between reading the flag and using it.** `paused` is written by the listener thread with no lock (#6). The loop must read it once per decision rather than twice, so a flip mid-tick cannot produce inconsistent bookkeeping within that tick.
- **Duration 0 with a pause already set** — must still exit immediately; there is no session to pause.
- **Very long durations.** `monotonic` is a float of seconds since an arbitrary point; precision is far beyond what a per-second display needs. No practical ceiling.
- **System sleep does not advance the timer.** On macOS `time.monotonic()` is backed by `mach_absolute_time`, which stops while the machine is asleep. Close the lid for an hour mid-session and the timer resumes owing the full remaining time rather than having expired.

  **This is intended.** A pomodoro measures time worked, and a closed laptop is not time worked. Documented rather than fixed because the alternative — `time.CLOCK_BOOTTIME` or similar, where available — would make a session silently expire while the user was away, which is worse.

  **It matters more for #11.** An all-day micro-break loop that spans a lunchtime lid-close will shift its whole remaining schedule by the length of the sleep, rather than resyncing to the wall clock. Whether a repeating timer should behave that way is a question for that issue, not this one.

## Failure modes

- **Using `time.time()` instead of `monotonic`.** An NTP correction or DST change mid-session would silently lengthen or shorten the timer. Monotonic is immune and costs nothing.
- **Busy-waiting while paused.** The current `while paused: time.sleep(0.1)` spins ten times a second for the whole pause. Preserved as-is here — replacing it with a `threading.Event` is #6 and does not belong in a timing fix.
- **Sleeping a full interval past the end.** A naive loop can overshoot by up to one tick. The final sleep must be clamped to the remaining time so the session ends on time rather than up to a second late.
- **Drift returning through a "catch-up" render loop.** If a tick is very late, rendering every missed intermediate frame would be wrong. The display shows current state; it is not an animation that owes frames.

## Verification

This is a behavior change with observable outputs, so unlike #10 it **does** get tests. Real tests, not toolchain checks.

Tests must not sleep for real. `time.monotonic` and `time.sleep` are both stubbed, so a "25 minute" session runs instantly and deterministically — the same stubbing convention already used for `simpleaudio.WaveObject` throughout the suite.

| Case | Asserts |
|---|---|
| Happy path | A session of N minutes ends after N minutes of monotonic time |
| Slow tick | A tick overrunning its interval does not extend total session length |
| Pause | Time spent paused is not counted toward the session |
| Pause past the end | A session cannot complete while still paused |
| Final render | The last progress bar shows 100% |
| Duration 0 | Returns immediately, renders nothing, sleeps not at all |
| Duration 0 while paused | Returns immediately; a pause flag cannot hold a zero-length session open |

**Measured against a real clock** (not the fake one), old implementation versus new:

| target | old | new |
|---|---|---|
| 3s | 3.010s (+0.0104) | 3.006s (+0.0059) |
| 5s | 5.015s (+0.0145) | 5.002s (+0.0016) |
| 10s | 10.035s (+0.0350) | 10.005s (+0.0054) |

Extrapolated to a 25-minute session: **+5.3s before, +0.8s after**. The old error scales with duration because each tick inherits the previous tick's lateness; the new one does not, because every tick recomputes from the clock.

## Out of scope

- Replacing the busy-wait with `threading.Event` — that is #6, and it needs #8's pause-path coverage first
- Any change to exit codes or `KeyboardInterrupt` handling — that is #4
- The micro-break repeat loop — that is #11, which this unblocks
- A cap on pause duration
