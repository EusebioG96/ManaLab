#!/usr/bin/env python3
"""Páginas interiores y guías de «La mesa de juego» (ML-275, WEB-04, WEB-06 y WEB-07): inclinación solo en escritorio y solo en
capturas fijas, nada viejo en las hojas interiores, guías siempre oscuras en pantalla con la impresión intacta. Sin red.

Uso:  python3 -m pytest tools/test_interiores_y_guias.py
"""
import hashlib
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLAS = RAIZ / "plantillas"
VIEJO = [r"Saira", r"Figtree", r"c2363f", r"d6454f", r"0d0304", r"1a0a0d", r"3a1d22", r"e8b07c", r"f4eae4", r"c9b8b0",
         r"--rojo", r"--carmesi", r"194,\s*54,\s*63"]
# La hoja de impresión de las guías tal como estaba antes de ML-275: el PDF del manual no puede cambiar
IMPRESION_GUIA = """@page{size:A4;margin:16mm 14mm}
@media print{
  body{background:#fff;color:#000}
  main{max-width:none;padding:0}
  h1{color:#4b2fa0}
  section h2{color:#4b2fa0}
  nav.indice{background:#fff}
  nav.inicio,footer nav{display:none}
  figure{background:#fff}
  figure.video video{display:none}
  figure.video img.solo-pdf{display:block;width:62%;height:auto;margin:0 auto;border:1px solid #ccc;border-radius:6px}
  span.solo-pdf{display:block;margin-top:4px}
  a{color:inherit}
}"""
BASE_CLARA_GUIA = ":root{--bg:#f7f6f2;--fg:#1d1d22;--muted:#5c5c66;--acc:#6b4fbb;--card:#fff;--line:#e3e1d9}"
# SHA-256 de la hoja de las guías de antes de ML-275 (sin las líneas del modo oscuro por sistema y sin @font-face)
HUELLA_BASE_GUIA = "d12edf38a66f55b21310047951e7e1d9db5884d8f8debc0faf9f34297f022197"
PAGINAS_INCLINADAS = ["magic-online", "novedades", "es/magic-online", "es/novedades"]
BLOQUE_INCLINACION = re.compile(r"@media \(min-width: 901px\)[^{]*\{(?P<c>.*?)\n\}", re.S)


def leer(ruta):
    return (PLANTILLAS / ruta).read_text(encoding="utf-8")


def bloque(texto, inicio):
    """El bloque `@media ... { ... }` que empieza en `inicio`, con sus llaves equilibradas."""
    i = texto.index(inicio)
    nivel = 0
    for j in range(texto.index("{", i), len(texto)):
        nivel += {"{": 1, "}": -1}.get(texto[j], 0)
        if nivel == 0:
            return texto[i:j + 1]
    raise AssertionError("llaves sin cerrar")


class TestInclinacion(unittest.TestCase):
    def test_la_inclinacion_solo_vive_en_escritorio_con_raton_y_sin_reducir_movimiento(self):
        css = leer("css_sitio.tpl")
        bloque_incl = bloque(css, "@media (min-width: 901px) and (hover: hover)")
        for condicion in ("(hover: hover)", "(pointer: fine)", "(prefers-reduced-motion: no-preference)"):
            self.assertIn(condicion, bloque_incl.split("{")[0])
        fuera = css.replace(bloque_incl, "")
        self.assertNotIn("rotateY", fuera, "una inclinación fuera de la consulta de escritorio con ratón")
        self.assertNotIn("rotateX", fuera)
        self.assertIn("rotateY(-14deg) rotateX(5deg)", bloque_incl)
        self.assertIn("transform: none", bloque_incl, "al pasar el ratón se endereza")

    def test_la_inclinacion_solo_afecta_a_capturas_marcadas(self):
        bloque_incl = bloque(leer("css_sitio.tpl"), "@media (min-width: 901px) and (hover: hover)")
        for sel in re.findall(r"([^{}]+)\{[^}]*rotate", bloque_incl):
            self.assertIn(".inclinable", sel)
        self.assertNotRegex(bloque_incl, r"\.ventana(?!\.inclinable)[^{]*\{[^}]*rotate")

    def test_ninguna_hoja_inclina_fuera_de_css_sitio(self):
        for f in PLANTILLAS.rglob("*"):
            if f.is_file() and f.suffix in (".tpl", ".txt") and f.name != "css_sitio.tpl":
                self.assertNotIn("rotateY", f.read_text(encoding="utf-8"), f.name)

    def test_solo_las_capturas_fijas_de_bloques_alternos_llevan_la_marca(self):
        total = 0
        for f in sorted((PLANTILLAS / "paginas").rglob("*.pagina")):
            actual = None
            for linea in f.read_text(encoding="utf-8").split("\n"):
                m = re.match(r'<div class="novedades([^"]*)"', linea)
                if m:
                    actual = m.group(1).split()
                elif re.search(r"</?section", linea):
                    actual = None
                if "inclinable" in linea:
                    total += 1
                    ruta = f.relative_to(PLANTILLAS / "paginas").parent.as_posix()
                    self.assertIn(ruta, PAGINAS_INCLINADAS, f"{f} no debería inclinar nada")
                    self.assertIsNotNone(actual, linea[:80])
                    self.assertNotIn("dos", actual, "las capturas en dos columnas no se inclinan")
                    self.assertRegex(linea, r'<div class="ventana(?: estrecha)? inclinable(?: estrecha)?"><picture>', "solo imágenes, nunca vídeo")
                    self.assertNotIn("<video", linea)
        self.assertEqual(total, 14)

    def test_las_paginas_generadas_no_inclinan_videos_ni_telefono(self):
        for f in RAIZ.rglob("*.html"):
            if ".git" in f.parts:
                continue
            t = f.read_text(encoding="utf-8")
            for m in re.finditer(r'class="ventana[^"]*inclinable[^"]*">(.{0,400})', t, re.S):
                self.assertTrue(m.group(1).startswith("<picture>"), f.name)
                self.assertNotIn("movil", m.group(1)[:300].lower())


