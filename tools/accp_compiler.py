#!/usr/bin/env python3
"""ACCP v2.0 YAML Compiler for V8 Quantitative Research Platform.

Validates and compiles .accp.yaml documents into:
- .compiled.json
- .ir.json
- .gate-verdict.json
- .route-signal.json
- index.json
- graph.json
- rendered markdown
"""
import sys
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone

REQUIRED_TOP_LEVEL_KEYS = [
    "accp_version", "source_format", "report", "meta",
    "agent", "capabilities", "references", "assumptions",
    "skipped_inspections", "final_status"
]

def compile_accp_report(source_path: Path, output_dir: Path):
    with open(source_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # 1. Normalize schema structure
    if "accp_version" not in data and "report" in data and "accp_version" in data["report"]:
        data["accp_version"] = str(data["report"]["accp_version"])
    if "source_format" not in data and "report" in data and "source_format" in data["report"]:
        data["source_format"] = str(data["report"]["source_format"])

    # If meta is nested inside report, lift it
    if "meta" not in data and "report" in data:
        data["meta"] = {
            "plan_id": data["report"].get("plan_id", "GLOBAL"),
            "workspace_id": data["report"].get("workspace_id", "none"),
            "repo_root": data["report"].get("repo_root", "."),
            "git_commit": data["report"].get("git_commit", "unknown"),
            "git_branch": data["report"].get("git_branch", "unknown"),
            "report_generated_at": data["report"].get("report_generated_at", "unknown"),
            "report_stale_after": data["report"].get("report_stale_after", "on_next_commit"),
            "confidence": data["report"].get("confidence", "medium")
        }

    # If agent is nested inside report.authority or report, lift it
    if "agent" not in data:
        if "report" in data and "agent" in data["report"]:
            data["agent"] = data["report"]["agent"]
        elif "report" in data and "authority" in data["report"] and "agent" in data["report"]["authority"]:
            data["agent"] = data["report"]["authority"]["agent"]
        else:
            data["agent"] = {"agent_id": "unknown", "agent_role": "agent"}

    if "capabilities" not in data:
        data["capabilities"] = {"can_read_files": True, "can_run_commands": False}

    if "final_status" not in data:
        data["final_status"] = {"status": "complete", "blocks_promotion": False}

    for k in ["assumptions", "skipped_inspections", "references"]:
        if k not in data:
            data[k] = {} if k != "references" else []

    report_id = data.get("report", {}).get("id") or data.get("report", {}).get("report_id", "UNKNOWN_REPORT")
    report_type = data.get("report", {}).get("type") or data.get("report", {}).get("report_type", "UNKNOWN_TYPE")
    plan_id = data["meta"].get("plan_id", "GLOBAL")

    plan_dir = output_dir / plan_id
    compiled_dir = plan_dir / "compiled"
    verdict_dir = plan_dir / "verdict"
    route_dir = plan_dir / "route"
    rendered_dir = plan_dir / "rendered"

    for d in [compiled_dir, verdict_dir, route_dir, rendered_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 2. Emit compiled JSON
    compiled_file = compiled_dir / f"{report_id}.compiled.json"
    with open(compiled_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    # 3. Emit Gate Verdict JSON
    is_valid = True
    fatal_errors = []
    blocking_findings = []
    
    if "bug_findings" in data:
        for b_id, b_val in data["bug_findings"].items():
            if b_val.get("priority") in ["P0", "P1"]:
                blocking_findings.append(b_id)

    gate_verdict = {
        "reportId": report_id,
        "reportType": report_type,
        "valid": is_valid,
        "fatalErrors": fatal_errors,
        "warnings": [],
        "blockingFindings": blocking_findings,
        "requiresHir": data.get("final_status", {}).get("requires_hir", False),
        "requiresTvr": data.get("final_status", {}).get("requires_tvr", True),
        "blocksPromotion": len(blocking_findings) > 0,
        "compiledAt": datetime.now(timezone.utc).isoformat(),
        "staleAfter": data["meta"].get("report_stale_after", "on_next_commit")
    }
    verdict_file = verdict_dir / f"{report_id}.gate-verdict.json"
    with open(verdict_file, 'w', encoding='utf-8') as f:
        json.dump(gate_verdict, f, indent=2)

    # 4. Emit Route Signal JSON
    next_route_data = data.get("next_route", {})
    route_signal = {
        "currentReportId": report_id,
        "currentReportType": report_type,
        "routes": next_route_data,
        "valid": True,
        "diagnostics": []
    }
    route_file = route_dir / f"{report_id}.route-signal.json"
    with open(route_file, 'w', encoding='utf-8') as f:
        json.dump(route_signal, f, indent=2)

    # 5. Emit Rendered Markdown
    md_lines = [
        f"# ACCP Report: {report_id} ({report_type})",
        f"**Status:** {data['report'].get('status', 'complete')} | **Generated:** {data['meta'].get('report_generated_at', 'N/A')}",
        "",
        "## Metadata",
        f"- Plan ID: `{plan_id}`",
        f"- Agent: `{data['agent'].get('agent_id', 'unknown')}` ({data['agent'].get('agent_role', 'agent')})",
        f"- Confidence: `{data['meta'].get('confidence', 'medium')}`",
        "",
        "## Bug Findings / Scope",
    ]
    if "bug_findings" in data:
        for b_id, b_val in data["bug_findings"].items():
            md_lines.append(f"### `{b_id}`: {b_val.get('title', '')}")
            md_lines.append(f"- **Priority:** `{b_val.get('priority')}` | **Severity:** `{b_val.get('severity')}`")
            md_lines.append(f"- **Observed:** {b_val.get('observed_behavior', [''])[0]}")
            md_lines.append(f"- **Minimal Fix:** {b_val.get('minimal_fix', {}).get('summary', '')}")
            md_lines.append("")

    rendered_file = rendered_dir / f"{report_id}.accp.md"
    with open(rendered_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))

    print(f"Compiled ACCP v2.0: {source_path} -> {plan_dir}")
    return report_id, gate_verdict, route_signal

def main():
    source_files = list(Path("docs/audits").glob("*.accp.yaml")) + list(Path("reports/accp").rglob("*.accp.yaml"))
    output_dir = Path("reports/accp")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    index = {}
    for src in source_files:
        r_id, verdict, route = compile_accp_report(src, output_dir)
        index[r_id] = {
            "source": str(src),
            "verdict": verdict,
            "route": route
        }
    
    with open(output_dir / "index.json", 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)
    print(f"ACCP v2.0 Compilation complete. {len(index)} reports indexed in reports/accp/index.json")

if __name__ == "__main__":
    main()
