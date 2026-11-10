#!/usr/bin/env python3
"""Pone en cada <lastmod> de sitemap.xml la fecha del último commit que tocó el archivo de su <loc>.

Solo cambia los valores de <lastmod>; el resto del archivo queda tal cual y, si no hay cambios, no se reescribe.
Solo usa la biblioteca estándar y necesita el historial completo de git (no un clon superficial).

Uso:  python3 tools/actualizar_sitemap.py [raíz]      (por defecto, la raíz del repositorio)
"""
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

BLOQUE = re.compile(r"<url>.*?</url>", re.S)
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
LASTMOD = re.compile(r"(<lastmod>)([^<]*)(</lastmod>)")


def archivo_de(url):
    """Ruta relativa del archivo que sirve esa URL (https://manalab.es/es/ -> es/index.html)."""
    ruta = urlparse(url).path.lstrip("/")
    if ruta == "" or ruta.endswith("/"):
        ruta += "index.html"
    return ruta


def ultima_fecha(raiz, archivo):
    """Fecha (AAAA-MM-DD) del último commit que tocó el archivo, o None si no hay ninguno."""
    r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", archivo], cwd=raiz, capture_output=True, text=True)
    fecha = r.stdout.strip()
    return fecha if r.returncode == 0 and fecha else None


def actualizar(texto, raiz):
    """Devuelve (texto nuevo, [(url, antes, después)]) con los <lastmod> puestos al día."""
    cambios = []

    def por_bloque(m):
        bloque = m.group(0)
        loc = LOC.search(bloque)
        if not loc or not LASTMOD.search(bloque):
            return bloque
        fecha = ultima_fecha(raiz, archivo_de(loc.group(1)))
        if not fecha:
            return bloque
        viejo = LASTMOD.search(bloque).group(2)
        if viejo != fecha:
            cambios.append((loc.group(1), viejo, fecha))
        return LASTMOD.sub(lambda n: n.group(1) + fecha + n.group(3), bloque, count=1)

    return BLOQUE.sub(por_bloque, texto), cambios


def main(argv):
    raiz = Path(argv[1]).resolve() if len(argv) > 1 else Path(__file__).resolve().parent.parent
    ruta = raiz / "sitemap.xml"
    texto = ruta.read_text(encoding="utf-8")
    nuevo, cambios = actualizar(texto, raiz)
    if nuevo == texto:
        print("sitemap.xml ya estaba al día")
        return 0
    ruta.write_text(nuevo, encoding="utf-8")
    for url, antes, despues in cambios:
        print(f"{url}: {antes} -> {despues}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
