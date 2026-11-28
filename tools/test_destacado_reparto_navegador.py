#!/usr/bin/env python3
"""ML-351: el destacado con el que empieza cada visita de «Learn» es uno al azar, igual de probable cada uno (learn.js, indiceInicial), en Chromium
con Playwright. Con Math.random controlado el inicial puede ser cualquiera; con muchas cargas cada uno sale ~50 %; con un solo destacado no cambia
nada; la rotación, la flecha y la barra fina siguen igual y la barra fina enseña el destacado que se ve, no siempre el primero. Se salta si
Playwright o Chromium no están.

Uso:  python3 -m pytest tools/test_destacado_reparto_navegador.py
"""
import json
import random
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from navegador_comun import esperar_pagina_estable
from test_pagina_learn_navegador import PNG, SERVIDOR_IA, Servidor, sitio

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

REALES = json.loads((RAIZ / "contenido.json").read_text(encoding="utf-8"))["destacados"]   # Palhares, TCG Academy y Yuya (ML-354)
DOS = REALES[:2]   # Palhares y TCG Academy: los casos de reparto con dos
ACTIVO = "#destacado .d2c.on"
CARGAS = 100   # cargas de la prueba estadística: con 2 destacados, 50 ± 15 es un margen de más de 3 sigmas; con 3, 33 ± 13 (~2,8 sigmas, sembrado)


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class RepartoDelDestacadoInicial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.nav = cls.pw.chromium.launch()
        except Exception as error:  # noqa: BLE001  silencio: sin Chromium instalado la prueba se salta
            cls.pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {error}")
        cls.dos = Servidor(sitio(DOS))
        cls.tres = Servidor(sitio(REALES))
        cls.uno = Servidor(sitio(REALES[:1]))

    @classmethod
    def tearDownClass(cls):
        for s in (cls.dos, cls.tres, cls.uno):
            s.cerrar()
        cls.nav.close()
        cls.pw.stop()

    def abrir(self, servidor, azar, ruta="learn/", ancho=1366, alto=800, reloj=False):
        """Abre la página con Math.random fijo en `azar` (un número en [0, 1)). Devuelve la página con `errores`."""
        ctx = self.nav.new_context(viewport={"width": ancho, "height": alto})
        self.addCleanup(ctx.close)
        p = ctx.new_page()
        p.errores = []
        p.on("pageerror", lambda e: p.errores.append(str(e)))
        p.add_init_script(f"Math.random=()=>{azar}")

        def ruta_(r):
            if r.request.url.startswith(servidor.url):
                return r.continue_()
            if r.request.url == SERVIDOR_IA:
                return r.fulfill(status=503, body="no")
            if r.request.url.startswith("https://cdn.metafy.gg/"):
                return r.fulfill(body=PNG, content_type="image/png")
            return r.abort()
        p.route("**/*", ruta_)
        if reloj:
            p.clock.install()
        p.goto(f"{servidor.url}/{ruta}", wait_until="load")
        p.wait_for_function("document.documentElement.classList.contains('learn-js') || document.documentElement.classList.contains('learn-sin-lista')")
        esperar_pagina_estable(p)
        return p

    def activo(self, p, tras_cambio: bool = False) -> str:
        """El id del destacado que se ve (el único .on). Falla si hay más de uno visible de verdad. `tras_cambio`: espera a que acabe el
        fundido de 0,4 s de la rotación o la flecha; al cargar no hay fundido (el inicial se pone sin él) y no se espera: eso también se prueba."""
        if tras_cambio:   # el .on ya está del todo opaco (al empezar el fundido su opacidad es 0) y no queda ninguna transición del destacado en marcha
            p.wait_for_function("""() => { const on = document.querySelector('#destacado .d2c.on');
                return !!on && getComputedStyle(on).opacity === '1'
                  && !document.getAnimations().some((a) => a.playState === 'running' && a.effect && a.effect.target && a.effect.target.closest && a.effect.target.closest('#destacado')); }""")
        visibles = p.evaluate("""() => Array.from(document.querySelectorAll('#destacado .d2c')).filter(c => {
            const e = getComputedStyle(c); return e.visibility === 'visible' && parseFloat(e.opacity) > 0.5; }).map(c => c.getAttribute('data-id'))""")
        self.assertEqual(len(visibles), 1, f"se ve más de un destacado a la vez: {visibles}")
        self.assertEqual(p.locator(ACTIVO).get_attribute("data-id"), visibles[0])
        return visibles[0]

    def test_el_dado_decide_cual_sale_primero_con_dos(self):
        for azar, esperado in ((0.0, "pcpalhares"), (0.49, "pcpalhares"), (0.5, "tcgacademy"), (0.999, "tcgacademy")):
            with self.subTest(azar=azar):
                p = self.abrir(self.dos, azar)
                self.assertEqual(self.activo(p), esperado)
                self.assertEqual(p.errores, [])

    def test_con_los_tres_reales_cada_tercio_del_dado_es_un_destacado_distinto(self):
        for azar, esperado in ((0.1, "pcpalhares"), (0.4, "tcgacademy"), (0.7, "yuyan"), (0.999, "yuyan")):
            with self.subTest(azar=azar):
                self.assertEqual(self.activo(self.abrir(self.tres, azar)), esperado)

    def test_con_muchas_cargas_cada_uno_sale_la_mitad_de_las_veces(self):
        dado = random.Random(351)   # sembrado: la prueba es repetible
        salidas = {"pcpalhares": 0, "tcgacademy": 0}
        for _ in range(CARGAS):
            p = self.abrir(self.dos, dado.random())
            salidas[self.activo(p)] += 1
            p.context.close()
        self.assertEqual(sum(salidas.values()), CARGAS)
        for creador, veces in salidas.items():
            self.assertTrue(35 <= veces <= 65, f"{creador} salió {veces} de {CARGAS} veces: el reparto no es 50/50 ({salidas})")

    def test_con_los_tres_reales_cada_uno_sale_un_tercio_de_las_veces(self):
        dado = random.Random(354)   # sembrado: la prueba es repetible
        salidas = {"pcpalhares": 0, "tcgacademy": 0, "yuyan": 0}
        for _ in range(CARGAS):
            p = self.abrir(self.tres, dado.random())
            salidas[self.activo(p)] += 1
            p.context.close()
        self.assertEqual(sum(salidas.values()), CARGAS)
        for creador, veces in salidas.items():
            self.assertTrue(20 <= veces <= 47, f"{creador} salió {veces} de {CARGAS} veces: el reparto no es 1/3 ({salidas})")

    def test_con_un_solo_destacado_nada_cambia_sea_cual_sea_el_dado(self):
        for azar in (0.0, 0.5, 0.999):
            p = self.abrir(self.uno, azar)
            self.assertEqual(self.activo(p), "pcpalhares")
            self.assertEqual(p.locator("#destacado .d2pag, #destacado .d2prog").count(), 0)
            self.assertEqual(p.errores, [])

    def test_sin_javascript_el_html_estatico_muestra_el_primero(self):
        ctx = self.nav.new_context(java_script_enabled=False)
        self.addCleanup(ctx.close)
        p = ctx.new_page()
        p.route("**/*", lambda r: r.continue_() if r.request.url.startswith(self.dos.url) else r.abort())
        p.goto(f"{self.dos.url}/learn/", wait_until="load")
        self.assertEqual(p.locator(ACTIVO).get_attribute("data-id"), "pcpalhares")

    def test_el_punto_el_contador_y_las_flechas_siguen_al_destacado_inicial(self):
        p = self.abrir(self.dos, 0.9)
        self.assertEqual(self.activo(p), "tcgacademy")
        self.assertEqual(p.locator("#destacado .d2pun").get_attribute("aria-label"), "2 / 2")
        self.assertEqual(p.locator("#destacado .d2pun i.on").count(), 1)
        self.assertEqual(p.evaluate("Array.from(document.querySelectorAll('#destacado .d2pun i')).findIndex(i => i.classList.contains('on'))"), 1)
        self.assertEqual(p.locator("#destacado .d2c:not(.on)").get_attribute("inert"), "")
        p.click("#destacado button[data-d2='1']")   # tras el último vuelve al primero
        self.assertEqual(self.activo(p, tras_cambio=True), "pcpalhares")
        self.assertEqual(p.locator("#destacado .d2pun").get_attribute("aria-label"), "1 / 2")

    def test_la_rotacion_sigue_cada_8_segundos_desde_el_inicial(self):
        p = self.abrir(self.dos, 0.9, reloj=True)
        self.assertEqual(self.activo(p), "tcgacademy")
        p.clock.run_for(8500)
        self.assertEqual(self.activo(p, tras_cambio=True), "pcpalhares")
        p.clock.run_for(8500)
        self.assertEqual(self.activo(p, tras_cambio=True), "tcgacademy")

    def test_la_barra_fina_enseña_el_destacado_que_se_ve(self):
        esperado = {0.0: ("Professor P. C. Palhares", "https://metafy.gg/@pcpalhares?utm_source=Manalab"), 0.9: ("TCG Academy", "https://metafy.gg/@luissalvatto?utm_source=Manalab")}
        for azar, (nombre, enlace) in esperado.items():
            with self.subTest(azar=azar):
                p = self.abrir(self.dos, azar)
                p.evaluate("window.scrollTo(0, 2400)")
                p.wait_for_function("document.getElementById('d2barra').classList.contains('visible')")
                barra = p.locator("#d2barra")
                self.assertEqual(barra.locator(".n").inner_text().strip(), nombre)
                self.assertEqual(barra.locator(".d2cta").get_attribute("href"), enlace)
                self.assertTrue(barra.locator(".d2cta").is_visible())

    def test_las_cuatro_paginas_empiezan_por_el_dado(self):
        for ruta in ("learn/", "es/aprender/", "pt/aprender/", "ja/learn/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.activo(self.abrir(self.dos, 0.9, ruta=ruta)), "tcgacademy")
                self.assertEqual(self.activo(self.abrir(self.dos, 0.1, ruta=ruta)), "pcpalhares")

    def test_los_botones_y_la_frase_caben_con_cada_destacado_en_tres_tamaños(self):
        for ancho, alto in ((1366, 768), (1040, 680), (390, 844)):
            for azar in (0.1, 0.9):
                with self.subTest(ancho=ancho, azar=azar):
                    p = self.abrir(self.dos, azar, ancho=ancho, alto=alto)
                    self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), ancho)
                    caja = p.evaluate("""() => { const c = document.querySelector('#destacado .d2c.on'), r = c.getBoundingClientRect();
                        const dentro = Array.from(c.querySelectorAll('.d2fra, .d2cta, .d2cas, .d2nom')).map(e => e.getBoundingClientRect())
                            .filter(b => b.width > 0).every(b => b.left >= r.left - 1 && b.right <= r.right + 1);
                        return { dentro: dentro, botones: c.querySelectorAll('.d2cta, .d2cas').length }; }""")
                    self.assertTrue(caja["dentro"], "algo se sale de la tarjeta")
                    self.assertTrue(p.locator(f"{ACTIVO} .d2cta").is_visible())


if __name__ == "__main__":
    unittest.main()
