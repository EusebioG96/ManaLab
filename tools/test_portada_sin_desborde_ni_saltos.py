#!/usr/bin/env python3
"""ML-326: las cuatro portadas (es, en, pt, ja) en un navegador real (Chromium con Playwright; se salta si no están).

Protege dos fallos que ya existían: (1) la fila de escritorio de la cabecera no cabía entre 901 y 1079 px y desplazaba la página en horizontal
(en es, 32 px a 1040 px); (2) descarga.js pasaba la portada a «modo teléfono» después de pintarla y todo saltaba (CLS 0,346 en móvil).

- Sin desplazamiento horizontal a 360, 390, 768, 1040 y 1366 px, y en una barrido de 901 a 1100 px cada 10 px.
- CLS (``PerformanceObserver`` de layout-shift) en 390 px, con CPU x4 y red lenta, por debajo de 0,1.
- Con descarga.js bloqueado (así es el primer pintado) en teléfono: el aviso y el botón del héroe ya no se ven y el hueco de la caja guarda su alto.

Uso:  python3 -m pytest tools/test_portada_sin_desborde_ni_saltos.py
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from test_huecos_mdn_navegador import Servidor, sitio  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

PORTADAS = ("index.html", "es/index.html", "pt/index.html", "ja/index.html")
ANCHOS = (360, 390, 768, 1040, 1366)
LIMITE_CLS = 0.1
ALTO_MINIMO_HUECO = 232   # alto de la caja de móvil más baja (767 px); a 480 px o menos se reservan 300
CLS_ENTRADA = """window.__cls = 0; try { new PerformanceObserver(function (l) { l.getEntries().forEach(function (e) {
  if (!e.hadRecentInput) window.__cls += e.value; }); }).observe({ type: "layout-shift", buffered: true }); } catch (e) {}"""


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class PortadaSinDesbordeNiSaltos(unittest.TestCase):
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

    def pagina(self, ancho: int, movil: bool = False, bloquear: str = ""):
        contexto = self.nav.new_context(viewport={"width": ancho, "height": 844}, device_scale_factor=2 if movil else 1, is_mobile=movil, has_touch=movil)
        pagina = contexto.new_page()

        def ruta(r):
            url = r.request.url
            if not url.startswith(self.web.url) or (bloquear and url.endswith(bloquear)):
                return r.abort()
            return r.continue_()
        pagina.route("**/*", ruta)
        return contexto, pagina

    def test_sin_desplazamiento_horizontal_en_todos_los_anchos(self):
        for portada in PORTADAS:
            for ancho in ANCHOS + tuple(range(901, 1101, 10)):
                contexto, pagina = self.pagina(ancho)
                pagina.goto(f"{self.web.url}/{portada}", wait_until="load")
                self.assertLessEqual(pagina.evaluate("document.documentElement.scrollWidth"), ancho, f"{portada} a {ancho} px se desplaza en horizontal")
                contexto.close()

    def test_cls_en_movil_con_red_lenta(self):
        for portada in PORTADAS:
            contexto, pagina = self.pagina(390, movil=True)
            cdp = contexto.new_cdp_session(pagina)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            cdp.send("Network.enable")
            cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150, "downloadThroughput": 1.6 * 1024 * 1024 / 8, "uploadThroughput": 750 * 1024 / 8})
            pagina.add_init_script(CLS_ENTRADA)
            pagina.goto(f"{self.web.url}/{portada}", wait_until="load")
            pagina.wait_for_timeout(2500)
            cls = pagina.evaluate("window.__cls")
            self.assertLess(cls, LIMITE_CLS, f"{portada}: CLS {cls:.3f} en 390 px")
            contexto.close()

    def test_primer_pintado_en_telefono_ya_reserva_el_espacio(self):
        """Estable aunque el CLS varíe: antes de que corra descarga.js, la portada ya está como quedará."""
        for portada in PORTADAS:
            for ancho, minimo in ((390, 300), (767, ALTO_MINIMO_HUECO)):
                contexto, pagina = self.pagina(ancho, movil=True, bloquear="/descarga.js")
                pagina.goto(f"{self.web.url}/{portada}", wait_until="load")
                estado = pagina.evaluate("""() => ({
                  aviso: getComputedStyle(document.querySelector('.aviso-version')).display,
                  boton: getComputedStyle(document.querySelector('.hero-cta .boton')).display,
                  hueco: document.querySelector("[data-movil-aqui]").getBoundingClientRect().height })""")
                self.assertEqual(estado["aviso"], "none", f"{portada} {ancho}: el aviso se ve antes de descarga.js")
                self.assertEqual(estado["boton"], "none", f"{portada} {ancho}: el botón del héroe se ve antes de descarga.js")
                self.assertGreaterEqual(estado["hueco"], minimo, f"{portada} {ancho}: el hueco de la caja no guarda su alto")
                contexto.close()

    def test_en_ordenador_no_cambia_nada_antes_de_descarga_js(self):
        contexto, pagina = self.pagina(1040, bloquear="/descarga.js")
        pagina.goto(f"{self.web.url}/es/index.html", wait_until="load")
        self.assertNotEqual(pagina.evaluate("getComputedStyle(document.querySelector('.aviso-version')).display"), "none")
        self.assertNotEqual(pagina.evaluate("getComputedStyle(document.querySelector('.hero-cta .boton')).display"), "none")
        contexto.close()


if __name__ == "__main__":
    unittest.main()
