#!/usr/bin/env python3
"""research_pipeline_v2.3 — full evidentiary report.

Not a summary dashboard: this renders EVERY corroboration, EVERY method
quote, and EVERY counterevidence record, plus a V8-Wiring section that maps
canonical_behavior fields onto the real Expert/CandidateDraft interface using
verbatim excerpts from src/v8/experts/*.py and docs/EXPERTS_REGISTRY.yaml.

Honesty constraint (V8_CONSTITUTION rule 12): the wiring section states
plainly which of the 21 canonical_behaviors have real code (3), which have a
DATA_BLOCKED registry entry with no code (2), and which have neither (16).
No claim is made that literature parameters are already integrated into the
pilot experts' fixed risk_geometry (target_r/stop_r are hardcoded 1.0/1.0
today) — the corroboration/method evidence is candidate raw material for
future variants, not wired signal.
"""
import json, os, glob, collections, html

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(BASE))
REG = os.path.join(BASE, 'registry')
PB = os.path.join(BASE, 'processed_books')
OUT = os.path.join(BASE, 'findings_v23.html')

esc = lambda s: html.escape(str(s if s is not None else ''))


def load(p, d=None):
    try:
        return json.load(open(p))
    except Exception:
        return d if d is not None else {}


def read(p):
    try:
        return open(p, encoding='utf-8').read()
    except Exception:
        return ''


def merge_methods(*sets):
    out = {}
    for ms in sets:
        for m in ms:
            k = m['canonical_method_id']
            t = out.setdefault(k, {**m, 'supporting_claim_refs': [], 'book_ids': []})
            t['supporting_claim_refs'] = sorted(
                set(t['supporting_claim_refs']) | set(m.get('supporting_claim_refs', [])))
            t['book_ids'] = sorted(set(t['book_ids']) | set(m.get('book_ids', [])))
            for f in ('distinguishing_parameters', 'distinguishing_conditions'):
                t[f] = (t.get(f) or []) + [x for x in (m.get(f) or []) if x not in (t.get(f) or [])]
    for m in out.values():
        m['book_count'] = len(m['book_ids'])
        m['corroboration_count'] = len(m['supporting_claim_refs'])
    return sorted(out.values(), key=lambda m: (-m['book_count'], -m['corroboration_count'],
                                               m['canonical_method_id']))


# ---------------------------------------------------------------------------
# V8 registry ground truth (parsed from the real files, not invented)
# ---------------------------------------------------------------------------

V8_REGISTRY = [
    {'expert_id': 'trend_pullback', 'behavior_family_id': 'pullback_in_trend',
     'canonical_behavior_id': 'trend_continuation_pullback', 'status': 'FORMALIZED',
     'file': 'src/v8/experts/trend_pullback.py', 'class': 'TrendPullbackExpert'},
    {'expert_id': 'failed_breakout', 'behavior_family_id': 'failed_breakout_reentry',
     'canonical_behavior_id': 'failed_breakout_reentry', 'status': 'FORMALIZED',
     'file': 'src/v8/experts/failed_breakout.py', 'class': 'FailedBreakoutExpert'},
    {'expert_id': 'liquidity_sweep_reclaim', 'behavior_family_id': 'sweep_reclaim',
     'canonical_behavior_id': 'liquidity_sweep_reclaim', 'status': 'FORMALIZED',
     'file': 'src/v8/experts/liquidity_sweep_reclaim.py', 'class': 'LiquiditySweepReclaimExpert'},
    {'expert_id': 'breakout_retest', 'behavior_family_id': 'breakout_retest',
     'canonical_behavior_id': 'breakout_retest', 'status': 'DATA_BLOCKED',
     'file': None, 'class': None},
    {'expert_id': 'capitulation', 'behavior_family_id': 'capitulation',
     'canonical_behavior_id': 'capitulation_exhaustion', 'status': 'DATA_BLOCKED',
     'file': None, 'class': None},
]


