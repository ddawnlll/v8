# V8 Kanıt Matrisi

| Alan | Literatür desteği | Proje kanıtı | V8 yaklaşımı |
|---|---|---|---|
| Likidite, emir akışı, volatilite bağlamı | Evet; Kaynak Haritası S1–S4 | V8'e özgü sonuç yok | Hipotez olarak kullan, trade göstergesi olarak değil |
| Trader bilişi | Uzmanlık koşulları ve karar teorisi | Trader çalışması yok | Gramer yalnızca biçimsel tasarım aracıdır |
| Candidate yaşam döngüsü | Olay-sourcing ve sansürleme denetlenebilirliği destekler | V7 state-machine/no-trade raporlama başarısızlıkları buldu | PROVISIONAL; yaşam döngüsü ablasyonu çalıştır |
| Zaman-noktası State | PIT/revizyon riskleri belgelenmiş | V7 nedensel sözleşmeler | LOCKED geçerlilik değişmezi |
| Expert ayrıştırması | Doğrudan trading kanıtı yok | İlgili karşılaştırma yok | OPEN; eşleştirilmiş global-taban-çizgi testi |
| Router | MoE'de açlık/yanlış-negatif riskleri var | Router testi yok | Taban çizgiden hariç tut |
| Scorer | Seçici tahmin/meta-label benzerlikleri | Çekimserlik (abstention) tuzakları gözlemlendi | Sabit-kapsam kazancına kadar ertelendi |
| Ranker | Portföy etkileşimi gerçektir | Kapasite-çekişmesi kanıtı yok | Ertelendi |
| Execution simülasyonu | Maliyet/etki teorisi ve olay sıralaması | V7 güçlü kontrollere sahip ama otorite sertifikasyonu başarısız | Yalnızca Level-1 karşılaştırıcı; ekonomi iddiası yok |
| Çıkarım | Bağımlılık ve arama-yanlılığı yöntemleri mevcut | V7 kümelenmiş/karıştırılmış teşhisler kullandı | Zorunlu protokol, dekoratif istatistik değil |

Detaylı alıntılar [SOURCE_MAP.md](SOURCE_MAP.md) içinde, yerel kanıt sınırları
[PROJECT_EVIDENCE_AUDIT.md](PROJECT_EVIDENCE_AUDIT.md) içindedir.
