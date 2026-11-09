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
            with mock.patch.object(M, "leer_releases", return_value=R2), mock.patch.object(M, "leer_visitas", return_value=({}, "x")), mock.patch.object(M, "leer_sitemap", return_value=(None, "ninguno")), mock.patch.object(M, "comprobar_paginas", return_value=[]), mock.patch("builtins.print"):
                M.main(["--historico", str(ruta)])
                M.main(["--historico", str(ruta)])  # mismo día: sustituye
            fotos = json.loads(ruta.read_text(encoding="utf-8"))["fotos"]
            self.assertEqual(len(fotos), 2)

    def test_main_guarda_historial_sin_red(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "h.json"
            with mock.patch.object(M, "leer_releases", return_value=R1), mock.patch.object(M, "leer_visitas", return_value=({}, "HTTP 403")), \
                    mock.patch.object(M, "leer_sitemap", return_value=(None, "ninguno")), mock.patch.object(M, "comprobar_paginas", return_value=[]):
                with mock.patch("builtins.print"):
                    self.assertEqual(M.main(["--historial", str(ruta)]), 0)
                    self.assertEqual(len(json.loads(ruta.read_text())["fotos"]), 1)
                    M.main(["--historial", str(ruta), "--sin-guardar"])
            self.assertEqual(len(M.cargar_historial(ruta)), 1)


def http_error(codigo, cuerpo=b"", cabeceras=None):
    import email.message
    h = email.message.Message()
    for k, v in (cabeceras or {}).items():
        h[k] = v
    return urllib.error.HTTPError("u", codigo, "x", h, io.BytesIO(cuerpo))


def resp_ok(cuerpo=b"", status=200):
    r = mock.MagicMock()
    r.__enter__.return_value = r
    r.read.return_value = cuerpo
    r.status = status
    return r


SITEMAP = ("<urlset><url><loc>https://manalab.es/</loc></url><url><loc>https://manalab.es/coaches/</loc></url>"
           "<url><loc>https://manalab.es/es/coaches/</loc><xhtml:link href=\"https://manalab.es/ignorada/\"/></url>"
           "<url><loc>https://manalab.es/pt/coaches/</loc></url><url><loc>https://manalab.es/sorteo/en/</loc></url>"
           "<url><loc>https://manalab.es/magic-online/</loc></url></urlset>")


class PruebasML139(unittest.TestCase):
    def test_repositorio_correcto(self):
        self.assertEqual(M.REPO, "EusebioG96/ManaLab")
        self.assertIn("/repos/EusebioG96/ManaLab/releases", M.URL_RELEASES)
        sh = (Path(__file__).resolve().parent / "metricas_ejecutar.sh").read_text(encoding="utf-8")
        self.assertIn("EusebioG96/ManaLab.git", sh)
        self.assertNotIn("EusebioG96/manalab", sh)
        self.assertNotIn("ML-057-metricas", sh)

    def test_releases_con_respuesta_simulada(self):
        cuerpo = json.dumps(R1).encode()
        with mock.patch("urllib.request.urlopen", return_value=resp_ok(cuerpo)) as uo:
            self.assertEqual(M.leer_releases("http")[0]["tag_name"], "v1.0.0")
            self.assertIn("EusebioG96/ManaLab/releases", uo.call_args[0][0].full_url)

    def test_404_de_goatcounter_es_cero_visitas(self):
        # GoatCounter: ruta sin visitas = HTTP 404 con {"count": "0"}; no es un fallo de la página.
        with mock.patch("urllib.request.urlopen", side_effect=http_error(404, b'{"count_unique":"0", "count":"0"}')):
            self.assertEqual(M.leer_visita("/es/seguridad/"), (0, "ok (sin visitas registradas)"))
        with mock.patch("urllib.request.urlopen", side_effect=http_error(404, b"<html>nope</html>")):
            n, motivo = M.leer_visita("/x/")
        self.assertIsNone(n)
        self.assertEqual(motivo, "HTTP 404")

    def test_visitas_con_ceros_no_cortan_la_lectura(self):
        def falso(req, timeout=None):
            if "%2Fes%2Fseguridad%2F" in req.full_url:
                raise http_error(404, b'{"count": "0"}')
            return resp_ok(b'{"count": "5"}')
        with mock.patch("urllib.request.urlopen", side_effect=falso):
            v, motivo = M.leer_visitas(["TOTAL", "/es/seguridad/", "/es/"])
        self.assertEqual(v, {"TOTAL": 5, "/es/seguridad/": 0, "/es/": 5})
        self.assertIsNone(motivo)

    def test_rutas_desde_el_sitemap_completo(self):
        r = M.rutas_visitas(texto=SITEMAP)
        for esperado in ("/coaches/", "/es/coaches/", "/pt/coaches/", "/sorteo/en/", "/magic-online/", "/sorteo/", "/es/seguridad/"):
            self.assertIn(esperado, r)
        self.assertNotIn("/ignorada/", r)  # solo <loc>, no los xhtml:link
        self.assertEqual(r[0], "TOTAL")
        self.assertEqual(len(r), len(set(r)))

    def test_leer_sitemap_web_y_respaldo(self):
        with mock.patch("urllib.request.urlopen", return_value=resp_ok(SITEMAP.encode())) as uo:
            texto, origen = M.leer_sitemap()
        self.assertEqual((origen, texto), ("web", SITEMAP))
        self.assertEqual(uo.call_args[0][0].full_url, "https://manalab.es/sitemap.xml")
        with tempfile.TemporaryDirectory() as d:
            loc = Path(d) / "sitemap.xml"
            loc.write_text(SITEMAP, encoding="utf-8")
            with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("sin red")):
                self.assertEqual(M.leer_sitemap(loc), (SITEMAP, "local"))
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("sin red")):
            self.assertEqual(M.leer_sitemap(Path("/nonexistent/sitemap.xml")), (None, "ninguno"))

    def test_url_con_barra(self):
        self.assertEqual(M.url_con_barra("https://manalab.es/es/seguridad"), "https://manalab.es/es/seguridad/")
        self.assertEqual(M.url_con_barra("https://manalab.es/es/seguridad/"), "https://manalab.es/es/seguridad/")
        self.assertEqual(M.url_con_barra("https://manalab.es/guia/guia_manalab_es.html"), "https://manalab.es/guia/guia_manalab_es.html")

    def _opener(self, respuestas):
        """Sustituye build_opener: cada open() consume la siguiente respuesta (o excepción) y guarda la URL pedida."""
        pedidas = []

        class Op:
            def open(self, req, timeout=None):
                pedidas.append((req.get_method(), req.full_url))
                r = respuestas.pop(0)
                if isinstance(r, Exception):
                    raise r
                return r
        return Op(), pedidas

    def test_pagina_200_redireccion_y_404(self):
        op, pedidas = self._opener([resp_ok(status=200)])
        with mock.patch("urllib.request.build_opener", return_value=op):
            r = M.comprobar_pagina("https://manalab.es/es/seguridad")
        self.assertEqual((r["estado"], r["saltos"]), ("ok", 0))
        self.assertEqual(pedidas[0][1], "https://manalab.es/es/seguridad/")  # usa la barra final
        # 301 -> 200: redirección, NO es un fallo
        op, _ = self._opener([http_error(301, cabeceras={"Location": "/otra/"}), resp_ok(status=200)])
        with mock.patch("urllib.request.build_opener", return_value=op):
            r = M.comprobar_pagina("https://manalab.es/vieja/")
        self.assertEqual((r["estado"], r["saltos"], r["final"]), ("redireccion", 1, "https://manalab.es/otra/"))
        # 404 real
        op, _ = self._opener([http_error(404)])
        with mock.patch("urllib.request.build_opener", return_value=op):
            self.assertEqual(M.comprobar_pagina("https://manalab.es/nada/")["estado"], "no_encontrada")
        # HEAD no admitido -> GET; sin red -> error
        op, pedidas = self._opener([http_error(405), resp_ok(status=200)])
        with mock.patch("urllib.request.build_opener", return_value=op):
            self.assertEqual(M.comprobar_pagina("https://manalab.es/a/")["estado"], "ok")
        self.assertEqual([m for m, _ in pedidas], ["HEAD", "GET"])
        op, _ = self._opener([urllib.error.URLError("x")])
        with mock.patch("urllib.request.build_opener", return_value=op):
            self.assertEqual(M.comprobar_pagina("https://manalab.es/a/")["estado"], "error")

    def test_redireccion_infinita_acaba_en_error(self):
        op, _ = self._opener([http_error(301, cabeceras={"Location": "/b/"}) for _ in range(10)])
        with mock.patch("urllib.request.build_opener", return_value=op):
            self.assertEqual(M.comprobar_pagina("https://manalab.es/a/")["estado"], "error")

    def test_eventos_agrupados_por_prefijo_e_idioma(self):
        g = M.agrupar_eventos({"descarga": 23, "descarga-mtgo-es": 2, "descarga-mtgo-en": 5, "descarga-mtgo-pt": 0,
                               "descarga-coaches-pt": 1, "compartir-movil": 3, "compartir-movil-coaches-es": 4})
        self.assertEqual(g["descarga"], {"total": 23, "idiomas": {}})
        self.assertEqual(g["descarga-mtgo"], {"total": 7, "idiomas": {"es": 2, "en": 5, "pt": 0}})
        self.assertEqual(g["descarga-coaches"]["total"], 1)
        self.assertEqual(g["compartir-movil"]["total"], 3)  # no se mezcla con compartir-movil-coaches
        self.assertEqual(g["compartir-movil-coaches"]["idiomas"], {"es": 4})

    def test_candidatos_de_eventos(self):
        c = M.eventos_candidatos()
        for n in ("descarga", "compartir-movil", "descarga-movil", "descarga-mtgo-es", "descarga-coaches-pt", "compartir-movil-coaches-en"):
            self.assertIn(n, c)
        self.assertEqual(len(c), len(set(c)))

    def test_resumen_eventos_paginas_y_dias(self):
        a = M.foto(R1, date(2026, 10, 23), {"TOTAL": 100}, {"descarga": 10, "descarga-mtgo-es": 1})
        b = M.foto(R2, date(2026, 11, 2), {"TOTAL": 160}, {"descarga": 25, "descarga-mtgo-es": 3, "descarga-mtgo-en": 2, "aviso-sorteo": 0})
        paginas = [{"url": "https://manalab.es/", "estado": "ok", "saltos": 0, "final": "https://manalab.es/"},
                   {"url": "https://manalab.es/v/", "estado": "redireccion", "saltos": 1, "final": "https://manalab.es/n/"},
                   {"url": "https://manalab.es/x/", "estado": "no_encontrada", "saltos": 0, "final": "https://manalab.es/x/"}]
        md = M.resumen_markdown(b, a, 10, (b["visitas"], None), (b["eventos"], None), paginas)
        self.assertIn("cubre 10 días, no 7", md)
        self.assertIn("(+60 en 10 días)", md)
        self.assertIn("- descarga: **25** (+15 en 10 días)", md)
        self.assertIn("- descarga-mtgo: **5** (+4 en 10 días) [en 2, es 3]", md)
        self.assertNotIn("aviso-sorteo:", md)  # los eventos a cero no ensucian
        self.assertIn("3 páginas comprobadas; 1 responden 200 directo, 1 con redirección (3xx, no es un fallo)", md)
        self.assertIn("PROBLEMA: https://manalab.es/x/ -> 404 no encontrada", md)
        md7 = M.resumen_markdown(b, a, 7, (b["visitas"], None), (b["eventos"], None), None)
        self.assertNotIn("cubre", md7)
        self.assertIn("(+60 esta semana)", md7)
        self.assertNotIn("Páginas del sitemap", md7)

    def test_foto_guarda_eventos_y_diferencia(self):
        a = M.foto(R1, date(2026, 10, 23), {"TOTAL": 1}, {"descarga": 4})
        b = M.foto(R1, date(2026, 10, 30), {"TOTAL": 2}, {"descarga": 9, "compartir-movil": 2})
        self.assertEqual(M.diferencia_visitas(b, a, "eventos"), {"descarga": 5, "compartir-movil": 2})  # evento nuevo: entero
        self.assertIsNone(M.diferencia_visitas(b, M.foto(R1, date(2026, 10, 23)), "eventos"))  # foto vieja sin eventos
        self.assertNotIn("eventos", M.foto(R1, date(2026, 10, 23)))

    def test_main_completo_con_respuestas_simuladas_sin_guardar(self):
        """main de punta a punta: GitHub, sitemap, GoatCounter y páginas simulados; --sin-guardar no escribe."""
        def falso(req, timeout=None):
            url = req.full_url
            if "api.github.com" in url:
                return resp_ok(json.dumps(R2).encode())
            if url.endswith("/sitemap.xml"):
                return resp_ok(SITEMAP.encode())
            if "%2Fes%2Fcoaches%2F" in url or "descarga-mtgo" in url:
                raise http_error(404, b'{"count": "0"}')
            return resp_ok(b'{"count": "7"}')
        op, _ = self._opener([resp_ok(status=200) for _ in range(20)])
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "h.json"
            salida = io.StringIO()
            with mock.patch("urllib.request.urlopen", side_effect=falso), mock.patch("urllib.request.build_opener", return_value=op), \
                    mock.patch("sys.stdout", salida):
                self.assertEqual(M.main(["--historico", str(ruta), "--sin-guardar"]), 0)
            self.assertFalse(ruta.exists())
        md = salida.getvalue()
        self.assertIn("- /es/coaches/: 0", md)
        self.assertIn("- /pt/coaches/: 7", md)
        self.assertIn("- descarga: **7**", md)
        self.assertNotIn("descarga-mtgo:", md)
        self.assertIn("responden 200 directo", md)


if __name__ == "__main__":
    unittest.main()
