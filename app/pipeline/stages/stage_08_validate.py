import re
from typing import Any, Dict, List
from app.core.config import settings
from app.pipeline.context import PipelineContext


class ValidateStage:
    @staticmethod
    def execute(ctx: PipelineContext) -> None:
        # Build page lookup maps
        page_quality_map = {p.page_no: p.quality_score for p in ctx.pages}
        page_ocr_conf_map = {p.page_no: p.ocr_mean_confidence for p in ctx.pages}

        for q in ctx.final_questions:
            q_pages = q.get("source_pages", [1])
            first_page = q_pages[0] if q_pages else 1

            # 1. OCR Mean Confidence Signal (0.25)
            avg_ocr_conf = sum(page_ocr_conf_map.get(p, 0.95) for p in q_pages) / len(q_pages)

            # 2. Page Quality Score Signal (0.15)
            avg_quality = sum(page_quality_map.get(p, 0.90) for p in q_pages) / len(q_pages)

            # 3. Numbering Continuity Signal (0.15)
            q_num = q.get("question_number")
            if q_num and q_num.isdigit():
                num_score = 1.0
            elif q_num:
                num_score = 0.8
            else:
                num_score = 0.4
                ctx.add_warning(
                    code="MISSING_QUESTION_NUMBER",
                    message="Question has no detectable question number",
                    severity="warning",
                    question_id=q.get("id"),
                )

            # 4. Option Completeness Signal (0.15)
            options = q.get("options", [])
            q_type = q.get("question_type", "unknown")
            if q_type in ("mcq_single", "mcq_multi"):
                if len(options) >= 4:
                    opt_score = 1.0
                elif len(options) >= 2:
                    opt_score = 0.75
                    ctx.add_warning(
                        code="INCOMPLETE_OPTIONS",
                        message=f"Question {q_num} has only {len(options)} options",
                        severity="warning",
                        question_id=q.get("id"),
                        details={"option_count": len(options)},
                    )
                else:
                    opt_score = 0.3
                    ctx.add_warning(
                        code="INCOMPLETE_OPTIONS",
                        message=f"MCQ Question {q_num} has fewer than 2 options",
                        severity="error",
                        question_id=q.get("id"),
                        details={"option_count": len(options)},
                    )
            else:
                opt_score = 1.0

            # 5. Answer Match Certainty Signal (0.15)
            match_status = q.get("answer_match_status", "not_found")
            if match_status == "matched":
                ans_score = 1.0
            elif match_status == "ambiguous":
                ans_score = 0.5
                ctx.add_warning(
                    code="ANSWER_AMBIGUOUS",
                    message=f"Answer for Question {q_num} is ambiguous",
                    severity="warning",
                    question_id=q.get("id"),
                )
            else:
                ans_score = 0.7  # Question may validly have no answer key attached yet

            # 6. Text Sanity & Garbled Character Ratio (0.15)
            q_text = q.get("question_text", "")
            if not q_text:
                sanity_score = 0.2
            else:
                clean_chars = len(re.findall(r"[A-Za-z0-9\s\.,\?\!\-\(\)]", q_text))
                total_chars = max(1, len(q_text))
                ratio = clean_chars / total_chars
                if ratio < 0.80:
                    sanity_score = 0.4
                    ctx.add_warning(
                        code="LOW_OCR_CONFIDENCE",
                        message=f"Garbled text detected in Question {q_num} (clean char ratio {ratio:.2f})",
                        severity="warning",
                        question_id=q.get("id"),
                        details={"clean_ratio": ratio},
                    )
                else:
                    sanity_score = min(1.0, ratio)

            # Weighted sum
            overall_conf = (
                0.25 * avg_ocr_conf
                + 0.15 * avg_quality
                + 0.15 * num_score
                + 0.15 * opt_score
                + 0.15 * ans_score
                + 0.15 * sanity_score
            )
            overall_conf = round(max(0.1, min(1.0, overall_conf)), 3)

            q["confidence"] = overall_conf
            q["confidence_breakdown"] = {
                "ocr_confidence": round(avg_ocr_conf, 3),
                "page_quality": round(avg_quality, 3),
                "numbering_continuity": round(num_score, 3),
                "option_completeness": round(opt_score, 3),
                "answer_certainty": round(ans_score, 3),
                "text_sanity": round(sanity_score, 3),
            }

            # Classify status
            if overall_conf >= settings.CONFIDENCE_THRESHOLD_HIGH:
                q["extraction_status"] = "success"
            elif overall_conf >= settings.CONFIDENCE_THRESHOLD_LOW:
                q["extraction_status"] = "partial"
            else:
                q["extraction_status"] = "needs_review"
