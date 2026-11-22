"""ML-271: valida contenido.json (el archivo que lee la app) contra el esquema v1 y comprueba que el validador rechaza lo malo.

Uso:  python3 -m pytest tools/test_contenido_remoto.py     (o python3 tools/test_contenido_remoto.py)
"""
import json
import re
import unicodedata
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

# Reglas de coaches y destacados (ML-278). Copiadas de /home/claude/wt-vis/manalab_aprender_validar.py de la app (la web no importa
# código de la app): si allí cambian, hay que cambiarlas aquí.
DOCUMENTO = RAIZ / "docs" / "contenido_remoto.md"
CARPETA_FOTOS = RAIZ / "coaches" / "fotos"  # donde se suben las fotos; si no existe, no se comprueban los archivos
MAX_NOMBRE = 60  # MAX_NOMBRE de la app: caracteres del nombre
MAX_LINEA = 80  # MAX_LINEA de la app: caracteres de la línea
MAX_COACHES = 100  # MAX_COACHES de la app
MAX_DESTACADOS = 10  # MAX_DESTACADOS de la app
MAX_FOTO_BYTES = 20 * 1024  # tamaño acordado de una foto (160x160 WebP, 20 kB); no lo comprueba la app
DOMINIOS_METAFY = ("metafy.gg",)  # DOMINIOS_METAFY de la app: el host o un subdominio
DOMINIOS_FOTO = ("manalab.es",)  # DOMINIOS_FOTO de la app
EXTENSIONES_FOTO = (".webp", ".png", ".jpg")  # EXTENSIONES_FOTO de la app
PROHIBIDOS_ENLACE = frozenset("\"'<>\\")  # PROHIBIDOS_ENLACE de la app: comillas, ángulos y barra invertida
HOST = re.compile(r"[a-z0-9.-]+")  # HOST de la app
BIDI = frozenset(chr(c) for c in (*range(0x202A, 0x202F), *range(0x2066, 0x206A), 0x200E, 0x200F, 0x061C))  # BIDI de la app
EXTRAS_DESTACADO = ("academia", "guias", "sesiones")  # enlaces opcionales de un destacado
MAX_FRASE = 140  # ML-324 (VIS-23): caracteres de la frase del creador; texto plano


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


