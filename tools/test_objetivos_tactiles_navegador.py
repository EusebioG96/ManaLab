#!/usr/bin/env python3
"""ML-417: ningún elemento interactivo de la web mide menos de 24x24 px a 320 y 390 px de ancho (WCAG 2.5.8, nivel AA).

Recorre todas las páginas (todos los idiomas), con el menú móvil cerrado y abierto, y lista lo que se toca: enlaces, botones, campos, resúmenes.
Quedan fuera lo que la norma exime: un enlace dentro de una frase (en línea, con texto suyo alrededor), la casilla de un <label> cuyo conjunto
sí llega a 24 px (el control nativo lo pone el navegador) y lo oculto. Lo demás que se justifique va en ``LISTA_BLANCA`` con su motivo.

Uso:  python3 -m pytest tools/test_objetivos_tactiles_navegador.py
"""
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_qa_web_navegador import ESPERA_MS, Servidor, sitio, sync_playwright  # noqa: E402
try:
    from playwright.sync_api import Error as PlaywrightError
except ImportError:  # silencio: sin Playwright la prueba se salta
    PlaywrightError = Exception

MINIMO = 24      # px: lado mínimo del objetivo (WCAG 2.5.8)
ANCHOS = (320, 390)
OMITIDAS = ("docs/", "plantillas/", "tools/", "google8d")
# (ruta, texto del elemento) -> motivo. Vacía: todo objetivo de la web cumple. Una entrada nueva debe decir por qué la norma la exime.
LISTA_BLANCA: dict[tuple[str, str], str] = {}

RECOGER = """(minimo) => {
  const sel = 'a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [tabindex]:not([tabindex="-1"])';
  const salida = [];
  for (const e of document.querySelectorAll(sel)) {
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    if ((!r.width && !r.height) || cs.visibility === 'hidden') continue;
    if (e.closest('details:not([open])') && !e.matches('summary')) continue;   // menú cerrado: no se toca
    if (e.closest('[aria-hidden=true]') || r.right < 0 || r.left > innerWidth + 1) continue;   // oculto o fuera de pantalla (el señuelo antispam)
    if (r.width >= minimo && r.height >= minimo) continue;
    if (e.tagName === 'INPUT' && e.closest('label')) {   // casilla dentro de su etiqueta: se toca la etiqueta entera
      const l = e.closest('label').getBoundingClientRect();
      if (l.width >= minimo && l.height >= minimo) continue;
    }
    if (e.tagName === 'A' && cs.display === 'inline') {   // enlace dentro de una frase
      let bloque = e.parentElement;
      while (bloque && getComputedStyle(bloque).display === 'inline') bloque = bloque.parentElement;
      const resto = (bloque ? bloque.textContent : '').replace(e.textContent, '').replace(/\\s+/g, '');
      if (resto.length >= 8) continue;
    }
    const texto = (e.textContent || e.getAttribute('aria-label') || e.name || '').trim().replace(/\\s+/g, ' ').slice(0, 40);
    salida.push([texto, Math.round(r.width), Math.round(r.height), e.outerHTML.slice(0, 90)]);
  }
  return salida;
}"""


def rutas(raiz: Path) -> list[str]:
    """Ruta de cada página .html de la web copiada en ``raiz`` (con barra final si es un index.html)."""
    salida = []
    for pagina in sorted(raiz.rglob("*.html")):
        relativa = pagina.relative_to(raiz).as_posix()
        if relativa.startswith(OMITIDAS):
            continue
        salida.append("/" + relativa[:-len("index.html")] if pagina.name == "index.html" else "/" + relativa)
    return salida


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class ObjetivosTactiles(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.raiz = sitio()
        cls.servidor = Servidor(cls.raiz)
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
        cls.servidor.cerrar()
        shutil.rmtree(cls.raiz.parent, ignore_errors=True)

    def pequenos(self, ruta: str, ancho: int) -> list[str]:
        """Elementos de ``ruta`` a ``ancho`` px que miden menos de MINIMO, con el menú cerrado y abierto."""
        contexto = self.nav.new_context(viewport={"width": ancho, "height": 800}, is_mobile=True, has_touch=True)
        contexto.route("**/*", lambda r: r.continue_() if r.request.url.startswith(self.servidor.url) else r.abort())
        pagina = contexto.new_page()
        pagina.goto(self.servidor.url + ruta, wait_until="load", timeout=ESPERA_MS)
        try:
            pagina.evaluate("document.fonts.ready")
            encontrados = pagina.evaluate(RECOGER, MINIMO)
            if pagina.locator("details.menu > summary").count():
                pagina.click("details.menu > summary")
                encontrados += pagina.evaluate(RECOGER, MINIMO)
        except PlaywrightError:  # la página redirige (sorteo): se mide la de destino, que el recorrido ya cubre
            contexto.close()
            return []
        contexto.close()
        return [f"{ruta} a {ancho}px: «{t}» {w}x{h}  {html}" for t, w, h, html in encontrados if (ruta, t) not in LISTA_BLANCA]

    def test_el_recorrido_cubre_todas_las_paginas_e_idiomas(self):
        paginas = rutas(self.raiz)
        self.assertGreaterEqual(len(paginas), 40)
        self.assertTrue({"/", "/es/", "/pt/", "/ja/", "/404.html", "/guia/guia_manalab_ko.html", "/privacy/"} <= set(paginas))

    def test_ningun_objetivo_tactil_mide_menos_de_24_px(self):
        fallos = []
        for ruta in rutas(self.raiz):
            for ancho in ANCHOS:
                fallos += self.pequenos(ruta, ancho)
        self.assertEqual([], sorted(set(fallos)), "objetivos de menos de 24 px")


if __name__ == "__main__":
    unittest.main()
