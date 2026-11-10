#!/usr/bin/env python3
"""ML-148, tanda 1 de la auditoría web: comprueba sobre los archivos (sin red) los puntos 1 a 9.

El punto 10 (quitar Patreon) se comprueba en tools/test_apoyo_kofi.py.

Uso:  python3 tools/test_tanda1.py
"""
import json
import re
import statistics
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
PORTADAS = {"en": RAIZ / "index.html", "es": RAIZ / "es" / "index.html"}
IDIOMAS_GUIA = ["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh"]
TEXTO_GUIA = {"en": "Download free", "es": "Descargar gratis", "fr": "Télécharger gratuitement", "de": "Kostenlos herunterladen",
              "it": "Scarica gratis", "pt": "Baixar grátis", "ja": "無料ダウンロード", "ko": "무료 다운로드", "zh": "免费下载"}
KOFI_TIERS = "https://ko-fi.com/eusebiog96/tiers"
KOFI = "https://ko-fi.com/eusebiog96"


def leer(ruta):
    return Path(ruta).read_text(encoding="utf-8")


class Enlaces(HTMLParser):
    """Todos los <a> con sus atributos, su texto y el contenedor (header / hero / nav.inicio / otro) donde están."""

    def __init__(self):
        super().__init__()
        self.enlaces = []
        self._pila = []
        self._a = None

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        self._pila.append((tag, a))
        if tag == "a":
            ctx = []
            for t, at in self._pila:
                if t == "header":
                    ctx.append("header")
                if t == "section" and "portada" in at.get("class", "").split():
                    ctx.append("hero")
                if t == "nav" and "inicio" in at.get("class", "").split():
                    ctx.append("nav.inicio")
                if t == "main":
                    ctx.append("main")
            self._a = {"attrs": a, "texto": "", "ctx": ctx}

    def handle_endtag(self, tag):
        if tag == "a" and self._a is not None:
            self._a["texto"] = " ".join(self._a["texto"].split())
            self.enlaces.append(self._a)
            self._a = None
        for i in range(len(self._pila) - 1, -1, -1):
            if self._pila[i][0] == tag:
                del self._pila[i:]
                break

    def handle_data(self, d):
        if self._a is not None:
            self._a["texto"] += d


def enlaces(ruta):
    p = Enlaces()
    p.feed(leer(ruta))
    return p.enlaces


def href_zip(ruta):
    for e in enlaces(ruta):
        if e["attrs"].get("id") == "enlace-descarga":
            return e["attrs"]["href"]
    raise AssertionError("falta #enlace-descarga")


