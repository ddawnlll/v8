# Python oracle sınırı

**Durum:** LOCKED_INVARIANT adayı (D-100).

`src/v8/` artık runtime uygulaması değildir. Otoriter istek ve doğrulama yolu
`v8-core/` içindedir. Python ağacı, yalnızca hash'i sabitlenmiş tarihsel parity
oracle'ı ve çıktıları runtime otoritesi olmayan, açıkça çağrılan legacy
araştırma tooling'inin bağımlılığı olarak korunur.

Kilit `docs/legacy/PYTHON_ORACLE_LOCK.json` içinde kayıtlıdır. `src/v8/`
değişikliği yeni registry kararı, changelog girdisi ve yeni tree hash'i
gerektirir. Sessiz değişiklik sınır ihlalidir.

İzinli Python çalıştırma alanı dardır:

- `tools/build_monograph.py` ve Markdown derleyici bağımlılıkları;
- `tools/forbidden_names.py` ve `tools/audit_python_boundary.py`;
- oracle'ı import eden, `v8-core`'a veya canlı yola girmeyen ve operatörün açıkça
  çağırdığı legacy veri/diagnostic scriptleri.

Python pytest/parity paketleri CI gate'i değildir. Oracle'ın silinmesi veya
yeniden yazılması, kalan legacy tüketicilerinin Rust/tooling karşılığı olana
dek ertelenir; aksi hâlde S0–S7 parity kaydındaki bağımsız tarihsel referans
yok edilir.
