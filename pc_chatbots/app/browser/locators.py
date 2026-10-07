from __future__ import annotations

from typing import Any

SelectorRung = dict[str, str]
SelectorChain = list[SelectorRung] | SelectorRung


def normalize_chain(chain: SelectorChain) -> list[SelectorRung]:
    if isinstance(chain, dict):
        return [chain]
    return list(chain)


def _rung_to_locator(page: Any, rung: SelectorRung) -> Any | None:
    """Convert one YAML rung into a Playwright locator (or None if unsupported)."""
    if "role" in rung:
        kwargs: dict[str, Any] = {}
        if "name" in rung:
            kwargs["name"] = rung["name"]
        return page.get_by_role(rung["role"], **kwargs)
    if "testid" in rung:
        return page.get_by_test_id(rung["testid"])
    if "placeholder" in rung:
        return page.get_by_placeholder(rung["placeholder"])
    if "css" in rung:
        return page.locator(rung["css"])
    if "text" in rung:
        return page.get_by_text(rung["text"])
    return None


def describe_rung(rung: SelectorRung) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in rung.items())


async def resolve_locator(
    page: Any, chain: SelectorChain
) -> tuple[Any | None, int | None]:
    """Try each rung of an ordered fallback chain; return (locator, rung_index).

    The first rung whose locator matches at least one element wins. Returns
    ``(None, None)`` when no rung matches.
    """
    for rung_index, rung in enumerate(normalize_chain(chain)):
        locator = _rung_to_locator(page, rung)
        if locator is None:
            continue
        try:
            if await locator.count() > 0:
                return locator, rung_index
        except Exception:  # noqa: BLE001 — a broken rung must not abort the chain
            continue
    return None, None


async def resolve_description(page: Any, chain: SelectorChain) -> str | None:
    """Human-readable description of the matching rung (for smoke_test output)."""
    locator, rung_index = await resolve_locator(page, chain)
    if locator is None or rung_index is None:
        return None
    return describe_rung(normalize_chain(chain)[rung_index])
