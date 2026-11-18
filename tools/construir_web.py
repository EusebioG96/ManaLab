#!/usr/bin/env python3
"""Genera las páginas HTML de la web a partir de plantillas (ML-197). Solo biblioteca estándar.

Uso:
    python3 tools/construir_web.py              escribe los .html en la raíz del repositorio
    python3 tools/construir_web.py --comprobar  no escribe; sale con 1 si algún .html no coincide con lo generado
    python3 tools/construir_web.py --salida DIR genera en DIR en vez de en la raíz

Versión: version.json (raíz) es la única fuente de la versión actual. Donde una plantilla o página dice ``{{VERSION}}``
se escribe su campo "version" (p. ej. 2.3.2) al generar. Solo se usa para lo que es «la versión actual / la descarga»;
las menciones a versiones pasadas (historial) se escriben tal cual.

Disposición (todo bajo plantillas/, que no es HTML y por eso no se indexa):
    plantillas/paginas/<ruta>.pagina   contenido de cada página; se publica en <ruta>.html
    plantillas/<nombre>.tpl            plantilla común (cabecera, pie o CSS); una línea ``{{@N}}`` es el hueco N
    plantillas/<nombre>/<N>.<v>.txt    valor v del hueco N (cada línea termina en salto de línea)

En una página, ``{{> nombre N=v N=v}}`` inserta la plantilla ``nombre``. Los huecos no citados
toman la variante ``a``. Una plantilla puede insertar otra con una línea ``{{> otra}}``. Más detalle en tools/README.md.
"""
import argparse
import html
import json
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from construir_learn import aplicar_learn  # noqa: E402
from construir_mdn import aplicar_mdn  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_PLANTILLAS = "plantillas"
CARPETA_PAGINAS = "paginas"
SUFIJO_PAGINA = ".pagina"
SUFIJO_PLANTILLA = ".tpl"
VARIANTE_POR_DEFECTO = "a"  # la variante que no hace falta citar en la página

# {{> nombre 3=b 7=c }}: inserta una plantilla con las variantes elegidas
_DIRECTIVA = re.compile(r"\{\{> (\w+)((?: \d+=\w+)*)\}\}")
_HUECO = re.compile(r"\{\{@(\d+)\}\}")
MARCA_VERSION = "{{VERSION}}"  # se sustituye por la versión de version.json en cada página generada
ARCHIVO_VERSION = "version.json"  # fuente única de la versión actual (lo escribe generar_version_json.py)
_VERSION_VALIDA = re.compile(r"\d{1,4}\.\d{1,5}\.\d{1,6}")
ARCHIVO_CONTENIDO = "contenido.json"  # fuente única de los enlaces de Metafy (lo lee también la app)
CAMPOS_ENLACE = ("enlace_apoyo_metafy", "enlace_suscripcion_ia")
HOSTS_ENLACE = ("metafy.gg", "manalab.es")  # el propio host o un subdominio, como valida la app
MAX_ENLACE = 300  # tope de caracteres de un enlace
RUTA_LOGO_METAFY = "/img/metafy.svg"  # logotipo de Metafy sin retocar
# {{SUSCRIPCION_IA clave="valor" ...}} y {{APOYO_METAFY clave="valor" ...}}: bloques que dependen de contenido.json
_BLOQUE_ENLACE = re.compile(r'\{\{(SUSCRIPCION_IA|APOYO_METAFY)((?: \w+="[^"]*")*)\}\}')
_PARAMETRO = re.compile(r'(\w+)="([^"]*)"')

