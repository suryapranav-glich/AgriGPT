# =============================================================================
# AgriGPT — Feature 3: Fertilizer Recommendation Engine
# fertilizer/static_kb.py
#
# Static ICAR-aligned knowledge base.
# Used as fallback when the FAISS index has no relevant chunks,
# or when no PDFs have been ingested yet.
#
# All doses are in kg/acre unless stated otherwise.
# Source: ICAR Nutrient Management Guidelines (public domain).
# =============================================================================

# Keys: lowercase crop name.  soil_type modifiers are applied at query time.
STATIC_KB: dict[str, dict] = {

    # ── TOMATO ────────────────────────────────────────────────────────────────
    "tomato": {
        "npk_summary": "N:P:K = 100:50:50 kg/acre (full season)",
        "fertilizer_schedule": [
            {
                "timing": "Basal (at transplanting)",
                "dap_days": 0,
                "fertilizers": [
                    {"name": "DAP (18:46:00)", "dose_kg_per_acre": 25,
                     "nutrient_supplied": "Phosphorus + starter N"},
                    {"name": "MOP (00:00:60)", "dose_kg_per_acre": 17,
                     "nutrient_supplied": "Potassium"},
                    {"name": "Urea (46% N)",   "dose_kg_per_acre": 22,
                     "nutrient_supplied": "Nitrogen (basal split)"},
                ],
                "notes": "Mix thoroughly in topsoil before transplanting. Apply Zinc Sulphate 5 kg/acre if soil Zn < 0.6 ppm.",
            },
            {
                "timing": "First top-dressing (vegetative)",
                "dap_days": 25,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 25,
                     "nutrient_supplied": "Nitrogen"},
                ],
                "notes": "Side-dress near drip line. Water immediately after application.",
            },
            {
                "timing": "Second top-dressing (flowering)",
                "dap_days": 45,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 20,
                     "nutrient_supplied": "Nitrogen"},
                    {"name": "SOP (00:00:50)", "dose_kg_per_acre": 10,
                     "nutrient_supplied": "Potassium — improves fruit quality"},
                ],
                "notes": "Avoid excess N at this stage to prevent excessive vegetative growth.",
            },
            {
                "timing": "Fruit development",
                "dap_days": 65,
                "fertilizers": [
                    {"name": "SOP", "dose_kg_per_acre": 10,
                     "nutrient_supplied": "Potassium — improves fruit size & brix"},
                    {"name": "Calcium Nitrate", "dose_kg_per_acre": 5,
                     "nutrient_supplied": "Ca + N — prevents blossom-end rot"},
                ],
                "notes": "Foliar spray of 0.5% Boron (Borax) helps fruit set.",
            },
        ],
        "organic_alternatives": [
            {"name": "FYM (Farm Yard Manure)", "dose_kg_per_acre": 2000,
             "timing": "Basal", "benefit": "Improves water retention; slow-release NPK"},
            {"name": "Vermicompost", "dose_kg_per_acre": 400,
             "timing": "Basal", "benefit": "Rich in micronutrients; improves soil biota"},
            {"name": "Neem Cake",    "dose_kg_per_acre": 80,
             "timing": "Basal", "benefit": "Slow-release N + nematicidal properties"},
            {"name": "Panchagavya 3% foliar", "dose_kg_per_acre": None,
             "timing": "Every 15 days", "benefit": "Micronutrient supplement; improves immunity"},
        ],
        "micronutrients": "Zinc Sulphate 5 kg/acre (basal). Boron 0.5% foliar at flowering.",
        "cautions": "Avoid excess N at flowering — leads to fruit cracking. Maintain Ca supply throughout.",
        "icar_source": "ICAR — Package of Practices for Vegetable Crops (Tomato)",
    },

    # ── POTATO ────────────────────────────────────────────────────────────────
    "potato": {
        "npk_summary": "N:P:K = 120:50:80 kg/acre (full season)",
        "fertilizer_schedule": [
            {
                "timing": "Basal (at planting)",
                "dap_days": 0,
                "fertilizers": [
                    {"name": "DAP",  "dose_kg_per_acre": 50, "nutrient_supplied": "P + starter N"},
                    {"name": "MOP",  "dose_kg_per_acre": 53, "nutrient_supplied": "K"},
                    {"name": "Urea", "dose_kg_per_acre": 50, "nutrient_supplied": "N (half dose)"},
                ],
                "notes": "Apply in furrows 5 cm below and beside seed tubers.",
            },
            {
                "timing": "First earthing-up",
                "dap_days": 25,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 50, "nutrient_supplied": "N (second half)"},
                ],
                "notes": "Cover with soil during earthing-up operation. Ensures deep root N uptake.",
            },
        ],
        "organic_alternatives": [
            {"name": "FYM",         "dose_kg_per_acre": 2500, "timing": "Basal",
             "benefit": "Improves tuber bulking; reduces scab"},
            {"name": "Vermicompost","dose_kg_per_acre": 500,  "timing": "Basal",
             "benefit": "Balanced micronutrients"},
            {"name": "Wood Ash",    "dose_kg_per_acre": 120,  "timing": "Basal",
             "benefit": "Potassium source; raises soil pH slightly"},
        ],
        "micronutrients": "Zinc Sulphate 5 kg/acre basal. Boron 0.5% foliar at tuber initiation.",
        "cautions": "Excessive K can suppress Mg uptake. Monitor Mg levels in sandy soils.",
        "icar_source": "ICAR — Nutrient Management in Potato",
    },

    # ── RICE / PADDY ──────────────────────────────────────────────────────────
    "rice": {
        "npk_summary": "N:P:K = 80:40:40 kg/acre (Kharif); 100:50:50 (Rabi/Boro)",
        "fertilizer_schedule": [
            {
                "timing": "Basal (at transplanting)",
                "dap_days": 0,
                "fertilizers": [
                    {"name": "DAP",  "dose_kg_per_acre": 22, "nutrient_supplied": "P + N"},
                    {"name": "MOP",  "dose_kg_per_acre": 13, "nutrient_supplied": "K"},
                    {"name": "Urea", "dose_kg_per_acre": 27, "nutrient_supplied": "N (1/3 dose)"},
                ],
                "notes": "Drain field before basal application. Flood 3 days after transplanting.",
            },
            {
                "timing": "Active tillering",
                "dap_days": 21,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 27, "nutrient_supplied": "N (1/3 dose)"},
                ],
                "notes": "Drain field, broadcast, flood after 2 days.",
            },
            {
                "timing": "Panicle initiation",
                "dap_days": 55,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 27, "nutrient_supplied": "N (final 1/3)"},
                    {"name": "MOP",  "dose_kg_per_acre": 13, "nutrient_supplied": "K (split)"},
                ],
                "notes": "Critical stage for grain filling. Do not skip.",
            },
        ],
        "organic_alternatives": [
            {"name": "Green Manure (Sesbania)", "dose_kg_per_acre": None,
             "timing": "Incorporate 20 days before transplanting",
             "benefit": "Adds ~30 kg N/acre; improves soil organic matter"},
            {"name": "Azolla",        "dose_kg_per_acre": None, "timing": "Post-transplant",
             "benefit": "Bio-N fixation; suppresses weeds"},
            {"name": "FYM",           "dose_kg_per_acre": 2000, "timing": "Basal",
             "benefit": "Improves soil structure in puddled conditions"},
        ],
        "micronutrients": "Zinc Sulphate 10 kg/acre basal if soil Zn < 0.6 ppm (common in alluvial soils).",
        "cautions": "Avoid urea application when field is flooded to minimise volatilisation losses. Use neem-coated urea where available.",
        "icar_source": "ICAR — Integrated Nutrient Management in Rice",
    },

    # ── WHEAT ─────────────────────────────────────────────────────────────────
    "wheat": {
        "npk_summary": "N:P:K = 120:60:40 kg/acre",
        "fertilizer_schedule": [
            {
                "timing": "Basal (at sowing)",
                "dap_days": 0,
                "fertilizers": [
                    {"name": "DAP",  "dose_kg_per_acre": 44, "nutrient_supplied": "Full P + starter N"},
                    {"name": "MOP",  "dose_kg_per_acre": 26, "nutrient_supplied": "Full K"},
                    {"name": "Urea", "dose_kg_per_acre": 50, "nutrient_supplied": "N (half dose)"},
                ],
                "notes": "Drill basal fertilisers 5 cm below the seed.",
            },
            {
                "timing": "First irrigation (CRI stage)",
                "dap_days": 21,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 50, "nutrient_supplied": "N (second half)"},
                ],
                "notes": "Apply just before or after first irrigation. Do not delay beyond CRI.",
            },
        ],
        "organic_alternatives": [
            {"name": "FYM",         "dose_kg_per_acre": 2000, "timing": "Pre-sowing",
             "benefit": "Improves soil organic carbon; slow-release NPK"},
            {"name": "Vermicompost","dose_kg_per_acre": 400,  "timing": "Basal",
             "benefit": "Balanced micronutrients; improves root growth"},
        ],
        "micronutrients": "Zinc Sulphate 5 kg/acre basal on Zn-deficient soils.",
        "cautions": "Split N application is critical to minimise leaching. Excess N causes lodging.",
        "icar_source": "ICAR — Soil Fertility and Fertiliser Use — Wheat",
    },

    # ── MAIZE / CORN ──────────────────────────────────────────────────────────
    "maize": {
        "npk_summary": "N:P:K = 120:50:40 kg/acre",
        "fertilizer_schedule": [
            {
                "timing": "Basal (at sowing)",
                "dap_days": 0,
                "fertilizers": [
                    {"name": "DAP",  "dose_kg_per_acre": 44, "nutrient_supplied": "P + N"},
                    {"name": "MOP",  "dose_kg_per_acre": 26, "nutrient_supplied": "K"},
                    {"name": "Urea", "dose_kg_per_acre": 50, "nutrient_supplied": "N (1/3)"},
                ],
                "notes": "Place 5 cm away from seed to avoid salt burn.",
            },
            {
                "timing": "Knee-high stage",
                "dap_days": 30,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 50, "nutrient_supplied": "N (1/3)"},
                ],
                "notes": "Side-dress in moist soil.",
            },
            {
                "timing": "Tasselling",
                "dap_days": 55,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 50, "nutrient_supplied": "N (final 1/3)"},
                ],
                "notes": "Top-dress before silking for maximum grain fill.",
            },
        ],
        "organic_alternatives": [
            {"name": "FYM",          "dose_kg_per_acre": 2000, "timing": "Basal",
             "benefit": "Improves moisture retention and micronutrient supply"},
            {"name": "Neem Cake",    "dose_kg_per_acre": 100,  "timing": "Basal",
             "benefit": "Slow N release; reduces soil pests"},
        ],
        "micronutrients": "Zinc Sulphate 5 kg/acre basal. Foliar spray of 0.5% ZnSO4 at knee-high if yellowing between veins.",
        "cautions": "Three-split N application is essential for maize. Single basal dose leads to 20-30% yield loss.",
        "icar_source": "ICAR — Nutrient Management in Maize",
    },

    # ── COTTON ────────────────────────────────────────────────────────────────
    "cotton": {
        "npk_summary": "N:P:K = 80:40:40 kg/acre (rainfed); 120:60:60 (irrigated)",
        "fertilizer_schedule": [
            {
                "timing": "Basal (at sowing)",
                "dap_days": 0,
                "fertilizers": [
                    {"name": "DAP",  "dose_kg_per_acre": 44, "nutrient_supplied": "P + N"},
                    {"name": "MOP",  "dose_kg_per_acre": 26, "nutrient_supplied": "K"},
                ],
                "notes": "Full P and K as basal. Add S (Gypsum 40 kg/acre) on S-deficient soils.",
            },
            {
                "timing": "40 days after sowing",
                "dap_days": 40,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 55, "nutrient_supplied": "N (1st split)"},
                ],
                "notes": "Ensure good soil moisture. Side-dress between rows.",
            },
            {
                "timing": "75 days (boll development)",
                "dap_days": 75,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 55, "nutrient_supplied": "N (2nd split)"},
                ],
                "notes": "Avoid N after 90 DAP to prevent late vegetative flush.",
            },
        ],
        "organic_alternatives": [
            {"name": "FYM",      "dose_kg_per_acre": 2000, "timing": "Pre-sowing",
             "benefit": "Improves Vertisol structure"},
            {"name": "Neem Cake","dose_kg_per_acre": 100,  "timing": "Basal",
             "benefit": "Slow N + deters root grubs"},
        ],
        "micronutrients": "Boron 0.5% foliar at squaring and boll setting. Zinc 0.5% foliar if interveinal chlorosis.",
        "cautions": "Excess N beyond 90 DAP delays maturity. K is critical for fibre strength.",
        "icar_source": "ICAR — Nutrient Management in Cotton",
    },

    # ── GROUNDNUT ─────────────────────────────────────────────────────────────
    "groundnut": {
        "npk_summary": "N:P:K = 20:40:40 kg/acre (low N — crop fixes its own)",
        "fertilizer_schedule": [
            {
                "timing": "Basal (at sowing)",
                "dap_days": 0,
                "fertilizers": [
                    {"name": "SSP (Single Super Phosphate)", "dose_kg_per_acre": 100,
                     "nutrient_supplied": "Full P + Ca + S — essential for pod filling"},
                    {"name": "MOP",  "dose_kg_per_acre": 26, "nutrient_supplied": "K"},
                    {"name": "Urea", "dose_kg_per_acre": 22, "nutrient_supplied": "Starter N only"},
                ],
                "notes": "Use SSP (not DAP) — groundnut needs Ca and S. Apply Gypsum 80 kg/acre at peg stage.",
            },
            {
                "timing": "Peg initiation (35–40 DAS)",
                "dap_days": 37,
                "fertilizers": [
                    {"name": "Gypsum", "dose_kg_per_acre": 80,
                     "nutrient_supplied": "Ca + S — directly absorbed by pegs for pod fill"},
                ],
                "notes": "Band-apply gypsum between rows. Critical — do not skip.",
            },
        ],
        "organic_alternatives": [
            {"name": "Rhizobium inoculant", "dose_kg_per_acre": None,
             "timing": "Seed treatment before sowing",
             "benefit": "Fixes atmospheric N — can supply up to 60 kg N/acre"},
            {"name": "FYM",   "dose_kg_per_acre": 2000, "timing": "Pre-sowing",
             "benefit": "Improves sandy soil water retention"},
        ],
        "micronutrients": "Boron 0.5% foliar at flowering. Fe-EDTA foliar if leaf chlorosis on calcareous soils.",
        "cautions": "Do NOT apply heavy N — inhibits Rhizobium nodulation. Rely on bio-N fixation.",
        "icar_source": "ICAR — Groundnut Production Technology",
    },

    # ── SUGARCANE ─────────────────────────────────────────────────────────────
    "sugarcane": {
        "npk_summary": "N:P:K = 200:80:80 kg/acre (plant crop, full season 12 months)",
        "fertilizer_schedule": [
            {
                "timing": "Basal (at planting)",
                "dap_days": 0,
                "fertilizers": [
                    {"name": "DAP",  "dose_kg_per_acre": 44,  "nutrient_supplied": "P + N"},
                    {"name": "MOP",  "dose_kg_per_acre": 53,  "nutrient_supplied": "K (half)"},
                    {"name": "Urea", "dose_kg_per_acre": 44,  "nutrient_supplied": "N (1/4 dose)"},
                ],
                "notes": "Place in planting furrow below setts.",
            },
            {
                "timing": "60 days (tillering)",
                "dap_days": 60,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 65, "nutrient_supplied": "N"},
                ],
                "notes": "Earthing-up operation. Ensure irrigation before application.",
            },
            {
                "timing": "120 days (grand growth)",
                "dap_days": 120,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 65, "nutrient_supplied": "N"},
                    {"name": "MOP",  "dose_kg_per_acre": 53, "nutrient_supplied": "K (second half)"},
                ],
                "notes": "Second earthing-up. K at this stage improves sucrose content.",
            },
            {
                "timing": "180 days",
                "dap_days": 180,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 65, "nutrient_supplied": "N (final)"},
                ],
                "notes": "Last N application. Do not apply after 8 months.",
            },
        ],
        "organic_alternatives": [
            {"name": "Pressmud (filter cake)", "dose_kg_per_acre": 2000,
             "timing": "Pre-planting", "benefit": "Rich in Ca, P, micronutrients; mill by-product"},
            {"name": "FYM",  "dose_kg_per_acre": 4000, "timing": "Basal",
             "benefit": "Improves soil organic matter and water-holding capacity"},
        ],
        "micronutrients": "Zinc Sulphate 10 kg/acre basal. Iron Sulphate 10 kg/acre if yellowing on alkaline soils.",
        "cautions": "Stagger N in 4 splits. Heavy N in one dose causes excessive vegetative growth and reduces sucrose.",
        "icar_source": "ICAR — Sugarcane Cultivation and Nutrient Management",
    },

    # ── BELL PEPPER ───────────────────────────────────────────────────────────
    "bell pepper": {
        "npk_summary": "N:P:K = 80:50:80 kg/acre",
        "fertilizer_schedule": [
            {
                "timing": "Basal (at transplanting)",
                "dap_days": 0,
                "fertilizers": [
                    {"name": "DAP",  "dose_kg_per_acre": 44, "nutrient_supplied": "P + N"},
                    {"name": "MOP",  "dose_kg_per_acre": 53, "nutrient_supplied": "K (half)"},
                    {"name": "Urea", "dose_kg_per_acre": 33, "nutrient_supplied": "N (starter)"},
                ],
                "notes": "Mix in top 15 cm soil before transplanting.",
            },
            {
                "timing": "Vegetative (25 DAT)",
                "dap_days": 25,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 33, "nutrient_supplied": "N"},
                ],
                "notes": "Water immediately after application.",
            },
            {
                "timing": "Fruiting (50 DAT)",
                "dap_days": 50,
                "fertilizers": [
                    {"name": "Urea", "dose_kg_per_acre": 33, "nutrient_supplied": "N"},
                    {"name": "MOP",  "dose_kg_per_acre": 53, "nutrient_supplied": "K (second half)"},
                ],
                "notes": "K at fruiting stage improves fruit wall thickness and vitamin C content.",
            },
        ],
        "organic_alternatives": [
            {"name": "Vermicompost", "dose_kg_per_acre": 400, "timing": "Basal",
             "benefit": "Balanced micronutrient supply"},
            {"name": "Neem Cake",   "dose_kg_per_acre": 80,  "timing": "Basal",
             "benefit": "Slow-release N; deters soil nematodes"},
        ],
        "micronutrients": "Calcium Nitrate foliar 0.5% at fruit set to prevent blossom-end rot.",
        "cautions": "Avoid excess N during fruit development — reduces fruit quality and increases susceptibility to disease.",
        "icar_source": "ICAR — Capsicum / Bell Pepper Production Technology",
    },
}

# Aliases for flexible matching
ALIASES = {
    "paddy"    : "rice",
    "corn"     : "maize",
    "pepper"   : "bell pepper",
    "capsicum" : "bell pepper",
    "chilli"   : "bell pepper",
    "groundnut": "groundnut",
    "peanut"   : "groundnut",
    "cane"     : "sugarcane",
}


def lookup(crop: str) -> dict | None:
    """
    Look up static KB entry by crop name.
    Returns the knowledge dict or None if crop is not in KB.
    """
    key = crop.strip().lower()
    key = ALIASES.get(key, key)
    return STATIC_KB.get(key)
