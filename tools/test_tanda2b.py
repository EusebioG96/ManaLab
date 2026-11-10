#!/usr/bin/env python3
"""Tanda 2B (ML-154): tipografías propias, vídeo del hero en teléfono, WebP y página 404. Sin red.

Uso:  python3 -m unittest tools/test_tanda2b.py
"""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def paginas(incluir_guia=True):
    for f in sorted(RAIZ.rglob("*.html")):
        rel = f.relative_to(RAIZ).as_posix()
        if rel.startswith((".git/", "node_modules/")):
            continue
        if not incluir_guia and rel.startswith("guia/"):
            continue
        yield f


def resolver(pagina, ruta):
    """Ruta de un recurso referenciado desde una página (absoluta desde la raíz del sitio o relativa a la página)."""
    ruta = ruta.split("#")[0].split("?")[0]
    return (RAIZ / ruta.lstrip("/")) if ruta.startswith("/") else (pagina.parent / ruta).resolve()


class TestTipografias(unittest.TestCase):
    def test_ningun_html_usa_google_fonts(self):
        for f in paginas():
            with self.subTest(f.relative_to(RAIZ).as_posix()):
                t = f.read_text(encoding="utf-8")
                self.assertNotIn("fonts.googleapis", t)
                self.assertNotIn("fonts.gstatic", t)
                self.assertNotIn("JetBrains", t)

    def test_font_face_apuntan_a_archivos_que_existen(self):
        total = 0
        for f in paginas():
            t = f.read_text(encoding="utf-8")
            for bloque in re.findall(r"@font-face\s*\{[^}]*\}", t):
                for u in re.findall(r"url\(([^)]+)\)", bloque):
                    total += 1
                    u = u.strip("'\"")
                    with self.subTest(f"{f.relative_to(RAIZ).as_posix()} {u}"):
                        self.assertTrue(resolver(f, u).is_file(), f"no existe {u}")
        self.assertGreaterEqual(total, 11 * 12, "faltan @font-face en las páginas")

    def test_preload_de_fuentes_existen_y_son_woff2(self):
        for f in paginas(False):
            t = f.read_text(encoding="utf-8")
            if "@font-face" not in t:
                continue
            pre = re.findall(r'<link rel="preload" href="([^"]+)" as="font" type="font/woff2" crossorigin>', t)
            with self.subTest(f.relative_to(RAIZ).as_posix()):
                self.assertEqual(len(pre), 2, "debe haber dos preload de fuente")
                for p in pre:
                    self.assertTrue(resolver(f, p).is_file(), p)

    def test_fuentes_pesan_menos_de_400_kb_y_llevan_licencia(self):
        d = RAIZ / "fuentes"
        self.assertLess(sum(x.stat().st_size for x in d.iterdir()), 400_000)
        self.assertTrue(list(d.glob("OFL-Saira*")) and list(d.glob("OFL-Figtree*")))


class TestHeroTelefono(unittest.TestCase):
    PORTADAS = {"en": RAIZ / "index.html", "es": RAIZ / "es" / "index.html"}

    def test_script_y_preload_del_poster(self):
        for idioma, f in self.PORTADAS.items():
            with self.subTest(idioma):
                t = f.read_text(encoding="utf-8")
                self.assertIn("(max-width: 767px) and (pointer: coarse)", t)
                self.assertRegex(t, rf'<link rel="preload" as="image" href="[^"]*video/hero/manalab-hero-{idioma}-poster\.jpg">')


class Enlaces(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.meta = [], []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "meta":
            self.meta.append(a)
        for k in ("href", "src"):
            if k in a and tag in ("a", "link", "img", "script", "source"):
                self.refs.append((tag, a[k]))


class TestWebP(unittest.TestCase):
    def test_cada_source_webp_existe_y_pesa_menos_que_su_jpg(self):
        total = 0
        for f in paginas(False):
            t = f.read_text(encoding="utf-8")
            for m in re.finditer(r'<picture><source srcset="([^"]+)" type="image/webp"><img [^>]*?src="([^"]+)"', t):
                total += 1
                w, j = resolver(f, m.group(1)), resolver(f, m.group(2))
                with self.subTest(f"{f.relative_to(RAIZ).as_posix()} {m.group(1)}"):
                    self.assertTrue(w.is_file(), f"falta {w}")
                    self.assertTrue(j.is_file(), f"falta {j}")
                    self.assertEqual(w.stem, j.stem)
                    self.assertLessEqual(w.stat().st_size, 0.85 * j.stat().st_size, "el WebP no pesa al menos un 15 % menos")
        self.assertGreaterEqual(total, 30, "faltan <picture> en las páginas")

    def test_galeria_actualiza_tambien_el_source(self):
        for f in (RAIZ / "index.html", RAIZ / "es" / "index.html"):
            t = f.read_text(encoding="utf-8")
            self.assertIn('querySelector("source")', t, f"{f.name}: las pestañas deben cambiar también el WebP")
            self.assertIn('.webp"', t)

    def test_no_se_tocan_og_posters_ni_guias(self):
        for f in paginas():
            t = f.read_text(encoding="utf-8")
            self.assertNotRegex(t, r'srcset="[^"]*(og|poster)[^"]*\.webp"')
        for f in (RAIZ / "guia" / "img").glob("*.webp"):
            self.fail(f"no debe haber WebP en guia/img: {f}")
        self.assertFalse((RAIZ / "img" / "og.webp").exists())


class TestPagina404(unittest.TestCase):
    def setUp(self):
        self.t = (RAIZ / "404.html").read_text(encoding="utf-8")
        p = Enlaces()
        p.feed(self.t)
        self.p = p

    def test_noindex_y_fuera_del_sitemap(self):
        self.assertTrue(any(m.get("name") == "robots" and m.get("content") == "noindex" for m in self.p.meta))
        self.assertNotIn("404", (RAIZ / "sitemap.xml").read_text(encoding="utf-8"))

    def test_solo_rutas_absolutas(self):
        self.assertTrue(self.p.refs)
        for tag, r in self.p.refs:
            with self.subTest(r):
                self.assertRegex(r, r"^(/|https?://)", f"ruta no absoluta en <{tag}>: {r}")
        for u in re.findall(r"url\(([^)]+)\)", self.t):
            self.assertTrue(u.strip("'\"").startswith("/"), u)

    def test_recursos_y_enlaces_internos_existen(self):
        for _, r in self.p.refs:
            if r.startswith("/"):
                with self.subTest(r):
                    self.assertTrue(resolver(RAIZ / "404.html", r).exists(), r)

    def test_contenido_bilingue_y_botones(self):
        hrefs = {r for _, r in self.p.refs}
        for h in ("/#descargar", "/es/#descargar", "/", "/es/", "/magic-online/", "/coaches/", "/#preguntas",
                  "/guia/guia_manalab_en.html", "/guia/guia_manalab_es.html"):
            self.assertIn(h, hrefs)
        for s in ("Page not found", "Esta página no existe", "Download ManaLab", "Descargar ManaLab"):
            self.assertIn(s, self.t)
        self.assertIn('<header class="cab">', self.t)
        self.assertIn("<footer>", self.t)


if __name__ == "__main__":
    unittest.main()
