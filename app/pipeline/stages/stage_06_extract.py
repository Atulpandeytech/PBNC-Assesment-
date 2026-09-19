import re
from typing import Any, Dict, List
from app.core.config import settings
from app.pipeline.context import PipelineContext
from app.providers.llm_gemini import GeminiExtractionProvider
from app.providers.llm_rule_based import RuleBasedExtractionProvider


class ExtractStage:
    @staticmethod
    async def execute(ctx: PipelineContext) -> None:
        # Determine provider
        if settings.LLM_ENABLED and settings.GEMINI_API_KEY:
            provider = GeminiExtractionProvider()
        else:
            provider = RuleBasedExtractionProvider()

        all_questions: List[Dict[str, Any]] = []

        # Extract per page or combined
        combined_text = ""
        for page in ctx.pages:
            combined_text += f"\n--- PAGE {page.page_no} ---\n" + page.raw_text

        page_numbers = [p.page_no for p in ctx.pages]
        questions = await provider.structure_questions(combined_text, page_numbers)

        # Cross-page stitching: if questions span across pages, attribute correct source_pages
        for q in questions:
            q_num = q.get("question_number")

            # Associate assets on same page
            q_assets = []
            for asset in ctx.assets:
                if asset["page"] in q["source_pages"]:
                    q_assets.append({
                        "id": asset["id"],
                        "type": asset["type"],
                        "page": asset["page"],
                        "bbox": asset.get("bbox"),
                        "url": f"/api/v1/storage/{asset['id']}.png"
                    })
            q["assets"] = q_assets

            all_questions.append(q)

        # Check for numbering gaps (e.g. Q1, Q2, Q4 -> missing Q3)
        ExtractStage._check_numbering_continuity(ctx, all_questions)

        ctx.final_questions = all_questions

    @staticmethod
    def _check_numbering_continuity(ctx: PipelineContext, questions: List[Dict[str, Any]]) -> None:
        numeric_q_nums = []
        for q in questions:
            q_num_str = q.get("question_number")
            if q_num_str and q_num_str.isdigit():
                numeric_q_nums.append((int(q_num_str), q))

        if not numeric_q_nums:
            return

        numeric_q_nums.sort(key=lambda x: x[0])
        nums = [x[0] for x in numeric_q_nums]

        # Check for duplicates
        seen = set()
        for num, q in numeric_q_nums:
            if num in seen:
                ctx.add_warning(
                    code="DUPLICATE_QUESTION",
                    message=f"Duplicate question number {num} detected",
                    severity="warning",
                    question_id=q.get("id"),
                    details={"question_number": str(num)},
                )
            seen.add(num)

        # Check for gaps in sequence
        for i in range(len(nums) - 1):
            curr_n, next_n = nums[i], nums[i + 1]
            if next_n - curr_n > 1:
                missing = list(range(curr_n + 1, next_n))
                ctx.add_warning(
                    code="MISSING_QUESTION_NUMBER",
                    message=f"Gap detected in question numbering: missing question(s) {missing}",
                    severity="warning",
                    details={"missing_numbers": missing},
                )
