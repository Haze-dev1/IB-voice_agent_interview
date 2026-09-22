"""Session route for the interview coach API.

Thin HTTP layer: request parsing, response wrapping, route-level error handling.
Business logic lives in the controller.
"""

from fastapi import APIRouter, HTTPException, status

from core.controllers.session_controller import SessionController
from core.schemas.interview import (
    SessionConnectRequest,
    SessionConnectResponse,
)

session_router = APIRouter()

_session_controller = SessionController()


@session_router.post(
    "/v1/sessions/connect",
    status_code=status.HTTP_201_CREATED,
    response_model=SessionConnectResponse,
)
async def create_session(request: SessionConnectRequest) -> SessionConnectResponse:
    """Create a new interview session.

    Starts a mock interview session with the specified number of questions.

    Args:
        request (SessionConnectRequest): Session creation payload.

    Returns:
        SessionConnectResponse: Session details and status.

    Raises:
        HTTPException 500: Internal server error.
    """
    try:
        response = await _session_controller.create_session(request)
        return response
    except HTTPException as httperror:
        raise httperror
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
