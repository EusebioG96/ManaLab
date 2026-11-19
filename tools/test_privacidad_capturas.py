#!/usr/bin/env python3
"""ML-339: /privacy/ no puede volver a hablar de capturas automáticas (mano inicial, mulligans, resultado, «por defecto»).

En la 3.0 no hay capturas automáticas: solo los momentos destacados que pide el usuario (F8, botón sobre el juego, «Capturar momento»).
Se lee el texto de privacy/index.html (es y en en la misma página), por frases, y se exige además que diga que las pide el usuario.

Uso:  python3 tools/test_privacidad_capturas.py
"""
import html
import re
import unittest
from pathlib import Path

PAGINA = Path(__file__).resolve().parent.parent / "privacy" / "index.html"
CAPTURA = re.compile(r"captura|screenshot", re.IGNORECASE)
AUTOMATICA = re.compile(r"mano inicial|mulligan|resultado|opening hand|\bresult\b|por defecto|by default|mientras est[eé]n activadas"
                        r"|while they are on|desactivarlas|turn them off|interruptor para Arena|one switch for Arena", re.IGNORECASE)


def frases_de_capturas() -> list[str]:
    """Las frases del texto visible de /privacy/ que hablan de capturas de pantalla."""
    texto = html.unescape(re.sub(r"<[^>]+>", " ", PAGINA.read_text(encoding="utf-8")))
    return [f.strip() for f in re.split(r"(?<=[.:;])\s+|\n", texto) if CAPTURA.search(f)]


class PrivacidadCapturas(unittest.TestCase):
    def test_no_habla_de_capturas_automaticas(self):
        malas = [f for f in frases_de_capturas() if AUTOMATICA.search(f) and "Team mode" not in f and "Modo equipo" not in f]
        self.assertEqual(malas, [])

    def test_dice_que_solo_se_hacen_si_las_pide_el_usuario(self):
        texto = " ".join(frases_de_capturas())
        self.assertIn("no hace capturas por su cuenta", texto)
        self.assertIn("does not take screenshots on its own", texto)


if __name__ == "__main__":
    unittest.main()
