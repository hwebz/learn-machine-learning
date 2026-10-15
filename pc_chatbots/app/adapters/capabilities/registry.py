from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import structlog

from app.adapters.capabilities.base import BaseProviderCapabilitiesStrategy
from app.adapters.capabilities.chatgpt import ChatGPTCapabilitiesStrategy
from app.adapters.capabilities.copilot import CopilotCapabilitiesStrategy
from app.adapters.capabilities.gemini import GeminiCapabilitiesStrategy
from app.adapters.capabilities.qwen import QwenCapabilitiesStrategy
from app.adapters.capabilities.claude import ClaudeCapabilitiesStrategy
from app.adapters.capabilities.deepseek import DeepSeekCapabilitiesStrategy
from app.adapters.capabilities.perplexity import PerplexityCapabilitiesStrategy
from app.adapters.capabilities.kimi import KimiCapabilitiesStrategy
from app.adapters.capabilities.grok import GrokCapabilitiesStrategy
from app.adapters.capabilities.mistral import MistralCapabilitiesStrategy
from app.adapters.capabilities.models import (
    OptionItem,
    ProviderLiveCapabilities,
    SupportedDataTypes,
    VoiceChatSupport,
)
from app.adapters.selectors_loader import load_selectors, provider_selectors
from app.browser.session import BrowserSessionManager

logger = structlog.get_logger(__name__)
CAPS_CACHE_FILE = Path("./data/provider_capabilities.json")


