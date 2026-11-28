#!/usr/bin/env python3
"""ML-379 (E1, E2, E4): origen en el nombre de los eventos de descarga, enlace por correo en la primera pantalla del móvil y /no-contar/.

E1: ``origen.js`` añade ``-utm-<campaña>`` (utm_campaign, o utm_source si no hay) o ``-ref-<clase>`` (x, google, metafy, instagram, directo, otro,
según document.referrer) a los eventos ``descarga-*``, ``correo-movil-*`` y ``compartir-movil-*``; el origen se fija con la primera página
vista de la visita (sessionStorage) y se normaliza a [a-z0-9_]. E2: a 375x812 y 390x844 el campo de correo y su botón se ven enteros en
la primera pantalla de las cuatro portadas, justo tras el título y antes de la frase y del botón de descarga. E4: ``/no-contar/`` pone o quita
``skipgc`` en localStorage, no se enlaza ni está en el sitemap, no carga GoatCounter, y el código propio no cuenta con la marca puesta.

Las pruebas con navegador usan Playwright y un count.js falso (copia de lo que hace el de GoatCounter: lee ``data-goatcounter-click`` al
hacer clic y se calla con ``skipgc``). Se saltan si Playwright o Chromium no están.

Uso:  python3 tools/test_origen_eventos.py
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_web  # noqa: E402
from test_pagina_learn_navegador import Servidor  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright las pruebas de navegador se saltan
    sync_playwright = None

RAIZ = construir_web.RAIZ
PORTADAS = {"en": "index.html", "es": "es/index.html", "pt": "pt/index.html", "ja": "ja/index.html"}
TAMANOS = ((375, 812), (390, 844))
CORREO_URL = construir_web.URL_ENLACE_CORREO
# Lo que hace count.js de GoatCounter con los eventos: filtra con skipgc, lee el nombre al hacer clic y manda path y título.
CONTADOR_FALSO = """(function(){window.__eventos=[];var g=window.goatcounter=window.goatcounter||{};
g.filter=function(){try{if(localStorage.getItem('skipgc')==='t')return 'skipgc'}catch(e){}return false};
g.count=function(v){if(g.filter())return;window.__eventos.push({path:v.path,title:v.title})};
function enlazar(){document.querySelectorAll('*[data-goatcounter-click]').forEach(function(el){if(el.dataset.goatcounterBound)return;
var f=function(){g.count({event:true,path:el.dataset.goatcounterClick,title:el.dataset.goatcounterTitle||''})};
el.addEventListener('click',f,false);el.addEventListener('auxclick',f,false);el.dataset.goatcounterBound='true'})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',enlazar);else enlazar()})();"""


def _paginas_con_goatcounter():
    return sorted(p for p in RAIZ.rglob("*.html") if not {".git", "plantillas", "docs", "tools"} & set(p.relative_to(RAIZ).parts)
                  and "gc.zgo.at/count.js" in p.read_text(encoding="utf-8"))


class TestPaginasEstaticas(unittest.TestCase):
    def test_origen_js_va_antes_de_goatcounter_en_todas_las_paginas_que_cuentan(self):
        paginas = _paginas_con_goatcounter()
        self.assertGreaterEqual(len(paginas), 30)
        for ruta in paginas:
            html = ruta.read_text(encoding="utf-8")
            with self.subTest(pagina=ruta.relative_to(RAIZ).as_posix()):
                self.assertEqual(html.count('src="/origen.js"'), 1)
                self.assertLess(html.index('src="/origen.js"'), html.index("gc.zgo.at/count.js"))

    def test_descarga_js_pide_el_nombre_a_origen_js_y_respeta_skipgc(self):
        js = (RAIZ / "descarga.js").read_text(encoding="utf-8")
        self.assertIn("window.manalabOrigen", js)
        self.assertIn("o.de(ruta)", js)
        self.assertIn('getItem("skipgc") === "t"', js)

    def test_origen_js_es_el_unico_sitio_que_arma_el_origen(self):
        for ruta in RAIZ.glob("*.js"):
            if ruta.name != "origen.js":
                self.assertNotIn("utm_campaign", ruta.read_text(encoding="utf-8"), ruta.name)

    def test_no_contar_no_esta_enlazada_ni_en_el_sitemap_ni_cuenta(self):
        pagina = (RAIZ / "no-contar" / "index.html").read_text(encoding="utf-8")
        self.assertRegex(pagina, r'<meta content="noindex, nofollow" name="robots"/>')
        self.assertNotIn("goatcounter", pagina)
        self.assertNotIn("gc.zgo.at", pagina)
        self.assertNotIn("no-contar", (RAIZ / "sitemap.xml").read_text(encoding="utf-8"))
        for ruta in RAIZ.rglob("*.html"):
            if {".git", "plantillas", "docs", "tools", "no-contar"} & set(ruta.relative_to(RAIZ).parts):
                continue
            self.assertNotIn("no-contar", ruta.read_text(encoding="utf-8"), f"{ruta.relative_to(RAIZ)} enlaza /no-contar/")


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class TestConNavegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.nav = cls.pw.chromium.launch()
        except Exception as error:  # noqa: BLE001  silencio: sin Chromium instalado la prueba se salta
            cls.pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {error}")
        cls.web = Servidor(RAIZ)

    @classmethod
    def tearDownClass(cls):
        cls.web.cerrar()
        cls.nav.close()
        cls.pw.stop()

    def abrir(self, ruta: str, ancho: int = 1040, alto: int = 800, movil: bool = False, referente: str | None = None):
        contexto = self.nav.new_context(viewport={"width": ancho, "height": alto}, is_mobile=movil, has_touch=movil, device_scale_factor=2 if movil else 1)
        pagina = contexto.new_page()
        pagina.route("**/*", self.ruta_red)
        pagina.goto(f"{self.web.url}/{ruta}", wait_until="load", referer=referente)
        return contexto, pagina

    def ruta_red(self, r):
        """Todo lo de fuera se aborta; GoatCounter es el contador falso y el ZIP una descarga de verdad (la página no navega)."""
        url = r.request.url
        if "gc.zgo.at/count.js" in url:
            return r.fulfill(status=200, content_type="application/javascript", body=CONTADOR_FALSO)
        if url.endswith("-portable.zip"):
            return r.fulfill(status=200, headers={"Content-Disposition": "attachment; filename=manalab.zip"}, body="zip")
        if url == CORREO_URL:
            return r.fulfill(status=204, body="")
        return r.continue_() if url.startswith(self.web.url) else r.abort()

    def evento_del_boton_hero(self, ruta: str, referente: str | None = None) -> str:
        contexto, pagina = self.abrir(ruta, referente=referente)
        pagina.click(".hero-cta a[data-descarga]")
        nombre = pagina.evaluate("window.__eventos[0].path")
        self.assertEqual(nombre, pagina.evaluate("window.__eventos[0].title"))
        contexto.close()
        return nombre

    def test_utm_campaign_va_en_el_nombre(self):
        self.assertEqual(self.evento_del_boton_hero("ja/index.html?utm_source=x&utm_campaign=Black-Friday%202026"),
                         "descarga-portada-ja-hero-utm-black_friday_2026")

    def test_sin_campaña_se_usa_utm_source(self):
        self.assertEqual(self.evento_del_boton_hero("index.html?utm_source=Instagram"), "descarga-portada-en-hero-utm-instagram")

    def test_clase_del_referente(self):
        casos = {"https://t.co/abc": "x", "https://twitter.com/manalab": "x", "https://www.google.com/": "google", "https://www.google.es/search?q=a": "google",
                 "https://metafy.gg/@manalab": "metafy", "https://l.instagram.com/?u=1": "instagram", "https://example.org/blog": "otro", None: "directo",
                 "https://evilgoogle.com/": "otro"}
        for referente, clase in casos.items():
            with self.subTest(referente=referente):
                self.assertEqual(self.evento_del_boton_hero("es/index.html", referente), f"descarga-portada-es-hero-ref-{clase}")

    def test_normaliza_y_limita_la_longitud(self):
        nombre = self.evento_del_boton_hero("index.html?utm_campaign=" + "Ñandú!!%20" + "a" * 80)
        self.assertRegex(nombre, r"^descarga-portada-en-hero-utm-[a-z0-9_]{1,30}$")
        self.assertEqual(self.evento_del_boton_hero("index.html?utm_campaign=%3Cscript%3E"), "descarga-portada-en-hero-utm-script")
        # sin nada aprovechable en la campaña se cae al referente
        self.assertEqual(self.evento_del_boton_hero("index.html?utm_campaign=%21%21%21"), "descarga-portada-en-hero-ref-directo")

    def test_la_descarga_desde_otra_pagina_conserva_el_origen_de_la_primera(self):
        contexto, pagina = self.abrir("index.html?utm_campaign=lanzamiento", referente="https://t.co/x")
        pagina.goto(f"{self.web.url}/es/magic-online/", wait_until="load")   # otra página de la misma visita, sin parámetros
        pagina.click("a[data-descarga]")
        self.assertRegex(pagina.evaluate("window.__eventos[0].path"), r"^descarga-magic-online-es(-\w+)?-utm-lanzamiento$")
        contexto.close()

    def test_sin_sessionstorage_sigue_funcionando(self):
        contexto = self.nav.new_context()
        pagina = contexto.new_page()
        pagina.add_init_script("Object.defineProperty(window,'sessionStorage',{get(){throw new Error('bloqueado')}})")
        pagina.route("**/*", self.ruta_red)
        pagina.goto(f"{self.web.url}/index.html?utm_campaign=sin_almacen", wait_until="load")
        pagina.click(".hero-cta a[data-descarga]")
        self.assertEqual(pagina.evaluate("window.__eventos[0].path"), "descarga-portada-en-hero-utm-sin_almacen")
        contexto.close()

    def test_lo_que_no_es_descarga_no_cambia(self):
        contexto, pagina = self.abrir("index.html?utm_campaign=bf")
        pagina.click("a[data-goatcounter-click=apoyo]", no_wait_after=True)
        self.assertEqual(pagina.evaluate("window.__eventos[0].path"), "apoyo")
        contexto.close()

    def test_telefono_correo_zip_y_compartir_llevan_el_origen(self):
        contexto, pagina = self.abrir("pt/index.html?utm_campaign=tiktok", 390, 844, movil=True)
        pagina.fill(".movil-correo input", "alguien@example.com")
        pagina.click(".movil-correo button")
        pagina.wait_for_function("window.__eventos.length >= 1")
        self.assertEqual(pagina.evaluate("window.__eventos[0].path"), "correo-movil-portada-pt-utm-tiktok")
        self.assertEqual(pagina.evaluate("window.__eventos[0].title"), "correo-movil-portada-pt-utm-tiktok")
        pagina.click(".movil-zip a")
        self.assertEqual(pagina.evaluate("window.__eventos[1].path"), "descarga-movil-portada-pt-utm-tiktok")
        contexto.close()

    def test_con_skipgc_ni_los_eventos_propios_ni_los_de_count_js_cuentan(self):
        contexto, pagina = self.abrir("index.html")
        pagina.evaluate("localStorage.setItem('skipgc','t')")
        pagina.click(".hero-cta a[data-descarga]")
        self.assertEqual(pagina.evaluate("window.__eventos.length"), 0)
        contexto.close()
        contexto, pagina = self.abrir("es/index.html", 390, 844, movil=True)
        pagina.evaluate("localStorage.setItem('skipgc','t')")
        pagina.fill(".movil-correo input", "alguien@example.com")
        pagina.click(".movil-correo button")
        pagina.wait_for_selector(".movil-correo-estado:not(:empty)")
        # el contador falso de GoatCounter también se calla, así que se espía directamente la llamada de descarga.js
        pagina.evaluate("window.__llamadas=0; var c=window.goatcounter.count; window.goatcounter.count=function(v){window.__llamadas++; return c(v)}; 0")
        pagina.click(".movil-zip a")
        self.assertEqual(pagina.evaluate("window.__llamadas"), 0, "descarga.js llamó a goatcounter.count con skipgc puesto")
        contexto.close()

    def test_no_contar_pone_y_quita_la_marca_y_muestra_el_estado(self):
        contexto, pagina = self.abrir("no-contar/")
        self.assertIn("SÍ se cuentan", pagina.inner_text("#estado"))
        pagina.click("#cambiar")
        self.assertEqual(pagina.evaluate("localStorage.getItem('skipgc')"), "t")
        self.assertIn("NO se cuentan", pagina.inner_text("#estado"))
        pagina.reload()
        self.assertIn("NO se cuentan", pagina.inner_text("#estado"))
        pagina.click("#cambiar")
        self.assertIsNone(pagina.evaluate("localStorage.getItem('skipgc')"))
        self.assertIn("SÍ se cuentan", pagina.inner_text("#estado"))
        contexto.close()

    def test_no_contar_avisa_si_el_navegador_no_guarda(self):
        contexto = self.nav.new_context()
        pagina = contexto.new_page()
        pagina.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('bloqueado')}})")
        pagina.goto(f"{self.web.url}/no-contar/", wait_until="load")
        self.assertIn("No se puede guardar", pagina.inner_text("#estado"))
        self.assertTrue(pagina.is_hidden("#cambiar"))
        contexto.close()

    def test_correo_en_la_primera_pantalla_del_telefono_en_los_cuatro_idiomas(self):
        for idioma, ruta in PORTADAS.items():
            for ancho, alto in TAMANOS:
                with self.subTest(idioma=idioma, tamano=f"{ancho}x{alto}"):
                    contexto, pagina = self.abrir(ruta, ancho, alto, movil=True)
                    m = pagina.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
                      const f = r('.movil-correo'), b = r('.movil-correo button'), h = r('h1'), s = r('p.sub');
                      return { fTop: f.top, bBottom: b.bottom, hBottom: h.bottom, sTop: s.top, ancho: document.documentElement.scrollWidth,
                               titulo: getComputedStyle(document.querySelector('.movil-tit')).display }; }""")
                    self.assertLessEqual(m["bBottom"], alto - 120, "el botón de enviar debe verse aun con las barras del navegador")   # ~120 px de barras
                    self.assertGreaterEqual(m["fTop"], m["hBottom"], "el bloque va después del título")
                    self.assertLessEqual(m["fTop"] - m["hBottom"], 40, "el bloque va justo tras el título")
                    self.assertLessEqual(m["bBottom"], m["sTop"], "el bloque va antes de la frase de la portada")
                    self.assertEqual(m["titulo"], "none", "el título duplicado de la caja se oculta con el campo de correo")
                    self.assertLessEqual(m["ancho"], ancho)
                    contexto.close()

    def test_en_ordenador_no_hay_bloque_de_correo_y_el_orden_no_cambia(self):
        for ruta in PORTADAS.values():
            contexto, pagina = self.abrir(ruta, 1040, 800)
            self.assertEqual(pagina.locator(".movil-correo").count(), 0)
            self.assertEqual(pagina.evaluate("document.querySelector('[data-movil-aqui]').getBoundingClientRect().height"), 0)
            contexto.close()


if __name__ == "__main__":
    unittest.main()
