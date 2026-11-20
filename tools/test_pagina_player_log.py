#!/usr/bin/env python3
"""ML-343 (LOG-01, LOG-02, LOG-03): la guía /player-log/ (solo inglés): textos exactos, datos estructurados, sitemap y enlaces. Sin red.

Uso:  python3 -m pytest -q tools/test_pagina_player_log.py
"""
import json
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from test_enlaces_internos import rotos_de_html  # noqa: E402

PAGINA = RAIZ / "player-log" / "index.html"
URL = "https://manalab.es/player-log/"
TITULO = "MTG Arena Player.log: Where It Is and Why It's Empty"
DESCRIPCION = ("Find MTG Arena's Player.log, learn what Player-prev.log is and fix a log with no games in it. "
               "Step by step, with the one setting that matters.")
H1 = "Where is MTG Arena's Player.log, and why is it empty?"
PRIMER_PARRAFO = ('Arena writes its log to a file called Player.log. On a PC it is in C:\\Users\\<your user>\\AppData\\LocalLow\\Wizards Of The Coast\\MTGA\\. '
                  'If the file exists but has no games in it, the cause is almost always the same: Arena only writes your match data when '
                  '"Detailed Logs (Plugin Support)" is turned on. Turn it on, restart Arena, and play one game.')
PREGUNTAS = {
    "Is it safe to open Player.log?": "Yes. It's a text file; opening or copying it changes nothing.",
    "Where is the Magic Online log?": "Magic Online writes mtgo.log with nothing to turn on.",
}
# Frases del encargo que van tal cual (marketing las fijó; no se reescriben)
FRASES_EXACTAS = (
    "Click the address bar, paste %appdata%\\..\\LocalLow\\Wizards Of The Coast\\MTGA and press Enter.",
    "AppData is a hidden folder, which is why browsing for it by hand fails.",
    "Arena keeps your last session. When you close and reopen the game, the previous log is saved as Player-prev.log in the same folder.",
    "In Arena: Options › Account. Without it, the log has only basic technical output and none of the game data a tracker needs.",
    "The setting applies on the next launch.",
    "The file only fills as you play.",
    "If all four are right and the file is still empty, send us the file and the date it was written. We'd rather look at it than guess.",
    "ManaLab reads Player.log and Arena's card database without modifying them. It does not read Arena's memory and does not connect to Wizards' servers.",
    "Updated 20 November 2026 · ManaLab",
)
# Lo que el encargo deja FUERA porque no está comprobado
PROHIBIDO = ("Arena closed or open", "Can I delete Player.log", "account name", "username", "~/Library", "macOS", "Mac ")


class Lector(HTMLParser):
    """Lo que estos tests miran: metadatos, texto visible del cuerpo, enlaces con su texto y JSON-LD."""

    def __init__(self, texto: str):
        super().__init__(convert_charrefs=True)
        self.titulo, self.meta, self.links, self.jsonld, self.scripts = "", {}, [], [], []
        self.enlaces, self.h1, self.sub = [], "", ""
        self.texto_main, self.respuestas = [], {}
        self._pila, self._ld, self._href, self._en_main, self._pregunta = [], None, None, False, None
        self.feed(texto)

    def handle_starttag(self, tag, attrs):
        a = {k: v or "" for k, v in attrs}
        self._pila.append((tag, a))
        if tag == "meta":
            self.meta[a.get("name") or a.get("property")] = a.get("content", "")
        elif tag == "link":
            self.links.append(a)
        elif tag == "script":
            self.scripts.append(a)
            if a.get("type") == "application/ld+json":
                self._ld = ""
        elif tag == "main":
            self._en_main = True
        elif tag == "a" and a.get("href"):
            self._href = a["href"]
            self.enlaces.append([a["href"], "", self._en_main])

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.jsonld.append(self._ld)
            self._ld = None
        elif tag == "a":
            self._href = None
        elif tag == "main":
            self._en_main = False
        while self._pila and self._pila[-1][0] != tag:
            self._pila.pop()
        if self._pila:
            self._pila.pop()

    def handle_data(self, data):
        etiquetas = [t for t, _ in self._pila]
        if self._ld is not None:
            self._ld += data
        if "title" in etiquetas:
            self.titulo += data
        if self._href is not None:
            self.enlaces[-1][1] += data
        if not self._en_main or "script" in etiquetas or "style" in etiquetas:
            return
        self.texto_main.append(data)
        if "h1" in etiquetas:
            self.h1 += data
        if "p" in etiquetas and ("class", "sub") in [kv for _, a in self._pila for kv in a.items()]:
            self.sub += data
        if "details" in etiquetas:
            if "summary" in etiquetas:
                self._pregunta = (self._pregunta or "") + data
            else:
                self.respuestas.setdefault(" ".join(self._pregunta.split()), "")
                self.respuestas[" ".join(self._pregunta.split())] += data
        else:
            self._pregunta = None


