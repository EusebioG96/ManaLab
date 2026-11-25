#!/usr/bin/env python3
"""ML-343 y ML-344 (LOG-01): /player-log/ y /es/player-log/ en un navegador real (Chromium con Playwright; se salta si no están): sin desplazamiento horizontal a 390 y 1366 px,
sin errores de consola ni de página, las dos rutas se seleccionan enteras con un clic (sin JavaScript) y las respuestas de la FAQ se ven.

Uso:  python3 -m pytest tools/test_pagina_player_log_navegador.py
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from test_huecos_mdn_navegador import Servidor, sitio

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

ANCHOS = (390, 1366)
RUTAS = ("C:\\Users\\<your user>\\AppData\\LocalLow\\Wizards Of The Coast\\MTGA\\", r"%appdata%\..\LocalLow\Wizards Of The Coast\MTGA")
RUTAS_ES = ("C:\\Users\\<tu usuario>\\AppData\\LocalLow\\Wizards Of The Coast\\MTGA\\", r"%appdata%\..\LocalLow\Wizards Of The Coast\MTGA")
# (ruta de la página, H1, rutas copiables) por idioma
PAGINAS = (("/player-log/", "Where is MTG Arena's Player.log, and why is it empty?", RUTAS),
           ("/es/player-log/", "¿Dónde está el Player.log de MTG Arena y por qué está vacío?", RUTAS_ES))
MEDIDAS = """() => { const caja = e => e.getBoundingClientRect(), ancho = document.documentElement.clientWidth;
  const rutas = [...document.querySelectorAll('.ruta-copiable')].map(e => ({ texto: e.textContent, derecha: caja(e).right, visible: e.checkVisibility() }));
  const faq = [...document.querySelectorAll('.preguntas details p')].map(e => e.checkVisibility());
  const h1 = document.querySelector('h1');
  return { desborde: document.documentElement.scrollWidth - ancho, rutas, faq, h1: h1.checkVisibility() && h1.textContent, ancho,
           seleccion: getComputedStyle(document.querySelector('.ruta-copiable')).userSelect }; }"""


def abrir(nav, url: str, ancho: int, errores: list):
    """Una página nueva a ``ancho`` px que anota en ``errores`` los fallos de consola y de página de la propia web (lo externo se bloquea)."""
    contexto = nav.new_context(viewport={"width": ancho, "height": 844}, is_mobile=ancho < 700, has_touch=ancho < 700)
    pagina = contexto.new_page()
    origen = url.split("/")[2]
    pagina.route("**/*", lambda r: r.continue_() if origen in r.request.url else r.abort())
    pagina.on("pageerror", lambda e: errores.append(f"pageerror: {e}"))
    pagina.on("console", lambda m: errores.append(f"{m.type}: {m.text}") if m.type == "error" and origen in (m.location.get("url") or origen) else None)
    pagina.on("requestfailed", lambda r: errores.append(f"requestfailed: {r.url}") if origen in r.url else None)
    pagina.goto(url, wait_until="load")
    pagina.evaluate("document.fonts.ready")
    return contexto, pagina


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class PlayerLogNavegador(unittest.TestCase):
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

    def test_sin_desborde_ni_errores_y_con_todo_a_la_vista(self):
        for ruta_pagina, h1, rutas in PAGINAS:
            for ancho in ANCHOS:
                errores: list = []
                contexto, pagina = abrir(self.nav, f"{self.web.url}{ruta_pagina}", ancho, errores)
                try:
                    m = pagina.evaluate(MEDIDAS)
                finally:
                    contexto.close()
                with self.subTest(pagina=ruta_pagina, ancho=ancho):
                    self.assertLessEqual(m["desborde"], 0, "hay desplazamiento horizontal")
                    self.assertEqual(errores, [])
                    self.assertEqual(m["h1"].strip(), h1)
                    self.assertEqual([r["texto"] for r in m["rutas"]], list(rutas))
                    for ruta in m["rutas"]:
                        self.assertTrue(ruta["visible"])
                        self.assertLessEqual(ruta["derecha"], m["ancho"], f"la ruta se sale de la pantalla: {ruta['texto']}")
                    self.assertEqual(m["faq"], [True, True], "las respuestas de la FAQ están a la vista")

    def test_un_clic_selecciona_la_ruta_entera(self):
        for ruta_pagina, _, rutas in PAGINAS:
            errores: list = []
            contexto, pagina = abrir(self.nav, f"{self.web.url}{ruta_pagina}", 1366, errores)
            try:
                for esperada in rutas:
                    pagina.evaluate("window.getSelection().removeAllRanges()")
                    pagina.locator(".ruta-copiable", has_text=esperada[:20]).first.click()
                    seleccion = pagina.evaluate("window.getSelection().toString()")
                    with self.subTest(pagina=ruta_pagina, ruta=esperada):
                        self.assertEqual(seleccion.strip(), esperada)
            finally:
                contexto.close()

    def test_la_medida_detecta_un_desborde(self):
        """Mutación permanente: una ruta sin salto de línea a 390 px desborda y la medida lo ve (si no, el test de arriba no mide nada)."""
        (self.raiz / "desborde.html").write_text("<!doctype html><meta charset=utf-8><body style='margin:0'><code class='ruta-copiable' style='white-space:nowrap'>"
                                                 + "x" * 200 + "</code><h1>Where is MTG Arena's Player.log, and why is it empty?</h1><div class=preguntas></div></body>",
                                                 encoding="utf-8")
        contexto, pagina = abrir(self.nav, f"{self.web.url}/desborde.html", 390, [])
        try:
            self.assertGreater(pagina.evaluate(MEDIDAS)["desborde"], 0)
        finally:
            contexto.close()


if __name__ == "__main__":
    unittest.main()
