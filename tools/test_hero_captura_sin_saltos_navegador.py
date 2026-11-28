#!/usr/bin/env python3
"""ML-406: la captura del héroe (``.hero-medio img``) reserva su hueco antes de cargar: sin salto de maquetación.

En coaches (en, es, pt) y Magic Online (en, es) el héroe es una captura dentro de ``.hero-medio``, una rejilla con ``justify-items: start``.
La ventana de la captura se encogía a su contenido y la imagen medía 0 hasta cargar, así que los atributos width y height no reservaban nada:
CLS de 0,11 a 0,12 en escritorio con carga lenta. Aquí la imagen se retrasa y se mide el CLS (``PerformanceObserver`` de layout-shift).

Uso:  python3 -m pytest tools/test_hero_captura_sin_saltos_navegador.py
"""
import sys
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from test_huecos_mdn_navegador import Servidor, sitio

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

PAGINAS = ("/coaches/", "/es/coaches/", "/pt/coaches/", "/magic-online/", "/es/magic-online/")
ANCHOS = (1366, 390)
LIMITE_CLS = 0.05
RETRASO_IMAGEN_S = 1.2   # la imagen llega después del primer pintado, como con una red lenta
CLS_ENTRADA = """window.__cls = 0; new PerformanceObserver(function (l) { l.getEntries().forEach(function (e) {
  if (!e.hadRecentInput) window.__cls += e.value; }); }).observe({ type: "layout-shift", buffered: true });"""
ALTO_IMAGEN = "document.querySelector('.hero-medio img').getBoundingClientRect().height"


def es_captura_del_heroe(url: str) -> bool:
    return url.split("?")[0].endswith((".jpg", ".webp", ".png")) and ("coaches_informe" in url or "mtgo_panel" in url)


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class HeroCapturaSinSaltos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.nav = cls.pw.chromium.launch()
        except Exception as error:  # noqa: BLE001  silencio: sin Chromium instalado la prueba se salta
            cls.pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {error}")
        cls.web = Servidor(sitio())

    @classmethod
    def tearDownClass(cls):
        cls.web.cerrar()
        cls.nav.close()
        cls.pw.stop()

    def cargar_con_imagen_retrasada(self, ruta: str, ancho: int) -> tuple[float, float, int]:
        """Devuelve (CLS, alto de la imagen mientras no ha llegado, imágenes del héroe retrasadas)."""
        contexto = self.nav.new_context(viewport={"width": ancho, "height": 800})
        pagina = contexto.new_page()
        pagina.add_init_script(CLS_ENTRADA)
        retrasadas = []
        altos = []

        def ruta_red(r):
            if es_captura_del_heroe(r.request.url):
                retrasadas.append(r.request.url)
                altos.append(pagina.evaluate(ALTO_IMAGEN))
                time.sleep(RETRASO_IMAGEN_S)
            r.continue_()
        pagina.route("**/*", ruta_red)
        pagina.goto(self.web.url + ruta, wait_until="load")
        pagina.wait_for_timeout(500)
        cls = pagina.evaluate("window.__cls")
        contexto.close()
        return cls, (altos[0] if altos else 0.0), len(retrasadas)

    def test_la_captura_del_heroe_no_hace_saltar_la_pagina(self):
        for ruta in PAGINAS:
            for ancho in ANCHOS:
                with self.subTest(ruta=ruta, ancho=ancho):
                    cls, alto_antes_de_cargar, retrasadas = self.cargar_con_imagen_retrasada(ruta, ancho)
                    self.assertGreater(retrasadas, 0, "la prueba no retrasó ninguna captura del héroe: el filtro de la ruta no coincide")
                    self.assertLessEqual(cls, LIMITE_CLS, f"CLS {cls:.3f} de la carga de {ruta} a {ancho} px")
                    self.assertGreater(alto_antes_de_cargar, 50, "la imagen no reserva su alto antes de cargar")


if __name__ == "__main__":
    unittest.main()
