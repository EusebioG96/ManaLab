#!/usr/bin/env python3
"""ML-325 (WEB-09): los huecos de anuncio de MDN en un navegador real (Chromium con Playwright). Se salta si Playwright o Chromium no están.

Nada sale a la red: la web se sirve desde una copia reconstruida y MDN se simula con una ruta de Playwright (``mdn.metafy.gg/embed.js``): un script
falso que hace lo que el real (elige formato por el ancho de la caja, reserva ``min-height``, marca ``data-mdn-state`` y pinta su anuncio en un
shadow root). El script real se probó a mano con las mismas medidas (ver el informe de ML-325).

Qué se comprueba, a 360, 390, 768, 1040 y 1366 px en todas las páginas con anuncio: el alto reservado antes de que MDN responda (728x90 o 300x250 y la
etiqueta), que no haya desplazamiento horizontal, la regla de colocación de WEB-09, que al llegar el anuncio no salte nada, que si MDN no tiene
anuncio, no llega o no hay JavaScript se vea el anuncio de casa con el mismo alto y un enlace a Learn en el idioma de la página, que con «reducir
movimiento» el hueco no se anime y, en Learn, que el hueco de la rejilla siga tras la octava guía al paginar y al filtrar.

Uso:  python3 -m pytest tools/test_huecos_mdn_navegador.py
"""
import functools
import http.server
import json
import shutil
import socketserver
import sys
import tempfile
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_mdn
import construir_web
from navegador_comun import esperar_pagina_estable
from test_huecos_mdn import CON_ANUNCIO, ETIQUETA, RUTA_LEARN, idioma_de

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

ANCHOS = (360, 390, 768, 1040, 1366)
SERVIDOR_IA = "https://registro-ia.eusebiog76.workers.dev/guias.json"
LIMITE_PRIMERA_SECCION = 560   # WEB-09: el primer hueco va tras la primera sección que termina a 560 px o más
CABECERA_ETIQUETA = 11         # alto de la línea de la etiqueta (11 px con line-height 1)
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63fcffff3f0300060001a7d2e8f90000000049454e44ae426082")

# El MDN de mentira. `modo`: render (pinta su anuncio tras `retraso` ms), empty (sin anuncio), colgado (se queda en loading), espera (se queda en waiting).
MDN_FALSO = """(function () {
  var MODO = %(modo)s, RETRASO = %(retraso)d;
  function formato(slot) { var w = slot.getBoundingClientRect().width; return w >= 728 ? "leaderboard" : w >= 300 ? "rectangle" : null; }
  function cargar(slot) {
    if (slot.dataset.mdnState) return;
    slot.dataset.mdnState = "waiting";
    var f = formato(slot);
    if (f === "leaderboard") slot.style.minHeight = "90px"; else if (f === "rectangle") slot.style.minHeight = "250px";
    if (MODO === "espera") return;
    slot.dataset.mdnState = "loading";
    if (MODO === "colgado") return;
    setTimeout(function () {
      if (MODO === "empty") { slot.dataset.mdnState = "empty"; return; }
      var ancho = f === "leaderboard" ? 728 : 300, alto = f === "leaderboard" ? 90 : 250;
      slot.attachShadow({ mode: "open" }).innerHTML = '<a style="display:block;width:' + ancho + 'px;height:' + alto + 'px;background:#35506b;color:#fff" href="https://example.com/">Sponsored</a>';
      slot.dataset.mdnState = "rendered";
    }, RETRASO);
  }
  function todos(raiz) { if (raiz.matches && raiz.matches("[data-mdn]")) cargar(raiz); raiz.querySelectorAll("[data-mdn]").forEach(cargar); }
  todos(document);
  new MutationObserver(function (ms) { ms.forEach(function (m) { m.addedNodes.forEach(function (n) { if (n.nodeType === 1) todos(n); }); }); })
    .observe(document.documentElement, { childList: true, subtree: true });
})();
"""

CLS_ENTRADA = """window.__cls = 0; try { new PerformanceObserver(function (l) { l.getEntries().forEach(function (e) { if (!e.hadRecentInput) window.__cls += e.value; }); })
  .observe({ type: "layout-shift", buffered: true }); } catch (e) {}"""

