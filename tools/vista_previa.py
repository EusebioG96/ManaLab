#!/usr/bin/env python3
"""Vista previa local de la web de ManaLab (ML-329): sirve la raíz del repositorio como lo hace GitHub Pages. Solo biblioteca estándar.

Uso:
    python3 tools/vista_previa.py                 sirve http://localhost:8000 (si está ocupado, el siguiente libre) y abre el navegador
    python3 tools/vista_previa.py --puerto 9000   empieza a buscar puerto en el 9000
    python3 tools/vista_previa.py --sin-abrir     no abre el navegador
    python3 tools/vista_previa.py --construir     antes ejecuta tools/construir_web.py (regenera los .html desde plantillas/)

Como GitHub Pages: ``/carpeta/`` da ``carpeta/index.html``; ``/carpeta`` redirige a ``/carpeta/``; ``/pagina`` da ``pagina.html`` si existe;
una ruta que no existe da 404 con el contenido de ``404.html``. No sirve nada fuera de la raíz (se rechaza ``..``) ni la carpeta ``.git``.
Solo escucha en 127.0.0.1: la web no se ve desde otros equipos. Windows: tools/ver_web.bat lo lanza con doble clic.
"""
import argparse
import http.server
import mimetypes
import os
import re
import socketserver
import subprocess
import sys
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

RAIZ = Path(__file__).resolve().parent.parent
PUERTO_POR_DEFECTO = 8000   # el que se prueba primero
PUERTOS_A_PROBAR = 50       # cuántos puertos seguidos se prueban antes de rendirse
DIRECCION = "127.0.0.1"     # solo este equipo; la URL que se enseña usa «localhost»
ARCHIVO_404 = "404.html"
ARCHIVO_INDICE = "index.html"
CARPETA_PROHIBIDA = ".git"  # nunca se sirve, esté donde esté en la ruta
# Páginas que se imprimen al arrancar (si el archivo existe): portadas, Learn en sus cuatro idiomas, privacidad y seguridad.
PAGINAS_PRINCIPALES = (
    ("Portada (en)", "/"), ("Portada (es)", "/es/"), ("Portada (pt)", "/pt/"), ("Portada (ja)", "/ja/"),
    ("Learn (en)", "/learn/"), ("Aprender (es)", "/es/aprender/"), ("Aprender (pt)", "/pt/aprender/"), ("Learn (ja)", "/ja/learn/"),
    ("Privacidad", "/privacy/"), ("Seguridad (en)", "/safety/"), ("Seguridad (es)", "/es/seguridad/"),
)
# Tipos que el navegador necesita bien y que el sistema (sobre todo Windows) puede no tener o tener distintos.
TIPOS_MIME = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8", ".xml": "application/xml; charset=utf-8", ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml", ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".ico": "image/x-icon",
    ".woff2": "font/woff2", ".mp4": "video/mp4", ".webm": "video/webm", ".pdf": "application/pdf",
}
TIPO_POR_DEFECTO = "application/octet-stream"
_RANGO = re.compile(r"bytes=(\d*)-(\d*)$")


@dataclass(frozen=True)
class Resolucion:
    """Qué hacer con una petición: ``estado`` es archivo, redireccion, prohibido o no_existe."""
    estado: str
    archivo: Path | None = None
    destino: str = ""


def tipo_mime(archivo: Path) -> str:
    """Tipo de contenido de ``archivo`` según su extensión (con juego de caracteres en el texto)."""
    extension = archivo.suffix.lower()
    return TIPOS_MIME.get(extension) or mimetypes.guess_type(archivo.name)[0] or TIPO_POR_DEFECTO


def _ruta_limpia(ruta_url: str) -> str | None:
    """La ruta de la URL sin consulta ni fragmento y decodificada; ``None`` si trae un byte nulo o un segmento ``..`` (también con ``\\``)."""
    ruta = unquote(urlsplit(ruta_url).path)
    if "\0" in ruta:
        return None
    segmentos = ruta.replace("\\", "/").split("/")
    return None if ".." in segmentos else ruta


def _dentro_de_la_raiz(raiz: Path, candidato: Path) -> bool:
    """¿``candidato`` (con los enlaces simbólicos resueltos) queda dentro de ``raiz``?"""
    try:
        return candidato.resolve().is_relative_to(raiz.resolve())
    except (OSError, ValueError):
        return False


