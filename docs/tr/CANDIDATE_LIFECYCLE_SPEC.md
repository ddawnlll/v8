# V8 Candidate Episode Yaşam Döngüsü

**Durum:** PROVISIONAL_DECISION. Bir Candidate yanlışlanabilir bir trade
hipotezi kaydeder; bir emir, tavsiye ya da gelecekteki kârlılık etiketi değildir.

## 1. Kimlik ve donmuş doğum kaydı

`candidate_id` bir UUID'dir. `episode_key` deterministiktir:
`hash(expert_id, expert_version, instrument_id, direction, setup_fingerprint,
birth_decision_time)`. Expert'in bildirdiği tekilleştirme penceresi içinde bir
çakışma ya da tekrar, sessizce kaybolmak yerine mevcut episode'a bağlanır
(`SUPPRESSED_DUPLICATE`). Maddi olarak farklı yeni kurulum kanıtı yeni bir ID
alır.

Doğumda değiştirilemez bir `BirthSnapshot` kaydet: durum/feature soyağacı,
expert sürümü, kurulum kanıtı, önerilen tetikleyici, geçersizleştirme, sona
erme, risk geometrisi, karar saati ve tüm girdi kullanılabilirlik
maksimumları. Daha sonraki durum bir geçiş anlık görüntüsü olarak eklenebilir
ama doğum kaydını yeniden yazamaz.

## 2. Durum makinesi

```text
DETECTED -> PENDING -> TRIGGERED -> ACCEPTED -> ORDER_SUBMITTED -> EXECUTED -> CLOSED
    |          |            |            |              |              |
    v          v            v            v              v              v
 REJECTED   EXPIRED     INVALIDATED   REJECTED       CANCELLED       (terminal)
    \__________\______________\____________\______________/
                       -> ARCHIVED
```

`DETECTED` bir expert gözlemidir, henüz tam bir trade hipotezi değildir.
`PENDING` tam bir tetikleyici/geçersizleştirme/sona erme sözleşmesine sahiptir.
`TRIGGERED`, tetikleyici yükleminin kabul edilebilir bilgi kullanılarak
gözlemlendiği anlamına gelir—dolumun gerçekleştiği değil. `ACCEPTED` bir
portföy/risk kabul kararıdır. `EXECUTED` en az bir dolum gerektirir. `CLOSED`
tamamlanmış bir pozisyon yaşam döngüsüne sahiptir. `REJECTED`, `EXPIRED`,
`INVALIDATED`, `CANCELLED` ve `ARCHIVED` terminaldir.

| From | Olay | To | Gerekli karar-zamanı kanıtı |
|---|---|---|---|
| — | `setup_detected` | DETECTED | expert değerlendirmesi + MarketState ref |
| DETECTED | `hypothesis_completed` | PENDING | tetikleyici, geçersizleştirme, sona erme, risk |
| DETECTED/PENDING/TRIGGERED/ACCEPTED | `reject` | REJECTED | neden kodu + aktör/sürüm |
| PENDING | `trigger_observed` | TRIGGERED | tetikleyici yüklemi + TriggerSnapshot |
| PENDING | `expiry_reached` | EXPIRED | saat ve sona erme kuralı |
| PENDING/TRIGGERED | `invalidation_observed` | INVALIDATED | yüklem + anlık görüntü |
| TRIGGERED | `risk_accept` | ACCEPTED | kapasite/risk kararı kanıtı |
| ACCEPTED | `submit_order` | ORDER_SUBMITTED | kurallı emir planı |
| ORDER_SUBMITTED | `fill_observed` | EXECUTED | dolum ref; kısmi dolumlar burada kalır |
| ORDER_SUBMITTED | `cancel_confirmed` | CANCELLED | mekan/emir olayı |
| EXECUTED | `position_flat` | CLOSED | pozisyon/dolum/sonuç ref'leri |
| herhangi bir terminal | `retain` | ARCHIVED | saklama/sürüm politikası |

