#!/usr/bin/env python3
"""ML-354: el creador destacado «Yuya Hosokawa» en las cuatro páginas Learn (/learn/, /es/aprender/, /pt/aprender/, /ja/learn/): va el tercero,
después de Palhares y TCG Academy, con «Ver en Metafy» a su perfil y una sola casilla (Guías; sin academia ni sesiones), sus imágenes son
locales de img/destacados/ y pesan lo esperado, y no caduca. «Artículos» NO se pinta hasta la versión siguiente: el campo `articulos` se queda
en contenido.json y el generador lo ignora. Sin navegador.

Uso:  python3 -m pytest tools/test_destacado_yuyan.py
"""
import json
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_learn  # noqa: E402
from test_destacado_tcgacademy import LOCAL, MAX_FONDO, MAX_FOTO, tarjetas  # noqa: E402

IDIOMAS = {"learn/": "en", "es/aprender/": "es", "pt/aprender/": "pt", "ja/learn/": "ja"}
PERFIL, GUIAS, ARTICULOS = "https://metafy.gg/@yuyan", "https://metafy.gg/@yuyan/guides", "https://metafy.gg/@yuyan/posts"


def entrada() -> dict:
    return json.loads((RAIZ / "contenido.json").read_text(encoding="utf-8"))["destacados"][2]


class YuyaTest(unittest.TestCase):
    def test_en_las_cuatro_paginas_yuya_es_la_tercera(self):
        for ruta in IDIOMAS:
            with self.subTest(ruta=ruta):
                self.assertEqual([t["attrs"].get("data-id") for t in tarjetas(ruta)], ["pcpalhares", "tcgacademy", "yuyan"])

    def test_ver_en_metafy_va_al_perfil_y_solo_hay_la_casilla_de_guias(self):
        for ruta, idioma in IDIOMAS.items():
            with self.subTest(ruta=ruta):
                t = tarjetas(ruta)[2]
                principal = [e for e in t["enlaces"] if "d2cta" in e["clase"]]
                casillas = [e for e in t["enlaces"] if "d2cas" in e["clase"]]
                self.assertEqual([e["href"] for e in principal], [PERFIL])
                self.assertEqual([(e["cas"], e["href"]) for e in casillas], [("guias", GUIAS)])
                self.assertEqual(len(t["enlaces"]), 2, "ni academia, ni sesiones, ni artículos, ni ningún otro enlace")
                self.assertEqual(casillas[0]["texto"].strip(), construir_learn.TEXTOS[idioma]["cas"][1])
                for e in principal + casillas:
                    self.assertIn("sponsored", e["rel"])

    def test_no_se_pinta_la_casilla_de_articulos_hasta_la_version_siguiente(self):
        self.assertEqual(entrada()["articulos"], ARTICULOS, "el campo se queda en el JSON para la versión siguiente")
        for ruta in IDIOMAS:
            with self.subTest(ruta=ruta):
                html = (RAIZ / ruta / "index.html").read_text(encoding="utf-8")
                self.assertNotIn("/@yuyan/posts", html)
                self.assertNotIn('data-cas="articulos"', html)
                self.assertEqual([e["cas"] for e in tarjetas(ruta)[2]["enlaces"] if "d2cas" in e["clase"]], ["guias"])

    def test_el_generador_ignora_articulos_sin_fallar(self):
        d = construir_learn.leer_destacados(RAIZ)[2]
        self.assertEqual(d["id"], "yuyan")
        self.assertNotIn("articulos", d)

    def test_las_imagenes_son_locales_existen_y_pesan_lo_esperado(self):
        d = entrada()
        self.assertEqual(d["id"], "yuyan")
        self.assertNotIn("hasta", d, "para siempre (decisión del dueño)")
        for campo, limite in (("foto", MAX_FOTO), ("fondo", MAX_FONDO)):
            with self.subTest(campo=campo):
                self.assertTrue(d[campo].startswith(LOCAL), "imagen propia, no de otro dominio")
                archivo = RAIZ / "img" / "destacados" / d[campo][len(LOCAL):]
                datos = archivo.read_bytes()
                self.assertGreater(len(datos), 1000)
                self.assertLessEqual(len(datos), limite)
                self.assertEqual(datos[:4] + datos[8:12], b"RIFFWEBP")
        for ruta in IDIOMAS:
            with self.subTest(ruta=ruta):
                self.assertEqual(sorted(i["src"] for i in tarjetas(ruta)[2]["imgs"]), sorted([d["foto"], d["fondo"]]))


if __name__ == "__main__":
    unittest.main()
