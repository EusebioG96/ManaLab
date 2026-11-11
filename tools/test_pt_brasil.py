#!/usr/bin/env python3
"""ML-174: todo el portugués de ManaLab es de Brasil (pt-BR). Comprueba sobre los archivos (sin red).

1. Códigos de idioma: ningún lang, hreflang ni inLanguage vale «pt» a secas, ni og:locale vale otra cosa que pt_BR
   (también en sitemap.xml). Las URLs /pt/… no cambian.
2. Texto: las páginas en portugués no llevan formas de Portugal (Equipa, ecrã, ficheiro, utilizador, registo, partilhar,
   definições, rato, telemóvel, contacto, facto, transferir, «estar a fazer», tu/teu/tua, guardar un archivo, secção,
   óptimo, acção, direcção, actual, objecto…).
3. seo_check.py falla si vuelve «pt» a secas.

Uso:  python3 tools/test_pt_brasil.py
"""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALTAR = {".git", "tools", "node_modules"}
PAGINAS_PT = [RAIZ / "pt" / "index.html", RAIZ / "pt" / "coaches" / "index.html", RAIZ / "guia" / "guia_manalab_pt.html"]

# Código «pt» sin -BR en atributos, JSON-LD (cadena o lista) y sitemap.
PT_SECO = [
    re.compile(r"""\b(?:hreflang|lang)\s*=\s*["']pt["']""", re.I),
    re.compile(r"""["']inLanguage["']\s*:\s*(?:"pt"|\[[^\]]*"pt"[^\]]*\])""", re.I),
    re.compile(r"""\bog:locale(?::alternate)?["'][^>]*content=["']pt(?!_BR)[^"']*["']|content=["']pt(?!_BR)[^"']*["'][^>]*og:locale""", re.I),
]

# Formas europeas (palabra entera, sin distinguir mayúsculas). Cada una con su forma brasileña.
EUROPEAS = [
    r"equipas?", r"ecrã", r"ecrãs", r"ficheiros?", r"utilizad(?:or|ores|ora|oras)", r"registos?",
    r"partilh\w+", r"definições", r"ratos?", r"telemóve(?:l|is)", r"contactos?", r"factos?",
    r"transfer(?:ir|e|em|ido|ida|ência|ências)", r"secç(?:ão|ões)", r"óptim[oa]s?", r"acç(?:ão|ões)",
    r"direcç(?:ão|ões)", r"actua(?:l|is)", r"objectos?", r"tu", r"teus?", r"tuas?", r"ti", r"contigo",
    r"guardar", r"guardad[oa]s?", r"guardá-l[oa]s?", r"meter", r"mete", r"meto",
    r"experimenta", r"selecciona\w*", r"descarrega\w*", r"aceder", r"utilizar", r"utiliza",
    r"ligação", r"ligações", r"estás", r"tens", r"podes", r"queres", r"precisas", r"o meu", r"a minha", r"os meus", r"as minhas",
    # «a + infinitivo» en lugar de gerundio: estar a fazer -> estar fazendo
    r"(?:estar|estou|estás|está|estão|estamos|estava|estavam|ficar|fica|ficam|continuar|continua|continuam|andar|anda) a [a-zçãõé]+(?:ar|er|ir|or)",
]
RE_EUROPEAS = re.compile(r"(?<!\w)(?:%s)(?!\w)" % "|".join(reversed(EUROPEAS)), re.I)


class Visible(HTMLParser):
    """Texto visible de una página (incluidos alt, title, aria-label, content de meta y JSON-LD), sin URLs ni clases."""

    def __init__(self):
        super().__init__()
        self.trozos = []
        self._skip = 0
        self._ld = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            if tag == "script" and a.get("type") == "application/ld+json":
                self._ld = True
            else:
                self._skip += 1
        for k in ("alt", "title", "aria-label", "placeholder", "content"):
            v = a.get(k)
            if v and not v.startswith(("http", "/", "#")):
                self.trozos.append(v)

    def handle_endtag(self, tag):
        if tag == "script" and self._ld:
            self._ld = False
        elif tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip and data.strip():
            self.trozos.append(data)


def visible(ruta):
    p = Visible()
    p.feed(Path(ruta).read_text(encoding="utf-8"))
    return "\n".join(p.trozos)


def archivos_web():
    for f in sorted(RAIZ.rglob("*")):
        if f.suffix in (".html", ".xml") and not any(parte in SALTAR for parte in f.relative_to(RAIZ).parts):
            yield f


def formas_europeas(texto):
    return sorted({m.group(0).lower() for m in RE_EUROPEAS.finditer(texto)})


