#!/usr/bin/env python3
"""ML-325 (WEB-09): los huecos de anuncio de MDN en el HTML generado. Sin red ni navegador (el alto, la posición real y el cambio de anuncio
se prueban en test_huecos_mdn_navegador.py).

Por cada página generada: cuántos huecos tiene y dónde (ninguno antes del botón de descarga ni dentro de la primera sección, dos como mucho,
el segundo solo en páginas de siete secciones o más y justo antes de las preguntas, ninguno dentro de un párrafo); las páginas sin anuncio
no llevan hueco NI script; el script de MDN va una sola vez, con ``async``, solo en las páginas con hueco.

Uso:  python3 -m pytest tools/test_huecos_mdn.py
"""
import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_mdn  # noqa: E402
import pendientes_eusebio  # noqa: E402

SCRIPT_MDN = "https://mdn.metafy.gg/embed.js"
# Páginas con anuncio y cuántos huecos lleva cada una en el HTML (WEB-09): portadas y coaches 2; Magic Online, overlay, novedades y registro
# detallado 1; Learn 2 (uno dentro de la rejilla, tras la octava guía, y otro tras el paginador).
CON_ANUNCIO = {
    **{f"{p}index.html": 2 for p in ("", "es/", "pt/", "ja/")},
    **{f"{p}coaches/index.html": 2 for p in ("", "es/", "pt/")},
    **{ruta: 1 for ruta in ("magic-online/index.html", "es/magic-online/index.html", "overlay/index.html", "es/overlay/index.html",
                            "novedades/index.html", "es/novedades/index.html", "detailed-logs/index.html", "es/registro-detallado/index.html")},
    **{f"{p}/index.html": 2 for p in ("learn", "es/aprender", "pt/aprender", "ja/learn")},
}
SIN_ANUNCIO = ("404.html", "anuncio/index.html", "privacy/index.html", "safety/index.html", "es/seguridad/index.html", "google8d4ac26b3d7a5735.html")
ETIQUETA = {"en": "Advertisement", "es": "Publicidad", "pt": "Publicidade", "ja": "広告"}
RUTA_LEARN = {"en": "/learn/", "es": "/es/aprender/", "pt": "/pt/aprender/", "ja": "/ja/learn/"}
EXCLUIDOS = {".git", "docs", "plantillas", "tools", "node_modules"}


def idioma_de(ruta: str) -> str:
    return next((i for i in ("es", "pt", "ja") if ruta.startswith(i + "/")), "en")


def paginas_publicadas() -> list[str]:
    return sorted(p.relative_to(RAIZ).as_posix() for p in RAIZ.rglob("*.html") if not EXCLUIDOS & set(p.relative_to(RAIZ).parts))


