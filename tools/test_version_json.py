"""Pruebas del generador de version.json, del workflow que lo publica y del archivo publicado (sin red)."""
import json
import re
import sys
import unittest
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import generar_version_json as G  # noqa: E402

SHA = "a" * 64
BASE = "https://github.com/EusebioG96/ManaLab/releases"
RELEASE = {
    "tag_name": "v2.3.0", "published_at": "2026-11-01T10:00:00Z", "html_url": f"{BASE}/tag/v2.3.0",
    "body": "## ManaLab 2.3.0\r\n\r\nIntro.\r\n\r\n### Descarga / Download\r\nRequisitos: Windows 10\r\n\r\n"
            "### Novedades / What's new\r\n\r\n- Cosa nueva\r\n- Compatible con Windows 11\r\n\r\n### Privacidad / Privacy\r\nsecreto\r\n",
    "assets": [
        {"name": "ManaLab-2.3.0-portable.zip", "browser_download_url": f"{BASE}/download/v2.3.0/ManaLab-2.3.0-portable.zip",
         "digest": "sha256:" + SHA},
        {"name": "ManaLab-2.3.0-portable.zip.sha256",
         "browser_download_url": f"{BASE}/download/v2.3.0/ManaLab-2.3.0-portable.zip.sha256"}]}


def leer(url):
    return f"{SHA.upper()}  ManaLab-2.3.0-portable.zip\n"


class TestGenerador(unittest.TestCase):
    def test_construye_los_campos(self):
        d = G.construir(RELEASE, leer)
        self.assertEqual({k: d[k] for k in d if k != "notas"}, {
            "esquema": 1, "tag": "v2.3.0", "version": "2.3.0", "fecha": "2026-11-01", "url": f"{BASE}/tag/v2.3.0",
            "descarga": f"{BASE}/download/v2.3.0/ManaLab-2.3.0-portable.zip", "sha256": SHA})

    def test_notas_solo_novedades_y_sin_windows(self):
        n = G.construir(RELEASE, leer)["notas"]
        self.assertIn("Cosa nueva", n)
        self.assertIn("Intro.", n)
        self.assertNotIn("secreto", n)
        self.assertNotIn("Requisitos", n)
        self.assertNotRegex(n, r"(?i)windows")

    def test_sha_solo_del_digest_si_no_hay_archivo(self):
        r = dict(RELEASE, assets=[RELEASE["assets"][0]])
        self.assertEqual(G.construir(r, leer)["sha256"], SHA)

    def test_rechaza_datos_malos(self):
        otro = lambda url: "b" * 64  # noqa: E731
        with self.assertRaises(ValueError):
            G.construir(RELEASE, otro)  # .sha256 y digest no coinciden
        with self.assertRaises(ValueError):
            G.construir(dict(RELEASE, tag_name="latest"), leer)
        with self.assertRaises(ValueError):
            G.construir(dict(RELEASE, html_url="https://otro.example/x"), leer)
        with self.assertRaises(ValueError):
            G.construir(dict(RELEASE, assets=[]), leer)
        sin_sha = dict(RELEASE, assets=[dict(RELEASE["assets"][0], digest="")])
        with self.assertRaises(ValueError):
            G.construir(sin_sha, leer)


