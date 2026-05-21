# =============================================================================
# AgriGPT — Feature 6: Government Schemes Q&A
# schemes/static_kb.py
#
# Bilingual (English + Hindi + Telugu) static knowledge base.
# Focus: Telangana, Andhra Pradesh + all central schemes.
# Used as fallback when FAISS / ChromaDB has no relevant chunks.
# =============================================================================

SCHEMES_KB: list[dict] = [

    # ── PM-KISAN ──────────────────────────────────────────────────────────────
    {
        "id"      : "pm_kisan",
        "name"    : "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "name_hi" : "पीएम-किसान (प्रधानमंत्री किसान सम्मान निधि)",
        "name_te" : "పీఎం-కిసాన్ (ప్రధాన మంత్రి కిసాన్ సమ్మాన్ నిధి)",
        "type"    : "Central Scheme",
        "category": "subsidies",
        "states"  : ["all"],
        "content_en": """
PM-KISAN provides ₹6,000 per year to farmer families in 3 instalments of ₹2,000 each,
directly to their bank account every 4 months.

Eligibility: All land-holding farmer families. Excludes government employees, income
tax payers, and institutional land holders.

How to apply: Visit pmkisan.gov.in or nearest CSC centre.
Documents: Aadhaar, bank passbook, land records (Patta/RoR).
Instalment months: April, August, December.
Helpline: 155261 / 1800-115-526 (toll-free)

Telangana: Also linked with Rythu Bandhu. Farmers get PM-KISAN + Rythu Bandhu both.
AP: Combined with YSR Rythu Bharosa — total ₹13,500/year.
        """,
        "content_hi": """
PM-KISAN योजना के तहत किसान परिवारों को हर साल ₹6,000 मिलते हैं।
यह राशि ₹2,000 की 3 किस्तों में सीधे बैंक खाते में आती है।

पात्रता: सभी भूमि-धारक किसान परिवार। सरकारी कर्मचारी, आयकर दाता पात्र नहीं।

आवेदन कैसे करें: pmkisan.gov.in पर जाएं या नजदीकी CSC केंद्र जाएं।
दस्तावेज़: आधार कार्ड, बैंक पासबुक, भूमि रिकॉर्ड (पट्टा/RoR)।
किस्त महीने: अप्रैल, अगस्त, दिसंबर।
हेल्पलाइन: 155261 / 1800-115-526 (टोल-फ्री)

तेलंगाना: रायतु बंधु के साथ दोनों मिलते हैं।
आंध्र प्रदेश: रायतु भरोसा के साथ कुल ₹13,500/वर्ष।
        """,
        "content_te": """
పీఎం-కిసాన్ పథకం ద్వారా ప్రతి ఏటా రైతు కుటుంబాలకు ₹6,000 పెట్టుబడి సహాయం లభిస్తుంది.
ఈ సహాయం ₹2,000 చొప్పున 3 విడతలలో ప్రతి 4 నెలలకు ఒకసారి నేరుగా వారి బ్యాంక్ ఖాతాల్లో జమ చేయబడుతుంది.

అర్హత: భూమి ఉన్న ప్రతి రైతు కుటుంబం అర్హులు. ప్రభుత్వ ఉద్యోగులు, ఆదాయపు పన్ను చెల్లించేవారు అర్హులు కారు.

దరఖాస్తు విధానం: pmkisan.gov.in పోర్టల్ ద్వారా లేదా దగ్గరలోని CSC కేంద్రంలో దరఖాస్తు చేసుకోవచ్చు.
కావలసిన పత్రాలు: ఆధార్ కార్డ్, బ్యాంక్ పాస్‌బుక్, భూమి రికార్డులు (పట్టాదార్ పాస్‌బుక్).
విడతలు వచ్చే నెలలు: ఏప్రిల్, ఆగస్టు, డిసెంబర్.
హెల్ప్‌లైన్: 155261 / 1800-115-526 (టోల్-ఫ్రీ)

తెలంగాణ: రైతు బంధు పథకంతో పాటు ఈ పథకం కూడా లభిస్తుంది.
ఆంధ్రప్రదేశ్: వైఎస్ఆర్ రైతు భరోసాతో కలిపి మొత్తం ₹13,500/ఏడాదికి లభిస్తుంది.
        """,
        "source": "PM-KISAN Official Guidelines — Ministry of Agriculture & Farmers Welfare",
    },

    # ── RYTHU BANDHU (Telangana) ──────────────────────────────────────────────
    {
        "id"      : "rythu_bandhu",
        "name"    : "Rythu Bandhu — Telangana",
        "name_hi" : "रायतु बंधु — तेलंगाना",
        "name_te" : "రైతు బంధు — తెలంగాణ",
        "type"    : "State Scheme — Telangana",
        "category": "subsidies",
        "states"  : ["telangana", "ts"],
        "content_en": """
Rythu Bandhu is Telangana's flagship scheme giving ₹5,000/acre/season (₹10,000/acre/year)
as direct investment support for seeds, fertilisers and inputs.

Eligibility: Land-owning farmers in Telangana registered in Dharani portal.
Tenant farmers are NOT eligible — only registered pattadar (land owners).

How to apply:
- Existing pattadar passbook holders: NO separate application needed.
- New farmers: Visit local Agriculture Office with Pattadar Passbook + Aadhaar + bank passbook.
- Land must be registered under farmer's name in Dharani portal (dharani.telangana.gov.in).

Payment:
- Kharif (June–July): ₹5,000/acre
- Rabi (December): ₹5,000/acre
- Credited directly to Aadhaar-linked bank account.

Helpline: 1800-425-0019 (Telangana Agriculture Dept, toll-free)
Portal: agriculture.telangana.gov.in

Important: If payment is delayed, visit nearest Rythu Seva Kendra (RSK) in your mandal.
        """,
        "content_hi": """
रायतु बंधु तेलंगाना की प्रमुख योजना है जो ₹5,000/एकड़/सीजन (₹10,000/एकड़/वर्ष)
बीज, खाद और इनपुट के लिए सीधे सहायता देती है।

पात्रता: तेलंगाना में धरानी पोर्टल में पंजीकृत भूमि-धारक किसान।
किरायेदार किसान पात्र नहीं — केवल पंजीकृत पट्टादार (भूमि मालिक)।

आवेदन कैसे करें:
- मौजूदा पट्टादार पासबुक धारक: कोई अलग आवेदन नहीं।
- नए किसान: आधार + पट्टादार पासबुक + बैंक पासबुक के साथ कृषि कार्यालय जाएं।
- भूमि धरानी पोर्टल (dharani.telangana.gov.in) में दर्ज होनी चाहिए।

भुगतान:
- खरीफ (जून-जुलाई): ₹5,000/एकड़
- रबी (दिसंबर): ₹5,000/एकड़
- आधार-लिंक्ड बैंक खाते में सीधे जमा।

हेल्पलाइन: 1800-425-0019 (तेलंगाना कृषि विभाग, टोल-फ्री)
पोर्टल: agriculture.telangana.gov.in

महत्वपूर्ण: भुगतान में देरी होने पर अपने मंडल के नजदीकी रायतु सेवा केंद्र (RSK) पर जाएं।
        """,
        "content_te": """
రైతు బంధు తెలంగాణ ప్రభుత్వ ప్రతిష్టాత్మక పథకం. దీని ద్వారా రైతులకు ప్రతి ఎకరాకు ఏడాదికి ₹10,000 (వానకాలం ₹5,000 మరియు యాసంగి ₹5,000) పెట్టుబడి సహాయం లభిస్తుంది.

అర్హత: ధరణి పోర్టల్‌లో నమోదైన భూమి ఉన్న తెలంగాణ రైతులు అర్హులు. కౌలు రైతులకు ఈ పథకం వర్తించదు.

దరఖాస్తు విధానం:
- కొత్త రైతులు: ఆధార్, పట్టాదార్ పాస్‌బుక్, బ్యాంక్ ఖాతా వివరాలతో స్థానిక వ్యవసాయ అధికారిని సంప్రదించాలి.
- పాత రైతులు: ప్రత్యేక దరఖాస్తు అవసరం లేదు.
- ల్యాండ్ కచ్చితంగా ధరణి పోర్టల్ (dharani.telangana.gov.in) లో నమోదై ఉండాలి.

విడతలు:
- వానకాలం (ఖరీఫ్ - జూన్/జూలై): ఎకరాకు ₹5,000
- యాసంగి (రబీ - డిసెంబర్): ఎకరాకు ₹5,000
- నేరుగా ఆధార్ అనుసంధాన బ్యాంక్ ఖాతాల్లో జమ అవుతుంది.

హెల్ప్‌లైన్: 1800-425-0019 (తెలంగాణ వ్యవసాయ శాఖ, టోల్-ఫ్రీ)
పోర్టల్: agriculture.telangana.gov.in
గమనిక: పేమెంట్ ఆలస్యమైతే మండలంలోని రైతు సేవా కేంద్రాన్ని (RSK) సంప్రదించండి.
        """,
        "source": "Rythu Bandhu Guidelines — Government of Telangana Agriculture Department",
    },

    # ── YSR RYTHU BHAROSA (Andhra Pradesh) ───────────────────────────────────
    {
        "id"      : "rythu_bharosa",
        "name"    : "YSR Rythu Bharosa — Andhra Pradesh",
        "name_hi" : "YSR रायतु भरोसा — आंध्र प्रदेश",
        "name_te" : "వైఎస్ఆర్ రైతు భరోసా — ఆంధ్రప్రదేశ్",
        "type"    : "State Scheme — Andhra Pradesh",
        "category": "subsidies",
        "states"  : ["andhra pradesh", "ap", "andhra"],
        "content_en": """
YSR Rythu Bharosa provides ₹13,500/family/year combining:
- PM-KISAN: ₹6,000 (central)
- State component: ₹7,500 (AP government)

Unique feature: Tenant farmers (varams) are also covered under AP's state component.

How to apply:
- Visit nearest YSR Rythu Bharosa Kendra (RBKS) in your village/mandal.
- Or register at MeeSeva centre.
- Documents: Land records / tenancy agreement, Aadhaar, bank account.

Helpline: 1902 (AP Agriculture)
Portal: apagrisnet.gov.in | rbks.ap.gov.in

Free services at Rythu Bharosa Kendra:
- Soil testing, seeds, fertilizers at subsidised rates.
- Free crop insurance enrollment (PMFBY).
- Agricultural advice from village agriculture assistants (VAA).
        """,
        "content_hi": """
YSR रायतु भरोसा ₹13,500/परिवार/वर्ष प्रदान करती है:
- PM-KISAN: ₹6,000 (केंद्र)
- राज्य घटक: ₹7,500 (आंध्र प्रदेश सरकार)

विशेषता: किरायेदार किसान (वरम) भी AP राज्य घटक के तहत पात्र हैं।

आवेदन कैसे करें:
- गांव/मंडल में YSR रायतु भरोसा केंद्र (RBKS) जाएं।
- या MeeSeva केंद्र में पंजीकरण करें।
- दस्तावेज़: भूमि रिकॉर्ड/किरायेदारी समझौता, आधार, बैंक खाता।

हेल्पलाइन: 1902 (AP कृषि)
पोर्टल: apagrisnet.gov.in

रायतु भरोसा केंद्र पर मुफ्त सेवाएं:
- मिट्टी परीक्षण, बीज, रियायती दर पर खाद।
- मुफ्त फसल बीमा नामांकन (PMFBY)।
- गांव कृषि सहायक (VAA) से कृषि सलाह।
        """,
        "content_te": """
వైఎస్ఆర్ రైతు భరోసా పథకం ద్వారా ఆంధ్రప్రదేశ్ ప్రభుత్వం రైతు కుటుంబాలకు ఏడాదికి ₹13,500 సహాయం అందిస్తుంది. ఇందులో:
- పిఎం-కిసాన్ (కేంద్రం): ₹6,000
- రాష్ట్ర ప్రభుత్వ వాటా: ₹7,500

ప్రత్యేకత: ఆంధ్రప్రదేశ్ ప్రభుత్వం ఈ పథకం కింద కౌలు రైతులకు కూడా పెట్టుబడి సహాయం అందిస్తుంది.

దరఖాస్తు విధానం:
- గ్రామ/వార్డు సచివాలయంలో లేదా రైతు భరోసా కేంద్రం (RBK) వద్ద దరఖాస్తు చేసుకోవాలి.
- లేదా మీసేవ (MeeSeva) ద్వారా నమోదు చేసుకోవచ్చు.
- కావలసిన పత్రాలు: భూమి రికార్డులు/కౌలు పత్రాలు, ఆధార్, బ్యాంక్ ఖాతా వివరాలు.

హెల్ప్‌లైన్: 1902 (ఏపీ వ్యవసాయ శాఖ)
పోర్టల్: apagrisnet.gov.in | rbks.ap.gov.in

రైతు భరోసా కేంద్రం (RBK) లో ఉచిత సేవలు:
- సబ్సిడీ ధరలపై నాణ్యమైన విత్తనాలు, ఎరువులు మరియు పురుగుల మందులు.
- ఉచిత మట్టి పరీక్షలు.
- ఉచిత పంటల బీమా నమోదు (PMFBY).
- విలేజ్ అగ్రికల్చర్ అసిస్టెంట్ (VAA) ల ద్వారా సాంకేతిక వ్యవసాయ సలహాలు.
        """,
        "source": "YSR Rythu Bharosa Guidelines — Government of Andhra Pradesh",
    },

    # ── PMFBY ─────────────────────────────────────────────────────────────────
    {
        "id"      : "pmfby",
        "name"    : "PMFBY (Pradhan Mantri Fasal Bima Yojana)",
        "name_hi" : "पीएमएफबीवाई (प्रधानमंत्री फसल बीमा योजना)",
        "name_te" : "పీఎంఎఫ్‌బీవై (ప్రధాన మంత్రి ఫసల్ బీమా యోజన)",
        "type"    : "Central Scheme",
        "category": "insurance",
        "states"  : ["all"],
        "content_en": """
PMFBY provides crop insurance covering losses from natural calamities, pests, diseases.

Premium (farmer pays):
- Kharif crops: 2% of sum insured
- Rabi crops: 1.5% of sum insured
- Horticulture/commercial: 5%

Coverage: Pre-sowing loss, standing crop, post-harvest, localised calamities.

Telangana & AP: Enrollment done at Rythu Seva Kendra / Rythu Bharosa Kendra.
Free enrollment for loan-linked farmers through their bank.

How to apply:
- Visit bank, CSC, or nearest Rythu Seva Kendra BEFORE season cut-off date.
- Documents: Land records, Aadhaar, bank account, sowing certificate.
- Online: pmfby.gov.in

Helpline: 1800-200-7710 (toll-free)

Claim process: Report crop loss to bank/insurance company within 72 hours of calamity.
        """,
        "content_hi": """
PMFBY प्राकृतिक आपदाओं, कीटों, बीमारियों से फसल नुकसान का बीमा कवर देती है।

प्रीमियम (किसान का हिस्सा):
- खरीफ फसलें: बीमित राशि का 2%
- रबी फसलें: बीमित राशि का 1.5%
- बागवानी/व्यावसायिक: 5%

कवरेज: बुवाई पूर्व, खड़ी फसल, कटाई उपरांत, स्थानीय आपदाएं।

तेलंगाना और AP: रायतु सेवा केंद्र / रायतु भरोसा केंद्र पर नामांकन।
ऋण-लिंक्ड किसानों के लिए बैंक के माध्यम से मुफ्त नामांकन।

आवेदन कैसे करें:
- सीजन कट-ऑफ तारीख से पहले बैंक, CSC या रायतु सेवा केंद्र जाएं।
- दस्तावेज़: भूमि रिकॉर्ड, आधार, बैंक खाता, बुवाई प्रमाण पत्र।
- ऑनलाइन: pmfby.gov.in

हेल्पलाइन: 1800-200-7710 (टोल-फ्री)

दावा प्रक्रिया: आपदा के 72 घंटे के भीतर बैंक/बीमा कंपनी को सूचित करें।
        """,
        "content_te": """
పంటల బీమా పథకం (PMFBY) ప్రకృతి వైపరీత్యాలు, తెగుళ్ళు, మరియు వ్యాధుల వల్ల జరిగే పంట నష్టానికి బీమా రక్షణ కల్పిస్తుంది.

ప్రీమియం (రైతు వాటా):
- ఖరీఫ్ పంటలు: భీమా మొత్తంలో 2%
- రబీ పంటలు: భీమా మొత్తంలో 1.5%
- తోట మరియు వాణిజ్య పంటలు: 5%

రక్షణ పరిధి: విత్తే ముందు నష్టం, నిలబడిన పంట నష్టం, కోత తర్వాతి నష్టం మరియు స్థానిక విపత్తులు.
తెలంగాణ & ఏపీ: నమోదు ప్రక్రియను రైతు సేవా కేంద్రాలు / రైతు భరోసా కేంద్రాలలో చేసుకోవచ్చు. పంట రుణం ఉన్న రైతులకు బ్యాంకుల ద్వారా స్వయంచాలకంగా నమోదు చేయబడుతుంది.

దరఖాస్తు విధానం:
- సీజన్ గడువు తేదీ కంటే ముందే బ్యాంక్, CSC, లేదా రైతు సేవా కేంద్రాన్ని సంప్రదించాలి.
- కావలసిన పత్రాలు: భూమి రికార్డులు, ఆధార్ కార్డ్, బ్యాంక్ పాస్‌బుక్, పంట సాగు ధృవీకరణ పత్రం.
- ఆన్‌లైన్: pmfby.gov.in

హెల్ప్‌లైన్: 1800-200-7710 (టోల్-ఫ్రీ)
క్లెయిమ్ విధానం: పంట నష్టం జరిగిన 72 గంటల లోపు బ్యాంక్ లేదా ఇన్సూరెన్స్ కంపెనీకి తెలియజేయాలి.
        """,
        "source": "PMFBY Operational Guidelines — Ministry of Agriculture & Farmers Welfare",
    },

    # ── KCC ───────────────────────────────────────────────────────────────────
    {
        "id"      : "kcc",
        "name"    : "KCC (Kisan Credit Card)",
        "name_hi" : "केसीसी (किसान क्रेडिट कार्ड)",
        "name_te" : "కేసీసీ (కిసాన్ క్రెడిట్ కార్డ్)",
        "type"    : "Central Scheme",
        "category": "credit",
        "states"  : ["all"],
        "content_en": """
KCC provides short-term credit at 4% effective interest rate (7% minus 3% prompt repayment rebate).

Credit limit: ₹50,000 – ₹3,00,000 based on land holding and crop.
Eligibility: All farmers, tenant farmers, sharecroppers, SHGs.

How to apply: Visit any nationalized bank, cooperative bank, or RRB.
Documents: Land records, Aadhaar, passport photo.

Telangana: Apply at District Cooperative Central Banks (DCCB) in your district.
AP: Apply at APCOB (AP State Cooperative Bank) branches.

Helpline: 1800-180-1551 (NABARD toll-free)
        """,
        "content_hi": """
KCC 4% प्रभावी ब्याज दर पर अल्पकालिक ऋण प्रदान करता है (7% - 3% समय पर चुकाने की छूट)।

ऋण सीमा: भूमि और फसल के आधार पर ₹50,000 – ₹3,00,000।
पात्रता: सभी किसान, किरायेदार किसान, बटाईदार, SHG।

आवेदन: किसी भी राष्ट्रीयकृत बैंक, सहकारी बैंक या RRB जाएं।
दस्तावेज़: भूमि रिकॉर्ड, आधार, पासपोर्ट फोटो।

तेलंगाना: जिले में DCCB (जिला सहकारी केंद्रीय बैंक) में आवेदन करें।
AP: APCOB (AP राज्य सहकारी बैंक) शाखाओं में आवेदन करें।

हेल्पलाइन: 1800-180-1551 (NABARD टोल-फ्री)
        """,
        "content_te": """
కిసాన్ క్రెడిట్ కార్డ్ (KCC) ద్వారా రైతులకు అతి తక్కువ వడ్డీకే (ప్రభావవంతమైన వడ్డీ రేటు 4% - సకాలంలో చెల్లింపులపై 3% వడ్డీ రాయితీ లభిస్తుంది) స్వల్పకాలిక రుణ సదుపాయం లభిస్తుంది.

రుణ పరిమితి: భూమి విస్తీర్ణం మరియు పండించే పంట ఆధారంగా ₹50,000 నుండి ₹3,00,000 వరకు లభిస్తుంది.
అర్హత: రైతులు, కౌలు రైతులు, భాగస్వామ్య రైతులు, మరియు స్వయం సహాయక బృందాలు (SHGs) అర్హులు.

దరఖాస్తు విధానం: ఏ జాతీయ బ్యాంకు, సహకార బ్యాంకు లేదా గ్రామీణ బ్యాంకునైనా సంప్రదించవచ్చు.
తెలంగాణ: జిల్లా సహకార కేంద్ర బ్యాంకు (DCCB) శాఖలలో దరఖాస్తు చేసుకోవచ్చు.
ఏపీ: సహకార బ్యాంకు (APCOB) శాఖలలో దరఖాస్తు చేసుకోవచ్చు.
కావలసిన పత్రాలు: భూమి పత్రాలు, ఆధార్ కార్డ్, పాస్‌పోర్ట్ సైజ్ ఫోటో.

హెల్ప్‌లైన్: 1800-180-1551 (నాబార్డ్ టోల్-ఫ్రీ)
        """,
        "source": "KCC Scheme Guidelines — RBI & NABARD",
    },

    # ── PMKSY ─────────────────────────────────────────────────────────────────
    {
        "id"      : "pmksy",
        "name"    : "PMKSY — Drip & Sprinkler Irrigation Subsidy",
        "name_hi" : "PMKSY — ड्रिप और स्प्रिंकलर सिंचाई सब्सिडी",
        "name_te" : "పీఎంకేఎస్‌వై — మైక్రో ఇరిగేషన్ (డ్రిప్ & స్ప్రింక్లర్) సబ్сиడీ",
        "type"    : "Central Scheme",
        "category": "irrigation",
        "states"  : ["all"],
        "content_en": """
PMKSY Per Drop More Crop component provides 55% subsidy for small/marginal farmers
and 45% for others on drip and sprinkler irrigation systems.

Telangana:
- Additional 10% state top-up → total 65% subsidy for small/marginal farmers.
- Apply at district agriculture office or Mission Kakatiya office.
- Online: pmksy.telangana.gov.in

AP:
- Additional state component for micro-irrigation.
- Apply at Horticulture Department office in your district.

How to apply:
1. Get quotation from approved vendor list (available at district office).
2. Submit application with land records, Aadhaar, bank passbook, borewell details.
3. Inspection by agriculture officer → approval → purchase → subsidy credited.

Helpline: 1800-180-1551
        """,
        "content_hi": """
PMKSY पर ड्रॉप मोर क्रॉप घटक ड्रिप और स्प्रिंकलर सिंचाई पर
छोटे/सीमांत किसानों को 55% और अन्य को 45% सब्सिडी देता है।

तेलंगाना:
- अतिरिक्त 10% राज्य सब्सिडी → छोटे/सीमांत किसानों को कुल 65%।
- जिला कृषि कार्यालय या मिशन काकतीय कार्यालय में आवेदन करें।
- ऑनलाइन: pmksy.telangana.gov.in

आंध्र प्रदेश:
- सूक्ष्म सिंचाई के लिए अतिरिक्त राज्य घटक।
- अपने जिले में बागवानी विभाग कार्यालय में आवेदन करें।

आवेदन प्रक्रिया:
1. जिला कार्यालय से अनुमोदित विक्रेता सूची से कोटेशन लें।
2. भूमि रिकॉर्ड, आधार, बैंक पासबुक, बोरवेल विवरण के साथ आवेदन करें।
3. कृषि अधिकारी निरीक्षण → स्वीकृति → खरीद → सब्सिडी।

हेल्पलाइन: 1800-180-1551
        """,
        "content_te": """
పీఎంకేఎస్‌వై (PMKSY) ద్వారా సూక్ష్మ సేద్య పరికరాలైన డ్రిప్ మరియు స్ప్రింక్లర్ సిస్టమ్స్‌పై చిన్న మరియు సన్నకారు రైతులకు 55%, ఇతర రైతులకు 45% సబ్సిడీ లభిస్తుంది.

తెలంగాణ:
- అదనంగా 10% రాష్ట్ర సబ్సిడీతో కలిపి మొత్తం 65% వరకు సబ్సిడీ లభిస్తుంది.
- జిల్లా వ్యవసాయ అధికారి లేదా మిషన్ కాకతీయ కార్యాలయంలో దరఖాస్తు చేసుకోవాలి.
- ఆన్‌లైన్: pmksy.telangana.gov.in

ఏపీ:
- మైక్రో ఇరిగేషన్ కోసం అదనపు రాష్ట్ర వాటా లభిస్తుంది.
- మీ జిల్లాలోని ఉద్యానవన శాఖ (Horticulture) కార్యాలయంలో దరఖాస్తు చేయాలి.

దరఖాస్తు విధానం:
1. ఆమోదించబడిన విక్రేత నుండి కొటేషన్ పొందాలి.
2. భూమి పత్రాలు, ఆధార్, బ్యాంక్ పాస్‌బుక్, బోరు బావి వివరాలతో దరఖాస్తు సమర్పించాలి.
3. వ్యవసాయ అధికారి క్షేత్రస్థాయి పరిశీలన చేసి ఆమోదించిన తర్వాత పరికరాలు కొనుగోలు చేసి సబ్సిడీ పొందవచ్చు.

హెల్ప్‌లైన్: 1800-180-1551
        """,
        "source": "PMKSY Operational Guidelines — Ministry of Jal Shakti",
    },

    # ── FREE SEEDS (Telangana + AP) ───────────────────────────────────────────
    {
        "id"      : "free_seeds_ts_ap",
        "name"    : "Free Seed Distribution — Telangana & AP",
        "name_hi" : "मुफ्त बीज वितरण — तेलंगाना और आंध्र प्रदेश",
        "name_te" : "ఉచిత విత్తనాల పంపిణీ — తెలంగాణ & ఏపీ",
        "type"    : "State Scheme",
        "category": "seeds",
        "states"  : ["telangana", "ts", "andhra pradesh", "ap"],
        "content_en": """
Telangana — Free Seed Kit Distribution:
- Every Kharif season, Telangana distributes free seed kits of paddy, maize, cotton,
  redgram, sunflower to small and marginal farmers (<5 acres).
- Distributed at Rythu Seva Kendra (RSK) in each mandal.
- Apply BEFORE June 15 each year at RSK with Pattadar Passbook + Aadhaar.
- Helpline: 1800-425-1556 (Telangana Agriculture, toll-free)

Andhra Pradesh — YSR Free Crop Input Scheme:
- Free seed mini-kits distributed at Rythu Bharosa Kendra (RBKS).
- Crops covered: paddy, groundnut, redgram, bengal gram.
- Priority to SC/ST farmers and flood-affected areas.
- Helpline: 1902 (AP Agriculture)
        """,
        "content_hi": """
तेलंगाना — मुफ्त बीज किट वितरण:
- हर खरीफ सीजन में तेलंगाना छोटे और सीमांत किसानों (<5 एकड़) को
  धान, मक्का, कपास, अरहर, सूरजमुखी के मुफ्त बीज किट देता है।
- हर मंडल के रायतु सेवा केंद्र (RSK) पर वितरित।
- पट्टादार पासबुक + आधार के साथ प्रति वर्ष 15 जून से पहले आवेदन करें।
- हेल्पलाइन: 1800-425-1556 (तेलंगाना कृषि, टोल-फ्री)

आंध्र प्रदेश — YSR मुफ्त फसल इनपुट योजना:
- रायतु भरोसा केंद्र (RBKS) पर मुफ्त बीज मिनी-किट वितरित।
- फसलें: धान, मूंगफली, अरहर, चना।
- SC/ST किसानों और बाढ़ प्रभावित क्षेत्रों को प्राथमिकता।
- हेल्पलाइन: 1902 (AP कृषि)
        """,
        "content_te": """
తెలంగాణ — ఉచిత విత్తన కిట్ల పంపిణీ:
- ప్రతి ఖరీఫ్ సీజన్‌లో చిన్న, సన్నకారు రైతులకు (<5 ఎకరాలు) వరి, మొక్కజొన్న, పత్తి, కందులు, పొద్దుతిరుగుడు ఉచిత విత్తన కిట్లను పంపిణీ చేస్తారు.
- వీటిని ప్రతి మండలంలోని రైతు సేవా కేంద్రంలో (RSK) పొందవచ్చు.
- ప్రతి ఏటా జూన్ 15 లోపు రైతు సేవా కేంద్రంలో పట్టాదార్ పాస్‌బుక్, ఆధార్ కార్డుతో దరఖాస్తు చేసుకోవాలి.
- హెల్ప్‌లైన్: 1800-425-1556 (వ్యవసాయ శాఖ)

ఆంధ్రప్రదేశ్ — వైఎస్ఆర్ ఉచిత పంటల ఇన్‌పుట్:
- రైతు భరోసా కేంద్రాల (RBK) ద్వారా వరి, వేరుశనగ, కందులు, శనగల ఉచిత విత్తన కిట్లు పంపిణీ చేయబడతాయి.
- ఎస్సీ/ఎస్టీ రైతులకు మరియు వరద ప్రభావిత ప్రాంత రైతులకు ప్రాధాన్యత ఇవ్వబడుతుంది.
- హెల్ప్‌లైన్: 1902 (ఏపీ వ్యవసాయ శాఖ)
        """,
        "source": "Telangana Agriculture Dept + AP Agriculture Dept — Seed Distribution Guidelines",
    },

    # ── PM-KUSUM ──────────────────────────────────────────────────────────────
    {
        "id"      : "pm_kusum",
        "name"    : "PM-KUSUM — Solar Pump Scheme",
        "name_hi" : "पीएम-कुसुम — सोलर पंप योजना",
        "name_te" : "పీఎం-కుసుమ్ — సోలార్ పంప్ సెట్ల పథకం",
        "type"    : "Central Scheme",
        "category": "irrigation",
        "states"  : ["all"],
        "content_en": """
PM-KUSUM provides solar-powered pumps to farmers with 60% total subsidy (30% central + 30% state).
Farmer pays only 10%; 30% bank loan.

Pump sizes: 3 HP, 5 HP, 7.5 HP.

Telangana: Apply through TSSPDCL (Telangana Southern Power Distribution Co. Ltd).
AP: Apply through APEPDCL / APSPDCL in your region.

Eligibility: Farmers with borewell or open well, agriculture land documents.
Priority: Small and marginal farmers.

Helpline: 1800-180-3333 (MNRE, toll-free)
Portal: mnre.gov.in → PM-KUSUM
        """,
        "content_hi": """
PM-KUSUM किसानों को 60% कुल सब्सिडी (30% केंद्र + 30% राज्य) पर सोलर पंप देता है।
किसान केवल 10% देता है; 30% bank ऋण।

पंप साइज: 3 HP, 5 HP, 7.5 HP।

तेलंगाना: TSSPDCL के माध्यम से आवेदन करें।
AP: अपने क्षेत्र में APEPDCL / APSPDCL के माध्यम से आवेदन करें।

पात्रता: बोरवेल या खुले कुएं वाले किसान, कृषि भूमि दस्तावेज।
प्राथमिकता: छोटे और सीमांत किसान।

हेल्पलाइन: 1800-180-3333 (MNRE, टोल-फ्री)
        """,
        "content_te": """
పీఎం-కుసుమ్ (PM-KUSUM) పథకం కింద రైతులకు సోలార్ పంప్ సెట్ల కొనుగోలుపై మొత్తం 60% సబ్సిడీ లభిస్తుంది (30% కేంద్ర + 30% రాష్ట్రం). రైతు కేవలం 10% మాత్రమే చెల్లించాలి, మిగిలిన 30% బ్యాంకు రుణం లభిస్తుంది.

పంప్ సైజులు: 3 HP, 5 HP, మరియు 7.5 HP సోలార్ పంపులు అందుబాటులో ఉన్నాయి.

తెలంగాణ: TSSPDCL లేదా TSNPDCL ద్వారా దరఖాస్తు చేసుకోవాలి.
ఏపీ: మీ ప్రాంతంలోని APEPDCL / APSPDCL ద్వారా దరఖాస్తు చేసుకోవాలి.

అర్హత: బోర్వెల్ లేదా ఓపెన్ బావి ఉన్న రైతులు, వ్యవసాయ భూమి రికార్డులు కలిగి ఉండాలి. చిన్న మరియు సన్నకారు రైతులకు ప్రాధాన్యత ఇవ్వబడుతుంది.

హెల్ప్‌లైన్: 1800-180-3333 (MNRE టోల్-ఫ్రీ)
వెబ్‌సైట్: mnre.gov.in → PM-KUSUM
        """,
        "source": "PM-KUSUM Scheme Guidelines — Ministry of New and Renewable Energy",
    },

    # ── SOIL HEALTH CARD ──────────────────────────────────────────────────────
    {
        "id"      : "soil_health_card",
        "name"    : "Soil Health Card Scheme",
        "name_hi" : "मृदा स्वास्थ्य कार्ड योजना",
        "name_te" : "సాయిల్ హెల్త్ కార్డ్ (మృదా ఆరోగ్య పత్రం)",
        "type"    : "Central Scheme",
        "category": "subsidies",
        "states"  : ["all"],
        "content_en": """
Free soil testing for 12 parameters (N, P, K, pH, EC, OC, S, Zn, Fe, Mn, Cu, B)
with crop-wise fertiliser recommendations.

How to get:
- Contact local Rythu Seva Kendra (Telangana) or RBKS (AP).
- Soil sample collected from your field by agriculture officer.
- Card issued in 3–4 weeks.
- View online: soilhealth.dac.gov.in

Benefit: Saves 20-30% on fertiliser costs by avoiding over-application.
        """,
        "content_hi": """
12 मापदंडों की मुफ्त मिट्टी जांच के साथ फसल-वार उर्वरक सिफारिशें।

कैसे पाएं:
- स्थानीय रायतु सेवा केंद्र (तेलंगाना) या RBKS (AP) से संपर्क करें।
- कृषि अधिकारी आपके खेत से मिट्टी का नमूना लेंगे।
- 3-4 सप्ताह में कार्ड मिलता है।
- ऑनलाइन देखें: soilhealth.dac.gov.in

फायदा: अधिक प्रयोग से बचकर उर्वरक लागत में 20-30% बचत।
        """,
        "content_te": """
ఈ పథకం కింద పొలంలోని మట్టిని పరీక్షించి, 12 రకాల పోషక విలువల వివరాలతో (N, P, K, pH, EC, OC, S, Zn, Fe, Mn, Cu, B) కూడిన కార్డును ఉచితంగా అందజేస్తారు. అలాగే పంటల వారీగా వాడాల్సిన ఎరువుల సిఫార్సులను అందిస్తారు.

ఎలా పొందాలి:
- స్థానిక రైతు సేవా కేంద్రం (తెలంగాణ) లేదా రైతు భరోసా కేంద్రం (RBK - ఏపీ) వ్యవసాయ అధికారిని సంప్రదించాలి.
- వ్యవసాయ అధికారి మీ పొలం నుండి మట్టి నమూనా సేకరిస్తారు.
- పరీక్షించిన కార్డు 3-4 వారాల్లో జారీ చేయబడుతుంది.
- ఆన్‌లైన్ పోర్టల్: soilhealth.dac.gov.in

ఫలితం: ఎరువుల అధిక వాడకాన్ని తగ్గించడం ద్వారా సాగు ఖర్చు 20-30% ఆదా అవుతుంది.
        """,
        "source": "Soil Health Card Scheme — Department of Agriculture & Farmers Welfare",
    },
]

# ── Aliases ───────────────────────────────────────────────────────────────────
STATE_ALIASES = {
    "ts"        : "telangana",
    "tg"        : "telangana",
    "ap"        : "andhra pradesh",
    "andhra"    : "andhra pradesh",
    "telangana" : "telangana",
}


def search_static(query: str, state: str = "", top_k: int = 4) -> list[dict]:
    """Keyword-ranked static KB search with state boost."""
    q      = query.lower()
    state  = STATE_ALIASES.get(state.lower().strip(), state.lower().strip())
    scored = []
    for entry in SCHEMES_KB:
        combined = (
            entry["name"] + " " + entry.get("name_hi", "") + " " + entry.get("name_te", "") + " " +
            entry["content_en"] + " " + entry.get("content_hi", "") + " " + entry.get("content_te", "") + " " + entry["id"]
        ).lower()
        score = sum(1 for w in q.split() if len(w) > 3 and w in combined)
        if state:
            if "all" in entry["states"]:
                score += 1
            elif any(state in s for s in entry["states"]):
                score += 4
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_k]]
