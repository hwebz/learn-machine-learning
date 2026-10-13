from __future__ import annotations

from typing import Type
from app.browser.converters.base import BaseMarkdownConverter
from app.browser.converters.chatgpt import ChatGPTMarkdownConverter

_REGISTRY: dict[str, Type[BaseMarkdownConverter]] = {
    "chatgpt": ChatGPTMarkdownConverter,
    "openai": ChatGPTMarkdownConverter,
}


def register_converter(provider_name: str, converter_cls: Type[BaseMarkdownConverter]) -> None:
    """Register a custom converter class for a given provider name."""
    _REGISTRY[provider_name.lower().strip()] = converter_cls


def get_converter(provider: str | None = None) -> BaseMarkdownConverter:
    """Instantiate and return the appropriate Markdown converter for the provider."""
    if not provider:
        return BaseMarkdownConverter()

    key = provider.lower().strip()
    converter_cls = _REGISTRY.get(key)
    if converter_cls is not None:
        return converter_cls()

    # Prefix / substring match for variants (e.g. "chatgpt_plus", "chatgpt_ui")
    for reg_key, cls in _REGISTRY.items():
        if reg_key in key or key in reg_key:
            return cls()

    return BaseMarkdownConverter()
