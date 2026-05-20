const statusMap = {
  ok:  { bar: "#3b6d11" },
  low: { bar: "#f59e0b" },
  def: { bar: "#e24b4a" },
};

const defaultLabels = {
  ok:  "Good",
  low: "Low",
  def: "Deficient",
};

export function NutrientBar({
  label,
  value,
  max,
  status,
  statusLabel,
}: {
  label: string;
  value: number;
  max: number;
  status: "ok" | "low" | "def";
  statusLabel?: string;
}) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const s = statusMap[status];
  const displayLabel = statusLabel ?? defaultLabels[status];

  return (
    <div>
      <div className="flex items-center justify-between" style={{ fontSize: 13 }}>
        <span style={{ color: "var(--c-ink)" }}>{label}</span>
        <div className="flex items-center gap-2">
          <span style={{ color: "var(--c-muted)" }}>
            {value} / {max} kg/ha
          </span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 500,
              borderRadius: 999,
              padding: "1px 8px",
              background: s.bar + "22",
              color: s.bar,
            }}
          >
            {displayLabel}
          </span>
        </div>
      </div>
      <div
        className="w-full rounded-full mt-1.5"
        style={{ height: 5, background: "var(--c-border)" }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: s.bar,
            borderRadius: 999,
            transition: "width 0.5s ease",
          }}
        />
      </div>
    </div>
  );
}
