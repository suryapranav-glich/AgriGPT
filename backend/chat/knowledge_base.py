"""
knowledge_base.py
─────────────────
Static agricultural knowledge chunks grounded in:
  - ICAR (Indian Council of Agricultural Research) manuals
  - Ministry of Agriculture crop handbooks
  - ANGRAU / PJTSAU guidelines (Telangana & AP specific)
  - Soil Health Card scheme guidelines

All content is stored in English; RAG retrieval happens in English,
then the final answer is translated into the user's detected language.
"""

KNOWLEDGE_CHUNKS: list[dict] = [

    # ── PADDY / RICE ──────────────────────────────────────────────────────────
    {
        "id": "rice_001",
        "agent": "general",
        "topic": "Paddy cultivation basics",
        "content": (
            "Rice (paddy) is the primary Kharif crop of Telangana and Andhra Pradesh. "
            "Kharif sowing: June–July. Rabi sowing: November–December. "
            "Recommended varieties for Telangana: BPT-5204 (Samba Mahsuri), MTU-1010, NLR-34449, RNR-15048 (Telangana Sona). "
            "Seed rate: 25–30 kg/acre (transplanted), 40–50 kg/acre (direct seeded). "
            "Nursery area: 1/10th of main field area. Spacing: 20×15 cm. "
            "Optimal soil pH: 5.5–7.0. Water requirement: 1,200–1,400 mm per season."
        ),
        "source": "ICAR Rice Cultivation Manual 2023; PJTSAU Crop Production Guide",
    },
    {
        "id": "rice_002",
        "agent": "general",
        "topic": "Paddy fertilizer schedule",
        "content": (
            "Paddy fertilizer recommendation (per acre): "
            "Nitrogen (N): 50 kg, Phosphorus (P2O5): 25 kg, Potassium (K2O): 25 kg. "
            "Apply full P and K as basal dose. Split nitrogen: 50% basal, 25% at active tillering (21–25 DAT), 25% at panicle initiation. "
            "Zinc deficiency is common in Telangana soils — apply ZnSO4 25 kg/acre once every 3 seasons. "
            "Use Soil Health Card recommendations for site-specific doses."
        ),
        "source": "ICAR Fertilizer Recommendations for Paddy 2022",
    },
    {
        "id": "rice_003",
        "agent": "disease",
        "topic": "Paddy blast disease",
        "content": (
            "Rice Blast (Magnaporthe oryzae): Most destructive fungal disease of paddy. "
            "Symptoms: Diamond-shaped grey lesions with brown borders on leaves; neck rot causes 'dead head' or white ear. "
            "Favoured by: cool nights (< 20°C), high humidity, heavy nitrogen application. "
            "Control: Spray Tricyclazole 75 WP @ 300 g/acre or Isoprothiolane 40 EC @ 400 ml/acre in 200 litres water. "
            "Repeat after 10–14 days. Use resistant varieties: MTU-1010, NLR-34449. "
            "Do not apply excess nitrogen — it increases susceptibility."
        ),
        "source": "ICAR Crop Disease Management Handbook 2023",
    },
    {
        "id": "rice_004",
        "agent": "disease",
        "topic": "Brown plant hopper (BPH) in paddy",
        "content": (
            "Brown Plant Hopper (Nilaparvata lugens): Major sucking pest of paddy causing 'hopper burn'. "
            "Symptoms: Circular yellowing and drying patches (burnt appearance) in the field. "
            "Monitoring: Use light traps; ETL is 10 hoppers per hill at vegetative stage. "
            "Control: Drain water from field. Spray Buprofezin 25 SC @ 400 ml/acre or "
            "Thiamethoxam 25 WG @ 40 g/acre. Avoid Pyrethroid sprays — they cause BPH resurgence. "
            "Use resistant varieties: Swarna, IR-36, MTU-7029."
        ),
        "source": "ICAR Integrated Pest Management for Rice 2023",
    },

    # ── COTTON ────────────────────────────────────────────────────────────────
    {
        "id": "cotton_001",
        "agent": "general",
        "topic": "Cotton cultivation",
        "content": (
            "Cotton is a major Kharif cash crop in Telangana. Sowing: June–July after first monsoon rain. "
            "Recommended varieties: Bt cotton hybrids (MRC-7017, RCH-2, Bunny BG-II). "
            "Seed rate: 800 g–1 kg/acre (hybrid). Spacing: 90×60 cm (rainfed), 90×45 cm (irrigated). "
            "Soil: Well-drained black cotton (regur) soil, pH 6.0–8.0. "
            "Do not grow cotton on same field more than 2 consecutive years to avoid soil-borne diseases."
        ),
        "source": "ICAR Cotton Cultivation Guide 2023",
    },
    {
        "id": "cotton_002",
        "agent": "disease",
        "topic": "Cotton bollworm pest management",
        "content": (
            "American Bollworm (Helicoverpa armigera) is the most damaging cotton pest. "
            "Symptoms: Circular holes in squares, flowers, and bolls; larva inside boll feeding on seeds. "
            "Economic Threshold Level (ETL): 2 larvae per meter row or 10% damaged squares. "
            "Control: Install pheromone traps @ 5/acre. Spray Profenophos 50 EC @ 2 ml/litre "
            "or Emamectin Benzoate 5 SG @ 4 g/10 litres. Neem Seed Kernel Extract (NSKE) 5% for organic option. "
            "Bt cotton inherently resists bollworm — avoid spraying pyrethroids in Bt cotton."
        ),
        "source": "ICAR Cotton Protection Handbook 2022",
    },
    {
        "id": "cotton_003",
        "agent": "disease",
        "topic": "Cotton pink bollworm",
        "content": (
            "Pink Bollworm (Pectinophora gossypiella) damages cotton bolls internally. "
            "Symptoms: 'Rosette' flowers (petals stuck together), internal feeding in seeds, 'double seed' appearance. "
            "Monitoring: Use gossyplure pheromone traps — 5 traps/acre, replace lure every 3 weeks. "
            "Action threshold: 8–10 moths/trap/night. "
            "Control: Spray Chlorpyriphos 20 EC @ 2 ml/litre or Thiodicarb 75 WP @ 2 g/litre at boll formation. "
            "Destroy crop residue after harvest to break the pest cycle."
        ),
        "source": "ICAR Cotton Pest Management 2022",
    },

    # ── SOIL MANAGEMENT ───────────────────────────────────────────────────────
    {
        "id": "soil_001",
        "agent": "general",
        "topic": "Soil pH and correction",
        "content": (
            "Optimal soil pH for most crops: 6.0–7.5. "
            "Acidic soils (pH < 6): Apply agricultural lime (CaCO3) @ 400–800 kg/acre depending on severity. "
            "Apply lime 2–4 weeks before sowing and incorporate well. "
            "Alkaline soils (pH > 8): Apply gypsum (CaSO4) @ 400–500 kg/acre or press mud. "
            "Saline-alkaline soils: Leach salts with irrigation, apply gypsum + farmyard manure. "
            "Test soil pH every 3 years using Soil Health Card scheme (free from Krishi Vigyan Kendra)."
        ),
        "source": "ICAR Soil Health Management Guide 2023",
    },
    {
        "id": "soil_002",
        "agent": "general",
        "topic": "Organic matter and FYM application",
        "content": (
            "Farmyard Manure (FYM): Apply 4–5 tonnes/acre as basal dose before sowing. "
            "Vermicompost: 1–2 tonnes/acre is equivalent to 2× FYM in nutrient value. "
            "Green manuring: Grow Dhaincha (Sesbania) or Sunhemp and incorporate at flowering — adds 40–60 kg N/acre. "
            "Crop residue incorporation: Chop stubble and incorporate to improve soil organic carbon. "
            "Benefits: Improves water retention, aeration, microbial activity, and reduces fertilizer need by 25%."
        ),
        "source": "ICAR Organic Farming Manual 2023",
    },
    {
        "id": "soil_003",
        "agent": "general",
        "topic": "Micronutrient deficiency in soils",
        "content": (
            "Common micronutrient deficiencies in Telangana/AP soils: "
            "Zinc (Zn): Most common — yellowing with green veins in young leaves. Apply ZnSO4 25 kg/acre or foliar spray 0.5% ZnSO4. "
            "Boron (B): Causes hollow stem in cauliflower, poor fruit set in cotton. Apply Borax 2 kg/acre. "
            "Iron (Fe): Yellowing of young leaves in alkaline soils. Foliar spray FeSO4 0.5% + citric acid. "
            "Sulphur (S): Important for oilseeds — apply SSP (which contains sulphur) or gypsum."
        ),
        "source": "ICAR Micronutrient Management Guide 2022",
    },

    # ── IRRIGATION ────────────────────────────────────────────────────────────
    {
        "id": "irrigation_001",
        "agent": "general",
        "topic": "Drip and sprinkler irrigation",
        "content": (
            "Drip irrigation saves 40–60% water compared to flood irrigation and increases yield by 20–30%. "
            "Suitable for: Cotton, chilli, tomato, mango, grapes, banana. "
            "Government subsidy: PM-KUSUM and PMKSY schemes provide 55–90% subsidy on drip installation. "
            "Contact District Agriculture Office or Krishi Vigyan Kendra for application. "
            "Sprinkler irrigation: Best for groundnut, maize, sunflower. Saves 30–40% water. "
            "Critical irrigation stages: Flowering and grain/boll filling are most sensitive to water stress."
        ),
        "source": "PMKSY Drip Irrigation Guidelines 2023; ICAR Water Management",
    },

    # ── MARKET / PRICES ───────────────────────────────────────────────────────
    {
        "id": "market_001",
        "agent": "market",
        "topic": "Minimum Support Price (MSP) and selling crops",
        "content": (
            "Minimum Support Price (MSP) is declared by Government of India for 23 crops every year. "
            "Kharif 2024-25 MSP examples: Paddy (common grade) ₹2,300/quintal, Cotton (medium staple) ₹7,121/quintal, "
            "Maize ₹2,225/quintal, Groundnut ₹6,783/quintal, Soybean ₹4,892/quintal. "
            "Selling channels: Government procurement through FCI, MARKFED, and RBK (Rythu Bharosa Kendras) in Telangana. "
            "eNAM (National Agriculture Market): Online platform for transparent market access — register at enam.gov.in. "
            "Rythu Bazars in Telangana: Sell directly to consumers without middlemen."
        ),
        "source": "CACP MSP Notification 2024-25; Telangana Agriculture Department",
    },
    {
        "id": "market_002",
        "agent": "market",
        "topic": "PM-KISAN and farmer schemes",
        "content": (
            "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi): ₹6,000/year in 3 instalments directly to farmer bank account. "
            "Eligibility: All small and marginal farmers with cultivable land. Apply at pmkisan.gov.in or CSC centre. "
            "Telangana Rythu Bandhu: ₹10,000/acre/year investment support (Rabi + Kharif combined). "
            "Rythu Bima: Free crop insurance for farmers in Telangana — ₹5 lakh coverage. "
            "Fasal Bima Yojana (PMFBY): Subsidised crop insurance — premium 2% for Kharif, 1.5% for Rabi food crops."
        ),
        "source": "Ministry of Agriculture PM-KISAN Portal; Telangana Agriculture Dept 2024",
    },

    # ── PEST/DISEASE GENERAL ──────────────────────────────────────────────────
    {
        "id": "disease_001",
        "agent": "disease",
        "topic": "Integrated Pest Management (IPM) principles",
        "content": (
            "IPM is a sustainable approach combining cultural, biological, and chemical controls. "
            "Cultural control: Crop rotation, resistant varieties, proper spacing, avoid water logging. "
            "Biological control: Release Trichogramma @ 50,000/acre for lepidopteran pests. "
            "Chrysoperla (Green lacewing) for sucking pests. NPV (Nuclear Polyhedrosis Virus) for bollworm. "
            "Chemical control: Use only when ETL is crossed; prefer selective insecticides. "
            "Avoid: Monocrotophos, Endosulfan (banned). Follow safety intervals before harvest."
        ),
        "source": "ICAR IPM Guidelines 2023; Central Insecticides Board",
    },
    {
        "id": "disease_002",
        "agent": "disease",
        "topic": "Yellow mosaic virus in soybean and moong",
        "content": (
            "Yellow Mosaic Virus (YMV) is spread by whitefly (Bemisia tabaci) in soybean, moong, and urad. "
            "Symptoms: Bright yellow-green mosaic patches on leaves, stunted growth, reduced pod set. "
            "Prevention: Use certified virus-free seeds. Plant resistant varieties (JS-335, MAUS-71 for soybean). "
            "Control whitefly vector: Yellow sticky traps @ 10/acre. Spray Imidacloprid 17.8 SL @ 0.5 ml/litre "
            "or Thiamethoxam 25 WG @ 0.3 g/litre at first sign. Rogue out infected plants immediately."
        ),
        "source": "ICAR Oilseeds Disease Management 2023",
    },

    # ── WEATHER / ADVISORY ────────────────────────────────────────────────────
    {
        "id": "weather_001",
        "agent": "general",
        "topic": "Monsoon advisory for farmers",
        "content": (
            "Kharif season starts with southwest monsoon onset (typically June 1–10 in Kerala, June 15–20 in Telangana). "
            "Sowing guideline: Sow after receiving 2–3 rainfalls totalling 50–75 mm to ensure soil moisture. "
            "Pre-sowing activities: Complete land preparation, procure seeds and fertilizers before June. "
            "Maha Agriculture: Check IMD (imd.gov.in) or Meghdoot App for 5-day weather forecast. "
            "Avoid sowing during forecast heavy rain > 50 mm — seeds may wash away. "
            "Agromet Advisory: Telangana State Development Planning Society issues bi-weekly advisories."
        ),
        "source": "IMD Agro-Met Services; TSDPS Telangana 2024",
    },

    # ── CHILLI / HORTICULTURE ─────────────────────────────────────────────────
    {
        "id": "hort_001",
        "agent": "general",
        "topic": "Chilli cultivation (Guntur chilli)",
        "content": (
            "Chilli (Capsicum annuum) — Guntur district is world's largest chilli market. "
            "Popular varieties: LCA-334, LCA-235, Teja (S-17), G-5 (Kaddi). "
            "Nursery: Sow seeds in raised nursery beds, transplant at 4–5 leaf stage (30–35 days). "
            "Spacing: 60×45 cm. Fertilizer (per acre): N:P:K = 30:30:30 kg + Boron 500 g. "
            "Critical pests: Thrips (spray Spinosad 45 SC @ 3 ml/10 litres), Mite (spray Propargite 57 EC @ 2 ml/litre). "
            "Disease: Anthracnose (die-back) — spray Carbendazim 50 WP @ 1 g/litre at fruiting stage."
        ),
        "source": "ICAR Chilli Production Technology 2023; ANGRAU Crop Guide",
    },

    # ── GROUNDNUT ─────────────────────────────────────────────────────────────
    {
        "id": "gnut_001",
        "agent": "general",
        "topic": "Groundnut cultivation and Tikka disease",
        "content": (
            "Groundnut is a major Kharif oilseed crop in Andhra Pradesh. "
            "Varieties: K-6, TMV-2, ICGS-44, Kadiri-6, Dh-86. "
            "Seed rate: 60–70 kg/acre (bold seeded), 50–60 kg/acre (small seeded). Spacing: 30×10 cm. "
            "Gypsum application: 200 kg/acre at pegging stage (45–50 DAS) — essential for pod development. "
            "Tikka Disease (Early and Late leaf spot, Cercospora): "
            "Symptoms: Circular brown spots with yellow halo. Spray Mancozeb 75 WP @ 400 g/acre or "
            "Chlorothalonil 75 WP @ 300 g/acre at 45 DAS. Repeat every 10–12 days until harvest."
        ),
        "source": "ICAR Groundnut Production Guide 2023; ANGRAU AP Crop Manual",
    },
]

