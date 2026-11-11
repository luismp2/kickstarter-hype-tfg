import os, csv
import requests
import torch
import torch.nn as nn
import open_clip
from PIL import Image

CARPETA = "covers"
SALIDA = "estetica_progreso.csv"
PESOS = "sac+logos+ava1-l14-linearMSE.pth"
URL_PESOS = ("https://github.com/christophschuhmann/improved-aesthetic-predictor/raw/main/"
             "sac%2Blogos%2Bava1-l14-linearMSE.pth")

if not os.path.exists(PESOS):
    print("Descargando pesos del predictor estético...")
    r = requests.get(URL_PESOS)
    if r.status_code != 200 or len(r.content) < 100_000:
        raise SystemExit(
            f"No se pudieron descargar los pesos (código {r.status_code}).\n"
            "Descárgalos a mano desde github.com/christophschuhmann/improved-aesthetic-predictor\n"
            f"(archivo {PESOS}) y ponlos en esta misma carpeta.")
    with open(PESOS, "wb") as f:
        f.write(r.content)

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(768, 1024), nn.Dropout(0.2),
            nn.Linear(1024, 128), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.Dropout(0.1),
            nn.Linear(64, 16),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.layers(x)

dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
mlp = MLP()
mlp.load_state_dict(torch.load(PESOS, map_location="cpu"))
mlp.to(dispositivo).eval()

print("Cargando CLIP ViT-L/14 (la primera vez se descarga)...")
clip, _, preprocesar = open_clip.create_model_and_transforms(
    "ViT-L-14", pretrained="openai", force_quick_gelu=True)
clip.to(dispositivo).eval()

hechos = set()
if os.path.exists(SALIDA) and os.path.getsize(SALIDA) > 10:
    with open(SALIDA, encoding="utf-8-sig") as f:
        hechos = {fila["id"] for fila in csv.DictReader(f, delimiter=";")}
    print(f"Continuando: {len(hechos)} imágenes ya hechas")

archivos = [a for a in sorted(os.listdir(CARPETA))
            if os.path.splitext(a)[0].isdigit() and os.path.splitext(a)[0] not in hechos]

nuevo = not (os.path.exists(SALIDA) and os.path.getsize(SALIDA) > 10)
with open(SALIDA, "a" if not nuevo else "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["id", "estetica"], delimiter=";")
    if nuevo:
        w.writeheader()
    with torch.no_grad():
        for i, archivo in enumerate(archivos, 1):
            id_ = os.path.splitext(archivo)[0]
            try:
                img = preprocesar(Image.open(os.path.join(CARPETA, archivo)).convert("RGB"))
                emb = clip.encode_image(img.unsqueeze(0).to(dispositivo)).float()
                emb = emb / emb.norm(dim=-1, keepdim=True)
                nota = mlp(emb).item()
            except Exception as e:
                print("Error en", archivo, e)
                nota = None
            w.writerow({"id": id_, "estetica": nota})
            f.flush()
            if i % 50 == 0 or i == len(archivos):
                print(f"[{i}/{len(archivos)}] última nota: {nota}")

import pandas as pd
resultado = pd.read_csv(SALIDA, sep=";", encoding="utf-8-sig")
resultado.to_excel("imagen_estetica.xlsx", index=False)
os.remove(SALIDA)
print(f"Listo → imagen_estetica.xlsx ({resultado['estetica'].notna().sum()} imágenes puntuadas)")
