import { LANGUAGES, type LangCode } from "../../lib/translations";

export function LanguageSelector({
  value,
  onChange,
}: {
  value: LangCode;
  onChange: (v: LangCode) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as LangCode)}
      style={{
        fontSize: 13,
        padding: "4px 10px",
        borderRadius: 8,
        border: "1px solid var(--c-border)",
        background: "var(--c-bg)",
        color: "var(--c-ink)",
        outline: "none",
        cursor: "pointer",
      }}
    >
      {LANGUAGES.map((l) => (
        <option key={l.code} value={l.code}>
          {l.flag} {l.native}
        </option>
      ))}
    </select>
  );
}
