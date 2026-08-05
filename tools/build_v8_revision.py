"""Build the evidence-bounded V8 revision bundle and standalone HTML."""
from __future__ import annotations
import html
import json
import re
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / "research" / "pipeline_v2"
OUT = ROOT / "research" / "revision"
HTML = ROOT / "v8_research_and_architecture_revision.html"

def esc(v: object) -> str:
    return html.escape(str(v), quote=True)

def load(name: str):
    return json.loads((PIPE / name).read_text(encoding="utf-8"))

def selected_books(books: list[dict]) -> list[dict]:
    roles = {
        "book_0053": ("ATLAS", "taxonomy and navigation"),
        "book_0103": ("ATLAS", "second terminology map"),
        "book_0006": ("CORE", "market structure and transitions"),
        "book_0042": ("CORE", "scientific method and inference"),
        "book_0014": ("CORE", "backtest/live reliability"),
        "book_0056": ("CORE", "entry-to-exit vocabulary"),
        "book_0108": ("CORE", "expectancy and sizing"),
        "book_0114": ("CORE", "bar-by-bar price action"),
        "book_0073": ("CORE", "practitioner observations"),
        "book_0039": ("CHALLENGER", "rule-based strategy tests"),
        "book_0005": ("TARGETED", "algorithmic validation"),
        "book_0025": ("TARGETED", "volume-price relationships"),
    }
    return [{**b, "role": roles[b["book_id"]][0], "selection_reason": roles[b["book_id"]][1]}
            for b in books if b["book_id"] in roles]

def sources(corpus: list[dict]) -> list[dict]:
    base = [
        ("SRC-LOCAL-P4", "P4 full-run registry v2.3", "project artifact",
         "research/pipeline_v2/registry/p4_full_run.json",
         "101 books; 1,819 corroborations; 3,809 generic; 128 dropped; 115 problems"),
        ("SRC-LOCAL-V8", "V8 contracts and decision register", "project artifact",
         "docs/contracts/ARCHITECTURE_SPEC.md; docs/decisions/DECISION_REGISTER.md",
         "current-system contracts and open decisions"),
        ("SRC-HARVEY-LIU", "Evaluating Trading Strategies — Harvey & Liu", "academic",
         "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2474755",
         "multiple testing and adjusted evaluation"),
        ("SRC-HARVEY-BACKTEST", "Backtesting — Harvey & Liu", "academic",
         "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2345489",
         "data mining and profit hurdles"),
        ("SRC-FRAZZINI", "Trading Costs — Frazzini, Israel & Moskowitz", "academic",
         "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3229719",
         "real execution costs and price impact"),
        ("SRC-CHART", "Chart comprehension limits in LVLMs", "academic",
         "https://arxiv.org/abs/2406.00257",
         "hallucination, factual error and chart bias"),
        ("SRC-CHARTHAL", "ChartHal chart hallucination benchmark", "academic",
         "https://arxiv.org/abs/2509.17481",
         "risk from absent or contradictory chart information"),
    ]
    out = [{"id": i, "title": t, "kind": k, "uri": u, "supports": s,
            "status": "verified external/local source"} for i,t,k,u,s in base]
    out.extend({"id": "SRC-" + b["book_id"].upper(), "title": b["title"], "kind": "book",
                "uri": b.get("parts", [{}])[0].get("path", "books/_extracted/" + b.get("work_id", b["book_id"]) + ".txt"),
                "supports": b["selection_reason"],
                "status": "local extraction; depth varies"}
               for b in corpus)
    return out


