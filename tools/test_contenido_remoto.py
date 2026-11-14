"""ML-271: valida contenido.json (el archivo que lee la app) contra el esquema v1 y comprueba que el validador rechaza lo malo.

Uso:  python3 -m pytest tools/test_contenido_remoto.py     (o python3 tools/test_contenido_remoto.py)
"""
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "contenido.json"
MAX_BYTES = 64 * 1024  # tope de tamaño que acepta la app
MAX_ENLACE = 300  # tope de caracteres de un enlace
CAMPOS_ENLACE = ("enlace_apoyo_metafy", "enlace_suscripcion_ia")  # los dos enlaces de Metafy
HOSTS = ("metafy.gg", "manalab.es")  # el propio host o cualquier subdominio (www incluido)
VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def _host_valido(host):
    return any(host == h or host.endswith("." + h) for h in HOSTS)


def _enlace_valido(valor):
    if valor == "":
        return True
    if not isinstance(valor, str) or len(valor) > MAX_ENLACE or not valor.startswith("https://"):
        return False
    try:
        u = urlparse(valor)
        return bool(u.hostname) and _host_valido(u.hostname) and u.username is None and u.password is None and u.port is None
    except ValueError:
        return False


def _interruptor_valido(valor):
    if isinstance(valor, bool):
        return True
    if not isinstance(valor, dict) or not isinstance(valor.get("valor"), bool):
        return False
    if set(valor) - {"valor", "desde", "hasta"}:
        return False
    return all(VERSION.match(valor[k]) for k in ("desde", "hasta") if k in valor and isinstance(valor[k], str)) and \
        all(isinstance(valor[k], str) for k in ("desde", "hasta") if k in valor)


def validar(datos, tamano):
    """Devuelve la lista de problemas del contenido (vacía si cumple el esquema v1)."""
    if tamano > MAX_BYTES:
        return ["más de 64 KB"]
    if not isinstance(datos, dict):
        return ["no es un objeto"]
    problemas = []
    if datos.get("v") != 1 or isinstance(datos.get("v"), bool):
        problemas.append("v debe ser 1")
    problemas += ["%s no válido" % c for c in CAMPOS_ENLACE if not _enlace_valido(datos.get(c))]
    interruptores = datos.get("interruptores")
    if not isinstance(interruptores, dict):
        problemas.append("interruptores debe ser un objeto")
    else:
        problemas += ["interruptor %s no válido" % k for k, v in interruptores.items() if not _interruptor_valido(v)]
    return problemas


def _con(**cambios):
    base = {"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "", "interruptores": {"banner_mdn": True}}
    base.update(cambios)
    return base


class ContenidoRemotoTest(unittest.TestCase):
    def test_archivo_real_cumple_el_esquema(self):
        crudo = ARCHIVO.read_bytes()
        self.assertEqual(validar(json.loads(crudo.decode("utf-8")), len(crudo)), [])

    def test_valores_iniciales_acordados(self):
        self.assertEqual(json.loads(ARCHIVO.read_text(encoding="utf-8")), _con())

    def test_no_esta_en_el_sitemap_ni_cuenta_goatcounter(self):
        self.assertNotIn("contenido.json", (RAIZ / "sitemap.xml").read_text(encoding="utf-8"))
        self.assertNotIn("goatcounter", ARCHIVO.read_text(encoding="utf-8").lower())

    def test_acepta_ejemplos_buenos(self):
        for d in (_con(enlace_apoyo_metafy="https://metafy.gg/@manalab"),
                  _con(enlace_apoyo_metafy="https://www.metafy.gg/x"),
                  _con(enlace_apoyo_metafy="https://sub.manalab.es/x"),
                  _con(interruptores={"banner_mdn": {"valor": False, "desde": "2.3.3", "hasta": "2.3.3"}}),
                  _con(interruptores={"a": {"valor": True}})):
            self.assertEqual(validar(d, 100), [], d)

    def test_el_enlace_de_suscripcion_sigue_las_mismas_reglas(self):
        self.assertEqual(validar(_con(enlace_suscripcion_ia="https://metafy.gg/@manalab/ia"), 100), [])
        for malo in ("http://metafy.gg/x", "https://evil.com/metafy.gg", "https://user@metafy.gg/x", "https://metafy.gg:8443/x",
                     "https://metafy.gg/" + "a" * 300, 5):
            self.assertNotEqual(validar(_con(enlace_suscripcion_ia=malo), 100), [], malo)
        self.assertNotEqual(validar({"v": 1, "enlace_apoyo_metafy": "", "interruptores": {}}, 100), [], "falta el campo")

    def test_rechaza_ejemplos_malos(self):
        malos = [
            _con(enlace_apoyo_metafy="https://evil.com/metafy.gg"),
            _con(enlace_apoyo_metafy="https://metafy.gg.evil.com/"),
            _con(enlace_apoyo_metafy="https://notmetafy.gg/"),
            _con(enlace_apoyo_metafy="http://metafy.gg/x"),
            _con(enlace_apoyo_metafy="https://user@metafy.gg/x"),
            _con(enlace_apoyo_metafy="https://metafy.gg:8443/x"),
            _con(enlace_apoyo_metafy="https://metafy.gg/" + "a" * 300),
            _con(v=2),
            _con(interruptores={"x": "si"}),
            _con(interruptores={"x": {"desde": "2.3.3"}}),
            _con(interruptores={"x": {"valor": True, "desde": "2.3"}}),
        ]
        for d in malos:
            self.assertNotEqual(validar(d, 100), [], d)
        self.assertNotEqual(validar(_con(), MAX_BYTES + 1), [])

    def test_mutacion_un_archivo_roto_falla(self):
        d = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        d["v"] = 2
        self.assertNotEqual(validar(d, 100), [])
        d["v"] = 1
        d["enlace_apoyo_metafy"] = "http://metafy.gg/x"
        self.assertNotEqual(validar(d, 100), [])
        d["enlace_apoyo_metafy"] = ""
        d["enlace_suscripcion_ia"] = "http://metafy.gg/x"
        self.assertNotEqual(validar(d, 100), [])


if __name__ == "__main__":
    unittest.main()
