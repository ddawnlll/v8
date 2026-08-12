"""Gate 3 (AGENT_RUNBOOK section 4): no forbidden component identifiers.

The gated components (router, learned scorer, ranker, learned/RL execution)
are ABSENT by default (V8_CONSTITUTION rules 6, 14) and this tool makes that
a CI property: any identifier naming one of them in `v8-core/src` or
`src/v8` fails the build. Prose in comments/docstrings that merely discusses
the forbidden components ("not a router") is not an identifier and does not
count. The vendored `simtruth/` tree is excluded.

Usage:  python3 tools/forbidden_names.py
Exit 0  no forbidden identifiers found
Exit 1  forbidden identifiers found (listed to stdout)
"""
from __future__ import annotations

import io
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = (ROOT / "v8-core" / "src", ROOT / "src" / "v8")
EXCLUDED_SEGMENTS = ("simtruth", "__pycache__")

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# router/scorer/ranker are matched as substrings (case-insensitive): no
# ordinary identifier in the scanned trees contains them, so any occurrence
# inside an identifier is a half-built gated component. "rl" IS a substring
# of ordinary identifiers (monte_carlo, early), so it is matched only as a
# whole component: bounded by start/underscore/digit on the left and by
# end/underscore/digit/uppercase (camelCase continuation) on the right.
_SUBSTRING = re.compile(r"(?:router|scorer|ranker)", re.IGNORECASE)
_RL_COMPONENT = re.compile(r"(?:^|_|[0-9])rl(?:$|_|[0-9]|[A-Z])",
                           re.IGNORECASE)

# Fallback strippers (used for Rust, and for Python files the tokenizer
# cannot parse). Order matters: comments before strings so a quote inside a
# comment cannot survive into the string pass.
_PY_COMMENTS_STRINGS = (
    (re.compile(r"#[^\n]*"), ""),
    (re.compile(r'"""(?:[^"\\]|\\.|"(?!""))*"""', re.DOTALL), ""),
    (re.compile(r"'''(?:[^'\\]|\\.|'(?!''))*'''", re.DOTALL), ""),
    (re.compile(r"'(?:[^'\\]|\\.)*'"), ""),
    (re.compile(r'"(?:[^"\\]|\\.)*"'), ""),
)
_RUST_COMMENTS_STRINGS = (
    (re.compile(r"//[^\n]*"), ""),
    (re.compile(r"/\*.*?\*/", re.DOTALL), ""),
    (re.compile(r"'(?:\\.|[^'\\])'"), ""),
    (re.compile(r'"(?:\\.|[^"\\])*"'), ""),
)


def _py_identifiers(text: str) -> list[tuple[str, int]]:
    """NAME tokens only; comments and string literals are dropped by the
    tokenizer, so docstring prose never counts as an identifier."""
    try:
        toks = tokenize.generate_tokens(io.StringIO(text).readline)
        return [(t.string, t.start[0]) for t in toks if t.type == tokenize.NAME]
    except (tokenize.TokenError, IndentationError):
        return _regex_identifiers(text, "py")


def _rust_identifiers(text: str) -> list[tuple[str, int]]:
    return _regex_identifiers(text, "rs")


def _regex_identifiers(text: str, lang: str) -> list[tuple[str, int]]:
    rules = _PY_COMMENTS_STRINGS if lang == "py" else _RUST_COMMENTS_STRINGS
    for pat, repl in rules:
        text = pat.sub(repl, text)
    return [(m.group(), lineno)
            for lineno, line in enumerate(text.splitlines(), start=1)
            for m in _IDENT.finditer(line)]


def _scan() -> list[tuple[Path, int, str]]:
    hits = []
    for base in SCAN_DIRS:
        if not base.is_dir():
            print(f"skipping missing scan dir: {base}")
            continue
        for p in sorted(base.rglob("*")):
            if p.is_dir() or any(seg in EXCLUDED_SEGMENTS for seg in p.parts):
                continue
            if p.suffix == ".py":
                ids = _py_identifiers(p.read_text(encoding="utf-8"))
            elif p.suffix == ".rs":
                ids = _rust_identifiers(p.read_text(encoding="utf-8"))
            else:
                continue
            for name, lineno in ids:
                if _SUBSTRING.search(name) or _RL_COMPONENT.search(name):
                    hits.append((p, lineno, name))
    return hits


def main() -> int:
    hits = _scan()
    if not hits:
        print("forbidden component identifiers "
              "(router|scorer|ranker|RL): none found — OK")
        return 0
    print("forbidden component identifiers "
          "(V8_CONSTITUTION rules 6, 14; AGENT_RUNBOOK gate 3):")
    for p, lineno, name in hits:
        print(f"  {p.relative_to(ROOT)}:{lineno}: {name}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