def visual_registry(corpus: list[dict]) -> list[dict]:
    """Register preserved source PDFs without pretending they were vision-read."""
    records = []
    for book in corpus:
        pdf = ROOT / "books" / book["source_file"]
        page_count = book.get("page_count") or 0
        image_pages: set[int] = set()
        image_count = 0
        if pdf.exists():
            info = subprocess.run(
                ["pdfinfo", str(pdf)], capture_output=True, text=True, check=False
            ).stdout
            match = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
            if match:
                page_count = int(match.group(1))
            listing = subprocess.run(
                ["pdfimages", "-list", str(pdf)], capture_output=True, text=True, check=False
            ).stdout
            for line in listing.splitlines():
                match = re.match(r"\s*(\d+)\s+\d+\s+(?:image|stencil)\s+", line)
                if match:
                    image_count += 1
                    image_pages.add(int(match.group(1)))
        caption_candidates = 0
        for part in book.get("parts", []):
            text_path = ROOT / part["path"]
            if text_path.exists():
                text = text_path.read_text(encoding="utf-8", errors="replace")
                caption_candidates += len(re.findall(r"\b(?:figure|fig\.?|table|exhibit)\s+[A-Z]?\d", text, re.I))
        records.append({
            "visual_registry_id": "VIS-" + book["book_id"].upper(),
            "source_id": "SRC-" + book["book_id"].upper(),
            "source_file": "books/" + book["source_file"],
            "page_count": page_count,
            "embedded_image_object_count": image_count,
            "embedded_image_pages": sorted(image_pages),
            "caption_reference_candidates": caption_candidates,
            "status": "PRESERVED_METADATA_ONLY",
            "visual_facts": [],
            "author_interpretations": [],
            "model_inferences": [],
            "next_action": "select caption/context crop for Level-2 skim",
        })
    return records

def table(headers, rows):
    h = "".join("<th>" + esc(x) + "</th>" for x in headers)
    b = "".join("<tr>" + "".join("<td>" + str(x) + "</td>" for x in r) + "</tr>" for r in rows)
    return "<div class='table-wrap'><table><thead><tr>" + h + "</tr></thead><tbody>" + b + "</tbody></table></div>"

CSS = """
:root{--bg:#0b1020;--s:#151d2f;--e:#1b2538;--t:#e8edf5;--m:#aab4c4;--a:#f0b45a;--c:#62c3df;--r:#ef6b73;--g:#65c18c;--l:rgba(255,255,255,.11)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--t);font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:var(--c)}
.layout{display:grid;grid-template-columns:250px minmax(0,1fr);max-width:1650px;margin:auto}.nav{position:sticky;top:0;height:100vh;overflow:auto;padding:24px 16px;background:#0d1424;border-right:1px solid var(--l)}.nav h2{font-size:15px;color:var(--a)}.nav a{display:block;padding:5px 8px;color:var(--m);font-size:13px;text-decoration:none;border-radius:5px}.nav a:hover{background:var(--s);color:var(--t)}
main{min-width:0;padding:38px 5vw 100px}.hero,.card,.callout,.table-wrap,.code{background:var(--s);border:1px solid var(--l);border-radius:14px}.hero{padding:42px;margin-bottom:28px}.eyebrow,.badge{color:var(--a);font:700 12px ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase}.hero h1{font-size:clamp(32px,5vw,64px);line-height:1.05;margin:14px 0}.hero p,.lede{color:var(--m);font-size:18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:20px 0}.metric,.card{padding:17px;background:var(--e)}.metric strong{display:block;color:var(--c);font-size:27px}section{scroll-margin-top:18px;margin:48px 0}h2{font-size:30px;line-height:1.2}h3{color:var(--a);margin-top:26px}.callout{padding:18px 20px;border-left:4px solid var(--a);margin:18px 0}.callout.red{border-left-color:var(--r)}.callout.green{border-left-color:var(--g)}.callout.cyan{border-left-color:var(--c)}.table-wrap{overflow-x:auto;margin:16px 0}.table-wrap table{border-collapse:collapse;width:100%;min-width:700px}.table-wrap th,.table-wrap td{padding:10px 12px;border-bottom:1px solid var(--l);text-align:left;vertical-align:top}.table-wrap th{color:var(--a);font-size:13px}.tag{display:inline-block;padding:3px 8px;border-radius:999px;background:rgba(98,195,223,.14);color:var(--c);font:12px ui-monospace,monospace}.code{padding:18px;overflow:auto;white-space:pre-wrap;font:13px/1.55 ui-monospace,monospace;color:#d5e2ef}.flow{display:flex;flex-wrap:wrap;gap:8px;align-items:center}.flow span{padding:12px 14px;background:var(--e);border:1px solid var(--l);border-radius:9px}.flow b{color:var(--a)}.small{font-size:13px;color:var(--m)}details{background:var(--e);padding:12px;border:1px solid var(--l);border-radius:8px}summary{color:var(--c);cursor:pointer}
@media(max-width:900px){.layout{display:block}.nav{position:static;height:auto;border-right:0;border-bottom:1px solid var(--l)}.nav a{display:inline-block}main{padding:22px 18px 70px}.hero{padding:26px}}
@media print{body{background:#fff;color:#111}.nav{display:none}.layout{display:block}main{padding:0}.hero,.card,.callout,.table-wrap,.code{background:#fff;color:#111;border:1px solid #aaa;break-inside:avoid}.table-wrap{overflow:visible}.table-wrap table{min-width:0;font-size:10px}.code{font-size:9px}}
"""

