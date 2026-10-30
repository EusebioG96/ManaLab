#!/usr/bin/env python3
"""Comprobador de que «Windows» no vuelve a primer plano en manalab.es (solo biblioteca estándar).

Falla si «Windows» aparece en: <title>, meta description, og:description, twitter:description,
la «description» del JSON-LD SoftwareApplication o los botones de descarga de cualquier página.
Verifica además que la sección de descarga conserva el requisito «Windows 10/11», que el JSON-LD
es JSON válido y que "operatingSystem" sigue declarando Windows.

Uso:  python3 tools/windows_check.py [raíz_del_repo]
Sale con código 1 si encuentra algún problema.
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SKIP_DIRS = {".git", "tools", "node_modules"}
WIN = re.compile(r"windows", re.I)
# Requisito en la sección de descarga, por idioma de la portada.
REQ = {"en": "Windows 10 or 11", "es": "Windows 10 u 11"}


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.title = ""
        self._t = False
        self.meta = {}        # clave (description, og:description, twitter:description) -> texto
        self.ld = []
        self._ld = None
        self.buttons = []     # textos de los botones de descarga
        self._stack = []      # (tag, es_boton, texto acumulado)
        self.dl_text = ""     # texto de los pasos de descarga (div.pasos, bajo #descargar)
        self._dl_depth = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self._depth += 1
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._t = True
        elif tag == "meta":
            k = a.get("name") or a.get("property")
            if k in ("description", "og:description", "twitter:description"):
                self.meta[k] = a.get("content", "")
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._ld = ""
        if self._dl_depth is None and "pasos" in a.get("class", "").split():
            self._dl_depth = self._depth
        cls = a.get("class", "").split()
        if tag == "a" and ("descarga" in cls or a.get("id") == "enlace-descarga"):
            self._stack.append([self._depth, ""])

    def handle_endtag(self, tag):
        if tag == "title":
            self._t = False
        elif tag == "script" and self._ld is not None:
            self.ld.append(self._ld)
            self._ld = None
        if self._stack and self._stack[-1][0] == self._depth:
            self.buttons.append(" ".join(self._stack.pop()[1].split()))
        if self._dl_depth == self._depth:
            self._dl_depth = None
        self._depth -= 1

    def handle_data(self, d):
        if self._t:
            self.title += d
        if self._ld is not None:
            self._ld += d
        for s in self._stack:
            s[1] += d
        if self._dl_depth is not None:
            self.dl_text += d


# Páginas de seguridad: «Windows» solo puede salir en <section id="firma"> (donde hace falta), no en cabecera, título, entrada ni pie.
SEGURIDAD = ("safety/index.html", "es/seguridad/index.html")


class FueraDeFirma(HTMLParser):
    """Texto visible de <body> que queda fuera de <section id="firma">."""
    def __init__(self):
        super().__init__()
        self.fuera = ""
        self._body = False
        self._firma = None   # profundidad de la sección de la firma
        self._d = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("meta", "link", "img", "br", "input", "path"):
            return
        self._d += 1
        if tag == "body":
            self._body = True
        if tag == "section" and dict(attrs).get("id") == "firma":
            self._firma = self._d

    def handle_endtag(self, tag):
        if tag in ("meta", "link", "img", "br", "input", "path"):
            return
        if self._firma == self._d:
            self._firma = None
        self._d -= 1

    def handle_data(self, d):
        if self._body and self._firma is None:
            self.fuera += d


def software_apps(node):
    if isinstance(node, dict):
        if node.get("@type") == "SoftwareApplication":
            yield node
        for v in node.values():
            yield from software_apps(v)
    elif isinstance(node, list):
        for v in node:
            yield from software_apps(v)


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent).resolve()
    errors = []
    n_pages = 0
    for f in sorted(root.rglob("*.html")):
        rel = f.relative_to(root).as_posix()
        if any(part in SKIP_DIRS for part in f.relative_to(root).parts):
            continue
        pg = P()
        pg.feed(f.read_text(encoding="utf-8"))
        n_pages += 1
        if WIN.search(pg.title):
            errors.append(f"{rel}: «Windows» en <title>: {pg.title.strip()!r}")
        for k, v in pg.meta.items():
            if WIN.search(v):
                errors.append(f"{rel}: «Windows» en {k}: {v!r}")
        for b in pg.buttons:
            if WIN.search(b):
                errors.append(f"{rel}: «Windows» en botón de descarga: {b!r}")
        for i, blob in enumerate(pg.ld):
            try:
                data = json.loads(blob)
            except ValueError as e:
                errors.append(f"{rel}: JSON-LD #{i + 1} inválido: {e}")
                continue
            for app in software_apps(data):
                if WIN.search(str(app.get("description", ""))):
                    errors.append(f"{rel}: «Windows» en la description del JSON-LD SoftwareApplication")
                if "windows" not in str(app.get("operatingSystem", "")).lower():
                    errors.append(f"{rel}: el JSON-LD SoftwareApplication perdió operatingSystem Windows")
        # Portadas (las que tienen sección de descarga): deben conservar el requisito y tener botones.
        if 'id="descargar"' in f.read_text(encoding="utf-8"):
            req = REQ.get((pg.lang or "").lower())
            if req and req not in " ".join(pg.dl_text.split()):
                errors.append(f"{rel}: la sección de descarga ya no contiene el requisito «{req}»")
            if not pg.buttons:
                errors.append(f"{rel}: no se encontraron botones de descarga")
    for rel in SEGURIDAD:
        f = root / rel
        if not f.is_file():
            errors.append(f"{rel}: falta la página de seguridad")
            continue
        fp = FueraDeFirma()
        fp.feed(f.read_text(encoding="utf-8"))
        if WIN.search(fp.fuera):
            errors.append(f"{rel}: «Windows» fuera de la sección de la firma")
    # README
    rd = root / "README.md"
    if rd.is_file():
        first = rd.read_text(encoding="utf-8").split("\n\n")[0]
        if WIN.search(first):
            errors.append("README.md: «Windows» en el párrafo de presentación")
    print(f"Páginas HTML revisadas: {n_pages}")
    if errors:
        print(f"\nFALLOS ({len(errors)}):")
        for e in errors:
            print("  -", e)
        return 1
    print("OK: «Windows» fuera del primer plano y requisitos de descarga presentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
