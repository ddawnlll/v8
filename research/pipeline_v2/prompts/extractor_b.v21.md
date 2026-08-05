# ## V.7 — `extractor_b` (P4.b, T4 — BAĞIMSIZ)

> research_pipeline_v2.1 worker prompt. Extract from the devir belgesi (AGENT_HANDOFF_PROMPT.md Bölüm V). No-leak, provenance and quota rules apply verbatim. Edit only with a research_pipeline_v2.2 version bump.
```
You are given a passage from a trading book. Reconstruct the procedure it
describes as a decision procedure that a careful clerk could follow with no
trading knowledge, using only what the passage states.

Work through it in this order:
1. What must already be true before this procedure applies?
2. What observable event puts it into play?
3. What observable event makes it act?
4. Which direction does it act in, and relative to what?
5. What observable event tells the clerk the procedure has failed?
6. Where does the passage go silent? List every point at which the clerk
   would have to ask a question the passage does not answer.

Then emit the same JSON structure as specified below.

[AYNI OUTPUT ŞEMASI — V.6'daki blok birebir tekrarlanır]

FORBIDDEN
[AYNI YASAK LİSTESİ — V.6'daki blok birebir tekrarlanır]

Step 6 is the most important step. A clerk who cannot proceed is telling you
the source is silent, and silence must be recorded as NOT_SPECIFIED, never
filled in.
```

### Tasarım kararı: A ve B neden farklı çerçevelenir

**Karar:** A ve B **aynı çıktı şemasını** ama **farklı elicitation
çerçevesini** kullanır. A "yazar ne dedi" diye sorar; B "bilgisiz bir kâtip
bunu nasıl uygular" diye sorar.

**Gerekçe:** Aynı model + aynı prompt = **korelasyonlu hata**. İkisi de aynı
körlüğe sahip olur, aynı yeri aynı şekilde yanlış okur, ve yüksek uyum oranı
doğruluk değil sadece tekrarlanabilirlik ölçer. Farklı çerçeveleme hataları
dekorelе eder; anlaşmazlık **bilgilendirici** hale gelir.

**Bedeli:** Uyum oranı artık "iki bağımsız okuyucu aynı şeyi gördü" değil,
"çıkarım çerçevelemeye dayanıklı" ölçer. Bu farklı bir şeydir.

**Durum:** `PROVISIONAL_DECISION`. HITL-1'de kalibrasyon uyum oranlarına
bakılıp bu çerçeve farkının uyumu anlamsız derecede düşürüp düşürmediği
değerlendirilecek. Düşürüyorsa B, A ile aynı çerçeveye çevrilir ve karar
`research_decisions.jsonl`'e yazılır.

---
