import { forwardRef } from "react";
import type { ReactNode, CSSProperties, InputHTMLAttributes, SelectHTMLAttributes } from "react";

// ── Card ─────────────────────────────────────────────────────────────────────
export function Card({
  children,
  className = "",
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div
      className={className}
      style={{
        background: "var(--c-bg)",
        border: "1px solid var(--c-border)",
        borderRadius: 12,
        padding: 16,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

// ── Label ─────────────────────────────────────────────────────────────────────
export function Label({ children }: { children: ReactNode }) {
  return (
    <div style={{ fontSize: 12, fontWeight: 500, color: "var(--c-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
      {children}
    </div>
  );
}

// ── SeverityBadge ─────────────────────────────────────────────────────────────
const severityMap = {
  low: { label: "Low", bg: "#fef3c7", color: "#92400e" },
  med: { label: "Medium", bg: "#fee2e2", color: "#991b1b" },
  high: { label: "High", bg: "#fecaca", color: "#7f1d1d" },
};

export function SeverityBadge({ level }: { level: "low" | "med" | "high" }) {
  const s = severityMap[level];
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 500,
        borderRadius: 999,
        padding: "2px 8px",
        background: s.bg,
        color: s.color,
      }}
    >
      {s.label}
    </span>
  );
}

// ── Pill ──────────────────────────────────────────────────────────────────────
const toneMap = {
  brand: { bg: "#f0f5ea", color: "#3b6d11" },
  muted: { bg: "#f3f4f6", color: "#6b7280" },
  danger: { bg: "#fee2e2", color: "#991b1b" },
};

export function Pill({
  children,
  tone = "muted",
}: {
  children: ReactNode;
  tone?: keyof typeof toneMap;
}) {
  const s = toneMap[tone];
  return (
    <span
      style={{
        fontSize: 11,
        fontWeight: 500,
        borderRadius: 999,
        padding: "2px 8px",
        background: s.bg,
        color: s.color,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}

// ── Button ─────────────────────────────────────────────────────────────────────
export function Button({
  children,
  className = "",
  type = "button",
  onClick,
  variant = "primary",
  disabled = false,
  style: styleProp,
}: {
  children: ReactNode;
  className?: string;
  type?: "button" | "submit" | "reset";
  onClick?: () => void;
  variant?: "primary" | "secondary";
  disabled?: boolean;
  style?: CSSProperties;
}) {
  const isPrimary = variant === "primary";
  return (
    <button
      type={type}
      onClick={onClick}
      className={className}
      disabled={disabled}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "8px 16px",
        borderRadius: 8,
        fontSize: 14,
        fontWeight: 500,
        cursor: disabled ? "not-allowed" : "pointer",
        border: isPrimary ? "none" : "1px solid var(--c-border)",
        background: isPrimary ? "#3b6d11" : "var(--c-bg)",
        color: isPrimary ? "#fff" : "var(--c-ink)",
        opacity: disabled ? 0.55 : 1,
        transition: "opacity 0.15s",
        ...styleProp,
      }}
      onMouseEnter={(e) => { if (!disabled) e.currentTarget.style.opacity = "0.88"; }}
      onMouseLeave={(e) => { if (!disabled) e.currentTarget.style.opacity = "1"; }}
    >
      {children}
    </button>
  );
}

// ── Input ─────────────────────────────────────────────────────────────────────
export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement> & { className?: string }
>(function Input({ className = "", style, ...props }, ref) {
  return (
    <input
      ref={ref}
      className={className}
      {...props}
      style={{
        width: "100%",
        padding: "8px 12px",
        borderRadius: 8,
        border: "1px solid var(--c-border)",
        background: "var(--c-bg)",
        color: "var(--c-ink)",
        fontSize: 14,
        outline: "none",
        boxSizing: "border-box",
        ...style,
      }}
      onFocus={(e) => { e.currentTarget.style.borderColor = "#3b6d11"; }}
      onBlur={(e) => { e.currentTarget.style.borderColor = "var(--c-border)"; }}
    />
  );
});

// ── Select ─────────────────────────────────────────────────────────────────────
export function Select({
  className = "",
  style,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { className?: string }) {
  return (
    <select
      className={className}
      {...props}
      style={{
        padding: "8px 12px",
        borderRadius: 8,
        border: "1px solid var(--c-border)",
        background: "var(--c-bg)",
        color: "var(--c-ink)",
        fontSize: 14,
        outline: "none",
        cursor: "pointer",
        ...style,
      }}
    >
      {children}
    </select>
  );
}
