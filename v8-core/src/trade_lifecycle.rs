//! SB02 (#411) — trade lifecycle identity and single-unit cash settlement.
//!
//! Owning gap (measured in SB01, not assumed from the Python finding):
//! `ExecutionEvent` carries `execution_id` + `intent_id` but **no position,
//! order or lifecycle identity**, and no closed-round-trip record type exists
//! anywhere in the boundary. `EconomicCashflow` identifies a closed trade by
//! `(candidate_id, expert_id, symbol, direction, event_time)` only. Therefore a
//! reused venue `position_id` is not merely mishandled in the Rust path — it is
//! *unrepresentable*: two lifecycles under one id are indistinguishable, so the
//! Python #407 defect class cannot be detected, let alone proven, here.
//!
//! This module adds the missing identity without rewriting anything that is
//! already correct:
//!
//! * `RoundTripId` — a distinct identity per flat→non-flat→flat round trip,
//!   never the venue position id.
//! * `TradeLifecycle` — one round trip, accumulating partial entries/exits.
//! * `LifecycleLedger` — exactly-once fill application, partial close, netting
//!   reversal, duplicate suppression, out-of-order rejection, fee/funding
//!   exactly-once, and an equity reconciliation that is independent of the
//!   ledger's own arithmetic.
//! * `MoneyUsdt` / `RMultiple` / `EquityReturn` — money, risk unit and equity
//!   return stay in separate types (SB02 R3).
//!
//! Invariants that must never be violated:
//!   * a fill is attributed to exactly one lifecycle, and only by event order;
//!   * a closed lifecycle is immutable — a later fill for the same venue
//!     position id opens a NEW round trip, it never re-attributes the old one;
//!   * slippage embedded in a fill price is not deducted a second time;
//!   * a parse or attribution failure is an error, never a zero;
//!   * two different trades may legitimately carry equal PnL — that is not an
//!     error, correctness is proven by event attribution, not by value novelty.

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

use serde::{Deserialize, Serialize};

use crate::execution_boundary::{CashflowEvent, CashflowType, ExecutionEvent};

/// Money in USDT. Kept distinct from risk units and from equity returns so a
/// unit mix-up fails to compile instead of silently cancelling out (R3).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize, Default)]
pub struct MoneyUsdt(pub f64);

impl MoneyUsdt {
    pub fn zero() -> Self {
        MoneyUsdt(0.0)
    }
    pub fn value(self) -> f64 {
        self.0
    }
    pub fn add(self, other: MoneyUsdt) -> Self {
        MoneyUsdt(self.0 + other.0)
    }
    pub fn sub(self, other: MoneyUsdt) -> Self {
        MoneyUsdt(self.0 - other.0)
    }
    pub fn is_finite(self) -> bool {
        self.0.is_finite()
    }
}

impl fmt::Display for MoneyUsdt {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:.8} USDT", self.0)
    }
}

/// Risk unit: a PnL expressed in multiples of the trade's own initial risk.
/// It is *not* money and it is *not* a return; a missing initial risk stays
/// absent (`None`), never `0.0` (R3).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct RMultiple(pub f64);

/// Period equity return as a fraction of starting equity. Distinct from money
/// PnL and from the trade risk unit (R3).
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub struct EquityReturn(pub f64);

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Direction {
    Long,
    Short,
}

impl Direction {
    /// Parses a declared direction. An unknown token is an error, never a
    /// silent default (R3: an attribution failure must not become a value).
    pub fn parse(token: &str) -> Result<Direction, AttributionError> {
        match token {
            "LONG" => Ok(Direction::Long),
            "SHORT" => Ok(Direction::Short),
            other => Err(AttributionError::UnparsableDirection {
                token: other.to_string(),
            }),
        }
    }

