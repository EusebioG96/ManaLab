"""La parte dinámica de las páginas «Learn» (ML-324, WEB-08): lo que construir_web.py escribe en el HTML al generar la web. Solo biblioteca estándar.

Las páginas (plantillas/paginas/learn/, es/aprender/, pt/aprender/, ja/learn/) llevan marcas ``{{LEARN:destacado}}``, ``{{LEARN:barra}}``,
``{{LEARN:filtros}}``, ``{{LEARN:rejilla}}`` y ``{{LEARN:datos}}``. ``aplicar_learn`` las sustituye con:
  - la primera página de guías (24, orden «Más compradas») de la copia learn/guias.json, que valida tools/guias_web.py;
  - los creadores destacados de contenido.json (el banner, la barra fina y su estado inicial);
  - los textos y ajustes que necesita learn/learn.js, en un bloque JSON.
No accede a la red: la copia la actualiza tools/actualizar_guias_web.py. learn/learn.js pinta lo mismo desde el navegador, con la lista del
servidor; tools/test_pagina_learn_navegador.py comprueba que ambos coinciden carácter a carácter.
"""
import html
import json
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guias_web  # noqa: E402

ARCHIVO_GUIAS = "learn/guias.json"                   # la copia de la lista, también servida en manalab.es
ARCHIVO_CONTENIDO = "contenido.json"                 # de él salen los destacados
URL_SERVIDOR = "https://registro-ia.eusebiog76.workers.dev/guias.json"   # de donde la lee el navegador (servidor_ia/guias.js)
POR_PAGINA = 24                                      # guías por página
NBSP = " "                                      # el precio no se parte en dos líneas
ROTAR_MS = 8000                                      # cada cuánto cambia solo el creador destacado (VIS-22)
MARCAS = ("destacado", "barra", "filtros", "rejilla", "datos")
GUIAS_ANTES_DEL_HUECO = 8                            # el hueco de anuncio de la rejilla va tras la octava guía (WEB-09)
MARCA_HUECO_MDN = "{{HUECO_MDN:suelto}}"             # lo resuelve construir_mdn.aplicar_mdn

LIBRO = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5C6.5 4.5 9.5 4.5 12 6c2.5-1.5 5.5-1.5 8-.5v13c-2.5-1-5.5-1-8 .5-2.5-1.5-5.5-1.5-8-.5zM12 6v13"/></svg>'
FLECHA = {-1: '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M7.5 2.5 4 6l3.5 3.5"/></svg>',
          1: '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M4.5 2.5 8 6 4.5 9.5"/></svg>'}

