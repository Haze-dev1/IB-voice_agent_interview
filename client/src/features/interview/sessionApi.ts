import { SESSION_API_URL } from "./client";

export const QUESTION_TOTAL = 5;

export interface SessionInfo {
  sessionId: string;
}

/** POST /v1/sessions/connect on the FastAPI host (main.py, :8000). */
export async function createSession(candidateName?: string): Promise<SessionInfo> {
  const res = await fetch(`${SESSION_API_URL}/v1/sessions/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      candidate_name: candidateName || null,
      question_count: QUESTION_TOTAL,
    }),
  });
  if (!res.ok) {
    throw new Error(`Session API returned ${res.status}`);
  }
  const data = (await res.json()) as { session_id: string };
  return { sessionId: data.session_id };
}
