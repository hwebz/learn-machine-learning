"""Debug: dump the raw segment around the escaped-JSON 'pong' thread in a
saved Copilot artifact, to see why the answer never rendered in this tab.

Usage: python scripts/debug_copilot_artifact.py <path-to-html>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = Path(sys.argv[1])
html = path.read_text(encoding="utf-8")

m = re.search(r'pong\\",\\"tone', html)
print("escaped json pong found:", bool(m))
if m:
    start = html.rfind('{"conversationId', 0, m.start())
    seg = html[start : m.start() + 3000]
    print("=" * 60)
    print(seg)
    print("=" * 60)
