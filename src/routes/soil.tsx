import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Card, Label, Input, Button } from "../components/ui/primitives";
import { NutrientBar } from "../components/ui/NutrientBar";
import { useTranslation } from "../contexts/LanguageContext";

export const Route = createFileRoute("/soil")({ component: Soil });

function Soil() {
  const [done, setDone] = useState(false);
  const [texture, setTexture] = useState("loamy");
  const { t } = useTranslation();

  return (
    <PageWrapper title={t("soilAnalyzer")}>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <Label>{t("soilParameters")}</Label>
          <form className="mt-3 space-y-3" onSubmit={(e) => { e.preventDefault(); setDone(true); }}>
            <Field label={t("ph")}><Input type="number" step="0.1" defaultValue={6.4} /></Field>
            <Field label={t("nitrogen")}><Input type="number" defaultValue={180} /></Field>
            <Field label={t("phosphorus")}><Input type="number" defaultValue={22} /></Field>
            <Field label={t("potassium")}><Input type="number" defaultValue={140} /></Field>
            <div>
              <Label>{t("soilTexture")}</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {(["sandy", "loamy", "clay", "black"] as const).map((tItem) => (
                  <label key={tItem} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md cursor-pointer"
                    style={{
                      border: `1px solid ${texture === tItem ? "#3b6d11" : "#e5e7eb"}`,
                      background: texture === tItem ? "#f0f5ea" : "#fff",
                      color: texture === tItem ? "#3b6d11" : "#1a1a1a", fontSize: 13,
                    }}>
                    <input type="radio" name="texture" className="sr-only"
                      checked={texture === tItem} onChange={() => setTexture(tItem)} />
                    {t(tItem)}
                  </label>
                ))}
              </div>
            </div>
            <Button type="submit" className="w-full mt-2">{t("analyseSoil")}</Button>
          </form>
        </Card>

        {done && (
          <Card>
            <div className="flex items-center gap-3">
              <div className="px-3 py-1 rounded-full" style={{ background: "#f0f5ea", color: "#3b6d11", fontSize: 32, fontWeight: 500, lineHeight: 1 }}>B</div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, color: "#1a1a1a" }}>{t("soilGrade")} · B</div>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{t("goodFertility")}</div>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              <NutrientBar label={t("nitrogen")} value={180} max={280} status="ok" />
              <NutrientBar label={t("phosphorus")} value={22} max={60} status="def" />
              <NutrientBar label={t("potassium")} value={140} max={280} status="low" />
            </div>

            <div className="mt-5">
              <Label>{t("topRecommendedCrops")}</Label>
              <ul className="mt-2 divide-y" style={{ borderColor: "#f5f5f5" }}>
                {[
                  ["tomato", 92], ["chilli", 88], ["maize", 81],
                ].map(([n, p]) => (
                  <li key={n as string} className="flex items-center justify-between py-2"
                      style={{ fontSize: 13 }}>
                    <span style={{ color: "#1a1a1a" }}>{t(n as string)}</span>
                    <span style={{ color: "#639922" }}>{p}% {t("suitability")}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-5">
              <Label>{t("improvementTips")}</Label>
              <ol className="mt-2 list-decimal pl-5 space-y-2" style={{ fontSize: 13, color: "#1a1a1a" }}>
                <li style={{ borderBottom: "1px solid #f5f5f5", paddingBottom: 8 }}>{t("soilTip1")}</li>
                <li style={{ borderBottom: "1px solid #f5f5f5", paddingBottom: 8 }}>{t("soilTip2")}</li>
                <li>{t("soilTip3")}</li>
              </ol>
            </div>
          </Card>
        )}
      </div>
    </PageWrapper>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}