def resolver(raiz: Path, ruta_url: str) -> Resolucion:
    """Decide qué sirve ``ruta_url`` como GitHub Pages: archivo, redirección ``/x`` a ``/x/``, prohibido (``..``) o no_existe."""
    ruta = _ruta_limpia(ruta_url)
    if ruta is None:
        return Resolucion("prohibido")
    partes = [p for p in ruta.replace("\\", "/").split("/") if p]
    if CARPETA_PROHIBIDA in partes:
        return Resolucion("no_existe")
    candidato = raiz.joinpath(*partes)
    if not _dentro_de_la_raiz(raiz, candidato):
        return Resolucion("prohibido")
    if candidato.is_dir():
        if not ruta.endswith("/") and partes:
            consulta = urlsplit(ruta_url).query
            return Resolucion("redireccion", destino=quote(ruta) + "/" + ("?" + consulta if consulta else ""))
        candidato = candidato / ARCHIVO_INDICE
    elif not candidato.is_file() and partes and candidato.with_name(candidato.name + ".html").is_file():
        candidato = candidato.with_name(candidato.name + ".html")   # GitHub Pages: /pagina da pagina.html
    return Resolucion("archivo", candidato) if candidato.is_file() else Resolucion("no_existe")


def rango_pedido(cabecera: str | None, tamano: int) -> tuple[int, int] | None:
    """Los bytes (inicio, fin) inclusivos de una cabecera ``Range: bytes=a-b``; ``None`` si no hay cabecera o no es un rango válido."""
    coincide = _RANGO.match(cabecera or "")
    if coincide is None or not (coincide.group(1) or coincide.group(2)):
        return None
    if not coincide.group(1):   # bytes=-N: los últimos N
        inicio, fin = max(tamano - int(coincide.group(2)), 0), tamano - 1
    else:
        inicio, fin = int(coincide.group(1)), int(coincide.group(2) or tamano - 1)
    return (inicio, min(fin, tamano - 1)) if inicio <= min(fin, tamano - 1) else None


class Manejador(http.server.BaseHTTPRequestHandler):
    """Atiende GET y HEAD. Cada hilo del servidor ejecuta uno; la raíz sale de ``self.server.raiz`` y no cambia."""
    protocol_version = "HTTP/1.1"
    server_version = "VistaPreviaManaLab"

    def log_message(self, formato: str, *argumentos) -> None:
        """Solo se anotan los errores (404, 403...): una web entera son cientos de peticiones y taparían lo útil."""
        if len(argumentos) >= 2 and str(argumentos[1]).isdigit() and int(argumentos[1]) >= 400:
            sys.stderr.write(f"  {argumentos[1]}  {self.path}\n")

    def do_GET(self) -> None:
        self._atender(con_cuerpo=True)

    def do_HEAD(self) -> None:
        self._atender(con_cuerpo=False)

    def _atender(self, con_cuerpo: bool) -> None:
        resolucion = resolver(self.server.raiz, self.path)
        if resolucion.estado == "redireccion":
            self._responder(301, b"", "text/plain", {"Location": resolucion.destino}, con_cuerpo)
        elif resolucion.estado == "prohibido":
            self._responder(400, "Ruta no permitida".encode("utf-8"), "text/plain; charset=utf-8", {}, con_cuerpo)
        elif resolucion.estado == "archivo":
            self._servir(resolucion.archivo, con_cuerpo)
        else:
            self._servir_404(con_cuerpo)

    def _servir_404(self, con_cuerpo: bool) -> None:
        pagina = self.server.raiz / ARCHIVO_404
        try:
            cuerpo = pagina.read_bytes()
        except OSError:
            cuerpo = "404: no existe".encode("utf-8")
        self._responder(404, cuerpo, TIPOS_MIME[".html"] if pagina.is_file() else "text/plain; charset=utf-8", {}, con_cuerpo)

    def _servir(self, archivo: Path, con_cuerpo: bool) -> None:
        try:
            datos = archivo.read_bytes()
        except OSError:
            self._servir_404(con_cuerpo)
            return
        rango = rango_pedido(self.headers.get("Range"), len(datos))
        if rango is None:
            self._responder(200, datos, tipo_mime(archivo), {"Accept-Ranges": "bytes"}, con_cuerpo)
            return
        inicio, fin = rango
        extra = {"Accept-Ranges": "bytes", "Content-Range": f"bytes {inicio}-{fin}/{len(datos)}"}
        self._responder(206, datos[inicio:fin + 1], tipo_mime(archivo), extra, con_cuerpo)

    def _responder(self, estado: int, cuerpo: bytes, tipo: str, extra: dict[str, str], con_cuerpo: bool) -> None:
        self.send_response(estado)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")   # es una vista previa: siempre lo último que hay en disco
        for nombre, valor in extra.items():
            self.send_header(nombre, valor)
        self.end_headers()
        if con_cuerpo:
            self.wfile.write(cuerpo)


