import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { ArrowUp } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from "recharts";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Card, Label, Select } from "../components/ui/primitives";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/market")({ component: Market });

const data = Array.from({ length: 30 }, (_, i) => ({
  d: `${i + 1}`,
  price: 1800 + Math.round(Math.sin(i / 4) * 180 + i * 12 + Math.random() * 40),
}));

function Market() {
  const [range, setRange] = useState<"7D" | "30D" | "90D">("30D");
  const { t } = useTranslation();

  const markets = [
    { name: t("kolarAPMC"), dist: "12 km", price: "₹2,340", trend: "up" },
    { name: t("chintamani"), dist: "28 km", price: "₹2,290", trend: "up" },
    { name: t("mulbagal"), dist: "34 km", price: "₹2,210", trend: "down" },
    { name: t("bangarapet"), dist: "45 km", price: "₹2,180", trend: "down" },
    { name: t("kgf"), dist: "52 km", price: "₹2,150", trend: "up" },
  ];

  return (
    <PageWrapper title={t("marketPrices")}>
      <div className="flex flex-wrap items-center gap-2">
        <Select defaultValue="Tomato">
          <option value="Tomato">{t("tomato")}</option>
          <option value="Onion">{t("onion")}</option>
          <option value="Paddy">{t("paddy")}</option>
        </Select>
        <Select defaultValue="Kolar">
          <option value="Kolar">{t("kolarAPMC")}</option>
          <option value="Mysore">{t("mysore")}</option>
          <option value="Hassan">{t("hassan")}</option>
        </Select>
        <div className="ml-auto flex rounded-md overflow-hidden" style={{ border: "1px solid #e5e7eb" }}>
          {(["7D", "30D", "90D"] as const).map((r) => (
            <button key={r} onClick={() => setRange(r)}
              className="px-3 py-1.5 text-[12px]"
              style={{
                background: range === r ? "#f0f5ea" : "#fff",
                color: range === r ? "#3b6d11" : "#6b7280",
                borderLeft: r !== "7D" ? "1px solid #e5e7eb" : undefined,
              }}>{r}</button>
          ))}
        </div>
      </div>

      <Card className="mt-3">
        <Label>{t("priceTrend")}</Label>
        <div style={{ height: 240 }} className="mt-3">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="d" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 12 }} />
              <Line type="monotone" dataKey="price" stroke="#639922" strokeWidth={1.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
        <Card>
          <Label>{t("currentPrice")}</Label>
          <div style={{ fontSize: 22, fontWeight: 500, color: "#1a1a1a", marginTop: 6 }}>₹2,340</div>
          <div style={{ fontSize: 12, color: "#6b7280" }}>{t("perQuintal")} · {t("kolarAPMC")}</div>
        </Card>
        <Card>
          <Label>{t("sevenDayChange")}</Label>
          <div className="flex items-center gap-2" style={{ fontSize: 22, fontWeight: 500, color: "#1a1a1a", marginTop: 6 }}>
            +₹148 <span style={{ color: "#639922", fontSize: 12 }} className="flex items-center"><ArrowUp size={12} />+6.7%</span>
          </div>
          <div style={{ fontSize: 12, color: "#6b7280" }}>{t("vsLastWeek")}</div>
        </Card>
        <div className="rounded-xl p-4" style={{ background: "#fff", border: "1px solid #e5e7eb", borderLeft: "3px solid #3b6d11" }}>
          <Label>{t("recommendation")}</Label>
          <div style={{ fontSize: 15, fontWeight: 500, color: "#1a1a1a", marginTop: 6 }}>{t("sellNow")}</div>
          <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>{t("priceAt3MonthPeak")}</div>
        </div>
      </div>

      <Card className="mt-3">
        <Label>{t("nearbyMarkets")}</Label>
        <table className="w-full mt-3 text-left">
          <thead style={{ fontSize: 12, color: "#6b7280" }}>
            <tr style={{ borderBottom: "1px solid #f5f5f5" }}>
              <th className="py-2 font-medium">{t("market")}</th>
              <th className="py-2 font-medium">{t("distance")}</th>
              <th className="py-2 font-medium">{t("price")}</th>
              <th className="py-2 font-medium">{t("trend")}</th>
            </tr>
          </thead>
          <tbody style={{ fontSize: 13 }}>
            {markets.map((m) => (
              <tr key={m.name} style={{ borderBottom: "1px solid #f5f5f5" }}>
                <td className="py-2.5" style={{ color: "#1a1a1a" }}>{m.name}</td>
                <td className="py-2.5" style={{ color: "#6b7280" }}>{m.dist}</td>
                <td className="py-2.5" style={{ color: "#1a1a1a" }}>{m.price}</td>
                <td className="py-2.5" style={{ color: m.trend === "up" ? "#639922" : "#e24b4a" }}>
                  {m.trend === "up" ? "↑" : "↓"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </PageWrapper>
  );
}
