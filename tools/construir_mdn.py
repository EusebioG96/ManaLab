"""Huecos de anuncio de MDN (Metafy) en las páginas generadas (ML-325, WEB-09). Solo biblioteca estándar.

Una página con anuncio escribe la marca ``{{HUECO_MDN}}`` (o ``{{HUECO_MDN:suelto}}`` dentro de la rejilla de Learn) donde va cada
hueco. ``aplicar_mdn`` la cambia por el ``<aside class="hueco-mdn">`` en el idioma de la página y, si la página tiene algún hueco,
añade UNA vez, antes de ``</head>``, su hoja de estilos (``plantillas/mdn/huecos.css``) y, antes de ``</body>``, el script de MDN (``async``) y el de ``/huecos_mdn.js``. Una página sin marcas no recibe ni
hueco ni script. Las páginas sin anuncio (``PAGINAS_SIN_ANUNCIO``) no pueden llevar marcas: si alguien la pone, la construcción falla.

La regla de dónde va cada hueco (WEB-09) está en ``tools/test_huecos_mdn.py`` (estática) y ``tools/test_huecos_mdn_navegador.py``
(con el alto real de cada sección).
"""
import html
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSS_HUECOS = Path("plantillas") / "mdn" / "huecos.css"   # estilos de los huecos: solo los lleva una página que tiene alguno (ML-329)

SCRIPT_MDN = "https://mdn.metafy.gg/embed.js"   # formatos leídos del propio script: leaderboard 728x90 (hueco de 728 px o más) y rectangle 300x250
SITIO_MDN = "mdn_obNMYPWbbmMClWCpy3Pss6JY"      # la misma clave que usa manalab.es/anuncio/ (el hueco de la app)
SCRIPT_HUECOS = "/huecos_mdn.js"                # lo propio: enseña el anuncio de casa si MDN no llega
PLAZO_MDN_MS = 6000                             # sin respuesta de MDN en este plazo se enseña el anuncio de casa (MDN abandona a los 4 s)
EVENTO_CASA = "anuncio-casa"                    # tipo del evento de GoatCounter del clic en el anuncio de casa (nombre completo: anuncio-casa-<página>-<idioma>-<1|2>)
MAX_HUECOS = 2                                  # por página (WEB-09, punto 4)
# Páginas sin anuncio (WEB-09, punto 6): las guías, privacidad, seguridad, la 404 y /anuncio/ (que carga el script a su manera).
PAGINAS_SIN_ANUNCIO = ("404.html", "anuncio/index.html", "no-contar/index.html", "privacy/index.html", "safety/index.html", "es/seguridad/index.html",
                       "sorteo/index.html", "sorteo/en/index.html", "es/sorteo/index.html",
                       "player-log/index.html", "es/player-log/index.html",
                       "blog/learn-mtg-arena-guides/index.html", "es/blog/learn-mtg-arena-guides/index.html",
                       "pt/blog/learn-mtg-arena-guides/index.html", "ja/blog/learn-mtg-arena-guides/index.html")  # blog, decisión del coordinador (ML-345); sorteo: redirecciones (ML-342); player-log: sin anuncio, decisión de Eusebio, 20/11 (ML-343)
PREFIJO_SIN_ANUNCIO = "guia/"

# Textos por idioma: etiqueta encima del hueco y anuncio de casa (casa_*: los aprobó Eusebio el 18/11/2026; el japonés sin revisar por un nativo).
TEXTOS = {
    "es": {"pub": "Publicidad", "ruta": "/es/aprender/", "casa_b": "Guías de Magic en Aprender",
           "casa_s": "De los creadores de Metafy, para Arena y Magic Online.", "casa_e": "Ver las guías →"},
    "en": {"pub": "Advertisement", "ruta": "/learn/", "casa_b": "Magic guides in Learn",
           "casa_s": "From Metafy creators, for Arena and Magic Online.", "casa_e": "See the guides →"},
    "pt": {"pub": "Publicidade", "ruta": "/pt/aprender/", "casa_b": "Guias de Magic em Aprender",
           "casa_s": "Dos criadores da Metafy, para Arena e Magic Online.", "casa_e": "Ver os guias →"},
    "ja": {"pub": "広告", "ruta": "/ja/learn/", "casa_b": "「学ぶ」でマジックのガイドを",
           "casa_s": "Metafyのクリエイターによる、アリーナとMagic Online向け。", "casa_e": "ガイドを見る →"},
}

_MARCA = re.compile(r"\{\{HUECO_MDN(:suelto)?\}\}\n?")


