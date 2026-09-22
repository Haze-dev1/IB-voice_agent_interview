#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""IB Interview Coach - Pipecat Voice Agent

This bot conducts mock investment banking interviews using a cascade pipeline:
Speech-to-Text → LLM → Text-to-Speech

The interviewer asks technical and behavioral questions, evaluates answers
using TypeSafe Jev, and provides spoken feedback at session end.

Required AI services:
- Deepgram (Speech-to-Text)
- Groq (LLM)
- Cartesia (Text-to-Speech)

Run the bot using::

    uv run bot.py
"""

import os

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndWorkerFrame, LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from pipecat.workers.runner import WorkerRunner

from core.controllers.session_controller import SessionController
from core.data.questions import get_question_by_id

load_dotenv(override=True)

IB_INTERVIEWER_SYSTEM_PROMPT = """You are a senior investment banking interviewer conducting a practice interview.

Your role:
- Conduct a structured mock interview with a candidate preparing for IB interviews
- Ask one question at a time from the question bank
- Listen to answers, provide brief acknowledgment, then ask a follow-up OR move on
- After all questions, provide spoken feedback on their performance

Interview flow:
1. Welcome the candidate and explain the format
2. Ask questions one at a time using the get_next_question tool
3. After each answer, evaluate it using the process_answer tool
4. When the candidate has answered enough questions, call get_feedback and share it

Important rules:
- Your responses will be spoken aloud, so avoid emojis, bullet points, or other formatting that can't be spoken.
- Be professional but encouraging, like a real IB interviewer
- Keep responses brief between questions - don't give away answers
- If an answer is thin, ask a follow-up before moving on
- At the end, give constructive feedback covering strengths and areas to improve
- Never break character - you are always the interviewer"""

APP_RESOURCES_KEY = "session_controller"


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments) -> None:
    """Run the voice bot for this session.

    Args:
        transport: The transport for this session, built by create_transport.
        runner_args: Runner session arguments. Carries the request body
            and session_id; the standard web/telephony pipelines don't need it.
    """
    logger.info("Starting IB Interview Coach bot")

    session_controller = SessionController()

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY") or "")

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY") or "",
        settings=CartesiaTTSService.Settings(
            voice=os.getenv("CARTESIA_VOICE_ID", "86e30c1d-714b-4074-a1f2-1cb6b552fb49"),
        ),
    )

    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY") or "",
        settings=GroqLLMService.Settings(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            system_instruction=IB_INTERVIEWER_SYSTEM_PROMPT,
        ),
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    async def get_next_question(params):
        """Get the next interview question from the question bank.

        Selects the next question based on what has been asked so far,
        mixing technical and behavioral questions.

        Args:
            params: Function call parameters from the LLM.
        """
        try:
            flow_service = session_controller.get_flow_service("default")
            if not flow_service:
                from core.schemas.interview import SessionConnectRequest

                session = await session_controller.create_session(
                    SessionConnectRequest(question_count=5)
                )
                flow_service = session_controller.get_flow_service(session.session_id)

            if not flow_service:
                raise RuntimeError("Failed to create or retrieve session")

            question = flow_service.get_next_question()
            await params.result_callback({
                "question_id": question.id,
                "question": question.text,
                "category": question.category,
            })
        except Exception as e:
            logger.error(f"Error getting next question: {e}")
            await params.result_callback({"error": str(e)})

    async def process_answer(params, question_id: str, answer_text: str):
        """Process a candidate's answer and evaluate it.

        Uses TypeSafe Jev to judge answer completeness, then decides
        whether to follow up or move to the next question.

        Args:
            params: Function call parameters from the LLM.
            question_id: The ID of the question being answered.
            answer_text: The candidate's transcribed answer.
        """
        try:
            result = await session_controller.process_answer(
                session_id="default",
                question_id=question_id,
                answer_text=answer_text,
            )
            action = result["action"]
            judgment = result["judgment"]

            await params.result_callback({
                "is_complete": judgment["is_complete"],
                "confidence": judgment["confidence"],
                "should_follow_up": action["should_follow_up"],
                "follow_up_text": action["follow_up_text"],
                "score": action["score"],
                "session_complete": result["session_complete"],
            })
        except Exception as e:
            logger.error(f"Error processing answer: {e}")
            await params.result_callback({"error": str(e)})

    async def get_feedback(params):
        """End the session and get feedback on performance.

        Generates a summary of the interview with strengths and areas
        for improvement based on the answers given.

        Args:
            params: Function call parameters from the LLM.
        """
        try:
            feedback = session_controller.get_feedback("default")
            await params.result_callback({
                "question_count": feedback.question_count,
                "average_score": feedback.average_score,
                "strengths": feedback.strengths,
                "areas_to_improve": feedback.areas_to_improve,
            })
        except Exception as e:
            logger.error(f"Error getting feedback: {e}")
            await params.result_callback({"error": str(e)})

    context = LLMContext(tools=[get_next_question, process_answer, get_feedback])
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[],
        app_resources={APP_RESOURCES_KEY: session_controller},
    )

    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)

    await runner.add_workers(worker)

    @worker.rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        session = await session_controller.create_session(
            __import__("core.schemas.interview", fromlist=["SessionConnectRequest"]).SessionConnectRequest(
                question_count=5
            )
        )
        session_controller._sessions["default"] = session_controller._sessions.pop(session.session_id)

        context.add_message({
            "role": "developer",
            "content": (
                "The candidate has connected. Welcome them, briefly explain the format "
                "(5 questions, mix of technical and behavioral), then ask your first "
                "question using get_next_question."
            ),
        })
        await worker.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Client connected")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        await runner.cancel()

    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Main bot entry point.

    Args:
        runner_args: Runner session arguments with transport and body config.
    """
    transport_params = {
        "daily": lambda: DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
