# ## V.17 — `risk_geometry_extractor` (P5, G track)

> research_pipeline_v2.1 worker prompt. Extract from the devir belgesi (AGENT_HANDOFF_PROMPT.md Bölüm V). No-leak, provenance and quota rules apply verbatim. Edit only with a research_pipeline_v2.2 version bump.
```
You extract position sizing and risk geometry rules from a book that discusses
them. These will inform a central resolver that supplies the geometry which
signal components deliberately leave unspecified.

INPUT
- passages routed to the risk track, with their sections

TASK
OUTPUT (JSONL)
{ "book_id": "...", "page": 0, "exact_text": "verbatim",
  "rule_kind": "POSITION_SIZE | RISK_PER_TRADE | PORTFOLIO_HEAT |
                CORRELATION_LIMIT | LOSS_STREAK | STOP_PLACEMENT |
                RISK_UNIT_DEFINITION | CAPITAL_ALLOCATION | EXPOSURE_CAP",
  "statement": "the rule in one plain sentence",
  "formula": "as the author states it, or NOT_SPECIFIED",
  "author_parameters": [ {"name","value","page"} ],
  "stated_justification": "the author's reason, or NOT_SPECIFIED",
  "empirical_support": "what evidence the author offers, or NONE_OFFERED",
  "assumes": [ "what must be true for this rule to make sense" ],
  "conflicts_with": [ "other rules in this corpus this contradicts" ],
  "confidence": "high|medium|low" }

RULES
- "assumes" is the most valuable field. A sizing rule that assumes independent
  trades, or a known win rate, or a stable edge, is only as good as that
  assumption. Name it.
- empirical_support: NONE_OFFERED is extremely common and must be recorded
  honestly. Much of this literature asserts sizing rules without evidence.
- Do not harmonise conflicting rules from different authors. Record the
  conflict.
- Capture the author's own definition of a risk unit. Authors mean different
  things by the same words and conflating them silently corrupts everything
  downstream.
```

---

# BÖLÜM VI — HATA VE İSTİSNA DAVRANIŞI

| Durum | Yapılacak |
|---|---|
| Worker geçersiz JSON döndürdü | 1 kez yeniden dene; yine başarısızsa kaydı `unresolved.jsonl`'e yaz, run'ı durdurma |
| Worker boş döndürdü | Geçerli sonuç. `NOT_FOUND_IN_SOURCE` yaz. Yeniden deneme |
| Bir kitap 0 claim verdi | Geçerli. `book_audit_report.json`'a yaz, kotayla zorlama |
| Sayfa eşlemesi başarısız (`\f` sapması >%5) | `page_anchor_status: UNMAPPED`, `part_id + line_range` ile anchor'la, sayfa **uydurma** |
| Novelty gate düşük güvenle NEW dedi | VARIANT_OF'a düşür, `open_questions.jsonl`'e yaz |
| A ve B tamamen çelişti | Adjudicator'a git; çözemezse `UNRESOLVED`, bu bir başarıdır |
| Validator BLOCKED verdi | Spec terminal durumda kalır. **Düzeltme, uydurma, gevşetme** |
| Şema/prompt değişikliği gerekiyor | Batch ortasında **yapma**. `v2.2` olarak yeni batch, `research_decisions.jsonl` girdisi |
| Süre tahmini %50'den fazla saptı | Durma; ölçülen değeri `run_ledger`'a yaz ve bir sonraki HITL'de bildir |
| Bir kural bu belgede tanımlı değil | **Uydurma.** `open_questions.jsonl` + insana sor |

---

# BÖLÜM VII — İNSAN ONAY PROTOKOLÜ

Üç noktada dur ve insan onayı olmadan devam etme.

### HITL-1 — P1 sonu (korpus koşusundan önce)

Sun:
- `scout_recall_report.json`: recall sayısı, claim tipine göre dağılım
- **Kaçan claim örnekleri** — regex'in görmediği gerçek pasajlar, ham metin
- A/B uyum matrisi ve en büyük 5 uyumsuzluk, pasajlarıyla
- 5 kalibrasyon kitabının uçtan uca ExpertSpec çıktısı
- **Ölçülmüş çağrı süresi ile güncellenmiş toplam süre tahmini**
- V.7'deki A/B çerçeve farkı kararının uyuma etkisi

Sor: *"Recall bu seviyede 125 kitap koşulsun mu? A/B çerçeve farkı korunsun mu?"*

### HITL-2 — P4 tur 3 sonu

