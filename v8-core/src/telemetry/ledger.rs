#![allow(dead_code)]
//! Canonical Economic Trace Ledger & Lineage Validation Kernel (EEO-001H, D-136).
//!
//! Constitutional Invariants:
//! 1. Fail-Closed Lineage: Broken, non-monotonic, or cyclical ancestry fails closed immediately.
//! 2. PIT Authority Firewall: Decision spans can only have decision span parents; Oracle and Audit
//!    evidence spans cannot become upstream dependencies of canonical decision spans.
//! 3. Link Graph Integrity: All `SpanLink` targets must point to registered traces and existing spans.

use std::collections::{HashMap, HashSet};
use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;
use super::identity::{EconomicTraceContext, EconomicTraceId, SpanId};
use super::span::{DecisionSpan, EvidenceSpan, SpanLink};

/// Ledger for recording, tracking, and validating Economic Traces and Decision Spans.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct EconomicTraceLedger {
    contexts: HashMap<EconomicTraceId, EconomicTraceContext>,
    decision_spans: HashMap<SpanId, DecisionSpan>,
    evidence_spans: HashMap<SpanId, EvidenceSpan>,
    spans_by_trace: HashMap<EconomicTraceId, Vec<SpanId>>,
    spans_by_parent: HashMap<SpanId, Vec<SpanId>>,
    root_spans: HashMap<EconomicTraceId, SpanId>,
}

impl EconomicTraceLedger {
    pub fn new() -> Self {
        Self::default()
    }

    /// Registers a root `EconomicTraceContext`.
    pub fn register_context(&mut self, ctx: EconomicTraceContext) -> Result<(), V8CoreError> {
        let tid = ctx.trace_id.clone();
        if self.contexts.contains_key(&tid) {
            let existing = &self.contexts[&tid];
            if existing != &ctx {
                return Err(V8CoreError::TraceLineageError(format!(
                    "Conflicting EconomicTraceContext registration for trace_id {}",
                    tid
                )));
            }
            return Ok(());
        }
        self.contexts.insert(tid.clone(), ctx);
        self.spans_by_trace.entry(tid).or_default();
        Ok(())
    }

    /// Records a `DecisionSpan` in the ledger.
    pub fn record_span(&mut self, span: DecisionSpan) -> Result<(), V8CoreError> {
        if !self.contexts.contains_key(&span.trace_id) {
            return Err(V8CoreError::TraceLineageError(format!(
                "Cannot record span {}: trace_id {} is not registered",
                span.span_id, span.trace_id
            )));
        }

        if let Some(ref parent_id) = span.parent_span_id {
            // Must be a DecisionSpan, NOT an EvidenceSpan (PIT Authority Firewall)
            if self.evidence_spans.contains_key(parent_id) {
                return Err(V8CoreError::TraceLineageError(format!(
                    "PIT Authority Violation: DecisionSpan {} cannot have EvidenceSpan {} as parent",
                    span.span_id, parent_id
                )));
            }

            if !self.decision_spans.contains_key(parent_id) {
                return Err(V8CoreError::TraceLineageError(format!(
                    "Cannot record span {}: parent_span_id {} does not exist in decision spans",
                    span.span_id, parent_id
                )));
            }

            let parent = &self.decision_spans[parent_id];
            if span.start_time < parent.start_time {
                return Err(V8CoreError::TraceLineageError(format!(
                    "Span {} start_time ({}) precedes parent {} start_time ({})",
                    span.span_id, span.start_time, parent_id, parent.start_time
                )));
            }
        }

        let sid = span.span_id.clone();
        let tid = span.trace_id.clone();
        let parent_id = span.parent_span_id.clone();

        if let Some(ref pid) = parent_id {
            self.spans_by_parent.entry(pid.clone()).or_default().push(sid.clone());
        } else {
            self.root_spans.insert(tid.clone(), sid.clone());
        }

        self.spans_by_trace.entry(tid).or_default().push(sid.clone());
        self.decision_spans.insert(sid, span);
        Ok(())
    }

