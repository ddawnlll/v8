# V8.7 Technical Acceptance — v8-next (NX01–NX11)

**Scope: TECHNICAL acceptance only.** This document certifies contracts, tests and
physical artifacts. It does **not** certify an economic edge, prospective maturity,
capital readiness or any live authority. Every verdict remains `NO_ECONOMIC_CLAIM`.

Acceptance matrix (machine-built, artifacts hashed by read-back):
`docs/evidence/v87/NX11/acceptance_matrix.json` sha256 `09ee76dec251c586d6dfb81b2ceee11538e0f1fe3e18bc922738da15e661fed9`.

**Correction (2026-09-11):** this file and the matrix originally cited the NX09
commit as `42136221`; the real commit is `42136231` (two digits transposed). The
matrix was rebuilt after the fix, so the hash above supersedes the earlier
`a3c04935…` published in the issue comments. No artifact content changed.

## 1. What was delivered

| Issue | Scope | Commit | Re-verified here |
|---|---|---|---|
| NX00 (#433) | epic: baseline identity, call-graph verification, evidence index | `ded4940d` (report) | — |
| NX01 (#422) | tape inventory, burn map, calendar, tape identity | `7a3d2859` | PASS |
| NX02 (#423) | one lifecycle/accounting contract, native reconciliation | `94e75c2c` | PASS |
| NX03 (#424) | 24/12/12 historical plan, warmup/purge, frozen forward path | `5deb4282` | PASS |
| NX04 (#425) | version-resolved ledger canon, no re-hashing of history | `453df499` | PASS |
| NX05 (#426) | one window/profile/run-key/resume contract for both paths | `311df69d` | PASS |
| NX06 (#427) | pre-registered swing baseline family over the existing grammar | `c7bb4c69` | PASS |
| NX07 (#428) | pinned statistics plan, dependency-aware adequacy | `fc054071` | PASS |
| NX08 (#429) | derived coverage, default-free certificate, canonical gate map | `74cb0f3d` | PASS |
| NX09 (#430) | registered four-fold swing research, conditional final | `42136231` | PASS |
| NX10 (#431) | bounded public capture, exactly-once restart, honest provenance | `a69d6772` | PASS |

Gate checks re-run at this boundary: `test_d153_runner_report.py` +
`test_portfolio_benchmark.py` (epic), the NX07 statistics suite (6 files) and the NX08
suite (3 files) — all exit 0. Full v8-next suite: **978 passed**. `ruff` clean.
`mypy v8-next/src`: **5 pre-existing errors**, unchanged by this work
(`expert_strategy.py:579`, `portfolio_backtest.py:200,387`, `trajectory.py:43`),
reported separately rather than fixed silently.

## 2. Measured results (not estimates)

| Measurement | Value |
|---|---|
| Tape | 226,706,603 B · sha256 `b27891e9…` · 394,545 rows · 960/960 archives matched 3 ways |
| Native vs independent replay | delta `0.00000000` (tolerance `1e-8`); closed-loop error `0.54947350 → 7.06e-13` |
| Legacy ledger | 20/20 entries verify under the version-resolved canon; file bytes unchanged (`657b2183…`) |
| Swing family (2025-01) | `causal_trend` net **+0.018861**, `plain_swing` net **−0.031357** (30 STOP / 31 campaigns) |
| Real fold family statistics | DSR confidence **0.11834**, Bonferroni p **1.0**, sufficiency SUFFICIENT (6 independent blocks), PBO UNDERPOWERED (named) |
| Registered four folds | swing family negative vs baseline in **7 of 8** fold-symbol cells; ablations did not improve |
| Bounded public capture | 1009 trades accepted, 1000 duplicate identities dropped, restart chain verified, G7 UNKNOWN |

## 3. Baseline failures — reported, not hidden

| Item | Status | Note |
|---|---|---|
| `tools/audit_doc_path_refs.py` | exit 1, **56 unaccounted citations** (30 distinct) | pre-existing, all in legacy/Rust-era documents whose `v8-core/…` paths the D-162 quarantine moved to `legacy/v8-core/`. Every citation in `docs/evidence/v87/**` and `docs/migration/V87_*` now resolves; the residual set is the owner's documentation sweep, and the guard was not weakened. |
| `tools/build_monograph.py` (EN and TR) | exit 1, **unreachable input** | `research/manifest/research_papers_manifest.json` is absent from this checkout (historical artifact, commit `9365fe87`). Recorded as pending evidence; the EN/TR site is a publish step and publishing stays with the owner (D-163). |
| `mypy v8-next/src` | 5 errors | pre-existing, enumerated above. |


### Provenance note (2026-09-11)

The `docs/evidence/v87/NX02/` directory also contains artifacts written by a different
workstream (issue #436: `LOOP_RECONCILIATION_436.md`, `loop_reconciliation_436.json`,
`bound_receipt_before/after.json`, `regenerate_loop_reconciliation_receipt.py`). They are
listed by the matrix under `foreign_artifacts` with their hashes but carry **no acceptance
weight** for NX02 or this acceptance; nothing of theirs was modified or claimed here.

## 4. Pending evidence backlog (open, by contract)

| Item | Status | Evidence |
|---|---|---|
| Protected final window | `NOT_AVAILABLE` | last 12 months are `TAIL_BURNED` (measured) |
| Funding / markout in the replay paths | `MISSING_NOT_ZERO` | no mark price in the archive |
| Prospective maturity | `PENDING` | frozen 24h window not yet observed |
| Engine fill parity for the swing family | `PENDING` | outcomes are decision-plane replay |
| Economic edge / live authority | `NO_ECONOMIC_CLAIM` | DSR 0.11834, Bonferroni p = 1.0 |

**Technical acceptance ≠ economic certificate.** A fully burned dataset still permits a
correct diagnostic benchmark delivery; it does not permit an economic claim.

## 5. Authority boundary

This acceptance is **not** release, tag, push-to-main, merge or live-activation
authority (D-163: merge authority is not publish authority). No private order, transfer
or account change was made; no credential was used. Publishing the EN/TR site and
tagging a release stay with the owner.

## TR özeti

V8.7 **teknik kabul** tamamlandı: NX01–NX10 kapatıldı, her biri commit + tekrar çalıştırılan
test + fiziksel artefakt hash'i ile matrise bağlandı (`acceptance_matrix.json`). Tam suite
**978 passed**; mypy'de **5 önceden var olan** hata ayrı raporlandı.

Ölçülen sonuçlar olumsuz/kararsız ve olduğu gibi yazıldı: swing ailesi kayıtlı dört foldda
8 hücrenin 7'sinde baseline'a göre negatif; aile istatistiği DSR 0.11834 / Bonferroni p = 1.0
(authority eşiği geçilmedi). Protected final **yok** (`TAIL_BURNED`), bu yüzden final
açılmadı ve `NO_PROTECTED_FINAL` metadata olarak yazıldı.

Açık kalanlar: prospektif olgunluk (frozen 24 saatlik pencere henüz gözlenmedi), engine fill
parity, funding/markout (`MISSING`, sıfır değil) ve belge-yolu denetiminin 56 legacy
bulgusu (D-162 karantina taşımasından; V8.7 belgelerinde bulgu kalmadı).

**Teknik kabul, ekonomik sertifika değildir**; `NO_ECONOMIC_CLAIM` geçerlidir ve bu teslim
release/tag/push-main/live aktivasyon yetkisi vermez.
