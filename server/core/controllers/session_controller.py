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
        self, request: SessionConnectRequest, session_id: str | None = None
    ) -> SessionConnectResponse:
        """Create a new interview session.

        Args:
            request: Session creation payload.
            session_id: Key to store the session under. Defaults to a new UUID;
                the bot passes a fixed key since it serves one session.

        Returns:
            SessionConnectResponse with session details.
        """
        logger.info("Executing SessionController.create_session")

        session_id = session_id or str(uuid.uuid4())
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

    async def process_answer(self, session_id: str, answer_text: str) -> dict:
        """Process a candidate's answer through TypeSafe judgment.

        The answer is always attributed to the question the flow service has in
        play, so the caller never has to track question identity.

        Args:
            session_id: The session identifier.
            answer_text: The candidate's transcribed answer.

        Returns:
            Dict with the next action and whether the session is complete.

        Raises:
            ValueError: If the session has no question in play.
        """
        logger.info(f"Executing SessionController.process_answer for session {session_id}")

        flow_service = self._sessions.get(session_id)
        if not flow_service:
            raise ValueError(f"Session {session_id} not found")

        # The question in play is ours to know, not the LLM's to remember. It
        # used to have to echo back the exact question_id; a stale one raised
        # and the LLM's recovery was to re-ask the question verbatim.
        current_question = flow_service.current_question
        if not current_question:
            raise ValueError("No question is currently in play")

        # Only a genuinely empty transcript means we heard nothing. A short
        # answer is still an answer — "I don't know" is a real response and
        # belongs in front of the judge, not treated as a dropped mic.
        if not answer_text.strip():
            logger.warning(f"Empty transcript for {current_question.id}; re-prompting")
            action = flow_service.record_not_heard()
        else:
            judgment = await judge_answer(
                question=current_question.text,
                answer=answer_text,
                key_points=current_question.key_points,
            )
            action = flow_service.process_answer(
                question_id=current_question.id,
                answer_text=answer_text,
                judgment=judgment,
            )

        return {
            "action": action,
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
