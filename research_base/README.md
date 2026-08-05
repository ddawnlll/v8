# V8 Progressive Evidence Research System

`v8research`, kitap ve makale metinlerini yedi bağımsız keşif kanalıyla tarayan,
okumaları receipt olarak kaydeden ve yalnızca doğrulanmış iddiaları immutable
finding olarak dışarı veren offline araştırma derleyicisidir.

## Çalıştırma

```bash
uv sync --extra store --extra dev
uv run v8research --workspace ./workspace ingest ./book.txt
uv run v8research --workspace ./workspace discover SRC-...
uv run v8research --workspace ./workspace reread SRC-...
uv run v8research --workspace ./workspace verify SRC-...
uv run v8research --workspace ./workspace report
uv run v8research --workspace ./workspace materialize
uv run v8research --workspace ./workspace status
```

Varsayılan `EchoClient` deterministiktir ve frontier model çağırmaz. Gerçek
model adaptörü yalnızca açıkça `llm` extra'sı ve bir model istemcisi
register edildiğinde kullanılmalıdır.

## Veri akışı

1. `ingest`: metni parse eder, yapısal node'ları ve navigation receipt'lerini
   append-only JSONL'e yazar.
2. `discover`: A–G kanallarını çalıştırır; mark'ları union eder, reread task'larını
   ve audit örneklerini kaydeder.
3. `verify`: claim çıkarır, exact evidence span'ine hizalar ve bağımsız verifier
   ile doğrular. Evidence yoksa finding üretilmez.
4. `materialize`: JSONL otoritesinden Parquet/DuckDB görünümlerini yeniden kurar.
5. `status`: unresolved critical task veya kaynak/bütçe eksikliği varsa run'ı
   `COMPLETE` ilan etmez.

JSONL kayıtları crash sonrası replay edilebilir otoritedir; Parquet ve DuckDB
yalnızca yeniden üretilebilir analitik görünümlerdir.

Gerçek sağlayıcı açıkça seçilmelidir; varsayılan akış offline `EchoClient`'tır:

```bash
uv run v8research --live --small-model claude-sonnet-4-20250514 \
  --strong-model claude-opus-4-20250514 \
  --workspace ./workspace reread SRC-...
```

`--live` API maliyeti doğurur. Sağlayıcı kimlik doğrulaması veya bağlantısı
başarısızsa run tamamlanmış sayılmamalıdır.

## Test

```bash
uv run pytest -q
uv run --with ruff ruff check src tests --select F401,F841
```
