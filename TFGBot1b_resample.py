import pandas as pd
import shutil, os

files = {
    "<25%": "estrato_menos25.csv",
    "25-50%": "estrato_25-50.csv",
    "50-75%": "estrato_50-75.csv",
    "75-100%": "estrato_75-100.csv",
    ">100%": "estrato_mas100.csv",
}

parts = []
for name, f in files.items():
    d = pd.read_csv(f, sep=";", encoding="utf-8-sig")
    d["estrato"] = name
    parts.append(d)
pop = pd.concat(parts).drop_duplicates(subset="id")
print("All projects in the strata files:", len(pop))

print(pop.groupby("estrato")["lanzamiento"].min())

cutoff = pop.groupby("estrato")["lanzamiento"].min().max()
print("Window starts:", cutoff)

pop = pop[pop["lanzamiento"] >= cutoff]
print("Projects in the window:", len(pop))
print(pop["estrato"].value_counts())

n = min(2000, len(pop))
sample = pop.sample(n=n, random_state=42)
print("Sample size:", len(sample))

if os.path.exists("muestra.csv"):
    old = pd.read_csv("muestra.csv", sep=";", encoding="utf-8-sig")
    print("Also in the old sample:", sample["id"].isin(old["id"]).sum())
if os.path.exists("detalles.csv"):
    scraped = pd.read_csv("detalles.csv", sep=";", encoding="utf-8-sig")
    print("Already scraped by Bot 2:", sample["id"].isin(scraped["id"]).sum())
    print("New projects Bot 2 will scrape:", (~sample["id"].isin(scraped["id"])).sum())

if os.path.exists("muestra.csv"):
    shutil.copy("muestra.csv", "muestra_old.csv")
sample.to_csv("muestra.csv", sep=";", index=False, encoding="utf-8-sig")
print("Saved muestra.csv (old one kept as muestra_old.csv)")
