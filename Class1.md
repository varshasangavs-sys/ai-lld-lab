## 1. `uv` — the modern Python toolchain

__What it is:__ `uv` is a single Rust-based tool that replaces `pip`, `pip-tools`, `virtualenv`, `pyenv`, and `poetry`/`pipenv`. It manages Python versions, virtual environments, dependencies, and lock files.

__Why it matters (real-world problem it solves):__

- __"Works on my machine":__ Different developers install different package versions because `requirements.txt` says `fastapi>=0.100` with no upper bound. `uv` generates a `uv.lock` file pinning *every* transitive dependency to an exact version + hash. Everyone gets byte-identical environments.
- __Speed:__ installs in milliseconds (Rust, parallel downloads, global cache). CI goes from minutes to seconds.
- __Python version pinning:__ `uv python install 3.12` + `.python-version` file means the project declares "I need 3.12" and uv enforces it — no more "I have 3.11 locally" surprises.
- __One command mental model:__ `uv sync` (install), `uv run pytest` (run in the env), `uv add fastapi` (add dep + update lock). No activating venvs.

__Without uv:__ you'd juggle `python -m venv`, `pip install -r requirements.txt`, `pip freeze`, and hope nothing drifted. That's the setup that costs new teammates days.

## 2. `pyproject.toml` — the single source of truth

__What it is:__ A standardized (PEP 518/621) TOML file that declares project metadata, dependencies, build system, and tool configuration (ruff, mypy, pytest, etc.).

__Why it matters:__

- __Before:__ `setup.py`, `setup.cfg`, `requirements.txt`, `requirements-dev.txt`, `tox.ini`, `.flake8`, `mypy.ini`, `pytest.ini` — 7 files, all drifting. Changing a rule meant editing 3 places.
- __After:__ one file. `uv` reads it, `ruff` reads it, `mypy` reads it, `pytest` reads it. New tool? Add a `[tool.x]` section.
- __Declarative over imperative:__ `setup.py` was *code* that ran at install time (security risk, hard to parse). `pyproject.toml` is *data* — tools can read it safely.
- __Build backend abstraction:__ `[build-system] requires = ["hatchling"]` lets you swap build tools without changing project metadata.

__Scalability angle:__ as the project grows (Days 2–35 add SQLAlchemy, Celery, etc.), dependencies and their configs live in one place. A new developer reads one file to understand the whole project.

## 3. `Makefile` — shortcuts and CI/local parity

__What it is:__ A set of named shortcuts (`install`, `lint`, `format`, `typecheck`, `test`, `check`) that wrap the longer `uv run ...` commands.

__Why it matters:__

- __Memorability:__ `make check` instead of remembering and typing 4 separate commands in the right order.
- __CI/local parity:__ CI (`ci.yml`) calls the exact same `make check`. This means "it works on my machine" and "it works in CI" are testing the *literal same command* — no drift between what you ran locally and what GitHub runs.
- `check` composes the other three targets (`lint typecheck test`), so one command gives you the full health check before you commit or push.

## 4. `scripts/check.py` — a `make`-free fallback

__What it is:__ The same 4 checks as `make check`, written as a plain Python script that runs each step and stops at the first failure.

__Why it matters:__ `make` isn't guaranteed to be installed everywhere (some Windows setups lack it out of the box). This gives a guaranteed-to-work alternative using only Python, which every contributor already has via `uv`.

## 5. `.pre-commit-config.yaml` — catching issues before they're even committed

__What it is:__ Config for the `pre-commit` framework, wired to run `ruff` (lint) and `ruff-format` automatically on `git commit`.

__Why it matters:__ This is the earliest possible checkpoint in the whole pipeline — style and simple lint errors get caught in seconds, on your machine, *before* a commit is even created. Compare that to waiting for CI to fail minutes later after a push.

## 6. `.github/workflows/ci.yml` — the safety net

__What it is:__ A GitHub Actions workflow that triggers on every `push` and `pull_request`, installs Python 3.12 via `uv`, and runs `make check`.

__Why it matters:__ Pre-commit hooks can be skipped (`--no-verify`) or simply not installed by a contributor. CI is the backstop that *cannot* be skipped — nothing merges with failing lint, type, or test checks, regardless of what happened locally.

## 7. `.gitignore` — keeping junk out of version control

__What it is:__ A list of file/folder patterns Git should never track.

__Why it matters:__ Without it, things like `.venv/`, `__pycache__/`, `.pytest_cache/`, and `.mypy_cache/` can get accidentally committed — bloating the repo and causing noisy diffs. __Status: currently empty — a gap to fill in soon.__

## 8. `src/ai_lld_lab/__init__.py` — package identity

__What it is:__ The file that makes `src/ai_lld_lab/` an importable Python package, holding `__version__ = "0.1.0"`.

__Why it matters:__ This single line is what `tests/test_smoke.py` actually verifies. It's also what `pyproject.toml`'s `[tool.hatch.build.targets.wheel]` points at when building a distributable package.

## 9. `tests/test_smoke.py` and `tests/conftest.py` — first test and fixture home

__What it is:__ `test_smoke.py` is a "smoke test" — it just checks that the package imports and `__version__` is correct. `conftest.py` is currently empty; it's pytest's designated place for shared fixtures (e.g. a reusable test client or DB session) once there's real functionality to test.

__Why it matters:__ A smoke test is the cheapest possible safety check — if it fails, nothing else is worth testing yet. Keeping fixtures in `conftest.py` (rather than duplicating setup in every test file) is what keeps the test suite maintainable as it grows across 35 days.

## 10. The `src/ai_lld_lab/` subpackages — sketching the architecture early

__What it is:__ Six empty subpackages: `core/`, `web/`, `booking/`, `agents/`, `rag/`, `finetune/`.

__Why it matters:__ They're deliberate placeholders for the planned architecture of the "AI support platform backend":

- `core/` — shared config, models, and utilities used across the whole app.
- `web/` — the FastAPI app and routes; the HTTP front door.
- `booking/` — the booking/appointment domain feature.
- `agents/` — AI agent/orchestration logic.
- `rag/` — Retrieval-Augmented Generation (retrieve docs, feed into an LLM prompt).
- `finetune/` — model fine-tuning code.

Having them exist (even empty) from Day 1 means the project's intended shape is visible immediately, instead of being decided ad hoc as code gets added over the next 34 days.

__Running theme across all of Day 1:__ every file added today exists to make *correctness checks happen as early and as automatically as possible* — pre-commit catches issues in seconds, CI catches anything that slips through, and `pyproject.toml` + `Makefile` make sure "the right way to check" is one command, not something each contributor reinvents.

