import os, shutil
from collections import Counter
from PIL import Image, features

CARPETA = "covers"
COPIA = "covers_original"

def formato(ruta):
    with open(ruta, "rb") as f:
        cab = f.read(32)
    if cab[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if cab[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if cab[:4] == b"RIFF" and cab[8:12] == b"WEBP":
        return "webp"
    if cab[4:8] == b"ftyp" and cab[8:12] in (b"avif", b"avis", b"mif1", b"msf1"):
        return "avif"
    if cab.lstrip()[:1] == b"<":
        return "html"
    if len(cab) == 0:
        return "vacio"
    return "desconocido"

archivos = [a for a in sorted(os.listdir(CARPETA)) if os.path.splitext(a)[0].isdigit()]
formatos = {a: formato(os.path.join(CARPETA, a)) for a in archivos}
print("Formatos encontrados:", dict(Counter(formatos.values())))

if "avif" in formatos.values() and not features.check("avif"):
    raise SystemExit("Tu versión de Pillow no lee AVIF. Ejecuta:  pip install --upgrade pillow\n"
                     "y vuelve a lanzar este script.")

os.makedirs(COPIA, exist_ok=True)
convertidas, fallidas = 0, []
for archivo, fmt in formatos.items():
    if fmt == "jpeg":
        continue
    ruta = os.path.join(CARPETA, archivo)
    if fmt in ("html", "vacio", "desconocido"):
        fallidas.append((archivo, fmt))
        continue
    try:
        shutil.copy2(ruta, os.path.join(COPIA, archivo))
        with Image.open(ruta) as img:
            img.convert("RGB").save(ruta, "JPEG", quality=95)
        convertidas += 1
    except Exception as e:
        fallidas.append((archivo, str(e)[:80]))

print(f"Convertidas a JPEG: {convertidas}")
if fallidas:
    print(f"No convertibles: {len(fallidas)} (ejemplos: {fallidas[:5]})")
print("Formatos ahora:", dict(Counter(formato(os.path.join(CARPETA, a)) for a in archivos)))
