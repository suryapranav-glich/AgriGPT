// =============================================================================
// src/routes/index.tsx — Dashboard (live data from MongoDB via /dashboard/metrics)
// =============================================================================

import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Sprout,
  Activity,
  Droplets,
  TrendingUp,
  ArrowUp,
  ArrowDown,
  Upload,
  MessageSquare,
  BarChart3,
  FileSearch,
  Cloud,
  CloudRain,
  Sun,
  CloudSnow,
  CloudSun,
  RefreshCw,
  AlertCircle,
  Loader2,
  MapPinOff,
  CloudOff,
} from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, Label, SeverityBadge, Pill } from "../components/ui/primitives";
import { AgentPill, type AgentType } from "../components/ui/AgentPill";
import { useTranslation } from "../contexts/LanguageContext";
import { useAuth } from "../contexts/AuthContext";
import { useDashboardMetrics } from "../hooks/useDashboard";
import { useWeather } from "../hooks/useWeather";
import type { ActivityItem } from "../lib/api";

export const Route = createFileRoute("/")({ component: Dashboard });



// Severity level helper
type SevLevel = "low" | "med" | "high" | "none";
function toSevLevel(s?: string): SevLevel {
  if (s === "severe") return "high";
  if (s === "moderate") return "med";
  if (s === "mild") return "low";
  return "none";
}

// Skeleton card for loading state
function SkeletonCard() {
  return (
    <div
      className="rounded-xl p-4 animate-pulse"
      style={{ background: "#f3f4f6", border: "1px solid #e5e7eb", height: 90 }}
    />
  );
}

