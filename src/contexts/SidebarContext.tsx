import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type SidebarCtx = {
  open: boolean;
  setOpen: (v: boolean) => void;
  toggle: () => void;
  mobileOpen: boolean;
  setMobileOpen: (v: boolean) => void;
};

const Ctx = createContext<SidebarCtx | null>(null);
const KEY = "agrigpt_sidebar_open";

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [open, setOpenState] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const saved = localStorage.getItem(KEY);
    if (saved !== null) setOpenState(saved === "1");
  }, []);

  const setOpen = (v: boolean) => {
    setOpenState(v);
    if (typeof window !== "undefined") localStorage.setItem(KEY, v ? "1" : "0");
  };

  return (
    <Ctx.Provider value={{ open, setOpen, toggle: () => setOpen(!open), mobileOpen, setMobileOpen }}>
      {children}
    </Ctx.Provider>
  );
}

export function useSidebar() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSidebar must be inside SidebarProvider");
  return v;
}
