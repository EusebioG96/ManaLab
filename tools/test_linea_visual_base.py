#!/usr/bin/env python3
"""Base visual «La mesa de juego» (ML-272, WEB-01 y WEB-02): menú de teléfono en todas las cabeceras, fuentes solo locales
y ni fuentes viejas ni color carmesí en el CSS de las páginas con cabecera. Sin red.

Uso:  python3 -m pytest tools/test_linea_visual_base.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLAS = RAIZ / "plantillas"
# nombre accesible esperado del botón del menú en cada idioma de cabecera
NOMBRE_MENU = {"es": "Menú", "en": "Menu", "pt": "Menu", "ja": "メニュー"}
# Lo que ya no puede aparecer en el CSS de sitio y seguridad: las fuentes de antes y el carmesí (hex, rgb y nombre de variable)
PROHIBIDO_EN_CSS = [
    r"Saira", r"Figtree", r"c2363f", r"d6454f", r"3d0d14", r"24090d", r"f06b74",
    r"194,\s*54,\s*63", r"240,\s*107,\s*116", r"--carmesi", r"--rojo",
]
# En español, inglés, portugués y japonés viven las cabeceras con `.cab`; la guía (WEB-07) tiene la suya
CABECERAS_PROPIAS = ("es", "en", "pt")
FUENTES_ESPERADAS = {"Marcellus", "Geist", "Geist Mono"}


def cabeceras():
    """Cada texto de cabecera con su idioma: las variantes de cabecera_<idioma>/1.<v>.txt y cabecera_ja.tpl y cabecera_ja_learn.tpl."""
    for idioma in CABECERAS_PROPIAS:
        for f in sorted((PLANTILLAS / f"cabecera_{idioma}").glob("1.*.txt")):
            yield idioma, f.relative_to(PLANTILLAS).as_posix(), f.read_text(encoding="utf-8")
    for nombre in ("cabecera_ja.tpl", "cabecera_ja_learn.tpl"):   # la de la portada y la de la página Learn (ML-324)
        yield "ja", nombre, (PLANTILLAS / nombre).read_text(encoding="utf-8")


def css_de_plantillas():
    """Las plantillas de CSS de sitio y seguridad con todas sus variantes (los huecos), tal como pueden salir en una página."""
    for f in [PLANTILLAS / "css_sitio.tpl", PLANTILLAS / "css_seguridad.tpl", *sorted((PLANTILLAS / "css_sitio").glob("*.txt"))]:
        yield f.relative_to(PLANTILLAS).as_posix(), f.read_text(encoding="utf-8")


def paginas_con_cabecera():
    for f in sorted(RAIZ.rglob("*.html")):
        if ".git" in f.parts:
            continue
        t = f.read_text(encoding="utf-8")
        if '<header class="cab">' in t:
            yield f.relative_to(RAIZ).as_posix(), t


class TestMenuDeTelefono(unittest.TestCase):
    def test_todas_las_cabeceras_llevan_el_menu_con_nombre_accesible(self):
        total = 0
        for idioma, nombre, t in cabeceras():
            total += 1
            with self.subTest(nombre):
                self.assertEqual(t.count('<details class="menu">'), 1)
                self.assertIn(f'<summary aria-label="{NOMBRE_MENU[idioma]}">', t)
                self.assertNotIn("<script", t, "el menú no lleva JavaScript")
        self.assertGreaterEqual(total, 17, "faltan variantes de cabecera")

    def test_el_menu_repite_los_enlaces_y_los_idiomas_de_la_fila(self):
        for _idioma, nombre, t in cabeceras():
            with self.subTest(nombre):
                fila, menu = t.split('<details class="menu">')
                self.assertEqual(re.findall(r"<nav .*?</nav>", menu, re.S), re.findall(r"<nav .*?</nav>", fila, re.S))
                en_fila = [re.sub(r' id="idioma"', "", a) for a in re.findall(r'<a class="idioma"[^>]*>.*?</a>', fila)]
                self.assertEqual(re.findall(r'<a class="idioma"[^>]*>.*?</a>', menu), en_fila)
                self.assertNotIn('id="', menu, "un id repetido en el menú")

    def test_la_pagina_generada_tiene_el_menu_despues_de_descargar(self):
        paginas = list(paginas_con_cabecera())
        self.assertGreaterEqual(len(paginas), 18)
        for ruta, t in paginas:
            cab = t[t.index('<header class="cab">'):t.index("</header>")]
            with self.subTest(ruta):
                self.assertLess(cab.index('class="boton prim'), cab.index('<details class="menu">'))
                self.assertRegex(cab, r'<summary aria-label="[^"]+">')

    def test_css_menu_oculto_en_escritorio_y_descargar_conserva_su_texto(self):
        for nombre, t in css_de_plantillas():
            if nombre not in ("css_sitio.tpl", "css_seguridad.tpl"):
                continue
            with self.subTest(nombre):
                self.assertIn(".menu { display: none; }", t)
                self.assertIn(".menu { display: block; }", t)
                self.assertIn(".cab .envoltura > nav, .cab .envoltura > .idioma { display: none; }", t)
                self.assertNotRegex(t, r"\.cab \.boton span\s*\{\s*display:\s*none", "«Descargar» no puede quedarse en un icono")


class TestFuentesLocales(unittest.TestCase):
    def test_font_face_solo_apuntan_a_fuentes(self):
        for nombre, html in paginas_con_cabecera():
            caras = re.findall(r"@font-face\s*\{[^}]*\}", html)
            with self.subTest(nombre):
                self.assertEqual(len(caras), 12)
                self.assertEqual({re.search(r"font-family:'([^']+)'", c).group(1) for c in caras}, FUENTES_ESPERADAS)
                for c in caras:
                    url = re.search(r"url\(([^)]+)\)", c).group(1)
                    self.assertTrue(url.startswith("/fuentes/"), url)
                    self.assertTrue((RAIZ / url.lstrip("/")).is_file(), url)
                self.assertNotRegex(html, r"https?://[^\"')\s]*\.(woff2?|ttf|otf)")
                self.assertNotIn("fonts.googleapis", html)
                self.assertNotIn("fonts.gstatic", html)

    def test_las_licencias_estan_junto_a_las_fuentes(self):
        for lic in ("OFL-Marcellus.txt", "OFL-Geist.txt"):
            self.assertIn("SIL OPEN FONT LICENSE", (RAIZ / "fuentes" / lic).read_text(encoding="utf-8"))
        self.assertEqual(sorted(p.name for p in (RAIZ / "fuentes").glob("*.woff2") if not p.name.startswith(("marcellus", "geist"))), [])


class TestSinRestosDelDisenoAnterior(unittest.TestCase):
    def test_el_css_de_sitio_y_seguridad_no_tiene_fuentes_viejas_ni_carmesi(self):
        for nombre, t in css_de_plantillas():
            for patron in PROHIBIDO_EN_CSS:
                with self.subTest(f"{nombre} {patron}"):
                    self.assertIsNone(re.search(patron, t, re.I), f"{nombre} todavía contiene {patron}")

    def test_las_paginas_generadas_tampoco(self):
        for nombre, html in paginas_con_cabecera():
            estilos = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))
            for patron in PROHIBIDO_EN_CSS:
                with self.subTest(f"{nombre} {patron}"):
                    self.assertIsNone(re.search(patron, estilos, re.I))

    def test_las_paginas_no_precargan_fuentes_viejas(self):
        for nombre, html in paginas_con_cabecera():
            with self.subTest(nombre):
                pre = re.findall(r'<link rel="preload" href="([^"]+)" as="font"', html)
                self.assertEqual(sorted(pre), ["/fuentes/geist-sans-latin-400-normal.woff2", "/fuentes/marcellus-latin-400-normal.woff2"])

    def test_fondo_de_mesa_sin_resplandor_en_la_portada_y_sin_movimiento_si_se_pide(self):
        for nombre, t in css_de_plantillas():
            if nombre in ("css_sitio.tpl", "css_seguridad.tpl"):
                with self.subTest(nombre):
                    self.assertIn("radial-gradient(1300px 760px at 70% -6%, #22302a 0%, #0d100f 60%)", t)
                    self.assertNotRegex(t, r"\.(portada|p404)::before\s*\{[^}]*radial-gradient")
                    self.assertIn("@media (prefers-reduced-motion: reduce)", t)
                    self.assertIn("transition: none !important", t)

    def test_la_404_no_conserva_el_resplandor(self):
        resto = "\n".join(t for nombre, t in css_de_plantillas() if nombre.startswith("css_sitio/"))
        self.assertIn(".p404", resto)
        self.assertNotRegex(resto, r"\.(portada|p404)::before")


if __name__ == "__main__":
    unittest.main()
