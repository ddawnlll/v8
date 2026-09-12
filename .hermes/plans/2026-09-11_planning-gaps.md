# Planlama Eksikleri — 2026-09-11

Bu dosya, 7/24 kontrol düzleminin bugüne kadar gözlenen **kanıtlı** planlama
boşluklarını toplar. Her madde: gözlem → kanıt → eksik olan → neden önemli.

Kanıt kaynakları: `~/.hermes/logs/errors.log`, `~/.hermes/cron/output/*`,
`~/.hermes/cron/jobs.json`, `~/.hermes/kanban/boards/v8/kanban.db`,
`ddawnlll/v8` GitHub issue'ları, `artifacts/bulletin.md`.

---

## Özet tablo

| # | Boşluk | Şiddet | Mevcut durum |
|---|--------|--------|--------------|
| A0 | Onay modu geçersiz: loop otonom değil | **Kritik** | `approvals.mode: yolo` ve `cron_mode: yolo` bu build'de geçersiz → kod `manual`/`deny`'ye düşüyor |
| A1 | Bul→çöz köprüsü yok | **Kritik** | 18 issue üretildi, 0'ı uygulandı |
| A2 | Üretim/tüketim dengesiz | **Kritik** | 62 açık issue, `max_in_progress=1` |
| B1 | Provider kesintisine dayanıklılık yok | **Kritik** | 7 saat tam kesinti, 0 alarm |
| B2 | Yanıltıcı hata mesajı | Yüksek | stream stall → "internetin yok" |
| B3 | Sessiz ölüm / eskalasyon yok | Yüksek | `cron_incomplete_no_output`, kimse uyarmadı |
| B4 | Fallback model/provider yok | Yüksek | `fallback_providers: []` |
| C1 | Model pinleme + fail-closed sessizliği | Orta | global değişince unpinned job ölür |
| C2 | Model envanteri/kapasite doğrulaması yok | Orta | muse-spark HTTP 500, deepseek 200 |
| D1 | Token bütçesi enforcement'ı yok | Orta | hedef 30k, gerçek 232k |
| D2 | $60/ay limit takibi yok | Orta | limit dolunca yine "provider yok" görünür |
| E1 | `done` ≠ doğrulandı | Yüksek | 7 done, bağımsız verifier receipt'i yok |
| E2 | Yayınlanan metriğin kaynak izi zorunlu değil | Yüksek | #395 readiness bug'ı bu yüzden çıktı |
| E3 | Ledger tamper çözülmedi | Orta | entry 0, chain true / ledger false |
| F1 | "Bitti" tanımı yok | **Kritik** | cap full mu, canlı kâr mı, readiness mi? |
| F2 | Negatif ekonomik sonucun planı yok | Yüksek | incremental −0.0038 |
| F3 | Kitaplar bağlanmıyor | Orta | 167 PDF, ~150'si mapped değil |

---

## A0. Onay düzlemi: loop hiç otonom olmadı (Kritik)

**Gözlem:** 7/24 döngü için `approvals.mode: yolo` ve `approvals.cron_mode: yolo`
ayarlandı, ama bu build `yolo` değerini tanımıyor.

**Kanıt:**
- `~/.hermes/hermes-agent/tools/approval_context.py:197` → `_VALID_MODES = ("manual", "smart", "off")`;
  bilinmeyen değer uyarıp **`manual`**'a düşüyor.
- `approval_context.py:260-272` → `_binary_approval_mode("cron_mode")`: yalnızca
  `approve|off|allow|yes` onay sayılıyor, **diğer her şey `deny`** — yani `cron_mode: yolo` = deny.
- `agent.log`: 441 × `Unknown approvals.mode 'yolo' — defaulting to 'manual'` (son: 01:38).
- Cron worker'ları `status: pending_approval` aldı (terminal tool), `execute_code` ise
  sert blok: `BLOCKED: execute_code runs arbitrary local Python ... Cron jobs run without
  a user present to approve it`.

**Eksik:** doğru değer `off`. `hermes config set approvals.mode off` +
`hermes config set approvals.cron_mode off` + `hermes gateway restart`. Ardından
`grep -c "Unknown approvals.mode" ~/.hermes/logs/agent.log` sabit kalmalı.

**Neden önemli:** A1/A2'yi açıklayan kök neden bu olabilir — worker'lar serbest
çalışmadığı için üretim/tüketim dengesi hiç kurulmamış olabilir. Otonomi ölçülmeden
"7/24 çalışıyor" denemez.

**Not:** Düzeltmeyi uygulayan komut da aynı onay katmanına takıldı
(`BLOCKED: Command timed out without user response`) — kilit kendi kendini kilitliyor,
insan eliyle `hermes config set` gerekiyor.

