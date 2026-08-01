# V8 Okuma Listesi — araştırma amacına göre sıralı

Bu, geçici brief'i yanlışlanabilir bir monografiye dönüştürmek için kompakt bir
çalışma bibliyografyasıdır. Tasarım sentezinden önce birincil öğeleri oku; son
iki öğe uygulama rehberidir ve ekonomik kanıt olarak kullanılmamalıdır.

## 1. Piyasa mekanizmaları ve durum değişkenleri

1. **Brandt, M. & Kavajecz, K. (2003), "Price Discovery in the U.S. Treasury Market: The Impact of Orderflow and Liquidity on the Yield Curve."** [NBER working paper PDF](https://www.nber.org/system/files/working_papers/w9529/w9529.pdf)  
   İlgi: bilgi/emir akışı, likidite ve fiyat keşfi arasındaki ayrım için çapa. `flow` ve `liquidity`nin ne anlama geldiğini tanımlarken ve yalnızca-gösterge açıklamalarını reddederken kullan.

2. **Vayanos, D. & Wang, J. (2012), "Market Liquidity — Theory and Empirical Evidence."** [MIT-hosted working paper PDF](https://web.mit.edu/wangj/www/pap/VayanosWang12Empirical.pdf)  
   İlgi: likidite arzı, talebi ve fiyat etkilerinin teorisi/ampirikleri. Maliyet, kapasite, dealer/envanter ve durum-değişkeni gerekçesi için kullan.

3. **Andersen, T., Bollerslev, T., Christoffersen, P. & Diebold, F. (2005), "Volatility Forecasting."** [NBER WP 11188 PDF](https://www.nber.org/system/files/working_papers/w11188/w11188.pdf)  
   İlgi: kalıcı koşullu volatilite ve aktiviteyi destekler. Belirli bir eşik taksonomisi değil, volatilite bağlamını motive etmek için kullan.

4. **Khandani, A. & Lo, A. (2008), "What Happened to the Quants in August 2007?"** [MIT PDF](https://web.mit.edu/Alo/www/Papers/august07b_2.pdf)  
   İlgi: zorunlu kaldıraç-sökümü ve geçici dislokasyonla tutarlı kanıt. "Dislocation" için bir uyarı-mekanizma kaynağı olarak kullan; bir tasfiye dedektörünün kârlı olacağının kanıtı olarak değil.

5. **Auer, R., Tercero-Lucas, D. & Tolle, M. (2025 revision), "Crypto carry."** [BIS working paper page](https://www.bis.org/publ/work1087.htm)  
   İlgi: spot/türev basisi ve kurumsal kısıtlar üzerine yerli kripto kanıtı. Fonlama/basis alanlarını değerlendirirken kullan; alıntı yaparken güncel sürümü/tarihi doğrula.

6. **Moskowitz, T., Ooi, Y. & Pedersen, L. (2012), "Time Series Momentum."** [DOI record](https://doi.org/10.1016/j.jfineco.2011.11.003)  
   İlgi: devam etkilerini test etmek için geniş ampirik motivasyon. Kapsam çeşitlendirilmiş future'lardır; V8 onu kendi OOS kanıtı olmadan belirli bir kripto zaman dilimine genişletmemelidir.

## 2. Candidate kalitesi, çekimserlik ve olasılık iddiaları

7. **Geifman, Y. & El-Yaniv, R. (2017), "Selective Classification for Deep Neural Networks."** [arXiv record](https://arxiv.org/abs/1705.08500)  
   İlgi: tahminleri kabul/reddetme ve kapsam–risk ödünleşimini değerlendirme için biçimsel dil. Dikkatli çevir: V8, tahmin riskinin yanı sıra ekonomik faydayı da ölçmelidir.

8. **scikit-learn, "Probability calibration."** [maintained documentation](https://scikit-learn.org/stable/modules/calibration.html)  
   İlgi: kalibre edilmiş olasılıklar, güvenilirlik eğrileri ve çapraz-doğrulanmış kalibrasyon için pratik gereksinimler. `p_trigger` ya da `P(net R > 0)` gibi iddialar için kullan.

9. **López de Prado, M. (2018), *Advances in Financial Machine Learning*.** [SSRN record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3104847)  
   İlgi: ikincil bir kalite modelinin arkasındaki meta-labelleme örüntüsünün kaynağı. Test edilecek önerilen bir yöntem olarak ele al; meta-labellemenin alpha yarattığının kanıtı olarak değil.

## 3. Execution, doğrulama ve aşırı-uyum karşıtı kontroller

10. **Almgren, R. & Chriss, N. (2000), "Optimal Execution of Portfolio Transactions."** [paper PDF](https://quantitativebrokers.com/s/Optimal-Execution-of-Portfolio-Transaction-_-AlmgrenChriss-1999.pdf)  
    İlgi: biçimsel beklenen-maliyet/risk ödünleşimi. Execution maliyetlerini modellemeyi ve alpha deneyleri sırasında bir execution politikasını açık/sürümlü tutmayı haklı çıkarmak için kullan.

11. **U.S. Securities and Exchange Commission, "Disclosure of Order Execution Information" (proposal).** [SEC PDF](https://www.sec.gov/files/rules/proposed/2022/34-96493.pdf)  
    İlgi: execution-kalitesi ölçümünün neden önemsiz olmadığına dair birincil düzenleyici tartışma. Hisse-senedi piyasası kapsamı; yalnızca ölçüm ilkesi olarak kullan, kripto-piyasası kanıtı olarak değil.

12. **Novy-Marx, R. (2015), "Backtesting Strategies Based on Multiple Signals."** [NBER page](https://www.nber.org/papers/w21329)  
    İlgi: birleştirilmiş/imzalanmış/ayarlanmış sinyallerin çarpıcı ama sahte in-sample sonuçlar üretebileceğine dair doğrudan uyarı. Parametre varyantlarını ayrı expert'ler olarak adlandırmadan önce gerekli okuma.

13. **Bailey, D. et al. (2015), "The Probability of Backtest Overfitting."** [SSRN record](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)  
    İlgi: seçim-kaynaklı aşırı-uyumu değerlendirmek için finans-özgü çerçeve. Walk-forward ve kilitli bir nihai holdout ile eşleştir; PBO bir teşhistir, garanti değildir.

14. **Simonian, J. (2024), *Investment Model Validation*.** [CFA Institute PDF](https://rpc.cfainstitute.org/sites/default/files/-/media/documents/article/rf-brief/investment-model-validation.pdf)  
    İlgi: uygulama-odaklı doğrulama yönetişimi, veri soyağacı, stres ve dağıtım kaygıları. İkincil/uygulayıcı kaynak—piyasa mekanizmalarının kanıtı olarak kullanma.

## 4. Biliş: yalnızca terminoloji, kârlılık kanıtı değil

15. **Kochenderfer, M. (2015), *Decision Making Under Uncertainty: Theory and Application*.** [Stanford-hosted PDF](https://web.stanford.edu/group/sisl/public/dmu.pdf)  
    İlgi: durum, belirsizlik, aksiyon ve sonuç için biçimsel sözcük dağarcığı. Bir "trader karar grameri"ni sınırlandırmaya yardımcı olabilir, ama discretionary trader anlatılarını ya da V8 davranış ailelerini doğrulamaz.

## Sonraki araştırma fazı için okuma sırası

Ekonomik-mekanizma ontolojisini yazmak için 1–5'i oku; scorer'ın etiketlerini ve metriklerini belirlemeden önce 7–9'u; simülasyon ve terfi kapılarını kesinleştirmeden önce 10–14'ü; 15'i yalnızca insan iş akışını denetlenebilir nesnelere çevirirken oku. Önerilen her expert, bölüm 1'den bir mekanizma kaynağı alıntılamalı, sonra alıntıyı kanıt olarak miras almak yerine kendi biçimselleştirmesini ve OOS deneyini taşımalıdır.
