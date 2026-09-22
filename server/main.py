"""FastAPI application entry point for the interview coach bot.

Hosts the bot behind a FastAPI server following Pipecat's production pattern:
a long-lived host adding/removing sessions passes auto_end=False.

This replaces the bare `main()` call in bot.py with a custom app that
adds the session route alongside Pipecat's transport routes.
"""

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.routes.session import session_router

load_dotenv(override=True)

app = FastAPI(
    title="IB Interview Coach",
    description="Voice practice-interview coach for investment banking candidates",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session_router, tags=["sessions"])


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        dict: Service health status.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
    )
