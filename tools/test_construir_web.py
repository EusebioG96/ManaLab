#!/usr/bin/env python3
"""ML-197: los .html del repositorio son exactamente lo que generan las plantillas. Sin red.

Falla si alguien edita un .html a mano sin cambiar su fuente, si se cambia una plantilla sin regenerar,
o si aparece un .html que no sale del generador.

Uso:  python3 tools/test_construir_web.py   (para arreglarlo: python3 tools/construir_web.py)
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_web  # noqa: E402

RAIZ = construir_web.RAIZ
PIE_ES = "pie_es"  # plantilla del pie en español, con el enlace de Privacidad
ENLACE_PRIVACIDAD = '<a href="/privacy/">Privacidad</a>'


def _html_del_repositorio() -> set[Path]:
    """Todos los .html publicados (fuera de .git)."""
    return {p.relative_to(RAIZ) for p in RAIZ.rglob("*.html") if ".git" not in p.parts}


class TestWebGeneradaDesdePlantillas(unittest.TestCase):
    def test_lo_generado_coincide_byte_a_byte_con_el_repositorio(self):
        with tempfile.TemporaryDirectory() as temporal:
            construir_web.construir(RAIZ, Path(temporal))
            self.assertEqual([], construir_web.paginas_distintas(RAIZ, Path(temporal)),
                             "regenera con: python3 tools/construir_web.py")

    def test_todo_html_del_repositorio_sale_del_generador(self):
        generadas = set(construir_web.listar_paginas(RAIZ))
        self.assertGreater(len(generadas), 25)
        self.assertEqual(set(), _html_del_repositorio() - generadas)

    def test_cambiar_una_plantilla_sin_regenerar_se_detecta(self):
        with tempfile.TemporaryDirectory() as temporal:
            copia = Path(temporal) / "repo"
            shutil.copytree(RAIZ / construir_web.CARPETA_PLANTILLAS, copia / construir_web.CARPETA_PLANTILLAS)
            shutil.copy(RAIZ / construir_web.ARCHIVO_VERSION, copia / construir_web.ARCHIVO_VERSION)
            plantilla = copia / construir_web.CARPETA_PLANTILLAS / (PIE_ES + ".tpl")
            texto = plantilla.read_text(encoding="utf-8")
            self.assertIn(ENLACE_PRIVACIDAD, texto)
            plantilla.write_text(texto.replace(ENLACE_PRIVACIDAD, '<a href="/privacy/?x">Privacidad</a>'), encoding="utf-8")
            salida = Path(temporal) / "salida"
            construir_web.construir(copia, salida)
            distintas = construir_web.paginas_distintas(RAIZ, salida)
            self.assertIn(Path("es/index.html"), distintas)
            self.assertIn(Path("es/seguridad/index.html"), distintas)
            self.assertNotIn(Path("index.html"), distintas)

    def test_no_quedan_plantillas_ni_variantes_sin_usar(self):
        carpeta = RAIZ / construir_web.CARPETA_PLANTILLAS
        fuentes = "".join(p.read_text(encoding="utf-8") for p in (carpeta / construir_web.CARPETA_PAGINAS).rglob("*.pagina"))
        for plantilla in carpeta.glob("*.tpl"):
            self.assertIn("{{> " + plantilla.stem, fuentes, f"plantilla sin usar: {plantilla.name}")

    def test_una_plantilla_inexistente_da_error(self):
        with self.assertRaises(ValueError):
            construir_web.generar_pagina(RAIZ / construir_web.CARPETA_PLANTILLAS, "{{> no_existe}}")


if __name__ == "__main__":
    unittest.main()
