# Prompt: build the `/micro-break` skill

This file holds a prompt to paste into a Claude Code session **opened in the Obsidian vault**, not in this repo. It produces a skill that tracks which 60-second movement blocks were done on a given day.

It lives here because the skill is the other half of [#11](https://github.com/jdot-santos/pomodoro-timer/issues/11): the timer *suggests* a block, the skill *records* it. Keeping the prompt next to the issue keeps the two halves findable together.

**Scope decisions already made** — the prompt below encodes them, listed here so they are reviewable without reading the whole thing:

| Decision | Choice |
|---|---|
| Where state lives | A subsection of that day's journal entry |
| Block menu source | Parsed from `daily-movement.md` §1 at runtime, not hardcoded |
| Model | Checkbox per block, not a count of breaks |
| Commands | Mark a block done; show today's list. Nothing else |
| Not included | Suggesting the next block, weekly summaries, counts |

---

## The prompt

> Build me a Claude Code skill called `micro-break` that tracks which 60-second movement blocks I have done today.
>
> ### What it does
>
> Exactly two things:
>
> 1. **Mark a block done** — e.g. `/micro-break done C` checks off block C for today.
> 2. **Show today's list** — e.g. `/micro-break` with no arguments prints each block with its status, and which ones are still outstanding.
>
> Nothing else. Do not add block suggestions, weekly summaries, streak tracking, or counts. If I want those later I will ask.
>
> ### Where the blocks come from
>
> **Parse them from `src/02-areas/fitness/daily-movement.md`, section `## 1. Micro-Breaks — 60 seconds, every 30 min`.** There is a markdown table there with a `Block` column (`**A. Hands**`, `**B. Thumbs** 🔴`, and so on) and a `What` column describing the movements.
>
> Do not hardcode the list. That file is actively edited — it was renamed on 09-19 — and a hardcoded copy will silently drift from it.
>
> Strip the bold markers and any trailing emoji from the block names so `A. Hands` is what gets written. Keep the letter prefix; it is how I refer to them.
>
> **Block F is special.** The file says it "runs in parallel" and stacks with A–E rather than being a separate interruption. Include it in the list, but note in the output that it stacks rather than standing alone.
>
> If the table cannot be parsed — the heading moved, the columns changed — **say so and stop**. Do not fall back to a guessed list; a wrong list recorded as fact is worse than an error message.
>
> ### Where state is stored
>
> In that day's journal entry: `src/02-areas/journal/YYYY/<month-name-lowercase>/entries/MM-DD-YYYY.md`
>
> For example, 21 September 2026 is `src/02-areas/journal/2026/september/entries/09-21-2026.md`.
>
> Add a subsection directly beneath the existing `### 🔄 Daily Rituals` section:
>
> ```markdown
> #### 🤸 Micro-breaks
>
> - [x] A. Hands
> - [ ] B. Thumbs
> - [x] C. Neck & shoulders
> - [ ] D. Upper back
> - [ ] E. Lower body
> - [x] F. Eyes *(stacks with any block above)*
> ```
>
> **Create the subsection on first use of the day** if it is not there. Do not create the journal entry itself — if today's entry does not exist, say so and stop. Something else owns creating those, and a skill that invents journal files will eventually invent one with the wrong name.
>
> A new day means a new file, so the daily reset and the history both come for free. Do not build any reset logic, and do not write a separate log file.
>
> ### Conventions to follow
>
> Read `src/02-areas/journal/CLAUDE.md` first and match what it says. In particular:
>
> - Completed items elsewhere in these files use `- [x]` with a `✅` and `~~strikethrough~~`. For this checklist **use plain `- [x]`** — six short lines that change several times a day should stay scannable, not accumulate decoration.
> - Never reorder or reword the other entries in the file. Edit only the Micro-breaks subsection.
>
> ### Edge cases to handle
>
> - **Today's entry does not exist** → say so, stop, do not create it.
> - **The Micro-breaks subsection does not exist** → create it under Daily Rituals.
> - **A block letter I gave you is not in the table** → list the valid letters, do not guess which one I meant.
> - **A block is already marked done** → say so; do not error, do not double-mark.
> - **`daily-movement.md` has more or fewer blocks than last time** → the file is the source of truth. Add or drop rows to match, and preserve the checked state of any block that still exists.
>
> ### How I will use it
>
> My pomodoro timer prints a suggestion when a 20+ minute work session ends — something like `Block C: Neck & shoulders ... Log it: /micro-break done C`. So `done <letter>` is the common path and should be the fastest thing to type. Showing the list is the occasional path.
>
> ### Before you build it
>
> Read `src/02-areas/fitness/daily-movement.md` §1 and today's journal entry first, then tell me:
>
> 1. The exact block list you parsed, so I can confirm it matches what I expect
> 2. Where precisely you will insert the subsection, quoting the surrounding lines
> 3. Anything in the journal conventions that conflicts with the above
>
> Then build it.

---

## Notes for future-me

**Why the skill reads the vault rather than this repo owning the data.** The vault already has dated files, a Daily Rituals section, and an established checkbox convention. Duplicating that in a Python CLI would mean inventing a storage format, a date rollover, and a history file that the vault already provides for free.

**Why the timer stays stateless.** It would be easy to have the timer suggest a block you have not done today, but that couples it to this skill's storage and gives it a file format to keep in sync. Across ~16 breaks a day, weighted random is indistinguishable from true rotation. See #11.

**The gap neither half closes.** Nothing prompts you if you are not running a timer. Tracking tells you whether the habit is working; it does not make it work.
