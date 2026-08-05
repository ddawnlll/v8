"""Re-export of discovery prompts for the verification package.

Kept as a thin module (rather than a cross-import) so `verification` does not
need to reach into `discovery`'s internals -- the two packages share prompt
text but not implementation.
"""

from ..discovery.prompts import (
    CLAIM_EXTRACTION_SYSTEM,
    PROMPT_VERSIONS,
    VERIFICATION_SYSTEM,
)

__all__ = ["CLAIM_EXTRACTION_SYSTEM", "PROMPT_VERSIONS", "VERIFICATION_SYSTEM"]