    pub fn opposite(self) -> Direction {
        match self {
            Direction::Long => Direction::Short,
            Direction::Short => Direction::Long,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Direction::Long => "LONG",
            Direction::Short => "SHORT",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum FillAction {
    /// Increases the lifecycle in `direction`.
    Open,
    /// Decreases the lifecycle in `direction` (a close against that side).
    Close,
}

/// One attributed fill. Built only through `Fill::from_execution_event`, which
/// validates every field — there is no path that turns a malformed fill into a
/// zero-valued one.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Fill {
    pub execution_id: String,
    pub intent_id: String,
    pub venue_position_id: String,
    pub symbol: String,
    pub direction: Direction,
    pub action: FillAction,
    pub fill_time_ns: i64,
    pub fill_price: f64,
    pub fill_quantity: f64,
    pub fee_paid: f64,
}

impl Fill {
    /// Validating constructor from the existing boundary event.
    pub fn from_execution_event(
        event: &ExecutionEvent,
        direction: Direction,
        action: FillAction,
        venue_position_id: &str,
    ) -> Result<Fill, AttributionError> {
        if event.execution_id.trim().is_empty() {
            return Err(AttributionError::MissingExecutionId);
        }
        if event.symbol.trim().is_empty() {
            return Err(AttributionError::MissingSymbol {
                execution_id: event.execution_id.clone(),
            });
        }
        if venue_position_id.trim().is_empty() {
            return Err(AttributionError::MissingPositionId {
                execution_id: event.execution_id.clone(),
            });
        }
        if !event.fill_price.is_finite() || event.fill_price <= 0.0 {
            return Err(AttributionError::InvalidPrice {
                execution_id: event.execution_id.clone(),
                price: event.fill_price,
            });
        }
        if !event.fill_quantity.is_finite() || event.fill_quantity <= 0.0 {
            return Err(AttributionError::NonPositiveQuantity {
                execution_id: event.execution_id.clone(),
                quantity: event.fill_quantity,
            });
        }
        if !event.fee_paid.is_finite() {
            return Err(AttributionError::NonFiniteFee {
                execution_id: event.execution_id.clone(),
                fee: event.fee_paid,
            });
        }
        Ok(Fill {
            execution_id: event.execution_id.clone(),
            intent_id: event.intent_id.clone(),
            venue_position_id: venue_position_id.to_string(),
            symbol: event.symbol.clone(),
            direction,
            action,
            fill_time_ns: event.fill_time_ns,
            fill_price: event.fill_price,
            fill_quantity: event.fill_quantity,
            fee_paid: event.fee_paid,
        })
    }
}

/// Canonical attribution failures. Every variant is an explicit refusal; none
/// of them may be collapsed into a numeric zero anywhere downstream.
/// (`Eq` is not derivable: several variants carry the offending f64 value.)
#[derive(Debug, Clone, PartialEq)]
pub enum AttributionError {
    MissingExecutionId,
    MissingSymbol {
        execution_id: String,
    },
    MissingPositionId {
        execution_id: String,
    },
    UnparsableDirection {
        token: String,
    },
    InvalidPrice {
        execution_id: String,
        price: f64,
    },
    NonPositiveQuantity {
        execution_id: String,
        quantity: f64,
    },
    NonFiniteFee {
        execution_id: String,
        fee: f64,
    },
    OutOfOrderFill {
        execution_id: String,
        fill_time_ns: i64,
        last_event_ns: i64,
    },
    NoOpenLifecycleForClose {
        execution_id: String,
        venue_position_id: String,
    },
    OpenAgainstOppositeDirection {
        execution_id: String,
        lifecycle_direction: Direction,
        fill_direction: Direction,
    },
    UnknownRoundTrip {
        round_trip_id: String,
    },
    /// A fee cashflow names an execution whose fee was already applied. Applying
    /// both is a double cost basis (R4).
    DoubleCostBasis {
        reference_id: String,
    },
    NonFiniteCashflow {
        cashflow_id: String,
    },
}

impl fmt::Display for AttributionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AttributionError::MissingExecutionId => write!(f, "MISSING_EXECUTION_ID"),
            AttributionError::MissingSymbol { execution_id } => {
                write!(f, "MISSING_SYMBOL:{execution_id}")
            }
            AttributionError::MissingPositionId { execution_id } => {
                write!(f, "MISSING_POSITION_ID:{execution_id}")
            }
            AttributionError::UnparsableDirection { token } => {
                write!(f, "UNPARSABLE_DIRECTION:{token}")
            }
            AttributionError::InvalidPrice {
                execution_id,
                price,
            } => write!(f, "INVALID_PRICE:{execution_id}:{price}"),
            AttributionError::NonPositiveQuantity {
                execution_id,
                quantity,
            } => write!(f, "NON_POSITIVE_QUANTITY:{execution_id}:{quantity}"),
            AttributionError::NonFiniteFee { execution_id, fee } => {
                write!(f, "NON_FINITE_FEE:{execution_id}:{fee}")
            }
            AttributionError::OutOfOrderFill {
                execution_id,
                fill_time_ns,
                last_event_ns,
            } => write!(
                f,
                "OUT_OF_ORDER_FILL:{execution_id}:{fill_time_ns}<{last_event_ns}"
            ),
            AttributionError::NoOpenLifecycleForClose {
                execution_id,
                venue_position_id,
            } => write!(
                f,
                "NO_OPEN_LIFECYCLE_FOR_CLOSE:{execution_id}:{venue_position_id}"
            ),
            AttributionError::OpenAgainstOppositeDirection {
                execution_id,
                lifecycle_direction,
                fill_direction,
            } => write!(
                f,
                "OPEN_AGAINST_OPPOSITE_DIRECTION:{execution_id}:{}:{}",
                lifecycle_direction.as_str(),
                fill_direction.as_str()
            ),
            AttributionError::UnknownRoundTrip { round_trip_id } => {
                write!(f, "UNKNOWN_ROUND_TRIP:{round_trip_id}")
            }
            AttributionError::DoubleCostBasis { reference_id } => {
                write!(f, "DOUBLE_COST_BASIS:{reference_id}")
            }
            AttributionError::NonFiniteCashflow { cashflow_id } => {
                write!(f, "NON_FINITE_CASHFLOW:{cashflow_id}")
            }
        }
    }
}

impl std::error::Error for AttributionError {}

/// What applying one fill did to the ledger. Reported so a caller never has to
/// infer state changes from arithmetic.
#[derive(Debug, Clone, PartialEq)]
pub enum AttributionOutcome {
    Opened {
        round_trip_id: String,
    },
    Increased {
        round_trip_id: String,
    },
    PartiallyClosed {
        round_trip_id: String,
        realized: MoneyUsdt,
    },
    Closed {
        round_trip_id: String,
        realized: MoneyUsdt,
    },
    /// Netting reversal: the fill closed the open lifecycle and opened a new
    /// one, with its own identity, for the residual quantity.
    Reversed {
        closed: String,
        opened: String,
        residual_quantity: f64,
    },
    /// A repeated execution id: state is unchanged, and the suppression is
    /// recorded instead of silently ignored (R2).
    DuplicateSuppressed {
        execution_id: String,
    },
}

/// One round trip. Immutable once `state == Closed`, except for funding and
/// fee settlements that belong to its own event window.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TradeLifecycle {
    pub round_trip_id: String,
    /// The venue's own position id — explicitly allowed to be reused by the
    /// venue, which is exactly why it is not the identity used above.
    pub venue_position_id: String,
    pub symbol: String,
    pub direction: Direction,
    pub opened_at_ns: i64,
    pub closed_at_ns: Option<i64>,
    pub entry_quantity: f64,
    pub exit_quantity: f64,
    pub open_quantity: f64,
    pub entry_notional_usdt: f64,
    pub gross_realized_pnl_usdt: MoneyUsdt,
    pub fees_usdt: MoneyUsdt,
    pub funding_usdt: MoneyUsdt,
    pub net_realized_pnl_usdt: MoneyUsdt,
    /// Initial risk in USDT (entry-to-stop distance × quantity) when known.
    /// Absent stays absent: it is never coerced to zero (R3).
    pub initial_risk_usdt: Option<f64>,
    pub realized_r: Option<RMultiple>,
    pub entries: Vec<Fill>,
    pub exits: Vec<Fill>,
    pub closed: bool,
}

