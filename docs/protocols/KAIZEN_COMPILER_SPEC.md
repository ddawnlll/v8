# V8 Kaizen Research Compiler Specification (v8.kaizen.compiler.v1)

**Status:** ACTIVE_SPECIFICATION / LOCKED_INVARIANT  
**Scope:** Defines the complete specification for the V8 Kaizen Continuous Improvement system as a **Research Compiler and Falsification Substrate** (rather than a naive parameter optimizer).

---

## 1. Paradigm: Research Compiler vs Parameter Optimizer

Continuous improvement (Kaizen) in quantitative finance cannot be framed as a naive optimization loop:
$$\text{NEVER: } \text{while } \text{pnl} < \text{target}: \text{optimize\_parameters\_harder}()$$

Doing so creates severe backtest overfitting, selection bias, and strategy fragility. Under V8, Kaizen is strictly codified as a **falsification and hypothesis compilation pipeline**:

```
Evaluation Bundle
       │
       ▼
KZ-001: Forensics & Failure Taxonomy (Gross vs Friction vs Regime)
       │
       ▼
KZ-002: Immutable Hypotheses & Finite Challenger Families (Research Debt Accounting)
       │
       ▼
KZ-003: DEV Robustness Surfaces (AlgoXpert Plateau Search & Cliff Veto)
       │
       ▼
KZ-004: Purged WFA + Catastrophic Veto + ONE-SHOT Frozen OOS Burn
       │
       ▼
Shadow Evaluation / Replication
       │
       ▼
Registry Decision (PROMOTE | REJECT | QUARANTINE)
```

---

## 2. KZ-001: Expert Forensics & Failure Taxonomy

The first step of Kaizen is never deleting or blindly muting an expert. It is **diagnosing the exact failure mechanism**:

### 2.1 Forensic Metrics (`ExpertForensics`)
For every active and historical expert:
- `gross_r`: Realized expectancy before any trading friction.
- `fee_r`, `slippage_r`, `funding_r`: Decomposition of execution drag.
- `net_r`: Realized post-friction expectancy ($R_{\text{net}} = R_{\text{gross}} - (\text{fees} + \text{slippage} + \text{funding})$).
- `turnover` & `execution_share`: Capital and slot utilization.
- `mean_mae_r` & `mean_mfe_r`: Path dynamics and trade excursion profiles.
- `break_even_cost_bps`: The maximum execution cost friction sustainable before the edge turns negative.
- `regime_breakdown`: Performance sliced across volatility, trend, and liquidity regimes.

### 2.2 Deterministic Failure Taxonomy (`FailureClass`)

| Failure Class | Mathematical Condition | Diagnostic Meaning | Subsequent Research Target |
|---|---|---|---|
| `GrossNegative` | $\text{Gross } R < 0.0$ | Sinyal ve yön tahmini temelden zararda. | Sinyal, gösterge veya giriş tetiği mantığı (Execution değil). |
| `CostDominated` | $\text{Gross } R > 0.0 \land \text{Net } R \le 0.0$ | Brüt kâr var ancak komisyon/funding/kayma kârı yok ediyor. | Tradability mask, volatilite filtresi, tutma süresi veya emir tipi. |
| `ParameterFragile` | $\Delta \text{Expectancy} > 50\%$ on $\pm 5\%$ parameter change | Uçurum kenarında aşırı hassas parametre (Curve-fit). | Parametre plato araması (AlgoXpert). |
| `RegimeFragile` | $R_{\text{regime}_1} \gg 0 \land R_{\text{regime}_2} \ll -2R$ | Belirli bir piyasa rejiminde (örn. yatay piyasa) çöküş. | Rejim/habitat filtrelemesi ve piyasa durumu koşullandırması. |
| `AttributionUnsafe` | Drop rate $> 40\%$ due to slot/capacity contention | Sermaye veya slot çakışması nedeniyle atıf güvenliği bozuk. | Portföy tahsisatı ve çakışma kuralları. |
| `InsufficientEvidence` | $N_{\text{trades}} < N_{\min}$ | İstatistiki olarak anlamlı hipotez kuracak örneklem yok. | Gözlemde tutulur, müdahale edilmez. |
| `CandidateForReplication` | $\text{Net } R > 0.0 \land \text{Friction} < \text{Gross } R$ | Tüm maliyet sonrası pozitif beklenti. | Replikasyon ve WFA aşamasına ilerleme. |

*Literature Grounding:* Modern cost-model literature (arXiv:2603.29086) demonstrates that execution cost assumptions alter not only absolute returns but also the relative ranking and viability of algorithmic signals.

---

## 3. KZ-002: Hypothesis & Challenger Registry