class TestPuntos1y9Descarga(unittest.TestCase):
    def test_botones_de_cabecera_y_hero_descargan_el_zip(self):
        for idioma, ruta in PORTADAS.items():
            zip_ = href_zip(ruta)
            self.assertTrue(zip_.endswith("-portable.zip"))
            botones = [e for e in enlaces(ruta) if "descarga" in e["attrs"].get("class", "").split()
                       and "boton" in e["attrs"].get("class", "").split()]
            self.assertEqual(len(botones), 2, "cabecera y hero")
            for lugar, e in zip(("cabecera", "hero"), botones):
                with self.subTest(idioma=idioma, lugar=lugar):
                    a = e["attrs"]
                    self.assertEqual(a["href"], zip_)
                    self.assertEqual(a["class"].split(), ["boton", "prim", "descarga"])
                    for atributo in ("download", "data-a-bloque", "data-descarga"):
                        self.assertIn(atributo, a)
                    self.assertEqual(a.get("data-goatcounter-click"), "descarga")
                    self.assertEqual(a.get("data-goatcounter-title"), f"descarga-{lugar}-{idioma}")
                    self.assertIn("noopener", a.get("rel", "").split())

    def test_el_hero_sigue_teniendo_un_solo_boton(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                hero = [e for e in enlaces(ruta) if "hero" in e["ctx"] and "boton" in e["attrs"].get("class", "").split()]
                self.assertEqual(len(hero), 1)

    def test_descarga_js_baja_a_los_pasos_en_ordenador(self):
        js = leer(RAIZ / "descarga.js")
        self.assertIn("bajarALosPasos", js)
        self.assertIn("400", js)
        self.assertIn('addEventListener("click", bajarALosPasos)', js)

    def test_kofi_con_medicion(self):
        esperado = {"kofi-ia": KOFI_TIERS, "kofi-funciones": KOFI_TIERS, "kofi-apoyo": KOFI}
        for idioma, ruta in PORTADAS.items():
            todos = [e["attrs"] for e in enlaces(ruta) if e["attrs"].get("href") in (KOFI, KOFI_TIERS)]
            self.assertEqual(len(todos), 3)
            for base, href in esperado.items():
                with self.subTest(idioma=idioma, enlace=base):
                    a = [x for x in todos if x.get("data-goatcounter-title") == f"{base}-{idioma}"]
                    self.assertEqual(len(a), 1)
                    self.assertEqual(a[0]["href"], href)
                    self.assertEqual(a[0].get("data-goatcounter-click"), "apoyo")
            self.assertEqual([x.get("id") for x in todos if x.get("id")], ["enlace-donar"])


class TestPunto2CajaMovil(unittest.TestCase):
    def test_hueco_entre_sub_y_nota_desc(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                self.assertEqual(html.count("data-movil-aqui"), 1)
                self.assertRegex(html, r'<p class="sub">[^<]*</p>\s*<div data-movil-aqui></div>\s*<div class="nota-desc">')

    def test_css_y_js(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                self.assertIn("html.movil .aviso-version { display: none; }", html)
                self.assertIn("html.movil .hero-cta .boton { display: none; }", html)
        js = leer(RAIZ / "descarga.js")
        self.assertIn('querySelector("[data-movil-aqui]")', js)
        self.assertIn('classList.add("movil")', js)
        self.assertIn('classList.remove("movil")', js)


class TestPunto3Guias(unittest.TestCase):
    def test_dos_botones_con_el_href_de_su_idioma(self):
        for idioma in IDIOMAS_GUIA:
            with self.subTest(idioma=idioma):
                lista = enlaces(RAIZ / "guia" / f"guia_manalab_{idioma}.html")
                botones = [e for e in lista if "descargar" in e["attrs"].get("class", "").split()]
                self.assertEqual(len(botones), 2)
                for e in botones:
                    self.assertEqual(e["attrs"]["href"], "/es/#descargar" if idioma == "es" else "/#descargar")
                    self.assertEqual(e["attrs"].get("data-goatcounter-click"), "guia-descarga")
                    self.assertEqual(e["attrs"].get("data-goatcounter-title"), f"guia-descarga-{idioma}")
                    self.assertEqual(e["texto"], TEXTO_GUIA[idioma])
                    self.assertIn("nav.inicio", e["ctx"])

    def test_uno_arriba_y_otro_antes_del_footer(self):
        for idioma in IDIOMAS_GUIA:
            with self.subTest(idioma=idioma):
                html = leer(RAIZ / "guia" / f"guia_manalab_{idioma}.html")
                navs = [m.start() for m in re.finditer(r'<nav class="inicio"', html)]
                self.assertEqual(len(navs), 2)
                self.assertLess(navs[0], html.index("<header>"))
                self.assertLess(navs[1], html.index("<footer>"))
                self.assertGreater(navs[1], html.index("</section>", html.rindex('<section id="privacidad"')))
                self.assertRegex(html, r'<nav class="inicio" aria-label="ManaLab"><a class="descargar"[^>]*>[^<]*</a></nav>\s*<footer>')

    def test_inicio_en_espanol_va_a_es(self):
        html = leer(RAIZ / "guia" / "guia_manalab_es.html")
        self.assertIn('<a href="/es/">← Inicio de ManaLab</a>', html)

    def test_el_boton_no_sale_al_imprimir(self):
        for idioma in IDIOMAS_GUIA:
            with self.subTest(idioma=idioma):
                html = leer(RAIZ / "guia" / f"guia_manalab_{idioma}.html")
                imprimir = html.index("@media print")
                self.assertIn("nav.inicio,footer nav{display:none}", html[imprimir:])
                # el estilo del botón (display:flex) va antes que la regla de impresión, que es la que manda
                self.assertLess(html.index("nav.inicio a.descargar"), imprimir)
                self.assertLess(html.index("nav.inicio{margin:0 0 14px;font-size:.9rem;display:flex"), imprimir)


class TestPunto4Logo(unittest.TestCase):
    def test_logo_claro_se_ve_sobre_la_cabecera_oscura(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("falta Pillow")
        im = Image.open(RAIZ / "img" / "logo-claro.png").convert("RGBA")
        self.assertEqual(im.size, (120, 120))
        lum = [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b, a in im.get_flattened_data() if a > 60] \
            if hasattr(im, "get_flattened_data") else \
            [0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b, a in im.getdata() if a > 60]
        self.assertGreater(len(lum), 500)
        self.assertTrue(150 <= statistics.median(lum) <= 210, statistics.median(lum))

    def test_la_cabecera_usa_el_logo_claro_y_el_original_sigue_intacto(self):
        usadas = 0
        for ruta in RAIZ.rglob("*.html"):
            html = leer(ruta)
            for m in re.finditer(r'<a class="marca"[^>]*><img[^>]*src="([^"]*)"', html):
                usadas += 1
                self.assertTrue(m.group(1).endswith("img/logo-claro.png"), f"{ruta}: {m.group(1)}")
        self.assertEqual(usadas, 9)
        self.assertTrue((RAIZ / "img" / "logo.png").exists())


class TestPunto5Titulos(unittest.TestCase):
    def test_titulos(self):
        esperado = {"en": "ManaLab: Free MTG Arena &amp; Magic Online Tracker",
                    "es": "ManaLab: tracker gratis para MTG Arena y Magic Online"}
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                t = esperado[idioma]
                self.assertIn(f"<title>{t}</title>", html)
                self.assertIn(f'<meta content="{t}" property="og:title"/>', html)
                self.assertIn(f'<meta content="{t}" name="twitter:title"/>', html)


class TestPunto6Faq(unittest.TestCase):
    NUEVAS = {"en": ["Does it work on Mac or Linux?", "Does it log Draft and Sealed (Limited)?"],
              "es": ["¿Funciona en Mac o en Linux?", "¿Registra Draft y Sellado (Limitado)?"]}
    VIEJAS = ["Mac or for Limited", "Does it work on Linux?", "¿Funciona en Mac o en Limitado?", "¿Funciona en Linux?"]

    @staticmethod
    def faq_html(html):
        # cada <details> tiene su pregunta y uno o más <p>; se toma la respuesta completa
        return [(re.sub(r"<[^>]+>", "", q).strip(), " ".join(re.sub(r"<[^>]+>", " ", a).split()).replace(" .", "."))
                for q, a in re.findall(r"<details[^>]*><summary>(.*?)</summary>(.*?)</details>", html, re.S)]

    @staticmethod
    def faq_json(html):
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
        return [(q["name"], q["acceptedAnswer"]["text"]) for n in ld["@graph"] if n["@type"] == "FAQPage" for q in n["mainEntity"]]

    def test_preguntas_nuevas_en_html_y_json_ld(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                en_html, en_json = self.faq_html(html), self.faq_json(html)
                self.assertEqual(len(en_json), 8)
                for q in self.NUEVAS[idioma]:
                    r_html = [a for n, a in en_html if n == q]
                    r_json = [a for n, a in en_json if n == q]
                    self.assertEqual(len(r_html), 1, q)
                    self.assertEqual(len(r_json), 1, q)
                    self.assertEqual(r_html[0].replace("&#x27;", "'"), r_json[0])
                for v in self.VIEJAS:
                    self.assertNotIn(v, html)

    def test_todas_las_preguntas_del_json_ld_estan_en_el_html_con_el_mismo_texto(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                en_html = dict(self.faq_html(html))
                for q, a in self.faq_json(html):
                    self.assertIn(q, en_html)
                    # algunas respuestas del HTML añaden al final un enlace («Más detalles: …») que el JSON-LD no lleva
                    self.assertTrue(en_html[q].replace("&#x27;", "'").startswith(a), q)


class TestPunto7SorteoYSitemap(unittest.TestCase):
    def test_sorteo_noindex_y_fuera_del_sitemap(self):
        for ruta in (RAIZ / "sorteo" / "index.html", RAIZ / "sorteo" / "en" / "index.html"):
            with self.subTest(pagina=str(ruta.relative_to(RAIZ))):
                self.assertIn('<meta name="robots" content="noindex, follow">', leer(ruta))
        sitemap = leer(RAIZ / "sitemap.xml")
        self.assertNotIn("/sorteo", sitemap)
        self.assertEqual(sitemap.count("<loc>"), 19)

    def test_cada_url_del_sitemap_tiene_su_archivo(self):
        import actualizar_sitemap as u
        for loc in re.findall(r"<loc>([^<]+)</loc>", leer(RAIZ / "sitemap.xml")):
            with self.subTest(loc=loc):
                self.assertTrue((RAIZ / u.archivo_de(loc)).is_file(), u.archivo_de(loc))

    def test_actualizar_sitemap_solo_cambia_los_lastmod(self):
        import actualizar_sitemap as u
        texto = ('<urlset><url>\n    <loc>https://manalab.es/</loc>\n    <lastmod>2000-01-01</lastmod>\n'
                 '    <xhtml:link rel="alternate" hreflang="en" href="https://manalab.es/"/>\n  </url>\n'
                 '  <url>\n    <loc>https://manalab.es/no-existe/</loc>\n    <lastmod>2000-01-01</lastmod>\n  </url></urlset>')
        nuevo, cambios = u.actualizar(texto, RAIZ)
        self.assertEqual(len(cambios), 1)                                   # el archivo que no existe se deja como estaba
        self.assertEqual(cambios[0][0], "https://manalab.es/")
        self.assertRegex(cambios[0][2], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(re.sub(r"<lastmod>[^<]*</lastmod>", "", nuevo), re.sub(r"<lastmod>[^<]*</lastmod>", "", texto))
        self.assertEqual(u.actualizar(nuevo, RAIZ)[1], [])                   # idempotente
        self.assertEqual(u.archivo_de("https://manalab.es/"), "index.html")
        self.assertEqual(u.archivo_de("https://manalab.es/es/magic-online/"), "es/magic-online/index.html")
        self.assertEqual(u.archivo_de("https://manalab.es/guia/guia_manalab_en.html"), "guia/guia_manalab_en.html")


class TestPunto8PrimeroSegundo(unittest.TestCase):
    ARCHIVOS = [RAIZ / "es" / "index.html", RAIZ / "es" / "magic-online" / "index.html"]

    def test_ni_rastro_de_play_draw(self):
        for ruta in self.ARCHIVOS:
            with self.subTest(pagina=str(ruta.relative_to(RAIZ))):
                self.assertEqual(len(re.findall(r"play/draw|play o draw|play y draw", leer(ruta), re.I)), 0)
                self.assertNotIn('<span class="g">Play</span>', leer(ruta))
                self.assertNotIn('<span class="g">Draw</span>', leer(ruta))

    def test_textos_nuevos(self):
        portada = leer(self.ARCHIVOS[0])
        self.assertIn('<span class="g">Primero</span>', portada)
        self.assertIn('<span class="g">Segundo</span>', portada)
        self.assertIn("minmax(0, 1fr) 66px 74px", portada)
        self.assertIn("el winrate por matchup y por ir primero o segundo", portada)
        self.assertIn("en sus partidas: si ibas primero o segundo, resultado y mulligans", portada)
        mo = leer(self.ARCHIVOS[1])
        self.assertIn("<h3>Primero o segundo</h3>", mo)
        self.assertIn("entre ir primero e ir segundo", mo)

    def test_metadescripciones_de_50_a_170_caracteres(self):
        for ruta in self.ARCHIVOS:
            with self.subTest(pagina=str(ruta.relative_to(RAIZ))):
                for d in re.findall(r'<meta content="([^"]*)" (?:name="description"|property="og:description")/>', leer(ruta)):
                    self.assertTrue(50 <= len(d) <= 170, f"{len(d)}: {d}")


if __name__ == "__main__":
    unittest.main()
