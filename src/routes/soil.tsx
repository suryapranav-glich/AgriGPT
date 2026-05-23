import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef } from "react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Card, Label, Input, Button } from "../components/ui/primitives";
import { NutrientBar } from "../components/ui/NutrientBar";
import { MarkdownText } from "../components/ui/MarkdownText";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/soil")({ component: Soil });

// ─── Types ────────────────────────────────────────────────────────────────────

type Texture = "sandy" | "loamy" | "clay" | "black";
type Grade = "A" | "B" | "C" | "D";
type Status = "ok" | "low" | "def";

interface SoilResult {
  grade: Grade;
  gradeLabel: string;
  ph: number;
  n: number;
  p: number;
  k: number;
  phStatus: "acidic" | "neutral" | "alkaline";
  nStatus: Status;
  pStatus: Status;
  kStatus: Status;
  crops: Array<{ name: string; pct: number }>;
  deficiencies: string;
  improvementPlan: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getNutrientStatus(n: number, p: number, k: number) {
  return {
    nStatus: (n < 120 ? "def" : n < 180 ? "low" : "ok") as Status,
    pStatus: (p < 15 ? "def" : p < 30 ? "low" : "ok") as Status,
    kStatus: (k < 100 ? "def" : k < 160 ? "low" : "ok") as Status,
  };
}

function computeGrade(ph: number, n: number, p: number, k: number): Grade {
  let score = 0;
  if (ph >= 6 && ph <= 7.5) score += 25;
  else if (ph >= 5.5 && ph <= 8) score += 12;
  if (n >= 200) score += 25;
  else if (n >= 150) score += 18;
  else if (n >= 100) score += 10;
  if (p >= 30) score += 25;
  else if (p >= 20) score += 18;
  else if (p >= 10) score += 10;
  if (k >= 200) score += 25;
  else if (k >= 120) score += 18;
  else if (k >= 80) score += 10;
  if (score >= 85) return "A";
  if (score >= 65) return "B";
  if (score >= 45) return "C";
  return "D";
}

const GRADE_TRANSLATION_KEYS: Record<Grade, string> = {
  A: "excellentFertilityLabel",
  B: "goodFertilityLabel",
  C: "moderateFertilityLabel",
  D: "poorFertilityLabel",
};

function getPhStatus(ph: number): "acidic" | "neutral" | "alkaline" {
  if (ph < 6.0) return "acidic";
  if (ph <= 7.5) return "neutral";
  return "alkaline";
}

function parseCropLine(line: string): { name: string; pct: number } | null {
  const m = line.match(/^[-•]?\s*(.+?)\s*[—–-]\s*(\d+)%/);
  if (m) return { name: m[1].trim(), pct: parseInt(m[2]) };
  return null;
}

// ─── AI streaming helper ──────────────────────────────────────────────────────

async function streamSoilAnalysis(
  ph: number,
  n: number,
  p: number,
  k: number,
  texture: string,
  grade: Grade,
  lang: string,
  onUpdate: (
    crops: Array<{ name: string; pct: number }>,
    deficiencies: string,
    plan: string,
  ) => void,
) {
  const api_url = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const resp = await fetch(`${api_url}/soil/analyse`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${localStorage.getItem("agrigpt_token")}`
    },
    body: JSON.stringify({ ph, n, p, k, texture, grade, lang }),
  });

  if (!resp.ok) throw new Error(`API error: ${resp.status}`);

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let fullText = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    for (const line of chunk.split("\n")) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6);
      if (data === "[DONE]") break;
      try {
        const parsed = JSON.parse(data);
        if (parsed.type === "content_block_delta" && parsed.delta?.text) {
          fullText += parsed.delta.text;
        }
      } catch {
        /* skip malformed SSE lines */
      }
    }

    // Parse sections from the accumulated text and emit partial updates
    const cropsMatch = fullText.match(
      /TOP 3 CROPS:([\s\S]*?)(?=DEFICIENCIES:|IMPROVEMENT PLAN:|$)/i,
    );
    const defMatch = fullText.match(/DEFICIENCIES:([\s\S]*?)(?=IMPROVEMENT PLAN:|$)/i);
    const planMatch = fullText.match(/IMPROVEMENT PLAN:([\s\S]*?)$/i);

    const crops: Array<{ name: string; pct: number }> = [];
    if (cropsMatch) {
      cropsMatch[1]
        .trim()
        .split("\n")
        .forEach((line) => {
          const c = parseCropLine(line);
          if (c) crops.push(c);
        });
    }

    onUpdate(crops, defMatch ? defMatch[1].trim() : "", planMatch ? planMatch[1].trim() : "");
  }
}

// ─── Status translation key mapping ──────────────────────────────────────────

const STATUS_TRANSLATION_KEYS: Record<Status, string> = {
  ok: "statusGood",
  low: "statusLow",
  def: "statusDeficient",
};

// ─── Component ────────────────────────────────────────────────────────────────

function Soil() {
  const { t, lang } = useTranslation();

  const [texture, setTexture] = useState<Texture>("loamy");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SoilResult | null>(null);

  // AI streaming state (separate from static result so it streams in)
  const [aiCrops, setAiCrops] = useState<Array<{ name: string; pct: number }>>([]);
  const [aiDef, setAiDef] = useState("");
  const [aiPlan, setAiPlan] = useState("");

  const phRef = useRef<HTMLInputElement>(null);
  const nRef = useRef<HTMLInputElement>(null);
  const pRef = useRef<HTMLInputElement>(null);
  const kRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setAiCrops([]);
    setAiDef("");
    setAiPlan("");

    const ph = parseFloat(phRef.current?.value ?? "6.4");
    const n = parseInt(nRef.current?.value ?? "180");
    const p = parseInt(pRef.current?.value ?? "22");
    const k = parseInt(kRef.current?.value ?? "140");

    const grade = computeGrade(ph, n, p, k);
    const { nStatus, pStatus, kStatus } = getNutrientStatus(n, p, k);

    setResult({
      grade,
      gradeLabel: t(GRADE_TRANSLATION_KEYS[grade]),
      ph,
      n,
      p,
      k,
      phStatus: getPhStatus(ph),
      nStatus,
      pStatus,
      kStatus,
      crops: [], // filled by AI stream
      deficiencies: "", // filled by AI stream
      improvementPlan: "",
    });

    setLoading(true);
    try {
      await streamSoilAnalysis(ph, n, p, k, texture, grade, lang, (crops, def, plan) => {
        setAiCrops(crops);
        setAiDef(def);
        setAiPlan(plan);
      });
    } catch (err) {
      setError((err as Error).message ?? "Failed to fetch AI recommendations");
    } finally {
      setLoading(false);
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <PageWrapper title={t("soilAnalyzer")}>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ── Input card ─────────────────────────────────────────── */}
        <Card>
          <Label>{t("soilParameters")}</Label>
          <form className="mt-3 space-y-3" onSubmit={handleSubmit}>
            <Field label={t("ph")}>
              <Input ref={phRef} type="number" step="0.1" defaultValue={6.4} min={0} max={14} />
            </Field>
            <Field label={t("nitrogen")}>
              <Input ref={nRef} type="number" step="1" defaultValue={180} min={0} />
            </Field>
            <Field label={t("phosphorus")}>
              <Input ref={pRef} type="number" step="1" defaultValue={22} min={0} />
            </Field>
            <Field label={t("potassium")}>
              <Input ref={kRef} type="number" step="1" defaultValue={140} min={0} />
            </Field>

            <div>
              <Label>{t("soilTexture")}</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {(["sandy", "loamy", "clay", "black"] as const).map((tItem) => (
                  <label
                    key={tItem}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md cursor-pointer"
                    style={{
                      border: `1px solid ${texture === tItem ? "#3b6d11" : "#e5e7eb"}`,
                      background: texture === tItem ? "#f0f5ea" : "#fff",
                      color: texture === tItem ? "#3b6d11" : "#1a1a1a",
                      fontSize: 13,
                    }}
                  >
                    <input
                      type="radio"
                      name="texture"
                      className="sr-only"
                      checked={texture === tItem}
                      onChange={() => setTexture(tItem)}
                    />
                    {t(tItem)}
                  </label>
                ))}
              </div>
            </div>

            <Button type="submit" className="w-full mt-2" disabled={loading}>
              {loading ? t("analysing") : t("analyseSoil")}
            </Button>
          </form>
        </Card>

        {/* ── Result card ─────────────────────────────────────────── */}
        {result && (
          <Card>
            {/* Grade header */}
            <div className="flex items-center gap-3">
              <div
                className="px-3 py-1 rounded-full"
                style={{
                  background: "#f0f5ea",
                  color: "#3b6d11",
                  fontSize: 32,
                  fontWeight: 500,
                  lineHeight: 1,
                }}
              >
                {result.grade}
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: "#1a1a1a" }}>
                  {t("soilGrade")} · {result.grade}
                </div>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{result.gradeLabel}</div>
              </div>
            </div>

            {/* Nutrient bars — from static local calculation */}
            <div className="mt-5 space-y-3">
              <NutrientBar
                label={t("nitrogen")}
                value={result.n}
                max={280}
                status={result.nStatus}
                statusLabel={t(STATUS_TRANSLATION_KEYS[result.nStatus])}
              />
              <NutrientBar
                label={t("phosphorus")}
                value={result.p}
                max={60}
                status={result.pStatus}
                statusLabel={t(STATUS_TRANSLATION_KEYS[result.pStatus])}
              />
              <NutrientBar
                label={t("potassium")}
                value={result.k}
                max={280}
                status={result.kStatus}
                statusLabel={t(STATUS_TRANSLATION_KEYS[result.kStatus])}
              />
            </div>

            {/* Top crops — streamed from AI */}
            <div className="mt-5">
              <Label>{t("topRecommendedCrops")}</Label>
              {aiCrops.length === 0 && loading && <LoadingDots />}
              {aiCrops.length > 0 && (
                <ul className="mt-2 divide-y" style={{ borderColor: "#f5f5f5" }}>
                  {aiCrops.map(({ name, pct }) => (
                    <li
                      key={name}
                      className="flex items-center justify-between py-2"
                      style={{ fontSize: 13 }}
                    >
                      <span style={{ color: "#1a1a1a" }}>{name}</span>
                      <span style={{ color: "#639922" }}>
                        {pct}% {t("suitability")}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Deficiencies — streamed */}
            {(aiDef || loading) && (
              <div className="mt-5">
                <Label>{t("deficienciesDetected")}</Label>
                {aiDef ? (
                  <div className="mt-2">
                    <MarkdownText>{aiDef}</MarkdownText>
                  </div>
                ) : (
                  <LoadingDots />
                )}
              </div>
            )}

            {/* Improvement plan — streamed */}
            {(aiPlan || loading) && (
              <div className="mt-5">
                <Label>{t("improvementTips")}</Label>
                {aiPlan ? (
                  <div className="mt-2">
                    <MarkdownText>{aiPlan}</MarkdownText>
                  </div>
                ) : (
                  <LoadingDots />
                )}
              </div>
            )}

            {/* Error state */}
            {error && (
              <div
                className="mt-4 rounded-md p-3"
                style={{
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  fontSize: 13,
                  color: "#b91c1c",
                }}
              >
                {error}
              </div>
            )}
          </Card>
        )}
      </div>
    </PageWrapper>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}

function LoadingDots() {
  return (
    <div className="flex gap-1 mt-2 items-center" style={{ height: 20 }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="rounded-full"
          style={{
            width: 6,
            height: 6,
            background: "#639922",
            opacity: 0.3,
            animation: `blink 1s ${i * 0.2}s infinite`,
          }}
        />
      ))}
      <style>{`@keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}`}</style>
    </div>
  );
}