### 3.1 Fundamental Invariant: Type-System Boundary
$$\text{OBSERVATION} \neq \text{CHANGE}, \quad \text{OBSERVATION} \longrightarrow \text{HYPOTHESIS}$$

Outcome data and diagnostic findings can **never** mutate the decision plane directly. Gözlemler (`ResearchFinding`) yalnızca immutable araştırma kayıtlarına (`HypothesisRecord`) derlenir.

```rust
pub struct HypothesisRecord {
    pub hypothesis_id: HypothesisId,
    pub parent_run: RunId,
    pub parent_expert: ExpertId,
    pub parent_variant: VariantId,
    pub claim: String,
    pub failure_class: FailureClass,
    pub primary_metric: MetricId,
    pub falsification_rule: FalsificationRule,
    pub candidate_family: ChallengerFamilySpec,
    pub evidence_refs: Vec<ArtifactHash>,
}
```

### 3.2 Global Research Trial Debt Accounting
Her denenen aday parametre (`TrialRecord`), global araştırma defterine (`GlobalTrialLedger`) kaydedilir:
- 100 varyant denendiyse: $\text{trial\_count} \mathrel{+}= 100$.
- Sadece kazanan kaydedilip diğer 99'u gizlenemez.
- Post-selection Sharpe çalışmasının (arXiv:2606.01650) gösterdiği üzere çok aday arasından seçilen tekil tepe noktası yanıltıcıdır; multiple-testing cezası (Bailey PBO & Deflated Sharpe Ratio) ödenmelidir.

---

## 4. KZ-003: DEV Robustness Surfaces (AlgoXpert Plateau & Cliff Analysis)

Tekil tepe noktaları (isolated peaks) yerine parametre komşuluğu boyunca kararlı platolar (plateaus) aranır (arXiv:2603.09219):

```
Net Expectancy
   ▲
   │        ┌───────────────┐
   │    ┌───┘               └───┐
   │ ───┘                       └──────   ◄─── PLATFORM / PLATO (Kabul Edilir)
   │
   │           /\
   │          /  \
   │ ────────/    \────────────────────   ◄─── SİVRİ TEPE / CLIFF (Veto Edilir)
   └──────────────────────────────────────► Parametre Değeri (örn. SL Mesafesi)
```

- **Plato Kriteri:** $\text{Sharpe}(\theta) \ge \alpha \times \text{best\_Sharpe}$ komşu bant içinde korunmalıdır.
- **Cliff Vetosu:** Komşu parametrede performans aniden düşüyorsa (`RobustnessVerdict::Cliff`), aday anında elenir.

---

## 5. KZ-004: Purged WFA & One-Shot Frozen OOS Burn

### 5.1 Purged Walk-Forward Analysis (WFA)
- Geliştirme (DEV) aşamasında geçerli plato bulunan adaylar, kronolojik katlamalı (walk-forward folds) ve bilgi sızıntısını engelleyen arındırma (purge bars) ile test edilir.
- **Majority Pass & Catastrophic Veto:** 5 katlamadan 4'ü başarılı olsa bile, tek bir katlamada katastrofik düşüş (`CatastrophicVeto`) gerçekleşirse WFA başarısız (`FAIL`) sayılır.
- **Validation Geometry Accounting:** Farklı train/test pencereleri denemek de bir araştırma tercihidir (arXiv:2602.10785); denenen tüm pencere geometrileri trial debt'e işlenir.

### 5.2 One-Shot Frozen Holdout Burn Invariant
Frozen Out-of-Sample (OOS) verisi bir kez açıldığında **yakılır (burned)**:

```rust
pub struct HoldoutBurnReceipt {
    pub experiment_id: ExperimentId,
    pub dataset_hash: Hash,
    pub policy_hash: Hash,
    pub simulator_hash: Hash,
    pub opened_at: Timestamp,
    pub output_hash: Hash,
}
```

Eğer bir ajan aynı `(experiment_id, dataset_hash)` kombinasyonunu tekrar açmaya çalışırsa sistem `Err(HoldoutError::AlreadyBurned)` ile çöker ve işlemi reddeder.

---

## 6. KZ-005: Adaptive Sweep Gate (Blocked under O-032)

- **Sequential Variant Streams & Stopped e-BH:** Wang–Dandapanthula–Ramdas (arXiv:2502.08539) ve safe anytime-valid inference literatürünün (arXiv:2210.01948, arXiv:2009.02824) gösterdiği üzere, aynı tape üzerinde eşzamanlı akan sequential varyantlarda yerel ve küresel süzgeç (filtration) bağımlılığı çözülmeden adaptif sequential sweep açılamaz.
- **Status:** `BLOCKED_BY_O032`.
- `SweepMode::AdaptiveSequential` çağrıları `Err(SweepError::SequentialEvidenceAuthorityMissing)` ile fail-closed kalır.
