"""Piezas de accesibilidad que se añaden a todas las páginas al generarlas (ML-412). Solo biblioteca estándar.

- «Saltar al contenido»: primer enlace del <body>, visible solo con el foco del teclado, traducido al idioma de la página.
- Script del menú móvil (menu.js): cierra el menú con Esc y al pulsar fuera. Solo en las páginas que tienen ese menú.
"""
import re

ID_CONTENIDO = "contenido"  # id que se pone al <main> cuando la página no tiene el suyo
TEXTO_SALTAR = {  # idioma (etiqueta de <html lang>, sin región) -> texto del enlace
    "en": "Skip to content", "es": "Saltar al contenido", "pt": "Ir para o conteúdo", "ja": "本文へ移動",
    "de": "Zum Inhalt springen", "fr": "Aller au contenu", "it": "Vai al contenuto", "ko": "본문으로 건너뛰기", "zh": "跳到正文",
}
# Estilo propio y mínimo para no tocar cada plantilla de CSS: fuera de pantalla hasta recibir el foco; el <main> no dibuja el aro al llegar.
ESTILO_SALTAR = (
    '<style>.saltar{position:absolute;left:8px;top:-60px;z-index:100;padding:10px 16px;border-radius:4px;background:#ece6d6;color:#0d100f;'
    'font:600 15px/1.3 system-ui,sans-serif;text-decoration:none}.saltar:focus{top:8px}main:focus{outline:none}</style>\n'
)
SCRIPT_MENU = '<script defer src="/menu.js"></script>\n'
_HTML_LANG = re.compile(r'<html lang="([A-Za-z-]+)"')
_BODY = re.compile(r"<body[^>]*>\n?")
_MAIN = re.compile(r"<main(?P<atributos>[^>]*)>")
_ID = re.compile(r'\bid="([^"]*)"')


def _destino_y_main(pagina: str) -> tuple[str, str]:
    """Devuelve (id al que salta el enlace, página con el <main> listo para recibir el foco)."""
    principal = _MAIN.search(pagina)
    atributos = principal.group("atributos")
    existente = _ID.search(atributos)
    destino = existente.group(1) if existente else ID_CONTENIDO
    nuevos = atributos + ("" if existente else f' id="{destino}"') + ('' if "tabindex" in atributos else ' tabindex="-1"')
    return destino, pagina[:principal.start()] + f"<main{nuevos}>" + pagina[principal.end():]


def aplicar_saltar_contenido(pagina: str) -> str:
    """Añade el enlace «Saltar al contenido» a una página con <main>; las que no lo tienen (redirecciones) quedan igual."""
    idioma = _HTML_LANG.search(pagina)
    if not (idioma and _MAIN.search(pagina) and _BODY.search(pagina)):
        return pagina
    texto = TEXTO_SALTAR[idioma.group(1).split("-")[0].lower()]
    destino, pagina = _destino_y_main(pagina)
    cuerpo = _BODY.search(pagina)
    enlace = f'<a class="saltar" href="#{destino}">{texto}</a>\n'
    pagina = pagina[:cuerpo.end()] + enlace + pagina[cuerpo.end():]
    return pagina.replace("</head>", ESTILO_SALTAR + "</head>", 1)


def aplicar_script_menu(pagina: str) -> str:
    """Carga menu.js (antes de </body>) en las páginas con menú móvil."""
    if '<details class="menu"' not in pagina or "</body>" not in pagina:
        return pagina
    return pagina.replace("</body>", SCRIPT_MENU + "</body>", 1)
