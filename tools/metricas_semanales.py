#!/usr/bin/env python3
"""Métricas semanales de ManaLab (prototipo, ML-057).

Descargas: API pública de releases de GitHub (download_count por asset, acumulado). Se guarda una foto con fecha en un
JSON acumulado y la cifra semanal es la resta con la foto de hace ~7 días.
Visitas: GoatCounter solo se puede leer sin credenciales si el sitio activa «allow using the visitor counter»; si no,
el informe lo dice como hueco. No usa tokens ni contraseñas.

Uso:  python tools/metricas_semanales.py [--historial RUTA.json] [--sin-guardar] [--fuente auto|http|gh]
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

REPO = "EusebioG96/ManaLab"
URL_RELEASES = f"https://api.github.com/repos/{REPO}/releases?per_page=100"
GOATCOUNTER = "https://manalab.goatcounter.com"
DIAS_SEMANA = 7
RE_ZIP_VERSION = re.compile(r"^ManaLab-\d+\.\d+\.\d+-portable\.zip$")


# ---------- lectura (red) ----------
def leer_releases(fuente="auto"):
    """Lista de releases (JSON de la API pública, sin credenciales). `gh` solo se usa como respaldo del proxy."""
    errores = []
    if fuente in ("auto", "http"):
        try:
            req = urllib.request.Request(URL_RELEASES, headers={"Accept": "application/vnd.github+json", "User-Agent": "manalab-metricas"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except (urllib.error.URLError, OSError, ValueError) as e:
            errores.append(f"http: {e}")
    if fuente in ("auto", "gh"):
        try:
            out = subprocess.run(["gh", "api", f"repos/{REPO}/releases", "--paginate"], capture_output=True, text=True, timeout=60, check=True).stdout
            return json.loads(out) if out.lstrip().startswith("[") else sum((json.loads(x) for x in out.splitlines() if x.strip()), [])
        except (subprocess.SubprocessError, OSError, ValueError) as e:
            errores.append(f"gh: {e}")
    raise RuntimeError("no se pudo leer la API de releases (" + "; ".join(errores) + ")")


def leer_visitas(ruta="TOTAL", base=GOATCOUNTER):
    """Contador público de GoatCounter. Devuelve (numero|None, motivo). None = hueco (no hay acceso sin credenciales)."""
    url = f"{base}/counter/{ruta.replace('/', '%2F')}.json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "manalab-metricas"}), timeout=20) as r:
            datos = json.load(r)
        return interpretar_contador(datos), "ok"
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}" + (" (contador público desactivado)" if e.code == 403 else "")
    except (urllib.error.URLError, OSError, ValueError) as e:
        return None, f"error: {e}"


def interpretar_contador(datos):
    """El JSON del contador trae {"count": "1 234", "count_unique": ...}: texto con separadores de miles."""
    bruto = str(datos.get("count", "")).replace(" ", "").replace("\xa0", "").replace(" ", "").replace(",", "").replace(".", "")
    return int(bruto) if bruto.isdigit() else None


# ---------- lógica pura (probada sin red) ----------
def foto(releases, hoy=None):
    """Foto con fecha: {fecha, versiones: {tag: {asset: download_count}}}. Los borradores no cuentan."""
    versiones = {}
    for rel in releases:
        if rel.get("draft"):
            continue
        versiones[rel["tag_name"]] = {a["name"]: int(a.get("download_count", 0)) for a in rel.get("assets", [])}
    return {"fecha": (hoy or datetime.now(timezone.utc).date()).isoformat(), "versiones": versiones}


def clasificar(nombre):
    """zip_version = ManaLab-X.Y.Z-portable.zip (lo que bajan el botón de la web Y la app al actualizar);
    zip_estable = ManaLab-portable.zip; sha256 = suma de verificación (la app la baja en cada actualización); otro."""
    if RE_ZIP_VERSION.match(nombre):
        return "zip_version"
    if nombre == "ManaLab-portable.zip":
        return "zip_estable"
    if nombre.endswith(".sha256"):
        return "sha256"
    return "otro"


def totales(f):
    t = {"zip_version": 0, "zip_estable": 0, "sha256": 0, "otro": 0}
    for assets in f["versiones"].values():
        for nombre, n in assets.items():
            t[clasificar(nombre)] += n
    t["descargas"] = t["zip_version"] + t["zip_estable"] + t["otro"]  # sin los .sha256
    return t


def diferencia(actual, previa):
    """Resta asset a asset (download_count es acumulado). Un asset nuevo cuenta entero; si baja (asset reemplazado), 0."""
    por_version = {}
    for tag, assets in actual["versiones"].items():
        antes = (previa or {}).get("versiones", {}).get(tag, {})
        d = {n: max(0, c - antes.get(n, 0)) for n, c in assets.items()}
        por_version[tag] = d
    return {"fecha": actual["fecha"], "versiones": por_version}


def elegir_previa(historial, hoy):
    """La foto más cercana a hace 7 días entre las anteriores a `hoy`. Devuelve (foto|None, dias)."""
    anteriores = [f for f in historial if f["fecha"] < hoy.isoformat()]
    if not anteriores:
        return None, None

    def distancia(f):
        return abs((hoy - date.fromisoformat(f["fecha"])).days - DIAS_SEMANA)
    f = min(anteriores, key=distancia)
    return f, (hoy - date.fromisoformat(f["fecha"])).days


def guardar_foto(historial, nueva):
    """Una foto por día: si ya hay una de la misma fecha, se sustituye."""
    resto = [f for f in historial if f["fecha"] != nueva["fecha"]]
    return sorted(resto + [nueva], key=lambda f: f["fecha"])


def cargar_historial(ruta):
    p = Path(ruta)
    if not p.exists():
        return []
    datos = json.loads(p.read_text(encoding="utf-8"))
    return datos.get("fotos", []) if isinstance(datos, dict) else []


def escribir_historial(ruta, historial):
    p = Path(ruta)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"esquema": 1, "fotos": historial}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def resumen_markdown(actual, previa, dias, visitas=None):
    t = totales(actual)
    L = [f"# ManaLab: métricas a {actual['fecha']}", "", "## Descargas (GitHub, acumulado)",
         f"- Total ZIP: **{t['descargas']}** (ZIP con versión {t['zip_version']}, ZIP estable {t['zip_estable']})",
         f"- Archivos .sha256: {t['sha256']} (la app los baja al actualizar: indicio de actualizaciones)"]
    if previa is None:
        L += ["", "## Semana", "- Sin foto anterior: esta es la primera. La semana que viene habrá diferencia."]
    else:
        d = diferencia(actual, previa)
        td = totales(d)
        nota = "" if dias == DIAS_SEMANA else f" (la foto anterior es de hace {dias} días, no 7)"
        L += ["", f"## Desde {previa['fecha']}{nota}",
              f"- ZIP nuevos: **{td['descargas']}** (con versión {td['zip_version']}, estable {td['zip_estable']})",
              f"- .sha256 nuevos: {td['sha256']}"]
        nuevas = [tag for tag in actual["versiones"] if tag not in previa["versiones"]]
        if nuevas:
            L.append("- Versiones nuevas: " + ", ".join(nuevas))
    L += ["", "## Por versión (ZIP con versión + estable, acumulado)"]
    for tag, assets in sorted(actual["versiones"].items(), key=lambda kv: [int(x) for x in re.findall(r"\d+", kv[0])], reverse=True):
        zips = sum(c for n, c in assets.items() if clasificar(n) in ("zip_version", "zip_estable"))
        extra = ""
        if previa is not None:
            extra = f" (+{sum(c for n, c in diferencia(actual, previa)['versiones'][tag].items() if clasificar(n) in ('zip_version', 'zip_estable'))})"
        L.append(f"- {tag}: {zips}{extra}")
    L += ["", "## Visitas (GoatCounter)"]
    if visitas is None or visitas[0] is None:
        L.append("- Sin datos: " + (visitas[1] if visitas else "no consultado") + ". Hace falta activar el contador público o un token de API (paso de Eusebio).")
    else:
        L.append(f"- Total de visitas (contador público): {visitas[0]}")
    L += ["", "Nota: el botón de la web y la actualización desde la app bajan el mismo asset (ManaLab-X.Y.Z-portable.zip), así que no se separan en GitHub."]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--historial", default="metricas_historial.json")
    ap.add_argument("--sin-guardar", action="store_true")
    ap.add_argument("--fuente", choices=("auto", "http", "gh"), default="auto")
    ap.add_argument("--sin-visitas", action="store_true")
    a = ap.parse_args(argv)
    hoy = datetime.now(timezone.utc).date()
    actual = foto(leer_releases(a.fuente), hoy)
    historial = cargar_historial(a.historial)
    previa, dias = elegir_previa(historial, hoy)
    visitas = None if a.sin_visitas else leer_visitas()
    print(resumen_markdown(actual, previa, dias, visitas), end="")
    if not a.sin_guardar:
        escribir_historial(a.historial, guardar_foto(historial, actual))
    return 0


if __name__ == "__main__":
    sys.exit(main())
