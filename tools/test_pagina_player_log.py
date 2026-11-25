#!/usr/bin/env python3
"""ML-343 y ML-344 (LOG-01, LOG-02, LOG-03): la guía /player-log/ y su par /es/player-log/: textos exactos, datos estructurados, hreflang, sitemap y enlaces. Sin red.

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
from test_enlaces_internos import rotos_de_html

PAGINA = RAIZ / "player-log" / "index.html"
PAGINA_ES = RAIZ / "es" / "player-log" / "index.html"
URL = "https://manalab.es/player-log/"
URL_ES = "https://manalab.es/es/player-log/"
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
TITULO_ES = "Player.log de MTG Arena: dónde está y por qué está vacío"
DESCRIPCION_ES = ("Encuentra el Player.log de MTG Arena, qué es Player-prev.log y cómo arreglar un log sin partidas. "
                  "Paso a paso, con el único ajuste que importa.")
H1_ES = "¿Dónde está el Player.log de MTG Arena y por qué está vacío?"
PRIMER_PARRAFO_ES = ('Arena escribe su registro en un archivo llamado Player.log. En el PC está en C:\\Users\\<tu usuario>\\AppData\\LocalLow\\Wizards Of The Coast\\MTGA\\. '
                     'Si el archivo existe pero no tiene partidas, la causa casi siempre es la misma: Arena solo escribe los datos de tus partidas cuando '
                     '«Registro detallado» («Detailed Logs (Plugin Support)», en inglés) está activado. Actívalo, reinicia Arena y juega una partida.')
PREGUNTAS_ES = {
    "¿Es seguro abrir Player.log?": "Sí. Es un archivo de texto; abrirlo o copiarlo no cambia nada.",
    "¿Dónde está el registro de Magic Online?": "Magic Online escribe mtgo.log sin que tengas que activar nada.",
}
FRASES_EXACTAS_ES = (
    "Haz clic en la barra de direcciones, pega %appdata%\\..\\LocalLow\\Wizards Of The Coast\\MTGA y pulsa Intro.",
    "AppData es una carpeta oculta; por eso no la encuentras navegando a mano.",
    "Arena guarda tu sesión anterior. Al cerrar y volver a abrir el juego, el registro anterior se guarda como Player-prev.log en la misma carpeta.",
    "Si acabas de reiniciar Arena y tu partida no está en Player.log, búscala en Player-prev.log.",
    "En Arena: Opciones › Cuenta. Sin él, el registro solo trae información técnica básica y ninguno de los datos de partida que necesita un tracker.",
    "El ajuste se aplica al volver a abrirlo.",
    "El archivo solo se llena mientras juegas.",
    "Dentro de la carpeta de instalación de Arena hay otros archivos .log; el que importa es Player.log en LocalLow, no esos.",
    "Si las cuatro están bien y el archivo sigue vacío, envíanos el archivo y la fecha en que se escribió. Preferimos mirarlo a adivinar.",
    "ManaLab lee Player.log y la base de cartas de Arena sin modificarlos. No lee la memoria de Arena ni se conecta a los servidores de Wizards.",
    "Actualizado el 20 de noviembre de 2026 · ManaLab",
)
H2_ES = ["Dónde encontrarlo", "Qué es Player-prev.log", "Cuando Player.log está vacío o no tiene partidas", "Qué hace ManaLab con él", "Preguntas"]
ETI_ES = ["MTG Arena · Player.log", "Dónde está", "Sesión anterior", "Solución de problemas", "ManaLab", "Preguntas"]
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
        self.links_a = []
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
            self.links_a.append(a)
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
        nodos += dato.get("@graph", [dato])
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
        h2 = re.findall(r"<h2>(.*?)</h2>", PAGINA.read_text(encoding="utf-8"), re.DOTALL)
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

    def test_hreflang_reciproco_y_selector_de_idioma(self):
        """La inglesa y la española se declaran la una a la otra, las dos con x-default a la inglesa, y el selector de idioma enlaza al par."""
        esperado = [("en", URL), ("es", URL_ES), ("x-default", URL)]
        for ruta, selector in ((PAGINA, ("es", "/es/player-log/")), (PAGINA_ES, ("en", "/player-log/"))):
            lector = Lector(ruta.read_text(encoding="utf-8"))
            with self.subTest(pagina=ruta.parent.name, idioma=ruta.parts[-3]):
                self.assertEqual([(x["hreflang"], x["href"]) for x in lector.links if x.get("rel") == "alternate"], esperado)
                selectores = [(x["hreflang"], x["href"]) for x in lector.links_a if "idioma" in x.get("class", "")]
                self.assertEqual(selectores, [(selector[0], selector[1])] * 2, "selector de escritorio y del menú del teléfono")

    def test_sin_anuncio_de_mdn(self):
        for ruta in (PAGINA, PAGINA_ES):
            html = ruta.read_text(encoding="utf-8")
            with self.subTest(ruta=str(ruta.relative_to(RAIZ))):
                for marca in ("anuncio-casa", "hueco-mdn", "HUECO_MDN", ">Publicidad<", ">Advertisement<"):
                    self.assertNotIn(marca, html)


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

    def test_estan_en_el_sitemap_una_vez_cada_una_y_con_alternates(self):
        sitemap = (RAIZ / "sitemap.xml").read_text(encoding="utf-8")
        for url in (URL, URL_ES):
            self.assertEqual(sitemap.count(f"<loc>{url}</loc>"), 1, url)
            bloque = re.search(r"<url>\s*<loc>" + re.escape(url) + r"</loc>.*?</url>", sitemap, re.DOTALL).group(0)
            self.assertEqual(re.findall(r'hreflang="([^"]+)" href="([^"]+)"', bloque),
                             [("en", URL), ("es", URL_ES), ("x-default", URL)], url)

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


class TestTextosEs(unittest.TestCase):
    """ML-344: /es/player-log/ con el texto exacto que escribió el coordinador por encargo de Eusebio."""

    @classmethod
    def setUpClass(cls):
        cls.p = Lector(PAGINA_ES.read_text(encoding="utf-8"))
        cls.html = PAGINA_ES.read_text(encoding="utf-8")
        # el lector separa con un espacio lo que va dentro de <code> y de enlaces: se quita ese espacio antes de la puntuación
        cls.visible = re.sub(r" ([.,;])(?!\w)", r"\1", normal(" ".join(cls.p.texto_main)))

    def test_titulo_descripcion_y_canonical(self):
        self.assertEqual(normal(self.p.titulo), TITULO_ES)
        self.assertEqual(len(TITULO_ES), 56)
        self.assertEqual(len(DESCRIPCION_ES), 143)
        for clave in ("description", "og:description", "twitter:description"):
            self.assertEqual(self.p.meta[clave], DESCRIPCION_ES, clave)
        for clave in ("og:title", "twitter:title"):
            self.assertEqual(self.p.meta[clave], TITULO_ES, clave)
        self.assertEqual([x["href"] for x in self.p.links if x.get("rel") == "canonical"], [URL_ES])
        self.assertEqual(self.p.meta["og:url"], URL_ES)
        self.assertEqual(self.p.meta["og:locale"], "es_ES")
        self.assertIn('<html lang="es">', self.html)

    def test_h1_y_primer_parrafo_exactos_y_sin_windows(self):
        self.assertEqual(normal(self.p.h1), H1_ES)
        self.assertEqual(normal(self.p.sub), PRIMER_PARRAFO_ES)
        for sitio, texto in (("título", TITULO_ES), ("H1", self.p.h1), ("primer párrafo", self.p.sub), ("descripción", DESCRIPCION_ES)):
            self.assertNotIn("windows", texto.lower().replace("wizards of the coast", ""), sitio)

    def test_frases_exactas_del_encargo(self):
        for frase in FRASES_EXACTAS_ES:
            self.assertIn(frase, self.visible)

    def test_los_h2_y_los_antetitulos_y_su_orden(self):
        self.assertEqual(re.findall(r"<h2>(.*?)</h2>", self.html, re.DOTALL)[:5], H2_ES)
        self.assertEqual(re.findall(r'<div class="eti">(.*?)</div>', self.html)[:6], ETI_ES)

    def test_menu_de_la_cabecera(self):
        cabecera = self.html.split("<header", 1)[1].split("</header>", 1)[0]
        self.assertEqual(re.findall(r'<a href="(#[a-z]+)">(.*?)</a>', cabecera),
                         [("#donde", "Dónde está"), ("#vacio", "Log vacío"), ("#preguntas", "Preguntas")] * 2, "escritorio y menú del teléfono")

    def test_las_rutas_son_codigo_seleccionable_con_un_clic(self):
        self.assertEqual(len(re.findall(r'<code class="ruta-copiable">', self.html)), 2)
        self.assertRegex(self.html, r"\.ruta-copiable\s*\{[^}]*user-select:\s*all")

    def test_la_descarga_lleva_los_textos_de_registro_detallado(self):
        modelo = normal(" ".join(Lector((RAIZ / "es/registro-detallado/index.html").read_text(encoding="utf-8")).texto_main))
        for texto in ("Descargar gratis", "otras versiones", "Requisitos: Windows 10 u 11. Descomprime el ZIP y abre ManaLab.exe. No hace falta instalar nada.",
                      "¿Es seguro? Compruébalo tú mismo →"):
            self.assertIn(texto, self.visible)
            self.assertIn(texto, modelo)
        self.assertIn('data-url="https://manalab.es/es/player-log/"', self.html)
        self.assertIn("descarga-player-log-es", self.html)


class TestDatosEstructuradosEs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = Lector(PAGINA_ES.read_text(encoding="utf-8"))
        cls.nodos = grafo(cls.p)

    def tipo(self, nombre):
        return [n for n in self.nodos if n.get("@type") == nombre]

    def test_article_en_espanol(self):
        (articulo,) = self.tipo("Article")
        self.assertEqual(articulo["headline"], H1_ES)
        self.assertEqual(articulo["inLanguage"], "es")
        self.assertEqual(articulo["description"], DESCRIPCION_ES)
        self.assertEqual((articulo["datePublished"], articulo["dateModified"]), ("2026-11-20", "2026-11-20"))
        self.assertEqual(articulo["mainEntityOfPage"], URL_ES)

    def test_faqpage_identico_al_texto_visible(self):
        (faq,) = self.tipo("FAQPage")
        self.assertEqual(faq["inLanguage"], "es")
        del_json = {q["name"]: q["acceptedAnswer"]["text"] for q in faq["mainEntity"]}
        self.assertEqual(del_json, PREGUNTAS_ES)
        self.assertEqual({k: normal(v) for k, v in self.p.respuestas.items()}, PREGUNTAS_ES)
        self.assertEqual(len(re.findall(r"<details open>", PAGINA_ES.read_text(encoding="utf-8"))), 2)

    def test_migas_inicio_y_guia_del_player_log(self):
        (migas,) = self.tipo("BreadcrumbList")
        self.assertEqual([(e["position"], e["name"], e["item"]) for e in migas["itemListElement"]],
                         [(1, "Inicio", "https://manalab.es/es/"), (2, "Guía del Player.log", URL_ES)])


class TestEnlacesEs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = Lector(PAGINA_ES.read_text(encoding="utf-8"))

    def test_todos_sus_enlaces_internos_existen(self):
        self.assertEqual(rotos_de_html(PAGINA_ES.read_text(encoding="utf-8"), PAGINA_ES), [])

    def test_enlaces_de_salida(self):
        destinos = {}
        for h, t, en_main in self.p.enlaces:
            if en_main:
                destinos.setdefault(h, []).append(normal(t))
        self.assertEqual(destinos["/es/registro-detallado/"], ["«Registro detallado»"])
        self.assertEqual(destinos["/es/seguridad/"][0], "Cómo comprobarlo →")
        self.assertEqual(destinos["/es/#contacto"], ["envíanos"], "el mismo contacto que la portada española")
        self.assertEqual(destinos["/es/magic-online/"], ["Magic Online"])
        self.assertTrue(any("-portable.zip" in h for h in destinos), "botón de descarga")
        self.assertNotIn("/detailed-logs/", destinos)

    def test_enlaces_de_entrada(self):
        """Registro-detallado (con su texto y su estilo) y la guía española enlazan a la página; el primer «Player.log» de la guía es el enlazado."""
        html = (RAIZ / "es/registro-detallado/index.html").read_text(encoding="utf-8")
        textos = [normal(t) for h, t, _ in Lector(html).enlaces if h == "/es/player-log/"]
        self.assertEqual(textos, ["¿El log está vacío o no tiene partidas? Mira qué hacer →"])
        self.assertIn('<p class="enlace-seccion"><a class="enlace-man" href="/es/player-log/">', html)
        guia = (RAIZ / "guia/guia_manalab_es.html").read_text(encoding="utf-8")
        cuerpo = guia.split("</header>", 1)[1]
        enlace = '<a href="/es/player-log/">Player.log</a>'
        self.assertEqual(cuerpo.count(enlace), 1)
        self.assertEqual(cuerpo.index("Player.log"), cuerpo.index(enlace) + len('<a href="/es/player-log/">'),
                         "es el primer «Player.log» del texto de la guía")

    def test_la_portada_espanola_no_recibe_enlace(self):
        self.assertNotIn("/es/player-log/", [h for h, _, _ in Lector((RAIZ / "es/index.html").read_text(encoding="utf-8")).enlaces])


if __name__ == "__main__":
    unittest.main()
