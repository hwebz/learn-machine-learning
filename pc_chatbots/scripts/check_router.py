from __future__ import annotations

import asyncio
import time

from openai import AsyncOpenAI

from app.core.config import settings


async def main() -> int:
    client = AsyncOpenAI(base_url=settings.router_base_url, api_key=settings.router_api_key)
    models = [settings.router_model_planner, settings.router_model_extractor, settings.router_model_lead]
    failures = 0
    try:
        for model in models:
            started = time.perf_counter()
            try:
                result = await client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Reply with a short readiness confirmation."}],
                    max_tokens=32,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                content = result.choices[0].message.content or ""
                print(f"{model}: {elapsed_ms:.0f} ms — {content[:50]}")
            except Exception as exc:
                failures += 1
                print(f"{model}: failed ({type(exc).__name__}: {exc})")
    finally:
        await client.close()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