# {{EVENTO:tipo}} o {{EVENTO:tipo:posicion}}: nombre del evento de GoatCounter de un botón (ML-280).
# Esquema único: <tipo>-<pagina>-<idioma>[-<posicion>]; página e idioma salen de la ruta de la página que se genera.
TIPOS_EVENTO = ("descarga", "descarga-movil", "compartir-movil", "correo-movil", "anuncio-casa")
IDIOMAS_RUTA = ("es", "pt", "ja")  # carpetas de idioma; el resto de rutas son inglés
_EVENTO = re.compile(r"\{\{EVENTO:([a-z-]+)(?::([a-z0-9]+))?\}\}")
_PAGINA_DE_RUTA = {"": "portada", "detailed-logs": "logs", "registro-detallado": "logs", "aprender": "learn"}  # lo demás: su carpeta

# Vídeo del lanzamiento de la 3.0 (ML-281). Cuando existan los dos archivos, las cuatro portadas lo usan en el héroe en lugar del vídeo
# actual (sin tocar plantillas); mientras falte alguno, se queda el de ahora. Para activarlo basta con subir los dos archivos.
VIDEO_LANZAMIENTO = "video/manalab-3.0.mp4"
POSTER_LANZAMIENTO = "video/manalab-3.0-poster.jpg"
PORTADAS_CON_VIDEO = ("index.html", "es/index.html", "pt/index.html", "ja/index.html")
_POSTER_HERO = re.compile(r"((?:\.\./|/)?)video/hero/manalab-hero-\w+-poster\.jpg")
_FUENTE_WEBM_HERO = re.compile(r'<source src="(?:\.\./|/)?video/hero/manalab-hero-\w+\.webm" type="video/webm"/>\n')
_FUENTE_MP4_HERO = re.compile(r"((?:\.\./|/)?)video/hero/manalab-hero-\w+\.mp4")

# Cita de Luis Salvatto junto al botón de descarga de las portadas en inglés y español (ML-281). Interruptor APAGADO: apagado, la cita
# no existe en el HTML generado (no se oculta con CSS: no se escribe). Para encenderla, ponlo en True y rellena el enlace a su post.
MOSTRAR_CITA_SALVATTO = False
ENLACE_CITA_SALVATTO = ""  # https del post de Luis Salvatto; vacío = la firma sale sin enlace
CITAS_SALVATTO = {
    "en": ("\u201cI already started to use ManaLab and I really like it.\u201d",
           "Luis Salvatto, Pro Tour champion and 2017\u201318 Player of the Year"),
    "es": ("\u00abYa he empezado a usar ManaLab y me gusta mucho.\u00bb",
           "Luis Salvatto, campe\u00f3n de Pro Tour y Jugador del A\u00f1o 2017-18."),
}
_MARCA_CITA = re.compile(r"\{\{CITA_SALVATTO\}\}\n?")  # en la plantilla, en una línea propia

