"""TypeSafe judgment service for answer quality scoring.

Uses TypeSafe's Jev model to judge whether a candidate's answer is complete
enough to move on, or thin enough to deserve a follow-up question.
"""

from loguru import logger
from typesafe_sdk import AsyncTypeSafeClient, Noul, Score

from core.schemas.interview import AnswerJudgment


async def judge_answer(
    question: str,
    answer: str,
    key_points: list[str],
) -> AnswerJudgment:
    """Judge whether a candidate's answer is complete enough to move on.

    Sends the question and answer to TypeSafe Jev for semantic evaluation.
    Code owns the decision from there: the interview flow service reads the
    typed judgment and decides follow-up vs next question.

    Args:
        question: The interview question that was asked.
        answer: The candidate's spoken answer (transcribed text).
        key_points: Key points a strong answer should cover.

    Returns:
        AnswerJudgment with completeness flag, confidence, and optional follow-up.

    Raises:
        RuntimeError: If the TypeSafe API call fails after retries.
    """
    logger.info("Executing judge_answer with TypeSafe")

    state = {
        "question": question,
        "answer": answer,
        "key_points": key_points,
    }

    key_points_text = "; ".join(key_points[:4])

    try:
        async with AsyncTypeSafeClient() as client:
            response = await client.system_one(
                state=state,
                questions={
                    "is_complete": Noul(
                        instructions=(
                            "Does the candidate's answer address the core of the question "
                            "and cover the key technical or behavioral points? "
                            "A complete answer demonstrates understanding, not just recitation. "
                            "Key points to check: " + key_points_text
                        ),
                    ),
                    "confidence": Score(
                        instructions=(
                            "How confident are you in this completeness judgment? "
                            "Consider whether the answer is clearly sufficient, clearly insufficient, "
                            "or ambiguous."
                        ),
                        criteria=[
                            "Very uncertain",
                            "Somewhat uncertain",
                            "Moderately confident",
                            "Confident",
                            "Very confident",
                        ],
                    ),
                },
            )

            noul_answer = response.nouls["is_complete"]
            score_answer = response.scores["confidence"]

            is_complete = noul_answer.noul >= 0.5
            confidence = score_answer.confidence

            suggested_follow_up = ""
            if not is_complete:
                suggested_follow_up = (
                    "Can you elaborate on that? "
                    "I'd like to hear more about the specific mechanisms or reasoning."
                )

            logger.info(
                f"TypeSafe judgment: is_complete={is_complete}, "
                f"confidence={confidence:.2f}"
            )

            return AnswerJudgment(
                is_complete=is_complete,
                confidence=confidence,
                suggested_follow_up=suggested_follow_up,
            )
    except Exception as error:
        logger.error(f"TypeSafe judgment failed: {error}")
        return AnswerJudgment(
            is_complete=True,
            confidence=0.5,
            suggested_follow_up="",
        )
