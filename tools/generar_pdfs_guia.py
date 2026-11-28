#!/usr/bin/env python3
"""Regenera los PDF de la guía (guia/guia_manalab_<idioma>.pdf) y el ZIP de los 9 idiomas a partir del HTML.

Los PDF no pueden llevar vídeo: al imprimir, cada <video> muestra su póster y el pie añade el enlace a la sección web
(.solo-pdf, visible solo al imprimir). Usa Chromium sin cabeza con Playwright (pip install playwright; playwright install chromium).

Idempotente (ML-392): Chromium mete la fecha de creación en cada PDF, así que dos pasadas con el mismo HTML dan archivos distintos.
Un PDF solo se reescribe si, quitadas esas fechas, su contenido cambió; si no, se queda el archivo del repo tal cual (ni bytes ni fecha
de modificación). El ZIP lleva fechas fijas y solo se reescribe si cambia su contenido.

Uso:  python3 tools/generar_pdfs_guia.py [raíz_del_repo]
"""
import io
import re
import sys
import zipfile
from pathlib import Path

IDIOMAS = ["es", "en", "de", "fr", "it", "pt", "ja", "ko", "zh"]
# Chromium escribe /CreationDate y /ModDate en el diccionario Info del PDF, con la hora de la pasada. Es lo único que cambia entre
# dos pasadas con el mismo HTML (mismo largo, así que las posiciones del xref no se mueven).
_FECHAS_PDF = re.compile(rb"/(CreationDate|ModDate) \(D:[^)]*\)")
# Fecha fija para las entradas del ZIP (el mínimo que admite el formato): el ZIP sale igual en cada pasada.
FECHA_ZIP = (1980, 1, 1, 0, 0, 0)


def quitar_fechas(pdf: bytes) -> bytes:
    """Devuelve el PDF sin las fechas de creación y modificación, para comparar su contenido."""
    return _FECHAS_PDF.sub(rb"/\1 ()", pdf)


def escribir_si_cambia(ruta: Path, contenido: bytes, normalizar=lambda b: b) -> bool:
    """Escribe `contenido` en `ruta` solo si difiere (tras `normalizar`) de lo que ya hay. Devuelve True si escribió."""
    if ruta.is_file() and normalizar(ruta.read_bytes()) == normalizar(contenido):
        return False
    ruta.write_bytes(contenido)
    return True


def zip_determinista(archivos: list[Path]) -> bytes:
    """ZIP en memoria con los archivos dados (solo su nombre), con fecha fija y el mismo orden: mismos PDF, mismos bytes."""
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as z:
        for ruta in archivos:
            info = zipfile.ZipInfo(ruta.name, FECHA_ZIP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, ruta.read_bytes())
    return memoria.getvalue()


def main(raiz):
    # La importación va aquí para que las pruebas de las funciones de arriba no necesiten Playwright.
    from playwright.sync_api import sync_playwright
    guia = raiz / "guia"
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pagina = nav.new_page()
        for idioma in IDIOMAS:
            html = guia / f"guia_manalab_{idioma}.html"
            pagina.goto(html.as_uri(), wait_until="load")
            pagina.emulate_media(media="print")
            # las imágenes son loading="lazy": se fuerzan para que entren en el PDF
            pagina.evaluate("""async () => {
                const imgs = [...document.images];
                imgs.forEach(i => { i.loading = "eager"; });
                await Promise.all(imgs.map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
            }""")
            # dentro de un PDF un enlace «/coaches/» no lleva a ningún sitio: se hacen absolutos a manalab.es
            pagina.evaluate("""() => document.querySelectorAll('a[href^="/"]').forEach(a => {
                a.setAttribute("href", "https://manalab.es" + a.getAttribute("href"));
            })""")
            pdf = pagina.pdf(prefer_css_page_size=True, print_background=True)
            escrito = escribir_si_cambia(guia / f"guia_manalab_{idioma}.pdf", pdf, quitar_fechas)
            print("PDF", idioma, "reescrito" if escrito else "sin cambios")
        nav.close()
    destino = guia / "guia_manalab_9_idiomas.zip"
    contenido = zip_determinista([guia / f"guia_manalab_{idioma}.pdf" for idioma in IDIOMAS])
    escrito = escribir_si_cambia(destino, contenido)
    print("ZIP", destino, "reescrito" if escrito else "sin cambios")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
