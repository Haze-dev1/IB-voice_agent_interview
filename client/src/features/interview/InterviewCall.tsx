"use client";

import { useState } from "react";
import { Mic, MicOff, MessageSquare, MessageSquareOff, Phone } from "lucide-react";
import { usePipecatClientMicControl } from "@pipecat-ai/client-react";
import { Shell } from "@/components/Shell";
import { useInterviewSession } from "./useInterviewSession";

export function InterviewCall() {
  const session = useInterviewSession();
  const { isMicEnabled, enableMic } = usePipecatClientMicControl();
  const [name, setName] = useState("");
  const [showTranscript, setShowTranscript] = useState(true);

  if (session.phase === "idle") {
    return (
      <Shell>
        <div className="call-panel-wrap">
          <div className="panel call-panel">
            <div className="panel-body">
              <p className="eyebrow dot">Practice</p>
              <h1>Mock Interview</h1>
              <p className="lead">Voice mock interview with an AI investment-banking interviewer.</p>
              <label className="field">
                Your name (optional)
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Candidate name"
                  autoComplete="name"
                />
              </label>
              <div className="actions">
                <button className="primary" onClick={() => session.start(name.trim() || undefined)}>
                  <Phone size={16} aria-hidden />
                  Start Interview
                </button>
              </div>
              {session.error && <p className="notice error">{session.error}</p>}
            </div>
          </div>
        </div>
      </Shell>
    );
  }

  if (session.phase === "connecting") {
    return (
      <Shell>
        <div className="call-panel-wrap">
          <div className="call-connecting">
            <div className="call-pulse" aria-hidden />
            <p>Connecting to your interviewer…</p>
          </div>
        </div>
      </Shell>
    );
  }

  if (session.phase === "ended") {
    return (
      <Shell>
        <div className="call-panel-wrap">
          <div className="panel call-panel wide">
            <div className="panel-body">
              <p className="eyebrow dot">Session ended</p>
              <h1>Thanks for practicing</h1>
              {session.feedback.length > 0 ? (
                <>
                  <h2>Feedback</h2>
                  {session.feedback.map((line, i) => (
                    <p key={i} className="feedback">{line}</p>
                  ))}
                </>
              ) : (
                <p className="lead">No feedback was recorded for this session.</p>
              )}
              {session.captions.length > 0 && (
                <>
                  <h2>Transcript</h2>
                  {session.captions.map((c, i) => (
                    <p key={i} className="small muted">
                      <strong>{c.role}:</strong> {c.text}
                    </p>
                  ))}
                </>
              )}
              <div className="actions">
                <button className="primary" onClick={session.restart}>
                  Start new session
                </button>
              </div>
            </div>
          </div>
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="call-main">
        <div className="call-stage">
          <span className="call-badge">
            <span className="dot" aria-hidden />
            {session.questionNumber > 0
              ? `Question ${session.questionNumber} of ${session.questionTotal}`
              : "Mock Interview"}
          </span>

          <button
            type="button"
            className="icon-button call-transcript-toggle"
            onClick={() => setShowTranscript((v) => !v)}
            aria-pressed={showTranscript}
            aria-label={showTranscript ? "Hide captions" : "Show captions"}
            title={showTranscript ? "Hide captions" : "Show captions"}
          >
            {showTranscript ? <MessageSquare size={17} aria-hidden /> : <MessageSquareOff size={17} aria-hidden />}
          </button>

          <div
            className={`persona-tile${session.botSpeaking ? " speaking" : ""}`}
            aria-label={session.botSpeaking ? "Interviewer speaking" : "Interviewer listening"}
          >
            <span className="initials" aria-hidden>IB</span>
            {session.botSpeaking && (
              <span className="persona-eq" aria-hidden>
                <i /><i /><i />
              </span>
            )}
          </div>

          <p className="call-meta">
            <strong>Interviewer</strong>
            {" · "}
            {session.botSpeaking ? "speaking…" : session.userSpeaking ? "listening…" : "your turn"}
          </p>

          <div className={`self-tile${session.userSpeaking ? " talking" : ""}`}>
            <span className={`mic-dot${isMicEnabled ? "" : " muted"}`} aria-hidden />
            {isMicEnabled ? "You" : "You (muted)"}
          </div>

          {showTranscript && session.captions.length > 0 && (
            <div className="call-captions" aria-live="polite">
              {session.captions.map((c, i) => (
                <p key={i} className={i === session.captions.length - 1 ? "latest" : undefined}>
                  <strong>{c.role}:</strong> {c.text}
                </p>
              ))}
            </div>
          )}

          <div className="call-toolbar">
            <button
              type="button"
              className={`call-round${isMicEnabled ? "" : " off"}`}
              onClick={() => enableMic(!isMicEnabled)}
              aria-label={isMicEnabled ? "Mute microphone" : "Unmute microphone"}
            >
              {isMicEnabled ? <Mic size={20} aria-hidden /> : <MicOff size={20} aria-hidden />}
            </button>
            <button
              type="button"
              className="call-round end"
              onClick={session.end}
              aria-label="End call"
            >
              <Phone size={20} aria-hidden />
            </button>
          </div>

          {session.error && <p className="notice error">{session.error}</p>}
        </div>
      </div>
    </Shell>
  );
}
