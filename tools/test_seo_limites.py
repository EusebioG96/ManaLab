#!/usr/bin/env python3
"""ML-341, SEO-01 a SEO-05, SEO-07 y SEO-09: límites de SEO de las páginas rastreables (las del sitemap), no de una lista fija.

Títulos (60; CJK 70 de ancho), descripciones latinas (70-160; mínimo 130 en las cuatro del SEO-03), alts (125, sin «datos de ejemplo»),
sitemap (cada <loc> existe, sin noindex, sin /sorteo/), BreadcrumbList y VideoObject (JSON-LD válido y coherente con la página) y
enlace en el cuerpo de las páginas de función a la guía de su idioma.

Uso:  python3 -m pytest -q tools/test_seo_limites.py
"""
import html
import json
import re
import subprocess
import unicodedata
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

RAIZ = Path(__file__).resolve().parent.parent
SITIO = "https://manalab.es"
MAX_TITULO, MAX_TITULO_CJK = 60, 70  # caracteres; en CJK, ancho (carácter de ancho completo = 2)
MIN_DESC, MAX_DESC, MIN_DESC_PORTADAS = 70, 160, 130
CJK = ("ja", "ko", "zh")
MAX_ALT = 125
RE_DATOS_DE_EJEMPLO = re.compile(r"sample data|datos de ejemplo|dados de exemplo|サンプルデータ|示例数据|예시 데이터|Beispieldaten", re.I)
PORTADAS = ("index.html", "es/index.html", "pt/index.html", "ja/index.html")  # sin migas
CON_DESC_MINIMA = ("coaches/index.html", "es/coaches/index.html", "index.html", "es/index.html")  # SEO-03
# Páginas de función y el ancla de la guía que habla de su tema (SEO-09): (página, idioma, ancla)
PAGINAS_CON_ENLACE_A_GUIA = [
    ("detailed-logs/index.html", "en", "inicio"), ("es/registro-detallado/index.html", "es", "inicio"),
    ("overlay/index.html", "en", "overlay"), ("es/overlay/index.html", "es", "overlay"),
    ("magic-online/index.html", "en", "mtgo"), ("es/magic-online/index.html", "es", "mtgo"),
    ("coaches/index.html", "en", "coach"), ("es/coaches/index.html", "es", "coach"),
    ("pt/coaches/index.html", "pt", None),  # ya llevaba en el cuerpo el enlace a la guía completa (sin ancla)
]


