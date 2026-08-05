"""DuckDB analytical views over materialised artifacts.

A graph database is deferred until a measured workload needs recursive
traversal DuckDB cannot serve. Graph-shaped questions are answered here by
joining relational tables.
"""

from __future__ import annotations

import hashlib

from .paths import TABLES, Workspace

try:  # pragma: no cover - import guard
    import duckdb  # type: ignore

    AVAILABLE = True
except ImportError:  # pragma: no cover
    duckdb = None  # type: ignore[assignment]
    AVAILABLE = False


#: Views the specification names under "Logical graph views".
VIEW_SQL: dict[str, str] = {
    "claim_evidence": """
        SELECT c.claim_id, c.source_id, c.node_id, c.modality, c.epistemic_act,
               s.span_id, s.char_start, s.char_end, s.verbatim_text
        FROM claims c
        LEFT JOIN evidence_spans s
          ON list_contains(from_json(c.evidence_span_ids, '["VARCHAR"]'), s.span_id)
    """,
    "verified_claims": """
        SELECT c.*, v.verdict, v.entailed, v.modality_preserved, v.scope_supported
        FROM claims c
        JOIN claim_verifications v ON v.claim_id = c.claim_id
        WHERE v.entailed AND v.modality_preserved AND v.scope_supported
    """,
    "finding_lineages": """
        SELECT f.finding_id, f.status, f.preregistered_value,
               f.verification_quality, f.source_independence,
               len(from_json(f.source_ids, '["VARCHAR"]')) AS raw_source_count,
               len(from_json(f.independent_lineage_ids, '["VARCHAR"]')) AS independent_lineage_count
        FROM findings f
    """,
    "v8_impacts": """
        SELECT i.impact_id, i.relation, i.confidence,
               f.finding_id, f.finding_statement, f.status AS finding_status,
               a.assumption_id, a.statement AS assumption_statement, a.status AS assumption_status
        FROM v8_impact_edges i
        JOIN findings f ON f.finding_id = i.finding_id
        JOIN v8_assumptions a ON a.assumption_id = i.assumption_id
    """,
    "read_cost_by_purpose": """
        SELECT purpose, model_id, count(*) AS reads,
               sum(input_tokens) AS input_tokens,
               sum(output_tokens) AS output_tokens,
               sum(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits
        FROM read_receipts
        GROUP BY purpose, model_id
    """,
    "marks_by_channel": """
        SELECT unnest(from_json(discovery_channels, '["VARCHAR"]')) AS channel,
               count(*) AS marks
        FROM marks
        GROUP BY channel
    """,
}


def connect(workspace: Workspace):
    """Register every materialised table, then create the logical views."""
    if not AVAILABLE or duckdb is None:
        raise RuntimeError("duckdb is not installed; install the 'store' extra")
    con = duckdb.connect()
    registered: set[str] = set()
    for name in TABLES.values():
        path = workspace.parquet / f"{name}.parquet"
        if path.exists():
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
            registered.add(name)
    for view_name, sql in VIEW_SQL.items():
        try:
            con.execute(f"CREATE VIEW {view_name} AS {sql}")
        except Exception:
            # A view whose base tables are not materialised yet is skipped
            # rather than failing the whole connection.
            continue
    return con


def row_hashes(workspace: Workspace, table: str) -> list[str]:
    """Deterministic per-row hashes, used to prove rebuild reproducibility."""
    con = connect(workspace)
    try:
        rows = con.execute(f"SELECT * FROM {table} ORDER BY ALL").fetchall()
    finally:
        con.close()
    return [hashlib.sha256(repr(row).encode("utf-8")).hexdigest() for row in rows]
