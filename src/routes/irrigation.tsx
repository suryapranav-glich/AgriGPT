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

  // Single cohesive applied plan state (starts empty)
  const [appliedPlan, setAppliedPlan] = useState<{
    loc: string;
    crop: string;
    fieldSize: number;
    days: { d: string; rain: number; hi: number; lo: number }[];
    refEt: number;
    hasHeatwave: boolean;
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
      // 1. Geocode location to get coordinates (Open-Meteo free geocoding API)
      const cleanName = locInput.replace(/,.*$/, "").trim();
      let lat = 13.13768; // fallback to Kolar coordinates
      let lon = 78.12999;
      let matchedName = locInput;

      let geoRes = await fetch(
        `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cleanName)}&count=1&language=en&format=json`
      );
      let geoData = await geoRes.json();

      // If spelling ends with 'y' (e.g. Kamareddy) and not found, fallback to 'i' (Kamareddi)
      if ((!geoData.results || geoData.results.length === 0) && cleanName.toLowerCase().endsWith("y")) {
        const altName = cleanName.slice(0, -1) + "i";
        geoRes = await fetch(
          `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(altName)}&count=1&language=en&format=json`
        );
        geoData = await geoRes.json();
      }

      if (geoData.results && geoData.results.length > 0) {
        lat = geoData.results[0].latitude;
        lon = geoData.results[0].longitude;
        matchedName = `${geoData.results[0].name}, ${geoData.results[0].admin1 || geoData.results[0].country}`;
      } else {
        console.warn("Geocoding returned no results, using regional default coordinates.");
      }

      // 2. Fetch daily weather forecast from Open-Meteo
      const weatherRes = await fetch(
        `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto`
      );
      const weatherData = await weatherRes.json();

      if (!weatherData.daily) {
        throw new Error("Invalid response structure from weather API.");
      }

      const daily = weatherData.daily;
      const parsedDays = [
        {
          d: t("today"),
          rain: daily.precipitation_probability_max[0] ?? 0,
          hi: Math.round(daily.temperature_2m_max[0] ?? 30),
          lo: Math.round(daily.temperature_2m_min[0] ?? 20),
        },
        {
          d: t("tomorrow"),
          rain: daily.precipitation_probability_max[1] ?? 0,
          hi: Math.round(daily.temperature_2m_max[1] ?? 30),
          lo: Math.round(daily.temperature_2m_min[1] ?? 20),
        },
        {
          d: t("day3"),
          rain: daily.precipitation_probability_max[2] ?? 0,
          hi: Math.round(daily.temperature_2m_max[2] ?? 30),
          lo: Math.round(daily.temperature_2m_min[2] ?? 20),
        },
      ];

      // 3. Compute Reference ET (ET0) based on regional temperatures (Hargreaves approximation)
      const hiToday = parsedDays[0].hi;
      const loToday = parsedDays[0].lo;
      const computedRefEt = Math.round((0.12 * hiToday + 0.1 * (hiToday - loToday) - 0.5) * 10) / 10;

      // Heatwave alert if temperature >= 38°C or ET0 > 6.2 mm/day
      const hasHeatwave = hiToday >= 38 || computedRefEt > 6.2;

      setAppliedPlan({
        loc: matchedName,
        crop: cropInput,
        fieldSize: Number(fieldSizeInput),
        days: parsedDays,
        refEt: computedRefEt,
        hasHeatwave,
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
  const appliedLoc = appliedPlan ? appliedPlan.loc : "";
  const appliedCrop = appliedPlan ? appliedPlan.crop : "Tomato";
  const appliedFieldSize = appliedPlan ? appliedPlan.fieldSize : 0;
  const days = appliedPlan ? appliedPlan.days : [];
  const refEt = appliedPlan ? appliedPlan.refEt : 0;
  const hasHeatwave = appliedPlan ? appliedPlan.hasHeatwave : false;

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

  // Effective rainfall (from tomorrow's expected rain probability)
  const tomorrowRain = hasAppliedData ? days[1].rain : 0;
  const effectiveRain = tomorrowRain > 50
    ? Math.round(tomorrowRain * 0.15 * 10) / 10
    : 0.0;

  // Net irrigation requirement
  const netIrrRequirement = Math.max(0, cropEt - effectiveRain);

  // Total water volume (Litres)
  const totalWaterLitres = Math.round(
    netIrrRequirement * appliedFieldSize * 4046.86
  );

  // Recommendation strings
  const shouldIrrigate = netIrrRequirement > 0;
  const recomTitle = shouldIrrigate
    ? t("irrigateToday")
    : t("doNotIrrigateToday");
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
