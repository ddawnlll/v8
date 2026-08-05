"""V8 assumption registry and verified-findings-only impact mapping."""

from .assumptions import attach_finding, new_assumption
from .impact_mapper import UnverifiedFindingError, map_to_v8
from .proposal_compiler import compile_proposal, no_compilation

__all__ = [
    "UnverifiedFindingError",
    "attach_finding",
    "compile_proposal",
    "map_to_v8",
    "new_assumption",
    "no_compilation",
]