# Los textos de la página, por idioma. Los de «dest» a «sig» los aprobó Eusebio el 18/11/2026 (18:06; el japonés sin revisar por un nativo); el resto
# (orden, cuenta, vacío…) son los de la pantalla Aprender de la app (idiomas/<idioma>.json), con los plurales que allí se escriben.
TEXTOS = {
    "es": {"dest": "Destacado · colaboración", "ver": "Ver en Metafy", "cas": ["Academia", "Guías", "Sesiones"], "ant": "Anterior", "sig": "Siguiente",
           "fil": ["Todas", "Gratis", "De pago", "Suscriptores"], "creador": "Todos los creadores", "buscar": "Buscar una guía",
           "orden": ["Más compradas", "Mejor valoradas", "Más cortas"], "de": "de {}", "gratis": "Gratis", "sus": "Suscriptores",
           "cuenta": ["1 guía", "{n} guías"], "res": ["1 reseña", "{n} reseñas"], "min": "{n} min", "paginas": "Páginas", "decimal": ",",
           "precio": "{n}" + NBSP + "US$", "vacio": ["Todavía no hay guías", "Las guías de Metafy para Magic aparecerán aquí en cuanto se publiquen."],
           "ninguna": ["Ninguna guía coincide", "Quitar los filtros"], "bajar": "Descargar gratis"},
    "en": {"dest": "Featured · partnership", "ver": "View on Metafy", "cas": ["Academy", "Guides", "Sessions"], "ant": "Previous", "sig": "Next",
           "fil": ["All", "Free", "Paid", "Subscribers"], "creador": "All creators", "buscar": "Search for a guide",
           "orden": ["Most purchased", "Top rated", "Shortest"], "de": "by {}", "gratis": "Free", "sus": "Subscribers",
           "cuenta": ["1 guide", "{n} guides"], "res": ["1 review", "{n} reviews"], "min": "{n} min", "paginas": "Pages", "decimal": ".",
           "precio": "${n}", "vacio": ["There are no guides yet", "Metafy guides for Magic will show up here as soon as they are published."],
           "ninguna": ["No guide matches", "Clear filters"], "bajar": "Download free"},
    "pt": {"dest": "Destaque · parceria", "ver": "Ver na Metafy", "cas": ["Academia", "Guias", "Sessões"], "ant": "Anterior", "sig": "Próxima",
           "fil": ["Todos", "Grátis", "Pagos", "Assinantes"], "creador": "Todos os criadores", "buscar": "Buscar um guia",
           "orden": ["Mais comprados", "Mais bem avaliadas", "Mais curtas"], "de": "de {}", "gratis": "Grátis", "sus": "Assinantes",
           "cuenta": ["1 guia", "{n} guias"], "res": ["1 avaliação", "{n} avaliações"], "min": "{n} min", "paginas": "Páginas", "decimal": ",",
           "precio": "US$" + NBSP + "{n}", "vacio": ["Ainda não há guias", "Os guias do Metafy para Magic aparecerão aqui assim que forem publicados."],
           "ninguna": ["Nenhum guia corresponde", "Remover os filtros"], "bajar": "Baixar grátis"},
    "ja": {"dest": "注目 · コラボ", "ver": "Metafyで見る", "cas": ["アカデミー", "ガイド", "セッション"], "ant": "前へ", "sig": "次へ",
           "fil": ["すべて", "無料", "有料", "購読者"], "creador": "すべてのクリエイター", "buscar": "ガイドを検索",
           "orden": ["購入数順", "評価の高い順", "短い順"], "de": "作成：{}", "gratis": "無料", "sus": "購読者",
           "cuenta": ["1件のガイド", "{n}件のガイド"], "res": ["1件のレビュー", "{n}件のレビュー"], "min": "{n}分", "paginas": "ページ", "decimal": ".",
           "precio": "${n}", "vacio": ["まだガイドはありません", "Magic 向けの Metafy ガイドは、公開され次第ここに表示されます。"],
           "ninguna": ["一致するガイドはありません", "フィルターを解除"], "bajar": "無料ダウンロード"},
}
RESENAS_MIN = 3   # reseñas necesarias para enseñar la valoración (como la app)


def _esc(texto: object) -> str:
    return html.escape(str(texto), quote=True)


def plano(texto: str) -> str:
    """Sin acentos y en minúsculas, para ordenar y buscar (learn.js hace lo mismo: NFD, sin marcas combinantes y toLowerCase)."""
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


def clave_de_orden(guia: dict) -> tuple:
    """La clave de «Más compradas»: más compras primero y, a igualdad, el título sin acentos en el orden de las unidades UTF-16 (como la
    comparación de cadenas de JavaScript) y, si aún empatan, la dirección."""
    return (-guia["purchase_count"], plano(guia["name"]).encode("utf-16-be"), guia["url"].encode("utf-16-be"))


def ordenar_compradas(guias: list) -> list:
    """Las guías en el orden por defecto, «Más compradas»."""
    return sorted(guias, key=clave_de_orden)


