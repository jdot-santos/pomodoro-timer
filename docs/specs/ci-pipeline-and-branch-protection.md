---
status: implemented
created: 2026-09-18
---

# Spec: CI Pipeline and Branch Protection

Tracked as issue #10.

## Problem

Nothing gates a merge into `main`. There is no `.github/` directory, no workflow, and `main` has no branch protection — `gh api .../branches/main/protection` returns 404 "Branch not protected". Anyone with push access can push directly to `main` with failing tests and unformatted code.

The lint tooling that exists runs only on `git commit`, locally, via pre-commit. `--no-verify` bypasses it, and a fresh clone has no hooks installed at all until someone runs `pre-commit install`.

## Inputs

Three triggers, none of them a function call:

- **A pull request opened or updated against `main`** — runs lint, type check, and tests
- **A push to `main`** — same checks, as a backstop for anything that lands another way
- **A direct `git push` to `main`** — must be rejected by GitHub before any code runs

## Outputs

- A required status check on every PR that must pass before merge
- `main` rejects direct pushes **from non-admins**; changes land through a PR. See Branch protection for why the owner is exempt and what that actually permits.
- One lint toolchain (Ruff) replacing three (black, flake8, isort)
- mypy configured rather than running permissive defaults
- A documented `pre-commit install` step for fresh clones

## Behavior

### Lint stack

Ruff replaces black, flake8, and isort. `ruff format` is black-compatible, so formatting output should not change meaningfully.

```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RUF"]
```

mypy stays, configured to moderate strictness:

```toml
[tool.mypy]
python_version = "3.12"
disallow_untyped_defs = true
warn_return_any = true
warn_unused_ignores = true

[[tool.mypy.overrides]]
module = ["pynput.*", "simpleaudio.*"]
ignore_missing_imports = true
```

**mypy checks `tests/` as well as the module**, so the annotation work is wider than the module alone:

| Location | Functions annotated |
|---|---|
| `pomodoro_timer.py` | 6 |
| `tests/test_pomodoro_timer.py` | 17 test functions + 4 helpers (2 module-level, 2 stub methods) |

Test fixtures get explicit types — `pytest.CaptureFixture[str]`, `pytest.MonkeyPatch`, `pytest.LogCaptureFixture`, `pathlib.Path` for `tmp_path`.

**The alternative, not taken:** an override exempting `tests/` from `disallow_untyped_defs`. Common practice, and it would have saved the 17 annotations — but exempting the test suite from type checking is backwards in a repo whose main quality asset is that suite. The fixture types also document what each test actually stubs, which matters in a file that stubs `simpleaudio` in five places. **This decision is provisional and gets revisited** — see the Tooling decisions section.

Annotations push several test signatures past 88 characters; `ruff format` wraps them automatically.

### CI

Runs on `macos-latest`. `pyproject.toml` declares `pyobjc` unconditionally and pyobjc is a macOS-only Objective-C bridge, so `poetry install` fails on Ubuntu. macOS also matches where the app actually runs, and Actions minutes are free on public repos.

CI invokes `pre-commit run --all-files` rather than calling ruff and mypy directly, so `.pre-commit-config.yaml` remains the single source of truth for tool versions. Pinning them again in the workflow is how CI and local hooks drift apart.

One job, explicitly `name: ci`. That string is the required status check on `main`, so it is pinned rather than inherited from the job key, and carries a comment saying so. See failure modes for why.

### Branch protection

Require a PR and a passing CI check. Zero required approvals, admins exempt.

Zero approvals because there is one contributor — requiring one would make `main` unmergeable. Admins exempt so a red check cannot lock the only maintainer out of fixing whatever made it red.

**What "admins exempt" actually permits, verified by testing it 2026-09-18:** the repo owner bypasses the protection rule entirely, including pushing directly to `main` with no PR and no CI run. GitHub prints the rejection reasons and allows the push anyway. This is broader than "can override a red check" — it is a full bypass, and it is the accepted cost of keeping an escape hatch on a single-maintainer repo.

**Force-pushing is blocked regardless.** `allow_force_pushes` is a separate setting from `enforce_admins`, and it applies to the owner too. History on `main` cannot be rewritten by anyone without first changing that setting. Branch deletion is blocked on the same basis.

Applied state, confirmed via the API:

```
required checks : ci        (only — not the dynamic update-pip-graph context)
strict          : true
approvals       : 0
enforce_admins  : false
force_pushes    : false
deletions       : false
```

## Tooling decisions

### Keep pre-commit

Once CI is required, pre-commit stops being a gate and becomes a convenience — `--no-verify` skips it, a fresh clone has no hooks until someone runs `pre-commit install`, and CI catches everything regardless. Keeping it anyway, for two reasons:

- **Speed.** A formatting slip caught in ~2 seconds locally beats a ~2-minute CI round trip on `macos-latest`, a push, and a status flip.
- **It auto-fixes.** `ruff --fix` and `ruff-format` rewrite the files. CI can only report.

Accepted costs:

- The **rewrite-on-commit dance** — a hook rewrites files, the commit fails, you re-`git add` and re-commit. Real friction on every commit that touches formatting.
- **Tools that only exist inside pre-commit's venvs.** `poetry run mypy` fails; use `pre-commit run mypy --files <path>` instead.
- **Two dependency systems** — tool versions in `.pre-commit-config.yaml`, app versions in `pyproject.toml`.

**The alternative, rejected for now:** drop pre-commit, add `ruff` and `mypy` to `[tool.poetry.group.dev.dependencies]`, and have CI call them directly. That gives one dependency system, one fewer config file, no failed-commit dance, and a working `poetry run mypy` — at the cost of no pre-push feedback.