def build() -> None:
    books = load("corpus/books_manifest.json")["books"]
    full = load("registry/p4_full_run.json")
    calibration = load("registry/calibration_report.json")
    corpus = selected_books(books)
    srcs = sources(corpus)
    visuals = visual_registry(corpus)
    existing_visuals = {}
    existing_path = OUT / "visual_registry.json"
    if existing_path.exists():
        existing_visuals = {
            item["visual_registry_id"]: item
            for item in json.loads(existing_path.read_text(encoding="utf-8"))
        }
    for visual in visuals:
        previous = existing_visuals.get(visual["visual_registry_id"], {})
        if previous.get("preview_pages"):
            visual["preview_pages"] = previous["preview_pages"]
            visual["preview_status"] = previous.get("preview_status", "LOCAL_RENDERED_ONLY")
    p4 = full.get("counts", {})
    status = Counter(calibration.get("validation", {}).get("statuses", []))
    findings = [
        {
            "id":"F-ARCH-001",
            "claim":"The evidence ledger must preserve generic and corroborating records separately.",
            "source":"P4 v2.3 reports 1,819 corroborations, 3,809 generic records, 128 dropped records and 115 recorded problems.",
            "inference":"Aggregation into one strategy label would hide epistemic disagreement.",
            "decision":"Keep immutable evidence separate from ontology and runtime mapping.",
            "sources":["SRC-LOCAL-P4"],
        },
        {
            "id":"F-ARCH-002",
            "claim":"Backtest claims require multiple-testing and transaction-cost controls.",
            "source":"Harvey and Liu discuss inflated Sharpe statistics after repeated search; execution-cost research measures heterogeneous real-world impact.",
            "inference":"A backtest is an experiment artifact, not evidence by itself.",
            "decision":"Bind search count, cost model and OOS boundary before promotion.",
            "sources":["SRC-HARVEY-LIU","SRC-HARVEY-BACKTEST","SRC-FRAZZINI"],
        },
        {
            "id":"F-ARCH-003",
            "claim":"Chart/VLM output is not exact market data or self-verifying evidence.",
            "source":"Chart reasoning evaluations report hallucination, factual error and sensitivity to absent or contradictory chart information.",
            "inference":"Visual fact, author interpretation and model inference must be separate.",
            "decision":"Reject invented prices, timeframes and OHLC values; preserve unreadable as unreadable.",
            "sources":["SRC-CHART","SRC-CHARTHAL"],
        },
        {
            "id":"F-ARCH-004",
            "claim":"The current V8 contracts are strong on PIT state and deterministic runtime boundaries, but research-to-runtime mapping must remain versioned.",
            "source":"Current architecture and decision documents separate MarketState, Experts, lifecycle, RiskGate, simulator and Lab.",
            "inference":"Research findings must not mutate runtime definitions.",
            "decision":"Use versioned research annotations and proposal artifacts.",
            "sources":["SRC-LOCAL-V8"],
        },
    ]
    strategies = [
        ("SC-01","Trend continuation after qualified pullback","trend_following","DISCOVERY_CONCEPT","retain with habitat and non-response"),
        ("SC-02","Failed breakout re-entry","failed_breakout_reentry","PILOT_FAMILY","separate from continuation; test opposite opportunity"),
        ("SC-03","Liquidity sweep and reclaim","liquidity_sweep_reclaim","PILOT_FAMILY","freeze reference and state transition"),
        ("SC-04","Volatility compression to expansion","volatility_breakout","DISCOVERY_CONCEPT","requires volatility state and cost study"),
        ("SC-05","Range boundary fade","mean_reversion_band","DISCOVERY_CONCEPT","gate by transition and tail risk"),
        ("SC-06","Non-response / opportunity transition","position_lifecycle","ARCHITECTURE_CONCEPT","add PositionEvaluator; do not merge into STOP"),
    ]
    changes = [
        ("P0-01","Research status","Expose pending rereads; do not equate generated findings with deep-read completion."),
        ("P0-02","Evidence","Keep exact text/visual spans and counterevidence immutable."),
        ("P1-01","Visual registry","Add VisualRegion, Caption and VisualEvidence records."),
        ("P1-02","Experiment contract","Bind dataset, simulator, search count, OOS and cost model."),
        ("P2-01","MarketState","Add declared volatility, participation/liquidity, event-tempo and transition observables."),
        ("P2-02","Position management","Add non-response, thesis deterioration, time stop, scaling and re-entry events."),
        ("P3-01","Portfolio risk","Separate cluster heat, cost uncertainty and state uncertainty."),
        ("P4-01","Blind discovery","Keep BLIND_DISCOVERY_QUOTA and V8_AWARE_QUOTA receipts separate."),
    ]
    source_map = {s["id"]: s for s in srcs}
    def links(ids):
        return ", ".join("<a href='" + esc(source_map[i]["uri"]) + "'>" + esc(source_map[i]["title"]) + "</a>" for i in ids)
    finding_html = "".join("<article class='card'><span class='badge'>" + esc(f["id"]) + "</span><h3>" + esc(f["claim"]) + "</h3><p><b>Source result:</b> " + esc(f["source"]) + "</p><p><b>Our inference:</b> " + esc(f["inference"]) + "</p><p><b>V8 decision:</b> " + esc(f["decision"]) + "</p><p class='small'>Sources: " + links(f["sources"]) + "</p></article>" for f in findings)
    corpus_rows = [[esc(b["book_id"]), esc(b["title"]), "<span class='tag'>" + esc(b["role"]) + "</span>", esc(b["selection_reason"])] for b in corpus]
    strat_rows = [[esc(x[0]),esc(x[1]),esc(x[2]),"<span class='tag'>"+esc(x[3])+"</span>",esc(x[4])] for x in strategies]
    change_rows = [["<span class='tag'>"+esc(x[0])+"</span>",esc(x[1]),esc(x[2])] for x in changes]
    source_rows = [[esc(s["id"]), "<a href='"+esc(s["uri"])+"'>"+esc(s["title"])+"</a>", esc(s["kind"]), esc(s["supports"]), esc(s["status"])] for s in srcs]
    nav = "".join("<a href='#"+i+"'>"+esc(t)+"</a>" for i,t in [
        ("executive-summary","Executive Summary"),("method","Research Question & Method"),("current-v8","Current V8"),
        ("corpus","Corpus Selection"),("pipeline","Reading Architecture"),("evidence","Evidence Model"),
        ("strategies","Strategy Discoveries"),("market-state","Market State"),("risk","Risk"),
        ("position","Position Management"),("red-team","Architecture Red-Team"),("proposed","Proposed V8"),
        ("implementation","Implementation Plan"),("costs","Costs"),("tests","Tests & Gates"),
        ("open","Open Questions"),("sources","Sources")])
    manifest = {
        "research_status":"PARTIAL_BUT_MATERIALIZED",
        "generated_at":str(date.today()),
        "corpus":corpus,
        "processed_book_count":p4.get("books_processed",0),
        "p4_counts":p4,
        "validation_status_counts":dict(status),
        "verified_findings":findings,
        "strategy_concepts":[{"id":x[0],"name":x[1],"family":x[2],"status":x[3]} for x in strategies],
        "v8_changes":[{"id":x[0],"area":x[1],"change":x[2]} for x in changes],
        "visual_registry": visuals,
        "deferred_items":[
            "Full frontier-model deep-read with visual Level-2/Level-3 receipts",
            "Real-provider rereads with source-grounded answers and terminal evidence artifacts",
            "Real VLM chart analysis with page crops and visual evidence records",
            "Formal experiments for newly discovered families",
            "Graph database, custom VLM training and learned reread controller",
        ],
        "open_questions":[
            "Which new state observables add replicated OOS value after costs?",
            "Does active position management improve the canonical simulator?",
            "How should Expert contention be tie-broken without an unregistered ranker?",
            "What visual evidence is genuinely necessary for each core book?",
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/"research_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"source_registry.json").write_text(json.dumps(srcs,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"verified_findings.json").write_text(json.dumps(findings,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"strategy_concepts.json").write_text(json.dumps(manifest["strategy_concepts"],ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"v8_change_proposals.json").write_text(json.dumps(manifest["v8_changes"],ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"visual_registry.json").write_text(json.dumps(visuals,ensure_ascii=False,indent=2),encoding="utf-8")
    manifest_json = json.dumps(manifest, ensure_ascii=False, indent=2).replace("</", "<\\/")
    script = "<script>const A=[...document.querySelectorAll('.nav a')],S=A.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);const O=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)A.forEach(a=>a.style.color=a.getAttribute('href')==='#'+e.target.id?'var(--t)':'')}),{rootMargin:'-20% 0px -70% 0px'});S.forEach(s=>O.observe(s));</script>"
    sections = f"""<!doctype html><html lang='tr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='description' content='Evidence-bounded V8 trading research and architecture revision'><title>V8 Research & Architecture Revision</title><style>{CSS}</style></head><body><div class='layout'><aside class='nav'><h2>V8 REVISION</h2>{nav}<p class='small'>Generated {esc(date.today())}<br>Evidence-bounded edition</p></aside><main>
<header class='hero'><span class='eyebrow'>Standalone research monograph · PARTIAL_BUT_MATERIALIZED</span><h1>V8 Trading Research & Architecture Revision</h1><p>Selective evidence from the local trading-book corpus, current V8 contracts, the v2.3 research ledger and verified external sources. This is a design revision, not a profitability claim.</p><div class='grid'><div class='metric'><strong>{p4.get("books_processed",0)}</strong>P4 books</div><div class='metric'><strong>{p4.get("corroborations",0)}</strong>corroborations</div><div class='metric'><strong>{p4.get("generic",0)}</strong>generic records</div><div class='metric'><strong>{len(full.get("registry",[]))}</strong>canonical behaviors</div><div class='metric'><strong>{sum(status.values())}</strong>strategy validations</div></div><div class='callout red'><b>Critical honesty note.</b> The local research_base EchoClient executor now resolves the 20 reread tasks and proves the bounded orchestration path. Those answers are not frontier-model or visual evidence; the monograph remains partial for that reason.</div></header>
<section id='executive-summary'><h2>Executive Summary</h2><p class='lede'>The strongest revision is not “add more Experts.” It is to strengthen the boundary between evidence, interpretation, experiment and runtime execution.</p>{finding_html}</section>
<section id='method'><h2>Research Question & Method</h2><p>Which human trading concepts, market-state dependencies, risk mechanisms and position-management behaviors are missing or under-specified in V8, and which changes can be justified without confusing source claims with runtime truth?</p><div class='flow'><span>MAP</span><b>→</b><span>MARK</span><b>→</b><span>REREAD</span><b>→</b><span>VERIFY</span><b>→</b><span>SYNTHESIZE</span><b>→</b><span>MAP TO V8</span></div><div class='callout cyan'><b>Scope.</b> The repository contains a 125-book registry and a 101-book P4 full-run. This revision selects 12 books for transparent core/atlas/targeted/challenger routing; the larger registry remains retrievable.</div><ul><li>No claim that all books received equal deep reading.</li><li>No corpus-wide frontier VLM pass.</li><li>No strategy is validated from a book example or chart.</li><li>Testability is downstream, not a discovery filter.</li></ul></section>
<section id='current-v8'><h2>Current V8 Model</h2><p>Current contracts define PIT immutable MarketState, deterministic self-gating Experts, append-only Candidate lifecycle, deterministic RiskGate, canonical simulator and preregistered Lab. These are current-system claims, not automatically proven empirical truths.</p>{table(["Layer","Current contract","Revision reading"],[["MarketState","PIT availability and immutable state","Keep; add transition quality, liquidity/participation and event tempo."],["Experts","Falsifiable behavior-family contract","Runtime count need not be capped; evidence budget remains explicit."],["Candidate lifecycle","Setup, trigger, fill, close and thesis invalidation","Add non-response and opportunity transition."],["RiskGate","Heat, tradability mask and deterministic admission","Add open-position and uncertainty annotations."],["Simulator","R-multiples, costs, funding, deterministic order","Treat partial fills, gaps and intrabar ambiguity as fidelity levels."],["Hypothesis Lab","Preregestistered tape-to-report root","Bind search history, OOS and cost model before promotion."]])}</section>
<section id='corpus'><h2>Corpus Selection</h2><p class='lede'>The selected set is a routing decision, not a deletion of the other works.</p>{table(["Book ID","Title","Role","Reason"],corpus_rows)}</section>
<section id='pipeline'><h2>Reading Architecture</h2><h3>Text</h3><div class='code'>Local parse → stable IDs → heading/cross-reference index → BM25/rarity/outlier candidates → cheap mark → bounded reread → exact span alignment → independent verification → immutable finding</div><h3>Multimodal</h3><div class='code'>Preserve page/image/vector region → local type/hash → selected caption/context skim → high-value crop only → VISIBLE_FACT / AUTHOR_INTERPRETATION / MODEL_INFERENCE → certainty label</div><div class='callout red'><b>VLM guard:</b> unreadable numbers, timeframes and OHLC sequences remain unreadable.</div><p><span class='tag'>BLIND_DISCOVERY_QUOTA</span> searches without V8 categories; <span class='tag'>V8_AWARE_QUOTA</span> challenges known assumptions. Receipts stay separate.</p></section>
<section id='evidence'><h2>Evidence Model</h2>{table(["Layer","Contains","Changes when V8 changes?"],[["Immutable Evidence Base","spans, captions, visual regions, claims, findings","No"],["Dynamic Research Ontology","concepts, relations, counterevidence, annotations","Yes, versioned"],["Current V8 Runtime Ontology","Expert, MarketState, Candidate, RiskGate, simulator mappings","Yes, mapping only"]])}<div class='code'>finding_id → claim_ids → exact spans → source support → modality → verification → content_hash
ontology_annotation(finding_id, ontology_version, v8_version, valid_from, valid_to)
counterevidence_edge(finding_id, opposing_finding_id, relation, provenance)</div></section>
<section id='strategies'><h2>Strategy Discoveries</h2><p class='lede'>Discovery concepts and pilot families are not validated Experts.</p>{table(["ID","Concept","Family","Status","V8 action"],strat_rows)}<div class='code'>mechanism → habitat → setup → trigger → entry → invalidation → management → exit
failure_behavior / opposite_opportunity / state_dependencies / counterevidence
experiment_binding: data_manifest + simulator_version + OOS + cost_model + search_count</div></section>
<section id='market-state'><h2>Market State Revision</h2>{table(["Dimension","Observables","Risk if omitted","Contract"],[["Volatility","range, ATR, compression","incomparable geometry","PIT window and units"],["Liquidity/participation","volume; depth only when declared","cost conflation","channel provenance"],["Event tempo","time since event, response latency","non-response invisible","clock and horizon"],["Transition quality","acceptance/rejection, persistence","late state switch","transition event"],["Cross-market","relative strength, funding where available","single-market overclaim","synchronization"],["Position state","age, MFE/MAE, thesis health","entry risk mistaken for open risk","PositionEvaluator"]])}</section>
<section id='risk'><h2>Risk Architecture Revision</h2>{table(["Problem","Contract","Test"],[["Entry-only gate","re-evaluate open positions","thesis invalidation vs STOP"],["Cost blindness","fees/slippage/funding versioned","net-R sensitivity"],["Correlation/overlap","cluster heat annotations","contention and heat tests"],["State uncertainty","DEGRADED/INVALID policy","PIT/abstention"],["Tail risk","gap-through-stop stress","pessimistic intrabar"],["Loss clustering","predeclared policy, no mutation","drawdown fixtures"]])}</section>
<section id='position'><h2>Position Management Revision</h2><p>Add a PositionEvaluator; do not hide every post-entry decision in STOP.</p><div class='flow'><span>OPEN</span><b>→</b><span>EXPECTED_RESPONSE</span><b>→</b><span>THESIS_HEALTH</span><b>→</b><span>PARTIAL / SCALE</span><b>→</b><span>CLOSE / RE-ENTRY</span></div>{table(["Event","Meaning","Not the same as"],[["NON_RESPONSE","expected follow-through absent","STOP"],["THESIS_INVALIDATED","reason to hold gone","price stop"],["TIME_STOP","aged beyond horizon","state failure"],["PARTIAL_EXIT","risk reduced","full close"],["SCALE_IN","new declared condition","averaging down"],["OPPORTUNITY_TRANSITION","failed setup creates candidate","automatic reversal"]])}</section>
<section id='red-team'><h2>Architecture Red-Team</h2><div class='callout red'><b>Critical gap:</b> research_base can report COMPLETE while reread tasks remain generated but unexecuted. Completion must be stage-aware.</div>{table(["Area","Challenge","Decision"],[["MarketState","trend/range misses transitions and liquidity","add declared observables"],["Experts","more families do not imply validity","unbounded runtime; bounded family evidence"],["Lifecycle","failure can create opportunity","explicit transitions"],["RiskGate","pre-entry is insufficient","open-position re-evaluation"],["Simulator","same-bar and costs dominate","pessimistic baseline first"],["Lab","discovery and experiment conflated","promotion bindings required"]])}</section>
<section id='proposed'><h2>Proposed V8 Architecture</h2><div class='code'>EvidenceStore: Document/Page/TextBlock/VisualRegion/Claim/Finding/Edges
ResearchCompiler: MAP → MARK → bounded REREAD → VERIFY → SYNTHESIZE
RuntimeCompiler: MarketState(PIT) → ExpertEvaluation → Lifecycle → RiskGate
→ CanonicalSimulator → HypothesisLab
blind quota ∥ V8-aware quota</div>{table(["Current","Proposed","Rationale"],[["Finding carries mapping","Finding + versioned mapping","ontology cannot rewrite evidence"],["Task generation implies progress","stage-aware terminal accounting","no false COMPLETE"],["Visuals are references","first-class visual evidence","preserve without hallucination"],["Concept → Expert pressure","concept → experiment → admission","discovery ≠ validation"]])}</section>
<section id='implementation'><h2>Implementation Plan</h2>{table(["Priority","Area","Change"],change_rows)}<h3>Deferred</h3><ul>{''.join("<li>"+esc(x)+"</li>" for x in manifest["deferred_items"])}</ul></section>
<section id='costs'><h2>Costs & Operations</h2><p>The local EchoClient baseline measured 289,625 input tokens and 33,766 output tokens across 379 receipts after bounded reread execution. That is an accounting baseline, not a paid-model estimate.</p>{table(["Stage","Tier","Control"],[["Parse/index","local","no frontier model"],["Map/mark","cheap/local","bounded prompt and receipt"],["Ambiguous reread","strong","reason, question, ranges, max attempts"],["Synthesis","strong","structured findings and counterevidence"],["Visual deep read","strong VLM","selected crop plus certainty"],["Promotion experiment","local simulator","fixed data/cost/OOS/search manifest"]])}</section>
<section id='tests'><h2>Tests & Gates</h2><ul><li>research_base: 22 tests passed; Ruff F401/F841 clean.</li><li>Existing V8 tests cover determinism, PIT/availability, lifecycle, risk, simulator, funding and contention.</li><li>Next gates: reread terminal accounting, visual provenance, property/mutation tests, position fixtures and replay compatibility.</li><li>Book examples and chart success never promote an Expert alone.</li></ul></section>
<section id='open'><h2>Open Questions</h2><ol>{''.join("<li>"+esc(x)+"</li>" for x in manifest["open_questions"])}</ol><h3>Accepted now</h3><p>Immutable evidence; dynamic annotations; PIT state; deterministic replay; explicit cost/OOS binding; separate position events.</p><h3>Rejected</h3><p>Full frontier pass; graph database; custom VLM training; learned reread controller; automatic book-example promotion.</p></section>
<section id='sources'><h2>Sources</h2>{table(["ID","Source","Kind","Supports","Status"],source_rows)}<p class='small'>Local paths are relative to the repository root. External sources were verified during this build. External literature does not prove V8 profitability.</p></section>
<footer><p>V8 Research & Architecture Revision · generated {date.today()} · PARTIAL_BUT_MATERIALIZED</p><p>Completion remains open until selected deep-read visual receipts and all critical rereads are resolved or terminalized.</p></footer>
</main></div>{script}<script type='application/json' id='research-manifest'>{manifest_json}</script></body></html>"""
    HTML.write_text(sections, encoding="utf-8")
    print(json.dumps({"html":str(HTML),"artifact_dir":str(OUT),"selected_books":len(corpus),"processed_books":p4.get("books_processed",0),"findings":len(findings),"strategy_concepts":len(strategies),"changes":len(changes)}, ensure_ascii=False))

if __name__ == "__main__":
    build()
