"""Report-center shim (consolidated 2026-08-08).

The single report center is `tools/diagnostics.py`; this module re-exports the
HTML renderers for backward compatibility.
"""
from __future__ import annotations

from tools.diagnostics import *  # noqa: F401,F403
from tools.diagnostics import (  # noqa: F401
    render_html, _table, _verdict_badge, _fmt, _CSS, _PALETTE,
)
