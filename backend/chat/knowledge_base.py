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

Content rules applied in this version:
  ✅  Yield numbers corrected to ICAR district-level averages (not lab maxima)
  ✅  Chunks structured as short bullets — farmer-oriented, not textbook
  ✅  Every crop chunk includes: season, nursery timing, yield expectation,
      weed control — the four fields most commonly missing before
  ✅  No duplicate facts across chunks for the same crop
"""

KNOWLEDGE_CHUNKS: list[dict] = [

    # ── PADDY / RICE ──────────────────────────────────────────────────────────

    {
        "id": "rice_001",
        "agent": "general",
        "topic": "Paddy cultivation basics — season, sowing, spacing, yield",
        "content": (
            "PADDY CULTIVATION — TELANGANA / AP\n"
            "\n"
            "Season & Sowing:\n"
            "- Kharif: Nursery in June 1–15; transplant by July 15 at the latest.\n"
            "- Rabi: Nursery in October–November; transplant by December 15.\n"
            "- Sow after 2–3 rains totalling 50 mm to ensure good soil moisture.\n"
            "\n"
            "Nursery:\n"
            "- Prepare raised beds of 1 m width. Sow 25–30 kg seed/acre of main field.\n"
            "- Nursery area = 1/10th of main field. Seedlings ready to transplant at 20–25 days.\n"
            "- Treat seed with Carbendazim 2 g/kg before sowing to prevent fungal seedling disease.\n"
            "\n"
            "Varieties (Telangana):\n"
            "- BPT-5204 (Samba Mahsuri) — fine grain, good market price, 135–140 days.\n"
            "- MTU-1010 — blast resistant, 120 days.\n"
            "- RNR-15048 (Telangana Sona) — short duration, 115 days.\n"
            "- NLR-34449 — drought tolerant, Rabi preferred.\n"
            "\n"
            "Spacing & Transplanting:\n"
            "- Spacing: 20×15 cm. Plant 2–3 seedlings per hill.\n"
            "- Avoid planting deeper than 3 cm — deep planting reduces tillering.\n"
            "\n"
            "Weed Control:\n"
            "- Apply Butachlor 50 EC @ 1.5 litres/acre + 20 kg sand as carrier at 3–5 DAT\n"
            "  (days after transplanting) for pre-emergence weed control.\n"
            "- OR Pyrazosulfuron-ethyl 10 WP @ 100 g/acre at 5–7 DAT.\n"
            "- Manual weeding at 30 DAT if needed.\n"
            "\n"
            "Expected Yield:\n"
            "- Average realistic: 25–35 quintals/acre (rainfed or average management).\n"
            "- Good scientific farming: 35–45 quintals/acre (transplanted, irrigated, timely inputs).\n"
            "- Note: 40–50 quintals/acre is possible only under exceptional conditions — not typical.\n"
            "\n"
            "Water Requirement: 1,200–1,400 mm/season. Maintain 5 cm standing water at tillering."
        ),
        "source": "ICAR Rice Cultivation Manual 2023; PJTSAU Crop Production Guide; ANGRAU 2023",
    },

    {
        "id": "rice_002",
        "agent": "general",
        "topic": "Paddy fertilizer schedule and nutrient management",
        "content": (
            "PADDY FERTILIZER — PER ACRE\n"
            "\n"
            "Recommended Doses:\n"
            "- Nitrogen (N): 50 kg | Phosphorus (P₂O₅): 25 kg | Potassium (K₂O): 25 kg.\n"
            "- Apply full P and full K as basal (before transplanting).\n"
            "\n"
            "Nitrogen Split Schedule:\n"
            "- 50% basal (mixed into soil before transplanting).\n"
            "- 25% at active tillering — 21–25 DAT.\n"
            "- 25% at panicle initiation — 45–50 DAT.\n"
            "\n"
            "Micronutrients:\n"
            "- Zinc deficiency is very common in Telangana soils. Symptoms: brown rusty spots on young leaves.\n"
            "- Apply ZnSO₄ @ 25 kg/acre as basal once every 3 seasons.\n"
            "- Use Soil Health Card recommendation for your specific plot.\n"
            "\n"
            "Organic Option:\n"
            "- Apply FYM 4–5 tonnes/acre two weeks before transplanting.\n"
            "- This reduces chemical fertilizer need by 25% and improves soil structure."
        ),
        "source": "ICAR Fertilizer Recommendations for Paddy 2022; PJTSAU Nutrient Management Guide",
    },

    {
        "id": "rice_003",
        "agent": "disease",
        "topic": "Paddy blast disease — symptoms and control",
        "content": (
            "RICE BLAST (Magnaporthe oryzae)\n"
            "\n"
            "Symptoms:\n"
            "- Leaf blast: Diamond-shaped grey lesions with brown borders on leaves.\n"
            "- Neck blast: Rotting at the base of the panicle — causes 'dead head' or white ear.\n"
            "- Favoured by: cool nights (< 20°C), high humidity, excess nitrogen.\n"
            "\n"
            "Chemical Control:\n"
            "- Spray Tricyclazole 75 WP @ 300 g/acre in 200 litres water.\n"
            "- OR Isoprothiolane 40 EC @ 400 ml/acre.\n"
            "- Repeat after 10–14 days if symptoms persist.\n"
            "\n"
            "Prevention:\n"
            "- Use resistant varieties: MTU-1010, NLR-34449.\n"
            "- Do NOT over-apply nitrogen — excess N makes the crop highly susceptible.\n"
            "- Avoid spraying in the afternoon — spray early morning for best uptake."
        ),
        "source": "ICAR Crop Disease Management Handbook 2023",
    },

    {
        "id": "rice_004",
        "agent": "disease",
        "topic": "Brown plant hopper (BPH) in paddy",
        "content": (
            "BROWN PLANT HOPPER (Nilaparvata lugens)\n"
            "\n"
            "Symptoms:\n"
            "- Circular yellowing and drying patches — called 'hopper burn'.\n"
            "- Insects cluster at the base of the plant near water level.\n"
            "\n"
            "Monitoring:\n"
            "- Use light traps. ETL = 10 hoppers per hill at vegetative stage.\n"
            "\n"
            "Control:\n"
            "- Drain water from field first (exposes hoppers).\n"
            "- Spray Buprofezin 25 SC @ 400 ml/acre OR Thiamethoxam 25 WG @ 40 g/acre.\n"
            "- Target base of the plant, not the canopy.\n"
            "\n"
            "Important:\n"
            "- NEVER use Pyrethroid insecticides — they kill natural enemies and cause BPH resurgence.\n"
            "- Use resistant varieties: Swarna, IR-36, MTU-7029."
        ),
        "source": "ICAR Integrated Pest Management for Rice 2023",
    },

    {
        "id": "rice_005",
        "agent": "market",
        "topic": "Paddy MSP and selling — 2024-25",
        "content": (
            "PADDY MSP — KHARIF 2024-25\n"
            "\n"
            "- Common grade: ₹2,300/quintal.\n"
            "- Grade A: ₹2,320/quintal.\n"
            "- Increase from 2023-24: ₹117/quintal.\n"
            "\n"
            "Where to Sell:\n"
            "- Telangana: Sell through RBK (Rythu Bharosa Kendra) — guaranteed MSP.\n"
            "- FCI procurement centres for large quantities.\n"
            "- eNAM portal (enam.gov.in) for online price discovery.\n"
            "\n"
            "Documents Needed:\n"
            "- Pattadar passbook, Aadhaar card.\n"
            "- Payment directly to bank account within 48 hours of sale."
        ),
        "source": "CACP MSP Notification Kharif 2024-25; FCI Procurement Guidelines",
    },

    # ── COTTON ────────────────────────────────────────────────────────────────

    {
        "id": "cotton_001",
        "agent": "general",
        "topic": "Cotton cultivation — season, sowing, yield",
        "content": (
            "COTTON CULTIVATION — TELANGANA\n"
            "\n"
            "Season & Sowing:\n"
            "- Kharif crop. Sow after first monsoon rains — June 15 to July 10.\n"
            "- Sow into moist soil; do NOT sow in dry soil hoping for rain.\n"
            "\n"
            "Varieties:\n"
            "- Bt cotton hybrids: MRC-7017, RCH-2, Bunny BG-II.\n"
            "- Seed rate: 800 g–1 kg/acre (2 packets of 450 g each).\n"
            "\n"
            "Spacing:\n"
            "- Rainfed: 90×60 cm. Irrigated: 90×45 cm.\n"
            "\n"
            "Weed Control:\n"
            "- Apply Pendimethalin 38.7 CS @ 700 ml/acre as pre-emergence (within 3 days of sowing).\n"
            "- Manual weeding at 30 and 60 DAS.\n"
            "- Keep field weed-free in first 45 days — critical for yield.\n"
            "\n"
            "Expected Yield:\n"
            "- Average: 8–12 quintals/acre (seed cotton).\n"
            "- Good farming: 12–18 quintals/acre with timely irrigation and pest control.\n"
            "\n"
            "Soil: Well-drained black cotton (regur) soil, pH 6.0–8.0."
        ),
        "source": "ICAR Cotton Cultivation Guide 2023; PJTSAU Cotton Handbook",
    },

    {
        "id": "cotton_002",
        "agent": "disease",
        "topic": "Cotton bollworm pest management",
        "content": (
            "AMERICAN BOLLWORM (Helicoverpa armigera)\n"
            "\n"
            "Symptoms:\n"
            "- Circular holes in squares (flower buds), flowers, and bolls.\n"
            "- Larva found inside boll feeding on seeds.\n"
            "\n"
            "ETL: 2 larvae per metre row OR 10% damaged squares.\n"
            "\n"
            "Control:\n"
            "- Install pheromone traps @ 5/acre to monitor.\n"
            "- Spray Profenophos 50 EC @ 2 ml/litre OR Emamectin Benzoate 5 SG @ 4 g/10 litres.\n"
            "- Organic option: NSKE 5% (Neem Seed Kernel Extract).\n"
            "\n"
            "Important:\n"
            "- Bt cotton resists bollworm — avoid pyrethroid sprays in Bt cotton fields."
        ),
        "source": "ICAR Cotton Protection Handbook 2022",
    },

    {
        "id": "cotton_003",
        "agent": "disease",
        "topic": "Cotton pink bollworm",
        "content": (
            "PINK BOLLWORM (Pectinophora gossypiella)\n"
            "\n"
            "Symptoms:\n"
            "- 'Rosette' flowers — petals stuck together.\n"
            "- Internal feeding inside seeds; 'double seed' appearance on splitting boll.\n"
            "\n"
            "Monitoring:\n"
            "- Gossyplure pheromone traps @ 5/acre. Replace lure every 3 weeks.\n"
            "- Action: 8–10 moths/trap/night.\n"
            "\n"
            "Control:\n"
            "- Spray Chlorpyriphos 20 EC @ 2 ml/litre at boll formation.\n"
            "- OR Thiodicarb 75 WP @ 2 g/litre.\n"
            "- Destroy crop residue after harvest — breaks pest cycle."
        ),
        "source": "ICAR Cotton Pest Management 2022",
    },

    {
        "id": "cotton_004",
        "agent": "market",
        "topic": "Cotton MSP and market prices 2024-25",
        "content": (
            "COTTON MSP — KHARIF 2024-25\n"
            "\n"
            "- Medium Staple: ₹7,121/quintal.\n"
            "- Long Staple: ₹7,521/quintal.\n"
            "- Increase from 2023-24: ₹501/quintal (medium staple).\n"
            "\n"
            "Market Prices (2024):\n"
            "- Warangal/Nalgonda mandis: ₹6,800–₹7,400/quintal.\n"
            "- Procurement via Cotton Corporation of India (CCI).\n"
            "\n"
            "Tip: Harvest when 60–70% bolls open for best fibre quality."
        ),
        "source": "CACP MSP Notification Kharif 2024-25; CCI Cotton Procurement",
    },

    # ── SOIL MANAGEMENT ───────────────────────────────────────────────────────

    {
        "id": "soil_001",
        "agent": "general",
        "topic": "Soil pH correction — acidic and alkaline soils",
        "content": (
            "SOIL pH MANAGEMENT\n"
            "\n"
            "Optimal pH for most crops: 6.0–7.5.\n"
            "\n"
            "Acidic soils (pH < 6):\n"
            "- Apply agricultural lime (CaCO₃) @ 400–800 kg/acre.\n"
            "- Incorporate well; apply 2–4 weeks before sowing.\n"
            "\n"
            "Alkaline soils (pH > 8):\n"
            "- Apply gypsum (CaSO₄) @ 400–500 kg/acre OR press mud.\n"
            "\n"
            "Saline-alkaline:\n"
            "- Leach salts with irrigation, then apply gypsum + FYM.\n"
            "\n"
            "Free Soil Testing:\n"
            "- Soil Health Card scheme — visit nearest KVK or Agriculture Dept lab.\n"
            "- Testing includes N, P, K, pH, EC, organic carbon, 8 micronutrients.\n"
            "- Online: soilhealth.dac.gov.in"
        ),
        "source": "ICAR Soil Health Management Guide 2023",
    },

    {
        "id": "soil_002",
        "agent": "general",
        "topic": "Organic matter, FYM, green manure",
        "content": (
            "ORGANIC MATTER MANAGEMENT\n"
            "\n"
            "FYM (Farmyard Manure):\n"
            "- Apply 4–5 tonnes/acre as basal dose before sowing.\n"
            "\n"
            "Vermicompost:\n"
            "- 1–2 tonnes/acre ≈ 2× the nutrient value of FYM.\n"
            "\n"
            "Green Manuring:\n"
            "- Grow Dhaincha (Sesbania) or Sunhemp; incorporate at flowering.\n"
            "- Adds 40–60 kg N/acre — saves one split dose of urea.\n"
            "\n"
            "Benefits:\n"
            "- Reduces chemical fertilizer need by ~25%.\n"
            "- Improves water retention and microbial activity."
        ),
        "source": "ICAR Organic Farming Manual 2023",
    },

    {
        "id": "soil_003",
        "agent": "general",
        "topic": "Micronutrient deficiency — zinc, boron, iron, sulphur",
        "content": (
            "MICRONUTRIENT DEFICIENCIES — TELANGANA / AP\n"
            "\n"
            "Zinc (most common):\n"
            "- Symptoms: yellowing with green veins in young leaves ('khaira' in rice).\n"
            "- Apply ZnSO₄ @ 25 kg/acre OR foliar spray 0.5% ZnSO₄.\n"
            "\n"
            "Boron:\n"
            "- Causes hollow stem in cauliflower, poor fruit set in cotton.\n"
            "- Apply Borax @ 2 kg/acre.\n"
            "\n"
            "Iron:\n"
            "- Yellowing of young leaves in alkaline soils.\n"
            "- Foliar spray FeSO₄ 0.5% + citric acid.\n"
            "\n"
            "Sulphur:\n"
            "- Critical for oilseeds (groundnut, mustard).\n"
            "- Apply SSP (contains sulphur) or gypsum @ 200 kg/acre."
        ),
        "source": "ICAR Micronutrient Management Guide 2022",
    },

    # ── IRRIGATION ────────────────────────────────────────────────────────────

    {
        "id": "irrigation_001",
        "agent": "general",
        "topic": "Drip, sprinkler irrigation and govt subsidy",
        "content": (
            "IRRIGATION SYSTEMS\n"
            "\n"
            "Drip Irrigation:\n"
            "- Saves 40–60% water vs flood irrigation; increases yield 20–30%.\n"
            "- Best for: cotton, chilli, tomato, mango, banana.\n"
            "- Subsidy: PMKSY / PM-KUSUM — 55–90% subsidy on installation cost.\n"
            "- Apply at District Agriculture Office or KVK.\n"
            "\n"
            "Sprinkler Irrigation:\n"
            "- Saves 30–40% water. Best for: groundnut, maize, sunflower.\n"
            "\n"
            "Critical Irrigation Stages (don't skip):\n"
            "- Flowering and grain/boll filling — water stress here reduces yield most."
        ),
        "source": "PMKSY Drip Irrigation Guidelines 2023; ICAR Water Management",
    },

    # ── MARKET / PRICES ───────────────────────────────────────────────────────

    {
        "id": "market_001",
        "agent": "market",
        "topic": "MSP 2024-25 all crops — Kharif and Rabi",
        "content": (
            "MINIMUM SUPPORT PRICE (MSP) — 2024-25\n"
            "\n"
            "KHARIF CROPS:\n"
            "- Paddy Common: ₹2,300 | Grade A: ₹2,320\n"
            "- Jowar Hybrid: ₹3,371 | Maldandi: ₹3,421\n"
            "- Bajra: ₹2,625 | Maize: ₹2,225 | Ragi: ₹4,290\n"
            "- Tur (Arhar): ₹7,550 | Moong: ₹8,682 | Urad: ₹7,400\n"
            "- Groundnut: ₹6,783 | Sunflower: ₹7,280 | Soybean: ₹4,892\n"
            "- Sesamum: ₹9,267 | Cotton Medium: ₹7,121 | Long: ₹7,521\n"
            "\n"
            "RABI CROPS:\n"
            "- Wheat: ₹2,275 | Barley: ₹1,735\n"
            "- Gram (Chana): ₹5,440 | Masur (Lentil): ₹6,425\n"
            "- Mustard: ₹5,950 | Safflower: ₹5,800\n"
            "\n"
            "All prices per quintal. These are government floor prices — actual mandi rates may vary.\n"
            "Selling channels: FCI, MARKFED, RBK (Telangana), eNAM (enam.gov.in)."
        ),
        "source": "CACP MSP Notification 2024-25; Ministry of Agriculture",
    },

    {
        "id": "market_002",
        "agent": "market",
        "topic": "PM-KISAN, Rythu Bandhu, crop insurance schemes",
        "content": (
            "FARMER WELFARE SCHEMES\n"
            "\n"
            "PM-KISAN:\n"
            "- ₹6,000/year in 3 instalments of ₹2,000 directly to bank account.\n"
            "- Apply at pmkisan.gov.in or nearest CSC centre.\n"
            "\n"
            "Telangana Rythu Bandhu:\n"
            "- ₹10,000/acre/year (₹5,000 per season — Kharif + Rabi).\n"
            "\n"
            "Rythu Bima (Telangana):\n"
            "- Free life insurance — ₹5 lakh coverage, premium paid by state govt.\n"
            "\n"
            "PMFBY (Crop Insurance):\n"
            "- Premium: 2% for Kharif | 1.5% for Rabi | 5% for horticulture.\n"
            "- Covers: drought, flood, hailstorm, pest attack, post-harvest losses.\n"
            "\n"
            "Kisan Credit Card (KCC):\n"
            "- Credit at 4% interest. Limit: ₹50,000–₹3,00,000 based on landholding."
        ),
        "source": "Ministry of Agriculture PM-KISAN Portal; Telangana Agri Dept 2024; PMFBY Guidelines",
    },

    {
        "id": "market_003",
        "agent": "market",
        "topic": "Vegetable and horticulture wholesale prices 2024",
        "content": (
            "VEGETABLE MANDI PRICES — TELANGANA / AP (2024, indicative)\n"
            "\n"
            "- Tomato: ₹500–₹2,500/qtl (peaks Nov–Jan)\n"
            "- Onion: ₹800–₹2,000/qtl\n"
            "- Chilli dry (Teja): ₹8,000–₹18,000/qtl (Guntur mandi)\n"
            "- Chilli fresh green: ₹1,500–₹4,000/qtl\n"
            "- Potato: ₹600–₹1,200/qtl\n"
            "- Brinjal: ₹400–₹1,000/qtl\n"
            "- Cabbage: ₹300–₹700/qtl | Cauliflower: ₹500–₹1,200/qtl\n"
            "- Mango (Banginapalli): ₹2,000–₹5,000/qtl\n"
            "\n"
            "Note: Prices fluctuate daily. Check agmarknet.gov.in for today's rates."
        ),
        "source": "AgMarkNet Portal 2024; Telangana State Agriculture Marketing Dept",
    },

    {
        "id": "market_004",
        "agent": "market",
        "topic": "Input costs — seeds, fertilizers, pesticides 2024",
        "content": (
            "INPUT COSTS — TELANGANA / AP (2024)\n"
            "\n"
            "Seeds (per acre):\n"
            "- Bt Cotton hybrid (450 g packet): ₹750–₹950 (need 2 packets/acre)\n"
            "- Paddy BPT-5204 certified seed: ₹35–₹45/kg\n"
            "- Groundnut: ₹60–₹80/kg | Soybean: ₹50–₹65/kg\n"
            "\n"
            "Fertilizers (subsidised MRP):\n"
            "- Urea 45 kg bag: ₹266.50 | DAP 50 kg bag: ₹1,350\n"
            "- MOP 50 kg: ₹1,700 | ZnSO₄ 25 kg: ₹700–₹900\n"
            "\n"
            "Common Pesticides:\n"
            "- Chlorpyriphos 20 EC (1 L): ₹350–₹450\n"
            "- Tricyclazole 75 WP (100 g): ₹200–₹280\n"
            "- Imidacloprid 17.8 SL (250 ml): ₹250–₹350"
        ),
        "source": "Dept of Fertilizers Govt of India 2024; Telangana State Seeds Dev Corp 2024",
    },

    # ── PEST/DISEASE GENERAL ──────────────────────────────────────────────────

    {
        "id": "disease_001",
        "agent": "disease",
        "topic": "Integrated Pest Management (IPM) principles",
        "content": (
            "INTEGRATED PEST MANAGEMENT (IPM)\n"
            "\n"
            "Cultural Control:\n"
            "- Crop rotation, resistant varieties, proper spacing, avoid waterlogging.\n"
            "\n"
            "Biological Control:\n"
            "- Trichogramma @ 50,000/acre for lepidopteran pests.\n"
            "- Chrysoperla (green lacewing) for sucking pests.\n"
            "- NPV (Nuclear Polyhedrosis Virus) for bollworm.\n"
            "\n"
            "Chemical Control:\n"
            "- Use only when ETL is crossed; prefer selective insecticides.\n"
            "- BANNED — never use: Monocrotophos, Endosulfan.\n"
            "- Follow pre-harvest intervals (PHI) before harvest."
        ),
        "source": "ICAR IPM Guidelines 2023; Central Insecticides Board",
    },

    {
        "id": "disease_002",
        "agent": "disease",
        "topic": "Yellow mosaic virus in soybean and moong",
        "content": (
            "YELLOW MOSAIC VIRUS (YMV) — Soybean / Moong / Urad\n"
            "\n"
            "Cause: Whitefly (Bemisia tabaci) transmits the virus.\n"
            "\n"
            "Symptoms:\n"
            "- Bright yellow-green mosaic patches on leaves.\n"
            "- Stunted growth, poor pod set.\n"
            "\n"
            "Control:\n"
            "- Yellow sticky traps @ 10/acre to catch whitefly.\n"
            "- Spray Imidacloprid 17.8 SL @ 0.5 ml/litre at first sign.\n"
            "- OR Thiamethoxam 25 WG @ 0.3 g/litre.\n"
            "- Immediately rogue out and destroy infected plants.\n"
            "\n"
            "Prevention:\n"
            "- Use virus-free certified seeds.\n"
            "- Resistant varieties: JS-335, MAUS-71 (soybean)."
        ),
        "source": "ICAR Oilseeds Disease Management 2023",
    },

    # ── WEATHER / ADVISORY ────────────────────────────────────────────────────

    {
        "id": "weather_001",
        "agent": "general",
        "topic": "Monsoon sowing advisory for Kharif",
        "content": (
            "KHARIF MONSOON ADVISORY\n"
            "\n"
            "Sowing Timing:\n"
            "- Southwest monsoon reaches Telangana: June 15–20.\n"
            "- Sow only after 2–3 rains totalling 50–75 mm.\n"
            "- Pre-sowing: complete land prep and procure seeds/fertilizers by June 1.\n"
            "\n"
            "Weather Tools:\n"
            "- IMD 5-day forecast: imd.gov.in or Meghdoot app (free).\n"
            "- Telangana agromet advisories: TSDPS — issued bi-weekly.\n"
            "\n"
            "Caution:\n"
            "- Avoid sowing if heavy rain (> 50 mm) is forecast in next 3 days.\n"
            "- Waterlogged sowing leads to poor germination and root rot."
        ),
        "source": "IMD Agro-Met Services; TSDPS Telangana 2024",
    },

    # ── CHILLI / HORTICULTURE ─────────────────────────────────────────────────

    {
        "id": "hort_001",
        "agent": "general",
        "topic": "Chilli cultivation — Guntur, season, yield",
        "content": (
            "CHILLI CULTIVATION (GUNTUR / AP)\n"
            "\n"
            "Season & Nursery:\n"
            "- Kharif: Nursery June–July; transplant at 4–5 leaf stage (30–35 days old).\n"
            "- Rabi: Nursery September–October.\n"
            "\n"
            "Varieties:\n"
            "- LCA-334, LCA-235 — medium hot, good yield.\n"
            "- Teja (S-17) — high pungency, top export price.\n"
            "- G-5 (Kaddi) — milder, lower price.\n"
            "\n"
            "Spacing & Fertilizer:\n"
            "- Spacing: 60×45 cm.\n"
            "- N:P:K = 30:30:30 kg/acre + Boron 500 g/acre.\n"
            "\n"
            "Weed Control:\n"
            "- Pendimethalin 38.7 CS @ 700 ml/acre pre-emergence (1–2 days after transplanting).\n"
            "\n"
            "Key Pests:\n"
            "- Thrips: Spray Spinosad 45 SC @ 3 ml/10 litres.\n"
            "- Mite: Spray Propargite 57 EC @ 2 ml/litre.\n"
            "- Anthracnose (die-back): Spray Carbendazim 50 WP @ 1 g/litre at fruiting.\n"
            "\n"
            "Expected Yield:\n"
            "- Dry chilli: 4–8 quintals/acre (average), 8–12 quintals/acre (good farming)."
        ),
        "source": "ICAR Chilli Production Technology 2023; ANGRAU Crop Guide",
    },

    {
        "id": "hort_002",
        "agent": "market",
        "topic": "Chilli market prices and export 2024",
        "content": (
            "CHILLI MARKET — GUNTUR MIRCHI YARD (2024)\n"
            "\n"
            "Prices:\n"
            "- Teja (S-17) dry red: ₹12,000–₹18,000/qtl\n"
            "- LCA-334 variety: ₹8,000–₹12,000/qtl\n"
            "- G-5 (Kaddi): ₹6,000–₹9,000/qtl\n"
            "\n"
            "Export:\n"
            "- India exports 250,000+ tonnes/year. Buyers: China, Bangladesh, Sri Lanka, USA.\n"
            "- For export: moisture < 11%, no banned pesticide residues.\n"
            "- Cold storage at Guntur Yard: ₹18–₹22/qtl/month."
        ),
        "source": "Guntur Mirchi Yard APMC 2024; APEDA Export Data 2024",
    },

    # ── GROUNDNUT ─────────────────────────────────────────────────────────────

    {
        "id": "gnut_001",
        "agent": "general",
        "topic": "Groundnut cultivation — season, yield, Tikka disease",
        "content": (
            "GROUNDNUT CULTIVATION — AP / TELANGANA\n"
            "\n"
            "Season & Sowing:\n"
            "- Kharif: Sow June–July. Rabi: November–December (irrigated).\n"
            "- Seed rate: 60–70 kg/acre (bold seeded), 50–60 kg/acre (small seeded).\n"
            "- Spacing: 30×10 cm.\n"
            "\n"
            "Key Input:\n"
            "- Gypsum @ 200 kg/acre at pegging stage (45–50 DAS) — essential for pod development.\n"
            "\n"
            "Weed Control:\n"
            "- Pendimethalin 38.7 CS @ 700 ml/acre pre-emergence (1–2 DAS).\n"
            "- Manual inter-row weeding at 30 DAS.\n"
            "\n"
            "Expected Yield:\n"
            "- Average: 6–10 quintals/acre (pods). Good farming: 10–14 quintals/acre.\n"
            "\n"
            "Tikka Disease (leaf spot — Cercospora):\n"
            "- Symptoms: Circular brown spots with yellow halo on leaves.\n"
            "- Spray Mancozeb 75 WP @ 400 g/acre at 45 DAS; repeat every 10–12 days."
        ),
        "source": "ICAR Groundnut Production Guide 2023; ANGRAU AP Crop Manual",
    },

    {
        "id": "gnut_002",
        "agent": "market",
        "topic": "Groundnut MSP and market prices 2024-25",
        "content": (
            "GROUNDNUT PRICES — 2024-25\n"
            "\n"
            "- MSP 2024-25: ₹6,783/quintal (with shell).\n"
            "- Market (AP/Telangana mandis): ₹5,500–₹7,200/qtl (bold pods).\n"
            "- Groundnut oil (mill gate): ₹130–₹155/litre.\n"
            "- De-oiled cake: ₹25,000–₹28,000/tonne.\n"
            "\n"
            "Quality Tip:\n"
            "- Grade A (bold, uniform pods) fetches ₹500–₹800 premium per quintal.\n"
            "- Store at < 9% moisture to avoid Aflatoxin contamination.\n"
            "- Major oil mills: Nellore, Kurnool, Guntur districts."
        ),
        "source": "CACP MSP 2024-25; Kurnool APMC 2024; ICAR Post-Harvest Manual",
    },

    # ── MAIZE ─────────────────────────────────────────────────────────────────

    {
        "id": "maize_001",
        "agent": "general",
        "topic": "Maize cultivation — season, yield, FAW pest",
        "content": (
            "MAIZE CULTIVATION — TELANGANA / AP\n"
            "\n"
            "Season:\n"
            "- Kharif: June–October. Rabi: November–February (irrigated, better yield).\n"
            "- Rabi maize generally gives 10–15% higher yield than Kharif.\n"
            "\n"
            "Varieties:\n"
            "- DHM-117, NK-6240, Bio-9681, DKC-9144 (popular hybrids).\n"
            "- Seed rate: 8–10 kg/acre. Spacing: 60×20 cm.\n"
            "\n"
            "Fertilizer:\n"
            "- N:P:K = 60:30:30 kg/acre. Split nitrogen: 1/3 basal, 1/3 at 30 DAS, 1/3 at tasseling.\n"
            "\n"
            "Fall Armyworm (FAW) — Spodoptera frugiperda:\n"
            "- Symptoms: Scraping on young leaves, frass inside whorl.\n"
            "- Spray Emamectin Benzoate 5 SG @ 4 g/10 litres directly into the whorl.\n"
            "- OR Chlorantraniliprole 18.5 SC @ 3 ml/10 litres.\n"
            "\n"
            "Expected Yield:\n"
            "- Average: 20–28 quintals/acre. Good farming (Rabi, irrigated): 28–35 quintals/acre.\n"
            "\n"
            "Tip: Dry grain to < 14% moisture before selling — adds ₹300–₹500/qtl premium."
        ),
        "source": "ICAR Maize Production Guide 2023; PJTSAU Maize Handbook",
    },

    {
        "id": "maize_002",
        "agent": "market",
        "topic": "Maize MSP and market prices 2024-25",
        "content": (
            "MAIZE PRICES — 2024-25\n"
            "\n"
            "- MSP 2024-25: ₹2,225/quintal.\n"
            "- Nizamabad/Karimnagar mandi (2024 Kharif):\n"
            "  Dry maize (< 14% moisture): ₹1,900–₹2,350/qtl.\n"
            "  Wet maize (> 18% moisture): ₹1,400–₹1,700/qtl.\n"
            "\n"
            "Buyers: Poultry feed mills (largest), starch industry, distilleries.\n"
            "Major markets: Nizamabad, Adilabad, Karimnagar APMC yards."
        ),
        "source": "CACP MSP 2024-25; Nizamabad APMC 2024",
    },

    # ── SOYBEAN ───────────────────────────────────────────────────────────────

    {
        "id": "soy_001",
        "agent": "general",
        "topic": "Soybean cultivation — season, yield, rhizobium",
        "content": (
            "SOYBEAN CULTIVATION\n"
            "\n"
            "Season & Sowing:\n"
            "- Kharif crop. Sow June–July after monsoon onset.\n"
            "- Seed rate: 30–35 kg/acre. Spacing: 45×5 cm. Depth: 3–4 cm.\n"
            "\n"
            "Seed Treatment (important):\n"
            "- Rhizobium culture + PSB inoculant before sowing.\n"
            "- This fixes atmospheric nitrogen — saves 25 kg urea/acre.\n"
            "\n"
            "Fertilizer:\n"
            "- No nitrogen needed if Rhizobium inoculated.\n"
            "- Apply P₂O₅ 30 kg + K₂O 20 kg/acre as basal.\n"
            "\n"
            "Weed Control:\n"
            "- Imazethapyr 10 SL @ 300 ml/acre at 15–20 DAS (post-emergence).\n"
            "\n"
            "Expected Yield:\n"
            "- Average: 6–10 quintals/acre. Good farming: 10–14 quintals/acre.\n"
            "- Harvest when 95% pods turn brown (95–100 DAS)."
        ),
        "source": "ICAR Soybean Production Manual 2023",
    },

    {
        "id": "soy_002",
        "agent": "market",
        "topic": "Soybean MSP and market prices 2024-25",
        "content": (
            "SOYBEAN PRICES — 2024-25\n"
            "\n"
            "- MSP 2024-25: ₹4,892/quintal (yellow variety).\n"
            "- Latur (Maharashtra) / Nanded mandis: ₹4,400–₹5,100/qtl.\n"
            "- Soybean oil (retail): ₹105–₹120/litre.\n"
            "- Soybean meal/cake: ₹35,000–₹42,000/tonne.\n"
            "\n"
            "Export: Soybean meal is a major export commodity — APEDA certification needed."
        ),
        "source": "CACP MSP 2024-25; Latur APMC 2024; SOPA",
    },

    # ── SCHEMES ───────────────────────────────────────────────────────────────

    {
        "id": "scheme_001",
        "agent": "market",
        "topic": "Soil Health Card — free soil testing",
        "content": (
            "SOIL HEALTH CARD SCHEME\n"
            "\n"
            "- Free soil test every 2 years for all farmers.\n"
            "- Tests: N, P, K, pH, EC, organic carbon, 8 micronutrients.\n"
            "- Get customised fertilizer recommendation for your specific plot.\n"
            "- Savings: Reduces fertilizer cost by ₹1,500–₹2,500/acre by avoiding excess use.\n"
            "\n"
            "How to Apply:\n"
            "- Visit nearest KVK or Agriculture Dept soil testing lab.\n"
            "- Online: soilhealth.dac.gov.in"
        ),
        "source": "Department of Agriculture, Cooperation and Farmers Welfare 2024",
    },

    {
        "id": "scheme_002",
        "agent": "market",
        "topic": "eNAM — digital marketing for farmers",
        "content": (
            "eNAM (NATIONAL AGRICULTURE MARKET)\n"
            "\n"
            "- Online platform connecting farmers to buyers across India.\n"
            "- Registration: Free at enam.gov.in or nearest APMC yard.\n"
            "- Required: Aadhaar, bank account, land record.\n"
            "\n"
            "Benefits:\n"
            "- Transparent online price discovery — buyers bid competitively.\n"
            "- Direct payment to bank account.\n"
            "- Wider buyer base — not limited to local mandi."
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

        parts = key.split("___")
        crop    = parts[0].replace("_", " ").strip()
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
            "id":     f"disease_auto_{key.lower().replace(',', '').replace(' ', '_')}",
            "agent":  "disease",
            "topic":  f"{crop} {disease}",
            "content": content,
            "source": "AgriGPT Disease Diagnosis Database 2026",
        })
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(
        "Failed to inject DISEASE_INFO into knowledge chunks: %s", e
    )