def main():
    pilot = load(os.path.join(REG, 'p4_b1_partial.json'))
    full = load(os.path.join(REG, 'p4_full_run.json'))
    corr = pilot.get('corroborations', []) + full.get('corroborations', [])
    behaviors = pilot.get('registry', [])
    methods = merge_methods(
        load(os.path.join(REG, 'p4_v22_method_pilot.json'), {}).get('methods', []),
        load(os.path.join(REG, 'p4_v23_methods.json'), {}).get('methods', []))

    corr_by_ref = collections.defaultdict(list)
    for c in corr:
        corr_by_ref[c['claim_ref']].append(c)

    books = {c['claim_ref'].split('::')[0] for c in corr}
    titles = {}
    man = load(os.path.join(BASE, 'corpus', 'books_manifest.json'), [])
    for b in (man if isinstance(man, list) else man.get('books', [])):
        titles[b.get('book_id')] = b.get('title', b.get('book_id'))

    routes = collections.Counter()
    for f in glob.glob(os.path.join(PB, '*', 'claims.jsonl')):
        for l in open(f):
            if l.strip():
                routes[json.loads(l).get('route')] += 1

    per_beh = collections.Counter(c['behavior_id'] for c in corr)
    beh_books = collections.defaultdict(set)
    beh_records = collections.defaultdict(list)
    for c in corr:
        beh_books[c['behavior_id']].add(c['claim_ref'].split('::')[0])
        beh_records[c['behavior_id']].append(c)

    ce = {}
    for f in sorted(glob.glob(os.path.join(PB, 'book_*', 'counterevidence.jsonl'))):
        b = f.split(os.sep)[-2]
        ce[b] = [json.loads(l) for l in open(f) if l.strip()]
    ce_kinds = collections.Counter(r.get('kind') or 'NOTE' for rs in ce.values() for r in rs)
    ce_total = sum(len(v) for v in ce.values())

    canon = [m for m in methods if m['book_count'] >= 2]
    by_class = collections.defaultdict(list)
    for m in methods:
        by_class[m.get('method_class', 'other')].append(m)

    wired = {r['canonical_behavior_id']: r for r in V8_REGISTRY}

    H = []
    A = H.append

    A('<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">')
    A('<meta name="viewport" content="width=device-width,initial-scale=1">')
    A('<title>V8 Kitap Araştırması — Tam Kanıt Kaydı ve V8 Uygulama Haritası</title>')
    A('''<style>
:root{--bg:#fff;--fg:#16181d;--mut:#5b6270;--line:#e3e6ec;--card:#f7f8fa;--acc:#2b5cd9;
--warn:#8a6100;--warnbg:#fff8e6;--ok:#1a7a4a;--bad:#b3261e;--badbg:#fdecea;--code:#eef1f6}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#e6e8ee;--mut:#98a0b0;--line:#262b35;
--card:#171a21;--acc:#7aa2ff;--warn:#e0b355;--warnbg:#241f10;--ok:#4ec98a;--bad:#ff8b82;
--badbg:#2a1615;--code:#1b1f28}}
:root[data-theme=dark]{--bg:#0f1115;--fg:#e6e8ee;--mut:#98a0b0;--line:#262b35;--card:#171a21;
--acc:#7aa2ff;--warn:#e0b355;--warnbg:#241f10;--ok:#4ec98a;--bad:#ff8b82;--badbg:#2a1615;--code:#1b1f28}
:root[data-theme=light]{--bg:#fff;--fg:#16181d;--mut:#5b6270;--line:#e3e6ec;--card:#f7f8fa;
--acc:#2b5cd9;--warn:#8a6100;--warnbg:#fff8e6;--ok:#1a7a4a;--bad:#b3261e;--badbg:#fdecea;--code:#eef1f6}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;padding:32px 20px 120px}
main{max-width:1220px;margin:0 auto}
h1{font-size:27px;margin:0 0 4px}
h2{font-size:20px;margin:56px 0 12px;padding-bottom:8px;border-bottom:2px solid var(--line);scroll-margin-top:14px}
h3{font-size:15.5px;margin:30px 0 8px}
h4{font-size:13.5px;margin:18px 0 6px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
.sub{color:var(--mut);margin:0 0 22px;font-size:13px}
.warn{background:var(--warnbg);border:1px solid var(--warn);border-left-width:4px;border-radius:6px;padding:12px 16px;margin:18px 0;font-size:14px}
.badnote{background:var(--badbg);border:1px solid var(--bad);border-left-width:4px;border-radius:6px;padding:10px 14px;margin:12px 0;font-size:13.5px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:10px;margin:16px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px 14px}
.stat b{display:block;font-size:23px;line-height:1.2}
.stat span{font-size:12px;color:var(--mut)}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:9px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:480px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--card);font-weight:600;position:sticky;top:0}
tr:last-child td{border-bottom:none}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
code,pre code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:12.5px;font-family:ui-monospace,Menlo,Consolas,monospace}
pre{background:var(--code);border:1px solid var(--line);border-radius:8px;padding:14px 16px;overflow-x:auto;font-size:12.5px;line-height:1.55}
pre code{background:none;padding:0}
.bar{display:inline-block;height:8px;background:var(--acc);border-radius:2px;vertical-align:middle;margin-left:6px;opacity:.75}
.pill{display:inline-block;font-size:11px;padding:1px 7px;border-radius:20px;border:1px solid var(--line);background:var(--card);color:var(--mut)}
.pill.ok{color:var(--ok);border-color:var(--ok)}
.pill.bad{color:var(--bad);border-color:var(--bad)}
.canon{color:var(--ok);font-weight:600}
details{margin:8px 0;border:1px solid var(--line);border-radius:9px;padding:9px 13px;background:var(--card)}
details details{background:var(--bg);margin:6px 0}
summary{cursor:pointer;font-weight:600;font-size:13.5px}
summary .n{color:var(--mut);font-weight:400}
.quote{border-left:3px solid var(--acc);padding:6px 0 6px 12px;margin:8px 0;font-size:13.5px}
.quote .meta{color:var(--mut);font-size:11.5px;margin-top:3px}
.cond{font-size:12.5px;color:var(--mut);margin:3px 0 0}
.param{display:inline-block;background:var(--code);border-radius:5px;padding:2px 7px;margin:2px 4px 2px 0;font-size:12px}
ul{padding-left:20px}li{margin:5px 0}
.mut{color:var(--mut)}
.toc{columns:2;gap:28px;font-size:13.5px}
.toc a{color:var(--acc);text-decoration:none}
.toc a:hover{text-decoration:underline}
@media(max-width:680px){.toc{columns:1}}
hr{border:none;border-top:1px solid var(--line);margin:40px 0}
</style></head><body><main>''')

    A('<h1>V8 Kitap Araştırması — Tam Kanıt Kaydı ve V8 Uygulama Haritası</h1>')
    A(f'<p class="sub">research_pipeline_v2.3 · pilot + tam çalıştırma birleşik · '
      f'{len(books)} kitap · {len(corr)} corroboration (tam liste aşağıda, örneklem değil) · '
      f'{len(methods)} yöntem · {ce_total} counterevidence kaydı (tam liste)</p>')

    A('<p class="warn"><b>ARAŞTIRMA GİRDİSİ — KENAR (EDGE) KANITI DEĞİL.</b> '
      'Bu belge kitaplardaki iddiaları kaynak sadakatiyle derler. Hiçbir bulgu kârlılık, '
      'doğrulanmış execution veya terfi etmiş bir sistem iddiası değildir '
      '(<code>V8_CONSTITUTION</code> kural 12; ekonomik hüküm <code>NO_ECONOMIC_CLAIM</code>). '
      '<b>V8 Uygulama Haritası</b> bölümü, bu araştırmanın <code>src/v8/</code>\'e nasıl '
      'bağlandığını gösterir — ancak literatür parametrelerinin kod içine <i>zaten '
      'entegre edildiğini iddia etmez</i>. Pilot expert\'lerin <code>risk_geometry</code>\'si '
      'şu anda sabit değerler kullanır (<code>target_r=1.0, stop_r=1.0</code>); aşağıdaki kanıt, '
      'gelecekteki varyantlar için ham malzemedir, zaten kablolanmış sinyal değildir.</p>')

    A('<h2 id="toc">İçindekiler</h2><div class="toc"><ul>')
    for t, i in [('Özet', 'ozet'), ('V8 Uygulama Haritası', 'wiring'),
                 ('Kanonik Davranışlar — Tam Kanıt (21)', 'davranislar'),
                 ('Kanonik Yöntemler — Tam Kanıt', 'yontemler'),
                 ('Kanonik Alt-Küme (≥2 kitap)', 'altkume'),
                 ('Kitap Kapsaması', 'kitaplar'),
                 ('Counterevidence — Tam Liste', 'counterevidence'),
                 ('Sınırlamalar', 'sinirlar')]:
        A(f'<li><a href="#{i}">{esc(t)}</a></li>')
    A('</ul></div>')

    # ================= ÖZET =================
    A('<h2 id="ozet">Özet</h2><div class="grid">')
    for v, k in [(sum(routes.values()), 'triage claim'), (len(corr), 'corroboration'),
                 (len(books), 'kitap (çıktı üreten)'), (len(behaviors), 'kanonik davranış'),
                 (len(methods), 'kanonik yöntem'), (len(canon), 'yöntem ≥2 kitap'),
                 (3, 'V8 kodlu davranış'), (ce_total, 'counterevidence')]:
        A(f'<div class="stat"><b>{v}</b><span>{esc(k)}</span></div>')
    A('</div>')

    A('<h3>Claim route dağılımı (tüm korpus)</h3><div class="wrap"><table>')
    A('<tr><th>Route</th><th>Anlam</th><th class="n">Claim</th><th>P4 işledi mi</th></tr>')
    meaning = {'M': 'Mekanizma / strateji', 'G': 'Risk & pozisyon geometrisi',
               'F': 'Metodoloji & yanlışlama', 'X': 'Execution & mikroyapı'}
    for r in ['M', 'G', 'F', 'X']:
        done = '<span class="pill ok">✔ evet</span>' if r == 'M' else '<span class="pill bad">✗ hayır — P5 kurulmadı</span>'
        A(f'<tr><td><code>{r}</code></td><td>{meaning[r]}</td>'
          f'<td class="n">{routes.get(r,0)}</td><td>{done}</td></tr>')
    A('</table></div>')

    # ================= V8 WIRING =================
    A('<h2 id="wiring">V8 Uygulama Haritası</h2>')
    A('<p>V8\'in Expert arayüzü <code>src/v8/experts/base.py</code>\'de tanımlıdır. Her Expert, '
      'noktasal-zamanlı (point-in-time) bir <code>MarketState</code> tüketir ve bir '
      '<code>CandidateDraft</code> (ya da hiçbir şey) üretir — asla emir vermez, asla '
      'sermaye tahsis etmez.</p>')
    A(f'<pre><code>{esc(read(os.path.join(ROOT, "src/v8/experts/base.py")).split("class Expert:")[1][:1400])}</code></pre>')

    A('<h3>Alan haritası: <code>canonical_behavior</code> → <code>Expert</code>/<code>CandidateDraft</code></h3>')
    A('<div class="wrap"><table><tr><th>P4 alanı</th><th>V8 karşılığı</th><th>Not</th></tr>')
    for a, b, c in [
        ('canonical_family_id', 'mechanism_family_id', 'Aynı seviye kavram, farklı isim.'),
        ('canonical_behavior_id', 'behavior_family_id', '3 kodlu expert\'te birebir eşleşiyor.'),
        ('precondition_class', 'evaluate() içindeki <code>NO_HABITAT</code> kontrolü',
         'Gerekli feature\'ların (trend/volatility/history) var olup olmadığı.'),
        ('boundary_event', 'evaluate() içindeki <code>NO_SETUP</code> geçiş koşulu',
         'Örn. <code>ema_fast &gt; ema_slow and close &lt; ema_slow</code>.'),
        ('follow_through_state / resolution_event', 'CandidateDraft.risk_geometry',
         'target_r/stop_r/expiry_bars — şu an SABİT (1.0/1.0/8), literatürden değil.'),
        ('corroboration.added_parameters', '<i>(henüz kablolu değil)</i>',
         'RSI eşiği, stop mesafesi gibi kaynak parametreleri — gelecekteki variant_id için ham girdi.'),
    ]:
        A(f'<tr><td><code>{a}</code></td><td>{b}</td><td class="mut">{c}</td></tr>')
    A('</table></div>')

    A('<h3>Registry durumu (<code>docs/EXPERTS_REGISTRY.yaml</code>, ham)</h3>')
    A('<div class="wrap"><table><tr><th>canonical_behavior_id</th><th>expert_id</th>'
      '<th>Durum</th><th>Kod dosyası</th><th>Corroboration</th></tr>')
    for bh in behaviors:
        bid = bh['canonical_behavior_id']
        w = wired.get(bid)
        if w:
            cls = 'ok' if w['status'] == 'FORMALIZED' else 'bad'
            status = f'<span class="pill {cls}">{w["status"]}</span>'
            fcol = f'<code>{esc(w["file"])}</code>' if w['file'] else '<span class="mut">yok</span>'
            eid = f'<code>{esc(w["expert_id"])}</code>'
        else:
            status = '<span class="pill bad">registry\'de yok</span>'
            fcol = '<span class="mut">—</span>'
            eid = '<span class="mut">—</span>'
        A(f'<tr><td><code>{esc(bid)}</code></td><td>{eid}</td><td>{status}</td>'
          f'<td>{fcol}</td><td class="n">{per_beh.get(bid,0)}</td></tr>')
    A('</table></div>')
    A('<p class="mut" style="font-size:13px">21 davranıştan <b>3</b>\'ünün gerçek kodu var '
      '(FORMALIZED), <b>2</b>\'si <code>DATA_BLOCKED</code> (registry kaydı var, kod yok — '
      'türev tape bekliyor), <b>16</b>\'sının hiçbir registry kaydı yoktur.</p>')

    A('<h3>3 kodlu expert — tam kaynak + eşleşen davranış tanımı</h3>')
    beh_by_id = {b['canonical_behavior_id']: b for b in behaviors}
    for w in V8_REGISTRY:
        if not w['file']:
            continue
        bid = w['canonical_behavior_id']
        bh = beh_by_id.get(bid, {})
        src = read(os.path.join(ROOT, w['file']))
        A(f'<details><summary>{esc(w["expert_id"])} <span class="n">'
          f'({esc(w["file"])}, {per_beh.get(bid,0)} corroboration bu davranışı besliyor)</span></summary>')
        draft = ' → '.join(filter(None, [bh.get('precondition_class'), bh.get('boundary_event'),
                                         bh.get('follow_through_state'), bh.get('resolution_event')]))
        A(f'<p class="mut">P4 mekanizma taslağı: <code>{esc(draft)}</code></p>')
        A(f'<pre><code>{esc(src)}</code></pre>')
        A('</details>')

    A('<h3>16 davranış — hiç kod yok (ExpertSpec hedefi)</h3>')
    A('<p class="mut">Bunlar için şu an ne <code>src/v8/experts/</code> altında dosya ne '
      '<code>docs/EXPERTS_REGISTRY.yaml</code>\'de kayıt var. Hedef sözleşme '
      '<code>research/pipeline_v2/schemas/expert_spec.schema.json</code>\'de tanımlıdır '
      '(<code>expert_type</code>, <code>required_inputs</code>, '
      '<code>emit_candidate_when</code>, <code>natural_invalidation</code>, '
      '<code>missing_geometry</code> zorunlu alanları).</p>')
    A('<div class="wrap"><table><tr><th>canonical_behavior_id</th><th class="n">Corroboration</th>'
      '<th class="n">Yöntem</th></tr>')
    unwired = [b for b in behaviors if b['canonical_behavior_id'] not in wired]
    for bh in sorted(unwired, key=lambda b: -per_beh.get(b['canonical_behavior_id'], 0)):
        bid = bh['canonical_behavior_id']
        nm = sum(1 for m in methods if m['parent_behavior_id'] == bid)
        A(f'<tr><td><code>{esc(bid)}</code></td><td class="n">{per_beh.get(bid,0)}</td>'
          f'<td class="n">{nm}</td></tr>')
    A('</table></div>')

    # ================= DAVRANIŞLAR — TAM KANIT =================
    A('<h2 id="davranislar">Kanonik Davranışlar — Tam Kanıt (21)</h2>')
    A('<p class="mut">Her davranış için TÜM corroboration kayıtları, kitap bazında gruplu. '
      'Örneklem değil — 2739 kaydın tamamı burada.</p>')
    for bh in sorted(behaviors, key=lambda x: -per_beh.get(x['canonical_behavior_id'], 0)):
        bid = bh['canonical_behavior_id']
        recs = beh_records.get(bid, [])
        draft = ' → '.join(filter(None, [bh.get('precondition_class'), bh.get('boundary_event'),
                                         bh.get('follow_through_state'), bh.get('resolution_event')]))
        w = wired.get(bid)
        wtag = f'<span class="pill ok">V8: {esc(w["expert_id"])}</span>' if w and w['file'] else \
               (f'<span class="pill bad">DATA_BLOCKED</span>' if w else '<span class="pill bad">kod yok</span>')
        A(f'<h3 id="beh-{esc(bid)}">{esc(bid)} {wtag} <span class="mut">'
          f'({len(recs)} corroboration, {len(beh_books.get(bid,()))} kitap)</span></h3>')
        A(f'<p class="mut"><code>{esc(bh.get("canonical_family_id"))}</code> · '
          f'{esc(draft)}</p>')
        by_book = collections.defaultdict(list)
        for r in recs:
            by_book[r['claim_ref'].split('::')[0]].append(r)
        for b in sorted(by_book, key=lambda x: -len(by_book[x])):
            A(f'<details><summary>{esc(titles.get(b,b))} <span class="n">'
              f'({b}, {len(by_book[b])} kayıt)</span></summary>')
            for r in by_book[b]:
                A('<div class="quote">')
                A(f'{esc(r.get("exact_text"))}')
                A(f'<div class="meta">s.{esc(r.get("page"))} · <code>{esc(r["claim_ref"])}</code></div>')
                for cnd in (r.get('added_conditions') or []):
                    A(f'<div class="cond">↳ {esc(cnd)}</div>')
                for p in (r.get('added_parameters') or []):
                    A(f'<span class="param">{esc(p.get("name"))}: {esc(p.get("value"))} '
                      f'(s.{esc(p.get("page"))})</span>')
                A('</div>')
            A('</details>')

    # ================= YÖNTEMLER — TAM KANIT =================
    A('<h2 id="yontemler">Kanonik Yöntemler — Tam Kanıt</h2>')
    A(f'<p class="mut">{len(methods)} adlandırılmış, parametreli yöntem. Her biri için '
      'destekleyen TÜM alıntılar (örneklem değil).</p>')
    order = ['harmonic_pattern', 'chart_pattern', 'indicator_method', 'level_method',
             'candlestick_single_line', 'candlestick_two_line', 'candlestick_three_line', 'other']
    for cls in order:
        rows = by_class.get(cls)
        if not rows:
            continue
        A(f'<h3>{esc(cls)} <span class="pill">{len(rows)}</span></h3>')
        for m in rows:
            mark = ' <span class="canon">● kanonik</span>' if m['book_count'] >= 2 else ''
            A(f'<details><summary><code>{esc(m["canonical_method_id"])}</code>{mark} — '
              f'{esc(m.get("method_name_in_source"))} <span class="n">'
              f'({m["book_count"]} kitap, {m["corroboration_count"]} kayıt · '
              f'üst davranış: {esc(m.get("parent_behavior_id"))})</span></summary>')
            for p in (m.get('distinguishing_parameters') or []):
                A(f'<span class="param">{esc(p.get("name"))}: {esc(p.get("value"))} '
                  f'(s.{esc(p.get("page"))})</span>')
            for cnd in (m.get('distinguishing_conditions') or []):
                A(f'<div class="cond">↳ {esc(cnd)}</div>')
            for ref in m.get('supporting_claim_refs', []):
                for r in corr_by_ref.get(ref, []):
                    b = ref.split('::')[0]
                    A('<div class="quote">')
                    A(f'{esc(r.get("exact_text"))}')
                    A(f'<div class="meta">{esc(titles.get(b,b))} · s.{esc(r.get("page"))} · '
                      f'<code>{esc(ref)}</code></div>')
                    A('</div>')
            A('</details>')

    # ================= KANONİK ALT-KÜME =================
    A('<h2 id="altkume">Kanonik Alt-Küme (≥2 kitap)</h2>')
    A('<p class="mut">Çapraz-kitap doğrulanmış çekirdek — tek kaynağa bağlı değil.</p>')
    A('<div class="wrap"><table><tr><th>Yöntem</th><th>Sınıf</th><th>Üst davranış</th>'
      '<th class="n">Kitap</th><th class="n">Corrob.</th></tr>')
    for m in canon:
        A(f'<tr><td><b>{esc(m.get("method_name_in_source"))}</b></td>'
          f'<td class="mut">{esc(m.get("method_class"))}</td>'
          f'<td class="mut">{esc(m.get("parent_behavior_id"))}</td>'
          f'<td class="n">{m["book_count"]}</td><td class="n">{m["corroboration_count"]}</td></tr>')
    A('</table></div>')

    # ================= KİTAP KAPSAMASI =================
    per_book = collections.Counter(c['claim_ref'].split('::')[0] for c in corr)
    A(f'<h2 id="kitaplar">Kitap Kapsaması ({len(books)} kitap)</h2>')
    A('<div class="wrap"><table><tr><th>Kitap</th><th class="n">Corroboration</th></tr>')
    for b, n in per_book.most_common():
        A(f'<tr><td>{esc(titles.get(b,b))} <span class="mut">({b})</span></td>'
          f'<td class="n">{n}</td></tr>')
    A('</table></div>')

    # ================= COUNTEREVIDENCE — TAM LİSTE =================
    A('<h2 id="counterevidence">Counterevidence — Tam Liste</h2>')
    A(f'<p class="mut"><b>{ce_total}</b> kayıt, <b>{len(ce)}</b> kitabın tamamına yayılı — '
      'örneklem değil, hepsi. Tür dağılımı: ' +
      ' · '.join(f'{k}={v}' for k, v in sorted(ce_kinds.items())) + '</p>')
    for b in sorted(ce, key=lambda x: -len(ce[x])):
        recs = ce[b]
        A(f'<details><summary>{esc(titles.get(b,b))} <span class="n">({b}, {len(recs)} kayıt)</span></summary>')
        A('<div class="wrap"><table><tr><th>Tür</th><th>Anlam</th><th class="n">Sayfa</th></tr>')
        for r in recs:
            A(f'<tr><td><code>{esc(r.get("kind") or "NOTE")}</code></td>'
              f'<td>{esc(r.get("normalized_meaning") or r.get("exact_text") or "")}</td>'
              f'<td class="n">{esc(r.get("page"))}</td></tr>')
        A('</table></div></details>')

    # ================= SINIRLAMALAR =================
    A('<h2 id="sinirlar">Sınırlamalar (dürüst)</h2><ul>')
    A('<li><b>Tarama recall\'ü ~%8.5.</b> Deterministik regex sözlüğü dar; korpusun büyük '
      'kısmı triage\'a hiç girmedi. Kanonik <i>aileleri tanımak</i> için yeterli '
      '(fibonacci 42 kitabın claim\'inde, elliott 28\'inde), ancak her yöntemin '
      '<i>tüm parametre varyantlarını</i> toplamak için yetersiz.</li>')
    A(f'<li><b>G/F/X track\'leri işlenmedi.</b> '
      f'{routes.get("G",0)+routes.get("F",0)+routes.get("X",0)} claim (risk geometrisi, '
      'metodoloji, execution) hiçbir işleme aşamasına girmemiştir. Sistem kurulumunu besleyen '
      'asıl malzeme burada ve eksik (<code>P5_GXF_TASK.md</code>).</li>')
    A('<li><b>V8 kablolaması kısmi ve dürüst işaretli.</b> 21 davranıştan yalnızca 3\'ünün '
      'gerçek kodu var; onlarda bile <code>risk_geometry</code> şu an sabit değerler '
      'kullanıyor, literatür parametreleriyle değil. Bu belgedeki eşleşme <i>yapısal</i> '
      'bir harita — "bu alan gelecekte bu veriyle beslenecek" demektir, "zaten besleniyor" '
      'değil.</li>')
    A('<li><b>Tek-kitaplık yöntemler kanon değildir.</b> ≥2 kitap filtresi rapor anında '
      'uygulanır; işlenmemiş kitaplar geldikçe <code>book_count</code> artıp terfi edebilir.</li>')
    A('<li><b>128 kayıt düşürüldü</b> (<code>claim_id</code> null, korpusun %2.6\'sı). '
      'Uydurma yerine düşürme tercih edildi.</li>')
    A('<li>Kitapların çoğu hisse/forex/vadeli odaklı ve kripto öncesidir; '
      'aktarım riskleri çeviri katmanında etiketlenir, bu belgede henüz yoktur '
      '(<code>V8_OPERATIONALIZATION</code> / <code>crypto_translator</code> aşaması çalışmadı).</li>')
    A('</ul>')

    A('<p class="sub" style="margin-top:34px">Üretim: '
      '<code>tools/build_v23_html.py</code> · kaynaklar: '
      '<code>registry/p4_b1_partial.json</code>, <code>registry/p4_full_run.json</code>, '
      '<code>registry/p4_v22_method_pilot.json</code>, <code>registry/p4_v23_methods.json</code>, '
      '<code>processed_books/*/counterevidence.jsonl</code>, '
      '<code>src/v8/experts/*.py</code>, <code>docs/EXPERTS_REGISTRY.yaml</code></p>')
    A('</main></body></html>')

    text = '\n'.join(H)
    open(OUT, 'w').write(text)
    print(f'{OUT}  ({len(text)/1e6:.2f} MB)')
    print(f'  kitap {len(books)} · corroboration {len(corr)} · davranış {len(behaviors)} · '
          f'yöntem {len(methods)} (kanonik {len(canon)}) · counterevidence {ce_total} · '
          f'V8 kodlu davranış 3/21')


if __name__ == '__main__':
    main()
