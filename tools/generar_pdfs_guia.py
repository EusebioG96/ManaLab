#!/usr/bin/env python3
"""Regenera los PDF de la guía (guia/guia_manalab_<idioma>.pdf) y el ZIP de los 9 idiomas a partir del HTML.

Los PDF no pueden llevar vídeo: al imprimir, cada <video> muestra su póster y el pie añade el enlace a la sección web
(.solo-pdf, visible solo al imprimir). Usa Chromium sin cabeza con Playwright (pip install playwright; playwright install chromium).

Uso:  python3 tools/generar_pdfs_guia.py [raíz_del_repo]
"""
import sys
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

IDIOMAS = ["es", "en", "de", "fr", "it", "pt", "ja", "ko", "zh"]


def main(raiz):
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
            pagina.pdf(path=str(guia / f"guia_manalab_{idioma}.pdf"), prefer_css_page_size=True, print_background=True)
            print("PDF", idioma)
        nav.close()
    destino = guia / "guia_manalab_9_idiomas.zip"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for idioma in IDIOMAS:
            z.write(guia / f"guia_manalab_{idioma}.pdf", f"guia_manalab_{idioma}.pdf")
    print("ZIP", destino)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
