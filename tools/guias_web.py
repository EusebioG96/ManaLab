"""Validación de la lista de guías de Metafy para la página «Learn» de la web (ML-324). Solo biblioteca estándar.

Es el espejo, en Python, de lo que valida la app (ManaLab-source: manalab_aprender_validar.py) y el servidor (servidor_ia/guias.js), y de
lo que valida el navegador (learn/learn.js). La web no importa código de la app: si allí cambian las reglas, hay que cambiarlas aquí y en
learn/learn.js (tools/test_pagina_learn_validacion.py comprueba que Python y JavaScript deciden lo mismo con una lista hostil).

Formato de la lista (el que sirve GET /guias.json y el de learn/guias.json): {v, actualizada, guias: [{name, description, url, cover_url,
price: {value_in_cents, currency} | null, subscriber_only, authors: [{name}], average_rating, review_count, total_reading_time_minutes,
purchase_count}]}. Una guía mala se descarta sola; una portada mala deja la guía sin portada; un encabezado malo invalida la lista.
"""
import json
import re
import unicodedata
from datetime import datetime
from urllib.parse import urlsplit

MAX_ENLACE = 300                     # caracteres de un enlace
DOMINIOS_METAFY = ("metafy.gg",)     # host de la url de una guía: este dominio o un subdominio
HOSTS_PORTADAS = ("metafy.gg",)      # host de una portada: este dominio o un subdominio (cdn.metafy.gg entra)
MAX_GUIAS = 2000                     # guías que se leen; las de más se recortan (igual que el servidor)
MAX_BYTES = 2 * 1024 * 1024          # tamaño máximo de la lista
MAX_TITULO = 140                     # caracteres del título
MAX_DESCRIPCION = 600                # caracteres de la descripción
MAX_NOMBRE = 60                      # caracteres del nombre de un autor
MAX_AUTORES = 5                      # autores por guía
MAX_CANTIDAD = 10_000_000            # tope de compras, reseñas y céntimos
MAX_MINUTOS = 100_000                # tope del tiempo de lectura
MAX_FECHA = 40                       # caracteres de la fecha de la lista
ESQUEMA = 1                          # valor obligatorio de «v»
MONEDA = "USD"                       # la única moneda de los precios de Metafy
PROHIBIDOS_ENLACE = frozenset("\"'<>\\")   # rompen un atributo HTML o los reinterpreta el navegador
HOST = re.compile(r"[a-z0-9.-]+")    # sin «%» ni nada que un navegador decodifique
CATEGORIAS_INVALIDAS = ("Cc", "Cf", "Zl", "Zp", "Cs", "Co", "Cn")   # control, invisibles, separadores, sustitutos, privados, sin asignar


def enlace_https(enlace: object, dominios: tuple) -> bool:
    """¿Es un https a uno de los `dominios` (o a un subdominio suyo), sin usuario, contraseña ni puerto y de MAX_ENLACE caracteres como mucho?"""
    if not isinstance(enlace, str) or not enlace.startswith("https://") or not enlace.isascii() or not 0 < len(enlace) <= MAX_ENLACE:
        return False
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 or c in PROHIBIDOS_ENLACE for c in enlace):
        return False
    try:
        partes = urlsplit(enlace)
    except ValueError:
        return False
    host = partes.hostname or ""
    if partes.username is not None or partes.password is not None or ":" in partes.netloc:
        return False
    if not HOST.fullmatch(host) or "" in host.split("."):
        return False
    return any(host == d or host.endswith("." + d) for d in dominios)


def texto_valido(valor: object, maximo: int, varias_lineas: bool = False) -> bool:
    """¿Es un texto de 1 a `maximo` caracteres, sin control, invisibles ni de inversión del sentido, y con algo visible?
    `varias_lineas`: admite saltos de línea y tabuladores."""
    if not isinstance(valor, str) or not 0 < len(valor.strip()) <= maximo or len(valor) > maximo:
        return False
    return all((varias_lineas and c in "\n\t") or unicodedata.category(c) not in CATEGORIAS_INVALIDAS for c in valor)


def _entero(valor: object, maximo: int) -> bool:
    """¿Es un entero (nunca un booleano) de 0 a `maximo`?"""
    return type(valor) is int and 0 <= valor <= maximo


def _opcional(guia: dict, campo: str) -> object:
    """El valor de un campo opcional: None si falta, es null o es «»."""
    valor = guia.get(campo)
    return None if valor in (None, "") else valor


