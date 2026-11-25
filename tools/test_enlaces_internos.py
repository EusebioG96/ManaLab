#!/usr/bin/env python3
"""ML-280 (RED-05): ninguna URL interna lleva a un 404. Sin red.

Comprueba, sobre el HTML publicado, que cada ``<loc>`` de sitemap.xml y cada enlace interno (``href`` que empieza por ``/`` o por
``https://manalab.es/``) apunta a un archivo que existe en el sitio: ``ruta/index.html`` para una carpeta, o el propio archivo. Las
anclas (``#...``) solo exigen que exista la página; un ``href="#x"`` apunta a la propia página. También se miran los
``<link rel="canonical|alternate">`` y los ``xhtml:link`` del sitemap (hreflang), que Search Console también rastrea.

Uso:  python3 tools/test_enlaces_internos.py
"""
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

RAIZ = Path(__file__).resolve().parent.parent
SITIO = "https://manalab.es"
NO_PUBLICADO = {".git", ".github", "plantillas", "docs", "tools"}
LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
HREF_SITEMAP = re.compile(r'<xhtml:link\b[^>]*\bhref="([^"]+)"')
ESQUEMAS_AJENOS = ("mailto:", "tel:", "javascript:", "data:")


class _Enlaces(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.enlaces = []  # (href, línea)

    def handle_starttag(self, etiqueta, atributos):
        a = {k: (v or "") for k, v in atributos}
        if etiqueta == "a" and "href" in a:
            self.enlaces.append((a["href"], self.getpos()[0]))
        elif etiqueta == "link" and a.get("rel") in ("canonical", "alternate") and "href" in a:
            self.enlaces.append((a["href"], self.getpos()[0]))


def paginas_html() -> list[Path]:
    return sorted(p for p in RAIZ.rglob("*.html") if not NO_PUBLICADO & set(p.relative_to(RAIZ).parts))


def archivo_de(ruta_url: str, raiz: Path = RAIZ) -> Path:
    """Archivo que sirve una ruta de URL: ``/es/`` -> es/index.html; ``/img/a.png`` -> img/a.png; ``/safety`` -> safety/index.html o safety."""
    limpia = unquote(ruta_url).lstrip("/")
    if limpia == "" or limpia.endswith("/"):
        return raiz / limpia / "index.html"
    destino = raiz / limpia
    if destino.is_file():
        return destino
    return destino / "index.html"


def es_interno(href: str) -> bool:
    if href.startswith(ESQUEMAS_AJENOS) or href.startswith("//"):
        return False
    return href.startswith("/") or href == SITIO or href.startswith(SITIO + "/") or href.startswith("#")


def rotos_de_html(texto: str, pagina: Path, raiz: Path = RAIZ) -> list[str]:
    """Enlaces internos de una página cuyo destino no existe, como «archivo:línea: href»."""
    analizador = _Enlaces()
    analizador.feed(texto)
    rel = pagina.relative_to(raiz).as_posix()
    url_propia = "/" + (rel[: -len("index.html")] if rel.endswith("index.html") else rel)
    salida = []
    for href, linea in analizador.enlaces:
        if not es_interno(href):
            continue
        if href.startswith("#"):
            continue  # ancla de la propia página: la página existe, que es lo que se comprueba
        ruta = urlparse(href[len(SITIO):] if href.startswith(SITIO) else href).path or url_propia
        if not archivo_de(ruta, raiz).is_file():
            salida.append(f"{rel}:{linea}: {href}")
    return salida


def rotos_de_sitemap(texto: str, raiz: Path = RAIZ) -> list[str]:
    salida = []
    for patron in (LOC, HREF_SITEMAP):
        for m in patron.finditer(texto):
            url = m.group(1)
            if not (url == SITIO or url.startswith(SITIO + "/")):
                salida.append(f"sitemap.xml: {url} no es de {SITIO}")
                continue
            ruta = urlparse(url[len(SITIO):] or "/").path or "/"
            if not archivo_de(ruta, raiz).is_file():
                salida.append(f"sitemap.xml: {url}")
    return salida


class TestEnlacesInternos(unittest.TestCase):
    def test_hay_paginas_y_sitemap(self):
        self.assertGreaterEqual(len(paginas_html()), 25)
        self.assertGreaterEqual(len(LOC.findall((RAIZ / "sitemap.xml").read_text(encoding="utf-8"))), 20)

    def test_cada_url_del_sitemap_existe(self):
        rotos = rotos_de_sitemap((RAIZ / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertEqual(rotos, [], "URL del sitemap sin archivo: " + "; ".join(rotos))

    def test_cada_enlace_interno_de_las_paginas_existe(self):
        rotos = []
        for pagina in paginas_html():
            rotos += rotos_de_html(pagina.read_text(encoding="utf-8"), pagina)
        self.assertEqual(rotos, [], "enlaces internos rotos (archivo:línea: href): " + "; ".join(rotos))

    def test_se_comprueban_enlaces_de_verdad(self):
        total = 0
        for pagina in paginas_html():
            a = _Enlaces()
            a.feed(pagina.read_text(encoding="utf-8"))
            total += sum(1 for h, _ in a.enlaces if es_interno(h))
        self.assertGreaterEqual(total, 300)


class TestDetectaRotos(unittest.TestCase):
    """El comprobador de verdad detecta lo roto (sobre un sitio de mentira)."""

    def setUp(self):
        import tempfile
        self.carpeta = tempfile.TemporaryDirectory()
        self.raiz = Path(self.carpeta.name)
        (self.raiz / "es").mkdir()
        (self.raiz / "es" / "index.html").write_text("x", encoding="utf-8")
        (self.raiz / "index.html").write_text("x", encoding="utf-8")
        (self.raiz / "robots.txt").write_text("x", encoding="utf-8")

    def tearDown(self):
        self.carpeta.cleanup()

    def test_enlaces_buenos_y_malos(self):
        html = ('<a href="/es/">a</a><a href="https://manalab.es/">b</a><a href="/robots.txt">c</a><a href="#x">d</a>'
                '<a href="/es/#descargar">e</a><a href="https://otro.com/x">f</a><a href="mailto:a@b.c">g</a>'
                '<a href="/no-existe/">MAL1</a><a href="https://manalab.es/es/seguridad/">MAL2</a>')
        rotos = rotos_de_html(html, self.raiz / "index.html", self.raiz)
        self.assertEqual([r.split(": ", 1)[1] for r in rotos], ["/no-existe/", "https://manalab.es/es/seguridad/"])

    def test_sitemap(self):
        xml = ("<url><loc>https://manalab.es/</loc></url><url><loc>https://manalab.es/es/</loc></url>"
               "<url><loc>https://manalab.es/inventada/</loc></url>")
        self.assertEqual(rotos_de_sitemap(xml, self.raiz), ["sitemap.xml: https://manalab.es/inventada/"])


if __name__ == "__main__":
    unittest.main()
