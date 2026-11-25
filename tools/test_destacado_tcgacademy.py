#!/usr/bin/env python3
"""ML-351: el creador destacado «TCG Academy» en las cuatro páginas Learn (/learn/, /es/aprender/, /pt/aprender/, /ja/learn/): va el segundo,
después de Palhares, con «Ver en Metafy» a su perfil y una sola casilla (sesiones, sin guías ni academia), sus imágenes son locales de
img/destacados/ y pesan lo esperado, y no caduca. Sin navegador.

Uso:  python3 -m pytest tools/test_destacado_tcgacademy.py
"""
import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_learn  # noqa: E402

PAGINAS = {"learn/": "Sessions", "es/aprender/": "Sesiones", "pt/aprender/": "Sessões", "ja/learn/": None}   # ja: el texto lo pone el generador
LOCAL = "https://manalab.es/img/destacados/"
MAX_FOTO, MAX_FONDO = 30 * 1024, 120 * 1024   # bytes


class Tarjetas(HTMLParser):
    """Las tarjetas .d2c del banner: atributos, enlaces (clase, data-cas, href, texto) e imágenes (clase, src)."""
    def __init__(self):
        super().__init__()
        self.tarjetas, self.actual, self.enlace = [], None, None

    def handle_starttag(self, etiqueta, atributos):
        a = dict(atributos)
        clases = (a.get("class") or "").split()
        if etiqueta == "article" and "d2c" in clases:
            self.actual = {"attrs": a, "enlaces": [], "imgs": []}
            self.tarjetas.append(self.actual)
        elif self.actual is not None and etiqueta == "a":
            self.enlace = {"clase": clases, "cas": a.get("data-cas"), "href": a.get("href"), "rel": a.get("rel"), "texto": ""}
            self.actual["enlaces"].append(self.enlace)
        elif self.actual is not None and etiqueta == "img":
            self.actual["imgs"].append({"clase": clases, "src": a.get("src")})

    def handle_endtag(self, etiqueta):
        if etiqueta == "a":
            self.enlace = None
        elif etiqueta == "article":
            self.actual = None

    def handle_data(self, dato):
        if self.enlace is not None:
            self.enlace["texto"] += dato


def tarjetas(ruta: str) -> list:
    analizador = Tarjetas()
    analizador.feed((RAIZ / ruta / "index.html").read_text(encoding="utf-8"))
    return analizador.tarjetas


class TcgAcademyTest(unittest.TestCase):
    def test_en_las_cuatro_paginas_tcgacademy_es_el_segundo_de_tres(self):
        for ruta in PAGINAS:
            with self.subTest(ruta=ruta):
                lista = tarjetas(ruta)
                self.assertEqual([t["attrs"].get("data-id") for t in lista], ["pcpalhares", "tcgacademy", "yuyan"])
                self.assertIn('data-total="3"', (RAIZ / ruta / "index.html").read_text(encoding="utf-8"))

    def test_ver_en_metafy_va_al_perfil_y_solo_hay_la_casilla_de_sesiones(self):
        for ruta, texto in PAGINAS.items():
            with self.subTest(ruta=ruta):
                t = tarjetas(ruta)[1]
                principal = [e for e in t["enlaces"] if "d2cta" in e["clase"]]
                casillas = [e for e in t["enlaces"] if "d2cas" in e["clase"]]
                self.assertEqual([e["href"] for e in principal], ["https://metafy.gg/@luissalvatto"])
                self.assertEqual([(e["cas"], e["href"]) for e in casillas], [("sesiones", "https://metafy.gg/@luissalvatto/sessions")])
                self.assertEqual(len(t["enlaces"]), 2, "ni guías, ni academia, ni ningún otro enlace")
                for e in principal + casillas:
                    self.assertIn("sponsored", e["rel"])
                if texto:
                    self.assertEqual(casillas[0]["texto"].strip(), texto, "el texto de la casilla es el que ya tenía el generador")
                self.assertTrue(casillas[0]["texto"].strip())

    def test_el_texto_de_la_casilla_es_el_del_generador_en_cada_idioma(self):
        textos = {ruta: construir_learn.TEXTOS[idioma]["cas"][2] for ruta, idioma in
                  (("learn/", "en"), ("es/aprender/", "es"), ("pt/aprender/", "pt"), ("ja/learn/", "ja"))}
        for ruta, texto in textos.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(tarjetas(ruta)[1]["enlaces"][1]["texto"].strip(), texto)
        self.assertEqual(textos["es/aprender/"], "Sesiones")

    def test_las_imagenes_son_locales_existen_y_pesan_lo_esperado(self):
        contenido = json.loads((RAIZ / "contenido.json").read_text(encoding="utf-8"))["destacados"]
        d = contenido[1]
        self.assertEqual(d["id"], "tcgacademy")
        self.assertNotIn("hasta", d, "para siempre (decisión del dueño)")
        for campo, limite in (("foto", MAX_FOTO), ("fondo", MAX_FONDO)):
            with self.subTest(campo=campo):
                self.assertTrue(d[campo].startswith(LOCAL), "imagen propia, no de otro dominio")
                archivo = RAIZ / "img" / "destacados" / d[campo][len(LOCAL):]
                self.assertTrue(archivo.is_file(), archivo)
                self.assertGreater(archivo.stat().st_size, 1000)
                self.assertLessEqual(archivo.stat().st_size, limite)
                self.assertEqual(archivo.read_bytes()[:4] + archivo.read_bytes()[8:12], b"RIFFWEBP")
        for ruta in PAGINAS:
            with self.subTest(ruta=ruta):
                srcs = [i["src"] for i in tarjetas(ruta)[1]["imgs"]]
                self.assertEqual(sorted(srcs), sorted([d["foto"], d["fondo"]]))
                self.assertFalse([s for s in srcs if not re.match(r"https://manalab\.es/img/destacados/[a-z-]+\.webp$", s)])

    def test_la_entrada_no_cambia_la_de_palhares(self):
        palhares = json.loads((RAIZ / "contenido.json").read_text(encoding="utf-8"))["destacados"][0]
        self.assertEqual(palhares["guias"], "https://metafy.gg/@pcpalhares/guides")
        self.assertEqual(sorted(palhares), ["enlace", "fondo", "foto", "frase", "guias", "id", "linea", "nombre"])


if __name__ == "__main__":
    unittest.main()
