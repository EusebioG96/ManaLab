#!/usr/bin/env python3
"""ML-412: arreglos del QA de la web (ML-409) en un navegador real (Chromium con Playwright; se salta si no están). Nada sale a la red.

Protege: (M1) ningún chip de ruta (``.ruta``) desborda la página a 320 px y en escritorio conserva su aspecto (no se parte);
(M4) con las tipografías retrasadas, las páginas de coaches de en, es y pt no saltan (CLS <= 0,05) a 390 y 1366 px;
el menú móvil se cierra con Esc (el foco vuelve al botón) y al pulsar fuera, pero no al pulsar dentro;
«Saltar al contenido» es lo primero que recibe el foco con Tab, se ve, y lleva al contenido.

Uso:  python3 -m pytest tools/test_qa_web_navegador.py
"""
import functools
import http.server
import re
import shutil
import socketserver
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_web  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

RETRASO_FUENTES = 0.6   # segundos que tarda el servidor en dar cada tipografía: la web se pinta antes con la de reserva
LIMITE_CLS = 0.05       # lo que pide ML-412 (el umbral «bueno» de Google es 0,1)
COACHES = ("/coaches/", "/es/coaches/", "/pt/coaches/")
PORTADAS = ("/", "/es/", "/pt/", "/ja/")
ESPERA_MS = 30000
MIDE_CLS = """window.__cls = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
  .observe({type: 'layout-shift', buffered: true});"""
ESTABLE = "() => document.fonts.status === 'loaded' && [...document.images].every(i => i.complete || i.loading === 'lazy')"


def sitio() -> Path:
    """Copia de la web reconstruida desde las plantillas (sin archivos de vídeo, PDF ni herramientas)."""
    raiz = Path(tempfile.mkdtemp(prefix="ml412-nav-")) / "web"
    shutil.copytree(RAIZ, raiz, ignore=shutil.ignore_patterns(".git", "tools", "docs", "*.pdf", "*.zip", "*.mp4", "*.webm", "__pycache__", ".pytest_cache"))
    construir_web.construir(raiz, raiz)
    return raiz


