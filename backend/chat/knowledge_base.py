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
        "topic": "Minimum Support Price (MSP) — all crops 2024-25",
        "content": (
            "Minimum Support Price (MSP) declared by Government of India for 2024-25:\n"
            "\n--- KHARIF CROPS ---\n"
            "Paddy (Common): ₹2,300/quintal | Paddy (Grade A): ₹2,320/quintal\n"
            "Jowar (Hybrid): ₹3,371/quintal | Jowar (Maldandi): ₹3,421/quintal\n"
            "Bajra: ₹2,625/quintal\n"
            "Maize: ₹2,225/quintal\n"
            "Ragi: ₹4,290/quintal\n"
            "Tur (Arhar/Pigeon Pea): ₹7,550/quintal\n"
            "Moong (Green Gram): ₹8,682/quintal\n"
            "Urad (Black Gram): ₹7,400/quintal\n"
            "Groundnut: ₹6,783/quintal\n"
            "Sunflower Seed: ₹7,280/quintal\n"
            "Soybean (Yellow): ₹4,892/quintal\n"
            "Sesamum: ₹9,267/quintal\n"
            "Nigerseed: ₹8,717/quintal\n"
            "Cotton (Medium Staple): ₹7,121/quintal\n"
            "Cotton (Long Staple): ₹7,521/quintal\n"
            "\n--- RABI CROPS ---\n"
            "Wheat: ₹2,275/quintal\n"
            "Barley: ₹1,735/quintal\n"
            "Gram (Chana): ₹5,440/quintal\n"
            "Masur (Lentil): ₹6,425/quintal\n"
            "Rapeseed/Mustard: ₹5,950/quintal\n"
            "Safflower: ₹5,800/quintal\n"
            "\nSelling channels: FCI, MARKFED, RBK (Rythu Bharosa Kendras) in Telangana. "
            "eNAM (National Agriculture Market): Online transparent market — register at enam.gov.in. "
            "Rythu Bazars in Telangana: Sell directly to consumers without middlemen."
        ),
        "source": "CACP MSP Notification 2024-25; Ministry of Agriculture; Telangana Agriculture Department",
    },
    {
        "id": "market_002",
        "agent": "market",
        "topic": "PM-KISAN and farmer welfare schemes",
        "content": (
            "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi): ₹6,000/year in 3 instalments of ₹2,000 directly to farmer bank account. "
            "Eligibility: All small and marginal farmers with cultivable land. Apply at pmkisan.gov.in or nearest CSC centre. "
            "\nTelangana Rythu Bandhu: ₹10,000/acre/year investment support (Rabi + Kharif combined, ₹5,000 per season). "
            "Rythu Bima (Telangana): Free life insurance for farmers — ₹5 lakh coverage, premium paid by state government. "
            "\nFasal Bima Yojana (PMFBY): Subsidised crop insurance. "
            "Premium: 2% of sum insured for Kharif crops, 1.5% for Rabi food/oilseed crops, 5% for horticultural crops. "
            "Coverage: Yield losses due to drought, flood, hailstorm, pest attack, post-harvest losses. "
            "\nKisan Credit Card (KCC): Short-term credit at 4% interest (after 2% interest subvention + 3% prompt repayment incentive). "
            "Credit limit: Based on landholding — typically ₹50,000–₹3,00,000."
        ),
        "source": "Ministry of Agriculture PM-KISAN Portal; Telangana Agriculture Dept 2024; PMFBY Guidelines",
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
    {
        "id": "rice_005",
        "agent": "market",
        "topic": "Paddy MSP price 2024-25",
        "content": (
            "Paddy Minimum Support Price (MSP) for Kharif 2024-25: "
            "Common grade: ₹2,300 per quintal. Grade A: ₹2,320 per quintal. "
            "Increase from 2023-24: ₹117/quintal (common grade). "
            "Procurement: Through Food Corporation of India (FCI) and state agencies. "
            "In Telangana: procured via RBK (Rythu Bharosa Kendras). "
            "Farmer must bring proof of land record (pattadar passbook) and Aadhaar. "
            "Direct payment: transferred to bank account within 48 hours of procurement."
        ),
        "source": "CACP MSP Notification Kharif 2024-25; FCI Procurement Guidelines",
    },
    {
        "id": "cotton_004",
        "agent": "market",
        "topic": "Cotton MSP price 2024-25",
        "content": (
            "Cotton Minimum Support Price (MSP) Kharif 2024-25: "
            "Medium Staple: ₹7,121 per quintal. Long Staple: ₹7,521 per quintal. "
            "Increase from 2023-24: ₹501/quintal (medium staple). "
            "Procurement agency: Cotton Corporation of India (CCI). "
            "Sale point: Designated cotton mandis and CCI procurement centres. "
            "Average market price in Warangal/Nalgonda mandis (2024 season): ₹6,800–₹7,400/quintal. "
            "Tip: Harvest when 60–70% bolls open for best fibre quality and higher price."
        ),
        "source": "CACP MSP Notification Kharif 2024-25; CCI Cotton Procurement",
    },
    {
        "id": "market_003",
        "agent": "market",
        "topic": "Vegetable and horticulture crop market prices",
        "content": (
            "Indicative wholesale mandi prices in Telangana/AP (2024 season, subject to variation):\n"
            "Tomato: ₹500–₹2,500/quintal (highly variable — peaks Nov–Jan)\n"
            "Onion: ₹800–₹2,000/quintal\n"
            "Chilli (dry, Teja variety): ₹8,000–₹18,000/quintal (Guntur mandi)\n"
            "Chilli (fresh green): ₹1,500–₹4,000/quintal\n"
            "Potato: ₹600–₹1,200/quintal\n"
            "Brinjal: ₹400–₹1,000/quintal\n"
            "Bitter Gourd: ₹800–₹1,600/quintal\n"
            "Cabbage: ₹300–₹700/quintal\n"
            "Cauliflower: ₹500–₹1,200/quintal\n"
            "Banana (local, per dozen): ₹20–₹50\n"
            "Mango (Banginapalli/Alphonso): ₹2,000–₹5,000/quintal\n"
            "Note: Prices fluctuate with season, surplus, and transport. "
            "Check current rates at agmarknet.gov.in or APMC mandi boards."
        ),
        "source": "AgMarkNet Portal 2024; Telangana State Agriculture Marketing Dept",
    },
    {
        "id": "market_004",
        "agent": "market",
        "topic": "Input costs — seeds, fertilizers, pesticides",
        "content": (
            "Indicative input costs for farmers in Telangana/AP (2024):\n"
            "\n--- SEEDS (per acre) ---\n"
            "Bt Cotton hybrid seed (450 g packet): ₹750–₹950/packet (need 2 packets/acre)\n"
            "Paddy certified seed (BPT-5204): ₹35–₹45/kg\n"
            "Groundnut seed: ₹60–₹80/kg\n"
            "Soybean certified seed: ₹50–₹65/kg\n"
            "Chilli hybrid seed: ₹800–₹2,500/10 g packet\n"
            "\n--- FERTILIZERS (per bag/unit) ---\n"
            "Urea (45 kg bag): ₹266.50 (subsidised MRP fixed by Govt)\n"
            "DAP (50 kg bag): ₹1,350 (subsidised MRP)\n"
            "MOP/Muriate of Potash (50 kg bag): ₹1,700 (approx)\n"
            "NPK 19:19:19 (25 kg): ₹850–₹950\n"
            "ZnSO4 (25 kg): ₹700–₹900\n"
            "\n--- PESTICIDES (common) ---\n"
            "Chlorpyriphos 20 EC (1 litre): ₹350–₹450\n"
            "Profenophos 50 EC (500 ml): ₹300–₹400\n"
            "Tricyclazole 75 WP (100 g): ₹200–₹280\n"
            "Imidacloprid 17.8 SL (250 ml): ₹250–₹350\n"
            "\nSubsidy: Fertilizer subsidy is direct to company (not farmer), keeping MRP low. "
            "Seeds: State government provides subsidised certified seeds through TSSDC/APSSDC centres."
        ),
        "source": "Department of Fertilizers Govt of India 2024; Telangana State Seeds Dev Corp 2024",
    },
    {
        "id": "hort_002",
        "agent": "market",
        "topic": "Chilli market prices and export",
        "content": (
            "Chilli market prices at Guntur Mirchi Yard (2024 season):\n"
            "Teja (S-17) dry red chilli: ₹12,000–₹18,000/quintal\n"
            "334 variety dry chilli: ₹8,000–₹12,000/quintal\n"
            "G-5 (Kaddi): ₹6,000–₹9,000/quintal\n"
            "Export: India exports 250,000+ tonnes chilli/year. Major buyers: China, Bangladesh, Sri Lanka, USA. "
            "APEDA (Agricultural and Processed Food Products Export Development Authority) facilitates export certification. "
            "For export quality: moisture < 11%, no banned pesticide residues (test at accredited labs). "
            "Cold storage facility available at Guntur Yard — cost ₹18–₹22/quintal/month."
        ),
        "source": "Guntur Mirchi Yard APMC 2024; APEDA Export Data 2024",
    },
    {
        "id": "gnut_002",
        "agent": "market",
        "topic": "Groundnut market prices 2024-25",
        "content": (
            "Groundnut MSP 2024-25: ₹6,783/quintal (with shell). "
            "Market prices at major AP/Telangana mandis (2024):\n"
            "Groundnut pods (bold): ₹5,500–₹7,200/quintal\n"
            "Groundnut oil (mill gate price): ₹130–₹155/litre\n"
            "De-oiled cake: ₹25,000–₹28,000/tonne (used as animal feed)\n"
            "Oil content: ICGS-44 and Kadiri-6 give 47–50% oil content. "
            "Processing: Nearest oil mills in Nellore, Kurnool, and Guntur districts. "
            "Storage: Store pods at < 9% moisture to avoid Aflatoxin contamination. "
            "Quality tip: Grade A groundnuts (bold, uniform) fetch ₹500–₹800 premium per quintal."
        ),
        "source": "CACP MSP 2024-25; Kurnool APMC 2024; ICAR Post-Harvest Manual",
    },
    {
        "id": "maize_001",
        "agent": "general",
        "topic": "Maize cultivation",
        "content": (
            "Maize (corn) grows in both Kharif (June–Oct) and Rabi (Nov–Feb) seasons in Telangana/AP. "
            "Recommended hybrid varieties: DHM-117, NK-6240, Bio-9681, DKC-9144. "
            "Seed rate: 8–10 kg/acre (hybrid). Spacing: 60×20 cm or 75×20 cm. "
            "Fertilizer (per acre): N 60 kg, P 30 kg, K 30 kg. "
            "Split nitrogen: 1/3 basal, 1/3 at knee-high stage (30 DAS), 1/3 at tasseling. "
            "Fall Armyworm (FAW) — Spodoptera frugiperda: Spray Emamectin Benzoate 5 SG @ 4 g/10 litres "
            "or Chlorantraniliprole 18.5 SC @ 3 ml/10 litres at early infestation. "
            "Water requirement: 450–600 mm; critical stages: knee-high, tasseling, silking, grain fill."
        ),
        "source": "ICAR Maize Production Guide 2023; PJTSAU Maize Handbook",
    },
    {
        "id": "maize_002",
        "agent": "market",
        "topic": "Maize MSP and market prices",
        "content": (
            "Maize MSP 2024-25: ₹2,225/quintal. "
            "Market prices at Nizamabad and Karimnagar mandis (2024 Kharif):\n"
            "Maize (dry, < 14% moisture): ₹1,900–₹2,350/quintal\n"
            "Wet maize (> 18% moisture): ₹1,400–₹1,700/quintal (significant discount)\n"
            "Tip: Dry maize to < 14% moisture before selling — adds ₹300–₹500/quintal premium. "
            "Buyers: Poultry feed mills (largest buyer), starch industry, distilleries. "
            "Major maize markets in Telangana: Nizamabad, Adilabad, Karimnagar APMC yards."
        ),
        "source": "CACP MSP 2024-25; Nizamabad APMC 2024",
    },
    {
        "id": "soy_001",
        "agent": "general",
        "topic": "Soybean cultivation",
        "content": (
            "Soybean is a major Kharif oilseed-cum-pulse crop. "
            "Recommended varieties: JS-335, JS-9305, MACS-450, NRC-37. "
            "Seed rate: 30–35 kg/acre. Spacing: 45×5 cm. Sowing depth: 3–4 cm. "
            "Seed treatment: Rhizobium culture + PSB inoculant before sowing — saves 25 kg urea/acre. "
            "Fertilizer: No nitrogen needed if Rhizobium inoculated; apply P 30 kg + K 20 kg/acre. "
            "Pod borer: Spray Indoxacarb 14.5 SC @ 10 ml/10 litres. "
            "Harvest when 95% pods turn brown (95–100 DAS). Threshing delay causes shattering."
        ),
        "source": "ICAR Soybean Production Manual 2023",
    },
    {
        "id": "soy_002",
        "agent": "market",
        "topic": "Soybean MSP and market prices",
        "content": (
            "Soybean MSP 2024-25: ₹4,892/quintal (yellow variety). "
            "Market prices at Latur (Maharashtra) and Nanded mandis (2024 Kharif): ₹4,400–₹5,100/quintal. "
            "Soybean oil price (retail): ₹105–₹120/litre. "
            "Soybean meal/cake: ₹35,000–₹42,000/tonne (high-value protein feed for poultry). "
            "Processing: De-hulling, solvent extraction for oil; residual is protein-rich meal. "
            "Export: Soybean meal is a major export commodity — APEDA certified labs needed for phytosanitary certificate."
        ),
        "source": "CACP MSP 2024-25; Latur APMC 2024; SOPA (Soybean Processors Association)",
    },
    {
        "id": "scheme_001",
        "agent": "market",
        "topic": "Soil Health Card and free soil testing",
        "content": (
            "Soil Health Card Scheme (Government of India): Free soil testing for all farmers every 2 years. "
            "Test includes: N, P, K, pH, EC, organic carbon, and 8 micronutrients. "
            "How to apply: Visit nearest Krishi Vigyan Kendra, or soil testing lab at Agriculture Department. "
            "Result: Customised fertilizer recommendation card for your specific plot. "
            "Savings: Following Soil Health Card reduces fertilizer cost by ₹1,500–₹2,500/acre by avoiding excess use. "
            "Online: Soil health data at soilhealth.dac.gov.in"
        ),
        "source": "Department of Agriculture, Cooperation and Farmers Welfare 2024",
    },
    {
        "id": "scheme_002",
        "agent": "market",
        "topic": "eNAM and digital marketing for farmers",
        "content": (
            "eNAM (National Agriculture Market): Online platform connecting farmers to buyers across India. "
            "Registration: Free — at enam.gov.in or nearest APMC yard. Required: Aadhaar, bank account, land record. "
            "How it works: Upload produce quality details, assay result, and buyers bid online. "
            "Benefits: Transparent price discovery, direct payment, and wider buyer base."
        ),
        "source": "Ministry of Agriculture eNAM Guidelines 2024",
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

