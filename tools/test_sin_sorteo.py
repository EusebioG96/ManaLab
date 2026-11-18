#!/usr/bin/env python3
"""ML-310: el sorteo ya terminó y su página se quitó de la web. Falla si alguna página generada, el sitemap o robots.txt
vuelven a enlazar /sorteo/ o /es/sorteo/ (o si reaparece la carpeta sorteo/). Sin red.

Uso:  python3 -m pytest -q tools/test_sin_sorteo.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# /sorteo seguido de barra o de fin de palabra; no casa con /sorteos ni con textos como «sorteo» sin barra
ENLACE_SORTEO = re.compile(r"/sorteo\b")
FICHEROS_PUBLICADOS = ["sitemap.xml", "robots.txt"]


def _paginas_generadas():
    return [p for p in RAIZ.rglob("*.html") if ".git" not in p.parts]


class TestSinSorteo(unittest.TestCase):
    def test_ninguna_pagina_generada_enlaza_al_sorteo(self):
        paginas = _paginas_generadas()
        self.assertGreater(len(paginas), 25)
        for ruta in paginas:
            with self.subTest(pagina=str(ruta.relative_to(RAIZ))):
                self.assertIsNone(ENLACE_SORTEO.search(ruta.read_text(encoding="utf-8")))

    def test_sitemap_y_robots_no_mencionan_el_sorteo(self):
        for nombre in FICHEROS_PUBLICADOS:
            with self.subTest(fichero=nombre):
                self.assertIsNone(ENLACE_SORTEO.search((RAIZ / nombre).read_text(encoding="utf-8")))

    def test_no_queda_la_carpeta_del_sorteo(self):
        self.assertFalse((RAIZ / "sorteo").exists())
        self.assertFalse((RAIZ / "es" / "sorteo").exists())


if __name__ == "__main__":
    unittest.main()
