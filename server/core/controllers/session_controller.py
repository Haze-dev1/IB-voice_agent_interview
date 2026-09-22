"""Session controller for interview session orchestration.

Coordinates the interview flow, manages session state, and bridges
the HTTP layer with the interview services.
"""

import uuid

from loguru import logger

from core.schemas.interview import (
    AnswerJudgment,
    InterviewFeedback,
    SessionConnectRequest,
    SessionConnectResponse,
)
from core.services.interview_flow import InterviewFlowService
from core.services.typesafe_judgment import judge_answer


class SessionController:
    """Orchestrates interview sessions and coordinates services.

    Manages session lifecycle: creation, answer processing, and feedback generation.
    """

    def __init__(self) -> None:
        """Initialize the session controller with empty session store."""
        logger.info("Executing SessionController.__init__")
        self._sessions: dict[str, InterviewFlowService] = {}

    async def create_session(
        self, request: SessionConnectRequest
    ) -> SessionConnectResponse:
        """Create a new interview session.

        Args:
            request: Session creation payload.

        Returns:
            SessionConnectResponse with session details.
        """
        logger.info("Executing SessionController.create_session")

        session_id = str(uuid.uuid4())
        flow_service = InterviewFlowService(question_count=request.question_count)
        self._sessions[session_id] = flow_service

        logger.info(f"Session created: {session_id}")
        return SessionConnectResponse(
            session_id=session_id,
            status="created",
            message="Interview session started. Ready to begin.",
        )

    def get_flow_service(self, session_id: str) -> InterviewFlowService | None:
        """Get the flow service for a session.

        Args:
            session_id: The session identifier.

        Returns:
            InterviewFlowService if session exists, None otherwise.
        """
        return self._sessions.get(session_id)

    async def process_answer(
        self, session_id: str, question_id: str, answer_text: str
    ) -> dict:
        """Process a candidate's answer through TypeSafe judgment.

        Args:
            session_id: The session identifier.
            question_id: The question that was answered.
            answer_text: The candidate's transcribed answer.

        Returns:
            Dict with judgment results and next action.

        Raises:
            ValueError: If session or question is not found.
        """
        logger.info(f"Executing SessionController.process_answer for session {session_id}")

        flow_service = self._sessions.get(session_id)
        if not flow_service:
            raise ValueError(f"Session {session_id} not found")

        current_question = flow_service._current_question
        if not current_question or current_question.id != question_id:
            raise ValueError(f"Question {question_id} is not the current question")

        judgment = await judge_answer(
            question=current_question.text,
            answer=answer_text,
            key_points=current_question.key_points,
        )

        result = flow_service.process_answer(
            question_id=question_id,
            answer_text=answer_text,
            judgment=judgment,
        )

        return {
            "judgment": judgment.model_dump(),
            "action": result,
            "session_complete": flow_service.is_session_complete(),
        }

    def get_feedback(self, session_id: str) -> InterviewFeedback:
        """Generate end-of-session feedback.

        Args:
            session_id: The session identifier.

        Returns:
            InterviewFeedback with summary and areas for improvement.

        Raises:
            ValueError: If session is not found.
        """
        logger.info(f"Executing SessionController.get_feedback for session {session_id}")

        flow_service = self._sessions.get(session_id)
        if not flow_service:
            raise ValueError(f"Session {session_id} not found")

        summary = flow_service.get_session_summary()

        feedback = InterviewFeedback(
            question_count=summary["question_count"],
            average_score=summary["average_score"],
            strengths=summary["strengths"],
            areas_to_improve=summary["areas_to_improve"],
        )

        del self._sessions[session_id]
        logger.info(f"Session {session_id} feedback generated and cleaned up")
        return feedback
