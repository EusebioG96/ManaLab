"""ML-392: generar_pdfs_guia.py no reescribe (ni cambia la fecha de modificación de) un PDF o el ZIP cuyo contenido no ha cambiado."""
import os
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generar_pdfs_guia as G  # noqa: E402

try:
    import playwright.sync_api  # noqa: F401
    HAY_PLAYWRIGHT = True
except ImportError:
    HAY_PLAYWRIGHT = False

PDF_A = b"%PDF-1.4\n<</Producer (Skia)\n/CreationDate (D:20261119014546+00'00')\n/ModDate (D:20261119014546+00'00')>>\ncuerpo\n%%EOF\n"
PDF_B = PDF_A.replace(b"20261119014546", b"20261128042955")      # misma pasada de otro día: solo cambian las fechas
PDF_C = PDF_A.replace(b"cuerpo", b"cuerpX")                       # contenido distinto


class TestEscribirSiCambia(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.ruta = Path(self.dir.name) / "a.pdf"

    def test_quitar_fechas_iguala_pasadas_distintas_y_distingue_contenido(self):
        self.assertEqual(G.quitar_fechas(PDF_A), G.quitar_fechas(PDF_B))
        self.assertNotEqual(G.quitar_fechas(PDF_A), G.quitar_fechas(PDF_C))

    def test_no_existe_se_escribe(self):
        self.assertTrue(G.escribir_si_cambia(self.ruta, PDF_A, G.quitar_fechas))
        self.assertEqual(self.ruta.read_bytes(), PDF_A)

    def test_mismo_contenido_con_otra_fecha_no_toca_el_archivo(self):
        self.ruta.write_bytes(PDF_A)
        os.utime(self.ruta, ns=(1_000_000_000, 1_000_000_000))
        self.assertFalse(G.escribir_si_cambia(self.ruta, PDF_B, G.quitar_fechas))
        self.assertEqual(self.ruta.read_bytes(), PDF_A)
        self.assertEqual(self.ruta.stat().st_mtime_ns, 1_000_000_000)

    def test_contenido_distinto_se_reescribe(self):
        self.ruta.write_bytes(PDF_A)
        self.assertTrue(G.escribir_si_cambia(self.ruta, PDF_C, G.quitar_fechas))
        self.assertEqual(self.ruta.read_bytes(), PDF_C)


class TestZipDeterminista(unittest.TestCase):
    def test_mismo_contenido_da_los_mismos_bytes_aunque_pase_el_tiempo(self):
        with tempfile.TemporaryDirectory() as d:
            rutas = []
            for n in ("x", "y"):
                r = Path(d) / f"{n}.pdf"
                r.write_bytes(PDF_A + n.encode())
                rutas.append(r)
            primero = G.zip_determinista(rutas)
            time.sleep(2.1)   # el ZIP guarda la hora en pasos de 2 s: con la fecha real saldría distinto
            for r in rutas:
                os.utime(r)
            self.assertEqual(G.zip_determinista(rutas), primero)
            with zipfile.ZipFile(__import__("io").BytesIO(primero)) as z:
                self.assertEqual(z.namelist(), ["x.pdf", "y.pdf"])
                self.assertEqual(z.read("y.pdf"), PDF_A + b"y")


@unittest.skipUnless(HAY_PLAYWRIGHT, "sin Playwright")
class TestPasadaCompleta(unittest.TestCase):
    def test_segunda_pasada_no_cambia_nada(self):
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            (raiz / "guia").mkdir()
            for idioma in G.IDIOMAS:
                (raiz / "guia" / f"guia_manalab_{idioma}.html").write_text(f"<html><body><h1>{idioma}</h1></body></html>", encoding="utf-8")
            G.main(raiz)
            archivos = sorted((raiz / "guia").glob("*.pdf")) + [raiz / "guia" / "guia_manalab_9_idiomas.zip"]
            for a in archivos:
                os.utime(a, ns=(1_000_000_000, 1_000_000_000))
            antes = {a.name: a.read_bytes() for a in archivos}
            time.sleep(1.1)   # Chromium escribe la fecha con segundos: la segunda pasada trae otra
            G.main(raiz)
            for a in archivos:
                self.assertEqual(a.read_bytes(), antes[a.name], a.name)
                self.assertEqual(a.stat().st_mtime_ns, 1_000_000_000, a.name)


if __name__ == "__main__":
    unittest.main()
