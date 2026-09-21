---
status: implemented
created: 2026-09-21
---

# Spec: Remind to Take a Micro-Break on Timer Completion

Tracked as issue #11. The issue's "name a specific block" design is deliberately narrowed here — see **Why no specific block**.

## Problem

When a `work` or `journal` timer finishes, the program prints a generic message ("Time's up! Take a break.") at exactly the moment it has the user's full attention — the 30-minute mark that `daily-movement.md` §1 says a 60-second movement block belongs on. "Take a break" reads as *stop working*, not *stand up and move for 60 seconds*, so the moment passes unused.

## Solution

Add a fixed micro-break reminder to the existing completion message on `work` and `journal` timers of 20+ minutes. No block selection, no randomness, no persisted state, no scheduler.

## Inputs

- `duration` (int, minutes) — already parsed from `--duration`
- `timer_type` (str) — already parsed from `--type`; one of `work`, `w`, `break`, `b`, `journal`, `j`

No files are read. No environment is consulted. Nothing is random.

## Outputs

On a `work` timer of 20+ minutes:

```
Time's up! Take a break.

  60-second micro-break — stand up and move.
  Log it:  /micro-break <letter>
```

On a `journal` timer of 20+ minutes, the first line is the existing "Journaling complete" instead. The two reminder lines are identical.

In every other case, output is byte-for-byte what it is today.

The reminder text is one module-level constant. Deciding *which* block to do is the user's, in the moment; `/micro-break` (in the vault) lists the blocks and records the answer; it takes the bare letter.

## Why no specific block

Naming a block would mean the timer holds a copy of the A–F table from `daily-movement.md` §1, and a weighted random picker over it. That copy lives in a different repo from the file it was transcribed from, so it goes stale silently, and it buys rotation the user can do themselves by looking at the block menu they already keep. The timer's job at this moment is to interrupt stillness — a reminder does that as well as a named block, with no table to maintain and no randomness to test.

## The 20-minute floor

| Invocation | Reminder? |
|---|---|
| `--d 30 --t work` | yes |
| `--d 25 --t work` | yes |
| `--d 20 --t work` | yes (boundary is inclusive) |
| `--d 19 --t work` | no |
| `--d 15 --t work` | no |
| `--d 5 --t work` | no |
| `--d 30 --t break` | no |
| `--d 30 --t journal` | yes |

Micro-breaks are meant to land every 30 minutes. Without a floor, `--d 15` nudges twice as often as intended and `--d 5` is noise — and a prompt that fires when it shouldn't is a prompt you learn to skip.

The exclusion of `break` lives in the same condition as the threshold, not in the per-type message branches: a timer type added later reminds by default, and silencing one is a deliberate edit rather than a line someone forgets to add.

One threshold constant. Rejected: always reminding (noise); a `--no-break` flag (a flag you must remember on exactly the runs where you least want to think).

## Edge cases

| Case | Behavior |
|---|---|
| `--d 20` exactly | reminds (inclusive boundary) |
| `--d 0 --t work` | silent (below floor) — keeps `TestMainEndToEnd` output unchanged |
| `break`/`b` of any duration | never reminds — a break timer *is* the break |
| Unknown timer type | silent; existing behavior (no completion message, then `play_completed_sound` errors) is unchanged |
| `KeyboardInterrupt` mid-session | silent; the interrupt path is untouched |

## Failure modes

| Failure | Response |
|---|---|
| Reminder code raises | Would swallow the completion message and the `.wav`. Mitigated by keeping it a constant and one comparison — no I/O, no parsing, no new imports |
| Terminal cannot render `—` | Garbled dash in one line. Accepted: this is a macOS/UTF-8 terminal tool and the existing codebase already emits non-ASCII progress output |

## Out of scope

- Naming, rotating, or choosing a block (see above)
- The all-day repeat loop, launchd, background running (the original #11 scope)
- `osascript` notification banners
- Snooze, skip, or any interaction
- Timing the 60-second break itself
- Writing any tracking state — that is the `/micro-break` skill's job, and it lives in the vault

## Acceptance criteria

- [ ] A `work` session of 20+ minutes prints the micro-break reminder after "Time's up! Take a break."
- [ ] A `journal` session of 20+ minutes prints it after "Journaling complete"
- [ ] Sessions under 20 minutes print the existing message unchanged
- [ ] `break` sessions never remind
- [ ] The timer reads and writes no state, and uses no randomness
- [ ] Existing completion messages and the `.wav` playback are unchanged
