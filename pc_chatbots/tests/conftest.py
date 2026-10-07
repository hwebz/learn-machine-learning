"""Shared pytest configuration.

The ``live`` marker tags tests that require a real signed-in browser profile
(Playwright + Chrome + manual login). These are skipped by default and only run
when explicitly selected with ``-m live``.
"""

from __future__ import annotations

import re

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    skip_live = pytest.mark.skip(reason="live test — run with '-m live' and a signed-in browser profile")
    expr = config.getoption("-m") or ""
    wants_live = "live" in _parse_mark_filter(expr)

    for item in items:
        if not wants_live and any(marker.name == "live" for marker in item.iter_markers()):
            item.add_marker(skip_live)


def _parse_mark_filter(expr: str) -> set[str]:
    """Best-effort extraction of marker names from a -m expression string."""
    names: set[str] = set()
    for token in re.split(r"\s+(?:and|or|not)\s+|\s+", expr):
        token = token.strip("() ")
        if token and token.isidentifier():
            names.add(token)
    return names
