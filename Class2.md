## 1. Typed config with `pydantic-settings`

__What it is:__ Instead of reading environment variables ad-hoc with `os.getenv(...)` scattered across files, `pydantic-settings` lets you declare one `Settings(BaseSettings)` class with typed fields. It reads matching env vars (and an optional `.env` file), validates and coerces their types, and fails fast at startup if something doesn't fit.

__Why it matters (real-world problem it solves):__

- __No more silent misconfiguration:__ `LOG_LEVEL=banana` or a missing required var gets caught immediately at startup, not discovered three layers deep in production.
- __One typed object instead of scattered getters:__ every config value lives in one place (`core/config.py`), with autocomplete and type-checking instead of stringly-typed lookups.
- __Singleton, done safely:__ you only want `Settings` built once, but a hand-rolled singleton (`__new__` + a class-level `_object`) is painful to override in tests — it's shared mutable global state. The fix is caching a *function*, not hardcoding an instance:

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Same "build once" benefit, but a test can call `get_settings.cache_clear()` to force a fresh read after changing env vars — something a baked-in global object can't do cleanly.

## 2. JSON logging with a request id

__What it is:__ A custom `logging.Formatter` subclass (`JSONFormatter`) that renders every log line as a single-line JSON object (`level`, `logger`, `message`, `request_id`, and `exc_info` when an exception is attached), wired to the root logger via `configure_logging()`.

__Why it matters:__

- __Searchable logs:__ plain-text logs can't be reliably filtered at scale. One JSON object per line can be queried (`jq 'select(.level=="ERROR")'`), unlike pretty-printed, multi-line JSON which breaks line-based parsing.
- __Tracing one request through the noise:__ the real problem this solves is "the bot broke for a customer, but which request?" By tagging every log line from one incoming request with the same `request_id`, you can pull every log tied to *one* failing request instead of guessing from a wall of mixed output.
- __`contextvars.ContextVar`, not a global or thread-local:__ the request id needs to travel correctly through `asyncio` code, where many requests interleave on one thread. A plain thread-local would leak request ids across concurrent requests; `ContextVar` is async-safe per-request storage.
- __No custom singleton needed:__ Python's `logging.getLogger(name)` is already a cached registry — calling it twice with the same name returns the same logger. Building a singleton class on top of it (as I first tried) was solving an already-solved problem.

## 3. A typed `AppError` hierarchy

__What it is:__ A base `AppError(Exception)` carrying a `code` (machine-readable string) and `status_code` (metadata, not literally raised as HTTP), with subclasses like `NotFoundError`, `ValidationError`, `UnauthorizedError` overriding `code`, `status_code`, and a default message.

__Why it matters:__

- __One shared base to catch:__ the whole point of a hierarchy is that calling code does `except AppError as e: ...` once, reading `e.code` / `e.status_code` off the instance — instead of a chain of `if code == 400: raise ValueError(...) elif code == 401: ...` branching across unrelated built-in exception types that share no common parent.
- __Layering and dependency direction:__ `core/errors.py` defines *domain* errors and never imports anything HTTP-related. `status_code` is just data sitting on the exception — the future `web/` layer reads it to build the actual HTTP response. Dependencies point inward, toward `core`; `core` stays framework-agnostic and testable without a running web server.
- __DRY via a class attribute, not a repeated `__init__`:__ each subclass only needs to override `code`, `status_code`, and `default_message` — the base class's single `__init__(self, message: str | None = None)` handles the "use custom message or fall back to default" logic for every subclass at once.

## 4. Testing patterns that came up

- __`monkeypatch.setenv`__ (pytest) sets an env var for the duration of one test only — used to prove `Settings` actually reads real env vars, not just its defaults.
- __Cache-clearing fixtures:__ because `get_settings` and `configure_logging` both touch shared/cached state (the `lru_cache` and the root logger's handlers), an `autouse` fixture resets that state before/after every test so tests can't leak into each other.
- __`capsys`__ (pytest) captures real stdout — used to prove `configure_logging` actually writes a parseable JSON line to the stream, end-to-end, not just that the formatter function returns the right string in isolation.
- __Coverage as a completeness signal, not a target to game:__ `pytest --cov` showing 100% across `config.py`, `errors.py`, and `logging.py` is what actually closed out Day 2 — writing the code and manually eyeballing it working wasn't enough; without tests, nothing stops a later change from silently breaking `get_settings()` or the error hierarchy.

__Running theme across Day 2:__ every "fix" today was replacing a hand-rolled, stateful pattern (a custom Singleton class) with Python/library features that already solve the same problem in a more testable way — `@lru_cache`, `logging.getLogger`, and a class-attribute-driven exception hierarchy.