impl TradeLifecycle {
    pub fn average_entry_price(&self) -> Option<f64> {
        if self.entry_quantity > 0.0 {
            Some(self.entry_notional_usdt / self.entry_quantity)
        } else {
            None
        }
    }

    /// Mark-to-market PnL of the still-open quantity, kept separate from the
    /// realized figure (R3).
    pub fn mark_to_market_usdt(&self, current_price: f64) -> MoneyUsdt {
        let entry = match self.average_entry_price() {
            Some(p) => p,
            None => return MoneyUsdt::zero(),
        };
        let delta = match self.direction {
            Direction::Long => current_price - entry,
            Direction::Short => entry - current_price,
        };
        MoneyUsdt(delta * self.open_quantity)
    }

    fn reprice_derived(&mut self) {
        self.net_realized_pnl_usdt = self
            .gross_realized_pnl_usdt
            .sub(self.fees_usdt)
            .add(self.funding_usdt);
        self.realized_r = match self.initial_risk_usdt {
            Some(risk) if risk > 0.0 && self.closed => {
                Some(RMultiple(self.net_realized_pnl_usdt.value() / risk))
            }
            _ => None,
        };
    }
}

/// A cashflow that could not be applied, kept visible with its reason.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SuppressedEvent {
    pub event_id: String,
    pub reason: String,
}

#[derive(Debug, Clone, Default)]
pub struct LifecycleLedger {
    lifecycles: Vec<TradeLifecycle>,
    /// open lifecycle index per venue position id (last opened round trip)
    open_by_venue_position: BTreeMap<String, usize>,
    seen_execution_ids: BTreeSet<String>,
    /// execution ids whose fee was already applied through the fill itself.
    fee_settled_executions: BTreeSet<String>,
    suppressed: Vec<SuppressedEvent>,
    next_round_trip_seq: u64,
}

impl LifecycleLedger {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn lifecycles(&self) -> &[TradeLifecycle] {
        &self.lifecycles
    }

    pub fn suppressed(&self) -> &[SuppressedEvent] {
        &self.suppressed
    }

    /// Closed round trips only.
    pub fn closed_lifecycles(&self) -> Vec<&TradeLifecycle> {
        self.lifecycles.iter().filter(|l| l.closed).collect()
    }

    /// Open round trips only.
    pub fn open_lifecycles(&self) -> Vec<&TradeLifecycle> {
        self.lifecycles.iter().filter(|l| !l.closed).collect()
    }

    pub fn find(&self, round_trip_id: &str) -> Option<&TradeLifecycle> {
        self.lifecycles
            .iter()
            .find(|l| l.round_trip_id == round_trip_id)
    }

    pub fn total_realized_usdt(&self) -> MoneyUsdt {
        self.lifecycles
            .iter()
            .fold(MoneyUsdt::zero(), |acc, l| acc.add(l.net_realized_pnl_usdt))
    }

    /// Gross realized PnL across lifecycles, **before** fees and funding.
    ///
    /// The equity reconciliation subtracts fees and adds signed funding as
    /// separate terms, so it must start from the gross figure: using the net one
    /// there counts both twice. This module's own reconciliation test caught
    /// exactly that defect when it was first written.
    pub fn total_gross_realized_usdt(&self) -> MoneyUsdt {
        self.lifecycles.iter().fold(MoneyUsdt::zero(), |acc, l| {
            acc.add(l.gross_realized_pnl_usdt)
        })
    }

    pub fn total_fees_usdt(&self) -> MoneyUsdt {
        self.lifecycles
            .iter()
            .fold(MoneyUsdt::zero(), |acc, l| acc.add(l.fees_usdt))
    }

    pub fn total_funding_usdt(&self) -> MoneyUsdt {
        self.lifecycles
            .iter()
            .fold(MoneyUsdt::zero(), |acc, l| acc.add(l.funding_usdt))
    }

    pub fn total_open_mtm_usdt(&self, price_of: impl Fn(&str) -> Option<f64>) -> MoneyUsdt {
        self.lifecycles.iter().filter(|l| !l.closed).fold(
            MoneyUsdt::zero(),
            |acc, l| match price_of(&l.symbol) {
                Some(price) => acc.add(l.mark_to_market_usdt(price)),
                None => acc,
            },
        )
    }

    fn mint_round_trip_id(&mut self, symbol: &str) -> String {
        self.next_round_trip_seq += 1;
        format!("RT-{symbol}-{:06}", self.next_round_trip_seq)
    }

    fn open_lifecycle(
        &mut self,
        fill: &Fill,
        direction: Direction,
        quantity: f64,
        price: f64,
        initial_risk_usdt: Option<f64>,
    ) -> String {
        let round_trip_id = self.mint_round_trip_id(&fill.symbol);
        let mut lifecycle = TradeLifecycle {
            round_trip_id: round_trip_id.clone(),
            venue_position_id: fill.venue_position_id.clone(),
            symbol: fill.symbol.clone(),
            direction,
            opened_at_ns: fill.fill_time_ns,
            closed_at_ns: None,
            entry_quantity: quantity,
            exit_quantity: 0.0,
            open_quantity: quantity,
            entry_notional_usdt: price * quantity,
            gross_realized_pnl_usdt: MoneyUsdt::zero(),
            fees_usdt: MoneyUsdt::zero(),
            funding_usdt: MoneyUsdt::zero(),
            net_realized_pnl_usdt: MoneyUsdt::zero(),
            initial_risk_usdt,
            realized_r: None,
            entries: Vec::new(),
            exits: Vec::new(),
            closed: false,
        };
        lifecycle.entries.push(fill.clone());
        lifecycle.fees_usdt = MoneyUsdt(fill.fee_paid);
        lifecycle.reprice_derived();
        self.lifecycles.push(lifecycle);
        let index = self.lifecycles.len() - 1;
        self.open_by_venue_position
            .insert(fill.venue_position_id.clone(), index);
        round_trip_id
    }

