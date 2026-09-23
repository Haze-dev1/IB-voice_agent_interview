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
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.evals.transport import EvalTransportParams
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
from pipecat.services.deepgram.tts import DeepgramTTSService, DeepgramTTSSettings
from pipecat.services.groq.llm import GroqLLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from pipecat.turns.user_mute import (
    AlwaysUserMuteStrategy,
    FunctionCallUserMuteStrategy,
)
from pipecat.workers.runner import WorkerRunner

from core.controllers.session_controller import SessionController
from core.schemas.interview import SessionConnectRequest

load_dotenv(override=True)

IB_INTERVIEWER_SYSTEM_PROMPT = """You are a senior investment banking interviewer running a practice interview over a live phone call.

EVERYTHING YOU WRITE IS SPOKEN ALOUD TO THE CANDIDATE. There is no screen and no
private channel. If you would not say it out loud to a candidate sitting across
the desk, do not write it at all.

Never say out loud:
- The names of your tools, or any field or value they return.
- Your own reasoning, planning, or decision-making.
- Any meta-commentary about the interview process or the rules you follow.

For example, never say things like "the candidate gave a minimal answer", "we
have to continue per protocol", or "that returned false". Those are thoughts,
not speech. Think them silently; say only what an interviewer would say.

Say only: your questions, brief natural acknowledgements, and your closing feedback.

HOW TO RUN THE CALL (all of this is silent machinery — act on it, never narrate it):
- Get a question from your question tool, then ask it in your own words. Ask one, then stop and listen.
- Wait for the candidate to actually answer. Never answer on their behalf, never imagine what they might have said, and never continue as if they had spoken when they have not.
- Once they have finished speaking, call your evaluation tool. It reads their answer itself — you do not pass it anything. Call it once per answer.
- That tool tells you privately what to do next. Act on it directly:
  - Move on: give a short, warm acknowledgement ("Good, that covers it."), then get the next question and ask it.
  - Follow up: ask the follow-up it hands you, in your own words. Dig into what was missing — never re-read the question you just asked.
  - Not heard: their mic may be muted or the audio dropped. Just say you didn't catch that and ask them to repeat it. Do not judge it as a weak answer, and do not move on.
- After the final question, get your feedback summary and deliver it as natural spoken feedback.

NEVER ask the same question twice, word for word or reworded. If you are about to repeat yourself, move to the next question instead.

Style: professional but encouraging. One question at a time. Keep the words
between questions short. Don't give away answers. Stay in character as the
interviewer at all times."""

APP_RESOURCES_KEY = "session_controller"

