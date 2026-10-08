"""Measure retrieved evidence separately from later context expansion."""


def score_case(case, ranked_chunk_ids, chunks, evidence, k=5):
    if len(ranked_chunk_ids) != len(set(ranked_chunk_ids)):
        raise ValueError("Ranked results must not contain duplicate chunk IDs")
    if any(cid not in chunks for cid in ranked_chunk_ids):
        raise ValueError("Ranked results contain unknown chunk IDs")
    selected = [chunks[cid] for cid in ranked_chunk_ids[:k]]
    direct_ids = {eid for chunk in selected for eid in chunk["evidence_ids"]}
    expanded_ids = direct_ids | {eid for chunk in selected for eid in chunk["related_evidence_ids"]}
    if not expanded_ids.issubset(evidence):
        raise ValueError("Chunk links contain unknown evidence IDs")
    groups = case["required_evidence_groups"]
    direct_hits, expanded_hits = [], []
    for group in groups:
        alternatives = set(group["alternative_evidence_ids"])
        if not alternatives.issubset(evidence):
            raise ValueError("Reference case contains unknown evidence IDs")
        if alternatives & direct_ids:
            direct_hits.append(group["group_id"])
        if alternatives & expanded_ids:
            expanded_hits.append(group["group_id"])
    denominator = len(groups)
    return {"case_id": case["case_id"], "top_k": k, "ranked_chunk_ids": ranked_chunk_ids[:k],
            "required_group_count": denominator, "direct_hit_groups": direct_hits,
            "expanded_hit_groups": expanded_hits,
            "recall_at_k": len(direct_hits) / denominator if denominator else None,
            "coverage_after_link_expansion": len(expanded_hits) / denominator if denominator else None,
            "expanded_evidence_ids": sorted(expanded_ids),
            "answer_correctness": None, "citation_accuracy": None,
            "note": "Link expansion only; no parent expansion or generated answer is scored."}


def validate_cases(cases, evidence):
    ids = [c["case_id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate reference case IDs")
    for case in cases:
        if not case["question"].strip() or not case["expected_facts"] or not case["forbidden_claims"]:
            raise ValueError(f"Incomplete reference case: {case['case_id']}")
        group_ids = [g["group_id"] for g in case["required_evidence_groups"]]
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("Duplicate reference evidence groups")
        for group in case["required_evidence_groups"]:
            ids = group["alternative_evidence_ids"]
            if not ids or any(eid not in evidence for eid in ids):
                raise ValueError(f"Invalid evidence group in {case['case_id']}")
            if set(group["pdf_pages"]) != {evidence[eid]["pdf_page"] for eid in ids}:
                raise ValueError(f"Incorrect reference pages in {case['case_id']}")
