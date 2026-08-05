"""Render bounded local visual previews for the selected corpus."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "research" / "revision" / "visual_registry.json"
OUT = ROOT / "research" / "revision" / "visual_previews"

def main() -> None:
    records = json.loads(REGISTRY.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for record in records:
        pdf = ROOT / record["source_file"]
        pages = record.get("embedded_image_pages", [])[:3]
        previews = []
        for page in pages:
            stem = f"{record['source_id'].lower()}-p{page}"
            output = OUT / stem
            result = subprocess.run(
                ["pdftocairo", "-png", "-singlefile", "-r", "72",
                 "-f", str(page), "-l", str(page), str(pdf), str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            image = output.with_suffix(".png")
            if result.returncode == 0 and image.exists():
                previews.append({
                    "page": page,
                    "path": str(image.relative_to(ROOT)),
                    "status": "PRESERVED_PREVIEW_NOT_SEMANTICALLY_ANALYZED",
                })
                total += 1
        record["preview_pages"] = previews
        record["preview_status"] = "LOCAL_RENDERED_ONLY"
    REGISTRY.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"books": len(records), "previews": total, "output": str(OUT)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