# «Envíame el enlace por correo» en el teléfono (ML-295). El campo lo envía a un servidor propio (Cloudflare Worker, POST /enlace-descarga).
# Mientras la dirección esté vacía NO se pinta el campo y las portadas se quedan con el bloque de siempre. Cuando el servidor esté
# desplegado, se pone aquí (https, p. ej. "https://registro-ia.eusebiog76.workers.dev/enlace-descarga") y se regenera la web.
URL_ENLACE_CORREO = "https://registro-ia.eusebiog76.workers.dev/enlace-descarga"
# Textos del campo por idioma (W5: no se cambian sin OK de Eusebio; pt y ja, traducidos con el mismo tono y pendientes de su revisión).
TEXTOS_CORREO = {
    "en": {"txt": "ManaLab runs on your PC. Email yourself the download link.", "boton": "Send", "marcador": "you@example.com",
           "nota": "One email, nothing else. We don't keep your address.", "ok": "Sent! Check your inbox.",
           "correo": "That email address doesn't look right.", "limite": "Too many requests. Try again in a few minutes.",
           "red": "Couldn't send it. Check your connection and try again."},
    "es": {"txt": "ManaLab funciona en tu PC. Envíate el enlace de descarga por correo.", "boton": "Enviar", "marcador": "tu@correo.com",
           "nota": "Un solo correo y nada más. No guardamos tu dirección.", "ok": "¡Enviado! Revisa tu bandeja de entrada.",
           "correo": "Ese correo no parece válido.", "limite": "Demasiados envíos. Inténtalo de nuevo en unos minutos.",
           "red": "No se pudo enviar. Revisa tu conexión e inténtalo de nuevo."},
    "pt": {"txt": "O ManaLab funciona no seu PC. Receba o link de download por e-mail.", "boton": "Enviar", "marcador": "voce@email.com",
           "nota": "Um único e-mail e nada mais. Não guardamos o seu endereço.", "ok": "Enviado! Confira sua caixa de entrada.",
           "correo": "Esse e-mail não parece válido.", "limite": "Muitos envios. Tente de novo em alguns minutos.",
           "red": "Não foi possível enviar. Verifique sua conexão e tente de novo."},
    "ja": {"txt": "ManaLabはPCで動きます。ダウンロードリンクをメールで送りましょう。", "boton": "送信", "marcador": "you@example.com",
           "nota": "メールは1通だけ送ります。アドレスは保存しません。", "ok": "送信しました。受信トレイをご確認ください。",
           "correo": "メールアドレスが正しくないようです。", "limite": "送信回数が多すぎます。数分後にもう一度お試しください。",
           "red": "送信できませんでした。接続を確認して、もう一度お試しください。"},
}
# {{CORREO_MOVIL txt="…"}}: en la plantilla del bloque móvil de las portadas; sin servidor, el párrafo de siempre (txt); con él, el campo.
# La marca y, justo debajo, el botón «Enviarme el enlace» (compartir) de la plantilla: con el campo de correo activo sobra (ML-296).
_BLOQUE_CORREO = re.compile(r'\{\{CORREO_MOVIL((?: \w+="[^"]*")*)\}\}(\n<p><button class="boton prim" data-compartir [^\n]*</button></p>)?')


def _leer(ruta: Path) -> str:
    """Lee un archivo de texto UTF-8 sin tocar los saltos de línea."""
    with open(ruta, encoding="utf-8", newline="") as f:
        return f.read()


def _lineas_con_salto(texto: str) -> list[str]:
    """Parte un texto en líneas sin salto; '' son cero líneas (las líneas del archivo terminan en salto)."""
    return texto.split("\n")[:-1] if texto else []


def expandir_plantilla(carpeta: Path, nombre: str, variantes: dict[str, str]) -> str:
    """Devuelve el texto de la plantilla ``nombre`` con sus huecos rellenos.

    ``variantes`` asigna a cada hueco (número como texto) la variante elegida; los que falten usan la ``a``.
    """
    ruta = carpeta / (nombre + SUFIJO_PLANTILLA)
    if not ruta.is_file():
        raise ValueError(f"plantilla inexistente: {nombre}")
    salida: list[str] = []
    for linea in _lineas_con_salto(_leer(ruta)):
        anidada = _DIRECTIVA.fullmatch(linea)
        if anidada is not None:  # una plantilla puede insertar otra en una línea propia (ML-329: css_cabecera)
            salida.append(_expandir_directiva(carpeta, anidada))
            continue
        hueco = _HUECO.fullmatch(linea)
        if hueco is None:
            salida.append(linea)
            continue
        numero = hueco.group(1)
        variante = variantes.get(numero, VARIANTE_POR_DEFECTO)
        valor = carpeta / nombre / f"{numero}.{variante}.txt"
        if not valor.is_file():
            raise ValueError(f"{nombre}: no existe la variante {variante} del hueco {numero}")
        salida.extend(_lineas_con_salto(_leer(valor)))
    return "\n".join(salida)


def _expandir_directiva(carpeta: Path, coincidencia: re.Match) -> str:
    """Resuelve una directiva ``{{> nombre N=v}}`` de una página."""
    variantes = dict(par.split("=") for par in coincidencia.group(2).split())
    return expandir_plantilla(carpeta, coincidencia.group(1), variantes)


