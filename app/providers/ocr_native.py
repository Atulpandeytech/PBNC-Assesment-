from typing import Any, Dict, List, Tuple
import pymupdf
from PIL import Image
import io


class NativePDFExtractor:
    """Extracts high-fidelity native text, reading order, and embedded visual assets from digital PDFs."""

    @staticmethod
    def extract_page_content(
        doc: pymupdf.Document,
        page_no: int
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], float]:
        """
        Extracts:
        - raw_text (sorted into natural multi-column reading order)
        - text_blocks (with bounding boxes)
        - image_assets (embedded images with bounding boxes and raw bytes)
        - confidence (default 0.98 for digital text)
        """
        page = doc[page_no]
        page_width = page.rect.width
        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)

        # Multi-column layout detection:
        mid = page_width / 2.0
        left_blocks = [b for b in blocks if b[2] <= mid + 20 and b[0] < mid]
        right_blocks = [b for b in blocks if b[0] >= mid - 20 and b[2] > mid]
        spanning_blocks = [b for b in blocks if b[0] < mid - 20 and b[2] > mid + 20]

        is_multi_column = (
            len(left_blocks) >= 2
            and len(right_blocks) >= 2
            and len(spanning_blocks) <= max(1, int(len(blocks) * 0.2))
        )

        if is_multi_column:
            def sort_key(b):
                if b[0] < mid - 20 and b[2] > mid + 20:
                    return (0, b[1], b[0])
                if b[2] <= mid + 20:
                    return (1, b[1], b[0])
                return (2, b[1], b[0])
            sorted_blocks = sorted(blocks, key=sort_key)
        else:
            # Single-column: sort by top-to-bottom position with line tolerance
            sorted_blocks = sorted(blocks, key=lambda b: (round(b[1] / 6) * 6, b[0]))

        full_text_lines = []
        structured_blocks = []

        for b in sorted_blocks:
            x0, y0, x1, y1, text, block_no, block_type = b[:7]
            clean_text = text.strip()
            if clean_text:
                full_text_lines.append(clean_text)
                structured_blocks.append({
                    "bbox": [x0, y0, x1, y1],
                    "text": clean_text,
                    "type": "text" if block_type == 0 else "image",
                })

        raw_text = "\n\n".join(full_text_lines)

        # Extract embedded images on this page
        image_assets: List[Dict[str, Any]] = []
        try:
            image_list = page.get_images(full=True)
            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Try to get image bbox on page
                rects = page.get_image_rects(xref)
                bbox = [rects[0].x0, rects[0].y0, rects[0].x1, rects[0].y1] if rects else None

                image_assets.append({
                    "id": f"page_{page_no + 1}_img_{img_index + 1}",
                    "type": "image",
                    "page": page_no + 1,
                    "bbox": bbox,
                    "ext": image_ext,
                    "bytes": image_bytes,
                })
        except Exception:
            pass

        return raw_text, structured_blocks, image_assets, 0.98
