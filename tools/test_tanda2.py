#!/usr/bin/env python3
"""ML-153, tanda 2A de la auditoría web: portada reordenada y página de novedades. Comprueba sobre los archivos (sin red).

Uso:  python3 tools/test_tanda2.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PORTADAS = {"en": RAIZ / "index.html", "es": RAIZ / "es" / "index.html"}
NOVEDADES = {"en": RAIZ / "novedades" / "index.html", "es": RAIZ / "es" / "novedades" / "index.html"}
URL = {"en": "https://manalab.es/novedades/", "es": "https://manalab.es/es/novedades/"}
ORDEN = ["confianza", "motivos", "mtgo", "funciones", "capturas", "como-funciona", "coaches", "empezar", "preguntas", "ia", "final", "contacto"]
FRANJAS = {"confianza", "mtgo", "capturas", "coaches", "preguntas", "final"}   # las demás van sin fondo: nunca dos iguales seguidas
CLIPS = ["03-opening-hand-mulligans", "05-statistics", "02-replay"]


def leer(ruta):
    return Path(ruta).read_text(encoding="utf-8")


def secciones(html):
    """[(clases, id, html de la sección)] de las <section> de <main>."""
    main = html[html.index("<main"):html.index("</main>")]
    cortes = [m.start() for m in re.finditer(r"<section ", main)] + [len(main)]
    salida = []
    for a, b in zip(cortes, cortes[1:]):
        trozo = main[a:b]
        cab = re.match(r'<section class="([^"]*)"(?: id="([^"]*)")?', trozo)
        salida.append((cab.group(1).split(), cab.group(2), trozo))
    return salida


def seccion(html, id_):
    return [t for _, i, t in secciones(html) if i == id_][0]


class TestOrdenDeLaPortada(unittest.TestCase):
    def test_ids_en_el_orden_de_la_tabla_y_iguales_en_los_dos_idiomas(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                s = secciones(leer(ruta))
                self.assertIn("portada", s[0][0])
                self.assertEqual([i for _, i, _ in s[1:]], ORDEN)

    def test_dos_fondos_iguales_nunca_seguidos(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                s = secciones(leer(ruta))[1:]
                for (c1, i1, _), (c2, i2, _) in zip(s, s[1:]):
                    self.assertNotEqual("franja" in c1, "franja" in c2, f"{i1} y {i2} tienen el mismo fondo")
                self.assertEqual({i for c, i, _ in s if "franja" in c}, FRANJAS)

    def test_novedades_y_anteriores_ya_no_estan_en_la_portada(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                for id_ in ("novedades", "anteriores"):
                    self.assertNotIn(f'id="{id_}"', html)
                    self.assertNotIn(f'href="#{id_}"', html)

    def test_apoyo_dentro_de_ia_y_con_h3(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                ia = seccion(leer(ruta), "ia")
                self.assertEqual(ia.count("<h2>"), 1)
                self.assertIn('<div class="apoyo" id="apoyo">', ia)
                self.assertEqual(len(re.findall(r'id="enlace-donar"', ia)), 1)
                self.assertRegex(ia[ia.index('id="apoyo"'):], r"<h3>")

    def test_menu(self):
        esperado = {"en": ["#funciones", "#mtgo", "#coaches", "#empezar", "#preguntas", "#ia"], "es": ["#funciones", "#mtgo", "#coaches", "#empezar", "#preguntas", "#ia"]}
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                nav = re.search(r'<nav aria-label="Secciones">(.*?)</nav>', html, re.S).group(1)
                self.assertEqual(re.findall(r'href="([^"]*)"', nav), esperado[idioma])
                for id_ in esperado[idioma]:
                    self.assertIn(f'id="{id_[1:]}"', html)


class TestCabecera(unittest.TestCase):
    def test_aviso_lleva_a_novedades_sin_descargar(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                aviso = leer(ruta)
                aviso = aviso[aviso.index('class="aviso-version"'):aviso.index("<header")]
                a = re.search(r"<a ([^>]*)>", aviso).group(1)
                self.assertIn('href="%s"' % ("/novedades/" if idioma == "en" else "/es/novedades/"), a)
                for prohibido in ("data-a-bloque", "data-descarga", "download", "goatcounter"):
                    self.assertNotIn(prohibido, a)

    def test_hero_sin_precio_de_ia_y_con_nota_de_version(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                hero = html[html.index('<section class="portada"'):html.index("</section>", html.index('<section class="portada"'))]
                self.assertNotRegex(hero, r"5 € (al mes|a month|per month)")
                self.assertRegex(hero, r'<p class="nota-hero"><span>(Versión|Version) <span data-version>[\d.]+</span> · ZIP · ')
                self.assertIn('href="%s"' % ("/safety/" if idioma == "en" else "/es/seguridad/"), hero)
                # columna izquierda: etiqueta, titular, entrada, hueco móvil, botón, nota, ventajas; el vídeo, solo a la derecha
                orden = [hero.index(x) for x in ('class="eti"', "<h1>", 'class="sub"', "data-movil-aqui", 'class="hero-cta"', 'class="nota-hero"', 'class="nota-desc"', 'class="hero-medio"')]
                self.assertEqual(orden, sorted(orden))
                self.assertEqual(hero.count('class="hero-cta"'), 1)
                self.assertLess(hero.index('class="hero-cta"'), hero.index("<video"))


class TestBotonesDeDescarga(unittest.TestCase):
    def test_cinco_botones_con_sus_titulos_y_atributos(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                botones = re.findall(r'<a class="boton prim descarga"[^>]*>', html)
                self.assertEqual(len(botones), 5)
                titulos = [re.search(r'data-goatcounter-title="([^"]*)"', b).group(1) for b in botones]
                self.assertEqual(titulos, [f"descarga-{l}-{idioma}" for l in ("cabecera", "hero", "motivos", "funciones", "final")])
                zips = {re.search(r'href="([^"]*)"', b).group(1) for b in botones}
                self.assertEqual(len(zips), 1)
                for b in botones:
                    for atributo in ("download", "data-a-bloque", "data-descarga", 'data-goatcounter-click="descarga"', 'rel="noopener"'):
                        self.assertIn(atributo, b)

    def test_botones_de_motivos_funciones_y_final_en_su_sitio(self):
        for idioma, ruta in PORTADAS.items():
            html = leer(ruta)
            for id_, lugar in (("motivos", "motivos"), ("funciones", "funciones"), ("final", "final")):
                with self.subTest(idioma=idioma, seccion=id_):
                    self.assertIn(f'data-goatcounter-title="descarga-{lugar}-{idioma}"', seccion(html, id_))

    def test_franja_final(self):
        titulo = {"en": "Start logging your games today", "es": "Empieza a registrar tus partidas hoy"}
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                final = seccion(leer(ruta), "final")
                self.assertIn(f"<h2>{titulo[idioma]}</h2>", final)
                self.assertRegex(final, r"<span data-version>[\d.]+</span> · ZIP · ")

    def test_descarga_js_convierte_los_botones_en_telefono(self):
        js = leer(RAIZ / "descarga.js")
        self.assertIn('querySelectorAll("a[data-a-bloque]")', js)
        self.assertIn('setAttribute("href", "#descargar")', js)


class TestConfianza(unittest.TestCase):
    def test_cuatro_elementos_y_el_cuarto_enlaza_a_seguridad(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                s = seccion(leer(ruta), "confianza")
                self.assertEqual(s.count("<li>"), 4)
                self.assertEqual(s.count("<b>"), 4)
                destino = "/safety/" if idioma == "en" else "/es/seguridad/"
                self.assertEqual(re.findall(r'href="([^"]*)"', s), [destino])
                self.assertIn("VirusTotal", s)

    def test_css_en_dos_columnas_en_telefono(self):
        for ruta in PORTADAS.values():
            html = leer(ruta)
            self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr))", html)
            self.assertRegex(html, r"@media \(max-width: 900px\) \{\s*\.novedades\.dos[^}]*\}\s*\.motivos[^}]*\}\s*\.confianza-lista \{ grid-template-columns: repeat\(2, minmax\(0, 1fr\)\); \}")


class TestMotivos(unittest.TestCase):
    def test_tres_clips_que_existen_y_no_se_descargan_hasta_reproducirse(self):
        for idioma, ruta in PORTADAS.items():
            pre = "" if idioma == "en" else "../"
            s = seccion(leer(ruta), "motivos")
            figuras = re.findall(r'<figure class="video">.*?</figure>', s, re.S)
            with self.subTest(idioma=idioma):
                self.assertEqual(len(figuras), 3)
                for clip, f in zip(CLIPS, figuras):
                    self.assertIn('preload="none"', f)
                    self.assertIn(f'poster="{pre}video/funciones/{clip}.jpg"', f)
                    self.assertIn(f'<source src="{pre}video/funciones/{clip}.mp4" type="video/mp4">', f)
                    self.assertTrue((RAIZ / "video" / "funciones" / f"{clip}.jpg").is_file())
                    self.assertTrue((RAIZ / "video" / "funciones" / f"{clip}.mp4").is_file())
                    aria = re.search(r'aria-label="([^"]*)"', f).group(1)
                    self.assertGreater(len(aria), 30)
                    self.assertNotRegex(aria, r"(?i)windows")
                self.assertEqual(s.count('class="novedad"'), 3)


class TestSeccionesMovidas(unittest.TestCase):
    def test_mtgo_dos_tarjetas_y_enlace(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                s = seccion(leer(ruta), "mtgo")
                self.assertEqual(s.count('class="novedad"'), 2)
                self.assertIn("mtgo_panel.jpg", s)
                self.assertIn("mtgo_banquillo.jpg", s)
                self.assertIn('href="%s"' % ("/magic-online/" if idioma == "en" else "/es/magic-online/"), s)
                self.assertNotIn("mtgo-caja", s)

    def test_coaches_dos_tarjetas_y_un_unico_enlace_a_la_guia(self):
        guia = {"en": "/coaches/", "es": "/es/coaches/"}
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                s = seccion(html, "coaches")
                self.assertEqual(s.count('class="novedad"'), 2)
                self.assertIn("v22_informe_sesion.jpg", s)
                self.assertIn("v22_tendencias.jpg", s)
                self.assertEqual(s.count(f'href="{guia[idioma]}"'), 1)
                self.assertNotIn(f'class="enlace-man" href="{guia[idioma]}"', seccion(html, "funciones"))

    def test_empezar_tres_pasos_con_windows_y_details(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                s = seccion(leer(ruta), "empezar")
                self.assertEqual(s.count('<div class="paso">'), 3)
                self.assertIn("Windows 10 u 11" if idioma == "es" else "Windows 10 or 11", s)
                self.assertIn("destacado", s)
                self.assertIn("<summary>¿Ya tenías ManaLab?</summary>" if idioma == "es" else "<summary>Already have ManaLab?</summary>", s)
                self.assertNotRegex(s, r"5 € (al mes|a month|per month)")
                self.assertNotIn("Ko-fi", s)


class TestLegibilidad(unittest.TestCase):
    def test_textos_bajo_botones_y_pies_de_captura_a_14px(self):
        for ruta in PORTADAS.values():
            css = leer(ruta)
            for regla in (".nota-descarga", ".nota-smartscreen", ".nota-desc", ".pie-captura", ".nota-hero"):
                m = re.search(re.escape(regla) + r" \{[^}]*?font-size: ([\d.]+)px", css)
                self.assertIsNotNone(m, regla)
                self.assertGreaterEqual(float(m.group(1)), 14, regla)

    def test_zonas_tactiles_de_44px_en_telefono(self):
        for ruta in PORTADAS.values():
            css = leer(ruta)
            bloque = css[css.index("@media (max-width: 767px) {\n  .seccion"):]
            bloque = bloque[:bloque.index("\n}\n")]
            self.assertIn(".movil-zip a { display: inline-flex; align-items: center; min-height: 44px; }", bloque)
            self.assertIn("footer .fila a, footer .guias a { display: inline-flex; align-items: center; min-height: 44px; }", bloque)


class TestPaginaDeNovedades(unittest.TestCase):
    def test_hreflang_reciproco_canonical_y_sitemap(self):
        sitemap = leer(RAIZ / "sitemap.xml")
        for idioma, ruta in NOVEDADES.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                self.assertIn(f'<link href="{URL[idioma]}" rel="canonical"/>', html)
                self.assertIn('<link href="https://manalab.es/novedades/" hreflang="en" rel="alternate"/>', html)
                self.assertIn('<link href="https://manalab.es/es/novedades/" hreflang="es" rel="alternate"/>', html)
                self.assertIn('<link href="https://manalab.es/novedades/" hreflang="x-default" rel="alternate"/>', html)
                self.assertNotIn("noindex", html)
                self.assertIn("goatcounter", html)
                self.assertIn("https://manalab.es/img/og.jpg", html)
                self.assertEqual(html.count("<h1>"), 1)
                self.assertIn(f"<loc>{URL[idioma]}</loc>", sitemap)
        self.assertEqual(sitemap.count("<loc>"), 21)

    def test_titulos_descripciones_y_h1(self):
        esperado = {"en": ("What&#x27;s new in ManaLab 2.3 · Release notes", "What&#x27;s new in ManaLab"),
                    "es": ("Novedades de ManaLab 2.3 · Historial de versiones", "Novedades de ManaLab")}
        for idioma, ruta in NOVEDADES.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                self.assertIn(f"<title>{esperado[idioma][0]}</title>", html)
                self.assertIn(f"<h1>{esperado[idioma][1]}</h1>", html)
                self.assertRegex(html, r'<meta content="(What changed in ManaLab 2.3 and 2.2|Qué cambió en ManaLab 2.3 y 2.2):[^"]*" name="description"/>')

    def test_contenido_identico_al_de_main_y_boton_arriba(self):
        for idioma, ruta in NOVEDADES.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                self.assertEqual(html.count('class="novedad"'), 6)   # las 2 de Arena y Magic Online + las 4 de la 2.2, también las que siguen en la portada
                self.assertEqual(html.count('class="funcion"'), 6)
                self.assertIn('class="mtgo-caja"', html)
                self.assertIn('id="novedades"', html)
                self.assertIn('id="anteriores"', html)
                self.assertIn('href="%s"' % ("/#descargar" if idioma == "en" else "/es/#descargar"), html)
                self.assertLess(html.index("#descargar", html.index("<h1>")), html.index('id="novedades"'))
                # ninguna ruta relativa de imagen apunta fuera
                for src in re.findall(r'src="([^"/][^"]*)"', html):
                    self.assertTrue((ruta.parent / src).resolve().is_file(), src)

    def test_pie_de_las_portadas_enlaza_a_novedades(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                pie = html[html.index("<footer>"):]
                self.assertIn('<a href="%s">%s</a>' % ("/novedades/" if idioma == "en" else "/es/novedades/", "What's new" if idioma == "en" else "Novedades"), pie)

    def test_enlaces_internos_de_las_paginas_de_novedades_no_estan_rotos(self):
        for idioma, ruta in NOVEDADES.items():
            html = leer(ruta)
            ids = set(re.findall(r'id="([^"]*)"', html))
            for ancla in re.findall(r'href="#([^"]+)"', html):
                with self.subTest(idioma=idioma, ancla=ancla):
                    self.assertIn(ancla, ids)


class TestSinPrecioEnLaCabecera(unittest.TestCase):
    def test_section_portada_sin_5_euros(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = leer(ruta)
                inicio = html.index('<section class="portada"')
                hero = html[inicio:html.index("</section>", inicio)]
                for texto in ("5 € al mes", "5 € per month", "5 € a month"):
                    self.assertNotIn(texto, hero)


if __name__ == "__main__":
    unittest.main()
