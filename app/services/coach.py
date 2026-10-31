import json
import re
import unicodedata

import httpx

from ..config import Settings

SYSTEM = """You are FinCoach, an educational personal-finance tutor for beginners in India
(students, first-job professionals, gig workers).

Rules:
- Answer the actual question. Do not give a generic canned reply based on a single keyword.
- Reply in the same language and script as the user (Hindi Devanagari, Hinglish in Latin script, or English).
- Keep the answer beginner-friendly and concise (about 120-180 words).
- You may explain concepts: budgeting, emergency funds, SIPs as a method, compounding, inflation, risk, diversification.
- You must NOT give personalized investment advice, pick a stock, or say how much to invest in a specific security.
- You must NOT claim to be a SEBI-registered adviser or guarantee returns.
- If asked to recommend a stock or asset, refuse and explain how to learn instead.
- Label numbers as examples or hypotheticals.
"""

HINGLISH_HINTS = {
    "kya", "hai", "kaise", "kitna", "paisa", "paise", "kharcha", "kamai",
    "bachat", "mahine", "sip", "budget", "mujhe", "mera", "meri", "karna",
    "chahiye", "nahi", "kyun", "kyunki", "samjhao", "batao", "please",
}


def detect_language(text: str) -> str:
    if any("DEVANAGARI" in unicodedata.name(ch, "") for ch in text if ch.isalpha()):
        return "hi"
    tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
    if len(tokens & HINGLISH_HINTS) >= 2:
        return "hinglish"
    return "en"


def _topics(question: str) -> list[str]:
    q = question.lower()
    mapping = [
        ("emergency", ["emergency", "aapat", "aapatkalin", "rainy day", "3 month", "six month"]),
        ("budget", ["budget", "kharcha", "expense", "spending", "bachat kaise", "save money", "bache"]),
        ("sip", ["sip", "mutual fund", "compound", "monthly invest", "recurring"]),
        ("stock_edu", ["stock", "share", "equity", "nse", "bse", "demat", "angel", "groww"]),
        ("gold", ["gold", "sona", "silver", "chandi"]),
        ("bitcoin", ["bitcoin", "btc", "crypto"]),
        ("gig", ["gig", "freelance", "irregular", "variable income", "udhari"]),
        ("advice_trap", ["which stock", "best stock", "buy now", "konsa stock", "kitna invest karun in"]),
    ]
    found = [name for name, keys in mapping if any(k in q for k in keys)]
    return found or ["general"]


