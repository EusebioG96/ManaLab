#!/usr/bin/env python3
"""ML-157, tanda 3B de la auditoría web: dos páginas para búsquedas concretas, cada una en inglés y en español.
Registro detallado de Arena (/detailed-logs/, /es/registro-detallado/) y overlay (/overlay/, /es/overlay/). Sin red.

Uso:  python3 tools/test_paginas_busqueda.py
"""
import json
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITIO = "https://manalab.es"
PAGINAS = {
    "logs-en": dict(ruta="detailed-logs/index.html", lang="en", url="/detailed-logs/", otra="/es/registro-detallado/",
                    title="How to Enable Detailed Logs in MTG Arena · ManaLab", h1="How to enable detailed logs in MTG Arena",
                    evento="descarga-logs-en"),
    "logs-es": dict(ruta="es/registro-detallado/index.html", lang="es", url="/es/registro-detallado/", otra="/detailed-logs/",
                    title="Cómo activar el registro detallado en MTG Arena · ManaLab", h1="Cómo activar el registro detallado en MTG Arena",
                    evento="descarga-logs-es"),
    "overlay-en": dict(ruta="overlay/index.html", lang="en", url="/overlay/", otra="/es/overlay/",
                       title="Free MTG Arena Overlay and Deck Tracker · ManaLab", h1="A free overlay and deck tracker for MTG Arena",
                       evento="descarga-overlay-en"),
    "overlay-es": dict(ruta="es/overlay/index.html", lang="es", url="/es/overlay/", otra="/overlay/",
                       title="Overlay y deck tracker gratis para MTG Arena · ManaLab", h1="Overlay y deck tracker gratis para MTG Arena",
                       evento="descarga-overlay-es"),
}
PROHIBIDAS = ["Patreon", "igual que", "same as Arena", "sin anuncios", "utm_", "ad-free"]
ENLACES_INICIO = {
    "index.html": ["/detailed-logs/", "/overlay/"],
    "es/index.html": ["/es/registro-detallado/", "/es/overlay/"],
}


def leer(ruta):
    return (RAIZ / ruta).read_text(encoding="utf-8")


def quitar_etiquetas(fragmento):
    import html
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def cuerpo(html):
    return re.sub(r"<(script|style|template)\b.*?</\1>", "", html[html.index("<body"):], flags=re.S)


def hreflangs(html):
    return {m.group(2).lower(): m.group(1) for m in re.finditer(r'<link href="([^"]*)" hreflang="([^"]*)" rel="alternate"/>', html)}


