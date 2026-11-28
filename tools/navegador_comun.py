"""Ayudas comunes de las pruebas de navegador (Playwright): esperar por condición y no por tiempo (ML-398).

Una espera fija (`wait_for_timeout`) acierta con la máquina libre y falla con carga: o se queda corta, o las medidas se toman antes de
que lleguen las tipografías y las imágenes. Aquí están las esperas por condición que usan varios archivos de pruebas.
"""
import time
from collections.abc import Callable

# Tope de cualquier espera por condición: con carga extra una página puede tardar segundos, pero si pasa de aquí es un fallo de verdad.
ESPERA_MAXIMA_MS = 30000
# Imágenes ya pedidas (las perezosas que aún no se han pedido no cuentan) y tipografías cargadas: lo que debe estar antes de medir la maqueta.
PAGINA_ESTABLE = """() => document.fonts.status === 'loaded'
  && [...document.images].every((i) => i.complete || (i.loading === 'lazy' && !i.currentSrc))"""


def esperar_pagina_estable(pagina, timeout: int = ESPERA_MAXIMA_MS) -> None:
    """Espera a que las tipografías estén cargadas y las imágenes pedidas hayan terminado (bien o con error): a partir de ahí la maqueta no se mueve sola."""
    pagina.wait_for_function(PAGINA_ESTABLE, timeout=timeout)


def esperar_hasta(pagina, condicion: Callable[[], bool], descripcion: str, timeout_ms: int = ESPERA_MAXIMA_MS) -> None:
    """Sondea `condicion()` (algo del lado de Python, como la lista que rellena una ruta de Playwright) hasta que sea cierta; si no, falla con `descripcion`.

    La API síncrona de Playwright solo atiende las rutas y los eventos mientras está dentro de una llamada suya, por eso cada vuelta cede 20 ms a la
    página: es un latido para que lleguen los eventos, no una espera de la que dependa el resultado.
    """
    limite = time.monotonic() + timeout_ms / 1000
    while not condicion():
        if time.monotonic() > limite:
            raise AssertionError(f"no se cumplió a tiempo: {descripcion}")
        pagina.wait_for_timeout(20)
