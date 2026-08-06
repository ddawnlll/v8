#!/usr/bin/env python3
"""Build the comprehensive, resumable V8/book comparison artifacts."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stable_source_time(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def ul(items: list[object]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def paragraphs(items: list[str]) -> str:
    return "".join(f"<p>{esc(item)}</p>" for item in items)


def chapter_card(chapter: dict) -> str:
    return f"""
    <article class="chapter" id="chapter-{chapter['chapter']}" data-status="{esc(chapter['v8_status'])}">
      <div class="meta"><span class="number">Bölüm {chapter['chapter']}</span><span class="status">{esc(chapter['v8_status'])}</span><span class="pages">Basılı s. {esc(chapter['printed_pages'])}</span></div>
      <h3>{esc(chapter['title'])}</h3>
      <p><strong>Ana soru:</strong> {esc(chapter['main_question'])}</p>
      <p><strong>Kitabın anlatısı:</strong> {esc(chapter['narrative'])}</p>
      <p><strong>Trading nesneleri:</strong> {esc(', '.join(chapter['trading_objects']))}</p>
      <p><strong>Risk/pozisyon:</strong> {esc(chapter['risk_position_implications'])}</p>
      <p><strong>V8 karşılaştırması:</strong> {esc(chapter['v8_alignment'])}</p>
      <p><strong>Gerilim/sınır:</strong> {esc(chapter['v8_tension'])}</p>
      <p><strong>Önerilen deney:</strong> {esc(chapter['experiment'])}</p>
      <p class="source"><strong>Kaynak ankrajı:</strong> {esc(' · '.join(chapter['source_anchors']))}</p>
    </article>"""


def comparison_table(items: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{esc(item['axis'])}</td><td>{esc(item['book'])}</td><td>{esc(item['v8'])}</td><td>{esc(item['judgement'])}</td><td><span class=\"status\">{esc(item['status'])}</span></td></tr>"
        for item in items
    )
    return f"<table><thead><tr><th>Eksen</th><th>Kitap</th><th>V8</th><th>Yargı</th><th>Durum</th></tr></thead><tbody>{rows}</tbody></table>"


def queue_table(items: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{esc(item['priority'])}</td><td>{esc(item['idea'])}</td><td>{esc(item['source'])}</td><td>{esc(item['action'])}</td><td>{esc(item['gate'])}</td></tr>"
        for item in items
    )
    return f"<table><thead><tr><th>Öncelik</th><th>Fikir</th><th>Kitap kaynağı</th><th>V8 aksiyonu</th><th>Gate</th></tr></thead><tbody>{rows}</tbody></table>"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    workdir = args.workdir
    manifest = load(workdir / "review_manifest.json")
    synthesis = load(workdir / "checkpoints" / "handbook_synthesis_v0_2.json")
    matrix = load(workdir / "checkpoints" / "chapter_matrix_01_15_v0_2.json") + load(workdir / "checkpoints" / "chapter_matrix_16_29_v0_2.json")
    chapters = load(workdir / "checkpoints" / "chapter_map.json")
    topics = load(workdir / "checkpoints" / "topic_pages.json")
    index_state = load(workdir / "checkpoints" / "state.json")
    chapter_state = load(workdir / "checkpoints" / "chapter_extraction_state.json")
    endmatter_state = load(workdir / "checkpoints" / "endmatter_state.json")
    legacy = load(workdir / "checkpoints" / "analysis_notes.json")

    output_dir = workdir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_pdf = workdir.parent.parent / manifest["source"]["relative_path"]
    final = {
        "schema_version": "v8-handbook-technical-analysis-v0.2",
        "generated_at": stable_source_time(source_pdf),
        "status": "COMPLETE_FULL_BOOK_REVIEW",
        "source": manifest["source"],
        "review_scope": synthesis["reading_scope"],
        "method": synthesis["method"],
        "resume_checkpoint": {
            "index_state": index_state,
            "chapter_extraction_state": chapter_state,
            "endmatter_state": endmatter_state,
            "source_layout_text": "source/book_layout.txt",
            "source_raw_text": "source/book_raw.txt",
            "chapter_map": "checkpoints/chapter_map.json",
            "topic_pages": "checkpoints/topic_pages.json",
            "chapter_matrix_01_15": "checkpoints/chapter_matrix_01_15_v0_2.json",
            "chapter_matrix_16_29": "checkpoints/chapter_matrix_16_29_v0_2.json",
            "synthesis": "checkpoints/handbook_synthesis_v0_2.json"
        },
        "chapter_map": chapters,
        "topic_page_counts": {key: len(value) for key, value in topics.items()},
        "book_general_trading_narrative": synthesis["book_general_trading_narrative"],
        "v8_comparison_axes": synthesis["v8_comparison_axes"],
        "contradictions_and_resolution": synthesis["contradictions_and_resolution"],
        "chapter_matrix": matrix,
        "v8_ideas_ranked": synthesis["v8_ideas_ranked"],
        "appendices": synthesis["appendices"],
        "visual_analysis": synthesis["visual_analysis"],
        "negative_transfer": synthesis["negative_transfer"],
        "detailed_findings_from_first_pass": legacy.get("findings", []),
        "artifact_paths": {
            "json": "output/technical_analysis_handbook_v8_full.json",
            "html": "output/full_index.html",
            "source_pdf": manifest["source"]["relative_path"]
        }
    }
    json_path = output_dir / "technical_analysis_handbook_v8_full.json"
    json_path.write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    narrative = synthesis["book_general_trading_narrative"]
    chain_rows = "".join(
        f"<tr><td>{item['step']}</td><td>{esc(item['name'])}</td><td>{esc(item['book_logic'])}</td><td>{esc(item['v8_translation'])}</td></tr>"
        for item in narrative["decision_chain"]
    )
    chapter_rows = "".join(
        f"<tr><td><a href=\"#chapter-{c['chapter']}\">{c['chapter']}</a></td><td>{esc(c['title'])}</td><td>{esc(c['printed_page_start'])}</td><td>{esc(c['page_start'])}–{esc(c['page_end'])}</td></tr>"
        for c in chapters
    )
    contradiction_cards = "".join(
        f"<article class=\"contradiction\"><h3>{esc(item['id'])}</h3><p><strong>Kitap:</strong> {esc(item['book_claim'])}</p><p><strong>V8 problemi:</strong> {esc(item['v8_problem'])}</p><p><strong>Çözüm:</strong> {esc(item['resolution'])}</p></article>"
        for item in synthesis["contradictions_and_resolution"]
    )
    appendix_cards = "".join(
        f"<article class=\"appendix\"><h3>{esc(item['name'])}</h3><p><strong>Sayfalar:</strong> {esc(item['physical_pages'])}</p><p>{esc(item['summary'])}</p><p><strong>V8 mapping:</strong> {esc(item['v8_mapping'])}</p><p class=\"warning\"><strong>Sınır:</strong> {esc(item['risk_note'])}</p></article>"
        for item in synthesis["appendices"]
    )
    visual_cards = "".join(
        f"<figure><img src=\"../{esc(item['file'])}\" alt=\"{esc(item['purpose'])}\"><figcaption>Physical page {esc(item['physical_page'])}: {esc(item['purpose'])}</figcaption></figure>"
        for item in synthesis["visual_analysis"]["reviewed_pages"]
    )

    html_doc = f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V8 × The Handbook of Technical Analysis — Full Review</title>
<style>
@page{{margin:16mm}}:root{{--blue:#0b4f86;--ink:#1d242b;--muted:#617080;--line:#d6dee7;--paper:#fbfcfe;--warn:#fff6df;--green:#e8f4ec}}*{{box-sizing:border-box}}body{{max-width:1240px;margin:auto;padding:30px 48px;background:var(--paper);color:var(--ink);font:15px/1.58 Georgia,serif}}h1,h2,h3,h4,th,.status,.number,.pages{{font-family:Arial,sans-serif}}h1{{font-size:2rem;color:var(--blue);border-bottom:3px solid var(--blue);padding-bottom:.35rem;margin-top:2.8rem}}h2{{font-size:1.45rem;color:var(--blue);margin-top:2.2rem}}h3{{margin:.3rem 0 .55rem}}p{{margin:.6rem 0}}code,pre{{font-family:ui-monospace,monospace}}.hero{{border-left:6px solid var(--blue);padding:1rem 1.2rem;background:#edf5fc}}.status,.number,.pages{{display:inline-block;border-radius:999px;padding:.15rem .55rem;font-size:.7rem;font-weight:700;letter-spacing:.02em}}.status{{background:#e9f1f8;color:var(--blue)}}.number{{background:#d8e9f6;color:#174d77;margin-right:.35rem}}.pages{{background:#eef0f2;color:#53616d;margin-left:.35rem}}.small,.source{{color:var(--muted);font-size:.9rem}}table{{border-collapse:collapse;width:100%;font:12px Arial,sans-serif;margin:1rem 0}}th,td{{border:1px solid var(--line);padding:.48rem;vertical-align:top}}th{{background:#eaf2f9;color:#174d77}}.chain td:first-child{{width:3rem;text-align:center;font-weight:700}}.chapter{{border-top:1px solid var(--line);padding:1rem 0 1.2rem;break-inside:avoid}}.chapter .meta{{margin-bottom:.5rem}}.chapter[data-status*="REJECTED"]{{background:#fff8f8}}.contradiction,.appendix{{border-left:4px solid #6c8ca6;padding:.7rem 1rem;margin:1rem 0;background:#f4f7f9;break-inside:avoid}}.warning{{background:var(--warn);border-left:4px solid #d99b00;padding:.6rem .8rem}}.callout{{background:var(--green);border-left:4px solid #388552;padding:.8rem 1rem}}.gallery{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.2rem}}figure{{margin:0 0 1.1rem;break-inside:avoid}}figure img{{max-width:100%;height:auto;border:1px solid var(--line);box-shadow:0 1px 5px #cbd5df}}figcaption{{font:12px Arial,sans-serif;color:var(--muted);margin-top:.25rem}}nav ol{{columns:2}}a{{color:#154c78}}@media(max-width:780px){{body{{padding:20px}}.gallery,nav ol{{columns:1;grid-template-columns:1fr}}table{{font-size:11px}}}}@media print{{body{{padding:0;font-size:10pt}}h1{{break-before:page}}a{{color:#000;text-decoration:none}}}}
</style>
</head>
<body>
<header><h1>V8 × <em>The Handbook of Technical Analysis</em></h1>
<div class="hero"><strong>Görev:</strong> Kitabın tamamını (29 bölüm + endmatter) okuyup, genel trading anlatısını V8’in strategy, market-state, risk, position-management ve evidence contracts’ıyla karşılaştırmak.<br><strong>Durum:</strong> FULL_BOOK_REVIEW_COMPLETE · <strong>Kaynak SHA-256:</strong> <code>{esc(manifest['source']['sha256'])}</code></div>
<p class="small">Bu belge kitabın iddialarını V8 ekonomik kanıtı olarak sunmaz. Kitap desteği ile V8 design inference birbirinden ayrılmıştır; promotion için frozen-OOS ve simulator authority gerekir.</p></header>

<h1>1. Sonuç: kitabın genel trading anlatısı</h1>
<p>{esc(narrative['one_sentence'])}</p>
<div class="callout"><strong>Temel hüküm:</strong> Kitabın V8’e gerçek katkısı indikatör kataloğu değil; market context ile action arasına state, signal, trigger, geometry, position ve risk katmanlarını yerleştirmesidir. V8’in görevi bu katmanları immutable ve falsifiable hale getirip ekonomik iddiayı ayrıca sınamaktır.</div>
<h2>Karar zinciri: kitap → V8</h2>
<table class="chain"><thead><tr><th>#</th><th>Adım</th><th>Kitabın trading mantığı</th><th>V8 karşılığı</th></tr></thead><tbody>{chain_rows}</tbody></table>
<h2>Kitabın aslında öğrettiği</h2>{ul(narrative['what_the_book_is_really_teaching'])}

<h1>2. Kitap ve V8: eksen bazlı karşılaştırma</h1>
{comparison_table(synthesis['v8_comparison_axes'])}

<h1>3. Çelişkiler ve çözüm kararları</h1>
{contradiction_cards}

<h1>4. Kapsam ve resumeability</h1>
<p>Kaynak PDF immutable text olarak çıkarıldı; 980 sayfa 40 batch halinde indekslendi. 29 chapter slice ve fiziksel 949–980 arasındaki 32 sayfa endmatter ayrı dosyalara yazıldı. Bölüm 29’un aralığı özellikle 939–946 fiziksel sayfalarıyla sınırlandı; Appendix A/B ve index artık bölüme karışmıyor.</p>
<table><thead><tr><th>Artifact</th><th>Path</th><th>İşlev</th></tr></thead><tbody>
<tr><td>Layout text</td><td><code>source/book_layout.txt</code></td><td>Sayfa ayrımlı tam extraction</td></tr>
<tr><td>Batch index</td><td><code>checkpoints/batch_0001.json … batch_0040.json</code></td><td>25 sayfalık resume checkpoint’leri</td></tr>
<tr><td>Chapter state</td><td><code>checkpoints/chapter_extraction_state.json</code></td><td>29 bölüm extraction durumu</td></tr>
<tr><td>Chapter matrix</td><td><code>checkpoints/chapter_matrix_01_15_v0_2.json</code> + <code>chapter_matrix_16_29_v0_2.json</code></td><td>Her bölümün trading/V8 mapping’i</td></tr>
<tr><td>Synthesis</td><td><code>checkpoints/handbook_synthesis_v0_2.json</code></td><td>Genel anlatı, çelişki ve backlog</td></tr>
<tr><td>Endmatter</td><td><code>source/endmatter.txt</code></td><td>Appendix A/B, website note, index</td></tr>
</tbody></table>

<h1>5. 29 bölümün tamamı: chapter-by-chapter V8 okuması</h1>
<p class="small">Her kartta kitabın ana sorusu, anlatı, trading nesneleri, risk/pozisyon sonucu, V8 uyumu, gerilim ve önerilen deney bulunur. Status ekonomik başarı değil, aktarımın sözleşme/deney durumudur.</p>
{''.join(chapter_card(chapter) for chapter in matrix)}

<h1>6. V8 için sıralı fikirler ve backlog</h1>
{queue_table(synthesis['v8_ideas_ranked'])}

<h1>7. Appendix A/B ve kitabın somut karar örneği</h1>
{appendix_cards}

<h1>8. Görsel analiz</h1>
<p>{esc(synthesis['visual_analysis']['design_language'])}</p>
<p><strong>V8 görsel okuma kuralı:</strong> {esc(synthesis['visual_analysis']['visual_to_v8_rule'])}</p>
{ul(synthesis['visual_analysis']['visual_limits'])}
<div class="gallery">{visual_cards}</div>

<h1>9. Negatif transfer kuralları</h1>
{ul(synthesis['negative_transfer'])}

<h1>10. Final değerlendirme</h1>
<p>Bu kitap V8’e üç şeyi aynı anda veriyor: geniş bir conditional market-state sözlüğü, signal/trigger/position/risk ayrımının pratik gerekçesi ve robust testing gereğinin trading dilindeki karşılığı. Buna karşılık V8’in katı saat/availability, append-only lifecycle, counterfactual attribution, deterministic risk ve authority gate’leri kitabın daha discretionary anlatısını denetlenebilir hale getiren ek katmandır.</p>
<p>Dolayısıyla doğru sonraki adım kitabın tüm araçlarını baseline’a doldurmak değil; önce signal→trigger→candidate→risk→outcome zincirini mevcut V8 slice’ında koruyup, P0/P1 fikirleri tek tek challenger olarak preregister etmektir. Kitap başarılı bir hipotez havuzu sağlar; sonuç sağlamaz.</p>
</body></html>"""
    html_path = output_dir / "full_index.html"
    html_path.write_text(html_doc, encoding="utf-8")
    # Keep the familiar entry point pointed at the comprehensive artifact.
    (output_dir / "index.html").write_text(html_doc, encoding="utf-8")
    (output_dir / "technical_analysis_handbook_v8.json").write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checkpoint = workdir / "checkpoints" / "final_review_state.json"
    checkpoint.write_text(
        json.dumps(
            {
                "schema_version": "v8-handbook-final-review-v0.2",
                "phase": "FULL_REVIEW_COMPLETE",
                "source_sha256": manifest["source"]["sha256"],
                "source_pages": manifest["source"]["physical_pages"],
                "chapters": len(matrix),
                "appendices": len(synthesis["appendices"]),
                "generated_at": final["generated_at"],
                "artifacts": {
                    "json": "output/technical_analysis_handbook_v8_full.json",
                    "html": "output/full_index.html",
                    "json_sha256": sha256(json_path),
                    "html_sha256": sha256(html_path)
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"json": str(json_path), "html": str(html_path), "checkpoint": str(checkpoint), "chapters": len(matrix), "appendices": len(synthesis["appendices"])}, indent=2))


if __name__ == "__main__":
    main()
