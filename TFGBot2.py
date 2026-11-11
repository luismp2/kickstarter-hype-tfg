from curl_cffi import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import pandas as pd
import csv, os, time, random

ENTRADA = "muestra.csv"
SALIDA = "detalles.csv"
DESCARGAR_PORTADAS = True
CARPETA_PORTADAS = "covers"

QUERY = """query($slug: String!) {
  project(slug: $slug) {
    story risks launchedAt
    creator {
      backingsCount
      launchedProjects(first: 100) { totalCount nodes { launchedAt state } }
    }
  }
}"""

COLUMNAS = ["id", "blurb", "portada_url", "story_texto", "story_palabras",
            "story_imagenes", "story_videos", "riesgos",
            "creador_proyectos_previos", "creador_exitos_previos", "creador_es_repetidor",
            "creador_proyectos_total_hoy", "creador_backings_hoy", "error"]

sesion = requests.Session(impersonate="chrome")

def meta(soup, nombre):
    tag = soup.find("meta", attrs={"property": nombre}) or soup.find("meta", attrs={"name": nombre})
    return tag.get("content") if tag else None

def detalles(link):
    fila = {}
    r = sesion.get(link)
    if r.status_code != 200:
        return {"error": f"página {r.status_code}"}
    soup = BeautifulSoup(r.text, "html.parser")
    fila["blurb"] = meta(soup, "og:description")
    fila["portada_url"] = meta(soup, "twitter:image") or meta(soup, "og:image")
    csrf = meta(soup, "csrf-token")

    slug = urlparse(link).path.split("/projects/")[1].strip("/")
    time.sleep(random.uniform(1, 2))
    g = sesion.post("https://www.kickstarter.com/graph",
                    json={"query": QUERY, "variables": {"slug": slug}},
                    headers={"X-CSRF-Token": csrf or "", "Content-Type": "application/json"})
    proyecto = (g.json().get("data") or {}).get("project") if g.status_code == 200 else None
    if not proyecto:
        fila["error"] = f"graph {g.status_code}"
        return fila

    story = BeautifulSoup(proyecto.get("story") or "", "html.parser")
    texto = story.get_text(" ", strip=True)
    fila["story_texto"] = texto
    fila["story_palabras"] = len(texto.split())
    fila["story_imagenes"] = len(story.find_all("img"))
    fila["story_videos"] = len(story.find_all(["video", "iframe"]))
    fila["riesgos"] = BeautifulSoup(proyecto.get("risks") or "", "html.parser").get_text(" ", strip=True)

    creador = proyecto.get("creator") or {}
    lanzados = creador.get("launchedProjects") or {}
    nodos = lanzados.get("nodes") or []
    inicio = proyecto.get("launchedAt") or 0
    previos = [n for n in nodos if n.get("launchedAt") and n["launchedAt"] < inicio]
    fila["creador_proyectos_previos"] = len(previos)
    fila["creador_exitos_previos"] = sum(n.get("state") == "SUCCESSFUL" for n in previos)
    fila["creador_es_repetidor"] = int(len(previos) > 0)
    fila["creador_proyectos_total_hoy"] = lanzados.get("totalCount")
    fila["creador_backings_hoy"] = creador.get("backingsCount")
    return fila

def descargar_portada(id_, url):
    ruta = os.path.join(CARPETA_PORTADAS, f"{id_}.jpg")
    if not url or os.path.exists(ruta):
        return
    r = sesion.get(url)
    if r.status_code == 200:
        with open(ruta, "wb") as f:
            f.write(r.content)

muestra = pd.read_csv(ENTRADA, sep=";", encoding="utf-8-sig")
hechos = set()
if os.path.exists(SALIDA):
    hechos = set(pd.read_csv(SALIDA, sep=";", encoding="utf-8-sig")["id"])
    print(f"Continuando: {len(hechos)} proyectos ya hechos")
if DESCARGAR_PORTADAS:
    os.makedirs(CARPETA_PORTADAS, exist_ok=True)

nuevo = not os.path.exists(SALIDA)
with open(SALIDA, "a", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=COLUMNAS, delimiter=";")
    if nuevo:
        w.writeheader()
    pendientes = muestra[~muestra["id"].isin(hechos)]
    for i, (_, p) in enumerate(pendientes.iterrows(), 1):
        try:
            fila = detalles(p["link"])
        except Exception as e:
            fila = {"error": str(e)[:200]}
        fila["id"] = p["id"]
        w.writerow({c: fila.get(c) for c in COLUMNAS})
        f.flush()
        if DESCARGAR_PORTADAS and not fila.get("error"):
            try:
                descargar_portada(p["id"], fila.get("portada_url"))
            except Exception:
                pass
        estado = fila.get("error") or f"{fila.get('story_palabras', 0)} palabras"
        print(f"[{i}/{len(pendientes)}] {p['nombre'][:40]} → {estado}")
        time.sleep(random.uniform(2, 5))

det = pd.read_csv(SALIDA, sep=";", encoding="utf-8-sig")
completa = muestra.merge(det, on="id", how="left")
completa.to_csv("muestra_completa.csv", sep=";", index=False, encoding="utf-8-sig")
print(f"\nListo: muestra_completa.csv ({len(completa)} proyectos, "
      f"{det['error'].notna().sum()} con error)")
