from __future__ import annotations

import pytest

from app.adapters.selectors_loader import get, load_selectors, provider_selectors


def test_load_selectors_parses_and_validates() -> None:
    selectors = load_selectors()
    assert isinstance(selectors, dict)
    assert "providers" in selectors
    assert "blocking" in selectors
    assert "completion" in selectors


def test_providers_have_required_keys() -> None:
    selectors = load_selectors()
    assert len(selectors["providers"]) >= 14
    for provider in selectors["providers"]:
        cfg = provider_selectors(selectors, provider)
        for key in ("new_chat_url", "question_input", "submit", "answer_container", "source_links"):
            assert key in cfg, f"provider {provider} missing key {key}"


def test_blocking_section_has_url_and_text_patterns() -> None:
    selectors = load_selectors()
    blocking = selectors["blocking"]
    assert isinstance(blocking.get("url_patterns"), list) and blocking["url_patterns"]
    assert isinstance(blocking.get("text_patterns"), list) and blocking["text_patterns"]


def test_completion_section_has_timing_params() -> None:
    selectors = load_selectors()
    comp = selectors["completion"]
    for key in ("stable_seconds", "poll_interval_s", "min_poll_s", "max_poll_s"):
        assert key in comp


def test_get_helper_returns_default_on_missing_path() -> None:
    selectors = load_selectors()
    assert get(selectors, "missing", "path", default="fallback") == "fallback"


def test_provider_selectors_raises_on_unknown() -> None:
    selectors = load_selectors()
    with pytest.raises(KeyError):
        provider_selectors(selectors, "nonexistent")