class Servidor:
    """Servidor local que puede tardar en dar las tipografías (``retraso`` segundos) para imitar una red lenta."""

    def __init__(self, raiz: Path, retraso: float = 0.0):
        class Manejador(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args, **kwargs):  # silencio: el servidor de pruebas no escribe nada
                pass

            def do_GET(self):
                if "/fuentes/" in self.path:
                    time.sleep(retraso)
                super().do_GET()

        class Hilos(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
        self.s = Hilos(("127.0.0.1", 0), functools.partial(Manejador, directory=str(raiz)))
        self.url = f"http://127.0.0.1:{self.s.server_address[1]}"
        threading.Thread(target=self.s.serve_forever, daemon=True).start()

    def cerrar(self) -> None:
        self.s.shutdown()
        self.s.server_close()


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class QaWebNavegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raiz = sitio()
        cls.rapido = Servidor(cls.raiz)
        cls.lento = Servidor(cls.raiz, RETRASO_FUENTES)
        cls.pw = sync_playwright().start()
        try:
            cls.nav = cls.pw.chromium.launch()
        except Exception as error:  # Chromium no instalado: se salta
            cls.pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {error}")

    @classmethod
    def tearDownClass(cls):
        cls.nav.close()
        cls.pw.stop()
        cls.rapido.cerrar()
        cls.lento.cerrar()
        shutil.rmtree(cls.raiz.parent, ignore_errors=True)

    def pagina(self, servidor: Servidor, ruta: str, ancho: int, tactil: bool = False):
        contexto = self.nav.new_context(viewport={"width": ancho, "height": 800}, is_mobile=tactil, has_touch=tactil)
        contexto.route("**/*", lambda r: r.continue_() if r.request.url.startswith(servidor.url) else r.abort())   # nada sale a la red
        contexto.add_init_script(MIDE_CLS)
        pagina = contexto.new_page()
        pagina.goto(servidor.url + ruta, wait_until="load")
        pagina.wait_for_function(ESTABLE, timeout=ESPERA_MS)
        return contexto, pagina

    # M1
    def test_ningun_chip_de_ruta_desborda_a_320_y_en_escritorio_no_se_parte(self):
        paginas = sorted(f"/{p.parent.relative_to(self.raiz).as_posix()}/".replace("/./", "/")
                         for p in self.raiz.rglob("index.html") if 'class="ruta"' in p.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(paginas), 5)
        for ruta in paginas + ["/ja/"]:
            for ancho in (320, 390):
                contexto, pagina = self.pagina(self.rapido, ruta, ancho)
                medidas = pagina.evaluate("""() => ({desborde: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    chips: [...document.querySelectorAll('.ruta')].map(e => e.getBoundingClientRect().right - document.documentElement.clientWidth)})""")
                contexto.close()
                self.assertLessEqual(medidas["desborde"], 0, f"{ruta} a {ancho}px desplaza la página en horizontal")
                self.assertTrue(all(derecha <= 0 for derecha in medidas["chips"]), f"{ruta} a {ancho}px: un chip sale de la pantalla")
        contexto, pagina = self.pagina(self.rapido, "/es/", 1366)
        alto = pagina.evaluate("[...document.querySelectorAll('.ruta')].map(e => e.getBoundingClientRect().height)")
        contexto.close()
        self.assertTrue(alto and all(a < 30 for a in alto), "en escritorio el chip debe seguir en una sola línea")

    # M4
    def test_coaches_no_salta_con_las_tipografias_retrasadas(self):
        for ruta in COACHES:
            for ancho in (390, 1366):
                contexto, pagina = self.pagina(self.lento, ruta, ancho)
                pagina.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
                cls = pagina.evaluate("window.__cls")
                contexto.close()
                self.assertLessEqual(cls, LIMITE_CLS, f"{ruta} a {ancho}px: CLS {cls:.3f}")

    # B7
    def test_menu_movil_se_cierra_con_esc_devolviendo_el_foco_y_al_pulsar_fuera(self):
        for ruta in ("/", "/es/", "/pt/", "/ja/", "/learn/"):
            contexto, pagina = self.pagina(self.rapido, ruta, 390, tactil=True)
            pagina.click("details.menu > summary")
            self.assertTrue(pagina.evaluate("document.querySelector('details.menu').open"), ruta)
            pagina.click(".menu-caja", position={"x": 3, "y": 3})   # dentro (en el margen, no en un enlace): sigue abierto
            self.assertTrue(pagina.evaluate("document.querySelector('details.menu').open"), f"{ruta}: se cerró al pulsar dentro")
            pagina.keyboard.press("Escape")
            self.assertFalse(pagina.evaluate("document.querySelector('details.menu').open"), f"{ruta}: Esc no cierra el menú")
            self.assertTrue(pagina.evaluate("document.activeElement === document.querySelector('details.menu > summary')"),
                            f"{ruta}: el foco no vuelve al botón")
            pagina.click("details.menu > summary")
            pagina.mouse.click(10, 790)   # fuera del menú (la caja del menú ocupa la parte de arriba)
            self.assertFalse(pagina.evaluate("document.querySelector('details.menu').open"), f"{ruta}: pulsar fuera no cierra el menú")
            contexto.close()

    # B5
    def test_saltar_al_contenido_es_lo_primero_con_tab_se_ve_y_lleva_al_contenido(self):
        for ruta in PORTADAS + ("/coaches/", "/novedades/", "/privacy/", "/guia/guia_manalab_en.html"):
            contexto, pagina = self.pagina(self.rapido, ruta, 1366)
            enlace = pagina.locator("a.saltar")
            self.assertEqual(1, enlace.count(), ruta)
            self.assertLess(pagina.evaluate("document.querySelector('a.saltar').getBoundingClientRect().bottom"), 0, f"{ruta}: debe estar oculto sin foco")
            pagina.keyboard.press("Tab")
            self.assertTrue(pagina.evaluate("document.activeElement.classList.contains('saltar')"), f"{ruta}: Tab no llega primero al enlace")
            visible = pagina.evaluate("(() => { const r = document.activeElement.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight && r.width > 40; })()")
            self.assertTrue(visible, f"{ruta}: con el foco el enlace debe verse")
            pagina.keyboard.press("Enter")
            destino = pagina.evaluate("location.hash.slice(1)")
            self.assertTrue(re.fullmatch(r"inicio|contenido", destino), f"{ruta}: {destino}")
            self.assertEqual("MAIN", pagina.evaluate("document.getElementById(location.hash.slice(1)).tagName"))
            contexto.close()


if __name__ == "__main__":
    unittest.main()
