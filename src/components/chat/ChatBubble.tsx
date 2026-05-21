import { AgentPill, type AgentType } from "../ui/AgentPill";

export function ChatBubble({
  role,
  text,
  agent,
}: {
  role: "user" | "ai";
  text: string;
  agent?: AgentType;
}) {
  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div
          className="max-w-[70%] px-3.5 py-2.5 rounded-2xl rounded-br-sm"
          style={{ background: "#f0f5ea", color: "#1a1a1a", fontSize: 14 }}
        >
          {text}
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-1.5 items-start">
      {agent && <AgentPill type={agent} />}
      <div
        className="max-w-[70%] px-3.5 py-2.5 rounded-2xl rounded-bl-sm"
        style={{ background: "#fff", border: "1px solid #e5e7eb", color: "#1a1a1a", fontSize: 14 }}
      >
        {text}
      </div>
    </div>
  );
}
