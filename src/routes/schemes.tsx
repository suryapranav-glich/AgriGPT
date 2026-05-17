import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Search } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { SchemeCard } from "../components/ui/SchemeCard";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/schemes")({ component: Schemes });

const filterKeys = ["all", "subsidies", "seeds", "insurance", "credit", "irrigationTab"] as const;

const schemesList = [
  { nameKey: "pmKisanName", stateKey: "central", categoryKey: "subsidies", summaryKey: "pmKisanSum" },
  { nameKey: "pmfbyName", stateKey: "central", categoryKey: "insurance", summaryKey: "pmfbySum" },
  { nameKey: "kccName", stateKey: "central", categoryKey: "credit", summaryKey: "kccSum" },
  { nameKey: "pmksyName", stateKey: "central", categoryKey: "irrigationTab", summaryKey: "pmksySum" },
  { nameKey: "raithaSiriName", stateKey: "karnataka", categoryKey: "subsidies", summaryKey: "raithaSiriSum" },
  { nameKey: "seedMissionName", stateKey: "central", categoryKey: "seeds", summaryKey: "seedMissionSum" },
];

function Schemes() {
  const [active, setActive] = useState<typeof filterKeys[number]>("all");
  const [q, setQ] = useState("");
  const { t } = useTranslation();
  const list = active === "all" ? schemesList : schemesList.filter((s) => s.categoryKey === active);
  return (
    <PageWrapper title={t("govtSchemes")}>
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-2 rounded-lg px-3 py-2.5"
             style={{ background: "#fff", border: "1px solid #e5e7eb" }}>
          <Search size={16} style={{ color: "#6b7280" }} />
          <input
            value={q} onChange={(e) => setQ(e.target.value)}
            placeholder={t("searchSchemes")}
            className="flex-1 bg-transparent outline-none text-[14px]" style={{ color: "#1a1a1a" }}
          />
        </div>
      </div>

      {q && (
        <div className="mt-4 rounded-xl p-4"
             style={{ background: "#fff", border: "1px solid #e5e7eb", borderTop: "3px solid #3b6d11" }}>
          <div style={{ fontSize: 14, color: "#1a1a1a", lineHeight: 1.6 }}>
            {t("schemeFaqAnswer")}
          </div>
          <div style={{ fontSize: 12, color: "#6b7280", marginTop: 10 }}>{t("schemeFaqSource")}</div>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mt-4">
        {filterKeys.map((f) => {
          const a = f === active;
          return (
            <button key={f} onClick={() => setActive(f)}
              className="px-3 py-1.5 rounded-full text-[12px]"
              style={{
                background: a ? "#f0f5ea" : "#fff",
                color: a ? "#3b6d11" : "#6b7280",
                border: `1px solid ${a ? "#3b6d11" : "#e5e7eb"}`,
              }}>{t(f)}</button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
        {list.map((s) => <SchemeCard key={s.nameKey} {...s} />)}
      </div>
    </PageWrapper>
  );
}
