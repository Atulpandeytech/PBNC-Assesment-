import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from PIL import Image
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.logging import logger
from app.providers.base import LLMStructuringProvider
from app.providers.llm_rule_based import RuleBasedExtractionProvider

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore


class ExtractedOptionSchema(BaseModel):
    label: str
    text: str


class ExtractedQuestionSchema(BaseModel):
    question_number: Optional[str] = None
    question_text: str
    question_type: str
    options: List[ExtractedOptionSchema] = Field(default_factory=list)


class ExtractedQuestionsDocument(BaseModel):
    questions: List[ExtractedQuestionSchema] = Field(default_factory=list)


class GeminiExtractionProvider(LLMStructuringProvider):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.enabled = settings.LLM_ENABLED and bool(self.api_key) and genai is not None
        self.fallback = RuleBasedExtractionProvider()
        self.client = genai.Client(api_key=self.api_key) if self.enabled else None

    async def structure_questions(
        self,
        raw_text: str,
        page_numbers: List[int],
        images: Optional[List[Image.Image]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.enabled or not self.client:
            logger.info("Gemini LLM disabled or unconfigured; using deterministic rule-based extractor.")
            return await self.fallback.structure_questions(raw_text, page_numbers, images)

        prompt = (
            "You are an expert exam extraction system. Extract all examination/test questions from the provided text.\n"
            "Format the output strictly as a JSON document containing a list of questions with their question_number, "
            "question_text, question_type (mcq_single, mcq_multi, true_false, fill_blank, short_answer, long_answer, match, numerical), "
            "and options (label: A/B/C/D, text: string).\n"
            "Do not include preamble or markdown wrapping outside JSON.\n\n"
            f"DOCUMENT TEXT:\n{raw_text}"
        )

        for attempt in range(1, settings.LLM_MAX_RETRIES + 1):
            try:
                start_time = time.time()
                # Run synchronous client call in threadpool with timeout
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.models.generate_content,
                        model=self.model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ExtractedQuestionsDocument,
                        ),
                    ),
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
                latency = time.time() - start_time
                logger.info(f"Gemini structuring succeeded in {latency:.2f}s (attempt {attempt})")

                parsed: ExtractedQuestionsDocument = response.parsed
                results = []
                for idx, q in enumerate(parsed.questions, start=1):
                    results.append({
                        "question_number": q.question_number or str(idx),
                        "sequence_index": idx,
                        "question_text": q.question_text,
                        "question_type": q.question_type,
                        "options": [{"label": opt.label.upper(), "text": opt.text, "asset_ids": []} for opt in q.options],
                        "source_pages": page_numbers,
                        "source_bbox": None,
                        "assets": [],
                        "confidence": 0.95,
                    })
                return results

            except Exception as e:
                logger.warning(f"Gemini structuring attempt {attempt} failed: {e}")
                if attempt < settings.LLM_MAX_RETRIES:
                    backoff = (2 ** attempt) + 0.5
                    await asyncio.sleep(backoff)
                else:
                    logger.error("Gemini structuring exceeded max retries; falling back to rule-based engine.")
                    fallback_res = await self.fallback.structure_questions(raw_text, page_numbers, images)
                    return fallback_res

        return await self.fallback.structure_questions(raw_text, page_numbers, images)
