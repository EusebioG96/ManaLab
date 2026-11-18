#!/usr/bin/env python3
"""Descarga la lista de guías del servidor, la valida con las reglas de la app y la guarda en learn/guias.json (ML-324). Solo biblioteca estándar.

construir_web.py NO accede a la red: lee esa copia (así las páginas salen siempre igual y los tests no necesitan red). Este script es lo
único que habla con el servidor. Si la lista no cumple, no escribe nada y sale con código 1; si no ha cambiado, no reescribe el archivo.
La copia también se sirve en https://manalab.es/learn/guias.json: es la que usa el navegador si el servidor no responde.

Uso:  python3 tools/actualizar_guias_web.py            descarga de URL_GUIAS y actualiza learn/guias.json
      python3 tools/actualizar_guias_web.py --desde X  lee la lista de un archivo o una dirección https de otro servidor (pruebas)
Después:  python3 tools/construir_web.py  y commit de learn/guias.json y de los .html que cambien.
"""
import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guias_web  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
URL_GUIAS = "https://registro-ia.eusebiog76.workers.dev/guias.json"   # el servidor de la IA (servidor_ia/guias.js)
ARCHIVO_COPIA = "learn/guias.json"    # la copia en el repositorio, también servida en manalab.es/learn/guias.json
PLAZO_SEGUNDOS = 20                   # tiempo máximo de la descarga
AGENTE = "manalab-web-guias/1"        # nombre genérico del cliente


def descargar(url: str) -> str:
    """El texto de la respuesta de `url` (https). Lanza ValueError si no es https, no responde 200 o pesa más de MAX_BYTES."""
    if not url.startswith("https://"):
        raise ValueError(f"la dirección no es https: {url}")
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(peticion, timeout=PLAZO_SEGUNDOS) as respuesta:
            if respuesta.status != 200:
                raise ValueError(f"el servidor respondió {respuesta.status}")
            cuerpo = respuesta.read(guias_web.MAX_BYTES + 1)
    except (urllib.error.URLError, OSError) as error:
        raise ValueError(f"no se pudo descargar {url}: {error}") from error
    if len(cuerpo) > guias_web.MAX_BYTES:
        raise ValueError("la lista pesa más de 2 MB")
    return cuerpo.decode("utf-8")


def actualizar(raiz: Path, texto: str) -> str:
    """Valida `texto` y escribe la copia en `raiz`. Devuelve «sin_cambios» o «guardada» (con las guías). Lanza ValueError si no vale o si no
    queda ninguna guía válida (no se pisa la copia buena con una vacía)."""
    lista = guias_web.validar_texto(texto)
    if not lista["guias"]:
        raise ValueError("el servidor no dio ninguna guía válida; se conserva la copia")
    nuevo = guias_web.serializar(lista)
    destino = raiz / ARCHIVO_COPIA
    anterior = destino.read_text(encoding="utf-8") if destino.is_file() else None
    if anterior is not None and _sin_fecha(anterior) == _sin_fecha(nuevo):
        return "sin_cambios"   # `actualizada` cambia en cada vuelta del servidor: no cuenta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(nuevo, encoding="utf-8", newline="\n")
    return f"guardada ({len(lista['guias'])} guías)"


def _sin_fecha(texto: str) -> list:
    """Las guías de un texto de lista (para comparar sin la fecha); [] si no se puede leer."""
    try:
        return guias_web.validar_texto(texto)["guias"]
    except ValueError:
        return []


def principal(argumentos: list[str] | None = None) -> int:
    """Punto de entrada; devuelve el código de salida."""
    analizador = argparse.ArgumentParser(description="Actualiza learn/guias.json desde el servidor de guías")
    analizador.add_argument("--desde", default=URL_GUIAS, help="archivo o dirección https de la que leer (por defecto, el servidor)")
    opciones = analizador.parse_args(argumentos)
    try:
        origen = opciones.desde
        texto = Path(origen).read_text(encoding="utf-8") if not origen.startswith("https://") else descargar(origen)
        print(actualizar(RAIZ, texto))
    except (ValueError, OSError) as error:
        print(f"no se actualiza: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(principal())
