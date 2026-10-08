"""Build evidence and retrieval chunks locally; no model or embedding calls."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.rag.preprocess import build, source_hash


def main(source, corrections, output, max_chars, overlap):
    raw = source.read_bytes()
    pages = json.loads(raw)
    config = json.loads(corrections.read_text(encoding="utf-8"))
    config["original_pages"] = pages
    result = build(pages, config, source_hash(raw), max_chars, overlap)
    output.mkdir(parents=True, exist_ok=True)
    for key in ["evidence", "parents", "chunks", "alignment", "changes", "omitted_blocks"]:
        (output / f"{key}.json").write_text(
            json.dumps(result[key], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {"input_sha256": source_hash(raw), "corrections_sha256": source_hash(corrections.read_bytes()),
                "preprocessor_version": "1", "max_chars": max_chars, "overlap_chars": overlap,
                "counts": {k: len(v) for k, v in result.items()},
                "language_hints": dict(Counter(e["language_hint"] for e in result["evidence"])),
                "stage": "RULE_BASELINE_NOT_RETRIEVAL_EVALUATED",
                "limitations": ["Bilingual numbered footnotes are paired; other clauses need alignment review.",
                                "No OCR or semantic rewriting; images with no extracted text are not indexed.",
                                "Reading order is inherited from MinerU; contextual section grouping needs review.",
                                "Length measured in characters, not tokens; no embedding or model calls."]}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 清洗与规则分块：第一版", "", f"统计：{manifest['counts']}。", "",
             "原始数据保持不变；source_text 是原始提取，text 是排版清洗或有依据修复后的文本。",
             "表格的 source_text 保留完整原始 HTML，实际引用仍需回 PDF 核对。",
             "脚注关联包含明确编号及单独核对的配置；父段落作为候选补齐，不承诺整个父段都进入上下文。",
             "当前未生成向量、未评测召回率、未完成全文双语语义核对。", "",
             "## 修复记录", ""]
    for change in result["changes"]:
        lines.append(f"- {change['block_id']}：{change['reason']}")
    lines += ["", "## 仍需注意", ""]
    for e in result["evidence"]:
        if e["review_flags"]:
            lines.append(f"- PDF 第 {e['pdf_page']} 页 / {e['evidence_id']}：{e['review_flags']}；{e['review_note'] or ''}")
    lines += ["", "未提取出文字的图片/图表块保留在原 JSON；omitted_blocks.json 记录列表，不能宣称全部图示已覆盖。",
              "下一步：从利率、失业保障、定期提款案例验证关联证据，再建立测试题与检索基线。"]
    (output / "review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "data/processed/mineru/pages.json")
    parser.add_argument("--corrections", type=Path, default=ROOT / "data/processed/mineru/corrections.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/knowledge")
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--overlap", type=int, default=120)
    args = parser.parse_args()
    main(args.source, args.corrections, args.output, args.max_chars, args.overlap)
