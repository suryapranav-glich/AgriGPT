import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef, useEffect } from "react";
import { Sidebar, MobileTabBar } from "../components/layout/Sidebar";
import { ChatBubble } from "../components/chat/ChatBubble";
import { ChatInput } from "../components/chat/ChatInput";
import { LanguageSelector } from "../components/ui/LanguageSelector";
import { AgentPill, type AgentType } from "../components/ui/AgentPill";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/chat")({ component: ChatPage });

// ── Types ────────────────────────────────────────────────────────────────────

type Msg = {
  role: "user" | "ai";
  text: string;
  agent?: AgentType;
  detectedLang?: string;
  langName?: string;
  sources?: string[];
  isLoading?: boolean;
  isError?: boolean;
  image_base64?: string;
  file_base64?: string;
  file_name?: string;
};

interface BackendResponse {
  response: string;
  detected_language: string;
  language_name: string;
  agent_type: string;
  sources: string[];
  english_query: string;
}

// ── Constants ────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ── Language badge ────────────────────────────────────────────────────────────

function LangBadge({ langCode, langName }: { langCode: string; langName: string }) {
  if (!langCode || langCode === "en") return null;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 7px",
        borderRadius: 9999,
        background: "#f0fdf4",
        color: "#16a34a",
        border: "1px solid #bbf7d0",
        marginTop: 4,
        marginBottom: 4,
      }}
    >
      🌐 {langName} detected
    </span>
  );
}

// ── Sources footer ─────────────────────────────────────────────────────────────

