import pytest
from app.providers.llm_rule_based import RuleBasedExtractionProvider


@pytest.mark.asyncio
async def test_question_numbering_formats():
    provider = RuleBasedExtractionProvider()

    sample_text = """
    Q1. What is the capital of India?
    (A) Mumbai
    (B) New Delhi
    (C) Kolkata
    (D) Chennai

    2. Which planet is known as the Red Planet?
    A. Venus
    B. Mars
    C. Jupiter
    D. Saturn

    (3) What is the chemical symbol for water?
    (a) H2O
    (b) CO2
    (c) NaCl
    (d) O2

    4) The boiling point of water at sea level is:
    1) 50 C
    2) 100 C
    3) 150 C
    4) 200 C

    Question 5: What is the speed of light?
    (A) 3x10^8 m/s
    (B) 3x10^6 m/s
    """

    questions = await provider.structure_questions(sample_text, [1])

    assert len(questions) == 5
    assert questions[0]["question_number"] == "1"
    assert "capital of India" in questions[0]["question_text"]
    assert len(questions[0]["options"]) == 4

    assert questions[1]["question_number"] == "2"
    assert "Red Planet" in questions[1]["question_text"]

    assert questions[2]["question_number"] == "3"
    assert questions[3]["question_number"] == "4"
    assert questions[4]["question_number"] == "5"


@pytest.mark.asyncio
async def test_roman_numerals():
    provider = RuleBasedExtractionProvider()
    text = """
    (i) Define Newton's First Law of Motion.
    (ii) State the law of conservation of momentum.
    """
    questions = await provider.structure_questions(text, [1])
    assert len(questions) == 2
    assert questions[0]["question_number"] == "i"
    assert questions[1]["question_number"] == "ii"
