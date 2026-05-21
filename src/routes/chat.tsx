import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Sidebar, MobileTabBar } from "../components/layout/Sidebar";
import { ChatBubble } from "../components/chat/ChatBubble";
import { ChatInput } from "../components/chat/ChatInput";
import { LanguageSelector } from "../components/ui/LanguageSelector";
import { AgentPill, type AgentType } from "../components/ui/AgentPill";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/chat")({ component: ChatPage });

type Msg = { role: "user" | "ai"; text: string; agent?: AgentType };

function ChatPage() {
  const { t, lang, setLang } = useTranslation();
  const [listening, setListening] = useState(false);
  const [customMsgs, setCustomMsgs] = useState<Msg[]>([]);

  const history = [
    { title: t("chatHist1"), time: "2h ago" },
    { title: t("chatHist2"), time: "5h ago" },
    { title: t("chatHist3"), time: "Yesterday" },
    { title: t("chatHist4"), time: "2d ago" },
  ];

  const initialMsgs: Msg[] = [
    { role: "user", text: t("chatMsgQ1") },
    { role: "ai", agent: "disease" as AgentType, text: t("chatMsgA1") },
    { role: "user", text: t("chatMsgQ2") },
    { role: "ai", agent: "market" as AgentType, text: t("chatMsgA2") },
  ];

  const allMsgs = [...initialMsgs, ...customMsgs];

  const send = (text: string) => {
    setCustomMsgs((m) => [
      ...m,
      { role: "user", text },
      { role: "ai", agent: "general", text: t("gotItAnalysing") },
    ]);
  };

  return (
    <div className="min-h-screen flex" style={{ background: "#fff" }}>
      <Sidebar />
      <div className="flex-1 md:pl-[240px] flex pb-16 md:pb-0">
        <aside
          className="hidden md:flex flex-col border-r"
          style={{ width: 280, borderColor: "#e5e7eb" }}
        >
          <div
            className="px-4 h-14 flex items-center border-b"
            style={{ borderColor: "#e5e7eb", fontSize: 13, fontWeight: 500 }}
          >
            {t("chats")}
          </div>
          <div className="p-2 space-y-1 overflow-y-auto">
            {history.map((h, i) => (
              <button
                key={i}
                className="w-full text-left px-3 py-2 rounded-md"
                style={{ background: i === 0 ? "#f0f5ea" : "transparent" }}
                onMouseEnter={(e) => {
                  if (i !== 0) e.currentTarget.style.background = "#f7f8f6";
                }}
                onMouseLeave={(e) => {
                  if (i !== 0) e.currentTarget.style.background = "transparent";
                }}
              >
                <div className="truncate" style={{ fontSize: 13, color: "#1a1a1a" }}>
                  {h.title}
                </div>
                <div style={{ fontSize: 11, color: "#6b7280" }}>{h.time}</div>
              </button>
            ))}
          </div>
        </aside>

        <main className="flex-1 flex flex-col">
          <div
            className="h-14 px-6 flex items-center justify-between border-b"
            style={{ borderColor: "#e5e7eb" }}
          >
            <AgentPill type="general" />
            <LanguageSelector value={lang} onChange={setLang} />
          </div>
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4 max-w-3xl mx-auto w-full">
            {allMsgs.map((m, i) => (
              <ChatBubble key={i} {...m} />
            ))}
          </div>
          <div className="px-6 pb-6 max-w-3xl mx-auto w-full">
            <ChatInput onSend={send} listening={listening} onMic={() => setListening((v) => !v)} />
          </div>
        </main>
      </div>
      <MobileTabBar />
    </div>
  );
}
