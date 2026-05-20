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
  const [fieldSizeInput, setFieldSizeInput] = useState<number | "">("");

  // Applied states initialized to empty
  const [appliedLoc, setAppliedLoc] = useState("");
  const [appliedCrop, setAppliedCrop] = useState("Tomato");
  const [appliedFieldSize, setAppliedFieldSize] = useState<number | "">("");

  // Transition state
  const [isCalculating, setIsCalculating] = useState(false);

  const handleApply = () => {
    if (!locInput.trim() || fieldSizeInput === "") {
      alert("Please enter a valid Location and Field Size first.");
      return;
    }
    setIsCalculating(true);
    setTimeout(() => {
      setAppliedLoc(locInput);
      setAppliedCrop(cropInput);
      setAppliedFieldSize(fieldSizeInput);
      setIsCalculating(false);
      setShowAlert(true); // Reset dismissible alert when recalculating
    }, 600);
  };

  const hasAppliedData = appliedLoc !== "" && appliedFieldSize !== "";

  // ── Calculation Pipeline ──────────────────────────────────────────────────
  const isKolarTomato =
    hasAppliedData &&
    appliedLoc.trim().toLowerCase() === "kolar, karnataka" &&
    appliedCrop === "Tomato";

  // Deterministic seed based on location string hash + crop length
  const hash = hasAppliedData
    ? (appliedLoc.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) +
      appliedCrop.length)
    : 0;

  // Temperature and Weather Forecast
  const days = isKolarTomato
    ? [
        { d: t("today"), rain: 22, hi: 34, lo: 24 },
        { d: t("tomorrow"), rain: 78, hi: 30, lo: 23 },
        { d: t("day3"), rain: 45, hi: 31, lo: 22 },
      ]
    : [
        {
          d: t("today"),
          rain: hasAppliedData ? (hash * 3) % 40 : 0,
          hi: hasAppliedData ? 28 + (hash % 11) : 0,
          lo: hasAppliedData ? 20 + (hash % 6) : 0,
        },
        {
          d: t("tomorrow"),
          rain: hasAppliedData ? (hash * 7) % 95 : 0,
          hi: hasAppliedData ? 28 + ((hash + 2) % 11) - 2 : 0,
          lo: hasAppliedData ? 20 + ((hash + 2) % 6) - 1 : 0,
        },
        {
          d: t("day3"),
          rain: hasAppliedData ? (hash * 13) % 70 : 0,
          hi: hasAppliedData ? 28 + ((hash + 4) % 11) - 1 : 0,
          lo: hasAppliedData ? 20 + ((hash + 4) % 6) - 1 : 0,
        },
      ];

  // Reference ET (ET0)
  const refEt = isKolarTomato ? 5.4 : hasAppliedData ? 4.5 + (hash % 21) * 0.1 : 0;

  // Crop coefficient (Kc) and label
  let Kc = 1.15;
  let cropLabel = "mid-stage";
  if (appliedCrop === "Tomato") {
    Kc = 1.15;
    cropLabel = "mid-stage";
  } else if (appliedCrop === "Onion") {
    Kc = 1.05;
    cropLabel = "bulb-dev";
  } else if (appliedCrop === "Paddy") {
    Kc = 1.20;
    cropLabel = "flooded";
  } else if (appliedCrop === "Cotton") {
    Kc = 1.15;
    cropLabel = "boll-dev";
  }

  // Crop ET (ETc)
  const cropEt = refEt * Kc;

  // Effective rainfall (from tomorrow's expected rain)
  const tomorrowRain = hasAppliedData ? days[1].rain : 0;
  const effectiveRain = isKolarTomato
    ? 12.0
    : tomorrowRain > 50
      ? Math.round(tomorrowRain * 0.15 * 10) / 10
      : 0.0;

  // Net irrigation requirement
  const netIrrRequirement = Math.max(0, cropEt - effectiveRain);

  // Total water volume (Litres)
  const appliedFieldSizeNum = typeof appliedFieldSize === "number" ? appliedFieldSize : 0;
  const totalWaterLitres = Math.round(
    netIrrRequirement * appliedFieldSizeNum * 4046.86
  );

  // Recommendation strings
  const shouldIrrigate = netIrrRequirement > 0;
  const recomTitle = shouldIrrigate
    ? t("irrigateToday")
    : t("doNotIrrigateToday");
  const recomDesc = shouldIrrigate
    ? `Apply approximately ${netIrrRequirement.toFixed(1)} mm of water (${totalWaterLitres.toLocaleString()} Litres) to maintain optimal soil moisture for ${appliedCrop}.`
    : `Rain expected tomorrow (${tomorrowRain}% probability). Soil moisture currently adequate. Skip irrigation today.`;

  // Heatwave alert
  const hasHeatwave = isKolarTomato ? true : hasAppliedData && (days[0].hi >= 38 || refEt > 6.2);

  return (
    <PageWrapper title={t("irrigationPlanner")}>
      {showAlert && hasHeatwave && (
        <div
          className="flex items-center justify-between gap-2 rounded-lg p-2.5 transition-all"
          style={{ background: "#fdf3e3", border: "1px solid #ba7517" }}
        >
          <div className="flex items-center gap-2">
            <AlertTriangle
              size={15}
              style={{ color: "#ba7517", flexShrink: 0 }}
            />
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

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-3 items-end">
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
            {days.map((f) => (
              <Card key={f.d}>
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
            <div style={{ fontSize: 20, fontWeight: 500, color: "#1a1a1a" }}>
              {recomTitle}
            </div>
            <div style={{ fontSize: 14, color: "#6b7280", marginTop: 4 }}>
              {recomDesc}
            </div>

            <div className="mt-5">
              <Label>{t("etcCalculation")}</Label>
              <table className="w-full mt-2 text-left">
                <tbody style={{ fontSize: 13 }}>
                  {[
                    [t("refEt"), `${refEt.toFixed(1)} mm/day`],
                    [t("cropCoeff"), `${Kc.toFixed(2)} (${cropLabel})`],
                    [t("cropEt"), `${cropEt.toFixed(2)} mm/day`],
                    [
                      t("effectiveRain"),
                      effectiveRain > 0
                        ? `${effectiveRain} mm expected`
                        : "0 mm expected",
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

