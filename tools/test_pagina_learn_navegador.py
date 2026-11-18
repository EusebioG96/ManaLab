#!/usr/bin/env python3
"""ML-324 (WEB-08): la página «Learn» en un navegador real (Chromium con Playwright): anchos 360 a 1366 sin desplazamiento horizontal, ?p=N, filtros,
barra fina (aparece, desaparece y no se alcanza con el teclado), rotación, sin destacados, sin guías, servidor caído (queda la copia), texto de la red
escapado y HTML estático igual que el pintado por el script. Se salta si Playwright o Chromium no están.

Uso:  python3 -m pytest tools/test_pagina_learn_navegador.py
"""
import functools
import http.server
import json
import re
import shutil
import socketserver
import sys
import tempfile
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_web  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

SERVIDOR_IA = "https://registro-ia.eusebiog76.workers.dev/guias.json"
DEST = [{"nombre": "Dana Voss", "linea": "Standard · ES/EN", "enlace": "https://metafy.gg/@dana", "frase": "Te enseño Izzet.", "academia": "https://metafy.gg/@dana/academy"},
        {"nombre": "Iker Lasa", "linea": "Draft · ES", "enlace": "https://metafy.gg/@iker"}]
ANCHOS = (360, 390, 768, 1040, 1366)
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63fcffff3f0300060001a7d2e8f90000000049454e44ae426082")   # 1x1
FECHA = "2026-11-18T12:00:00.000Z"


def guia(i: int, **extra) -> dict:
    g = {"name": f"Guía {i}", "description": "d", "url": f"https://metafy.gg/guides/n{i}", "cover_url": "", "price": {"value_in_cents": 999, "currency": "USD"},
         "subscriber_only": False, "authors": [{"name": "Ana"}], "average_rating": 9.0, "review_count": 5, "total_reading_time_minutes": 7, "purchase_count": 100 - i}
    g.update(extra)
    return g


def lista(guias: list) -> str:
    return json.dumps({"v": 1, "actualizada": FECHA, "guias": guias})


def sitio(destacados: list, vacio: bool = False) -> Path:
    """Copia de la web (sin vídeo ni tools) reconstruida con esos destacados y, si `vacio`, sin guías."""
    base = Path(tempfile.mkdtemp(prefix="ml324-nav-"))
    raiz = base / "web"
    shutil.copytree(RAIZ, raiz, ignore=shutil.ignore_patterns(".git", "video", "guia", "tools", "docs", "__pycache__", ".pytest_cache"))
    contenido = json.loads((raiz / "contenido.json").read_text(encoding="utf-8"))
    contenido["destacados"] = destacados
    (raiz / "contenido.json").write_text(json.dumps(contenido), encoding="utf-8")
    if vacio:
        (raiz / "learn" / "guias.json").write_text(lista([]), encoding="utf-8")
    construir_web.construir(raiz, raiz)
    return raiz