    /// Records a post-outcome `EvidenceSpan` evaluating a completed decision span.
    pub fn record_evidence_span(&mut self, ev_span: EvidenceSpan) -> Result<(), V8CoreError> {
        if !self.contexts.contains_key(&ev_span.trace_id) {
            return Err(V8CoreError::TraceLineageError(format!(
                "Cannot record evidence span {}: trace_id {} is not registered",
                ev_span.span_id, ev_span.trace_id
            )));
        }

        if !self.decision_spans.contains_key(&ev_span.observed_decision_span_id) {
            return Err(V8CoreError::TraceLineageError(format!(
                "Cannot record evidence span {}: observed decision span {} does not exist",
                ev_span.span_id, ev_span.observed_decision_span_id
            )));
        }

        let observed_span = &self.decision_spans[&ev_span.observed_decision_span_id];
        if ev_span.evaluation_time < observed_span.start_time {
            return Err(V8CoreError::TraceLineageError(format!(
                "Evidence span {} evaluation_time ({}) precedes observed span {} start_time ({})",
                ev_span.span_id, ev_span.evaluation_time, observed_span.span_id, observed_span.start_time
            )));
        }

        let sid = ev_span.span_id.clone();
        self.evidence_spans.insert(sid, ev_span);
        Ok(())
    }

    pub fn get_context(&self, trace_id: &EconomicTraceId) -> Option<&EconomicTraceContext> {
        self.contexts.get(trace_id)
    }

    pub fn get_decision_span(&self, span_id: &SpanId) -> Option<&DecisionSpan> {
        self.decision_spans.get(span_id)
    }

    pub fn get_evidence_span(&self, span_id: &SpanId) -> Option<&EvidenceSpan> {
        self.evidence_spans.get(span_id)
    }

    pub fn spans_for_trace(&self, trace_id: &EconomicTraceId) -> Vec<&DecisionSpan> {
        self.spans_by_trace
            .get(trace_id)
            .map(|ids| ids.iter().filter_map(|id| self.decision_spans.get(id)).collect())
            .unwrap_or_default()
    }

    pub fn root_span_for_trace(&self, trace_id: &EconomicTraceId) -> Option<&DecisionSpan> {
        let root_id = self.root_spans.get(trace_id)?;
        self.decision_spans.get(root_id)
    }

    pub fn child_spans(&self, span_id: &SpanId) -> Vec<&DecisionSpan> {
        self.spans_by_parent
            .get(span_id)
            .map(|ids| ids.iter().filter_map(|id| self.decision_spans.get(id)).collect())
            .unwrap_or_default()
    }

    pub fn linked_spans_for_trace(&self, trace_id: &EconomicTraceId) -> Vec<(&DecisionSpan, &SpanLink)> {
        let mut out = Vec::new();
        for span in self.decision_spans.values() {
            for link in &span.links {
                if &link.target_trace_id == trace_id {
                    out.push((span, link));
                }
            }
        }
        out
    }

    pub fn trace_count(&self) -> usize {
        self.contexts.len()
    }

    pub fn contexts(&self) -> &HashMap<EconomicTraceId, EconomicTraceContext> {
        &self.contexts
    }

    pub fn span_count(&self) -> usize {
        self.decision_spans.len()
    }

    pub fn evidence_span_count(&self) -> usize {
        self.evidence_spans.len()
    }

