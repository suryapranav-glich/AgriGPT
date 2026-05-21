import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef, useCallback, useEffect } from "react";
import { Mic, Loader2, Square, Volume2 } from "lucide-react";
import { Sidebar, MobileTabBar } from "../components/layout/Sidebar";
import { Header } from "../components/layout/Header";
import { AgentPill, type AgentType } from "../components/ui/AgentPill";
import { useTranslation } from "../contexts/LanguageContext";
import { LANGUAGES } from "../lib/translations";

export const Route = createFileRoute("/voice")({ component: Voice });

// ─── Types ────────────────────────────────────────────────────────────────────

type State = "idle" | "listening" | "processing" | "response" | "playing" | "error";

interface VoiceResult {
  transcript: string;
  agentReply: string;
  detectedLang: "en" | "te" | "hi";
}

// ─── Constants ────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Maps detected lang code → AgentType pill (best-effort guess; agent router sets real type)
const LANG_AGENT_MAP: Record<string, AgentType> = {
  en: "market",
  te: "market",
  hi: "market",
};

// ─── Component ────────────────────────────────────────────────────────────────

function Voice() {
  const [state, setState] = useState<State>("idle");
  const [result, setResult] = useState<VoiceResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const { t, lang } = useTranslation();

  // Refs for recording
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef   = useRef<Blob[]>([]);
  const audioPlayerRef   = useRef<HTMLAudioElement | null>(null);

  // Fetch dynamic history from backend
  const [history, setHistory] = useState<{q: string, agent: AgentType, t: string}[]>([]);

  useEffect(() => {
    fetch(`${API_BASE}/voice/history`, {
      headers: { "Authorization": `Bearer ${localStorage.getItem("agrigpt_token")}` }
    })
    .then(res => res.json())
    .then(data => {
      if (data.history) {
        // Format timestamps nicely if needed, or just use what backend sends
        const formatted = data.history.map((h: any) => ({
          ...h,
          t: new Date(h.t).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})
        }));
        setHistory(formatted);
      }
    })
    .catch(console.error);
  }, [state]); // Refresh history when state changes (like after a new query completes)

  const currentLangNative =
    LANGUAGES.find((l) => l.code === lang)?.native || "English";

  // ─── Send audio blob to /voice/process ──────────────────────────────────
  const processAudio = useCallback(async (mimeType: string, lat: string, lng: string) => {
    try {
      const blob     = new Blob(audioChunksRef.current, { type: mimeType });
      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");
      if (lat) formData.append("lat", lat);
      if (lng) formData.append("lng", lng);

      const res = await fetch(`${API_BASE}/voice/process`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${localStorage.getItem("agrigpt_token")}` },
        body:   formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as any).detail || "Server error");
      }

      // Metadata comes back in response headers
      const txText = decodeURIComponent(res.headers.get("X-Transcribed-Text") || "");
      const detectedLang = (res.headers.get("X-Detected-Language") || "en") as VoiceResult["detectedLang"];
      const agentReply   = decodeURIComponent(res.headers.get("X-Agent-Response") || "");

      setResult({ transcript: txText, agentReply, detectedLang });
      setState("response");

      // Play the returned MP3
      const audioBlobUrl = URL.createObjectURL(await res.blob());
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = audioBlobUrl;
        audioPlayerRef.current.onended = () => setState("idle");
        audioPlayerRef.current.play();
        setState("playing");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Something went wrong. Please try again.");
      setState("error");
    }
  }, []);

  // ─── Stop recording → triggers processAudio ─────────────────────────────
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();   // triggers recorder.onstop → processAudio
      setState("processing");
    }
  }, []);

  // ─── Start recording ────────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    setErrorMsg("");
    setResult(null);

    let lat = "";
    let lng = "";
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 4000 });
      });
      lat = pos.coords.latitude.toString();
      lng = pos.coords.longitude.toString();
    } catch (e) {
      console.warn("Location not available", e);
    }

    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop()); // release mic
        processAudio(mimeType, lat, lng);
      };

      recorder.start(250); // collect chunks every 250 ms
      mediaRecorderRef.current = recorder;
      setState("listening");
    } catch {
      setErrorMsg("Microphone access denied. Please allow microphone permissions.");
      setState("error");
    }
  }, [processAudio]);

  // ─── Mic button click handler ────────────────────────────────────────────
  const handleMicClick = () => {
    if (state === "listening") {
      stopRecording();
    } else if (state === "idle" || state === "error" || state === "response") {
      startRecording();
    }
    // Do nothing while processing or playing
  };

  // ─── Derived UI values ───────────────────────────────────────────────────
  const isDisabled = state === "processing" || state === "playing";

  const micBg =
    state === "listening"   ? "#c0392b"   // red while recording
    : state === "playing"   ? "#1d6a3a"   // darker green while playing
    : state === "error"     ? "#b45309"   // amber on error
    : "#3b6d11";                          // default green

  const micIcon = () => {
    if (state === "processing") return <Loader2 size={28} className="animate-spin" />;
    if (state === "listening")  return <Square  size={24} strokeWidth={2} />;
    if (state === "playing")    return <Volume2 size={28} strokeWidth={1.75} />;
    return <Mic size={28} strokeWidth={1.75} />;
  };

  const statusText = () => {
    if (state === "idle")       return t("tapToSpeak");
    if (state === "listening")  return t("listening");
    if (state === "processing") return t("thinking");
    if (state === "playing")    return t("hereIsWhatIFound");
    if (state === "response")   return t("hereIsWhatIFound");
    if (state === "error")      return errorMsg || "Error — tap to retry";
    return "";
  };

  return (
    <div className="min-h-screen" style={{ background: "#fff" }}>
      <Sidebar />

      <div className="md:pl-[240px] pb-16 md:pb-0">
        <Header title={t("voiceMode")} />

        <main className="flex flex-col items-center justify-center px-6 py-16 page-fade">

          {/* ── Language badge ── */}
          <div
            className="px-3 py-1 rounded-full text-[12px]"
            style={{ background: "#f0f5ea", color: "#3b6d11" }}
          >
            {t("speakingIn")} {currentLangNative}
          </div>

          {/* ── Mic button with ripple ── */}
          <div className="relative mt-8">
            {state === "listening" && (
              <>
                <span
                  className="absolute inset-0 rounded-full ripple-ring"
                  style={{ background: "#c0392b", opacity: 0.15 }}
                />
                <span
                  className="absolute inset-0 rounded-full ripple-ring"
                  style={{ background: "#c0392b", opacity: 0.15, animationDelay: "0.6s" }}
                />
              </>
            )}

            <button
              onClick={handleMicClick}
              disabled={isDisabled}
              aria-label={statusText()}
              className="relative w-20 h-20 rounded-full flex items-center justify-center transition-colors duration-200"
              style={{
                background: micBg,
                color:      "#fff",
                cursor:     isDisabled ? "not-allowed" : "pointer",
                opacity:    isDisabled ? 0.85 : 1,
              }}
            >
              {micIcon()}
            </button>
          </div>

          {/* ── Status label ── */}
          <div
            className="mt-6"
            style={{
              fontSize: 14,
              color:    state === "error" ? "#b45309" : "#6b7280",
              textAlign: "center",
              maxWidth: 280,
            }}
          >
            {statusText()}
          </div>

          {/* ── Transcript card (what the farmer said) ── */}
          {result?.transcript && (
            <div
              className="mt-4 rounded-xl p-4 max-w-md w-full"
              style={{
                background: "#f9fafb",
                borderLeft: "3px solid #3b6d11",
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 600, color: "#6b7280", marginBottom: 4, letterSpacing: "0.05em" }}>
                {t("youSaid") || "YOU SAID"}
              </div>
              <p style={{ fontSize: 14, color: "#1a1a1a", lineHeight: 1.6, margin: 0 }}>
                {result.transcript}
              </p>
            </div>
          )}

          {/* ── Agent response card ── */}
          {(state === "response" || state === "playing") && result?.agentReply && (
            <div
              className="mt-3 rounded-xl p-4 max-w-md w-full"
              style={{ background: "#fff", border: "1px solid #e5e7eb" }}
            >
              <AgentPill type={LANG_AGENT_MAP[result.detectedLang] ?? "market"} />
              <p style={{ fontSize: 14, color: "#1a1a1a", marginTop: 10, lineHeight: 1.6 }}>
                {result.agentReply}
              </p>
            </div>
          )}

          {/* ── Recent voice queries (static history, unchanged) ── */}
          <div className="mt-12 w-full max-w-md">
            <div style={{ fontSize: 12, fontWeight: 500, color: "#6b7280" }}>
              {t("recentVoiceQueries")}
            </div>
            <ul className="mt-2 divide-y" style={{ borderColor: "#f5f5f5" }}>
              {history.map((h, i) => (
                <li key={i} className="py-3 flex items-center gap-3">
                  <span className="flex-1 truncate" style={{ fontSize: 13, color: "#1a1a1a" }}>
                    {h.q}
                  </span>
                  <AgentPill type={h.agent} />
                  <span style={{ fontSize: 12, color: "#6b7280" }}>{h.t}</span>
                </li>
              ))}
            </ul>
          </div>

        </main>
      </div>

      {/* Hidden audio player for TTS playback */}
      <audio ref={audioPlayerRef} style={{ display: "none" }} />

      <MobileTabBar />
    </div>
  );
}