def normal(texto: str) -> str:
    return " ".join(texto.split())


def leer() -> Lector:
    return Lector(PAGINA.read_text(encoding="utf-8"))


def grafo(lector: Lector) -> list[dict]:
    nodos = []
    for bruto in lector.jsonld:
        dato = json.loads(bruto)
        nodos += dato["@graph"] if "@graph" in dato else [dato]
    return nodos


class TestTextos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = leer()
        cls.visible = normal(" ".join(cls.p.texto_main))

    def test_titulo_descripcion_y_canonical(self):
        self.assertEqual(normal(self.p.titulo), TITULO)
        for clave in ("description", "og:description", "twitter:description"):
            self.assertEqual(self.p.meta[clave], DESCRIPCION, clave)
        for clave in ("og:title", "twitter:title"):
            self.assertEqual(self.p.meta[clave], TITULO, clave)
        self.assertEqual([x["href"] for x in self.p.links if x.get("rel") == "canonical"], [URL])
        self.assertEqual(self.p.meta["og:url"], URL)

    def test_h1_y_primer_parrafo_exactos_y_sin_windows(self):
        self.assertEqual(normal(self.p.h1), H1)
        self.assertEqual(normal(self.p.sub), PRIMER_PARRAFO)
        for sitio, texto in (("título", TITULO), ("H1", self.p.h1), ("primer párrafo", self.p.sub), ("descripción", DESCRIPCION)):
            self.assertNotIn("windows", texto.lower().replace("wizards of the coast", ""), sitio)

    def test_frases_exactas_del_encargo(self):
        for frase in FRASES_EXACTAS:
            self.assertIn(frase, self.visible)

    def test_los_h2_y_su_orden(self):
        h2 = re.findall(r"<h2>(.*?)</h2>", PAGINA.read_text(encoding="utf-8"), re.S)
        self.assertEqual(h2[:5], ["Where to find it", "What Player-prev.log is", "When Player.log is empty or has no games",
                                  "What ManaLab does with it", "Questions"])

    def test_lo_no_comprobado_no_esta(self):
        for fuera in PROHIBIDO:
            self.assertNotIn(fuera.lower(), self.visible.lower(), fuera)

    def test_las_rutas_son_codigo_seleccionable_con_un_clic_y_sin_js_nuevo(self):
        html = PAGINA.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'<code class="ruta-copiable">', html)), 2)
        self.assertRegex(html, r"\.ruta-copiable\s*\{[^}]*user-select:\s*all")
        self.assertEqual(sorted(s.get("src", "inline") for s in self.p.scripts if s.get("type") != "application/ld+json"),
                         ["//gc.zgo.at/count.js", "/descarga.js"])

    def test_sin_par_en_espanol(self):
        html = PAGINA.read_text(encoding="utf-8")
        self.assertEqual([x for x in self.p.links if x.get("rel") == "alternate"], [])
        self.assertNotIn("hreflang", html.split("</head>")[0])
        self.assertNotIn("/es/player-log", html)
        self.assertNotIn('class="idioma"', html)


