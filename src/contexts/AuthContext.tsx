import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type User = {
  name: string;
  email: string;
  language: string;
  location?: string;
};

type AuthCtx = {
  user: User | null;
  isAuthenticated: boolean;
  ready: boolean;
  login: (u: User) => void;
  signup: (u: User) => void;
  loginWithGoogle: () => void;
  logout: () => void;
};

const Ctx = createContext<AuthCtx | null>(null);
const KEY = "agrigpt_user";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem(KEY);
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch {
        localStorage.removeItem(KEY);
      }
    }
    setReady(true);
  }, []);

  const persist = (u: User | null) => {
    setUser(u);
    if (typeof window !== "undefined") {
      if (u) localStorage.setItem(KEY, JSON.stringify(u));
      else localStorage.removeItem(KEY);
    }
  };

  const login = (u: User) => persist(u);
  const signup = (u: User) => persist(u);
  const loginWithGoogle = () =>
    persist({ name: "Demo Farmer", email: "demo@agrigpt.in", language: "en", location: "Karnataka" });
  const logout = () => persist(null);

  return (
    <Ctx.Provider value={{ user, isAuthenticated: !!user, ready, login, signup, loginWithGoogle, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be inside AuthProvider");
  return v;
}
