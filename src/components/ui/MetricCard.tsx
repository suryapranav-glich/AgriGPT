import type { ReactNode } from "react";

export function MetricCard({
  label,
  value,
  sub,
  icon,
}: {
  label: string;
  value: ReactNode;
  sub?: string;
  icon?: ReactNode;
}) {
  return (
    <div
      style={{
        background: "var(--c-bg)",
        border: "1px solid var(--c-border)",
        borderRadius: 12,
        padding: 16,
      }}
    >
      <div className="flex items-center justify-between">
        <div
          style={{
            fontSize: 12,
            fontWeight: 500,
            color: "var(--c-muted)",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
          }}
        >
          {label}
        </div>
        {icon && (
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 8,
              background: "#f0f5ea",
              color: "#3b6d11",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {icon}
          </div>
        )}
      </div>
      <div style={{ fontSize: 20, fontWeight: 500, color: "var(--c-ink)", marginTop: 10 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: "var(--c-muted)", marginTop: 3 }}>{sub}</div>}
    </div>
  );
}