# ── DYNAMICALLY INJECT DISEASE DETECTOR DATABASE ──────────────────────────────
try:
    from disease_info import DISEASE_INFO
    for key, info in DISEASE_INFO.items():
        if "healthy" in key.lower():
            continue
        
        # Parse key e.g. "Tomato___Early_blight" -> crop: Tomato, disease: Early blight
        parts = key.split("___")
        crop = parts[0].replace("_", " ").strip()
        disease = parts[1].replace("_", " ").strip() if len(parts) > 1 else "Disease"
        
        content = (
            f"Crop: {crop}. Disease: {disease}. "
            f"Severity: {info.get('severity', 'moderate')}. "
            f"Cause: {info.get('cause', 'N/A')} "
            f"Organic Treatment: {info.get('organic', 'N/A')} "
            f"Chemical Treatment: {info.get('chemical', 'N/A')} "
            f"Prevention Tips: {info.get('prevention', 'N/A')}"
        )
        
        KNOWLEDGE_CHUNKS.append({
            "id": f"disease_auto_{key.lower().replace(',', '').replace(' ', '_')}",
            "agent": "disease",
            "topic": f"{crop} {disease}",
            "content": content,
            "source": "AgriGPT Disease Diagnosis Database 2026",
        })
except Exception as e:
    import logging
    logging.getLogger(__name__).warning("Failed to inject DISEASE_INFO into knowledge chunks: %s", e)

