#!/usr/bin/env python3
"""Comprobador SEO estático de manalab.es (solo biblioteca estándar).

Uso:  python3 tools/seo_check.py [raíz_del_repo]
Sale con código 1 si encuentra algún problema.
"""
import json
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

SITE = "https://manalab.es"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9", "xhtml": "http://www.w3.org/1999/xhtml"}
DESC_MIN, DESC_MAX = 50, 170
SKIP_DIRS = {".git", "tools", "node_modules"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.title = ""
        self._in_title = False
        self._in_ld = False
        self._ld = ""
        self.jsonld = []
        self.desc = None
        self.robots = None
        self.canonical = []
        self.alternates = {}
        self.h1 = 0
        self.refs = []   # (tag, attr, value)
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "meta":
            n = a.get("name", "").lower()
            if n == "description":
                self.desc = a.get("content", "")
            elif n == "robots":
                self.robots = a.get("content", "").lower()
        elif tag == "link":
            rel = a.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonical.append(a.get("href", ""))
            elif "alternate" in rel and a.get("hreflang"):
                self.alternates[a["hreflang"].lower()] = a.get("href", "")
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld, self._ld = True, ""
        if tag in ("a", "link", "area") and "href" in a and not (tag == "link" and "alternate" in a.get("rel", "")):
            self.refs.append((tag, "href", a["href"]))
        if tag in ("img", "script", "source", "video", "iframe", "audio") and a.get("src"):
            self.refs.append((tag, "src", a["src"]))
        if tag == "video" and a.get("poster"):
            self.refs.append((tag, "poster", a["poster"]))
        if tag == "link" and a.get("rel", "").lower() in ("icon", "apple-touch-icon", "stylesheet") and a.get("href"):
            pass  # ya contado arriba como href

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_ld:
            self._in_ld = False
            self.jsonld.append(self._ld)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_ld:
            self._ld += data


def url_to_file(root, url):
    """URL absoluta del sitio -> fichero que GitHub Pages serviría (o None)."""
    p = urlparse(url)
    if p.netloc and p.netloc != "manalab.es":
        return None
    path = unquote(p.path) or "/"
    f = root / path.lstrip("/")
    if path.endswith("/"):
        f = f / "index.html"
    if f.is_file():
        return f
    if f.is_dir() and (f / "index.html").is_file():
        return f / "index.html"
    return None


def file_to_url(root, f):
    rel = f.relative_to(root).as_posix()
    if rel == "index.html":
        return SITE + "/"
    if rel.endswith("/index.html"):
        return SITE + "/" + rel[: -len("index.html")]
    return SITE + "/" + rel


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent).resolve()
    errors, notes = [], []
    err = lambda m: errors.append(m)

    pages = {}
    for f in sorted(root.rglob("*.html")):
        if any(part in SKIP_DIRS for part in f.relative_to(root).parts):
            continue
        pg = Page()
        pg.feed(f.read_text(encoding="utf-8"))
        pages[f] = pg

    def rel(f):
        return f.relative_to(root).as_posix()

    # ---- 404 con noindex
    f404 = root / "404.html"
    if f404 not in pages:
        err("404.html no existe")
    elif "noindex" not in (pages[f404].robots or ""):
        err("404.html: falta <meta name=robots content=noindex>")

    # ---- enlaces y recursos internos
    for f, pg in pages.items():
        for tag, attr, val in pg.refs:
            v = val.strip()
            if not v or v.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            p = urlparse(v)
            if v.startswith("//") and p.netloc != "manalab.es":
                continue  # URL con protocolo relativo a un dominio externo
            if p.scheme in ("http", "https") and p.netloc != "manalab.es":
                continue
            if p.scheme in ("http", "https"):
                target = url_to_file(root, v)
            elif v.startswith("#"):
                if v[1:] and v[1:] not in pg.ids:
                    err(f"{rel(f)}: ancla {v} sin id correspondiente")
                continue
            else:
                path = unquote(p.path)
                base = root if path.startswith("/") else f.parent
                t = (base / path.lstrip("/")).resolve() if path else f
                if path.endswith("/") or t.is_dir():
                    t = t / "index.html"
                target = t if t.is_file() else None
            if target is None or not Path(target).is_file():
                err(f"{rel(f)}: <{tag} {attr}={val}> no resuelve a un fichero existente")
            elif p.fragment and Path(target) in pages and p.fragment not in pages[Path(target)].ids:
                err(f"{rel(f)}: {val} apunta a un ancla inexistente")

    # ---- sitemap
    sm_urls = {}
    sm = root / "sitemap.xml"
    if not sm.is_file():
        err("sitemap.xml no existe")
    else:
        try:
            tree = ET.parse(sm)
            for u in tree.getroot().findall("sm:url", NS):
                loc = u.findtext("sm:loc", namespaces=NS).strip()
                alts = {x.get("hreflang").lower(): x.get("href") for x in u.findall("xhtml:link", NS)}
                sm_urls[loc] = alts
        except ET.ParseError as e:
            err(f"sitemap.xml no es XML válido: {e}")
    if len(sm_urls) and len(sm_urls) != len(set(sm_urls)):
        err("sitemap.xml tiene <loc> duplicados")
    for loc, alts in sm_urls.items():
        if url_to_file(root, loc) is None:
            err(f"sitemap: {loc} no corresponde a ningún fichero")
        for h, href in alts.items():
            if url_to_file(root, href) is None:
                err(f"sitemap: alternate {h} {href} no existe")
    robots = root / "robots.txt"
    if not robots.is_file() or f"Sitemap: {SITE}/sitemap.xml" not in robots.read_text():
        err("robots.txt no referencia el sitemap")

    # ---- páginas indexables
    indexable = {}
    for f, pg in pages.items():
        if "noindex" in (pg.robots or ""):
            continue
        if f.name.startswith("google") and not pg.title:  # fichero de verificación de Search Console
            continue
        indexable[f] = pg
    urls_by_file = {f: file_to_url(root, f) for f in indexable}
    file_by_url = {u: f for f, u in urls_by_file.items()}

    titles = {}
    for f, pg in indexable.items():
        n = rel(f)
        url = urls_by_file[f]
        if url not in sm_urls:
            err(f"{n}: indexable pero no está en sitemap.xml ({url})")
        # canonical
        if len(pg.canonical) != 1:
            err(f"{n}: debe tener exactamente 1 canonical (tiene {len(pg.canonical)})")
        elif pg.canonical[0] != url:
            err(f"{n}: canonical {pg.canonical[0]} no apunta a sí misma ({url})")
        # título único
        t = " ".join(pg.title.split())
        if not t:
            err(f"{n}: falta <title>")
        elif t in titles:
            err(f"{n}: título duplicado con {titles[t]}")
        titles.setdefault(t, n)
        # descripción
        d = (pg.desc or "").strip()
        if not d:
            err(f"{n}: falta meta description")
        elif not DESC_MIN <= len(d) <= DESC_MAX:
            err(f"{n}: meta description de {len(d)} caracteres (rango {DESC_MIN}-{DESC_MAX})")
        # H1
        if pg.h1 != 1:
            err(f"{n}: {pg.h1} etiquetas H1 (debe haber exactamente 1)")
        # lang
        if not pg.lang:
            err(f"{n}: falta atributo lang en <html>")
        # JSON-LD
        for blob in pg.jsonld:
            try:
                json.loads(blob)
            except ValueError as e:
                err(f"{n}: JSON-LD inválido: {e}")
        # viewport/og básicos
        # hreflang
        alts = pg.alternates
        if alts:
            if "x-default" not in alts:
                err(f"{n}: hreflang sin x-default")
            selfl = [h for h, href in alts.items() if href == url and h != "x-default"]
            if len(selfl) != 1:
                err(f"{n}: el conjunto hreflang debe incluir un idioma que apunte a sí misma")
            else:
                if (pg.lang or "").lower() != selfl[0]:
                    err(f"{n}: lang=\"{pg.lang}\" no coincide con su hreflang ({selfl[0]})")
            for h, href in alts.items():
                tf = file_by_url.get(href)
                if tf is None:
                    err(f"{n}: hreflang {h} -> {href} no es una página indexable existente")
                    continue
                other = indexable[tf].alternates
                if other != alts:
                    err(f"{n}: hreflang no recíproco/idéntico con {rel(tf)}")
            # coherencia con el sitemap
            if url in sm_urls and sm_urls[url] != alts:
                err(f"{n}: los alternates del sitemap difieren de los de la página")
        else:
            notes.append(f"{n}: sin hreflang (página única, aceptado)")

    # ---- resumen
    print(f"Páginas HTML analizadas: {len(pages)} (indexables: {len(indexable)}); URLs en sitemap: {len(sm_urls)}")
    for n in notes:
        print("  nota:", n)
    if errors:
        print(f"\nFALLOS ({len(errors)}):")
        for e in errors:
            print("  -", e)
        return 1
    print("OK: sin problemas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
