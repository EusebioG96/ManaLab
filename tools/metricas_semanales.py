#!/usr/bin/env python3
"""Métricas semanales de ManaLab (prototipo, ML-057).

Descargas: API pública de releases de GitHub (download_count por asset, acumulado). Se guarda una foto con fecha en un
JSON acumulado y la cifra semanal es la resta con la foto de hace ~7 días.
Visitas: GoatCounter solo se puede leer sin credenciales si el sitio activa «Allow using the visitor counter»; si no,
el informe lo dice como hueco y el resto sigue. /counter/<ruta>.json devuelve el TOTAL acumulado de la ruta como texto
con separador de miles ({"count": "1,234", "count_unique": ...}); la cifra semanal es la resta entre fotos. Sin tokens.

Páginas: la lista sale de https://manalab.es/sitemap.xml (las nuevas entran solas; si no se puede leer, del sitemap.xml
local y de RUTAS_PRINCIPALES). GoatCounter responde 404 con {"count": "0"} a una ruta sin visitas: eso es «0 visitas», no
un fallo. Aparte se comprueba que cada página del sitemap responde (siguiendo redirecciones: 3xx no es 404).
Eventos: el contador público solo cuenta por RUTA del evento (data-goatcounter-click / g.count({path})), no por título.
Se leen las rutas conocidas y, por si algún día la ruta lleva el idioma, la rejilla prefijo-idioma; se agrupan por prefijo.
Todo es de solo lectura (GET/HEAD); no toca la web publicada.

Uso:  python tools/metricas_semanales.py --historico RUTA.json [--sin-guardar] [--fuente auto|http|gh]
                                           [--sin-visitas] [--sin-paginas]
      Carga el JSON (si existe), añade la foto de hoy (sustituye la del mismo día), lo guarda y escribe el resumen en stdout.
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
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


SITIO = "https://manalab.es"
URL_SITEMAP = SITIO + "/sitemap.xml"
RUTAS_PRINCIPALES = ["/", "/es/", "/safety/", "/es/seguridad/", "/privacy/", "/sorteo/"]
IDIOMAS = ("en", "es", "pt", "fr", "de", "it", "ja", "ko", "zh")
RE_IDIOMA = re.compile(r"^(.+)-(" + "|".join(IDIOMAS) + r")$")
# Rutas de evento que emite la web hoy (data-goatcounter-click y g.count de descarga.js).
EVENTOS_RUTA = ["descarga", "compartir-movil", "descarga-movil", "aviso-sorteo"]
# Prefijos de título/ruta con idioma (descarga-*, compartir-movil*, descarga-mtgo-*, descarga-coaches-*).
EVENTOS_PREFIJOS = ["descarga-portada", "descarga-aviso", "descarga-mtgo", "descarga-coaches", "descarga-movil",
                    "descarga-movil-coaches", "compartir-movil", "compartir-movil-coaches"]
EVENTOS_IDIOMAS = ("en", "es", "pt")


def eventos_candidatos():
    """Nombres de evento a consultar: rutas conocidas + rejilla prefijo-idioma. Sin duplicados."""
    nombres = list(EVENTOS_RUTA)
    for pref in EVENTOS_PREFIJOS:
        nombres += [f"{pref}-{i}" for i in EVENTOS_IDIOMAS]
    return list(dict.fromkeys(nombres))


def leer_sitemap(local=None, url=URL_SITEMAP):
    """Texto del sitemap: el publicado y, si no se puede leer, el local. Devuelve (texto|None, origen)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "manalab-metricas"}), timeout=20) as r:
            texto = r.read().decode("utf-8")
        if "<loc>" in texto:
            return texto, "web"
    except (urllib.error.URLError, OSError, ValueError):
        pass
    try:
        return Path(local or Path(__file__).resolve().parent.parent / "sitemap.xml").read_text(encoding="utf-8"), "local"
    except OSError:
        return None, "ninguno"


def rutas_visitas(sitemap=None, texto=None):
    """'TOTAL' + rutas principales + TODAS las páginas del sitemap (texto, o el fichero `sitemap`). Sin duplicados."""
    rutas = ["TOTAL"] + RUTAS_PRINCIPALES
    try:
        if texto is None:
            texto = Path(sitemap or Path(__file__).resolve().parent.parent / "sitemap.xml").read_text(encoding="utf-8")
        for loc in re.findall(r"<loc>\s*https?://[^/<\s]+(/[^<\s#]*)\s*</loc>", texto):
            if loc not in rutas:
                rutas.append(loc)
    except OSError:
        pass
    return rutas


