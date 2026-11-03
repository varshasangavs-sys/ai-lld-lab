## 1. `ChatInterface` — an abstract base class as the seam

__What it is:__ `ChatInterface(ABC)` declares one abstract method, `invoke(self, request: str, system_prompt: str | None = None) -> str`. Every concrete chat client — real or fake — must implement it.

__Why it matters (real-world problem it solves):__

- __Vendor lock-in, literally prevented by the type checker:__ business code (anything in `agents/`, `booking/`, `web/` later on) will depend only on `ChatInterface`, never on `anthropic`'s or `openai`'s SDK types. If every file called a vendor SDK directly, switching providers — or just testing without one — means hunting through dozens of files.
- __Protocol vs ABC:__ Python offers two ways to define an interface. A `Protocol` is *structural* — any class with a matching `invoke` method satisfies it, no inheritance needed (duck typing, checked statically). An `ABC` is *nominal* — a class must explicitly `class AnthropicChat(ChatInterface)` to count, and Python enforces at instantiation time that every `@abstractmethod` is actually implemented. We used `ABC` here because that runtime enforcement is worth it for something this central: forgetting to implement `invoke` fails immediately and loudly, not silently at some later call site.
- __Dependency Inversion:__ the classic layering mistake is business logic depending on low-level details (a specific vendor's request/response shape). Here it's inverted — `ChatInterface` is the abstraction both sides depend on: business code depends on it, and `AnthropicChat`/`OpenAIChat` depend on it too (by implementing it). Neither depends on the other directly.

## 2. `AnthropicChat` / `OpenAIChat` — the Adapter pattern

__What it is:__ Two concrete classes, each wrapping one vendor's HTTP API behind the same `invoke` signature. Neither uses a vendor SDK package (`anthropic`, `openai`) — both just use `httpx`, already a project dependency, to POST directly to the vendor's REST endpoint and reshape the JSON response into a plain `str`.

__Why it matters:__

- __Adapter, not reinvention:__ Anthropic's Messages API and OpenAI's Chat Completions API have genuinely different request shapes — Anthropic takes a top-level `"system"` string field; OpenAI has no such field and instead expects a `{"role": "system", ...}` entry mixed into its `"messages"` list. The adapter's whole job is absorbing that difference so the caller never has to know it exists:

```python
# AnthropicChat — system prompt is its own field, omitted (not null) when absent
json={
    "model": self._model,
    "max_tokens": 1024,
    **({"system": system_prompt} if system_prompt else {}),
    "messages": [{"role": "user", "content": request}],
}

# OpenAIChat — system prompt becomes a message, prepended to the list
messages = []
if system_prompt:
    messages.append({"role": "system", "content": system_prompt})
messages.append({"role": "user", "content": request})
```

- __No vendor SDK dependency at all:__ going through raw `httpx` instead of installing `anthropic`/`openai` packages is a stronger version of "no vendor lock-in" — even the *adapters* don't depend on vendor-authored code, only on a generic HTTP client.
- __Errors cross the adapter boundary as domain errors, not vendor errors:__ a failed HTTP call (`httpx.HTTPError` — bad key, rate limit, timeout, network failure) is caught inside each adapter and re-raised as `UpstreamError` (see §5), never leaked to the caller as a raw `httpx` exception.

## 3. `FakeChat` — testability without a vendor or a network

__What it is:__ A third implementation of `ChatInterface` that does no networking at all — it just records every `request` it was given and returns a canned `response`.

__Why it matters:__

- __The actual point of the interface:__ an interface only pays off once there's more than one implementation behind it. `FakeChat` is what lets every other module (and every test) exercise "something that answers chat requests" with zero API key, zero network call, and a fully deterministic answer — no flaky tests, no cost, no internet dependency.
- __Records calls for assertions:__ keeping `self.requests` lets a test assert *what was asked*, not just that *something* was returned — e.g. proving a `system_prompt` was actually passed through by a caller, without needing a real model to interpret it.

## 4. `ChatInterfaceFactory` — a creational seam

__What it is:__ `ChatInterfaceFactory.create_chat_interface(provider: str, api_key: str)` is a static method that takes a provider name and returns the matching `ChatInterface` implementation, raising `ValidationError` for anything unrecognized.

__Why it matters:__ it's the one place that knows all three concrete classes exist. Everything else in the codebase only ever sees the `ChatInterface` it gets back — which concrete class got built is a decision made in exactly one spot, instead of `if provider == "anthropic": AnthropicChat(...)` scattered across every call site. (Day 4 will replace *calling* this factory directly with FastAPI's `Depends` — letting one composition root decide what's real vs. fake, instead of each piece of code constructing its own dependencies.)

## 5. Extending the `AppError` hierarchy: `UpstreamError`

__What it is:__ A new subclass of Day 2's `AppError` (`core/errors.py`), `code = "upstream_error"`, `status_code = 502`, raised whenever a call to Anthropic or OpenAI fails.

__Why it matters:__ this is Day 2's typed-error pattern paying off immediately — adding a new failure category (a dependency that's down or rejecting us) meant adding one small subclass, not inventing a new way to signal errors. Calling code still just does `except AppError as e: ...` and reads `e.code` / `e.status_code`, now covering vendor failures too, without ever importing `httpx` itself.

## 6. Bugs the type checker and linter caught today

Writing this module surfaced several real, user-visible bugs — all caught by `mypy`/`ruff` before ever running the code, which is the entire argument for having them in CI from Day 1:

- __Silent `None` instead of a string:__ `invoke` methods that were just `pass` (no `return`) type-check as returning `None` while declared `-> str`. `mypy`'s `empty-body` check caught this — a caller expecting text would otherwise get `None` and fail somewhere far from the real cause.
- __`{system_prompt}` builds a *set*, not a string:__ a one-character mistake — curly braces around a single variable is Python's set-literal syntax, not grouping. This would have sent a `set` object into a JSON payload instead of the system prompt string.
- __Signature drift breaks Liskov Substitution:__ when `system_prompt` was added to the interface, `FakeChat.invoke` briefly fell out of sync (still `invoke(self, request: str) -> str`, missing the new parameter). `mypy`'s `override` check caught the mismatch — without it, polymorphic code calling `chat.invoke(req, system_prompt=...)` would work for every implementation *except* the fake one, exactly the kind of inconsistency contract tests (Day 5) exist to prevent.
- __Wrong API shape entirely, not just a typo:__ the first attempt at passing a system prompt to OpenAI added a top-level `"system"` key to the request body. OpenAI's Chat Completions API has no such field — the system prompt has to be a message *inside* `"messages"`. Neither `mypy` nor `ruff` can catch this kind of bug (it's valid Python, correctly typed); only knowing the actual API contract (or a test matching JSON structure) catches it.

__Running theme across Day 3:__ an interface is only as good as every implementation actually honoring it — the type checker enforces the *shape* (signatures matching), but honoring the *meaning* of a vendor's API still has to be checked by someone who knows that API, which is exactly why Day 5's contract tests exist: one shared test suite run against every implementation, so a new adapter can't pass a signature check while being behaviorally wrong.
