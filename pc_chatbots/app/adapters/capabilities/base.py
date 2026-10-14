from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from app.adapters.capabilities.models import (
    ProviderLiveCapabilities,
    ProviderSelectionRequest,
)


@runtime_checkable
class ICapabilitiesInspector(Protocol):
    """Interface for inspecting a live browser page DOM to discover capabilities."""

    async def inspect(self, page: Any) -> ProviderLiveCapabilities:
        """Query page DOM elements and extract available options and input types."""
        ...


@runtime_checkable
class ICapabilitiesApplier(Protocol):
    """Interface for configuring chosen model, thinking level, and modes on the page."""

    async def apply(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Actuate DOM selectors to switch model, thinking level, or mode."""
        ...


@runtime_checkable
class IVoiceTranscriber(Protocol):
    """Interface for asynchronous speech-to-text conversion."""

    async def transcribe(self, audio_bytes: bytes, filename: str, content_type: str) -> str:
        """Convert recorded voice audio into text asynchronously."""
        ...


class BaseProviderCapabilitiesStrategy(ABC):
    """Abstract base strategy for a provider's option discovery and manipulation.

    Follows Open/Closed Principle: each provider implements its own strategy
    subclass without modifying orchestrator or routes.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier, e.g. 'chatgpt', 'gemini'."""
        ...

    @abstractmethod
    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        """Return safe default capabilities when the live DOM is unreachable."""
        ...

    @abstractmethod
    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        """Inspect the live Playwright page DOM to collect current options."""
        ...

    @abstractmethod
    async def apply_selection(self, page: Any, config: ProviderSelectionRequest) -> None:
        """Apply the user's selected model, thinking level, and mode in the page DOM."""
        ...

    async def inspect(self, page: Any) -> ProviderLiveCapabilities:
        """ICapabilitiesInspector interface implementation."""
        return await self.inspect_dom(page)

    async def apply(self, page: Any, config: ProviderSelectionRequest) -> None:
        """ICapabilitiesApplier interface implementation."""
        await self.apply_selection(page, config)

    # Common helpers
    async def safe_inner_text(self, locator: Any, timeout: int = 1500) -> str:
        try:
            return (await locator.inner_text(timeout=timeout)).strip()
        except Exception:
            return ""

    async def safe_attr(self, locator: Any, name: str, timeout: int = 1000) -> str:
        try:
            val = await locator.get_attribute(name, timeout=timeout)
            return (val or "").strip()
        except Exception:
            return ""

    async def is_disabled(self, locator: Any, timeout: int = 1000) -> bool:
        try:
            aria = await self.safe_attr(locator, "aria-disabled", timeout=timeout)
            if aria.lower() == "true":
                return True
            return bool(await locator.is_disabled(timeout=timeout))
        except Exception:
            return False
