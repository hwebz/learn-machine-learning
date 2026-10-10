"""Utility to clone the shared Chrome profile into isolated per-provider profiles.

This allows migrating existing logins from WORK_MODE=sync (./data/profiles/main)
to WORK_MODE=async (./data/profiles/<provider>) without having to re-authenticate
each chatbot manually.

Usage:
    python scripts/clone_profiles.py
    python scripts/clone_profiles.py --provider gemini
    python scripts/clone_profiles.py --force
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from app.adapters.selectors_loader import load_selectors
from app.core.config import get_provider_profile_dir, settings

# Files that should not be copied across live/new profiles
IGNORE_PATTERNS = shutil.ignore_patterns(
    "SingletonLock",
    "SingletonCookie",
    "SingletonSocket",
    "*lock*",
    "Cache*",
    "Code Cache*",
    "GPUCache*",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clone shared profile to per-provider profiles")
    parser.add_argument("--source", default=None, help="Source profile directory (default: BROWSER_PROFILE_DIR)")
    parser.add_argument("--provider", default=None, help="Specific provider target (e.g. gemini, copilot)")
    parser.add_argument("--force", action="store_true", help="Overwrite target provider profile if it already exists")
    args = parser.parse_args()

    src: Path = Path(args.source) if args.source else settings.browser_profile_dir
    if not src.is_dir():
        print(f"Error: Source profile directory does not exist: {src.resolve()}")
        return 1

    selectors = load_selectors()
    providers = [args.provider] if args.provider else list(selectors.get("providers", {}).keys())

    print(f"Source profile: {src.resolve()}")
    print(f"Target providers: {', '.join(providers)}\n")

    copied_count = 0
    skipped_count = 0

    for provider in providers:
        dst = get_provider_profile_dir(provider, mode="async")
        if dst == src:
            continue
        if dst.exists():
            if not args.force:
                print(f"[skip] {provider}: Destination already exists ({dst}). Use --force to overwrite.")
                skipped_count += 1
                continue
            print(f"[overwrite] Removing existing profile for {provider}...")
            shutil.rmtree(dst, ignore_errors=True)

        dst.parent.mkdir(parents=True, exist_ok=True)
        print(f"[copy] Cloning to {provider}: {dst.resolve()}...")
        try:
            shutil.copytree(src, dst, ignore=IGNORE_PATTERNS)
            copied_count += 1
        except Exception as exc:
            print(f"[error] Failed to clone for {provider}: {exc}")

    print(f"\nDone! Copied: {copied_count}, Skipped: {skipped_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
