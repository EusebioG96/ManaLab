#!/usr/bin/env python3
"""ML-329: la vista previa local (tools/vista_previa.py) sirve la web como GitHub Pages. Sin red.

Arranca el servidor en un puerto libre dentro del test y comprueba por HTTP: portada, carpetas con y sin barra final (redirección), JSON con su tipo,
404 con el contenido de 404.html, y que ``..`` y ``.git`` se rechazan. Los rechazos se prueban en una raíz de pruebas con un archivo «secreto» justo
fuera de ella (con la raíz real no habría nada que filtrar). Un test en Chromium (se salta si no está) mira que Learn pinte las guías desde la copia.

Uso:  python3 -m pytest tools/test_vista_previa.py
"""
import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import vista_previa
from navegador_comun import esperar_hasta

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright el test de navegador se salta
    sync_playwright = None

SECRETO = "contenido-fuera-de-la-raiz"
CONFIG_GIT = "[core] secreto-del-repositorio"


class ServidorDePrueba:
    """Un servidor de la vista previa en un hilo y en un puerto libre; ``pedir`` hace una petición con la ruta tal cual (sin normalizarla)."""

    def __init__(self, raiz: Path):
        self.servidor = vista_previa.abrir_servidor(raiz, 0)
        self.puerto = self.servidor.server_address[1]
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def pedir(self, ruta: str, metodo: str = "GET", cabeceras: dict | None = None) -> tuple[int, dict, bytes]:
        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=10)
        try:
            conexion.putrequest(metodo, ruta, skip_host=False, skip_accept_encoding=True)   # putrequest no normaliza «..»
            for nombre, valor in (cabeceras or {}).items():
                conexion.putheader(nombre, valor)
            conexion.endheaders()
            respuesta = conexion.getresponse()
            return respuesta.status, {k.lower(): v for k, v in respuesta.getheaders()}, respuesta.read()
        finally:
            conexion.close()

    def cerrar(self) -> None:
        self.servidor.shutdown()
        self.servidor.server_close()


class TestSirveLaWebReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.web = ServidorDePrueba(RAIZ)

    @classmethod
    def tearDownClass(cls):
        cls.web.cerrar()

    def test_la_portada_y_las_carpetas_dan_su_index(self):
        for ruta, archivo in (("/", "index.html"), ("/es/", "es/index.html"), ("/learn/", "learn/index.html")):
            with self.subTest(ruta):
                estado, cabeceras, cuerpo = self.web.pedir(ruta)
                self.assertEqual(estado, 200)
                self.assertEqual(cabeceras["content-type"], "text/html; charset=utf-8")
                self.assertEqual(cuerpo, (RAIZ / archivo).read_bytes())

    def test_una_carpeta_sin_barra_redirige_a_la_carpeta(self):
        estado, cabeceras, _ = self.web.pedir("/learn")
        self.assertEqual(estado, 301)
        self.assertEqual(cabeceras["location"], "/learn/")

    def test_el_json_de_las_guias_sale_con_su_tipo(self):
        estado, cabeceras, cuerpo = self.web.pedir("/learn/guias.json")
        self.assertEqual(estado, 200)
        self.assertTrue(cabeceras["content-type"].startswith("application/json"))
        json.loads(cuerpo)   # es JSON válido, el mismo archivo de learn/guias.json

    def test_una_ruta_inexistente_da_404_con_el_html_de_404(self):
        estado, cabeceras, cuerpo = self.web.pedir("/esta/ruta/no/existe")
        self.assertEqual(estado, 404)
        self.assertEqual(cabeceras["content-type"], "text/html; charset=utf-8")
        self.assertEqual(cuerpo, (RAIZ / "404.html").read_bytes())

    def test_tipos_de_los_archivos_que_el_navegador_necesita(self):
        for extension, tipo in ((".js", "text/javascript"), (".webp", "image/webp"), (".svg", "image/svg+xml"), (".woff2", "font/woff2"),
                                (".mp4", "video/mp4"), (".json", "application/json")):
            with self.subTest(extension):
                self.assertTrue(vista_previa.tipo_mime(Path("archivo" + extension)).startswith(tipo))

    def test_las_urls_principales_existen_y_son_las_de_las_paginas_clave(self):
        urls = [url for _, url in vista_previa.urls_principales(RAIZ, 8000)]
        for esperada in ("/", "/es/", "/pt/", "/ja/", "/learn/", "/es/aprender/", "/pt/aprender/", "/ja/learn/", "/privacy/", "/safety/", "/es/seguridad/"):
            self.assertIn(f"http://localhost:8000{esperada}", urls)


