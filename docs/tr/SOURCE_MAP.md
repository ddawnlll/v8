# V8 Kaynak Haritası — kanıttan-karara triyaj

`v8-0.2.html` (geçici brief) dikkate alınarak hazırlanmıştır. Bu bir araştırma
haritasıdır, **bir mimari karar belgesi değildir.** Bir mekanizmayı destekleyen
kaynak, tek başına bir V8 expert'ini, bir feature'ı ya da canlı-trading kuralını
doğrulamaz.

## Kaynak-seçim standardı

Öncelik orijinal makalelere, resmi araştırma kurumlarına ve bakımı yapılan
teknik dokümantasyona verildi. Aşağıdaki iki uygulayıcı-odaklı öğe, yalnızca
mühendislik/doğrulama bağlamı için tutulur; alpha kanıtı olarak değil.
Kaynaklar 2026-07-31'de doğrudan sayfa/PDF çıkarımıyla kontrol edildi.

| ID | İncelenecek V8 kararı / iddiası | En iyi kaynak(lar) | Kaynağın gerçekte desteklediği | V8 sınıflandırması ve sınır |
|---|---|---|---|---|
| S1 | Likiditeyi ve emir akışını `MarketState`'e dahil et; mekanizmayı görsel bir örüntüden ayır. | [Brandt & Kavajecz (2003), NBER WP 9529](https://www.nber.org/system/files/working_papers/w9529/w9529.pdf); [Vayanos & Wang, *Market Liquidity*](https://web.mit.edu/wangj/www/pap/VayanosWang12Empirical.pdf) | Fiyat keşfi emir akışına ve likiditeye bağlanabilir; likidite, yalnızca teknik bir gösterge değil, arz/talebi olan ekonomik bir nesnedir. | Akış/likidite ilgililiği için **LITERATURE_SUPPORTED**. Mevcut kripto verisinin belirli bir expert için onları yeterince iyi ölçüp ölçmediği **OPEN_QUESTION**'dır. |
| S2 | Dislokasyon/tasfiye-benzeri davranışı bir gösterge reçetesi yerine ekonomik bir hipotez olarak ele al. | [Khandani & Lo (2008)](https://web.mit.edu/Alo/www/Papers/august07b_2.pdf); [BIS, *Crypto carry*](https://www.bis.org/publ/work1087.htm) | Birincisi, kaldıraç-sökümü-güdümlü geçici dislokasyonla tutarlı kanıt verir; BIS çalışması kriptoda ekonomik olarak anlamlı spot–türev basisini ve kurumsal bağlamını belgeler. | Kısıtların ve türevlerin önemli olabileceği **LITERATURE_SUPPORTED**'dır. "Capitulation"ın ayrılabilir, trade edilebilir bir V8 ailesi olduğu **DESIGN_INFERENCE**'dır. Mekan başına biçimsel olarak tanımlanıp test edilmelidir. |
| S3 | `MarketState`, volatilite, aktivite ve rejim-yaşı alanlarına ihtiyaç duyar; değerleri zaman-noktası olmalıdır. | [Andersen et al., *Volatility Forecasting*, NBER WP 11188](https://www.nber.org/system/files/working_papers/w11188/w11188.pdf) | Volatilite/aktivite kalıcılık ve kümelenme sergiler; koşullu volatilite savunulabilir bir bağlam değişkeni yapar. | Koşullu-volatilite bağlamı için **LITERATURE_SUPPORTED**. Kesin durum taksonomisi (`compressed`, `shock` vb.) **PROVISIONAL_DECISION** olarak kalır. |
| S4 | Geniş bir trend/devam ailesi test edilmeye değer, ama evrensel varsayılmamalı. | [Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*](https://doi.org/10.1016/j.jfineco.2011.11.003); [AQR reference paper](https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/A-Half-Century-of-Macro-Momentum.pdf) | Zaman-serisi momentum likit future'lar arasında belgelenmiştir; intraday kripto pullback'leri ya da breakout retest'leri için kanıt değil, koşullu devam araştırması için kanıttır. | Alıntılanan varlık/ufuk kapsamında **LITERATURE_SUPPORTED**. V8'in adlandırılmış expert'leri **OPEN_QUESTION**'dır. |
| S5 | `Candidate | None`'u, aktif çekimserliği ve bir candidate-kalite katmanını destekle. | [Geifman & El-Yaniv (2017), selective classification](https://arxiv.org/abs/1705.08500); [scikit-learn probability calibration guide](https://scikit-learn.org/stable/modules/calibration.html) | Seçici tahmin, doğruluk/kapsam ödünleşimini biçimselleştirir; olasılık çıktıları kalibrasyon kontrolü gerektirir ve kötü tahmin edilmiş olabilir. | Reddetme-seçeneği fikirlerini trading'e uygulamak **DESIGN_INFERENCE**'dır. Kapsam, risk ve güvenilirlik ölçmeyi destekler; bir skoru varsayılan olarak ekonomik olarak kalibre edilmiş saymak değil. |
| S6 | Kurulum tespitini trade-değerliliğinden ayır (strateji-başına meta-kalite). | [López de Prado, *Advances in Financial Machine Learning* SSRN record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3104847) | Meta-labellemeyi, birincil modelin sinyallerine ne zaman aksiyon alınacağını öğrenen ikincil bir model olarak sunar. | **Makul tasarım hipotezi**, V8 skorlamasının net faydayı iyileştirdiğinin bağımsız kanıtı değil. Deterministik bir filtreye karşı karşılaştır ve kalibrasyon artı net sonuçları raporla. |
| S7 | Tespit edilen, tetiklenen, sona eren, geçersizleştirilen ve risk-iptal edilen candidate episode'larını koru. | [CFA Institute, *Investment Model Validation*](https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/rf-brief/investment-model-validation.pdf); [scikit-learn calibration guide](https://scikit-learn.org/stable/modules/calibration.html) | Doğrulama, model girdilerini/çıktılarını ve uygulama koşullarını izlemeyi gerektirir; kalibrasyon, sonuç taşıyan ayrılmış gözlemler gerektirir. | Güçlü ölçüm gerekçesiyle **PROVISIONAL_DECISION**. "Yalnızca-trade hayatta-kalma yanlılığıdır" yönde doğrudur, ama tetiklenmemiş episode'ların kesin öğrenme faydası bir ablasyon gerektirir. |
| S8 | Alpha araştırması sırasında kurallı execution'ı ayrı tut; maliyetleri modelle ama bağımsızlık ilan etme. | [Almgren & Chriss, *Optimal Execution of Portfolio Transactions*](https://quantitativebrokers.com/s/Optimal-Execution-of-Portfolio-Transaction-_-AlmgrenChriss-1999.pdf); [SEC execution-quality proposal](https://www.sec.gov/files/rules/proposed/2022/34-96493.pdf) | Execution'ın açık bir maliyet/risk ödünleşimi vardır; execution kalitesi ölçülebilir açıklama/metrikler gerektirir. | **PROVISIONAL_DECISION**: sabit, sürümlenmiş simülasyon atıf için gereklidir. **REJECTED_OPTION**: execution'ın sinyalden, likiditeden ya da aciliyetten istatistiksel olarak bağımsız olduğunu varsaymak. |
| S9 | Katı zamansal doğrulama, holdout'lar ve çoklu-test kontrolleri kullan; parametre varyantlarını expert olarak terfi ettirme. | [Novy-Marx (2015), NBER WP 21329](https://www.nber.org/papers/w21329); [Bailey et al., Probability of Backtest Overfitting](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253) | Sinyalleri birleştirmek/ayarlamak, gerçek tahmin gücü olmayan görünüşte anlamlı backtestler üretebilir; PBO finans-özgü bir teşhis çerçevesi sağlar. | **LITERATURE_SUPPORTED** risk. Temizlenmiş/ambargolu doğrulama makul bir kontroldür, ama gerçekten dokunulmamış bir nihai dönemin ve uygulama-maliyeti stresinin yerine geçmez. |
| S10 | Expert ayrıştırması vs evrensel bir tahminci; router vs self-gating. | Bunu bir trading sonucu olarak kuran birincil bir kaynak bulunamadı; seçici tahmin ve rejim literatürü yalnızca dolaylı benzetmelerdir. | Davranışa-özgü MoE'nin bir global modeli yeneceğini ya da açık bir router'ın gerekli olduğunu iddia etmek için burada dayanak yoktur. | **OPEN_QUESTION**. Brief'teki deney—global baseline vs self-gated expert'ler vs açık kapı—doğru kanıt yoludur. |
| S11 | Trader bilişi: bir durumu tanı, koşullu bir plan kur, kanıt bekle. | [Kochenderfer, *Decision Making Under Uncertainty*](https://web.stanford.edu/group/sisl/public/dmu.pdf) (genel karar-teorisi metni) | Durum, belirsizlik, aksiyon ve sonuçların biçimsel ele alınışını destekler; trader sezgisini ya da V8 sözlüğünü doğrulamaz. | Yalnızca **DESIGN_INFERENCE**. İnsan iş akışı sözleşmelere ilham verebilir ama kârlılık için kanıt olmamalıdır. |
| S12 | Yalnızca kıt sermaye ve korelasyon/maliyet kısıtları altında candidate'lar-arası sıralama. | [Almgren & Chriss](https://quantitativebrokers.com/s/Optimal-Execution-of-Portfolio-Transaction-_-AlmgrenChriss-1999.pdf); [Vayanos & Wang](https://web.mit.edu/wangj/www/pap/VayanosWang12Empirical.pdf) | Sermaye tahsisi ve trading maliyetler/riskler yaratır; portföy seçimleri bu yüzden etkileşimlere sahiptir. | **PROVISIONAL_DECISION**. Yalnızca gerçekten eşzamanlı kabul edilebilir candidate'lar ve sabit bir tahsis baseline'ı var olduktan sonra ranker ekle. |

## Monografi için acil kanıt sonuçları

1. "Edge yereldir" ifadesini bir olgu olarak belirtme. Test edilebilir bir
   çalışma hipotezidir. Mevcut kanıt, likidite, emir akışı ve volatilite gibi
   mekanizmalara koşullamayı haklı çıkarır; V8'in önerdiği habitatları kurmaz.
2. Üç katmanı tutarlı şekilde ayır: ekonomik mekanizma → gözlemlenebilir imza →
   biçimsel candidate kuralı. S1–S4 ilk ikisini sınırlı bağlamlarda destekler;
   üçüncüyü asla benzersiz şekilde tanımlamazlar.
3. `Candidate`, denetlenebilir bir veri nesnesi olarak savunulabilir, ama
   yaşam-döngüsü etiketleri sonuçların incelenmesinden önce tanımlanmalı ve
   ileriye-dönük/zaman-noktası üretilmelidir.
4. `P(net R > 0)` ve `p_trigger` olarak tanıtılan skorlar, ayrılmış güvenilirlik
   diyagramları, uygun skorlama kuralları ve maliyet-farkında karar eğrileri
   gerektirir; ham sınıflandırıcı güveni yetersizdir (S5).
5. Kurallı execution bir araştırma-kontrol kararıdır. Bir expert'in sonucunu
   atfetmek için kullan, sonra uyarlanabilir execution'ın artımlı net fayda
   ekleyip eklemediğini ayrıca test et (S8).
6. Brief'in Faz 2 deterministik baseline'ı doğru minimumdur. Öğrenilmiş bir
   router, paylaşılan scorer, ranker ya da uyarlanabilir yöneticiyi, kendi
   ablasyonu S9-tarzı kontroller altında o baseline'ı yenene kadar ekleme.

## Bilinçli olarak açık bırakılan kaynak boşlukları

- Kalıcı discretionary-trader edge'i ve doğrulanmış bir "trader karar grameri."
  Mevcut genel karar teorisi ikisini de kurmaz.
- Perpetual-futures tasfiye alanlarını önerilen mekanlarda/ufuklarda kârlı,
  çalıştırılabilir V8-tarzı episode'lara bağlayan birincil bir ampirik çalışma.
- Tetiklenmemiş gözlemleri olan candidate episode'larının, trade-kalitesi
  modelini yalnızca-trade verisine kıyasla iyileştirdiğini kanıtlayan
  yayınlanmış bir sonuç.
- Kripto için istikrarlı, evrensel bir davranış ontolojisi kuran yayınlanmış bir
  sonuç.

Bunlar araştırma sorularıdır; üretilecek alıntılar değil. Nihai belge bunları
`OPEN_QUESTION` ya da `PROVISIONAL_DECISION` olarak etiketlemeli ve ablasyonlar
belirtmelidir.
