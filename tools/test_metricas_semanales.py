"""Pruebas de metricas_semanales (datos de ejemplo, sin red)."""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metricas_semanales as M  # noqa: E402


def rel(tag, **assets):
    return {"tag_name": tag, "draft": False, "assets": [{"name": n, "download_count": c} for n, c in assets.items()]}


R1 = [rel("v1.0.0", **{"ManaLab-1.0.0-portable.zip": 10, "ManaLab-1.0.0-portable.zip.sha256": 4})]
R2 = [rel("v1.1.0", **{"ManaLab-1.1.0-portable.zip": 3, "ManaLab-portable.zip": 1, "ManaLab-portable.zip.sha256": 1}),
      rel("v1.0.0", **{"ManaLab-1.0.0-portable.zip": 15, "ManaLab-1.0.0-portable.zip.sha256": 6}),
      {"tag_name": "v9", "draft": True, "assets": [{"name": "ManaLab-9-portable.zip", "download_count": 99}]}]


class Pruebas(unittest.TestCase):
    def test_clasificar(self):
        self.assertEqual(M.clasificar("ManaLab-2.2.2-portable.zip"), "zip_version")
        self.assertEqual(M.clasificar("ManaLab-portable.zip"), "zip_estable")
        self.assertEqual(M.clasificar("ManaLab-2.2.2-portable.zip.sha256"), "sha256")
        self.assertEqual(M.clasificar("otra.exe"), "otro")

    def test_foto_y_totales(self):
        f = M.foto(R2, date(2026, 10, 30))
        self.assertNotIn("v9", f["versiones"])
        t = M.totales(f)
        self.assertEqual((t["zip_version"], t["zip_estable"], t["sha256"], t["descargas"]), (18, 1, 7, 19))

    def test_diferencia_semanal(self):
        a, b = M.foto(R1, date(2026, 10, 23)), M.foto(R2, date(2026, 10, 30))
        d = M.diferencia(b, a)
        self.assertEqual(d["versiones"]["v1.0.0"]["ManaLab-1.0.0-portable.zip"], 5)
        self.assertEqual(d["versiones"]["v1.1.0"]["ManaLab-1.1.0-portable.zip"], 3)  # asset nuevo: entero
        self.assertEqual(M.totales(d)["descargas"], 9)

    def test_diferencia_nunca_negativa(self):
        a, b = M.foto(R2, date(2026, 10, 23)), M.foto(R1, date(2026, 10, 30))
        self.assertEqual(M.totales(M.diferencia(b, a))["descargas"], 0)

    def test_elegir_previa(self):
        h = [{"fecha": "2026-10-10", "versiones": {}}, {"fecha": "2026-10-22", "versiones": {}}, {"fecha": "2026-10-29", "versiones": {}}]
        f, dias = M.elegir_previa(h, date(2026, 10, 30))
        self.assertEqual((f["fecha"], dias), ("2026-10-22", 8))
        self.assertEqual(M.elegir_previa([], date(2026, 10, 30)), (None, None))
        self.assertEqual(M.elegir_previa([{"fecha": "2026-10-30", "versiones": {}}], date(2026, 10, 30)), (None, None))

    def test_guardar_foto_sustituye_el_mismo_dia(self):
        a = M.foto(R1, date(2026, 10, 30))
        b = M.foto(R2, date(2026, 10, 30))
        h = M.guardar_foto(M.guardar_foto([], a), b)
        self.assertEqual(len(h), 1)
        self.assertEqual(h[0], b)

    def test_contador_gc(self):
        self.assertEqual(M.interpretar_contador({"count": "1 234"}), 1234)
        self.assertEqual(M.interpretar_contador({"count": "12"}), 12)
        self.assertIsNone(M.interpretar_contador({}))

    def test_resumen(self):
        a, b = M.foto(R1, date(2026, 10, 23)), M.foto(R2, date(2026, 10, 30))
        md = M.resumen_markdown(b, a, 7, (None, "HTTP 403"))
        self.assertIn("ZIP nuevos: **9**", md)
        self.assertIn("Versiones nuevas: v1.1.0", md)
        self.assertIn("Sin datos: HTTP 403", md)
        self.assertNotIn("no 7", md)
        self.assertIn("primera", M.resumen_markdown(b, None, None))
        self.assertIn("no 7", M.resumen_markdown(b, a, 8))
        self.assertIn("Total de visitas (contador público): 55", M.resumen_markdown(b, a, 7, (55, "ok")))

    def test_main_guarda_historial_sin_red(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "h.json"
            with mock.patch.object(M, "leer_releases", return_value=R1), mock.patch.object(M, "leer_visitas", return_value=(None, "HTTP 403")):
                with mock.patch("builtins.print"):
                    self.assertEqual(M.main(["--historial", str(ruta)]), 0)
                    self.assertEqual(len(json.loads(ruta.read_text())["fotos"]), 1)
                    M.main(["--historial", str(ruta), "--sin-guardar"])
            self.assertEqual(len(M.cargar_historial(ruta)), 1)


if __name__ == "__main__":
    unittest.main()
