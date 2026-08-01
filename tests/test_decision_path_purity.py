"""Decision-path purity (V8_CONSTITUTION rules 12, 14, 15; IMPLEMENTATION_LAYOUT 3).

The gated components (router, learned scorer, ranker, learned/RL execution,
online learning) are ABSENT by default and this test makes that a property,
not a convention: the decision path stays stdlib-only, clock-free, and
learner-free, so Phases 5 (gated components) and 7 (learning plane) cannot be
half-built by accident. These are the fail-closed probes for work that is
forbidden until Phase-4 evidence / certified edge exists.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / 'src' / 'v8'

# Learned/routing libraries that must never enter the decision path.
LEARNER_IMPORTS = ('numpy', 'scipy', 'sklearn', 'torch', 'tensorflow',
                   'pandas', 'polars', 'pyarrow', 'duckdb', 'joblib')
# Real wall-clock reads (not the word "time" in a docstring).
CLOCK_READS = re.compile(r'\b(time\.time|time\.time_ns|time\.monotonic|'
                         r'datetime\.now|datetime\.utcnow)\b')
# Component definitions, not prose: a class/def whose name names a gated
# component would be a half-built Phase-5/7 artifact.
COMPONENT_DEF = re.compile(r'\b(?:class|def)\s+[A-Za-z_0-9]*(?:router|scorer|'
                           r'ranker|bandit|policy_gradient|reinforcement)',
                           re.IGNORECASE)


def _decision_files():
    files = [p for p in SRC.rglob('*.py') if 'simtruth' not in str(p)]
    # Guard against vacuous passes: if the decision path is ever emptied, the
    # loop-based purity tests must FAIL, not pass with zero assertions.
    assert files, f'no decision-path files found under {SRC}'
    return files


def test_decision_path_is_stdlib_only():
    for p in _decision_files():
        text = p.read_text(encoding='utf-8')
        for mod in LEARNER_IMPORTS:
            assert f'import {mod}' not in text and f'from {mod}' not in text, \
                f'{p} imports {mod}'


def test_decision_path_has_no_wall_clock():
    for p in _decision_files():
        text = p.read_text(encoding='utf-8')
        assert not CLOCK_READS.search(text), f'{p} reads the wall clock'


def test_no_gated_component_definitions():
    for p in _decision_files():
        text = p.read_text(encoding='utf-8')
        assert not COMPONENT_DEF.search(text), \
            f'{p} defines a gated component (Phase 5/7 name)'


def test_no_gated_component_modules():
    for p in SRC.rglob('*.py'):
        if 'simtruth' in str(p):
            continue
        assert not re.search(r'(?:router|scorer|ranker|_rl)\.py$', p.name), \
            f'gated component module exists: {p}'


def test_authority_and_verdict_gate():
    """The economic verdict stays blocked without an authority receipt and the
    certification keeps live unreachable — the fail-closed spine of rules 8-9
    and 12 (exercised end-to-end by the golden regression's verdict)."""
    from tools.artifact_status import certification_allows_live
    assert certification_allows_live() is False