class CodigosDeIdioma(unittest.TestCase):
    def test_ningun_pt_a_secas(self):
        fallos = []
        for f in archivos_web():
            t = f.read_text(encoding="utf-8")
            for patron in PT_SECO:
                for m in patron.finditer(t):
                    fallos.append(f"{f.relative_to(RAIZ)}: {m.group(0)[:80]}")
        self.assertEqual(fallos, [], "el portugués es pt-BR (lang, hreflang, inLanguage, og:locale)")

    def test_paginas_pt_declaran_pt_br(self):
        for f in PAGINAS_PT:
            t = f.read_text(encoding="utf-8")
            self.assertRegex(t, r'<html lang="pt-BR">', f.name)
            self.assertRegex(t, r'hreflang="pt-BR"', f.name)
            self.assertIn("pt_BR", t, f.name)

    def test_sitemap_usa_pt_br(self):
        t = (RAIZ / "sitemap.xml").read_text(encoding="utf-8")
        self.assertNotRegex(t, r'hreflang="pt"')
        self.assertIn('hreflang="pt-BR" href="https://manalab.es/pt/"', t)
        self.assertIn('hreflang="pt-BR" href="https://manalab.es/pt/coaches/"', t)
        self.assertIn('hreflang="pt-BR" href="https://manalab.es/guia/guia_manalab_pt.html"', t)

    def test_las_urls_no_cambian(self):
        for ruta in ("pt/index.html", "pt/coaches/index.html", "guia/guia_manalab_pt.html"):
            self.assertTrue((RAIZ / ruta).is_file(), ruta)
        t = (RAIZ / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("<loc>https://manalab.es/pt/</loc>", t)
        self.assertNotIn("pt-BR/", t)


class TextoBrasil(unittest.TestCase):
    def test_sin_formas_de_portugal(self):
        for f in PAGINAS_PT:
            with self.subTest(pagina=f.name):
                self.assertTrue(f.is_file())
                self.assertEqual(formas_europeas(visible(f)), [], f"formas de Portugal en {f.relative_to(RAIZ)}")

    def test_citas_de_la_interfaz_como_en_pt_json(self):
        coaches = visible(RAIZ / "pt" / "coaches" / "index.html")
        guia = visible(RAIZ / "guia" / "guia_manalab_pt.html")
        self.assertIn("Sua nota de coach para esta partida…", coaches)
        self.assertIn("tela Equipe", coaches)
        self.assertIn("tela Equipe", guia)
        self.assertIn("Coloco", guia)          # pt.json: Meto -> Coloco
        self.assertIn("Meu plano", guia)       # pt.json: Mi plan -> Meu plano

    def test_el_detector_detecta(self):
        malo = ("A Equipa partilha o ficheiro no ecrã do telemóvel. O utilizador clica em definições e vai a transferir "
                "o registo. Estás a fazer a tua parte. Guardar ficheiro. A secção óptima, a acção, a direcção actual, o objecto. "
                "Entre em contacto: o facto é que o rato é teu.")
        encontrado = formas_europeas(malo)
        for esperado in ("equipa", "partilha", "ficheiro", "ecrã", "telemóvel", "utilizador", "definições", "transferir",
                         "registo", "estás a fazer", "tua", "guardar", "secção", "óptima", "acção", "direcção", "actual",
                         "objecto", "contacto", "facto", "rato", "teu"):
            self.assertIn(esperado, encontrado, esperado)
        bueno = ("A equipe compartilha o arquivo na tela do celular. O usuário clica em configurações e vai baixar o relatório. "
                 "Você está fazendo a sua parte. Salvar arquivo. Entre em contato. O ManaLab guarda suas mãos.")
        self.assertEqual(formas_europeas(bueno), [])


class SeoCheckExigePtBr(unittest.TestCase):
    def ejecutar(self, cambio=None):
        with tempfile.TemporaryDirectory() as tmp:
            copia = Path(tmp) / "sitio"
            shutil.copytree(RAIZ, copia, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            if cambio:
                cambio(copia)
            r = subprocess.run([sys.executable, str(RAIZ / "tools" / "seo_check.py"), str(copia)], capture_output=True, text=True)
            return r.returncode, r.stdout + r.stderr

    def test_pasa_con_pt_br(self):
        rc, salida = self.ejecutar()
        self.assertEqual(rc, 0, salida)

    def test_falla_con_lang_pt(self):
        def cambio(c):
            p = c / "pt" / "coaches" / "index.html"
            p.write_text(p.read_text(encoding="utf-8").replace('<html lang="pt-BR">', '<html lang="pt">'), encoding="utf-8")
        rc, salida = self.ejecutar(cambio)
        self.assertEqual(rc, 1, salida)
        self.assertIn('lang="pt"', salida)

    def test_falla_con_hreflang_pt(self):
        def cambio(c):
            for p in c.rglob("*.html"):
                t = p.read_text(encoding="utf-8")
                if 'hreflang="pt-BR"' in t:
                    p.write_text(t.replace('hreflang="pt-BR"', 'hreflang="pt"'), encoding="utf-8")
        rc, salida = self.ejecutar(cambio)
        self.assertEqual(rc, 1, salida)
        self.assertIn('hreflang="pt"', salida)

    def test_falla_con_sitemap_pt(self):
        def cambio(c):
            p = c / "sitemap.xml"
            p.write_text(p.read_text(encoding="utf-8").replace('hreflang="pt-BR"', 'hreflang="pt"'), encoding="utf-8")
        rc, salida = self.ejecutar(cambio)
        self.assertEqual(rc, 1, salida)
        self.assertIn("sitemap", salida)


if __name__ == "__main__":
    unittest.main()
