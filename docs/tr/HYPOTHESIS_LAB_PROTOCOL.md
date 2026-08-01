# V8 Hipotez Laboratuvarı Protokolü v0.1

**Amaç:** öğrenilmiş yönlendirme, skorlama, sıralama, daha zengin veri ya da
execution öğreniminden önce zayıf davranış hipotezlerini ucuzca reddetmek.
**Durum:** PROVISIONAL_DECISION; eşikler deneye-özgüdür ve önceden
kaydedilmelidir, donmuş holdout'u inceledikten sonra asla ayarlanmaz.

## Hipotez kaydı

Her H1–H8 kaydı şunları içerir: biçimsel null/alternatif; ekonomik mekanizma ya
da açık bir `mechanism unknown`; davranış ve deterministik tespit kuralı;
as-of evren üyeliği; veri/kaynak manifesti; karar/bilgi/kullanılabilirlik
saatleri; kurallı geometri ve maliyetler; bağımlılık birimi; birincil metrik;
test; minimum olay/varlık kapsamı; geliştirme/donmuş bölümler; ve reddetme
sonucu.

Dört tarama durumu şunlardır: `NO_OPPORTUNITY`, `HINDSIGHT_ONLY`,
`WEAKLY_SELECTABLE`, `FORMALIZATION_CANDIDATE`. Bunlar belirtilen deney için
etiketlerdir, piyasa gerçekleri değildir. Oracle istatistiği
`E[max(U_long,U_short,0)]`, sonucun ardından yönü seçtiği için seçilebilir edge
kanıtı olarak yasaktır.

## Ucuzdan-pahalıya merdiven

| Aşama | Soru | Gerekli kontrol | Çıktı |
|---|---|---|---|
| Tarama | Sabit bir dedektör, maliyetler sonrası null'dan ayırt edilebilir mi? | kronoloji, muhafazakâr Level-1 simülasyon, basit null | reddet/replikasyon önerisi |
| Replikasyon | Varlık/zaman rejimine göre kalıcı mı? | dokunulmamış kronolojik dilim, blok bootstrap | replike ya da reddet |
| Terfi | Bir ekleme daha basit sabit baseline'ı yeniyor mu? | eşleştirilmiş OOS farkı, çokluk kontrolü | bileşeni kabul/erte/reddet |
| Shadow/canlı | Kağıt sonucu operasyonel gerçekliğe dayanıyor mu? | donmuş kod/veri + gerçekleşmiş defter | yalnızca operasyonel kanıt |

Etiketler/tutma aralıkları eğitim gözlemleriyle örtüştüğünde yalnızca temizleme/
ambargo ile bloklanmış zaman bölmeleri kullan. Bildirilen bir bağımlılık
biriminde (en az gün/oturum; otokorelasyon gerektiriyorsa daha uzun) blok ya da
durağan bootstrap, IID trade'ler varsaymadan belirsizlik verir. Permütasyon,
null'un gerektirdiği yerde volatiliteyi ve zaman yapısını korumalıdır (örn. blok/
işaret ya da yön karıştırma) ve test edilen yapıyı karıştırıp atmamalıdır.
Candidate-örtüşmesi ve çapraz-varlık bağımlılığı, küme-farkında özetler ya da
hiyerarşik bir model gerektirir; saf trade-düzeyi t istatistikleri sunma.

## Baselinelar ve kapılar

Her davranış şunlarla başlar: trade-yok; deterministik ham candidate; maliyet
stresi altında aynı candidate; yön/etiket-karıştırılmış kontrol; ve bir global
model iddia ediliyorsa eşit-bilgili global baseline. Tüm geometri/maliyet
seçimleri donmuş OOS'tan önce sabitlenir. Bir geçiş, önceden kayıtlı
net-fayda etkisini, belirsizlik aralığını/testini, operasyonel geçerliliği ve
replikasyon koşullarını gerektirir. Bir başarısızlık/yetersiz olay sayısı, aşağı
akış bileşen çalışmasını engeller; zıt piyasa hipotezini kanıtlamaz.

Keşfedilen çoklu Expert varyantları bir aile oluşturur: tüm denemeleri raporla,
FDR'yi kontrol et ya da uygun olduğunda bir Reality Check/SPA-tarzı aile
karşılaştırması uygula ve son dokunulmamış bir değerlendirme ayır. Deflated
Sharpe ve PBO, seçim yanlılığı için teşhislerdir; donmuş bir holdout ya da
ekonomik bir modelin yerine geçmezler.

## Kaynaklar ve kapsam

* **LITERATURE_SUPPORTED:** White'ın Reality Check'i, test edilen bir kural
  ailesi üzerinde veri-snooping'i ele alır; Hansen'in SPA'sı zayıf/kötü
  alternatifler için pratik davranışı iyileştirir
  ([White 2000](https://doi.org/10.1111/1468-0262.00152),
  [Hansen 2005](https://doi.org/10.1198/073500104000000631)).
* **LITERATURE_SUPPORTED:** durağan bootstrap, bağımlı serileri bloklar halinde
  yeniden örnekler
  ([Politis & Romano 1994](https://doi.org/10.1080/01621459.1994.10476870)).
* **LITERATURE_SUPPORTED (sınırlı):** deflated Sharpe, normal-dışılık ve
  seçim/backtest-aşırı-uyum riskleri için ayarlar; varsayımları ve deneme sayısı
  açıklanmalıdır
  ([Bailey & López de Prado 2014](https://doi.org/10.3905/jpm.2014.40.5.094)).
* **PROJECT_EVIDENCE_SUPPORTED:** V7'nin gün-kümeli belirsizliği ve
  karıştırılmış yön kontrolü, belirtilen P1 ayarının başarısız olduğunu buldu;
  bu sonuç V8 Expert'leri hakkında kanıt değildir (`PROJECT_EVIDENCE_AUDIT.md`).
