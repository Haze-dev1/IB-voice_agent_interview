You're building the client for an already-working voice interview coach (see `server/` — RTVI + SmallWebRTC/Daily transport, session/controller/service layering, TypeSafe judgment, all done). `client/` currently only has an empty `client/src/features/interview/` folder and no `package.json` — this is a real greenfield build, not a redo. Read `AGENTS.md` in this directory first (client SDK conventions live there too — §2 transports, §4 RTVI events) and `server/bot.py` + `server/main.py` to see exactly what you're connecting to before writing any connection code. Don't guess the wire contract — verify the RTVI client SDK's connection setup via the context hub (`search_docs` / `search_examples` for "RTVI client" and "SmallWebRTC client"), and confirm which port/endpoint serves the WebRTC offer vs. which serves `/v1/sessions/connect` by reading how `bot.py`'s dev runner and `main.py` are actually run — they're two separate processes right now, don't assume they share a port.

Before writing any frontend code, invoke the `eigi-frontend-standards` skill and follow it for the whole build: route/page thin, a feature component for the call UI, API/connection calls centralized in one place, loading/connecting/error/ended states all covered, no ad-hoc fetches scattered through components.

Also run this whole task under `/ponytail` at **ultra** intensity — YAGNI extremist, no exceptions:
- Before adding anything, ask "does this need to exist at all?" If it's speculative, skip it and say so in one line.
- No component library, no state-management library, no design-token system, no theming engine — this is one screen with a handful of states, not a platform.
- No routing beyond what Next.js gives you for free. No multi-page flow unless the interview genuinely needs a second screen (e.g. a feedback screen at session end — see below).
- Fewest files, shortest working diff that's actually correct.
- No account system, no history of past sessions, no settings panel, no persisted preferences — unless explicitly asked for below.

## What to build

**A single-screen, audio-only call interface, heavily inspired by Google Meet's calling UI** — but adapted for a one-on-one voice-only call with an AI interviewer instead of a video grid. No camera, no video tiles, ever. Use **Mobbin** as your design reference for the actual visual language (search it for "Google Meet call screen," "voice call interface," "in-call controls," "audio-only call") rather than inventing a look from scratch — ground spacing, typography scale, control-bar layout, and motion in real patterns you find there, don't just eyeball a Meet screenshot from memory.

**Screens/states (one route, state-driven — not separate pages unless truly necessary):**

1. **Pre-call / lobby** — candidate's name (optional, matches `SessionConnectRequest.candidate_name`), a "Start Interview" action, nothing else. No device/mic picker unless you find a real need for one (single mic input is the common case).
2. **Connecting** — brief, calm loading state while the session is created and the WebRTC connection negotiates. Don't over-build this; a Meet-style spinner/pulse is enough.
3. **In-call** — the core screen:
   - A large, centered "persona tile" for the AI interviewer in place of a video tile — think Meet's audio-only participant tile (avatar/initials on a solid or subtly animated background), not a static image. It should visibly react when the interviewer is speaking (an animated speaking indicator — a Meet-style pulsing ring or waveform around the tile), and show a distinct idle/listening state when it's the candidate's turn.
   - A small self-indicator for the candidate's own mic (talking/muted state), Meet-style — not a self video tile, just a mic-level indicator.
   - A bottom control bar, Meet-style: mute/unmute mic, end call. Nothing else unless the interview flow needs it.
   - Minimal session context on-screen: which question number you're on (the bot already tracks this via `get_next_question`/`process_answer` — surface it from the RTVI events/messages the client already receives, don't duplicate interview-flow logic client-side).
   - Optional: a lightweight live transcript/captions strip (Meet has this) — only add it if it's a small lift given the RTVI transcription events already flowing through the client SDK; don't build a full chat-log UI.
4. **Ended / feedback** — when the bot calls `get_feedback` and ends the session, show the spoken feedback as readable text (strengths / areas to improve, matching `InterviewFeedback` in `server/core/schemas/interview.py`) plus a way to start a new session. Don't build this as a separate route if a state swap on the same screen is simpler.

**Visual direction:** dark theme (Meet's default in-call look), calm and professional — this is an interview practice tool, not a consumer app. Real motion (the speaking-indicator animation, connecting-state pulse) but nothing gratuitous. No confetti, no gradients-for-their-own-sake, no illustration library.

## Stack

Next.js/TypeScript. Use Pipecat's **React SDK** (`@pipecat-ai/client-react` + `@pipecat-ai/client-js` + the small-webrtc transport package — confirm exact package names and hook APIs via the context hub, they change) — Next.js is a React framework, so this is the correct SDK, not a separate "Next.js" one. Anything using the SDK's hooks/components (the connection logic, the call screen) touches browser WebRTC/mic APIs and must be a Client Component (`'use client'`) — it cannot run server-side or during SSR/RSC. Centralize the connection lifecycle (create session → connect transport → subscribe to RTVI events for bot-speaking/user-speaking/transcript/tool-call states → disconnect) in one hook or module per eigi-frontend-standards, and drive the UI state machine (`idle → connecting → in-call → ended`) off that.

No extra dependencies beyond: Next.js, the Pipecat client SDK packages, and — only if Mobbin research turns up a genuinely non-trivial audio-waveform/speaking-indicator pattern you don't want to hand-roll in SVG/CSS — a minimal single-purpose package for that one thing. Justify any dependency beyond the SDK in one line before adding it.

## Env & config

The client needs to know the session API base URL and the bot's connection endpoint. Add a minimal `.env.local.example` listing exactly what's needed (likely `NEXT_PUBLIC_SESSION_API_URL` and whatever the RTVI/SmallWebRTC transport needs) — don't invent config beyond what the actual connection code reads.

## Explicitly out of scope — do not build

Video/camera support in any form, multiple participants or a participant grid, screen sharing, chat/DM UI, device picker beyond default mic, account/auth, session history, a settings screen, dark/light theme toggle (pick dark and ship it), any backend changes (server/ is done — if the client needs something the API doesn't expose, name it and ask rather than reaching into server/ yourself).

Report back with: what you built, the final `client/` file layout, the exact env vars required, and how you verified the call actually connects and reacts to bot-speaking/user-speaking state (screenshot or a description of a manual run against `uv run bot.py` + `uv run main.py`).
