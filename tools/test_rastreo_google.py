#!/usr/bin/env python3
"""ML-312, avisos de Search Console: (1) ninguna página generada lleva una cadena «img/xx_» sin nombre de archivo, que Googlebot
tomaba por URL (404 en /img/es_); (2) la portada en portugués enlaza a su guía. Comprueba sobre los archivos (sin red).

Uso:  python3 tools/test_search_console_ml312.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# «img/es_» o «img/en_» seguido de una comilla, una comilla simple o el fin de cadena: prefijo sin nombre de archivo.
PREFIJO_SUELTO = re.compile(r"img/[a-z]{2}_[\"'`]")


def paginas():
    return [p for p in RAIZ.rglob("*.html") if ".git" not in p.parts and "node_modules" not in p.parts]


class PrefijoDeImagenSuelto(unittest.TestCase):
    def test_ninguna_pagina_tiene_prefijo_de_imagen_incompleto(self):
        malas = [str(p.relative_to(RAIZ)) for p in paginas() if PREFIJO_SUELTO.search(p.read_text(encoding="utf-8"))]
        self.assertEqual(malas, [], "cadena «img/xx_» sin nombre de archivo (Googlebot la lee como URL)")

    def test_las_portadas_con_pestanas_llevan_el_prefijo_en_un_atributo(self):
        for ruta, raiz, idioma in (("index.html", "", "en"), ("es/index.html", "../", "es")):
            html = (RAIZ / ruta).read_text(encoding="utf-8")
            self.assertIn('data-raiz="%s" data-idioma="%s"' % (raiz, idioma), html, ruta)


class PortadaPortuguesaEnlazaSuGuia(unittest.TestCase):
    def test_pt_enlaza_a_su_guia_en_el_cuerpo_y_sin_noindex(self):
        html = (RAIZ / "pt" / "index.html").read_text(encoding="utf-8")
        cuerpo = html[html.index("<main"):html.index("</main>")]
        self.assertIn('href="/guia/guia_manalab_pt.html"', cuerpo)
        guia = (RAIZ / "guia" / "guia_manalab_pt.html").read_text(encoding="utf-8")
        self.assertNotIn("noindex", guia)


if __name__ == "__main__":
    unittest.main()
