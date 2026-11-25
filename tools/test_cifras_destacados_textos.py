#!/usr/bin/env python3
"""ML-333: la respuesta «¿Qué datos envía?» de las portadas y de las páginas de Magic Online dice que se envían las cifras de los
creadores destacados, en el HTML y en el JSON-LD, y ya no repite que el banner «se apaga en Ajustes».

Uso:  python3 -m pytest tools/test_cifras_destacados_textos.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FRASES = {
    "index.html": "It also sends, at most once an hour, how many times each featured creator in Learn was seen and clicked, as totals only.",
    "magic-online/index.html": "It also sends, at most once an hour, how many times each featured creator in Learn was seen and clicked, as totals only.",
    "es/index.html": "También envía, como mucho una vez por hora, cuántas veces se vio cada creador destacado de Aprender y cuántos clics recibió, solo en totales.",
    "es/magic-online/index.html": "También envía, como mucho una vez por hora, cuántas veces se vio cada creador destacado de Aprender y cuántos clics recibió, solo en totales.",
    "pt/index.html": "Ele também envia, no máximo uma vez por hora, quantas vezes cada criador em destaque do Aprender foi visto e clicado, só em totais.",
    "ja/index.html": "また、「学ぶ」画面の注目クリエイターが何回表示され、何回クリックされたかを、合計だけ、最大で1時間に1回送信します。",
}
FINALES_REPETIDOS = ("y se apaga en Ajustes", "and turns off in Settings", "e se desliga em Configurações", "広告スクリプトを読み込み、設定でオフにできます")


class TestCifrasDestacadosTextos(unittest.TestCase):
    def test_la_frase_sale_en_el_html_y_en_el_json_ld_de_cada_pagina(self):
        for ruta, frase in FRASES.items():
            html = (RAIZ / ruta).read_text(encoding="utf-8")
            with self.subTest(ruta=ruta):
                self.assertGreaterEqual(html.count(frase), 2, "debe salir en el desplegable y en el JSON-LD")

    def test_el_final_repetido_del_banner_ya_no_esta(self):
        for ruta in FRASES:
            html = (RAIZ / ruta).read_text(encoding="utf-8")
            for final in FINALES_REPETIDOS:
                with self.subTest(ruta=ruta, final=final):
                    self.assertNotIn(final, html)

    def test_en_las_cuatro_portadas_la_frase_va_justo_tras_el_script_del_banner(self):
        for ruta in ("index.html", "es/index.html", "pt/index.html", "ja/index.html"):
            html = (RAIZ / ruta).read_text(encoding="utf-8")
            with self.subTest(ruta=ruta):
                self.assertRegex(html, r"(?:ad script|script de anuncios de Metafy|script de anúncios da Metafy|広告スクリプトを読み込みます)[.。] ?" + re.escape(FRASES[ruta][:12]))


if __name__ == "__main__":
    unittest.main()
