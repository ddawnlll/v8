"""Artifact status lifecycle (OPERATIONS_SPEC section 1).

research -> shadow -> paper -> live, with promotion gates — the automation
side of the registry's shadow/paper status (EXPERT_PROTOCOL section 4). Live
is unreachable while the simulation authority certification is FAIL/BLOCKED;
shadow and paper run the same code path (a single Lab.run; the fill source is
a manifest input, not a separate codebase).

The lifecycle is a deterministic state machine with the required evidence per
promotion. It adds no component to the decision path.
"""
from __future__ import annotations

import json
from pathlib import Path

STATUS_VOCABULARY = ('research', 'shadow', 'paper', 'live')

CERTIFICATION_PATH = Path(__file__).resolve().parents[1] / 'research' / \
    'certification' / 'simulation_authority_certification_v1.json'

# Required evidence per promotion target (OPERATIONS_SPEC section 1).
PROMOTION_EVIDENCE = {
    'research': 'preregistered hypothesis + frozen spec + canonical simulation',
    'shadow': 'registry experiment gate passed',
    'paper': 'paper review: backtest config, shadow results, risk limits',
    'live': 'independently renewed simulation authority (autopilot permission)',
}


def load_certification(path: Path = CERTIFICATION_PATH) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def certification_allows_live(cert: dict | None = None) -> bool:
    """Live is reachable only with PASS + GRANTED (OPERATIONS_SPEC section 1)."""
    cert = cert if cert is not None else load_certification()
    return cert.get('certification') == 'PASS' \
        and cert.get('autopilot_permission') == 'GRANTED'


def legal_status_transition(current: str, target: str,
                            cert: dict | None = None) -> tuple[bool, str]:
    """(allowed, required evidence). Adjacent promotions only; live is blocked
    while the certification is FAIL/BLOCKED."""
    if current not in STATUS_VOCABULARY or target not in STATUS_VOCABULARY:
        return False, f'unknown status {current!r} -> {target!r}'
    if current == target:
        return True, 'no-op'
    index = {s: i for i, s in enumerate(STATUS_VOCABULARY)}
    if index[target] != index[current] + 1:
        return False, f'non-adjacent promotion {current} -> {target}'
    if target == 'live' and not certification_allows_live(cert):
        return False, f'live blocked: {CERTIFICATION_PATH.name} is not PASS/GRANTED'
    return True, PROMOTION_EVIDENCE[target]


def main(cert_path: Path = CERTIFICATION_PATH) -> int:
    cert = load_certification(cert_path)
    print(json.dumps({'certification': cert.get('certification'),
                      'autopilot_permission': cert.get('autopilot_permission'),
                      'live_reachable': certification_allows_live(cert),
                      'path': str(cert_path)}, sort_keys=True))
    return 0 if not certification_allows_live(cert) else 1


if __name__ == '__main__':
    raise SystemExit(main())
