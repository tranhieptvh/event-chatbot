"""LLM provider abstraction supporting Gemini and OpenAI via LangChain."""
from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import settings


class LLMProvider(ABC):
    @abstractmethod
    def extract_fields(self, prompt: str) -> str:
        """Send prompt to LLM and return raw text response."""


class GeminiProvider(LLMProvider):
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0,
        )

    def extract_fields(self, prompt: str) -> str:
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )

    def extract_fields(self, prompt: str) -> str:
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content


_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is not None:
        return _provider

    provider_name = settings.LLM_PROVIDER.lower()
    if provider_name == "gemini":
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        _provider = GeminiProvider()
    elif provider_name == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        _provider = OpenAIProvider()
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}. Use 'gemini' or 'openai'."
        )

    return _provider


def reset_provider() -> None:
    """Reset cached provider (used in tests)."""
    global _provider
    _provider = None
