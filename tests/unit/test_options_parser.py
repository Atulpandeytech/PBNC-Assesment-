import pytest
from app.providers.llm_rule_based import RuleBasedExtractionProvider


@pytest.mark.asyncio
async def test_inline_options():
    provider = RuleBasedExtractionProvider()
    text = """
    1. Select the smallest prime number:
    (A) 0  (B) 1  (C) 2  (D) 3
    """
    questions = await provider.structure_questions(text, [1])
    assert len(questions) == 1
    q = questions[0]
    assert len(q["options"]) == 4
    labels = [opt["label"] for opt in q["options"]]
    assert labels == ["A", "B", "C", "D"]
    assert q["options"][2]["text"] == "2"


@pytest.mark.asyncio
async def test_question_type_inference():
    provider = RuleBasedExtractionProvider()
    text = """
    1. Which element has atomic number 1?
    (A) Helium (B) Hydrogen (C) Lithium (D) Carbon

    2. State whether True or False: Photosynthesis produces oxygen.

    3. The chemical formula for table salt is _______.

    4. Calculate the resistance when voltage is 12V and current is 2A.

    5. Match the following elements with their symbols: Column A and Column B.
    """
    questions = await provider.structure_questions(text, [1])
    assert len(questions) == 5

    assert questions[0]["question_type"] == "mcq_single"
    assert questions[1]["question_type"] == "true_false"
    assert questions[2]["question_type"] == "fill_blank"
    assert questions[3]["question_type"] == "numerical"
    assert questions[4]["question_type"] == "match"
