#!/usr/bin/env python3
"""ML-073: el sorteo cierra el domingo 8/11/2026 a las 23:59 (Madrid) y se sortea el lunes 9/11. Sin red.

Comprueba las fechas nuevas en /sorteo/ (es y en), en los avisos de las portadas y en los metadatos, y que no queden
menciones al 3/11 ni al 4/11 ligadas al sorteo. Si existe data-hasta en las portadas, debe ser 2026-11-08T23:59:59+01:00.

Uso:  python3 tools/test_sorteo_fechas.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BASES = {"es": RAIZ / "sorteo" / "index.html", "en": RAIZ / "sorteo" / "en" / "index.html"}
PORTADAS = {"es": RAIZ / "es" / "index.html", "en": RAIZ / "index.html"}
VIEJAS = re.compile(r"3/11|4/11|3 de noviembre|4 de noviembre|3 November|4 November|Nov 3\b|Nov 4\b|November 3\b|November 4\b|2026-11-0[34]|miércoles 4|Wednesday 4", re.I)


def leer(r):
    return r.read_text(encoding="utf-8")


def aviso_sorteo(t):
    m = re.search(r"<a [^>]*href=\"/sorteo/[^\"]*\"[^>]*>.*?</a>", t, re.S)
    return m.group(0) if m else ""


class TestSorteoFechas(unittest.TestCase):
    def test_bases_es(self):
        t = leer(BASES["es"])
        self.assertIn("al domingo 8 de noviembre de 2026 a las 23:59 (hora de Madrid)", t)
        self.assertIn("hasta el domingo 8 de noviembre de 2026 a las 23:59 (hora de Madrid)", t)
        self.assertEqual(t.count("el lunes 9 de noviembre"), 3)
        self.assertIn("del 27 de octubre al 8 de noviembre de 2026", t)

    def test_bases_en(self):
        t = leer(BASES["en"])
        self.assertIn("to Sunday 8 November 2026 at 23:59 (Madrid time)", t)
        self.assertIn("until Sunday 8 November 2026 at 23:59 (Madrid time)", t)
        self.assertEqual(t.count("on Monday 9 November"), 3)
        self.assertIn("from 27 October to 8 November 2026", t)

    def test_avisos_portada(self):
        self.assertIn("hasta el domingo 8/11", aviso_sorteo(leer(PORTADAS["es"])))
        self.assertIn("until Sunday Nov 8", aviso_sorteo(leer(PORTADAS["en"])))

    def test_hasta_si_existe(self):
        for lang, r in PORTADAS.items():
            m = re.search(r'data-hasta="([^"]+)"', leer(r))
            if m:
                with self.subTest(lang=lang):
                    self.assertEqual(m.group(1), "2026-11-08T23:59:59+01:00")

    def test_sin_fechas_viejas(self):
        for r in list(BASES.values()):
            with self.subTest(r=r.name):
                self.assertIsNone(VIEJAS.search(leer(r)))
        for lang, r in PORTADAS.items():
            with self.subTest(lang=lang):
                self.assertIsNone(VIEJAS.search(aviso_sorteo(leer(r))))
                self.assertIsNone(re.search(r'data-hasta="2026-11-0[34]', leer(r)))


if __name__ == "__main__":
    unittest.main()
