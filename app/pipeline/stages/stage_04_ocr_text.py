import pymupdf
from app.pipeline.context import PipelineContext
from app.providers.ocr_native import NativePDFExtractor
from app.providers.ocr_tesseract import TesseractOCRProvider


class OCRTextStage:
    @staticmethod
    async def execute(ctx: PipelineContext) -> None:
        ocr_provider = TesseractOCRProvider()

        doc = None
        if ctx.mime_type == "application/pdf":
            doc = pymupdf.open(ctx.file_path)

        try:
            for page in ctx.pages:
                if page.text_source == "native" and doc is not None:
                    # Native digital PDF extraction
                    raw_text, blocks, assets, conf = NativePDFExtractor.extract_page_content(
                        doc, page.page_no - 1
                    )
                    page.raw_text = raw_text
                    page.blocks = blocks
                    page.ocr_mean_confidence = conf

                    for asset in assets:
                        ctx.assets.append(asset)
                        ctx.add_warning(
                            code="FIGURE_DETECTED",
                            message=f"Embedded figure or diagram detected on page {page.page_no}",
                            severity="info",
                            page_no=page.page_no,
                            details={"asset_id": asset["id"], "type": asset["type"]},
                        )
                else:
                    # Scanned page / Image OCR extraction
                    if page.image is not None:
                        ocr_res = await ocr_provider.extract_page_ocr(page.image)
                        page.raw_text = ocr_res.text
                        page.ocr_mean_confidence = ocr_res.mean_confidence

                        if ocr_res.mean_confidence < 0.70:
                            ctx.add_warning(
                                code="LOW_OCR_CONFIDENCE",
                                message=f"Page {page.page_no} OCR mean confidence is low ({ocr_res.mean_confidence:.2f})",
                                severity="warning",
                                page_no=page.page_no,
                                details={"confidence": ocr_res.mean_confidence},
                            )
        finally:
            if doc is not None:
                doc.close()
