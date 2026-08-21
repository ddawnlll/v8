# ACCP v2.0 — YAML Tabanlı Ajan Kodlama İletişim Protokolü Şartnamesi

**Durum:** ONAYLANMIŞ SÖZLEŞME (D-124)  
**Sürüm:** 2.0.0  
**Format:** ACCP-YAML  
**Yetkili Otorite:** `docs/contracts/ACCP_V2_SPEC.md`, `WORK_ITEM_POLICY.md` §1–4

---

## 1. Yönetici Özeti

ACCP v2.0, ajan kodlama iletişimleri için şema tarafından doğrulanabilir, katı ve derlenebilir bir protokol kurar:
- Kaynak raporlar saf YAML belgeleridir (`.accp.yaml`).
- Markdown sadece insan tarafından okunabilir bir görünümdür, asla makine girdi kaynağı değildir.
- 27 resmi rapor tipi kademeli destek seviyeleriyle tescil edilmiştir (`known`, `template_available`, `schema_lite`, `schema_strict`, `gate_blocking`).
- Temel Prensip: *Ajan önerir $\to$ Derleyici doğrular $\to$ Çalışma zamanı karar verir.*

---

## 2. 27 Resmi Rapor Türü

1. **Çekirdek (10):** `RIR`, `PIR`, `IPR`, `TVR`, `HIR`, `RAR`, `PRR`, `CAR`, `ASR`, `ECR`
2. **Hata Düzeltme (5):** `BSR`, `BRR`, `RCA`, `FPR`, `FVR`
3. **Özellik Geliştirme (5):** `FER`, `FDR`, `FCR`, `FIR`, `FGR`
4. **Metin/Yazım (4):** `WBR`, `WDR`, `WER`, `WQR`
5. **Koordinasyon (2):** `DCR`, `ECR`
6. **Belgelendirme (1):** `ASR`

---

## 3. Katı YAML Kaynak Profili ve V8 Entegrasyonu

Tüm `.accp.yaml` kaynak dosyaları şema standartlarına uyar, diff bütünlüğü, geri alma planı ve kanıt komutlarını bağlayıcı biçimde derleyerek çalışma zamanı kapılarına girdi sağlar.