def generar_pagina(carpeta: Path, fuente: str) -> str:
    """Devuelve el HTML de una página: su contenido con las plantillas insertadas."""
    return _DIRECTIVA.sub(lambda m: _expandir_directiva(carpeta, m), fuente)


def fuentes_de_pagina(raiz: Path, relativa: Path) -> list[Path]:
    """Archivos fuente que dan el texto de la página ``relativa`` (un .html): su .pagina y las variantes de hueco que cita.

    No incluye las partes fijas de las plantillas (.tpl), porque las comparten otras páginas.
    """
    carpeta = raiz / CARPETA_PLANTILLAS
    pagina = carpeta / CARPETA_PAGINAS / relativa.with_suffix(SUFIJO_PAGINA)
    fuentes = [pagina]
    for directiva in _DIRECTIVA.finditer(_leer(pagina)):
        nombre = directiva.group(1)
        variantes = dict(par.split("=") for par in directiva.group(2).split())
        for linea in _lineas_con_salto(_leer(carpeta / (nombre + SUFIJO_PLANTILLA))):
            hueco = _HUECO.fullmatch(linea)
            if hueco is not None:
                variante = variantes.get(hueco.group(1), VARIANTE_POR_DEFECTO)
                fuentes.append(carpeta / nombre / f"{hueco.group(1)}.{variante}.txt")
    return fuentes


def leer_version(raiz: Path) -> str:
    """Versión actual (p. ej. ``2.3.2``) según version.json de ``raiz``. Lanza ValueError si falta o no es válida."""
    ruta = raiz / ARCHIVO_VERSION
    try:
        version = str(json.loads(_leer(ruta)).get("version", ""))
    except (OSError, ValueError, AttributeError) as error:
        raise ValueError(f"no se puede leer la versión de {ruta}: {error}") from error
    if not _VERSION_VALIDA.fullmatch(version):
        raise ValueError(f"versión no válida en {ruta}: {version!r}")
    return version


def enlace_valido(valor: object) -> bool:
    """Un enlace de contenido.json: vacío, o https a metafy.gg / manalab.es (o subdominio), sin usuario ni puerto, de 300 como mucho."""
    if valor == "":
        return True
    if not isinstance(valor, str) or len(valor) > MAX_ENLACE or not valor.startswith("https://"):
        return False
    try:
        partes = urlparse(valor)
        host = partes.hostname or ""
        return any(host == h or host.endswith("." + h) for h in HOSTS_ENLACE) \
            and partes.username is None and partes.password is None and partes.port is None
    except ValueError:
        return False


def leer_enlaces(raiz: Path) -> dict[str, str]:
    """Los enlaces de Metafy de contenido.json de ``raiz`` (``""`` = sin enlace). Lanza ValueError si falta el archivo o un enlace no vale."""
    ruta = raiz / ARCHIVO_CONTENIDO
    try:
        datos = json.loads(_leer(ruta))
    except (OSError, ValueError) as error:
        raise ValueError(f"no se puede leer {ruta}: {error}") from error
    enlaces = {}
    for campo in CAMPOS_ENLACE:
        valor = datos.get(campo, "") if isinstance(datos, dict) else None
        if not enlace_valido(valor):
            raise ValueError(f"{ruta}: {campo} no es válido: {valor!r}")
        enlaces[campo] = valor
    return enlaces


def _atributos(texto: str) -> dict[str, str]:
    """Los ``clave="valor"`` de un bloque de enlace."""
    return dict(_PARAMETRO.findall(texto))


def _bloque_suscripcion_ia(parametros: dict[str, str], enlace: str) -> str:
    """Botón «Suscribirme en Metafy» con el enlace de suscripción; sin enlace, el texto «muy pronto» (nunca un botón muerto)."""
    if not enlace:
        return f'<span class="pronto">{parametros["pronto"]}</span>'
    estilo = f' style="{parametros["estilo"]}"' if parametros.get("estilo") else ""
    clase = f' class="{parametros["clase"]}"' if parametros.get("clase") else ""
    return (f'<a{clase} href="{html.escape(enlace, quote=True)}" data-goatcounter-click="apoyo" '
            f'data-goatcounter-title="{parametros["medicion"]}" rel="noopener"{estilo} target="_blank"><span>{parametros["texto"]}</span></a>')


