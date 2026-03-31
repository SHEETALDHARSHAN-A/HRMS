from types import SimpleNamespace

import pytest

from app.services.coding_service import CodingService


@pytest.mark.asyncio
async def test_build_coding_question_honors_assessment_settings(monkeypatch):
    service = CodingService(db=SimpleNamespace())

    async def _fake_ai_question(**kwargs):
        return {
            "id": "ai_q_1",
            "source": "ai",
            "title": "AI Generated",
            "problem": "Implement graph traversal",
            "constraints": ["Use adjacency list"],
            "hints": ["Try BFS first"],
        }

    monkeypatch.setattr(service, "_generate_ai_question", _fake_ai_question)

    config = SimpleNamespace(
        round_name="Round 2",
        coding_question_mode="ai",
        coding_difficulty="hard",
        coding_languages=["python"],
        provided_coding_question=None,
        coding_test_case_mode="provided",
        coding_test_cases=[
            {
                "id": "tc_1",
                "input": "1 2",
                "expectedOutput": "3",
                "isHidden": False,
                "weight": 1,
            }
        ],
        coding_starter_code={},
        custom_questions=["legacy custom"],
        score_distribution={
            "assessment_settings": {
                "coding_question_count": 3,
                "coding_question_type": "dsa",
                "coding_categories": ["arrays", "graphs"],
                "coding_custom_questions": [
                    "Solve two-sum",
                    "Find first non-repeating character",
                ],
            }
        },
    )

    payload = await service._build_coding_question(config=config)

    assert payload["questionCountConfigured"] == 3
    assert payload["questionType"] == "dsa"
    assert payload["questionCategories"] == ["arrays", "graphs"]
    assert len(payload["questionPool"]) == 3
    assert payload["questionPool"][0]["source"] == "custom"
    assert payload["questionPool"][1]["source"] == "custom"
    assert payload["questionPool"][2]["source"] == "ai"


@pytest.mark.asyncio
async def test_build_mcq_question_honors_count_and_category(monkeypatch):
    service = CodingService(db=SimpleNamespace())

    config = SimpleNamespace(
        round_name="Apti Round",
        mcq_question_mode="provided",
        mcq_difficulty="medium",
        mcq_questions=[
            {
                "id": "q1",
                "question": "2 + 2 = ?",
                "options": ["3", "4", "5", "6"],
                "answer": "4",
            },
            {
                "id": "q2",
                "question": "3 * 3 = ?",
                "options": ["6", "7", "8", "9"],
                "answer": "9",
            },
        ],
        mcq_passing_score=70,
        score_distribution={
            "assessment_settings": {
                "mcq_question_count": 5,
                "mcq_question_type": "aptitude",
                "mcq_categories": ["quant", "logical"],
                "mcq_custom_questions": [],
            }
        },
    )

    payload = await service._build_mcq_question(config=config)

    assert payload["questionCountConfigured"] == 5
    assert payload["questionType"] == "aptitude"
    assert payload["questionCategories"] == ["quant", "logical"]
    assert len(payload["questions"]) == 5
    assert payload["passingScore"] == 70


def test_select_coding_question_payload_from_pool():
    service = CodingService(db=SimpleNamespace())
    payload = {
        "challengeType": "coding",
        "questionCountConfigured": 2,
        "questionType": "dsa",
        "questionCategories": ["arrays"],
        "questionPool": [
            {
                "id": "coding_q_1",
                "title": "Q1",
                "problem": "Problem 1",
                "testCases": [],
            },
            {
                "id": "coding_q_2",
                "title": "Q2",
                "problem": "Problem 2",
                "testCases": [],
            },
        ],
    }

    selected = service._select_coding_question_payload(
        question_payload=payload,
        requested_question_id="coding_q_2",
    )

    assert selected["id"] == "coding_q_2"
    assert selected["selectedQuestionId"] == "coding_q_2"
    assert selected["questionCountConfigured"] == 2
