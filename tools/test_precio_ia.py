#!/usr/bin/env python3
"""ML-307: la IA cuesta 6 dólares al mes (la cobra Metafy en USD). Comprueba sobre las páginas generadas (sin red).

Uso:  python3 -m pytest tools/test_precio_ia.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PRECIO_VIEJO = re.compile(r"5[\s  ]*(€|euros?\b|EUR\b|ユーロ|유로|欧元)|€[\s  ]*5\b|月額5", re.I)
# formato del precio por idioma (guía) y la frase donde debe aparecer
PRECIO_POR_IDIOMA = {"es": "6 $ al mes", "en": "$6 per month", "pt": "US$ 6 por mês", "fr": "6 $ par mois",
                     "de": "6 $ im Monat", "it": "6 $ al mese", "ja": "月6ドル", "ko": "월 6달러", "zh": "每月 6 美元"}


def _paginas():
    return [p for p in RAIZ.rglob("*.html") if ".git" not in p.parts]


class TestPrecioDeLaIa(unittest.TestCase):
    def test_ninguna_pagina_generada_dice_5_euros(self):
        paginas = _paginas()
        self.assertGreater(len(paginas), 25)
        for ruta in paginas:
            with self.subTest(pagina=str(ruta.relative_to(RAIZ))):
                self.assertIsNone(PRECIO_VIEJO.search(ruta.read_text(encoding="utf-8")))

    def test_cada_guia_da_el_precio_en_dolares_de_su_idioma(self):
        for idioma, precio in PRECIO_POR_IDIOMA.items():
            with self.subTest(idioma=idioma):
                html = (RAIZ / "guia" / f"guia_manalab_{idioma}.html").read_text(encoding="utf-8")
                self.assertIn(precio, html)

    def test_la_portada_en_ingles_y_el_json_ld_dicen_6_dolares(self):
        html = (RAIZ / "index.html").read_text(encoding="utf-8")
        self.assertIn('<div class="ia-precio">$6 <small>per month</small></div>', html)
        self.assertIn("Subscribe on Metafy ($6 per month)", html)  # respuesta de la FAQ (HTML y JSON-LD)


if __name__ == "__main__":
    unittest.main()
