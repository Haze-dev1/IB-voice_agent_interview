"""TypeSafe transcript check - second opinion on interview quality.

This is a standalone dev script that runs alongside pipecat eval run.
It feeds a transcript to TypeSafe Jev for a holistic assessment of whether
the interviewer held character and gave substantive feedback across the
whole conversation.

Usage:
    python check_transcript.py <transcript_file>

The transcript file should be a JSON list of messages with 'role' and 'content' keys.
"""

import asyncio
import json
import sys

from typesafe_sdk import AsyncTypeSafeClient, Noul, Score


async def check_transcript(transcript_path: str) -> dict:
    """Evaluate a transcript for interviewer character and feedback quality.

    Args:
        transcript_path: Path to a JSON transcript file.

    Returns:
        Dict with character_held, gave_feedback, and overall scores.
    """
    with open(transcript_path) as f:
        transcript = json.load(f)

    conversation = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in transcript
    )

    state = {"transcript": conversation}

    async with AsyncTypeSafeClient() as client:
        response = await client.system_one(
            state=state,
            questions={
                "character_held": Noul(
                    instructions=(
                        "Did the interviewer maintain a consistent professional "
                        "investment banking interviewer persona throughout the "
                        "entire conversation? Never breaking character, never "
                        "revealing they are an AI, never deviating from the "
                        "interview format."
                    ),
                ),
                "gave_feedback": Noul(
                    instructions=(
                        "Did the interviewer provide substantive, constructive "
                        "feedback on the candidate's answers? Not just generic "
                        "praise, but specific observations about strengths and "
                        "areas for improvement."
                    ),
                ),
                "question_quality": Score(
                    instructions=(
                        "How would you rate the overall quality and relevance "
                        "of the interview questions asked?"
                    ),
                    criteria=[
                        "Irrelevant or off-topic",
                        "Somewhat relevant",
                        "Moderately relevant",
                        "Highly relevant",
                        "Excellent IB interview questions",
                    ],
                ),
            },
        )

    character_held = response.nouls["character_held"]
    gave_feedback = response.nouls["gave_feedback"]
    question_quality = response.scores["question_quality"]

    return {
        "character_held": character_held,
        "gave_feedback": gave_feedback,
        "question_quality_score": question_quality,
        "passed": character_held and gave_feedback,
    }


async def main():
    """Run the transcript check from command line."""
    if len(sys.argv) < 2:
        print("Usage: python check_transcript.py <transcript_file>")
        sys.exit(1)

    transcript_path = sys.argv[1]
    result = await check_transcript(transcript_path)

    print("\n=== TypeSafe Transcript Check ===")
    print(f"Character held: {result['character_held']}")
    print(f"Gave feedback: {result['gave_feedback']}")
    print(f"Question quality: {result['question_quality_score']}")
    print(f"Overall passed: {result['passed']}")
    print("=================================\n")

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    asyncio.run(main())