class TestReescritura(unittest.TestCase):
    NUEVO = f"{BASE}/download/v2.3.0/ManaLab-2.3.0-portable.zip"
    HTML = ('<a class="boton" href="OLD" download data-descarga data-goatcounter-click="d" rel="noopener"><span>X</span></a>'
            '<a href="/otra">no</a><a href="https://x.es/" data-descarga>y</a><p>V <span data-version>2.2.1</span></p>'
            '<script type="application/ld+json">{"@type": "SoftwareApplication", "softwareVersion": "2.2.1", "name": "X"}</script>'
            '<footer><span id="version">v<span data-version>2.2.1</span></span></footer>')

    def test_reescribe_href_y_version(self):
        h = G.reescribir_enlaces(self.HTML, "2.3.0", self.NUEVO)
        self.assertEqual(h.count(f'href="{self.NUEVO}"'), 2)
        self.assertNotIn("OLD", h)
        self.assertIn('href="/otra"', h)
        self.assertIn("<span data-version>2.3.0</span>", h)
        self.assertIn('"softwareVersion": "2.3.0"', h)
        self.assertIn('<span id="version">v<span data-version>2.3.0</span></span>', h)
        self.assertNotIn("2.2.1", h)
        self.assertEqual(json.loads(re.search(r">({.*})</script>", h).group(1))["name"], "X")  # el JSON-LD sigue siendo JSON
        self.assertIn("data-goatcounter-click", h)
        self.assertEqual(G.reescribir_enlaces(h, "2.3.0", self.NUEVO), h)  # idempotente

    def test_rechaza_enlace_ajeno(self):
        with self.assertRaises(ValueError):
            G.reescribir_enlaces(self.HTML, "2.3.0", "https://otro.example/a.zip")
        with self.assertRaises(ValueError):
            G.reescribir_enlaces(self.HTML, "x", self.NUEVO)

    def test_paginas_publicadas_coinciden_con_version_json(self):
        d = json.loads((RAIZ / "version.json").read_text(encoding="utf-8"))
        for n in G.PAGINAS:
            h = (RAIZ / n).read_text(encoding="utf-8")
            self.assertEqual(G.reescribir_enlaces(h, d["version"], d["descarga"]), h, n)
            self.assertGreaterEqual(h.count("data-descarga"), 2, n)
            self.assertNotIn('href="https://github.com/EusebioG96/ManaLab/releases/latest"', h, n)

    def test_pie_y_json_ld_coinciden_con_version_json(self):
        """El pie estático (respaldo si falla el fetch de descarga.js) y el softwareVersion del JSON-LD no pueden quedarse viejos."""
        v = json.loads((RAIZ / "version.json").read_text(encoding="utf-8"))["version"]
        for n in G.PAGINAS:
            h = (RAIZ / n).read_text(encoding="utf-8")
            pie = re.findall(r'<span id="version">v<span data-version>([^<]*)</span></span>', h)
            self.assertEqual(pie, [v], f"{n}: el pie estático debe ser v{v} (con el span data-version que rellena descarga.js)")
            ld = re.findall(r'"softwareVersion":\s*"([^"]*)"', h)
            self.assertEqual(ld, [v], f"{n}: softwareVersion del JSON-LD debe ser {v}")
            versiones = {x for x in re.findall(r"<span data-version>([^<]*)</span>", h)}
            self.assertEqual(versiones, {v}, f"{n}: todos los span data-version deben ser {v}")

    def test_workflow_incluye_paginas(self):
        t = (RAIZ / ".github/workflows/version_json.yml").read_text(encoding="utf-8")
        self.assertIn("git add version.json index.html es/index.html", t)


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.wf = yaml.safe_load((RAIZ / ".github/workflows/version_json.yml").read_text(encoding="utf-8"))
        self.on = self.wf.get("on", self.wf.get(True))  # PyYAML lee «on» como True

    def test_disparadores(self):
        self.assertEqual(self.on["release"]["types"], ["published"])
        self.assertIn("workflow_dispatch", self.on)

    def test_permisos_minimos(self):
        self.assertEqual(self.wf["permissions"], {"contents": "write"})

    def test_usa_token_y_hace_commit_a_main(self):
        texto = (RAIZ / ".github/workflows/version_json.yml").read_text(encoding="utf-8")
        self.assertIn("secrets.GITHUB_TOKEN", texto)
        self.assertIn("generar_version_json.py", texto)
        self.assertIn("git push origin HEAD:main", texto)
        pasos = self.wf["jobs"]["version-json"]["steps"]
        self.assertEqual(pasos[0]["with"]["ref"], "main")
        self.assertNotRegex(texto, r"(?i)windows")


class TestArchivoPublicado(unittest.TestCase):
    def test_version_json_valido(self):
        d = json.loads((RAIZ / "version.json").read_text(encoding="utf-8"))
        self.assertEqual(d["esquema"], 1)
        self.assertRegex(d["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(d["tag"], "v" + d["version"])
        self.assertRegex(d["sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(d["url"].startswith(BASE + "/"))
        self.assertEqual(d["descarga"], f"{BASE}/download/{d['tag']}/ManaLab-{d['version']}-portable.zip")
        self.assertRegex(d["fecha"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertNotRegex(json.dumps(d, ensure_ascii=False), r"(?i)windows")


if __name__ == "__main__":
    unittest.main()
