"use client";

import { useEffect, useState } from "react";
import { PipecatClientAudio, PipecatClientProvider } from "@pipecat-ai/client-react";
import { getInterviewClient } from "@/features/interview/client";
import { InterviewCall } from "@/features/interview/InterviewCall";

export default function Page() {
  // Render the provider only after mount: the transport needs browser
  // WebRTC APIs, which don't exist during prerender/SSR.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) {
    return (
      <div className="call-panel-wrap" style={{ minHeight: "100vh" }}>
        <div className="call-connecting">
          <div className="call-pulse" aria-hidden />
          <p>Loading…</p>
        </div>
      </div>
    );
  }
  return (
    <PipecatClientProvider client={getInterviewClient()}>
      <InterviewCall />
      <PipecatClientAudio />
    </PipecatClientProvider>
  );
}