MEDIR = """() => {
  const abs = (e) => { const r = e.getBoundingClientRect(); return { top: Math.round(r.top + scrollY), bottom: Math.round(r.bottom + scrollY), w: Math.round(r.width), h: Math.round(r.height) }; };
  const main = document.querySelector("main");
  const secciones = [...main.children].filter((x) => x.tagName === "SECTION").map((s) => ({ id: s.id || s.className, ...abs(s), franja: s.classList.contains("confianza") }));
  const huecos = [...document.querySelectorAll(".hueco-mdn")].map((h) => {
    const caja = h.querySelector(".hm-caja"), eti = h.querySelector(".hm-eti"), previo = h.previousElementSibling;
    return { ...abs(h), suelto: h.classList.contains("suelto"), caja: abs(caja), eti: abs(eti), aria: h.getAttribute("aria-label"), etiqueta: eti.textContent,
             fuente: getComputedStyle(eti).fontFamily, tam: getComputedStyle(eti).fontSize, previo: previo ? (previo.id || previo.className || previo.tagName) : null,
             padre: h.parentElement.tagName.toLowerCase(), estado: caja.getAttribute("data-mdn-state"), propio: h.hasAttribute("data-propio") };
  });
  const bot = [...document.querySelectorAll("a.boton")].find((a) => (a.hasAttribute("data-descarga") || (a.getAttribute("href") || "").endsWith("#descargar")) && a.offsetParent !== null);
  return { desbordeX: document.documentElement.scrollWidth, alto: document.documentElement.scrollHeight, secciones, huecos, descarga: bot ? abs(bot) : null, cls: window.__cls };
}"""


def sitio() -> Path:
    """Copia de la web (sin vídeo, guías ni herramientas) reconstruida desde las plantillas."""
    raiz = Path(tempfile.mkdtemp(prefix="ml325-nav-")) / "web"
    shutil.copytree(RAIZ, raiz, ignore=shutil.ignore_patterns(".git", "video", "guia", "tools", "docs", "__pycache__", ".pytest_cache"))
    construir_web.construir(raiz, raiz)
    return raiz


