import re
import pandas as pd
from langdetect import detect, DetectorFactory

INPUT = "muestra_completa.csv"
OUTPUT = "text_ai.xlsx"

DetectorFactory.seed = 0

L = r"A-Za-zÀ-ÿ"
I = re.I

STRICT = [
    ("ai",                      rf"(?<![{L}.])(?:A\.I\.|AI)(?![{L}])", 0),
    ("artificial intelligence", r"\bartificial[\s-]+intelligence\b", I),
    ("inteligencia artificial", r"\bintelig[eê]ncia\s+artificial\b", I),
    ("intelligence artificielle", r"\bintelligence\s+artificielle\b", I),
    ("intelligenza artificiale", r"\bintelligenza\s+artificiale\b", I),
    ("künstliche intelligenz",  r"\bk(?:ü|ue)nstliche[nr]?\s+intelligenz\b", I),
    ("人工知能/人工智能",         r"人工知能|人工智能", 0),
]
FOREIGN_ABBR = [
    ("ia/ki",                   rf"(?<![{L}])(?:IA|KI)(?![{L}])", 0),
]

BROAD_EXTRA = [
    ("machine learning",        r"\bmachine[\s-]+learning\b", I),
    ("deep learning",           r"\bdeep[\s-]+learning\b", I),
    ("reinforcement learning",  r"\breinforcement[\s-]+learning\b", I),
    ("neural network",          r"\b(?:artificial\s+|deep\s+|convolutional\s+)?neural[\s-]+net(?:work)?s?\b", I),
    ("large language model",    r"\blarge[\s-]+language[\s-]+models?\b", I),
    ("llm",                     rf"(?<![{L}])LLMs?(?![{L}])", 0),
    ("language model",          r"\b(?:small\s+)?language[\s-]+models?\b", I),
    ("generative model/genai",  r"\bgen[\s-]?AI\b|\bgenerative[\s-]+(?:model|pre-?trained)s?\b", I),
    ("foundation model",        r"\bfoundation[\s-]+models?\b", I),
    ("multimodal model",        r"\bmulti-?modal[\s-]+(?:model|AI|LLM)s?\b", I),
    ("computer vision",         r"\bcomputer[\s-]+vision\b|\bmachine[\s-]+vision\b", I),
    ("natural language processing", r"\bnatural[\s-]+language[\s-]+(?:processing|understanding)\b", I),
    ("nlp",                     rf"(?<![{L}])NLP(?![{L}])(?!\s+practitioner)", 0),
    ("object/image recognition", r"\b(?:object|image|facial|face|gesture|pattern)[\s-]+(?:recognition|detection|classification)\b", I),
    ("speech recognition",      r"\b(?:speech|voice)[\s-]+recognition\b", I),
    ("predictive model/analytics", r"\bpredictive[\s-]+(?:model(?:l?ing)?s?|analytics|algorithms?)\b", I),
    ("trained model",           r"\b(?:pre-?)?trained[\s-]+(?:AI\s+|ML\s+)?models?\b", I),
    ("ml model/algorithm",      r"\b(?:ML|AI)[\s-]+(?:models?|algorithms?)\b", 0),
    ("chatbot",                 r"\bchat[\s-]?bots?\b", I),
    ("ai agent/agentic",        r"\bagentic\b|\bAI[\s-]+agents?\b", 0),
    ("conversational ai",       r"\bconversational\s+(?:AI|agents?|assistants?)\b", I),
    ("edge ai/tinyml",          r"\bedge[\s-]+AI\b|\bTinyML\b|\bon-?device\s+(?:AI|ML|inference|models?)\b", I),
    ("ai chip/npu/tpu",         rf"\bneural[\s-]+(?:processing[\s-]+unit|engine)s?\b|(?<![{L}])(?:NPU|TPU)s?(?![{L}])", 0),
    ("transformer model",       r"\btransformer[\s-]+(?:models?|architecture|networks?)\b", I),
    ("diffusion model",         r"\b(?:stable\s+)?diffusion[\s-]+models?\b|\bStable\s+Diffusion\b", I),
    ("chatgpt",                 r"\bChat-?GPT\b", I),
    ("gpt",                     rf"(?<![{L}])GPT(?:-?\d(?:\.\d)?o?)?(?![{L}])", 0),
    ("openai",                  r"\bOpenAI\b", I),
    ("anthropic",               r"\bAnthropic\b", I),
    ("deepseek",                r"\bDeepSeek\b", I),
    ("midjourney",              r"\bMidjourney\b", I),
    ("dall-e",                  r"\bDALL[\s·-]?E\b", I),
    ("tensorflow",              r"\bTensorFlow(?:\s+Lite)?\b", I),
    ("pytorch",                 r"\bPyTorch\b", I),
    ("hugging face",            r"\bHugging\s?Face\b", I),
    ("edge impulse",            r"\bEdge\s+Impulse\b", I),
    ("nvidia jetson",           r"\b(?:NVIDIA\s+)?Jetson\b", I),
    ("ollama",                  r"\bOllama\b", I),
    ("elevenlabs",              r"\bElevenLabs\b", I),
    ("gemini (ai)",             r"\b(?:Google\s+Gemini|Gemini\s+(?:AI|Pro|Nano|API|model))\b", I),
    ("claude (ai)",             r"\bClaude\s+(?:AI|API|Sonnet|Opus|Haiku)\b", I),
    ("llama (ai)",              r"\b(?:Meta\s+Llama|Llama\s?\d(?:\.\d)?)\b", I),
    ("mistral (ai)",            r"\bMistral\s+(?:AI|model|API)\b", I),
    ("copilot (ai)",            r"\b(?:GitHub|Microsoft)\s+Copilot\b", I),
    ("whisper (ai)",            r"\b(?:OpenAI\s+)?Whisper\s+(?:AI|model|API)\b|\bOpenAI\s+Whisper\b", I),
    ("grok (ai)",               r"\bGrok\s+(?:AI|\d)\b|\bxAI\b", I),
    ("perplexity (ai)",         r"\bPerplexity\s+AI\b", I),
]