    /// Applies one fill. The fill is bound to exactly one lifecycle, chosen by
    /// event order and side — never by the venue position id alone, which the
    /// venue may reuse.
    pub fn apply_fill(
        &mut self,
        fill: &Fill,
        initial_risk_usdt: Option<f64>,
    ) -> Result<AttributionOutcome, AttributionError> {
        // Exactly-once: a repeated execution id never moves state.
        if self.seen_execution_ids.contains(&fill.execution_id) {
            self.suppressed.push(SuppressedEvent {
                event_id: fill.execution_id.clone(),
                reason: "DUPLICATE_EXECUTION_ID".to_string(),
            });
            return Ok(AttributionOutcome::DuplicateSuppressed {
                execution_id: fill.execution_id.clone(),
            });
        }

        let open_index = self
            .open_by_venue_position
            .get(&fill.venue_position_id)
            .copied()
            .filter(|i| !self.lifecycles[*i].closed);
        self.apply_fill_inner(fill, open_index, initial_risk_usdt)?;
        self.seen_execution_ids.insert(fill.execution_id.clone());
        self.fee_settled_executions
            .insert(fill.execution_id.clone());

        // Report what happened.
        let index = self
            .open_by_venue_position
            .get(&fill.venue_position_id)
            .copied();
        let outcome = match (open_index, index) {
            (None, Some(i)) => AttributionOutcome::Opened {
                round_trip_id: self.lifecycles[i].round_trip_id.clone(),
            },
            (Some(before), Some(after)) if before == after => {
                let l = &self.lifecycles[after];
                if l.closed {
                    AttributionOutcome::Closed {
                        round_trip_id: l.round_trip_id.clone(),
                        realized: l.net_realized_pnl_usdt,
                    }
                } else if fill.action == FillAction::Close {
                    AttributionOutcome::PartiallyClosed {
                        round_trip_id: l.round_trip_id.clone(),
                        realized: l.net_realized_pnl_usdt,
                    }
                } else {
                    AttributionOutcome::Increased {
                        round_trip_id: l.round_trip_id.clone(),
                    }
                }
            }
            (Some(before), Some(after)) => {
                let closed = self.lifecycles[before].round_trip_id.clone();
                let opened = self.lifecycles[after].round_trip_id.clone();
                let residual = self.lifecycles[after].open_quantity;
                AttributionOutcome::Reversed {
                    closed,
                    opened,
                    residual_quantity: residual,
                }
            }
            (Some(before), None) => {
                let l = &self.lifecycles[before];
                AttributionOutcome::Closed {
                    round_trip_id: l.round_trip_id.clone(),
                    realized: l.net_realized_pnl_usdt,
                }
            }
            (None, None) => unreachable!("a fill always leaves an open lifecycle"),
        };
        Ok(outcome)
    }

    fn apply_fill_inner(
        &mut self,
        fill: &Fill,
        open_index: Option<usize>,
        initial_risk_usdt: Option<f64>,
    ) -> Result<(), AttributionError> {
        match (open_index, fill.action) {
            // Opening a round trip.
            (None, FillAction::Open) => {
                self.open_lifecycle(
                    fill,
                    fill.direction,
                    fill.fill_quantity,
                    fill.fill_price,
                    initial_risk_usdt,
                );
                Ok(())
            }
            // Closing with nothing open: refuse. Attribution is never zero.
            (None, FillAction::Close) => Err(AttributionError::NoOpenLifecycleForClose {
                execution_id: fill.execution_id.clone(),
                venue_position_id: fill.venue_position_id.clone(),
            }),
            (Some(index), FillAction::Open) => {
                if self.lifecycles[index].direction != fill.direction {
                    return Err(AttributionError::OpenAgainstOppositeDirection {
                        execution_id: fill.execution_id.clone(),
                        lifecycle_direction: self.lifecycles[index].direction,
                        fill_direction: fill.direction,
                    });
                }
                if fill.fill_time_ns < self.lifecycles[index].opened_at_ns {
                    return Err(AttributionError::OutOfOrderFill {
                        execution_id: fill.execution_id.clone(),
                        fill_time_ns: fill.fill_time_ns,
                        last_event_ns: self.lifecycles[index].opened_at_ns,
                    });
                }
                let l = &mut self.lifecycles[index];
                l.entry_quantity += fill.fill_quantity;
                l.open_quantity += fill.fill_quantity;
                l.entry_notional_usdt += fill.fill_price * fill.fill_quantity;
                l.fees_usdt = l.fees_usdt.add(MoneyUsdt(fill.fee_paid));
                l.entries.push(fill.clone());
                l.reprice_derived();
                Ok(())
            }
            (Some(index), FillAction::Close) => {
                let close_direction = self.lifecycles[index].direction;
                if fill.fill_time_ns < self.lifecycles[index].opened_at_ns {
                    return Err(AttributionError::OutOfOrderFill {
                        execution_id: fill.execution_id.clone(),
                        fill_time_ns: fill.fill_time_ns,
                        last_event_ns: self.lifecycles[index].opened_at_ns,
                    });
                }
                let open_quantity = self.lifecycles[index].open_quantity;
                let entry_price =
                    self.lifecycles[index]
                        .average_entry_price()
                        .ok_or_else(|| AttributionError::NoOpenLifecycleForClose {
                            execution_id: fill.execution_id.clone(),
                            venue_position_id: fill.venue_position_id.clone(),
                        })?;
                let closing_quantity = fill.fill_quantity.min(open_quantity);
                let residual = fill.fill_quantity - closing_quantity;

                {
                    let l = &mut self.lifecycles[index];
                    let delta = match close_direction {
                        Direction::Long => fill.fill_price - entry_price,
                        Direction::Short => entry_price - fill.fill_price,
                    };
                    l.gross_realized_pnl_usdt = l
                        .gross_realized_pnl_usdt
                        .add(MoneyUsdt(delta * closing_quantity));
                    l.fees_usdt = l.fees_usdt.add(MoneyUsdt(fill.fee_paid));
                    l.exit_quantity += closing_quantity;
                    l.open_quantity -= closing_quantity;
                    l.exits.push(fill.clone());
                    if l.open_quantity <= 0.0 {
                        l.open_quantity = 0.0;
                        l.closed = true;
                        l.closed_at_ns = Some(fill.fill_time_ns);
                    }
                    l.reprice_derived();
                }

                if residual > 0.0 {
                    // Netting reversal: the residual belongs to a NEW round trip
                    // with its own identity. The closed lifecycle above stays
                    // immutable; nothing is re-attributed to it.
                    let closed_clone = self.lifecycles[index].clone();
                    let mut residual_fill = fill.clone();
                    residual_fill.fill_quantity = residual;
                    // the entry fee of the residual leg is zero here: the fill's
                    // fee was charged once, to the closure above.
                    residual_fill.fee_paid = 0.0;
                    self.open_lifecycle(
                        &residual_fill,
                        close_direction.opposite(),
                        residual,
                        fill.fill_price,
                        None,
                    );
                    debug_assert_eq!(
                        closed_clone.round_trip_id,
                        self.lifecycles[index].round_trip_id
                    );
                }
                Ok(())
            }
        }
    }

