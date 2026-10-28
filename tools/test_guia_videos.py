#!/usr/bin/env python3
"""Comprueba que las guías (9 idiomas) referencian vídeos que existen, con póster y atributos de rendimiento/accesibilidad.

Uso:  python3 -m unittest tools/test_guia_videos.py   (o python3 tools/test_guia_videos.py)
"""
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GUIA = RAIZ / "guia"
IDIOMAS = ["es", "en", "de", "fr", "it", "pt", "ja", "ko", "zh"]
MAX_VIDEO = 4 * 1024 * 1024
MAX_POSTER = 150 * 1024


class Lector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.videos = []     # atributos de cada <video>
        self.fuentes = []    # (indice_video, src)
        self.ids = set()
        self.secciones = set()
        self.enlaces_internos = []
        self._en_video = False

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if "id" in a:
            self.ids.add(a["id"])
            if tag == "section":
                self.secciones.add(a["id"])
        if tag == "video":
            self.videos.append(a)
            self._en_video = True
        elif tag == "source" and self._en_video:
            self.fuentes.append((len(self.videos) - 1, a.get("src", "")))
        elif tag == "a" and a.get("href", "").startswith("#"):
            self.enlaces_internos.append(a["href"][1:])

    def handle_endtag(self, tag):
        if tag == "video":
            self._en_video = False


def leer(idioma):
    p = Lector()
    p.feed((GUIA / f"guia_manalab_{idioma}.html").read_text(encoding="utf-8"))
    return p


class TestGuiaVideos(unittest.TestCase):
    def test_cada_guia_tiene_videos(self):
        for idioma in IDIOMAS:
            with self.subTest(idioma=idioma):
                self.assertGreaterEqual(len(leer(idioma).videos), 9)

    def test_mismos_videos_en_todos_los_idiomas(self):
        conjuntos = {i: sorted(Path(v["poster"]).name for v in leer(i).videos) for i in IDIOMAS}
        base = conjuntos["es"]
        for idioma, c in conjuntos.items():
            with self.subTest(idioma=idioma):
                self.assertEqual(c, base)

    def test_videos_y_posters_existen_y_pesan_poco(self):
        for idioma in IDIOMAS:
            p = leer(idioma)
            for i, v in enumerate(p.videos):
                with self.subTest(idioma=idioma, video=i):
                    poster = (GUIA / v.get("poster", "")).resolve()
                    self.assertTrue(v.get("poster"), "falta poster")
                    self.assertTrue(poster.is_file(), f"no existe {poster}")
                    self.assertLess(poster.stat().st_size, MAX_POSTER)
                    srcs = [s for j, s in p.fuentes if j == i]
                    self.assertTrue(srcs, "falta <source>")
                    for s in srcs:
                        self.assertFalse(s.startswith(("/", "http")), "ruta no relativa: " + s)
                        f = (GUIA / s).resolve()
                        self.assertTrue(f.is_file(), f"no existe {f}")
                        self.assertLess(f.stat().st_size, MAX_VIDEO)

    def test_atributos_de_rendimiento_y_accesibilidad(self):
        for idioma in IDIOMAS:
            for i, v in enumerate(leer(idioma).videos):
                with self.subTest(idioma=idioma, video=i):
                    self.assertIn("controls", v)
                    self.assertIn("muted", v)
                    self.assertIn("playsinline", v)
                    self.assertNotIn("autoplay", v)
                    self.assertEqual(v.get("preload"), "none")
                    self.assertTrue(v.get("width", "").isdigit() and v.get("height", "").isdigit())
                    self.assertTrue(v.get("aria-label", "").strip())
                    self.assertTrue(v.get("title", "").strip())

    def test_ids_unicos_y_enlaces_internos(self):
        for idioma in IDIOMAS:
            with self.subTest(idioma=idioma):
                p = leer(idioma)
                self.assertTrue(set(p.enlaces_internos) <= p.ids)
                ids_video = [v for v in p.ids if v.startswith("video-")]
                self.assertEqual(len(ids_video), len(p.videos))

    def test_pdf_enlaza_a_la_seccion_web(self):
        for idioma in IDIOMAS:
            txt = (GUIA / f"guia_manalab_{idioma}.html").read_text(encoding="utf-8")
            with self.subTest(idioma=idioma):
                self.assertIn(f"https://manalab.es/guia/guia_manalab_{idioma}.html#video-", txt)

    def test_guia_en_el_zip(self):
        import zipfile
        with zipfile.ZipFile(GUIA / "guia_manalab_9_idiomas.zip") as z:
            self.assertEqual(sorted(z.namelist()), sorted(f"guia_manalab_{i}.pdf" for i in IDIOMAS))


if __name__ == "__main__":
    unittest.main()
