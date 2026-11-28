#!/usr/bin/env python3
"""ML-417: con las tipografías retrasadas, la guía y /privacy/ no saltan (CLS <= 0,02) y /safety/ tampoco pasa de 0,05, gracias a los tipos de reserva y a que la columna ya no se mide en ch.

Mide como test_qa_web_navegador: el servidor tarda en dar cada tipografía y se suma el desplazamiento de diseño hasta que cargan.

Uso:  python3 -m pytest tools/test_fuentes_reserva_navegador.py
"""
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_qa_web_navegador import ESPERA_MS, ESTABLE, MIDE_CLS, RETRASO_FUENTES, Servidor, sitio, sync_playwright  # noqa: E402

LIMITE_CLS = 0.02
LIMITE_SEGURIDAD = 0.05   # el límite de test_qa_web_navegador: el párrafo de /safety/ a 390px cae justo en un salto de línea (la reserva mide un 1,4 % menos)
SEGURIDAD = ("/safety/", "/es/seguridad/")
RUTAS = ("/guia/guia_manalab_en.html", "/guia/guia_manalab_es.html", "/guia/guia_manalab_de.html", "/privacy/") + SEGURIDAD


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class FuentesRetrasadas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raiz = sitio()
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
        cls.lento.cerrar()
        shutil.rmtree(cls.raiz.parent, ignore_errors=True)

    def test_guia_privacidad_y_seguridad_no_saltan_con_las_tipografias_retrasadas(self):
        for ruta in RUTAS:
            self.assertTrue((self.raiz / ruta.strip("/")).exists() or (self.raiz / ruta.strip("/") / "index.html").exists(), ruta)
            for ancho in (320, 390, 1366):
                contexto = self.nav.new_context(viewport={"width": ancho, "height": 800})
                contexto.route("**/*", lambda r: r.continue_() if r.request.url.startswith(self.lento.url) else r.abort())
                contexto.add_init_script(MIDE_CLS)
                pagina = contexto.new_page()
                pagina.goto(self.lento.url + ruta, wait_until="load")
                pagina.wait_for_function(ESTABLE, timeout=ESPERA_MS)
                pagina.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
                cls = pagina.evaluate("window.__cls")
                contexto.close()
                self.assertLessEqual(cls, LIMITE_SEGURIDAD if ruta in SEGURIDAD else LIMITE_CLS, f"{ruta} a {ancho}px: CLS {cls:.3f}")


if __name__ == "__main__":
    unittest.main()