class Servidor:
    def __init__(self, raiz: Path):
        manejador = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(raiz))
        manejador.log_message = lambda *a, **k: None

        class Hilos(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
        self.s = Hilos(("127.0.0.1", 0), manejador)
        self.url = f"http://127.0.0.1:{self.s.server_address[1]}"
        threading.Thread(target=self.s.serve_forever, daemon=True).start()

    def cerrar(self) -> None:
        self.s.shutdown()
        self.s.server_close()


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class Navegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.nav = cls.pw.chromium.launch()
        except Exception as error:  # noqa: BLE001  silencio: sin Chromium instalado la prueba se salta
            cls.pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {error}")
        cls.con = Servidor(sitio(DEST))
        cls.sin_dest = Servidor(sitio([]))
        cls.sin_guias = Servidor(sitio(DEST, vacio=True))

    @classmethod
    def tearDownClass(cls):
        for s in (cls.con, cls.sin_dest, cls.sin_guias):
            s.cerrar()
        cls.nav.close()
        cls.pw.stop()

    def abrir(self, servidor, ruta="es/aprender/", ancho=1366, servidor_ia=None, js=True, reducido=False, reloj=False):
        """Abre la página. `servidor_ia`: None = responde 503; texto = esa lista; 'copia' = lo que haría el real (la misma copia)."""
        ctx = self.nav.new_context(viewport={"width": ancho, "height": 800}, java_script_enabled=js, reduced_motion="reduce" if reducido else "no-preference")
        self.addCleanup(ctx.close)
        pagina = ctx.new_page()
        pagina.errores = []
        pagina.on("pageerror", lambda e: pagina.errores.append(str(e)))
        pagina.peticiones_ia = []

        def ruta_(r):
            url = r.request.url
            if url.startswith(servidor.url):
                return r.continue_()
            if url == SERVIDOR_IA:
                pagina.peticiones_ia.append(r.request.headers)
                if servidor_ia is None:
                    return r.fulfill(status=503, body="no")
                return r.fulfill(status=200, body=servidor_ia, content_type="application/json", headers={"access-control-allow-origin": "*"})
            if url.startswith("https://cdn.metafy.gg/"):
                return r.fulfill(body=PNG, content_type="image/png")
            return r.abort()   # nada de fuera: portadas y fotos rotas, que es lo que la página debe aguantar
        pagina.route("**/*", ruta_)
        if reloj:
            pagina.clock.install()
        pagina.goto(f"{servidor.url}/{ruta}", wait_until="load")
        if js:
            pagina.wait_for_function("document.documentElement.classList.contains('learn-js') || document.documentElement.classList.contains('learn-sin-lista') || !document.getElementById('ap-barra') || document.getElementById('ap-barra').hidden")
        return pagina

    def total_guias(self, p) -> int:
        return p.locator("#guias a.guia").count()

    def test_sin_desplazamiento_horizontal_en_todos_los_anchos(self):
        for ancho in ANCHOS:
            with self.subTest(ancho=ancho):
                p = self.abrir(self.con, ancho=ancho, servidor_ia=(RAIZ / "learn" / "guias.json").read_text(encoding="utf-8"))
                self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), ancho)
                self.assertEqual(p.errores, [])
                p.goto(f"{self.con.url}/es/aprender/?p=2", wait_until="load")
                p.wait_for_timeout(300)
                self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), ancho)

    def test_pagina_2_por_la_url_y_el_paginador_navega_sin_recargar(self):
        p = self.abrir(self.con, ruta="es/aprender/?p=2", servidor_ia=None)
        self.assertEqual(self.total_guias(p), 24)
        primera_p2 = p.locator("#guias a.guia").first.get_attribute("href")
        self.assertEqual(p.locator("#ap-pag [aria-current='page']").inner_text().strip(), "2")
        p.locator("#ap-pag a[data-p='1']").first.click()
        p.wait_for_timeout(300)
        self.assertNotEqual(p.locator("#guias a.guia").first.get_attribute("href"), primera_p2)
        self.assertNotIn("p=", p.url)
        p.go_back()
        p.wait_for_timeout(300)
        self.assertEqual(p.locator("#guias a.guia").first.get_attribute("href"), primera_p2)

    def test_filtros_tipo_busqueda_creador_y_contador(self):
        servidor_ia = lista([guia(1, price=None, subscriber_only=False, authors=[{"name": "Ana"}]), guia(2, price=None, subscriber_only=True, authors=[{"name": "Bea"}]),
                             guia(3), guia(4, name="Zorro especial", authors=[{"name": "Bea"}])])
        p = self.abrir(self.con, servidor_ia=servidor_ia)
        self.assertEqual(self.total_guias(p), 4)
        self.assertIn("4", p.locator("#ap-cuenta").inner_text())
        p.click("button[data-tipo='gratis']")
        self.assertEqual([x.split("/")[-1] for x in p.locator("#guias a.guia").evaluate_all("els=>els.map(e=>e.href)")], ["n1"])
        self.assertEqual(p.locator("button[data-tipo='gratis']").get_attribute("aria-pressed"), "true")
        p.click("button[data-tipo='suscriptores']")
        self.assertEqual(self.total_guias(p), 1)
        p.click("button[data-tipo='pago']")
        self.assertEqual(self.total_guias(p), 2)
        p.click("button[data-tipo='todas']")
        p.select_option("#ap-creador", "Bea")
        self.assertEqual(self.total_guias(p), 2)
        p.fill("#ap-buscar", "zorro")   # sin acentos ni mayúsculas
        self.assertEqual(self.total_guias(p), 1)
        p.fill("#ap-buscar", "nada que coincida")
        self.assertEqual(self.total_guias(p), 0)
        self.assertGreater(p.locator("#guias button[data-ap='limpiar']").count(), 0)
        p.click("#guias button[data-ap='limpiar']")
        self.assertEqual(self.total_guias(p), 4)

    def test_barra_fina_aparece_desaparece_y_oculta_no_se_alcanza_con_el_teclado(self):
        p = self.abrir(self.con, servidor_ia=(RAIZ / "learn" / "guias.json").read_text(encoding="utf-8"))
        barra = p.locator("#d2barra")
        self.assertEqual(barra.get_attribute("inert"), "")
        self.assertEqual(barra.get_attribute("aria-hidden"), "true")
        self.assertFalse(p.evaluate("document.getElementById('d2barra').classList.contains('visible')"))
        for _ in range(40):   # con la barra oculta, Tab nunca cae dentro
            p.keyboard.press("Tab")
            self.assertFalse(p.evaluate("!!document.activeElement.closest('#d2barra')"))
        p.evaluate("document.querySelector('#d2barra .d2cta').focus()")
        self.assertFalse(p.evaluate("!!document.activeElement.closest('#d2barra')"), "un elemento inerte no recibe el foco")
        p.evaluate("window.scrollTo(0, 2400)")
        p.wait_for_function("document.getElementById('d2barra').classList.contains('visible')")
        self.assertIsNone(barra.get_attribute("inert"))
        self.assertIsNone(barra.get_attribute("aria-hidden"))
        self.assertTrue(barra.locator(".d2cta").is_visible())
        self.assertIn("sponsored", barra.locator(".d2cta").get_attribute("rel"))
        self.assertEqual(barra.locator(".n").inner_text().strip(), "Dana Voss")
        p.evaluate("window.scrollTo(0, 0)")
        p.wait_for_function("!document.getElementById('d2barra').classList.contains('visible')")
        self.assertEqual(barra.get_attribute("inert"), "")
        self.assertEqual(barra.get_attribute("aria-hidden"), "true")
        p.evaluate("document.querySelector('#d2barra .d2cta').focus()")
        self.assertFalse(p.evaluate("!!document.activeElement.closest('#d2barra')"))

    def test_el_contenido_que_no_se_ve_del_banner_tampoco_recibe_foco(self):
        p = self.abrir(self.con, servidor_ia=None)
        inertes = p.locator("#destacado .d2c:not(.on)")
        self.assertEqual(inertes.count(), 1)
        self.assertEqual(inertes.first.get_attribute("inert"), "")
        self.assertEqual(inertes.first.get_attribute("aria-hidden"), "true")

    def test_rotacion_cada_8_segundos_con_el_reloj_simulado(self):
        p = self.abrir(self.con, servidor_ia=None, reloj=True)
        self.assertEqual(p.locator("#destacado .d2c.on .d2nom").inner_text().strip(), "Dana Voss")
        p.clock.run_for(8500)
        self.assertEqual(p.locator("#destacado .d2c.on .d2nom").inner_text().strip(), "Iker Lasa")
        self.assertEqual(p.locator("#destacado .d2c:not(.on)").first.get_attribute("inert"), "")
        p.clock.run_for(8500)
        self.assertEqual(p.locator("#destacado .d2c.on .d2nom").inner_text().strip(), "Dana Voss")

    def test_con_movimiento_reducido_no_rota_sola(self):
        p = self.abrir(self.con, servidor_ia=None, reloj=True, reducido=True)
        p.clock.run_for(20000)
        self.assertEqual(p.locator("#destacado .d2c.on .d2nom").inner_text().strip(), "Dana Voss")

    def test_pasar_el_raton_pausa_y_las_flechas_cambian_de_creador(self):
        p = self.abrir(self.con, servidor_ia=None, reloj=True)
        p.hover("#destacado")
        p.clock.run_for(20000)
        self.assertEqual(p.locator("#destacado .d2c.on .d2nom").inner_text().strip(), "Dana Voss")
        p.click("#destacado button[data-d2='1']")
        self.assertEqual(p.locator("#destacado .d2c.on .d2nom").inner_text().strip(), "Iker Lasa")

    def test_sin_destacados_no_hay_banner_ni_barra_y_la_pagina_funciona(self):
        p = self.abrir(self.sin_dest, servidor_ia=None)
        self.assertEqual(p.locator("#destacado, #d2barra").count(), 0)
        self.assertEqual(self.total_guias(p), 24)
        self.assertEqual(p.errores, [])

    def test_sin_guias_sale_el_estado_vacio_y_la_descarga(self):
        p = self.abrir(self.sin_guias, servidor_ia=lista([]))
        self.assertEqual(self.total_guias(p), 0)
        self.assertTrue(p.locator("#guias .ap-caja").is_visible())
        self.assertTrue(p.locator("#guias .ap-caja a[href='#descargar']").is_visible())
        self.assertTrue(p.locator("#ap-barra").is_hidden())
        self.assertEqual(p.locator("#ap-pag").count(), 0)
        self.assertTrue(p.locator("#descargar").count() == 1)

    def test_si_el_servidor_falla_queda_la_copia_y_los_filtros_funcionan(self):
        p = self.abrir(self.con, servidor_ia=None)
        self.assertGreaterEqual(len(p.peticiones_ia), 1)
        self.assertNotIn("cookie", {k.lower() for k in p.peticiones_ia[0]})
        self.assertEqual(self.total_guias(p), 24)
        self.assertTrue(p.evaluate("document.documentElement.classList.contains('learn-js')"), "con la copia, el script se activa")
        total_copia = len(json.loads((RAIZ / "learn" / "guias.json").read_text(encoding="utf-8"))["guias"])
        self.assertIn(str(total_copia), p.locator("#ap-cuenta").inner_text())
        p.fill("#ap-buscar", "zzzz-no-existe")
        self.assertEqual(self.total_guias(p), 0)

    def test_si_el_servidor_manda_una_lista_mala_se_usa_la_copia(self):
        for mala in ("no es json", json.dumps({"v": 2, "actualizada": FECHA, "guias": [guia(1)]}), lista([guia(1, url="https://evil.com/x")])):
            with self.subTest(mala=mala[:30]):
                p = self.abrir(self.con, servidor_ia=mala)
                self.assertEqual(self.total_guias(p), 24)
                self.assertNotIn("evil.com", p.content())

    def test_si_el_servidor_responde_con_su_lista_se_pinta_esa(self):
        p = self.abrir(self.con, servidor_ia=lista([guia(1), guia(2, url="https://evil.com/x"), guia(3)]))
        self.assertEqual(self.total_guias(p), 2)
        self.assertNotIn("evil.com", p.content())

    def test_el_texto_hostil_de_la_red_se_escapa(self):
        hostil = guia(1, name="<img src=x onerror=window.__roto=1>", authors=[{"name": "<b onmouseover=window.__roto=2>x</b>"}], description="<script>window.__roto=3</script>")
        p = self.abrir(self.con, servidor_ia=lista([hostil]))
        p.wait_for_timeout(300)
        self.assertEqual(self.total_guias(p), 1)
        self.assertIsNone(p.evaluate("window.__roto"))
        self.assertEqual(p.locator("#guias img[src='x']").count(), 0)
        self.assertIn("<img src=x onerror=window.__roto=1>", p.locator("#guias a.guia").first.inner_text())
        self.assertIn("<b onmouseover", p.locator("#ap-creador").inner_html().replace("&lt;", "<"))
        self.assertEqual(p.locator("#guias img[loading='lazy']").count(), p.locator("#guias img").count())

    def test_portadas_perezosas_y_sin_referrer(self):
        p = self.abrir(self.con, servidor_ia=lista([guia(i, cover_url=f"https://cdn.metafy.gg/c{i}.png") for i in range(1, 4)]))
        p.wait_for_timeout(300)
        self.assertEqual(p.locator("#guias img").count(), 3)
        self.assertEqual(p.evaluate("[...document.querySelectorAll('#guias img')].map(i=>i.getAttribute('loading')+'/'+i.getAttribute('referrerpolicy'))"),
                         ["lazy/no-referrer"] * 3)

    def test_el_html_estatico_es_igual_que_el_que_pinta_el_script(self):
        sin_js = self.abrir(self.con, js=False)
        con_js = self.abrir(self.con, servidor_ia=None)
        sin_imagenes = lambda html: re.sub(r"<img\b[^>]*>", "", html)   # las portadas de fuera no cargan aquí y el script quita las rotas
        self.assertEqual(sin_imagenes(sin_js.locator("#guias").inner_html()), sin_imagenes(con_js.locator("#guias").inner_html()))
        self.assertEqual(sin_js.locator("#ap-pag").evaluate("e=>e.outerHTML"), con_js.locator("#ap-pag").evaluate("e=>e.outerHTML"))

    def test_las_cuatro_paginas_cargan_sin_errores(self):
        for ruta in ("learn/", "es/aprender/", "pt/aprender/", "ja/learn/"):
            with self.subTest(ruta=ruta):
                p = self.abrir(self.con, ruta=ruta, servidor_ia=None, ancho=390)
                self.assertEqual(self.total_guias(p), 24)
                self.assertEqual(p.errores, [])
                self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), 390)


if __name__ == "__main__":
    unittest.main()
