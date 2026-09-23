"""Interview flow service for question selection and session management.

Manages the interview state: which question to ask next, whether to follow up,
and when to end the session. Reads TypeSafe judgments to make decisions.
"""

from loguru import logger

from core.data.questions import (
    ALL_QUESTIONS,
    InterviewQuestion,
    get_behavioral_questions,
    get_technical_questions,
)
from core.schemas.interview import AnswerJudgment


class InterviewFlowService:
    """Manages interview flow: question selection, follow-up decisions, feedback.

    Args:
        question_count: Number of questions to ask in the session.
    """

    def __init__(self, question_count: int = 5) -> None:
        """Initialize the interview flow service.

        Args:
            question_count: Total questions to ask in this session.
        """
        logger.info("Executing InterviewFlowService.__init__")
        self._question_count = min(question_count, len(ALL_QUESTIONS))
        self._questions_asked: list[str] = []
        self._answers: list[dict] = []
        self._current_question: InterviewQuestion | None = None
        self._current_answered = False
        self._follow_up_count = 0
        self._max_follow_ups = 1

    @property
    def current_question(self) -> InterviewQuestion | None:
        """The question currently in play, if any.

        Returns:
            The InterviewQuestion awaiting an answer, or None before the first.
        """
        return self._current_question

    def get_next_question(self) -> InterviewQuestion:
        """Select the next question to ask, mixing technical and behavioral.

        Idempotent until the current question is answered: repeat calls return
        the question already in play rather than advancing. The LLM calls this
        more than once per turn (Groq retries malformed tool args), and without
        this guard each stray call burned a question and desynced
        `_current_question` from the one the candidate actually heard.

        Returns:
            The next InterviewQuestion to present to the candidate.

        Raises:
            RuntimeError: If no more questions are available.
        """
        logger.info("Executing InterviewFlowService.get_next_question")

        if self._current_question and not self._current_answered:
            logger.info(f"Re-returning unanswered question {self._current_question.id}")
            return self._current_question

        remaining = [
            q for q in ALL_QUESTIONS if q.id not in self._questions_asked
        ]

        if not remaining:
            raise RuntimeError("No more questions available")

        tech_remaining = [q for q in remaining if q.category == "technical"]
        behav_remaining = [q for q in remaining if q.category == "behavioral"]

        asked_tech = sum(
            1 for qid in self._questions_asked
            if any(t.id == qid for t in get_technical_questions())
        )
        asked_behav = sum(
            1 for qid in self._questions_asked
            if any(b.id == qid for b in get_behavioral_questions())
        )

        if asked_tech <= asked_behav and tech_remaining:
            question = tech_remaining[0]
        elif behav_remaining:
            question = behav_remaining[0]
        else:
            question = remaining[0]

        self._current_question = question
        self._current_answered = False
        self._questions_asked.append(question.id)
        self._follow_up_count = 0

        logger.info(
            f"Selected question {question.id} ({question.category}), "
            f"{len(self._questions_asked)}/{self._question_count}"
        )
        return question

    def record_not_heard(self) -> dict:
        """Handle a turn that carried no usable speech.

        Re-prompts without scoring: the candidate said nothing we could judge,
        so the question stays in play and its follow-up budget is untouched.

        Returns:
            An action dict in the same shape process_answer returns.
        """
        logger.warning("Executing InterviewFlowService.record_not_heard")
        return {
            "should_follow_up": True,
            "follow_up_text": "I didn't catch that — could you say that again?",
            "score": None,
            "not_heard": True,
        }

    def process_answer(
        self, question_id: str, answer_text: str, judgment: AnswerJudgment
    ) -> dict:
        """Process a candidate's answer and the TypeSafe judgment.

        Decides whether to follow up or move to the next question.
        Code owns the decision; TypeSafe only supplies the structured judgment.

        Args:
            question_id: The question that was answered.
            answer_text: The candidate's transcribed answer.
            judgment: TypeSafe judgment on answer completeness.

        Returns:
            Dict with keys: should_follow_up (bool), follow_up_text (str),
            score (float).
        """
        logger.info("Executing InterviewFlowService.process_answer")

        # Judgment unavailable: move on so the interview isn't stuck, but keep
        # the turn out of scoring so the final feedback reflects what was
        # actually assessed instead of inventing a perfect score.
        if not judgment.judged:
            logger.warning(f"Unscored answer for {question_id}: judgment unavailable")
            self._current_answered = True
            return {
                "should_follow_up": False,
                "follow_up_text": "",
                "score": None,
                "not_heard": False,
            }

        score = 1.0 if judgment.is_complete else 0.3

        self._answers.append({
            "question_id": question_id,
            "answer": answer_text,
            "is_complete": judgment.is_complete,
            "confidence": judgment.confidence,
            "score": score,
        })

        should_follow_up = (
            not judgment.is_complete
            and self._follow_up_count < self._max_follow_ups
        )

        # Answered either way: a follow-up digs into the same question, but the
        # candidate has spoken, so the next get_next_question must advance.
        self._current_answered = True

        if should_follow_up:
            self._follow_up_count += 1
            follow_up = judgment.suggested_follow_up or (
                "Can you go deeper on that? "
                "Walk me through the specific mechanics."
            )
            logger.info(f"Follow-up on {question_id}: confidence={judgment.confidence:.2f}")
            return {
                "should_follow_up": True,
                "follow_up_text": follow_up,
                "score": score,
                "not_heard": False,
            }

        logger.info(
            f"Moving past {question_id}: is_complete={judgment.is_complete}, "
            f"score={score}"
        )
        return {
            "should_follow_up": False,
            "follow_up_text": "",
            "score": score,
            "not_heard": False,
        }

    def is_session_complete(self) -> bool:
        """Check whether all questions have been asked.

        Returns:
            True if the session is done, False otherwise.
        """
        return len(self._questions_asked) >= self._question_count

    def get_session_summary(self) -> dict:
        """Generate end-of-session summary with feedback.

        Returns:
            Dict with question_count, average_score, strengths, areas_to_improve.
        """
        logger.info("Executing InterviewFlowService.get_session_summary")

        if not self._answers:
            return {
                "question_count": 0,
                "average_score": 0.0,
                "strengths": [],
                "areas_to_improve": [],
            }

        avg_score = sum(a["score"] for a in self._answers) / len(self._answers)
        complete_count = sum(1 for a in self._answers if a["is_complete"])

        strengths = []
        areas = []

        if complete_count == len(self._answers):
            strengths.append("Consistently thorough answers across all questions")
        elif complete_count > len(self._answers) / 2:
            strengths.append("Strong performance on most questions")
        else:
            areas.append("Answers need more depth and specific examples")

        if any(a["confidence"] > 0.8 for a in self._answers):
            strengths.append("Clear and confident communication")

        if any(a["confidence"] < 0.4 for a in self._answers):
            areas.append("Could benefit from more structured responses")

        return {
            "question_count": len(self._answers),
            "average_score": avg_score,
            "strengths": strengths,
            "areas_to_improve": areas,
        }