def ancho(texto: str) -> int:
    """Ancho de un texto: los caracteres de ancho completo o ancho (CJK) cuentan 2."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in texto)


def archivo_de_url(url: str) -> Path:
    """Archivo del repositorio de una URL de manalab.es (``https://manalab.es/x/`` -> ``x/index.html``)."""
    ruta = urlparse(url).path.lstrip("/")
    return RAIZ / (ruta + "index.html" if ruta == "" or ruta.endswith("/") else ruta)


def urls_del_sitemap() -> list[str]:
    """Las ``<loc>`` de sitemap.xml."""
    raiz = ET.parse(RAIZ / "sitemap.xml").getroot()
    return [e.text.strip() for e in raiz.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]


class Pagina(HTMLParser):
    """Lo que estos tests miran de una página: lang, título, descripciones, alts, JSON-LD, vídeos y enlaces del cuerpo."""

    def __init__(self, texto: str):
        super().__init__(convert_charrefs=True)
        self.lang, self.titulo, self.descripcion, self.robots = "", "", None, ""
        self.alts, self.jsonld, self.videos, self.enlaces_cuerpo = [], [], [], []
        self._en_titulo = self._en_ld = False
        self._ld = ""
        self._fuera = 0  # profundidad dentro de header/footer
        self.feed(texto)

    def handle_starttag(self, tag, attrs):
        a = {k: v or "" for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "")
        elif tag == "title":
            self._en_titulo = True
        elif tag == "meta" and a.get("name") == "description":
            self.descripcion = a.get("content", "")
        elif tag == "meta" and a.get("name") == "robots":
            self.robots = a.get("content", "").lower()
        elif tag == "img" and "alt" in a:
            self.alts.append(a["alt"])
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._en_ld, self._ld = True, ""
        elif tag == "video":
            self.videos.append(a)
        elif tag in ("header", "footer"):
            self._fuera += 1
        elif tag == "a" and not self._fuera and a.get("href"):
            self.enlaces_cuerpo.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._en_titulo = False
        elif tag == "script" and self._en_ld:
            self._en_ld = False
            self.jsonld.append(self._ld)
        elif tag in ("header", "footer"):
            self._fuera -= 1

    def handle_data(self, data):
        if self._en_titulo:
            self.titulo += data
        if self._en_ld:
            self._ld += data


def paginas_rastreables() -> dict[str, Pagina]:
    """Ruta relativa -> página analizada, de cada URL del sitemap."""
    salida = {}
    for url in urls_del_sitemap():
        archivo = archivo_de_url(url)
        if archivo.is_file():
            salida[archivo.relative_to(RAIZ).as_posix()] = Pagina(archivo.read_text(encoding="utf-8"))
    return salida


def es_cjk(ruta: str, pagina: Pagina) -> bool:
    return pagina.lang.split("-")[0] in CJK


def grafo(pagina: Pagina) -> list[dict]:
    """Todos los nodos de todos los JSON-LD de la página. Lanza ValueError si alguno no es JSON válido."""
    nodos = []
    for bruto in pagina.jsonld:
        dato = json.loads(bruto)
        nodos += dato["@graph"] if isinstance(dato, dict) and "@graph" in dato else [dato]
    return nodos


class TestLimites(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paginas = paginas_rastreables()

    def test_se_recorren_todas_las_paginas_del_sitemap(self):
        self.assertEqual(len(self.paginas), len(urls_del_sitemap()))
        self.assertGreaterEqual(len(self.paginas), 31)

    def test_titulos_de_60_o_menos(self):
        for ruta, p in self.paginas.items():
            titulo = " ".join(p.titulo.split())
            with self.subTest(ruta=ruta, titulo=titulo):
                if es_cjk(ruta, p):
                    self.assertLessEqual(ancho(titulo), MAX_TITULO_CJK)
                else:
                    self.assertLessEqual(len(titulo), MAX_TITULO)
                self.assertIn("ManaLab", titulo)

    def test_descripciones_latinas_de_70_a_160_y_sin_cortar(self):
        for ruta, p in self.paginas.items():
            if es_cjk(ruta, p):
                continue
            descripcion = p.descripcion or ""
            with self.subTest(ruta=ruta, longitud=len(descripcion)):
                self.assertTrue(MIN_DESC <= len(descripcion) <= MAX_DESC)
                self.assertRegex(descripcion, r"[.!?)]$", "la descripción termina a mitad de frase")

    def test_descripciones_de_portada_y_coaches_de_130_o_mas(self):
        for ruta in CON_DESC_MINIMA:
            with self.subTest(ruta=ruta):
                self.assertGreaterEqual(len(self.paginas[ruta].descripcion), MIN_DESC_PORTADAS)

    def test_alts_de_125_o_menos_y_sin_datos_de_ejemplo(self):
        for ruta, p in self.paginas.items():
            for alt in p.alts:
                with self.subTest(ruta=ruta, alt=alt[:50]):
                    self.assertLessEqual(len(alt), MAX_ALT)
                    self.assertIsNone(RE_DATOS_DE_EJEMPLO.search(alt))


class TestSitemap(unittest.TestCase):
    def test_cada_loc_existe_y_no_tiene_noindex(self):
        urls = urls_del_sitemap()
        self.assertGreaterEqual(len(urls), 31)
        for url in urls:
            with self.subTest(url=url):
                archivo = archivo_de_url(url)
                self.assertTrue(archivo.is_file(), f"{url} no tiene archivo")
                self.assertNotIn("noindex", Pagina(archivo.read_text(encoding="utf-8")).robots)

    def test_el_sorteo_no_esta(self):
        urls = urls_del_sitemap()
        for fuera in (f"{SITIO}/sorteo/", f"{SITIO}/sorteo/en/"):
            self.assertNotIn(fuera, urls)
        self.assertFalse([u for u in urls if "/sorteo" in u])


class TestDatosEstructurados(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paginas = paginas_rastreables()

    def test_todo_el_json_ld_es_valido(self):
        for ruta, p in self.paginas.items():
            with self.subTest(ruta=ruta):
                grafo(p)

    def test_migas_en_las_interiores_y_no_en_las_portadas(self):
        for ruta, p in self.paginas.items():
            migas = [n for n in grafo(p) if n.get("@type") == "BreadcrumbList"]
            with self.subTest(ruta=ruta):
                if ruta in PORTADAS:
                    self.assertEqual(migas, [])
                    continue
                self.assertEqual(len(migas), 1)
                elementos = migas[0]["itemListElement"]
                self.assertEqual([e["position"] for e in elementos], [1, 2])
                self.assertTrue(all(e["name"].strip() for e in elementos))
                inicio, actual = elementos[0]["item"], elementos[1]["item"]
                self.assertTrue(archivo_de_url(inicio).is_file(), f"el inicio {inicio} no existe")
                self.assertIn(inicio, urls_del_sitemap(), "el inicio debe ser una portada del sitemap")
                self.assertEqual(actual, f"{SITIO}/" + ruta.removesuffix("index.html"))

    def test_un_videoobject_por_video_con_poster(self):
        total = 0
        for ruta, p in self.paginas.items():
            url_pagina = f"{SITIO}/" + ruta.removesuffix("index.html")
            objetos = [n for n in grafo(p) if n.get("@type") == "VideoObject"]
            esperados = [v for v in p.videos if v.get("poster")]
            with self.subTest(ruta=ruta):
                self.assertEqual(len(objetos), len(esperados))
            for objeto in objetos:
                total += 1
                with self.subTest(ruta=ruta, video=objeto["contentUrl"]):
                    for campo in ("name", "description", "thumbnailUrl", "contentUrl", "uploadDate"):
                        self.assertTrue(objeto.get(campo), campo)
                    for campo in ("thumbnailUrl", "contentUrl"):
                        self.assertTrue(objeto[campo].startswith(SITIO + "/"))
                        self.assertTrue(archivo_de_url(objeto[campo]).is_file(), objeto[campo])
                    self.assertRegex(objeto["uploadDate"], r"^\d{4}-\d{2}-\d{2}$")
                    self.assertIn(objeto["thumbnailUrl"], [urljoin(url_pagina, v["poster"]) for v in esperados])
        self.assertGreaterEqual(total, 40)

    def test_las_fechas_de_los_videos_son_las_del_ultimo_commit(self):
        fechas = json.loads((RAIZ / "plantillas/video_fechas.json").read_text(encoding="utf-8"))
        if subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=RAIZ, capture_output=True, text=True).stdout.strip() != "false":
            self.skipTest("clon superficial: no hay historial para comprobar las fechas")
        self.assertTrue(fechas)
        for ruta, fecha in fechas.items():
            with self.subTest(video=ruta):
                real = subprocess.run(["git", "log", "-1", "--format=%cs", "--", ruta], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
                self.assertEqual(fecha, real)


class TestEnlaceAGuia(unittest.TestCase):
    def test_paginas_de_funcion_enlazan_en_el_cuerpo_a_la_guia_de_su_idioma(self):
        for ruta, idioma, ancla in PAGINAS_CON_ENLACE_A_GUIA:
            pagina = Pagina((RAIZ / ruta).read_text(encoding="utf-8"))
            base = f"/guia/guia_manalab_{idioma}.html"
            esperado = base + (f"#{ancla}" if ancla else "")
            with self.subTest(ruta=ruta):
                self.assertEqual(pagina.enlaces_cuerpo.count(esperado), 1, "un único enlace, en el cuerpo (fuera de header y footer)")
                guia = (RAIZ / base.lstrip("/")).read_text(encoding="utf-8")
                for enlace in pagina.enlaces_cuerpo:
                    if enlace.startswith(base + "#"):
                        self.assertIn(f'id="{enlace.split("#")[1]}"', guia, f"el ancla de {enlace} no existe en la guía")
                self.assertEqual([h for h in pagina.enlaces_cuerpo if h.startswith("/guia/") and not h.startswith(base)], [],
                                 "en el cuerpo solo se enlaza a la guía del idioma de la página")


if __name__ == "__main__":
    unittest.main()
