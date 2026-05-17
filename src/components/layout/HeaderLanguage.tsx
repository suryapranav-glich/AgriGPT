import { useEffect, useRef, useState } from "react";
import { Globe, ChevronDown, Check } from "lucide-react";
import { useTranslation } from "../../contexts/LanguageContext";
import { LANGUAGES, type LangCode } from "../../lib/translations";

export function HeaderLanguage() {
  const { lang, setLang } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = LANGUAGES.find((l) => l.code === lang) ?? LANGUAGES[0];

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-2 py-1.5 rounded-md hover:bg-[var(--c-hover)]"
        style={{ fontSize: 13, color: "var(--c-muted)" }}
      >
        <Globe size={16} strokeWidth={1.75} />
        <span className="hidden sm:inline">{current.native}</span>
        <ChevronDown size={14} strokeWidth={1.75} />
      </button>
      {open && (
        <div
          className="absolute right-0 mt-2 rounded-xl overflow-y-auto page-fade z-50"
          style={{
            background: "var(--c-bg)",
            border: "1px solid var(--c-border)",
            maxHeight: 280, width: 240,
          }}
        >
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              onClick={() => { setLang(l.code as LangCode); setOpen(false); }}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[var(--c-hover)]"
              style={{
                fontSize: 13,
                background: l.code === lang ? "#f0f5ea" : "transparent",
                color: "var(--c-ink)",
              }}
            >
              <span>{l.flag}</span>
              <span style={{ minWidth: 80 }}>{l.native}</span>
              <span className="flex-1 text-left" style={{ color: "var(--c-muted)", fontSize: 12 }}>{l.name}</span>
              {l.code === lang && <Check size={14} style={{ color: "#3b6d11" }} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
