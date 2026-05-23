import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { Search, Loader2, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { SchemeCard } from "../components/ui/SchemeCard";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/schemes")({ component: Schemes });

// ── Types ─────────────────────────────────────────────────────────────────────
interface SchemeAnswer {
  answer: string;
  scheme_name: string;
  eligibility: string;
  how_to_apply: string;
  documents_needed: string[];
  helpline: string;
  amount_or_benefit: string;
  sources: string[];
  state_specific: string;
  tip: string;
  _meta: {
    pdf_chunks_used: number;
    static_hits: number;
    llm_model: string;
  };
}

// ── Constants ─────────────────────────────────────────────────────────────────
const BACKEND = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const filterKeys = ["all", "subsidies", "seeds", "insurance", "credit", "irrigationTab"] as const;

const schemesList = [
  {
    nameKey: "pmKisanName",
    stateKey: "central",
    categoryKey: "subsidies",
    summaryKey: "pmKisanSum",
    url: "https://pmkisan.gov.in",
  },
  {
    nameKey: "pmfbyName",
    stateKey: "central",
    categoryKey: "insurance",
    summaryKey: "pmfbySum",
    url: "https://pmfby.gov.in",
  },
  {
    nameKey: "kccName",
    stateKey: "central",
    categoryKey: "credit",
    summaryKey: "kccSum",
    url: "https://www.nabard.org/content1.aspx?id=572",
  },
  {
    nameKey: "pmksyName",
    stateKey: "central",
    categoryKey: "irrigationTab",
    summaryKey: "pmksySum",
    url: "https://pmksy.gov.in",
  },
  {
    nameKey: "raithaSiriName",
    stateKey: "karnataka",
    categoryKey: "subsidies",
    summaryKey: "raithaSiriSum",
    url: "https://raitamitra.karnataka.gov.in",
  },
  {
    nameKey: "seedMissionName",
    stateKey: "central",
    categoryKey: "seeds",
    summaryKey: "seedMissionSum",
    url: "https://seednet.gov.in",
  },
];

// ── Debounce hook ─────────────────────────────────────────────────────────────
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================
function Schemes() {
  const { t, lang } = useTranslation();
  const [active, setActive] = useState<(typeof filterKeys)[number]>("all");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<SchemeAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);
  const debouncedQ = useDebounce(q.trim(), 700);
  const abortRef = useRef<AbortController | null>(null);

  // Filtered scheme cards
  const list = active === "all" ? schemesList : schemesList.filter((s) => s.categoryKey === active);

  // ── Ask RAG backend ─────────────────────────────────────────────────────────
  // Re-fetch when language changes mid-query
  useEffect(() => {
    if (!debouncedQ || debouncedQ.length < 4) {
      setAnswer(null);
      setError(null);
      return;
    }

    // Cancel previous in-flight request
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    setLoading(true);
    setError(null);
    setAnswer(null);
    setExpanded(false);

    // Detect state from query (simple heuristic — extend as needed)
    const stateMap: Record<string, string> = {
      telangana: "Telangana",
      andhra: "Andhra Pradesh",
      ap: "Andhra Pradesh",
      karnataka: "Karnataka",
      maharashtra: "Maharashtra",
      punjab: "Punjab",
      haryana: "Haryana",
      tamil: "Tamil Nadu",
      kerala: "Kerala",
      gujarat: "Gujarat",
      rajasthan: "Rajasthan",
      madhya: "Madhya Pradesh",
      uttar: "Uttar Pradesh",
    };
    const lower = debouncedQ.toLowerCase();
    const detectedState = Object.keys(stateMap).find((k) => lower.includes(k)) ?? "";
    const state = detectedState ? stateMap[detectedState] : "";

    // Pass current UI language so backend responds in the same language
    const language = lang === "en" || lang === "hi" || lang === "te" ? lang : "en";

    fetch(`${BACKEND}/schemes/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${localStorage.getItem("agrigpt_token")}`
      },
      body: JSON.stringify({ question: debouncedQ, state, language }),
      signal: abortRef.current.signal,
    })
      .then(async (res) => {
        if (res.status === 429) {
          const body = await res.json().catch(() => ({}));
          const detail: string = body?.detail ?? "";
          // Extract retry seconds if present
          const m = detail.match(/(\d+) second/);
          const retryMsg = m ? t("quotaRetry").replace("{s}", m[1]) : t("quotaExceeded");
          throw Object.assign(new Error(retryMsg), { name: "QuotaError" });
        }
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setAnswer(data as SchemeAnswer);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err.message || t("couldNotFetch"));
        setLoading(false);
      });
  }, [debouncedQ, lang]);

  // ── Clear when search is empty ───────────────────────────────────────────
  const handleClear = () => {
    setQ("");
    setAnswer(null);
    setError(null);
  };

  // ==========================================================================
  // RENDER
  // ==========================================================================
  return (
    <PageWrapper title={t("govtSchemes")}>
      {/* ── Search bar ──────────────────────────────────────────────────────── */}
      <div className="max-w-2xl mx-auto">
        <div
          className="flex items-center gap-2 rounded-lg px-3 py-2.5"
          style={{ background: "#fff", border: "1px solid #e5e7eb" }}
        >
          {loading ? (
            <Loader2 size={16} className="animate-spin" style={{ color: "#3b6d11" }} />
          ) : (
            <Search size={16} style={{ color: "#6b7280" }} />
          )}
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("searchSchemes")}
            className="flex-1 bg-transparent outline-none text-[14px]"
            style={{ color: "#1a1a1a" }}
          />
          {q && (
            <button onClick={handleClear} style={{ fontSize: 18, color: "#9ca3af", lineHeight: 1 }}>
              ×
            </button>
          )}
        </div>
        <p style={{ fontSize: 11, color: "#9ca3af", marginTop: 4, paddingLeft: 2 }}>
          Ask anything — e.g. "How to apply for PM-KISAN in Telangana?"
        </p>
      </div>

      {/* ── Error state ─────────────────────────────────────────────────────── */}
      {error && (
        <div
          className="mt-4 rounded-xl p-4 flex items-start gap-3"
          style={{ background: "#fef2f2", border: "1px solid #fecaca" }}
        >
          <AlertCircle size={16} style={{ color: "#dc2626", marginTop: 2, flexShrink: 0 }} />
          <p style={{ fontSize: 13, color: "#dc2626" }}>{error}</p>
        </div>
      )}

      {/* ── Loading skeleton ─────────────────────────────────────────────────── */}
      {loading && (
        <div
          className="mt-4 rounded-xl p-4 animate-pulse"
          style={{ background: "#fff", border: "1px solid #e5e7eb" }}
        >
          <div
            className="h-3 rounded"
            style={{ background: "#f3f4f6", width: "60%", marginBottom: 10 }}
          />
          <div
            className="h-3 rounded"
            style={{ background: "#f3f4f6", width: "90%", marginBottom: 8 }}
          />
          <div className="h-3 rounded" style={{ background: "#f3f4f6", width: "75%" }} />
        </div>
      )}

      {/* ── RAG Answer card ─────────────────────────────────────────────────── */}
      {!loading && answer && (
        <div
          className="mt-4 rounded-xl"
          style={{
            background: "#fff",
            border: "1px solid #e5e7eb",
            borderTop: "3px solid #3b6d11",
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div className="px-4 pt-4 pb-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <span
                  style={{
                    display: "inline-block",
                    fontSize: 10,
                    fontWeight: 600,
                    background: "#f0f5ea",
                    color: "#3b6d11",
                    borderRadius: 4,
                    padding: "2px 8px",
                    marginBottom: 6,
                  }}
                >
                  {answer.scheme_name}
                </span>

                {/* Amount badge */}
                {answer.amount_or_benefit && (
                  <span
                    style={{
                      display: "inline-block",
                      fontSize: 10,
                      fontWeight: 600,
                      background: "#fffbeb",
                      color: "#b45309",
                      borderRadius: 4,
                      padding: "2px 8px",
                      marginBottom: 6,
                      marginLeft: 6,
                    }}
                  >
                    {answer.amount_or_benefit}
                  </span>
                )}
              </div>
            </div>

            {/* Main answer */}
            <p style={{ fontSize: 14, color: "#1a1a1a", lineHeight: 1.65 }}>{answer.answer}</p>
          </div>

          {/* Expandable details */}
          <button
            onClick={() => setExpanded((p) => !p)}
            className="w-full flex items-center justify-between px-4 py-2"
            style={{ background: "#f9fafb", borderTop: "1px solid #f3f4f6", cursor: "pointer" }}
          >
            <span style={{ fontSize: 12, color: "#3b6d11", fontWeight: 600 }}>
              {expanded ? "Hide details" : "Show eligibility, documents & how to apply"}
            </span>
            {expanded ? (
              <ChevronUp size={14} style={{ color: "#3b6d11" }} />
            ) : (
              <ChevronDown size={14} style={{ color: "#3b6d11" }} />
            )}
          </button>

          {expanded && (
            <div className="px-4 py-3" style={{ borderTop: "1px solid #f3f4f6" }}>
              {/* Eligibility */}
              <div className="mb-3">
                <p
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: "#6b7280",
                    textTransform: "uppercase",
                    marginBottom: 4,
                  }}
                >
                  Who is eligible
                </p>
                <p style={{ fontSize: 13, color: "#374151", lineHeight: 1.55 }}>
                  {answer.eligibility}
                </p>
              </div>

              {/* How to apply */}
              <div className="mb-3">
                <p
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    color: "#6b7280",
                    textTransform: "uppercase",
                    marginBottom: 4,
                  }}
                >
                  How to apply
                </p>
                <p style={{ fontSize: 13, color: "#374151", lineHeight: 1.55 }}>
                  {answer.how_to_apply}
                </p>
              </div>

              {/* Documents */}
              {answer.documents_needed?.length > 0 && (
                <div className="mb-3">
                  <p
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: "#6b7280",
                      textTransform: "uppercase",
                      marginBottom: 4,
                    }}
                  >
                    Documents needed
                  </p>
                  <ul style={{ margin: 0, paddingLeft: 16 }}>
                    {answer.documents_needed.map((doc, i) => (
                      <li key={i} style={{ fontSize: 13, color: "#374151", marginBottom: 2 }}>
                        {doc}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* State-specific */}
              {answer.state_specific &&
                answer.state_specific !== "Applies across all Indian states" && (
                  <div
                    className="mb-3 rounded-lg p-3"
                    style={{ background: "#f0f5ea", border: "1px solid #d1e8b0" }}
                  >
                    <p
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        color: "#3b6d11",
                        textTransform: "uppercase",
                        marginBottom: 3,
                      }}
                    >
                      State-specific note
                    </p>
                    <p style={{ fontSize: 13, color: "#374151" }}>{answer.state_specific}</p>
                  </div>
                )}

              {/* Tip */}
              {answer.tip && (
                <div
                  className="mb-3 rounded-lg p-3"
                  style={{ background: "#fffbeb", border: "1px solid #fde68a" }}
                >
                  <p
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: "#b45309",
                      textTransform: "uppercase",
                      marginBottom: 3,
                    }}
                  >
                    Quick tip
                  </p>
                  <p style={{ fontSize: 13, color: "#374151" }}>{answer.tip}</p>
                </div>
              )}

              {/* Helpline */}
              {answer.helpline && (
                <div className="mb-3 flex items-center gap-2">
                  <p
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      color: "#6b7280",
                      textTransform: "uppercase",
                    }}
                  >
                    Helpline:
                  </p>
                  <p style={{ fontSize: 13, color: "#1a1a1a", fontWeight: 500 }}>
                    {answer.helpline}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Footer — sources */}
          <div
            className="px-4 py-2 flex flex-wrap items-center gap-2"
            style={{ borderTop: "1px solid #f3f4f6", background: "#fafafa" }}
          >
            <span style={{ fontSize: 11, color: "#9ca3af" }}>Sources:</span>
            {answer.sources?.map((src, i) => (
              <span
                key={i}
                style={{
                  fontSize: 10,
                  color: "#6b7280",
                  background: "#f3f4f6",
                  borderRadius: 4,
                  padding: "1px 6px",
                }}
              >
                {src}
              </span>
            ))}
            {answer._meta?.pdf_chunks_used > 0 && (
              <span style={{ fontSize: 10, color: "#9ca3af" }}>
                · {answer._meta.pdf_chunks_used} PDF chunk
                {answer._meta.pdf_chunks_used > 1 ? "s" : ""} used
              </span>
            )}
          </div>
        </div>
      )}

      {/* ── Category filters ─────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2 mt-4">
        {filterKeys.map((f) => {
          const a = f === active;
          return (
            <button
              key={f}
              onClick={() => setActive(f)}
              className="px-3 py-1.5 rounded-full text-[12px]"
              style={{
                background: a ? "#f0f5ea" : "#fff",
                color: a ? "#3b6d11" : "#6b7280",
                border: `1px solid ${a ? "#3b6d11" : "#e5e7eb"}`,
              }}
            >
              {t(f)}
            </button>
          );
        })}
      </div>

      {/* ── Scheme cards ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
        {list.map((s) => (
          <SchemeCard key={s.nameKey} {...s} />
        ))}
      </div>
    </PageWrapper>
  );
}