def _texto_valido(valor, maximo):
    """1 a `maximo` caracteres, sin control, invisibles ni inversión del sentido, con algo visible."""
    if not isinstance(valor, str) or not 0 < len(valor.strip()) <= maximo or len(valor) > maximo:
        return False
    return not any(c in BIDI or unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp", "Cs", "Co", "Cn") for c in valor)


def _enlace_https(valor, dominios):
    """https a un dominio (o subdominio) sin usuario, contraseña ni puerto, de hasta MAX_ENLACE caracteres."""
    if not isinstance(valor, str) or not valor.startswith("https://") or not valor.isascii() or not 0 < len(valor) <= MAX_ENLACE:
        return False
    if any(c.isspace() or ord(c) < 32 or c in PROHIBIDOS_ENLACE for c in valor):
        return False
    try:
        u = urlparse(valor)
        host = u.hostname or ""
        if u.username is not None or u.password is not None or ":" in u.netloc or not HOST.fullmatch(host) or "" in host.split("."):
            return False
    except ValueError:
        return False
    return any(host == d or host.endswith("." + d) for d in dominios)


def _foto_valida(valor):
    if not _enlace_https(valor, DOMINIOS_FOTO):
        return False
    u = urlparse(valor)
    return not u.query and not u.fragment and u.path.lower().endswith(EXTENSIONES_FOTO)


def _problemas_perfil(e, extras):  # `extras` no vacío = es un destacado: además admite frase y fondo
    if not isinstance(e, dict):
        return ["no es un objeto"]
    p = []
    if not _texto_valido(e.get("nombre"), MAX_NOMBRE):
        p.append("nombre no válido")
    if not _texto_valido(e.get("linea"), MAX_LINEA):
        p.append("línea no válida")
    if not _enlace_https(e.get("enlace"), DOMINIOS_METAFY):
        p.append("enlace no válido")
    if e.get("foto") not in (None, "") and not _foto_valida(e["foto"]):
        p.append("foto no válida")  # la app enseña al coach sin foto, pero en el archivo publicado no debe haberla mala
    for c in extras:
        if e.get(c) not in (None, "") and not _enlace_https(e[c], DOMINIOS_METAFY):
            p.append("%s no válido" % c)
    if extras:
        if e.get("frase") not in (None, "") and not _texto_valido(e["frase"], MAX_FRASE):
            p.append("frase no válida")  # la app enseña el destacado sin frase, pero en el archivo publicado no debe haberla mala
        if e.get("fondo") not in (None, "") and not _foto_valida(e["fondo"]):
            p.append("fondo no válido")  # mismas reglas que la foto: https de manalab.es, .webp/.png/.jpg, sin parámetros
    return p


def _problemas_lista(datos, campo, maximo, extras):
    if campo not in datos:
        return []
    lista = datos[campo]
    if not isinstance(lista, list):
        return ["%s debe ser una lista" % campo]
    p = ["%s: más de %d" % (campo, maximo)] if len(lista) > maximo else []
    for i, e in enumerate(lista):
        p += ["%s[%d]: %s" % (campo, i, m) for m in _problemas_perfil(e, extras)]
    return p


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
    problemas += _problemas_lista(datos, "coaches", MAX_COACHES, ())
    problemas += _problemas_lista(datos, "destacados", MAX_DESTACADOS, EXTRAS_DESTACADO)
    return problemas


def problemas_fotos(datos):
    """Fotos citadas que no existen o pesan más de 20 kB. Solo si existe CARPETA_FOTOS (si no, no se comprueba nada)."""
    if not CARPETA_FOTOS.is_dir():
        return []
    p = []
    for campo in ("coaches", "destacados"):
        for e in datos.get(campo, []) if isinstance(datos.get(campo), list) else []:
            foto = e.get("foto") if isinstance(e, dict) else None
            if foto and _foto_valida(foto):
                ruta = RAIZ / urlparse(foto).path.lstrip("/")
                if not ruta.is_file():
                    p.append("falta la foto %s" % foto)
                elif ruta.stat().st_size > MAX_FOTO_BYTES:
                    p.append("la foto %s pesa más de 20 kB" % foto)
    return p


def ejemplos_del_documento():
    """Los bloques ```json de docs/contenido_remoto.md, como texto."""
    return re.findall(r"```json\n(.*?)\n```", DOCUMENTO.read_text(encoding="utf-8"), re.S)


def _con(**cambios):
    base = {"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "", "interruptores": {"banner_mdn": True}}
    base.update(cambios)
    return base


class ContenidoRemotoTest(unittest.TestCase):
    def test_archivo_real_cumple_el_esquema(self):
        crudo = ARCHIVO.read_bytes()
        self.assertEqual(validar(json.loads(crudo.decode("utf-8")), len(crudo)), [])

    def test_valores_iniciales_acordados(self):
        enlaces = {"enlace_apoyo_metafy": "https://metafy.gg/@manalab",  # ML-307: fijados por el dueño el 18/11
                   "enlace_suscripcion_ia": "https://metafy.gg/@manalab/members?membershipId=6696173a-b185-4a9e-ad09-abce63885f73"}
        destacados = [{"id": "pcpalhares", "nombre": "Professor P. C. Palhares",   # ML-334: primer destacado, decidido por el dueño el 19/11
                       "linea": "Standard · Pioneer · Modern - Competitive Magic · PT/EN",
                       "frase": "Professor, jogador competitivo e mentor. Análise de metagame e estratégias para ajudar você a evoluir no Magic!",
                       "enlace": "https://metafy.gg/@pcpalhares", "foto": "https://manalab.es/img/destacados/pcpalhares.webp",
                       "fondo": "https://manalab.es/img/destacados/pcpalhares-fondo.webp", "guias": "https://metafy.gg/@pcpalhares/guides"},
                      {"id": "tcgacademy", "nombre": "TCG Academy",   # ML-351: segundo destacado, sin «hasta» (para siempre, decisión del dueño)
                       "linea": "All Constructed formats · Limited (Draft & Sealed) · EN/ES",
                       "frase": "A competitive Magic community with on-demand coaching, match reviews, and guides to help you play better and prepare "
                                "for tournaments.",
                       "enlace": "https://metafy.gg/@luissalvatto", "foto": "https://manalab.es/img/destacados/tcgacademy.webp",
                       "fondo": "https://manalab.es/img/destacados/tcgacademy-fondo.webp", "sesiones": "https://metafy.gg/@luissalvatto/sessions"},
                      {"id": "yuyan", "nombre": "Yuya Hosokawa",   # ML-354: tercer destacado, sin «hasta»; «articulos» va en la versión siguiente
                       "linea": "Deck guides, metagame analyses and more · 2+ updates a week",
                       "frase": "Members get free access to all articles! There are tons of articles, and more are added every week!",
                       "enlace": "https://metafy.gg/@yuyan", "foto": "https://manalab.es/img/destacados/yuyan.webp",
                       "fondo": "https://manalab.es/img/destacados/yuyan-fondo.webp", "guias": "https://metafy.gg/@yuyan/guides",
                       "articulos": "https://metafy.gg/@yuyan/posts"}]
        esperado = dict(_con(**enlaces), destacados=destacados)
        self.assertEqual(json.loads(ARCHIVO.read_text(encoding="utf-8")), esperado)
        self.assertEqual(validar(esperado, 100), [])

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

    def test_archivo_real_con_coaches_o_destacados_cumple_las_reglas_y_sus_fotos(self):
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))  # hoy no lleva coaches ni destacados: pasa igual
        self.assertEqual(problemas_fotos(datos), [])

    def test_cada_ejemplo_del_documento_es_json_valido_y_cumple_las_reglas(self):
        ejemplos = ejemplos_del_documento()
        self.assertGreaterEqual(len(ejemplos), 5)
        claves = set()
        for texto in ejemplos:
            datos = json.loads(texto)
            self.assertEqual(validar(datos, len(texto.encode("utf-8"))), [], texto)
            claves |= set(datos)
        self.assertLessEqual({"coaches", "destacados"}, claves, "el documento debe tener un ejemplo de cada uno")

    def test_el_documento_dice_que_la_app_3_0_no_ensena_los_coaches(self):
        """ML-283: solo los destacados (los que pagan) se ven; el documento no puede sugerir que un coach sale en la app."""
        doc = DOCUMENTO.read_text(encoding="utf-8")
        linea_coaches = [l for l in doc.splitlines() if l.startswith("- `coaches`")][0]
        self.assertIn("no los enseña", linea_coaches)
        self.assertIn("no lo hace visible", linea_coaches)
        linea_destacados = [l for l in doc.splitlines() if l.startswith("- `destacados`")][0]
        self.assertIn("única lista que se ve", linea_destacados)
        self.assertNotIn("Poner un coach (", doc)
        self.assertNotIn("la lista de coaches de la pantalla Aprender", doc)

    def test_acepta_coaches_y_destacados_buenos(self):
        coach = {"nombre": "Ana Ejemplo", "linea": "Standard · ES", "enlace": "https://metafy.gg/@ana"}
        con_todo = dict(coach, foto="https://manalab.es/coaches/fotos/ana.webp", academia="https://sub.metafy.gg/a", guias="", sesiones=None)
        self.assertEqual(validar(_con(coaches=[], destacados=[]), 100), [])
        self.assertEqual(validar(_con(coaches=[coach, con_todo] * 50), 100), [])
        self.assertEqual(validar(_con(destacados=[con_todo] * 10), 100), [])

    def test_rechaza_coaches_malos(self):
        coach = {"nombre": "Ana", "linea": "Standard", "enlace": "https://metafy.gg/@ana"}
        malos = [dict(coach, foto="https://evil.com/ana.webp"), dict(coach, foto="https://manalab.es/a.gif"),
                 dict(coach, foto="https://manalab.es/a.webp?x=1"), dict(coach, foto="http://manalab.es/a.webp"),
                 dict(coach, enlace="http://metafy.gg/@ana"), dict(coach, enlace="https://evil.com/metafy.gg"),
                 dict(coach, enlace="https://metafy.gg:8443/x"), dict(coach, enlace="https://metafy.gg/a\"b"),
                 dict(coach, nombre="a" * 61), dict(coach, nombre=""), dict(coach, nombre="Ana\u202eEva"),
                 dict(coach, nombre="Ana\u200bEva"), dict(coach, nombre="Ana\nEva"), dict(coach, linea="a" * 81),
                 "no soy un objeto"]
        for malo in malos:
            self.assertNotEqual(validar(_con(coaches=[malo]), 100), [], malo)
        self.assertNotEqual(validar(_con(coaches=[coach] * 101), 100), [])
        self.assertNotEqual(validar(_con(coaches="x"), 100), [])

    def test_destacados_con_frase_y_fondo(self):
        """ML-324: `frase` (texto de 140 como mucho) y `fondo` (imagen de manalab.es) son opcionales en un destacado y se validan."""
        d = {"nombre": "Marta", "linea": "Standard", "enlace": "https://metafy.gg/@m"}
        buenos = dict(d, frase="Te enseño a jugar contra el meta.", fondo="https://manalab.es/coaches/fondos/marta.webp")
        self.assertEqual(validar(_con(destacados=[buenos, dict(d, frase="", fondo=None), dict(d, frase="f" * MAX_FRASE)]), 100), [])
        for malo in ({"frase": "f" * (MAX_FRASE + 1)}, {"frase": "a\u200bb"}, {"frase": "a\nb"}, {"frase": 5},
                     {"fondo": "https://evil.com/f.webp"}, {"fondo": "http://manalab.es/f.webp"}, {"fondo": "https://manalab.es/f.gif"},
                     {"fondo": "https://manalab.es/f.webp?x=1"}, {"fondo": "https://manalab.es:8443/f.webp"}):
            self.assertNotEqual(validar(_con(destacados=[dict(d, **malo)]), 100), [], malo)
        # en un coach (que la app 3.0 no enseña) no se comprueban: no son campos suyos
        self.assertEqual(validar(_con(coaches=[dict(d, frase="f" * 500)]), 100), [])

    def test_rechaza_destacados_malos(self):
        d = {"nombre": "Marta", "linea": "Standard", "enlace": "https://metafy.gg/@m"}
        for campo in EXTRAS_DESTACADO:
            self.assertNotEqual(validar(_con(destacados=[dict(d, **{campo: "https://evil.com/x"})]), 100), [], campo)
            self.assertNotEqual(validar(_con(destacados=[dict(d, **{campo: "http://metafy.gg/x"})]), 100), [], campo)
        self.assertNotEqual(validar(_con(destacados=[d] * 11), 100), [])
        self.assertNotEqual(validar(_con(destacados={}), 100), [])

    def test_mutaciones_de_un_archivo_con_coaches_fallan(self):
        base = {"nombre": "Ana", "linea": "Standard", "enlace": "https://metafy.gg/@ana", "foto": "https://manalab.es/coaches/fotos/a.webp"}
        self.assertEqual(validar(_con(coaches=[base]), 100), [])
        for cambio in ({"foto": "https://otro.com/a.webp"}, {"enlace": "http://metafy.gg/x"}, {"nombre": "n" * 61}):
            self.assertNotEqual(validar(_con(coaches=[dict(base, **cambio)]), 100), [], cambio)
        self.assertNotEqual(validar(_con(coaches=[base] * 101), 100), [])

    def test_un_ejemplo_roto_del_documento_se_detecta(self):
        roto = [t for t in ejemplos_del_documento() if "destacados" in t][0].replace("https://manalab.es", "https://otro.com")
        mal = [t for t in (roto, roto.replace("https://metafy.gg", "http://metafy.gg"), roto[:-1])]
        for texto in mal:
            try:
                problemas = validar(json.loads(texto), 100)
            except ValueError:
                continue  # JSON roto
            self.assertNotEqual(problemas, [], texto)

    def test_las_fotos_citadas_existen_y_pesan_poco(self):
        # una foto que no existe o pesa de más debe dar problema (se simula con una carpeta temporal)
        import tempfile
        global CARPETA_FOTOS, RAIZ
        guardado = (CARPETA_FOTOS, RAIZ)
        with tempfile.TemporaryDirectory() as t:
            RAIZ, CARPETA_FOTOS = Path(t), Path(t) / "coaches" / "fotos"
            CARPETA_FOTOS.mkdir(parents=True)
            try:
                datos = _con(coaches=[{"nombre": "A", "linea": "B", "enlace": "https://metafy.gg/@a",
                                       "foto": "https://manalab.es/coaches/fotos/a.webp"}])
                self.assertNotEqual(problemas_fotos(datos), [], "falta la foto")
                (CARPETA_FOTOS / "a.webp").write_bytes(b"x" * 100)
                self.assertEqual(problemas_fotos(datos), [])
                (CARPETA_FOTOS / "a.webp").write_bytes(b"x" * (MAX_FOTO_BYTES + 1))
                self.assertNotEqual(problemas_fotos(datos), [], "pesa más de 20 kB")
            finally:
                CARPETA_FOTOS, RAIZ = guardado


if __name__ == "__main__":
    unittest.main()
