import { useRef, useState } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  Home,
  Scan,
  MessageSquare,
  Droplets,
  TrendingUp,
  FileText,
  Layers,
  Mic,
  Leaf,
  ChevronLeft,
  ChevronRight,
  X,
} from "lucide-react";
import { useSidebar } from "../../contexts/SidebarContext";
import { useAuth } from "../../contexts/AuthContext";
import { useTranslation } from "../../contexts/LanguageContext";
import { ProfileDropdown, NoUserAvatar } from "../ui/ProfileDropdown";

const nav = [
  { to: "/", labelKey: "dashboard", icon: Home },
  { to: "/disease", labelKey: "diseaseDetection", icon: Scan },
  { to: "/chat", labelKey: "aiChat", icon: MessageSquare },
  { to: "/irrigation", labelKey: "irrigationPlanner", icon: Droplets },
  { to: "/market", labelKey: "marketPrices", icon: TrendingUp },
  { to: "/schemes", labelKey: "govtSchemes", icon: FileText },
  { to: "/soil", labelKey: "soilAnalyzer", icon: Layers },
  { to: "/fertilizer", labelKey: "fertilizerRecommendation", icon: Leaf },
  { to: "/voice", labelKey: "voiceMode", icon: Mic },
];

export function Sidebar() {
  const { open, toggle, mobileOpen, setMobileOpen } = useSidebar();
  const { user } = useAuth();
  const { t } = useTranslation();
  const { location } = useRouterState();
  const path = location.pathname;
  const [hovered, setHovered] = useState<string | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const userBtnRef = useRef<HTMLButtonElement>(null);

  const width = open ? 240 : 64;
  const initials = user
    ? user.name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "";

  const content = (isMobile: boolean) => (
    <aside
      className="flex flex-col h-full"
      style={{
        background: "var(--c-sidebar)",
        borderRight: "1px solid var(--c-border)",
        width: isMobile ? 260 : width,
        transition: "width 200ms ease",
      }}
    >
      <div
        className="flex items-center gap-2 px-3 h-14 border-b"
        style={{
          borderColor: "var(--c-border)",
          justifyContent: open || isMobile ? "space-between" : "center",
        }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <Leaf size={20} style={{ color: "#3b6d11", flexShrink: 0 }} strokeWidth={1.75} />
          {(open || isMobile) && (
            <span style={{ fontSize: 15, fontWeight: 500, color: "var(--c-ink)" }}>AgriGPT</span>
          )}
        </div>
        {isMobile ? (
          <button
            onClick={() => setMobileOpen(false)}
            className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-[var(--c-hover)]"
          >
            <X size={16} strokeWidth={1.75} style={{ color: "var(--c-muted)" }} />
          </button>
        ) : (
          <button
            onClick={toggle}
            className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-[#f0f5ea]"
            aria-label={open ? "Collapse sidebar" : "Expand sidebar"}
          >
            {open ? (
              <ChevronLeft size={18} strokeWidth={1.75} style={{ color: "var(--c-muted)" }} />
            ) : (
              <ChevronRight size={18} strokeWidth={1.75} style={{ color: "var(--c-muted)" }} />
            )}
          </button>
        )}
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {nav.map((item) => {
          const active = item.to === "/" ? path === "/" : path.startsWith(item.to);
          const Icon = item.icon;
          const collapsed = !open && !isMobile;
          return (
            <div
              key={item.to}
              className="relative"
              onMouseEnter={() => setHovered(item.to)}
              onMouseLeave={() => setHovered(null)}
            >
              <Link
                to={item.to}
                onClick={() => isMobile && setMobileOpen(false)}
                className="flex items-center gap-2.5 py-2 rounded-md transition-colors relative"
                style={{
                  fontSize: 13,
                  color: active ? "#3b6d11" : "var(--c-muted)",
                  background: active ? "#f0f5ea" : "transparent",
                  borderLeft: active ? "2px solid #3b6d11" : "2px solid transparent",
                  paddingLeft: collapsed ? 0 : 12,
                  paddingRight: collapsed ? 0 : 12,
                  justifyContent: collapsed ? "center" : "flex-start",
                }}
              >
                <Icon size={collapsed ? 18 : 16} strokeWidth={1.75} />
                {!collapsed && <span>{t(item.labelKey)}</span>}
              </Link>
              {collapsed && hovered === item.to && (
                <div
                  className="absolute z-50 rounded-md px-2.5 py-1.5 whitespace-nowrap"
                  style={{
                    left: 60,
                    top: 6,
                    background: "var(--c-bg)",
                    border: "1px solid var(--c-border)",
                    fontSize: 13,
                    color: "var(--c-ink)",
                  }}
                >
                  {t(item.labelKey)}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      <div className="border-t" style={{ borderColor: "var(--c-border)" }}>
        <button
          ref={userBtnRef}
          onClick={() => setProfileOpen((v) => !v)}
          className="w-full flex items-center gap-2.5 px-3 py-3 hover:bg-[var(--c-hover)]"
          style={{ justifyContent: !open && !isMobile ? "center" : "flex-start" }}
        >
          {user ? (
            <div
              className="rounded-full flex items-center justify-center flex-shrink-0"
              style={{
                width: 32,
                height: 32,
                background: "#f0f5ea",
                color: "#3b6d11",
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              {initials}
            </div>
          ) : (
            <NoUserAvatar />
          )}
          {(open || isMobile) && user && (
            <div className="flex-1 min-w-0 text-left">
              <div
                className="truncate"
                style={{ fontSize: 13, fontWeight: 500, color: "var(--c-ink)" }}
              >
                {user.name}
              </div>
              <div className="truncate" style={{ fontSize: 12, color: "var(--c-muted)" }}>
                {user.location ?? user.email}
              </div>
            </div>
          )}
        </button>
        {profileOpen && (
          <ProfileDropdown
            anchor={userBtnRef.current}
            position={!open && !isMobile ? "right" : "top-right"}
            onClose={() => setProfileOpen(false)}
          />
        )}
      </div>
    </aside>
  );

  return (
    <>
      <div
        className="hidden md:block fixed left-0 top-0 h-screen z-30"
        style={{ width, transition: "width 200ms ease" }}
      >
        {content(false)}
      </div>
      {mobileOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 z-40"
            style={{ background: "rgba(0,0,0,0.3)" }}
            onClick={() => setMobileOpen(false)}
          />
          <div className="md:hidden fixed left-0 top-0 h-screen z-50">{content(true)}</div>
        </>
      )}
    </>
  );
}

export function OpenSidebarButton() {
  const { open, setOpen } = useSidebar();
  if (open) return null;
  return (
    <button
      onClick={() => setOpen(true)}
      className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md"
      style={{
        background: "var(--c-bg)",
        border: "1px solid var(--c-border)",
        fontSize: 13,
        color: "var(--c-ink)",
      }}
    >
      <ChevronRight size={14} strokeWidth={1.75} />
      <span>Open sidebar</span>
    </button>
  );
}

// Backward-compat export so existing imports still resolve
export function MobileTabBar() {
  return null;
}
