from abc import ABC, abstractmethod

import httpx

from ai_lld_lab.core.errors import UpstreamError, ValidationError


class ChatInterface(ABC):
    @abstractmethod
    def invoke(self, request: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError


class AnthropicChat(ChatInterface):
    _url = "https://api.anthropic.com/v1/messages"
    _model = "claude-sonnet-5-5"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def invoke(self, request: str, system_prompt: str | None = None) -> str:
        try:
            response = httpx.post(
                self._url,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 1024,
                    **({"system": system_prompt} if system_prompt else {}),
                    "messages": [{"role": "user", "content": request}],
                },
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpstreamError(f"Anthropic request failed: {exc}") from exc

        data = response.json()
        return str(data["content"][0]["text"])


class OpenAIChat(ChatInterface):
    _url = "https://api.openai.com/v1/chat/completions"
    _model = "gpt-4o"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def invoke(self, request: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": request})

        try:
            response = httpx.post(
                self._url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": messages,
                },
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpstreamError(f"OpenAI request failed: {exc}") from exc

        data = response.json()
        return str(data["choices"][0]["message"]["content"])


class FakeChat(ChatInterface):
    def __init__(self, response: str = "This is a fake response.") -> None:
        self.response = response
        self.requests: list[str] = []

    def invoke(self, request: str, system_prompt: str | None = None) -> str:
        self.requests.append(request)
        return self.response


class ChatInterfaceFactory:
    @staticmethod
    def create_chat_interface(provider: str, api_key: str) -> ChatInterface:
        if provider == "anthropic":
            return AnthropicChat(api_key)
        elif provider == "openai":
            return OpenAIChat(api_key)
        elif provider == "fake":
            return FakeChat()
        else:
            raise ValidationError(f"Unsupported provider: {provider}")