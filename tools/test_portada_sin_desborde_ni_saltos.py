#!/usr/bin/env python3
"""ML-326: las cuatro portadas (es, en, pt, ja) en un navegador real (Chromium con Playwright; se salta si no están).

Protege dos fallos que ya existían: (1) la fila de escritorio de la cabecera no cabía entre 901 y 1079 px y desplazaba la página en horizontal
(en es, 32 px a 1040 px); (2) descarga.js pasaba la portada a «modo teléfono» después de pintarla y todo saltaba (CLS 0,346 en móvil).

- Sin desplazamiento horizontal a 360, 390, 768, 1040 y 1366 px, y en una barrido de 901 a 1100 px cada 10 px.
- CLS (``PerformanceObserver`` de layout-shift) en 390 px, con CPU x4 y red lenta, por debajo de 0,1.
- ML-326b: en todas las páginas con cabecera (portadas, Learn, coaches, Magic Online, overlay, novedades, registro detallado, seguridad, 404),
  de 340 a 1400 px cada 10 px: sin desplazamiento horizontal y ningún enlace ni botón visible de la cabecera ocupa más de una línea
  (si la fila de escritorio no cabe, la cabecera tiene que estar en el menú de teléfono).
- Con descarga.js bloqueado (así es el primer pintado) en teléfono: el aviso y el botón del héroe ya no se ven y el hueco de la caja guarda su alto.

Uso:  python3 -m pytest tools/test_portada_sin_desborde_ni_saltos.py
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from navegador_comun import esperar_pagina_estable
from test_huecos_mdn_navegador import Servidor, sitio

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

PORTADAS = ("index.html", "es/index.html", "pt/index.html", "ja/index.html")
ANCHOS = (360, 390, 768, 1040, 1366)
LIMITE_CLS = 0.1
ALTO_MINIMO_HUECO = 232   # alto de la caja de móvil más baja (767 px); a 480 px o menos se reservan 300
ANCHOS_BARRIDO = range(340, 1401, 10)
# Alto de lo que ocupa el texto visible de cada enlace de la cabecera: una línea de texto mide como mucho esto veces la altura de una caja de texto
MAX_LINEAS = 1.6
LINEAS_PARTIDAS = """() => { const partidos = [];
  document.querySelectorAll('.cab nav a, .cab > .envoltura > .boton, .cab .idioma, .cab .marca').forEach(function (a) {
    if (!a.checkVisibility({ contentVisibilityAuto: true, visibilityProperty: true })) return;
    const hojas = document.createTreeWalker(a, NodeFilter.SHOW_TEXT); let caja = 0, arriba = 1e9, abajo = -1e9, n;
    while ((n = hojas.nextNode())) { if (!n.textContent.trim()) continue; const r = document.createRange(); r.selectNodeContents(n);
      for (const q of r.getClientRects()) { if (q.width > 0) { caja = Math.max(caja, q.height); arriba = Math.min(arriba, q.top); abajo = Math.max(abajo, q.bottom); } } }
    if (caja > 0 && (abajo - arriba) > caja * %s) partidos.push(a.textContent.trim().slice(0, 24)); });
  return partidos; }""" % MAX_LINEAS
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

    def paginas_con_cabecera(self):
        return sorted(p.relative_to(self.raiz).as_posix() for p in self.raiz.rglob("*.html") if '<header class="cab">' in p.read_text(encoding="utf-8"))

    def test_cabecera_sin_desborde_ni_enlaces_partidos_en_todas_las_paginas(self):
        paginas = self.paginas_con_cabecera()
        self.assertGreaterEqual(len(paginas), 20, "faltan páginas con cabecera")
        for ruta in paginas:
            contexto, pagina = self.pagina(1000)
            pagina.goto(f"{self.web.url}/{ruta}", wait_until="load")
            for ancho in ANCHOS_BARRIDO:
                pagina.set_viewport_size({"width": ancho, "height": 844})
                self.assertLessEqual(pagina.evaluate("document.documentElement.scrollWidth"), ancho, f"{ruta} a {ancho} px se desplaza en horizontal")
                self.assertEqual(pagina.evaluate(LINEAS_PARTIDAS), [], f"{ruta} a {ancho} px: enlaces de la cabecera partidos en dos líneas")
            contexto.close()

    def caja_del_menu_abierto(self, ruta: str, ancho: int) -> dict:
        """Ancho de la caja del menú y de la ventana con el menú abierto, y si su borde derecho coincide con el de la cabecera."""
        contexto, pagina = self.pagina(ancho)
        pagina.goto(f"{self.web.url}/{ruta}", wait_until="load")
        pagina.click(".cab .menu > summary")
        medidas = pagina.evaluate("""() => { const c = document.querySelector('.cab .menu-caja').getBoundingClientRect();
          const e = document.querySelector('.cab .envoltura').getBoundingClientRect();
          return { caja: c.width, derecha: Math.abs(c.right - e.right) < 1, envoltura: e.width }; }""")
        contexto.close()
        return medidas

    def test_menu_compacto_no_se_estira_de_lado_a_lado_en_escritorio(self):
        """ML-329: con la cabecera compacta (data-compacta, ML-326b) la caja del menú es una tarjeta a la derecha; en teléfono sigue a todo el ancho."""
        for ruta in ("es/index.html", "pt/index.html", "ja/index.html", "index.html"):
            escritorio = self.caja_del_menu_abierto(ruta, 1000)
            with self.subTest(ruta):
                self.assertLessEqual(escritorio["caja"], 380, "la caja del menú se estira en escritorio")
                self.assertTrue(escritorio["derecha"], "la caja no queda pegada a la derecha")
                telefono = self.caja_del_menu_abierto(ruta, 390)
                self.assertAlmostEqual(telefono["caja"], telefono["envoltura"], delta=1, msg="en teléfono la caja debe ocupar todo el ancho")

    def test_cls_en_movil_con_red_lenta(self):
        for portada in PORTADAS:
            contexto, pagina = self.pagina(390, movil=True)
            cdp = contexto.new_cdp_session(pagina)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            cdp.send("Network.enable")
            cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150, "downloadThroughput": 1.6 * 1024 * 1024 / 8, "uploadThroughput": 750 * 1024 / 8})
            pagina.add_init_script(CLS_ENTRADA)
            pagina.goto(f"{self.web.url}/{portada}", wait_until="load")
            esperar_pagina_estable(pagina, timeout=120000)   # con la red y la CPU frenadas la carga tarda: se mide cuando ya terminó, no a un tiempo fijo
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
