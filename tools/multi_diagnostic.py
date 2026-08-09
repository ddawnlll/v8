"""Report-center shim (consolidated 2026-08-08).

The single report center is `tools/diagnostics.py` — including the multi-symbol
× multi-timeframe matrix runner (formerly this module). This shim re-exports
it for backward compatibility; there is no separate "multi" report anymore.
"""
from __future__ import annotations

from tools.diagnostics import *  # noqa: F401,F403
from tools.diagnostics import run_multi, render_multi_html, main  # noqa: F401

if __name__ == '__main__':
    raise SystemExit(main())
