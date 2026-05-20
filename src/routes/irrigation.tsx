import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { MapPin, AlertTriangle, X } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Card, Input, Select, Label } from "../components/ui/primitives";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/irrigation")({ component: Irrigation });

function Irrigation() {
  const { t } = useTranslation();
  const [showAlert, setShowAlert] = useState(true);

  const days = [
    { d: t("today"), rain: 22, hi: 34, lo: 24 },
    { d: t("tomorrow"), rain: 78, hi: 30, lo: 23 },
    { d: t("day3"), rain: 45, hi: 31, lo: 22 },
  ];

  return (
    <PageWrapper title={t("irrigationPlanner")}>
      {showAlert && (
        <div className="flex items-center justify-between gap-2 rounded-lg p-2.5 transition-all"
             style={{ background: "#fdf3e3", border: "1px solid #ba7517" }}>
          <div className="flex items-center gap-2">
            <AlertTriangle size={15} style={{ color: "#ba7517", flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: "#1a1a1a", fontWeight: 500 }}>{t("heatwaveAlert")}</span>
          </div>
          <button
            onClick={() => setShowAlert(false)}
            className="p-1 rounded-md transition-colors hover:bg-amber-100 flex items-center justify-center cursor-pointer"
            style={{ border: "none", background: "transparent", color: "#ba7517" }}
            aria-label="Dismiss alert"
          >
            <X size={16} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
        <Card>
          <Label>{t("location")}</Label>
          <div className="flex items-center gap-2 mt-2">
            <MapPin size={14} style={{ color: "#3b6d11" }} />
            <Input defaultValue="Kolar, Karnataka" />
          </div>
        </Card>
        <Card>
          <Label>{t("crop")}</Label>
          <Select className="w-full mt-2" defaultValue="Tomato">
            <option value="Tomato">{t("tomato")}</option>
            <option value="Onion">{t("onion")}</option>
            <option value="Paddy">{t("paddy")}</option>
            <option value="Cotton">{t("cotton")}</option>
          </Select>
        </Card>
        <Card>
          <Label>{t("fieldSize")}</Label>
          <Input className="mt-2" type="number" defaultValue={2.5} />
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
        {days.map((f) => (
          <Card key={f.d}>
            <div className="flex items-center justify-between">
              <Label>{f.d}</Label>
              <span style={{ fontSize: 12, color: "#1a1a1a" }}>{f.hi}°/{f.lo}°</span>
            </div>
            <div className="flex items-center justify-between mt-3" style={{ fontSize: 12, color: "#6b7280" }}>
              <span>{t("rainProbability")}</span><span>{f.rain}%</span>
            </div>
            <div className="w-full rounded-full mt-1" style={{ height: 4, background: "#f3f4f6" }}>
              <div style={{ width: `${f.rain}%`, height: "100%", background: "#9aa6b2", borderRadius: 999 }} />
            </div>
          </Card>
        ))}
      </div>

      <div className="mt-3 rounded-xl p-5"
           style={{ background: "#fff", border: "1px solid #e5e7eb", borderLeft: "3px solid #3b6d11" }}>
        <div style={{ fontSize: 20, fontWeight: 500, color: "#1a1a1a" }}>{t("doNotIrrigateToday")}</div>
        <div style={{ fontSize: 14, color: "#6b7280", marginTop: 4 }}>
          {t("rainExpectedTomorrow")}
        </div>

        <div className="mt-5">
          <Label>{t("etcCalculation")}</Label>
          <table className="w-full mt-2 text-left">
            <tbody style={{ fontSize: 13 }}>
              {[
                [t("refEt"), t("refEtVal")],
                [t("cropCoeff"), t("cropCoeffVal")],
                [t("cropEt"), t("cropEtVal")],
                [t("effectiveRain"), t("effectiveRainVal")],
                [t("netIrrRequirement"), t("netIrrRequirementVal")],
              ].map(([k, v]) => (
                <tr key={k} style={{ borderBottom: "1px solid #f5f5f5" }}>
                  <td className="py-2" style={{ color: "#6b7280" }}>{k}</td>
                  <td className="py-2 text-right" style={{ color: "#1a1a1a" }}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageWrapper>
  );
}
