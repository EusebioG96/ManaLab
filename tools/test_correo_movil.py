#!/usr/bin/env python3
"""ML-295 (RED-10): «Envíate el enlace de descarga por correo» en la primera pantalla de las portadas en teléfono. Sin red.

Con ``URL_ENLACE_CORREO`` vacía (hasta que Eusebio despliegue el servidor) no se pinta el campo y queda el bloque de siempre; con valor,
el campo va dentro de ``<template id="bloque-movil">`` (solo lo monta descarga.js en teléfono) en las cuatro portadas, con los textos W5.
La dirección de correo nunca llega a GoatCounter ni a una URL: se comprueba sobre descarga.js.

Uso:  python3 tools/test_correo_movil.py
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_web  # noqa: E402

RAIZ = construir_web.RAIZ
URL = "https://registro-ia.eusebiog76.workers.dev/enlace-descarga"
PORTADAS = {"en": "index.html", "es": "es/index.html", "pt": "pt/index.html", "ja": "ja/index.html"}
W5 = {  # textos de Eusebio: no se cambian
    "en": ("ManaLab runs on your PC. Email yourself the download link.", "Send", "One email, nothing else. We don&#x27;t keep your address."),
    "es": ("ManaLab funciona en tu PC. Envíate el enlace de descarga por correo.", "Enviar", "Un solo correo y nada más. No guardamos tu dirección."),
}
EVENTO = re.compile(r"correo-movil-portada-(en|es|pt|ja)")


def _generar(url: str) -> Path:
    destino = Path(tempfile.mkdtemp(prefix="correo-movil-"))
    with mock.patch.object(construir_web, "URL_ENLACE_CORREO", url):
        construir_web.construir(RAIZ, destino)
    return destino


def _plantilla(html: str) -> str:
    """El contenido de <template id="bloque-movil"> (lo único que se pinta en teléfono)."""
    inicio = html.index('<template id="bloque-movil">')
    return html[inicio:html.index("</template>", inicio)]


class TestCorreoMovil(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vacia = _generar("")
        cls.con_url = _generar(URL)

    def test_la_constante_publicada_es_la_del_servidor_desplegado(self):
        self.assertEqual(construir_web.URL_ENLACE_CORREO, URL)   # ML-304: el servidor ya está desplegado

    def test_lo_publicado_en_las_portadas_es_lo_que_genera_la_constante(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                self.assertEqual((self.con_url / ruta).read_bytes(), (RAIZ / ruta).read_bytes())   # web regenerada tras poner la URL
                self.assertIn('data-correo-url="%s"' % URL, (RAIZ / ruta).read_text(encoding="utf-8"))

    def test_con_la_constante_vacia_no_hay_campo_y_queda_el_bloque_de_hoy(self):
        for idioma, ruta in PORTADAS.items():
            for base in (self.vacia,):  # el generado con la constante vacía (lo publicado lleva ya la URL: ML-304)
                with self.subTest(idioma=idioma):
                    html = (base / ruta).read_text(encoding="utf-8")
                    self.assertNotIn("<form", _plantilla(html))
                    self.assertNotIn('class="movil-correo', html.replace("movil-correo-", "").replace(".movil-correo", ""))
                    self.assertNotIn("data-correo-url", html)
                    self.assertIn('<p class="movil-txt">', _plantilla(html))
                    self.assertNotIn("{{", html)

    def test_con_valor_el_campo_esta_en_las_cuatro_portadas_dentro_de_la_plantilla_movil(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = (self.con_url / ruta).read_text(encoding="utf-8")
                self.assertEqual(html.count("<form"), html.count("</form>"))
                self.assertEqual(html.count('data-correo-url="%s"' % URL), 1)
                self.assertIn('data-correo-url="%s"' % URL, _plantilla(html))   # solo en teléfono: fuera de la plantilla no hay nada
                self.assertIn('type="email"', _plantilla(html))
                self.assertIn('data-idioma="%s"' % idioma, _plantilla(html))
                self.assertNotIn("{{", html)

    def test_con_valor_no_hay_boton_de_compartir_en_el_bloque_movil_y_si_campo_y_descarga(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                html = (self.con_url / ruta).read_text(encoding="utf-8")
                bloque = _plantilla(html)
                self.assertNotIn("data-compartir", bloque)
                self.assertNotIn("compartir-movil", html)          # ni el evento queda huérfano en la portada
                self.assertIn("data-correo-url", bloque)
                self.assertIn('type="email"', bloque)
                self.assertIn('class="movil-zip"', bloque)         # «Descargar el ZIP igualmente»
                self.assertIn("data-descarga", bloque[bloque.index('class="movil-zip"'):])
                self.assertEqual(bloque.count("<button"), 1)       # solo el «Enviar» del formulario
                self.assertNotIn("{{", html)

    def test_con_la_constante_vacia_el_boton_de_compartir_sigue_en_las_cuatro_portadas(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                bloque = _plantilla((self.vacia / ruta).read_text(encoding="utf-8"))
                self.assertEqual(bloque.count("data-compartir"), 1)
                self.assertIn("compartir-movil-portada-%s" % idioma, bloque)
                if not construir_web.URL_ENLACE_CORREO:   # lo publicado es la constante vacía
                    self.assertEqual((self.vacia / ruta).read_bytes(), (RAIZ / ruta).read_bytes())   # byte a byte lo publicado

    def test_otras_paginas_con_valor_conservan_su_boton_de_compartir(self):
        for ruta in ("magic-online/index.html", "coaches/index.html", "es/overlay/index.html"):
            with self.subTest(ruta=ruta):
                self.assertIn("data-compartir", (self.con_url / ruta).read_text(encoding="utf-8"))

    def test_descarga_js_tolera_un_bloque_sin_boton_de_compartir(self):
        self.assertIn("if (boton) boton.addEventListener", (RAIZ / "descarga.js").read_text(encoding="utf-8"))

    def test_los_textos_w5_en_ingles_y_espanol_y_hay_los_cuatro_idiomas_completos(self):
        for idioma, (txt, boton, nota) in W5.items():
            html = _plantilla((self.con_url / PORTADAS[idioma]).read_text(encoding="utf-8"))
            with self.subTest(idioma=idioma):
                self.assertIn(">%s</p>" % txt, html)
                self.assertIn("<span>%s</span></button>" % boton, html)
                self.assertIn(">%s</p>" % nota, html)
        for idioma, textos in construir_web.TEXTOS_CORREO.items():
            html = _plantilla((self.con_url / PORTADAS[idioma]).read_text(encoding="utf-8"))
            for clave in ("txt", "boton", "nota", "ok", "correo", "limite", "red"):
                with self.subTest(idioma=idioma, clave=clave):
                    self.assertTrue(textos[clave].strip())
                    self.assertIn(construir_web.html.escape(textos[clave], quote=True), html)   # incluidos éxito y los tres errores

    def test_el_evento_sigue_el_patron_y_no_lleva_direccion(self):
        for idioma, ruta in PORTADAS.items():
            html = (self.con_url / ruta).read_text(encoding="utf-8")
            with self.subTest(idioma=idioma):
                self.assertIn('data-evento="correo-movil-portada-%s"' % idioma, html)
                self.assertRegex(re.search(r'data-evento="([^"]+)"', html).group(1), r"^%s$" % EVENTO.pattern)

    def test_otras_paginas_no_llevan_el_campo(self):
        for ruta in ("magic-online/index.html", "overlay/index.html", "coaches/index.html", "es/overlay/index.html", "404.html"):
            with self.subTest(ruta=ruta):
                self.assertNotIn("data-correo-url", (self.con_url / ruta).read_text(encoding="utf-8"))

    def test_una_direccion_no_https_o_con_comillas_se_rechaza(self):
        for mala in ("http://x.dev/enlace", 'https://x.dev/"><script>', "https://x.dev/a b"):
            with self.subTest(url=mala), self.assertRaises(ValueError):
                construir_web.bloque_correo("en", mala, "x")

    def test_descarga_js_nunca_manda_la_direccion_a_goatcounter_ni_a_una_url(self):
        js = (RAIZ / "descarga.js").read_text(encoding="utf-8")
        sin_textos = [re.sub(r'"[^"]*"|//.*$', '""', linea) for linea in js.splitlines()]   # sin literales de texto ni comentarios
        for linea, codigo in zip(js.splitlines(), sin_textos):
            if "contar(" in linea and "function contar" not in linea:
                with self.subTest(linea=linea.strip()):
                    self.assertNotRegex(codigo[codigo.index("contar("):], r"\bcorreo\b|campo")   # solo nombres de evento (data-evento / data-titulo)
        # la dirección solo se usa para validarla y para el cuerpo del POST
        for numero, (linea, codigo) in enumerate(zip(js.splitlines(), sin_textos), 1):
            if re.search(r"\bcorreo\b", codigo):
                with self.subTest(linea=numero):
                    self.assertRegex(linea, r"var correo = campo\.value\.trim|CORREO_VALIDO\.test\(correo\)|JSON\.stringify\(\{ correo: correo|correo\.length")
        self.assertEqual(len(re.findall(r"fetch\(", js)), 2)                 # version.json y el POST
        self.assertIn('fetch(f.getAttribute("data-correo-url"), { method: "POST"', js)
        self.assertNotIn("goatcounter.count({ event: true, path: correo", js)

    def test_privacidad_cuenta_el_envio_por_correo_en_espanol_e_ingles(self):
        html = (RAIZ / "privacy" / "index.html").read_text(encoding="utf-8")
        for idioma, fecha, frases in (("es", "16 de noviembre de 2026", ("enlace de descarga por correo", "no se guarda", "huella anónima")),
                                      ("en", "16 November 2026", ("download link by email", "is not stored", "anonymous fingerprint"))):
            with self.subTest(idioma=idioma):
                bloque = html[html.index(f'<section lang="{idioma}"'):]
                bloque = bloque[:bloque.index("</section>")]
                self.assertIn(fecha, bloque)
                for frase in frases:
                    self.assertIn(frase, bloque)
                self.assertIn("Resend", bloque[bloque.index(frases[0]):])


if __name__ == "__main__":
    unittest.main()
