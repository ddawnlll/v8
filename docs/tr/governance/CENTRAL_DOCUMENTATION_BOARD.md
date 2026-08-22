# Merkezi Döküman Kurulu Tüzüğü (Central Documentation Board)

**Statü:** KİLİTLİ DEĞİŞMEZ (Kural 8, Kural 36, Karar D-134).

**Merkezi Döküman Kurulu**, V8 ekosisteminde epistemik dürüstlüğü, çift dilli senkronizasyonu, karar izlenebilirliğini ve sıfır-gölge dokümantasyonu korumaktan sorumlu egemen kurumsal organdır.

---

## 🏛️ 1. Kurumsal Görev

Merkezi Döküman Kurulu üç temel anayasal görev tarafından yönetilir:
1. **Sıfır-Gölge Dokümantasyon:** `docs/contracts/IMPLEMENTATION_LAYOUT.md` ve `docs/decisions/DECISION_REGISTER.md` içinde haritalanmamış hiçbir Rust modülü, API arayüzü veya algoritmik değişiklik var olamaz.
2. **Katı Çift Dilli Senkronizasyon:** Her İngilizce şartname, karar, anayasa maddesi ve yol haritası maddesi `docs/tr/` altında doğrulanmış birebir Türkçe karşılığa sahip olmak zorundadır.
3. **Deterministik Tek Dosyalı Monograf Derlemesi:** Her mimari değişiklikte İngilizce ve Türkçe monograflar (`site/index.html` ve `site/tr.html`), `tools/build_monograph.py` ile deterministik olarak derlenmelidir.

---

## 🔍 2. Doğrulama ve Teftiş Hattı

```text
       GIT COMMIT / DEĞİŞİKLİK
                  │
                  ▼
    SIFIR-GÖLGE DENETİMİ (D-032, D-132)
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
 İNGİLİZCE DOKÜMAN    TÜRKÇE AYNA
  (docs/*)             (docs/tr/*)
        │                   │
        └─────────┬─────────┘
                  ▼
    TOOLS/BUILD_MONOGRAPH.PY
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
  site/index.html       site/tr.html
 (Tek Dosyalı EN)      (Tek Dosyalı TR)
```

---

## ⚖️ 3. Kurul Yetkileri ve Veto Gücü

1. **Kapı Kilitleme:** Dokümantasyon as-built koddan saparsa veya monograf derlemesi başarısız olursa, Merkezi Döküman Kurulu CI kapısını kırarak merge'i engeller.
2. **Karar ve Hafıza Emaneti:** Kurul, `docs/decisions/DECISION_REGISTER.md` ve `docs/governance/COMMITTEE_MEMORY_LEDGER.jsonl` üzerinde kriptografik emanetçidir.
