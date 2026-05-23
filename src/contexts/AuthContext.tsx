// =============================================================================
// src/contexts/AuthContext.tsx — Real auth context backed by FastAPI + MongoDB
//
// • email/password login → POST /auth/signin (bcrypt verified on backend)
// • signup → POST /auth/signup (bcrypt hashed + stored in MongoDB)
// • Google OAuth → Google popup → id_token sent to POST /auth/google
//   (Client ID is fetched from /auth/config — NEVER hardcoded here)
// • JWT stored in localStorage, sent as Bearer header on every request
// • On mount, /auth/me is called to restore session from existing token
// =============================================================================

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authApi, setToken, getToken, clearToken, type UserOut } from "../lib/api";

export type User = UserOut & { token: string };

type AuthCtx = {
  user: User | null;
  isAuthenticated: boolean;
  ready: boolean;
  error: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string, language?: string) => Promise<string>;
  loginWithGoogle: (idToken: string, language?: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // ── On mount: restore session from existing JWT ──────────────────────────
  useEffect(() => {
    if (typeof window === "undefined") {
      setReady(true);
      return;
    }
    const existingToken = getToken();
    if (!existingToken) {
      setReady(true);
      return;
    }
    authApi
      .me()
      .then(({ access_token, user: u }) => {
        setUser({ ...u, token: access_token });
      })
      .catch(() => {
        // Token expired or invalid — clear it
        clearToken();
      })
      .finally(() => setReady(true));
  }, []);

  const persist = (token: string, u: UserOut) => {
    setToken(token);
    setUser({ ...u, token });
  };

  // ── Email/password login ─────────────────────────────────────────────────
  const login = async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const { access_token, user: u } = await authApi.signin({ email, password });
      persist(access_token, u);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Sign in failed";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // ── Email/password signup (account creation only — does NOT log in) ────────
  // Returns the email so the signin page can pre-fill it.
  const signup = async (name: string, email: string, password: string, language = "en"): Promise<string> => {
    setLoading(true);
    setError(null);
    try {
      // Call backend to create the account — but do NOT persist the token
      await authApi.signup({ name, email, password, language });
      // Return the email so signin page can pre-fill it
      return email;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Sign up failed";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // ── Google OAuth login ───────────────────────────────────────────────────
  // idToken is obtained from Google Identity Services on the frontend,
  // then sent to /auth/google for server-side verification.
  const loginWithGoogle = async (idToken: string, language = "en") => {
    setLoading(true);
    setError(null);
    try {
      const { access_token, user: u } = await authApi.googleAuth(idToken, language);
      persist(access_token, u);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Google sign in failed";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // ── Logout ───────────────────────────────────────────────────────────────
  const logout = () => {
    clearToken();
    setUser(null);
    setError(null);
    queryClient.clear();
    // Fire-and-forget — backend is stateless, just clears server-side hints
    authApi.logout().catch(() => {});
  };

  const clearError = () => setError(null);

  return (
    <Ctx.Provider
      value={{
        user,
        isAuthenticated: !!user,
        ready,
        error,
        loading,
        login,
        signup,
        loginWithGoogle,
        logout,
        clearError,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be inside AuthProvider");
  return v;
}
