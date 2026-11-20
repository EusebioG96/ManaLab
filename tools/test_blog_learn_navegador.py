#!/usr/bin/env python3
"""ML-345 (BLOG-01): el post del blog «Learn» en en, es, pt y ja en un navegador real (Chromium con Playwright; se salta si no están): sin
desplazamiento horizontal a 390 y 1366 px, sin errores de consola ni de página, con el H1, la fecha y el botón final a la vista y sin ningún hueco
visible donde irá la captura.

Uso:  python3 -m pytest tools/test_blog_learn_navegador.py
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from test_blog_learn import PAGINAS, RUTA
from test_huecos_mdn_navegador import Servidor, sitio
from test_pagina_player_log_navegador import abrir

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

ANCHOS = (390, 1366)
MEDIDAS = """() => { const ancho = document.documentElement.clientWidth, caja = e => e.getBoundingClientRect();
  const h1 = document.querySelector('h1'), autoria = document.querySelector('.autoria'), boton = document.querySelector('.cuerpo-blog .boton');
  const cuerpo = document.querySelector('.cuerpo-blog'), hijos = [...cuerpo.children];
  const sobresale = [...document.querySelectorAll('main *')].filter(e => caja(e).right > ancho + 0.5 && e.checkVisibility()).map(e => e.tagName);
  const huecos = hijos.filter(e => e.tagName === 'P' && !e.textContent.trim()).length;
  return { desborde: document.documentElement.scrollWidth - ancho, sobresale, h1: h1.checkVisibility() && h1.textContent.trim(),
           autoria: autoria.checkVisibility() && autoria.textContent.replace(/\\s+/g, ' ').trim(),
           boton: boton.checkVisibility() && boton.textContent.trim(), botonDerecha: caja(boton).right, ancho,
           h2: document.querySelectorAll('.cuerpo-blog h2').length, imagenes: document.querySelectorAll('main img, main figure').length, huecos,
           menu: getComputedStyle(document.querySelector('.menu')).display, columna: caja(cuerpo).width }; }"""


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class BlogLearnNavegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.nav = cls.pw.chromium.launch()
        except Exception as error:  # noqa: BLE001  silencio: sin Chromium instalado la prueba se salta
            cls.pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {error}")
        cls.raiz = sitio()
        cls.web = Servidor(cls.raiz)

    @classmethod
    def tearDownClass(cls):
        cls.web.cerrar()
        cls.nav.close()
        cls.pw.stop()

    def test_sin_desborde_ni_errores_en_los_cuatro_idiomas(self):
        for idioma, datos in PAGINAS.items():
            titulo, fecha, boton = datos[4], datos[11], datos[9]
            for ancho in ANCHOS:
                errores: list = []
                contexto, pagina = abrir(self.nav, f"{self.web.url}/{datos[0]}{RUTA}", ancho, errores)
                try:
                    m = pagina.evaluate(MEDIDAS)
                finally:
                    contexto.close()
                with self.subTest(idioma=idioma, ancho=ancho):
                    self.assertLessEqual(m["desborde"], 0, "hay desplazamiento horizontal")
                    self.assertEqual(m["sobresale"], [], "algún elemento se sale de la pantalla")
                    self.assertEqual(errores, [])
                    self.assertEqual(m["h1"], titulo)
                    self.assertEqual(m["autoria"], f"{fecha} · ManaLab")
                    self.assertEqual(m["boton"], boton)
                    self.assertLessEqual(m["botonDerecha"], m["ancho"])
                    self.assertEqual(m["h2"], 5)
                    self.assertEqual((m["imagenes"], m["huecos"]), (0, 0), "ningún hueco visible donde irá la captura")
                    self.assertEqual(m["menu"], "block" if ancho < 900 else "none", "el menú de teléfono solo por debajo de 900 px")
                    self.assertLessEqual(m["columna"], 720.5, "columna de lectura")

    def test_la_medida_detecta_un_desborde(self):
        """Mutación permanente: una palabra larga sin salto a 390 px desborda y la medida lo ve (si no, el test de arriba no mide nada)."""
        (self.raiz / "desborde.html").write_text(
            "<!doctype html><meta charset=utf-8><body style='margin:0'><main><h1>x</h1><p class=autoria>y</p><div class=cuerpo-blog><a class=boton style='white-space:nowrap'>"
            + "x" * 200 + "</a></div></main><div class=menu></div></body>", encoding="utf-8")
        contexto, pagina = abrir(self.nav, f"{self.web.url}/desborde.html", 390, [])
        try:
            m = pagina.evaluate(MEDIDAS)
            self.assertGreater(m["desborde"], 0)
            self.assertTrue(m["sobresale"])
        finally:
            contexto.close()


if __name__ == "__main__":
    unittest.main()