def _bloque_apoyo_metafy(parametros: dict[str, str], enlace: str) -> str:
    """Bloque «Apoya el proyecto» con el botón grande «Apoyar en Metafy»; sin enlace no se genera nada."""
    if not enlace:
        return ""
    return ('<div class="apoyo uno" id="apoyo">\n<div>\n'
            f'<div class="eti">{parametros["eti"]}</div>\n<h3>{parametros["titulo"]}</h3>\n<p>{parametros["texto"]}</p>\n'
            f'<div class="acciones" style="margin-top:18px"><a class="b-metafy" data-goatcounter-click="apoyo" '
            f'data-goatcounter-title="{parametros["medicion"]}" href="{html.escape(enlace, quote=True)}" rel="noopener" target="_blank">'
            f'<img src="{RUTA_LOGO_METAFY}" alt="" width="39" height="30"/><span>{parametros["boton"]}</span></a></div>\n'
            '</div>\n</div>')


def aplicar_enlaces(fuente: str, enlaces: dict[str, str]) -> str:
    """Resuelve los bloques ``{{SUSCRIPCION_IA ...}}`` y ``{{APOYO_METAFY ...}}`` de una página con los enlaces de contenido.json."""
    def resolver(coincidencia: re.Match) -> str:
        parametros = _atributos(coincidencia.group(2))
        if coincidencia.group(1) == "SUSCRIPCION_IA":
            return _bloque_suscripcion_ia(parametros, enlaces["enlace_suscripcion_ia"])
        return _bloque_apoyo_metafy(parametros, enlaces["enlace_apoyo_metafy"])
    return _BLOQUE_ENLACE.sub(resolver, fuente)


def pagina_e_idioma(relativa: Path) -> tuple[str, str]:
    """(página, idioma) de una ruta generada, p. ej. es/coaches/index.html -> ("coaches", "es"); guia/guia_manalab_ja.html -> ("guia", "ja")."""
    partes = list(relativa.with_suffix("").parts)
    if partes[0] == "guia" and len(partes) == 2 and partes[1].startswith("guia_manalab_"):
        return "guia", partes[1].removeprefix("guia_manalab_")
    idioma = "en"
    if partes[0] in IDIOMAS_RUTA:
        idioma = partes.pop(0)
    if partes and partes[-1] == "index":
        partes.pop()
    clave = "-".join(partes)
    return _PAGINA_DE_RUTA.get(clave, clave), idioma


def bloque_correo(idioma: str, url: str, texto_actual: str) -> str:
    """El bloque del teléfono para pedir el enlace por correo: sin ``url`` es el párrafo de siempre (``texto_actual``); con ella, el
    formulario con los textos de ``idioma``. Lanza ValueError si la dirección no es https o el idioma no tiene textos."""
    if not url:
        return f'<p class="movil-txt">{texto_actual}</p>'
    if not url.startswith("https://") or len(url) > MAX_ENLACE or any(c in url for c in ' "<>\r\n'):
        raise ValueError(f"URL_ENLACE_CORREO no es una dirección https válida: {url!r}")
    t = {k: html.escape(v, quote=True) for k, v in TEXTOS_CORREO[idioma].items()}
    return (f'<form class="movil-correo" data-correo-url="{html.escape(url, quote=True)}" data-idioma="{idioma}" '
            f'data-evento="{{{{EVENTO:correo-movil}}}}" data-ok="{t["ok"]}" data-e-correo="{t["correo"]}" '
            f'data-e-limite="{t["limite"]}" data-e-red="{t["red"]}" novalidate>\n'
            f'<p class="movil-txt" id="movil-correo-txt">{t["txt"]}</p>\n'
            f'<div class="movil-correo-fila"><input aria-labelledby="movil-correo-txt" autocapitalize="off" autocomplete="email" '
            f'inputmode="email" maxlength="120" name="correo" placeholder="{t["marcador"]}" required type="email"/>'
            f'<button class="boton prim" type="submit"><span>{t["boton"]}</span></button></div>\n'
            f'<p class="movil-correo-nota">{t["nota"]}</p>\n'
            '<p aria-live="polite" class="movil-correo-estado" role="status"></p>\n</form>')


