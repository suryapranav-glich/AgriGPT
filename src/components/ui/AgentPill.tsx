const agentConfig = {
  disease: { label: "Disease Agent", bg: "#fef3c7", color: "#92400e" },
  weather: { label: "Weather Agent", bg: "#dbeafe", color: "#1e40af" },
  market: { label: "Market Agent", bg: "#dcfce7", color: "#166534" },
  scheme: { label: "Scheme Agent", bg: "#ede9fe", color: "#5b21b6" },
  soil: { label: "Soil Agent", bg: "#ffedd5", color: "#9a3412" },
  general: { label: "AgriGPT", bg: "#f0f5ea", color: "#3b6d11" },
  fertilizer: { label: "Fertilizer Agent", bg: "#fce7f3", color: "#9d174d" },
} as const;

export type AgentType = keyof typeof agentConfig;

export function AgentPill({ type }: { type: AgentType }) {
  const c = agentConfig[type] ?? agentConfig.general;
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 500,
        borderRadius: 999,
        padding: "3px 10px",
        background: c.bg,
        color: c.color,
        whiteSpace: "nowrap",
        display: "inline-block",
      }}
    >
      {c.label}
    </span>
  );
}
