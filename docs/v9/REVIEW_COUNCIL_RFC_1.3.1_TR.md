# V9 RFC 1.3.1 — Bağımsız, Adversarial Mimari Kabul İncelemesi

**İncelenen belge:** `docs/v9/V9_ARCHITECTURE_MONOGRAPH.md`, sürüm etiketi `V9-ARCH-RFC-1.3.1`
**Sabitlenen commit:** `cb72c3bb1e44d0f1ce2511d4c57d37f7d74d40c3` (PR #507, dal `docs/v9-architecture-rfc-1.3`)
**Önceki RFC 1.3 commit:** `c84fecbff3981ad2e6d4da3e0f974c81e2d80b61`
**Yardımcı kaynaklar:** `docs/v9/V9_IMPLEMENTATION_PLAN.md`, `docs/V9_BACKLOG.md`, `docs/v9/README.md` (aynı SHA)
**Kod incelemesi:** `v8-next/` aynı SHA'da, `git worktree` ile `cb72c3bb` üzerinde salt-okunur
**NautilusTrader:** `2.0.0rc4` (depo pin'i; `v8-next/pyproject.toml:12`) — imza doğrulaması yerel `.venv` üzerinde yapıldı

**Yöntem sınırı (açıkça):** Bu inceleme monografın 1.380 satırının tamamını, uygulama planını ve backlog'un V9 ile ilgili bölümlerini okudu; `c84fecb..cb72c3bb` farkını hunk hunk çıkardı; ve yalnız *tartışmalı* noktalarda kodu kaynak düzeyinde doğruladı. Hiçbir V9 fixture'ı, backtest, native replay veya ekonomik ölçüm **çalıştırılmadı**. `site/v9.html` hiçbir yerde kanıt olarak kullanılmadı. Aşağıdaki tek "çalıştırma" `Strategy.cancel_order` tip kontrolüdür ve sonucu F4'te kayıtlıdır.

---

## A. Bağımsız hüküm

**`CONDITIONALLY ACCEPTABLE — MINOR NON-BLOCKING CLARIFICATIONS`**

**Gerekçe.** RFC 1.3.1'in taşıyıcı iddiası şudur: ilk uygulanabilir dilim adaptif bir trader değil, *tek bir sabitlenmiş V8 baseline'ının entry-only, yan etkisiz parite yürütücüsüdür*; güvenlik yeni bir "beyin" değil, mevcut risk/adapter çağrılarına yapılan operasyonel bir bağlamadır; ve her kanıt kapısı `claim × producer × dataset × execution_profile` kapsamındadır. Bu üç sınır da **iç tutarlı** ve **uygulanabilir**tir. RFC 1.3'ün en ciddi çelişkisi — "expert çıktıları hiçbir karar girdisi olamaz" derken aynı belgede V8 paritesini istemek — 1.3.1'de doğru biçimde çözülmüştür: legacy expert quorum *pinlenmiş baseline'ın iç hesabıdır* (§5.1, §7.0, §7.2). Bu, kodla da uyumludur: `ExpertEnsembleStrategy` kendi `min_support_quorum` kapısını gövdesinde taşır (`adapters/expert_strategy.py:105,187,635`).

Kabulün koşullu olması, **hiçbir tasarım sınırının yeniden çizilmesini gerektirmeyen** üç kapanış eksiğinden kaynaklanır: (i) §7.1'in "kanonik sözlük" iddiası kendi pseudocode'u ve fixture tablosuyla çelişiyor (F1); (ii) atomik intent/outbox yazımının *sahibi* adlandırılmamış ve `intent_revision` mantıksal anahtarın parçası olduğu için at-most-once garantisinin dayanağı belirsiz (F2); (iii) kapsamlı kanıt kapısı, aynı estimand için "daha uygun bir producer" seçilmesini yasaklayan bir kural içermiyor (F3). Üçü de aynı belge içinde paragrafla kapatılabilir; hiçbiri P0-A/B/C'nin başlamasını engellemez.

**P0'ı bitirmeden önemli mimari sınırların yeniden tasarlanması gerekecek mi? Hayır.** Ayrıntı ve gerekçe Bölüm E'de; koşul listesi Bölüm H'de.

---

## B. Öne çıkan bulgular (10, tekrarsız, şiddete göre)

> Her bulgu yedi alan taşır: **Şiddet · Sınıflandırma · Tam kaynak · Başarısız senaryo · V9 etkisi · En küçük yeterli düzeltme · Güven**. Kod bağımlı olup doğrulanamayan hiçbir iddia "DOĞRU" sayılmadı; doğrulanamayanlar `IMPLEMENTATION_UNKNOWN` etiketlidir.

### F1 — Kanonik karar sözlüğü kendi normatif metniyle çelişiyor
- **Şiddet:** HIGH
- **Sınıflandırma:** `DOCUMENTED_DEFECT`
- **Kaynak:** Monograf §7.1 `ReasonCode` tablosu (12 kod) ve §XXV-A ("aynı semantik kavram için ikinci synonym enum bulunmaz") vs §7.4 normatif pseudocode (`ORDER_PENDING`, `PARTIAL_FILL_ENTRY_PENDING`, `BASELINE_NATIVE_MANAGEMENT_UNCHANGED`, `NO_BASELINE_ENTRY`, `DATA_UNAVAILABLE`, `BASELINE_ADMITTED`) ve §7.8 `DEC-006` (`ABSTAIN/RECONCILE`).
- **Başarısız senaryo:** P0-C'de receipt şeması "kapalı enum" olarak kodlanır. Pseudocode'un ürettiği altı neden kodunun hiçbiri §7.1 listesinde yoktur; `ENTRY_PENDING` ile `ORDER_PENDING`, `STALE_DATA` ile `DATA_UNAVAILABLE`, `NO_OPPORTUNITY` ile `NO_BASELINE_ENTRY` eşanlamlı çiftlerdir. `RECONCILE` bir `DecisionAction` değil, `IntentKind.SAFETY_RECONCILE` adıdır. Uygulayıcı ya enum'u genişletir (o zaman "kanonik" olmaz) ya da pseudocode'u reddeder (o zaman §7.4 normatif olmaz).
- **V9 etkisi:** `G-DEC-01` ("her native order intent bir `decision_id` ile bağlı") ve tüm reason-code telemetrisi kararlı bir join anahtarına sahip olmaz. Denetim tarafında "reason dağılımı" raporları sürümden sürüme karşılaştırılamaz hâle gelir.
- **En küçük yeterli düzeltme:** `ReasonCode` listesini pseudocode'un fiilen kullandığı kodlarla kapatmak, eşanlamlıları tek koda indirmek ve `DEC-006`'yı `ABSTAIN` + `ReasonCode.VENUE_UNCERTAIN` + `IntentKind.SAFETY_RECONCILE` olarak yeniden yazmak. Yeni kavram gerekmiyor.
- **Güven:** 0.95 (metin içi çelişki, kod gerekmez).

### F2 — Atomik intent/outbox'ın sahibi adlandırılmamış; `intent_revision` at-most-once'ı deliyor
- **Şiddet:** HIGH
- **Sınıflandırma:** `DESIGN_RISK`
- **Kaynak:** Monograf §8.7 madde 1 ("tek account-scoped native adapter execution boundary") ve madde 5; §7.5 mantıksal anahtar `(venue, account, strategy, opportunity, intent_revision, policy_hash)`; §7.3.2 tablosu son satırı `UNMAPPED`; kodda en yakın aday `evaluation/store.py:1-3` — docstring: *"Not an execution ledger or authority issuer."* (`sqlite3` + `BEGIN IMMEDIATE` altyapısı mevcut: `evaluation/store.py:243,333`).
- **Başarısız senaryo:** (a) Adapter'ın içinde atomik yazım yapacak bir bileşen yok; tek aday store kendi sözleşmesiyle "execution ledger değildir" diyor. (b) Bir submit timeout'undan sonra `intent_revision` artırılırsa `logical_key` değişir, dolayısıyla *yeni* `client_order_id` üretmek meşru görünür — oysa §8.7 madde 2 "yeni ID ile ikinci risk gönderilmez" der. Hangi olayın revizyonu artırabileceği hiçbir yerde yazmıyor.
- **V9 etkisi:** §8.7'nin "at-most-one unintended risk side-effect" kabulü, tanımlanmamış bir aktöre ve politikanın serbestçe değiştirebildiği bir anahtar alanına dayanıyor. `DURABLE_INTENT_BLOCKED` fail-closed yolu sayesinde bu bir *güvenlik açığı* değil, ama sözleşme boşluğudur.
- **En küçük yeterli düzeltme:** P0-A çıktısında tek bir sahip (modül + tablo) adı vermek; `evaluation/store.py` sözleşmesini "execution-intent tablosu bu store'da yaşamaz/yaşar" diye açıkça karara bağlamak; ve `intent_revision`'ın yalnız venue tarafından doğrulanmış *terminal* red/iptal sonrası, yeni bir receipt ile artabileceğini normatif yazmak.
- **Güven:** 0.85.

### F3 — Kapsamlı kanıt kapısı "producer ikamesi" ile aşılabilir
- **Şiddet:** HIGH
- **Sınıflandırma:** `DESIGN_RISK`
- **Kaynak:** Monograf §12.9 ("P0 evidence-gate'leri yalnız ilgili `claim × producer × dataset × execution_profile` kapsamında zorunlu"), §12.4 (rapor bağlama listesi), §P0-C "V9.1 kapı eklemesi", `docs/V9_BACKLOG.md` §1 Preamble notu ("`#491` blocks only the affected equity producer and claims").
- **Başarısız senaryo:** `#491` residual'ı (`portfolio_P unexplained = 5.8050 USDT`, `portfolio_PE unexplained = 22.5040 USDT`; `docs/V9_BACKLOG.md` B19) mevcut equity producer'ını `BLOCKED` yapar. Ekip aynı estimand (net marked equity / Sharpe) için *yeni* bir equity producer tanımlar, claim'i ona bağlar ve kapı yeşil görünür — eski producer'ın çürüklüğü hiçbir verdict'te görünmez. Belge hiçbir yerde bunu yasaklamıyor; §12.4 sadece "bu rapor neye bağlı" der.
- **V9 etkisi:** Doğrudan Soru E'nin riski: "daha uygun bir producer seçerek gerçek muhasebe kusurunu atlamak". Kapsamlı kapı, kapsamı daralttığı ölçüde kaçış yüzeyi yaratır; yasak olmadan bu yüzey açık kalır.
- **En küçük yeterli düzeltme:** Estimand kimliğini producer'dan ayırmak: aynı estimand için producer değişimi *yeni claim* + *eski producer'ın `BLOCKED` durumunun zorunlu beyanı* gerektirsin; receipt `known_failing_producers` alanını taşısın. Tek paragraf.
- **Güven:** 0.8.

### F4 — `cancel_order(order)` pinli rc4 bağlamasında tip hatası; bağımsız olarak yeniden üretildi
- **Şiddet:** HIGH
- **Sınıflandırma:** `IMPLEMENTATION_VERIFIED_DEFECT`
- **Kaynak:** `v8-next/src/v8_next/adapters/swing_engine.py:402` ve `:463` (`self.cancel_order(order)`); doğru kullanım aynı repoda `adapters/campaign.py:88` (`self.cancel_order(order.client_order_id)`). Pinli bağlama: `nautilus_trader/trading/__init__.pyi:550-555` → `cancel_order(self, client_order_id: model.ClientOrderId, client_id=None, params=None)`.
- **Bağımsız yeniden üretim (bu incelemede çalıştırıldı):** `Strategy(None)` örneği üzerinde `cancel_order(object())` → `TypeError: 'object' object is not an instance of 'ClientOrderId'`. Yani bir `Order` nesnesi geçildiğinde aynı hata oluşur; sessiz yanlış davranış değil, **çalışma zamanı istisnası**dır. (Fixture çalıştırılmadı; yalnız tip sözleşmesi doğrulandı.)
- **Başarısız senaryo:** Bracket bacağı fill olduğunda kardeş emir iptal edilemez (`on_order_filled`, `swing_engine.py:455-467`); `_close_at_market` içindeki "açık bracket'ları emekliye ayır" döngüsü de (`:400-403`) istisna atar. Kalan stop/target emri kitapta kalır ve sonradan dolduğunda NETTING modunda izlenmeyen ters pozisyon açabilir — monografın §8.4'te "yasak kestirme" olarak adlandırdığı sınıfın ta kendisi.
- **V9 etkisi:** Bu yol V9 alpha'sı değil, `SAFETY_REPAIR` kapısıdır (§3.3.3). Ancak seçilen baseline bu strateji ise V0 parity bu yolda *native güvenlik doğrulanmadan* ilan edilemez.
- **En küçük yeterli düzeltme:** İki çağrıyı `self.cancel_order(order.client_order_id)` yapmak (repoda zaten doğru desen var); ardından sibling-cancel + late-fill native trace fixture'ı.
- **Güven:** 0.98.

### F5 — Partial fill'de koruma bacağı plan miktarıyla kuruluyor
- **Şiddet:** HIGH
- **Sınıflandırma:** `IMPLEMENTATION_VERIFIED_DEFECT`
- **Kaynak:** `adapters/swing_engine.py:358-395` (`_submit_bracket`): `quantity = Quantity(float(plan["quantity"]), ...)`; bacaklar `submit_order(stop, position_id=self._position_id())` ile gönderiliyor. `_submit_bracket` yalnız `status == "ENTRY_SUBMITTED"` iken ilk fill'de çağrılıyor (`:441-449`), yani ilk fill kısmi olsa bile miktar **plan miktarıdır**; sonraki fill'lerde yeniden uzlaştırma yok.
- **Başarısız senaryo:** Plan 100 birim, ilk fill 30 birim → pozisyon 30, koruma 100. Kalan 70 entry fill olmazsa (timeout/cancel) koruma aşırı boyutlu kalır; bacak dolduğunda pozisyonu aşan miktar NETTING'de ters pozisyon üretir. `POS-001`/`DEC-005` kâğıt üzerinde geçebilir, çünkü fixture "verified protection" alanını adapter'ın beyanından okur.
- **V9 etkisi:** §8.2 ("koruma kapsamı `verified_reduce_only_qty >= exposed_qty`'den daha zordur") ve §8.2.1 geçiş tablosu, kullanılan yolda ihlal edilir. `P0-NATIVE` ve `P0-SAFETY` kapıları bu düzeltme olmadan anlamsızdır.
- **En küçük yeterli düzeltme:** `_submit_bracket` miktarını *doğrulanmış açık miktar* ile kurmak; her ek fill'de kalan açık miktarı yeniden doğrulamak; aşırı korumayı `PROTECTION_GAP`/`REPLACING` olarak raporlamak. Yeni aktör gerekmiyor.
- **Güven:** 0.9.

### F6 — Fill uzlaştırması çokluk (multiplicity) kaybediyor; `last_trade_id` kimlik zincirinde yok
- **Şiddet:** MEDIUM
- **Sınıflandırma:** `IMPLEMENTATION_VERIFIED_DEFECT`
- **Kaynak:** `audit/native_telemetry.py:89-94` (`_fill_identity`: `trade_id > venue_order_id > client_order_id > order_id`) ve `:115-116` (`set(native_ids) - set(audit_ids)`).
- **Başarısız senaryo:** Aynı `client_order_id` ile iki farklı fill (partial ×2, `trade_id` yoksa) tek kimliğe çöküyor; iki native fill'e karşı bir audit fill varsa `unmatched_native_fills = 0` çıkıyor. `last_trade_id` alanı olaylarda bulunmasına rağmen kimlik zincirinde hiç okunmuyor — oysa §8.3 onu "her fill olayında kayıt edilir" diye normatifleştiriyor.
- **V9 etkisi:** `P0-LINEAGE` verdict'i, tam da kapatmayı vaat ettiği hata sınıfında (partial fill çokluğu) yeşil verebilir. `AUD-006` ("partial fill aggregate duplicate → FAIL") mevcut kodla garanti değildir.
- **En küçük yeterli düzeltme:** `Counter` tabanlı iki yönlü çokluk farkı ve `last_trade_id`'nin kimlik zincirine eklenmesi; kimlik kuralı sürümlenmiş olarak receipt'e yazılsın.
- **Güven:** 0.9.

### F7 — Campaign atfı sıra sınırı + client-ID son eki sezgisine dayanıyor
- **Şiddet:** MEDIUM
- **Sınıflandırma:** `IMPLEMENTATION_VERIFIED_DEFECT`
- **Kaynak:** `audit/pipeline.py:295-334` (`assign_campaign_ids`): `campaign = bisect_right(open_sequences, sequence_number)` (`:318`) ve `:321-324` içindeki ileri atama sezgisi — aynı `event_time_ns` + `client_id.endswith("-1")` veya `ADMISSION` olayı → `campaign += 1`.
- **Başarısız senaryo:** Aynı `event_time_ns`'te iki `POSITION_OPENED` (partial fill'lerin ayrı pozisyon açtığı NETTING dışı senaryo, replace/retry sonrası yeniden açılış), son eki `-1` olmayan entry (retry/replace), veya aynı saniyede admission + entry. Sonuç: **yanlış ama tamamen dolu** campaign kimliği — sıfır orphan, yanlış zincir.
- **V9 etkisi:** §3.3 ve §12.1.1'in tüm "wrong-but-populated join" mutasyon programı, eğer bu fonksiyon değişmezse *kendi hatasını* test eden bir oracle üretir. `P0-LINEAGE` "orphan=0 yeterli değildir" derken tam bu mekanizmayı hedefliyor; ancak düzeltme P0-B kapsamında açıkça adlandırılmamış.
- **En küçük yeterli düzeltme:** Campaign bağını `native_position_id`/`decision_id` üzerinden kurmak; sıra-sınırı yalnız geriye dönük uyumluluk için ikincil yol olarak korunmak ve `campaign_join_method` receipt'e yazılsın.
- **Güven:** 0.85.

### F8 — Minimum notional'a yukarı yuvarlama, quantization sonrası riski yeniden doğrulamıyor
- **Şiddet:** MEDIUM
- **Sınıflandırma:** `IMPLEMENTATION_VERIFIED_DEFECT`
- **Kaynak:** `adapters/expert_strategy.py:891-924`: `min_notional_qty = ceil((min_notional/px)/step)*step` (`:911-913`), `floored = max(min_step_qty, min_notional_qty)` (`:914`), tavan freni yalnız `max_notional_per_order` (`:915-918`), sonuç etiketi `SIZED_TO_MIN_NOTIONAL` (`:923`). Bu blok sonrasında stop-risk / margin / liquidation yeniden hesabı **yok**.
- **Başarısız senaryo:** 20 USDT hesap, stop mesafesi geniş, risk bütçesi 0.5 USDT → `qty_raw` venue minimumunun altında → miktar minimuma **yukarı** çekilir → gerçekleşen stop-risk bütçenin katı olur; kod bunu ret değil, "SIZED_TO_MIN_NOTIONAL" olarak kaydeder.
- **V9 etkisi:** §11.5.2'nin açık kuralını ("miktarı minimuma yukarı zorlayıp riski aşmak yasaktır") pinli kod ihlal ediyor. `P0-CAPITAL` ve Soru G'nin "küçük hesap" güvenliği bu yolda fail-closed değil.
- **En küçük yeterli düzeltme:** Yukarı yuvarlama sonrası `stop_distance × qty` risk bütçesini aşarsa `REJECT:RISK_AFTER_QUANTIZATION`; floor davranışı yalnız açıkça işaretlenmiş bir risk-modunda kalsın.
- **Güven:** 0.9.

### F9 — "Tekil baseline" şema olarak tanımlı, örnek olarak değil; tek ampirik bantta kapı dejenere
- **Şiddet:** MEDIUM
- **Sınıflandırma:** `DESIGN_RISK`
- **Kaynak:** Monograf §7.0 ve `V9_IMPLEMENTATION_PLAN.md` P0-A ("Choose exactly one `strategy_class + config_hash + code_sha + execution_profile`"). Kodda en az dört aday `Strategy`: `adapters/basket_backtest.py:71`, `adapters/campaign.py:29`, `adapters/expert_strategy.py:187`, `adapters/swing_engine.py:133`. §3.1'deki tek ampirik bant expert ensemble üzerinedir ve o ensemble'ın varsayılan kapısı `min_support_quorum: int = 1` (`adapters/expert_strategy.py:105`) — yani 123/123 consensus sonucu, quorum=1 ile *dejenere* bir kapıdan da üretilebilir.
- **Başarısız senaryo:** Ekip `swing_engine`'i seçip "V8 baseline paritesi" der (expert kapısı yok, dolayısıyla §5.1 tartışması boşa düşer); ya da expert ensemble'ı seçip F4/F5'teki doğrulanmış kusurları parity'nin içine miras alır ve "parity" ile "güvenli"yi karıştırır.
- **V9 etkisi:** Soru A'nın cevabı şema düzeyinde evet, *örnek* düzeyinde hayır. Bu, parity iddiasının hangi sınıfa ve hangi kapıya göre verildiğini belirsiz bırakır.
- **En küçük yeterli düzeltme:** P0-A çıktısı tek tuple + seçilen sınıfın legacy kapı parametreleri olsun; parity receipt'i `strategy_class` ve `quorum` alanlarını taşısın. Monografın iddiası değişmiyor, sadece bağlanıyor.
- **Güven:** 0.8.

### F10 — Dört paralel kanıt-kapısı sözlüğü var; eşleme tablosu yok
- **Şiddet:** MEDIUM
- **Sınıflandırma:** `DESIGN_RISK`
- **Kaynak:** §17 `G-*` matrisi (`G-MKT-01`…`G-OPS-01`), §12.2 dört verdict (`MECHANICAL/ACCOUNTING/SCIENTIFIC/PROMOTION`), §12.9 on `P0-*` kapısı, `docs/V9_BACKLOG.md` F1–F7, ve mevcut kod `evaluation/gate_registry.py`, `evaluation/gate_resolution.py` (77.7 KB). §12.2 açıkça "mevcut `G0–G9` adlarını yeniden yazmak için değil" diyor — yani beşinci bir adlandırma katmanı ekliyor, mevcut olanı eşlemiyor.
- **Başarısız senaryo:** P0-B raporu `P0-LINEAGE=BLOCKED` der, `G-AUD-01` aynı kanıt için "mekanik gate" der, `MECHANICAL_VERDICT=FAIL` der ve `gate_registry` üçüncü bir durum döndürür; hangisinin otorite olduğu kodda belirsiz kalır. Soru H'nin "V9 bir audit framework'e mi dönüşüyor" riski tam burada somutlaşır.
- **V9 etkisi:** Aynı kanıt için çoklu otorite, §2.1'in yasakladığı "ikinci claim registry"nin ad değiştirmiş hâlidir; ayrıca §12.2'nin kendi uyarısıyla çelişir.
- **En küçük yeterli düzeltme:** P0-A'da tek bir eşleme tablosu (`G-* ↔ 4 verdict ↔ P0-* ↔ gate_registry durum kodu`) yayınlamak ve yeni bir registry modülü açmayı yasaklamak. Yeni soyutlama değil, tek sayfa haritalama.
- **Güven:** 0.75.

**Kota notu:** On bulgu dolduruldu; daha düşük değerli öneriler (ör. §9.4'ün `cooldown_bars` sayılarının hâlâ örnek olması) bilinçli olarak dışarıda bırakıldı, çünkü ilgili bölüm zaten "bu makale optimum sayı icat etmez" diyor.

---

## C. RFC 1.3 → RFC 1.3.1 düzeltme denetimi

Fark: `git diff c84fecb..cb72c3bb` → 4 dosya, 91 satır değişim (monograf +59/−32, plan +8/−10, README +12/−3, backlog +7/−5). Aşağıdaki her satır bir hunk kümesine ve tek bir önceki-eleştiri hedefine karşılık gelir.

| # | Revizyon (yer) | Hedeflediği eleştiri | Sınıf | Gerekçe |
|---|---|---|---|---|
| C1 | Başlık/`Normatif durum` alanı: `RFC-1.3` → `RFC-1.3.1`, `DESIGN REVISION / OWNER APPROVAL PENDING` → `FINAL CANDIDATE / ARCHITECTURE NOT YET APPROVED` | Statü belirsizliği | **RESOLVED** | Monograf, plan, README ve backlog aynı dili kullanıyor; hiçbiri kabul iddia etmiyor. |
| C2 | Yeni bölüm "RFC-1.3.1 — Son inceleme adayı" (dört netleştirme) | Dört ayrı çelişki | **PARTIALLY_RESOLVED** | (i) baseline öznesi, (ii) `OPEN_EXPOSURE + ENTRY_PENDING`, (iv) kapsamlı kanıt kapısı uygulanabilir; (iii) "atomik intent/outbox mevcut native execution sınırındadır" *sahibi adlandırmıyor* → F2. |
| C3 | Yeni §3.3.3 code-surface defect register (5 satır) | "Kod iddiaları kaynaksız" | **RESOLVED** (belge olarak) | Beş mekanizmanın **beşini de** `cb72c3bb` üzerinde bağımsız doğruladım (F4–F8 ve `assign_campaign_ids`). Kapsam sınırı ("diğer stratejilere otomatik genellenmez") kodla uyumlu: `cancel_order(` çağrılarının yalnız ikisi yanlış, `campaign.py:88` doğru. Fixture sonuçları ise **NOT_VERIFIABLE** (yeniden koşulmadı, belge de bunu söylüyor). |
| C4 | §4.3 `MarketBeliefV0` → "FUTURE RESEARCH ONLY; NOT V0/V1 RUNTIME" | "Belief erken runtime sözleşmesi" | **RESOLVED** | Kodda `MarketBelief`/`PITFeatureView` yok (grep: 0 eşleşme) — belge fazla iddia etmiyor. |
| C5 | §5.1 + §7.0: legacy expert quorum baseline içinde kalır, *yeni* routing kapalı | RFC 1.3'ün parite/izolasyon çelişkisi | **RESOLVED** | Doğru çözüm: parite ancak iç hesaplama korunarak mümkün (`expert_strategy.py:105,635`). |
| C6 | §7.2 mermaid düğümü: "Existing V8 baseline decision" → "Chosen pinned V8 baseline decision; legacy gate internal" | "V0 grafiğinde expert oku var" | **RESOLVED** | Grafik ve prose aynı şeyi söylüyor. |
| C7 | §7.4 pseudocode: `durable_intent_store` parametresi kaldırıldı; entry-only; `PARTIAL_FILL_ENTRY_PENDING` dalı eklendi; sıra (pending < exposed-only) değişti; "Side-effect sınırı" paragrafı eklendi | Karar/yan etki karışması + partial fill | **PARTIALLY_RESOLVED** | Sıra ve saflık doğru: `PROTECTION_GAP` her şeyden önce, `HOLD`/`WAIT` native exit'i susturamaz. Kalan: neden-kodu sözlüğü (F1) ve sahiplik (F2). |
| C8 | §7.8 `DEC-005`: "Partial fill + open qty **+ kalan entry pending**" | Partial-fill fixture'ın gerçek durumu temsil etmemesi | **RESOLVED** | Beklenti pseudocode dalıyla birebir; "native exit/cancel callback sürer" notu Soru B'nin cevabını kapatıyor. |
| C9 | §7.9 "Zorunlu sıra" → "Bağlayıcı **kapsamlı** sıra" | #491'in tüm geliştirmeyi kilitlemesi | **PARTIALLY_RESOLVED** | Kapsam daraltması mekanik olarak çalışıyor; producer ikamesi yasağı yok → F3. |
| C10 | §8.2.1 bounded recovery: `BLOCKED` sonrası "salt-okunur, rate-bounded venue inquiry + operator notice" | `BLOCKED` sonrası açık pozisyonun izlenmemesi | **RESOLVED** | Açık exposure'ın görünürlüğü korunuyor, yeni risk/flatten yetkisi verilmiyor; Soru D'nin "bounded recovery ve monitoring" maddesi karşılanıyor. |
| C11 | §8.7 madde 1: "Pure policy / tek native execution writer" | Policy'nin DB'ye yazması | **PARTIALLY_RESOLVED** | Yan etki politika dışına çıktı; ama yazıcı bileşen ve `intent_revision` disiplini tanımsız → F2. |
| C12 | §11.5.2: kategorik TP1/TP2 yasağı kaldırıldı → sembol-özel `REJECT/NO_TRADE` | "20 USDT'de partial exit imkânsız" iddiası | **RESOLVED** | Doğru yön: yasak yerine fail-closed ret; Soru G ve 8. önerme bununla kapanıyor. |
| C13 | §12.6'ya M1 veto karşılaştırma paragrafı (same-calendar full replay, cash/no-trade, coverage-matched random veto, raw-feature/ATR, ex-ante power/stopping, "az zarar ≠ pozitif beklenti") | M1'in negatif baseline'a karşı yanlış yorumlanması | **RESOLVED** | Soru F'nin istediği yedi kontrolün tamamı tek paragrafta adlandırılmış. |
| C14 | §12.9 + plan + backlog: `claim × producer × dataset × execution_profile` | Kapıların aşırı genişliği | **PARTIALLY_RESOLVED** | Kapsam doğru; ikame yasağı eksik (F3). |
| C15 | §17.0 V0 parity satırı: "mekanik kapsamla sınırlı; ekonomik kıyas için ayrı equity/funding gate" | "Parity = ekonomik kanıt" karışması | **RESOLVED** | `V0_MECHANICS_ONLY` ile `EQUITY_VERDICT` ayrımı net. |
| C16 | §XXVI kapanış: "`ARCHITECTURALLY ACCEPTABLE` bu belgenin verilmiş hâkim hükmü değildir" | Yazarın kendi lehine hüküm vermesi | **RESOLVED** | Belge kendi statüsünü doğru tarif ediyor; README/backlog da aynı. |
| C17 | Plan P0-A/B/C satırları + README "Last design-freeze decisions" | Planın monografla hizasız olması | **RESOLVED** | Plan artık aynı yedi kararı tekrarlıyor; çelişki yok. |

**Özet:** 12 RESOLVED, 5 PARTIALLY_RESOLVED, 0 NOT_RESOLVED; ayrıca C3'ün *fixture* yarısı tek başına NOT_VERIFIABLE (kod mekanizması doğrulandı, fixture sonucu doğrulanmadı). Hiçbir düzeltme geri alınmamış; hiçbir eski eleştiri "yeniden paketlenmiş" değil — her hunk gerçek bir metin değişikliği içeriyor.

---

## D. Council yanlış-pozitif denetimi (10 önerme)

| # | Önerme | Sınıf | Gerekçe |
|---|---|---|---|
| 1 | 123/123 expert konsensüsü 28 modülün silinmesi gerektiğini kanıtlar | **FALSE_POSITIVE** | Sonuç yalnız *o bantta marjinal seçim etkisinin sıfır* olduğunu gösterir (§5.3). Dahası pinli kodda varsayılan `min_support_quorum = 1` (`expert_strategy.py:105`) — 123/123, kapının *dejenere* olduğunun da kanıtı olabilir; hangi expert'in ne elediği ölçülmemiş. Silme kararı bu veriden çıkmaz. |
| 2 | Negatif D4 sonucu OpportunityBook'un gereksizliğini kanıtlar | **FALSE_POSITIVE** | D4 tek bir admission kuralını (retest/reclaim + zorunlu gecikme) test eder (§6.3). Kimlik/hafıza ile zorunlu bekleme ayrılabilir; §6.1 bunu açıkça ayırıyor. |
| 3 | Çözülmemiş #491 residual'ı repodaki **her** mekanik ve ekonomik gözlemi geçersiz kılar | **FALSE_POSITIVE** | Aşırı geniş. O producer'dan türeyen ekonomik estimand'lar geçersizdir (`UNEXPLAINED_RESIDUAL` fiilen kodda: `evaluation/economic_benchmark.py:2160`); mekanik lineage/order/fill fixture'ları bu residual'a bağlı değildir. Kapsamlı kısım geçerli, "her gözlem" kısmı yanlış. |
| 4 | V0 paritesi expert davranışının tümünün kaldırılmasını zorunlu kılar | **FALSE_POSITIVE** | Tersine: legacy quorum baseline sınıfının *içinde* (`expert_strategy.py:187,635`). Kaldırmak parite değil, baseline değişikliğidir — RFC 1.3.1 bunu doğru yazıyor. |
| 5 | Native yürütmeyi güvenli kılmak için ayrı bir `SafetyReconciler` zorunludur | **FALSE_POSITIVE** (kayıtlı çekince ile) | Zorunlu değil: mevcut risk/adapter çağrılarına operasyonel bağlama yeterli *olabilir*. Çekince: bugün böyle bir çağrı kümesi adlandırılmış değil; ekip fiilen ikinci bir aktör yazarsa §7.3.1/ADR-011 ihlal edilir. Bu bir tasarım zorunluluğu değil, disiplin riskidir. |
| 6 | MarketBelief yalnızca gösterge yeniden adlandırmasıdır ve meşru araştırma amacı yoktur | **FALSE_POSITIVE** | "Meşru amaç yok" iddiası yanlış: §4.6 üç ayrı yanlışlanabilir iddia ve §4.7 M1 ablation'ı tanımlıyor. "Yeniden adlandırma mı" sorusu ise **UNVERIFIED** — ölçülmemiş; ama bu önermenin kanıtlanmış kısmı değil. |
| 7 | Offline otonom Kaizen mimariden kalıcı olarak çıkarılmalıdır | **FALSE_POSITIVE** | P2 kapsamına alınmış, trading core'dan fiziksel olarak ayrılmış, tek bounded pilot + aynı bütçeli manuel baseline ile sınanıyor (§13.7, ADR-008). Zararlı olduğu gösterilmedi; "şimdi gerekli değil" ile "kaldırılmalı" aynı şey değil. |
| 8 | 20 USDT hesap her partial exit'i ekonomik/teknik olarak imkânsız kılar | **FALSE_POSITIVE** | Sembol-özel `min_notional/step/margin` ile belirlenir; §11.5.2 kategorik yasağı kaldırıp fail-closed ret tanımlıyor. Genel imkânsızlık iddiası kanıtsız. |
| 9 | Uygulanmamış native API bağlamaları otomatik olarak mimari reddi gerektirir | **FALSE_POSITIVE** | Bunlar `IMPLEMENTATION_GATE`'tir (§12.9 `BLOCKED` + no-new-risk). P0-A'nın varlık nedeni tam olarak bu boşluğu kapatmaktır. |
| 10 | Revize durable intent/outbox tasarımı, bir spesifikasyonda yer aldığı için doğrudur | **VALID** | Doğru bir epistemik uyarı: §8.7 kendi içinde "transaction henüz uygulanmış ve test edilmiş sayılmaz" diyor; F2 de tam olarak bu boşluğu gösteriyor. Önerme geçerli. |

**Denge notu:** On önermenin dokuzu yanlış-pozitif, biri geçerli çıktı; bu, yazarı memnun etmek için üretilmiş bir sonuç değil — 4 numaralı önermenin reddi *kodla* doğrulandı, 10 numaralı önermenin kabulü ise §8.7'nin kendi ihtiyat diliyle uyumlu.

---

## E. Gerçek tasarım engelleri mi, uygulama kapıları mı?

### DESIGN_BLOCKER: **yok (0)**

Bu sonucu savunmak için her adayın neden *bloke etmediğini* ayrı ayrı göstermek gerekir:

| Aday | Neden DESIGN_BLOCKER değil |
|---|---|
| F1 (sözlük çelişkisi) | Bir enum'un kapatılması; karar/yan-etki sınırını değiştirmiyor. Bir paragraflık düzeltmeyle aynı mimari kalır. Kapsamlı bir fixture bunu çözmez (fixture hangi kodu test edeceğini bilemez), fakat *metin düzeltmesi* çözer — bu yüzden "kapsamlı implementasyon" değil, "küçük sözleşme kapanışı"dır. |
| F2 (outbox sahibi + `intent_revision`) | Sınır (policy saflığı / tek yazıcı) zaten doğru çizilmiş; eksik olan *atama*. §8.7 kendi fail-closed yolunu (`DURABLE_INTENT_BLOCKED`) tanımladığı için belirsizlik güvenli yönde kapanıyor. Sahip ataması P0-A'nın doğal çıktısıdır; yeni bir mimari sınır doğurmuyor. |
| F3 (producer ikamesi) | Kapı mekanizması doğru; eksik olan tek bir yasak cümlesi. Bir fixture bunu yakalayamaz (yanlış producer'ı "yanlış" ilan edecek bir üst-otorite yok) — bu yüzden **H'ye giren bir düzeltme**, ama mimari yeniden tasarım değil. |
| F4/F5 (cancel tipi, bracket miktarı) | Yerel adapter kusurları; mimari §8.2/§8.4 zaten doğru davranışı tarif ediyor. `SAFETY_REPAIR` kapısı. |
| F6/F7 (audit) | `AUDIT_REPAIR` kapıları; §12.1.1 protokolü zaten "yanlış-ama-dolu join" mutasyonunu ve bağımsız oracle'ı şart koşuyor. Eksik olan uygulama. |
| F8 (min-notional uplift) | Tek bir risk yeniden doğrulaması; §11.5.2'nin kuralı doğru, kod uymuyor. |
| F9 (baseline örneği) | Şema tam; seçim P0-A'nın *tanımı*. |
| F10 (kapı sözlükleri) | Bir haritalama tablosu; yeni soyutlama gerektirmiyor. |

**"Kapsamlı bir fixture yeterli olmaz" testi:** Hiçbir aday bu testi geçmedi, çünkü hiçbiri *hangi davranışın doğru olduğunun* belirsiz olduğu bir noktada değil. Belirsizlik ya adlandırmada (F1, F10), ya sahiplikte (F2), ya da yasakta (F3) — üçü de tek sayfalık normatif düzeltmeyle kapanır.

### IMPLEMENTATION_GATE: **8**

- `G1` — `SAFETY_REPAIR`: `cancel_order` argümanı (F4) + sibling/late-fill native trace.
- `G2` — `SAFETY_REPAIR`: bracket miktarı = doğrulanmış açık miktar; per-fill reconcile (F5); NETTING position identity fixture'ları.
- `G3` — `AUDIT_REPAIR`: fill multiset + `last_trade_id` kimliği (F6).
- `G4` — `AUDIT_REPAIR`: campaign atfının native position/decision kimliğine bağlanması (F7).
- `G5` — `RISK_REPAIR`: quantization sonrası stop-risk/margin/liquidation yeniden doğrulaması (F8) + 20 USDT sembol-özel fixture.
- `G6` — `P0-IDEMP`: tek transaction'da unique reservation + concurrent writer + power-loss/restart probu (§8.7 son paragraf).
- `G7` — `P0-NATIVE`: pinli rc4 callback sırası ve eşzamanlı kısmi fill/cancel/stop golden trace (§8.8).
- `G8` — `P0-EQUITY`: #491 residual'ının imzalı ayrıştırılması (`5.8050 / 22.5040` USDT); `EXT-TAPE` yokluğunda `REAL_WINDOW_ACCOUNTING_BLOCKED` kalır.

### OPTIONAL_IMPROVEMENT: 3
`O1` — §9.4'teki örnek sayıların (cooldown, max_amends) prereg dosyasına taşınması; `O2` — §13.8'deki donanım bütçelerinin ölçülmüş değerlerle değiştirilmesi; `O3` — §XXIV kaynakçasındaki `[L11]`/`[L13]`/`[L15]` gibi 2026 tarihli preprint'lerin "yöntem örneği" olarak kalmasının açıkça işaretlenmesi (şu an başlıkta "hakemli/preprint" ayrımı var, ancak V9 için kanıt statüsü belirtilmiyor).

---

## F. Bileşen düzeyinde mimari karar

| Bileşen | Karar | Gerekçe |
|---|---|---|
| V8 çekirdeği (PIT `MarketState`, `OpportunityBook`, hard risk, Nautilus adapter, audit) | **KEEP** (+yerel REFINE) | Değiştirmek baseline kimliğini yok eder; mimari zaten üstüne kuruyor. |
| `DecisionPolicyV0` (saflaştırılmış, entry-only) | **KEEP / REFINE** | Doğru sınır; F1 ve F2 kapanışı gerekli. |
| Safety Binding Contract (§7.3.1) | **KEEP** | İkinci politika yasağı doğru; ADR-011 ile tutarlı. |
| Durable Intent + Outbox (§8.7) | **KEEP / REFINE** | Mekanizma doğru; sahibi ve `intent_revision` disiplini adlandırılmalı. |
| `PITFeatureView` | **DEFER → P1-A** | İlk diagnostic arayüz olarak doğru; bugün runtime'da olmamalı. |
| `MarketBeliefV0` | **DEFER → V2+** | §4.3 doğru sınıflandırılmış; erken kodlamak ADR-003'ü ihlal eder. |
| Expert stance / clone-graph / yeni routing | **DEFER** (kod silinmeden, unreachable) | Silmek negatif kanıtı da siler (§XXV-D); V0'da karar girdisi olamaz. |
| `PositionPolicyV2` (dinamik stop) | **DEFER** | C4 zaten `INCONCLUSIVE`; ayrı prereg + native amend fixture'ı olmadan açılamaz. |
| Allocator / rotation | **DEFER** | Ex-ante alternatif tanımsızken rotation yasak (§10.2); bu doğru. |
| Q-optimizer / learned scorer | **REMOVE** (runtime'dan) | §7.7 açık yasak; ayrı RFC olmadan geri gelmemeli. |
| Ayrı `SafetyReconciler` aktörü | **REMOVE** | Gerekmiyor (D-5); eklenirse ikinci yetki doğar. |
| Autonomous Kaizen / `research_ops` | **DEFER → P2** | Ayrı kapsam, ayrı onay; trading core'a bağlanmamalı. |
| V9 kanıt-kapısı sözlükleri (§17 `G-*`, §12.2, §12.9 `P0-*`) | **REFINE** | Dördü mevcut `evaluation/gate_registry.py` ile haritalanmalı; beşinci katman eklenmemeli (F10). |
| Monograf + plan + backlog üçlüsü | **KEEP** | `site/v9.html`'in "STALE / normatif değil" ilan edilmesi doğru ve gerekliydi. |

---

## G. Bilimsel ve ekonomik geçerlilik

**Desteklenen (yalnız mekanik/olgu düzeyinde):**
- `cancel_order` argümanı pinli rc4 bağlamasıyla uyumsuz (tip düzeyinde yeniden üretildi).
- `_submit_bracket` plan miktarını kullanıyor; per-fill reconcile yok.
- `assign_campaign_ids` sıra-sınırı + son-ek sezgisi kullanıyor.
- `reconcile_fills` çokluk kaybediyor; `last_trade_id` kimlik zincirinde yok.
- `expert_strategy` miktarı minimuma yukarı çekebiliyor, sonrasında risk yeniden doğrulaması yok.
- #491 residual'ı kodda **adlandırılmış** bir durum olarak yayınlanıyor (`UNEXPLAINED_RESIDUAL`, `evaluation/economic_benchmark.py:2160`), yani "graft" iddiası doğru biçimde terk edilmiş.

**Geçersiz / yanlış yorumlanmış:**
- `B3 realistic profile` sonuçları ekonomik tabloya giremez (monograf §3.1 kendi `INVALID` damgasını taşıyor).
- Tek 90 günlük banttan birleştirilmiş politika için doğrulayıcı çıkarım çıkmaz (§12.5).
- 123/123 consensus'tan expert popülasyonu hakkında genel hüküm çıkmaz (D-1).

**Sonuçsuz (`INCONCLUSIVE`):**
- C4 stop→BE: eşleşmiş fark +0.1008R, GA sıfırı kapsıyor; `HOLD` dışı dinamik müdahale için yetki yok.
- D4 lifecycle: 12 ortak fırsatta −0.91391R, tüm-birim −0.00130R; farklı birimler farklı sorular, genel "zararlı" hükmü çıkmaz.

**Doğrulanmamış / bloke:**
- Native callback sırası, NETTING/OCO davranışı, koruma kapsamı — `P0-NATIVE` fixture'ı yok.
- Funding finality — `EXT-FUNDING` yok; `funding_cost = MISSING`.
- Equity reconciliasyon — `P0-EQUITY` bloke; Sharpe/DD/tail mean bu producer'dan **otorite üretemez**.
- 20 USDT venue fizibilitesi — `FEASIBILITY_NOT_ESTABLISHED`; sembol-özel PIT filtre testi yok.
- Sealed OOS — V8 tarafında yakılmış (`TAIL_BURNED`), yeni V9 ailesi için ayrılmış pencere tanımsız.

**Açıkça söylenmesi gereken:** Bu inceleme hiçbir **pozitif net beklenti** kanıtı bulmadı ve aramadı. Belgede de yok; belge bunu iddia etmiyor. Mevcut tek ampirik bant negatif (−8.6747 USDT net). Dolayısıyla "V9 mimarisi kabul edilebilir" hükmü **hiçbir ekonomik iddia taşımaz** ve taşıyamaz.

---

## H. Asgari gerekli değişiklikler (5, kabul öncesi)

**H1 — Sözlüğü kapat.** §7.1 `ReasonCode` kümesini §7.4 pseudocode'unun ve §7.8 fixture'larının fiilen kullandığı kodlarla birebir hizala; eşanlamlı çiftleri (`ORDER_PENDING`/`ENTRY_PENDING`, `DATA_UNAVAILABLE`/`STALE_DATA`, `NO_BASELINE_ENTRY`/`NO_OPPORTUNITY`) tek koda indir; `DEC-006`'daki `RECONCILE`'ı `IntentKind.SAFETY_RECONCILE` olarak düzelt. *(F1; kabul öncesi, tek sayfa.)*

**H2 — Yazıcıyı ve revizyon disiplinini adlandır.** Atomik `receipt + intent + logical_key + client_order_id + outbox` yazımının hangi bileşende yaşadığını (modül + tablo + transaction sınırı) P0-A çıktısı olarak zorunlu kıl; `evaluation/store.py`'nin "execution ledger değildir" sözleşmesiyle çelişkiyi açıkça çöz; `intent_revision`'ın yalnız venue-doğrulanmış terminal sonuç sonrası artabileceğini normatif yaz. *(F2; kabul öncesi, tek paragraf + bir tablo satırı.)*

**H3 — Producer ikamesini yasakla.** Aynı estimand için producer değişikliğinin yeni claim kimliği + eski producer'ın `BLOCKED` durumunun receipt'te zorunlu beyanı olmadan yapılamayacağını §12.4/§12.9'a ekle. *(F3; kabul öncesi, tek paragraf.)*

**H4 — Baseline'ı örnekle.** P0-A'nın çıktısını "şema" değil "tek tuple + legacy kapı parametreleri" olarak zorunlu kıl; parity receipt'i `strategy_class` ve `quorum` taşısın. Not: bugünkü tek ampirik bantta quorum varsayılanı 1'dir, dolayısıyla 123/123 sonucu expert seçiciliğini *test etmez*. *(F9; kabul öncesi ama P0-A ile eşzamanlı yapılabilir.)*

**H5 — Tek haritalama tablosu yayınla.** `G-*` ↔ dört verdict ↔ `P0-*` ↔ `evaluation/gate_registry.py` durum kodları; yeni bir registry modülü açmak yasak. *(F10; kabul öncesi, tek tablo.)*

**Yeni büyük revizyon talep edilmiyor.** Beş maddenin hiçbiri yeni bölüm, yeni aktör veya yeni alt sistem gerektirmiyor.

---

## I. Nihai uygulama-girişi kararı

1. **P0-A salt-okunur kaynak haritalaması başlayabilir mi?** **EVET.** Bu incelemenin kendisi kısmi bir P0-A provasıdır: beş kod mekanizması, bir API imzası, dört strateji sınıfı ve store'un transaction kapasitesi `cb72c3bb` üzerinde doğrulandı. Hiçbir engel yok.
2. **Kullanılan yolun güvenlik ve audit onarımı başlayabilir mi?** **EVET.** F4–F8'in beşi de gerçek, kaynak-adresli ve kapsamı sınırlı kusurlardır; `SAFETY_REPAIR`/`AUDIT_REPAIR` etiketiyle V9 alpha'sından ayrılmış durumda. Bu onarımlar mimari onay beklemez.
3. **`DecisionPolicyV0` kontrollü mekanik implementasyon için yeterince belirtilmiş mi?** **EVET — H1/H2/H3/H5 kapanışıyla.** Pseudocode'ın sırası, saflığı ve entry-only sınırı doğru; `OPEN_EXPOSURE + ENTRY_PENDING` durumu artık temsil ediliyor ve `HOLD/WAIT/ABSTAIN` native exit/stop/cancel yolunu susturamıyor. Yalnız *isimlendirme* ve *sahiplik* kapanışı gerekli.
4. **Adaptif M1 challenger bugün açılabilir mi?** **HAYIR.** `P0-B AUDIT_VERIFIED`, `P0-C V0_PARITY_VERIFIED`, `PINNED_NATIVE_CALLBACK_VERIFIED`, preregistration ve nitelikli equity producer'ın tamamı açık. Sealed OOS da yok.
5. **Herhangi bir canlı işlem yetkilendirildi mi?** **HAYIR.** Bu inceleme hiçbir işlem, sermaye veya üretim yetkisi vermez; belge de vermiyor. 20 USDT fizibilitesi `FEASIBILITY_NOT_ESTABLISHED`.

---

**My verdict would change if…**

- P0-A'da seçilen baseline'ın tek bir native submit/risk yolu **tek bir account-scoped yazıcıya** izole edilemediği ve bunun için ikinci bir yetki merkezi (ikinci store, ikinci OMS veya fiilen ikinci bir safety aktörü) zorunlu olduğu *kaynakla* gösterilirse → hüküm `PROMISING BUT REQUIRES TARGETED DESIGN REVISION` olur. (Seçilmiş strateji `cancel_order`/`_submit_bracket` kusurlarını taşıyorsa bu risk artar.)
- `intent_revision` yolunun bir crash/retry fixture'ında **iki ayrı `client_order_id` ve iki ayrı risk** ürettiği gösterilirse → F2 bloker'a yükselir.
- Legacy expert quorum'un pinlenmiş baseline içinde korunmasının, `decision_id`/receipt eklenmesiyle **kararları değiştirdiği** (yani paritenin yapısal olarak imkânsız olduğu) ölçülürse → baseline kimliği bölümü (Soru A) yeniden tasarım gerektirir.
- Ters yönde: F1/F2/F3/H1–H5 kapatılır ve `P0-LINEAGE` + `P0-IDEMP` + `P0-NATIVE` fixture'ları bağımsız oracle ile geçerse → hüküm `ARCHITECTURALLY ACCEPTABLE FOR CONTROLLED P0 — IMPLEMENTATION UNVERIFIED` olur; bu bile tek başına ekonomik veya canlı yetki anlamına gelmez.

*İnceleme sonu · V9-ARCH-RFC-1.3.1 · bağımsız adversarial model council · 2026-11-03*
