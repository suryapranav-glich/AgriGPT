import { useRef, useState } from "react";
import { Menu } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useSidebar } from "../../contexts/SidebarContext";
import { ProfileDropdown, NoUserAvatar } from "../ui/ProfileDropdown";
import { HeaderLanguage } from "./HeaderLanguage";

export function Header({ title }: { title: string }) {
  const { user } = useAuth();
  const { setMobileOpen } = useSidebar();
  const [open, setOpen] = useState(false);
  const avatarRef = useRef<HTMLButtonElement>(null);

  const initials = user ? user.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase() : "";

  return (
    <header
      className="h-14 flex items-center justify-between px-4 md:px-6 border-b sticky top-0 z-20"
      style={{ background: "var(--c-bg)", borderColor: "var(--c-border)" }}
    >
      <div className="flex items-center gap-2">
        <button
          onClick={() => setMobileOpen(true)}
          className="md:hidden w-8 h-8 rounded-md flex items-center justify-center hover:bg-[var(--c-hover)]"
          aria-label="Open menu"
        >
          <Menu size={18} strokeWidth={1.75} style={{ color: "var(--c-muted)" }} />
        </button>
        <h1 style={{ fontSize: 16, fontWeight: 500, color: "var(--c-ink)" }}>{title}</h1>
      </div>
      <div className="flex items-center gap-2">
        <HeaderLanguage />
        <button
          ref={avatarRef}
          onClick={() => setOpen((v) => !v)}
          className="rounded-full flex items-center justify-center"
          style={user
            ? { width: 32, height: 32, background: "#f0f5ea", color: "#3b6d11", fontSize: 13, fontWeight: 500 }
            : { width: 32, height: 32 }}
          aria-label="Account"
        >
          {user ? initials : <NoUserAvatar />}
        </button>
        {open && (
          <ProfileDropdown
            anchor={avatarRef.current}
            position="bottom-right"
            onClose={() => setOpen(false)}
          />
        )}
      </div>
    </header>
  );
}