function SourcesFooter({ sources }: { sources: string[] }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;
  return (
    <div style={{ marginTop: 6 }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          fontSize: 10,
          color: "#6b7280",
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: 0,
          textDecoration: "underline dotted",
        }}
      >
        {open ? "Hide sources" : `${sources.length} source${sources.length > 1 ? "s" : ""} (ICAR/Govt)`}
      </button>
      {open && (
        <ul style={{ margin: "4px 0 0 0", padding: 0, listStyle: "none" }}>
          {sources.map((s, i) => (
            <li
              key={i}
              style={{
                fontSize: 10,
                color: "#6b7280",
                background: "#f9fafb",
                borderRadius: 4,
                padding: "2px 6px",
                marginTop: 2,
              }}
            >
              📖 {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Typing indicator ──────────────────────────────────────────────────────────

function TypingDots() {
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center", padding: "4px 0" }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "#16a34a",
            display: "inline-block",
            animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.6; }
          40% { transform: translateY(-6px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

interface DBResultSession {
  session_id: string;
  title: string;
  last_active: string;
}

function ChatPage() {
  const { t, lang, setLang } = useTranslation();
  const [listening, setListening] = useState(false);
  const [messages, setMessages] = useState<Msg[]>(() => [
    {
      role: "ai",
      agent: "general",
      text: "Namaste! I am KrishiMitra, your AI agricultural advisor. Ask me anything about paddy, cotton, soil management, irrigation, or market prices in your preferred language."
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<AgentType>("general");
  const [sessionId, setSessionId] = useState(() => `session_${Date.now()}`);
  const [sessions, setSessions] = useState<DBResultSession[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const fetchSessions = async () => {
    const token = localStorage.getItem("agrigpt_token");
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/api/sessions`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.sessions) {
          setSessions(data.sessions);
        }
      }
    } catch (e) {
      console.error("Error fetching sessions:", e);
    }
  };

  const handleSelectSession = async (sId: string) => {
    const token = localStorage.getItem("agrigpt_token");
    if (!token) return;
    setIsLoading(true);
    setSessionId(sId);
    try {
      const res = await fetch(`${API_BASE}/api/sessions/${sId}/messages`, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          const mappedMsgs: Msg[] = data.messages.map((m: any) => ({
            role: m.role === "user" ? "user" : "ai",
            text: m.text,
            agent: m.agent_type || undefined,
            detectedLang: m.detected_language || undefined,
            langName: m.language_name || undefined,
            sources: m.sources || [],
            image_base64: m.image_base64 || undefined,
            file_base64: m.file_base64 || undefined,
            file_name: m.file_name || undefined,
          }));
          setMessages(mappedMsgs);
          const aiMsgs = mappedMsgs.filter(m => m.role === "ai" && m.agent);
          if (aiMsgs.length > 0) {
            setCurrentAgent(aiMsgs[aiMsgs.length - 1].agent || "general");
          } else {
            setCurrentAgent("general");
          }
        } else {
          setMessages([
            {
              role: "ai",
              agent: "general",
              text: "Namaste! I am KrishiMitra, your AI agricultural advisor. Ask me anything about paddy, cotton, soil management, irrigation, or market prices in your preferred language."
            }
          ]);
        }
      }
    } catch (e) {
      console.error("Error loading session messages:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewChat = () => {
    setSessionId(`session_${Date.now()}`);
    setMessages([
      {
        role: "ai",
        agent: "general",
        text: "Namaste! I am KrishiMitra, your AI agricultural advisor. Ask me anything about paddy, cotton, soil management, irrigation, or market prices in your preferred language."
      }
    ]);
    setCurrentAgent("general");
  };

  // Load chat sessions history list on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Voice input via Web Speech API
  const startVoiceInput = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice input not supported in this browser. Please use Chrome.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = lang === "te" ? "te-IN" : lang === "hi" ? "hi-IN" : "en-IN";

    setListening(true);
    recognition.start();

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setListening(false);
      send(transcript);
    };

    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);
  };

  const send = async (text: string, imageBase64?: string, fileBase64?: string, fileName?: string) => {
    if (!text.trim() && !imageBase64 && !fileBase64) return;

    // Add user message immediately
    const userMsg: Msg = {
      role: "user",
      text: text || (imageBase64 ? "Uploaded image" : "Uploaded file"),
      image_base64: imageBase64,
      file_base64: fileBase64,
      file_name: fileName,
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    // Add loading placeholder
    const loadingMsg: Msg = { role: "ai", text: "", agent: currentAgent, isLoading: true };
    setMessages((prev) => [...prev, loadingMsg]);

    try {
      const token = localStorage.getItem("agrigpt_token");
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "Authorization": `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          message: text || (imageBase64 ? "Analyzing the uploaded image." : "Analyzing the uploaded document."),
          session_id: sessionId,
          image_base64: imageBase64,
          file_base64: fileBase64,
          file_name: fileName,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Server error" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data: BackendResponse = await res.json();

      // Update agent type in header
      setCurrentAgent((data.agent_type as AgentType) || "general");

      // Replace loading placeholder with real answer
      const aiMsg: Msg = {
        role: "ai",
        text: data.response,
        agent: (data.agent_type as AgentType) || "general",
        detectedLang: data.detected_language,
        langName: data.language_name,
        sources: data.sources,
        isLoading: false,
      };

      setMessages((prev) => {
        const updated = [...prev];
        const lastIdx = updated.map((m) => m.isLoading).lastIndexOf(true);
        if (lastIdx !== -1) updated[lastIdx] = aiMsg;
        return updated;
      });

      // Refresh list
      fetchSessions();
    } catch (error) {
      const errText =
        error instanceof Error
          ? `⚠️ ${error.message}`
          : "⚠️ Could not reach the server. Please check your connection.";

      setMessages((prev) => {
        const updated = [...prev];
        const lastIdx = updated.map((m) => m.isLoading).lastIndexOf(true);
        if (lastIdx !== -1) {
          updated[lastIdx] = {
            role: "ai",
            text: errText,
            agent: "general",
            isLoading: false,
            isError: true,
          };
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getRelativeTime = (isoString: string) => {
    if (!isoString) return "Recently";
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) return "Recently";
      const diffMs = Date.now() - date.getTime();
      const diffMins = Math.round(diffMs / 60000);
      if (diffMins < 1) return "Just now";
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.round(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.round(diffHours / 24);
      return `${diffDays}d ago`;
    } catch (e) {
      return "Recently";
    }
  };

  return (
    <div className="min-h-screen flex" style={{ background: "#fff" }}>
      <Sidebar />

      <div className="flex-1 md:pl-[240px] flex pb-16 md:pb-0">
        {/* ── Chat history sidebar ─────────────────────────────────────── */}
        <aside
          className="hidden md:flex flex-col border-r"
          style={{ width: 280, borderColor: "#e5e7eb" }}
        >
          <div
            className="px-4 h-14 flex items-center justify-between border-b shrink-0"
            style={{ borderColor: "#e5e7eb" }}
          >
            <span style={{ fontSize: 13, fontWeight: 600, color: "#374151" }}>
              {t("chats")}
            </span>
            <button
              onClick={startNewChat}
              className="text-xs font-semibold px-2.5 py-1 rounded bg-[#3b6d11] hover:bg-[#2d520d] text-white transition-colors cursor-pointer"
            >
              + New Chat
            </button>
          </div>
          <div className="p-2 space-y-1 overflow-y-auto flex-1">
            {sessions.length === 0 ? (
              <div className="text-xs text-gray-400 p-4 text-center">
                No past conversations.
              </div>
            ) : (
              sessions.map((h, i) => (
                <button
                  key={h.session_id}
                  onClick={() => handleSelectSession(h.session_id)}
                  className="w-full text-left px-3 py-2 rounded-md transition-colors cursor-pointer group"
                  style={{ background: h.session_id === sessionId ? "#f0f5ea" : "transparent" }}
                >
                  <div
                    className="truncate font-medium transition-colors"
                    style={{
                      fontSize: 13,
                      color: h.session_id === sessionId ? "#1b3c1b" : "#4b5563"
                    }}
                  >
                    {h.title || "Untitled Conversation"}
                  </div>
                  <div style={{ fontSize: 11, color: "#9ca3af" }}>
                    {getRelativeTime(h.last_active)}
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        {/* ── Main Chat Area ───────────────────────────────────────────── */}
        <main className="flex-1 flex flex-col h-screen overflow-hidden">
          <div
            className="h-14 px-6 flex items-center justify-between border-b shrink-0"
            style={{ borderColor: "#e5e7eb" }}
          >
            <div className="flex items-center gap-2">
              <AgentPill type={currentAgent} />
              {sessionId && (
                <span className="hidden sm:inline text-xs text-gray-400 font-mono">
                  ID: {sessionId.substring(0, 15)}...
                </span>
              )}
            </div>
            <LanguageSelector value={lang} onChange={setLang} />
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4 max-w-3xl mx-auto w-full">
            {messages.map((m, i) => (
              <div key={i} className="flex flex-col gap-1">
                <ChatBubble
                  role={m.role}
                  text={m.text}
                  agent={m.agent}
                  image_base64={m.image_base64}
                  file_base64={m.file_base64}
                  file_name={m.file_name}
                />
                {m.role === "ai" && (
                  <div style={{ paddingLeft: m.agent ? 0 : 0 }}>
                    {m.isLoading ? (
                      <TypingDots />
                    ) : (
                      <div className="flex flex-col items-start gap-1">
                        <LangBadge langCode={m.detectedLang || ""} langName={m.langName || ""} />
                        <SourcesFooter sources={m.sources || []} />
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <div className="px-6 pb-6 max-w-3xl mx-auto w-full shrink-0">
            <ChatInput onSend={send} listening={listening} onMic={startVoiceInput} />
          </div>
        </main>
      </div>

      <MobileTabBar />
    </div>
  );
}

