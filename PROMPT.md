You're building a voice practice-interview coach for investment banking candidates, on top of an already-scaffolded Pipecat project. Do not re-scaffold — a cascade pipeline (Deepgram STT → OpenAI Responses LLM → Cartesia TTS) with SmallWebRTC + Daily transport already exists in server/bot.py. Read AGENTS.md in this directory first — it's the framework's own rules for agents building Pipecat apps (non-negotiable: don't hand-write boilerplate, don't guess APIs from memory — verify via the context hub or installed package source, ask for missing API keys instead of inventing them).

Before writing any backend code, invoke the `eigi-backend-standards` skill. Before writing any frontend code, invoke the `eigi-frontend-standards` skill. Before designing the answer-judgment step (section 3 below), invoke the `typesafe-ai` skill and read the live docs it points you to — don't hand-write the integration from memory. Follow all three for the rest of this task.

Stack: host the bot behind a FastAPI server rather than relying only on Pipecat's built-in dev runner (AGENTS.md §4 confirms this is a normal Pipecat production pattern — a long-lived host adding/removing sessions passes `auto_end=False`). Verify the exact wiring via the context hub/installed source per AGENTS.md §3, don't hand-write it from memory. If a client is built (section 2), it's Next.js/React. This also makes the eigi-backend-standards route→controller→service layering apply literally instead of by analogy: a route for the session/connect endpoint, a controller for session orchestration, services for interview-flow and TypeSafe-judgment logic.

Also follow this ruleset for every decision (ponytail, ultra intensity — YAGNI extremist, no exceptions):
- Before adding anything, ask "does this need to exist at all?" If it's speculative, skip it and say so in one line.
- Reuse what's already in the scaffold before writing new code. Stdlib/native/already-installed-dependency before a new one.
- No interfaces with one implementation, no config for values that never change, no abstraction for a single call site, no "for later" scaffolding.
- Fewest files, shortest working diff that's actually correct.
- No database, no auth system, no admin panel, no analytics, no multi-persona config system, no session persistence beyond in-memory — unless something below explicitly asks for it.

## What to build

**1. Interviewer persona (server/bot.py + new modules under server/)**
Replace the generic assistant system prompt with an IB practice-interviewer persona:
- Conducts a structured mock interview: a mix of technical questions (valuation methods, DCF mechanics, LBO basics, accounting linkages — "walk me through how a $10 depreciation increase affects the three statements") and behavioral/fit questions ("why banking", "walk me through your resume").
- Asks one question at a time, listens to the answer, asks a natural follow-up or moves on, and at the end of the session gives spoken feedback on the candidate's answers.
- Keep the scaffold's voice-safe instruction ("responses are spoken aloud, no emojis/bullets/markdown") — carry it into the new system prompt.

Pull the question bank and interview-flow logic out of bot.py into properly layered FastAPI modules per eigi-backend-standards: a route for the session/connect endpoint (thin — request parsing, response wrapping), a controller for session orchestration, services for interview-flow (question selection, follow-up decisions, TypeSafe calls) and static question content in its own data module, schemas for any request/response shapes. Keep bot.py's pipeline-construction logic (services, pipeline, `bot(runner_args)` contract) as-is and call it from the FastAPI session route rather than duplicating it — don't let either file become a dumping ground. Add docstrings and the logging pattern the skill specifies to every new function.

**2. Client**
No client currently exists. Decide for yourself first whether Pipecat's built-in SmallWebRTC Prebuilt UI (already free at localhost:7860, ships with the scaffold) is enough — if it is, use it and stop there, don't build a custom app for its own sake. Only build a minimal custom client if the practice-interview experience genuinely needs something the generic voice widget doesn't give you (e.g. showing which question you're on, a start/end-session control, a readable transcript). If you do build one: Next.js/React with Pipecat's official client SDK, one page, structured per eigi-frontend-standards (route/page thin, feature component for the interview UI, API/connection calls centralized, loading/connecting/error/ended states covered). No extra routing/state-management/component libraries beyond what's already needed — this is a single-screen tool.

**3. Answer-quality judgment (TypeSafe / Jev)**
Use TypeSafe's System One model (Jev) for exactly one thing: judging whether the candidate's spoken answer to the current question is complete enough to move on, or thin enough to deserve a follow-up. This is a semantic judgment call, not a fact lookup or calculation — the right place for it per the skill's own guidance ("keep known rules, calculations, exact lookups in code; add TypeSafe where semantic understanding helps").
- After each candidate answer, send the question + the answer as state and ask a single `Score` (or `Noul`, whichever the primitive docs say fits "is this answer complete/on-topic") judgment — don't invent a bespoke classifier when a documented primitive already covers it.
- Code owns the decision from there: the interview-flow service (section 1) reads the typed judgment and decides follow-up-vs-next-question and, at session end, folds the per-answer scores into the spoken feedback. Don't let TypeSafe generate the feedback text itself — that's still the interviewer LLM's job; TypeSafe only supplies the structured judgment it reasons from.
- `TYPESAFE_API_KEY` is already set as a global environment variable on this machine — list it in `.env.example` (no value) like the other keys, but don't ask the user for it or duplicate it into `.env`.
- Keep this server-side only, per the skill's own instruction ("keep API credentials server-side in web apps") — never expose the key or call the API from the client.
- If, after reading the primitive docs, a single Score/Noul call per answer doesn't cleanly fit, say so and propose the closest documented pattern rather than forcing it.

**4. Env & secrets**
Keep .env.example in sync with whatever keys the final code actually reads. Don't invent placeholder keys or vendors not already in the scaffold (Deepgram/OpenAI/Cartesia/Daily/TypeSafe). If you need something not already configured, stop and ask which env var and provider.

**5. Verification**
Use Pipecat's eval harness, not a live call, to prove the interview flow works: scaffold or hand-add the eval transport if missing, write one scripted text-mode scenario under server/evals/ that exercises the greeting, one technical question, a follow-up, and confirms the bot stays in interviewer character. Run it and show it passing before calling this done.

This is Pipecat's own pass/fail judge (Ollama or an OpenAI-compatible `factory:`) and stays as-is — don't replace it. Add Jev as a second, independent dev-time check on top of it: after the scripted scenario runs, feed its transcript to one TypeSafe judgment (invoke `typesafe-ai` again if you need the pattern) answering something a scripted `expect:` assertion can't cleanly phrase — e.g. a `Score` on whether the interviewer held character and gave substantive feedback across the *whole* conversation, not just the turn-by-turn checks. This is a small standalone dev script (e.g. `server/evals/check_transcript.py`), not part of the shipped bot and not wired into bot.py — it's a second opinion you run alongside `pipecat eval run`, not a replacement for it. Report both results.

## Explicitly out of scope — do not build
Multiple interviewer personalities/configs, a question bank admin UI, user accounts, persisted interview history/analytics, scoring rubrics beyond spoken end-of-session feedback, telephony support, deployment changes beyond what the scaffold already has. If you think one of these is actually needed, name it and ask rather than building it.

Report back with: what you changed, the final file layout, which env vars are required, and the eval scenario result.
