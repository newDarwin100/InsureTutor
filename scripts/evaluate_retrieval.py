"""Validate references or score real ranked retrieval output; never invent rankings."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evaluation.scoring import score_case, validate_cases


def main(results_path, output):
    cases = json.loads((ROOT / "evaluation/questions.json").read_text(encoding="utf-8"))["cases"]
    chunks = {c["chunk_id"]: c for c in json.loads((ROOT / "data/processed/knowledge/chunks.json").read_text(encoding="utf-8"))}
    evidence = {e["evidence_id"]: e for e in json.loads((ROOT / "data/processed/knowledge/evidence.json").read_text(encoding="utf-8"))}
    validate_cases(cases, evidence)
    if results_path is None:
        print(f"Validated {len(cases)} reference cases; no retrieval or model evaluation performed.")
        return
    inputs = json.loads(results_path.read_text(encoding="utf-8"))
    if not isinstance(inputs, list):
        raise ValueError("Results must be a list of case_id / ranked_chunk_ids records")
    known = {c["case_id"]: c for c in cases}
    seen, rows = set(), []
    for record in inputs:
        cid = record["case_id"]
        if cid in seen or cid not in known:
            raise ValueError("Duplicate or unknown result case ID")
        seen.add(cid)
        rows.append(score_case(known[cid], record["ranked_chunk_ids"], chunks, evidence))
    measured = [r for r in rows if r["recall_at_k"] is not None]
    report = {"source_results": str(results_path), "measured_cases": len(rows),
              "missing_case_ids": sorted(set(known) - seen),
              "retrieval_case_count": len(measured),
              "mean_recall_at_5": sum(r["recall_at_k"] for r in measured)/len(measured) if measured else None,
              "mean_coverage_after_link_expansion": sum(r["coverage_after_link_expansion"] for r in measured)/len(measured) if measured else None,
              "cases": rows, "limitations": "No answers, citation support, timings or model quality were evaluated."}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Scored {len(rows)} provided rankings; report: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, help="Rankings produced by an actual retriever")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/results/retrieval.json")
    args = parser.parse_args()
    main(args.results, args.output)
