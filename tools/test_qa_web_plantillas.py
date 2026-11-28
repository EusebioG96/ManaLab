#!/usr/bin/env python3
"""ML-412: arreglos del QA de la web (ML-409) que se comprueban sobre el HTML generado, sin navegador ni red.

Protege: la imagen de las tarjetas (og:image) existe y mide lo que dice (M2); el menú de Novedades lista las versiones que tiene la página (M3);
todas las páginas llevan og:image:alt traducido, el enlace «Saltar al contenido» (con destino que existe) y, las que tienen menú móvil, menu.js;
el enlace «English» de /privacy/ declara su idioma; y los <lastmod> del sitemap se ponen al día sin cambiar nada en una segunda pasada.

Uso:  python3 -m pytest tools/test_qa_web_plantillas.py
"""
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_accesibilidad  # noqa: E402
import construir_web  # noqa: E402

RAIZ = construir_web.RAIZ
SITIO = "https://manalab.es"
OMITIDAS = ("docs/", "plantillas/", "tools/")  # .html que no son páginas de la web


def paginas() -> dict[str, str]:
    """Ruta relativa -> HTML de cada página publicada."""
    salida = {}
    for relativa in construir_web.listar_paginas(RAIZ):
        if relativa.as_posix().startswith(OMITIDAS):
            continue
        salida[relativa.as_posix()] = (RAIZ / relativa).read_text(encoding="utf-8")
    return salida


def idioma(html: str) -> str:
    coincidencia = re.search(r'<html lang="([^"]+)"', html)
    return coincidencia.group(1).split("-")[0] if coincidencia else ""


def medidas_jpeg(ruta: Path) -> tuple[int, int]:
    """(ancho, alto) de un JPEG leyendo su cabecera SOF; sin dependencias."""
    datos = ruta.read_bytes()
    pos = 2
    while pos < len(datos):
        marca = datos[pos + 1]
        largo = struct.unpack(">H", datos[pos + 2:pos + 4])[0]
        if marca in (0xC0, 0xC1, 0xC2):
            alto, ancho = struct.unpack(">HH", datos[pos + 5:pos + 9])
            return ancho, alto
        pos += 2 + largo
    raise ValueError(f"{ruta}: sin cabecera SOF")


def meta(html: str, clave: str) -> str | None:
    """Valor de un <meta> por property o name, con el atributo en cualquier orden."""
    for etiqueta in re.findall(r"<meta [^>]*>", html):
        if re.search(rf'(?:property|name)="{re.escape(clave)}"', etiqueta):
            valor = re.search(r'content="([^"]*)"', etiqueta)
            return valor.group(1) if valor else None
    return None


class TarjetasDeRedes(unittest.TestCase):
    def test_og_image_existe_y_mide_lo_que_declara(self):
        vistas = 0
        for ruta, html in paginas().items():
            url = meta(html, "og:image")
            if not url:
                continue
            vistas += 1
            archivo = RAIZ / url.removeprefix(SITIO + "/")
            self.assertTrue(archivo.is_file(), f"{ruta}: no existe {url}")
            declarado = (int(meta(html, "og:image:width") or 0), int(meta(html, "og:image:height") or 0))
            if declarado != (0, 0):
                self.assertEqual(declarado, medidas_jpeg(archivo), f"{ruta}: las medidas declaradas no son las de la imagen")
            self.assertEqual(url, meta(html, "twitter:image") or url, f"{ruta}: twitter:image distinta de og:image")
        self.assertGreaterEqual(vistas, 25)

    def test_overlay_usa_una_imagen_horizontal_1200x630(self):
        for ruta in ("overlay/index.html", "es/overlay/index.html"):
            html = paginas()[ruta]
            self.assertEqual(f"{SITIO}/img/og-3.0.jpg", meta(html, "og:image"))
            self.assertEqual((1200, 630), medidas_jpeg(RAIZ / "img/og-3.0.jpg"))

    def test_todas_llevan_og_image_alt_en_su_idioma(self):
        por_idioma: dict[str, set[str]] = {}
        for ruta, html in paginas().items():
            if not meta(html, "og:image"):
                continue
            alt = meta(html, "og:image:alt")
            self.assertTrue(alt, f"{ruta}: sin og:image:alt")
            por_idioma.setdefault(idioma(html), set()).add(alt)
        for idi, textos in por_idioma.items():
            self.assertEqual(1, len(textos), f"{idi}: el texto alternativo debe ser uno por idioma")
        todos = [t for textos in por_idioma.values() for t in textos]
        self.assertEqual(len(todos), len(set(todos)), "dos idiomas comparten el mismo texto alternativo: falta traducir")
        self.assertGreaterEqual(len(por_idioma), 9)   # en, es, pt, ja y las guías de, fr, it, ko, zh