def aplicar_correo(fuente: str, relativa: Path, url: str | None = None) -> str:
    """Resuelve los ``{{CORREO_MOVIL txt="…"}}`` de una portada (ver ``bloque_correo``); el idioma sale de la ruta.
    Sin ``url`` se usa ``URL_ENLACE_CORREO`` (leída al llamar, para que los tests puedan cambiarla). Con dirección, el formulario sustituye
    también al botón de compartir que sigue a la marca (ML-296); sin ella queda todo como estaba, el botón incluido."""
    _, idioma = pagina_e_idioma(relativa)
    url = URL_ENLACE_CORREO if url is None else url
    return _BLOQUE_CORREO.sub(lambda m: bloque_correo(idioma, url, _atributos(m.group(1))["txt"]) + ("" if url else m.group(2) or ""), fuente)


def aplicar_eventos(fuente: str, relativa: Path) -> str:
    """Resuelve los ``{{EVENTO:tipo[:posicion]}}`` de una página con su nombre de evento (tipo-pagina-idioma[-posicion])."""
    pagina, idioma = pagina_e_idioma(relativa)

    def resolver(coincidencia: re.Match) -> str:
        tipo, posicion = coincidencia.group(1), coincidencia.group(2)
        if tipo not in TIPOS_EVENTO:
            raise ValueError(f"{relativa.as_posix()}: tipo de evento desconocido: {tipo!r}")
        return "-".join([tipo, pagina, idioma] + ([posicion] if posicion else []))
    return _EVENTO.sub(resolver, fuente)


def bloque_cita(idioma: str, encendida: bool, enlace: str) -> str:
    """El HTML de la cita de Luis Salvatto (en o es), o ``""`` si el interruptor está apagado o la página no es en/es."""
    if not encendida or idioma not in CITAS_SALVATTO:
        return ""
    if enlace and not enlace.startswith("https://"):
        raise ValueError(f"el enlace de la cita no es https: {enlace!r}")
    frase, firma = CITAS_SALVATTO[idioma]
    firma = f'<a href="{html.escape(enlace, quote=True)}" rel="noopener" target="_blank">{firma}</a>' if enlace else firma
    return ('<figure class="cita-hero" style="margin:16px 0 0;max-width:46ch">'
            f'<blockquote style="margin:0;font-style:italic;color:var(--texto)">{frase}</blockquote>'
            f'<figcaption style="margin-top:6px;font-size:14px;color:var(--texto2)">{firma}</figcaption></figure>\n')


def aplicar_cita(fuente: str, relativa: Path) -> str:
    """Resuelve la marca ``{{CITA_SALVATTO}}`` de una portada: la cita si el interruptor está encendido y, si no, nada."""
    _, idioma = pagina_e_idioma(relativa)
    cita = bloque_cita(idioma, MOSTRAR_CITA_SALVATTO, ENLACE_CITA_SALVATTO)
    return _MARCA_CITA.sub(lambda _: cita, fuente)


def hay_video_lanzamiento(raiz: Path) -> bool:
    """¿Están el vídeo del lanzamiento y su póster en ``raiz``?"""
    return (raiz / VIDEO_LANZAMIENTO).is_file() and (raiz / POSTER_LANZAMIENTO).is_file()