class TestNoSirveNadaFueraDeLaRaiz(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporal = tempfile.TemporaryDirectory(prefix="ml329-vista-")
        base = Path(cls.temporal.name)
        raiz = base / "web"
        (raiz / ".git").mkdir(parents=True)
        (raiz / "carpeta").mkdir()
        (raiz / "index.html").write_text("portada", encoding="utf-8")
        (raiz / "404.html").write_text("no existe", encoding="utf-8")
        (raiz / "carpeta" / "index.html").write_text("dentro de carpeta", encoding="utf-8")
        (raiz / "pagina.html").write_text("pagina suelta", encoding="utf-8")
        (raiz / ".git" / "config").write_text(CONFIG_GIT, encoding="utf-8")
        (base / "secreto.txt").write_text(SECRETO, encoding="utf-8")
        cls.web = ServidorDePrueba(raiz)

    @classmethod
    def tearDownClass(cls):
        cls.web.cerrar()
        cls.temporal.cleanup()

    def test_dos_puntos_se_rechaza_en_todas_sus_formas(self):
        for ruta in ("/../", "/../secreto.txt", "/%2e%2e/secreto.txt", "/carpeta/../index.html", "/carpeta/%2E%2E/index.html",
                     "/..%2fsecreto.txt", "/carpeta/..\\index.html", "/..\\secreto.txt"):
            with self.subTest(ruta):
                estado, _, cuerpo = self.web.pedir(ruta)
                self.assertEqual(estado, 400)
                self.assertNotIn(SECRETO.encode(), cuerpo)

    def test_git_no_se_sirve(self):
        for ruta in ("/.git/config", "/.git/", "/.git", "/carpeta/.git/config", "/%2egit/config", "/.GIT/config"):
            with self.subTest(ruta):
                estado, _, cuerpo = self.web.pedir(ruta)
                self.assertEqual(estado, 404)
                self.assertNotIn(CONFIG_GIT.encode(), cuerpo)

    def test_lo_de_dentro_si_se_sirve(self):
        self.assertEqual(self.web.pedir("/")[2], b"portada")
        self.assertEqual(self.web.pedir("/carpeta/")[2], b"dentro de carpeta")
        self.assertEqual(self.web.pedir("/pagina")[2], b"pagina suelta")   # como GitHub Pages: /pagina da pagina.html

    def test_head_no_lleva_cuerpo_y_un_rango_devuelve_un_trozo(self):
        estado, cabeceras, cuerpo = self.web.pedir("/", "HEAD")
        self.assertEqual((estado, cuerpo, cabeceras["content-length"]), (200, b"", "7"))
        estado, cabeceras, cuerpo = self.web.pedir("/", cabeceras={"Range": "bytes=0-2"})
        self.assertEqual((estado, cuerpo, cabeceras["content-range"]), (206, b"por", "bytes 0-2/7"))


class TestPuertos(unittest.TestCase):
    def test_si_el_puerto_esta_ocupado_usa_el_siguiente(self):
        primero = vista_previa.abrir_servidor(RAIZ, 0)
        try:
            ocupado = primero.server_address[1]
            segundo = vista_previa.abrir_servidor(RAIZ, ocupado)
            try:
                self.assertGreater(segundo.server_address[1], ocupado)
            finally:
                segundo.server_close()
        finally:
            primero.server_close()


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class TestEnChromium(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.nav = cls.pw.chromium.launch()
        except Exception as error:  # noqa: BLE001  silencio: sin Chromium instalado la prueba se salta
            cls.pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {error}")
        cls.web = ServidorDePrueba(RAIZ)

    @classmethod
    def tearDownClass(cls):
        cls.web.cerrar()
        cls.nav.close()
        cls.pw.stop()

    def abrir(self, ruta: str):
        pagina = self.nav.new_page(viewport={"width": 1366, "height": 800})
        # Sin red: lo de fuera (servidor de guías, MDN, GoatCounter) falla, como en un equipo sin conexión; la vista previa solo usa lo local.
        pagina.route("**/*", lambda r: r.continue_() if r.request.url.startswith(f"http://localhost:{self.web.puerto}") or
                     r.request.url.startswith(f"http://127.0.0.1:{self.web.puerto}") else r.abort())
        pagina.pedidas = []
        pagina.on("requestfinished", lambda r: pagina.pedidas.append(r.url))
        pagina.goto(f"http://127.0.0.1:{self.web.puerto}{ruta}", wait_until="load")
        return pagina

    def test_portada_y_aprender_se_ven_y_learn_pinta_las_guias_desde_la_copia(self):
        for ruta in ("/", "/es/", "/learn/", "/es/aprender/"):
            with self.subTest(ruta):
                pagina = self.abrir(ruta)
                self.assertTrue(pagina.locator("h1").first.is_visible())
                if "learn" in ruta or "aprender" in ruta:
                    pagina.wait_for_function("document.querySelectorAll('#guias a.guia').length >= 8")
                    self.assertGreaterEqual(pagina.locator("#guias a.guia").count(), 8)
                    esperar_hasta(pagina, lambda p=pagina: any(u.endswith("/learn/guias.json") for u in p.pedidas), "learn.js pide la copia local de las guías")
                    self.assertTrue(any(u.endswith("/learn/guias.json") for u in pagina.pedidas), "learn.js no pidió la copia local de las guías")
                pagina.close()


if __name__ == "__main__":
    unittest.main()
