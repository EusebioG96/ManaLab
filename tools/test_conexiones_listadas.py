#!/usr/bin/env python3
"""Comprueba que la página de seguridad (en: /safety/, es: /es/seguridad/) nombra cada host al que se conecta la app (ML-281, RED-04).

Uso:  python3 tools/test_conexiones_listadas.py
"""
import unittest
from pathlib import Path

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
    "mdn.metafy.gg",            # script del anuncio (lo carga manalab.es/anuncio/)
    "metafy.gg",                # portadas de las guías de Aprender
    "workers.dev",              # servidor de la IA y de los reportes (manalab_ajustes.URL_IA)
)


def leer(idioma: str) -> str:
    return PAGINAS[idioma].read_text(encoding="utf-8")


class TestConexionesListadas(unittest.TestCase):
    def test_cada_host_de_la_app_sale_en_seguridad(self):
        for idioma in PAGINAS:
            seccion = leer(idioma)
            seccion = seccion[seccion.index('id="conexiones"'):seccion.index('id="comprobar"')]
            for host in HOSTS_DE_LA_APP:
                with self.subTest(idioma=idioma, host=host):
                    self.assertIn(host, seccion)

    def test_no_hay_inicio_de_sesion_con_metafy(self):
        for idioma in PAGINAS:
            seccion = leer(idioma).lower()
            with self.subTest(idioma=idioma):
                self.assertNotIn("iniciar sesión con metafy", seccion)
                self.assertNotIn("sign in with metafy", seccion)
                self.assertNotIn("log in with metafy", seccion)


if __name__ == "__main__":
    unittest.main()