def aplicar_video_lanzamiento(pagina: str, relativa: Path, raiz: Path) -> str:
    """En las cuatro portadas, cambia el vídeo y el póster del héroe por los del lanzamiento si existen (y quita la fuente WebM, que
    solo hay del vídeo actual). Conserva el prefijo de ruta de cada página («», «../» o «/»)."""
    if relativa.as_posix() not in PORTADAS_CON_VIDEO or not hay_video_lanzamiento(raiz):
        return pagina
    pagina = _POSTER_HERO.sub(lambda m: m.group(1) + POSTER_LANZAMIENTO, pagina)
    pagina = _FUENTE_WEBM_HERO.sub("", pagina)
    return _FUENTE_MP4_HERO.sub(lambda m: m.group(1) + VIDEO_LANZAMIENTO, pagina)


def listar_paginas(raiz: Path) -> list[Path]:
    """Rutas (relativas a la raíz) de los .html que se generan, ordenadas."""
    base = raiz / CARPETA_PLANTILLAS / CARPETA_PAGINAS
    return sorted(p.relative_to(base).with_suffix(".html") for p in base.rglob("*" + SUFIJO_PAGINA))


def construir(raiz: Path, destino: Path) -> list[Path]:
    """Genera todas las páginas de ``raiz`` en ``destino`` y devuelve las rutas relativas escritas.

    No reescribe un archivo cuyo contenido ya es idéntico (así no cambian las fechas ni se ensucia git).
    """
    carpeta = raiz / CARPETA_PLANTILLAS
    version = leer_version(raiz)
    enlaces = leer_enlaces(raiz)
    escritas = []
    for relativa in listar_paginas(raiz):
        fuente = _leer(carpeta / CARPETA_PAGINAS / relativa.with_suffix(SUFIJO_PAGINA))
        expandida = aplicar_learn(generar_pagina(carpeta, fuente), pagina_e_idioma(relativa)[1], raiz)   # ML-324: páginas Learn
        pagina = aplicar_correo(aplicar_enlaces(expandida, enlaces), relativa)
        pagina = aplicar_mdn(pagina, relativa, pagina_e_idioma(relativa)[1], raiz)   # ML-325: huecos de anuncio de MDN (antes de los eventos: el anuncio de casa lleva el suyo)
        pagina = aplicar_video_lanzamiento(aplicar_cita(aplicar_eventos(pagina, relativa), relativa), relativa, raiz)
        datos = pagina.replace(MARCA_VERSION, version).encode("utf-8")
        salida = destino / relativa
        if salida.is_file() and salida.read_bytes() == datos:
            escritas.append(relativa)
            continue
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_bytes(datos)
        escritas.append(relativa)
    return escritas


def paginas_distintas(raiz: Path, generado: Path) -> list[Path]:
    """Páginas de ``generado`` cuyo contenido difiere del .html de ``raiz`` (o que no existen en ella)."""
    distintas = []
    for relativa in listar_paginas(raiz):
        actual = raiz / relativa
        if not actual.is_file() or actual.read_bytes() != (generado / relativa).read_bytes():
            distintas.append(relativa)
    return distintas


def principal(argumentos: list[str] | None = None) -> int:
    """Punto de entrada de la línea de órdenes; devuelve el código de salida."""
    analizador = argparse.ArgumentParser(description="Genera la web desde plantillas")
    analizador.add_argument("--comprobar", action="store_true", help="no escribe; falla si el repositorio no coincide")
    analizador.add_argument("--salida", type=Path, help="carpeta de destino (por defecto, la raíz del repositorio)")
    opciones = analizador.parse_args(argumentos)
    if opciones.comprobar:
        with tempfile.TemporaryDirectory() as temporal:
            construir(RAIZ, Path(temporal))
            distintas = paginas_distintas(RAIZ, Path(temporal))
        for relativa in distintas:
            print(f"desactualizada: {relativa.as_posix()}")
        return 1 if distintas else 0
    escritas = construir(RAIZ, opciones.salida or RAIZ)
    print(f"{len(escritas)} páginas generadas")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
