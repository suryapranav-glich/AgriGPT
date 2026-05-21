// =============================================================================
// src/routes/signup.tsx — Sign-up page (fixed hydration + Google OAuth)
// =============================================================================

import { useState, useEffect } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Leaf, AlertCircle, Loader2 } from "lucide-react";
import { Input, Button, Label } from "../components/ui/primitives";
import { useAuth } from "../contexts/AuthContext";
import { useTranslation } from "../contexts/LanguageContext";
import { LANGUAGES, type LangCode } from "../lib/translations";
import { authApi } from "../lib/api";

export const Route = createFileRoute("/signup")({ component: SignUp });

declare global {
  interface Window {
    _agrigpt_gsi_signup_cb?: (resp: { credential: string }) => void;
  }
}

// Separate portal container for signup page
let _gisContainerSignup: HTMLDivElement | null = null;
function getGisContainerSignup(): HTMLDivElement {
  if (!_gisContainerSignup) {
    _gisContainerSignup = document.createElement("div");
    _gisContainerSignup.id = "gis-btn-portal-signup";
    _gisContainerSignup.style.cssText =
      "width:100%;display:flex;justify-content:center;min-height:44px;";
    document.body.appendChild(_gisContainerSignup);
  }
  return _gisContainerSignup;
}

function SignUp() {
  const { signup, loginWithGoogle, error, loading, clearError } = useAuth();
  const { t, lang, setLang } = useTranslation();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [localErr, setLocalErr] = useState("");
  const [gsiReady, setGsiReady] = useState(false);

  // ── Mount GIS button into a portal div outside React ──────────────────────
  useEffect(() => {
    window._agrigpt_gsi_signup_cb = async (response: { credential: string }) => {
      setLocalErr("");
      try {
        await loginWithGoogle(response.credential, lang);
        navigate({ to: "/" });
      } catch {
        setLocalErr("Google sign-up failed. Please try again.");
      }
    };

    authApi
      .getConfig()
      .then(({ google_client_id }) => {
        const loadGsi = () => {
          if (!window.google) return;
          window.google.accounts.id.initialize({
            client_id: google_client_id,
            callback: window._agrigpt_gsi_signup_cb!,
          });
          const container = getGisContainerSignup();
          container.innerHTML = "";
          window.google.accounts.id.renderButton(container, {
            theme: "outline",
            size: "large",
            width: 352,
            text: "signup_with",
            logo_alignment: "center",
          });
          setGsiReady(true);
        };

        if (window.google) {
          loadGsi();
        } else if (!document.getElementById("gsi-script")) {
          const script = document.createElement("script");
          script.id = "gsi-script";
          script.src = "https://accounts.google.com/gsi/client";
          script.async = true;
          script.defer = true;
          script.onload = loadGsi;
          document.head.appendChild(script);
        } else {
          const poll = setInterval(() => {
            if (window.google) { clearInterval(poll); loadGsi(); }
          }, 100);
        }
      })
      .catch(() =>
        console.warn("[AgriGPT] Could not load Google client config from backend")
      );

    return () => {
      const c = getGisContainerSignup();
      c.style.display = "none";
    };
  }, [lang]);

  useEffect(() => {
    const slot = document.getElementById("gsi-slot-signup");
    const c = getGisContainerSignup();
    if (slot && c) {
      c.style.display = "flex";
      slot.appendChild(c);
    }
  });

  // ── Email / password submit ────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalErr("");
    clearError();

    if (!name.trim()) {
      setLocalErr("Please enter your full name.");
      return;
    }
    if (password.length < 6) {
      setLocalErr("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirm) {
      setLocalErr(t("passwordsDoNotMatch"));
      return;
    }

    try {
      // signup() creates the account but does NOT log in
      const createdEmail = await signup(name.trim(), email, password, lang);
      // Redirect to signin with email pre-filled and a success flag
      navigate({
        to: "/signin",
        search: { email: createdEmail, registered: "1" } as Record<string, string>,
      });
    } catch {
      /* error stored in context */
    }
  };

  const displayErr = localErr || error;

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-8"
      style={{ background: "var(--c-surface)" }}
    >
      <div
        className="w-full max-w-[420px] rounded-2xl p-8 relative"
        style={{ background: "var(--c-bg)", border: "1px solid var(--c-border)" }}
      >
        {/* Language selector */}
        <div className="absolute top-4 right-4">
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value as LangCode)}
            style={{
              fontSize: 13,
              padding: "4px 10px",
              borderRadius: 8,
              border: "1px solid var(--c-border)",
              background: "var(--c-bg)",
              color: "var(--c-ink)",
            }}
          >
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.flag} {l.native}
              </option>
            ))}
          </select>
        </div>

        {/* Logo */}
        <div className="flex items-center gap-2 justify-center">
          <Leaf size={18} style={{ color: "#3b6d11" }} strokeWidth={1.75} />
          <span style={{ fontSize: 15, fontWeight: 500, color: "var(--c-ink)" }}>
            AgriGPT
          </span>
        </div>

        <h1
          className="text-center mt-6"
          style={{ fontSize: 20, fontWeight: 500, color: "var(--c-ink)" }}
        >
          {t("createAccount")}
        </h1>

        {/* Error banner */}
        {displayErr && (
          <div
            className="mt-4 flex items-center gap-2 rounded-lg px-3 py-2"
            style={{
              background: "#fef2f2",
              border: "1px solid #fca5a5",
              fontSize: 13,
              color: "#dc2626",
            }}
          >
            <AlertCircle size={14} />
            <span>{displayErr}</span>
          </div>
        )}

        {/* Signup form */}
        <form className="mt-6 space-y-3" onSubmit={handleSubmit}>
          <div>
            <Label>{t("fullName")}</Label>
            <div className="mt-1.5">
              <Input
                id="signup-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ravi Kumar"
                required
                disabled={loading}
              />
            </div>
          </div>
          <div>
            <Label>{t("email")}</Label>
            <div className="mt-1.5">
              <Input
                id="signup-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                disabled={loading}
              />
            </div>
          </div>
          <div>
            <Label>{t("password")}</Label>
            <div className="mt-1.5">
              <Input
                id="signup-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 6 characters"
                required
                disabled={loading}
              />
            </div>
          </div>
          <div>
            <Label>{t("confirmPassword")}</Label>
            <div className="mt-1.5">
              <Input
                id="signup-confirm"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••"
                required
                disabled={loading}
              />
            </div>
          </div>

          <Button
            id="signup-submit"
            type="submit"
            className="w-full mt-2"
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 size={14} className="animate-spin" />
                Creating account…
              </span>
            ) : (
              t("createAccount")
            )}
          </Button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-3 my-5">
          <div className="flex-1" style={{ height: 1, background: "var(--c-border)" }} />
          <span style={{ fontSize: 12, color: "var(--c-muted)" }}>
            {t("orContinueWith")}
          </span>
          <div className="flex-1" style={{ height: 1, background: "var(--c-border)" }} />
        </div>

        {/* GIS button slot */}
        <div
          id="gsi-slot-signup"
          style={{ minHeight: 44, display: "flex", justifyContent: "center" }}
        >
          {!gsiReady && (
            <button
              type="button"
              disabled
              className="w-full flex items-center justify-center gap-2 py-2 rounded-md"
              style={{
                background: "var(--c-bg)",
                border: "1px solid var(--c-border)",
                fontSize: 13,
                color: "var(--c-muted)",
                cursor: "wait",
              }}
            >
              <GoogleIcon />
              {t("continueGoogle")}
            </button>
          )}
        </div>

        <p className="text-center mt-6" style={{ fontSize: 13, color: "var(--c-muted)" }}>
          {t("haveAccount")}{" "}
          <Link to="/signin" style={{ color: "#3b6d11" }}>
            {t("signIn")}
          </Link>
        </p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.99.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z" />
    </svg>
  );
}
