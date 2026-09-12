# Hermes goal — V8.7 v8-next

```text
Ana issue https://github.com/ddawnlll/v8/issues/433 ve gövdesinde bağlı NX01–NX11 işlerini v8-next Python/Nautilus codebase üzerinde teknik kabul ölçütleri tamamlanana kadar otonom çöz.

Önce ana issue ve tüm alt issue gövdelerini gh CLI ile oku; docs/contracts/V87_SWING_BENCHMARK_SPEC.md, docs/migration/V87_SWING_BENCHMARK_IMPLEMENTATION_PLAN.md ve V87_ISSUE_INDEX.md dosyalarını incele. Belgeler checkout’ta yoksa codex/v87-swing-benchmark-plans dalından git show ile oku; kullanıcının ağacını resetleme. Bu docs dalını runtime implementation dalı sanma. Gerçek checkout SHA/dirty tree/uv.lock kimliğini kaydet. Kaynak eksikse yanlış Rust checkout’unda iş yapma; eksik v8-next checkout’unu açıkça bildir.

2026-09-11 owner talimatı v8-next’i bu çalışma için açıkça yetkilendirir. Eski Rust-only/frozen ifadeler ve #410–#420 goal promptları superseded. Yeni runtime/test işi v8-next içinde Python; v8-core yalnızca referans. Kök src/v8 ve tests oracle alanlarını koru. Mevcut pair_positions, native equity, ResearchStore, ForwardPlan, CampaignProtection, catalog ve statistics arayüzlerini yeniden kullan. Her issue gerçek dosya ve test adlarını içerir; hayali Rust/Python arayüzü üretme.

NX01/NX02/NX04 ile başla; sonra NX03, NX05/NX06, NX07, NX08, NX09/NX10 ve NX11 bağımlılıklarını somut artifactlarla doğrulayarak ilerle. Bu sıralama bağımsız işleri bekletme gerekçesi değildir. Her R için en küçük doğru değişikliği yap, Python 3.12 ve uv.lock ile ilgili ruff/mypy/pytest kontrollerini çalıştır, fiziksel artifactı hash/read-back ile doğrula. Eski baseline test hatalarını ayrı raporla. Kullanıcının ilgisiz değişikliklerine dokunma.

Dört yıllık geçmişte burn/usage_unknown veriyi protected final sayma. Ledgerı yeniden hashleme; kanıtlı legacy canonicalization düzelt. Synthetic yalnızca MECHANICS ONLY testte kalır. Eksik metriği sıfır, diagnostic sonucu PASS, local paperı live venue settlement, skor tahminini kabul hedefi yapma. NO_ECONOMIC_CLAIM geçerlidir. Protected final yoksa NX09 diagnostic teslimle tamamlanabilir; prospective olgunluk NX10’da açık pending evidence olarak kalır. Teknik kabul ile ekonomik sertifika farklıdır.

Rutin geri alınabilir implementation kararlarında tekrar izin isteme. Gerçek veri/authority/semantik engelinde yalnızca ilgili kol için OPEN_PIN/pending evidence kaydet, bağımsız işleri tamamla. Bu goal private emir, transfer, hesap değişikliği, live activation, main push, otomatik merge veya release/tag yetkisi vermez.

Her alt issueye R→commit→exact check sonucu→artifact path/hash matrisi ekle; Completed/Remaining R IDs ve lifecycle güncel olsun. Zorunlu R tamamlanmadan issueyi kapatma. Hepsi teknik olarak doğrulandığında ana issueyi de kapat; son raporda ölçülen skorları, eksik ekonomik kanıtları ve kalan riskleri açık yaz. Tahminleri gerçekleşmiş sonuç diye sunma.
```