def leer(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8")


class Estructura(HTMLParser):
    """Recorre una página y apunta, de cada hueco, su posición, sus ancestros y lo que había antes (botón de descarga, secciones)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pila: list[tuple[str, dict]] = []
        self.huecos: list[dict] = []
        self.descargas_vistas = 0
        self.secciones_cerradas = 0
        self.secciones: list[str] = []          # id o clase de cada <section> hija directa de <main>
        self.siguiente_seccion_tras_hueco: dict[int, str] = {}
        self._pendiente: list[int] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "a" and ("data-descarga" in a or a.get("href", "").endswith("#descargar")) and "boton" in a.get("class", ""):
            self.descargas_vistas += 1
        if tag == "section" and any(t == "main" for t, _ in self.pila):
            self.secciones.append(a.get("id") or a.get("class", ""))
            for h in self._pendiente:
                self.siguiente_seccion_tras_hueco[h] = a.get("id", "")
            self._pendiente = []
        if tag == "aside" and "hueco-mdn" in a.get("class", "").split():
            self.huecos.append({"clase": a.get("class", ""), "aria": a.get("aria-label", ""), "ancestros": [t for t, _ in self.pila],
                                "descargas_antes": self.descargas_vistas, "secciones_cerradas": self.secciones_cerradas,
                                "dentro_de_seccion": any(t == "section" for t, _ in self.pila), "secciones_antes": len(self.secciones)})
            self._pendiente.append(len(self.huecos) - 1)
        if tag not in ("br", "img", "meta", "link", "input", "source", "path", "use"):
            self.pila.append((tag, a))

    def handle_endtag(self, tag):
        for i in range(len(self.pila) - 1, -1, -1):
            if self.pila[i][0] == tag:
                if tag == "section" and any(t == "main" for t, _ in self.pila[:i]):
                    self.secciones_cerradas += 1
                del self.pila[i:]
                return


def estructura(ruta: str) -> Estructura:
    e = Estructura()
    e.feed(leer(ruta))
    return e


class TestTodasLasPaginasEstanDecididas(unittest.TestCase):
    def test_cada_pagina_publicada_esta_en_una_de_las_dos_listas(self):
        """Una página nueva obliga a decidir si lleva anuncio: si no está en ninguna lista, falla."""
        decididas = set(CON_ANUNCIO) | set(SIN_ANUNCIO)
        nuevas = [p for p in paginas_publicadas() if p not in decididas and not p.startswith("guia/")]
        self.assertEqual(nuevas, [], "decide si llevan anuncio (WEB-09) y añádelas a CON_ANUNCIO o a SIN_ANUNCIO")

    def test_el_generador_y_el_test_coinciden_en_que_paginas_no_llevan_anuncio(self):
        for ruta in SIN_ANUNCIO + tuple(f"guia/guia_manalab_{i}.html" for i in ("en", "es", "fr")):
            with self.subTest(ruta):
                self.assertTrue(construir_mdn.sin_anuncio(Path(ruta)) or ruta == "google8d4ac26b3d7a5735.html")
        for ruta in CON_ANUNCIO:
            with self.subTest(ruta):
                self.assertFalse(construir_mdn.sin_anuncio(Path(ruta)))

    def test_nueve_guias(self):
        self.assertEqual(len([p for p in paginas_publicadas() if p.startswith("guia/")]), 9)


class TestPaginasConAnuncio(unittest.TestCase):
    def test_numero_de_huecos(self):
        for ruta, esperados in CON_ANUNCIO.items():
            with self.subTest(ruta):
                self.assertEqual(len(estructura(ruta).huecos), esperados)
                self.assertEqual(leer(ruta).count('class="hueco-mdn'), esperados)

    def test_el_script_de_mdn_esta_una_sola_vez_y_es_async(self):
        for ruta in CON_ANUNCIO:
            with self.subTest(ruta):
                html = leer(ruta)
                self.assertEqual(html.count(SCRIPT_MDN), 1)
                etiquetas = re.findall(r"<script[^>]*mdn\.metafy\.gg[^>]*></script>", html)
                self.assertEqual(len(etiquetas), 1)
                self.assertRegex(etiquetas[0], r"<script async src=")
                self.assertIn('data-mdn-site="mdn_', etiquetas[0])
                self.assertEqual(html.count('src="/huecos_mdn.js"'), 1)
                self.assertRegex(html, r'<script defer src="/huecos_mdn\.js" data-plazo="\d+"></script>')
                self.assertEqual(html.count("</body>"), 1)
                # los scripts van después del último hueco y antes de </body>
                self.assertGreater(html.index(SCRIPT_MDN), html.rindex('class="hueco-mdn'))
                self.assertLess(html.index(SCRIPT_MDN), html.index("</body>"))

    def test_marcado_de_cada_hueco_en_el_idioma_de_la_pagina(self):
        for ruta in CON_ANUNCIO:
            idioma = idioma_de(ruta)
            html = leer(ruta)
            asides = re.findall(r'<aside class="hueco-mdn[^"]*" aria-label="([^"]*)">(.*?)</aside>', html, flags=re.S)
            self.assertEqual(len(asides), CON_ANUNCIO[ruta])
            for etiqueta, cuerpo in asides:
                with self.subTest(ruta):
                    self.assertEqual(etiqueta, ETIQUETA[idioma])
                    self.assertIn(f'<span class="hm-eti" aria-hidden="true">{ETIQUETA[idioma]}</span>', cuerpo)
                    self.assertIn('class="hm-caja" data-mdn="auto" data-mdn-theme="dark"', cuerpo)
                    self.assertIn(f'<a class="hm-casa" href="{RUTA_LEARN[idioma]}">', cuerpo)   # el anuncio de casa lleva a Learn en su idioma

    def test_ninguno_antes_del_boton_de_descarga_ni_dentro_de_la_primera_seccion(self):
        for ruta in CON_ANUNCIO:
            e = estructura(ruta)
            for n, h in enumerate(e.huecos):
                with self.subTest(ruta=ruta, hueco=n):
                    self.assertGreaterEqual(h["descargas_antes"], 1, "hay un hueco antes del primer botón de descarga")
                    self.assertGreaterEqual(h["secciones_antes"], 1)
                    if not h["dentro_de_seccion"]:
                        self.assertGreaterEqual(h["secciones_cerradas"], 1, "hay un hueco dentro de la primera sección")

    def test_ninguno_dentro_de_un_parrafo_ni_fijo(self):
        for ruta in CON_ANUNCIO:
            for n, h in enumerate(estructura(ruta).huecos):
                with self.subTest(ruta=ruta, hueco=n):
                    self.assertNotIn("p", h["ancestros"])
                    self.assertNotIn("details", h["ancestros"])
                    self.assertNotIn("header", h["ancestros"])
                    self.assertNotIn("footer", h["ancestros"])
        css = (RAIZ / "plantillas" / "css_sitio.tpl").read_text(encoding="utf-8")
        reglas = re.findall(r"\.hueco-mdn[^{]*\{([^}]*)\}", css) + re.findall(r"\.hm-caja[^{]*\{([^}]*)\}", css)
        self.assertTrue(reglas)
        for regla in reglas:
            self.assertNotRegex(regla, r"position:\s*(fixed|sticky)")

    def test_segundo_hueco_solo_en_paginas_largas_y_justo_antes_de_las_preguntas(self):
        for ruta in CON_ANUNCIO:
            e = estructura(ruta)
            if Path(ruta).parent.name in ("learn", "aprender"):
                continue   # Learn: el segundo va tras el paginador (test propio abajo)
            with self.subTest(ruta):
                largas = len(e.secciones) - 1 >= 7    # siete secciones o más, sin contar la primera (la cabecera de la página)
                self.assertEqual(len(e.huecos), 2 if largas else 1)
                if largas:
                    self.assertEqual(e.siguiente_seccion_tras_hueco[1], "preguntas")
                    self.assertGreater(e.huecos[1]["secciones_antes"], e.huecos[0]["secciones_antes"])

    def test_learn_un_hueco_tras_la_octava_guia_y_otro_tras_el_paginador(self):
        for ruta in ("learn/index.html", "es/aprender/index.html", "pt/aprender/index.html", "ja/learn/index.html"):
            html = leer(ruta)
            with self.subTest(ruta):
                rejilla = html[html.index('id="guias"'):html.index('<nav', html.index('id="guias"'))]
                tarjetas = [m.start() for m in re.finditer(r'<a class="guia[ "]', rejilla)]
                self.assertEqual(len(tarjetas), 24)
                hueco = rejilla.index('<aside class="hueco-mdn suelto"')
                self.assertEqual(len([t for t in tarjetas if t < hueco]), 8)
                self.assertEqual(len([t for t in tarjetas if t > hueco]), 16)
                paginador = html.index('id="ap-pag"')
                segundo = html.index('<aside class="hueco-mdn"')
                self.assertGreater(segundo, paginador)
                self.assertLess(segundo, html.index('id="descargar"', segundo))   # antes del panel de descarga del final


class TestPaginasSinAnuncio(unittest.TestCase):
    def todas(self):
        return list(SIN_ANUNCIO) + [p for p in paginas_publicadas() if p.startswith("guia/")]

    def test_ni_hueco_ni_script_de_huecos(self):
        for ruta in self.todas():
            with self.subTest(ruta):
                html = leer(ruta)
                # (la hoja de estilos común nombra las clases: se busca el marcado y los scripts, no las palabras sueltas)
                self.assertNotIn('<aside class="hueco-mdn', html)
                self.assertNotIn('class="hm-caja"', html)
                self.assertNotIn("huecos_mdn", html)
                if ruta != "anuncio/index.html":
                    self.assertNotRegex(html, r"<script[^>]*mdn\.metafy\.gg")   # privacidad y seguridad nombran el host en el texto, que es otra cosa
                    self.assertNotIn('data-mdn="', html)

    def test_anuncio_sigue_cargando_el_script_a_su_manera(self):
        html = leer("anuncio/index.html")
        self.assertEqual(html.count(SCRIPT_MDN), 1)
        self.assertIn('data-mdn="leaderboard"', html)
        self.assertIn('data-mdn-fallback-scope="same_game"', html)

    def test_la_construccion_se_niega_a_poner_un_hueco_donde_no_va(self):
        for ruta in ("privacy/index.html", "safety/index.html", "es/seguridad/index.html", "404.html", "guia/guia_manalab_es.html", "anuncio/index.html"):
            with self.subTest(ruta):
                with self.assertRaises(ValueError):
                    construir_mdn.aplicar_mdn("<body>{{HUECO_MDN}}</body>", Path(ruta), "en")


class TestTextosPendientesDePrivacidadYSeguridad(unittest.TestCase):
    """El script de MDN hace que Metafy reciba la visita (IP y navegador). Esos textos los escribe Eusebio: aquí solo está el sitio, oculto y marcado."""
    SITIOS = {"privacy/index.html": 2, "safety/index.html": 1, "es/seguridad/index.html": 1}   # privacidad lleva el texto en español y en inglés

    def test_cada_pagina_tiene_su_marca_y_su_parrafo_oculto_y_vacio(self):
        for ruta, esperadas in self.SITIOS.items():
            with self.subTest(ruta):
                html = leer(ruta)
                self.assertEqual(html.count("<!-- PENDIENTE-EUSEBIO (ML-325"), esperadas)
                self.assertEqual(html.count("<p data-pendiente-eusebio hidden></p>"), esperadas)

    def test_el_detector_las_lista_y_la_comprobacion_de_publicar_falla_mientras_falten(self):
        hallazgos = pendientes_eusebio.buscar()
        for ruta, esperadas in self.SITIOS.items():
            with self.subTest(ruta):
                self.assertEqual(len([h for h in hallazgos if h.startswith(ruta + ":")]), esperadas)
                plantilla = "plantillas/paginas/" + ruta.replace("index.html", "index.pagina")
                self.assertEqual(len([h for h in hallazgos if h.startswith(plantilla + ":")]), esperadas)
        self.assertNotEqual(hallazgos, [], "MANALAB_PUBLICAR=1 debe fallar mientras Eusebio no escriba esos textos")


class TestAltoReservado(unittest.TestCase):
    """El alto de cada hueco está escrito en la hoja de estilos (así no salta al llegar el anuncio); el navegador lo mide en el otro archivo."""
    CSS = (RAIZ / "plantillas" / "css_sitio.tpl").read_text(encoding="utf-8")

    def test_rectangle_300x250_por_defecto_y_leaderboard_728x90_si_el_hueco_mide_728_o_mas(self):
        self.assertRegex(self.CSS, r"\.hm-caja \{[^}]*width: 300px; height: 250px;")
        self.assertRegex(self.CSS, r"@container \(min-width: 728px\) \{ \.hm-caja \{ width: 728px; height: 90px; \} \}")

    def test_etiqueta_en_geist_mono_de_11_px(self):
        self.assertRegex(self.CSS, r"\.hm-eti \{ font: 500 11px/1 var\(--f-mono\);")

    def test_el_anuncio_de_casa_solo_se_ve_con_mdn_vacio_plazo_agotado_o_sin_javascript(self):
        self.assertRegex(self.CSS, r"\.hm-casa \{[^}]*visibility: hidden;")
        self.assertIn('.hm-caja[data-mdn-state="empty"] .hm-casa, .hueco-mdn[data-propio] .hm-casa { visibility: visible; }', self.CSS)
        self.assertIn("@media (scripting: none) { .hm-casa { visibility: visible; } }", self.CSS)

    def test_con_reducir_movimiento_el_hueco_no_se_anima(self):
        self.assertIn("@media (prefers-reduced-motion: reduce) { .hueco-mdn, .hueco-mdn * { animation: none !important; transition: none !important; } }", self.CSS)


class TestGenerador(unittest.TestCase):
    def test_sin_marcas_no_cambia_nada(self):
        pagina = "<html><body><main>x</main></body></html>"
        self.assertEqual(construir_mdn.aplicar_mdn(pagina, Path("index.html"), "en"), pagina)

    def test_tres_huecos_no_se_construyen(self):
        with self.assertRaises(ValueError):
            construir_mdn.aplicar_mdn("<body>{{HUECO_MDN}}{{HUECO_MDN}}{{HUECO_MDN}}</body>", Path("index.html"), "en")

    def test_un_hueco_lleva_los_dos_scripts_una_sola_vez(self):
        salida = construir_mdn.aplicar_mdn("<body>\n{{HUECO_MDN}}\n{{HUECO_MDN}}\n</body>", Path("index.html"), "es")
        self.assertEqual(salida.count("embed.js"), 1)
        self.assertEqual(salida.count("huecos_mdn.js"), 1)
        self.assertEqual(salida.count("<aside"), 2)
        self.assertNotIn("{{", salida)

    def test_textos_de_los_cuatro_idiomas(self):
        self.assertEqual({i: t["pub"] for i, t in construir_mdn.TEXTOS.items()}, ETIQUETA)
        self.assertEqual({i: t["ruta"] for i, t in construir_mdn.TEXTOS.items()}, RUTA_LEARN)

    def test_el_plazo_es_una_constante_con_nombre_y_llega_al_script(self):
        self.assertIn(f'data-plazo="{construir_mdn.PLAZO_MDN_MS}"', construir_mdn.html_scripts())
        self.assertGreater(construir_mdn.PLAZO_MDN_MS, 4000)   # MDN espera hasta 4 s a su servidor: antes no se le puede dar por vencido


if __name__ == "__main__":
    unittest.main()
