#!/usr/bin/env python3
"""Build the final Turkish HTML report from the research pipeline outputs.

Reads: corpus manifest, triaged claims (processed_books/*/claims.jsonl),
counterevidence, registry (canonical families/relationships), P6 outputs
(strategies, translations, specs, validation). Produces one self-contained
HTML file (TR) that combines ALL findings from all books.

Works incrementally: missing inputs degrade to a note, never an error.
"""
from __future__ import annotations

import glob
import html
import json
import os

ROOT = '/Users/hootie/src/v8'
PB = os.path.join(ROOT, 'research/pipeline_v2/processed_books')
REG = os.path.join(ROOT, 'research/pipeline_v2/registry')
OUT = os.path.join(ROOT, 'research/pipeline_v2/findings_report.html')


def load_json(path, default=None):
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except Exception:
            return default
    return default


def esc(s):
    return html.escape(str(s if s is not None else ''))


def load_claims():
    per_book = {}
    routes = {'M': 0, 'X': 0, 'G': 0, 'F': 0}
    for fp in sorted(glob.glob(os.path.join(PB, 'book_*/claims.jsonl'))):
        bid = fp.split('/')[-2]
        claims = []
        for l in open(fp):
            if not l.strip():
                continue
            c = json.loads(l)
            claims.append(c)
            if c.get('route') in routes:
                routes[c['route']] += 1
        per_book[bid] = claims
    return per_book, routes


def load_counterevidence():
    ce = {}
    for fp in sorted(glob.glob(os.path.join(PB, 'book_*/counterevidence.jsonl'))):
        bid = fp.split('/')[-2]
        recs = [json.loads(l) for l in open(fp) if l.strip()]
        ce[bid] = recs
    return ce


