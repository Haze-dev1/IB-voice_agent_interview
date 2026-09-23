import { PipecatClient } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";

// Single shared client, created lazily in the browser: SmallWebRTCTransport
// touches WebRTC APIs at construction, so this must never run during SSR.
let cached: PipecatClient | undefined;

export function getInterviewClient(): PipecatClient {
  cached ??= new PipecatClient({
    transport: new SmallWebRTCTransport(),
    enableMic: true,
  });
  return cached;
}

export const SESSION_API_URL =
  process.env.NEXT_PUBLIC_SESSION_API_URL ?? "http://localhost:8000";

export const WEBRTC_OFFER_URL =
  process.env.NEXT_PUBLIC_WEBRTC_OFFER_URL ??
  "http://localhost:7860/api/offer";
