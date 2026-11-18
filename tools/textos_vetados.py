#!/usr/bin/env python3
"""Frases que no pueden aparecer en nada de lo que publica la web (ML-280, RED-03). Solo biblioteca estándar.

Las usan tools/test_textos_vetados.py (que recorre lo publicado) y tools/generar_version_json.py (que no copia a version.json
las novedades de una release que las contengan).

Se busca sin distinguir mayúsculas y por palabras completas: «ad free» no salta con «Download free» ni «no ads» con «piano ads».
"""
import re

FRASES_VETADAS = (
    "no ads", "ad-free", "ad free", "sin anuncios", "sem anúncios", "広告なし",
    "supported by Metafy", "lo sostiene Metafy", "la apoya Metafy",
    "Ko-fi", "kofi", "ko-fi.com", "Patreon",
)

# Una frase solo cuenta si no está pegada a otra letra o cifra (así «Download free» no es «ad free»).
_PATRON = re.compile("|".join(r"(?<![\w])%s(?![\w])" % re.escape(f) for f in FRASES_VETADAS), re.IGNORECASE)


def buscar(linea: str) -> list[str]:
    """Las frases vetadas que contiene una línea de texto (tal y como aparecen escritas en ella)."""
    return [m.group(0) for m in _PATRON.finditer(linea)]