    /// Applies a boundary cashflow event.
    ///
    /// * `FundingFee` is a signed cashflow (negative = paid) and is bound to the
    ///   open lifecycle of the referenced position when one exists.
    /// * `TradingFee` whose `reference_id` is an execution that already carried
    ///   `fee_paid` is refused as a double cost basis (R4).
    /// * `RealizedPnL` / `LiquidationFee` are not applied here: realized PnL is
    ///   derived from attributed fills, and applying it twice would double count.
    pub fn apply_cashflow(&mut self, cf: &CashflowEvent) -> Result<(), AttributionError> {
        if !cf.amount.is_finite() {
            return Err(AttributionError::NonFiniteCashflow {
                cashflow_id: cf.cashflow_id.clone(),
            });
        }
        match cf.cashflow_type {
            CashflowType::TradingFee | CashflowType::LiquidationFee => {
                if self.fee_settled_executions.contains(&cf.reference_id) {
                    return Err(AttributionError::DoubleCostBasis {
                        reference_id: cf.reference_id.clone(),
                    });
                }
                let index = self
                    .open_by_venue_position
                    .values()
                    .copied()
                    .find(|i| !self.lifecycles[*i].closed);
                match index {
                    Some(i) => {
                        let l = &mut self.lifecycles[i];
                        l.fees_usdt = l.fees_usdt.add(MoneyUsdt(cf.amount.abs()));
                        l.reprice_derived();
                        Ok(())
                    }
                    None => {
                        self.suppressed.push(SuppressedEvent {
                            event_id: cf.cashflow_id.clone(),
                            reason: "FEE_WITHOUT_OPEN_LIFECYCLE".to_string(),
                        });
                        Ok(())
                    }
                }
            }
            CashflowType::FundingFee => {
                let index = self
                    .open_by_venue_position
                    .values()
                    .copied()
                    .find(|i| !self.lifecycles[*i].closed);
                match index {
                    Some(i) => {
                        let l = &mut self.lifecycles[i];
                        l.funding_usdt = l.funding_usdt.add(MoneyUsdt(cf.amount));
                        l.reprice_derived();
                        Ok(())
                    }
                    None => {
                        self.suppressed.push(SuppressedEvent {
                            event_id: cf.cashflow_id.clone(),
                            reason: "FUNDING_WITHOUT_OPEN_LIFECYCLE".to_string(),
                        });
                        Ok(())
                    }
                }
            }
            CashflowType::RealizedPnL => {
                self.suppressed.push(SuppressedEvent {
                    event_id: cf.cashflow_id.clone(),
                    reason: "REALIZED_PNL_IS_DERIVED_FROM_FILLS".to_string(),
                });
                Ok(())
            }
        }
    }