function Dashboard() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { data: metrics, isLoading, isError, refetch } = useDashboardMetrics();
  const { data: weather, loading: weatherLoading, error: weatherError, permissionDenied } = useWeather();

  // ── Loading state ──────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <PageWrapper title={t("dashboard")}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-3 mt-3">
          <div className="lg:col-span-3"><SkeletonCard /></div>
          <div className="lg:col-span-2"><SkeletonCard /></div>
        </div>
      </PageWrapper>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────
  if (isError || !metrics) {
    return (
      <PageWrapper title={t("dashboard")}>
        <div
          className="flex flex-col items-center justify-center gap-4 rounded-xl p-8 mt-4"
          style={{ border: "1px dashed #e5e7eb", background: "#fafafa" }}
        >
          <AlertCircle size={32} style={{ color: "#ef4444" }} />
          <p style={{ fontSize: 14, color: "#6b7280" }}>
            Could not load dashboard data. Make sure the backend is running at{" "}
            <code style={{ background: "#f3f4f6", padding: "2px 6px", borderRadius: 4, fontSize: 12 }}>
              http://localhost:8000
            </code>
          </p>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 rounded-lg px-4 py-2"
            style={{ background: "#3b6d11", color: "#fff", fontSize: 13 }}
          >
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      </PageWrapper>
    );
  }

  // ── Derived values from live MongoDB data ──────────────────────────────────
  const activeCrop    = metrics.active_crop || "Not specified";
  const lastDiag      = metrics.last_diagnosis || "No diagnosis yet";
  const diagSeverity  = toSevLevel(metrics.last_diagnosis_severity);
  const nextIrrigation = metrics.next_irrigation || "Not scheduled";
  const mandiPrice    = metrics.mandi_price != null
    ? `₹${metrics.mandi_price.toLocaleString("en-IN")}`
    : "—";
  const mandiChange   = metrics.mandi_price_change ?? 0;
  const mandiLocation = metrics.mandi_location || "Local";

  // ── Activity feed from MongoDB ─────────────────────────────────────────────
  const activity: ActivityItem[] = metrics.recent_activity ?? [];

  // Map agent string to AgentType
  const agentType = (a: string): AgentType => {
    if (["disease", "market", "weather", "scheme", "soil", "fertilizer"].includes(a)) {
      return a as AgentType;
    }
    return "disease";
  };

  return (
    <PageWrapper title={t("dashboard")}>
      {/* ── Metric Cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label={t("activeCrop")}
          value={activeCrop}
          icon={<Sprout size={14} strokeWidth={1.75} />}
        />
        <MetricCard
          label={t("lastDiagnosis")}
          value={
            <span className="flex items-center gap-2">
              {lastDiag} <SeverityBadge level={diagSeverity} />
            </span>
          }
          icon={<Activity size={14} strokeWidth={1.75} />}
        />
        <MetricCard
          label={t("nextIrrigation")}
          value={nextIrrigation}
          icon={<Droplets size={14} strokeWidth={1.75} />}
        />
        <MetricCard
          label={t("mandiPrice")}
          value={
            <span className="flex items-center gap-2">
              {mandiPrice}
              {mandiChange !== 0 && (
                <span
                  style={{
                    color: mandiChange > 0 ? "#639922" : "#ef4444",
                    fontSize: 12,
                  }}
                  className="flex items-center"
                >
                  {mandiChange > 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
                  {Math.abs(mandiChange).toFixed(1)}%
                </span>
              )}
            </span>
          }
          sub={`${t("perQuintal")} · ${mandiLocation}`}
          icon={<TrendingUp size={14} strokeWidth={1.75} />}
        />
      </div>

      {/* ── Activity + Weather ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3 mt-3">
        <Card className="lg:col-span-3">
          <div className="flex items-center justify-between">
            <Label>{t("recentActivity")}</Label>
            <button
              onClick={() => refetch()}
              title="Refresh"
              className="rounded p-1 hover:bg-[var(--c-hover)] transition-colors"
            >
              <RefreshCw size={12} style={{ color: "var(--c-muted)" }} />
            </button>
          </div>

          {activity.length === 0 ? (
            <div className="mt-4 py-8 text-center" style={{ fontSize: 13, color: "var(--c-muted)" }}>
              No activity yet. Start using AgriGPT features to see your history here.
            </div>
          ) : (
            <ul className="mt-3 divide-y" style={{ borderColor: "#f5f5f5" }}>
              {activity.map((a, i) => (
                <li key={i} className="py-2.5 flex items-center gap-3">
                  <div className="flex-1 min-w-0 flex items-center gap-3">
                    <AgentPill type={agentType(a.agent)} />
                    <span className="truncate" style={{ fontSize: 13, color: "#1a1a1a" }}>
                      {a.query}
                    </span>
                  </div>
                  <span style={{ fontSize: 12, color: "#6b7280" }}>{a.time}</span>
                  <Pill tone="brand">{a.status}</Pill>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <Label>{t("weatherForecast")}</Label>
          
          {permissionDenied ? (
            <div className="mt-4 flex flex-col items-center justify-center p-4 text-center rounded-lg bg-gray-50 border border-gray-200">
              <MapPinOff size={24} className="text-gray-400 mb-2" />
              <p className="text-sm text-gray-600">Location access denied. Please allow location to see local weather.</p>
            </div>
          ) : weatherError ? (
            <div className="mt-4 flex flex-col items-center justify-center p-4 text-center rounded-lg bg-red-50 border border-red-200">
              <CloudOff size={24} className="text-red-400 mb-2" />
              <p className="text-sm text-red-600">Unable to load weather forecast.</p>
            </div>
          ) : weatherLoading || !weather ? (
            <div className="mt-4 flex flex-col items-center justify-center p-4">
              <Loader2 size={24} className="text-gray-400 animate-spin mb-2" />
              <p className="text-sm text-gray-500">Locating & loading weather...</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-5 gap-2 mt-3">
                {weather.forecast.map((f, idx) => {
                  const Icon = f.icon;
                  return (
                    <div
                      key={idx}
                      className="rounded-lg p-2 text-center"
                      style={{ border: "1px solid #e5e7eb", background: "#fff" }}
                    >
                      <div style={{ fontSize: 11, color: "#6b7280" }}>
                        {idx === 0 ? "Today" : t(f.dayKey)}
                      </div>
                      <Icon
                        size={20}
                        strokeWidth={1.5}
                        style={{ color: "#6b7280", margin: "8px auto" }}
                      />
                      <div style={{ fontSize: 12, color: "#1a1a1a" }}>
                        {f.hi}°<span style={{ color: "#6b7280" }}>/{f.lo}°</span>
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="mt-4 flex items-center gap-2" style={{ fontSize: 12, color: "#6b7280" }}>
                {weather.isRaining ? (
                  <><CloudRain size={12} className="text-blue-500" /> Rain expected this week</>
                ) : (
                  <><Sun size={12} className="text-yellow-500" /> No rain expected this week</>
                )}
              </div>
            </>
          )}
        </Card>
      </div>

      {/* ── Quick Actions ─────────────────────────────────────────────────── */}
      <div className="mt-3 grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { i: Upload, l: t("uploadLeaf"), to: "/disease" },
          { i: MessageSquare, l: t("askAI"), to: "/chat" },
          { i: BarChart3, l: t("checkPrices"), to: "/market" },
          { i: FileSearch, l: t("findSchemes"), to: "/schemes" },
        ].map(({ i: Icon, l, to }) => (
          <Link
            key={l}
            to={to}
            className="rounded-xl py-4 flex flex-col items-center gap-2 transition-colors block"
            style={{ background: "#f7f8f6", border: "1px solid #e5e7eb", textDecoration: "none" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "#fff";
              e.currentTarget.style.borderColor = "#3b6d11";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "#f7f8f6";
              e.currentTarget.style.borderColor = "#e5e7eb";
            }}
          >
            <Icon size={18} strokeWidth={1.5} style={{ color: "#3b6d11" }} />
            <span style={{ fontSize: 13, color: "#1a1a1a" }}>{l}</span>
          </Link>
        ))}
      </div>
    </PageWrapper>
  );
}
