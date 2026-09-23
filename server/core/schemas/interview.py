"""Request and response schemas for the interview coach API.

Thin Pydantic models for wire contracts. Keep business logic in controllers.
"""

from pydantic import BaseModel, Field


class SessionConnectRequest(BaseModel):
    """Request body for starting an interview session.

    Args:
        candidate_name: Optional name for the candidate.
        question_count: Number of questions to ask (default 5).
    """

    candidate_name: str | None = Field(default=None, description="Candidate name for the session")
    question_count: int = Field(default=5, ge=1, le=10, description="Number of questions to ask")


class SessionConnectResponse(BaseModel):
    """Response from the session connect endpoint.

    Args:
        session_id: Unique session identifier.
        status: Session status.
        message: Human-readable status message.
    """

    session_id: str = Field(description="Unique session identifier")
    status: str = Field(description="Session status")
    message: str = Field(description="Human-readable status message")


class AnswerJudgment(BaseModel):
    """Structured judgment on a candidate's answer from TypeSafe.

    Args:
        is_complete: Whether the answer is complete enough to move on.
        confidence: Confidence score (0-1).
        suggested_follow_up: Optional follow-up question if answer is thin.
    """

    is_complete: bool = Field(description="Whether the answer covers enough to move on")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the judgment")
    suggested_follow_up: str = Field(default="", description="Follow-up if answer is thin")
    judged: bool = Field(
        default=True,
        description="False when judgment was unavailable; the other fields are then meaningless",
    )


class InterviewFeedback(BaseModel):
    """End-of-session feedback summary.

    Args:
        question_count: Total questions asked.
        average_score: Average completeness score across answers.
        strengths: List of strengths noted.
        areas_to_improve: List of areas for improvement.
    """

    question_count: int = Field(description="Total questions asked")
    average_score: float = Field(description="Average completeness score (0-1)")
    strengths: list[str] = Field(default_factory=list, description="Noted strengths")
    areas_to_improve: list[str] = Field(default_factory=list, description="Areas to improve")