def _autores(crudo: object) -> list:
    """Los autores de una guía como [{name}]; ValueError si no es una lista de como mucho MAX_AUTORES autores válidos."""
    if not isinstance(crudo, list) or len(crudo) > MAX_AUTORES:
        raise ValueError("autores")
    for autor in crudo:
        if not isinstance(autor, dict) or not texto_valido(autor.get("name"), MAX_NOMBRE):
            raise ValueError("autor")
    return [{"name": autor["name"].strip()} for autor in crudo]


def _precio(crudo: object) -> dict | None:
    """El precio {value_in_cents, currency}, o None si es gratis (null); ValueError si es otra cosa."""
    if crudo is None:
        return None
    if not isinstance(crudo, dict) or crudo.get("currency") != MONEDA or not _entero(crudo.get("value_in_cents"), MAX_CANTIDAD):
        raise ValueError("precio")
    return {"value_in_cents": crudo["value_in_cents"], "currency": MONEDA}


def _valoracion(crudo: object) -> float | int | None:
    """La valoración (1 a 10) o None; ValueError si es otra cosa. Nunca un booleano ni un no-número."""
    if crudo is None:
        return None
    if type(crudo) not in (int, float) or not 1 <= crudo <= 10:
        raise ValueError("valoración")
    return crudo


def _cantidad(guia: dict, campo: str, maximo: int, por_defecto: int | None) -> int | None:
    """El entero ≥ 0 de un campo (`por_defecto` si falta o es null); ValueError si es de otro tipo o pasa de `maximo`."""
    valor = guia.get(campo)
    if valor is None:
        return por_defecto
    if not _entero(valor, maximo):
        raise ValueError(campo)
    return valor


def validar_guia(elemento: object) -> dict:
    """Una guía normalizada con todos sus campos; ValueError si algo no cuadra (esa guía se descarta)."""
    if not isinstance(elemento, dict):
        raise ValueError("no es un objeto")
    if not texto_valido(elemento.get("name"), MAX_TITULO) or not enlace_https(elemento.get("url"), DOMINIOS_METAFY):
        raise ValueError("título o enlace")
    descripcion = _opcional(elemento, "description")
    if descripcion is not None and not texto_valido(descripcion, MAX_DESCRIPCION, varias_lineas=True):
        raise ValueError("descripción")
    portada = _opcional(elemento, "cover_url")
    if portada is not None and not enlace_https(portada, HOSTS_PORTADAS):
        portada = None   # portada mala: la guía sale sin portada
    solo = elemento.get("subscriber_only", False)
    if not isinstance(solo, bool):
        raise ValueError("subscriber_only")
    return {"name": elemento["name"].strip(), "description": (descripcion or "").strip(), "url": elemento["url"], "cover_url": portada or "",
            "price": _precio(elemento.get("price")), "subscriber_only": solo, "authors": _autores(elemento.get("authors", [])),
            "average_rating": _valoracion(elemento.get("average_rating")), "review_count": _cantidad(elemento, "review_count", MAX_CANTIDAD, 0),
            "total_reading_time_minutes": _cantidad(elemento, "total_reading_time_minutes", MAX_MINUTOS, None),
            "purchase_count": _cantidad(elemento, "purchase_count", MAX_CANTIDAD, 0)}


def validar_lista(datos: object) -> dict:
    """La lista {v, actualizada, guias} con solo las guías válidas (sin repetir url, MAX_GUIAS como mucho); ValueError si el encabezado
    no cuadra (v ≠ 1, fecha mala, `guias` que no es una lista)."""
    if not isinstance(datos, dict) or type(datos.get("v")) is not int or datos["v"] != ESQUEMA:
        raise ValueError("esquema no soportado")
    fecha = datos.get("actualizada")
    if not isinstance(fecha, str) or len(fecha) > MAX_FECHA:
        raise ValueError("fecha no válida")
    datetime.fromisoformat(fecha)   # ValueError si no es ISO 8601
    if not isinstance(datos.get("guias"), list):
        raise ValueError("guias no es una lista")
    guias, vistas = [], set()
    for elemento in datos["guias"][:MAX_GUIAS]:
        try:
            guia = validar_guia(elemento)
        except (ValueError, TypeError, OverflowError, RecursionError):
            continue   # una guía mala no tumba la lista
        if guia["url"] not in vistas:
            vistas.add(guia["url"])
            guias.append(guia)
    return {"v": ESQUEMA, "actualizada": fecha, "guias": guias}


def validar_texto(texto: str) -> dict:
    """Lo mismo que `validar_lista`, partiendo del texto JSON de la respuesta; ValueError si es demasiado grande o no es JSON."""
    if len(texto.encode("utf-8")) > MAX_BYTES:
        raise ValueError("lista demasiado grande")
    return validar_lista(json.loads(texto))


