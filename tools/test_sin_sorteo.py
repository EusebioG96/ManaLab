#!/usr/bin/env python3
"""ML-310 y ML-342: el sorteo ya terminó y su página se quitó de la web. GitHub Pages no admite redirecciones 301, así que
/sorteo/, /sorteo/en/ y /es/sorteo/ son tres páginas mínimas que redirigen con ``<meta refresh>`` a las novedades de su idioma
(ML-342). Este test falla si:
- alguna página normal, el sitemap o robots.txt enlazan a /sorteo/ o /es/sorteo/;
- existe cualquier otra cosa bajo sorteo/ o es/sorteo/ que no sea el ``index.html`` de redirección (o falta alguno);
- una redirección no apunta (refresh y canonical) a las novedades de su idioma, lleva noindex, scripts, cabecera, pie o
  GoatCounter, o aparece en el sitemap.

Sin red.  Uso:  python3 -m pytest -q tools/test_sin_sorteo.py
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# /sorteo seguido de barra o de fin de palabra; no casa con /sorteos ni con textos como «sorteo» sin barra
ENLACE_SORTEO = re.compile(r"/sorteo\b")
FICHEROS_PUBLICADOS = ["sitemap.xml", "robots.txt"]
SITIO = "https://manalab.es"
# página de redirección -> (destino, idioma, texto del enlace de respaldo); decisión de Eusebio, 20/11/2026
REDIRECCIONES = {
    "sorteo/index.html": ("/novedades/", "en", "What&#x27;s new in ManaLab 3.0 →"),
    "sorteo/en/index.html": ("/novedades/", "en", "What&#x27;s new in ManaLab 3.0 →"),
    "es/sorteo/index.html": ("/es/novedades/", "es", "Novedades de ManaLab 3.0 →"),
}
CARPETAS_SORTEO = ("sorteo", "es/sorteo")


def _paginas_generadas():
    return [p for p in RAIZ.rglob("*.html") if ".git" not in p.parts]


def _paginas_normales():
    return [p for p in _paginas_generadas() if p.relative_to(RAIZ).as_posix() not in REDIRECCIONES]


def _leer(ruta: str) -> str:
    return (RAIZ / ruta).read_text(encoding="utf-8")


class TestSinSorteo(unittest.TestCase):
    def test_ninguna_pagina_normal_enlaza_al_sorteo(self):
        paginas = _paginas_normales()
        self.assertGreater(len(paginas), 25)
        for ruta in paginas:
            with self.subTest(pagina=str(ruta.relative_to(RAIZ))):
                self.assertIsNone(ENLACE_SORTEO.search(ruta.read_text(encoding="utf-8")))

    def test_sitemap_y_robots_no_mencionan_el_sorteo(self):
        for nombre in FICHEROS_PUBLICADOS:
            with self.subTest(fichero=nombre):
                self.assertIsNone(ENLACE_SORTEO.search((RAIZ / nombre).read_text(encoding="utf-8")))

    def test_las_carpetas_del_sorteo_solo_llevan_la_redireccion(self):
        archivos = sorted(p.relative_to(RAIZ).as_posix() for c in CARPETAS_SORTEO for p in (RAIZ / c).rglob("*") if p.is_file())
        self.assertEqual(archivos, sorted(REDIRECCIONES))

    def test_solo_existen_las_tres_paginas_de_redireccion(self):
        con_refresh = [p.relative_to(RAIZ).as_posix() for p in _paginas_generadas() if "http-equiv=\"refresh\"" in p.read_text(encoding="utf-8")]
        self.assertEqual(sorted(con_refresh), sorted(REDIRECCIONES))


class TestRedireccionesDelSorteo(unittest.TestCase):
    def test_refresh_canonical_e_idioma_van_a_las_novedades_de_su_idioma(self):
        for ruta, (destino, idioma, _) in REDIRECCIONES.items():
            with self.subTest(ruta):
                texto = _leer(ruta)
                self.assertIn(f'<meta content="0; url={destino}" http-equiv="refresh"/>', texto)
                self.assertEqual(re.findall(r'<link href="([^"]*)" rel="canonical"/>', texto), [SITIO + destino])
                self.assertIn(f'<html lang="{idioma}">', texto)
                self.assertTrue((RAIZ / destino.lstrip("/") / "index.html").is_file())

    def test_un_unico_enlace_visible_de_respaldo(self):
        for ruta, (destino, _, texto_enlace) in REDIRECCIONES.items():
            with self.subTest(ruta):
                cuerpo = _leer(ruta).split("<body>", 1)[1]
                self.assertEqual(re.findall(r"<a [^>]*>.*?</a>", cuerpo), [f'<a href="{destino}">{texto_enlace}</a>'])

    def test_sin_noindex_ni_scripts_ni_goatcounter_ni_cabecera_ni_pie(self):
        for ruta in REDIRECCIONES:
            with self.subTest(ruta):
                texto = _leer(ruta)
                for prohibido in ("noindex", "<script", "goatcounter", "<header", "<footer", "<nav", "<style"):
                    self.assertNotIn(prohibido, texto.lower())
                self.assertIn("<title>", texto)

    def test_fuera_del_sitemap(self):
        sitemap = _leer("sitemap.xml")
        for ruta in REDIRECCIONES:
            with self.subTest(ruta):
                url = SITIO + "/" + ruta.removesuffix("index.html")
                self.assertNotIn(f"<loc>{url}</loc>", sitemap)


if __name__ == "__main__":
    unittest.main()
