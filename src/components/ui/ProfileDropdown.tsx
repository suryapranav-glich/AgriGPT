import { useEffect, useRef } from "react";
import { useNavigate } from "@tanstack/react-router";
import { LogOut, User, Moon, Sun } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { useTranslation } from "../../contexts/LanguageContext";

export function NoUserAvatar() {
  return (
    <div
      style={{
        width: 32,
        height: 32,
        borderRadius: "50%",
        background: "#f3f4f6",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <User size={16} strokeWidth={1.75} style={{ color: "#6b7280" }} />
    </div>
  );
}

export function ProfileDropdown({
  anchor,
  position = "bottom-right",
  onClose,
}: {
  anchor: HTMLElement | null;
  position?: "bottom-right" | "top-right" | "right";
  onClose: () => void;
}) {
  const { user, logout } = useAuth();
  const { dark, toggle } = useTheme();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handle = (e: MouseEvent) => {
      if (
        ref.current &&
        !ref.current.contains(e.target as Node) &&
        anchor &&
        !anchor.contains(e.target as Node)
      ) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, [anchor, onClose]);

  const posStyle: React.CSSProperties = (() => {
    if (position === "top-right") return { bottom: "100%", left: 0, marginBottom: 8 };
    if (position === "right") return { left: "100%", bottom: 0, marginLeft: 8 };
    return { top: "100%", right: 0, marginTop: 8 };
  })();

  const handleLogout = () => {
    logout();
    onClose();
    navigate({ to: "/signin" });
  };

  return (
    <div
      ref={ref}
      className="absolute z-50 rounded-xl overflow-hidden page-fade"
      style={{
        ...posStyle,
        background: "var(--c-bg)",
        border: "1px solid var(--c-border)",
        minWidth: 200,
        boxShadow: "0 8px 24px rgba(0,0,0,0.08)",
      }}
    >
      {user && (
        <div
          style={{
            padding: "12px 14px",
            borderBottom: "1px solid var(--c-border)",
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 500, color: "var(--c-ink)" }}>{user.name}</div>
          <div style={{ fontSize: 12, color: "var(--c-muted)" }}>{user.email}</div>
        </div>
      )}

      <button
        onClick={toggle}
        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 hover:bg-[var(--c-hover)]"
        style={{ fontSize: 13, color: "var(--c-ink)" }}
      >
        {dark ? <Sun size={14} strokeWidth={1.75} /> : <Moon size={14} strokeWidth={1.75} />}
        {dark ? t("lightMode") : t("darkMode")}
      </button>

      <button
        onClick={handleLogout}
        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 hover:bg-[var(--c-hover)]"
        style={{ fontSize: 13, color: "#e24b4a" }}
      >
        <LogOut size={14} strokeWidth={1.75} />
        {t("logout")}
      </button>
    </div>
  );
}
