import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Leaf, Loader2, Bug, FlaskConical, Shield, Sprout } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Card, Label, SeverityBadge, Button } from "../components/ui/primitives";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/disease")({ component: DiseaseDetection });

function DiseaseDetection() {
  const [state, setState] = useState<"idle" | "loading" | "result">("idle");
  const onUpload = () => { setState("loading"); setTimeout(() => setState("result"), 1500); };
  const { t } = useTranslation();

  return (
    <PageWrapper title={t("diseaseDetection")}>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div>
          <Card>
            <button
              onClick={onUpload}
              className="w-full flex flex-col items-center justify-center gap-2 rounded-lg cursor-pointer"
              style={{ border: "2px dashed #e5e7eb", height: 200, background: "#fff" }}
            >
              <Leaf size={32} strokeWidth={1.5} style={{ color: "#9ca3af" }} />
              <div style={{ fontSize: 14, color: "#1a1a1a" }}>{t("dropLeafPhoto")}</div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>{t("supportsJPG")}</div>
            </button>
          </Card>
          <div className="mt-4">
            <Label>{t("commonExamples")}</Label>
            <div className="grid grid-cols-3 gap-2 mt-2">
              {[{k: "leafBlight"}, {k: "powderyMildew"}, {k: "rust"}].map((n) => (
                <div key={n.k} className="rounded-lg p-3 text-center"
                     style={{ border: "1px solid #e5e7eb", background: "#fff" }}>
                  <div className="rounded-md mx-auto flex items-center justify-center"
                       style={{ width: 56, height: 56, background: "#f7f8f6" }}>
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
                <div style={{ fontSize: 14, color: "#6b7280", marginTop: 10 }}>{t("uploadPhotoToSee")}</div>
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
              <div className="flex items-center gap-2 mt-4" style={{ fontSize: 13, color: "#6b7280" }}>
                <Loader2 size={14} className="animate-spin" /> {t("analysingLeaf")}
              </div>
            </Card>
          )}
          {state === "result" && <ResultCard t={t} />}
        </div>
      </div>
    </PageWrapper>
  );
}

function ResultCard({ t }: { t: (key: string) => string }) {
  return (
    <Card>
      <div className="flex items-start gap-4">
        <div className="rounded-lg flex items-center justify-center" style={{ width: 120, height: 120, background: "#f0f5ea" }}>
          <Leaf size={48} strokeWidth={1.5} style={{ color: "#3b6d11" }} />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h2 style={{ fontSize: 18, fontWeight: 500, color: "#1a1a1a" }}>{t("earlyLeafBlight")}</h2>
            <SeverityBadge level="med" />
          </div>
          <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>{t("alternariaSolani")}</div>
          <div className="mt-4">
            <div className="flex items-center justify-between" style={{ fontSize: 12, color: "#6b7280" }}>
              <span>{t("confidence")}</span><span>87%</span>
            </div>
            <div className="w-full rounded-full mt-1" style={{ height: 4, background: "#f3f4f6" }}>
              <div style={{ width: "87%", height: "100%", background: "#639922", borderRadius: 999 }} />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 divide-y" style={{ borderColor: "#f5f5f5" }}>
        <Section icon={<Bug size={14} />} title={t("likelyCause")}
          body={t("causeDesc")} />
        <Section icon={<Sprout size={14} />} title={t("organicTreatment")}
          body={t("organicDesc")} />
        <Section icon={<FlaskConical size={14} />} title={t("chemicalTreatment")}
          body={t("chemicalDesc")} />
        <Section icon={<Shield size={14} />} title={t("preventionTips")}
          body={t("preventionDesc")} />
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

void Button;
