import { FileText, ExternalLink } from "lucide-react";
import { useTranslation } from "../../contexts/LanguageContext";

const categoryColors: Record<string, { bg: string; color: string }> = {
  subsidies:     { bg: "#f0f5ea", color: "#3b6d11" },
  insurance:     { bg: "#dbeafe", color: "#1e40af" },
  credit:        { bg: "#ede9fe", color: "#5b21b6" },
  irrigationTab: { bg: "#dcfce7", color: "#166534" },
  seeds:         { bg: "#ffedd5", color: "#9a3412" },
};

export function SchemeCard({
  nameKey,
  stateKey,
  categoryKey,
  summaryKey,
  url,
}: {
  nameKey: string;
  stateKey: string;
  categoryKey: string;
  summaryKey: string;
  url?: string;
}) {
  const { t } = useTranslation();
  const c = categoryColors[categoryKey] ?? { bg: "#f3f4f6", color: "#6b7280" };

  return (
    <div
      style={{
        background: "var(--c-bg)",
        border: "1px solid var(--c-border)",
        borderRadius: 12,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: c.bg,
              color: c.color,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <FileText size={15} strokeWidth={1.75} />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: "var(--c-ink)" }}>{t(nameKey)}</div>
            <div style={{ fontSize: 12, color: "var(--c-muted)" }}>{t(stateKey)}</div>
          </div>
        </div>

        {/* Category badge */}
        <span
          style={{
            fontSize: 11,
            fontWeight: 500,
            borderRadius: 999,
            padding: "3px 10px",
            background: c.bg,
            color: c.color,
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          {t(categoryKey)}
        </span>
      </div>

      {/* Summary */}
      <p style={{ fontSize: 13, color: "var(--c-muted)", lineHeight: 1.55 }}>{t(summaryKey)}</p>

      {/* Learn More — real anchor when url is provided */}
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            alignSelf: "flex-start",
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            fontSize: 12,
            color: "#3b6d11",
            textDecoration: "none",
            cursor: "pointer",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.textDecoration = "underline"; }}
          onMouseLeave={(e) => { e.currentTarget.style.textDecoration = "none"; }}
        >
          {t("learnMore")} <ExternalLink size={12} strokeWidth={1.75} />
        </a>
      ) : (
        <span
          style={{
            alignSelf: "flex-start",
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            fontSize: 12,
            color: "#9ca3af",
          }}
        >
          {t("learnMore")} <ExternalLink size={12} strokeWidth={1.75} />
        </span>
      )}
    </div>
  );
}
