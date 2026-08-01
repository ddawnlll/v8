# V8 Karar Kaydı v0.1

| ID | Karar | Durum | Kanıt / sonuç |
|---|---|---|---|
| D-001 | Candidate bir emir değildir; her yaşam-döngüsü terminal durumunu kaydet | PROVISIONAL_DECISION | V7 seçim-yanlılığı/state-machine başarısızlıklarıyla desteklenen tasarım çıkarımı. Yalnızca-trade verisine karşı test et. |
| D-002 | Açık saatlerle zaman-noktası, değiştirilemez MarketState kullan | LOCKED_INVARIANT adayı | V7 nedensellik/otorite kontrolleri; sızıntı bir geçerlilik ihlalidir. |
| D-003 | 2–3 deterministik kendi-kendine kapılanan Expert ile başla | PROVISIONAL_DECISION | En küçük atfedilebilir yönlendirme taban çizgisi; Expert'lerin global modelleri yendiğine dair kanıt yok. |
| D-004 | Başlangıçta router uygulama | REJECTED_OPTION (taban çizgi için) | Router değerli-candidate geri çağırımı ve bağlayıcı bir compute/gecikme gerekçesi gerektirir. |
| D-005 | Kurallı deterministik Level-1 execution ilk karşılaştırıcıdır | PROVISIONAL_DECISION | V7 kontrolleri uygulamayı destekler, ama sertifikasyon FAIL/BLOCKED olarak kalır. |
| D-006 | Öğrenilmiş execution/RL başlangıç mimarisinden hariç tutulur | REJECTED_OPTION (taban çizgi için) | V7 kanıtında entegrasyon/state-machine sorunları ve ekonomik sertifikasyon yok. |
| D-007 | Başlangıçta scorer yok | PROVISIONAL_DECISION | Yalnızca tekrarlanabilir sabit-kapsam OOS net faydası deterministik skoru aşarsa kabul et. |
| D-008 | Başlangıçta ranker yok | PROVISIONAL_DECISION | Yalnızca gösterilmiş sermaye/risk çekişmesi ve eşleştirilmiş tahsis kazancı altında kabul et. |
| D-009 | Alpha/execution'ı operasyonel olarak ayrık tut, istatistiksel olarak bağımsız değil | LOCKED_INVARIANT | Ana brief ve denetim bir bağımsızlık iddiasını reddeder. |
| D-010 | Tüm terfi iddiaları kod/veri/config/tohum/defter hash'lerini bağlar | LOCKED_INVARIANT adayı | Proje mühendislik kanıtı; eksik makbuz hükmü engeller. |

Durum sözlüğü kasıtlıdır: `LOCKED_INVARIANT` geçerliliği sınırlar;
`PROVISIONAL_DECISION` geri alınabilir; `REJECTED_OPTION` adı geçen taban
çizgiden hariç tutulmuştur, sonsuza dek çürütülmüş değildir. Hiçbiri kârlılık
anlamına gelmez.
