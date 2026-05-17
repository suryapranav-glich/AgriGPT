import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Leaf } from "lucide-react";
import { Input, Button, Label } from "../components/ui/primitives";
import { useAuth } from "../contexts/AuthContext";
import { useTranslation } from "../contexts/LanguageContext";
import { LANGUAGES, type LangCode } from "../lib/translations";

export const Route = createFileRoute("/signin")({ component: SignIn });

function SignIn() {
  const { login, loginWithGoogle } = useAuth();
  const { t, lang, setLang } = useTranslation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    const name = email.split("@")[0].replace(/\./g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    login({ name: name || "Farmer", email, language: lang, location: "Karnataka" });
    navigate({ to: "/" });
  };

  const google = () => { loginWithGoogle(); navigate({ to: "/" }); };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: "var(--c-surface)" }}>
      <div className="w-full max-w-[420px] rounded-2xl p-8 relative"
           style={{ background: "var(--c-bg)", border: "1px solid var(--c-border)" }}>
           
        <div className="absolute top-4 right-4">
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value as LangCode)}
            style={{ fontSize: 13, padding: "4px 10px", borderRadius: 8,
                     border: "1px solid var(--c-border)", background: "var(--c-bg)", color: "var(--c-ink)" }}
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.flag} {l.native}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2 justify-center">
          <Leaf size={18} style={{ color: "#3b6d11" }} strokeWidth={1.75} />
          <span style={{ fontSize: 15, fontWeight: 500, color: "var(--c-ink)" }}>AgriGPT</span>
        </div>
        <h1 className="text-center mt-6" style={{ fontSize: 20, fontWeight: 500, color: "var(--c-ink)" }}>
          {t("welcome")}
        </h1>
        <p className="text-center mt-1" style={{ fontSize: 13, color: "var(--c-muted)" }}>
          {t("signInSub")}
        </p>

        <form className="mt-6 space-y-3" onSubmit={submit}>
          <div>
            <Label>{t("email")}</Label>
            <div className="mt-1.5"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required /></div>
          </div>
          <div>
            <Label>{t("password")}</Label>
            <div className="mt-1.5"><Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required /></div>
          </div>
          <Button type="submit" className="w-full mt-2">{t("continueTxt")}</Button>
        </form>

        <div className="flex items-center gap-3 my-5">
          <div className="flex-1" style={{ height: 1, background: "var(--c-border)" }} />
          <span style={{ fontSize: 12, color: "var(--c-muted)" }}>{t("orContinueWith")}</span>
          <div className="flex-1" style={{ height: 1, background: "var(--c-border)" }} />
        </div>

        <button onClick={google} className="w-full flex items-center justify-center gap-2 py-2 rounded-md hover:bg-[var(--c-hover)]"
                style={{ background: "var(--c-bg)", border: "1px solid var(--c-border)", fontSize: 13, color: "var(--c-ink)" }}>
          <GoogleIcon />
          {t("continueGoogle")}
        </button>

        <p className="text-center mt-6" style={{ fontSize: 13, color: "var(--c-muted)" }}>
          {t("noAccount")} <Link to="/signup" style={{ color: "#3b6d11" }}>{t("signUp")}</Link>
        </p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.99.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/>
    </svg>
  );
}

