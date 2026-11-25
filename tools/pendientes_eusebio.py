#!/usr/bin/env python3
"""Lista los textos que escribe Eusebio y aún faltan (marca PENDIENTE-EUSEBIO) en las plantillas y en el HTML generado (ML-324).
Sale con 1 si queda alguno: ejecútalo antes de publicar. Solo biblioteca estándar.

Uso:  python3 tools/pendientes_eusebio.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA = "PENDIENTE-EUSEBIO"
CARPETAS = ("plantillas",)   # el HTML generado se busca por sufijo en la raíz y en sus carpetas de idioma, no en tools/ ni docs/
EXCLUIDOS = {".git", "tools", "docs", "plantillas", "node_modules"}


def buscar(raiz: Path = RAIZ) -> list[str]:
    """«archivo:línea» de cada marca PENDIENTE-EUSEBIO en las plantillas (.pagina, .tpl, .txt) y en los .html publicados."""
    hallazgos = []
    candidatos = [p for c in CARPETAS for p in (raiz / c).rglob("*") if p.is_file() and p.suffix in (".pagina", ".tpl", ".txt")]
    candidatos += [p for p in raiz.rglob("*.html") if not EXCLUIDOS & set(p.relative_to(raiz).parts)]
    for ruta in sorted(candidatos):
        for n, linea in enumerate(ruta.read_text(encoding="utf-8").split("\n"), 1):
            if MARCA in linea:
                hallazgos.append(f"{ruta.relative_to(raiz).as_posix()}:{n}")
    return hallazgos


if __name__ == "__main__":
    restos = buscar()
    for r in restos:
        print("pendiente:", r)
    print(f"{len(restos)} marcas {MARCA}" if restos else "sin pendientes de Eusebio")
    sys.exit(1 if restos else 0)