def sin_anuncio(relativa: Path) -> bool:
    """¿Es ``relativa`` (un .html relativo a la raíz) una página que no lleva anuncio?"""
    ruta = relativa.as_posix()
    return ruta in PAGINAS_SIN_ANUNCIO or ruta.startswith(PREFIJO_SIN_ANUNCIO)


def html_hueco(idioma: str, suelto: bool = False, posicion: int = 1) -> str:
    """El ``<aside>`` de un hueco en ``idioma`` (es, en, pt, ja). ``suelto``: dentro de la rejilla de Learn, sin bordes ni salto de línea
    detrás (en la rejilla un salto sería un nodo de texto que el repintado de learn.js no espera). ``posicion``: 1 o 2, el orden del
    hueco en la página; da nombre al evento de GoatCounter del anuncio de casa (``{{EVENTO:anuncio-casa:N}}``, que completa construir_web).

    Lleva dentro el anuncio de casa (un enlace a Learn); la hoja de estilos lo oculta salvo que MDN marque ``data-mdn-state="empty"``,
    que ``/huecos_mdn.js`` lo pida por plazo agotado o que la página se vea sin JavaScript.
    """
    t = {clave: html.escape(valor, quote=True) for clave, valor in TEXTOS[idioma].items()}
    evento = f"{{{{EVENTO:{EVENTO_CASA}:{posicion}}}}}"
    casa = (f'<a class="hm-casa" href="{t["ruta"]}" data-goatcounter-click="{evento}" data-goatcounter-title="{evento}"><span class="hm-t"><strong>{t["casa_b"]}</strong><span>{t["casa_s"]}</span></span>'
            f'<em>{t["casa_e"]}</em></a>')
    clase = "hueco-mdn suelto" if suelto else "hueco-mdn"
    return (f'<aside class="{clase}" aria-label="{t["pub"]}"><span class="hm-eti" aria-hidden="true">{t["pub"]}</span>'
            f'<div class="hm-caja" data-mdn="auto" data-mdn-theme="dark">{casa}</div></aside>' + ("" if suelto else "\n"))


def html_scripts() -> str:
    """Los dos scripts que lleva una página con hueco, en una línea: el de casa (diferido) y el de MDN (``async``)."""
    return (f'<script defer src="{SCRIPT_HUECOS}" data-plazo="{PLAZO_MDN_MS}"></script>'
            f'<script async src="{SCRIPT_MDN}" data-mdn-site="{SITIO_MDN}"></script>')


def html_estilos(raiz: Path) -> str:
    """La hoja de estilos de los huecos como ``<style>``, leída de ``raiz`` (el repositorio), en una línea propia con su salto."""
    with open(raiz / CSS_HUECOS, encoding="utf-8", newline="") as f:
        return "<style>" + f.read().rstrip("\n") + "</style>\n"


def aplicar_mdn(pagina: str, relativa: Path, idioma: str, raiz: Path = RAIZ) -> str:
    """Resuelve las marcas ``{{HUECO_MDN}}`` de una página con sus huecos y le añade, una sola vez, su hoja de estilos y los scripts.

    ``raiz`` es el repositorio del que se lee la hoja de estilos. Lanza ``ValueError`` si la página no debe llevar anuncio y tiene marcas,
    si tiene más de ``MAX_HUECOS`` o si no cierra con un único ``</body>`` y un único ``</head>``. Sin marcas, devuelve ``pagina`` sin tocar.
    """
    marcas = _MARCA.findall(pagina)
    if not marcas:
        return pagina
    nombre = relativa.as_posix()
    if sin_anuncio(relativa):
        raise ValueError(f"{nombre}: es una página sin anuncio y tiene {{{{HUECO_MDN}}}}")
    if len(marcas) > MAX_HUECOS:
        raise ValueError(f"{nombre}: {len(marcas)} huecos de anuncio; como mucho {MAX_HUECOS}")
    if pagina.count("</body>") != 1:
        raise ValueError(f"{nombre}: no tiene un único </body> donde poner el script de MDN")
    posiciones = iter(range(1, MAX_HUECOS + 1))
    if pagina.count("</head>") != 1:
        raise ValueError(f"{nombre}: no tiene un único </head> donde poner los estilos de los huecos")
    pagina = pagina.replace("</head>", html_estilos(raiz) + "</head>")
    pagina = _MARCA.sub(lambda m: html_hueco(idioma, suelto=bool(m.group(1)), posicion=next(posiciones)), pagina)
    return pagina.replace("</body>", html_scripts() + "</body>")