class TestPaginas(unittest.TestCase):
    def paginas(self):
        return [(k, p, leer(p["ruta"])) for k, p in PAGINAS.items()]

    def test_existen_con_su_idioma_y_titulo_exacto(self):
        for k, p, html in self.paginas():
            self.assertRegex(html, r'<html lang="%s">' % p["lang"])
            self.assertEqual(re.search(r"<title>(.*?)</title>", html).group(1), p["title"])
            self.assertEqual(quitar_etiquetas(re.search(r"<h1>(.*?)</h1>", html, re.S).group(1)), p["h1"])
            self.assertEqual(html.count("<h1>"), 1)

    def test_canonical_hreflang_reciproco_og_y_goatcounter(self):
        for k, p, html in self.paginas():
            self.assertIn('<link href="%s%s" rel="canonical"/>' % (SITIO, p["url"]), html)
            en, es = (p["url"], p["otra"]) if p["lang"] == "en" else (p["otra"], p["url"])
            self.assertEqual(hreflangs(html), {"en": SITIO + en, "es": SITIO + es, "x-default": SITIO + en})
            otra = leer(next(q["ruta"] for q in PAGINAS.values() if q["url"] == p["otra"]))
            self.assertEqual(hreflangs(otra), hreflangs(html))                     # reciprocidad
            self.assertIn('<meta content="%s/img/og.jpg" property="og:image"/>' % SITIO if k.startswith("logs") else
                          '<meta content="%s/img/v22_overlay.jpg" property="og:image"/>' % SITIO, html)
            self.assertIn("https://manalab.goatcounter.com/count", html)
            self.assertNotIn("noindex", html)

    def test_sitemap_con_las_cuatro_urls_y_sus_alternates(self):
        sm = leer("sitemap.xml")
        self.assertEqual(sm.count("<url>"), 27)
        for k, p, _ in self.paginas():
            bloque = re.search(r"<url>\s*<loc>%s%s</loc>.*?</url>" % (SITIO, re.escape(p["url"])), sm, re.S)
            self.assertIsNotNone(bloque)
            self.assertEqual(sorted(re.findall(r'hreflang="([^"]*)"', bloque.group(0))), ["en", "es", "x-default"])

    def test_un_boton_de_descarga_con_su_titulo_de_goatcounter(self):
        for k, p, html in self.paginas():
            botones = re.findall(r'<a [^>]*data-goatcounter-click="descarga"[^>]*>', html)
            self.assertEqual(len(botones), 1)
            self.assertIn('data-goatcounter-title="%s"' % p["evento"], botones[0])
            self.assertIn('id="enlace-descarga"', botones[0])
            self.assertIn("data-descarga", botones[0])
            self.assertIn('<template id="bloque-movil">', html)                       # caja de móvil de descarga.js
            self.assertIn('<script defer="" src="/descarga.js"></script>', html)

    def test_sin_palabras_prohibidas(self):
        for k, p, html in self.paginas():
            for palabra in PROHIBIDAS:
                self.assertNotIn(palabra.lower(), html.lower(), palabra)
            if p["lang"] == "es":
                self.assertNotIn("play/draw", html.lower())
                self.assertNotIn("play or draw", html.lower())
            self.assertNotRegex(cuerpo(html), r"\b20(2[6-9]|3\d)\b")                  # ni fechas futuras ni años sueltos
            # «Windows» solo en los requisitos (ni titular, ni descripción, ni botones)
            for m in re.finditer(r"Windows", cuerpo(html)):
                self.assertRegex(cuerpo(html)[m.start() - 15:m.start() + 20], r"(Requisitos|Requirements): Windows 10 (u|or) 11")
            self.assertNotIn("Windows", re.search(r"<head>.*?</head>", html, re.S).group(0))

    def test_no_nombra_otros_trackers(self):
        for k, p, html in self.paginas():
            for otro in ("Untapped", "17lands", "Draftsmith", "MTGA Assistant", "Aetherhub", "MTGGoldfish Arena"):
                self.assertNotIn(otro.lower(), cuerpo(html).lower(), otro)


class TestRegistroDetallado(unittest.TestCase):
    def test_howto_valido_y_con_los_mismos_pasos_que_la_lista(self):
        for k in ("logs-en", "logs-es"):
            html = leer(PAGINAS[k]["ruta"])
            with self.subTest(pagina=k):
                ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
                tipos = [n["@type"] for n in ld["@graph"]]
                self.assertEqual(tipos, ["WebPage", "HowTo"])
                howto = ld["@graph"][1]
                visibles = [quitar_etiquetas(x) for x in re.findall(r"<li>(.*?)</li>", re.search(r'<ol class="pasos-reg".*?</ol>', html, re.S).group(0), re.S)]
                self.assertEqual(len(visibles), 3)
                self.assertEqual([s["text"] for s in howto["step"]], visibles)
                self.assertEqual([s["position"] for s in howto["step"]], [1, 2, 3])

    def test_nombre_literal_de_la_opcion_y_enlaces(self):
        en, es = leer("detailed-logs/index.html"), leer("es/registro-detallado/index.html")
        self.assertIn("Options › Account › Detailed Logs (Plugin Support)", en)
        self.assertIn("Opciones › Cuenta › Registro detallado", es)
        self.assertIn('href="/safety/"', en)
        self.assertIn('href="/es/seguridad/"', es)
        self.assertIn('href="/magic-online/"', en)
        self.assertIn('href="/es/magic-online/"', es)

    def test_los_pasos_van_antes_que_todo_lo_demas(self):
        for k in ("logs-en", "logs-es"):
            html = leer(PAGINAS[k]["ruta"])
            with self.subTest(pagina=k):
                self.assertLess(html.index('<ol class="pasos-reg"'), html.index('id="lee"'))
                self.assertLess(html.index('id="lee"'), html.index('id="mtgo"'))
                self.assertLess(html.index('id="mtgo"'), html.index('id="descargar"'))


