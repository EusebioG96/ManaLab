#!/usr/bin/env python3
"""ML-417: el enlace al manual en PDF sale de version.json, igual que el botón de descarga.

Protege: toda página con un enlace a ManaLab-manual-en.pdf lo marca con data-manual y carga descarga.js; con un version.json válido el enlace
se actualiza a esa versión sin tocar el HTML (en el pie de cada idioma y en Novedades); con un version.json no válido queda el href generado al construir.

Uso:  python3 -m pytest tools/test_manual_version_json.py
"""
import json
import re
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_qa_web_navegador import Servidor, sitio, sync_playwright  # noqa: E402

BASE = "https://github.com/EusebioG96/ManaLab/releases/download/"
PAGINAS = ("/", "/es/", "/pt/", "/ja/", "/ja/learn/", "/novedades/", "/es/novedades/", "/coaches/", "/404.html")
_ENLACE = re.compile(r'<a [^>]*ManaLab-manual-en\.pdf[^>]*>')


def version_json(version: str) -> str:
    """Un version.json válido para ``version``, con el mismo formato que escribe generar_version_json.py."""
    return json.dumps({"esquema": 1, "tag": f"v{version}", "version": version, "descarga": f"{BASE}v{version}/ManaLab-{version}-portable.zip"})


class ManualEnHtml(unittest.TestCase):
    def test_todo_enlace_al_manual_lleva_data_manual_y_la_pagina_carga_descarga_js(self):
        raiz = Path(__file__).resolve().parent.parent
        total = 0
        for pagina in raiz.rglob("*.html"):
            if pagina.relative_to(raiz).parts[0] in ("docs", "plantillas", "tools"):
                continue
            html = pagina.read_text(encoding="utf-8")
            enlaces = _ENLACE.findall(html)
            for enlace in enlaces:
                self.assertIn("data-manual", enlace, f"{pagina}: falta data-manual")
            if enlaces:
                total += len(enlaces)
                self.assertIn("/descarga.js", html, f"{pagina}: tiene el manual pero no carga descarga.js")
        self.assertGreaterEqual(total, 8)


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class ManualEnNavegador(unittest.TestCase):
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

    def hrefs(self, ruta: str, cuerpo: str | None) -> list[str]:
        """href de los enlaces al manual de ``ruta`` tras servir ``cuerpo`` como /version.json (None: el real)."""
        contexto = self.nav.new_context()
        contexto.route("**/*", lambda r: r.continue_() if r.request.url.startswith(self.servidor.url) else r.abort())
        if cuerpo is not None:   # Playwright da prioridad a la ruta registrada la última
            contexto.route("**/version.json", lambda r: r.fulfill(status=200, content_type="application/json", body=cuerpo))
        pagina = contexto.new_page()
        pagina.goto(self.servidor.url + ruta, wait_until="load")
        pagina.wait_for_timeout(400)
        salida = pagina.evaluate("[...document.querySelectorAll('a[data-manual]')].map(a => a.getAttribute('href'))")
        contexto.close()
        return salida

    def test_el_manual_toma_la_version_de_version_json(self):
        esperado = f"{BASE}v9.8.7/ManaLab-manual-en.pdf"
        for ruta in PAGINAS:
            hrefs = self.hrefs(ruta, version_json("9.8.7"))
            if ruta != "/404.html" and ruta != "/coaches/":
                self.assertTrue(hrefs, f"{ruta}: sin enlace al manual")
            self.assertTrue(all(h == esperado for h in hrefs), f"{ruta}: {hrefs}")

    def test_con_un_version_json_no_valido_queda_el_enlace_generado(self):
        generado = json.loads((Path(__file__).resolve().parent.parent / "version.json").read_text(encoding="utf-8"))["version"]
        malo = json.dumps({"tag": "v1.2.3", "version": "1.2.3", "descarga": "https://ejemplo.test/x.zip"})
        for ruta in ("/", "/es/novedades/"):
            hrefs = self.hrefs(ruta, malo)
            self.assertTrue(hrefs and all(h == f"{BASE}v{generado}/ManaLab-manual-en.pdf" for h in hrefs), f"{ruta}: {hrefs}")


if __name__ == "__main__":
    unittest.main()
