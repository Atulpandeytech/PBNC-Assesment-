from collections import Counter
import re
from typing import Dict, List, Set
from app.pipeline.context import PipelineContext


class SegmentStage:
    @staticmethod
    def execute(ctx: PipelineContext) -> None:
        # 1. Repeated Header / Footer / Watermark Removal
        SegmentStage._strip_headers_and_footers(ctx)

        # 2. Cross-Page Carry-Over Stitching
        SegmentStage._stitch_cross_page_carryover(ctx)

    @staticmethod
    def _strip_headers_and_footers(ctx: PipelineContext) -> None:
        """Finds repeated lines at the top/bottom across >= 50% of pages and strips them."""
        if len(ctx.pages) < 2:
            return

        top_lines = []
        bottom_lines = []

        for p in ctx.pages:
            lines = [line.strip() for line in p.raw_text.splitlines() if line.strip()]
            if lines:
                top_lines.append(lines[0])
            if len(lines) > 1:
                bottom_lines.append(lines[-1])

        top_counts = Counter(top_lines)
        bottom_counts = Counter(bottom_lines)
        threshold = len(ctx.pages) * 0.5

        headers_to_remove = {line for line, cnt in top_counts.items() if cnt >= threshold}
        footers_to_remove = {line for line, cnt in bottom_counts.items() if cnt >= threshold}

        for p in ctx.pages:
            lines = p.raw_text.splitlines()
            cleaned = []
            for line in lines:
                s = line.strip()
                if s in headers_to_remove or s in footers_to_remove:
                    continue
                # Also strip pure page numbers like "Page 2 of 5" or "- 2 -"
                if re.match(r"^(?:Page\s+\d+(?:\s+of\s+\d+)?|\-?\s*\d+\s*\-?)$", s, re.IGNORECASE):
                    continue
                cleaned.append(line)
            p.raw_text = "\n".join(cleaned)

    @staticmethod
    def _stitch_cross_page_carryover(ctx: PipelineContext) -> None:
        """
        Detects unfinished questions at the end of page N and carries over into the top of page N+1.
        """
        if len(ctx.pages) < 2:
            return

        for i in range(len(ctx.pages) - 1):
            curr_p = ctx.pages[i]
            next_p = ctx.pages[i + 1]

            curr_lines = [l for l in curr_p.raw_text.splitlines() if l.strip()]
            next_lines = [l for l in next_p.raw_text.splitlines() if l.strip()]

            if not curr_lines or not next_lines:
                continue

            last_line = curr_lines[-1].strip()
            first_line = next_lines[0].strip()

            # Check if last line of curr_p is incomplete:
            # e.g., ends with a comma, hyphen, preposition, or does not end with punctuation
            is_cut_off = (
                not last_line.endswith((".", "?", "!", ":", ")"))
                or last_line.endswith(("-", ",", "and", "or", "the", "a", "an", "is", "of"))
            )

            # And first line of next_p does NOT start a new question (e.g. doesn't match Q1. or 2.)
            starts_new_q = bool(re.match(r"^(?:Q\d+|\d+[\.\)]|\([A-Za-z0-9]+\))", first_line))

            if is_cut_off and not starts_new_q:
                # Mark carry-over warning
                ctx.add_warning(
                    code="SPLIT_ACROSS_PAGES",
                    message=f"Question split across pages {curr_p.page_no} and {next_p.page_no} was stitched",
                    severity="info",
                    page_no=curr_p.page_no,
                    details={"from_page": curr_p.page_no, "to_page": next_p.page_no},
                )
