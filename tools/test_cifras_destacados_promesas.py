#!/usr/bin/env python3
"""ML-336: ninguna página promete que Aprender/Learn «no envía nada» ni que el servidor de ManaLab no recibe más que una visita,
porque la app y Learn envían las cifras de los creadores destacados (en totales). Falla si vuelve una de esas frases.

Uso:  python3 -m pytest tools/test_cifras_destacados_promesas.py
"""
import html
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = ("safety/index.html", "es/seguridad/index.html", "privacy/index.html")
PROMESAS_FALSAS = (
    "have no switch of their own and send nothing of yours",
    "no tienen interruptor propio y no envían nada tuyo",
    "neither receives more than any visit does",
    "ninguno recibe más que lo de cualquier visita",
)
FRASES_NUEVAS = {
    "safety/index.html": ("send nothing from your games, your PC or your account", "the featured creators' figures, as totals only"),
    "es/seguridad/index.html": ("No envían nada de tus partidas, de tu equipo ni de tu cuenta", "las cifras de los creadores destacados, solo en totales"),
    "privacy/index.html": (
        "Metafy receives no more than any visit does (IP and browser); the ManaLab server also receives the featured creators' figures",
        "Metafy no recibe más que lo de cualquier visita (IP y navegador); el servidor de ManaLab recibe además las cifras de los creadores destacados",
    ),
}


def leer(ruta: str) -> str:
    return html.unescape((RAIZ / ruta).read_text(encoding="utf-8"))


class TestPromesasDeAprender(unittest.TestCase):
    def test_no_vuelven_las_promesas_falsas(self):
        for ruta in PAGINAS:
            texto = leer(ruta)
            for frase in PROMESAS_FALSAS:
                with self.subTest(ruta=ruta, frase=frase):
                    self.assertNotIn(frase, texto)

    def test_las_frases_corregidas_estan(self):
        for ruta, frases in FRASES_NUEVAS.items():
            texto = leer(ruta)
            for frase in frases:
                with self.subTest(ruta=ruta, frase=frase):
                    self.assertIn(frase, texto)


if __name__ == "__main__":
    unittest.main()
