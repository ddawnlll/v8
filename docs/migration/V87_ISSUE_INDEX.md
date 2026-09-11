# V8.7 issue index — v8-next Python/Nautilus

2026-09-11 owner correction. Eski #410–#420 Rust kapsamı geri çekildi; aşağıdaki işler gerçek v8-next kaynak taramasına göre açıldı. Bunlar yeni implementation teslimi değildir.

| İş | GitHub | Bağımlılıklar |
|---|---|---|
| NX01 | [[IMPL] [V8.7/NX01] [v8-next] Dört yıllık tape kimliği, burn haritası ve Python veri bağlantısı](https://github.com/ddawnlll/v8/issues/422) | NONE |
| NX02 | [[IMPL] [V8.7/NX02] [v8-next] Runner muhasebesini mevcut kronolojik eşleştirme ve native equity ile uzlaştır](https://github.com/ddawnlll/v8/issues/423) | NONE |
| NX03 | [[IMPL] [V8.7/NX03] [v8-next] Historical walk-forward planını ForwardPlan güvenliğinden ayır](https://github.com/ddawnlll/v8/issues/424) | NX01 |
| NX04 | [[IMPL] [V8.7/NX04] [v8-next] Ledger legacy canonicalization sürümünü doğrula; geçmişi yeniden hashleme](https://github.com/ddawnlll/v8/issues/425) | NONE |
| NX05 | [[IMPL] [V8.7/NX05] [v8-next] D153 ve portfolio benchmark yollarını ortak pencere ve receipt kimliğine bağla](https://github.com/ddawnlll/v8/issues/426) | NX02, NX03, NX04 |
| NX06 | [[IMPL] [V8.7/NX06] [v8-next] Mevcut grammar ve squeeze protection ile swing baseline bağla](https://github.com/ddawnlll/v8/issues/427) | NX02, NX03 |
| NX07 | [[IMPL] [V8.7/NX07] [v8-next] Trial ailesini gerçek bağımlılık duyarlı istatistiklere bağla](https://github.com/ddawnlll/v8/issues/428) | NX03, NX05, NX06 |
| NX08 | [[IMPL] [V8.7/NX08] [v8-next] Scorer, certificate ve gate adlarını aynı kanıta bağla](https://github.com/ddawnlll/v8/issues/429) | NX04, NX05, NX07 |
| NX09 | [[IMPL] [V8.7/NX09] [v8-next] Kayıtlı dört fold swing araştırması ve koşullu final raporu](https://github.com/ddawnlll/v8/issues/430) | NX01, NX03, NX05, NX06, NX07, NX08 |
| NX10 | [[IMPL] [V8.7/NX10] [v8-next] Gerçek prospective public shadow ve restart kanıtı](https://github.com/ddawnlll/v8/issues/431) | NX03, NX05, NX06, NX08 |
| NX11 | [[IMPL] [V8.7/NX11] [v8-next] v8-next teknik V8.7 kabul dosyası ve belge tutarlılığı](https://github.com/ddawnlll/v8/issues/432) | NX01, NX02, NX03, NX04, NX05, NX06, NX07, NX08, NX09, NX10 |
| NX00 | [[IMPL] [V8.7/NX00] [v8-next] Ana goal: v8-next swing benchmark paketini bağımlılık sırasıyla tamamla](https://github.com/ddawnlll/v8/issues/433) | NX01, NX02, NX03, NX04, NX05, NX06, NX07, NX08, NX09, NX10, NX11 |

## Geri çekilen paket

| Eski issue | Yerine geçen işler |
|---|---|
| [#410](https://github.com/ddawnlll/v8/issues/410) | [#422](https://github.com/ddawnlll/v8/issues/422) |
| [#411](https://github.com/ddawnlll/v8/issues/411) | [#423](https://github.com/ddawnlll/v8/issues/423) |
| [#412](https://github.com/ddawnlll/v8/issues/412) | [#424](https://github.com/ddawnlll/v8/issues/424) |
| [#413](https://github.com/ddawnlll/v8/issues/413) | [#425](https://github.com/ddawnlll/v8/issues/425), [#426](https://github.com/ddawnlll/v8/issues/426) |
| [#414](https://github.com/ddawnlll/v8/issues/414) | [#427](https://github.com/ddawnlll/v8/issues/427) |
| [#415](https://github.com/ddawnlll/v8/issues/415) | [#428](https://github.com/ddawnlll/v8/issues/428) |
| [#416](https://github.com/ddawnlll/v8/issues/416) | [#429](https://github.com/ddawnlll/v8/issues/429) |
| [#417](https://github.com/ddawnlll/v8/issues/417) | [#430](https://github.com/ddawnlll/v8/issues/430) |
| [#418](https://github.com/ddawnlll/v8/issues/418) | [#431](https://github.com/ddawnlll/v8/issues/431) |
| [#419](https://github.com/ddawnlll/v8/issues/419) | [#432](https://github.com/ddawnlll/v8/issues/432) |
| [#420](https://github.com/ddawnlll/v8/issues/420) | [#433](https://github.com/ddawnlll/v8/issues/433) |

## Tek goal

[Hermes ana goal promptu](V87_V8NEXT_HERMES_GOAL.md). Her issue gövdesi ayrıca kendi tek-goal promptunu, R1–R6 ölçütlerini, doğrulanmış dosya/test yüzeyini ve kanıt koşullarını içerir.

Kaynak tarama SHA: `0990615962431ca8434824b3be33ac076a69f3bf`. Kaynak çalışma ağacı ile docs yayın dalı farklıdır; yayın dalı runtime teslimatı değildir. Kanıt durumu yeni işler için PENDING.
