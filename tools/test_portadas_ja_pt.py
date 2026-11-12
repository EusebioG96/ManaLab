#!/usr/bin/env python3
"""ML-156, tanda 3A de la auditoría web: portadas en japonés y portugués de Brasil. Comprueba sobre los archivos (sin red).

Uso:  python3 tools/test_portadas_ja_pt.py
"""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NUEVAS = {"ja": RAIZ / "ja" / "index.html", "pt": RAIZ / "pt" / "index.html"}
CUATRO = {"en": RAIZ / "index.html", "es": RAIZ / "es" / "index.html", **NUEVAS}
ORDEN = ["confianza", "motivos", "mtgo", "funciones", "empezar", "preguntas", "ia", "final"]
HREFLANG = {"en": "https://manalab.es/", "es": "https://manalab.es/es/", "pt-br": "https://manalab.es/pt/",
            "ja": "https://manalab.es/ja/", "x-default": "https://manalab.es/"}
FIJOS = {
    "ja": dict(title="ManaLab – MTGアリーナ・Magic Online対応の無料戦績トラッカー", h1="アリーナとMagic Onlineの全対戦を、自動で記録。",
               boton="無料ダウンロード", req="Windows 10 / 11", nota="翻訳に誤りがあれば、X（@ManaLabApp）までお知らせください。"),
    "pt": dict(title="ManaLab: tracker grátis para MTG Arena e Magic Online", h1="Cada partida de Arena e Magic Online, registrada sozinha.",
               boton="Baixar grátis", req="Windows 10 ou 11", nota="Encontrou um erro de tradução? Avise a gente no X (@ManaLabApp)."),
}


def leer(ruta):
    return Path(ruta).read_text(encoding="utf-8")


def texto(fragmento):
    return " ".join(re.sub(r"<[^>]+>", "", fragmento).replace("&amp;", "&").split())


def ids_de_secciones(html):
    main = html[html.index("<main"):html.index("</main>")]
    return re.findall(r'<section class="[^"]*"(?: id="([^"]*)")?', main)