def url_con_barra(url):
    """Una URL de página sin barra final ni extensión se consulta con barra (evita el 301 de GitHub Pages)."""
    p = urllib.parse.urlsplit(url)
    if not p.path.endswith("/") and "." not in p.path.rsplit("/", 1)[-1]:
        p = p._replace(path=p.path + "/")
    return urllib.parse.urlunsplit(p)


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def comprobar_pagina(url, max_saltos=5):
    """Estado de una página siguiendo redirecciones a mano (solo HEAD, con GET si el servidor no admite HEAD).
    Devuelve {url, final, estado, saltos}; estado: ok (200), redireccion (3xx que acaba en 200), no_encontrada (404), error."""
    actual, saltos, opener = url_con_barra(url), 0, urllib.request.build_opener(_SinRedireccion)
    for _ in range(max_saltos + 1):
        codigo, destino = None, None
        for metodo in ("HEAD", "GET"):
            try:
                with opener.open(urllib.request.Request(actual, method=metodo, headers={"User-Agent": "manalab-metricas"}), timeout=20) as r:
                    codigo = r.status
                break
            except urllib.error.HTTPError as e:
                codigo, destino = e.code, e.headers.get("Location") if e.headers else None
                if codigo in (403, 405, 501) and metodo == "HEAD":
                    continue
                break
            except (urllib.error.URLError, OSError, ValueError):
                return {"url": url, "final": actual, "estado": "error", "saltos": saltos}
        if codigo is not None and 300 <= codigo < 400 and destino:
            actual, saltos = urllib.parse.urljoin(actual, destino), saltos + 1
            continue
        estado = {200: "ok", 404: "no_encontrada"}.get(codigo, "error")
        if estado == "ok" and saltos:
            estado = "redireccion"
        return {"url": url, "final": actual, "estado": estado, "saltos": saltos, "codigo": codigo}
    return {"url": url, "final": actual, "estado": "error", "saltos": saltos}


def comprobar_paginas(rutas):
    """Comprueba las páginas (rutas con '/' inicial; se ignora TOTAL). Devuelve la lista de resultados."""
    return [comprobar_pagina(SITIO + r) for r in rutas if r.startswith("/")]


def leer_visita(ruta, base=GOATCOUNTER):
    """Contador público de una ruta. Devuelve (numero|None, motivo). None = hueco.
    GoatCounter contesta 404 + {"count": "0"} a una ruta sin visitas: es un 0 real, no un fallo."""
    url = f"{base}/counter/{urllib.parse.quote(ruta, safe='')}.json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "manalab-metricas"}), timeout=20) as r:
            n = interpretar_contador(json.load(r))
        return (n, "ok") if n is not None else (None, "respuesta sin 'count'")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            try:
                n = interpretar_contador(json.loads(e.read().decode("utf-8")))
            except (OSError, ValueError, AttributeError):
                n = None
            if n is not None:
                return n, "ok (sin visitas registradas)"
        return None, f"HTTP {e.code}" + (" (contador público desactivado)" if e.code == 403 else "")
    except (urllib.error.URLError, OSError, ValueError) as e:
        return None, f"error: {e}"


def leer_visitas(rutas=None, base=GOATCOUNTER):
    """({ruta: total acumulado}, motivo_del_fallo|None). Si la primera ruta da 403/error no se insiste con las demás."""
    visitas, motivo = {}, None
    for ruta in (rutas or rutas_visitas()):
        n, m = leer_visita(ruta, base)
        if n is None:
            motivo = motivo or f"{ruta}: {m}"
            if not visitas:
                break
            continue
        visitas[ruta] = n
    return visitas, motivo


def leer_eventos(nombres=None, base=GOATCOUNTER):
    """({evento: total acumulado}, motivo|None). Mismo criterio que las visitas (403/error en el primero: no se insiste)."""
    return leer_visitas(nombres or eventos_candidatos(), base)


