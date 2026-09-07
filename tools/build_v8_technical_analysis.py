#!/usr/bin/env python3
"""Build a simple HTML report from the V8 technical-analysis idea register."""
import argparse
import html
import json
from pathlib import Path


CSS = """
@page{margin:18mm}
body{max-width:1060px;margin:auto;padding:28px 48px;background:#fffdf9;color:#181818;font:15px/1.55 Georgia,serif}
h1,h2,h3,h4,th{font-family:Arial,sans-serif}
h1{font-size:1.8rem;margin-top:3rem;border-bottom:2px solid #333;padding-bottom:.3rem}
h2{margin-top:2.2rem}
h3{margin-top:1.5rem}
pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:.8rem;background:#f0eee8;font:13px/1.45 ui-monospace,monospace}
table{border-collapse:collapse;width:100%;font:12px Arial,sans-serif;margin:1rem 0}
th,td{border:1px solid #aaa;padding:.4rem;vertical-align:top}
th{background:#ece9e1}
a{color:#154c78}
.status{border-left:4px solid #333;background:#f0eee8;padding:.8rem 1rem}
.tag{display:inline-block;border:1px solid #999;border-radius:3px;padding:.1rem .35rem;margin:.1rem .2rem .1rem 0;font:11px Arial,sans-serif;background:#f4f1ea}
.idea{border-top:1px solid #bbb;padding-top:.5rem}
.muted{color:#555}
@media print{body{padding:0;font-size:10pt}pre{font-size:8pt}a{color:#000;text-decoration:none}h1{break-before:page}}
"""


def esc(value):
    return html.escape(str(value), quote=True)


def tags(values):
    return "".join(f'<span class="tag">{esc(v)}</span>' for v in values)


def source_links(source_ids, source_map):
    out = []
    for source_id in source_ids:
        source = source_map[source_id]
        label = esc(source["title"])
        if source.get("url"):
            out.append(f'<a href="{esc(source["url"])}">{label}</a>')
        else:
            out.append(label)
    return ", ".join(out)


def render(data):
    source_map = {x["id"]: x for x in data["source_register"]}
    ideas = data["ideas"]
    priority = data["executive_summary"]["priority_order"]
    priority_map = {x["id"]: x for x in ideas}
    rows = []
    for idea_id in priority:
        idea = priority_map[idea_id]
        rows.append(
            "<tr>"
            f"<td><code>{esc(idea['id'])}</code></td>"
            f"<td>{esc(idea['title'])}</td>"
            f"<td>{esc(idea['priority'])}</td>"
            f"<td>{tags([idea['domain'], idea['disposition']])}</td>"
            f"<td>{esc(idea['one_line_v8_action'])}</td>"
            "</tr>"
        )

    sections = []
    for idea in ideas:
        book = idea["book_source"]
        external = source_links(idea.get("external_source_ids", []), source_map)
        sections.append(
            '<section class="idea">'
            f'<h2 id="{esc(idea["id"].lower())}">{esc(idea["id"])}: {esc(idea["title"])}</h2>'
            f"<p>{tags([idea['domain'], idea['priority'], idea['disposition'], idea['evidence_label']])}</p>"
            f"<p><strong>Kitaptaki çıkarım:</strong> {esc(book['paraphrase'])} "
            f"<span class=\"muted\">(PDF s. {esc(book['pdf_pages'])}; kitap s. {esc(book['book_pages'])}; {esc(book['section'])})</span></p>"
            f"<p><strong>V8'e çeviri:</strong> {esc(idea['v8_translation'])}</p>"
            f"<p><strong>Uygulama yüzeyi:</strong> {esc(idea['implementation_surface'])}</p>"
            f"<p><strong>Kontrol ve sınır:</strong> {esc(idea['guardrail'])}</p>"
            f"<p><strong>Test/karar:</strong> {esc(idea['test_or_decision'])}</p>"
            f"<p><strong>Kaynaklar:</strong> {source_links(idea.get('source_ids', ['BOOK']), source_map)}"
            + (f"; dış doğrulama: {external}" if external else "")
            + "</p></section>"
        )

    next_rows = []
    for item in data["recommended_next_experiments"]:
        next_rows.append(
            "<tr>"
            f"<td>{esc(item['order'])}</td><td>{esc(item['question'])}</td>"
            f"<td>{esc(item['owner'])}</td><td>{esc(item['gate'])}</td>"
            "</tr>"
        )

    do_not_import = "".join(f"<li>{esc(x)}</li>" for x in data["executive_summary"]["do_not_import"])
    key_findings = "".join(f"<li>{esc(x)}</li>" for x in data["executive_summary"]["key_findings"])
    source_rows = []
    for source in data["source_register"]:
        location = esc(source.get("location", ""))
        if source.get("url"):
            location = f'<a href="{esc(source["url"])}">{location}</a>'
        source_rows.append(f"<tr><td>{esc(source['id'])}</td><td>{esc(source['title'])}</td><td>{location}</td><td>{esc(source['boundary'])}</td></tr>")

    return (
        '<!doctype html><html lang="tr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{esc(data["title"])}</title><style>{CSS}</style></head><body>'
        f'<header><h1>{esc(data["title"])}</h1>'
        f'<p><strong>Kitap tabanlı V8 fikir registerı.</strong> {esc(data["purpose"])}</p></header>'
        f'<section id="status"><h1>Durum ve okuma kuralı</h1><p class="status"><strong>{esc(data["status"]["v8_status"])}</strong> '
        f'Bu rapor kârlılık, doğrulanmış execution veya ekonomik üstünlük iddiası değildir. Ekonomik hüküm: '
        f'<code>{esc(data["status"]["economic_verdict"])}</code>.</p>'
        f'<p>{esc(data["method_note"])}</p></section>'
        '<section id="summary"><h1>Özet</h1><ul>' + key_findings + '</ul>'
        '<h2>Öncelik sırası</h2><table><tr><th>ID</th><th>Fikir</th><th>Öncelik</th><th>Alan / durum</th><th>V8 aksiyonu</th></tr>'
        + "".join(rows) + '</table><h2>Varsayılan olarak aktarılmayanlar</h2><ul>' + do_not_import + '</ul></section>'
        '<section id="ideas"><h1>Fikirler</h1>' + "".join(sections) + '</section>'
        '<section id="experiments"><h1>Önerilen sonraki deneyler</h1><p>Hepsi yeni preregistration, veri erişimi ve ilgili V8 kapılarıyla yürütülmelidir; mevcut frozen holdout geriye dönük değiştirilmez.</p>'
        '<table><tr><th>#</th><th>Soru</th><th>Sahip / yüzey</th><th>Geçiş koşulu</th></tr>' + "".join(next_rows) + '</table></section>'
        '<section id="sources"><h1>Kaynak registerı</h1><table><tr><th>ID</th><th>Kaynak</th><th>Konum</th><th>Sınır</th></tr>' + "".join(source_rows) + '</table></section>'
        f'<p class="muted">Üretim tarihi: {esc(data["created_utc"])}. Ham veri: <code>research/handbook_v8_ideas.json</code>.</p>'
        '</body></html>\n'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    Path(args.out).write_text(render(data), encoding="utf-8")
    print(f"wrote {args.out}: ideas={len(data['ideas'])} sources={len(data['source_register'])}")


if __name__ == "__main__":
    main()
