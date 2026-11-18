#!/usr/bin/env python3
"""ML-324 (WEB-08): la validación de guías del navegador (learn/learn.js) y la de la construcción (tools/guias_web.py) deciden lo mismo,
con un corpus hostil. Hace falta `node` (se salta si no está).

Uso:  python3 -m pytest tools/test_pagina_learn_validacion.py
"""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import guias_web  # noqa: E402

FECHA = "2026-11-18T12:00:00.000Z"
SCRIPT_NODE = (
    "const L=require(process.argv[1]);const lista=JSON.parse(require('fs').readFileSync(0,'utf8'));"
    "process.stdout.write(JSON.stringify(lista.map(g=>L.validarLista({v:1,actualizada:'%s',guias:[g]}).guias[0]||null)));" % FECHA)


def base(**extra) -> dict:
    g = {"name": "Guía", "description": "Texto\ncon línea", "url": "https://metafy.gg/guides/a", "cover_url": "https://cdn.metafy.gg/c.png", "price": None,
         "subscriber_only": False, "authors": [{"name": "Ana"}], "average_rating": 8.5, "review_count": 4, "total_reading_time_minutes": 9, "purchase_count": 3}
    g.update(extra)
    return g


def corpus() -> list:
    hostiles = [
        {"url": "https://evil.com/g"}, {"url": "http://metafy.gg/g"}, {"url": "https://metafy.gg.evil.com/g"}, {"url": "https://evilmetafy.gg/g"},
        {"url": "https://user@metafy.gg/g"}, {"url": "https://metafy.gg:443/g"}, {"url": "https://metafy.gg/g\"onclick=1"}, {"url": "https://metafy.gg/a b"},
        {"url": "https://metafy.gg/ñ"}, {"url": "https://METAFY.GG/g"}, {"url": "https://www.metafy.gg/g"}, {"url": "https://metafy.gg/" + "a" * 300},
        {"url": "https://metafy.gg/​"}, {"url": "javascript:alert(1)"}, {"url": 5}, {"url": None}, {"url": "https://.metafy.gg/g"}, {"url": "https://a..metafy.gg/g"},
        {"cover_url": "https://evil.com/c.png"}, {"cover_url": "https://sub.metafy.gg/c.png"}, {"cover_url": "https://metafy.gg.evil.com/c"}, {"cover_url": 7},
        {"cover_url": ""}, {"cover_url": None},
        {"name": ""}, {"name": "   "}, {"name": "x" * 140}, {"name": "x" * 141}, {"name": "ñ" * 140}, {"name": "😀" * 140}, {"name": "😀" * 141},
        {"name": "a​b"}, {"name": "a\u0000b"}, {"name": "a\ud800b"}, {"name": "ab"}, {"name": "a b"}, {"name": "a͸b"}, {"name": "  recortada  "},
        {"name": 3}, {"name": None},
        {"description": None}, {"description": ""}, {"description": "a\tb\nc"}, {"description": "a\rb"}, {"description": "x" * 601}, {"description": "x" * 600},
        {"description": 4}, {"description": "a‮b"},
        {"subscriber_only": "true"}, {"subscriber_only": 1}, {"subscriber_only": None}, {"subscriber_only": True},
        {"price": {"value_in_cents": 999, "currency": "USD"}}, {"price": {"value_in_cents": 999, "currency": "EUR"}}, {"price": {"value_in_cents": -1, "currency": "USD"}},
        {"price": {"value_in_cents": 1.5, "currency": "USD"}}, {"price": {"value_in_cents": 10_000_001, "currency": "USD"}}, {"price": {"value_in_cents": 0, "currency": "USD"}},
        {"price": {"value_in_cents": "9", "currency": "USD"}}, {"price": "9"}, {"price": []}, {"price": {"value_in_cents": True, "currency": "USD"}},
        {"authors": []}, {"authors": [{"name": "A"}] * 5}, {"authors": [{"name": "A"}] * 6}, {"authors": [{"name": ""}]}, {"authors": [{"name": "x" * 61}]},
        {"authors": ["Ana"]}, {"authors": "Ana"}, {"authors": None}, {"authors": [{"nombre": "Ana"}]}, {"authors": [{"name": " Ana "}]},
        {"average_rating": 0}, {"average_rating": 0.99}, {"average_rating": 1}, {"average_rating": 10}, {"average_rating": 10.01}, {"average_rating": "8"},
        {"average_rating": True}, {"average_rating": None}, {"average_rating": 9.25},
        {"review_count": -1}, {"review_count": 1.5}, {"review_count": 10_000_001}, {"review_count": 10_000_000}, {"review_count": "3"}, {"review_count": True}, {"review_count": None},
        {"total_reading_time_minutes": 0}, {"total_reading_time_minutes": 100_001}, {"total_reading_time_minutes": -3}, {"total_reading_time_minutes": 2.5},
        {"purchase_count": 10_000_001}, {"purchase_count": -1}, {"purchase_count": "9"},
    ]
    return [base(**h) for h in hostiles] + [base(), "texto", 5, None, [], {}, {"name": "solo nombre"}]