Diğer tüm geçişler kapalı-başarısız olur. Tetikleme sonrası geçersizleştirme,
bir deney açıkça iptal/değiştirme modellemediği sürece, dolum
gerçekleşene kadar yasaldır. Yeniden aktivasyon yasaktır: terminal durumdan
sonra `parent_candidate_id` ve bildirilmiş yeni bir kurulum parmak iziyle yeni
bir episode yarat. Bir Expert, belgelenmiş eşzamanlılık ve tekilleştirme
politikalarına bağlı olarak birçok candidate'a sahip olabilir.

## 3. Yaşam-döngüsü doğruluğu ve olay sourcing

`CandidateTransition` yalnızca-eklenendir. Değiştirilemez sırası
`(knowledge_time, transition_sequence)`'tir; alım sırası değil. Şunları içerir:
`event_time`, `available_time`, `knowledge_time`, `from_state`, `to_state`,
`reason_code`, `actor_type`, `actor_version`, `snapshot_ref`,
`evidence_refs` ve `event_hash`. Güncel durum, somutlaştırılmış bir
projeksiyondur; geçiş günlüğünün replay'ı onu yeniden üretmelidir.
Düzeltmeler, orijinali koruyarak üstün gelen bir olay ekler.

Bu, bir denetim/yeniden-inşa örüntüsü olarak **LITERATURE_SUPPORTED**'dır:
olay sourcing, durum değişikliklerini olaylar olarak saklar ve
yeniden-inşa/zamansal sorgulara izin verir
([Fowler, Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)).
Kesin durum adları ve yeniden-aktivasyon yasağı **DESIGN_INFERENCE**'dır.

## 4. Etiketler, karşı-olgusallar ve sansürleme

Geçiş sonucu candidate kalitesi değildir. Ayrı alanları koru:

* `observed_execution_outcome`: yalnızca gerçekten gönderilen emirler/dolumlar.
* `counterfactual_outcome`: adlandırılmış, sürümlenmiş bir execution politikası
  altında deterministik simülatör sonucu; asla gözlemlenmiş bir dolum değil.
* `label_status`: `MATURE`, `RIGHT_CENSORED`, `INVALIDATED`, `EXPIRED`,
  `NOT_EXECUTED` ya da `UNAVAILABLE`.

Sona erme/geçersizleştirme yaşam-döngüsü olgularıdır, otomatik olumsuz
etiketler değildir. Bir candidate, önceden bildirilmiş etiket ufku
tamamlanmadıysa ya da gerekli piyasa verisi kullanılamıyorsa sağdan
sansürlüdür. Rakip son noktalar (hedef, stop, sona erme, zorunlu çıkış) ayrı
nedenler olarak temsil edilmelidir; aynı-bardaki eşitlikler geriye-dönük
seçimle değil, önceden bildirilmiş simülatör politikasıyla çözülür. Bu,
takibin son nokta olmadan bitebileceği ve olay türünün farklı olduğu standart
rakip-risk konvansiyonunu izler
([R survival competing-risk vignette](https://cran.r-project.org/web/packages/survival/vignettes/compete.pdf)).

## 5. Ucuz testler

* Karıştırılmış-alım günlüğünü `(knowledge_time, sequence)` ile sırala ve
  replay et; özdeş durum/hash'i iddia et.
* `PENDING -> EXECUTED`, `CLOSED -> PENDING` ve çift geçişi dene; her biri
  başarısız olmalı.
* Aynı saatte tetikle ve geçersizleştir: bildirilen önceliği uygula ve her iki
  kaynak olgusunu da sakla; daha sonraki fiyat yolundan seçim yapma.
* Bastırma penceresi içinde ikinci bir eşit `episode_key` yarat: düşen bir
  satır değil, açık bir bastırma kaydı sağla.
* Ufuk-sonrası veriyi sil: etiket kayıp değil `RIGHT_CENSORED` olur.