class TestHojasInterioresSinRestosViejos(unittest.TestCase):
    HOJAS = ["css_seguridad.tpl", "css_privacidad.tpl", "css_sorteo.tpl", "css_guia.tpl"]

    def test_las_hojas_interiores_no_traen_fuentes_ni_colores_viejos(self):
        for hoja in self.HOJAS:
            for patron in VIEJO:
                with self.subTest(f"{hoja} {patron}"):
                    self.assertIsNone(re.search(patron, leer(hoja), re.I))

    def test_las_paginas_con_hoja_propia_usan_las_fuentes_nuevas(self):
        for hoja in ("css_privacidad.tpl", "css_sorteo.tpl", "css_guia.tpl"):
            t = leer(hoja)
            self.assertEqual(len(re.findall(r"@font-face", t)), 12, hoja)
            self.assertIn('"Marcellus"', t)
            self.assertIn('"Geist"', t)

    def test_el_color_de_tema_de_las_paginas_ya_no_es_el_viejo(self):
        for f in (PLANTILLAS / "paginas").rglob("*.pagina"):
            if "anuncio" not in f.parts:
                self.assertNotIn("0d0304", f.read_text(encoding="utf-8"), f)

    def test_privacidad_y_sorteo_son_una_columna_de_68_caracteres_con_rombo(self):
        for hoja in ("css_privacidad.tpl", "css_sorteo.tpl"):
            t = leer(hoja)
            self.assertIn("max-width: 68ch", t)
            self.assertIn("rotate(45deg)", t)
            self.assertIn(".idiomas a[aria-current] { background: var(--hueso)", t)

    def test_seguridad_sin_caja_con_rombo_y_disco_hueso(self):
        t = leer("css_seguridad.tpl")
        self.assertRegex(t, r"\.tarjeta \{ background: none; border: 0; border-top: 1px solid var\(--linea\)")
        self.assertIn("rotate(45deg)", t)
        self.assertNotIn('content: "✓"', t)
        self.assertRegex(t, r"\.tarjeta ol li::before \{[^}]*background: var\(--hueso\)")


class TestGuias(unittest.TestCase):
    def test_la_hoja_de_impresion_no_cambia(self):
        css = leer("css_guia.tpl")
        self.assertIn(IMPRESION_GUIA, css)
        self.assertIn(BASE_CLARA_GUIA, css, "las variables claras siguen siendo la base: el PDF sale claro")

    def test_el_resto_de_la_hoja_base_es_la_de_antes(self):
        css = leer("css_guia.tpl")
        base = re.sub(r"@font-face\{[^}]*\}\n", "", css[:css.index("\n/* WEB-07")]).strip()
        self.assertEqual(hashlib.sha256(base.encode()).hexdigest(), HUELLA_BASE_GUIA)

    def test_lo_nuevo_va_dentro_de_media_screen_y_no_hay_modo_oscuro_por_sistema(self):
        css = leer("css_guia.tpl")
        self.assertNotIn("prefers-color-scheme", css)
        self.assertNotIn("data-theme", css)
        pantalla = bloque(css, "@media screen {")
        resto = css.replace(pantalla, "").replace(IMPRESION_GUIA, "")
        resto = re.sub(r"@font-face\{[^}]*\}", "", resto)
        self.assertNotRegex(resto, r"Marcellus|Geist|0d100f|ece6d6", "un valor nuevo fuera de @media screen")
        for valor in ("--bg: #0d100f", "--fg: #ece6d6", "color-scheme: dark", "max-width: 68ch", "var(--oro)"):
            self.assertIn(valor, pantalla)
        self.assertIn("@media screen and (max-width: 560px) { nav.indice ol { columns: 1; } }", css)

    def test_las_nueve_guias_generadas_llevan_la_hoja_nueva(self):
        guias = sorted((RAIZ / "guia").glob("guia_manalab_*.html"))
        self.assertEqual(len(guias), 9)
        for g in guias:
            t = g.read_text(encoding="utf-8")
            with self.subTest(g.name):
                self.assertIn("@media screen {", t)
                self.assertIn(IMPRESION_GUIA, t)
                self.assertNotIn("prefers-color-scheme", t)
                self.assertNotRegex(t, r"https?://[^\"')\s]*\.woff")


if __name__ == "__main__":
    unittest.main()
