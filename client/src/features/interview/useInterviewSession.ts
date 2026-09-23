import { useCallback, useRef, useState } from "react";
import {
  RTVIEvent,
  type BotOutputData,
  type BotTTSTextData,
  type ErrorData,
  type LLMFunctionCallStartedData,
  type RTVIMessage,
  type TranscriptData,
} from "@pipecat-ai/client-js";
import {
  usePipecatClient,
  useRTVIClientEvent,
} from "@pipecat-ai/client-react";
import { WEBRTC_OFFER_URL } from "./client";
import { QUESTION_TOTAL, createSession } from "./sessionApi";

export type Phase = "idle" | "connecting" | "in-call" | "ended";

export interface Caption {
  role: "You" | "Interviewer";
  text: string;
}

// Two lines is what fits without the box growing tall enough to crowd the
// toolbar; TTS chunks arrive roughly a sentence at a time.
const MAX_CAPTIONS = 2;

/**
 * Owns the whole interview connection lifecycle: create session on the
 * FastAPI host, connect the WebRTC transport to the bot runner, subscribe
 * to RTVI speaking/transcript/function-call events, disconnect.
 * UI state (phase, captions, question progress, feedback) derives from that.
 */
export function useInterviewSession() {
  const client = usePipecatClient();
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [botSpeaking, setBotSpeaking] = useState(false);
  const [userSpeaking, setUserSpeaking] = useState(false);
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [questionNumber, setQuestionNumber] = useState(0);
  const [feedback, setFeedback] = useState<string[]>([]);
  // Set once the bot calls get_feedback; later bot output is spoken feedback.
  const feedbackArmed = useRef(false);

  // Dev-mode Fast Refresh can re-subscribe the RTVI event bus without the
  // previous subscription's cleanup running, double-firing the same event.
  // Dropping an immediate repeat of the same line is a robust guard against
  // that either way, without depending on the SDK's internal retry/HMR behavior.
  const pushCaption = useCallback((caption: Caption) => {
    setCaptions((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === caption.role && last.text === caption.text) return prev;
      return [...prev.slice(-(MAX_CAPTIONS - 1)), caption];
    });
  }, []);

  // Captions follow TTS, not the LLM. BotOutput fires the moment text is
  // generated — the bot writes its whole turn in about a second then spends
  // half a minute speaking it, so captions sourced from it ran far ahead of
  // the audio. BotTtsText is speech-timed but arrives one word at a time, so
  // buffer words and flush a caption at each sentence end.
  const sentence = useRef("");

  const flushSentence = useCallback(() => {
    const text = sentence.current.trim();
    sentence.current = "";
    if (text) pushCaption({ role: "Interviewer", text });
  }, [pushCaption]);

  useRTVIClientEvent(RTVIEvent.BotStartedSpeaking, useCallback(() => setBotSpeaking(true), []));
  // A turn can end on a fragment with no closing punctuation; don't strand it.
  useRTVIClientEvent(
    RTVIEvent.BotStoppedSpeaking,
    useCallback(() => {
      setBotSpeaking(false);
      flushSentence();
    }, [flushSentence]),
  );
  useRTVIClientEvent(RTVIEvent.UserStartedSpeaking, useCallback(() => setUserSpeaking(true), []));
  useRTVIClientEvent(RTVIEvent.UserStoppedSpeaking, useCallback(() => setUserSpeaking(false), []));

  useRTVIClientEvent(
    RTVIEvent.UserTranscript,
    useCallback(
      (data: TranscriptData) => {
        if (data.final) pushCaption({ role: "You", text: data.text });
      },
      [pushCaption],
    ),
  );

  useRTVIClientEvent(
    RTVIEvent.BotTtsText,
    useCallback(
      (data: BotTTSTextData) => {
        sentence.current += `${sentence.current ? " " : ""}${data.text.trim()}`;
        if (/[.!?]$/.test(sentence.current)) flushSentence();
      },
      [flushSentence],
    ),
  );

  // Feedback text still comes from the LLM stream: it is read after the call
  // ends, so it wants the complete sentences rather than speech timing.
  useRTVIClientEvent(
    RTVIEvent.BotOutput,
    useCallback((data: BotOutputData) => {
      if (data.aggregated_by !== "sentence" || !feedbackArmed.current) return;
      setFeedback((prev) => (prev[prev.length - 1] === data.text ? prev : [...prev, data.text]));
    }, []),
  );

  useRTVIClientEvent(
    RTVIEvent.LLMFunctionCallStarted,
    useCallback((data: LLMFunctionCallStartedData) => {
      if (data.function_name === "get_next_question") {
        setQuestionNumber((n) => Math.min(n + 1, QUESTION_TOTAL));
      } else if (data.function_name === "get_feedback") {
        feedbackArmed.current = true;
      }
    }, []),
  );

  // Only a fatal error ends the call. The pipeline emits recoverable ones —
  // a rejected tool call, for instance — and the bot carries on talking after
  // them; ending on those dropped the UI to the feedback screen mid-interview
  // while the interviewer was still speaking.
  useRTVIClientEvent(
    RTVIEvent.Error,
    useCallback((message: RTVIMessage) => {
      const detail = message.data as Partial<ErrorData> | undefined;
      if (!detail?.fatal) {
        console.warn("Recoverable pipeline error", detail?.error);
        return;
      }
      setError(detail.error ?? "Connection error");
      setPhase((prev) => (prev === "in-call" || prev === "connecting" ? "ended" : prev));
    }, []),
  );

  useRTVIClientEvent(
    RTVIEvent.Disconnected,
    useCallback(() => {
      setBotSpeaking(false);
      setUserSpeaking(false);
      setPhase((prev) => (prev === "in-call" || prev === "connecting" ? "ended" : prev));
    }, []),
  );

  const start = useCallback(
    async (candidateName?: string) => {
      if (!client || phase === "connecting") return;
      setError(null);
      setPhase("connecting");
      try {
        await createSession(candidateName);
        await client.connect({
          webrtcRequestParams: { endpoint: WEBRTC_OFFER_URL },
        });
        setPhase("in-call");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to connect");
        setPhase("idle");
      }
    },
    [client, phase],
  );

  const end = useCallback(async () => {
    try {
      await client?.disconnect();
    } finally {
      setBotSpeaking(false);
      setUserSpeaking(false);
      setPhase("ended");
    }
  }, [client]);

  const restart = useCallback(() => {
    feedbackArmed.current = false;
    sentence.current = "";
    setCaptions([]);
    setFeedback([]);
    setQuestionNumber(0);
    setError(null);
    setBotSpeaking(false);
    setUserSpeaking(false);
    setPhase("idle");
  }, []);

  return {
    phase,
    error,
    botSpeaking,
    userSpeaking,
    captions,
    questionNumber,
    questionTotal: QUESTION_TOTAL,
    feedback,
    start,
    end,
    restart,
  };
}