class GenericDefaultCapabilitiesStrategy(BaseProviderCapabilitiesStrategy):
    """Fallback strategy providing safe defaults for providers pending custom DOM strategies."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def provider_name(self) -> str:
        return self._name

    def get_default_capabilities(self) -> ProviderLiveCapabilities:
        return ProviderLiveCapabilities(
            provider=self._name,
            synced_at=datetime.now(timezone.utc),
            is_live_dom=False,
            available_models=[
                OptionItem(
                    id="default",
                    label=f"{self._name.capitalize()} Default",
                    description=f"Mô hình mặc định của {self._name.capitalize()}",
                    selected=True,
                )
            ],
            selected_model_id="default",
            thinking_levels=[
                OptionItem(id="auto", label="Auto", description="Tự động", selected=True)
            ],
            selected_thinking_level_id="auto",
            modes=[
                OptionItem(id="standard", label="Standard", description="Tiêu chuẩn", selected=True)
            ],
            selected_mode_id="standard",
            supported_data_types=SupportedDataTypes(
                text=True,
                image=True,
                file=True,
                audio=False,
                video=False,
                supported_mime_types=["image/*", ".pdf", ".txt", ".csv", ".json"],
            ),
            voice_chat=VoiceChatSupport(
                supported=True,
                mode="backend_stt",
                details="Hỗ trợ ghi âm microphone và chuyển thành văn bản bất đồng bộ qua backend.",
            ),
        )

    async def inspect_dom(self, page: Any) -> ProviderLiveCapabilities:
        # Default inspector returns default baseline
        caps = self.get_default_capabilities()
        caps.synced_at = datetime.now(timezone.utc)
        return caps

    async def apply_selection(self, page: Any, config: Any) -> None:
        pass


class CapabilitiesRegistry:
    """Central registry and cache manager for provider options and DOM synchronization."""

    _instance: CapabilitiesRegistry | None = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        self._strategies: dict[str, BaseProviderCapabilitiesStrategy] = {}
        self._cache: dict[str, ProviderLiveCapabilities] = {}
        self._selectors = load_selectors()
        self._register_builtins()
        self._load_cache_from_disk()

    @classmethod
    def instance(cls) -> CapabilitiesRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _register_builtins(self) -> None:
        """Register provider strategies."""
        chatgpt_strat = ChatGPTCapabilitiesStrategy()
        self.register(chatgpt_strat)
        copilot_strat = CopilotCapabilitiesStrategy()
        self.register(copilot_strat)
        gemini_strat = GeminiCapabilitiesStrategy()
        self.register(gemini_strat)
        qwen_strat = QwenCapabilitiesStrategy()
        self.register(qwen_strat)
        claude_strat = ClaudeCapabilitiesStrategy()
        self.register(claude_strat)
        deepseek_strat = DeepSeekCapabilitiesStrategy()
        self.register(deepseek_strat)
        perplexity_strat = PerplexityCapabilitiesStrategy()
        self.register(perplexity_strat)
        kimi_strat = KimiCapabilitiesStrategy()
        self.register(kimi_strat)
        grok_strat = GrokCapabilitiesStrategy()
        self.register(grok_strat)
        mistral_strat = MistralCapabilitiesStrategy()
        self.register(mistral_strat)

    def register(self, strategy: BaseProviderCapabilitiesStrategy) -> None:
        self._strategies[strategy.provider_name.lower()] = strategy

    def get_strategy(self, provider: str) -> BaseProviderCapabilitiesStrategy:
        p = provider.lower()
        if p in self._strategies:
            return self._strategies[p]
        return GenericDefaultCapabilitiesStrategy(p)

    def _load_cache_from_disk(self) -> None:
        if not CAPS_CACHE_FILE.is_file():
            return
        try:
            raw = json.loads(CAPS_CACHE_FILE.read_text(encoding="utf-8"))
            for p, item in raw.items():
                self._cache[p] = ProviderLiveCapabilities.model_validate(item)
            logger.info("capabilities_cache_loaded", count=len(self._cache))
        except Exception as exc:
            logger.warning("capabilities_cache_load_failed", error=str(exc))

    def _save_cache_to_disk(self) -> None:
        try:
            CAPS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            serializable = {p: item.model_dump(mode="json") for p, item in self._cache.items()}
            CAPS_CACHE_FILE.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            logger.warning("capabilities_cache_save_failed", error=str(exc))

    async def get_capabilities(self, provider: str, force_sync: bool = False) -> ProviderLiveCapabilities:
        """Retrieve capabilities for a provider. If force_sync is True, perform live DOM scan."""
        p = provider.lower()
        strategy = self.get_strategy(p)

        if not force_sync and p in self._cache:
            return self._cache[p]

        if not force_sync:
            # Return strategy baseline if not yet synced
            caps = strategy.get_default_capabilities()
            self._cache[p] = caps
            return caps

        # Perform live DOM inspection via Playwright
        async with self._lock:
            session = BrowserSessionManager.get_session(p)
            cfg = provider_selectors(self._selectors, p)
            target_url = cfg.get("new_chat_url", "")
            if not target_url:
                target_url = "https://chatgpt.com/" if p == "chatgpt" else f"https://{p}.com"

            page = None
            try:
                async with session.exclusive():
                    page = await session.new_page(target_url)
                    # Allow SPA container to hydrate
                    await asyncio.sleep(2.0)
                    caps = await strategy.inspect_dom(page)
                    self._cache[p] = caps
                    self._save_cache_to_disk()
                    return caps
            except Exception as exc:
                logger.warning("live_dom_sync_failed", provider=p, error=str(exc))
                caps = strategy.get_default_capabilities()
                caps.last_error = f"Không thể đồng bộ trực tiếp từ DOM: {type(exc).__name__}: {exc}"
                caps.is_live_dom = False
                self._cache[p] = caps
                return caps
            finally:
                if page is not None:
                    try:
                        if session._ctx is not None and len(session._ctx.pages) <= 1:
                            await page.goto("about:blank")
                        else:
                            await page.close()
                    except Exception:
                        pass

    async def sync_all(self, providers: list[str] | None = None) -> dict[str, ProviderLiveCapabilities]:
        """Asynchronously sync capabilities for multiple providers."""
        target_providers = providers or list(self._strategies.keys())
        results: dict[str, ProviderLiveCapabilities] = {}

        for p in target_providers:
            results[p] = await self.get_capabilities(p, force_sync=True)

        return results
