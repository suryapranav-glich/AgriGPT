import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Mic, Loader2 } from "lucide-react";
import { Sidebar, MobileTabBar } from "../components/layout/Sidebar";
import { Header } from "../components/layout/Header";
import { AgentPill, type AgentType } from "../components/ui/AgentPill";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/voice")({ component: Voice });

type State = "idle" | "listening" | "processing" | "response";

import { LANGUAGES } from "../lib/translations";

function Voice() {
  const [state, setState] = useState<State>("idle");
  const { t, lang } = useTranslation();

  const history = [
    { q: t("voiceQ1"), agent: "market" as const, t: t("tenMinAgo") },
    { q: t("voiceQ2"), agent: "weather" as const, t: t("oneHourAgo") },
    { q: t("voiceQ3"), agent: "scheme" as const, t: t("threeHoursAgo") },
  ];

  const click = () => {
    if (state === "idle") {
      setState("listening");
      setTimeout(() => setState("processing"), 2000);
      setTimeout(() => setState("response"), 3500);
    } else {
      setState("idle");
    }
  };

  const currentLangNative = LANGUAGES.find((l) => l.code === lang)?.native || "English";

  return (
    <div className="min-h-screen" style={{ background: "#fff" }}>
      <Sidebar />
      <div className="md:pl-[240px] pb-16 md:pb-0">
        <Header title={t("voiceMode")} />
        <main className="flex flex-col items-center justify-center px-6 py-16 page-fade">
          <div className="px-3 py-1 rounded-full text-[12px]"
               style={{ background: "#f0f5ea", color: "#3b6d11" }}>{t("speakingIn")} {currentLangNative}</div>

          <div className="relative mt-8">
            {state === "listening" && (
              <>
                <span className="absolute inset-0 rounded-full ripple-ring"
                      style={{ background: "#3b6d11", opacity: 0.15 }} />
                <span className="absolute inset-0 rounded-full ripple-ring"
                      style={{ background: "#3b6d11", opacity: 0.15, animationDelay: "0.6s" }} />
              </>
            )}
            <button onClick={click}
               className="relative w-20 h-20 rounded-full flex items-center justify-center"
               style={{ background: "#3b6d11", color: "#fff" }}>
              {state === "processing"
                ? <Loader2 size={28} className="animate-spin" />
                : <Mic size={28} strokeWidth={1.75} />}
            </button>
          </div>

          <div className="mt-6" style={{ fontSize: 14, color: "#6b7280" }}>
            {state === "idle" && t("tapToSpeak")}
            {state === "listening" && t("listening")}
            {state === "processing" && t("thinking")}
            {state === "response" && t("hereIsWhatIFound")}
          </div>

          {state === "response" && (
            <div className="mt-6 rounded-xl p-4 max-w-md w-full"
                 style={{ background: "#fff", border: "1px solid #e5e7eb" }}>
              <AgentPill type="market" />
              <p style={{ fontSize: 14, color: "#1a1a1a", marginTop: 10, lineHeight: 1.6 }}>
                {t("voiceResponseText")}
              </p>
            </div>
          )}

          <div className="mt-12 w-full max-w-md">
            <div style={{ fontSize: 12, fontWeight: 500, color: "#6b7280" }}>{t("recentVoiceQueries")}</div>
            <ul className="mt-2 divide-y" style={{ borderColor: "#f5f5f5" }}>
              {history.map((h, i) => (
                <li key={i} className="py-3 flex items-center gap-3">
                  <span className="flex-1 truncate" style={{ fontSize: 13, color: "#1a1a1a" }}>{h.q}</span>
                  <AgentPill type={h.agent} />
                  <span style={{ fontSize: 12, color: "#6b7280" }}>{h.t}</span>
                </li>
              ))}
            </ul>
          </div>
        </main>
      </div>
      <MobileTabBar />
    </div>
  );
}
