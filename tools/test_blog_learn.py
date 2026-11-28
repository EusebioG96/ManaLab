#!/usr/bin/env python3
"""ML-345 (BLOG-01, BLOG-02): el primer post del blog «Learn» de la 3.0 en en, es, pt y ja: textos exactos, límites de SEO, hreflang, sitemap,
Article y migas, fecha única, enlaces de entrada y de salida y ausencia de anuncio. Sin red.

Uso:  python3 -m pytest -q tools/test_blog_learn.py
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_mdn
import construir_web
from test_enlaces_internos import rotos_de_html
from test_pagina_player_log import Lector, grafo, normal
from test_seo_limites import MAX_DESC, MAX_TITULO, MAX_TITULO_CJK, MIN_DESC, ancho
from textos_vetados import buscar

SITIO = "https://manalab.es"
RUTA = "blog/learn-mtg-arena-guides/"
# idioma -> (carpeta, hreflang, lang de <html>, og:locale, título = H1, descripción, párrafo inicial, H2, negritas de la lista, texto del botón final,
#            enlace del botón final, fecha visible)
PAGINAS = {
    "en": ("", "en", "en", "en_US", "Learn MTG Arena with Guides Inside ManaLab 3.0",
           "ManaLab 3.0 adds Learn: Magic guides from Metafy creators, right next to your own match data. Find what to study after a session. The tracker stays free.",
           "You finish a session and open your stats. One row stands out: you keep losing to the same deck. The tracker has told you where you lose. It can't tell you how to fix it.",
           ['From "I lose to this deck" to "here\'s how to beat it"', "What's inside Learn", "How featured creators are chosen", "The tracker is still free", "Try it"],
           ["Magic guides from Metafy creators", "Featured creators", "Coaching sessions", "Cover art loaded from Metafy."],
           "Download ManaLab free →", "/#descargar", "20 November 2026"),
    "es": ("es/", "es", "es", "es_ES", "Aprende MTG Arena con guías dentro de ManaLab 3.0",
           "ManaLab 3.0 añade Aprender: guías de Magic de creadores de Metafy junto a tus partidas. Descubre qué estudiar tras cada sesión. El tracker sigue siendo gratis.",
           "Terminas una sesión y abres tus estadísticas. Hay una fila que destaca: pierdes siempre contra el mismo mazo. El tracker te ha dicho dónde pierdes, pero no cómo arreglarlo.",
           ["De «pierdo contra este mazo» a «así se le gana»", "Qué hay dentro de Aprender", "Cómo se eligen los creadores destacados", "El tracker sigue siendo gratis", "Pruébalo"],
           ["Guías de Magic de creadores de Metafy", "Creadores destacados", "Sesiones de coaching", "Portadas cargadas desde Metafy."],
           "Descargar ManaLab gratis →", "/es/#descargar", "20 de noviembre de 2026"),
    "pt": ("pt/", "pt-BR", "pt-BR", "pt_BR", "Aprenda MTG Arena com guias dentro do ManaLab 3.0",
           "O ManaLab 3.0 traz Aprender: guias de Magic de criadores da Metafy ao lado das suas partidas. Veja o que estudar após cada sessão. O tracker continua grátis.",
           "Você termina uma sessão e abre suas estatísticas. Uma linha chama a atenção: você perde sempre para o mesmo deck. O tracker mostrou onde você perde, mas não como resolver.",
           ["De «perco para esse deck» a «é assim que se vence»", "O que há dentro do Aprender", "Como os criadores em destaque são escolhidos", "O tracker continua grátis", "Experimente"],
           ["Guias de Magic de criadores da Metafy", "Criadores em destaque", "Sessões de coaching", "Capas carregadas da Metafy."],
           "Baixar o ManaLab grátis →", "/pt/#descargar", "20 de novembro de 2026"),
    "ja": ("ja/", "ja", "ja", "ja_JP", "ManaLab 3.0で学ぶMTGアリーナ:アプリ内ガイド",
           "ManaLab 3.0の新機能「学ぶ」で、Metafyのクリエイターによる対戦ガイドを自分の戦績のそばで確認。セッション後に何を練習すべきかが分かります。トラッカーは無料のままです。",
           "セッションを終えて統計を開くと、ある行が目に留まります。毎回同じデッキに負けているのです。トラッカーは「どこで負けるか」を教えてくれますが、「どう直すか」までは教えてくれません。",
           ["「このデッキに勝てない」から「こう戦えばいい」へ", "「学ぶ」の中身", "注目のクリエイターはどう選ばれるか", "トラッカーは無料のまま", "試してみる"],
           ["Metafyのクリエイターによるマジックのガイド", "注目のクリエイター", "注目のクリエイターによるコーチングセッション", "Metafyから読み込むカバー画像"],
           "ManaLabを無料でダウンロード →", "/ja/#descargar", "2026年11月20日"),
}
IDIOMAS = tuple(PAGINAS)
URL = {i: f"{SITIO}/{PAGINAS[i][0]}{RUTA}" for i in IDIOMAS}
ESPERADO_HREFLANG = [("en", URL["en"]), ("es", URL["es"]), ("pt-BR", URL["pt"]), ("ja", URL["ja"]), ("x-default", URL["en"])]
# Los textos que el encargo manda dejar fuera de la página y los que la web veta
FUERA = ("windows", "[", "]", "CAPTURA-LEARN")
CAPTURA = "<!-- CAPTURA-LEARN: pendiente (pantalla Aprender 3.0, datos de ejemplo, sin rivales; alt ≤125) -->"


def ruta_html(idioma: str) -> Path:
    return RAIZ / PAGINAS[idioma][0] / RUTA / "index.html"


def leer_html(idioma: str) -> str:
    return ruta_html(idioma).read_text(encoding="utf-8")


def lector(idioma: str) -> Lector:
    return Lector(leer_html(idioma))


class TestTextos(unittest.TestCase):
    def por_idioma(self):
        for idioma in IDIOMAS:
            with self.subTest(idioma=idioma):
                yield idioma, PAGINAS[idioma], lector(idioma), leer_html(idioma)

    def test_titulo_descripcion_h1_y_etiquetas_de_idioma(self):
        for idioma, (_, hreflang, lang, locale, titulo, descripcion, *_resto), p, html in self.por_idioma():
            self.assertEqual(normal(p.titulo), titulo)
            for clave in ("description", "og:description", "twitter:description"):
                self.assertEqual(p.meta[clave], descripcion, clave)
            for clave in ("og:title", "twitter:title"):
                self.assertEqual(p.meta[clave], titulo, clave)
            self.assertEqual(p.meta["og:locale"], locale)
            self.assertIn(f'<html lang="{lang}">', html)
            self.assertEqual(len(re.findall(r"<h1>", html)), 1, "un solo H1")
            self.assertEqual(normal(p.h1), titulo)

    def test_limites_de_titulo_y_de_descripcion_en_y_ja(self):
        """Los límites de test_seo_limites (no se tocan), medidos sobre la página publicada. El título lleva «ManaLab»: no entra en TITULO_SIN_MARCA."""
        for idioma in ("en", "ja"):
            p = lector(idioma)
            titulo, descripcion = normal(p.titulo), p.meta["description"]
            with self.subTest(idioma=idioma):
                self.assertIn("ManaLab", titulo)
                if idioma == "ja":
                    self.assertLessEqual(ancho(titulo), MAX_TITULO_CJK)
                else:
                    self.assertLessEqual(len(titulo), MAX_TITULO)
                    self.assertTrue(MIN_DESC <= len(descripcion) <= MAX_DESC)
                    self.assertRegex(descripcion, r"[.!?)]$")

    def test_limites_de_titulo_y_de_descripcion_en_es_y_pt(self):
        """El título cabe en 60. Las descripciones de es y pt, recortadas por el coordinador (20/11) para caber en 160."""
        for idioma in ("es", "pt"):
            p = lector(idioma)
            with self.subTest(idioma=idioma):
                self.assertIn("ManaLab", p.titulo)
                self.assertLessEqual(len(normal(p.titulo)), MAX_TITULO)
                self.assertGreaterEqual(len(p.meta["description"]), MIN_DESC)
                self.assertRegex(p.meta["description"], r"[.!?)]$")
                self.assertLessEqual(len(p.meta["description"]), MAX_DESC)


    def test_primer_parrafo_h2_negritas_y_cursivas_exactos(self):
        for idioma, (_, _, _, _, _, _, primero, h2, negritas, *_), p, html in self.por_idioma():
            cuerpo = html.split('<div class="cuerpo-blog">', 1)[1].split("</article>", 1)[0]
            self.assertEqual(normal(re.sub(r"<[^>]+>", "", re.search(r"<p>(.*?)</p>", cuerpo).group(1))), primero)
            self.assertEqual([re.sub(r"<[^>]+>", "", t) for t in re.findall(r"<h2>(.*?)</h2>", cuerpo)], h2)
            self.assertEqual(re.findall(r"<li><strong>(.*?)</strong>", cuerpo), negritas, "cuatro viñetas, cada una con su negrita")
            self.assertEqual(len(re.findall(r"<li>", cuerpo)), 4)
            self.assertEqual(len(re.findall(r"<em>", cuerpo)), 2 if idioma != "ja" else 0, "las dos cursivas del primer párrafo")
            self.assertEqual(len(re.findall(r"<strong>", cuerpo)), 4 + 1 + 1, "viñetas, el nombre de la sección y el botón final")

    def test_viñeta_de_sesiones_corregida_sin_pestaña_de_coaches(self):
        """El encargo corrige el borrador: Aprender no tiene coaches, los destacados llevan «Sessions»; la viñeta no dice que haya una pestaña de coaches."""
        textos = {"en": "Coaching sessions</strong> with featured creators, if you'd rather have a person look at your play than read about it.",
                  "es": "Sesiones de coaching</strong> con los creadores destacados, si prefieres que una persona revise tu juego en lugar de leer sobre él.",
                  "pt": "Sessões de coaching</strong> com os criadores em destaque, se você prefere que uma pessoa analise seu jogo em vez de ler sobre ele.",
                  "ja": "注目のクリエイターによるコーチングセッション</strong>。読むより、自分のプレイを直接見てもらいたい人向けです。"}
        for idioma, esperado in textos.items():
            with self.subTest(idioma=idioma):
                self.assertIn(esperado, leer_html(idioma))
                visible = " ".join(lector(idioma).texto_main)
                self.assertNotRegex(visible, r"(?i)\bcoaches\b|pesta[ñn]a de coach|aba de coach|コーチ.{0,6}タブ|coach tab|tab of coach")

    def test_nada_vetado_ni_windows_ni_notas_de_marketing(self):
        for idioma, _, p, html in self.por_idioma():
            visible = " ".join(p.texto_main)
            cuerpo = html.split("<main", 1)[1].split("</main>", 1)[0]
            self.assertEqual(buscar(visible), [], "frase vetada")
            for fuera in ("windows", "[", "]"):
                self.assertNotIn(fuera, visible.lower(), fuera)
            self.assertNotIn("windows", html.split("</head>")[0].lower())
            self.assertEqual(cuerpo.count("<!--"), 1, "solo el comentario de la captura")
            self.assertEqual(cuerpo.count(CAPTURA), 1)
            self.assertNotIn("<img", cuerpo, "sin captura ni hueco visible")
            self.assertNotIn("<figure", cuerpo)

    def test_el_comentario_de_la_captura_va_entre_la_lista_y_la_seccion_de_creadores(self):
        for idioma in IDIOMAS:
            html = leer_html(idioma)
            with self.subTest(idioma=idioma):
                antes, despues = html.split(CAPTURA)
                self.assertTrue(antes.rstrip().endswith("</ul>"))
                self.assertTrue(despues.lstrip().startswith("<h2>"))

    def test_autor_y_fecha_bajo_el_h1_en_cada_idioma(self):
        for idioma, (*_, fecha), p, html in self.por_idioma():
            self.assertRegex(html, r'</h1>\n<p class="autoria"><time datetime="2026-11-20">' + re.escape(fecha) + r"</time> · ManaLab</p>")
            self.assertEqual(construir_web.fecha_blog_legible(construir_web.FECHA_BLOG_LEARN, idioma), fecha)


class TestFechaUnica(unittest.TestCase):
    def test_una_sola_constante_alimenta_la_fecha_visible_y_las_dos_del_article(self):
        """Con otra FECHA_BLOG_LEARN, las cuatro páginas cambian el texto visible, datePublished y dateModified, y ninguna fecha queda escrita en las plantillas."""
        original = construir_web.FECHA_BLOG_LEARN
        construir_web.FECHA_BLOG_LEARN = "2027-01-05"
        try:
            with tempfile.TemporaryDirectory() as temporal:
                construir_web.construir(RAIZ, Path(temporal))
                visibles = {"en": "5 January 2027", "es": "5 de enero de 2027", "pt": "5 de janeiro de 2027", "ja": "2027年1月5日"}
                for idioma in IDIOMAS:
                    html = (Path(temporal) / PAGINAS[idioma][0] / RUTA / "index.html").read_text(encoding="utf-8")
                    articulo = next(n for n in grafo(Lector(html)) if n["@type"] == "Article")
                    with self.subTest(idioma=idioma):
                        self.assertEqual((articulo["datePublished"], articulo["dateModified"]), ("2027-01-05", "2027-01-05"))
                        self.assertIn(f'<time datetime="2027-01-05">{visibles[idioma]}</time> · ManaLab', html)
                        self.assertNotIn("2026-11-20", html.split("</head>", 1)[0].replace('"lastmod"', ""))
        finally:
            construir_web.FECHA_BLOG_LEARN = original

    def test_las_plantillas_del_blog_no_llevan_la_fecha_escrita(self):
        for idioma in IDIOMAS:
            fuente = (RAIZ / "plantillas" / "paginas" / PAGINAS[idioma][0] / "blog/learn-mtg-arena-guides/index.pagina").read_text(encoding="utf-8")
            with self.subTest(idioma=idioma):
                self.assertNotRegex(fuente, r"2026-11-20|20 (de )?[Nn]ov|2026年")
                self.assertEqual(fuente.count("{{FECHA_BLOG_LEARN"), 4, "datePublished, dateModified, el datetime de <time> y el texto visible")

    def test_la_constante_dice_que_se_cambia_el_dia_del_lanzamiento(self):
        fuente = (RAIZ / "tools" / "construir_web.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'^FECHA_BLOG_LEARN = "\d{4}-\d{2}-\d{2}"$', fuente, re.MULTILINE)), 1)
        self.assertRegex(fuente, r"día del lanzamiento de la 3\.0[^\n]*\n[^\n]*\nFECHA_BLOG_LEARN = ")


class TestHreflangYSitemap(unittest.TestCase):
    def test_hreflang_reciproco_canonical_og_y_selector_de_idioma(self):
        for idioma in IDIOMAS:
            p = lector(idioma)
            hreflang = PAGINAS[idioma][1]
            with self.subTest(idioma=idioma):
                self.assertEqual([(x["hreflang"], x["href"]) for x in p.links if x.get("rel") == "alternate"], ESPERADO_HREFLANG)
                self.assertEqual([x["href"] for x in p.links if x.get("rel") == "canonical"], [URL[idioma]])
                self.assertEqual(p.meta["og:url"], URL[idioma])
                self.assertEqual(p.meta["og:type"], "article")
                self.assertEqual(p.meta["og:image"], f"{SITIO}/img/og-3.0.jpg")
                self.assertEqual(p.meta["twitter:image"], f"{SITIO}/img/og-3.0.jpg")
                self.assertNotIn("noindex", p.meta.get("robots", ""))
                otros = [(PAGINAS[o][1], URL[o].removeprefix(SITIO)) for o in IDIOMAS if o != idioma]
                selector = [(x["hreflang"], x["href"]) for x in p.links_a if "idioma" in x.get("class", "")]
                self.assertEqual(selector, otros * 2, "selector de escritorio y del menú del teléfono, hacia los tres pares del blog")
                self.assertNotIn(hreflang, [h for h, _ in selector])

    def test_goatcounter_como_el_resto(self):
        for idioma in IDIOMAS:
            fuentes = [(s.get("src"), s.get("data-goatcounter")) for s in lector(idioma).scripts if s.get("type") != "application/ld+json" and s.get("src") != "/menu.js"]   # menu.js: menú móvil (ML-412)
            with self.subTest(idioma=idioma):
                self.assertEqual(fuentes, [("//gc.zgo.at/count.js", "https://manalab.goatcounter.com/count")])

    def test_las_cuatro_estan_en_el_sitemap_una_vez_con_alternates(self):
        sitemap = (RAIZ / "sitemap.xml").read_text(encoding="utf-8")
        for idioma in IDIOMAS:
            with self.subTest(idioma=idioma):
                self.assertEqual(sitemap.count(f"<loc>{URL[idioma]}</loc>"), 1)
                bloque = re.search(r"<url>\s*<loc>" + re.escape(URL[idioma]) + r"</loc>.*?</url>", sitemap, re.DOTALL).group(0)
                self.assertEqual(re.findall(r'hreflang="([^"]+)" href="([^"]+)"', bloque), ESPERADO_HREFLANG)

    def test_todos_los_enlaces_internos_existen(self):
        for idioma in IDIOMAS:
            with self.subTest(idioma=idioma):
                self.assertEqual(rotos_de_html(leer_html(idioma), ruta_html(idioma)), [])


class TestDatosEstructurados(unittest.TestCase):
    def nodos(self, idioma):
        return grafo(lector(idioma))

    def test_article_valido_en_cada_idioma(self):
        for idioma in IDIOMAS:
            _, _, _, _, titulo, descripcion, *_ = PAGINAS[idioma]
            (articulo,) = [n for n in self.nodos(idioma) if n["@type"] == "Article"]
            with self.subTest(idioma=idioma):
                self.assertEqual(articulo["headline"], titulo)
                self.assertEqual(articulo["headline"], normal(lector(idioma).h1), "el headline es el H1")
                self.assertEqual(articulo["author"], {"@id": f"{SITIO}/#org"})
                self.assertEqual(articulo["publisher"], {"@id": f"{SITIO}/#org"})
                self.assertEqual(articulo["inLanguage"], PAGINAS[idioma][2])
                self.assertEqual(articulo["description"], descripcion)
                self.assertEqual(articulo["mainEntityOfPage"], URL[idioma])
                self.assertEqual((articulo["datePublished"], articulo["dateModified"]), (construir_web.FECHA_BLOG_LEARN,) * 2)
                self.assertEqual(articulo["image"], f"{SITIO}/img/og-3.0.jpg")
                (org,) = [n for n in self.nodos(idioma) if n["@type"] == "Organization"]
                self.assertEqual((org["@id"], org["name"]), (f"{SITIO}/#org", "ManaLab"))

    def test_migas_generadas_por_el_proceso(self):
        esperado = {
            "en": [("Home", f"{SITIO}/"), ("What's new", f"{SITIO}/novedades/")],
            "es": [("Inicio", f"{SITIO}/es/"), ("Novedades", f"{SITIO}/es/novedades/")],
            "pt": [("Início", f"{SITIO}/pt/")],
            "ja": [("ホーム", f"{SITIO}/ja/")],
        }
        for idioma in IDIOMAS:
            (migas,) = [n for n in self.nodos(idioma) if n["@type"] == "BreadcrumbList"]
            elementos = esperado[idioma] + [(PAGINAS[idioma][4], URL[idioma])]
            with self.subTest(idioma=idioma):
                self.assertEqual([(e["position"], e["name"], e["item"]) for e in migas["itemListElement"]],
                                 [(n, nombre, url) for n, (nombre, url) in enumerate(elementos, 1)])

    def test_las_migas_de_pt_y_ja_no_inventan_novedades(self):
        for idioma in ("pt", "ja"):
            (migas,) = [n for n in self.nodos(idioma) if n["@type"] == "BreadcrumbList"]
            self.assertEqual(len(migas["itemListElement"]), 2, idioma)
        self.assertFalse((RAIZ / "pt" / "novedades").exists() or (RAIZ / "ja" / "novedades").exists())


class TestEnlaces(unittest.TestCase):
    def test_enlaces_de_entrada(self):
        casos = (("novedades/index.html", "/blog/learn-mtg-arena-guides/", "Read more about Learn →", "A Learn section with Metafy guides"),
                 ("es/novedades/index.html", "/es/blog/learn-mtg-arena-guides/", "Más sobre Aprender →", "Una sección Aprender con guías de Metafy"),
                 ("pt/aprender/index.html", "/pt/blog/learn-mtg-arena-guides/", "Mais sobre o Aprender →", None),
                 ("ja/learn/index.html", "/ja/blog/learn-mtg-arena-guides/", "「学ぶ」について詳しく →", None))
        for pagina, destino, texto, titulo_del_bloque in casos:
            html = (RAIZ / pagina).read_text(encoding="utf-8")
            enlaces = [(h, normal(t)) for h, t, _ in Lector(html).enlaces if h == destino]
            with self.subTest(pagina=pagina):
                self.assertEqual(enlaces, [(destino, texto)], "un solo enlace, con el texto del encargo")
                self.assertIn(f'<a class="enlace-man" href="{destino}">{texto}</a>', html)
                if titulo_del_bloque:  # dentro del bloque de la 3.0 que habla de Learn, no en otro
                    bloque = html.split(f"<h3>{titulo_del_bloque}</h3>", 1)[1].split("</div>", 1)[0]
                    self.assertIn(destino, bloque)

    def test_enlaces_de_salida(self):
        salida = {
            "en": ("/#descargar", ["/detailed-logs/", "/player-log/", "/safety/"]),
            "es": ("/es/#descargar", ["/es/registro-detallado/", "/es/player-log/", "/es/seguridad/"]),
            "pt": ("/pt/#descargar", ["/detailed-logs/", "/safety/"]),
            "ja": ("/ja/#descargar", ["/detailed-logs/", "/safety/"]),
        }
        for idioma, (descarga, otros) in salida.items():
            p = lector(idioma)
            cuerpo = [(h, normal(t)) for h, t, en_main in p.enlaces if en_main]
            with self.subTest(idioma=idioma):
                self.assertEqual([t for h, t in cuerpo if h == descarga], [PAGINAS[idioma][9]], "el botón final va a #descargar de su portada")
                self.assertEqual([h for h, _ in cuerpo if h not in (descarga,)], otros, "después del botón, solo la línea final de enlaces")
                self.assertFalse([h for h, _ in cuerpo if "utm" in h or h.endswith("-portable.zip")], "sin UTM y sin el ZIP en la página")
                self.assertRegex(leer_html(idioma), r'<p class="antes">[^<]+<a ')

    def test_la_linea_final_es_la_ultima_de_la_pagina_y_va_tras_el_boton(self):
        for idioma in IDIOMAS:
            cuerpo = leer_html(idioma).split('<div class="cuerpo-blog">', 1)[1]
            with self.subTest(idioma=idioma):
                self.assertLess(cuerpo.index(PAGINAS[idioma][9]), cuerpo.index('<p class="antes">'))
                self.assertTrue(cuerpo.split('<p class="antes">', 1)[1].split("</p>", 1)[1].lstrip().startswith("</div>"))

    def test_cabecera_con_descarga_hacia_la_portada_de_su_idioma(self):
        for idioma in IDIOMAS:
            cabecera = leer_html(idioma).split("<header", 1)[1].split("</header>", 1)[0]
            with self.subTest(idioma=idioma):
                self.assertEqual(cabecera.count(f'class="boton prim descarga" href="{PAGINAS[idioma][10]}"'), 1)


class TestSinAnuncio(unittest.TestCase):
    def test_sin_hueco_de_mdn_ni_etiqueta_de_anuncio(self):
        for idioma in IDIOMAS:
            html = leer_html(idioma)
            with self.subTest(idioma=idioma):
                for marca in ("anuncio-casa", "hueco-mdn", "HUECO_MDN", "mdn.metafy.gg", ">Publicidad<", ">Advertisement<", ">Publicidade<", ">広告<"):
                    self.assertNotIn(marca, html)

    def test_estan_en_la_lista_de_paginas_sin_anuncio_con_su_comentario(self):
        fuente = (RAIZ / "tools" / "construir_mdn.py").read_text(encoding="utf-8")
        self.assertIn("blog, decisión del coordinador (ML-345)", fuente)
        for idioma in IDIOMAS:
            ruta = f"{PAGINAS[idioma][0]}{RUTA}index.html"
            with self.subTest(idioma=idioma):
                self.assertIn(ruta, construir_mdn.PAGINAS_SIN_ANUNCIO)
                self.assertIn(f'"{ruta}"', (RAIZ / "tools" / "test_huecos_mdn.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
