import json, os, csv, time, sys
import pandas as pd
import ollama

TEST = None
MODEL = "gemma3:4b"
MAX_CONTEXT = 131072

def context_size(prompt):
    needed = len(prompt) // 3 + 1024
    size = 4096
    while size < needed and size < MAX_CONTEXT:
        size *= 2
    return min(size, MAX_CONTEXT)

INPUT = "muestra_completa.csv"
PROGRESS = "ai_llm_progress.csv"
OUTPUT = "text_ai_llm.xlsx"

PROMPT = """You are coding Kickstarter technology campaigns for an academic study on artificial intelligence (AI).
Read the campaign text below and decide whether it says that the PRODUCT uses or includes AI.
AI includes machine learning, deep learning, neural networks, large language models (e.g. GPT),
computer vision and similar techniques, in any language.

- mentions_ai: 1 if the text says the product uses or includes AI, else 0.
  Use 0 if AI is only mentioned to say the product does NOT use it, or in a way unrelated to the product.
- evidence: a short quote (max 25 words) from the text that supports your decision,
  or an empty string if mentions_ai is 0 and there is nothing relevant.

CAMPAIGN TITLE: {title}
BLURB: {blurb}
STORY:
{story}"""

SCHEMA = {
    "type": "object",
    "properties": {
        "mentions_ai": {"type": "integer", "enum": [0, 1]},
        "evidence": {"type": "string"},
    },
    "required": ["mentions_ai", "evidence"],
}

SCHEMA_FALLBACK = {
    "type": "object",
    "properties": {"mentions_ai": {"type": "integer", "enum": [0, 1]}},
    "required": ["mentions_ai"],
}

FIELDS = ["id", "mentions_ai", "evidence", "attempt", "story_chars", "too_long", "model", "seconds", "error"]

def classify(prompt):
    base = {"temperature": 0, "seed": 42, "num_ctx": context_size(prompt)}
    try:
        r = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}],
                        format=SCHEMA, options={**base, "num_predict": 300})
        return json.loads(r.message.content), 1
    except Exception:
        r = ollama.chat(model=MODEL, messages=[{"role": "user", "content": prompt}],
                        format=SCHEMA_FALLBACK, options={**base, "num_predict": 30})
        return json.loads(r.message.content), 2

try:
    installed = [m.model for m in ollama.list().models]
except Exception:
    sys.exit("Cannot connect to Ollama. Open it (its icon should appear next to the clock) and run the script again.")
if not any(m == MODEL or m.startswith(MODEL + ":") for m in installed):
    sys.exit(f"Model {MODEL} is not downloaded. Run:  ollama pull {MODEL}")

def clean(x):
    return x if isinstance(x, str) else ""

df = pd.read_csv(INPUT, sep=";", encoding="utf-8-sig", dtype={"id": str})

done = set()
exists = os.path.exists(PROGRESS) and os.path.getsize(PROGRESS) > 10
if exists:
    previous = pd.read_csv(PROGRESS, sep=";", encoding="utf-8-sig", dtype={"id": str})
    done = set(previous.loc[previous["error"].isna(), "id"])
    print(f"Resuming: {len(done)} projects already done")
    if list(previous.columns) != FIELDS:
        if "attempt" not in previous.columns:
            previous["attempt"] = previous["error"].isna().map({True: 1, False: None})
        previous.reindex(columns=FIELDS).to_csv(PROGRESS, sep=";", index=False, encoding="utf-8-sig")

pending = df[~df["id"].isin(done)]
batch = pending.head(TEST) if TEST else pending
print(f"Processing {len(batch)} of {len(pending)} pending projects with {MODEL}"
      + (" (test mode)" if TEST else ""))
print("The first project takes longer because the model is loaded into memory.\n")

times = []
consecutive_errors = 0
with open(PROGRESS, "a" if exists else "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, delimiter=";")
    if not exists:
        w.writeheader()
    for i, (_, p) in enumerate(batch.iterrows(), 1):
        story = clean(p.get("story_texto"))
        prompt = PROMPT.format(title=clean(p.get("nombre")), blurb=clean(p.get("blurb")),
                               story=story or "(no story text available)")
        start = time.time()
        try:
            row, attempt = classify(prompt)
            row["model"], row["attempt"] = MODEL, attempt
            consecutive_errors = 0
        except Exception as e:
            row = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
            consecutive_errors += 1
        seconds = round(time.time() - start, 1)
        row.update({"id": p["id"], "seconds": seconds, "story_chars": len(story),
                    "too_long": int(len(prompt) // 3 + 1024 > MAX_CONTEXT)})
        if not row.get("error"):
            times.append(seconds)
        w.writerow({c: row.get(c) for c in FIELDS})
        f.flush()
        print(f"[{i}/{len(batch)}] {str(p.get('nombre'))[:40]}: mentions_ai = {row.get('mentions_ai')}  ({seconds} s)"
              + ("  [fallback without evidence]" if row.get("attempt") == 2 else "")
              + (f"  ERROR {row['error']}" if row.get("error") else ""))
        if consecutive_errors >= 5:
            print("\n5 errors in a row: stopping.")
            break

if len(times) > 1:
    avg = sum(times[1:]) / len(times[1:])
    remaining = len(pending) - len(batch)
    print(f"\nAverage: {avg:.1f} s per project. The remaining {remaining} would take "
          f"about {remaining * avg / 3600:.1f} hours.")

result = (pd.read_csv(PROGRESS, sep=";", encoding="utf-8-sig", dtype={"id": str})
          .drop_duplicates(subset="id", keep="last"))
result["id"] = result["id"].astype("int64")
result = result.sort_values("id")
result.to_excel(OUTPUT, index=False)
ok = result["error"].isna()
print(f"{OUTPUT} updated: {ok.sum()} of {len(df)} projects done"
      + (f", {(~ok).sum()} with errors (retried on the next run)" if (~ok).any() else ""))
done_ok = result.loc[ok, "mentions_ai"]
print(f"Mentions AI so far: {int(done_ok.sum())} of {len(done_ok)} ({done_ok.mean():.1%})")
if ok.sum() >= len(df):
    os.remove(PROGRESS)
    print("Finished.")
