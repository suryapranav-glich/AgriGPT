import { Paperclip, Mic, ArrowUp } from "lucide-react";
import { useState } from "react";

export function ChatInput({ onSend, listening, onMic }:
  { onSend: (s: string) => void; listening?: boolean; onMic?: () => void }) {
  const [v, setV] = useState("");
  return (
    <div className="flex items-center gap-2 rounded-xl px-2 py-1.5"
         style={{ background: "#fff", border: "1px solid #e5e7eb" }}>
      <button className="p-2 rounded-md hover:bg-[#f7f8f6]">
        <Paperclip size={16} strokeWidth={1.75} style={{ color: "#6b7280" }} />
      </button>
      <button className="p-2 rounded-md hover:bg-[#f7f8f6] relative" onClick={onMic}>
        {listening
          ? <span className="w-3 h-3 rounded-full block animate-pulse" style={{ background: "#e24b4a" }} />
          : <Mic size={16} strokeWidth={1.75} style={{ color: "#6b7280" }} />}
      </button>
      <input
        value={v}
        onChange={(e) => setV(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && v.trim()) { onSend(v); setV(""); } }}
        placeholder={listening ? "Listening..." : "Ask anything in your language..."}
        className="flex-1 bg-transparent outline-none px-2 text-[14px]"
        style={{ color: "#1a1a1a" }}
      />
      <button
        onClick={() => { if (v.trim()) { onSend(v); setV(""); } }}
        className="w-8 h-8 rounded-md flex items-center justify-center"
        style={{ background: "#3b6d11", color: "#fff" }}>
        <ArrowUp size={16} strokeWidth={2} />
      </button>
    </div>
  );
}
