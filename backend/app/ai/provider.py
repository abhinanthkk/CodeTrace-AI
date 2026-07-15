"""
CodeTrace AI — AI Provider Abstraction

Pluggable provider interface. Supports OpenAI and Gemini.
No provider? The app still works with deterministic explanations.
"""

import logging
from abc import ABC, abstractmethod

from ..config import settings

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract interface for AI model providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a response from the given prompt."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...


class OpenAIProvider(AIProvider):
    """OpenAI API provider (GPT-4o, etc.)."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.AI_API_KEY
        self.model = model or settings.AI_MODEL

    @property
    def name(self) -> str:
        return f"OpenAI ({self.model})"

    def generate(self, prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("openai package not installed")
            raise RuntimeError("OpenAI package not installed. Run: pip install openai")

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise Python debugging tutor. You ONLY use the "
                        "execution evidence provided to explain failures. Never invent "
                        "variable states, values, or events not present in the evidence. "
                        "Use beginner-friendly language. Be concise."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        return response.choices[0].message.content or ""


class GeminiProvider(AIProvider):
    """Google Gemini API provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.AI_API_KEY
        self.model = model or settings.AI_MODEL or "gemini-1.5-flash"

    @property
    def name(self) -> str:
        return f"Gemini ({self.model})"

    def generate(self, prompt: str) -> str:
        try:
            import google.generativeai as genai
        except ImportError:
            logger.error("google-generativeai package not installed")
            raise RuntimeError(
                "Google Generative AI package not installed. Run: pip install google-generativeai"
            )

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(
            [
                "You are a precise Python debugging tutor. You ONLY use the "
                "execution evidence provided to explain failures. Never invent "
                "variable states, values, or events not present in the evidence. "
                "Use beginner-friendly language. Be concise.",
                prompt,
            ],
            generation_config={"temperature": 0.3, "max_output_tokens": 1000},
        )
        return response.text or ""


def create_provider() -> AIProvider | None:
    """
    Factory: create the configured AI provider.

    Returns None if no provider is configured or the API key is missing.
    """
    provider_name = settings.AI_PROVIDER.lower().strip()

    if not provider_name or not settings.AI_API_KEY:
        return None

    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name in ("gemini", "google"):
        return GeminiProvider()
    else:
        logger.warning(f"Unknown AI provider: {provider_name}")
        return None
