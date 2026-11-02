#!/usr/bin/env python3
"""Build the standalone V9 monograph HTML from its canonical Markdown source.

Repo placement: tools/build_v9_monograph.py
Run from repository root:
    python tools/build_v9_monograph.py \
      --src docs/v9/V9_ARCHITECTURE_MONOGRAPH.md \
      --out site/v9.html --figdir docs/v9/figures

Uses the existing project's Python Markdown renderer when present; falls back
on markdown-it-py for standalone preview builds. Pin the renderer version for
byte-identical builds. Figures are bundled as inline static SVG, not generated.
Never edit site/v9.html by hand.
"""
import argparse
import hashlib
import html
import re
from pathlib import Path

CSS = r'''
@page{margin:18mm}
:root{color-scheme:light}
body{max-width:1060px;margin:auto;padding:28px 48px;background:#fffdf9;color:#181818;font:15px/1.55 Georgia,serif}
h1,h2,h3,h4,th{font-family:Arial,sans-serif}
h1{font-size:1.8rem;margin-top:3rem;border-bottom:2px solid #333;padding-bottom:.3rem;line-height:1.25}
h2{margin-top:2.2rem;font-size:1.36rem}
h3{margin-top:1.5rem;font-size:1.13rem}
pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:.8rem;background:#f0eee8;font:13px/1.45 ui-monospace,monospace;border-radius:5px}
code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:.9em}
table{border-collapse:collapse;width:100%;font:12px/1.45 Arial,sans-serif;margin:1rem 0}
th,td{border:1px solid #aaa;padding:.4rem;vertical-align:top;overflow-wrap:anywhere}th{background:#ece9e1;text-align:left}a{color:#154c78}
blockquote{margin:1.5rem 0;padding:12px 20px;border-left:4px solid #506c87;background:#f0f3f5}
hr{border:0;border-top:1px solid #dad4c9;margin:2rem 0}
.cover{padding:28px 20px 22px;background:#f0eee8;border-top:5px solid #273848;margin:0 0 28px}
.kicker{font:700 11px Arial,sans-serif;letter-spacing:.12em;color:#4f6475}.cover h1{font-size:2.24rem;margin:10px 0 6px;border:0;padding:0}.cover p{color:#52606a;margin:7px 0}
.metadata{font:12px Arial,sans-serif;margin:18px 0;color:#4a5360}
.notice{padding:12px 16px;border-left:4px solid #6b7377;background:#f5f1eb;font:13px/1.5 Arial,sans-serif;margin:20px 0}
#toc{background:#f6f3ed;border:1px solid #ded7cb;padding:13px 22px;margin:24px 0 45px}
#toc h2{margin:8px 0 12px;font-size:1.1rem}#toc ol{columns:2;column-gap:32px;font:12px/1.5 Arial,sans-serif;padding-left:18px}
#toc li{break-inside:avoid;padding:3px 0}#toc a{text-decoration:none}
.figure{margin:20px auto 26px;text-align:center;border:1px solid #e1ded7;padding:14px;border-radius:8px;background:white}
.figure svg{width:100%;height:auto;max-height:960px}.figure figcaption{font:12px/1.45 Arial,sans-serif;color:#5d6771;margin-top:10px}
.source-block{margin:12px 0;font:12px Arial,sans-serif}.source-block summary{cursor:pointer}
.math{font-size:13px;text-align:center;background:#f4f2ed;padding:12px;overflow-x:auto}
footer{margin:40px 0 20px;border-top:1px solid #aaa;padding-top:16px;font:12px/1.6 Arial,sans-serif;color:#666}
@media(max-width:760px){body{padding:16px 14px;font-size:14px}.cover{padding:15px}h1{font-size:1.5rem}.cover h1{font-size:1.8rem}table{font-size:10px}th,td{padding:5px}#toc ol{columns:1}.figure{padding:5px}.metadata{font-size:11px}}
@media print{body{padding:0;font-size:10pt}pre{font-size:8pt}a{color:#000;text-decoration:none}h1{break-before:page}#toc ol{columns:2}.cover h1{break-before:auto}table{break-inside:avoid}figure{break-inside:avoid}.source-block{display:none}}
'''


def markdown_to_html(source: str) -> tuple[str, str]:
    try:
        import markdown
        return markdown.markdown(source, extensions=['tables', 'fenced_code', 'sane_lists'], output_format='html5'), 'python-markdown'
    except ModuleNotFoundError:
        from markdown_it import MarkdownIt
        return MarkdownIt('default', {'html': False}).enable('table').render(source), 'markdown-it-py'


