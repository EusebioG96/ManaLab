"""Pruebas de metricas_semanales (datos de ejemplo, sin red)."""
import io
import json
import sys
import urllib.error
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
        md = M.resumen_markdown(b, a, 7, ({}, "TOTAL: HTTP 403"))
        self.assertIn("ZIP nuevos: **9**", md)
        self.assertIn("Versiones nuevas: v1.1.0", md)
        self.assertIn("Visitas: sin datos (activa el contador público en GoatCounter)", md)
        self.assertIn("Última versión (v1.1.0)", md)
        self.assertIn("APROXIMADO", md)
        self.assertNotIn("no 7", md)
        self.assertIn("primera", M.resumen_markdown(b, None, None))
        self.assertIn("no 7", M.resumen_markdown(b, a, 8))
        self.assertIn("Total del sitio: **55**", M.resumen_markdown(b, a, 7, ({"TOTAL": 55}, None)))

    def test_visitas_diferencia_semanal(self):
        a = M.foto(R1, date(2026, 10, 23), {"TOTAL": 1000, "/": 600})
        b = M.foto(R2, date(2026, 10, 30), {"TOTAL": 1234, "/": 700, "/es/": 50})
        self.assertEqual(M.diferencia_visitas(b, a), {"TOTAL": 234, "/": 100})
        self.assertIsNone(M.diferencia_visitas(b, M.foto(R1, date(2026, 10, 23))))
        md = M.resumen_markdown(b, a, 7, (b["visitas"], None))
        self.assertIn("Total del sitio: **1234** (+234 esta semana)", md)
        self.assertIn("- /: 700 (+100)", md)

    def test_visitas_403(self):
        err = urllib.error.HTTPError("u", 403, "Forbidden", {}, None)
        with mock.patch("urllib.request.urlopen", side_effect=err) as uo:
            self.assertEqual(M.leer_visitas(["TOTAL", "/"]), ({}, "TOTAL: HTTP 403 (contador público desactivado)"))
            self.assertEqual(uo.call_count, 1)  # no insiste con el resto

    def test_visitas_ok_y_url(self):
        resp = mock.MagicMock()
        resp.__enter__.return_value = io.BytesIO(b'{"count": "1,234", "count_unique": "900"}')
        with mock.patch("urllib.request.urlopen", return_value=resp) as uo:
            self.assertEqual(M.leer_visitas(["/es/"]), ({"/es/": 1234}, None))
            self.assertIn("/counter/%2Fes%2F.json", uo.call_args[0][0].full_url)

    def test_rutas_desde_sitemap(self):
        with tempfile.TemporaryDirectory() as d:
            sm = Path(d) / "sitemap.xml"
            sm.write_text("<loc>https://manalab.es/guia/guia_manalab_es.html</loc><loc>https://manalab.es/privacy/</loc>", encoding="utf-8")
            r = M.rutas_visitas(sm)
        self.assertEqual(r[0], "TOTAL")
        self.assertIn("/guia/guia_manalab_es.html", r)
        self.assertEqual(len(r), len(set(r)))
        self.assertIn("/es/seguridad/", r)

    def test_historico_carga_guarda_y_sustituye(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "sub" / "historico.json"
            self.assertEqual(M.cargar_historial(ruta), [])
            M.escribir_historial(ruta, [M.foto(R1, date(2026, 10, 23))])
            self.assertEqual(M.cargar_historial(ruta)[0]["fecha"], "2026-10-23")
            with mock.patch.object(M, "leer_releases", return_value=R2), mock.patch.object(M, "leer_visitas", return_value=({}, "x")), mock.patch("builtins.print"):
                M.main(["--historico", str(ruta)])
                M.main(["--historico", str(ruta)])  # mismo día: sustituye
            fotos = json.loads(ruta.read_text(encoding="utf-8"))["fotos"]
            self.assertEqual(len(fotos), 2)

    def test_main_guarda_historial_sin_red(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "h.json"
            with mock.patch.object(M, "leer_releases", return_value=R1), mock.patch.object(M, "leer_visitas", return_value=({}, "HTTP 403")):
                with mock.patch("builtins.print"):
                    self.assertEqual(M.main(["--historial", str(ruta)]), 0)
                    self.assertEqual(len(json.loads(ruta.read_text())["fotos"]), 1)
                    M.main(["--historial", str(ruta), "--sin-guardar"])
            self.assertEqual(len(M.cargar_historial(ruta)), 1)


if __name__ == "__main__":
    unittest.main()
