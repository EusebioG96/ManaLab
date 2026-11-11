#!/usr/bin/env python3
"""ML-207: nombres de mazo de Magic Online tras la 2.3.2. Comprueba sobre los archivos (sin red).

Desde la 2.3.2, un mazo de Magic Online toma el nombre guardado en Magic Online si su lista coincide exactamente con un
solo mazo guardado; si no, se nombra por sus colores. Este test falla si:
1. En cualquier página o guía vuelve una frase que dice que el mazo de MTGO se nombra SOLO por colores
   (o que «el registro no trae el nombre del mazo») o que lo anuncia como «por ahora».
2. Una página que habla de nombres de mazo de MTGO no menciona el nombre guardado en Magic Online.
3. Una página con una frase de «nombrar por colores» no está en la tabla de comprobación (para que no se escape ninguna).

Los nombres del mazo del RIVAL (comparación con el meta) no cambian y no se tocan aquí.

Uso:  python3 tools/test_nombres_mtgo.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALTAR = {".git", "tools", "node_modules"}

# Frases viejas: el mazo de MTGO «se nombra por sus colores» sin más, o «por ahora». Una por idioma y forma.
VIEJAS = [
    r"decks? (?:is|are) named by (?:its|their) colors\.?(?: for now)?(?=[\"<])",
    r"(?:your deck|deck) is named by its colors(?:</b>)? for now",
    r"your deck is named by its colors\.(?=[\"<])",
    r"usually named by its colors",
    r"log has no deck name",
    r"(?:tu mazo|el mazo) se nombra por sus colores(?:</b>)? por ahora",
    r"tu mazo se nombra por sus colores\.(?=[\"<])",
    r"los mazos se nombran por sus colores",
    r"suele llamarse por sus colores",
    r"registro no trae el nombre del mazo",
    r"seu deck recebe o nome pelas cores\.(?=[\"<])",
    r"os decks recebem o nome pelas cores",
    r"costuma ser nomeado pelas cores",
    r"log não traz o nome do deck",
    r"デッキには色で名前が付きます",
    r"デッキに色で名前が付きます",
    r"デッキ名は色から付けられ",
    r"ログにはデッキ名がない",
    r"套牌会按颜色命名",
    r"日志里没有套牌名称",
    r"덱 이름은 색깔로 붙으며",
    r"로그에는 덱 이름이 없으므로",
    r"ton deck est nommé d'après ses couleurs\s*;",
    r"le journal ne contient pas le nom du deck",
    r"il tuo mazzo prende il nome dai suoi colori",
    r"il log non contiene il nome del mazzo",
    r"dein deck bekommt einen namen nach seinen farben",
    r"log keinen decknamen",
]

# Cada página que habla del nombre del mazo de MTGO y la frase que menciona el nombre guardado en Magic Online.
PAGINAS = {
    "index.html": r"saved it with in Magic Online",
    "magic-online/index.html": r"saved it with in Magic Online",
    "novedades/index.html": r"saved it with in Magic Online",
    "coaches/index.html": r"gave it in Magic Online",
    "es/index.html": r"con el que lo guardaste en Magic Online",
    "es/magic-online/index.html": r"con el que lo guardaste en Magic Online",
    "es/novedades/index.html": r"con el que lo guardaste en Magic Online",
    "es/coaches/index.html": r"el alumno le puso en Magic Online",
    "pt/index.html": r"nome que você salvou no Magic Online",
    "pt/coaches/index.html": r"o aluno deu a ele no Magic Online",
    "ja/index.html": r"Magic Onlineで保存した名前",
    "guia/guia_manalab_en.html": r"saved it with in Magic Online",
    "guia/guia_manalab_es.html": r"con el que lo guardaste en Magic Online",
    "guia/guia_manalab_pt.html": r"nome que você salvou no Magic Online",
    "guia/guia_manalab_de.html": r"in Magic Online gespeichert hast",
    "guia/guia_manalab_fr.html": r"enregistré dans Magic Online",
    "guia/guia_manalab_it.html": r"salvato in Magic Online",
    "guia/guia_manalab_ja.html": r"Magic Onlineで保存した名前",
    "guia/guia_manalab_ko.html": r"Magic Online에 저장한 이름",
    "guia/guia_manalab_zh.html": r"Magic Online 中保存的套牌",
}

# Cualquier frase de «nombrar por colores» (rival incluido): si aparece en una página, esa página debe estar en PAGINAS.
POR_COLORES = re.compile(
    r"by (?:its|their) colors|por sus colores|pelas cores|d'après ses couleurs|nach seinen Farben|dai suoi colori|"
    r"in base ai suoi colori|色で名前|色から付け|按颜色|색깔로", re.I)


def paginas_html():
    """Todas las páginas y guías HTML del sitio (ruta relativa -> texto)."""
    salida = {}
    for p in sorted(RAIZ.rglob("*.html")):
        rel = p.relative_to(RAIZ)
        if rel.parts[0] in SALTAR:
            continue
        salida[rel.as_posix()] = p.read_text(encoding="utf-8").replace(" ", " ")
    return salida


class TestNombresMtgo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paginas = paginas_html()

    def test_ninguna_frase_vieja(self):
        """Ni «solo por colores» ni «por ahora» en ninguna página, incluido el JSON-LD de las FAQ."""
        for ruta, texto in self.paginas.items():
            for patron in VIEJAS:
                m = re.search(patron, texto, re.I)
                self.assertIsNone(m, f"{ruta}: frase vieja sobre el nombre del mazo de MTGO: {m.group(0) if m else ''}")

    def test_cada_pagina_menciona_el_nombre_guardado(self):
        """Las páginas que hablan de nombres de mazo de MTGO dicen que toma el nombre guardado en Magic Online."""
        for ruta, patron in PAGINAS.items():
            self.assertIn(ruta, self.paginas, f"{ruta}: no existe")
            self.assertTrue(re.search(patron, self.paginas[ruta]), f"{ruta}: no menciona el nombre guardado en Magic Online")

    def test_ninguna_pagina_con_nombres_por_colores_queda_fuera(self):
        """Una página nueva con «por colores» debe entrar en PAGINAS (y así decir lo del nombre guardado)."""
        for ruta, texto in self.paginas.items():
            if POR_COLORES.search(texto):
                self.assertIn(ruta, PAGINAS, f"{ruta}: habla de nombrar por colores y no está en la tabla de PAGINAS")

    def test_el_json_ld_de_las_faq_tambien(self):
        """El texto de las FAQ (JSON-LD) de la portada y de /magic-online/ lleva la regla nueva, no solo el texto visible."""
        for ruta in ("index.html", "es/index.html", "pt/index.html", "ja/index.html", "magic-online/index.html", "es/magic-online/index.html"):
            m = re.search(r'<script type="application/ld\+json">(.*?)</script>', self.paginas[ruta], re.S)
            self.assertIsNotNone(m, ruta)
            self.assertTrue(re.search(PAGINAS[ruta], m.group(1)), f"{ruta}: el JSON-LD no menciona el nombre guardado")


if __name__ == "__main__":
    unittest.main()
