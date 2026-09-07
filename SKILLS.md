# V8 Agent Skills

Bu dosya, bu repository üzerinde çalışan agent’ların hangi Codex skill’lerini
kullanacağını ve sınırlarını belirtir. Projeye özgü ana skill:
`$v8-research`.

## Zorunlu proje skill’i

### `$v8-research`

Her V8 kodu, veri hattı, araştırma, simülasyon, deney altyapısı veya doküman
değişikliğinde kullan. Bu skill; constitution, contract’lar, point-in-time
veri, deterministik replay, evidence label’ları, frozen-OOS kapıları ve
fail-closed davranışını korur.

Skill dosyası: `C:\Users\dresden\.codex\skills\v8-research\SKILL.md`

## Destek skill’leri

| Skill | Kullanım alanı | Ne zaman kullanma |
|---|---|---|
| `github:github` | Repo, issue ve PR bağlamı | Sadece yerel kod değişikliği varsa zorunlu değil |
| `github:gh-fix-ci` | GitHub Actions/CI hata teşhisi ve düzeltmesi | CI başarısızlığı yoksa |
| `github:gh-address-comments` | PR review yorumlarını uygulama | Açık review yorumu yoksa |
| `github:yeet` | Bilinçli commit, push ve draft PR akışı | Kullanıcı publish/PR istemediyse |
| `pdf:pdf` | `research/papers/` PDF’leri, metin çıkarımı ve görsel QA | PDF ile çalışılmıyorsa |
| `browser:control-in-app-browser` | Güncel kaynak, dokümantasyon, veri sağlayıcı ve web sayfası inceleme | Yerel kaynaklar yeterliyse |
| `visualize:visualize` | Backtest/deney tanıları, grafikler ve keşif araçları | Kısa metin yanıtı veya basit test sonucu yeterliyse |
| `documents:documents` | İstenen DOCX/Word çıktısı | Markdown/HTML proje dokümanları için |
| `spreadsheets:Spreadsheets` | Açıkça istenen XLSX/CSV/TSV analizi veya çıktısı | Canonical Parquet/JSONL hattını spreadsheet’e çevirmek gerekmiyorsa |
| `openai-docs` | OpenAI API/ürün entegrasyonu | V8’te OpenAI entegrasyonu yoksa |

İnternet araştırması için ayrıca plugin kurulması gerekmez; web erişimi mevcut
olduğunda agent kaynakları doğrudan doğrulayabilir.

## Kullanım sırası

1. `$v8-research` ile repository kurallarını ve ilgili contract’ı oku.
2. Göreve göre yalnızca gerekli destek skill’ini seç.
3. Kod değişikliğinde pytest ve ilgili determinism/PIT/fail-closed testlerini
   çalıştır.
4. Doküman değişikliğinde monograph’ları yeniden üret ve byte-identity kontrolü
   yap.
5. Sonuçta kullanılan skill’leri, testleri ve açık gate/pin’leri raporla.

## Mutlak sınırlar

- `router`, learned/shared scorer, ranker, learned/RL execution ve online
  learning ekleme.
- Frozen holdout’u açma veya `v8_slice_001` deneyini izinsiz çalıştırma.
- `site/*` dosyalarını elle düzenleme.
- Testleri zayıflatma, silme veya skip etme.
- `src/v8/` karar yoluna wall clock veya gereksiz ağır bağımlılık ekleme.
- Authority receipt olmadan ekonomik/verimlilik/profitability iddiası yazma.