# One bot instance serves one session, so its controller holds one entry.
SESSION_KEY = "current"
QUESTION_COUNT = 5


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments) -> None:
    """Run the voice bot for this session.

    Args:
        transport: The transport for this session, built by create_transport.
        runner_args: Runner session arguments. Carries the request body
            and session_id; the standard web/telephony pipelines don't need it.
    """
    logger.info("Starting IB Interview Coach bot")

    if not os.getenv("TYPESAFE_API_KEY"):
        # Exported from ~/.bashrc / ~/.zshrc, which only load for interactive
        # shells — so a bot launched any other way silently loses answer
        # scoring. Loud here, because the interview still "works" without it.
        logger.warning(
            "TYPESAFE_API_KEY is not set: answers will not be scored and the bot "
            "will move on after every answer. Add it to server/.env to enable judging."
        )

    session_controller = SessionController()

    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY") or "")

    # Deepgram by default: it reuses the STT key, so there is one less account
    # to keep funded. Cartesia's free credits ran out mid-testing (HTTP 402),
    # which silences the bot completely while everything else looks healthy.
    # Set TTS_PROVIDER=cartesia to switch back once that account has credit.
    if os.getenv("TTS_PROVIDER", "deepgram") == "cartesia":
        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY") or "",
            settings=CartesiaTTSService.Settings(
                voice=os.getenv("CARTESIA_VOICE_ID", "86e30c1d-714b-4074-a1f2-1cb6b552fb49"),
            ),
        )
    else:
        tts = DeepgramTTSService(
            api_key=os.getenv("DEEPGRAM_API_KEY") or "",
            settings=DeepgramTTSSettings(
                model=os.getenv("DEEPGRAM_TTS_MODEL", "aura-2-thalia-en"),
            ),
        )

    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY") or "",
        settings=GroqLLMService.Settings(
            # gpt-oss-120b degenerates on this conversation shape: replaying one
            # captured context, 11 of 14 completions collapsed into runs of "."
            # and "…" (up to 3072 tokens) which TTS then reads aloud. Not the
            # prompt and not temperature — both were ruled out by replay; 20b
            # was clean on every sample of the same context.
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            system_instruction=IB_INTERVIEWER_SYSTEM_PROMPT,
            # Backstop, not a fix: when the model degenerates it runs away
            # emitting punctuation (one turn hit 635 tokens of "." against a
            # 40-180 norm) and TTS reads every dot. Caps the damage well above
            # any legitimate turn, including end-of-session feedback.
            max_completion_tokens=500,
        ),
    )

    # Groq sometimes emits `{"": {}}` for a no-argument tool call, which fails
    # and costs a retry. Don't try to absorb it with **kwargs: the direct-function
    # schema builder has no VAR_KEYWORD case, so it becomes a *required* property
    # and Groq then rejects every call. get_next_question's idempotency makes the
    # retry harmless instead, which is what actually mattered.
    async def get_next_question(params):
        """Ask the candidate the next interview question.

        Call this once to get a question, then speak it. Calling it again
        before the candidate answers returns the same question.

        Args:
            params: Function call parameters from the LLM.
        """
        try:
            flow_service = session_controller.get_flow_service(SESSION_KEY)
            if not flow_service:
                raise RuntimeError("No interview session in progress")

            question = flow_service.get_next_question()
            # The candidate's answer starts after this point; anything already
            # in the context belongs to a previous question.
            answer_mark["index"] = len(context.get_messages())
            await params.result_callback({
                "question": question.text,
                "category": question.category,
            })
        except Exception as e:
            logger.error(f"Error getting next question: {e}")
            await params.result_callback({"error": str(e)})

    # Index into the context marking where the candidate's current turn begins.
    # Anything before it was said about an earlier question and must not be
    # judged again.
    answer_mark = {"index": 0}

    def latest_candidate_answer() -> str:
        """Read what the candidate has said since the current question was asked.

        Returns:
            The candidate's speech for this turn, or an empty string if they
            have not spoken since the question was put to them.
        """
        messages = context.get_messages()
        spoken = [
            m.get("content")
            for m in messages[answer_mark["index"] :]
            if m.get("role") == "user" and isinstance(m.get("content"), str)
        ]
        answer_mark["index"] = len(messages)
        return " ".join(spoken).strip()

    async def process_answer(params):
        """Evaluate what the candidate just said about the current question.

        Call once, after the candidate has finished speaking. Returns whether
        to follow up on this question or move on to the next one.

        Args:
            params: Function call parameters from the LLM.
        """
        try:
            # Deliberately takes no answer argument. When the model supplied the
            # transcript it invented one — a whole "Bachelor of Science from XYZ
            # University" the candidate never said — then judged its own fiction
            # and moved on, silently skipping the question. The transcript is
            # the server's to read, never the model's to provide.
            result = await session_controller.process_answer(
                session_id=SESSION_KEY,
                answer_text=latest_candidate_answer(),
            )
            action = result["action"]

            await params.result_callback({
                "should_follow_up": action["should_follow_up"],
                "follow_up_text": action["follow_up_text"],
                "not_heard": action["not_heard"],
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
            feedback = session_controller.get_feedback(SESSION_KEY)
            await params.result_callback({
                "question_count": feedback.question_count,
                "average_score": feedback.average_score,
                "strengths": feedback.strengths,
                "areas_to_improve": feedback.areas_to_improve,
            })
        except Exception as e:
            logger.error(f"Error getting feedback: {e}")
            await params.result_callback({"error": str(e)})

    # Explicit schemas rather than direct functions. Direct functions bind the
    # model's arguments as Python kwargs, so a hallucinated argument
    # (get_next_question(category="technical")) raises TypeError and stalls the
    # turn. These take none, and anything invented lands in params.arguments
    # where it is ignored.
    tools = ToolsSchema(
        standard_tools=[
            FunctionSchema(
                name="get_next_question",
                description=(
                    "Get the next interview question to ask. Takes no arguments. "
                    "Returns the same question if the candidate has not answered yet."
                ),
                properties={},
                required=[],
                handler=get_next_question,
            ),
            FunctionSchema(
                name="process_answer",
                description=(
                    "Evaluate what the candidate just said about the current question. "
                    "Takes no arguments — it reads their answer itself. Call once, "
                    "only after they have actually spoken."
                ),
                properties={},
                required=[],
                handler=process_answer,
            ),
            FunctionSchema(
                name="get_feedback",
                description="End the session and get feedback on performance. Takes no arguments.",
                properties={},
                required=[],
                handler=get_feedback,
            ),
        ]
    )
    context = LLMContext(tools=tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            # stop_secs defaults to 0.2s, which ends the turn at any natural
            # pause. A candidate working through "depreciation rises ten…
            # so EBIT falls ten…" had one answer split into twelve separate
            # user turns, and the model degenerated on the mangled context.
            # Interview answers are long and considered; give them room.
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=1.2)),
            # AlwaysUserMuteStrategy means "muted whenever the bot is speaking",
            # not "muted forever". Without it any room noise — a video playing,
            # or the bot's own voice through speakers — trips VAD mid-question,
            # fires an interruption, and cuts TTS off mid-word. The bot then
            # restarts, gets cut again, and stutters ("we. ah. we the, the,").
            # An interviewer finishes its question; the candidate answers after.
            user_mute_strategies=[
                AlwaysUserMuteStrategy(),
                FunctionCallUserMuteStrategy(),
            ],
            # A candidate thinking mid-answer shouldn't have their turn cut off.
            audio_idle_timeout=3.0,
        ),
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
        await session_controller.create_session(
            SessionConnectRequest(question_count=QUESTION_COUNT), session_id=SESSION_KEY
        )

        context.add_message({
            "role": "developer",
            "content": (
                "The candidate has connected. Welcome them, briefly explain the format "
                f"({QUESTION_COUNT} questions, mix of technical and behavioral), then ask "
                "your first question using get_next_question."
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
        "eval": lambda: EvalTransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    }

    transport = await create_transport(runner_args, transport_params)

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