def formatear_numero(centimos: int, t: dict) -> str:
    """«7,99» o «12» (dos decimales solo si no son cero) con el separador decimal del idioma."""
    if centimos % 100 == 0:
        return str(centimos // 100)
    return f"{centimos // 100}{t['decimal']}{centimos % 100:02d}"


def formatear_precio(centimos: int, t: dict) -> str:
    """El precio como se escribe en el idioma (7,99 US$ · $7.99 · US$ 7,99)."""
    return t["precio"].replace("{n}", formatear_numero(centimos, t))


def formatear_valoracion(valor: float, t: dict) -> str:
    """La valoración con un decimal. Redondea sumando medio y truncando, la misma aritmética que learn.js (toFixed no coincide en los empates)."""
    decimas = int(valor * 10 + 0.5)
    return f"{decimas // 10}{t['decimal']}{decimas % 10}"


def uno_o_varios(textos: list, n: int) -> str:
    """El texto de singular (n = 1) o de plural, con «{n}» sustituido."""
    return textos[0] if n == 1 else textos[1].replace("{n}", str(n))


def iniciales(nombre: str) -> str:
    """Las letras de las dos primeras palabras (o las dos primeras del nombre) en mayúsculas, para el creador sin foto."""
    palabras = [list(p) for p in nombre.split()]
    letras = [palabras[0][0], palabras[1][0]] if len(palabras) > 1 else (palabras[0][:2] if palabras else [])
    return "".join(letras).upper()


# ------------------------------------------------------------------ guías
def es_gratis(guia: dict) -> bool:
    """¿Es gratis? (sin precio, o a 0, y no solo para suscriptores)"""
    return not guia["subscriber_only"] and not (guia["price"] or {}).get("value_in_cents")


def html_precio(guia: dict, t: dict) -> str:
    """La etiqueta de precio de la portada: «Gratis», «Suscriptores» o el precio."""
    if guia["subscriber_only"]:
        return f'<span class="precio sus">{_esc(t["sus"])}</span>'
    if es_gratis(guia):
        return f'<span class="precio gratis">{_esc(t["gratis"])}</span>'
    return f'<span class="precio">{_esc(formatear_precio(guia["price"]["value_in_cents"], t))}</span>'


def html_datos(guia: dict, t: dict) -> str:
    """La fila de datos de una tarjeta: valoración (con 3 reseñas o más), reseñas y minutos."""
    valor = ""
    if guia["review_count"] >= RESENAS_MIN and guia["average_rating"] is not None:
        valor = f'<b>{formatear_valoracion(guia["average_rating"], t)}</b>'
    if guia["review_count"] > 0:
        resenas = _esc(uno_o_varios(t["res"], guia["review_count"]))
        valor = f"{valor} · {resenas}" if valor else resenas
    partes = [f"<span>{valor}</span>"] if valor else []
    if guia["total_reading_time_minutes"] is not None:
        partes.append(f'<span>{_esc(t["min"].replace("{n}", str(guia["total_reading_time_minutes"])))}</span>')
    return "".join(partes)


def html_tarjeta(guia: dict, t: dict) -> str:
    """Una guía: toda la tarjeta es un enlace a Metafy, con portada perezosa y sin referrer (lo que Metafy no necesita saber)."""
    imagen = (f'<img alt="" decoding="async" loading="lazy" referrerpolicy="no-referrer" src="{_esc(guia["cover_url"])}">'
              if guia["cover_url"] else "")
    autores = ", ".join(a["name"] for a in guia["authors"])
    de = f'<div class="a">{_esc(t["de"].replace("{}", autores))}</div>' if autores else ""
    return (f'<a class="guia" href="{_esc(guia["url"])}" rel="noopener" target="_blank"><div class="port c0">{LIBRO}{imagen}{html_precio(guia, t)}</div>'
            f'<div class="cu"><div class="t">{_esc(guia["name"])}</div>{de}<div class="m">{html_datos(guia, t)}</div></div></a>')


def paginas_visibles(actual: int, total: int) -> list:
    """Los números del paginador (None = «…»): la primera y la última, la actual y sus vecinas, y 1-3 o los tres últimos en los extremos.
    learn.js calcula lo mismo."""
    visibles = {1, total, actual - 1, actual, actual + 1}
    if actual <= 2:
        visibles |= {2, 3}
    if actual >= total - 1:
        visibles |= {total - 2, total - 1}
    ordenadas = sorted(n for n in visibles if 1 <= n <= total)
    salida, previo = [], None
    for n in ordenadas:
        if previo is not None and n - previo == 2:
            salida.append(previo + 1)   # «…» por una sola página sería absurdo: se enseña la página
        elif previo is not None and n - previo > 2:
            salida.append(None)
        salida.append(n)
        previo = n
    return salida


def html_paginador(actual: int, total: int, t: dict) -> str:
    """El paginador: cada página es un enlace con su dirección (?p=N; la primera, sin parámetro) para poder enlazarla."""
    if total <= 1:
        return ""

    def direccion(n: int) -> str:
        return "./" if n == 1 else f"?p={n}"

    def flecha(n: int, signo: str, etiqueta: str) -> str:
        if not 1 <= n <= total:
            return f'<span class="apagado" aria-hidden="true">{signo}</span>'
        return f'<a href="{direccion(n)}" aria-label="{_esc(etiqueta)}" data-p="{n}">{signo}</a>'

    cuerpo = "".join('<span aria-hidden="true">…</span>' if n is None else
                     f'<a href="{direccion(n)}" data-p="{n}"' + (' aria-current="page"' if n == actual else "") + f">{n}</a>"
                     for n in paginas_visibles(actual, total))
    return f'<nav class="ap-pag" id="ap-pag" aria-label="{_esc(t["paginas"])}">{flecha(actual - 1, "‹", t["ant"])}{cuerpo}{flecha(actual + 1, "›", t["sig"])}</nav>'


def html_caja_vacia(t: dict) -> str:
    """El estado «no hay guías»: lo dice y ofrece la descarga."""
    return (f'<div class="ap-caja"><b>{_esc(t["vacio"][0])}</b><span>{_esc(t["vacio"][1])}</span>'
            f'<a class="boton prim" href="#descargar">{_esc(t["bajar"])}</a></div>')


def html_rejilla(guias: list, t: dict) -> str:
    """La rejilla y el paginador con la primera página de `guias` ya en el orden por defecto; sin guías, la caja de «no hay» y nada más."""
    if not guias:
        return f'<div class="ap-rej vacia" id="guias">{html_caja_vacia(t)}</div>'
    total = -(-len(guias) // POR_PAGINA)
    tarjetas = [html_tarjeta(g, t) for g in guias[:POR_PAGINA]]
    if len(tarjetas) > GUIAS_ANTES_DEL_HUECO:   # el hueco de MDN (ML-325) va entre guías, nunca al final de la rejilla
        tarjetas.insert(GUIAS_ANTES_DEL_HUECO, MARCA_HUECO_MDN)
    return f'<div class="ap-rej" id="guias">{"".join(tarjetas)}</div>\n{html_paginador(1, total, t)}'


def html_filtros(n: int, t: dict) -> str:
    """La barra de filtros (los de la app) con el contador. Oculta si no hay guías; learn.js la rellena (creadores) y la activa."""
    botones = "".join(f'<button type="button" data-tipo="{tipo}" aria-pressed="{"true" if i == 0 else "false"}">{_esc(nombre)}</button>'
                      for i, (tipo, nombre) in enumerate(zip(("todas", "gratis", "pago", "suscriptores"), t["fil"])))
    ordenes = "".join(f'<option value="{valor}"{" selected" if i == 0 else ""}>{_esc(nombre)}</option>'
                      for i, (valor, nombre) in enumerate(zip(("compradas", "valoradas", "cortas"), t["orden"])))
    oculta = "" if n else " hidden"
    return (f'<div class="ap-barra" id="ap-barra"{oculta}><div class="ap-seg" role="group" aria-label="{_esc(t["fil"][0])}">{botones}</div>'
            f'<select class="ap-campo" id="ap-creador" aria-label="{_esc(t["creador"])}"><option value="">{_esc(t["creador"])}</option></select>'
            f'<select class="ap-campo" id="ap-orden" aria-label="{_esc(t["orden"][0])}">{ordenes}</select>'
            f'<input class="ap-campo" id="ap-buscar" type="search" placeholder="{_esc(t["buscar"])}" aria-label="{_esc(t["buscar"])}" autocomplete="off">'
            f'<span class="ap-cuenta" id="ap-cuenta" role="status">{_esc(uno_o_varios(t["cuenta"], n))}</span></div>')


# ------------------------------------------------------------------ destacados
def html_foto(nombre: str, foto: str, clase: str) -> str:
    """La foto redonda del creador: las iniciales debajo y, encima, la imagen si hay (si no carga, learn.js la quita y quedan las iniciales)."""
    imagen = f'<img alt="" decoding="async" referrerpolicy="no-referrer" src="{_esc(foto)}">' if foto else ""
    return f'<span class="{clase}" aria-hidden="true"><span class="ini">{_esc(iniciales(nombre))}</span>{imagen}</span>'


def html_creador(indice: int, d: dict, t: dict) -> str:
    """Un creador del banner. Todos van en la misma celda de la rejilla: el alto lo marca el más alto y nada salta al rotar. Los enlaces
    llevan rel="sponsored noopener" (es una colaboración de pago) y toda la tarjeta lleva al enlace principal (el ::after del botón)."""
    activo = indice == 0
    fondo = f'<img class="d2fondo" alt="" decoding="async" referrerpolicy="no-referrer" src="{_esc(d["fondo"])}">' if d["fondo"] else ""
    frase = f'<div class="d2fra">{_esc(d["frase"])}</div>' if d["frase"] else ""
    casillas = "".join(f'<a class="d2cas" href="{_esc(d[campo])}" rel="sponsored noopener" target="_blank">{_esc(nombre)}</a>'
                       for campo, nombre in zip(guias_web.CASILLAS, t["cas"]) if d[campo])
    estado = ' class="d2c on"' if activo else ' class="d2c" inert aria-hidden="true"'
    return (f'<article{estado} data-i="{indice}"><div class="d2esc" aria-hidden="true">{fondo}<div class="d2zona"><div class="d2aba">'
            f'<i></i><i></i><i></i><i></i><i></i></div></div></div>{html_foto(d["nombre"], d["foto"], "d2foto")}'
            f'<div class="d2txt"><span class="eti">{_esc(t["dest"])}</span><div class="d2nom">{_esc(d["nombre"])}</div>'
            f'<div class="d2lin">{_esc(d["linea"])}</div>{frase}<div class="d2acc"><a class="d2cta" href="{_esc(d["enlace"])}" '
            f'rel="sponsored noopener" target="_blank">{_esc(t["ver"])} <b aria-hidden="true">→</b></a>{casillas}</div></div></article>')


def html_destacado(destacados: list, t: dict) -> str:
    """El banner del creador destacado (VIS-23); sin destacados, nada (ni banner ni hueco). Con varios, flechas, rombos y línea de avance."""
    if not destacados:
        return ""
    creadores = "".join(html_creador(i, d, t) for i, d in enumerate(destacados))
    mando = ""
    if len(destacados) > 1:
        puntos = "".join(f'<i class="on"></i>' if i == 0 else "<i></i>" for i in range(len(destacados)))
        mando = (f'<div class="d2pag"><button type="button" data-d2="-1" aria-label="{_esc(t["ant"])}">{FLECHA[-1]}</button>'
                 f'<span class="d2pun" role="img" aria-label="1 / {len(destacados)}">{puntos}</span>'
                 f'<button type="button" data-d2="1" aria-label="{_esc(t["sig"])}">{FLECHA[1]}</button></div>'
                 '<span class="d2prog" aria-hidden="true"><i></i></span><span class="d2anuncio" role="status"></span>')
    return (f'<section class="ap-bloque"><div class="envoltura"><section class="d2" id="destacado" aria-label="{_esc(t["dest"])}" '
            f'data-total="{len(destacados)}">{creadores}{mando}</section></div></section>')


def html_barra(destacados: list, t: dict) -> str:
    """La barra fina fija (44 px): sale cuando el banner se ha ido. Mientras no se ve lleva inert y aria-hidden. Sin destacados, nada."""
    if not destacados:
        return ""
    d = destacados[0]
    return (f'<div class="d2barra" id="d2barra" role="region" aria-label="{_esc(t["dest"])}" inert aria-hidden="true"><div class="envoltura">'
            f'{html_foto(d["nombre"], d["foto"], "f")}<span class="n">{_esc(d["nombre"])}</span><span class="eti">{_esc(t["dest"])}</span>'
            f'<a class="d2cta" href="{_esc(d["enlace"])}" rel="sponsored noopener" target="_blank">{_esc(t["ver"])} <b aria-hidden="true">→</b></a></div></div>')


# ------------------------------------------------------------------ datos para learn.js
def html_datos_js(idioma: str, t: dict) -> str:
    """El bloque JSON con los ajustes y los textos de learn.js. «<» y «&» van escapados para que nada cierre el <script>."""
    datos = {"idioma": idioma, "servidor": URL_SERVIDOR, "copia": "/" + ARCHIVO_GUIAS, "porPagina": POR_PAGINA, "rotarMs": ROTAR_MS,
             "resenasMin": RESENAS_MIN, "t": {k: t[k] for k in ("fil", "creador", "buscar", "orden", "de", "gratis", "sus", "cuenta", "res", "min",
                                                                   "paginas", "ant", "sig", "decimal", "precio", "vacio", "ninguna", "bajar")}}
    texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'<script id="learn-datos" type="application/json">{texto}</script>'


# ------------------------------------------------------------------ lectura de los datos y marcas
def leer_guias(raiz: Path) -> list:
    """Las guías de la copia learn/guias.json de `raiz`, validadas y en el orden por defecto. Sin el archivo (una raíz de pruebas), ninguna:
    la página saldrá con el estado «no hay guías»; test_pagina_learn.py exige que el repositorio real lo tenga. ValueError si existe y no cumple."""
    ruta = raiz / ARCHIVO_GUIAS
    if not ruta.is_file():
        return []
    try:
        lista = guias_web.validar_texto(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"{ruta} no es válido: {error}. Ejecuta tools/actualizar_guias_web.py") from error
    return ordenar_compradas(lista["guias"])


def leer_destacados(raiz: Path) -> list:
    """Los destacados válidos de contenido.json de `raiz` (ninguno si el campo falta). ValueError si el archivo no se puede leer."""
    ruta = raiz / ARCHIVO_CONTENIDO
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"no se puede leer {ruta}: {error}") from error
    return guias_web.validar_destacados(datos.get("destacados") if isinstance(datos, dict) else None)


def aplicar_learn(fuente: str, idioma: str, raiz: Path) -> str:
    """Resuelve las marcas ``{{LEARN:...}}`` de una página con los datos de `raiz`. Sin marcas, devuelve `fuente` sin tocar (y sin leer nada)."""
    if "{{LEARN:" not in fuente:
        return fuente
    t = TEXTOS[idioma]
    guias, destacados = leer_guias(raiz), leer_destacados(raiz)
    valores = {"destacado": html_destacado(destacados, t), "barra": html_barra(destacados, t), "filtros": html_filtros(len(guias), t),
               "rejilla": html_rejilla(guias, t), "datos": html_datos_js(idioma, t)}
    for marca in MARCAS:
        fuente = fuente.replace("{{LEARN:" + marca + "}}", valores[marca])
    return fuente