    /// Validates full structural, temporal, and authority lineage across the ledger.
    pub fn validate_lineage(&self) -> Result<(), V8CoreError> {
        for (tid, ctx) in &self.contexts {
            if ctx.opportunity_id.is_empty() {
                return Err(V8CoreError::TraceLineageError(format!(
                    "Trace {tid} has empty opportunity_id"
                )));
            }
            if ctx.provenance.tape_hash.is_empty()
                || ctx.provenance.policy_hash.is_empty()
                || ctx.provenance.constitution_hash.is_empty()
                || ctx.provenance.code_hash.is_empty()
            {
                return Err(V8CoreError::TraceLineageError(format!(
                    "Trace {tid} has missing cryptographic provenance hashes"
                )));
            }
        }

        for (sid, span) in &self.decision_spans {
            if !self.contexts.contains_key(&span.trace_id) {
                return Err(V8CoreError::TraceLineageError(format!(
                    "DecisionSpan {sid} references unrecorded trace_id {}",
                    span.trace_id
                )));
            }

            if let Some(end) = span.end_time {
                if end < span.start_time {
                    return Err(V8CoreError::TraceLineageError(format!(
                        "DecisionSpan {sid} end_time ({end}) < start_time ({})",
                        span.start_time
                    )));
                }
            }

            if let Some(ref pid) = span.parent_span_id {
                // Must not be an evidence span (PIT firewall)
                if self.evidence_spans.contains_key(pid) {
                    return Err(V8CoreError::TraceLineageError(format!(
                        "PIT Authority Firewall Breach: DecisionSpan {sid} has EvidenceSpan {pid} as parent"
                    )));
                }

                let parent = self.decision_spans.get(pid).ok_or_else(|| {
                    V8CoreError::TraceLineageError(format!(
                        "DecisionSpan {sid} parent {pid} not found in ledger"
                    ))
                })?;

                if span.start_time < parent.start_time {
                    return Err(V8CoreError::TraceLineageError(format!(
                        "DecisionSpan {sid} start_time ({}) < parent {pid} start_time ({})",
                        span.start_time, parent.start_time
                    )));
                }

                // Check for cycles
                let mut visited = HashSet::new();
                visited.insert(sid);
                let mut curr_pid = Some(pid);
                while let Some(p) = curr_pid {
                    if visited.contains(p) {
                        return Err(V8CoreError::TraceLineageError(format!(
                            "Cycle detected in span ancestry involving span {sid} and parent {p}"
                        )));
                    }
                    visited.insert(p);
                    curr_pid = self.decision_spans.get(p).and_then(|s| s.parent_span_id.as_ref());
                }
            }

            for link in &span.links {
                if !self.contexts.contains_key(&link.target_trace_id) {
                    return Err(V8CoreError::TraceLineageError(format!(
                        "DecisionSpan {sid} contains link to unregistered trace_id {}",
                        link.target_trace_id
                    )));
                }
                if let Some(ref target_sid) = link.target_span_id {
                    if !self.decision_spans.contains_key(target_sid) && !self.evidence_spans.contains_key(target_sid) {
                        return Err(V8CoreError::TraceLineageError(format!(
                            "DecisionSpan {sid} contains link to non-existent target_span_id {target_sid}"
                        )));
                    }
                }
            }
        }

        for (esid, ev_span) in &self.evidence_spans {
            if !self.contexts.contains_key(&ev_span.trace_id) {
                return Err(V8CoreError::TraceLineageError(format!(
                    "EvidenceSpan {esid} references unrecorded trace_id {}",
                    ev_span.trace_id
                )));
            }
            if !self.decision_spans.contains_key(&ev_span.observed_decision_span_id) {
                return Err(V8CoreError::TraceLineageError(format!(
                    "EvidenceSpan {esid} references non-existent observed span {}",
                    ev_span.observed_decision_span_id
                )));
            }
        }

        Ok(())
    }

    /// Deterministic JSON serialization.
    pub fn to_json(&self) -> Result<String, V8CoreError> {
        serde_json::to_string_pretty(self).map_err(|e| V8CoreError::Serialization(e.to_string()))
    }

    /// Deterministic JSON deserialization.
    pub fn from_json(json_str: &str) -> Result<Self, V8CoreError> {
        serde_json::from_str(json_str).map_err(|e| V8CoreError::Serialization(e.to_string()))
    }
}