def agrupar_eventos(eventos):
    """{prefijo: {"total": n, "idiomas": {idioma: n}}} a partir de {nombre: n}. «descarga-mtgo-es» -> prefijo
    «descarga-mtgo», idioma «es»; un nombre sin idioma (p. ej. «descarga») es su propio prefijo, sin desglose."""
    grupos = {}
    for nombre, n in (eventos or {}).items():
        m = RE_IDIOMA.match(nombre)
        pref, idioma = (m.group(1), m.group(2)) if m else (nombre, None)
        g = grupos.setdefault(pref, {"total": 0, "idiomas": {}})
        g["total"] += n
        if idioma:
            g["idiomas"][idioma] = g["idiomas"].get(idioma, 0) + n
    return grupos


def interpretar_contador(datos):
    """El JSON del contador trae {"count": "1,234", "count_unique": ...}: texto con separador de miles (coma, punto,
    espacio, espacio duro o fino). Es el total acumulado de la ruta, no el de un periodo."""
    bruto = re.sub(r"\D", "", str(datos.get("count", "")))
    return int(bruto) if bruto else None


# ---------- lógica pura (probada sin red) ----------
def foto(releases, hoy=None, visitas=None, eventos=None):
    """Foto con fecha: {fecha, versiones: {tag: {asset: download_count}}}. Los borradores no cuentan."""
    versiones = {}
    for rel in releases:
        if rel.get("draft"):
            continue
        versiones[rel["tag_name"]] = {a["name"]: int(a.get("download_count", 0)) for a in rel.get("assets", [])}
    f = {"fecha": (hoy or datetime.now(timezone.utc).date()).isoformat(), "versiones": versiones}
    if visitas:
        f["visitas"] = dict(visitas)
    if eventos:
        f["eventos"] = dict(eventos)
    return f


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


def diferencia_visitas(actual, previa, campo="visitas"):
    """Resta por ruta (o por evento, con campo="eventos") de los totales acumulados. None si la foto previa no lo trae.
    Nunca negativa."""
    if not previa or not previa.get(campo) or not actual.get(campo):
        return None
    if campo == "eventos":  # un evento que la foto previa no traía (nuevo nombre o idioma) cuenta entero, como un asset nuevo
        return {r: max(0, n - previa[campo].get(r, 0)) for r, n in actual[campo].items()}
    return {r: max(0, n - previa[campo][r]) for r, n in actual[campo].items() if r in previa[campo]}


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