def serializar(lista: dict) -> str:
    """El texto con el que se guarda la lista en learn/guias.json: siempre igual para la misma lista (sin espacios, UTF-8, con salto final)."""
    return json.dumps(lista, ensure_ascii=False, separators=(",", ":")) + "\n"


# ------------------------------------------------------------------ creadores destacados (contenido.json, campo «destacados»)
DOMINIOS_FOTO = ("manalab.es",)                # la foto y el fondo de un destacado se alojan en esta web
EXTENSIONES_IMAGEN = (".webp", ".png", ".jpg")  # la ruta de una foto o un fondo termina en una de estas
MAX_DESTACADOS = 10                            # destacados que se leen; los de más se recortan
MAX_NOMBRE_DESTACADO = 60                      # caracteres del nombre
MAX_LINEA = 80                                 # caracteres de la línea («Standard y Pioneer · ES/EN»)
MAX_FRASE = 140                                # caracteres de la frase del creador (campo nuevo, VIS-23)
CASILLAS = ("academia", "guias", "sesiones")   # enlaces opcionales a Metafy
PATRON_ID = re.compile(r"^[a-z0-9-]{1,40}$")   # identificador de un destacado para contar sus cifras (ML-333); sin él no se cuenta
PATRON_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # «hasta»: AAAA-MM-DD, el día desde el que el destacado ya no se enseña


def imagen_valida(enlace: object) -> bool:
    """¿Es un https a manalab.es cuya ruta termina en .webp, .png o .jpg, sin parámetros ni ancla? (foto y fondo de un destacado)"""
    if not enlace_https(enlace, DOMINIOS_FOTO):
        return False
    partes = urlsplit(enlace)
    return not partes.query and not partes.fragment and partes.path.lower().endswith(EXTENSIONES_IMAGEN)


def fecha_valida(valor: object) -> bool:
    """¿Es una fecha AAAA-MM-DD que existe en el calendario?"""
    if not isinstance(valor, str) or not PATRON_FECHA.match(valor):
        return False
    try:
        datetime.strptime(valor, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _destacado(elemento: object) -> dict:
    """Un destacado normalizado {nombre, linea, enlace, foto, frase, fondo, academia, guias, sesiones, id, hasta} (lo que falta, «»); ValueError si
    nombre, línea o enlace no valen, una casilla trae un enlace que no es de Metafy o «hasta» no es una fecha. Una foto, una frase, un fondo o
    un id malos se quedan en «» (un destacado sin id se enseña pero no se cuenta)."""
    if not isinstance(elemento, dict):
        raise ValueError("no es un objeto")
    if not texto_valido(elemento.get("nombre"), MAX_NOMBRE_DESTACADO) or not texto_valido(elemento.get("linea"), MAX_LINEA):
        raise ValueError("nombre o línea")
    if not enlace_https(elemento.get("enlace"), DOMINIOS_METAFY):
        raise ValueError("enlace")
    salida = {"nombre": elemento["nombre"].strip(), "linea": elemento["linea"].strip(), "enlace": elemento["enlace"]}
    for campo in ("foto", "fondo"):
        valor = _opcional(elemento, campo)
        salida[campo] = valor if imagen_valida(valor) else ""
    frase = _opcional(elemento, "frase")
    salida["frase"] = frase.strip() if texto_valido(frase, MAX_FRASE) else ""
    for campo in CASILLAS:
        valor = _opcional(elemento, campo)
        if valor is not None and not enlace_https(valor, DOMINIOS_METAFY):
            raise ValueError(campo)
        salida[campo] = valor or ""
    identificador = _opcional(elemento, "id")
    salida["id"] = identificador if isinstance(identificador, str) and PATRON_ID.match(identificador) else ""
    hasta = _opcional(elemento, "hasta")
    if hasta is not None and not fecha_valida(hasta):
        raise ValueError("hasta")
    salida["hasta"] = hasta or ""
    return salida


def validar_destacados(crudo: object) -> list:
    """Los destacados válidos de `crudo` (como mucho MAX_DESTACADOS); [] si no es una lista. Uno inválido se descarta sin tirar los demás."""
    if not isinstance(crudo, list):
        return []
    salida = []
    for elemento in crudo[:MAX_DESTACADOS]:
        try:
            salida.append(_destacado(elemento))
        except (ValueError, TypeError, OverflowError, RecursionError):
            continue
    return salida
