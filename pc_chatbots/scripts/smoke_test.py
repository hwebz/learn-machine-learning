from __future__ import annotations

import argparse
import asyncio
from typing import Any

from app.adapters.gemini_ui import GeminiUIAdapter
from app.adapters.perplexity_ui import PerplexityUIAdapter
from app.adapters.selectors_loader import load_selectors, provider_selectors
from app.browser.locators import resolve_locator
from app.browser.session import BrowserSession
from app.browser.waits import detect_blocking_state
from app.core.config import settings

ADAPTERS: dict[str, Any] = {
    "perplexity": PerplexityUIAdapter,
    "gemini": GeminiUIAdapter,
}

REQUIRED_CHAINS = ("question_input", "submit", "answer_container", "source_links")


async def check_static(name: str) -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True
    try:
        selectors = load_selectors()
        cfg = provider_selectors(selectors, name)
        lines.append(f"[ok] selectors.yaml has provider '{name}'")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"[FAIL] selectors.yaml: {exc}")
        return False, lines
    profile = settings.browser_profile_dir
    if profile.is_dir() and any(profile.iterdir()):
        lines.append(f"[ok] profile dir non-empty: {profile}")
    else:
        lines.append(f"[warn] profile dir empty/missing — run scripts/login_profile.py ({profile})")
    return ok, lines


async def check_live(name: str, adapter: Any, *, ask: str | None, timeout_s: int) -> tuple[bool, list[str]]:
    lines: list[str] = []
    session = BrowserSession.instance()
    try:
        await session.start()
        cfg = adapter._cfg
        page = await session.new_page(cfg["new_chat_url"])
        try:
            blocking = await detect_blocking_state(page, load_selectors().get("blocking", {}))
            if blocking is not None:
                lines.append(f"[FAIL] blocking state: {blocking.kind} — {blocking.detail}")
                lines.append("       Complete login/CAPTCHA in the browser window, then re-run.")
                return False, lines
            lines.append("[ok] not blocked (no login/CAPTCHA wall detected)")

            all_ok = True
            for chain_name in REQUIRED_CHAINS:
                locator, rung = await resolve_locator(page, cfg.get(chain_name, []))
                if locator is None:
                    lines.append(f"[FAIL] {chain_name}: no rung matched")
                    all_ok = False
                else:
                    lines.append(f"[ok] {chain_name}: matched rung #{rung}")
            if not all_ok:
                return False, lines

            if ask:
                lines.append(f"[ask] sending probe question: {ask!r}")
                result = await adapter.ask(ask, timeout_s=timeout_s)
                lines.append(f"[ask] status={result.status} sources={len(result.sources)} answer_len={len(result.answer_markdown)}")
                if result.status == "ok" and result.answer_markdown.strip():
                    lines.append(f"[ask] answer preview: {result.answer_markdown[:200]!r}")
                    return True, lines
                if result.status == "needs_user_action":
                    lines.append(f"[ask] needs user action: {result.error}")
                    return False, lines
                lines.append(f"[warn] non-ok status: {result.status} ({result.error})")
                return False, lines

            lines.append("[ok] live selector check passed (no question sent)")
            return True, lines
        finally:
            try:
                await page.close()
            except Exception:  # noqa: BLE001
                pass
    finally:
        await session.close()


async def main() -> int:
    parser = argparse.ArgumentParser(description="Validate chatbot UI adapters and selectors.")
    parser.add_argument("--provider", choices=[*ADAPTERS, "all"], default="all")
    parser.add_argument("--ask", nargs="?", const="Reply with the single word: pong", default=None,
                        help="Send one probe question per provider after the selector check.")
    parser.add_argument("--timeout", type=int, default=120, help="Per-question timeout seconds.")
    parser.add_argument("--live", action="store_true", help="Open the browser and check selectors on the live sites.")
    args = parser.parse_args()

    names = list(ADAPTERS) if args.provider == "all" else [args.provider]
    overall_ok = True
    for name in names:
        print(f"\n=== {name} ===")
        static_ok, static_lines = await check_static(name)
        for line in static_lines:
            print(line)
        if not static_ok:
            overall_ok = False
            continue
        if args.live:
            adapter = ADAPTERS[name]()
            live_ok, live_lines = await check_live(name, adapter, ask=args.ask, timeout_s=args.timeout)
            for line in live_lines:
                print(line)
            if not live_ok:
                overall_ok = False
        else:
            print("[skip] live check (pass --live to open the browser)")

    print("\n" + ("SMOKE TEST PASSED" if overall_ok else "SMOKE TEST FAILED"))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
