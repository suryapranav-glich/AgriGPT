// =============================================================================
// src/routes/signin.tsx — Sign-in page (fixed hydration + Google OAuth)
//
// Fix: Google GIS SDK button is rendered into a div that is OUTSIDE React's
// control (appended to body, not managed by React), avoiding the removeChild
// hydration mismatch error in TanStack Start SSR.
// =============================================================================

import { useState, useEffect } from "react";
import { createFileRoute, Link, useNavigate, useSearch } from "@tanstack/react-router";
import { Leaf, AlertCircle, Loader2 } from "lucide-react";
import { Input, Button, Label } from "../components/ui/primitives";
import { useAuth } from "../contexts/AuthContext";
import { useTranslation } from "../contexts/LanguageContext";
import { LANGUAGES, type LangCode } from "../lib/translations";
import { authApi } from "../lib/api";

export const Route = createFileRoute("/signin")({ component: SignIn });

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (cfg: object) => void;
          prompt: () => void;
          renderButton: (el: HTMLElement, cfg: object) => void;
          cancel: () => void;
        };
      };
    };
    _agrigpt_gsi_callback?: (resp: { credential: string }) => void;
  }
}

// Keep a stable container element outside React's tree
let _gisContainer: HTMLDivElement | null = null;
function getGisContainer(): HTMLDivElement {
  if (!_gisContainer) {
    _gisContainer = document.createElement("div");
    _gisContainer.id = "gis-btn-portal";
    _gisContainer.style.cssText =
      "width:100%;display:flex;justify-content:center;min-height:44px;";
    document.body.appendChild(_gisContainer);
  }
  return _gisContainer;
}

function SignIn() {
  const { login, loginWithGoogle, error, loading, clearError } = useAuth();
  const { t, lang, setLang } = useTranslation();
  const navigate = useNavigate();

  const search = useSearch({ strict: false }) as { email?: string; registered?: string };
  const [email, setEmail] = useState(search.email || "");
  const [password, setPassword] = useState("");
  const [localErr, setLocalErr] = useState("");
  const [gsiReady, setGsiReady] = useState(false);

  // ── Mount GIS button into a portal div outside React ───────────────────────
  useEffect(() => {
    // Expose callback globally so GIS can call it
    window._agrigpt_gsi_callback = async (response: { credential: string }) => {
      setLocalErr("");
      try {
        await loginWithGoogle(response.credential, lang);
        navigate({ to: "/" });
      } catch {
        setLocalErr("Google sign-in failed. Please try again.");
      }
    };

    authApi
      .getConfig()
      .then(({ google_client_id }) => {
        const loadGsi = () => {
          if (!window.google) return;
          window.google.accounts.id.initialize({
            client_id: google_client_id,
            callback: window._agrigpt_gsi_callback!,
          });

          const container = getGisContainer();
          container.innerHTML = ""; // clear previous render
          window.google.accounts.id.renderButton(container, {
            theme: "outline",
            size: "large",
            width: 352,
            text: "continue_with",
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
          // Script tag exists but window.google not ready yet — poll briefly
          const poll = setInterval(() => {
            if (window.google) { clearInterval(poll); loadGsi(); }
          }, 100);
        }
      })
      .catch(() =>
        console.warn("[AgriGPT] Could not load Google client config from backend")
      );

    return () => {
      // Move GIS container off-screen when unmounting (keep it for reuse)
      const c = getGisContainer();
      c.style.display = "none";
    };
  }, [lang]);

  // ── Slot: a plain div where we will move the GIS container ─────────────────
  useEffect(() => {
    const slot = document.getElementById("gsi-slot-signin");
    const c = getGisContainer();
    if (slot && c) {
      c.style.display = "flex";
      slot.appendChild(c);
    }
  });

  // ── Email / password submit ─────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalErr("");
    clearError();
    try {
      await login(email, password);
      navigate({ to: "/" });
    } catch {
      /* error stored in context */
    }
  };

  const displayErr = localErr || error;

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
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
          {t("welcome")}
        </h1>
        <p className="text-center mt-1" style={{ fontSize: 13, color: "var(--c-muted)" }}>
          {t("signInSub")}
        </p>

        {/* Success banner after registration */}
        {search.registered === "1" && !displayErr && (
          <div
            className="mt-4 flex items-center gap-2 rounded-lg px-3 py-2"
            style={{
              background: "#f0fdf4",
              border: "1px solid #bbf7d0",
              fontSize: 13,
              color: "#166534",
            }}
          >
            <Leaf size={14} />
            <span>Account created successfully. Please sign in.</span>
          </div>
        )}

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

        {/* Email + Password form */}
        <form className="mt-6 space-y-3" onSubmit={handleSubmit}>
          <div>
            <Label>{t("email")}</Label>
            <div className="mt-1.5">
              <Input
                id="signin-email"
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
                id="signin-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={loading}
              />
            </div>
          </div>
          <Button
            id="signin-submit"
            type="submit"
            className="w-full mt-2"
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 size={14} className="animate-spin" />
                Signing in…
              </span>
            ) : (
              t("continueTxt")
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

        {/*
          Slot for the Google GIS button.
          The actual <div> injected by the GIS SDK lives in a body-level portal
          and is moved here via DOM appendChild — this avoids React's removeChild
          hydration crash.
        */}
        <div
          id="gsi-slot-signin"
          style={{ minHeight: 44, display: "flex", justifyContent: "center" }}
        >
          {/* Shown only while GIS SDK hasn't rendered yet */}
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
          {t("noAccount")}{" "}
          <Link to="/signup" style={{ color: "#3b6d11" }}>
            {t("signUp")}
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
