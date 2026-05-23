import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import {
  ArrowUp,
  ArrowDown,
  TrendingUp,
  Sparkles,
  MapPin,
  RefreshCw,
  TrendingDown,
  Info,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  Area,
  Legend,
  AreaChart,
  ComposedChart,
} from "recharts";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Card, Label, Select, Button, Pill } from "../components/ui/primitives";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/market")({ component: Market });

// ─── Interfaces ──────────────────────────────────────────────────────────────

interface PricePoint {
  date: string;
  price: number;
}

interface ForecastPoint {
  date: string;
  price: number;
  lower: number;
  upper: number;
}

interface Recommendation {
  action: "WAIT" | "SELL" | "HOLD";
  reason: string;
  confidence: number;
  pct_vs_90d_avg: number;
  pct_vs_90d_peak: number;
  forecast_7d: number;
  days_to_peak: number;
}

interface NearbyMarket {
  name: string;
  dist_km: number;
  price: number;
  trend: "up" | "down";
  arrivals_qtl: number;
}

interface MarketData {
  crop: string;
  district: string;
  current_price: number;
  change_7d: number;
  change_7d_pct: number;
  history: PricePoint[];
  forecast: ForecastPoint[];
  recommendation: Recommendation;
  nearby_markets: NearbyMarket[];
  forecast_model: string;
  data_source: string;
}