**Revisit when:** Ruff format-on-save is configured in the editor. At that point pre-commit's remaining value mostly evaporates and dropping it becomes the smaller setup.

### Annotate the tests rather than exempt them

mypy walks `tests/` too, which this spec did not originally account for. Annotating the suite rather than exempting it from `disallow_untyped_defs` — see the Lint stack section for the reasoning and the counts.

**This is provisional.** It was decided mid-implementation to keep the toolchain moving, not from a considered position on how test suites should be typed. There is no issue tracking it yet.

**Revisit when:** the fixture annotations start costing more than they explain — a new fixture whose type is awkward to name, or a signature that wraps to three lines to accommodate it. Either is the signal that an exemption was the better call.

### Drop the dead mypy dependency

`.pre-commit-config.yaml` pins `additional_dependencies: ['types-PyYAML']` on the mypy hook. Nothing in this repo imports YAML — it came from a template. Remove it during the Ruff migration.

### Pinned versions

`pre-commit autoupdate` resolved ruff to **v0.16.8** and mypy to **v2.3.1**, replacing the 2023-era pins (black 23.3.0, flake8 6.0.0, isort 5.12.0, mypy v1.2.0).

## Edge cases

- **Ruff rewrites files on its first run.** Expect a failed first commit, re-`git add`, re-commit — the same dance black does today.
- **Ruff and black may disagree on specific formatting.** `ruff format` is black-compatible but not byte-identical across all constructs. Any diff beyond whitespace normalization should be reviewed, not accepted blindly. *Outcome: no disagreement — `ruff format` passed on the existing code with no reformatting.*
- **The new rule set surfaces code changes, not just formatting.** `select` includes `B` (bugbear), which is broader than flake8's defaults were. It flagged `B904` on the `KeyboardInterrupt` handler — a `raise` inside an `except` with no `from`. Resolved with `raise SystemExit(0) from None` because the lint stack cannot go green otherwise, but **accepting a linter's default is not the same as deciding the behavior**. That line's semantics are now an open question in #4.
- **`pynput` and `simpleaudio` ship no type stubs.** Without the overrides, mypy errors on the imports themselves before reaching any real check.
- **mypy is not a Poetry dev dependency.** It exists only inside pre-commit's isolated environment, so `poetry run mypy` fails. Running it via pre-commit works; running it ad hoc does not.
- **`argparse.Namespace` attributes are `Any`.** Annotating `get_arguments() -> argparse.Namespace` does not make attribute access type-safe, so type checking will not catch argument-shaped bugs downstream of it. This is a known ceiling, not a defect in the config.

## Failure modes

- **Requiring a status check that has never run blocks every merge.** GitHub can only require a context it has already observed. Protection must be applied *after* CI runs green at least once, never before.
- **Renaming the CI job breaks protection.** The job name is the required context, so renaming it means no check reports and every PR blocks. Not silent — the PR sits at "Expected — waiting for status to be reported" — but confusing enough to cost real time. Three guards, in order of when they apply:
  1. **Set `name:` explicitly and comment it.** Pinning the displayed name decouples it from the job key, so the key can change freely:
     ```yaml
     jobs:
       ci:
         # ⚠️ "ci" is the required status check on main.
         # Renaming this blocks every PR until branch protection is updated.
         name: ci
         runs-on: macos-latest
     ```
  2. **A matrix renames the context without touching the job name.** Adding one turns `ci` into `ci (3.12)`; changing or removing it renames the context again. Same failure, sneakier cause. Out of scope here, but the reason to re-check protection if a matrix is ever added.
  3. **Adopt an aggregate job when CI becomes more than one job.** A single job named `ci` with `needs: [lint, test]` becomes the only required context, letting the real jobs be renamed or split freely. Premature while there is one job. When adopted it needs `if: always()` plus explicit `needs.<job>.result` checks — without them a skipped dependency reports success and the gate passes everything, which is worse than the failure it prevents.
- **The blake2 warning looks like a failure.** `pytest` prints a `ValueError: unsupported hash type blake2s` traceback from pyenv's OpenSSL before results. It is local noise and may not appear on a clean runner — but if it does, green CI logs will look alarming.
- **Enforcing on admins removes the escape hatch.** Deliberately not enabled. A red check would otherwise require unprotecting the branch to fix anything.
- **Annotation may surface a real type error.** If mypy flags genuine incorrect behavior rather than a missing annotation, that is a bug, and it gets its own failing test and fix rather than an annotation papering over it. *Outcome: it did not. All 27 mypy findings were missing annotations. The one real code finding came from Ruff, not mypy — see edge cases.*

## Verification

There are no new pytest tests. Every part of this spec is verified by the toolchain itself:

| Part | Verified by |
|---|---|
| Ruff migration | `pre-commit run --all-files` passes |
| mypy config and annotations | mypy passes; the existing 17 tests prove runtime behavior is unchanged |
| CI workflow | CI observed green on its own PR |
| Branch protection | A direct push to `main` is rejected for non-admins. *Outcome: verified 2026-09-18 — the owner's push succeeded, because `enforce_admins` is false. The rule is live and correct; the exemption is doing what it was configured to do.* |

A test asserting that a config file contains a config value tests the file, not behavior. The exception is the failure mode above: a real type error found during annotation gets a real test.

## Out of scope

- `strict = true` — a follow-up once annotations land
- Multi-OS or multi-Python CI matrix
- Publishing, releases, or packaging the `.wav` files (separate README TODO)
- Adding mypy as a Poetry dev dependency — noted, not required for CI to work
