#!/usr/bin/env python3
"""Build the final JSON and HTML technical document from resumable checkpoints."""

from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def list_html(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def finding_card(finding: dict) -> str:
    evidence = list_html(finding["source"])
    visuals = list_html(finding.get("visual_evidence", []))
    return f"""
    <article class="finding" id="{esc(finding['id'])}">
      <div class="finding-meta"><span class="badge">{esc(finding['theme'])}</span><span class="status">{esc(finding['v8_status'])}</span></div>
      <h3>{esc(finding['id'])} — {esc(finding['title'])}</h3>
      <p><strong>Kitapta:</strong> {esc(finding['book_claim'])}</p>
      <div class="grid">
        <div><h4>Kaynak sayfalar</h4>{evidence}</div>
        <div><h4>Görsel referans</h4>{visuals}</div>
      </div>
      <p><strong>V8 aktarımı:</strong> {esc(finding['v8_mapping'])}</p>
      <p><strong>Uygulama:</strong> {esc(finding['implementation'])}</p>
      <p><strong>Deney:</strong> {esc(finding['experiment'])}</p>
      <p class="warning"><strong>Risk / sınır:</strong> {esc(finding['failure_mode'])}</p>
    </article>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    workdir = args.workdir
    manifest = load(workdir / "review_manifest.json")
    notes = load(workdir / "checkpoints" / "analysis_notes.json")
    chapters = load(workdir / "checkpoints" / "chapter_map.json")
    topics = load(workdir / "checkpoints" / "topic_pages.json")
    state = load(workdir / "checkpoints" / "state.json")
    chapter_state = load(workdir / "checkpoints" / "chapter_extraction_state.json")

    final = {
        "schema_version": "v8-handbook-technical-analysis-v0.1",
        "generated_at": now(),
        "status": "COMPLETE",
        "source": manifest["source"],
        "review_scope": manifest["review_scope"],
        "resume_checkpoint": {
            "index_state": state,
            "chapter_extraction_state": chapter_state,
            "source_layout_text": "source/book_layout.txt",
            "source_raw_text": "source/book_raw.txt",
            "chapter_map": "checkpoints/chapter_map.json",
            "topic_pages": "checkpoints/topic_pages.json",
            "analysis_notes": "checkpoints/analysis_notes.json"
        },
        "chapter_map": chapters,
        "topic_page_counts": {key: len(value) for key, value in topics.items()},
        "executive_takeaways": notes["executive_takeaways"],
        "findings": notes["findings"],
        "v8_admission_queue": notes["v8_admission_queue"],
        "visual_analysis": notes["visual_analysis"],
        "negative_transfer": notes["negative_transfer"],
        "method": notes["method"],
        "artifact_paths": {
            "json": "output/technical_analysis_handbook_v8.json",
            "html": "output/index.html",
            "source_pdf": manifest["source"]["relative_path"]
        }
    }
    output_dir = workdir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "technical_analysis_handbook_v8.json"
    json_path.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    chapter_rows = "".join(
        f"<tr><td>{esc(c['chapter'])}</td><td>{esc(c['title'])}</td><td>{esc(c['printed_page_start'])}</td><td>{esc(c['page_start'])}–{esc(c['page_end'])}</td></tr>"
        for c in chapters
    )
    queue_rows = "".join(
        f"<tr><td>{esc(q['priority'])}</td><td>{esc(q['proposal'])}</td><td><span class=\"status\">{esc(q['status'])}</span></td><td>{esc(q['reason'])}</td></tr>"
        for q in notes["v8_admission_queue"]
    )
    visual_cards = "".join(
        f"<figure><img src=\"../{esc(item['file'])}\" alt=\"{esc(item['purpose'])}\"><figcaption>Physical page {esc(item['physical_page'])}: {esc(item['purpose'])}</figcaption></figure>"
        for item in notes["visual_analysis"]["rendered_pages"]
    )
    finding_cards = "".join(finding_card(finding) for finding in notes["findings"])

    html_doc = f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V8 — Technical Analysis Handbook Extraction</title>
<style>
@page{{margin:18mm}}:root{{--blue:#0b4f86;--ink:#1d242b;--muted:#617080;--line:#d6dee7;--paper:#fbfcfe;--warn:#fff6df}}*{{box-sizing:border-box}}body{{max-width:1180px;margin:auto;padding:30px 48px;background:var(--paper);color:var(--ink);font:15px/1.58 Georgia,serif}}h1,h2,h3,h4,th,.badge,.status{{font-family:Arial,sans-serif}}h1{{font-size:2rem;color:var(--blue);border-bottom:3px solid var(--blue);padding-bottom:.35rem;margin-top:2.8rem}}h2{{font-size:1.45rem;color:var(--blue);margin-top:2.2rem}}h3{{margin-bottom:.3rem}}h4{{margin-bottom:.2rem;color:var(--blue)}}p{{margin:.6rem 0}}code,pre{{font-family:ui-monospace,monospace}}.hero{{border-left:6px solid var(--blue);padding:1rem 1.2rem;background:#edf5fc}}.status,.badge{{display:inline-block;border-radius:999px;padding:.15rem .55rem;font-size:.73rem;font-weight:700;letter-spacing:.03em}}.status{{background:#e9f1f8;color:var(--blue)}}.badge{{background:#e8eef4;color:#35495c;margin-right:.35rem}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}.finding{{border-top:1px solid var(--line);padding:1rem 0 1.2rem;break-inside:avoid}}.finding-meta{{margin-top:.2rem}}.warning{{background:var(--warn);border-left:4px solid #d99b00;padding:.6rem .8rem}}table{{border-collapse:collapse;width:100%;font:12px Arial,sans-serif;margin:1rem 0}}th,td{{border:1px solid var(--line);padding:.45rem;vertical-align:top}}th{{background:#eaf2f9;color:#174d77}}figure{{margin:0 0 1.1rem;break-inside:avoid}}figure img{{max-width:100%;height:auto;border:1px solid var(--line);box-shadow:0 1px 5px #cbd5df}}figcaption{{font:12px Arial,sans-serif;color:var(--muted);margin-top:.25rem}}.gallery{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.2rem}}.small{{color:var(--muted);font-size:.9rem}}@media(max-width:780px){{body{{padding:20px}}.grid,.gallery{{grid-template-columns:1fr}}}}@media print{{body{{padding:0;font-size:10pt}}h1{{break-before:page}}a{{color:#000;text-decoration:none}}}}
</style>
</head>
<body>
<header><h1>V8: Technical Analysis Handbook Extraction</h1>
<div class="hero"><strong>Görev:</strong> Mark Andrew Lim’in 2016 tarihli <em>The Handbook of Technical Analysis</em> kitabından V8’e aktarılabilecek strateji, market-state, risk ve pozisyon yönetimi fikirlerinin teknik çıkarımı.<br><strong>Durum:</strong> {esc(final['status'])}; kaynak SHA-256: <code>{esc(manifest['source']['sha256'])}</code>.</div>
<p class="small">Bu belge kitap iddialarını V8 ekonomik kanıtı olarak sunmaz. Her aktarım, V8’de ayrı bir deney, veri sözleşmesi veya challenger gerektiren tasarım çıkarımıdır.</p></header>

<h1>1. Executive takeaways</h1>{list_html(notes['executive_takeaways'])}

<h1>2. Method and resumeability</h1>
<p>PDF metadata, SHA-256, ham layout/raw metin, 25 sayfalık batch indeksleri, 29 bölüm dosyası ve analiz notları diske yazılmıştır. Çalışma yeniden başlatıldığında <code>checkpoints/state.json</code> ve <code>chapter_extraction_state.json</code> son tamamlanan noktayı gösterir.</p>
<table><tr><th>Artifact</th><th>Path</th><th>Role</th></tr>
<tr><td>Source layout text</td><td><code>source/book_layout.txt</code></td><td>Sayfa ayrımlı metin</td></tr>
<tr><td>Page index</td><td><code>checkpoints/page_index.json</code></td><td>980 sayfa, konu eşleşmeleri</td></tr>
<tr><td>Chapter map</td><td><code>checkpoints/chapter_map.json</code></td><td>29 bölüm, basılı/fiziksel sayfa</td></tr>
<tr><td>Analysis checkpoint</td><td><code>checkpoints/analysis_notes.json</code></td><td>Kaynak, V8 mapping, deney, sınır</td></tr>
<tr><td>Final JSON</td><td><code>output/technical_analysis_handbook_v8.json</code></td><td>Makine-okunur çıktı</td></tr></table>

<h1>3. Chapter map</h1><table><tr><th>#</th><th>Chapter</th><th>Printed start</th><th>Physical range</th></tr>{chapter_rows}</table>

<h1>4. V8 findings</h1>{finding_cards}

<h1>5. V8 admission queue</h1><table><tr><th>Priority</th><th>Proposal</th><th>Status</th><th>Reason</th></tr>{queue_rows}</table>

<h1>6. Visual analysis</h1>
<p>{esc(notes['visual_analysis']['design_language'])}</p>{list_html(notes['visual_analysis']['useful_visual_patterns'])}<h2>Visual limits</h2>{list_html(notes['visual_analysis']['visual_limits'])}<div class="gallery">{visual_cards}</div>

<h1>7. Negative transfer rules</h1>{list_html(notes['negative_transfer'])}

<h1>8. Final V8 position</h1>
<p>Kitabın V8 için en güçlü katkısı yeni bir indikatör listesi değil, karar nesnelerinin ayrıştırılmasıdır: setup/signals, price-confirmed trigger, immutable geometry, deterministic risk, stepped position lifecycle ve regime-conditioned validation. Bu fikirler mevcut V8 baseline’ı genişletmeden önce sözleşme testleriyle, ardından frozen-OOS challenger deneyleriyle sınanmalıdır.</p>
</body></html>"""
    html_path = output_dir / "index.html"
    html_path.write_text(html_doc, encoding="utf-8")
    print(json.dumps({"json": str(json_path), "html": str(html_path), "findings": len(notes["findings"]), "chapters": len(chapters)}, indent=2))


if __name__ == "__main__":
    main()