function Market() {
  const { t, lang } = useTranslation();
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastFetchRef = useRef<string>("");

  // Filter States
  const [selectedCrop, setSelectedCrop] = useState("Tomato");
  const [selectedDistrict, setSelectedDistrict] = useState("Hyderabad");
  const [range, setRange] = useState<"7" | "30" | "90">("30");

  // Dynamic Metadata
  const [crops, setCrops] = useState<string[]>([
    "Tomato",
    "Onion",
    "Paddy",
    "Cotton",
    "Maize",
    "Chilli",
    "Groundnut",
    "Soybean",
    "Sugarcane",
    "Wheat",
  ]);
  const [districts, setDistricts] = useState<string[]>([
    "Adilabad",
    "Anantapur",
    "Chittoor",
    "Eluru",
    "Guntur",
    "Hyderabad",
    "Kadapa",
    "Kakinada",
    "Karimnagar",
    "Khammam",
    "Kurnool",
    "Mahabubnagar",
    "Medak",
    "Nalgonda",
    "Nellore",
    "Nizamabad",
    "Rangareddy",
    "Sangareddy",
    "Siddipet",
    "Suryapet",
    "Tirupati",
    "Vijayawada",
    "Visakhapatnam",
    "Vizianagaram",
    "Warangal",
    "West Godavari",
  ]);

  // Main Data States
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MarketData | null>(null);

  // AI Advisory States
  const [advisory, setAdvisory] = useState("");
  const [streaming, setStreaming] = useState(false);

  // Load available crops & districts on mount
  useEffect(() => {
    const fetchMetadata = async () => {
      const api_url = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      try {
        const res = await fetch(`${api_url}/api/market/crops`);
        if (res.ok) {
          const json = await res.json();
          if (json?.crops) setCrops(json.crops);
        }
      } catch (e) {
        console.warn("Could not load dynamic crops metadata", e);
      }

      try {
        const res = await fetch(`${api_url}/api/market/districts`);
        if (res.ok) {
          const json = await res.json();
          if (json?.districts) setDistricts(json.districts);
        }
      } catch (e) {
        console.warn("Could not load dynamic districts metadata", e);
      }
    };
    fetchMetadata();
  }, []);

  // Fetch Main Market Data
  const fetchData = async (isManualRefresh = false) => {
    const queryKey = `${selectedCrop}-${selectedDistrict}-${range}-${lang}`;
    if (!isManualRefresh && lastFetchRef.current === queryKey) return;
    lastFetchRef.current = queryKey;

    setLoading(true);
    setError(null);
    const api_url = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
    try {
      const res = await fetch(
        `${api_url}/api/market/prices?crop=${encodeURIComponent(selectedCrop)}&district=${encodeURIComponent(selectedDistrict)}&range=${range}`,
        {
          headers: { "Authorization": `Bearer ${localStorage.getItem("agrigpt_token")}` }
        }
      );
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const json: MarketData = await res.json();
      setData(json);

      // Trigger AI stream advisory once main data arrives
      if (json) {
        streamAdvisory(
          json.crop,
          json.district,
          json.current_price,
          json.recommendation.action,
          json.recommendation.forecast_7d,
          json.recommendation.pct_vs_90d_avg
        );
      }
    } catch (err: any) {
      console.error("Error fetching market prices:", err);
      setError("Failed to fetch market data. Verify your backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  // SSE Stream logic for Agent 3 Advisory
  const streamAdvisory = async (
    crop: string,
    district: string,
    price: number,
    action: string,
    trend_7d: number,
    pct_avg: number
  ) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setStreaming(true);
    setAdvisory("");

    const api_url = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
    const url = `${api_url}/api/market/advisor/stream?crop=${encodeURIComponent(crop)}&district=${encodeURIComponent(district)}&price=${price}&action=${encodeURIComponent(action)}&trend_7d=${trend_7d}&pct_avg=${pct_avg}&lang=${lang}`;

    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error("Streaming error");

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No body reader");

      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            if (dataStr === "[DONE]") break;
            try {
              const parsed = JSON.parse(dataStr);
              if (parsed.text) {
                accumulated += parsed.text;
                setAdvisory(accumulated);
              }
            } catch {
              // skip malformed JSON chunks
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("Stream aborted");
      } else {
        console.error("Advisory stream error:", err);
        setAdvisory("Failed to stream advisor recommendation. Please check backend connection.");
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setStreaming(false);
      }
    }
  };

  useEffect(() => {
    fetchData();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [selectedCrop, selectedDistrict, range, lang]);

  // Helpers for Chart formatting
  const getChartData = () => {
    if (!data) return [];

    // Connect the history line to the first forecast line point smoothly
    const lastHistoryItem = data.history[data.history.length - 1];

    const formattedHistory = data.history.map((h) => ({
      dateLabel: formatDate(h.date),
      price: h.price,
      forecast: null,
      bounds: null,
    }));

    const formattedForecast = data.forecast.map((f) => ({
      dateLabel: formatDate(f.date),
      price: null,
      forecast: f.price,
      bounds: [f.lower, f.upper],
    }));

    // Inject connection point
    if (lastHistoryItem) {
      const connectionPoint = {
        dateLabel: formatDate(lastHistoryItem.date),
        price: lastHistoryItem.price,
        forecast: lastHistoryItem.price,
        bounds: [lastHistoryItem.price, lastHistoryItem.price],
      };
      return [...formattedHistory, connectionPoint, ...formattedForecast];
    }

    return [...formattedHistory, ...formattedForecast];
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch {
      return dateStr;
    }
  };

  const getCropLabel = (cropName: string) => {
    const lower = cropName.toLowerCase();
    const val = t(lower);
    return val !== lower ? val : cropName;
  };

  const getDistrictLabel = (districtName: string) => {
    if (lang === "te") {
      const teDistricts: Record<string, string> = {
        "Adilabad": "అదిలాబాద్",
        "Anantapur": "అనంతపురం",
        "Chittoor": "చిత్తూరు",
        "Eluru": "ఏలూరు",
        "Guntur": "గుంటూరు",
        "Hyderabad": "హైదరాబాద్",
        "Kadapa": "కడప",
        "Kakinada": "కాకినాడ",
        "Karimnagar": "కరీంనగర్",
        "Khammam": "ఖమ్మం",
        "Kurnool": "కర్నూలు",
        "Mahabubnagar": "మహబూబ్‌నగర్",
        "Medak": "మెదక్",
        "Nalgonda": "నల్గొండ",
        "Nellore": "నెల్లూరు",
        "Nizamabad": "నిజామాబాద్",
        "Rangareddy": "రంగారెడ్డి",
        "Sangareddy": "సంగారెడ్డి",
        "Siddipet": "సిద్దిపేట",
        "Suryapet": "సూర్యాపేట",
        "Tirupati": "తిరుపతి",
        "Vijayawada": "విజయవాడ",
        "Visakhapatnam": "విశాఖపట్నం",
        "Vizianagaram": "విజయనగరం",
        "Warangal": "వరంగల్",
        "West Godavari": "పశ్చిమ గోదావరి",
      };
      return teDistricts[districtName] || districtName;
    }
    if (lang === "hi") {
      const hiDistricts: Record<string, string> = {
        "Adilabad": "आदिलाबाद",
        "Anantapur": "अनंतपुर",
        "Chittoor": "चित्तूर",
        "Eluru": "एलुरु",
        "Guntur": "गुंंटूर",
        "Hyderabad": "हैदराबाद",
        "Kadapa": "कड़पा",
        "Kakinada": "काकीनाडा",
        "Karimnagar": "करीमनगर",
        "Khammam": "खम्मम",
        "Kurnool": "कर्नूल",
        "Mahabubnagar": "महबूबनगर",
        "Medak": "मेडक",
        "Nalgonda": "नलगोंडा",
        "Nellore": "नेल्लोर",
        "Nizamabad": "निजामाबाद",
        "Rangareddy": "रंगारेड्डी",
        "Sangareddy": "संगारेड्डी",
        "Siddipet": "सिद्दीपेट",
        "Suryapet": "सूर्यापेट",
        "Tirupati": "तिरुपति",
        "Vijayawada": "विजयवाड़ा",
        "Visakhapatnam": "विशाखापट्टनम",
        "Vizianagaram": "विजयनगरम",
        "Warangal": "वारंगल",
        "West Godavari": "पश्चिम गोदावरी",
      };
      return hiDistricts[districtName] || districtName;
    }
    return districtName;
  };

  const getMarketNameLabel = (name: string) => {
    if (lang === "te") {
      return name.replace(/\bAPMC\b/g, "ఏపీఎంసీ");
    }
    if (lang === "hi") {
      return name.replace(/\bAPMC\b/g, "एपीएमसी");
    }
    return name;
  };

  const getActionLabel = (action: string) => {
    if (action === "SELL") return t("sellNow");
    if (action === "WAIT") return t("waitDays");
    if (action === "HOLD") return t("holdStock");
    return action;
  };

  // Re-run streaming advisory manual button trigger
  const handleRegenerateAdvisory = () => {
    if (data) {
      streamAdvisory(
        data.crop,
        data.district,
        data.current_price,
        data.recommendation.action,
        data.recommendation.forecast_7d,
        data.recommendation.pct_vs_90d_avg
      );
    }
  };

  return (
    <PageWrapper title={t("marketPrices")}>
      {/* ─── FILTER CONTROLS ─── */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={selectedCrop}
            onChange={(e) => setSelectedCrop(e.target.value)}
            disabled={loading}
          >
            {crops.map((c) => (
              <option key={c} value={c}>
                {getCropLabel(c)}
              </option>
            ))}
          </Select>

          <Select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            disabled={loading}
          >
            {districts.map((d) => (
              <option key={d} value={d}>
                {getDistrictLabel(d)}
              </option>
            ))}
          </Select>

          <Button
            variant="secondary"
            onClick={() => fetchData(true)}
            disabled={loading}
            style={{ padding: "8px 12px" }}
          >
            <RefreshCw
              size={14}
              className={`${loading ? "animate-spin" : ""}`}
            />
          </Button>
        </div>

        {/* Range Selector */}
        <div
          className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-800"
          style={{ background: "var(--c-bg)" }}
        >
          {(["7", "30", "90"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className="px-4 py-2 text-xs font-medium transition-colors"
              style={{
                background: range === r ? "var(--color-brand-soft)" : "transparent",
                color: range === r ? "var(--color-brand)" : "var(--c-muted)",
                borderLeft: r !== "7" ? "1px solid var(--c-border)" : undefined,
              }}
            >
              {r}D
            </button>
          ))}
        </div>
      </div>

      {/* ─── ERROR STATE ─── */}
      {error && (
        <Card className="mb-4" style={{ borderColor: "var(--color-danger)" }}>
          <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
            <Info size={20} />
            <div>
              <p className="font-semibold">{t("serviceUnavailable")}</p>
              <p className="text-sm opacity-90">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {/* ─── SKELETON LOADER ─── */}
      {loading && !data ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="skeleton h-24 rounded-xl"
                style={{ background: "var(--c-bg)", border: "1px solid var(--c-border)" }}
              />
            ))}
          </div>
          <div
            className="skeleton h-72 rounded-xl"
            style={{ background: "var(--c-bg)", border: "1px solid var(--c-border)" }}
          />
          <div
            className="skeleton h-32 rounded-xl"
            style={{ background: "var(--c-bg)", border: "1px solid var(--c-border)" }}
          />
        </div>
      ) : (
        data && (
          <div className="space-y-4 page-fade">
            {/* ─── METRICS ROW ─── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* Card 1: Current Mandi Price */}
              <Card className="flex flex-col justify-between">
                <div>
                  <Label>{t("currentPrice")}</Label>
                  <div
                    className="text-3xl font-semibold mt-1.5 flex items-baseline gap-1.5 text-zinc-900 dark:text-zinc-100"
                  >
                    ₹{data.current_price?.toLocaleString("en-IN") ?? "—"}
                    <span className="text-xs font-normal text-gray-500">
                      / {t("qtl")}
                    </span>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {getDistrictLabel(data.district)} {t("mandi")}
                  </span>
                  <Pill tone={data.data_source === "agmarknet" ? "brand" : "muted"}>
                    {data.data_source === "agmarknet" ? "Live Mandi" : "Simulation"}
                  </Pill>
                </div>
              </Card>

              {/* Card 2: 7-Day Trend */}
              <Card className="flex flex-col justify-between">
                <div>
                  <Label>{t("sevenDayChange")}</Label>
                  <div
                    className={`text-3xl font-semibold mt-1.5 flex items-center gap-1.5 ${
                      data.change_7d >= 0
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-rose-600 dark:text-rose-400"
                    }`}
                  >
                    {data.change_7d >= 0 ? "+" : ""}
                    ₹{data.change_7d.toLocaleString("en-IN")}
                    <span className="text-sm font-medium flex items-center gap-0.5 ml-1">
                      {data.change_7d >= 0 ? (
                        <ArrowUp size={16} />
                      ) : (
                        <ArrowDown size={16} />
                      )}
                      {Math.abs(data.change_7d_pct)}%
                    </span>
                  </div>
                </div>
                <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                  {t("vsLastWeek")}
                </div>
              </Card>

              {/* Card 3: Direct Decision Advisor */}
              <div
                className="rounded-xl p-4 flex flex-col justify-between transition-all"
                style={{
                  background:
                    data.recommendation.action === "WAIT"
                      ? "#f0f5ea"
                      : data.recommendation.action === "SELL"
                        ? "#fee2e2"
                        : "#f3f4f6",
                  border:
                    data.recommendation.action === "WAIT"
                      ? "1px solid #3b6d11"
                      : data.recommendation.action === "SELL"
                        ? "1px solid #e24b4a"
                        : "1px solid #6b7280",
                }}
              >
                <div>
                  <Label>{t("recommendation")}</Label>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span
                      className="text-2xl font-bold"
                      style={{
                        color:
                          data.recommendation.action === "WAIT"
                            ? "#3b6d11"
                            : data.recommendation.action === "SELL"
                              ? "#e24b4a"
                              : "#1a1a1a",
                      }}
                    >
                      {getActionLabel(data.recommendation.action)}
                    </span>
                    <span
                      className="text-[11px] font-semibold px-2 py-0.5 rounded-full"
                      style={{
                        background:
                          data.recommendation.action === "WAIT"
                            ? "rgba(59, 109, 17, 0.15)"
                            : data.recommendation.action === "SELL"
                              ? "rgba(226, 75, 74, 0.15)"
                              : "rgba(0, 0, 0, 0.08)",
                        color:
                          data.recommendation.action === "WAIT"
                            ? "#3b6d11"
                            : data.recommendation.action === "SELL"
                              ? "#e24b4a"
                              : "#6b7280",
                      }}
                    >
                      {data.recommendation.confidence}% {t("confident")}
                    </span>
                  </div>
                  <div
                    className="text-xs mt-2 font-medium"
                    style={{
                      color:
                        data.recommendation.action === "WAIT"
                          ? "#27500a"
                          : data.recommendation.action === "SELL"
                            ? "#991b1b"
                            : "#4b5563",
                    }}
                  >
                    {data.recommendation.reason}
                  </div>
                </div>
                <div className="mt-3 text-[11px] opacity-75 flex items-center justify-between text-gray-500 dark:text-gray-400">
                  <span>{t("forecastModel")}: {data.forecast_model.toUpperCase()}</span>
                  {data.recommendation.days_to_peak > 0 && (
                    <span>{t("peak")}: ~{data.recommendation.days_to_peak} {t("days")}</span>
                  )}
                </div>
              </div>
            </div>

            {/* ─── DYNAMIC PRICE CHART WITH CONFIDENCE BAND ─── */}
            <Card>
              <div className="flex items-center justify-between mb-4">
                <Label>{t("priceTrend")}</Label>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                  <div className="flex items-center gap-1.5">
                    <span className="w-3.5 h-0.5 bg-[#639922] inline-block" />
                    <span>{t("historicalPrice")}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-3.5 h-0.5 border-t-2 border-dashed border-[#3b6d11] inline-block" />
                    <span>{t("forecastedTrend")}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="w-3.5 h-2 bg-[#639922]/15 inline-block" />
                    <span>{t("confidenceRange80")}</span>
                  </div>
                </div>
              </div>

              <div style={{ height: 260 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={getChartData()} margin={{ top: 5, right: 5, left: 20, bottom: 5 }}>
                    <CartesianGrid stroke="#f3f4f6" vertical={false} />
                    <XAxis
                      dataKey="dateLabel"
                      stroke="#9ca3af"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="#9ca3af"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      width={65}
                      domain={["dataMin - 150", "dataMax + 150"]}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--c-bg)",
                        border: "1px solid var(--c-border)",
                        borderRadius: 8,
                        fontSize: 12,
                        color: "var(--c-ink)",
                      }}
                    />
                    {/* Confidence band shading */}
                    <Area
                      type="monotone"
                      dataKey="bounds"
                      stroke="none"
                      fill="#639922"
                      fillOpacity={0.12}
                      name={t("confidenceBand")}
                    />
                    {/* History solid line */}
                    <Line
                      type="monotone"
                      dataKey="price"
                      stroke="#639922"
                      strokeWidth={2}
                      dot={false}
                      name={t("actualPrice")}
                    />
                    {/* Forecast dashed line */}
                    <Line
                      type="monotone"
                      dataKey="forecast"
                      stroke="#3b6d11"
                      strokeDasharray="5 5"
                      strokeWidth={2.2}
                      dot={false}
                      name={t("forecastedPrice")}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* ─── AGENT 3 AI MARKET ADVISORY NODE ─── */}
            <Card style={{ borderLeft: "4px solid var(--color-brand)" }}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles size={16} className="text-brand-500 text-[#639922]" />
                  <Label>Agent 3: Market Advisory Node</Label>
                </div>
                <div className="flex items-center gap-2">
                  {/* ── Updated label: xAI Grok 3 Mini ── */}
                  <Pill tone="brand">xAI Grok 3 Mini</Pill>
                  <Button
                    variant="secondary"
                    onClick={handleRegenerateAdvisory}
                    disabled={streaming}
                    style={{ padding: "4px 8px", fontSize: 11 }}
                  >
                    <RefreshCw
                      size={10}
                      className={`mr-1 ${streaming ? "animate-spin" : ""}`}
                    />
                    {t("rerun")}
                  </Button>
                </div>
              </div>

              <div
                className="p-3.5 rounded-lg text-sm leading-relaxed font-medium bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100"
                style={{
                  minHeight: 70,
                }}
              >
                {streaming && !advisory ? (
                  <div className="flex items-center gap-2 py-2 text-gray-500">
                    <span className="flex h-2 w-2 relative">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-brand"></span>
                    </span>
                    <span>{t("aiAgentDrafting")}</span>
                  </div>
                ) : (
                  <div>
                    <span>{advisory}</span>
                    {streaming && (
                      <span className="inline-block w-1.5 h-4 bg-brand-500 bg-[#3b6d11] ml-1 animate-pulse align-middle" />
                    )}
                  </div>
                )}
              </div>
            </Card>

            {/* ─── NEARBY MARKETS COMPARISON TABLE ─── */}
            <Card>
              <div className="flex items-center justify-between mb-3">
                <Label>{t("nearbyMarkets")}</Label>
                <span className="text-[11px] text-gray-500 font-medium flex items-center gap-1">
                  <MapPin size={12} /> {t("rankedByBestRates")}
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead style={{ fontSize: 11, color: "var(--c-muted)", borderBottom: "1px solid var(--c-border)" }}>
                    <tr>
                      <th className="py-2.5 font-medium">{t("market")}</th>
                      <th className="py-2.5 font-medium">{t("distance")}</th>
                      <th className="py-2.5 font-medium">{t("dailyArrivals")}</th>
                      <th className="py-2.5 font-medium">{t("price")}</th>
                      <th className="py-2.5 font-medium">{t("trend")}</th>
                    </tr>
                  </thead>
                  <tbody style={{ fontSize: 13 }} className="divide-y divide-gray-100 dark:divide-zinc-800">
                    {data.nearby_markets.map((m, idx) => (
                      <tr
                        key={m.name}
                        className={`transition-colors ${
                          idx === 0
                            ? "bg-[#f0f5ea]/40 dark:bg-[#1a2e10]/10 font-semibold"
                            : "hover:bg-gray-50/50 dark:hover:bg-zinc-800/20"
                        }`}
                      >
                        <td className="py-3 flex items-center gap-2">
                          <span className="text-zinc-900 dark:text-zinc-100">{getMarketNameLabel(m.name)}</span>
                          {idx === 0 && (
                            <span className="bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300 text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                              {t("bestRate")}
                            </span>
                          )}
                        </td>
                        <td className="py-3 text-gray-500 dark:text-gray-400">
                          {m.dist_km} km
                        </td>
                        <td className="py-3 text-gray-500 dark:text-gray-400">
                          {m.arrivals_qtl} Qtl
                        </td>
                        <td className="py-3 text-zinc-900 dark:text-zinc-100">
                          ₹{m.price.toLocaleString("en-IN")}
                        </td>
                        <td
                          className="py-3 font-semibold"
                          style={{
                            color: m.trend === "up" ? "var(--color-success)" : "var(--color-danger)",
                          }}
                        >
                          {m.trend === "up" ? (
                            <span className="flex items-center gap-0.5">
                              <ArrowUp size={14} /> {t("bullish")}
                            </span>
                          ) : (
                            <span className="flex items-center gap-0.5">
                              <ArrowDown size={14} /> {t("bearish")}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )
      )}
    </PageWrapper>
  );
}