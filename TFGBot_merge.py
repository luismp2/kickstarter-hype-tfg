import os
import pandas as pd

LONG_TEXT = ["story_texto", "riesgos"]

SOURCES = [
    ("text_ai.xlsx", ["mention"]),
    ("text_ai_llm.xlsx", ["mentions_ai"]),
    ("imagen_opencv.xlsx", ["nitidez", "brillo", "contraste", "colorido"]),
    ("imagen_estetica.xlsx", ["estetica"]),
]

base = pd.read_csv("muestra_completa.csv", sep=";", encoding="utf-8-sig")
base = base.drop(columns=[c for c in LONG_TEXT if c in base.columns])
print(f"Base sample: {len(base)} projects, {base.shape[1]} columns")

for filename, columns in SOURCES:
    if not os.path.exists(filename):
        print(f"  (skipped, not found: {filename})")
        continue
    extra = pd.read_excel(filename)
    missing = [c for c in columns if c not in extra.columns]
    if missing:
        print(f"  WARNING: {filename} has no column(s) {missing}; skipped")
        continue
    extra = extra[["id"] + columns].drop_duplicates(subset="id", keep="last")
    base = base.merge(extra, on="id", how="left")
    print(f"  + {filename}: {', '.join(columns)}  "
          f"(filled for {base[columns[0]].notna().sum()} of {len(base)} projects)")

base.to_excel("muestra_final.xlsx", index=False)

print(f"\nmuestra_final.xlsx: {len(base)} projects, {base.shape[1]} columns")
if "estado" in base.columns:
    print(f"  Success rate: {(base['estado'] == 'successful').mean():.1%}")
for col, label in [("mention", "AI mention (script)"), ("mentions_ai", "AI mention (LLM)")]:
    if col in base.columns:
        print(f"  {label}: {base[col].mean():.1%}")
if {"mention", "mentions_ai"} <= set(base.columns):
    both = base[["mention", "mentions_ai"]].dropna()
    agree = (both["mention"] == both["mentions_ai"]).mean()
    llm_only = ((both["mentions_ai"] == 1) & (both["mention"] == 0)).sum()
    script_only = ((both["mention"] == 1) & (both["mentions_ai"] == 0)).sum()
    print(f"  Script and LLM agree on {agree:.1%} of projects")
    print(f"    LLM says AI, script doesn't: {llm_only}")
    print(f"    Script says AI, LLM doesn't: {script_only}")