class TestOverlay(unittest.TestCase):
    def test_clip_e_imagen_existen_y_el_clip_no_se_descarga_hasta_reproducirlo(self):
        for k in ("overlay-en", "overlay-es"):
            html = leer(PAGINAS[k]["ruta"])
            with self.subTest(pagina=k):
                video = re.search(r"<video [^>]*>", html).group(0)
                self.assertIn('preload="none"', video)
                self.assertIn("controls", video)
                self.assertIn("muted", video)
                base = Path(PAGINAS[k]["ruta"]).parent
                for ref in re.findall(r'(?:src|poster|srcset)="([^"#]*)"', html):
                    if "video/funciones/09-in-game-overlay" in ref or "v22_overlay" in ref:
                        self.assertTrue((RAIZ / base / ref).resolve().exists(), ref)
                self.assertIn('<figure class="video" id="video-in-game-overlay">', html)
                self.assertTrue((RAIZ / "video/funciones/09-in-game-overlay.mp4").exists())
                self.assertIn("v22_overlay.webp", html)
                self.assertIn("v22_overlay.jpg", html)
                self.assertNotIn('<video autoplay', html)

    def test_enlaces_a_seguridad_y_a_magic_online(self):
        self.assertIn('href="/safety/"', leer("overlay/index.html"))
        self.assertIn('href="/magic-online/"', leer("overlay/index.html"))
        self.assertIn('href="/es/seguridad/"', leer("es/overlay/index.html"))
        self.assertIn('href="/es/magic-online/"', leer("es/overlay/index.html"))

    def test_magic_online_dice_lista_sin_confirmar_y_estado_de_la_mesa(self):
        self.assertIn("«Unconfirmed list»", leer("overlay/index.html"))
        self.assertIn("«Lista sin confirmar»", leer("es/overlay/index.html"))
        self.assertIn("table lines", leer("overlay/index.html"))
        self.assertIn("líneas de la mesa", leer("es/overlay/index.html"))

    def test_incluye_la_lista_de_tierras_de_la_2_3(self):
        self.assertIn("Lands list", leer("overlay/index.html"))
        self.assertIn("Lista de tierras", leer("es/overlay/index.html"))


class TestEnlacesInternos(unittest.TestCase):
    def test_portadas_enlazan_a_las_dos_paginas_en_el_cuerpo_y_en_el_pie(self):
        textos = {
            "index.html": ("How to turn it on, step by step →", "Overlay and deck tracker: what it shows →"),
            "es/index.html": ("Cómo activarlo, paso a paso →", "Overlay y deck tracker: qué muestra →"),
        }
        for ruta, (logs, overlay) in ENLACES_INICIO.items():
            html = leer(ruta)
            with self.subTest(portada=ruta):
                pie = html[html.index("<footer>"):]
                cuerpo_ = html[:html.index("<footer>")]
                self.assertEqual(len(re.findall(r'<a [^>]*href="%s"' % re.escape(ENLACES_INICIO[ruta][0]), cuerpo_)), 1)
                self.assertEqual(len(re.findall(r'<a [^>]*href="%s"' % re.escape(ENLACES_INICIO[ruta][1]), cuerpo_)), 1)
                self.assertIn(">%s</a>" % textos[ruta][0], cuerpo_)
                self.assertIn(">%s</a>" % textos[ruta][1], cuerpo_)
                for destino in ENLACES_INICIO[ruta]:
                    self.assertIn('href="%s"' % destino, pie)
                # el enlace del paso va dentro de «Get your game ready» y el del overlay dentro de su tarjeta
                paso = cuerpo_[cuerpo_.index(ENLACES_INICIO[ruta][0]) - 600:cuerpo_.index(ENLACES_INICIO[ruta][0])]
                self.assertRegex(paso, r"Detailed Logs|Registro detallado")
                tarjeta = cuerpo_[cuerpo_.index(ENLACES_INICIO[ruta][1]) - 900:cuerpo_.index(ENLACES_INICIO[ruta][1])]
                self.assertRegex(tarjeta, r"Overlay while you play|Overlay mientras juegas")

    def test_los_enlaces_internos_resuelven_a_un_archivo(self):
        for ruta in list(ENLACES_INICIO) + [p["ruta"] for p in PAGINAS.values()]:
            html = leer(ruta)
            for destino in ("/detailed-logs/", "/es/registro-detallado/", "/overlay/", "/es/overlay/"):
                if 'href="%s"' % destino in html:
                    self.assertTrue((RAIZ / destino.strip("/") / "index.html").exists(), destino)


if __name__ == "__main__":
    unittest.main()
