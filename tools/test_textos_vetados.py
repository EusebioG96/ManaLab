#!/usr/bin/env python3
"""ML-280 (RED-03): ninguna frase vetada aparece en nada de lo que publica la web. Sin red.

Recorre todo el HTML generado (con sus datos estructurados JSON-LD, <meta>, alt y title, porque se lee el texto en bruto y también
con las entidades HTML resueltas), contenido.json, version.json, los .js públicos, sitemap.xml y robots.txt. Falla con archivo, línea y
frase. La lista de frases vive en tools/textos_vetados.py (FRASES_VETADAS); se busca sin distinguir mayúsculas y por palabras completas.

Lo que NO se comprueba es lo que no se publica: docs/ y tools/ (documentación y herramientas), .github/ y plantillas/ (las
plantillas llegan a la web a través del HTML generado, que sí se comprueba, y un fallo en ellas se ve ahí).

Uso:  python3 tools/test_textos_vetados.py
"""
import html
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generar_version_json  # noqa: E402
import textos_vetados  # noqa: E402
from textos_vetados import FRASES_VETADAS  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
NO_PUBLICADO = {".git", ".github", "docs", "tools", "plantillas"}
SUFIJOS = {".html", ".js"}
NOMBRES = {"contenido.json", "version.json", "sitemap.xml", "robots.txt"}


def publicados() -> list[Path]:
    """Archivos de texto que se publican, ordenados."""
    return sorted(p for p in RAIZ.rglob("*")
                  if p.is_file() and not NO_PUBLICADO & set(p.relative_to(RAIZ).parts)
                  and (p.suffix in SUFIJOS or p.relative_to(RAIZ).as_posix() in NOMBRES))


def hallazgos(ruta: Path, texto: str | None = None) -> list[str]:
    """«archivo:línea: frase» por cada frase vetada de un archivo."""
    texto = ruta.read_text(encoding="utf-8") if texto is None else texto
    rel = ruta.relative_to(RAIZ).as_posix() if ruta.is_absolute() and RAIZ in ruta.parents else str(ruta)
    salida = []
    for n, linea in enumerate(texto.split("\n"), 1):
        for frase in dict.fromkeys(textos_vetados.buscar(linea) + textos_vetados.buscar(html.unescape(linea))):
            salida.append(f"{rel}:{n}: «{frase}»")
    return salida


class TestTextosVetados(unittest.TestCase):
    def test_se_recorre_todo_lo_publicado(self):
        nombres = {p.relative_to(RAIZ).as_posix() for p in publicados()}
        for esperado in ("index.html", "es/index.html", "404.html", "descarga.js", "contacto.js", "contenido.json", "version.json"):
            self.assertIn(esperado, nombres)
        self.assertGreaterEqual(len(nombres), 30)
        self.assertFalse([n for n in nombres if n.startswith(("tools/", "docs/", "plantillas/"))])

    def test_ninguna_frase_vetada_en_lo_publicado(self):
        restos = [h for p in publicados() for h in hallazgos(p)]
        self.assertEqual(restos, [], "frases vetadas (archivo:línea): " + "; ".join(restos))

    def test_la_lista_trae_todas_las_frases_del_brief(self):
        esperadas = {"no ads", "ad-free", "ad free", "sin anuncios", "sem anúncios", "広告なし", "supported by metafy",
                     "lo sostiene metafy", "la apoya metafy", "ko-fi", "kofi", "ko-fi.com", "patreon"}
        self.assertEqual({f.lower() for f in FRASES_VETADAS}, esperadas)

    def test_cada_frase_se_detecta_sin_distinguir_mayusculas(self):
        for frase in FRASES_VETADAS:
            for texto in (f"antes {frase} después", f"<p>{frase.upper()}</p>", f'"{frase.title()}"'):
                with self.subTest(frase=frase, texto=texto):
                    self.assertTrue(textos_vetados.buscar(texto), texto)

    def test_no_salta_con_palabras_que_solo_las_contienen(self):
        for texto in ("Download free", "Baixar grátis", "Descargar gratis", "download free for Windows", "broad free"):
            self.assertEqual(textos_vetados.buscar(texto), [], texto)

    def test_el_mensaje_dice_archivo_linea_y_frase(self):
        self.assertEqual(hallazgos(RAIZ / "index.html", "uno\n<p>Sin Anuncios</p>\n"), ["index.html:2: «Sin Anuncios»"])
        self.assertEqual(hallazgos(RAIZ / "index.html", "<p>Ko&#45;fi</p>"), ["index.html:1: «Ko-fi»"])

    def test_json_ld_meta_alt_y_title_tambien_se_leen(self):
        for texto in ('<script type="application/ld+json">{"description": "ad-free"}</script>',
                      '<meta name="description" content="No ads">', '<img alt="Patreon" src="x">', '<a title="kofi">'):
            with self.subTest(texto=texto):
                self.assertTrue(hallazgos(RAIZ / "x.html", texto), texto)


class TestVersionJsonSinVetados(unittest.TestCase):
    NOTAS = ("## ManaLab 9.9.9\n\nIntro.\n\n### Novedades / What's new\n\n- **Algo** — texto.\n  *Something.*\n"
             "- **Patreon fuera** — solo en Ko-fi.\n  *Patreon removed.*\n- **Otro** — texto.\n  *Other.*")

    def test_los_puntos_con_frases_vetadas_no_pasan_a_version_json(self):
        n = generar_version_json.notas_publicas(self.NOTAS)
        self.assertNotIn("Patreon", n)
        self.assertNotIn("Ko-fi", n)
        self.assertIn("**Algo**", n)
        self.assertIn("  *Something.*", n)
        self.assertIn("**Otro**", n)
        self.assertIn("  *Other.*", n)

    def test_sin_frases_vetadas_las_notas_no_cambian(self):
        limpio = "## ManaLab 9.9.9\n\n### Novedades / What's new\n\n- **Algo** — texto.\n  *Something.*"
        self.assertEqual(generar_version_json.notas_publicas(limpio), limpio)


if __name__ == "__main__":
    unittest.main()
