import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { translations, type LangCode } from "../lib/translations";

type LangCtx = {
  lang: LangCode;
  setLang: (l: LangCode) => void;
  t: (key: string) => string;
};

const Ctx = createContext<LangCtx | null>(null);
const KEY = "agrigpt_lang";

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<LangCode>("en");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem(KEY) as LangCode | null;
    if (saved && saved in translations) setLangState(saved);
  }, []);

  const setLang = (l: LangCode) => {
    setLangState(l);
    if (typeof window !== "undefined") localStorage.setItem(KEY, l);
  };

  const t = (key: string): string => translations[lang]?.[key] ?? translations["en"]?.[key] ?? key;

  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export function useTranslation() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useTranslation must be inside LanguageProvider");
  return v;
}
