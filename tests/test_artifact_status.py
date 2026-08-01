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
    promoted (rule 13). Pilots are FORMALIZED; DATA_BLOCKED backlog entries
    are blocked by design until derivatives tape."""
    data = yaml.safe_load((REPO / 'docs' / 'EXPERTS_REGISTRY.yaml').read_text())
    for entry in data['experts']:
        assert entry['status'] in EXPERT_PROTOCOL_STATUS
        assert entry['status'] in ('FORMALIZED', 'DATA_BLOCKED')
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


def test_noop_transition_allowed():
    assert legal_status_transition('research', 'research') == (True, 'no-op')
    assert legal_status_transition('live', 'live') == (True, 'no-op')


def test_live_positive_half_with_renewed_authority():
    """With a PASS + GRANTED certification, live becomes reachable and
    paper -> live is an allowed promotion with the renewed-authority
    evidence (OPERATIONS_SPEC section 1)."""
    renewed = {'certification': 'PASS', 'autopilot_permission': 'GRANTED',
               'live_reachable': True}
    assert certification_allows_live(renewed) is True
    ok, evidence = legal_status_transition('paper', 'live', cert=renewed)
    assert ok is True
    assert 'independently renewed simulation authority' in evidence


def test_unknown_current_and_full_demotion_matrix_rejected():
    assert legal_status_transition('nope', 'research')[0] is False
    assert legal_status_transition('shadow', 'research')[0] is False
    assert legal_status_transition('paper', 'shadow')[0] is False


def test_main_exit_code_with_renewed_cert(tmp_path):
    """main() returns 1 when live is reachable (fail-open side of the CLI)."""
    from tools.artifact_status import main
    renewed = tmp_path / 'cert.json'
    renewed.write_text(json.dumps({'certification': 'PASS',
                                   'autopilot_permission': 'GRANTED',
                                   'live_reachable': True}), encoding='utf-8')
    assert main(cert_path=renewed) == 1