compile_ = lambda lst: [(lab, re.compile(rx, fl)) for lab, rx, fl in lst]
STRICT_C, FOREIGN_C, BROAD_C = compile_(STRICT), compile_(FOREIGN_ABBR), compile_(BROAD_EXTRA)

NEG_BEFORE = re.compile(r"\b(?:no|not|without|zero|non|never|free\s+of|instead\s+of|unlike|nor)"
                        r"(?:[\s-]+(?:any|an|a|the|use\s+of|need\s+for))?[\s-]*$", I)
NEG_AFTER = re.compile(r"^[\s-]*(?:free|-free|not\s+required|not\s+needed)\b", I)
ILLUSTRATOR = re.compile(r"\b(?:EPS|SVG|PDF|PSD|PNG|DXF|Illustrator)\b|\bfiles?\b|^\s*/|/\s*$", I)

def language(text):
    if not isinstance(text, str) or len(text.split()) < 5:
        return None
    try:
        return detect(text[:3000])
    except Exception:
        return None

def find_mentions(text, patterns):
    if not isinstance(text, str) or not text:
        return []
    hits = []
    for label, rx in patterns:
        hits += [(m.start(), m.end(), label) for m in rx.finditer(text)]
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    kept, last_end = [], -1
    for s, e, lab in hits:
        if s >= last_end:
            kept.append((lab, s, e))
            last_end = e
    return kept

def classify(text, mentions):
    valid = []
    for lab, s, e in mentions:
        before, after = text[max(0, s - 30):s], text[e:e + 25]
        if lab == "ai" and (ILLUSTRATOR.search(text[max(0, s - 15):s]) or ILLUSTRATOR.search(after[:15])):
            continue
        if NEG_BEFORE.search(before) or NEG_AFTER.search(after):
            continue
        valid.append(lab)
    return valid

df = pd.read_csv(INPUT, sep=";", encoding="utf-8-sig")
rows = []
for _, p in df.iterrows():
    fields = [p.get("nombre"), p.get("blurb"), p.get("story_texto")]
    lang = language(p.get("story_texto")) or language(p.get("blurb"))
    strict_pats = STRICT_C + (FOREIGN_C if lang not in (None, "en") else [])
    broad_pats = strict_pats + BROAD_C
    strict_labels = {lab for lab, _ in strict_pats}

    found = []
    for text in fields:
        found += classify(text, find_mentions(text, broad_pats))

    rows.append({
        "id": p["id"],
        "mention": int(len(found) > 0),
        "ai_strict_count": len([lab for lab in found if lab in strict_labels]),
    })

out = pd.DataFrame(rows)
out.to_excel(OUTPUT, index=False)
print(len(out), "projects analysed")
print("mention = 1:", out["mention"].sum())
