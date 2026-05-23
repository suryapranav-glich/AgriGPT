import { createFileRoute } from "@tanstack/react-router";
import { useState, useRef } from "react";
import { Leaf, Loader2, Bug, FlaskConical, Shield, Sprout, UploadCloud } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Card, Label, SeverityBadge } from "../components/ui/primitives";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/disease")({ component: DiseaseDetection });

// Type for the API response
interface DiagnoseResponse {
  status: "success" | "uncertain";
  plant?: string;
  disease?: string;
  confidence: number;
  severity?: "none" | "mild" | "moderate" | "severe";
  cause?: string;
  organic_treatment?: string;
  chemical_treatment?: string;
  prevention_tips?: string;
  message?: string;
}

function DiseaseDetection() {
  const [state, setState] = useState<"idle" | "loading" | "result">("idle");
  const [resultData, setResultData] = useState<DiagnoseResponse | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { t } = useTranslation();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Show preview
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    setState("loading");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${API_URL}/diagnose`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${localStorage.getItem("agrigpt_token")}` },
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to diagnose image");
      }

      const data: DiagnoseResponse = await response.json();
      setResultData(data);
      setState("result");
    } catch (error) {
      console.error("Error diagnosing:", error);
      alert("Failed to connect to the disease detection server. Ensure the backend is running.");
      setState("idle");
    }
  };

  const triggerUpload = () => fileInputRef.current?.click();

  return (
    <PageWrapper title={t("diseaseDetection")}>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div>
          <Card>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/jpeg, image/png"
              className="hidden"
            />
            <button
              onClick={triggerUpload}
              className="w-full flex flex-col items-center justify-center gap-2 rounded-lg cursor-pointer overflow-hidden relative"
              style={{ border: "2px dashed #e5e7eb", height: 200, background: "#fff" }}
            >
              {previewUrl && state !== "idle" ? (
                <img
                  src={previewUrl}
                  alt="Leaf Preview"
                  className="absolute inset-0 w-full h-full object-cover opacity-30"
                />
              ) : null}
              <div className="z-10 flex flex-col items-center">
                <UploadCloud size={32} strokeWidth={1.5} style={{ color: "#9ca3af" }} />
                <div style={{ fontSize: 14, color: "#1a1a1a", marginTop: 8 }}>
                  {t("dropLeafPhoto")}
                </div>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{t("supportsJPG")}</div>
              </div>
            </button>
          </Card>
          <div className="mt-4">
            <Label>{t("commonExamples")}</Label>
            <div className="grid grid-cols-3 gap-2 mt-2">
              {[{ k: "leafBlight" }, { k: "powderyMildew" }, { k: "rust" }].map((n) => (
                <div
                  key={n.k}
                  className="rounded-lg p-3 text-center"
                  style={{ border: "1px solid #e5e7eb", background: "#fff" }}
                >
                  <div
                    className="rounded-md mx-auto flex items-center justify-center"
                    style={{ width: 56, height: 56, background: "#f7f8f6" }}
                  >
                    <Leaf size={24} strokeWidth={1.5} style={{ color: "#639922" }} />
                  </div>
                  <div style={{ fontSize: 12, color: "#6b7280", marginTop: 6 }}>{t(n.k)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div>
          {state === "idle" && (
            <Card>
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <Sprout size={28} strokeWidth={1.5} style={{ color: "#9ca3af" }} />
                <div style={{ fontSize: 14, color: "#6b7280", marginTop: 10 }}>
                  {t("uploadPhotoToSee")}
                </div>
              </div>
            </Card>
          )}
          {state === "loading" && (
            <Card>
              <div className="flex items-center gap-3">
                <div className="rounded-lg skeleton" style={{ width: 120, height: 120 }} />
                <div className="flex-1 space-y-2">
                  <div className="h-4 rounded skeleton w-2/3" />
                  <div className="h-3 rounded skeleton w-1/2" />
                  <div className="h-2 rounded skeleton w-full" />
                </div>
              </div>
              <div
                className="flex items-center gap-2 mt-4"
                style={{ fontSize: 13, color: "#6b7280" }}
              >
                <Loader2 size={14} className="animate-spin" /> {t("analysingLeaf")}
              </div>
            </Card>
          )}
          {state === "result" && resultData && (
            <ResultCard data={resultData} t={t} previewUrl={previewUrl} />
          )}
        </div>
      </div>
    </PageWrapper>
  );
}

function ResultCard({
  data,
  t,
  previewUrl,
}: {
  data: DiagnoseResponse;
  t: (key: string) => string;
  previewUrl: string | null;
}) {
  if (data.status === "uncertain") {
    return (
      <Card>
        <div className="flex items-start gap-4 py-4 text-center flex-col items-center">
          <div
            className="rounded-full flex items-center justify-center mb-2"
            style={{ width: 64, height: 64, background: "#fef2f2" }}
          >
            <Shield size={32} strokeWidth={1.5} style={{ color: "#dc2626" }} />
          </div>
          <h2 style={{ fontSize: 18, fontWeight: 500, color: "#1a1a1a" }}>Uncertain Result</h2>
          <p style={{ fontSize: 14, color: "#6b7280" }}>{data.message}</p>
          <button
            className="mt-2 flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors cursor-pointer"
            style={{
              background: "#fef3c7",
              color: "#92400e",
              fontSize: 14,
              border: "1px solid #fde68a",
            }}
          >
            <Shield size={16} /> Consult Agronomist
          </button>
        </div>
      </Card>
    );
  }

  // Map severity string from backend to our component format
  const severityLevel =
    data.severity === "moderate"
      ? "med"
      : data.severity === "severe"
        ? "high"
        : data.severity === "none"
          ? "low"
          : "low";

  return (
    <Card>
      <div className="flex items-start gap-4">
        <div
          className="rounded-lg flex items-center justify-center overflow-hidden"
          style={{ width: 120, height: 120, background: "#f0f5ea", flexShrink: 0 }}
        >
          {previewUrl ? (
            <img src={previewUrl} alt="Analyzed leaf" className="w-full h-full object-cover" />
          ) : (
            <Leaf size={48} strokeWidth={1.5} style={{ color: "#3b6d11" }} />
          )}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h2
              style={{
                fontSize: 18,
                fontWeight: 500,
                color: "#1a1a1a",
                textTransform: "capitalize",
              }}
            >
              {data.plant && data.plant !== "Unknown Plant"
                ? `${data.plant.replace(/_/g, " ")} - `
                : ""}
              {(data.disease || "Healthy").replace(/_/g, " ")}
            </h2>
            <SeverityBadge level={severityLevel} />
          </div>

          {data.confidence < 60 && (
            <button
              className="mt-3 flex items-center gap-2 px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer"
              style={{
                background: "#fef3c7",
                color: "#92400e",
                fontSize: 13,
                border: "1px solid #fde68a",
              }}
            >
              <Shield size={14} /> Consult Agronomist
            </button>
          )}
        </div>
      </div>

      <div className="mt-5 divide-y" style={{ borderColor: "#f5f5f5" }}>
        {data.cause && (
          <Section icon={<Bug size={14} />} title={t("likelyCause") || "Cause"} body={data.cause} />
        )}
        {data.organic_treatment && (
          <Section
            icon={<Sprout size={14} />}
            title={t("organicTreatment") || "Organic Treatment"}
            body={data.organic_treatment}
          />
        )}
        {data.chemical_treatment && (
          <Section
            icon={<FlaskConical size={14} />}
            title={t("chemicalTreatment") || "Chemical Treatment"}
            body={data.chemical_treatment}
          />
        )}
        {data.prevention_tips && (
          <Section
            icon={<Shield size={14} />}
            title={t("preventionTips") || "Prevention Tips"}
            body={data.prevention_tips}
          />
        )}
      </div>
    </Card>
  );
}

function Section({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return (
    <div className="py-3">
      <div className="flex items-center gap-2" style={{ fontSize: 12, color: "#6b7280" }}>
        <span style={{ color: "#3b6d11" }}>{icon}</span> {title}
      </div>
      <p style={{ fontSize: 14, color: "#1a1a1a", marginTop: 4, lineHeight: 1.55 }}>{body}</p>
    </div>
  );
}