class MenuDeNovedades(unittest.TestCase):
    def test_el_menu_lista_las_tres_versiones_y_cada_enlace_apunta_a_una_seccion(self):
        for ruta, esperado in (("novedades/index.html", ("New in 3.0", "Version 2.3", "Version 2.2")),
                               ("es/novedades/index.html", ("Novedades 3.0", "Versión 2.3", "Versión 2.2"))):
            html = paginas()[ruta]
            cabecera = html[html.index("<header"):html.index("</header>")]
            for nav in re.findall(r"<nav[^>]*>(.*?)</nav>", cabecera, re.S):
                enlaces = re.findall(r'<a href="#([^"]+)">([^<]+)</a>', nav)
                self.assertEqual(esperado, tuple(t for _, t in enlaces), ruta)
                for ancla, _ in enlaces:
                    self.assertIn(f'id="{ancla}"', html, f"{ruta}: #{ancla} no existe")
            self.assertEqual("novedades-3-0", re.findall(r'<a href="#([^"]+)">', cabecera)[0])   # la primera sección es la 3.0
            self.assertNotIn("New in 2.3", html)
            self.assertNotIn("Novedades de la 2.3", html)


class Accesibilidad(unittest.TestCase):
    def test_todas_las_paginas_con_main_tienen_saltar_al_contenido_traducido(self):
        vistas = 0
        for ruta, html in paginas().items():
            if "<main" not in html:
                continue
            vistas += 1
            enlace = re.search(r'<body[^>]*>\n<a class="saltar" href="#([^"]+)">([^<]+)</a>', html)
            self.assertIsNotNone(enlace, f"{ruta}: el primer elemento del <body> no es «Saltar al contenido»")
            destino, texto = enlace.groups()
            self.assertEqual(construir_accesibilidad.TEXTO_SALTAR[idioma(html)], texto, ruta)
            self.assertEqual(1, html.count(f'id="{destino}"'), f"{ruta}: #{destino} debe existir una sola vez")
            self.assertRegex(html, rf'<main[^>]*id="{destino}"', f"{ruta}: el destino debe ser el <main>")
        self.assertGreaterEqual(vistas, 35)

    def test_los_textos_de_saltar_son_distintos_en_cada_idioma(self):
        textos = list(construir_accesibilidad.TEXTO_SALTAR.values())
        self.assertEqual(len(textos), len(set(textos)))
        self.assertEqual({"en", "es", "pt", "ja", "de", "fr", "it", "ko", "zh"}, set(construir_accesibilidad.TEXTO_SALTAR))

    def test_menu_js_solo_en_paginas_con_menu_movil(self):
        for ruta, html in paginas().items():
            self.assertEqual('<details class="menu"' in html, '<script defer src="/menu.js"></script>' in html, ruta)
        self.assertTrue((RAIZ / "menu.js").is_file())

    def test_privacidad_marca_el_enlace_a_la_seccion_en_ingles(self):
        html = paginas()["privacy/index.html"]
        self.assertIn('<a href="#en" lang="en" hreflang="en">English</a>', html)
        self.assertIn('<section lang="en" id="en">', html)


class SitemapAlDia(unittest.TestCase):
    def test_lastmod_sale_de_git_y_la_segunda_pasada_no_cambia_nada(self):
        entorno = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
                   "GIT_COMMITTER_DATE": "2026-11-27T10:00:00", "GIT_AUTHOR_DATE": "2026-11-27T10:00:00"}
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            (raiz / "index.html").write_text("<html></html>", encoding="utf-8")
            (raiz / "sitemap.xml").write_text(
                "<urlset><url><loc>https://manalab.es/</loc><lastmod>2026-01-01</lastmod></url></urlset>\n", encoding="utf-8")
            for orden in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "x"]):
                subprocess.run(["git", *orden], cwd=raiz, env=entorno, check=True, capture_output=True)
            self.assertTrue(construir_web.actualizar_sitemap(raiz))
            primera = (raiz / "sitemap.xml").read_bytes()
            self.assertIn(b"<lastmod>2026-11-27</lastmod>", primera)
            self.assertFalse(construir_web.actualizar_sitemap(raiz))   # nada que cambiar: no reescribe
            self.assertEqual(primera, (raiz / "sitemap.xml").read_bytes())

    def test_generar_la_web_en_otra_carpeta_no_toca_el_sitemap(self):
        antes = (RAIZ / "sitemap.xml").read_bytes()
        with tempfile.TemporaryDirectory() as temporal:
            self.assertEqual(0, construir_web.principal(["--salida", temporal]))
        self.assertEqual(antes, (RAIZ / "sitemap.xml").read_bytes())


if __name__ == "__main__":
    unittest.main()