class ValidacionIgualEnPythonYNavegador(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "hace falta node")
    def test_cada_guia_del_corpus_hostil_se_acepta_o_se_rechaza_igual_y_sale_igual(self):
        casos = json.loads(json.dumps(corpus()))   # lo mismo que verá node: tras pasar por JSON
        salida = subprocess.run(["node", "-e", SCRIPT_NODE, str(RAIZ / "learn" / "learn.js")], input=json.dumps(casos), capture_output=True, text=True, timeout=60)
        self.assertEqual(salida.returncode, 0, salida.stderr)
        de_js = json.loads(salida.stdout)
        self.assertEqual(len(de_js), len(casos))
        aceptadas = 0
        for i, caso in enumerate(casos):
            try:
                de_py = guias_web.validar_lista({"v": 1, "actualizada": FECHA, "guias": [caso]})["guias"]
            except (ValueError, TypeError) as error:
                self.fail(f"caso {i} {caso!r}: la lista no debería fallar por una guía mala ({error})")
            esperado = de_py[0] if de_py else None
            aceptadas += esperado is not None
            self.assertEqual(de_js[i], esperado, f"caso {i}: {json.dumps(caso, ensure_ascii=False)[:160]}")
        self.assertGreater(aceptadas, 10)
        self.assertLess(aceptadas, len(casos) - 40, "el corpus debe rechazar de verdad")

    @unittest.skipUnless(shutil.which("node"), "hace falta node")
    def test_la_copia_real_da_el_mismo_resultado_en_los_dos(self):
        texto = (RAIZ / "learn" / "guias.json").read_text(encoding="utf-8")
        script = ("const L=require(process.argv[1]);const t=require('fs').readFileSync(0,'utf8');process.stdout.write(JSON.stringify(L.validarLista(JSON.parse(t))));")
        salida = subprocess.run(["node", "-e", script, str(RAIZ / "learn" / "learn.js")], input=texto, capture_output=True, text=True, timeout=60)
        self.assertEqual(salida.returncode, 0, salida.stderr)
        self.assertEqual(json.loads(salida.stdout), guias_web.validar_texto(texto))

    @unittest.skipUnless(shutil.which("node"), "hace falta node")
    def test_el_dominio_de_las_guias_se_valida_en_el_navegador(self):
        """Protege la mutación «quitar la validación del dominio»: sin ella, una guía de otro dominio saldría en la lista."""
        script = "const L=require(process.argv[1]);process.stdout.write(String(L.enlaceHttps('https://evil.com/g',['metafy.gg'])));"
        salida = subprocess.run(["node", "-e", script, str(RAIZ / "learn" / "learn.js")], capture_output=True, text=True, timeout=30)
        self.assertEqual(salida.stdout, "false")


if __name__ == "__main__":
    unittest.main()
