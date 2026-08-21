# Kanonik Kanser Taksonomisi ve Mega Hareket Kampanyası Denetimi

**Durum:** ONAYLANMIŞ DENETİM (D-123)  
**Yetkili Otorite:** `docs/contracts/VENUE_AND_CAPITAL_SIMULATION_SPEC.md`, `TARGET_ORACLE_SPEC.md` §12, `docs/audits/CANONICAL_CANCERS_AND_MEGA_MOVE_AUDIT.accp.yaml`  
**Akademik Kaynaklar:** arXiv:1603.06183 (Risk-Constrained Kelly), arXiv:2602.11708 (AdaptiveTrend), arXiv:2402.05272 (Jump Modelleri), arXiv:1904.04912 (Deep Momentum Networks).

---

## 1. Yönetici Teşhisi

Bu denetim raporu V8'in **6 Kanonik Kök Kanserini** tesciller ve **05–06 Şubat 2026 BTC Mega Atağını (5250–5310 Barları)** resmi mikro zemin gerçeği (Ground Truth) olarak tanımlar.

### 6 Kanonik Kanser
1. **KANSER-01 — Sermaye ve Lot Diskretizasyon Felci:** Sabit %0.5 risk, bakiye düştüğünde Binance 0.001 BTC lot adımının altında kalarak 32.428 adayın elenmesine (`QUANTITY_ROUNDS_TO_ZERO`) yol açar.
2. **KANSER-02 — Sağ Kuyruğu Kesen Exit Geometrisi:** Sabit 1R/2R TP sağ kuyruğu budar; çıkış yapanların %79'u +2R üstüne devam etmiş, post-exit MFE ortalama +4.5R olmuştur.
3. **KANSER-03 — Uzman Çorbası ve Tahsis Kaosu:** 42.647 tetikleme 14.766 dedup ve yalnızca 2 gerçekleşen işlem üretir; 28 sensör tek bir kampanya altında toplanamamaktadır.
4. **KANSER-04 — Portföy Bağlamı ve Rejim Körlüğü:** Soft Bayesian risk çarpanlarının yokluğu; katı rejim filtreleri gecikme yüzünden mega hareketin ilk %30–50'sini kaçırır.
5. **KANSER-05 — Alfa / Mekanik Taban Yetersizliği:** Ham sinyaller sıfır-beceri rastgele girişten farksızdır; önce büyük hareket yakalama başarısı (Large-Move Recall) ölçülmelidir.
6. **KANSER-06 — Veri ve Sponsorluk Körlüğü:** 1h OHLCV + fonlama bandında açık pozisyon (OI) ve likidasyon derinliği eksiktir.

---

## 2. Zemin Gerçeği: 05–06 Şubat 2026 Olayı

- **Çöküş Fazı:** $73.137 \to 62.868 \text{ \$}$ (24 saatte -%14.04).
- **V-Dip Yükselişi:** $62.868 \to 70.544 \text{ \$}$ (24 saatte +%12.21).
- **Mevcut Durum:** 191 sinyal üretildi $\to$ **0 işlem açıldı.**
- **İyileştirme Hedefi:** Quantization-Aware boyutlandırma ve Trailing Stop ile hareketin $\ge \%65$'ini cebe indirmek.
