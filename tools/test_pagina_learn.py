#!/usr/bin/env python3
"""ML-324 (WEB-08): las cuatro páginas «Learn» publicadas (hreflang, canonical, sitemap, 24 guías en el HTML, destacado, estados vacíos,
validación de la lista y marca PENDIENTE-EUSEBIO). Sin red ni navegador.

Uso:  python3 -m pytest tools/test_pagina_learn.py
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_learn  # noqa: E402
import construir_web  # noqa: E402
import guias_web  # noqa: E402
import pendientes_eusebio  # noqa: E402
import actualizar_guias_web  # noqa: E402

PAGINAS = {"en": "learn/index.html", "es": "es/aprender/index.html", "pt": "pt/aprender/index.html", "ja": "ja/learn/index.html"}
URLS = {"en": "https://manalab.es/learn/", "es": "https://manalab.es/es/aprender/", "pt-BR": "https://manalab.es/pt/aprender/", "ja": "https://manalab.es/ja/learn/"}
H1 = {"en": "Learn", "es": "Aprender", "pt": "Aprender", "ja": "学ぶ"}
DEST = {"nombre": "Dana Voss", "linea": "Standard y Pioneer · ES/EN", "enlace": "https://metafy.gg/@dana-voss", "foto": "https://manalab.es/coaches/fotos/dana.webp",
        "frase": "Te enseño <b>Izzet</b> & más", "fondo": "https://manalab.es/coaches/fondos/dana.webp", "academia": "https://metafy.gg/@dana/academy"}


def leer(ruta: str, raiz: Path = RAIZ) -> str:
    return (raiz / ruta).read_text(encoding="utf-8")


def guia(i: int, **extra) -> dict:
    base = {"name": f"Guía {i}", "description": "d", "url": f"https://metafy.gg/guides/g{i}", "cover_url": f"https://cdn.metafy.gg/c{i}.png", "price": None,
            "subscriber_only": True, "authors": [{"name": "Ana"}], "average_rating": 9.1, "review_count": 5, "total_reading_time_minutes": 7, "purchase_count": i}
    base.update(extra)
    return base


def construir_con(guias: list, destacados: list | None = None) -> Path:
    """Construye toda la web en una carpeta temporal con esa lista de guías y esos destacados; devuelve la carpeta de salida."""
    base = Path(tempfile.mkdtemp())
    raiz = base / "repo"
    (raiz / "learn").mkdir(parents=True)
    shutil.copytree(RAIZ / "plantillas", raiz / "plantillas")
    shutil.copy(RAIZ / "version.json", raiz / "version.json")
    contenido = json.loads(leer("contenido.json"))
    if destacados is not None:
        contenido["destacados"] = destacados
    (raiz / "contenido.json").write_text(json.dumps(contenido), encoding="utf-8")
    (raiz / "learn" / "guias.json").write_text(json.dumps({"v": 1, "actualizada": "2026-11-18T12:00:00.000Z", "guias": guias}), encoding="utf-8")
    salida = base / "salida"
    construir_web.construir(raiz, salida)
    return salida


class PaginasPublicadas(unittest.TestCase):
    def test_las_cuatro_paginas_existen_con_hreflang_canonical_y_sitemap(self):
        sitemap = leer("sitemap.xml")
        for idioma, ruta in PAGINAS.items():
            with self.subTest(idioma):
                html = leer(ruta)
                self.assertIn(f'<link href="{URLS["pt-BR" if idioma == "pt" else idioma]}" rel="canonical"/>', html)
                for hl, url in URLS.items():
                    self.assertIn(f'<link href="{url}" hreflang="{hl}" rel="alternate"/>', html)
                self.assertIn(f'<link href="{URLS["en"]}" hreflang="x-default" rel="alternate"/>', html)
                self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)
                self.assertIn(f"<h1>{H1[idioma]}</h1>", html)
        for url in URLS.values():
            self.assertEqual(sitemap.count(f"<loc>{url}</loc>"), 1, url)

    def test_el_html_trae_las_24_primeras_guias_de_la_copia_y_el_paginador(self):
        lista = guias_web.validar_texto(leer("learn/guias.json"))
        primeras = construir_learn.ordenar_compradas(lista["guias"])[:24]
        self.assertGreaterEqual(len(lista["guias"]), 25, "la copia real debe tener más de una página")
        for idioma, ruta in PAGINAS.items():
            with self.subTest(idioma):
                html = leer(ruta)
                self.assertEqual(html.count('<a class="guia" '), 24)
                for g in primeras:
                    self.assertIn(f'href="{construir_learn._esc(construir_web.url_con_utm(g["url"]))}"', html)
                self.assertIn('data-p="2"', html)
                self.assertIn(f'data-p="{-(-len(lista["guias"]) // 24)}"', html)

    def test_la_copia_real_cumple_las_reglas_y_pasa_por_el_validador_sin_perder_nada(self):
        texto = leer("learn/guias.json")
        lista = guias_web.validar_texto(texto)
        self.assertEqual(guias_web.serializar(lista), texto, "learn/guias.json debe ser lo que escribe actualizar_guias_web.py")
        self.assertLessEqual(len(texto.encode()), guias_web.MAX_BYTES)

    def test_no_hay_nota_bajo_el_paginador_en_las_cuatro_paginas_y_sin_marcas_pendientes(self):
        """ML-333: la nota de Metafy bajo el paginador se quitó (dato del dueño, 18/11): ni el elemento ni su CSS, y sin marca pendiente."""
        hallazgos = pendientes_eusebio.buscar()
        for idioma, ruta in PAGINAS.items():
            with self.subTest(idioma):
                html = leer(ruta)
                self.assertNotIn("PENDIENTE-EUSEBIO", html)
                self.assertNotIn("ap-nota", html)
                self.assertFalse(any(h.startswith(ruta + ":") for h in hallazgos), ruta)
        self.assertNotIn("ap-nota", leer("plantillas/css_learn.tpl"))
        self.assertEqual(len([h for h in hallazgos if h.startswith("plantillas/paginas/") and "/aprender/" in h or "plantillas/paginas/learn/" in h
                              or "plantillas/paginas/ja/learn/" in h]), 0)

    def test_el_detector_encuentra_la_marca_en_una_raiz_cualquiera_y_no_salta_sin_ella(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            (raiz / "plantillas").mkdir()
            (raiz / "plantillas" / "a.pagina").write_text("uno\n<!-- PENDIENTE-EUSEBIO: x -->\n", encoding="utf-8")
            (raiz / "x.html").write_text("limpio", encoding="utf-8")
            self.assertEqual(pendientes_eusebio.buscar(raiz), ["plantillas/a.pagina:2"])
            (raiz / "plantillas" / "a.pagina").write_text("limpio", encoding="utf-8")
            self.assertEqual(pendientes_eusebio.buscar(raiz), [])

    @unittest.skipUnless(__import__("os").environ.get("MANALAB_PUBLICAR") == "1", "solo antes de publicar: MANALAB_PUBLICAR=1")
    def test_para_publicar_no_queda_ningun_texto_pendiente_de_eusebio(self):
        self.assertEqual(pendientes_eusebio.buscar(), [])

    def test_solo_el_script_de_mdn_es_de_otro_dominio(self):
        """ML-325 (WEB-09): Learn lleva el script de MDN (y el suyo, huecos_mdn.js) y nada más de fuera; los huecos se prueban en test_huecos_mdn.py."""
        for idioma, ruta in PAGINAS.items():
            html = leer(ruta)
            with self.subTest(idioma):
                self.assertEqual(sorted(re.findall(r'<script[^>]*src="([^"]+)"', html)),
                                 ["//gc.zgo.at/count.js", "/descarga.js", "/huecos_mdn.js", "/learn/cifras.js", "/learn/learn.js", "https://mdn.metafy.gg/embed.js"])

    def test_el_cierre_ofrece_la_descarga_con_el_panel_de_siempre(self):
        for idioma, ruta in PAGINAS.items():
            with self.subTest(idioma):
                html = leer(ruta)
                self.assertIn('id="descargar"', html)
                self.assertIn('id="enlace-descarga"', html)
                self.assertIn('<template id="bloque-movil">', html)
                self.assertIn(f"descarga-learn-{idioma}", html)


class ConstruccionConDatos(unittest.TestCase):
    def test_sin_destacados_no_hay_banner_ni_barra(self):
        salida = construir_con([guia(1)], destacados=[])
        for ruta in PAGINAS.values():
            html = leer(ruta, salida)
            self.assertNotIn('id="destacado"', html)
            self.assertNotIn("d2barra", html.split("</style>", 1)[1])

    def test_con_destacados_el_html_trae_banner_y_barra_con_enlaces_sponsored_y_todo_escapado(self):
        otro = dict(DEST, nombre="Iker", enlace="https://metafy.gg/@iker", foto="", frase="", fondo="")
        salida = construir_con([guia(1)], destacados=[DEST, otro])
        html = leer("es/aprender/index.html", salida)
        cuerpo = html.split("</style>", 1)[1]
        self.assertEqual(cuerpo.count('class="d2c on"'), 1)
        self.assertEqual(cuerpo.count('class="d2c"'), 1, "el segundo creador va en la misma celda, inerte")
        self.assertIn('class="d2c" inert aria-hidden="true"', cuerpo)
        self.assertIn('aria-label="1 / 2"', cuerpo)
        self.assertIn('id="d2barra"', cuerpo)
        self.assertRegex(cuerpo, r'<div class="d2barra"[^>]* inert aria-hidden="true"')
        self.assertIn("Te enseño &lt;b&gt;Izzet&lt;/b&gt; &amp; más", cuerpo)
        self.assertNotIn("<b>Izzet</b>", cuerpo)
        for enlace in re.findall(r'<a class="d2(?:cta|cas)"[^>]*>', cuerpo):
            self.assertIn('rel="sponsored noopener"', enlace)
        self.assertIn('src="https://manalab.es/coaches/fondos/dana.webp"', cuerpo)
        self.assertEqual(cuerpo.count('class="d2fondo"'), 1)

    def test_frase_o_fondo_malos_no_tiran_el_destacado(self):
        malo = dict(DEST, frase="x" * 141, fondo="https://evil.com/f.webp", foto="http://manalab.es/f.webp")
        lista = guias_web.validar_destacados([malo, dict(DEST, enlace="https://evil.com/x"), "no", dict(DEST, academia="https://evil.com/a")])
        self.assertEqual(len(lista), 1)
        self.assertEqual((lista[0]["frase"], lista[0]["fondo"], lista[0]["foto"]), ("", "", ""))
        self.assertEqual(lista[0]["nombre"], "Dana Voss")

    def test_sin_guias_la_pagina_lo_dice_y_ofrece_la_descarga(self):
        salida = construir_con([])
        for idioma, ruta in PAGINAS.items():
            html = leer(ruta, salida)
            with self.subTest(idioma):
                self.assertIn(construir_learn.TEXTOS[idioma]["vacio"][0], html)
                caja = html[html.index('<div class="ap-caja">'):]
                self.assertIn('href="#descargar"', caja[:600])
                self.assertIn('id="ap-barra" hidden', html)
                self.assertNotIn('<nav class="ap-pag"', html)

    def test_una_guia_con_enlace_o_portada_malos_no_sale_o_sale_sin_portada(self):
        malas = [guia(1, url="https://evil.com/g"), guia(2, cover_url="https://evil.com/c.png"), guia(3, url="http://metafy.gg/g"),
                 guia(4, cover_url="https://metafy.gg.evil.com/c.png"), guia(5, name="x" * 141), guia(6)]
        salida = construir_con(malas)
        html = leer("learn/index.html", salida)
        self.assertEqual(html.count('<a class="guia" '), 3)   # la 2 y la 4 (sin portada) y la 6
        self.assertNotIn("evil.com", html)
        self.assertIn("https://metafy.gg/guides/g2", html)
        self.assertIn("https://cdn.metafy.gg/c6.png", html)
        self.assertNotIn("https://cdn.metafy.gg/c2.png", html)
        self.assertIn("https://metafy.gg/guides/g4", html)
        self.assertNotIn("/guides/g5", html)

    def test_orden_por_defecto_mas_compradas_y_un_titulo_hostil_se_escapa(self):
        lista = [guia(1, name="<img src=x onerror=alert(1)>"), guia(2, purchase_count=50)]
        html = leer("learn/index.html", construir_con(lista))
        self.assertLess(html.index("/guides/g2"), html.index("/guides/g1"))
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)

    def test_construir_no_toca_la_red(self):
        import socket
        original = socket.socket.connect
        socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError("construir_web accedió a la red"))
        try:
            construir_con([guia(1)])
        finally:
            socket.socket.connect = original


class ActualizarGuias(unittest.TestCase):
    def test_valida_antes_de_guardar_y_no_pisa_la_copia_buena_con_una_vacia(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            buena = json.dumps({"v": 1, "actualizada": "2026-11-18T12:00:00Z", "guias": [guia(1), guia(2, url="https://evil.com/x")]})
            self.assertTrue(actualizar_guias_web.actualizar(raiz, buena).startswith("guardada"))
            guardada = guias_web.validar_texto((raiz / "learn" / "guias.json").read_text(encoding="utf-8"))
            self.assertEqual([g["name"] for g in guardada["guias"]], ["Guía 1"])
            self.assertEqual(actualizar_guias_web.actualizar(raiz, buena.replace("12:00:00Z", "13:00:00Z")), "sin_cambios")
            for mala in (json.dumps({"v": 1, "actualizada": "2026-11-18T12:00:00Z", "guias": [guia(1, url="https://evil.com/x")]}),
                         json.dumps({"v": 2, "actualizada": "2026-11-18T12:00:00Z", "guias": [guia(1)]}), "no es json"):
                with self.assertRaises(ValueError):
                    actualizar_guias_web.actualizar(raiz, mala)
            self.assertEqual(len(guias_web.validar_texto((raiz / "learn" / "guias.json").read_text(encoding="utf-8"))["guias"]), 1)

    def test_solo_acepta_direcciones_https(self):
        with self.assertRaises(ValueError):
            actualizar_guias_web.descargar("http://registro-ia.eusebiog76.workers.dev/guias.json")


if __name__ == "__main__":
    unittest.main()
