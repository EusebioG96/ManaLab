#!/usr/bin/env python3
"""ML-417: las tipografías web y sus tipos de reserva viven en una sola plantilla (css_fuentes.tpl) que usan todas las hojas.

Protege: ninguna otra plantilla declara @font-face; toda página generada que carga Geist/Marcellus lleva exactamente los mismos @font-face
(web y reserva) y sus pilas --f-display/--f-texto/--f-mono nombran el tipo de reserva justo detrás de la fuente web.

Uso:  python3 -m pytest tools/test_fuentes_reserva.py
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_web  # noqa: E402

RAIZ = construir_web.RAIZ
OMITIDAS = ("docs/", "plantillas/", "tools/")
PILAS = {"--f-display": ("Marcellus", "Marcellus Reserva"), "--f-texto": ("Geist", "Geist Reserva"), "--f-mono": ("Geist Mono", "Geist Mono Reserva")}
_FONT_FACE = re.compile(r"@font-face\{[^}]*\}")


def paginas_con_fuentes() -> dict[str, str]:
    """Ruta -> HTML de las páginas publicadas que declaran @font-face."""
    salida = {}
    for relativa in construir_web.listar_paginas(RAIZ):
        if relativa.as_posix().startswith(OMITIDAS):
            continue
        html = (RAIZ / relativa).read_text(encoding="utf-8")
        if "@font-face" in html:
            salida[relativa.as_posix()] = html
    return salida


class FuentesReserva(unittest.TestCase):
    def test_solo_css_fuentes_declara_font_face(self):
        duenos = [p.name for p in (RAIZ / "plantillas").glob("*.tpl") if "@font-face" in p.read_text(encoding="utf-8")]
        self.assertEqual(["css_fuentes.tpl"], duenos)

    def test_todas_las_paginas_llevan_los_mismos_font_face_con_reserva(self):
        esperado = _FONT_FACE.findall((RAIZ / "plantillas" / "css_fuentes.tpl").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(esperado), 16)
        paginas = paginas_con_fuentes()
        self.assertTrue({"guia/guia_manalab_en.html", "privacy/index.html", "safety/index.html", "index.html"} <= set(paginas), sorted(paginas))
        for ruta, html in paginas.items():
            if "font-family:'Geist'" not in html:
                continue   # solo cargan Marcellus/Geist las hojas que usan la tipografía de la web
            self.assertEqual(esperado, _FONT_FACE.findall(html), f"{ruta}: @font-face distintos a css_fuentes.tpl")

    def test_las_pilas_ponen_el_tipo_de_reserva_tras_la_fuente_web(self):
        for ruta, html in paginas_con_fuentes().items():
            if "font-family:'Geist'" not in html:
                continue
            for variable, (web, reserva) in PILAS.items():
                declaraciones = re.findall(rf'{variable}:\s*"{web}"([^;]*);', html)
                self.assertTrue(declaraciones, f"{ruta}: sin {variable}")
                for resto in declaraciones:
                    self.assertTrue(resto.startswith(f', "{reserva}"'), f"{ruta}: {variable} sin «{reserva}» tras «{web}»")


if __name__ == "__main__":
    unittest.main()