class TestDatosEstructurados(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = leer()
        cls.nodos = grafo(cls.p)

    def tipo(self, nombre):
        return [n for n in self.nodos if n.get("@type") == nombre]

    def test_article(self):
        (articulo,) = self.tipo("Article")
        self.assertEqual(articulo["headline"], H1)
        self.assertEqual(articulo["datePublished"], "2026-11-20")
        self.assertEqual(articulo["dateModified"], "2026-11-20")
        self.assertEqual(articulo["inLanguage"], "en")
        self.assertEqual(articulo["description"], DESCRIPCION)
        self.assertEqual(articulo["author"], {"@id": "https://manalab.es/#org"})
        self.assertEqual(articulo["publisher"], {"@id": "https://manalab.es/#org"})
        (org,) = self.tipo("Organization")
        self.assertEqual((org["@id"], org["name"]), ("https://manalab.es/#org", "ManaLab"))

    def test_faqpage_es_identico_al_texto_visible(self):
        (faq,) = self.tipo("FAQPage")
        del_json = {q["name"]: q["acceptedAnswer"]["text"] for q in faq["mainEntity"]}
        self.assertEqual(del_json, PREGUNTAS)
        visibles = {k: normal(v) for k, v in self.p.respuestas.items()}
        self.assertEqual(visibles, PREGUNTAS, "las preguntas y respuestas visibles son las del JSON-LD")

    def test_migas_generadas_por_el_proceso(self):
        (migas,) = self.tipo("BreadcrumbList")
        self.assertEqual([(e["position"], e["name"], e["item"]) for e in migas["itemListElement"]],
                         [(1, "Home", "https://manalab.es/"), (2, "Player.log guide", URL)])

    def test_las_respuestas_de_la_faq_estan_a_la_vista(self):
        html = PAGINA.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"<details open>", html)), 2, "FAQ visible: abierta desde el principio")


class TestSitemapYEnlaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = leer()

    def test_esta_en_el_sitemap_una_vez_y_sin_alternates(self):
        sitemap = (RAIZ / "sitemap.xml").read_text(encoding="utf-8")
        self.assertEqual(sitemap.count(f"<loc>{URL}</loc>"), 1)
        bloque = re.search(r"<url>\s*<loc>" + re.escape(URL) + r"</loc>.*?</url>", sitemap, re.S).group(0)
        self.assertNotIn("hreflang", bloque)

    def test_todos_sus_enlaces_internos_existen(self):
        self.assertEqual(rotos_de_html(PAGINA.read_text(encoding="utf-8"), PAGINA), [])

    def test_enlaces_de_entrada(self):
        """Detailed-logs (con su texto) y la guía inglesa enlazan a la página; el primer Player.log de la guía es el enlazado."""
        detalle = Lector((RAIZ / "detailed-logs/index.html").read_text(encoding="utf-8"))
        textos = [normal(t) for h, t, _ in detalle.enlaces if h == "/player-log/"]
        self.assertEqual(textos, ["Log empty or no games in it? See what to do →"])
        html = (RAIZ / "detailed-logs/index.html").read_text(encoding="utf-8")
        self.assertIn('<p class="enlace-seccion"><a class="enlace-man" href="/player-log/">', html)
        guia = (RAIZ / "guia/guia_manalab_en.html").read_text(encoding="utf-8")
        cuerpo = guia.split("</header>", 1)[1]
        self.assertEqual(cuerpo.count('<a href="/player-log/">Player.log</a>'), 1)
        self.assertLess(cuerpo.index('<a href="/player-log/">'), cuerpo.index("Player.log", cuerpo.index("</a>", cuerpo.index('<a href="/player-log/">'))))
        self.assertEqual(cuerpo.index("Player.log"), cuerpo.index('<a href="/player-log/">Player.log</a>') + len('<a href="/player-log/">'),
                         "es el primer «Player.log» del texto de la guía")

    def test_enlaces_de_salida(self):
        destinos = {}
        for h, t, en_main in self.p.enlaces:
            if en_main:
                destinos.setdefault(h, []).append(normal(t))
        for h in ("/detailed-logs/", "/safety/", "/magic-online/"):
            self.assertIn(h, destinos, h)
        self.assertIn("How to check it →", destinos["/safety/"])
        self.assertEqual(destinos["/#contacto"], ["send us"])
        self.assertTrue(any("-portable.zip" in h for h in destinos), "botón de descarga")
        cabecera = [h for h, _, en_main in self.p.enlaces if not en_main]
        self.assertIn("#descargar", cabecera)

    def test_la_portada_no_recibe_enlace_si_no_tiene_pregunta_de_logs(self):
        """La FAQ de la portada inglesa no tiene pregunta sobre logs o Detailed Logs: no se le añade enlace (decisión del encargo)."""
        portada = Lector((RAIZ / "index.html").read_text(encoding="utf-8"))
        self.assertNotIn("/player-log/", [h for h, _, _ in portada.enlaces])
        preguntas = " ".join(re.findall(r"<summary>(.*?)</summary>", (RAIZ / "index.html").read_text(encoding="utf-8")))
        self.assertNotRegex(preguntas.lower(), r"detailed logs|player\.log|\blogs?\b(?! (draft|and sealed))")


if __name__ == "__main__":
    unittest.main()