class TestPortadasNuevas(unittest.TestCase):
    def test_orden_de_secciones(self):
        for c, ruta in NUEVAS.items():
            with self.subTest(c=c):
                self.assertEqual(ids_de_secciones(leer(ruta)), [""] + ORDEN)

    def test_no_llevan_lo_que_no_toca(self):
        for c, ruta in NUEVAS.items():
            html = leer(ruta)
            with self.subTest(c=c):
                for id_ in ("capturas", "como-funciona", "coaches", "contacto", "apoyo"):
                    self.assertNotIn(f'id="{id_}"', html)
                self.assertNotIn("aviso-version", html.split("</style>")[1])

    def test_lang_y_textos_fijados(self):
        for c, ruta in NUEVAS.items():
            html = leer(ruta)
            f = FIJOS[c]
            with self.subTest(c=c):
                self.assertRegex(html, r'<html lang="%s">' % ("ja" if c == "ja" else "pt-BR"))
                self.assertEqual(texto(re.search(r"<title>(.*?)</title>", html).group(1)), f["title"])
                self.assertEqual(texto(re.search(r"<h1>(.*?)</h1>", html, re.S).group(1)).replace(" ", ""), f["h1"].replace(" ", ""))
                self.assertIn("<em>", re.search(r"<h1>(.*?)</h1>", html, re.S).group(1))
                botones = re.findall(r'<a class="boton prim descarga"[^>]*data-a-bloque[^>]*>(.*?)</a>', html)
                self.assertEqual(len(botones), 5)
                self.assertEqual({texto(b) for b in botones} - {texto(botones[0])}, {f["boton"]})
                self.assertIn(f["nota"], texto(html[html.index('class="nota-trad"'):]))

    def test_botones_de_descarga_con_titulo_del_idioma(self):
        for c, ruta in NUEVAS.items():
            html = leer(ruta)
            with self.subTest(c=c):
                titulos = re.findall(r'data-a-bloque[^>]*data-goatcounter-title="([^"]*)"', html)
                self.assertEqual(len(titulos), 5)
                for t in titulos + re.findall(r'data-goatcounter-title="(descarga-portada-[^"]*)"', html):
                    self.assertTrue(t.endswith(f"-{c}"), t)
                self.assertIn(f'data-titulo="compartir-movil-{c}"', html)
                self.assertIn('data-movil-aqui', html)
                self.assertIn('id="bloque-movil"', html)

    def test_hreflang_reciproco_entre_las_cuatro(self):
        for c, ruta in CUATRO.items():
            html = leer(ruta)
            with self.subTest(c=c):
                alts = {m[1].lower(): m[0] for m in re.findall(r'<link href="([^"]*)" hreflang="([^"]*)" rel="alternate"/>', html)}
                self.assertEqual(alts, HREFLANG)

    def test_selector_de_idioma(self):
        esperado = {"en": ["ES", "PT", "日本語"], "es": ["EN", "PT", "日本語"], "pt": ["EN", "ES", "日本語"], "ja": ["EN", "ES", "PT"]}
        for c, ruta in CUATRO.items():
            html = leer(ruta)
            with self.subTest(c=c):
                cab = html[html.index('<header class="cab">'):html.index("</header>")]
                self.assertEqual(re.findall(r'<a class="idioma"[^>]*>([^<]*)</a>', cab), esperado[c])

    def test_faq_igual_en_html_y_json_ld(self):
        for c, ruta in NUEVAS.items():
            html = leer(ruta)
            with self.subTest(c=c):
                ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S).group(1))
                faq = [x for x in ld["@graph"] if x["@type"] == "FAQPage"][0]
                self.assertEqual(faq["inLanguage"], "ja" if c == "ja" else "pt-BR")
                det = re.findall(r"<details[^>]*><summary>(.*?)</summary>\s*<p>(.*?)</p>", html[html.index('id="preguntas"'):], re.S)
                self.assertEqual(len(det), 8)
                self.assertEqual(len(faq["mainEntity"]), 8)
                for (q, a), e in zip(det, faq["mainEntity"]):
                    self.assertEqual(texto(q), e["name"])
                    self.assertEqual(texto(a), e["acceptedAnswer"]["text"])
                app = [x for x in ld["@graph"] if x["@type"] == "SoftwareApplication"][0]
                self.assertEqual(app["inLanguage"], "ja" if c == "ja" else "pt-BR")

    def test_sin_patreon_ni_equipa_ni_cosas_prohibidas(self):
        for c, ruta in NUEVAS.items():
            low = leer(ruta).lower()
            with self.subTest(c=c):
                for mala in ("patreon", "equipa", "ecrã", "partilhar", "utm_", "sin anuncios"):
                    self.assertNotIn(mala, low)

    def test_requisito_windows_en_el_paso_1(self):
        for c, ruta in NUEVAS.items():
            html = leer(ruta)
            with self.subTest(c=c):
                self.assertIn(FIJOS[c]["req"], texto(html[html.index('class="pasos"'):html.index('id="preguntas"')]))
        w = leer(RAIZ / "tools" / "windows_check.py")
        self.assertIn('"ja": "Windows 10 / 11"', w)
        self.assertIn('"pt-br": "Windows 10 ou 11"', w)

    def test_notas_de_imagenes_en_ingles(self):
        nota = {"ja": "画面は英語版です。アプリは日本語に対応しています。", "pt": "As imagens mostram o app em inglês. O app está disponível em português."}
        for c, ruta in NUEVAS.items():
            with self.subTest(c=c):
                self.assertEqual(leer(ruta).count(nota[c]), 3)   # portada, motivos y mtgo

    def test_enlaces_a_paginas_solo_en_ingles_van_marcados(self):
        marca = {"ja": "（英語）", "pt": "(em inglês)"}
        for c, ruta in NUEVAS.items():
            html = leer(ruta)
            with self.subTest(c=c):
                for m in re.finditer(r'<a [^>]*href="(/safety/|/magic-online/|/novedades/|/privacy/|/#contacto|/coaches/)"[^>]*>(.*?)</a>', html, re.S):
                    self.assertIn(marca[c], texto(m.group(2)), m.group(0)[:120])
        self.assertIn('href="/pt/coaches/"', leer(NUEVAS["pt"]))
        self.assertNotIn('href="/coaches/"', leer(NUEVAS["pt"]))


class TestGuiasEnlazanASuPortada(unittest.TestCase):
    def test_inicio_y_botones(self):
        for c in ("ja", "pt"):
            html = leer(RAIZ / "guia" / f"guia_manalab_{c}.html")
            with self.subTest(c=c):
                navs = re.findall(r'<nav class="inicio".*?</nav>', html)
                self.assertEqual(len(navs), 2)
                for n in navs:
                    self.assertIn(f'href="/{c}/#descargar"', n)
                    self.assertNotIn('href="/#descargar"', n)
                self.assertIn(f'<nav class="inicio" aria-label="ManaLab"><a href="/{c}/">', navs[0])


class TestPunto5SeparacionBajoLaCaja(unittest.TestCase):
    def test_regla_en_las_cuatro(self):
        for c, ruta in CUATRO.items():
            with self.subTest(c=c):
                self.assertIn("html.movil .hero-cta { margin-top: 16px; }", leer(ruta))

    def test_logo_de_coaches_pt(self):
        self.assertIn('<a class="marca" href="/pt/">', leer(RAIZ / "pt" / "coaches" / "index.html"))


class TestSitemap(unittest.TestCase):
    def test_dos_urls_nuevas_con_alternates(self):
        sm = leer(RAIZ / "sitemap.xml")
        self.assertEqual(sm.count("<url>"), 27)
        for c in ("ja", "pt"):
            bloque = re.search(r"<url>\s*<loc>https://manalab.es/%s/</loc>.*?</url>" % c, sm, re.S).group(0)
            self.assertEqual(sorted(re.findall(r'hreflang="([^"]*)"', bloque)), sorted(["en", "es", "pt-BR", "ja", "x-default"]))


if __name__ == "__main__":
    unittest.main()
