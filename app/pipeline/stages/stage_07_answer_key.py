import re
from typing import Any, Dict, List, Optional, Tuple
from app.pipeline.context import PipelineContext


class AnswerKeyStage:
    # Regex patterns for various answer key formats
    PAIR_PATTERNS = [
        # Matches: 1-A, 2: C, 3. (D), 5-A,C, 6-42.5, Question 1: (B), Question 1: Option (B), Q1: Option B
        re.compile(r"(?:Q(?:uestion)?\s*)?(\d+)\s*[\-\:\.\)]\s*(?:Option\s*)?\(?([A-Da-d0-9\.]+(?:\s*,\s*[A-Da-d])?)\)?", re.IGNORECASE),
        # (1) A or (1) (A)
        re.compile(r"\((\d+)\)\s*\(?([A-Da-d1-4])\)?"),
    ]

    TABLE_ROW_PATTERN = re.compile(
        r"^(?:\|\s*)?(?:Q(?:uestion)?\s*)?(\d+)\s*\|\s*\(?([A-Da-d1-40-9\.]+)\)?(?:\s*\|)?$"
    )

    @staticmethod
    def execute(ctx: PipelineContext) -> None:
        entries: List[Dict[str, Any]] = []

        # 1. Scan all pages for answer key sections
        for page in ctx.pages:
            page_entries = AnswerKeyStage._extract_entries_from_page(page.raw_text, page.page_no)
            entries.extend(page_entries)

        if not entries:
            # Check if this document itself is purely an answer key document
            if ctx.role_in_group == "answer_key" or "answer" in ctx.original_filename.lower():
                full_text = "\n".join(p.raw_text for p in ctx.pages)
                entries = AnswerKeyStage._extract_entries_from_page(full_text, 1)

        ctx.answer_keys = entries

        # 2. Match with extracted questions
        AnswerKeyStage._match_answers_with_questions(ctx, entries)

    @staticmethod
    def _extract_entries_from_page(text: str, page_no: int) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        lines = text.splitlines()

        # Look for Answer Key indicators or compact pairs
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check table row
            t_match = AnswerKeyStage.TABLE_ROW_PATTERN.match(line_str)
            if t_match:
                q_num, ans = t_match.group(1), t_match.group(2)
                entries.append({
                    "question_number": q_num,
                    "answer": ans.upper().strip(),
                    "source_page": page_no,
                    "confidence": 0.95,
                    "raw_snippet": line_str,
                })
                continue

            # Check compact pairs (e.g. 1-A, 2-C, 3-D)
            for pattern in AnswerKeyStage.PAIR_PATTERNS:
                for match in pattern.finditer(line_str):
                    q_num = match.group(1).strip()
                    ans = match.group(2).strip()
                    # Filter out False positives like dates or page numbers
                    if len(ans) <= 10:
                        entries.append({
                            "question_number": q_num,
                            "answer": ans.upper().replace(" ", ""),
                            "source_page": page_no,
                            "confidence": 0.95,
                            "raw_snippet": match.group(0),
                        })

        # Check two-line sequences: line i is Question X, line i+1 is Option Y / (Y)
        clean_lines = [l.strip() for l in lines if l.strip()]
        for i in range(len(clean_lines) - 1):
            curr_l = clean_lines[i]
            next_l = clean_lines[i + 1]
            q_m = re.match(r"^(?:Question|Q)\s*(\d+)$", curr_l, re.IGNORECASE)
            if q_m:
                ans_m = re.match(r"^\(?([A-Da-d1-4])\)?(?:\s+.*)?$", next_l)
                if ans_m:
                    entries.append({
                        "question_number": q_m.group(1),
                        "answer": ans_m.group(1).upper(),
                        "source_page": page_no,
                        "confidence": 0.95,
                        "raw_snippet": f"{curr_l}: {next_l}",
                    })

        # Deduplicate entries by question_number
        deduped = {}
        for entry in entries:
            deduped[entry["question_number"]] = entry
        return list(deduped.values())

    @staticmethod
    def _match_answers_with_questions(ctx: PipelineContext, entries: List[Dict[str, Any]]) -> None:
        key_map = {e["question_number"]: e for e in entries}
        matched_keys = set()

        for q in ctx.final_questions:
            q_num = q.get("question_number")
            matched_entry = key_map.get(q_num) if q_num else None

            if matched_entry:
                matched_keys.add(q_num)
                ans_str = matched_entry["answer"]
                values = [v.strip() for v in ans_str.split(",") if v.strip()]
                q["answer"] = {
                    "value": values,
                    "raw": matched_entry.get("raw_snippet", ans_str),
                    "source_page": matched_entry.get("source_page"),
                    "match_status": "matched",
                    "confidence": matched_entry.get("confidence", 0.95),
                }
                q["answer_match_status"] = "matched"
                q["answer_source_page"] = matched_entry.get("source_page")
            else:
                q["answer"] = None
                q["answer_match_status"] = "not_found"
                q["answer_source_page"] = None
                ctx.add_warning(
                    code="ANSWER_NOT_FOUND",
                    message=f"No answer key entry found for question {q_num or 'unknown'}",
                    severity="info",
                    question_id=q.get("id"),
                    details={"question_number": q_num},
                )

        # Detect orphan answers (in answer key but no question found)
        orphans = []
        for q_num, entry in key_map.items():
            if q_num not in matched_keys:
                orphans.append(entry)
                ctx.add_warning(
                    code="ORPHAN_ANSWER",
                    message=f"Answer key contains entry for Q{q_num} ('{entry['answer']}') but no matching question exists",
                    severity="warning",
                    details={"question_number": q_num, "answer": entry["answer"]},
                )
        ctx.orphan_answers = orphans
