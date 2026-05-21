import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Card, Label, Input, Button, Select } from "../components/ui/primitives";
import { useTranslation } from "../contexts/LanguageContext";
import { Loader2, Leaf, AlertCircle } from "lucide-react";

export const Route = createFileRoute("/fertilizer")({ component: Fertilizer });

function Fertilizer() {
  const { t } = useTranslation();
  
  const [crop, setCrop] = useState("Tomato");
  const [soilType, setSoilType] = useState("Red loamy soil");
  const [growthStage, setGrowthStage] = useState("Vegetative");
  const [symptoms, setSymptoms] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);

  const handleRecommend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!crop || !soilType || !growthStage) {
      alert("Please fill in all required fields.");
      return;
    }
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const api_url = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";
      const res = await fetch(`${api_url}/fertilizer/recommend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("agrigpt_token")}`
        },
        body: JSON.stringify({
          crop: crop.trim(),
          soil_type: soilType.trim(),
          growth_stage: growthStage.trim(),
          symptoms: symptoms.trim() || undefined
        })
      });
      
      if (!res.ok) {
        throw new Error("Failed to get recommendation from backend.");
      }
      
      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper title={t("fertilizerRecommendation") || "Fertilizer Recommendation"}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Input Card */}
        <Card className="lg:col-span-1">
          <Label>{t("cropDetails") || "Crop Details"}</Label>
          <form className="mt-4 space-y-4" onSubmit={handleRecommend}>
            <div>
              <Label>{t("crop")}</Label>
              <Input 
                className="mt-1.5" 
                value={crop} 
                onChange={(e) => setCrop(e.target.value)} 
                placeholder="e.g., Tomato" 
              />
            </div>
            
            <div>
              <Label>{t("soilType") || "Soil Type"}</Label>
              <Input 
                className="mt-1.5" 
                value={soilType} 
                onChange={(e) => setSoilType(e.target.value)} 
                placeholder="e.g., Red loamy soil, Black cotton" 
              />
            </div>
            
            <div>
              <Label>{t("growthStage") || "Growth Stage"}</Label>
              <Input 
                className="mt-1.5" 
                value={growthStage} 
                onChange={(e) => setGrowthStage(e.target.value)} 
                placeholder="e.g., Vegetative, Flowering" 
              />
            </div>
            
            <div>
              <Label>{t("visibleSymptoms") || "Visible Symptoms (Optional)"}</Label>
              <Input 
                className="mt-1.5" 
                value={symptoms} 
                onChange={(e) => setSymptoms(e.target.value)} 
                placeholder="e.g., Yellowing leaves" 
              />
            </div>
            
            <Button type="submit" className="w-full mt-2" disabled={loading}>
              {loading ? (
                <div className="flex items-center gap-2 justify-center">
                  <Loader2 size={16} className="animate-spin" />
                  {t("analysing")}
                </div>
              ) : (
                t("getRecommendation") || "Get Recommendation"
              )}
            </Button>
          </form>
          
          {error && (
            <div className="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded border border-red-200 flex items-start gap-2">
              <AlertCircle size={16} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </Card>

        {/* Results */}
        <div className="lg:col-span-2 space-y-4">
          {result ? (
            <>
              {/* Summary */}
              <Card>
                <div className="flex items-start gap-3">
                  <div className="bg-[#f0f5ea] p-2 rounded-full text-[#3b6d11]">
                    <Leaf size={24} />
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">{t("npkSummary") || "NPK Summary"}</h3>
                    <p className="text-gray-600 mt-1">{result.npk_summary}</p>
                  </div>
                </div>
              </Card>

              {/* Schedule */}
              <Card>
                <h3 className="text-lg font-medium text-gray-900 mb-4">{t("fertilizerSchedule") || "Fertilizer Schedule"}</h3>
                <div className="space-y-4">
                  {result.fertilizer_schedule?.map((step: any, idx: number) => (
                    <div key={idx} className="border border-gray-100 rounded-lg p-4 bg-gray-50">
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-medium text-[#3b6d11]">{step.timing}</h4>
                        <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
                          {step.dap_days} Days After Planting
                        </span>
                      </div>
                      
                      <div className="mt-3 space-y-2">
                        {step.fertilizers?.map((f: any, fIdx: number) => (
                          <div key={fIdx} className="flex justify-between items-center bg-white p-2 rounded shadow-sm text-sm border border-gray-100">
                            <span className="font-medium text-gray-800">{f.name}</span>
                            <div className="text-right">
                              <div className="text-gray-900">{f.dose_kg_per_acre} kg/acre</div>
                              <div className="text-xs text-gray-500">{f.nutrient_supplied}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                      
                      {step.notes && (
                        <p className="mt-3 text-sm text-gray-600 bg-[#fefce8] p-2 rounded border border-[#fef08a]">
                          <span className="font-medium">Note:</span> {step.notes}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </Card>

              {/* Organics & Deficiencies */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">{t("organicAlternatives") || "Organic Alternatives"}</h3>
                  <ul className="space-y-3">
                    {result.organic_alternatives?.map((org: any, idx: number) => (
                      <li key={idx} className="text-sm">
                        <div className="font-medium text-gray-800">{org.name}</div>
                        <div className="text-gray-600">
                          {org.dose_kg_per_acre ? `${org.dose_kg_per_acre} kg/acre` : 'As needed'} · {org.timing}
                        </div>
                        <div className="text-xs text-green-700 mt-0.5">{org.benefit}</div>
                      </li>
                    ))}
                  </ul>
                </Card>

                <Card className="flex flex-col gap-4">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">{t("micronutrients") || "Micronutrients"}</h3>
                    <p className="text-sm text-gray-700">{result.micronutrients}</p>
                  </div>
                  
                  {result.deficiency_treatment && result.deficiency_treatment !== "No specific deficiency reported." && (
                    <div>
                      <h3 className="text-lg font-medium text-red-700 mb-2">{t("deficiencyTreatment") || "Deficiency Treatment"}</h3>
                      <p className="text-sm text-gray-700">{result.deficiency_treatment}</p>
                    </div>
                  )}

                  {result.cautions && (
                    <div className="mt-auto pt-3 border-t border-red-100">
                      <div className="flex items-center gap-1.5 text-red-600 mb-1">
                        <AlertCircle size={14} />
                        <span className="text-sm font-medium">Cautions</span>
                      </div>
                      <p className="text-xs text-gray-600">{result.cautions}</p>
                    </div>
                  )}
                </Card>
              </div>
            </>
          ) : (
            <div className="h-full min-h-[400px] flex items-center justify-center border-2 border-dashed border-gray-200 rounded-xl">
              <div className="text-center max-w-sm px-4">
                <Leaf size={48} className="mx-auto text-gray-300 mb-4" />
                <h3 className="text-gray-900 font-medium">{t("enterCropDetails") || "Enter Crop Details"}</h3>
                <p className="text-sm text-gray-500 mt-2">
                  Fill in your crop, soil type, and growth stage to get an ICAR-compliant fertilizer schedule and recommendations.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageWrapper>
  );
}