Sun:
- Doyum eğrisinin ilk üç noktası (tur başına yeni family / toplam)
- O ana kadarki family ontolojisinin **tam listesi**, taslaklarıyla
- Birbirine en yakın 5 family çifti

Sor: *"Bu ayrımlar gerçekten farklı mekanizma mı, yoksa aynı şeyin varyantı
mı?"*

**Neden insan:** Ontoloji çok kaba ise doyum **yapay olarak erken** görünür ve
metrik bunu yakalayamaz — çünkü metrik ontolojinin kendisiyle tanımlanmıştır.
Bu sadece bakılarak görülür.

### HITL-3 — P6.b sonrası, translation'dan önce

Sun:
- Dondurulacak canonical family kümesinin tamamı
- `trial_ledger.jsonl` özeti: önerilen / reddedilen / birleştirilen family
  sayısı ve türetilen `N`
- `data_blocked.jsonl`
- `CONTRADICTS` ilişkili family çiftleri

Sor: *"Bu family kümesi ve bu `N` donduruluyor. Onaylıyor musun?"*

**Neden geri alınamaz:** Bu `N`, backtest fazının istatistiksel geçerliliğini
belirler. Donduktan sonra büyütmek her sonraki iddiayı zayıflatır; küçültmek
ise dürüstlük ihlalidir.

---

# BÖLÜM VIII — RAPORLAMA

Her faz sonunda `run_ledger.jsonl`'e ve konsola:

```
FAZ <ad> TAMAMLANDI
  çağrı: <n>        süre: <dk>        hata: <n>
  girdi: <n>        çıktı: <n>        drop/blocked: <n> (gerekçe dağılımı)
  kapı: PASS|FAIL   <fail ise: hangi kontrol, kaç kayıt>
  ölçülen çağrı süresi: <s>  (tahmin: 45 s)  sapma: <%>
```

Run sonunda `registry/final_report.json` ve insana özet:
- kapsama: işlenen kitap / toplam, sayfa eşlenen kitap / toplam
- claim akışı: lead → triaged → gated → extracted → adjudicated → synthesized
- family: toplam canonical, source variant, `CONTRADICTS` çifti
- spec: QA_PASSED / SPEC_INCOMPLETE / NOT_EXECUTABLE / DATA_BLOCKED
- doyum eğrisi (13 nokta)
- **trial ledger `N`**
- scout recall
- açık sorular sayısı

**Rapor dürüstlük kuralı:** Çalıştırılmayan kontrol "geçti" diye yazılmaz.
Atlanan faz atlandı diye yazılır. Bir kapı başarısız olduysa çıktısıyla
birlikte yazılır. Bu boru hattının tüm değeri buradan gelir.

---

# BÖLÜM IX — KAPSAM DIŞI

- **Expert compilation.** `src/v8/` altına kod yazmak `D-032` gereği register
  kararı + CHANGELOG girdisi ister. Bu run **QA_PASSED ExpertSpec'te biter.**
- **Backtest / experiment registry.** Family kümesi ve trial ledger
  dondurulmadan hiçbir ölçüm başlamaz.
- **Legacy v1 migrasyonu.** 1.080 v1 bulgusu `LEGACY_UNVERIFIED` kalır.
  P4 sonunda **yalnızca recall kontrol listesi** olarak kullanılır: "v1'de X
  vardı, v2.1 bunu buldu mu?" Bulmadıysa `open_questions.jsonl`.
  Otomatik `RawClaim`'e çevirme **yasak** — exact kaynak pasaj yeniden
  bulunmalıdır.
- **Gated bileşenler.** Router, shared scorer, ranker, RL execution, online
  learning.
- **`docs/` ve `site/` düzenlemesi.** Bu run `research/pipeline_v2/` altında
  kalır. `site/*` zaten elle düzenlenemez (üretilmiş artefakt).

---

# BÖLÜM X — SON SÖZ

Bu boru hattının tek amacı şudur: altı ay sonra biri bir expert'e bakıp
**"bu kural nereden geldi?"** diye sorduğunda, cevabın bir sayfa numarası ve
birebir alıntı olması — ya da dürüst bir `EXPERIMENTAL_ASSUMPTION` etiketi.

Bunu bozan tek şey, boşluğu doldurma dürtüsüdür. Eksik kural eksik kalır.
`UNRESOLVED` bir başarısızlık değil, bir sonuçtur.

Emin değilsen: **yazma, sor.**
