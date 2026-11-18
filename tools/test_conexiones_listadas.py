#!/usr/bin/env python3
"""Comprueba que la página de seguridad (en: /safety/, es: /es/seguridad/) nombra cada host al que se conecta la app (ML-281, RED-04).

Uso:  python3 tools/test_conexiones_listadas.py
"""
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = {"en": RAIZ / "safety" / "index.html", "es": RAIZ / "es" / "seguridad" / "index.html"}

# Hosts de la app. Salen del inventario de salidas a la red de la app 3.0 (urlopen, fetch, iframe, <img src> de fuera) y hay que
# MANTENERLA: si la app habla con un host nuevo, se añade aquí y a la página de seguridad en inglés y en español (y a privacidad).
HOSTS_DE_LA_APP = (
    "api.github.com",           # versión nueva (manalab_actualizar.URL_ULTIMA)
    "github.com",               # descarga del ZIP al pulsar «Actualizar ahora»
    "raw.githubusercontent.com",  # listas del meta (manalab_ajustes.URL_META)
    "api.scryfall.com",         # nombres de cartas, overlay e imágenes
    "cards.scryfall.io",        # imágenes de las cartas (las direcciones llegan en la respuesta de Scryfall)
    "manalab.es",               # version.json, contenido.json, anuncio/, fotos de los creadores
    "mdn.metafy.gg",            # script del anuncio (lo carga manalab.es/anuncio/ y, desde ML-325, las páginas de la web con hueco de anuncio)
    "metafy.gg",                # portadas de las guías de Aprender
    "workers.dev",              # servidor de la IA y de los reportes (manalab_ajustes.URL_IA)
)


# Hosts de los scripts que cargan las páginas de la web (no la app). Un script de otro host obliga a revisar privacidad y seguridad (ML-325, WEB-09).
HOSTS_DE_SCRIPTS_DE_LA_WEB = {"mdn.metafy.gg", "gc.zgo.at"}   # anuncios de MDN (Metafy) y estadísticas de visitas (GoatCounter)
PRIVACIDAD = RAIZ / "privacy" / "index.html"


def leer(idioma: str) -> str:
    return PAGINAS[idioma].read_text(encoding="utf-8")


def leer_privacidad() -> str:
    return PRIVACIDAD.read_text(encoding="utf-8")


class TestConexionesListadas(unittest.TestCase):
    def test_cada_host_de_la_app_sale_en_seguridad(self):
        for idioma in PAGINAS:
            seccion = leer(idioma)
            seccion = seccion[seccion.index('id="conexiones"'):seccion.index('id="comprobar"')]
            for host in HOSTS_DE_LA_APP:
                with self.subTest(idioma=idioma, host=host):
                    self.assertIn(host, seccion)

    def test_los_scripts_de_fuera_de_la_web_son_solo_los_listados(self):
        vistos = set()
        for ruta in RAIZ.rglob("*.html"):
            if {".git", "docs", "plantillas", "tools"} & set(ruta.relative_to(RAIZ).parts):
                continue
            for fuente in re.findall(r'<script[^>]*\ssrc="((?:https?:)?//[^"]+)"', ruta.read_text(encoding="utf-8")):
                vistos.add(urlparse(fuente if not fuente.startswith("//") else "https:" + fuente).hostname)
        self.assertEqual(vistos, HOSTS_DE_SCRIPTS_DE_LA_WEB)

    def test_el_host_de_mdn_se_nombra_en_privacidad_y_en_seguridad_en_los_dos_idiomas(self):
        self.assertGreaterEqual(leer_privacidad().count("mdn.metafy.gg"), 2)   # una vez por idioma como mínimo; el texto de los anuncios de la web lo escribe Eusebio
        for idioma in PAGINAS:
            self.assertIn("mdn.metafy.gg", leer(idioma))

    def test_las_cifras_de_los_destacados_se_listan_en_seguridad_y_privacidad(self):
        """ML-333: la app y la web envían a workers.dev las cifras de los creadores destacados; lo dicen seguridad (es/en) y privacidad (es/en)."""
        frases = {"en": "send a ManaLab server (<code>workers.dev</code>), at most once an hour, the figures of the featured creators",
                  "es": "a un servidor de ManaLab (<code>workers.dev</code>), como mucho una vez por hora, las cifras de los creadores destacados"}
        for idioma, frase in frases.items():
            seccion = leer(idioma)
            seccion = seccion[seccion.index('id="conexiones"'):seccion.index('id="comprobar"')]
            with self.subTest(idioma=idioma):
                self.assertIn(frase, seccion)
        privacidad = leer_privacidad()
        self.assertIn("<strong>Cifras de los creadores destacados:</strong>", privacidad)
        self.assertIn("<strong>Featured creator figures:</strong>", privacidad)
        self.assertIn("el servidor no guarda tu IP", privacidad)
        self.assertIn("the server does not store your IP", privacidad)

    def test_no_hay_inicio_de_sesion_con_metafy(self):
        for idioma in PAGINAS:
            seccion = leer(idioma).lower()
            with self.subTest(idioma=idioma):
                self.assertNotIn("iniciar sesión con metafy", seccion)
                self.assertNotIn("sign in with metafy", seccion)
                self.assertNotIn("log in with metafy", seccion)


if __name__ == "__main__":
    unittest.main()
