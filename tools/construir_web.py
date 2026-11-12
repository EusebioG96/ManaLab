#!/usr/bin/env python3
"""Genera las páginas HTML de la web a partir de plantillas (ML-197). Solo biblioteca estándar.

Uso:
    python3 tools/construir_web.py              escribe los .html en la raíz del repositorio
    python3 tools/construir_web.py --comprobar  no escribe; sale con 1 si algún .html no coincide con lo generado
    python3 tools/construir_web.py --salida DIR genera en DIR en vez de en la raíz

Disposición (todo bajo plantillas/, que no es HTML y por eso no se indexa):
    plantillas/paginas/<ruta>.pagina   contenido de cada página; se publica en <ruta>.html
    plantillas/<nombre>.tpl            plantilla común (cabecera, pie o CSS); una línea ``{{@N}}`` es el hueco N
    plantillas/<nombre>/<N>.<v>.txt    valor v del hueco N (cada línea termina en salto de línea)

En una página, ``{{> nombre N=v N=v}}`` inserta la plantilla ``nombre``. Los huecos no citados
toman la variante ``a``. Más detalle en tools/README.md.
"""
import argparse
import re
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_PLANTILLAS = "plantillas"
CARPETA_PAGINAS = "paginas"
SUFIJO_PAGINA = ".pagina"
SUFIJO_PLANTILLA = ".tpl"
VARIANTE_POR_DEFECTO = "a"  # la variante que no hace falta citar en la página

# {{> nombre 3=b 7=c }}: inserta una plantilla con las variantes elegidas
_DIRECTIVA = re.compile(r"\{\{> (\w+)((?: \d+=\w+)*)\}\}")
_HUECO = re.compile(r"\{\{@(\d+)\}\}")


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


def listar_paginas(raiz: Path) -> list[Path]:
    """Rutas (relativas a la raíz) de los .html que se generan, ordenadas."""
    base = raiz / CARPETA_PLANTILLAS / CARPETA_PAGINAS
    return sorted(p.relative_to(base).with_suffix(".html") for p in base.rglob("*" + SUFIJO_PAGINA))


def construir(raiz: Path, destino: Path) -> list[Path]:
    """Genera todas las páginas de ``raiz`` en ``destino`` y devuelve las rutas relativas escritas.

    No reescribe un archivo cuyo contenido ya es idéntico (así no cambian las fechas ni se ensucia git).
    """
    carpeta = raiz / CARPETA_PLANTILLAS
    escritas = []
    for relativa in listar_paginas(raiz):
        fuente = _leer(carpeta / CARPETA_PAGINAS / relativa.with_suffix(SUFIJO_PAGINA))
        datos = generar_pagina(carpeta, fuente).encode("utf-8")
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
