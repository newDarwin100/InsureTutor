"""Extract unchanged page text as a baseline; does not clean or translate it."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parents[1]
EXTRACTION_VERSION = "1"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def extract(source, output_root):
    source = source.resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    output = output_root / "flexi-ulife-prime-saver" / (
        f"{digest[:12]}-pypdf-{pypdf.__version__}-v{EXTRACTION_VERSION}"
    )
    if output.exists():
        raise SystemExit(f"Output already exists; kept unchanged: {output}")

    reader = pypdf.PdfReader(source)
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        pages.append({
            "document_id": "flexi-ulife-prime-saver",
            "document_name": source.name,
            "pdf_page": number,
            "text": text,
            "character_count": len(text),
            "review_status": "NOT_REVIEWED",
        })

    output.mkdir(parents=True)
    page_dir = output / "pages"
    page_dir.mkdir()
    for page in pages:
        (page_dir / f"page-{page['pdf_page']:03d}.txt").write_text(page["text"], encoding="utf-8")
    write_json(output / "pages.json", pages)
    write_json(output / "manifest.json", {
        "document_id": "flexi-ulife-prime-saver",
        "document_name": source.name,
        "source_path": str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),
        "source_sha256": digest,
        "tool": "pypdf",
        "tool_version": pypdf.__version__,
        "extraction_version": EXTRACTION_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "page_count": len(pages),
        "page_numbering": "Physical PDF pages, 1-based; includes cover",
        "stage": "RAW_BASELINE",
        "empty_pages": [p["pdf_page"] for p in pages if not p["text"].strip()],
        "limitations": [
            "Reading order, tables, footnotes and bilingual alignment require review.",
            "No cleaning, translation, language splitting or OCR has been applied.",
        ],
    })
    print(f"Extracted {len(pages)} pages to {output}")
    print(f"Empty pages: {sum(not p['text'].strip() for p in pages)}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "docs/FLEXI-ULife Prime Saver.pdf")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data/raw")
    args = parser.parse_args()
    extract(args.source, args.output_root)
