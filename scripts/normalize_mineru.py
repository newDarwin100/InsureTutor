"""Normalize MinerU JSON without repairing, translating or discarding source text."""

import argparse
import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1"


class TableParser(HTMLParser):
    """Keep cell boundaries and spans; do not infer merged numeric relationships."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.row = []
        elif tag in {"td", "th"}:
            self.cell = {"text": "", "rowspan": int(attrs.get("rowspan", 1)),
                         "colspan": int(attrs.get("colspan", 1))}
        elif tag == "br" and self.cell is not None:
            self.cell["text"] += "\n"

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"] += data

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def walk_blocks(block):
    yield block
    for child in block.get("blocks", []):
        yield from walk_blocks(child)


def language_hint(text):
    chinese = bool(re.search(r"[\u3400-\u9fff]", text))
    # Only a hint: English currencies/abbreviations can occur in Chinese blocks.
    english = bool(re.search(r"[A-Za-z]{3,}", text))
    return "mixed" if chinese and english else "zh" if chinese else "en" if english else "und"


def normalize_block(block, pointer, page, position, discarded):
    texts, tables, images = [], [], []
    for node in walk_blocks(block):
        for line in node.get("lines", []):
            spans = line.get("spans", [])
            content = "".join(span.get("content", "") for span in spans)
            if content:
                texts.append(content)
            for span in spans:
                if span.get("html"):
                    parser = TableParser()
                    parser.feed(span["html"])
                    tables.append({"html": span["html"], "rows": parser.rows})
                if span.get("image_path"):
                    images.append(span["image_path"])
    text = "\n".join(texts)
    table_text = "\n".join(" | ".join(c["text"] for c in row)
                           for table in tables for row in table["rows"])
    combined = text + "\n" + table_text
    flags = []
    if any(ord(c) < 32 and c not in "\n\r\t" for c in combined):
        flags.append("CONTROL_CHARACTER")
    if re.search(r"HK\$\s*/", combined):
        flags.append("POSSIBLE_MISSING_CURRENCY_AMOUNT")
    if re.search(r"\d+(?:\.\d+)?%\s*\d+(?:\.\d+)?%", combined):
        flags.append("MERGED_PERCENT_VALUES")
    return {
        "block_id": f"p{page:03d}-{'d' if discarded else 'b'}{position:03d}",
        "pdf_page": page,
        "source_pointer": pointer,
        "source_index": block.get("index"),
        "type": block.get("type"),
        "bbox": block.get("bbox"),
        "heading_level": block.get("level"),
        "source_discarded": discarded,
        "text": text,
        "tables": tables,
        "image_references": images,
        "language_hint": language_hint(combined),
        "review_flags": flags,
        "review_status": "NOT_REVIEWED",
    }


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize(source, output):
    raw_bytes = source.read_bytes()
    data = json.loads(raw_bytes)
    source_pages = data["pdf_info"]
    indices = [p["page_idx"] for p in source_pages]
    if indices != list(range(len(source_pages))):
        raise ValueError("Unexpected page indices; verify page mapping before proceeding")
    pages, all_blocks = [], []
    for i, page in enumerate(source_pages):
        groups = {}
        for key in ["para_blocks", "discarded_blocks"]:
            groups[key] = [normalize_block(b, f"/pdf_info/{i}/{key}/{j}", i + 1,
                                          j + 1, key == "discarded_blocks")
                           for j, b in enumerate(page.get(key, []))]
            all_blocks.extend(groups[key])
        pages.append({"pdf_page": i + 1, "mineru_page_idx": page["page_idx"],
                      "page_size": page["page_size"], "blocks": groups["para_blocks"],
                      "discarded_blocks": groups["discarded_blocks"]})
    types = Counter(b["type"] for b in all_blocks if not b["source_discarded"])
    flagged = [b for b in all_blocks if b["review_flags"]]
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "pages.json", pages)
    write_json(output / "manifest.json", {
        "source_file": str(source.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "pdf_file": "docs/FLEXI-ULife Prime Saver.pdf",
        "pdf_sha256": hashlib.sha256((ROOT / "docs/FLEXI-ULife Prime Saver.pdf").read_bytes()).hexdigest(),
        "normalizer_version": VERSION,
        "mineru_metadata": {k: v for k, v in data.items() if k != "pdf_info"},
        "page_count": len(pages), "content_block_types": dict(types),
        "discarded_blocks_preserved": sum(b["source_discarded"] for b in all_blocks),
        "flagged_blocks": len(flagged),
        "stage": "NORMALIZED_NOT_CLEANED",
        "limitations": ["Preserves MinerU block order, not a verified reading order.",
                        "Language hints are not verified bilingual clause alignment.",
                        "No source character or currency repair has been applied.",
                        "No remote images have been downloaded."]})
    lines = ["# MinerU 初步结构检查", "", f"页数：{len(pages)}；内容块：{dict(types)}。",
             "", "本结果只整理结构，尚未清洗、修正、对齐语言或构建检索分块。",
             "PDF 页码从 1 开始，包含封面；MinerU page_idx 从 0 开始。",
             "保留正文、标题、表格 HTML、单元格和合并属性、坐标、被解析器丢弃的块及源 JSON 路径。",
             "language_hint 只用于辅助筛选，中文未自动判定简繁；含货币缩写的中文可能标为 mixed。",
             "", "## 自动标记的待核对项", "", "| PDF 页 | 块 | 原因 |", "| --- | --- | --- |"]
    lines.extend(f"| {b['pdf_page']} | {b['block_id']} | {', '.join(b['review_flags'])} |" for b in flagged)
    lines.extend(["", "标记只提示可能的问题，不代表全文已检查，也不自动给出正确替代值。",
                  "下一步：按原 PDF 核对这些项、恢复阅读关系、关联中英文条款和脚注，再建立测试题。"])
    (output / "review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"pages": len(pages), "content_block_types": dict(types),
                      "flagged_blocks": len(flagged), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
                        default=ROOT / "data/raw/MinerU_FLEXI-ULife Prime Saver__20261008094732.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/mineru")
    args = parser.parse_args()
    normalize(args.source.resolve(), args.output.resolve())
