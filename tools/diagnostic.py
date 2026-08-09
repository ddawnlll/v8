"""Report-center shim (consolidated 2026-08-08).

The single report center is `tools/diagnostics.py` — the deterministic
diagnostic engine, its 9 sections, forensics, the multi-symbol matrix runner
and the HTML renderers all live there. This module re-exports the diagnostic
engine surface so existing imports and CLI invocations keep working.

The report itself is one self-contained file: `diagnostics.py`.
"""
from __future__ import annotations

from tools.diagnostics import *  # noqa: F401,F403
from tools.diagnostics import (  # noqa: F401
    DiagnosticEngine, run_diagnostic, write_report, _provenance,
    _guard_no_write, DiagnosticWriteError, SimTrade, _serialize, _render_md,
    ALL_EXPERT_CLASSES, main,
)

if __name__ == '__main__':
    raise SystemExit(main())