---

## A. Döngü akışı: bulmak ≠ çözmek

### A1 — Scout buluyor, engineer tüketmiyor (Kritik)
**Gözlem:** Scout 23 tick koştu, 3 gerçek defect buldu (`#387`, `#394`, `#395`).
24 saatte 18 issue açıldı, 62 issue açık. Kanban'a düşen yeni kart: 0.
**Kanıt:** `gh issue list --state open` → 62; `kanban.db` → `created_by=v8-engineer`
sadece 2 kayıt; main'e 21 saat commit yok.
**Eksik:** issue → kanban kartı dönüşümü yok. İki ayrı sistem, aralarında kuyruk yok.
**Neden önemli:** Sistem şu an 7/24 *raporluyor*, 7/24 *çalışmıyor*. Üretilen
her issue karşılıksız bir borç.

### A2 — Üretim hızı > tüketim hızı (Kritik)
**Gözlem:** Scout 30 dakikada 1 issue'ya kadar üretiyor; kanban `max_in_progress=1`
ve iş başına ~15-45 dk worker süresi.
**Eksik:** backpressure yok. Kuyruk şişince üretimi yavaşlatan bir kural yok
(prompt'ta "tick başına max 1" var, ama *toplam açık iş sayısı* sınırı yok).
**Neden önemli:** 62 issue = ~31 saatlik worker kuyruğu; ve öncelik sırası yok.

### A3 — İnsan kapısında bekleyen işin kuyruğu yok
**Gözlem:** `t_a9030f28` (re-benchmark) 13+ saattir `blocked`; nedeni
"autonomous merge prohibited". Onu açacak mekanizma yok.
**Eksik:** "insan kararı bekliyor" durumu için ayrı bir kuyruk + eskalasyon
(push bildirim, günlük özet başlığı).
**Neden önemli:** Loop kendi kilitini çözemiyor, sessizce duruyor.

### A4 — Block → resume politikası tanımsız
**Gözlem:** 1 blocked task 13 saat durdu, hiçbir koordinatör tick'i eskalasyon
üretmedi.
**Eksik:** block yaşı eşiği (örn. >2 saat) → otomatik rapor/eskalasyon.

---

## B. Dayanıklılık

### B1 — Provider kesintisinde tüm loop ölüyor (Kritik)
**Gözlem:** 16:42:29–23:52 arası 4 job'un tamamı başarısız.
`Codex stream produced no SSE events for 237s (threshold 60s)`.
**Eksik:** circuit breaker, uzun kesinti alarmı, kuyruk dayanıklılığı
(kesinti bitince biriken işi kontrollü işleme).
**Neden önemli:** 7 saatlik kesinti fark edilmedi; "7/24 çalışıyor" iddiası boşta.

### B2 — Hata mesajı yanıltıcı (Yüksek)
**Gözlem:** Gerçek neden `ReadError / Broken pipe / SSE stall`; kullanıcıya
gösterilen mesaj `Hermes can't reach the model provider. You may be offline.`
**Eksik:** hata sınıflandırması — "stream stall" ile "DNS/bağlantı yok" ayrılmalı.
**Neden önemli:** Bugün yanlış teşhis yüzünden model değiştirme yoluna girildi.

### B3 — Sessiz ölüm (Yüksek)
**Gözlem:** `cron.scheduler: Job ... session ended without a final assistant
message — booking run as cron_incomplete_no_output`. Hiçbir bildirim gitmedi.
**Eksik:** incident → kullanıcı bildirimi yolu (delivery 'local' ile bitiyor).

### B4 — Fallback yok (Yüksek)
**Gözlem:** `fallback_providers: []`, `delegation.model: ''`.
**Eksik:** ikinci provider/model zinciri (örn. Nous, Antigravity local :8045).

---

## C. Model / konfigürasyon yönetimi

### C1 — Fail-closed sessizliği (Orta)
**Gözlem:** `hermes config set model.default` sonrası uyarı:
"2 enabled unpinned cron jobs have stored model_snapshot values that differ...
They will fail closed on their next run."
**Eksik:** unpinned job'ların varlığını sürekli denetleyen bir kontrol; pin
zorunluluğu (drift check).

### C2 — Model envanteri doğrulanmamış (Orta)
**Gözlem:** Doğrudan provider testinde `muse-spark-1.3-contributor` → HTTP 500,
`deepseek-v4.1-flash` → HTTP 200. Hermes üzerinden ikisi de bir kez çalıştı.
**Eksik:** periyodik "hangi model gerçekten sağlıklı" probu + sonuç kaydı.
**Not:** Bugün yapılan düzeltme: global + 4 profil + 4 cron job →
`deepseek-v4.1-flash` / `opencode-go`, `reasoning_effort: medium`.

---

## D. Maliyet / bütçe

### D1 — Token bütçesi sadece prompt'ta (Orta)
**Gözlem:** Scout prompt'unda "30k token tavan" yazıyor; ölçülen gerçek
~232k token/run. Teknik enforcement yok.
**Eksik:** run başına token ölçümü + eşik aşımında uyarı/kesme.

### D2 — Abonelik limiti takibi yok (Orta)
**Gözlem:** opencode-go $60/ay limiti kullanıcı beyanı; harcama görünürlüğü yok.
**Eksik:** günlük/aylık harcama raporu; limite yaklaşınca uyarı.
**Neden önemli:** limit dolduğunda hata yine "provider'a ulaşılamıyor" olarak
görünür (B2 ile aynı tuzak).

---

## E. Doğrulama / kanıt

### E1 — `done` doğrulanmış anlamına gelmiyor (Yüksek)
**Gözlem:** 17 done; `v8-verifier` atamalı yalnızca 1 task var.
**Eksik:** her `done` için bağımsız verifier receipt'i zorunlu mu, değil mi —
kural net değil.

### E2 — Yayınlanan her sayının kaynak izi yok (Yüksek)
**Gözlem:** `#395` — readiness, `cap × 0.18` olarak hardcode türetiliyordu ve
bültende bağımsız bir iyileşme gibi yayınlanıyordu.
**Düzeltme:** readiness artık sertifika artifact'ından okunuyor, kaynak + mtime
ile yayınlanıyor; kaynak yoksa alan yayınlanmıyor.
**Eksik:** bu kuralın (kaynaksız metrik yayınlanmaz) genel bir kontrol olarak
uygulanması — bulletin/status üreticilerinde tek tek değil, tek kapıda.

### E3 — Ledger tamper açık (Orta)
**Gözlem:** entry 0 `DIGEST_TAMPERED`; `verify_chain()` → chain true, ledger false.
**Eksik:** recompute prosedürünün insan onayı olmadan çalışabilmesi mi, yoksa
append-only kabul mü — karar yok.

---

## F. Ürün / ekonomik planlama

### F1 — "Bitti" tanımı yok (Kritik)
**Gözlem:** Amaçlar karışık: cap'i fullemek, readiness'i yükseltmek, canlıda
kâr etmek, kitapları bağlamak.
**Eksik:** tek cümlelik, ölçülebilir bitiş koşulu + hangi metrik birincil.
**Neden önemli:** Öncelik sırası olmadan her tick farklı yöne çekiyor.

### F2 — Negatif ekonomik sonucun planı yok (Yüksek)
**Gözlem:** `P net +0.0073`, `P+E +0.0035`, incremental **−0.0038**.
**Eksik:** "challenger daha kötüyse ne yapılır" prosedürü (reddet ve kaydet —
zorla pozitife çevirme kuralı var ama sonraki adım tanımsız).

### F3 — Kitaplar bağlanmıyor (Orta)
**Gözlem:** 167 PDF, ~150'si BenchmarkCase'e mapped değil.
**Eksik:** books → grammar → BenchmarkCase döngüsünün worker'a verilmiş bir işi yok.

---

## Öncelik önerisi (ilk 5)

1. **A1** — issue → kanban köprüsü: scout'un açtığı issue otomatik `v8-engineer`
   kartına dönüşsün (dedup + tick başına 1 sınırı korunarak).
2. **B1/B3** — kesinti tespiti + bildirim: N ardışık job fail → kullanıcıya uyarı.
3. **F1** — "bitti" tanımı: birincil metrik + bitiş koşulu tek cümle.
4. **B4** — fallback provider/model zinciri.
5. **E1/E2** — doğrulama ve kaynak izi kapısı (tek kapı, üretici başına değil).

## Bu turda yapılan düzeltmeler (kanıtlı)

- `model.default` = `deepseek-v4.1-flash`, provider `opencode-go`,
  `agent.reasoning_effort` = `medium` (global).
- 4 profil (`v8`, `v8-engineer`, `v8-scout`, `v8-verifier`) aynı değerlere çekildi.
- 4 cron job (`e0a9e2697d65`, `22cc41110ef7`, `fc3ed15d4d90`, `87718e7675a1`)
  model/provider'a pinlendi; `model_snapshot` temizlendi.
- Canlı doğrulama: `hermes chat -q "reply with the single word: ok" --oneshot -Q`
  → `ok`, exit 0.
- `#395` düzeltildi: readiness gerçek sertifika artifact'ından okunuyor
  (commit `b1c29bea`).