def svg_inline(path: Path) -> str:
    raw = path.read_text('utf-8')
    return raw[raw.find('<svg'):].strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--src', default='docs/v9/V9_ARCHITECTURE_MONOGRAPH.md')
    p.add_argument('--out', default='site/v9.html')
    p.add_argument('--figdir', default='docs/v9/figures')
    args = p.parse_args()
    source = Path(args.src).read_text('utf-8')
    content, renderer = markdown_to_html(source)
    h1_index = 0
    toc = []
    def tag_heading(m):
        nonlocal h1_index
        inner = m.group(1)
        text = re.sub('<[^>]+>', '', inner)
        h1_index += 1
        ident = f'sec-{h1_index:02d}'
        if h1_index > 1:
            toc.append((ident, text))
        return f'<h1 id="{ident}">{inner}</h1>'
    content = re.sub(r'<h1>(.*?)</h1>', tag_heading, content, flags=re.S)

    figs = [
        ('VII. Trader', 'trader_loop.svg', 'Şekil 1. V9 trading core: native yürütme, kanıt ve yeni piyasa olaylarıyla yeniden değerlendirilen trader karar döngüsü.'),
        ('VIII. Entry', 'decision_orthogonal.svg', 'Şekil 2. Eşzamanlı ve ayrı karar/niyet/emir/pozisyon/koruma durumları; venue safety reconciliation.'),
        ('XIII. Autonomous', 'kaizen_loop.svg', 'Şekil 3. Trading runtime’dan ayrı, insan onaylı offline Kaizen araştırma çevrimi.'),
    ]
    for heading, fname, caption in figs:
        if fname and (Path(args.figdir)/fname).exists():
            svg = svg_inline(Path(args.figdir)/fname)
            figure = '<figure class="figure">' + svg + f'<figcaption>{html.escape(caption)}</figcaption></figure>'
            pattern = r'(<h1 id="sec-\d+">[^<]*' + re.escape(heading) + r'[^<]*</h1>)'
            content, num = re.subn(pattern, lambda m:m.group(1) + figure, content, count=1)
            if num!=1: print('warning: did not insert figure',fname)

    # Replace mermaid source with disclosure: figures above are always static/offline.
    content=re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        lambda m:'<details class="source-block"><summary>Şema kaynak kodu (Mermaid)</summary><pre><code>'+m.group(1)+'</code></pre></details>',content,flags=re.S)

    cover='''<header class="cover"><div class="kicker">V9 · RESEARCH MONOGRAPH & ARCHITECTURE SPECIFICATION</div><h1>Market-Aware Adaptive Trading Intelligence</h1><p>V8-next evolutionary redesign · scientific evidence, decision contracts, validation and autonomous Kaizen extension</p><div class="metadata"><strong>V9-ARCH-RFC-1.1-REVISED</strong> · 2 Kasım 2026 · OWNER APPROVAL PENDING · NO ECONOMIC CLAIM</div></header>'''
    notice='<div class="notice"><strong>Reading rule:</strong> Mimari öneri ≠ uygulanmış kod ≠ mekanik doğrulama ≠ ekonomik üstünlük ≠ üretim yetkisi. Kaynak içeriği, raporlanmış proje deneyleri ve yeni tasarım çıkarımları ayrı etiketlenmiştir.</div>'
    toc_html='<nav id="toc"><h2>İçindekiler</h2><ol>'+''.join(f'<li><a href="#{id}">{html.escape(t)}</a></li>' for id,t in toc)+'</ol></nav>'
    digest=hashlib.sha256(source.encode('utf-8')).hexdigest()
    footer=f'<footer>Kaynak: {html.escape(args.src)} · Markdown SHA-256: <code>{digest}</code> · HTML sürümü yalnız okuma çıktısıdır. Canonical source Markdown&#39;dır.</footer>'
    page='<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V9 — Market-Aware Adaptive Trading Intelligence · Research Monograph</title><style>'+CSS+'</style></head><body>'+cover+notice+toc_html+'<main>'+content+'</main>'+footer+'</body></html>\n'
    target=Path(args.out);target.parent.mkdir(parents=True, exist_ok=True);target.write_text(page,'utf-8')
    print('wrote',target,'bytes',len(page.encode('utf-8')),'sections',len(toc),'source_sha256',digest,'renderer',renderer)

if __name__=='__main__': main()