def resumen_markdown(actual, previa, dias, visitas=None, eventos=None, paginas=None):
    """`visitas` / `eventos` = (dict nombre->total, motivo_fallo) o None si no se consultó; `paginas` = lista de comprobar_pagina."""
    t = totales(actual)
    L = [f"# ManaLab: métricas a {actual['fecha']}", "", "## Descargas (GitHub, acumulado)",
         f"- Total ZIP: **{t['descargas']}** (ZIP con versión {t['zip_version']}, ZIP estable {t['zip_estable']})",
         f"- Archivos .sha256: {t['sha256']} (indicio APROXIMADO de actualizaciones desde la app: puede incluir comprobaciones manuales y descargas repetidas)"]
    tags = sorted(actual["versiones"], key=lambda k: [int(x) for x in re.findall(r"\d+", k)])
    if tags:
        ult = tags[-1]
        z = sum(c for n, c in actual["versiones"][ult].items() if clasificar(n) in ("zip_version", "zip_estable"))
        L.insert(3, f"- Última versión ({ult}): **{z}** descargas de ZIP")
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
    # Si la comparación no cubre 7 días, el resumen lo dice (también en visitas y eventos).
    periodo = "esta semana" if dias in (None, DIAS_SEMANA) else f"en {dias} días"
    L += ["", "## Visitas (GoatCounter, acumulado)"]
    if previa is not None and dias not in (None, DIAS_SEMANA):
        L.append(f"- Comparación con la foto del {previa['fecha']}: cubre {dias} días, no 7.")
    v, motivo = visitas if visitas else ({}, "no consultado")
    if not v:
        L.append("- Visitas: sin datos (activa el contador público en GoatCounter)" + (f" [{motivo}]" if motivo else ""))
    else:
        dv = diferencia_visitas(actual, previa)
        L.append(f"- Total del sitio: **{v.get('TOTAL', 'n/d')}**" + (f" (+{dv['TOTAL']} {periodo})" if dv and "TOTAL" in dv else " (sin foto de visitas anterior)"))
        for r, n in v.items():
            if r != "TOTAL":
                L.append(f"- {r}: {n}" + (f" (+{dv[r]})" if dv and r in dv else ""))
        if motivo:
            L.append(f"- Aviso: faltan rutas ({motivo})")
    if eventos is not None:
        L += ["", "## Eventos (GoatCounter, acumulado)"]
        ev, ev_motivo = eventos
        if not ev:
            L.append("- Eventos: sin datos" + (f" [{ev_motivo}]" if ev_motivo else ""))
        else:
            de = diferencia_visitas(actual, previa, "eventos")
            nuevos = lambda k: f" (+{de[k]} {periodo})" if de and k in de else ""
            hay = False
            for pref, g in sorted(agrupar_eventos(ev).items()):
                if not g["total"]:
                    continue
                hay = True
                idiomas = ", ".join(f"{i} {n}" for i, n in sorted(g["idiomas"].items()) if n)
                dif = ""
                if de:
                    # diferencia del grupo = suma de las diferencias de sus miembros
                    miembros = [k for k in de if (RE_IDIOMA.match(k).group(1) if RE_IDIOMA.match(k) else k) == pref]
                    dif = f" (+{sum(de[k] for k in miembros)} {periodo})"
                L.append(f"- {pref}: **{g['total']}**{dif}" + (f" [{idiomas}]" if idiomas else ""))
            if not hay:
                L.append("- Sin eventos registrados todavía.")
            if ev_motivo:
                L.append(f"- Aviso: faltan eventos ({ev_motivo})")
            L.append("- Nota: el contador público solo cuenta por ruta del evento; los títulos con idioma (descarga-mtgo-es...) "
                     "no se pueden leer sin token, así que el desglose por idioma solo aparece si la ruta del evento lleva el idioma.")
    if paginas is not None:
        L += ["", "## Páginas del sitemap (¿responden?)"]
        malas = [p for p in paginas if p["estado"] in ("no_encontrada", "error")]
        redir = [p for p in paginas if p["estado"] == "redireccion"]
        L.append(f"- {len(paginas)} páginas comprobadas; {len(paginas) - len(malas) - len(redir)} responden 200 directo"
                 + (f", {len(redir)} con redirección (3xx, no es un fallo)" if redir else "") + ".")
        for p in redir:
            L.append(f"  - {p['url']} -> {p['final']} ({p['saltos']} salto(s))")
        for p in malas:
            L.append(f"- PROBLEMA: {p['url']} -> {'404 no encontrada' if p['estado'] == 'no_encontrada' else 'error de conexión o estado inesperado'}")
    L += ["", "Nota: el botón de la web y la actualización desde la app bajan el mismo asset (ManaLab-X.Y.Z-portable.zip), así que no se separan en GitHub."]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--historico", "--historial", dest="historico", default="metricas_historial.json",
                    help="JSON acumulado de fotos (se crea si no existe)")
    ap.add_argument("--sin-guardar", action="store_true")
    ap.add_argument("--fuente", choices=("auto", "http", "gh"), default="auto")
    ap.add_argument("--sin-visitas", action="store_true", help="no consultar GoatCounter (ni visitas ni eventos)")
    ap.add_argument("--sin-paginas", action="store_true", help="no comprobar que las páginas del sitemap responden")
    a = ap.parse_args(argv)
    hoy = datetime.now(timezone.utc).date()
    texto, origen = leer_sitemap()
    if origen != "web":
        print(f"AVISO: sitemap leído de: {origen}", file=sys.stderr)
    rutas = rutas_visitas(texto=texto)
    visitas = None if a.sin_visitas else leer_visitas(rutas)
    eventos = leer_eventos() if visitas and visitas[0] else None  # si las visitas fallan (403), no se insiste con los eventos
    paginas = None if a.sin_paginas else comprobar_paginas(rutas)
    actual = foto(leer_releases(a.fuente), hoy, visitas[0] if visitas else None, eventos[0] if eventos else None)
    historial = cargar_historial(a.historico)
    previa, dias = elegir_previa(historial, hoy)
    print(resumen_markdown(actual, previa, dias, visitas, eventos, paginas), end="")
    if not a.sin_guardar:
        escribir_historial(a.historico, guardar_foto(historial, actual))
    return 0


if __name__ == "__main__":
    sys.exit(main())
