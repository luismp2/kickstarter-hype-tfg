import cv2, os
import numpy as np
import pandas as pd

CARPETA = "covers"

filas = []
for archivo in sorted(os.listdir(CARPETA)):
    nombre, _ = os.path.splitext(archivo)
    if not nombre.isdigit():
        continue
    img = cv2.imread(os.path.join(CARPETA, archivo))
    if img is None:
        print("No se pudo leer", archivo)
        continue
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    b, g, r = cv2.split(img.astype("float"))
    rg = np.abs(r - g)
    yb = np.abs(0.5 * (r + g) - b)
    filas.append({
        "id": int(nombre),
        "nitidez": cv2.Laplacian(gris, cv2.CV_64F).var(),
        "brillo": gris.mean(),
        "contraste": gris.std(),
        "colorido": np.sqrt(rg.std() ** 2 + yb.std() ** 2)
                    + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2),
    })

pd.DataFrame(filas).to_excel("imagen_opencv.xlsx", index=False)
print(len(filas), "imágenes procesadas → imagen_opencv.xlsx")