    /// Independent equity reconciliation.
    ///
    /// `equity_end - equity_start = net cash transfer + gross realized Δ + MTM Δ
    ///  - fees + signed funding`, with fees and funding taken from separate
    ///  fields so neither can be counted twice. The realized term is the GROSS
    ///  figure: `total_realized_usdt()` is already net of fees and funding, so
    ///  feeding it here would double both. Slippage is not a term at all — the
    ///  fill price already carries it, and subtracting a slippage figure again
    ///  would double the cost basis (R4).
    pub fn reconcile_equity(
        &self,
        equity_start: f64,
        equity_end: f64,
        net_cash_transfer: f64,
        mark_to_market_pnl: f64,
        tolerance: f64,
    ) -> Result<ReconcileReport, String> {
        let realized = self.total_gross_realized_usdt().value();
        let fees = self.total_fees_usdt().value();
        let funding = self.total_funding_usdt().value();
        let expected_end =
            equity_start + net_cash_transfer + realized + mark_to_market_pnl - fees + funding;
        let drift = equity_end - expected_end;
        let report = ReconcileReport {
            equity_start,
            equity_end,
            net_cash_transfer,
            realized_pnl_usdt: realized,
            fees_usdt: fees,
            funding_usdt: funding,
            mark_to_market_pnl_usdt: mark_to_market_pnl,
            expected_equity_end: expected_end,
            drift_usdt: drift,
            tolerance,
            equity_return: if equity_start.abs() > f64::EPSILON {
                Some(EquityReturn((equity_end - equity_start) / equity_start))
            } else {
                None
            },
        };
        if drift.abs() > tolerance {
            return Err(format!(
                "EQUITY_RECONCILIATION_BREACH: drift {:.8} USDT exceeds tolerance {:.8}",
                drift, tolerance
            ));
        }
        Ok(report)
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ReconcileReport {
    pub equity_start: f64,
    pub equity_end: f64,
    pub net_cash_transfer: f64,
    pub realized_pnl_usdt: f64,
    pub fees_usdt: f64,
    pub funding_usdt: f64,
    pub mark_to_market_pnl_usdt: f64,
    pub expected_equity_end: f64,
    pub drift_usdt: f64,
    pub tolerance: f64,
    /// Money PnL and equity return are reported as different quantities.
    pub equity_return: Option<EquityReturn>,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn exec(id: &str, t: i64, px: f64, qty: f64, fee: f64) -> ExecutionEvent {
        ExecutionEvent {
            execution_id: id.to_string(),
            intent_id: format!("intent-{id}"),
            symbol: "BTCUSDT".to_string(),
            fill_time_ns: t,
            fill_price: px,
            fill_quantity: qty,
            fee_paid: fee,
            fee_currency: "USDT".to_string(),
        }
    }

    fn fill(
        id: &str,
        t: i64,
        px: f64,
        qty: f64,
        fee: f64,
        direction: Direction,
        action: FillAction,
        position_id: &str,
    ) -> Fill {
        Fill::from_execution_event(&exec(id, t, px, qty, fee), direction, action, position_id)
            .expect("valid fill fixture")
    }

    /// R1/R5 — the venue reuses one position id across two round trips. Two
    /// distinct lifecycle identities must result, and the first must stay
    /// immutable instead of absorbing the second entry.
    #[test]
    fn reused_venue_position_id_yields_two_distinct_round_trips() {
        let mut ledger = LifecycleLedger::new();
        let l = Direction::Long;
        // round trip 1: open then close
        ledger
            .apply_fill(
                &fill("e1", 10, 100.0, 1.0, 0.5, l, FillAction::Open, "POS-REUSED"),
                None,
            )
            .unwrap();
        let first_close = ledger
            .apply_fill(
                &fill(
                    "e2",
                    20,
                    110.0,
                    1.0,
                    0.5,
                    l,
                    FillAction::Close,
                    "POS-REUSED",
                ),
                None,
            )
            .unwrap();
        // round trip 2 under the SAME venue position id
        let second = ledger
            .apply_fill(
                &fill("e3", 30, 200.0, 2.0, 0.5, l, FillAction::Open, "POS-REUSED"),
                None,
            )
            .unwrap();

        let ids: Vec<String> = ledger
            .lifecycles()
            .iter()
            .map(|x| x.round_trip_id.clone())
            .collect();
        assert_eq!(ids.len(), 2, "two round trips must exist");
        assert_ne!(ids[0], ids[1], "round-trip identities must differ");
        assert_eq!(ledger.lifecycles()[0].closed, true);
        assert_eq!(ledger.lifecycles()[0].entry_quantity, 1.0);
        assert_eq!(ledger.lifecycles()[1].entry_quantity, 2.0);
        // the closed round trip keeps its own economics; it did not absorb e3
        assert_eq!(ledger.lifecycles()[0].gross_realized_pnl_usdt.value(), 10.0);
        match first_close {
            AttributionOutcome::Closed { realized, .. } => {
                assert!((realized.value() - 9.0).abs() < 1e-9)
            }
            other => panic!("expected Closed, got {other:?}"),
        }
        match second {
            AttributionOutcome::Opened { round_trip_id } => assert_eq!(round_trip_id, ids[1]),
            other => panic!("expected Opened, got {other:?}"),
        }
    }

    /// R2 — partial entry, partial exit, then full close.
    #[test]
    fn partial_entry_partial_exit_then_close_settles_once() {
        let mut ledger = LifecycleLedger::new();
        let l = Direction::Long;
        ledger
            .apply_fill(
                &fill("a", 1, 100.0, 1.0, 0.1, l, FillAction::Open, "P1"),
                None,
            )
            .unwrap();
        ledger
            .apply_fill(
                &fill("b", 2, 102.0, 1.0, 0.1, l, FillAction::Open, "P1"),
                None,
            )
            .unwrap();
        let partial = ledger
            .apply_fill(
                &fill("c", 3, 110.0, 1.0, 0.1, l, FillAction::Close, "P1"),
                None,
            )
            .unwrap();
        match partial {
            AttributionOutcome::PartiallyClosed { realized, .. } => {
                // avg entry 101, exit 110, qty 1 => gross 9, fees 0.3 => net 8.7
                assert!((realized.value() - 8.7).abs() < 1e-9, "{realized}");
            }
            other => panic!("expected PartiallyClosed, got {other:?}"),
        }
        assert_eq!(ledger.lifecycles()[0].open_quantity, 1.0);
        assert_eq!(ledger.lifecycles()[0].closed, false);
        ledger
            .apply_fill(
                &fill("d", 4, 90.0, 1.0, 0.1, l, FillAction::Close, "P1"),
                None,
            )
            .unwrap();
        let done = &ledger.lifecycles()[0];
        assert_eq!(done.closed, true);
        assert_eq!(done.open_quantity, 0.0);
        // gross = +9 then -11 => -2; fees 0.4 => net -2.4
        assert!((done.gross_realized_pnl_usdt.value() - (-2.0)).abs() < 1e-9);
        assert!((done.net_realized_pnl_usdt.value() - (-2.4)).abs() < 1e-9);
        assert!((ledger.total_realized_usdt().value() - (-2.4)).abs() < 1e-9);
    }

    /// R2 — netting reversal closes the open side and opens a new identity.
    #[test]
    fn netting_reversal_opens_a_new_round_trip_for_the_residual() {
        let mut ledger = LifecycleLedger::new();
        let l = Direction::Long;
        ledger
            .apply_fill(
                &fill("r1", 1, 100.0, 1.0, 0.0, l, FillAction::Open, "P9"),
                None,
            )
            .unwrap();
        let outcome = ledger
            .apply_fill(
                &fill("r2", 2, 120.0, 3.0, 0.0, l, FillAction::Close, "P9"),
                None,
            )
            .unwrap();
        match outcome {
            AttributionOutcome::Reversed {
                closed,
                opened,
                residual_quantity,
            } => {
                assert_ne!(closed, opened);
                assert!((residual_quantity - 2.0).abs() < 1e-9);
            }
            other => panic!("expected Reversed, got {other:?}"),
        }
        assert_eq!(ledger.lifecycles().len(), 2);
        let closed = &ledger.lifecycles()[0];
        let opened = &ledger.lifecycles()[1];
        assert_eq!(closed.closed, true);
        assert_eq!(
            closed.gross_realized_pnl_usdt.value(),
            20.0,
            "only the 1.0 closed"
        );
        assert_eq!(opened.direction, Direction::Short, "residual flips side");
        assert_eq!(opened.open_quantity, 2.0);
        assert_eq!(
            opened.venue_position_id, "P9",
            "same venue id, new identity"
        );
    }

    /// R2 — a repeated execution id never moves state.
    #[test]
    fn duplicate_execution_id_is_suppressed_not_double_counted() {
        let mut ledger = LifecycleLedger::new();
        let f = fill(
            "dup",
            1,
            100.0,
            1.0,
            0.7,
            Direction::Long,
            FillAction::Open,
            "P2",
        );
        ledger.apply_fill(&f, None).unwrap();
        let again = ledger.apply_fill(&f, None).unwrap();
        assert_eq!(
            again,
            AttributionOutcome::DuplicateSuppressed {
                execution_id: "dup".to_string()
            }
        );
        assert_eq!(ledger.lifecycles().len(), 1);
        assert_eq!(ledger.lifecycles()[0].entry_quantity, 1.0);
        assert_eq!(ledger.total_fees_usdt().value(), 0.7, "fee applied once");
        assert_eq!(ledger.suppressed().len(), 1);
    }

    /// R5 — two different trades with coincidentally equal PnL are accepted:
    /// correctness is proven by event attribution, not by value novelty.
    #[test]
    fn equal_pnl_on_two_different_trades_is_not_an_error() {
        let mut ledger = LifecycleLedger::new();
        let l = Direction::Long;
        ledger
            .apply_fill(
                &fill("t1a", 1, 100.0, 1.0, 0.0, l, FillAction::Open, "PA"),
                None,
            )
            .unwrap();
        ledger
            .apply_fill(
                &fill("t1b", 2, 110.0, 1.0, 0.0, l, FillAction::Close, "PA"),
                None,
            )
            .unwrap();
        ledger
            .apply_fill(
                &fill("t2a", 3, 500.0, 1.0, 0.0, l, FillAction::Open, "PB"),
                None,
            )
            .unwrap();
        ledger
            .apply_fill(
                &fill("t2b", 4, 510.0, 1.0, 0.0, l, FillAction::Close, "PB"),
                None,
            )
            .unwrap();
        let closed = ledger.closed_lifecycles();
        assert_eq!(closed.len(), 2);
        assert_eq!(
            closed[0].net_realized_pnl_usdt,
            closed[1].net_realized_pnl_usdt
        );
        assert_ne!(closed[0].round_trip_id, closed[1].round_trip_id);
        // attribution, not value novelty, is what makes them distinct
        assert_eq!(closed[0].entries[0].execution_id, "t1a");
        assert_eq!(closed[1].entries[0].execution_id, "t2a");
    }

    /// R3 — a parse/attribution failure is an error, never a zero.
    #[test]
    fn attribution_failures_are_never_zero_valued() {
        assert_eq!(
            Direction::parse("FLAT").unwrap_err(),
            AttributionError::UnparsableDirection {
                token: "FLAT".to_string()
            }
        );
        let bad_price = Fill::from_execution_event(
            &exec("x", 1, f64::NAN, 1.0, 0.0),
            Direction::Long,
            FillAction::Open,
            "P",
        );
        assert!(matches!(
            bad_price,
            Err(AttributionError::InvalidPrice { .. })
        ));
        let zero_qty = Fill::from_execution_event(
            &exec("y", 1, 100.0, 0.0, 0.0),
            Direction::Long,
            FillAction::Open,
            "P",
        );
        assert!(matches!(
            zero_qty,
            Err(AttributionError::NonPositiveQuantity { .. })
        ));
        let missing_pos = Fill::from_execution_event(
            &exec("z", 1, 100.0, 1.0, 0.0),
            Direction::Long,
            FillAction::Open,
            "   ",
        );
        assert!(matches!(
            missing_pos,
            Err(AttributionError::MissingPositionId { .. })
        ));
        // a close with nothing open is refused rather than booked as zero PnL
        let mut ledger = LifecycleLedger::new();
        let orphan = fill(
            "orphan",
            5,
            100.0,
            1.0,
            0.0,
            Direction::Long,
            FillAction::Close,
            "P3",
        );
        assert!(matches!(
            ledger.apply_fill(&orphan, None),
            Err(AttributionError::NoOpenLifecycleForClose { .. })
        ));
        assert_eq!(ledger.lifecycles().len(), 0);
        assert_eq!(ledger.total_realized_usdt().value(), 0.0);
    }

    /// R4 — a fee cashflow for an execution that already carried `fee_paid` is
    /// a double cost basis and is refused.
    #[test]
    fn fee_is_settled_exactly_once() {
        let mut ledger = LifecycleLedger::new();
        ledger
            .apply_fill(
                &fill(
                    "f1",
                    1,
                    100.0,
                    1.0,
                    0.75,
                    Direction::Long,
                    FillAction::Open,
                    "PF",
                ),
                None,
            )
            .unwrap();
        assert_eq!(ledger.total_fees_usdt().value(), 0.75);
        let duplicate_fee = CashflowEvent {
            cashflow_id: "cf-1".to_string(),
            reference_id: "f1".to_string(),
            event_time_ns: 2,
            cashflow_type: CashflowType::TradingFee,
            amount: -0.75,
            currency: "USDT".to_string(),
        };
        assert_eq!(
            ledger.apply_cashflow(&duplicate_fee),
            Err(AttributionError::DoubleCostBasis {
                reference_id: "f1".to_string()
            })
        );
        assert_eq!(
            ledger.total_fees_usdt().value(),
            0.75,
            "fee must not be applied twice"
        );
    }

    /// R4 — funding is signed and separate; slippage is never a second term.
    #[test]
    fn funding_is_signed_and_slippage_is_not_deducted_twice() {
        let mut ledger = LifecycleLedger::new();
        ledger
            .apply_fill(
                &fill(
                    "g1",
                    1,
                    100.0,
                    1.0,
                    0.0,
                    Direction::Long,
                    FillAction::Open,
                    "PG",
                ),
                None,
            )
            .unwrap();
        let funding = CashflowEvent {
            cashflow_id: "cf-fund".to_string(),
            reference_id: "g1".to_string(),
            event_time_ns: 2,
            cashflow_type: CashflowType::FundingFee,
            amount: -0.25,
            currency: "USDT".to_string(),
        };
        ledger.apply_cashflow(&funding).unwrap();
        assert_eq!(ledger.total_funding_usdt().value(), -0.25);
        // realized PnL comes from attributed fills only: no slippage term exists
        // that could subtract the cost already inside the fill price.
        ledger
            .apply_fill(
                &fill(
                    "g2",
                    3,
                    105.0,
                    1.0,
                    0.0,
                    Direction::Long,
                    FillAction::Close,
                    "PG",
                ),
                None,
            )
            .unwrap();
        let trade = ledger.closed_lifecycles()[0];
        assert_eq!(trade.gross_realized_pnl_usdt.value(), 5.0);
        assert_eq!(trade.net_realized_pnl_usdt.value(), 4.75);
        // equity reconciliation: start 1000, end 1004.75, no transfers
        let report = ledger
            .reconcile_equity(1000.0, 1004.75, 0.0, 0.0, 1e-6)
            .unwrap();
        // the realized term is gross (5.00); fees and funding are separate
        // terms, so net (4.75) is not repeated anywhere in the sum
        assert_eq!(report.realized_pnl_usdt, 5.0);
        assert_eq!(report.fees_usdt, 0.0);
        assert_eq!(report.funding_usdt, -0.25);
        assert_eq!(report.expected_equity_end, 1004.75);
        assert_eq!(report.drift_usdt, 0.0);
        assert_eq!(report.equity_return, Some(EquityReturn(0.00475)));
        // a 0.5 slippage subtraction would breach the reconciliation
        assert!(ledger
            .reconcile_equity(1000.0, 1004.25, 0.0, 0.0, 1e-6)
            .is_err());
        // feeding the net figure into the realized term would double-count the
        // funding; the gross accessor is what keeps that impossible
        assert_eq!(ledger.total_realized_usdt().value(), 4.75);
        assert_eq!(ledger.total_gross_realized_usdt().value(), 5.0);
    }

    /// R3 — realized and mark-to-market are separate; an open trade reports MTM
    /// while its realized figure stays untouched.
    #[test]
    fn open_position_keeps_mtm_separate_from_realized() {
        let mut ledger = LifecycleLedger::new();
        ledger
            .apply_fill(
                &fill(
                    "m1",
                    1,
                    100.0,
                    2.0,
                    0.0,
                    Direction::Long,
                    FillAction::Open,
                    "PM",
                ),
                Some(50.0),
            )
            .unwrap();
        let open = ledger.open_lifecycles()[0];
        assert_eq!(open.net_realized_pnl_usdt.value(), 0.0);
        assert_eq!(open.mark_to_market_usdt(103.0).value(), 6.0);
        assert_eq!(open.realized_r, None, "unrealized trade has no realized R");
        // missing initial risk stays absent, not zero
        let mut other = LifecycleLedger::new();
        other
            .apply_fill(
                &fill(
                    "m2",
                    1,
                    100.0,
                    1.0,
                    0.0,
                    Direction::Long,
                    FillAction::Open,
                    "PN",
                ),
                None,
            )
            .unwrap();
        other
            .apply_fill(
                &fill(
                    "m3",
                    2,
                    90.0,
                    1.0,
                    0.0,
                    Direction::Long,
                    FillAction::Close,
                    "PN",
                ),
                None,
            )
            .unwrap();
        assert_eq!(other.closed_lifecycles()[0].initial_risk_usdt, None);
        assert_eq!(other.closed_lifecycles()[0].realized_r, None);
    }

    /// R2/R3 — an out-of-order fill is refused instead of being re-ordered.
    #[test]
    fn out_of_order_fill_is_refused() {
        let mut ledger = LifecycleLedger::new();
        ledger
            .apply_fill(
                &fill(
                    "o1",
                    100,
                    100.0,
                    1.0,
                    0.0,
                    Direction::Long,
                    FillAction::Open,
                    "PO",
                ),
                None,
            )
            .unwrap();
        let late = fill(
            "o2",
            50,
            101.0,
            1.0,
            0.0,
            Direction::Long,
            FillAction::Open,
            "PO",
        );
        assert!(matches!(
            ledger.apply_fill(&late, None),
            Err(AttributionError::OutOfOrderFill { .. })
        ));
        assert_eq!(ledger.lifecycles()[0].entry_quantity, 1.0);
    }

    /// R4 — realized PnL arriving as its own cashflow is refused: the ledger
    /// derives it from fills, so applying it again would double count.
    #[test]
    fn realized_pnl_cashflow_is_not_applied_on_top_of_fill_attribution() {
        let mut ledger = LifecycleLedger::new();
        ledger
            .apply_fill(
                &fill(
                    "q1",
                    1,
                    100.0,
                    1.0,
                    0.0,
                    Direction::Long,
                    FillAction::Open,
                    "PQ",
                ),
                None,
            )
            .unwrap();
        let realized = CashflowEvent {
            cashflow_id: "cf-rp".to_string(),
            reference_id: "q1".to_string(),
            event_time_ns: 2,
            cashflow_type: CashflowType::RealizedPnL,
            amount: 10.0,
            currency: "USDT".to_string(),
        };
        ledger.apply_cashflow(&realized).unwrap();
        assert_eq!(ledger.total_realized_usdt().value(), 0.0);
        assert_eq!(ledger.suppressed().len(), 1);
        assert_eq!(
            ledger.suppressed()[0].reason,
            "REALIZED_PNL_IS_DERIVED_FROM_FILLS"
        );
    }
}
