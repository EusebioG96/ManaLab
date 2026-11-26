"""ML-376: los enlaces «pide una prueba gratis por correo» de la web llevan el asunto exacto
que busca el script de Gmail (servidor_ia/gmail/Codigo.gs): sin él, el correo nunca se contesta solo."""
import re
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_web

RAIZ = construir_web.RAIZ
ASUNTO_ES = "Prueba gratis de la IA"   # igual que ASUNTO_ES de Codigo.gs y el mailto de la app
ASUNTO_EN = "Free AI trial"            # igual que ASUNTO_EN de Codigo.gs y el mailto de la app
CONTACTO = ("privacy/", "safety/", "es/seguridad/")   # páginas cuyo correo es de contacto, no de prueba
ENLACE = re.compile(r'href="mailto:manalab\.app@gmail\.com([^"]*)"')


class TestCorreoPruebaGratis(unittest.TestCase):
    def test_cada_enlace_de_prueba_lleva_el_asunto_del_script(self):
        vistos = 0
        for pagina in construir_web.listar_paginas(RAIZ):
            ruta = pagina.as_posix()
            if ruta.startswith(CONTACTO):
                continue
            esperado = ASUNTO_ES if ruta.startswith("es/") else ASUNTO_EN
            for resto in ENLACE.findall((RAIZ / pagina).read_text(encoding="utf-8")):
                vistos += 1
                with self.subTest(pagina=ruta):
                    asunto = re.search(r"[?&]subject=([^&]*)", resto.replace("&amp;", "&"))
                    self.assertIsNotNone(asunto, "falta el asunto")
                    self.assertEqual(unquote(asunto.group(1)), esperado)
        self.assertGreaterEqual(vistos, 20)

    def test_los_correos_de_contacto_no_llevan_asunto_de_prueba(self):
        for ruta in ("privacy/index.html", "safety/index.html", "es/seguridad/index.html"):
            with self.subTest(pagina=ruta):
                self.assertNotIn("subject=", "".join(ENLACE.findall((RAIZ / ruta).read_text(encoding="utf-8"))))


if __name__ == "__main__":
    unittest.main()
