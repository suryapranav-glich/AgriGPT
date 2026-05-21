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
  Scan,
} from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, Label, SeverityBadge, Pill } from "../components/ui/primitives";
import { AgentPill, type AgentType } from "../components/ui/AgentPill";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/")({ component: Dashboard });

const activity: { agent: AgentType; qKey: string; t: string; statusKey: string }[] = [
  { agent: "disease", qKey: "recentActivity1", t: "2h ago", statusKey: "resolved" },
  { agent: "market", qKey: "recentActivity2", t: "5h ago", statusKey: "answered" },
  { agent: "weather", qKey: "recentActivity3", t: "Yesterday", statusKey: "answered" },
  { agent: "scheme", qKey: "recentActivity4", t: "2d ago", statusKey: "resolved" },
  { agent: "soil", qKey: "recentActivity5", t: "3d ago", statusKey: "answered" },
];

const forecast = [
  { dayKey: "mon", icon: Sun, hi: 32, lo: 22 },
  { dayKey: "tue", icon: CloudSun, hi: 31, lo: 23 },
  { dayKey: "wed", icon: CloudRain, hi: 28, lo: 22 },
  { dayKey: "thu", icon: Cloud, hi: 29, lo: 21 },
  { dayKey: "fri", icon: CloudSnow, hi: 27, lo: 20 },
];

function Dashboard() {
  const { t } = useTranslation();

  return (
    <PageWrapper title={t("dashboard")}>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label={t("activeCrop")}
          value={t("tomato")}
          sub={t("sownDateVal")}
          icon={<Sprout size={14} strokeWidth={1.75} />}
        />
        <MetricCard
          label={t("lastDiagnosis")}
          value={
            <span className="flex items-center gap-2">
              {t("leafBlight")} <SeverityBadge level="med" />
            </span>
          }
          sub={t("lastDiagVal")}
          icon={<Activity size={14} strokeWidth={1.75} />}
        />
        <MetricCard
          label={t("nextIrrigation")}
          value={t("in2Days")}
          sub={t("morning16May")}
          icon={<Droplets size={14} strokeWidth={1.75} />}
        />
        <MetricCard
          label={t("mandiPrice")}
          value={
            <span className="flex items-center gap-2">
              ₹2,340{" "}
              <span style={{ color: "#639922", fontSize: 12 }} className="flex items-center">
                <ArrowUp size={12} />
                4.2%
              </span>
            </span>
          }
          sub={`${t("perQuintal")} · Kolar`}
          icon={<TrendingUp size={14} strokeWidth={1.75} />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3 mt-3">
        <Card className="lg:col-span-3">
          <Label>{t("recentActivity")}</Label>
          <ul className="mt-3 divide-y" style={{ borderColor: "#f5f5f5" }}>
            {activity.map((a, i) => (
              <li key={i} className="py-2.5 flex items-center gap-3">
                <div className="flex-1 min-w-0 flex items-center gap-3">
                  <AgentPill type={a.agent} />
                  <span className="truncate" style={{ fontSize: 13, color: "#1a1a1a" }}>
                    {t(a.qKey)}
                  </span>
                </div>
                <span style={{ fontSize: 12, color: "#6b7280" }}>{a.t}</span>
                <Pill tone="brand">{t(a.statusKey)}</Pill>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="lg:col-span-2">
          <Label>{t("weatherForecast")}</Label>
          <div className="grid grid-cols-5 gap-2 mt-3">
            {forecast.map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.dayKey}
                  className="rounded-lg p-2 text-center"
                  style={{ border: "1px solid #e5e7eb", background: "#fff" }}
                >
                  <div style={{ fontSize: 11, color: "#6b7280" }}>{t(f.dayKey)}</div>
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
            <ArrowDown size={12} /> {t("rainExpected")}
          </div>
        </Card>
      </div>

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
