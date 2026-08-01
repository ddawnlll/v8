# V8 Açık Kararlar v0.1

| ID | Açık soru | En ucuz çözücü deney | Kabul / reddetme koşulu |
|---|---|---|---|
| O-001 | Seçilen herhangi bir davranışın maliyet-sonrası koşullu değeri var mı? | Sabit deterministik Expert vs trade-yok/karıştırılmış kontrol | Yalnızca önceden kayıtlı, replike OOS kanıtıyla terfi et; aksi halde o Expert'i reddet. |
| O-002 | Hangi durum temsili değer katar? | ham pencere vs işlenmiş durum vs hibrit, eşit veri/model bütçesi | Yalnızca artımlı replike sonucu koru; öğrenilmiş gizli durum ertelendi. |
| O-003 | Tam yaşam döngüsü öğrenmeyi/denetlenebilirliği iyileştirir mi? | Sabit bir görev için Candidate-geçiş tablosu vs yalnızca-işlem tablosu | Önceden kayıtlı kalibrasyon/atıfı iyileştirirse koru; aksi halde yönetişim değeri maliyeti haklı çıkarıyorsa yalnızca kayıt tut. |
| O-004 | Router değerli mi? | self-gating vs deterministik ön-router eşleştirilmiş replay | Neredeyse-mükemmel önceden kayıtlı değerli-candidate geri çağırımı artı bağlayıcı kaynak kazancı gerektir. |
| O-005 | Scorer seçim değeri katar mı? | deterministik kanıt skoru vs lojistik vs sığ ağaç, eşleşen kapsamda | Tekrarlanan OOS net-fayda kazancı ve kalibrasyon gerektir; yalnızca daha az trade başarısız olur. |
| O-006 | Sıralama gerekli mi? | çekişme sırasında tüm kabul edilen candidate'lar vs deterministik 1/N/risk sınırı | Tekrarlayan çekişme ve eşleştirilmiş marjinal portföy-faydası kazancı gerektir. |
| O-007 | Hangi sadakat gerekiyor? | Spesifik sonucun Level 0/1 arası duyarlılığı; yalnızca maddi belirsizlikte ilerle | Sonuç desteklenmeyen dolum varsayımlarıyla değişiyorsa, daha zengin tape olmadan engelle. |
| O-008 | Execution uzmanlaşabilir mi? | herhangi bir öğrenilmiş politikadan önce stres altında sabit kurallı execution | Sertifikalı pozitif bir Expert ve istikrarlı kurallı taban çizgi olmadan öğrenilmiş executor yok. |

Tümü `OPEN_QUESTION`'dır. Hiçbir alan bir dashboard sonucu, kayıtsız parametre
taraması ya da sentetik veriyle sessizce çözülemez.
