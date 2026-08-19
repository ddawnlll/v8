# V8 İş Öğesi, Çekme İsteği (PR) ve Birleştirme Yönetişim Politikası v1.2

**Belge Durumu:** `LOCKED_INVARIANT / PROVISIONAL_DECISION (v1.2 Pilot)`  
**Yetkili Otorite:** V8 Anayasası, D-099, D-117  
**Kanonik Kapsam:** Depo genelinde işbirlikçi geliştirme iş akışı (Issue → PR → Review → Merge).

---

## 1. Temel İlkeler ve Felsefe

V8, kanıta dayalı bir kantitatif araştırma ve çalışma zamanı sistemidir. Depoya yapılan her değişiklik şu özelliklere sahip olmalıdır:
1. **İzlenebilir (Traceable):** Eyleme geçirilebilir bir iş öğesinden gereksinim düzeyinde `R#` tanımlayıcılarıyla somut şartname maddelerine ve kayıtlı kararlara eşlenmiş olmalıdır.
2. **Bağlamı Eksiksiz (Context-Complete):** Uygulamaya başlanmadan önce tüm matematiksel değişmezleri, yeniden kullanılacak mevcut tipleri, kanonik hata semantiklerini, bağımlılık topolojilerini ve OPEN_PIN tetikleyicilerini içermelidir.
3. **Kanıt Taşıyan (Evidence-Bearing):** En küçük ayırt edici kontrolle doğrulanmalı ve yeniden üretilebilir doğrulama makbuzları ile sunulmalıdır.
4. **Uydurma Karşıtı (Anti-Invention):** Mevcut yetkili bir sözleşmenin alanı sahiplendiği yerlerde paralel tipler, sahte hata kodları veya geçici arayüzler asla oluşturulmamalıdır.

---

## 2. Otorite Öncelik Hiyerarşisi

Tüm depo geliştirme ve işbirliği süreçleri için:

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. Alan Semantiği                                           │
│    V8 Anayasası > İlgili Sözleşmeler > Karar Kayıtları       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. İşbirlikçi İş Akışı                                      │
│    docs/WORK_ITEM_POLICY.md (Kanonik Issue/PR/Merge Kuralları)│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Giriş Noktası                                            │
│    CONTRIBUTING.md (Politikaya işaret eder, çatallamaz)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Oturum / Otonom Ajanlar                                  │
│    CLAUDE.md / AGENT_RUNBOOK.md / GEMINI.md (Kapsamlı)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Uyuşmazlık Çözümü                                        │
│    İki aktif otorite çelişirse → DUR / OPEN_PIN             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. İş Öğesi Taksonomisi ve Evrensel Issue Sözleşmesi

Tüm çalışmalar beş kanonik formdan biri altında GitHub Issue olarak başlar:
1. **`[DEFECT]`**: Mevcut şartname, değişmez veya temel davranışla gözlemlenen çelişki.
2. **`[IMPL]`**: Yeni semantikler uydurmadan sabitlenmiş bir kararın, sözleşmenin veya eksik modülün uygulanması/bağlanması.
3. **`[RESEARCH]`**: Yanlışlanabilir bir hipotezin, karşılaştırmalı değerlendirmenin (benchmark) veya meydan okuyan (challenger) deneyin ön kaydı.
4. **`[PERF]`**: Bit düzeyinde/semantik eşlik korunarak ölçülmüş profil güdümlü hesaplama optimizasyonu.
5. **`[GOV]`**: Resmi karar kaydı (D serisi), OPEN_PIN çözümü veya kayıt defteri mutasyonu.

### Evrensel Bağlam Eksiksizliği Sözleşmesi
Bir iş öğesi uygulanmak üzere `state:ready` durumuna geçirilmeden önce mutlaka şunları sağlamalıdır:
- **11. Normatif İzlenebilirlik (`R1`, `R2`, ...):** Her gereksinimin şartname maddelerine, D-/O- kararlarına veya testlere açık eşlemesi.
- **12. Yeniden Kullanılacak Mevcut Tipler/Arayüzler:** Yeniden kullanılacak tip, trait, enum, manifest ve sözleşmeler.
- **13. Matematiksel / Semantik Değişmezler:** Formüller, sıralama kuralları ve durum geçişleri.
- **14. Kanonik Hata Semantikleri:** Geçersiz durumların kanonik hata kodlarına eşlenmesi.
- **15. Bağımlılık Haritası:** Mevcut ve yeni düğümleri gösteren veri akış şeması.
- **16. Belirsizlik / OPEN_PIN Tetikleyicileri:** Yürütmeyi durdurup yönetişime iletecek koşullar.

---

## 4. Çekme İsteği (PR) Sözleşmesi ve Doğrulama

Her PR, `.github/PULL_REQUEST_TEMPLATE.md` kullanılarak açılmalı ve şu gereksinimleri karşılamalıdır:
1. **Değişiklik Sınıfı Bildirimi** (ör. `CONTRACT_GOVERNANCE`, `CONTRACT_IMPLEMENTATION`).
2. **Normatif İzlenebilirlik Matrisi (`R# → Otorite → Yüzey → Doğrulama Kapısı → Makbuz`).**
3. **Kapsam ve Sınır Kapanışı:** Yönetişim ve dokümantasyon PR'ları sıfır çalışma zamanı kaynak dosyasına dokunmalıdır.
4. **Aktif CI Kontrolleri:** GitHub Actions check adı: `check` (workflow: `ci`).
5. **Hesaplama Bütçesi (D-099):** 5 saniyeyi aşan kontroller gerekçelendirilmelidir.
6. **Sentetik Veri Yasağı:** Anayasa Kural 12 (`NO_ECONOMIC_CLAIM`) tam uyumu.

---

## 5. Etiket Kataloğu ve Yönlendirme

| Etiket | Kategori | Açıklama |
|---|---|---|
| `triage` | Giriş | Formlar tarafından otomatik uygulanan varsayılan giriş etiketi |
| `type:defect` | Tür | Hata bildirimi |
| `type:implementation` | Tür | Sabitlenmiş uygulama veya bağlantı |
| `type:research` | Tür | Araştırma hipotezi veya deney |
| `type:performance` | Tür | Hesaplama optimizasyonu |
| `type:governance` | Tür | Karar kaydı, OPEN_PIN veya yönetişim |
| `state:triage` | Yaşam Döngüsü | İlk inceleme bekliyor |
| `state:ready` | Yaşam Döngüsü | Bağlamı tam, R# eşlenmiş, geliştirmeye hazır |
| `state:in-progress` | Yaşam Döngüsü | Geliştirme aşamasında |
| `state:review` | Yaşam Döngüsü | İnceleme bekliyor |
| `state:blocked` | Yaşam Döngüsü | OPEN_PIN nedeniyle durduruldu |

---

## 6. CODEOWNERS ve Korumalı Dal Kuralları

- **Korumalı Dal:** `main` dalı korumalıdır. Doğrudan push yasaktır.
- **Birleştirme Koşulları:** `check` CI kontrolü geçmeli, `.github/CODEOWNERS` onayları alınmalı (`@ddawnlll`), doğrusal geçmiş korunmalıdır.

---

## 7. Ölçülen 10–20 Issue Pilotu

v1.2 kuralları, `docs/governance/PILOT_TRACKING_RECORD.md` içinde takip edilen 10–20 issue'luk ölçümlü pilot ile işletilmeye başlanmıştır.