class Servidor:
    def __init__(self, raiz: Path):
        class Manejador(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args, **kwargs):  # silencio: el servidor de pruebas no escribe nada
                pass
        manejador = functools.partial(Manejador, directory=str(raiz))

        class Hilos(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True
        self.s = Hilos(("127.0.0.1", 0), manejador)
        self.url = f"http://127.0.0.1:{self.s.server_address[1]}"
        threading.Thread(target=self.s.serve_forever, daemon=True).start()

    def cerrar(self) -> None:
        self.s.shutdown()
        self.s.server_close()


def guia(i: int) -> dict:
    return {"name": f"Guía {i}", "description": "d", "url": f"https://metafy.gg/guides/n{i}", "cover_url": "", "price": {"value_in_cents": 999, "currency": "USD"},
            "subscriber_only": False, "authors": [{"name": "Ana" if i % 2 else "Bea"}], "average_rating": 9.0, "review_count": 5, "total_reading_time_minutes": 7,
            "purchase_count": 1000 - i}


def lista(n: int) -> str:
    return json.dumps({"v": 1, "actualizada": "2026-11-18T12:00:00.000Z", "guias": [guia(i) for i in range(n)]})


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
        cls.raiz = sitio()
        cls.web = Servidor(cls.raiz)

    @classmethod
    def tearDownClass(cls):
        cls.web.cerrar()
        cls.nav.close()
        cls.pw.stop()

    def abrir(self, ruta: str, ancho: int = 1366, modo: str = "render", retraso: int = 300, reducido: bool = False, reloj: bool = False,
              js: bool = True, servidor_ia: str | None = None, web: Servidor | None = None):
        """Abre `ruta`. `modo`: los de MDN_FALSO o «bloqueado» (el script de MDN no llega). `servidor_ia`: lista de guías que responde el servidor (None: 503)."""
        web = web or self.web
        ctx = self.nav.new_context(viewport={"width": ancho, "height": 800}, java_script_enabled=js, reduced_motion="reduce" if reducido else "no-preference")
        self.addCleanup(ctx.close)
        pagina = ctx.new_page()
        pagina.errores = []
        pagina.on("pageerror", lambda e: pagina.errores.append(str(e)))
        pagina.peticiones_mdn = []
        pagina.add_init_script(CLS_ENTRADA)

        def enrutar(r):
            url = r.request.url
            if url.startswith(web.url):
                return r.continue_()
            if url == construir_mdn.SCRIPT_MDN:
                pagina.peticiones_mdn.append(url)
                if modo == "bloqueado":
                    return r.abort()
                cuerpo = MDN_FALSO % {"modo": json.dumps(modo), "retraso": retraso}
                return r.fulfill(body=cuerpo, content_type="text/javascript")
            if url == SERVIDOR_IA and servidor_ia is not None:
                return r.fulfill(body=servidor_ia, content_type="application/json", headers={"access-control-allow-origin": "*"})
            if url.startswith("https://cdn.metafy.gg/"):
                return r.fulfill(body=PNG, content_type="image/png")
            return r.abort()
        pagina.route("**/*", enrutar)
        if reloj:
            pagina.clock.install()
        pagina.goto(f"{web.url}/{ruta}", wait_until="load")
        if reloj:
            pagina.clock.run_for(50)
        else:
            # Con las tipografías y las imágenes ya puestas la maqueta no cambia más. El CLS que se mide es solo el de lo que ocurre después (la
            # llegada del anuncio): los saltos de la propia carga de la página, que dependen de lo que tarden las imágenes, no son de este test.
            esperar_pagina_estable(pagina)
            pagina.evaluate("window.__cls = 0")
        return pagina

    def medir(self, p) -> dict:
        return p.evaluate(MEDIR)

    def caja_esperada(self, caja_ancho: int) -> tuple[int, int]:
        return (728, 90) if caja_ancho >= 728 else (300, 250)

    # ---------------------------------------------------------------- alto reservado y regla de colocación

    def test_alto_reservado_sin_desplazamiento_y_regla_de_colocacion_en_todas_las_paginas_y_anchos(self):
        for ruta in CON_ANUNCIO:
            for ancho in ANCHOS:
                with self.subTest(ruta=ruta, ancho=ancho):
                    p = self.abrir(ruta, ancho, modo="bloqueado")
                    m = self.medir(p)   # sin MDN: lo que se ve es solo lo que está reservado
                    sin_huecos = p.evaluate("(() => { document.querySelectorAll('.hueco-mdn').forEach((h) => { h.hidden = true; h.style.display = 'none'; }); return document.documentElement.scrollWidth; })()")
                    # los huecos no añaden desplazamiento horizontal (alguna página ya se pasa de ancho sin ellos: eso no es de este encargo)
                    self.assertLessEqual(m["desbordeX"], max(ancho, sin_huecos), "el hueco añade desplazamiento horizontal")
                    self.assertTrue(all(h["caja"]["w"] <= ancho for h in m["huecos"]))
                    self.assertEqual(len(m["huecos"]), CON_ANUNCIO[ruta])
                    for h in m["huecos"]:
                        w, alto = (728, 90) if h["w"] - (40 if ancho >= 768 and not h["suelto"] else 0) >= 728 else (300, 250)
                        self.assertEqual((h["caja"]["w"], h["caja"]["h"]), (w, alto), "alto o ancho reservado")
                        self.assertEqual(h["eti"]["h"], CABECERA_ETIQUETA)
                        self.assertEqual(h["etiqueta"], ETIQUETA[idioma_de(ruta)])
                        self.assertEqual(h["aria"], ETIQUETA[idioma_de(ruta)])
                        self.assertEqual(h["tam"], "11px")
                        self.assertIn("Geist Mono", h["fuente"])
                        self.assertGreaterEqual(h["caja"]["top"], h["eti"]["bottom"])
                    self.comprobar_colocacion(ruta, m)

    def comprobar_colocacion(self, ruta: str, m: dict) -> None:
        huecos, secciones = m["huecos"], m["secciones"]
        if Path(ruta).parent.name in ("learn", "aprender"):
            self.assertTrue(huecos[0]["suelto"])
            self.assertFalse(huecos[1]["suelto"])
            self.assertGreater(huecos[1]["top"], huecos[0]["bottom"])
            return
        # nunca antes del botón de descarga ni dentro de la primera sección
        self.assertIsNotNone(m["descarga"], "no se encontró el botón de descarga")
        for h in huecos:
            self.assertGreater(h["top"], m["descarga"]["bottom"], "hueco antes del botón de descarga")
            self.assertGreaterEqual(h["top"], secciones[0]["bottom"], "hueco dentro de la primera sección")
            self.assertEqual(h["padre"], "main")
        # primer hueco: tras la primera sección que termina a 560 px o más; si sigue la franja de datos, tras la franja
        k = next(i for i, s in enumerate(secciones) if s["bottom"] >= LIMITE_PRIMERA_SECCION)
        if k + 1 < len(secciones) and secciones[k + 1]["franja"]:
            k += 1
        self.assertEqual(huecos[0]["previo"], secciones[k]["id"], f"el primer hueco debía ir tras {secciones[k]['id']}")
        # segundo: solo con siete secciones o más (sin contar la primera), justo antes de las preguntas
        largas = len(secciones) - 1 >= 7
        self.assertEqual(len(huecos), 2 if largas else 1)
        if largas:
            self.assertEqual(huecos[1]["previo"], secciones[[s["id"] for s in secciones].index("preguntas") - 1]["id"])
        self.assertLessEqual(len(huecos), 2)

    # ---------------------------------------------------------------- el anuncio llega: nada salta

    RECORRER = """async () => { for (const y of [0.25, 0.5, 0.75, 1, 0].map((f) => f * (document.documentElement.scrollHeight - innerHeight))) {
      scrollTo(0, y); await new Promise((r) => setTimeout(r, 40)); } }"""

    def recorrida(self, ruta: str, ancho: int, modo: str):
        """Abre la página, la recorre entera (para que carguen las imágenes perezosas y cada hueco se acerque a la pantalla) y devuelve (página, medidas)."""
        p = self.abrir(ruta, ancho, modo=modo, retraso=150)
        p.evaluate(self.RECORRER)
        if modo == "render":
            p.wait_for_function("[...document.querySelectorAll('.hm-caja')].every((c) => c.getAttribute('data-mdn-state') === 'rendered')")
        esperar_pagina_estable(p)   # las imágenes perezosas que ha traído la recorrida ya están puestas
        return p, self.medir(p)

    def test_al_llegar_el_anuncio_de_mdn_no_salta_nada(self):
        """Misma página con MDN parado (el hueco reservado y vacío) y con su anuncio pintado: mismo alto de página y cada hueco en el mismo sitio."""
        for ruta in ("es/index.html", "coaches/index.html", "novedades/index.html", "ja/learn/index.html"):
            for ancho in ANCHOS:
                with self.subTest(ruta=ruta, ancho=ancho):
                    _, reservado = self.recorrida(ruta, ancho, "colgado")
                    p, pintado = self.recorrida(ruta, ancho, "render")
                    self.assertTrue(all(h["estado"] == "rendered" for h in pintado["huecos"]))
                    self.assertEqual(pintado["alto"], reservado["alto"], "la página cambió de alto al llegar el anuncio")
                    for a, d in zip(reservado["huecos"], pintado["huecos"]):
                        self.assertEqual((a["top"], a["h"], a["caja"]["w"], a["caja"]["h"]), (d["top"], d["h"], d["caja"]["w"], d["caja"]["h"]))
                        w, alto = self.caja_esperada(d["caja"]["w"])   # el anuncio pintado mide justo lo reservado
                        self.assertEqual((d["caja"]["w"], d["caja"]["h"]), (w, alto))
                    self.assertLess(pintado["cls"], 0.1, "CLS de la página con el anuncio")
                    self.assertEqual(p.errores, [])
                    self.assertEqual(len(p.peticiones_mdn), 1, "el script de MDN se pide una sola vez")

    # ---------------------------------------------------------------- anuncio de casa

    def comprobar_casa_visible(self, p, ruta: str, antes: dict) -> None:
        idioma = idioma_de(ruta)
        for i, h in enumerate(antes["huecos"]):
            casa = p.locator(".hueco-mdn").nth(i).locator(".hm-casa")
            self.assertEqual(casa.evaluate("e => getComputedStyle(e).visibility"), "visible")
            self.assertEqual(casa.get_attribute("href"), RUTA_LEARN[idioma])
            caja = casa.evaluate("e => { const r = e.getBoundingClientRect(), c = e.parentElement.getBoundingClientRect(); return [r.width, r.height, c.width, c.height]; }")
            self.assertEqual((round(caja[0]), round(caja[1])), (round(caja[2]), round(caja[3])), "el anuncio de casa llena la caja reservada")
        despues = self.medir(p)
        self.assertEqual(despues["alto"], antes["alto"], "el anuncio de casa cambió el alto de la página")
        for a, d in zip(antes["huecos"], despues["huecos"]):
            self.assertEqual((a["top"], a["h"], a["caja"]["w"], a["caja"]["h"]), (d["top"], d["h"], d["caja"]["w"], d["caja"]["h"]))

    def test_si_mdn_no_tiene_anuncio_sale_el_de_casa_con_el_mismo_alto_y_enlaza_a_learn_en_su_idioma(self):
        for ruta in ("index.html", "es/index.html", "pt/index.html", "ja/index.html", "es/aprender/index.html", "pt/aprender/index.html", "ja/learn/index.html", "overlay/index.html"):
            for ancho in (360, 768, 1366):
                with self.subTest(ruta=ruta, ancho=ancho):
                    p = self.abrir(ruta, ancho, modo="empty", retraso=50)
                    antes = self.medir(p)
                    p.evaluate("document.querySelectorAll('.hueco-mdn').forEach((h) => h.scrollIntoView())")
                    p.wait_for_function("[...document.querySelectorAll('.hm-caja')].every((c) => c.getAttribute('data-mdn-state') === 'empty')")
                    p.evaluate("window.scrollTo(0, 0)")
                    self.assertTrue(all(h["estado"] in (None, "waiting", "loading", "empty") for h in antes["huecos"]))
                    self.comprobar_casa_visible(p, ruta, antes)

    def test_si_el_script_de_mdn_no_llega_en_el_plazo_sale_el_de_casa(self):
        for modo in ("bloqueado", "colgado"):
            for ancho in (390, 1366):
                with self.subTest(modo=modo, ancho=ancho):
                    p = self.abrir("es/coaches/index.html", ancho, modo=modo, reloj=True)
                    antes = self.medir(p)
                    p.clock.run_for(construir_mdn.PLAZO_MDN_MS - 1000)
                    self.assertEqual(p.locator(".hm-casa").first.evaluate("e => getComputedStyle(e).visibility"), "hidden", "no debe salir antes del plazo")
                    p.clock.run_for(2000)
                    self.assertTrue(all(h["propio"] for h in self.medir(p)["huecos"]))
                    self.comprobar_casa_visible(p, "es/coaches/index.html", antes)

    def test_un_hueco_que_aun_no_ha_pedido_nada_no_enseña_el_de_casa_al_acabar_el_plazo(self):
        p = self.abrir("es/index.html", 1366, modo="espera", reloj=True)   # MDN vivo, pero el hueco aún está lejos de la pantalla
        p.clock.run_for(construir_mdn.PLAZO_MDN_MS + 1000)
        self.assertEqual([h["propio"] for h in self.medir(p)["huecos"]], [False, False])

    def test_sin_javascript_se_ve_el_anuncio_de_casa(self):
        p = self.abrir("es/index.html", 1366, js=False)
        casa = p.locator(".hm-casa")
        self.assertEqual(casa.count(), 2)
        self.assertEqual(casa.first.evaluate("e => getComputedStyle(e).visibility"), "visible")
        self.assertEqual(p.locator(".hueco-mdn").first.evaluate("e => e.getBoundingClientRect().height") > 100, True)

    def test_el_anuncio_de_casa_se_alcanza_con_el_teclado_solo_cuando_se_ve(self):
        p = self.abrir("es/index.html", 1366, modo="colgado")
        self.assertFalse(p.evaluate("(() => { const a = document.querySelector('.hm-casa'); a.focus(); return document.activeElement === a; })()"), "oculto no recibe el foco")
        p2 = self.abrir("es/index.html", 1366, modo="empty", retraso=20)
        p2.evaluate("document.querySelector('.hueco-mdn').scrollIntoView()")
        p2.wait_for_function("document.querySelector('.hm-caja').getAttribute('data-mdn-state') === 'empty'")
        self.assertTrue(p2.evaluate("(() => { const a = document.querySelector('.hm-casa'); a.focus(); return document.activeElement === a; })()"))

    # ---------------------------------------------------------------- movimiento

    def test_con_reducir_movimiento_el_hueco_no_se_anima(self):
        p = self.abrir("es/index.html", 1366, modo="empty", retraso=20, reducido=True)
        p.evaluate("document.querySelector('.hueco-mdn').scrollIntoView()")
        p.wait_for_function("document.querySelector('.hm-caja').getAttribute('data-mdn-state') === 'empty'")
        animado = p.evaluate("""() => [...document.querySelectorAll('.hueco-mdn, .hueco-mdn *')].filter((e) => {
          const c = getComputedStyle(e); return (c.animationName !== 'none' && c.animationDuration !== '0s') || (c.transitionDuration.split(',').some((d) => parseFloat(d) > 0)); }).length""")
        self.assertEqual(animado, 0)

    def test_el_hueco_no_es_fijo_ni_se_abre_solo(self):
        p = self.abrir("es/index.html", 390, modo="render")
        posiciones = p.evaluate("[...document.querySelectorAll('.hueco-mdn, .hm-caja')].map((e) => getComputedStyle(e).position)")
        self.assertTrue(all(x in ("static", "relative") for x in posiciones), posiciones)

    # ---------------------------------------------------------------- Learn

    def esperar_learn(self, p) -> None:
        p.wait_for_function("document.documentElement.classList.contains('learn-js') || document.documentElement.classList.contains('learn-sin-lista')")

    def esperar_pagina_activa(self, p, numero: str) -> None:
        p.wait_for_function("n => { const a = document.querySelector('#ap-pag [aria-current=\"page\"]'); return !!a && a.textContent.trim() === n; }", arg=numero)

    def hueco_tras_la_octava(self, p) -> bool:
        return p.evaluate("""() => { const g = document.getElementById('guias'), tarjetas = [...g.children].filter((x) => x.matches('a.guia')), h = g.querySelector('.hueco-mdn');
          return !!h && h.previousElementSibling === tarjetas[7] && g.querySelectorAll('.hueco-mdn').length === 1; }""")

    def hueco_en_rejilla(self, p) -> int:
        return p.locator("#guias .hueco-mdn").count()

    def test_learn_el_hueco_va_tras_la_octava_guia_al_cargar_y_el_otro_tras_el_paginador(self):
        for ruta in ("learn/", "es/aprender/", "pt/aprender/", "ja/learn/"):
            for ancho in ANCHOS:
                with self.subTest(ruta=ruta, ancho=ancho):
                    p = self.abrir(ruta, ancho, servidor_ia=None)
                    self.esperar_learn(p)
                    self.assertTrue(self.hueco_tras_la_octava(p))
                    self.assertEqual(p.locator(".hueco-mdn").count(), 2)
                    debajo = p.evaluate("document.querySelector('#ap-pag').getBoundingClientRect().bottom < document.querySelector('.hueco-mdn:not(.suelto)').getBoundingClientRect().top")
                    self.assertTrue(debajo, "el segundo hueco va tras el paginador")
                    self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), ancho)

    def test_learn_el_hueco_sigue_tras_la_octava_al_paginar_y_es_el_mismo_nodo(self):
        p = self.abrir("es/aprender/", 1366, servidor_ia=None)
        self.esperar_learn(p)
        p.evaluate("window.__hueco = document.querySelector('#guias .hueco-mdn')")
        for destino in ("2", "3", "1"):
            p.locator(f"#ap-pag a[data-p='{destino}']").first.click()
            self.esperar_pagina_activa(p, destino)
            self.assertTrue(self.hueco_tras_la_octava(p), f"página {destino}")
            self.assertTrue(p.evaluate("window.__hueco === document.querySelector('#guias .hueco-mdn')"), "MDN no debe pedir un anuncio nuevo con cada página")
        p.goto(f"{self.web.url}/es/aprender/?p=2", wait_until="load")
        self.esperar_learn(p)
        self.assertTrue(self.hueco_tras_la_octava(p))

    def test_learn_al_filtrar_el_hueco_aparece_solo_si_hay_mas_de_ocho_guias(self):
        p = self.abrir("es/aprender/", 1366, servidor_ia=lista(40))
        self.esperar_learn(p)
        p.evaluate("window.__hueco = document.querySelector('#guias .hueco-mdn')")
        self.assertTrue(self.hueco_tras_la_octava(p))
        p.select_option("#ap-creador", "Ana")        # 20 guías
        self.assertTrue(self.hueco_tras_la_octava(p))
        p.fill("#ap-buscar", "Guía 3")               # de las 20 de Ana (las impares), las que se llaman «Guía 3…»: 3, 31, 33, 35, 37 y 39
        self.assertEqual(p.locator("#guias a.guia").count(), 6)
        self.assertEqual(self.hueco_en_rejilla(p), 0, "con ocho guías o menos no hay hueco en la rejilla")
        self.assertEqual(p.locator(".hueco-mdn").count(), 1, "queda el de debajo del paginador")
        p.fill("#ap-buscar", "")
        self.assertTrue(self.hueco_tras_la_octava(p))
        self.assertTrue(p.evaluate("window.__hueco === document.querySelector('#guias .hueco-mdn')"))
        p.fill("#ap-buscar", "no existe esta guía")
        self.assertEqual(self.hueco_en_rejilla(p), 0)
        self.assertEqual(p.locator(".hueco-mdn").count(), 1)

    def test_learn_con_ocho_guias_o_menos_no_hay_hueco_en_la_rejilla_y_con_nueve_si(self):
        for n, esperado in ((5, 0), (8, 0), (9, 1)):
            with self.subTest(guias=n):
                p = self.abrir("es/aprender/", 1366, servidor_ia=lista(n))
                self.esperar_learn(p)
                self.assertEqual(self.hueco_en_rejilla(p), esperado)
                if esperado:
                    self.assertTrue(self.hueco_tras_la_octava(p))
                self.assertEqual(p.locator(".hueco-mdn:not(.suelto)").count(), 1)

    def test_learn_si_la_pagina_se_construyo_sin_guias_y_luego_llegan_el_hueco_se_crea_sin_copiar_el_estado_de_mdn(self):
        raiz = Path(tempfile.mkdtemp(prefix="ml325-sin-guias-")) / "web"
        shutil.copytree(self.raiz, raiz)
        (raiz / "learn" / "guias.json").write_text(lista(0), encoding="utf-8")
        construir_web.construir(raiz, raiz)
        web = Servidor(raiz)
        self.addCleanup(web.cerrar)
        html = (raiz / "es" / "aprender" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count('<aside class="hueco-mdn'), 1, "sin guías solo queda el de debajo")
        p = self.abrir("es/aprender/", 1366, servidor_ia=lista(30), web=web, retraso=50)
        self.esperar_learn(p)
        p.wait_for_function("document.querySelector('.hueco-mdn:not(.suelto) .hm-caja').getAttribute('data-mdn-state') === 'rendered'")   # el de abajo ya tiene el suyo
        p.evaluate("window.scrollTo(0, 0)")
        self.assertTrue(self.hueco_tras_la_octava(p))
        self.assertEqual(p.locator(".hueco-mdn").count(), 2)
        p.wait_for_function("document.querySelector('#guias .hueco-mdn .hm-caja').getAttribute('data-mdn-state') !== null")
        self.assertEqual(p.errores, [])

    def test_learn_el_html_estatico_y_el_pintado_dan_la_misma_rejilla(self):
        p = self.abrir("es/aprender/", 1366, servidor_ia=None, modo="colgado")   # con MDN parado, para que su estado no cambie el HTML
        self.esperar_learn(p)
        antes = p.evaluate("document.getElementById('guias').outerHTML")
        p.locator("#ap-pag a[data-p='2']").first.click()
        self.esperar_pagina_activa(p, "2")
        p.locator("#ap-pag a[data-p='1']").first.click()
        self.esperar_pagina_activa(p, "1")
        self.assertEqual(p.evaluate("document.getElementById('guias').outerHTML"), antes)


if __name__ == "__main__":
    unittest.main()
