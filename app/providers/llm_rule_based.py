import re
from typing import Any, Dict, List, Optional, Tuple
from app.providers.base import LLMStructuringProvider


class RuleBasedExtractionProvider(LLMStructuringProvider):
    """
    Deterministic rule-based and regex extraction engine.
    Extracts question boundaries, options, types, and embedded keys across diverse layouts.
    """

    # Comprehensive question numbering regexes
    QUESTION_START_PATTERNS = [
        # Q1. / Q.1 / Q1: / Question 1: / Question 1.
        re.compile(r"^(?:Q(?:uestion)?[\.\s]*(\d+))\s*[\.\:\-\)]\s*(.*)", re.IGNORECASE),
        # 1. / 2. / 10.
        re.compile(r"^(\d+)\s*[\.]\s+(.*)"),
        # (1) / (2) / (10)
        re.compile(r"^\((\d+)\)\s*(.*)"),
        # 1) / 2) / 10)
        re.compile(r"^(\d+)\s*\)\s*(.*)"),
        # Roman numerals: (i) / (ii) / (iv) / i. / ii.
        re.compile(r"^\(([ivxlcdm]+)\)\s*(.*)", re.IGNORECASE),
        re.compile(r"^([ivxlcdm]+)\s*[\.\)]\s+(.*)", re.IGNORECASE),
    ]

    # Option patterns (A-D, a-d, 1-4)
    OPTION_LINE_PATTERNS = [
        # (A) text, (B) text, (1) text
        re.compile(r"^\(([A-Da-d1-4])\)\s*(.*)"),
        # A. text, B. text, a. text
        re.compile(r"^([A-Da-d])\s*[\.\)]\s+(.*)"),
        # A) text, B) text, a) text
        re.compile(r"^([A-Da-d])\s*\)\s*(.*)"),
        # 1) text, 2) text, 3) text, 4) text
        re.compile(r"^([1-4])\s*\)\s+(.*)"),
    ]

    # Inline options pattern: (A) ... (B) ... (C) ... (D) ...
    INLINE_OPTIONS_PATTERN = re.compile(
        r"\(?([A-Da-d1-4])\)[\.\s]+([^(\n]+?)(?=\s*\(?[B-Db-d2-4]\)|\s*$)"
    )

    async def structure_questions(
        self,
        raw_text: str,
        page_numbers: List[int],
        images: Optional[List[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Parses text into structured questions using regex heuristics."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if not lines:
            return []

        body_lines, _ = self._separate_answer_key_section(lines)

        questions: List[Dict[str, Any]] = []
        current_q: Optional[Dict[str, Any]] = None

        seq_index = 1
        for line in body_lines:
            # If current question is active, check if line is an expected option
            if current_q is not None:
                # 1. Inline options (e.g. (A) x (B) y)
                inline_opts = self._extract_inline_options(line)
                if len(inline_opts) >= 2:
                    for lbl, txt in inline_opts:
                        current_q["options"].append({
                            "label": lbl.upper(),
                            "text": txt.strip(),
                            "asset_ids": [],
                        })
                    continue

                # 2. Check if line matches sequential option
                if self._is_option_for_current_q(line, current_q):
                    opt_match = self._match_option(line)
                    if opt_match:
                        opt_label, opt_text = opt_match
                        current_q["options"].append({
                            "label": opt_label.upper(),
                            "text": opt_text.strip(),
                            "asset_ids": [],
                        })
                        continue

            # Check if this line starts a NEW question
            q_match = self._match_question_start(line)
            if q_match:
                if current_q:
                    self._finalize_question(current_q)
                    questions.append(current_q)

                current_q = self._create_question(q_match[0], q_match[1], seq_index, page_numbers)
                seq_index += 1
                continue

            if current_q is not None:
                # Append continuation lines
                if current_q["options"]:
                    current_q["options"][-1]["text"] += " " + line
                else:
                    current_q["raw_lines"].append(line)
                    if current_q["question_text"]:
                        current_q["question_text"] += " " + line
                    else:
                        current_q["question_text"] = line

        if current_q:
            self._finalize_question(current_q)
            questions.append(current_q)

        return questions

    def _is_option_for_current_q(self, line: str, current_q: Dict[str, Any]) -> bool:
        opt = self._match_option(line)
        if not opt:
            return False
        lbl = opt[0].upper()
        existing = [o["label"].upper() for o in current_q.get("options", [])]

        if not existing:
            # First option should be A or a or 1
            return lbl in ("A", "1")

        last = existing[-1]
        progression = {
            "A": "B", "B": "C", "C": "D", "D": "E",
            "1": "2", "2": "3", "3": "4", "4": "5",
        }
        return lbl == progression.get(last, "")

    def _create_question(self, q_num: str, q_text: str, seq_index: int, page_numbers: List[int]) -> Dict[str, Any]:
        q = {
            "question_number": str(q_num),
            "sequence_index": seq_index,
            "question_text": q_text,
            "raw_lines": [q_text] if q_text else [],
            "options": [],
            "question_type": "unknown",
            "source_pages": page_numbers,
            "source_bbox": None,
            "assets": [],
            "confidence": 0.90,
        }
        inline_opts = self._extract_inline_options(q_text)
        if len(inline_opts) >= 2:
            clean_text = self.INLINE_OPTIONS_PATTERN.split(q_text)[0].strip()
            q["question_text"] = clean_text
            for lbl, txt in inline_opts:
                q["options"].append({
                    "label": lbl.upper(),
                    "text": txt.strip(),
                    "asset_ids": [],
                })
        return q

    def _match_question_start(self, line: str) -> Optional[Tuple[str, str]]:
        if re.match(r"^(?:SECTION|PART|GROUP|UNIT)\s+[A-Z0-9]+", line, re.IGNORECASE):
            return None
        if re.match(r"^(?:ANSWER\s+KEY|ANSWERS|SOLUTIONS)", line, re.IGNORECASE):
            return None

        for pattern in self.QUESTION_START_PATTERNS:
            m = pattern.match(line)
            if m:
                q_num = m.group(1).strip()
                q_text = m.group(2).strip()
                return q_num, q_text
        return None

    def _match_option(self, line: str) -> Optional[Tuple[str, str]]:
        for pattern in self.OPTION_LINE_PATTERNS:
            m = pattern.match(line)
            if m:
                return m.group(1), m.group(2)
        return None

    def _extract_inline_options(self, line: str) -> List[Tuple[str, str]]:
        results = []
        matches = list(self.INLINE_OPTIONS_PATTERN.finditer(line))
        if len(matches) >= 2:
            for m in matches:
                results.append((m.group(1), m.group(2).strip()))
        return results

    def _separate_answer_key_section(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        body = []
        key_lines = []
        is_key = False
        for line in lines:
            if re.match(r"^(?:ANSWER\s+KEY|ANSWERS|SOLUTIONS)\b", line, re.IGNORECASE):
                is_key = True
                key_lines.append(line)
                continue

            if is_key:
                # If we encounter a question start or examination header, transition back to questions
                if (
                    re.match(r"^(?:EXAMINATION\s+QUESTIONS|QUESTIONS|PART\s+[A-Z0-9]+|SECTION\s+[A-Z0-9]+)\b", line, re.IGNORECASE)
                    or self._match_question_start(line) is not None
                ):
                    is_key = False
                    body.append(line)
                else:
                    key_lines.append(line)
            else:
                body.append(line)
        return body, key_lines

    def _finalize_question(self, q: Dict[str, Any]) -> None:
        q_text = q["question_text"]
        options = q["options"]

        if len(options) >= 2:
            if re.search(r"\b(?:select all|multiple correct|choose all)\b", q_text, re.IGNORECASE):
                q["question_type"] = "mcq_multi"
            else:
                q["question_type"] = "mcq_single"
        elif re.search(r"\b(?:true\s+or\s+false|state\s+whether\s+true)\b", q_text, re.IGNORECASE):
            q["question_type"] = "true_false"
        elif re.search(r"(?:_{3,}|\bfill\s+in\s+the\s+blank)", q_text, re.IGNORECASE):
            q["question_type"] = "fill_blank"
        elif re.search(r"\b(?:match\s+the\s+following|column\s+[ab])\b", q_text, re.IGNORECASE):
            q["question_type"] = "match"
        elif re.search(r"\b(?:calculate|find\s+the\s+value\s+of|evaluate)\b", q_text, re.IGNORECASE):
            q["question_type"] = "numerical"
        elif len(q_text) > 150:
            q["question_type"] = "long_answer"
        elif q_text:
            q["question_type"] = "short_answer"
        else:
            q["question_type"] = "unknown"

        seen_labels = set()
        clean_opts = []
        for opt in options:
            lbl = opt["label"]
            if lbl not in seen_labels:
                seen_labels.add(lbl)
                clean_opts.append(opt)
        q["options"] = clean_opts
