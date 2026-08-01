"""Artifact status lifecycle + certification record (OPERATIONS_SPEC section 1).

The certification record parses and is FAIL/BLOCKED; live is unreachable;
promotions are adjacent-only with documented gates; nothing in the expert
registry is beyond FORMALIZED (nothing promoted, rule 13).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root for tools/

import yaml

from tools.artifact_status import (
    STATUS_VOCABULARY, certification_allows_live, legal_status_transition,
    load_certification,
)

REPO = Path(__file__).resolve().parents[1]
EXPERT_PROTOCOL_STATUS = ('PROPOSED', 'FORMALIZED', 'SCREENING', 'REPLICATION',
                          'SHADOW', 'PROMOTED', 'REJECTED', 'MERGED',
                          'QUARANTINED', 'DATA_BLOCKED')


def test_certification_record_parses_and_blocks_live():
    cert = load_certification()
    assert cert['certification'] == 'FAIL'
    assert cert['autopilot_permission'] == 'BLOCKED'
    assert cert['live_reachable'] is False
    assert certification_allows_live(cert) is False


def test_live_unreachable_without_renewed_authority():
    """paper -> live is blocked while the certification is FAIL (rule 12)."""
    ok, evidence = legal_status_transition('paper', 'live')
    assert ok is False
    assert 'live blocked' in evidence


def test_adjacent_promotions_with_evidence():
    ok, evidence = legal_status_transition('research', 'shadow')
    assert ok is True and 'registry experiment gate' in evidence
    ok, evidence = legal_status_transition('shadow', 'paper')
    assert ok is True and 'paper review' in evidence


def test_non_adjacent_and_unknown_rejected():
    assert legal_status_transition('research', 'paper')[0] is False
    assert legal_status_transition('live', 'research')[0] is False   # no demotion
    assert legal_status_transition('research', 'nope')[0] is False


def test_registry_nothing_promoted():
    """No pilot sits at or beyond the ops lifecycle statuses — the expert
    registry vocabulary is a separate axis (EXPERT_PROTOCOL 4) and nothing is
    promoted (rule 13)."""
    data = yaml.safe_load((REPO / 'docs' / 'EXPERTS_REGISTRY.yaml').read_text())
    for entry in data['experts']:
        assert entry['status'] in EXPERT_PROTOCOL_STATUS
        assert entry['status'] == 'FORMALIZED'
    # The ops vocabulary is exactly the OPERATIONS_SPEC four-status ladder.
    assert list(STATUS_VOCABULARY) == ['research', 'shadow', 'paper', 'live']


def test_certification_cli_fails_closed():
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(REPO / 'tools' / 'artifact_status.py')],
        capture_output=True, text=True, cwd=REPO)
    assert proc.returncode == 0            # exits 0 while live is unreachable
    out = json.loads(proc.stdout)
    assert out['live_reachable'] is False and out['autopilot_permission'] == 'BLOCKED'
