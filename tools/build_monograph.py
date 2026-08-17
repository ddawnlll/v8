#!/usr/bin/env python3
"""Build the single-file V8 monograph from the docs/ corpus.

Reproducible: the same corpus + manifest + code produces byte-identical output.

Usage:
  python3 tools/build_monograph.py --lang en --docs docs --out site/index.html
  python3 tools/build_monograph.py --lang tr --docs docs/tr --out site/tr.html

The head templates (tools/heads/head_en.html, tools/heads/head_tr.html) carry
the fixed document-status section; every corpus file becomes one <section>;
the reading-list manifest becomes the final access-manifest table.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

import markdown

# Ordered by reading purpose; names are searched recursively under --docs so the
# same list works for docs/ (EN, nested) and docs/tr/ (TR, flat).
NAMES = [
    'V8_CONSTITUTION.md',
    'RESEARCH_AUDIT.md',
    'PROJECT_EVIDENCE_AUDIT.md',
    'PERFORMANCE_AUDIT_V82.md',
    'ARCHITECTURE_SPEC.md',
    'COMPUTE_CORE_SPEC.md',
    'COMPUTE_SCHEDULING_SPEC.md',
    'MARKET_STATE_CONTRACT.md',
    'EXPERT_PROTOCOL.md',
    'PREDICATE_IR_SPEC.md',
    'CANDIDATE_LIFECYCLE_SPEC.md',
    'DATASET_SPEC.md',
    'FEED_INGESTION_SPEC.md',
    'PERSISTENCE_REPLAY_SPEC.md',
    'PARITY_AND_IDENTITY_SPEC.md',
    'LEDGER_FORMAT_SPEC.md',
    'RUNTIME_SCHEDULER_SPEC.md',
    'SIMULATION_TRUTH_SPEC.md',
    'OUTCOME_CUBE_SPEC.md',
    'RECOVERABLE_REGRET_PROTOCOL.md',
    'HYPOTHESIS_LAB_PROTOCOL.md',
    'SWEEP_PROTOCOL.md',
    'OPERATIONS_SPEC.md',
    'LEARNING_PROTOCOL.md',
    'IMPLEMENTATION_LAYOUT.md',
    'DECISION_REGISTER.md',
    'OPEN_DECISIONS.md',
    'EVIDENCE_MATRIX.md',
    'CONTRADICTION_MAP.md',
    'SOURCE_MAP.md',
    'READING_LIST.md',
    'analysis_moe_selective.md',
    'analysis_survival_temporal.md',
    'analysis_validation_microstructure.md',
    'CHANGELOG.md',
    'ROADMAP.md',
    'AGENT_RUNBOOK.md',
    'COMPUTATION_BUDGET_POLICY.md',
    'PYTHON_ORACLE_POLICY.md',
    'CLAIMS_REGISTRY.yaml',
    'EXPERIMENT_REGISTRY.yaml',
    'EXPERTS_REGISTRY.yaml',
    'PREREGISTRATION_V8_SLICE_001.md',
]


def find(docs_dir: Path, name: str) -> Path | None:
    hits = list(docs_dir.rglob(name))
    return hits[0] if hits else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lang', choices=['en', 'tr'], default='en')
    ap.add_argument('--docs', required=True, help='corpus directory (docs or docs/tr)')
    ap.add_argument('--out', required=True, help='output HTML path')
    ap.add_argument(
        '--manifest',
        default='research/manifest/research_papers_manifest.json',
        help='reading-list access manifest (shared across languages)',
    )
    ap.add_argument('--head', default=None, help='head template (default tools/heads/head_<lang>.html)')
    args = ap.parse_args()

    head_path = Path(args.head or f'tools/heads/head_{args.lang}.html')
    head = head_path.read_text(encoding='utf-8')

    docs = Path(args.docs)
    # A Turkish reader must never receive a silently truncated monograph.  Keep
    # translated files authoritative, but include the matching English source
    # when a translation has not landed yet.  This is an explicit, visible
    # fallback—not a dropped section and not a build warning that CI ignores.
    fallback_docs = Path('docs') if args.lang == 'tr' else None
    sections = []
    toc_items = []
    for name in NAMES:
        p = find(docs, name)
        fallback = False
        if p is None and fallback_docs is not None:
            p = find(fallback_docs, name)
            fallback = p is not None
        if p is None:
            print(f'warning: {name} not found under {docs} — skipped', file=sys.stderr)
            continue
        title = html.escape(p.stem.replace('_', ' '))
        sec_id = 'sec-' + re.sub(r'[^a-z0-9]+', '-', p.stem.lower()).strip('-')
        if p.suffix == '.yaml':
            body = '<pre>' + html.escape(p.read_text(encoding='utf-8')) + '</pre>'
        else:
            body = markdown.markdown(
                p.read_text(encoding='utf-8'),
                extensions=['tables', 'fenced_code', 'sane_lists', 'toc'],
                output_format='html5',
            )
        fallback_note = (
            '<p><em>English source fallback: Turkish translation pending.</em></p>'
            if fallback else ''
        )
        sections.append(
            f'<section id="{sec_id}"><h1>{title}</h1>' + fallback_note + body + '</section>'
        )
        toc_items.append(f'<li><a href="#{sec_id}">{title}</a></li>')
    toc = '<nav id="toc"><h2>Contents</h2><ul>' + ''.join(toc_items) + '</ul></nav>'

    manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    rows = []
    for x in manifest:
        rows.append(
            '<tr><td>' + str(x['list_number']) + '</td><td>'
            + html.escape(x['title']) + '</td><td>'
            + html.escape(str(x.get('arxiv_id') or '—')) + '</td><td>'
            + html.escape(x['download_status']) + '</td><td><a href="'
            + html.escape(str(x.get('canonical_url') or '#')) + '">source</a></td></tr>'
        )
    source_table = (
        '<section><h1>Supplied 60-entry reading list: access manifest</h1>'
        '<table><tr><th>#</th><th>Title</th><th>arXiv</th><th>Access</th><th>Source</th></tr>'
        + ''.join(rows) + '</table></section>'
    )

    document = head + toc + '\n'.join(sections) + source_table + '</body></html>\n'
    # The final reader artifact must not depend on any separate Markdown artifact.
    document = re.sub(r'<a href="[^"]+\.md">([^<]+)</a>', r'\1', document)
    Path(args.out).write_text(document, encoding='utf-8')
    print(f'wrote {args.out}: sections={len(sections)} papers={len(manifest)} words={len(document.split())}')


if __name__ == '__main__':
    main()
