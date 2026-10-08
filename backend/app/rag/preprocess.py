"""Deterministic cleaning and bounded chunking of normalized MinerU blocks."""

import copy
import hashlib
import html
import re

CJK = r"\u3400-\u9fff"


def clean_text(text):
    """Remove layout artifacts, not facts. Unknown controls remain visible for review."""
    text = html.unescape(re.sub(r"</?[^>]+>", "", text))
    text = text.replace("\r\n", "\n")
    text = re.sub(r"([A-Za-z])-\n([a-z])", r"\1\2", text)
    text = re.sub(r"(?<=\d)\n(?=\d)", "", text)
    text = re.sub(rf"([{CJK}])\n(?=[{CJK}])", r"\1", text)
    text = re.sub(r"\n", " ", text)
    text = re.sub(rf"([{CJK}]) +(?=[{CJK}])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def lang(text):
    chinese = bool(re.search(rf"[{CJK}]", text))
    english = bool(re.search(r"[A-Za-z]{3,}", text))
    return "mixed" if chinese and english else "zh" if chinese else "en" if english else "und"


def expand_table(rows):
    """Carry rowspan/colspan values forward so numeric rows retain their labels."""
    grid, pending = [], {}
    for row in rows:
        cells = {}
        remaining = {}
        for column, (value, count) in pending.items():
            cells[column] = value
            if count > 1:
                remaining[column] = (value, count - 1)
        column = 0
        for cell in row:
            while column in cells:
                column += 1
            value = clean_text(cell["text"])
            for offset in range(cell.get("colspan", 1)):
                target = column + offset
                cells[target] = value
                if cell.get("rowspan", 1) > 1:
                    remaining[target] = (value, cell["rowspan"] - 1)
            column += cell.get("colspan", 1)
        grid.append([cells.get(i, "") for i in range(max(cells, default=-1) + 1)])
        pending = remaining
    return grid


def split_text(text, max_chars=1200, overlap_chars=120):
    """Sentence boundaries first, character fallback only for oversized sentences."""
    if max_chars <= 0 or not 0 <= overlap_chars < max_chars:
        raise ValueError("Require 0 <= overlap_chars < max_chars")
    if len(text) <= max_chars:
        return [text] if text else []
    sentences = re.split(r"(?<=[。！？；])|(?<=[.!?;])\s+", text)
    pieces, current = [], ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            for start in range(0, len(sentence), max_chars - overlap_chars):
                pieces.append(sentence[start:start + max_chars])
            continue
        if len(current) + len(sentence) + 1 > max_chars:
            pieces.append(current)
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = tail if len(tail) + len(sentence) + 1 <= max_chars else ""
        current = (current + " " + sentence).strip()
    if current:
        pieces.append(current)
    return pieces


def get_refs(raw):
    refs = re.findall(r"<(?:sup|eq)>\s*(?:\^\{)?(10|[1-9])(?:\})?\s*</(?:sup|eq)>", raw)
    refs += re.findall(r"\^\{(10|[1-9])\}", raw)
    decoded = html.unescape(re.sub(r"</?[^>]+>", "", raw))
    refs += re.findall(rf"(?<=[{CJK}])(10|[1-9])(?=[。，；\s]|$)", decoded)
    return sorted({int(n) for n in refs})


def build(pages, config, source_sha256, max_chars=1200, overlap_chars=120):
    if config["normalized_source_sha256"] != source_sha256:
        raise ValueError("Normalized input changed: recheck document-specific corrections")
    pages = copy.deepcopy(pages)
    lookup = {b["block_id"]: b for p in pages for b in p["blocks"]}
    changes = []
    for correction in config["text_corrections"]:
        block = lookup[correction["block_id"]]
        old, new = correction["old"], correction["new"]
        if block["text"].count(old) != correction["count"]:
            raise ValueError(f"Correction no longer matches: {block['block_id']}")
        block["text"] = block["text"].replace(old, new)
        changes.append(correction)
    for correction in config["table_corrections"]:
        table = lookup[correction["block_id"]]["tables"][0]
        target = table["rows"][correction["row"]][correction["cell"]]
        if target["text"] != correction["old"]:
            raise ValueError("Table correction no longer matches")
        target["text"] = correction["new"]
        changes.append(correction)

    originals = {b["block_id"]: b for p in config["original_pages"] for b in p["blocks"]}
    evidence, parents, notes, omitted = [], [], {}, []
    parent_map = {}
    last_header = "FLEXI-ULife Prime Saver"
    for page in pages:
        number = page["pdf_page"]
        headers = [clean_text(b["text"]) for b in page["discarded_blocks"]
                   if b["type"] == "header" and re.search(rf"[{CJK}A-Za-z]", b["text"])]
        if headers:
            last_header = " / ".join(headers)
        heading = last_header
        heading_refs = []
        parent_id = f"page-{number:03d}-intro"
        for block in page["blocks"]:
            block_id = block["block_id"]
            original = originals[block_id]
            if block["type"] == "title":
                heading = clean_text(block["text"])
                heading_refs = get_refs(block["text"])
                parent_id = f"section-{block_id}"
                continue
            sources = []
            if block["text"].strip():
                sources.append((block_id, block["text"], original["text"], get_refs(block["text"])))
            for t, table in enumerate(block["tables"]):
                grid = expand_table(table["rows"])
                context = []
                for r, cells in enumerate(grid):
                    unique = list(dict.fromkeys(c for c in cells if c))
                    raw_row = table["rows"][r]
                    if len(raw_row) == 2 and raw_row[1].get("colspan", 1) >= 3:
                        context = []  # New independent item after an age/plan subtable.
                    if len(unique) == 1:
                        context = unique
                    if r == 0:
                        context = unique
                    if r == 0 and block_id in config.get("table_first_row_is_content", []):
                        context = []  # First item is content, not a header for later items.
                    # Stable row pointer; keep source HTML for original citation/review.
                    row_text = " | ".join(unique)
                    prefix = " / ".join(context)
                    raw_cells = " ".join(c["text"] for c in table["rows"][r])
                    sources.append((f"{block_id}-t{t+1}-r{r+1}",
                                    (prefix + "\n" + row_text).strip(),
                                    original["tables"][t]["html"], get_refs(raw_cells)))
            if not sources:
                omitted.append({"block_id": block_id, "reason": "NO_EXTRACTED_TEXT",
                                "type": block["type"]})
            for eid, raw, source_raw, refs in sources:
                text = clean_text(raw)
                note_match = re.match(r"^(10|[1-9])\.\s*", text) if number == 12 else None
                kind = "table_row" if "-t" in eid else "paragraph"
                pid = parent_id
                if kind == "table_row":
                    pid = f"row-{eid}"
                if note_match:
                    kind = "footnote"
                    pid = f"note-{int(note_match[1]):02d}"
                if number == 8 and (text.startswith(("*", "^", "#")) or eid == "p008-b013"):
                    kind = "local_footnote"
                    pid = "page-008-rate-notes"
                flags = []
                if any(ord(c) < 32 and c not in "\n\r\t" for c in text):
                    flags.append("UNRESOLVED_CONTROL_CHARACTER")
                annotation = config["annotations"].get(eid, {})
                flags.extend(annotation.get("flags", []))
                if kind == "table_row" and re.search(r"\d+(?:\.\d+)?%\s*\d+(?:\.\d+)?%", text):
                    flags.append("MERGED_PERCENT_VALUES")
                entry = {"evidence_id": eid, "document_id": "flexi-ulife-prime-saver",
                         "document_name": "FLEXI-ULife Prime Saver.pdf", "pdf_page": number,
                         "bbox": block["bbox"], "source_pointer": block["source_pointer"],
                         "source_block_id": block_id, "source_text": source_raw,
                         "text": text, "section": heading, "parent_id": pid,
                         "kind": kind, "language_hint": lang(text),
                         "footnote_numbers": sorted(set(refs + heading_refs)),
                         "related_evidence_ids": [], "review_flags": sorted(set(flags)),
                         "review_note": annotation.get("note"),
                         "review_status": "NEEDS_REVIEW" if flags else "NOT_FULLY_REVIEWED"}
                evidence.append(entry)
                parent_map.setdefault(pid, []).append(eid)
                if kind == "footnote":
                    notes.setdefault(int(note_match[1]), []).append(eid)

    # MinerU's discarded flag is a layout decision, not proof of irrelevance.
    # Restore explicitly reviewed substantive blocks, appended so old IDs stay stable.
    discarded = {b["block_id"]: b for page in pages for b in page["discarded_blocks"]}
    for eid, reason in config.get("retained_discarded_blocks", {}).items():
        if eid not in discarded or not discarded[eid]["text"].strip():
            raise ValueError("Retained discarded block is missing or empty")
        block = discarded[eid]
        pid = f"restored-{eid}"
        evidence.append({"evidence_id": eid, "document_id": "flexi-ulife-prime-saver",
                         "document_name": "FLEXI-ULife Prime Saver.pdf", "pdf_page": block["pdf_page"],
                         "bbox": block["bbox"], "source_pointer": block["source_pointer"],
                         "source_block_id": eid, "source_text": block["text"],
                         "text": clean_text(block["text"]), "section": reason, "parent_id": pid,
                         "kind": "restored_discarded", "language_hint": lang(block["text"]),
                         "footnote_numbers": [], "related_evidence_ids": [], "review_flags": [],
                         "review_note": reason, "review_status": "SOURCE_RESTORED"})
        parent_map[pid] = [eid]

    by_id = {e["evidence_id"]: e for e in evidence}
    if not set(config["explicit_links"]).issubset(by_id):
        raise ValueError("Explicit link source is absent from evidence")
    for entry in evidence:
        related = set()
        if entry["kind"] != "footnote":
            for n in entry["footnote_numbers"]:
                related.update(notes.get(n, []))
        related.update(config["explicit_links"].get(entry["evidence_id"], []))
        entry["related_evidence_ids"] = sorted(related - {entry["evidence_id"]})
        if not related.issubset(by_id):
            raise ValueError(f"Unknown related evidence: {entry['evidence_id']}")
    for pid, ids in parent_map.items():
        parents.append({"parent_id": pid, "evidence_ids": ids,
                        "pdf_pages": sorted({by_id[e]["pdf_page"] for e in ids})})

    # Only numbered bilingual notes are paired automatically; other pairs stay unconfirmed.
    alignment = [{"clause_group_id": f"note-{n:02d}", "evidence_ids": ids,
                  "status": "PAIRED_BY_NOTE_NUMBER_NOT_SEMANTICALLY_VERIFIED"}
                 for n, ids in sorted(notes.items())]
    chunks = []

    def add_chunk(pid, entries, text):
        related = sorted({eid for e in entries for eid in e["related_evidence_ids"]})
        flags = sorted({flag for e in entries for flag in e["review_flags"]})
        chunks.append({"chunk_id": f"{pid}-c{len(chunks)+1:03d}",
                       "evidence_ids": [e["evidence_id"] for e in entries], "parent_id": pid,
                       "pdf_pages": sorted({e["pdf_page"] for e in entries}),
                       "language_hint": lang(text), "text": text,
                       "retrieval_text": f"{entries[0]['section']}\n{text}",
                       "related_evidence_ids": related, "review_flags": flags})

    for pid, ids in parent_map.items():
        entries, text = [], ""
        for eid in ids:
            entry = by_id[eid]
            value = entry["text"]
            if len(value) > max_chars:
                if entries:
                    add_chunk(pid, entries, text)
                    entries, text = [], ""
                for piece in split_text(value, max_chars, overlap_chars):
                    add_chunk(pid, [entry], piece)
                continue
            if entries and len(text) + len(value) + 1 > max_chars:
                add_chunk(pid, entries, text)
                entries, text = [], ""
            entries.append(entry)
            text = (text + "\n" + value).strip()
        if entries:
            add_chunk(pid, entries, text)
    return {"evidence": evidence, "parents": parents, "chunks": chunks,
            "alignment": alignment, "changes": changes, "omitted_blocks": omitted}


def source_hash(raw_bytes):
    return hashlib.sha256(raw_bytes).hexdigest()