class Servidor(socketserver.ThreadingTCPServer):
    """Servidor con un hilo por petición. En Windows no se reutiliza la dirección: ahí permitiría abrir un puerto ya ocupado."""
    allow_reuse_address = os.name != "nt"
    daemon_threads = True

    def __init__(self, raiz: Path, puerto: int):
        self.raiz = raiz
        super().__init__((DIRECCION, puerto), Manejador)


def abrir_servidor(raiz: Path, puerto: int, intentos: int = PUERTOS_A_PROBAR) -> Servidor:
    """Un servidor ya escuchando en el primer puerto libre desde ``puerto``; ``puerto`` 0 pide uno cualquiera al sistema.

    Lanza ``OSError`` si ninguno de los ``intentos`` puertos seguidos está libre.
    """
    ultimo_error = OSError("sin puertos libres")
    for candidato in ([0] if puerto == 0 else range(puerto, puerto + intentos)):
        try:
            return Servidor(raiz, candidato)
        except OSError as error:   # el puerto está ocupado (o no se puede usar): se prueba el siguiente
            ultimo_error = error
    raise OSError(f"no hay un puerto libre entre {puerto} y {puerto + intentos - 1}: {ultimo_error}")


def urls_principales(raiz: Path, puerto: int) -> list[tuple[str, str]]:
    """Pares (nombre, URL) de las páginas principales que existen en ``raiz``."""
    salida = []
    for nombre, ruta in PAGINAS_PRINCIPALES:
        if resolver(raiz, ruta).estado == "archivo":
            salida.append((nombre, f"http://localhost:{puerto}{ruta}"))
    return salida


def construir_web(raiz: Path) -> int:
    """Ejecuta tools/construir_web.py sobre ``raiz`` y devuelve su código de salida."""
    return subprocess.call([sys.executable, str(raiz / "tools" / "construir_web.py")], cwd=raiz)


def leer_argumentos(argumentos: list[str] | None) -> argparse.Namespace:
    """Las opciones de la línea de órdenes (``--puerto``, ``--sin-abrir``, ``--construir``)."""
    analizador = argparse.ArgumentParser(description="Vista previa local de la web de ManaLab, sin desplegarla.")
    analizador.add_argument("--puerto", type=int, default=PUERTO_POR_DEFECTO, help=f"puerto por el que empezar (por defecto {PUERTO_POR_DEFECTO})")
    analizador.add_argument("--sin-abrir", action="store_true", help="no abrir el navegador")
    analizador.add_argument("--construir", action="store_true", help="antes de servir, regenerar los .html con tools/construir_web.py")
    return analizador.parse_args(argumentos)


def principal(argumentos: list[str] | None = None) -> int:
    """Punto de entrada: construye si se pidió, abre el servidor, escribe las URLs y sirve hasta Ctrl+C."""
    opciones = leer_argumentos(argumentos)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")   # consola de Windows con otra codificación: nunca falla por un acento
    if opciones.construir and construir_web(RAIZ) != 0:
        print("construir_web.py ha fallado: no se arranca la vista previa.")
        return 1
    try:
        servidor = abrir_servidor(RAIZ, opciones.puerto)
    except OSError as error:
        print(f"No se pudo abrir el servidor: {error}")
        return 1
    puerto = servidor.server_address[1]
    print(f"Vista previa de la web en http://localhost:{puerto}/   (Ctrl+C para parar)\n")
    for nombre, url in urls_principales(RAIZ, puerto):
        print(f"  {nombre:<16} {url}")
    print()
    if not opciones.sin_abrir:
        threading.Timer(0.3, webbrowser.open, args=(f"http://localhost:{puerto}/",)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nVista previa parada.")
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
