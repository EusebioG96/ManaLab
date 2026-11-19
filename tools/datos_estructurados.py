#!/usr/bin/env python3
"""Datos estructurados invisibles (JSON-LD) de las páginas: BreadcrumbList y VideoObject (ML-341, SEO-07). Solo biblioteca estándar.

Los genera ``construir_web.py`` sobre el HTML ya completo; las plantillas no llevan nada a mano. Los textos salen de lo que la página
ya dice (enlaces de la web, título del bloque junto al vídeo, texto del vídeo): no se inventa ninguno.

La fecha de subida de cada vídeo es la del último commit que lo tocó. Como ese dato no está en un clon superficial, se guarda en
``plantillas/video_fechas.json``; para refrescarlo:  python3 tools/datos_estructurados.py --actualizar-fechas
"""
import html
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

SITIO = "https://manalab.es"
ARCHIVO_FECHAS = "plantillas/video_fechas.json"  # fecha (AAAA-MM-DD) del último commit de cada vídeo, por ruta relativa
PORTADAS = ("index.html", "es/index.html", "pt/index.html", "ja/index.html")  # sin migas: son el inicio de su idioma
# Inicio de cada idioma de las páginas interiores: (nombre que ya usa la web, ruta)
INICIO = {"en": ("Home", "/"), "es": ("Inicio", "/es/"), "pt": ("Início", "/pt/"), "ja": ("ホーム", "/ja/")}
# Inicio de las guías: el enlace «← …» que la propia guía lleva arriba (ruta y nombre)
_ENLACE_INICIO_GUIA = re.compile(r'<nav class="inicio"[^>]*><a href="([^"]*)"[^>]*>(.*?)</a>')
# Nombre de la página en la miga final: el texto con que la web ya la enlaza en su idioma (cabecera, pie o portada)
NOMBRE_PAGINA = {
    "magic-online/index.html": "Magic Online tracker", "es/magic-online/index.html": "Tracker para Magic Online",
    "detailed-logs/index.html": "How to enable detailed logs", "es/registro-detallado/index.html": "Cómo activar el registro detallado",
    "overlay/index.html": "Overlay and deck tracker", "es/overlay/index.html": "Overlay y deck tracker",
    "novedades/index.html": "What's new", "es/novedades/index.html": "Novedades",
    "safety/index.html": "Safety", "es/seguridad/index.html": "Seguridad", "privacy/index.html": "Privacidad",
    "coaches/index.html": "Guide for coaches", "es/coaches/index.html": "Guía para coaches", "pt/coaches/index.html": "Guia para coaches",
    "learn/index.html": "Learn", "es/aprender/index.html": "Aprender", "pt/aprender/index.html": "Aprender", "ja/learn/index.html": "学ぶ",
}
IDIOMA_DE_PAGINA = {"privacy/index.html": "es"}  # privacy/ está en español aunque cuelgue de la raíz
_BLOQUES = {"p", "div", "li", "h1", "h2", "h3", "section", "br"}  # al unir textos, estas etiquetas separan con un espacio
_VACIAS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _Nodo:
    def __init__(self, etiqueta: str, atributos: dict[str, str], padre: "_Nodo | None"):
        self.etiqueta, self.atributos, self.padre = etiqueta, atributos, padre
        self.items: list = []  # textos (str) y nodos hijos, en el orden del documento

    def contenido(self) -> str:
        """Texto del nodo y sus descendientes, con los espacios normalizados."""
        return " ".join("".join(i if isinstance(i, str) else i.contenido() + " " * (i.etiqueta in _BLOQUES) for i in self.items).split())

    def buscar(self, etiquetas: tuple[str, ...]) -> "_Nodo | None":
        """Primer descendiente (en orden de documento) con alguna de ``etiquetas``."""
        for hijo in (i for i in self.items if not isinstance(i, str)):
            if hijo.etiqueta in etiquetas:
                return hijo
            dentro = hijo.buscar(etiquetas)
            if dentro is not None:
                return dentro
        return None

    @property
    def hijos(self) -> list["_Nodo"]:
        return [i for i in self.items if not isinstance(i, str)]


class _Arbol(HTMLParser):
    """Árbol mínimo del HTML generado (las páginas son HTML bien cerrado)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = _Nodo("raiz", {}, None)
        self._actual = self.raiz
        self.videos: list[_Nodo] = []

    def handle_starttag(self, tag, attrs):
        nodo = _Nodo(tag, {k: (v or "") for k, v in attrs}, self._actual)
        self._actual.items.append(nodo)
        if tag == "video":
            self.videos.append(nodo)
        if tag not in _VACIAS:
            self._actual = nodo

    def handle_endtag(self, tag):
        nodo = self._actual
        while nodo.padre is not None and nodo.etiqueta != tag:
            nodo = nodo.padre
        if nodo.padre is not None and nodo.etiqueta == tag:
            self._actual = nodo.padre

    def handle_data(self, data):
        self._actual.items.append(data)


def url_de_pagina(relativa: Path) -> str:
    """URL absoluta de una página generada: ``es/coaches/index.html`` -> ``https://manalab.es/es/coaches/``."""
    ruta = relativa.as_posix()
    if ruta.endswith("index.html"):
        ruta = ruta[: -len("index.html")]
    return f"{SITIO}/{ruta}"


