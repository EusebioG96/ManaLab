#!/usr/bin/env python3
"""Vídeo de la cabecera de las portadas (ML-058): archivos, peso y atributos del <video>, y un único botón en el hero.

Uso:  python3 -m unittest tools/test_video_hero.py   (o python3 tools/test_video_hero.py)
"""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
HERO = RAIZ / "video" / "hero"
MAX_BYTES = 1_500_000            # 1,5 MB por archivo (vídeos y pósters)
PORTADAS = {"en": (RAIZ / "index.html", ""), "es": (RAIZ / "es" / "index.html", "../")}


class Lector(HTMLParser):
    """Lee el hero (<section class="portada">): el <video>, sus <source> y los enlaces con clase «boton»."""

    def __init__(self):
        super().__init__()
        self.en_portada = False
        self.profundidad = 0
        self.videos, self.fuentes, self.botones, self.enlaces = [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        if tag == "section" and "portada" in a.get("class", "").split():
            self.en_portada, self.profundidad = True, 0
        if not self.en_portada:
            return
        if tag == "section":
            self.profundidad += 1
        if tag == "video":
            self.videos.append(a)
        elif tag == "source" and self.videos:
            self.fuentes.append(a)
        elif tag == "a":
            (self.botones if "boton" in a.get("class", "").split() else self.enlaces).append(a)

    def handle_endtag(self, tag):
        if self.en_portada and tag == "section":
            self.profundidad -= 1
            if self.profundidad == 0:
                self.en_portada = False


def leer(idioma):
    ruta, _ = PORTADAS[idioma]
    lector = Lector()
    lector.feed(ruta.read_text(encoding="utf-8"))
    return lector


class TestArchivos(unittest.TestCase):
    def test_existen_y_pesan_poco(self):
        for idioma in PORTADAS:
            for nombre in (f"manalab-hero-{idioma}.mp4", f"manalab-hero-{idioma}.webm", f"manalab-hero-{idioma}-poster.jpg"):
                with self.subTest(nombre):
                    f = HERO / nombre
                    self.assertTrue(f.is_file(), f"falta {f}")
                    self.assertLessEqual(f.stat().st_size, MAX_BYTES, f"{nombre} pesa más de 1,5 MB")

    def test_cabeceras_de_formato(self):
        for idioma in PORTADAS:
            with self.subTest(idioma):
                mp4 = (HERO / f"manalab-hero-{idioma}.mp4").read_bytes()
                self.assertEqual(mp4[4:8], b"ftyp", "el MP4 no empieza por ftyp")
                self.assertIn(b"avc1", mp4[:200_000], "el MP4 no es H.264")
                self.assertLess(mp4.find(b"moov"), mp4.find(b"mdat"), "MP4 sin +faststart (moov detrás de mdat)")
                webm = (HERO / f"manalab-hero-{idioma}.webm").read_bytes()
                self.assertEqual(webm[:4], b"\x1a\x45\xdf\xa3", "el WebM no es EBML")
                self.assertIn(b"V_VP9", webm[:4096], "el WebM no es VP9")
                self.assertEqual((HERO / f"manalab-hero-{idioma}-poster.jpg").read_bytes()[:3], b"\xff\xd8\xff")


class TestPortadas(unittest.TestCase):
    def test_atributos_del_video(self):
        for idioma, (ruta, pre) in PORTADAS.items():
            with self.subTest(idioma):
                h = leer(idioma)
                self.assertEqual(len(h.videos), 1, "debe haber un solo <video> en el hero")
                v = h.videos[0]
                for attr in ("autoplay", "muted", "loop", "playsinline"):
                    self.assertIn(attr, v, f"falta {attr}")
                self.assertEqual(v.get("preload"), "metadata")
                self.assertEqual(v.get("poster"), f"{pre}video/hero/manalab-hero-{idioma}-poster.jpg")
                self.assertGreater(len(v.get("aria-label", "")), 40, "falta una descripción accesible (aria-label)")
                self.assertNotRegex(v.get("aria-label", ""), r"(?i)windows")
                self.assertEqual([(s.get("type"), s.get("src")) for s in h.fuentes],
                                 [("video/webm", f"{pre}video/hero/manalab-hero-{idioma}.webm"),
                                  ("video/mp4", f"{pre}video/hero/manalab-hero-{idioma}.mp4")], "primero WebM y luego MP4")
                for f in [v["poster"]] + [s["src"] for s in h.fuentes]:
                    self.assertTrue((ruta.parent / f).resolve().is_file(), f"{f} no existe")

    def test_un_solo_boton_en_el_hero(self):
        for idioma in PORTADAS:
            with self.subTest(idioma):
                h = leer(idioma)
                self.assertEqual(len(h.botones), 1, "en el hero solo debe quedar el botón de descarga")
                self.assertIn("descarga", h.botones[0].get("class", "").split())
                self.assertIn("enlace-sec", {c for e in h.enlaces for c in e.get("class", "").split()})

    def test_reducir_movimiento_y_ahorro_de_datos(self):
        for idioma, (ruta, _) in PORTADAS.items():
            with self.subTest(idioma):
                t = ruta.read_text(encoding="utf-8")
                bloque = t[t.index('id="hero-video"'):t.index('class="hero-cta"')]
                self.assertIn("prefers-reduced-motion: reduce", bloque)
                self.assertIn("saveData", bloque)
                self.assertRegex(bloque, r'removeAttribute\("autoplay"\)')
                self.assertRegex(bloque, r"querySelectorAll\(\"source\"\)")
                # en móvil también se reproduce: ninguna regla oculta el vídeo por anchura
                self.assertIsNone(re.search(r"@media[^{]*max-width[^{]*\{[^}]*\.hero-video[^}]*display:\s*none", t))


if __name__ == "__main__":
    unittest.main()
