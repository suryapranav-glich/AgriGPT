import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { MapPin, AlertTriangle, X, Loader2 } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Card, Input, Select, Label, Button } from "../components/ui/primitives";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/irrigation")({ component: Irrigation });

function Irrigation() {
  const { t } = useTranslation();
  const [showAlert, setShowAlert] = useState(true);

  // Input states initialized to empty strings
  const [locInput, setLocInput] = useState("");
  const [cropInput, setCropInput] = useState("Tomato");
  const [growthStageInput, setGrowthStageInput] = useState("Vegetative");
  const [fieldSizeInput, setFieldSizeInput] = useState<number | "">("");

  // Single cohesive applied plan state (starts empty)
  const [appliedPlan, setAppliedPlan] = useState<{
    loc: string;
    crop: string;
    fieldSize: number;
    days: { d: string; rain: number; hi: number; lo: number }[];
    refEt: number;
    kc: number;
    cropEt: number;
    effectiveRain: number;
    netIrrigation: number;
    totalWaterLitres: number;
    hasHeatwave: boolean;
    bestWateringTime: string;
  } | null>(null);

  // Transition state
  const [isCalculating, setIsCalculating] = useState(false);

  const handleApply = async () => {
    if (!locInput.trim() || fieldSizeInput === "") {
      alert("Please enter a valid Location and Field Size first.");
      return;
    }

    setIsCalculating(true);
    try {
      const api_url = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";
      const res = await fetch(`${api_url}/irrigation/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          location: locInput,
          crop: cropInput,
          growth_stage: growthStageInput,
          field_size: Number(fieldSizeInput)
        })
      });

      if (!res.ok) throw new Error("Backend failed");

      const data = await res.json();
      
      setAppliedPlan({
        loc: data.location,
        crop: cropInput,
        fieldSize: Number(fieldSizeInput),
        days: data.forecast_15_days.map((d: any, i: number) => ({
          d: i === 0 ? t("today") : i === 1 ? t("tomorrow") : `${t("day")} ${i+1}`,
          rain: d.rain_prob,
          hi: d.t_max,
          lo: d.t_min
        })),
        refEt: data.ref_et,
        kc: data.kc,
        cropEt: data.crop_et,
        effectiveRain: data.effective_rain,
        netIrrigation: data.net_irrigation,
        totalWaterLitres: data.total_water_litres,
        hasHeatwave: data.has_heatwave,
        bestWateringTime: data.best_watering_time
      });
      setShowAlert(true);
    } catch (err) {
      console.error("Error fetching live weather plan:", err);
      alert("Failed to load live weather. Please check your internet connection and try again.");
    } finally {
      setIsCalculating(false);
    }
  };

  const hasAppliedData = appliedPlan !== null;
  const appliedCrop = appliedPlan ? appliedPlan.crop : "Tomato";
  const days = appliedPlan ? appliedPlan.days : [];
  const refEt = appliedPlan ? appliedPlan.refEt : 0;
  const kc = appliedPlan ? appliedPlan.kc : 0;
  const cropEt = appliedPlan ? appliedPlan.cropEt : 0;
  const effectiveRain = appliedPlan ? appliedPlan.effectiveRain : 0;
  const netIrrRequirement = appliedPlan ? appliedPlan.netIrrigation : 0;
  const totalWaterLitres = appliedPlan ? appliedPlan.totalWaterLitres : 0;
  const bestWateringTime = appliedPlan ? appliedPlan.bestWateringTime : "";
  const hasHeatwave = appliedPlan ? appliedPlan.hasHeatwave : false;

  const tomorrowRain = hasAppliedData ? days[1].rain : 0;
  const shouldIrrigate = netIrrRequirement > 0;
  const recomTitle = shouldIrrigate ? t("irrigateToday") : t("doNotIrrigateToday");
  const recomDesc = shouldIrrigate
    ? `Apply approximately ${netIrrRequirement.toFixed(1)} mm of water (${totalWaterLitres.toLocaleString()} Litres) to maintain optimal soil moisture for ${appliedCrop}.`
    : `Rain expected tomorrow (${tomorrowRain}% probability). Soil moisture currently adequate. Skip irrigation today.`;

  return (
    <PageWrapper title={t("irrigationPlanner")}>
      {showAlert && hasHeatwave && (
        <div
          className="flex items-center justify-between gap-2 rounded-lg p-2.5 transition-all"
          style={{ background: "#fdf3e3", border: "1px solid #ba7517" }}
        >
          <div className="flex items-center gap-2">
            <AlertTriangle size={15} style={{ color: "#ba7517", flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: "#1a1a1a", fontWeight: 500 }}>
              {t("heatwaveAlert")}
            </span>
          </div>
          <button
            onClick={() => setShowAlert(false)}
            className="p-1 rounded-md transition-colors hover:bg-amber-100 flex items-center justify-center cursor-pointer"
            style={{
              border: "none",
              background: "transparent",
              color: "#ba7517",
            }}
            aria-label="Dismiss alert"
          >
            <X size={16} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mt-3 items-end">
        <Card>
          <Label>{t("location")}</Label>
          <div className="flex items-center gap-2 mt-2">
            <MapPin size={14} style={{ color: "#3b6d11" }} />
            <Input
              value={locInput}
              onChange={(e) => setLocInput(e.target.value)}
              placeholder={t("locationPlaceholder") || "e.g., Kolar, Karnataka"}
            />
          </div>
        </Card>
        <Card>
          <Label>{t("crop")}</Label>
          <Select
            className="w-full mt-2"
            value={cropInput}
            onChange={(e) => setCropInput(e.target.value)}
          >
            <option value="Tomato">{t("tomato")}</option>
            <option value="Onion">{t("onion")}</option>
            <option value="Paddy">{t("paddy")}</option>
            <option value="Cotton">{t("cotton")}</option>
          </Select>
        </Card>
        <Card>
          <Label>{t("growthStage") || "Growth Stage"}</Label>
          <Select
            className="w-full mt-2"
            value={growthStageInput}
            onChange={(e) => setGrowthStageInput(e.target.value)}
          >
            <option value="Seedling">Seedling</option>
            <option value="Vegetative">Vegetative</option>
            <option value="Flowering">Flowering</option>
            <option value="Bulb Development">Bulb Development</option>
            <option value="Boll Development">Boll Development</option>
            <option value="Maturity">Maturity</option>
          </Select>
        </Card>
        <Card>
          <Label>{t("fieldSize")}</Label>
          <Input
            className="mt-2"
            type="number"
            step="0.1"
            value={fieldSizeInput}
            onChange={(e) =>
              setFieldSizeInput(e.target.value === "" ? "" : parseFloat(e.target.value))
            }
            placeholder={t("fieldSizePlaceholder") || "e.g., 2.5"}
          />
        </Card>
        <div style={{ height: "100%", display: "flex", alignItems: "flex-end" }}>
          <Button
            onClick={handleApply}
            className="w-full"
            style={{ height: "44px", display: "flex", gap: "8px" }}
            disabled={isCalculating}
          >
            {isCalculating ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                {t("thinking") || "Calculating..."}
              </>
            ) : (
              t("applyChanges")
            )}
          </Button>
        </div>
      </div>

      {!hasAppliedData ? (
        <Card className="mt-3">
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <MapPin size={28} strokeWidth={1.5} style={{ color: "#9ca3af" }} />
            <div style={{ fontSize: 14, color: "#6b7280", marginTop: 10 }}>
              {t("enterDetailsPrompt") || "Please enter your details to generate plan."}
            </div>
          </div>
        </Card>
      ) : (
        <>
          <div className="flex gap-3 mt-3 overflow-x-auto pb-2" style={{ scrollbarWidth: "thin" }}>
            {days.map((f) => (
              <Card key={f.d} className="min-w-[140px] flex-shrink-0">
                <div className="flex items-center justify-between">
                  <Label>{f.d}</Label>
                  <span style={{ fontSize: 12, color: "#1a1a1a" }}>
                    {f.hi}°/{f.lo}°
                  </span>
                </div>
                <div
                  className="flex items-center justify-between mt-3"
                  style={{ fontSize: 12, color: "#6b7280" }}
                >
                  <span>{t("rainProbability")}</span>
                  <span>{f.rain}%</span>
                </div>
                <div
                  className="w-full rounded-full mt-1"
                  style={{ height: 4, background: "#f3f4f6" }}
                >
                  <div
                    style={{
                      width: `${f.rain}%`,
                      height: "100%",
                      background: "#9aa6b2",
                      borderRadius: 999,
                    }}
                  />
                </div>
              </Card>
            ))}
          </div>

          <div
            className="mt-3 rounded-xl p-5"
            style={{
              background: "#fff",
              border: "1px solid #e5e7eb",
              borderLeft: "3px solid #3b6d11",
            }}
          >
            <div style={{ fontSize: 20, fontWeight: 500, color: "#1a1a1a" }}>{recomTitle}</div>
            <div style={{ fontSize: 14, color: "#6b7280", marginTop: 4 }}>{recomDesc}</div>

            <div className="mt-5">
              <Label>{t("bestWateringTime") || "Best Watering Time"}</Label>
              <div style={{ fontSize: 16, fontWeight: 500, color: "#1e40af", marginTop: 4 }}>
                {bestWateringTime}
              </div>
            </div>

            <div className="mt-5">
              <Label>{t("etcCalculation")}</Label>
              <table className="w-full mt-2 text-left">
                <tbody style={{ fontSize: 13 }}>
                  {[
                    [t("refEt"), `${refEt.toFixed(1)} mm/day`],
                    [t("cropCoeff"), `${kc.toFixed(2)}`],
                    [t("cropEt"), `${cropEt.toFixed(2)} mm/day`],
                    [
                      t("effectiveRain"),
                      effectiveRain > 0 ? `${effectiveRain} mm expected` : "0 mm expected",
                    ],
                    [
                      t("netIrrRequirement"),
                      netIrrRequirement > 0
                        ? `${netIrrRequirement.toFixed(1)} mm`
                        : "0 mm — skip today",
                    ],
                  ].map(([k, v]) => (
                    <tr key={k} style={{ borderBottom: "1px solid #f5f5f5" }}>
                      <td className="py-2" style={{ color: "#6b7280" }}>
                        {k}
                      </td>
                      <td className="py-2 text-right" style={{ color: "#1a1a1a" }}>
                        {v}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </PageWrapper>
  );
}
