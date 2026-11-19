#!/usr/bin/env python3
"""ML-342 (SEO-08): ningún título de sección (H2) de las cuatro portadas ocupa tres líneas o más, a 390 y a 1366 px, en un navegador real
(Chromium con Playwright; se salta si no están). Mide lo visible: el alto del contenido del H2 dividido entre su ``line-height`` calculado.
Los H2 ocultos no cuentan, así que la prueba exige además que se midan los H2 que importan (los tres títulos nuevos de cada portada).

Uso:  python3 -m pytest tools/test_portadas_h2_navegador.py
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
from test_huecos_mdn_navegador import Servidor, sitio

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

ANCHOS = (390, 1366)
MAX_LINEAS = 2  # un título de sección ocupa como mucho dos líneas (SEO-08)
MIN_H2_VISIBLES = 7  # la portada más corta tiene 7 H2 visibles; menos significa que la medida no está viendo la página
# Los tres títulos nuevos por portada (tal cual los dio Eusebio, 20/11/2026): descarga, seguridad, Arena y Magic Online
TITULOS_NUEVOS = {
    "index.html": ("Download the tracker in three steps", "Is ManaLab safe? What it reads on your PC",
                   "A free tracker for Arena and Magic Online, side by side"),
    "es/index.html": ("Descarga el tracker en tres pasos", "¿Es seguro? Qué lee ManaLab en tu PC",
                      "Tracker gratis para Arena y Magic Online, a la vez"),
    "pt/index.html": ("Baixe o tracker em três passos", "É seguro? O que o ManaLab lê no seu PC",
                      "Tracker grátis para Arena e Magic Online, lado a lado"),
    "ja/index.html": ("トラッカーのダウンロードは3ステップ", "安全ですか？ManaLabがPCで読むもの", "アリーナとMagic Onlineに対応した無料トラッカー"),
}
# H2 que YA ocupan tres líneas a 390 px y no son de este encargo (ML-342 no cambia más textos que los tres de la tabla de Eusebio), más el
# nuevo de Arena y Magic Online en inglés, que la regla del encargo manda no tocar y contar en el informe. Es un tope, no un permiso: un H2
# de tres líneas que no esté aquí falla. Quitar una entrada cuando se acorte su texto.
TRES_LINEAS_CONOCIDOS_A_390 = {
    "index.html": ("A free tracker for Arena and Magic Online, side by side", "Everything you'd note down after each match, done for you",
                   "Know what went wrong in every lost game"),
    "es/index.html": ("Todo lo que apuntarías después de cada match, ya apuntado",),
    "pt/index.html": ("Três coisas que você vai olhar depois de cada sessão", "Tudo o que você anotaria depois de cada match, já anotado",
                      "Saiba o que deu errado em cada partida perdida"),
    "ja/index.html": ("負けたゲームで、何が悪かったのかがわかる",),
}
H2_MEDIDOS = """() => { const salida = [];
  document.querySelectorAll('h2').forEach(function (h) {
    if (!h.checkVisibility({ contentVisibilityAuto: true, visibilityProperty: true })) return;
    const e = getComputedStyle(h), caja = h.getBoundingClientRect().height, relleno = parseFloat(e.paddingTop) + parseFloat(e.paddingBottom)
      + parseFloat(e.borderTopWidth) + parseFloat(e.borderBottomWidth);
    let linea = parseFloat(e.lineHeight); if (isNaN(linea)) linea = parseFloat(e.fontSize) * 1.2;  // "normal"
    salida.push({ texto: h.textContent.replace(/\\s+/g, ' ').trim(), lineas: Math.round((caja - relleno) / linea * 100) / 100 }); });
  return salida; }"""


def lineas_de_los_h2(nav, url: str, ancho: int) -> list[dict]:
    """Los H2 visibles de ``url`` a ``ancho`` px, cada uno con su texto y sus líneas (alto del contenido / line-height)."""
    contexto = nav.new_context(viewport={"width": ancho, "height": 844}, is_mobile=ancho < 700, has_touch=ancho < 700)
    try:
        pagina = contexto.new_page()
        pagina.route("**/*", lambda r: r.continue_() if r.request.url.startswith(url.split("/", 3)[0] + "//" + url.split("/")[2]) else r.abort())
        pagina.goto(url, wait_until="load")
        pagina.evaluate("document.fonts.ready")
        return pagina.evaluate(H2_MEDIDOS)
    finally:
        contexto.close()


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class H2DeLasPortadas(unittest.TestCase):
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

    def test_ningun_h2_ocupa_tres_lineas_o_mas(self):
        for portada, nuevos in TITULOS_NUEVOS.items():
            for ancho in ANCHOS:
                with self.subTest(portada=portada, ancho=ancho):
                    medidos = lineas_de_los_h2(self.nav, f"{self.web.url}/{portada}", ancho)
                    self.assertGreaterEqual(len(medidos), MIN_H2_VISIBLES, f"{portada} a {ancho} px: se miden pocos H2 visibles")
                    textos = [m["texto"] for m in medidos]
                    for titulo in nuevos:
                        self.assertIn(titulo, textos, f"{portada}: el H2 nuevo «{titulo}» no está visible")
                    conocidos = TRES_LINEAS_CONOCIDOS_A_390.get(portada, ()) if ancho == 390 else ()
                    largos = [(m["texto"], m["lineas"]) for m in medidos if m["lineas"] > MAX_LINEAS + 0.2 and m["texto"] not in conocidos]
                    self.assertEqual(largos, [], f"{portada} a {ancho} px: H2 de tres líneas o más")

    def test_la_medida_detecta_un_h2_largo(self):
        """Mutación permanente: con un H2 de 200 caracteres a 390 px la medida da más de dos líneas (si no, el test de arriba no mide nada)."""
        larga = self.raiz / "h2-largo.html"
        larga.write_text("<!doctype html><meta charset=utf-8><body style='margin:0'><h2 style='font:28px/1.2 serif'>" + "Título larguísimo " * 12
                         + "</h2></body>", encoding="utf-8")
        medidos = lineas_de_los_h2(self.nav, f"{self.web.url}/h2-largo.html", 390)
        self.assertEqual(len(medidos), 1)
        self.assertGreater(medidos[0]["lineas"], MAX_LINEAS + 0.2)


if __name__ == "__main__":
    unittest.main()
