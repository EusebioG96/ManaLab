#!/usr/bin/env python3
"""ML-336 (RED-11): título y descripción aprobados de /ja/ y /overlay/ en <title>, meta description, Open Graph, Twitter y JSON-LD.
ML-341: Eusebio aprobó recortar la descripción de /overlay/ a 157 caracteres (el título y todo /ja/ siguen como estaban).

Uso:  python3 -m pytest tools/test_metadatos_red11.py
"""
import html
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS = {
    "ja/index.html": (
        "MTGアリーナ戦績トラッカー｜勝率・マリガンを自動記録 ManaLab",
        "MTGアリーナとMagic Onlineの対戦を自動で記録する無料トラッカー。初手・マリガン、先攻・後攻、相手のデッキを保存し、"
        "マッチアップ別の勝率とターンごとのリプレイで振り返れます。アカウント不要。",
    ),
    "overlay/index.html": (
        "Free MTG Arena Overlay: Library & Draw Odds · ManaLab",
        "Free overlay for MTG Arena: see the cards left in your library, your odds of drawing each one and what your opponent "
        "revealed. Magic Online is supported too.",
    ),
}


class TestMetadatosRed11(unittest.TestCase):
    def test_titulo_y_descripcion_en_todas_las_etiquetas(self):
        for ruta, (titulo, descripcion) in PAGINAS.items():
            texto = html.unescape((RAIZ / ruta).read_text(encoding="utf-8"))
            cabecera = texto.split("</head>")[0]
            with self.subTest(ruta=ruta):
                self.assertEqual(re.findall(r"<title>(.*?)</title>", cabecera), [titulo])
                self.assertEqual(len(re.findall(re.escape(f'content="{titulo}"'), cabecera)), 2, "og:title y twitter:title")
                self.assertEqual(len(re.findall(re.escape(f'content="{descripcion}"'), cabecera)), 3, "description, og y twitter")
                self.assertIn(f'"description": "{descripcion}"', cabecera)
                self.assertTrue(30 <= len(titulo) <= 60 and 50 <= len(descripcion) <= 170)


if __name__ == "__main__":
    unittest.main()
