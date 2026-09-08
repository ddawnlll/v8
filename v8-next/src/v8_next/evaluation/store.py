"""Transactional research metadata, not an execution ledger or authority issuer."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class ResearchStore:
    def __init__(self, path: Path) -> None:
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS campaign_observations (
                campaign_id TEXT NOT NULL, observed_ns INTEGER NOT NULL,
                payload TEXT NOT NULL, digest TEXT NOT NULL,
                PRIMARY KEY(campaign_id, observed_ns));
            CREATE TABLE IF NOT EXISTS trials (
                trial_id TEXT PRIMARY KEY, family TEXT NOT NULL,
                policy_hash TEXT NOT NULL, dataset_hash TEXT NOT NULL,
                role TEXT NOT NULL, registered_ns INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS forward_plans (
                plan_id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                digest TEXT NOT NULL, registered_ns INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS dataset_windows (
                dataset_hash TEXT NOT NULL, instrument_id TEXT NOT NULL,
                start_ns INTEGER NOT NULL, end_ns INTEGER NOT NULL,
                PRIMARY KEY(dataset_hash, instrument_id));
            CREATE TABLE IF NOT EXISTS burns (
                lineage TEXT NOT NULL, dataset_hash TEXT NOT NULL,
                burned_ns INTEGER NOT NULL,
                PRIMARY KEY(lineage, dataset_hash));
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY, payload TEXT NOT NULL,
                digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS lifecycle (
                opportunity_id TEXT NOT NULL, sequence INTEGER NOT NULL,
                state TEXT NOT NULL, decision_ns INTEGER NOT NULL,
                reason TEXT NOT NULL,
                PRIMARY KEY(opportunity_id, sequence));
        """)

    def close(self) -> None:
        self.db.close()

    def record_campaign_observation(
        self, campaign_id: str, observed_ns: int, payload: dict[str, Any]
    ) -> None:
        """Persist native observations, not an independent order state machine."""
        text = canonical(payload)
        digest = hashlib.sha256(text.encode()).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute(
                "SELECT payload,digest FROM campaign_observations WHERE campaign_id=? AND observed_ns=?",
                (campaign_id, observed_ns),
            ).fetchone()
            if existing is not None:
                if existing != (text, digest):
                    raise ValueError("campaign observation replay diverged")
            else:
                latest = self.db.execute(
                    "SELECT MAX(observed_ns) FROM campaign_observations WHERE campaign_id=?",
                    (campaign_id,),
                ).fetchone()[0]
                if latest is not None and observed_ns < latest:
                    raise ValueError("campaign observation moved backwards")
                self.db.execute(
                    "INSERT INTO campaign_observations VALUES (?,?,?,?)",
                    (campaign_id, observed_ns, text, digest),
                )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def register_trial(
        self,
        trial_id: str,
        family: str,
        policy_hash: str,
        dataset_hash: str,
        role: str,
        registered_ns: int,
    ) -> None:
        if role not in {"DEVELOPMENT", "HOLDOUT", "PROSPECTIVE"}:
            raise ValueError("unknown data role")
        values = (trial_id, family, policy_hash, dataset_hash, role, registered_ns)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute(
                "SELECT * FROM trials WHERE trial_id=?", (trial_id,)
            ).fetchone()
            if existing is not None and existing != values:
                raise ValueError("trial identity cannot be rewritten")
            roles = {
                row[0]
                for row in self.db.execute(
                    "SELECT DISTINCT role FROM trials WHERE dataset_hash=?", (dataset_hash,)
                )
            }
            if (role == "HOLDOUT" and roles - {"HOLDOUT"}) or (
                role != "HOLDOUT" and "HOLDOUT" in roles
            ):
                raise ValueError("dataset cannot mix protected holdout and observed research roles")
            if existing is None:
                self.db.execute("INSERT INTO trials VALUES (?,?,?,?,?,?)", values)
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def register_dataset_window(
        self, dataset_hash: str, instrument_id: str, start_ns: int, end_ns: int
    ) -> None:
        """Conservative half-open source coverage, including feature warmup.

        This guards locally declared overlap, not unseen datasets or cross-asset
        information leakage. The caller derives coverage from verified input.
        """
        if not instrument_id or not 0 <= start_ns < end_ns:
            raise ValueError("invalid dataset coverage")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            roles = {
                r[0]
                for r in self.db.execute(
                    "SELECT DISTINCT role FROM trials WHERE dataset_hash=?", (dataset_hash,)
                )
            }
            if not roles:
                raise ValueError("register trial before dataset coverage")
            previous = self.db.execute(
                "SELECT start_ns,end_ns FROM dataset_windows WHERE dataset_hash=? AND instrument_id=?",
                (dataset_hash, instrument_id),
            ).fetchone()
            if previous is not None and previous != (start_ns, end_ns):
                raise ValueError("dataset coverage cannot be rewritten")
            overlapping = {
                r[0]
                for r in self.db.execute(
                    "SELECT DISTINCT t.role FROM dataset_windows w JOIN trials t "
                    "ON t.dataset_hash=w.dataset_hash WHERE w.instrument_id=? "
                    "AND w.start_ns < ? AND w.end_ns > ?",
                    (instrument_id, end_ns, start_ns),
                )
            }
            if ("HOLDOUT" in roles and overlapping - {"HOLDOUT"}) or (
                roles - {"HOLDOUT"} and "HOLDOUT" in overlapping
            ):
                raise ValueError("overlapping observed and holdout dataset windows")
            if previous is None:
                self.db.execute(
                    "INSERT INTO dataset_windows VALUES (?,?,?,?)",
                    (dataset_hash, instrument_id, start_ns, end_ns),
                )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def family_size(self, family: str) -> int:
        result = self.db.execute("SELECT COUNT(*) FROM trials WHERE family=?", (family,)).fetchone()
        return int(result[0])

    def burn_holdout(self, lineage: str, dataset_hash: str, decision_ns: int) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO burns VALUES (?,?,?)", (lineage, dataset_hash, decision_ns)
        )

    def holdout_pristine(self, lineage: str, dataset_hash: str) -> bool:
        return (
            self.db.execute(
                "SELECT 1 FROM burns WHERE lineage=? AND dataset_hash=?", (lineage, dataset_hash)
            ).fetchone()
            is None
        )

    def record_decision(self, decision_id: str, payload: dict[str, Any]) -> bool:
        """Idempotent replay accepts identical output only; divergent replay fails."""
        text = canonical(payload)
        digest = hashlib.sha256(text.encode()).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT payload,digest FROM decisions WHERE decision_id=?", (decision_id,)
            ).fetchone()
            if row is not None:
                if row != (text, digest):
                    raise ValueError("non-deterministic or corrupted decision replay")
                self.db.execute("COMMIT")
                return False
            self.db.execute("INSERT INTO decisions VALUES (?,?,?)", (decision_id, text, digest))
            if "decision_ns" in payload:
                self._expire_observed_opportunities(int(payload["decision_ns"]))
            opportunity = payload.get("opportunity")
            if opportunity is not None:
                opportunity_id = opportunity["opportunity_id"]
                decision_ns = int(payload["decision_ns"])
                previous = self.db.execute(
                    "SELECT sequence,state,decision_ns FROM lifecycle WHERE opportunity_id=? "
                    "ORDER BY sequence DESC LIMIT 1",
                    (opportunity_id,),
                ).fetchone()
                if previous is not None and decision_ns < previous[2]:
                    raise ValueError("opportunity observation moved backwards")
                if previous is None:
                    self.db.execute(
                        "INSERT INTO lifecycle VALUES (?,?,?,?,?)",
                        (opportunity_id, 0, "DETECTED", decision_ns, "GRAMMAR_OBSERVATION"),
                    )
                    self.db.execute(
                        "INSERT INTO lifecycle VALUES (?,?,?,?,?)",
                        (opportunity_id, 1, "PENDING", decision_ns, "AWAITING_ADMISSION"),
                    )
                    previous = (1, "PENDING", decision_ns)
                if previous[1] in {"DETECTED", "PENDING", "TRIGGERED"}:
                    terminal = None
                    if decision_ns >= opportunity["expires_ns"]:
                        terminal = "EXPIRED"
                    elif str(payload.get("reason", "")).startswith("REJECTED_"):
                        terminal = "REJECTED"
                    if terminal:
                        self.db.execute(
                            "INSERT INTO lifecycle VALUES (?,?,?,?,?)",
                            (
                                opportunity_id,
                                previous[0] + 1,
                                terminal,
                                decision_ns,
                                payload["reason"],
                            ),
                        )
            self.db.execute("COMMIT")
            return True
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _expire_observed_opportunities(self, decision_ns: int) -> None:
        """Advance observed deadlines inside the decision transaction, even without a signal.

        The transition time is when this process observes expiry, not a fabricated
        historical callback at the deadline. Submitted campaigns remain engine-owned.
        """
        due = self.db.execute(
            "SELECT DISTINCT json_extract(d.payload,'$.opportunity.opportunity_id'), "
            "l.sequence FROM decisions d JOIN lifecycle l ON l.opportunity_id = "
            "json_extract(d.payload,'$.opportunity.opportunity_id') "
            "WHERE json_extract(d.payload,'$.opportunity.expires_ns') <= ? "
            "AND l.state IN ('DETECTED','PENDING','TRIGGERED','ACCEPTED') "
            "AND l.decision_ns <= ? AND l.sequence = "
            "(SELECT MAX(sequence) FROM lifecycle WHERE opportunity_id=l.opportunity_id)",
            (decision_ns, decision_ns),
        ).fetchall()
        self.db.executemany(
            "INSERT INTO lifecycle VALUES (?,?,?,?,?)",
            [
                (identity, sequence + 1, "EXPIRED", decision_ns, "DEADLINE_OBSERVED")
                for identity, sequence in due
            ],
        )

    def transition(self, opportunity_id: str, state: str, decision_ns: int, reason: str) -> None:
        """Economic lifecycle only. Engine owns order/fill state separately."""
        allowed = {
            None: {"DETECTED"},
            "DETECTED": {"PENDING", "REJECTED", "EXPIRED", "INVALIDATED"},
            "PENDING": {"TRIGGERED", "REJECTED", "EXPIRED", "INVALIDATED"},
            "TRIGGERED": {"ACCEPTED", "REJECTED", "EXPIRED", "INVALIDATED"},
            "ACCEPTED": {"CAMPAIGN_SUBMITTED", "REJECTED", "EXPIRED", "INVALIDATED"},
            "CAMPAIGN_SUBMITTED": {"COMPLETED", "CANCELLED"},
        }
        self.db.execute("BEGIN IMMEDIATE")
        try:
            previous = self.db.execute(
                "SELECT sequence,state,decision_ns FROM lifecycle WHERE opportunity_id=? "
                "ORDER BY sequence DESC LIMIT 1",
                (opportunity_id,),
            ).fetchone()
            prior = previous[1] if previous else None
            if state not in allowed.get(prior, set()):
                raise ValueError("invalid or terminal lifecycle transition")
            if previous and decision_ns < previous[2]:
                raise ValueError("lifecycle time moved backwards")
            sequence = previous[0] + 1 if previous else 0
            self.db.execute(
                "INSERT INTO lifecycle VALUES (?,?,?,?,?)",
                (opportunity_id, sequence, state, decision_ns, reason),
            )
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