def _json_ld(grafo: list[dict]) -> str:
    """El ``<script type="application/ld+json">`` con ``grafo``; los «<» van escapados para que nada cierre el script."""
    cuerpo = json.dumps({"@context": "https://schema.org", "@graph": grafo}, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{cuerpo}</script>\n'


def migas(relativa: Path, arbol: _Arbol, pagina: str) -> dict | None:
    """BreadcrumbList (Inicio del idioma › página) de una página interior; ``None`` en las portadas y donde no toca."""
    ruta = relativa.as_posix()
    if ruta in PORTADAS or ruta.startswith("404") or ruta.startswith(("anuncio/", "google")):
        return None
    if ruta.startswith("guia/"):
        idioma = ruta.removeprefix("guia/guia_manalab_").removesuffix(".html")
        enlace = _ENLACE_INICIO_GUIA.search(pagina)
        inicio = (html.unescape(enlace.group(2)).removeprefix("←").strip(), enlace.group(1))
        final = arbol.raiz.buscar(("h1",))
        nombre = final.contenido() if final is not None else ""
    else:
        idioma = IDIOMA_DE_PAGINA.get(ruta) or (ruta.split("/")[0] if ruta.split("/")[0] in ("es", "pt", "ja") else "en")
        inicio, nombre = INICIO[idioma], NOMBRE_PAGINA[ruta]
    elementos = [(inicio[0], SITIO + inicio[1]), (nombre, url_de_pagina(relativa))]
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": n, "name": nombre_miga, "item": url} for n, (nombre_miga, url) in enumerate(elementos, 1)]}


def _nombre_del_video(video: _Nodo, arbol: _Arbol) -> str:
    """Título del bloque que acompaña al vídeo: el h3 de su ``.novedad``, el h2 de su sección o, si no hay, el h1 de la página."""
    nodo = video.padre
    while nodo is not None:
        clases = nodo.atributos.get("class", "").split()
        if "novedad" in clases:
            titulo = nodo.buscar(("h3",))
        elif nodo.etiqueta == "section":
            titulo = nodo.buscar(("h2",))
        else:
            titulo = None
        if titulo is not None:
            return titulo.contenido()
        nodo = nodo.padre
    titulo = arbol.raiz.buscar(("h1",))
    return titulo.contenido() if titulo is not None else ""


def _fuente_del_video(video: _Nodo) -> str:
    """Ruta del MP4 de un ``<video>`` (su ``src`` o la de su ``<source>`` MP4; el WebM del héroe no se usa)."""
    if video.atributos.get("src"):
        return video.atributos["src"]
    for hijo in video.hijos:
        if hijo.etiqueta == "source" and hijo.atributos.get("src", "").endswith(".mp4"):
            return hijo.atributos["src"]
    return ""


def leer_fechas(raiz: Path) -> dict[str, str]:
    """Fechas de subida de los vídeos (ruta relativa -> AAAA-MM-DD) de ``plantillas/video_fechas.json``."""
    return json.loads((raiz / ARCHIVO_FECHAS).read_text(encoding="utf-8"))


def videos(relativa: Path, arbol: _Arbol, raiz: Path) -> list[dict]:
    """Un VideoObject por cada ``<video>`` con póster de la página. Lanza ValueError si falta la fecha de un vídeo."""
    url_pagina, fechas, salida = url_de_pagina(relativa), leer_fechas(raiz), []
    for video in arbol.videos:
        poster, fuente = video.atributos.get("poster", ""), _fuente_del_video(video)
        descripcion = (video.atributos.get("title") or video.atributos.get("aria-label") or "").strip()
        if not poster or not fuente:  # sin póster no hay VideoObject (se anota en el informe)
            continue
        ruta_mp4 = urlparse(urljoin(url_pagina, fuente)).path.lstrip("/")
        if ruta_mp4 not in fechas:
            raise ValueError(f"{relativa.as_posix()}: no hay fecha de subida de {ruta_mp4} en {ARCHIVO_FECHAS}")
        salida.append({"@type": "VideoObject", "name": _nombre_del_video(video, arbol), "description": descripcion,
                       "thumbnailUrl": urljoin(url_pagina, poster), "contentUrl": urljoin(url_pagina, fuente),
                       "uploadDate": fechas[ruta_mp4]})
    repetidos = {v["name"] for v in salida if [w["name"] for w in salida].count(v["name"]) > 1}
    for v in salida:  # varios vídeos bajo el mismo título: cada uno se llama como su propio texto
        if v["name"] in repetidos:
            v["name"] = v["description"]
    return salida


def aplicar_datos_estructurados(pagina: str, relativa: Path, raiz: Path) -> str:
    """Inserta, justo antes de ``</head>``, el JSON-LD de migas y vídeos de la página (si le tocan). ``pagina`` es el HTML ya completo."""
    if "</head>" not in pagina:
        return pagina
    arbol = _Arbol()
    arbol.feed(pagina.split("</head>", 1)[1])
    grafo = [g for g in [migas(relativa, arbol, pagina.split("</head>", 1)[1])] if g] + videos(relativa, arbol, raiz)
    if not grafo:
        return pagina
    return pagina.replace("</head>", _json_ld(grafo) + "</head>", 1)


def actualizar_fechas(raiz: Path) -> None:
    """Reescribe ``video_fechas.json`` con la fecha del último commit de cada .mp4 de ``video/`` (``git log -1 --format=%cs``)."""
    fechas = {}
    for mp4 in sorted((raiz / "video").rglob("*.mp4")):
        ruta = mp4.relative_to(raiz).as_posix()
        fechas[ruta] = subprocess.run(["git", "log", "-1", "--format=%cs", "--", ruta], cwd=raiz, check=True,
                                      capture_output=True, text=True).stdout.strip()
    (raiz / ARCHIVO_FECHAS).write_text(json.dumps(fechas, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if "--actualizar-fechas" in sys.argv:
        actualizar_fechas(Path(__file__).resolve().parent.parent)
