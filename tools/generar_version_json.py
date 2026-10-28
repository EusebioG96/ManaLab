#!/usr/bin/env python3
"""Genera version.json (raíz de la web) con la última release pública de ManaLab (solo biblioteca estándar).

La app lee https://manalab.es/version.json cuando la API de GitHub le responde con el límite de consultas.
Dentro del Action la API se consulta autenticada (GITHUB_TOKEN), sin el límite de 60 peticiones/hora por IP.

Uso:  python3 tools/generar_version_json.py [salida]          (por defecto version.json en la raíz del repo)
Variables: GITHUB_REPOSITORY (por defecto EusebioG96/ManaLab), GITHUB_TOKEN (opcional).
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY") or "EusebioG96/ManaLab"
PREFIJO = f"https://github.com/{REPO}/releases/"
MAX_NOTAS = 8000
HEX64 = re.compile(r"\b[0-9a-f]{64}\b", re.I)


def _get(url, token=None, limite=2_000_000):
    cab = {"Accept": "application/vnd.github+json", "User-Agent": "manalab-version-json"}
    if token:
        cab["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=30) as r:
        return r.read(limite)


def notas_publicas(cuerpo):
    """Solo la cabecera y «Novedades / What's new» de la release; sin descarga, privacidad ni avisos del sistema."""
    trozos = re.split(r"\n(?=### )", str(cuerpo or "").replace("\r\n", "\n"))
    quedan = [trozos[0]] + [t for t in trozos[1:] if re.match(r"### (Novedades|What's new)", t, re.I)]
    texto = "\n\n".join("\n".join(ln for ln in t.splitlines() if not re.search(r"windows", ln, re.I)) for t in quedan)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()[:MAX_NOTAS]


def construir(release, leer_texto):
    """release: JSON de la API. leer_texto(url) -> texto del .sha256. Lanza ValueError si falta algo."""
    tag = str(release.get("tag_name") or "")
    version = tag.lstrip("vV")
    if not re.fullmatch(r"\d{1,4}\.\d{1,5}\.\d{1,6}", version):
        raise ValueError(f"etiqueta de versión no válida: {tag!r}")
    activos = {str(a.get("name", "")): a for a in release.get("assets") or []}
    zip_nombre = f"ManaLab-{version}-portable.zip"
    if zip_nombre not in activos:
        raise ValueError(f"la release no trae {zip_nombre}")
    descarga = str(activos[zip_nombre].get("browser_download_url") or "")
    url = str(release.get("html_url") or "")
    for u in (descarga, url):
        if not u.startswith(PREFIJO):
            raise ValueError(f"enlace fuera de las releases del repositorio: {u!r}")
    candidatos = []
    if zip_nombre + ".sha256" in activos:
        m = HEX64.search(leer_texto(activos[zip_nombre + ".sha256"]["browser_download_url"]))
        if m:
            candidatos.append(m.group(0).lower())
    digest = str(activos[zip_nombre].get("digest") or "")
    if digest.startswith("sha256:") and HEX64.fullmatch(digest[7:]):
        candidatos.append(digest[7:].lower())
    if not candidatos:
        raise ValueError("no hay SHA-256 publicado")
    if len(set(candidatos)) != 1:
        raise ValueError("el SHA-256 del .sha256 y el del ZIP no coinciden")
    return {"esquema": 1, "tag": f"v{version}", "version": version,
            "fecha": str(release.get("published_at") or "")[:10], "url": url, "descarga": descarga,
            "sha256": candidatos[0], "notas": notas_publicas(release.get("body"))}


PAGINAS = ("index.html", "es/index.html")


def reescribir_enlaces(html, version, descarga):
    """Pone la descarga directa en los enlaces con data-descarga y la versión en los span data-version."""
    if not re.fullmatch(r"\d{1,4}\.\d{1,5}\.\d{1,6}", version) or not descarga.startswith(PREFIJO + "download/"):
        raise ValueError("versión o enlace no válidos")

    def enlace(m):
        etiqueta = m.group(0)
        if re.search(r'\shref="[^"]*"', etiqueta):
            return re.sub(r'(\shref=")[^"]*(")', lambda h: h.group(1) + descarga + h.group(2), etiqueta, count=1)
        return etiqueta.replace("<a", f'<a href="{descarga}"', 1)

    html = re.sub(r"<a\b[^>]*\bdata-descarga\b[^>]*>", enlace, html)
    return re.sub(r"(<span data-version>)[^<]*(</span>)", lambda m: m.group(1) + version + m.group(2), html)


def actualizar_paginas(raiz, datos):
    for nombre in PAGINAS:
        ruta = Path(raiz) / nombre
        ruta.write_text(reescribir_enlaces(ruta.read_text(encoding="utf-8"), datos["version"], datos["descarga"]),
                        encoding="utf-8")


def main(argv):
    token = os.environ.get("GITHUB_TOKEN") or None
    release = json.loads(_get(f"https://api.github.com/repos/{REPO}/releases/latest", token))
    datos = construir(release, lambda u: _get(u, token, 4096).decode("utf-8", "replace"))
    salida = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent / "version.json"
    salida.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if len(argv) <= 1:
        actualizar_paginas(salida.parent, datos)
    print(f"{salida}: {datos['tag']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
