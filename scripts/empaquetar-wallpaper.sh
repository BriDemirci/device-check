#!/usr/bin/env bash
# Copia core.js dentro del wallpaper (Wallpaper Engine y Lively importan solo esa carpeta)
# y arma dist/device-check-wallpaper.zip para subir como release.
set -euo pipefail
cd "$(dirname "$0")/.."
cp docs/core.js docs/wallpaper/core.js
mkdir -p dist
rm -f dist/device-check-wallpaper.zip
python3 - <<'PY'
import zipfile, pathlib
origen = pathlib.Path("docs/wallpaper")
with zipfile.ZipFile("dist/device-check-wallpaper.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(origen.rglob("*")):
        # estilos.jpg es solo para el README
        if f.is_file() and f.name != "estilos.jpg":
            z.write(f, f"device-check-wallpaper/{f.relative_to(origen)}")
print("dist/device-check-wallpaper.zip listo")
PY
