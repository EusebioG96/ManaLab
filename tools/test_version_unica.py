#!/usr/bin/env python3
"""ML-197: la versión actual sale de una sola fuente (version.json) y todas las páginas la muestran. Sin red.

Comprueba que ninguna página generada trae una versión de descarga distinta de la actual, y que una release nueva
(simulada) cambia todas las páginas con versión a la vez y no toca nada más.

Uso:  python3 tools/test_version_unica.py
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import construir_web  # noqa: E402

RAIZ = construir_web.RAIZ
NUEVA = "2.3.99"  # versión inventada para simular una release
# toda mención de versión «actual» en una página: descarga, manual, texto data-version y JSON-LD
_DESCARGA = re.compile(r"releases/download/v(\d+\.\d+\.\d+)/ManaLab-(?:(\d+\.\d+\.\d+)-portable\.zip|manual-en\.pdf)")
_TEXTO = re.compile(r"<span data-version>([^<]*)</span>")
_JSON_LD = re.compile(r'"softwareVersion":\s*"([^"]*)"')


def _version_actual() -> str:
    return json.loads((RAIZ / "version.json").read_text(encoding="utf-8"))["version"]


def _versiones_de(html: str) -> set[str]:
    """Todas las versiones «actuales» que cita una página."""
    encontradas = set(_TEXTO.findall(html)) | set(_JSON_LD.findall(html))
    for coincidencia in _DESCARGA.finditer(html):
        encontradas.update(v for v in coincidencia.groups() if v)
    return encontradas


def _copiar_repositorio(destino: Path) -> None:
    shutil.copytree(RAIZ / construir_web.CARPETA_PLANTILLAS, destino / construir_web.CARPETA_PLANTILLAS)
    shutil.copy(RAIZ / construir_web.ARCHIVO_VERSION, destino / construir_web.ARCHIVO_VERSION)


def _generar(raiz: Path, salida: Path) -> dict[Path, bytes]:
    construir_web.construir(raiz, salida)
    return {p: (salida / p).read_bytes() for p in construir_web.listar_paginas(raiz)}


class TestVersionUnica(unittest.TestCase):
    def test_ninguna_pagina_trae_otra_version_de_descarga(self):
        actual = _version_actual()
        for relativa in construir_web.listar_paginas(RAIZ):
            versiones = _versiones_de((RAIZ / relativa).read_text(encoding="utf-8"))
            self.assertLessEqual(versiones, {actual}, f"{relativa.as_posix()}: {versiones} y la actual es {actual}")

    def test_las_paginas_de_descarga_la_muestran_y_enlazan(self):
        actual = _version_actual()
        zip_actual = f"releases/download/v{actual}/ManaLab-{actual}-portable.zip"
        con_descarga = [p for p in construir_web.listar_paginas(RAIZ)
                        if "data-descarga" in (RAIZ / p).read_text(encoding="utf-8")]
        self.assertGreaterEqual(len(con_descarga), 13)
        for relativa in con_descarga:
            html = (RAIZ / relativa).read_text(encoding="utf-8")
            self.assertIn(zip_actual, html, relativa.as_posix())
            if "nota-descarga" in html:
                self.assertIn(f"<span data-version>{actual}</span>", html, relativa.as_posix())

    def test_las_fuentes_no_llevan_numeros_de_version_escritos(self):
        for ruta in (RAIZ / construir_web.CARPETA_PLANTILLAS).rglob("*"):
            if ruta.is_file():
                escritas = _versiones_de(ruta.read_text(encoding="utf-8")) - {construir_web.MARCA_VERSION}
                self.assertEqual(set(), escritas, ruta.as_posix())

    def test_sin_marcas_sin_sustituir_en_las_paginas(self):
        for relativa in construir_web.listar_paginas(RAIZ):
            self.assertNotIn(construir_web.MARCA_VERSION, (RAIZ / relativa).read_text(encoding="utf-8"))

    def test_version_json_invalido_da_error(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            with self.assertRaises(ValueError):
                construir_web.leer_version(raiz)  # no existe
            (raiz / construir_web.ARCHIVO_VERSION).write_text('{"version": "dos"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                construir_web.leer_version(raiz)


class TestReleaseNueva(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _nueva_release(self) -> tuple[dict[Path, bytes], dict[Path, bytes]]:
        antes = _generar(RAIZ, self.tmp / "antes")
        raiz = self.tmp / "repo"
        _copiar_repositorio(raiz)
        datos = json.loads((raiz / construir_web.ARCHIVO_VERSION).read_text(encoding="utf-8"))
        (raiz / construir_web.ARCHIVO_VERSION).write_text(json.dumps(dict(datos, version=NUEVA)), encoding="utf-8")
        return antes, _generar(raiz, self.tmp / "despues")

    def test_todas_las_paginas_con_version_cambian_a_la_vez(self):
        actual = _version_actual()
        antes, despues = self._nueva_release()
        con_version = {p for p, datos in antes.items() if _versiones_de(datos.decode("utf-8"))}
        self.assertGreaterEqual(len(con_version), 16)
        self.assertEqual(con_version, {p for p in antes if antes[p] != despues[p]})
        for relativa in con_version:
            nuevo = despues[relativa].decode("utf-8")
            self.assertEqual({NUEVA}, _versiones_de(nuevo), relativa.as_posix())
            self.assertNotIn(f"/v{actual}/", nuevo)

    def test_no_cambia_nada_mas_que_la_version(self):
        actual = _version_actual()
        antes, despues = self._nueva_release()
        for relativa, datos in antes.items():
            esperado = datos.decode("utf-8")
            esperado = re.sub(r"(?<![\d.])" + re.escape(actual) + r"(?![\d.])", NUEVA, esperado)
            self.assertEqual(esperado, despues[relativa].decode("utf-8"), relativa.as_posix())


if __name__ == "__main__":
    unittest.main()
