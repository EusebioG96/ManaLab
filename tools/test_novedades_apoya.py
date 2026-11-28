#!/usr/bin/env python3
"""ML-381: dos fallos visibles de manalab.es, en un navegador real (Chromium con Playwright; se salta si no están).

1. La rejilla de novedades de la 3.0 (7 celdas en 3 columnas) dejaba dos huecos grises al final: sus celdas deben llenar la rejilla entera,
   sin huecos, a 1366, 1040 y 375 px (y la rejilla de funciones de las cuatro portadas, que no debe cambiar).
2. El bloque «Apoya el proyecto» llevaba el título «Gratis, con análisis de IA por suscripción» (de otro bloque) y ocupaba solo media caja:
   debe llevar su título y el contenido debe ocupar la caja entera.

Uso:  python3 -m pytest tools/test_novedades_apoya.py
"""
import functools
import http.server
import socketserver
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

ANCHOS = (1366, 1040, 375)
NOVEDADES = {"en": "/novedades/", "es": "/es/novedades/"}  # la página de novedades solo existe en inglés y español
PORTADAS = {"en": "/", "es": "/es/", "pt": "/pt/", "ja": "/ja/"}
TITULO_APOYO = {"en": "Help keep ManaLab going", "es": "Ayuda a que ManaLab siga adelante"}  # el bloque solo está en en y es
TITULOS_AJENOS = ("Free, with AI analysis by subscription", "Gratis, con análisis de IA por suscripción")
TOLERANCIA = 1.5  # px: redondeos de subpíxel entre celdas

# Mide las celdas de una rejilla: filas (por su borde superior) con el borde izquierdo y derecho de cada celda, y el interior de la rejilla.
MEDIR_REJILLA = """(sel) => {
  const g = document.querySelector(sel); const r = g.getBoundingClientRect();
  const cs = getComputedStyle(g), bi = parseFloat(cs.borderLeftWidth), bd = parseFloat(cs.borderRightWidth);
  const celdas = [...g.children].map(c => { const b = c.getBoundingClientRect(); return {top: b.top, bottom: b.bottom, left: b.left, right: b.right}; });
  return {izq: r.left + bi, der: r.right - bd, celdas, desborde: document.documentElement.scrollWidth - innerWidth};
}"""
MEDIR_APOYO = """() => {
  const caja = document.querySelector('.apoyo'), hijo = caja.firstElementChild, cs = getComputedStyle(caja);
  const c = caja.getBoundingClientRect(), h = hijo.getBoundingClientRect();
  return {cajaInterior: caja.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight), contenido: h.width, titulo: caja.querySelector('h3').textContent.trim(),
          desborde: document.documentElement.scrollWidth - innerWidth};
}"""


def filas(celdas: list[dict]) -> list[list[dict]]:
    """Agrupa las celdas por fila (mismo borde superior, con tolerancia), cada fila ordenada de izquierda a derecha."""
    resultado: list[list[dict]] = []
    for celda in sorted(celdas, key=lambda c: (c["top"], c["left"])):
        if resultado and abs(resultado[-1][0]["top"] - celda["top"]) <= TOLERANCIA:
            resultado[-1].append(celda)
        else:
            resultado.append([celda])
    return resultado


def huecos(medida: dict) -> list[str]:
    """Describe cada hueco de la rejilla: fila que no llega a los dos bordes, o celdas de una fila que no se tocan (salvo el 1 px de separación)."""
    problemas = []
    for numero, fila in enumerate(filas(medida["celdas"]), 1):
        if abs(fila[0]["left"] - medida["izq"]) > TOLERANCIA or abs(fila[-1]["right"] - medida["der"]) > TOLERANCIA:
            problemas.append(f"fila {numero}: no llena el ancho ({fila[0]['left']:.1f}-{fila[-1]['right']:.1f} de {medida['izq']:.1f}-{medida['der']:.1f})")
        for a, b in zip(fila, fila[1:]):
            if b["left"] - a["right"] > 1 + TOLERANCIA:
                problemas.append(f"fila {numero}: hueco de {b['left'] - a['right']:.1f}px entre celdas")
    return problemas


@unittest.skipIf(sync_playwright is None, "Playwright no está instalado")
class NovedadesYApoya(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        manejador = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(RAIZ))
        manejador.log_message = lambda *a, **k: None  # type: ignore[attr-defined]  # silencio: sin ruido del servidor de pruebas
        cls.servidor = socketserver.TCPServer(("127.0.0.1", 0), manejador)
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        cls.pw = sync_playwright().start()
        try:
            cls.navegador = cls.pw.chromium.launch()
        except Exception as error:  # silencio: sin Chromium instalado la prueba se salta  # noqa: BLE001
            cls.pw.stop()
            cls.servidor.shutdown()
            raise unittest.SkipTest(f"Chromium no disponible: {error}")

    @classmethod
    def tearDownClass(cls):
        cls.navegador.close()
        cls.pw.stop()
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def abrir(self, ruta: str, ancho: int):
        pagina = self.navegador.new_page(viewport={"width": ancho, "height": 900})
        self.addCleanup(pagina.close)
        pagina.route("**/*", lambda r: r.continue_() if r.request.url.startswith(self.base) else r.abort())  # nada sale a la red
        pagina.goto(self.base + ruta, wait_until="load")
        return pagina

    def test_novedades_3_0_sin_huecos(self):
        for idioma, ruta in NOVEDADES.items():
            for ancho in ANCHOS:
                with self.subTest(idioma=idioma, ancho=ancho):
                    medida = self.abrir(ruta, ancho).evaluate(MEDIR_REJILLA, "#novedades-3-0 .funciones")
                    self.assertEqual(len(medida["celdas"]), 7)
                    self.assertEqual(huecos(medida), [])
                    self.assertLessEqual(medida["desborde"], 0)

    def test_rejilla_de_funciones_de_las_portadas_sin_huecos(self):
        for idioma, ruta in PORTADAS.items():
            for ancho in ANCHOS:
                with self.subTest(idioma=idioma, ancho=ancho):
                    medida = self.abrir(ruta, ancho).evaluate(MEDIR_REJILLA, ".funciones")
                    self.assertEqual(huecos(medida), [])

    def test_apoya_el_proyecto_tiene_su_titulo_y_ocupa_la_caja(self):
        for idioma, titulo in TITULO_APOYO.items():
            for ancho in ANCHOS:
                with self.subTest(idioma=idioma, ancho=ancho):
                    medida = self.abrir(PORTADAS[idioma], ancho).evaluate(MEDIR_APOYO)
                    self.assertEqual(medida["titulo"], titulo)
                    self.assertNotIn(medida["titulo"], TITULOS_AJENOS)
                    self.assertGreaterEqual(medida["contenido"], medida["cajaInterior"] - TOLERANCIA, "el contenido deja media caja vacía")
                    self.assertLessEqual(medida["desborde"], 0)


if __name__ == "__main__":
    unittest.main()