def fallback_answer(question: str) -> str:
    lang = detect_language(question)
    topics = _topics(question)
    q_short = question.strip()[:180]

    if "advice_trap" in topics:
        copies = {
            "hi": (
                f"आपने पूछा: “{q_short}”. FinCoach किसी शेयर या संपत्ति को खरीदने की सलाह नहीं देता। "
                "शिक्षण के लिए याद रखें: शेयर की कीमतें घट-बढ़ सकती हैं, पुराना लाभ भविष्य की गारंटी नहीं है, "
                "और कुल लाभ खरीद के बाद से होता है जबकि दैनिक बदलाव पिछली बंद कीमत से तुलना है। "
                "सीखने का रास्ता: अपनी आय-खर्च समझें, आपातकालीन निधि, फिर जोखिम और विविधता के सिद्धांत पढ़ें।"
            ),
            "hinglish": (
                f"Aapne poocha: “{q_short}”. FinCoach kisi specific stock ya asset ko buy karne ki salah nahi deta. "
                "Seekhne ke liye: prices gir-chad sakte hain, past return guarantee nahi hai, overall P&L purchase se hota hai "
                "aur daily move previous close se. Pehle income-expense aur emergency buffer samjho, phir risk concepts."
            ),
            "en": (
                f"You asked: “{q_short}”. FinCoach does not recommend a specific stock or tell you how much to buy. "
                "Educational points: prices can fall, past returns are not a promise, overall P&L is since purchase, "
                "and daily movement is versus the previous close. Start with cash flow and an emergency buffer, then learn risk."
            ),
        }
        return copies[lang]

    blocks = {
        "emergency": {
            "en": "An emergency fund is cash set aside for surprise bills or a pause in income. Many learners aim for a few months of essential expenses in a safe, easy-to-access place. The right size depends on how irregular your income is — gig work often needs a larger buffer. This is a planning idea, not a product pick.",
            "hi": "आपातकालीन निधि अप्रत्याशित खर्च या आय रुकने के लिए अलग रखा गया पैसा है। कई लोग कुछ महीनों के जरूरी खर्च के बराबर राशि सोचते हैं। गिग काम में आय अस्थिर हो तो बफर बड़ा रखने की जरूरत हो सकती है। यह योजना का विचार है, कोई उत्पाद सिफारिश नहीं।",
            "hinglish": "Emergency fund surprise bill ya income rukne ke liye alag rakha hua cash hai. Kai log kuch mahine ke zaroori kharch jitna sochte hain. Gig income uneven ho to buffer bada ho sakta hai. Yeh planning idea hai, koi product pick nahi.",
        },
        "budget": {
            "en": "A flexible budget starts with monthly income, lists must-pay expenses, then leftover for goals and savings. If income varies, budget from a conservative month and treat extra as optional. Track categories you can actually edit. Leftover is an estimate until real bills arrive.",
            "hi": "लचीला बजट मासिक आय से शुरू होता है, जरूरी खर्च लिखता है, फिर बची राशि लक्ष्य और बचत के लिए देखता है। आय बदलती हो तो कम वाले महीने से योजना बनाएं। श्रेणियाँ वही रखें जिन्हें आप बदल सकें। बचा पैसा अनुमान है जब तक वास्तविक बिल न आएं।",
            "hinglish": "Flexible budget monthly income se start hota hai, zaroori kharch list karta hai, phir leftover goals/savings ke liye. Income variable ho to conservative month se plan karo. Categories woh rakho jo aap edit kar sako. Leftover estimate hai jab tak real bills na aayein.",
        },
        "sip": {
            "en": "A SIP (systematic investment plan) is a habit of investing a chosen amount at a regular interval. Compounding illustrations assume a return; real results can be lower, zero, or negative. Always compare a zero-return case with a hypothetical return. This app’s numbers are classroom math, not a promise.",
            "hi": "SIP नियमित अंतराल पर चुनी हुई राशि लगाने की आदत है। चक्रवृद्धि के चित्र एक रिटर्न मानते हैं; असल नतीजा कम, शून्य या नकारात्मक हो सकता है। शून्य रिटर्न वाले दृश्य की तुलना जरूर करें। ऐप के आंकड़े कक्षा का गणित हैं, वादा नहीं।",
            "hinglish": "SIP regular interval par chosen amount lagane ki aadat hai. Compounding picture ek return assume karti hai; asal result kam, zero, ya negative ho sakta hai. Zero-return scenario se compare karo. App ke numbers classroom math hain, promise nahi.",
        },
        "stock_edu": {
            "en": "Shares are units of ownership in a company. Price, quantity, average buy price, latest price, current value, overall P&L (since purchase), and daily move (versus previous close) are different numbers. Brokers can fail to return data; never invent a price. FinCoach does not rank or pick stocks.",
            "hi": "शेयर कंपनी में स्वामित्व की इकाई हैं। कीमत, मात्रा, औसत खरीद, ताजा कीमत, वर्तमान मूल्य, कुल लाभ-हानि (खरीद से) और दैनिक बदलाव (पिछली बंद से) अलग आंकड़े हैं। ब्रोकर डेटा न दे तो कीमत गढ़ना गलत है। FinCoach शेयर नहीं चुनता।",
            "hinglish": "Share company me ownership ki unit hai. Price, quantity, average buy, latest price, current value, overall P&L (purchase se) aur daily move (previous close se) alag numbers hain. Broker data na de to price gadhna galat hai. FinCoach stock nahi chunta.",
        },
        "gold": {
            "en": "Gold and silver are commodities. Prices move with global markets, currency, and demand. They can lose purchasing power in some periods and have storage or product costs. Live quotes may be unavailable; the app will say so rather than guess. This is not a buy/sell call.",
            "hi": "सोना और चांदी वस्तुएं हैं। कीमत वैश्विक बाजार, मुद्रा और मांग से चलती है। कुछ अवधियों में मूल्य घट सकता है। लाइव भाव उपलब्ध न हों तो ऐप अनुमान नहीं लगाएगा। यह खरीद/बिक्री की सलाह नहीं है।",
            "hinglish": "Sona aur chandi commodity hain. Price global market, currency aur demand se chalti hai. Kuch periods me value gir sakti hai. Live quote na ho to app guess nahi karega. Yeh buy/sell call nahi hai.",
        },
        "bitcoin": {
            "en": "Bitcoin is a volatile digital asset. It can swing sharply in short periods, has no cash flow like a business, and is not a bank deposit. Quotes here, when shown, come from CoinGecko and can lag or fail. Never treat a quote as a recommendation.",
            "hi": "बिटकॉइन अस्थिर डिजिटल संपत्ति है। यह जल्दी तेज उतार-चढ़ाव दिखा सकता है, व्यवसाय जैसी नकदी प्रवाह नहीं देता, और बैंक जमा नहीं है। भाव CoinGecko से आ सकते हैं और रुक भी सकते हैं। भाव सिफारिश नहीं है।",
            "hinglish": "Bitcoin volatile digital asset hai. Short time me tez swing ho sakta hai, business jaisa cash flow nahi, bank deposit nahi. Quote CoinGecko se aa sakta hai aur fail bhi. Quote recommendation nahi hai.",
        },
        "gig": {
            "en": "Irregular income is easier to handle if you separate essential expenses from optional ones and save extra in strong months. A percentage rule that works on a salary month may fail on a slow month. Plan with a floor income, then revisit categories.",
            "hi": "अनियमित आय में जरूरी और वैकल्पिक खर्च अलग रखें और अच्छे महीनों में अधिक बचाएं। वेतन वाले महीने का प्रतिशत धीमे महीने में फेल हो सकता है। न्यूनतम आय से योजना बनाएं, फिर श्रेणियाँ दोहराएं।",
            "hinglish": "Irregular income me zaroori aur optional kharch alag rakho, acche mahine extra bachaao. Salary month ka percentage slow month me fail ho sakta hai. Floor income se plan karo, phir categories revisit karo.",
        },
        "general": {
            "en": "FinCoach can help you map income, expenses, a flexible budget, and hypothetical savings math. It cannot tell you what to buy. If you add more detail — income type, a goal, or a concept to unpack — the explanation can be more specific while staying educational.",
            "hi": "FinCoach आय-खर्च, लचीला बजट और काल्पनिक बचत गणित समझने में मदद करता है। यह नहीं बताता कि क्या खरीदें। आय का प्रकार, लक्ष्य या अवधारणा लिखें तो व्याख्या और सटीक हो सकती है, फिर भी केवल शिक्षा।",
            "hinglish": "FinCoach income-expense, flexible budget aur hypothetical savings math samjhane me madad karta hai. Kya khareedna hai yeh nahi batata. Income type, goal, ya concept likho to explanation zyada specific ho sakti hai, phir bhi sirf education.",
        },
    }

    chosen = [t for t in topics if t in blocks][:2] or ["general"]
    intro = {
        "en": f"You asked: “{q_short}”.",
        "hi": f"आपने पूछा: “{q_short}”.",
        "hinglish": f"Aapne poocha: “{q_short}”.",
    }[lang]
    body = " ".join(blocks[t][lang] for t in chosen)
    return f"{intro} {body}"


def ask_openai(settings: Settings, question: str) -> tuple[str, str, bool]:
    """Returns answer, source label, used_fallback."""
    if not settings.openai_configured:
        return fallback_answer(question), "limited_demo_fallback", True

    payload = {
        "model": settings.openai_model,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ],
    }
    try:
        with httpx.Client(timeout=40.0) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": "Bearer " + settings.openai_api_key,
                    "Content-Type": "application/json",
                },
                content=json.dumps(payload),
            )
        if response.status_code >= 400:
            return (
                fallback_answer(question) + " (OpenAI request failed; this is the limited demo fallback.)",
                "limited_demo_fallback",
                True,
            )
        data = response.json()
        text = data["choices"][0]["message"]["content"].strip()
        return text, "openai", False
    except (httpx.HTTPError, KeyError, IndexError, TypeError):
        return (
            fallback_answer(question) + " (OpenAI unavailable; this is the limited demo fallback.)",
            "limited_demo_fallback",
            True,
        )
