from curl_cffi import requests
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from datetime import datetime
import pandas as pd
import numpy as np
import os, time, random

TAMANO_MUESTRA = 2000
SEMILLA = 42
MAX_PAGINAS = 200

ESTRATOS = {
    "<25%":    {"N": 37390, "url": "https://www.kickstarter.com/discover/categories/technology?sort=newest&agg_fields=state&raised_max=25&category_id%5B%5D=16&state%5B%5D=canceled&state%5B%5D=failed&state%5B%5D=successful"},
    "25-50%":  {"N": 2779,  "url": "https://www.kickstarter.com/discover/categories/technology?sort=newest&agg_fields=state&raised_min=25&raised_max=50&category_id%5B%5D=16&state%5B%5D=canceled&state%5B%5D=failed&state%5B%5D=successful"},
    "50-75%":  {"N": 1118,  "url": "https://www.kickstarter.com/discover/categories/technology?sort=newest&agg_fields=state&raised_min=50&raised_max=75&category_id%5B%5D=16&state%5B%5D=canceled&state%5B%5D=failed&state%5B%5D=successful"},
    "75-100%": {"N": 410,   "url": "https://www.kickstarter.com/discover/categories/technology?sort=newest&agg_fields=state&raised_min=75&raised_max=100&category_id%5B%5D=16&state%5B%5D=canceled&state%5B%5D=failed&state%5B%5D=successful"},
    ">100%":   {"N": 15815, "url": "https://www.kickstarter.com/discover/categories/technology?sort=newest&agg_fields=state&raised_min=100&category_id%5B%5D=16&state%5B%5D=canceled&state%5B%5D=failed&state%5B%5D=successful"},
}

def url_pagina(base, pagina):
    partes = urlparse(base)
    params = [(k, v) for k, v in parse_qsl(partes.query) if k not in ("format", "page")]
    params += [("format", "json"), ("page", str(pagina))]
    return urlunparse(partes._replace(path="/discover/advanced", query=urlencode(params)))

def fecha(ts):
    return datetime.fromtimestamp(ts).date().isoformat() if ts else None

def descargar_estrato(nombre, base):
    archivo = f"estrato_{nombre.replace('%', '').replace('<', 'menos').replace('>', 'mas')}.csv"
    if os.path.exists(archivo):
        print(f"[{nombre}] ya descargado, leyendo {archivo}")
        return pd.read_csv(archivo, sep=";", encoding="utf-8-sig")

    filas = []
    for pagina in range(1, MAX_PAGINAS + 1):
        r = requests.get(url_pagina(base, pagina), impersonate="chrome",
                         headers={"Accept": "application/json"})
        if r.status_code != 200:
            print(f"[{nombre}] página {pagina} falló con código {r.status_code}. Me paro aquí.")
            break
        proyectos = r.json().get("projects", [])
        if not proyectos:
            print(f"[{nombre}] página {pagina} vacía: fin del listado")
            break
        for p in proyectos:
            filas.append({
                "id": p.get("id"),
                "nombre": p.get("name"),
                "link": p.get("urls", {}).get("web", {}).get("project"),
                "subcategoria": p.get("category", {}).get("name"),
                "pais": p.get("country"),
                "moneda": p.get("currency"),
                "objetivo": p.get("goal"),
                "recaudado": p.get("pledged"),
                "recaudado_usd": p.get("usd_pledged"),
                "backers": p.get("backers_count"),
                "estado": p.get("state"),
                "lanzamiento": fecha(p.get("launched_at")),
                "fin": fecha(p.get("deadline")),
                "staff_pick": p.get("staff_pick"),
            })
        print(f"[{nombre}] página {pagina} OK ({len(filas)} proyectos)")
        time.sleep(random.uniform(2, 5))

    df = pd.DataFrame(filas).drop_duplicates(subset="id")
    df.to_csv(archivo, sep=";", index=False, encoding="utf-8-sig")
    print(f"[{nombre}] {len(df)} proyectos únicos guardados en {archivo}")
    return df

nombres = list(ESTRATOS)
N_h = [ESTRATOS[e]["N"] for e in nombres]
rng = np.random.default_rng(SEMILLA)
n_h = dict(zip(nombres, rng.multivariate_hypergeometric(N_h, TAMANO_MUESTRA)))
print("Reparto de la muestra:", n_h)

datos = {e: descargar_estrato(e, ESTRATOS[e]["url"]) for e in nombres}

todos = pd.concat([d.assign(estrato=e) for e, d in datos.items()])
repetidos = todos[todos.duplicated(subset="id", keep=False)]
if len(repetidos):
    print(f"\nAVISO: {repetidos['id'].nunique()} proyectos aparecen en más de un estrato "
          f"(guardados en repetidos.csv). Se quedan solo en el primer estrato.")
    repetidos.to_csv("repetidos.csv", sep=";", index=False, encoding="utf-8-sig")
    vistos = set()
    for e in nombres:
        datos[e] = datos[e][~datos[e]["id"].isin(vistos)]
        vistos |= set(datos[e]["id"])
else:
    print("\nSin proyectos repetidos entre estratos.")

muestras = []
for e in nombres:
    df = datos[e]
    n = int(n_h[e])
    if n > len(df):
        print(f"AVISO [{e}]: tocan {n} pero solo hay {len(df)} accesibles. Se cogen todos.")
        n = len(df)
    m = df.sample(n=n, random_state=SEMILLA).copy()
    m["estrato"] = e
    m["N_estrato"] = ESTRATOS[e]["N"]
    m["accesibles_estrato"] = len(df)
    muestras.append(m)

muestra = pd.concat(muestras, ignore_index=True)
muestra.to_csv("muestra.csv", sep=";", index=False, encoding="utf-8-sig")
print(f"\nMuestra final: {len(muestra)} proyectos guardados en muestra.csv")
print(muestra["estrato"].value_counts())