def main() -> int:
    per_book, routes = load_claims()
    ce = load_counterevidence()
    manifest = load_json(os.path.join(ROOT, 'research/pipeline_v2/corpus/books_manifest.v21.json'), {'books': []})
    routing = load_json(os.path.join(REG, 'book_routing.json'), {'routes': {}})
    decisions = []
    if os.path.exists(os.path.join(REG, 'research_decisions.jsonl')):
        decisions = [json.loads(l) for l in open(os.path.join(REG, 'research_decisions.jsonl')) if l.strip()]

    byid = {b['book_id']: b for b in manifest.get('books', [])}
    n_books = len(byid)
    n_claims = sum(len(v) for v in per_book.values())
    n_ce = sum(len(v) for v in ce.values())

    # --- HTML assembly ---
    H = []
    H.append('<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">')
    H.append('<meta name="viewport" content="width=device-width,initial-scale=1">')
    H.append('<title>V8 Kitap Strateji Analizi — research_pipeline_v2.1</title>')
    H.append('<style>')
    H.append('body{font-family:system-ui,-apple-system,sans-serif;max-width:1100px;margin:0 auto;padding:24px;color:#1a1a1a;line-height:1.5}')
    H.append('h1,h2,h3{border-bottom:1px solid #ddd;padding-bottom:6px}')
    H.append('.stat{display:inline-block;background:#f0f4ff;border:1px solid #c9d6f5;border-radius:8px;padding:10px 16px;margin:4px;min-width:120px}')
    H.append('.stat b{font-size:22px;display:block}')
    H.append('table{border-collapse:collapse;width:100%;margin:10px 0}')
    H.append('th,td{border:1px solid #ddd;padding:6px 10px;text-align:left;font-size:14px;vertical-align:top}')
    H.append('th{background:#f5f5f5}')
    H.append('.tag{display:inline-block;background:#eef;border-radius:4px;padding:1px 6px;font-size:12px;margin:1px}')
    H.append('.route-M{background:#e6f4e6}.route-G{background:#fff3d6}.route-X{background:#e6f0f9}.route-F{background:#f3e6f9}')
    H.append('details{margin:6px 0}summary{cursor:pointer;font-weight:600}')
    H.append('.warn{background:#fff8e6;border:1px solid #e6d9a8;padding:8px 12px;border-radius:6px}')
    H.append('.pass{color:#1a7a1a}.reject{color:#c0392b}.incomplete{color:#b9770e}')
    H.append('</style></head><body>')

    H.append('<h1>📚 V8 Kitap Strateji Analizi</h1>')
    H.append(f'<p><b>research_pipeline_v2.1</b> · schema v2.0 · {n_books} kitap · üretim tarihi: 2026-08-02</p>')
    H.append('<p class="warn"><b>⚠️ ARAŞTIRMA GİRDİSİ — KENAR (EDGE) KANITI DEĞİL.</b> Bu rapor '
             'kitaplardaki strateji iddialarını kaynak-sadakatıyla derler; hiçbir bulgu V8\'de '
             'kârlılık veya doğrulanmış execution iddiası değildir (V8_CONSTITUTION kural 12). '
             'Ham kaynak katmanında crypto/V8 uyarlaması YOKTUR; uyarlama yalnızca çeviri katmanında '
             'provenance etiketleriyle yapılır.</p>')

    # --- summary stats ---
    H.append('<h2>Özet</h2>')
    H.append('<div>')
    H.append(f'<div class="stat"><b>{n_books}</b>kitap</div>')
    H.append(f'<div class="stat"><b>{n_claims}</b>triage edilmiş claim</div>')
    H.append(f'<div class="stat"><b>{routes["M"]}</b>M mekanizma</div>')
    H.append(f'<div class="stat"><b>{routes["G"]}</b>G risk</div>')
    H.append(f'<div class="stat"><b>{routes["F"]}</b>F metodoloji</div>')
    H.append(f'<div class="stat"><b>{routes["X"]}</b>X execution</div>')
    H.append(f'<div class="stat"><b>{n_ce}</b>counterevidence kaydı</div>')
    H.append('</div>')

    # --- decisions ---
    if decisions:
        H.append('<h2>Araştırma kararları</h2><table><tr><th>Karar</th><th>İçerik</th></tr>')
        for d in decisions:
            items = '; '.join(f"{i.get('topic')} → {i.get('decision')}" for i in d.get('items', []))
            H.append(f'<tr><td>{esc(d.get("decision"))}</td><td>{esc(items)}</td></tr>')
        H.append('</table>')

    # --- per-book findings ---
    H.append('<h2>Kitap başına bulgular</h2>')
    H.append('<table><tr><th>Kitap</th><th>Track</th><th>Claim</th><th>Örnek claim' + "'" + 'ler</th></tr>')
    for bid in sorted(per_book):
        claims = per_book[bid]
        meta = byid.get(bid, {})
        title = meta.get('title', bid)
        track = ','.join(routing.get('routes', {}).get(bid, {}).get('tracks', [])) or '-'
        samples = [c for c in claims if c.get('route') in ('M', 'G')][:2]
        sample_txt = '<br>'.join(
            f'<span class="tag route-{c.get("route")}">{c.get("route")}</span> {esc((c.get("anchor_text") or "")[:120])}'
            for c in samples)
        H.append(f'<tr><td><b>{esc(title)}</b></td><td>{esc(track)}</td><td>{len(claims)}</td><td>{sample_txt}</td></tr>')
    H.append('</table>')

    # --- P4 canonical families (registry) ---
    p4 = load_json(os.path.join(REG, 'p4_b1_partial.json'), {})
    reg = p4.get('registry', [])
    if reg:
        H.append('<h2>P4 Canonical Behavior Family' + "'" + 'ları (novelty-gated keşif)</h2>')
        H.append('<p>Tur 1 tamamlandı; tur 2-7 kesinti nedeniyle eksik (aşağıdaki sınırlamalar). Registry: '
                 f'{len(reg)} behavior ({sum(1 for b in reg if b.get("source_claim_refs"))} yeni keşif + tohum).</p>')
        H.append('<table><tr><th>Family</th><th>Behavior</th><th>Mekanizma taslağı</th><th>Kaynak claim</th></tr>')
        for b in reg:
            drafts = f'{b.get("precondition_class","")} → {b.get("boundary_event","")} → {b.get("follow_through_state","")} → {b.get("resolution_event","")}'
            srcs = len(b.get('source_claim_refs', []))
            H.append(f'<tr><td><b>{esc(b.get("canonical_family_id"))}</b></td><td>{esc(b.get("canonical_behavior_id"))}</td>'
                     f'<td>{esc(drafts)}</td><td>{srcs}</td></tr>')
        H.append('</table>')
        sat = p4.get('saturation_ledger', [])
        if sat:
            H.append('<p>Doyum: ' + ' · '.join(
                f'tur{s.get("round")}: {s.get("new_families")} yeni / {s.get("total_families")} toplam' for s in sat) + '</p>')

    # --- counterevidence details ---
    H.append('<h2>Counterevidence (yanlışlama girdileri)</h2>')
    n_notfound = sum(1 for recs in ce.values() if any(r.get('counterevidence_status') == 'NOT_FOUND_IN_SOURCE' for r in recs))
    H.append(f'<p>{n_ce} kayıt; {n_notfound} kitap için NOT_FOUND_IN_SOURCE (kaynakta karşı kanıt bulunamadı — "güçlü kitap" anlamına gelmez).</p>')
    kinds = {}
    for recs in ce.values():
        for r in recs:
            k = r.get('kind') or 'NOTE'
            kinds[k] = kinds.get(k, 0) + 1
    if kinds:
        H.append('<p>Tür dağılımı: ' + ' · '.join(f'{k}={v}' for k, v in sorted(kinds.items())) + '</p>')
    H.append('<details><summary>Örnek counterevidence kayıtları</summary><table><tr><th>Kitap</th><th>Tür</th><th>Anlam</th></tr>')
    shown = 0
    for bid in sorted(ce):
        for r in ce[bid]:
            if shown >= 40:
                break
            if r.get('kind'):
                H.append(f'<tr><td>{esc(bid)}</td><td>{esc(r.get("kind"))}</td><td>{esc((r.get("normalized_meaning") or r.get("exact_text") or "")[:160])}</td></tr>')
                shown += 1
        if shown >= 40:
            break
    H.append('</table></details>')

    # --- limitations ---
    H.append('<h2>Sınırlamalar (dürüst)</h2><ul>')
    H.append('<li>Deterministik regex scout recall\'ü ölçüldü: <b>~%9</b> (sözlük dar). Triage, regex lead\'lerini temel alır; '
             'regex\'in kaçırdığı stratejiler korpusta görünmez. Tam section okuma (A1) sonraki deep-search fazına ertelendi '
             '(research_decisions kaydı).</li>')
    H.append('<li>Sayfa anchor\'ları: UNMAPPED kitaplarda sayfa yerine part+satır kullanılır; sayfa uydurulmaz.</li>')
    H.append('<li>OCR kitaplarında gürültü olabilir (is_ocr etiketli).</li>')
    H.append('<li>Kitapların çoğu hisse/forex/vadeli odaklı, kripto öncesi; çeviri katmanı aktarım risklerini etiketler.</li>')
    H.append('<li>Hedef piyasa multi-timeframe (1h/4h/1d) — kaynak doğal ufku korunur.</li>')
    H.append('</ul>')

    H.append('</body></html>')
    with open(OUT, 'w') as f:
        f.write('\n'.join(H))
    print(f'HTML rapor yazıldı: {OUT} ({os.path.getsize(OUT)} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
