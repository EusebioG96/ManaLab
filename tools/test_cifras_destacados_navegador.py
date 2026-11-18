#!/usr/bin/env python3
"""ML-333: las cifras de los creadores destacados de la página «Learn» (learn/cifras.js) en Chromium con Playwright y un servidor falso:
el cuerpo exacto del POST, 204 borra, 429 conserva y frena, 400 descarta, «visto» (1 s seguido, una vez por minuto, nunca con la pestaña oculta),
la barra fina no suma en metafy, sin id no se cuenta, «hasta» oculta el destacado y nunca sale nada que no sea del contrato. Y, sin navegador,
la validación de id y hasta de tools/guias_web.py y su efecto en el HTML generado. Se salta si Playwright o Chromium no están.

Uso:  python3 -m pytest tools/test_cifras_destacados_navegador.py
"""
import json
import re
import sys
import unittest
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_learn  # noqa: E402
import guias_web  # noqa: E402
from test_pagina_learn_navegador import PNG, SERVIDOR_IA, Servidor, sitio  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # silencio: sin Playwright la prueba se salta
    sync_playwright = None

CIFRAS = "https://registro-ia.eusebiog76.workers.dev/cifras-destacados"
CLAVE = "manalab_cifras_destacados_v1"
METAFY = "https://metafy.gg/@"
DANA = {"id": "dana-voss", "nombre": "Dana Voss", "linea": "Standard · ES/EN", "enlace": METAFY + "dana", "academia": METAFY + "dana/academy",
        "guias": METAFY + "dana/guides", "sesiones": METAFY + "dana/sessions"}
IKER = {"id": "iker", "nombre": "Iker Lasa", "linea": "Draft · ES", "enlace": METAFY + "iker"}
CONTADORES = {"visto", "metafy", "academia", "guias", "sesiones", "barra"}
ENVOLTURA = """(function(){var f=window.fetch;window.__cifras=[];window.fetch=function(u,o){
  if(String(u).indexOf('/cifras-destacados')>=0)window.__cifras.push({keepalive:o.keepalive,credentials:o.credentials,referrerPolicy:o.referrerPolicy,method:o.method,
  tipo:o.headers['Content-Type'],url:String(u)});return f.apply(this,arguments)}})()"""
OCULTAR = ("Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'hidden'});"
           "Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
NACER_OCULTA = OCULTAR.rsplit(";", 1)[0]   # la página nace «oculta» (sin el evento): la cuenta de «visto» no empieza antes de parar el reloj
MOSTRAR = ("Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'visible'});"
           "Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))")


def dia_utc(delta: int = 0) -> str:
    return (datetime.now(UTC) + timedelta(days=delta)).strftime("%Y-%m-%d")


def sin_contrato(texto: str) -> list:
    """Lo que un cuerpo tiene de más o de menos respecto al contrato v1 de POST /cifras-destacados (lista vacía = cumple)."""
    fallos = []
    try:
        cuerpo = json.loads(texto)
    except ValueError:
        return ["no es JSON"]
    if len(texto.encode()) > 4096:
        fallos.append("más de 4 KB")
    if set(cuerpo) != {"v", "superficie", "dias"} or cuerpo.get("v") != 1 or cuerpo.get("superficie") != "web":
        fallos.append("cabecera: " + str(sorted(cuerpo)))
    dias = cuerpo.get("dias", {})
    hoy = datetime.now(UTC).date()
    for dia, creadores in dias.items():
        edad = (hoy - datetime.strptime(dia, "%Y-%m-%d").date()).days if re.fullmatch(r"\d{4}-\d{2}-\d{2}", dia) else -9
        if not 0 <= edad <= 2:
            fallos.append("día fuera de rango " + dia)
        if not creadores or len(creadores) > 10:
            fallos.append("creadores por día")
        for ident, cifras in creadores.items():
            if not re.fullmatch(r"[a-z0-9-]{1,40}", ident) or not cifras or not set(cifras) <= CONTADORES:
                fallos.append("creador " + ident)
            for n in cifras.values():
                if not (isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= 500):
                    fallos.append(f"número {n!r}")
    return fallos


@unittest.skipIf(sync_playwright is None, "hace falta playwright")
class CifrasNavegador(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        try:
            cls.nav = cls.pw.chromium.launch()
        except Exception as error:  # noqa: BLE001  silencio: sin Chromium instalado la prueba se salta
            cls.pw.stop()
            raise unittest.SkipTest(f"sin Chromium: {error}")
        manana = (date.today() + timedelta(days=1)).isoformat()
        cls.dos = Servidor(sitio([DANA, IKER]))
        cls.uno = Servidor(sitio([DANA]))
        cls.sin_id = Servidor(sitio([{k: v for k, v in DANA.items() if k != "id"}]))
        cls.caduca_uno = Servidor(sitio([dict(DANA, hasta=manana), IKER]))
        cls.caduca_todos = Servidor(sitio([dict(DANA, hasta=manana)]))

    @classmethod
    def tearDownClass(cls):
        for s in (cls.dos, cls.uno, cls.sin_id, cls.caduca_uno, cls.caduca_todos):
            s.cerrar()
        cls.nav.close()
        cls.pw.stop()

    def abrir(self, servidor, estado=204, reloj=None, ancho=1366):
        """Abre es/aprender/. `estado`: lo que contesta el servidor falso (número) o «caida» para cortar la conexión; se puede cambiar en `p.estado`.
        `reloj`: si no es None, se instala un reloj falso y se detiene al cargar (0 = parte de la hora real; un datetime, de esa hora local), y solo
        avanza con p.clock.run_for. `p.cifras`: los POST recibidos como (cabeceras, cuerpo)."""
        ctx = self.nav.new_context(viewport={"width": ancho, "height": 800}, reduced_motion="reduce")   # sin rotación sola: nada cambia de creador a mitad de prueba
        self.addCleanup(ctx.close)
        p = ctx.new_page()
        p.errores, p.cifras, p.estado = [], [], estado
        p.on("pageerror", lambda e: p.errores.append(str(e)))
        p.add_init_script(ENVOLTURA)

        def ruta(r):
            url, metodo = r.request.url, r.request.method
            if url.startswith(servidor.url):
                return r.continue_()
            if url == CIFRAS:
                cors = {"access-control-allow-origin": "*", "access-control-allow-headers": "content-type", "access-control-allow-methods": "POST"}
                if metodo == "OPTIONS":
                    return r.fulfill(status=204, headers=cors)
                p.cifras.append((r.request.headers, r.request.post_data))
                return r.abort() if p.estado == "caida" else r.fulfill(status=p.estado, headers=cors, body="")
            if url == SERVIDOR_IA:
                return r.fulfill(status=503, body="no")
            if url.startswith("https://cdn.metafy.gg/"):
                return r.fulfill(body=PNG, content_type="image/png")
            return r.abort()
        p.route("**/*", ruta)
        if reloj is not None:
            p.add_init_script(NACER_OCULTA)
            p.clock.install(time=reloj) if reloj else p.clock.install()
        p.goto(f"{servidor.url}/es/aprender/", wait_until="load")
        p.wait_for_function("document.documentElement.classList.contains('learn-js') || document.documentElement.classList.contains('learn-sin-lista')")
        if reloj is not None:
            p.wait_for_timeout(300)   # el IntersectionObserver da su primera lectura (con la página aún «oculta»)
            p.clock.pause_at(datetime.fromtimestamp(p.evaluate("Date.now()") / 1000 + 0.05))
            p.evaluate(MOSTRAR)
        return p

    def enviar(self, p):
        """Oculta la página (lo que dispara el envío) y espera a que termine; la vuelve a mostrar."""
        p.evaluate(OCULTAR)
        p.wait_for_timeout(250)
        p.evaluate(MOSTRAR)

    def pendiente(self, p):
        texto = p.evaluate(f"localStorage.getItem('{CLAVE}')")
        return json.loads(texto) if texto else {}

    def cuerpos(self, p):
        return [json.loads(c) for _, c in p.cifras]

    def vistas(self, p) -> int:
        """Las vistas contadas hasta ahora: las ya enviadas (cada ocultar envía) más las pendientes."""
        total = sum(c.get("visto", 0) for cuerpo in self.cuerpos(p) for dia in cuerpo["dias"].values() for c in dia.values())
        return total + sum(c.get("visto", 0) for dia in self.pendiente(p).values() for c in dia.values())

    def clic(self, p, selector):
        p.locator(selector).first.click()
        p.wait_for_timeout(50)

    # ------------------------------------------------------------------ el contrato
    def test_cuerpo_exacto_y_forma_de_la_peticion(self):
        p = self.abrir(self.dos)
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.clic(p, "#destacado .d2c.on .d2cas[data-cas='academia']")
        self.clic(p, "#destacado .d2c.on .d2cas[data-cas='guias']")
        self.clic(p, "#destacado .d2c.on .d2cas[data-cas='sesiones']")
        self.enviar(p)
        self.assertEqual(len(p.cifras), 1)
        cabeceras, texto = p.cifras[0]
        self.assertEqual(json.loads(texto), {"v": 1, "superficie": "web", "dias": {dia_utc(): {"dana-voss": {"metafy": 2, "academia": 1, "guias": 1, "sesiones": 1}}}})
        self.assertNotIn("version", texto)
        self.assertEqual(sin_contrato(texto), [])
        self.assertEqual(cabeceras["content-type"], "application/json")
        self.assertNotIn("referer", cabeceras)
        self.assertNotIn("cookie", cabeceras)
        opciones = p.evaluate("window.__cifras")
        self.assertEqual(opciones, [{"keepalive": True, "credentials": "omit", "referrerPolicy": "no-referrer", "method": "POST", "tipo": "application/json", "url": CIFRAS}])
        self.assertEqual(p.errores, [])

    def test_sin_nada_que_contar_no_se_envia_nada(self):
        p = self.abrir(self.dos)
        self.enviar(p)
        self.assertEqual(p.cifras, [])

    def test_204_borra_lo_enviado_y_conserva_lo_que_llega_despues(self):
        p = self.abrir(self.dos, estado=204)
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.enviar(p)
        self.assertEqual(self.pendiente(p), {})
        self.clic(p, "#destacado .d2c.on .d2cas[data-cas='guias']")
        self.assertEqual(self.pendiente(p), {dia_utc(): {"dana-voss": {"guias": 1}}})
        self.enviar(p)
        self.assertEqual([json.loads(c)["dias"][dia_utc()]["dana-voss"] for _, c in p.cifras], [{"metafy": 1}, {"guias": 1}])

    def test_429_conserva_y_frena_el_siguiente_envio_una_hora(self):
        p = self.abrir(self.dos, estado=429)
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.enviar(p)
        self.assertEqual(self.pendiente(p), {dia_utc(): {"dana-voss": {"metafy": 1}}})
        self.enviar(p)
        self.assertEqual(len(p.cifras), 1, "tras un 429 no se insiste hasta pasada una hora")

    def test_400_descarta_lo_enviado(self):
        p = self.abrir(self.dos, estado=400)
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.enviar(p)
        self.assertEqual(len(p.cifras), 1)
        self.assertEqual(self.pendiente(p), {})

    def test_403_de_local_y_red_caida_conservan_sin_romper_nada(self):
        for estado in (403, 500, "caida"):
            with self.subTest(estado=estado):
                p = self.abrir(self.dos, estado=estado)
                self.clic(p, "#destacado .d2c.on .d2cta")
                self.enviar(p)
                self.assertEqual(len(p.cifras), 1)
                self.assertEqual(self.pendiente(p), {dia_utc(): {"dana-voss": {"metafy": 1}}})
                p.estado = 204   # vuelve la red: el siguiente envío lo manda y lo borra
                self.enviar(p)
                self.assertEqual(len(p.cifras), 2)
                self.assertEqual(self.pendiente(p), {})
                self.assertEqual(p.errores, [])

    def test_sin_localstorage_se_cuenta_en_memoria(self):
        p = self.abrir(self.dos)
        p.evaluate("Object.defineProperty(window,'localStorage',{configurable:true,get:()=>{throw new DOMException('no','SecurityError')}})")
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.enviar(p)
        self.assertEqual(self.cuerpos(p)[0]["dias"][dia_utc()], {"dana-voss": {"metafy": 1}})
        self.assertEqual(p.errores, [])

    def test_cada_hora_con_la_pagina_abierta(self):
        p = self.abrir(self.dos, reloj=0)
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.assertEqual(p.cifras, [])
        p.clock.run_for(3600000 + 1000)
        p.wait_for_timeout(250)
        self.assertEqual(len(p.cifras), 1)
        self.assertEqual(self.cuerpos(p)[0]["dias"][dia_utc()]["dana-voss"]["metafy"], 1)

    def test_pagehide_tambien_envia(self):
        p = self.abrir(self.dos)
        self.clic(p, "#destacado .d2c.on .d2cta")
        p.evaluate("window.dispatchEvent(new Event('pagehide'))")
        p.wait_for_timeout(250)
        self.assertEqual(len(p.cifras), 1)

    # ------------------------------------------------------------------ qué se cuenta
    def test_la_barra_fina_cuenta_barra_y_no_suma_en_metafy(self):
        p = self.abrir(self.dos)
        p.evaluate("window.scrollTo(0, 2400)")
        p.wait_for_function("document.getElementById('d2barra').classList.contains('visible')")
        p.route("**/metafy.gg/**", lambda r: r.abort())
        self.clic(p, "#d2barra .d2cta")
        self.enviar(p)
        self.assertEqual(self.cuerpos(p)[0]["dias"][dia_utc()], {"dana-voss": {"barra": 1}})

    def test_el_clic_del_banner_no_suma_en_barra(self):
        p = self.abrir(self.dos)
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.enviar(p)
        self.assertEqual(self.cuerpos(p)[0]["dias"][dia_utc()], {"dana-voss": {"metafy": 1}})

    def test_un_enlace_cualquiera_de_la_pagina_no_cuenta(self):
        p = self.abrir(self.dos)
        self.clic(p, "#guias a.guia")
        self.clic(p, "header a")
        self.enviar(p)
        self.assertEqual(p.cifras, [])

    def test_con_dos_creadores_cada_clic_va_al_suyo(self):
        p = self.abrir(self.dos)
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.clic(p, "#destacado button[data-d2='1']")
        p.wait_for_function("document.querySelector('#destacado .d2c.on').dataset.id === 'iker'")
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.enviar(p)
        self.assertEqual(self.cuerpos(p)[0]["dias"][dia_utc()], {"dana-voss": {"metafy": 1}, "iker": {"metafy": 1}})

    def test_sin_id_no_se_cuenta_nada(self):
        p = self.abrir(self.sin_id)
        self.assertEqual(p.locator("#destacado .d2c").count(), 1)
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.clic(p, "#destacado .d2c.on .d2cas[data-cas='guias']")
        p.evaluate("window.scrollTo(0, 2400)")
        p.wait_for_function("document.getElementById('d2barra').classList.contains('visible')")
        self.clic(p, "#d2barra .d2cta")
        p.wait_for_timeout(1300)
        self.enviar(p)
        self.assertEqual(p.cifras, [])
        self.assertEqual(self.pendiente(p), {})

    # ------------------------------------------------------------------ visto
    def test_visto_exige_un_segundo_seguido(self):
        p = self.abrir(self.uno, reloj=0)
        p.clock.run_for(900)
        self.assertEqual(self.vistas(p), 0, "con menos de 1 s no hay vista")
        p.clock.run_for(300)
        self.assertEqual(self.vistas(p), 1)
        self.enviar(p)
        self.assertEqual(self.cuerpos(p)[0]["dias"][dia_utc()], {"dana-voss": {"visto": 1}})

    def test_visto_se_reinicia_si_la_pagina_se_oculta_antes_del_segundo(self):
        p = self.abrir(self.uno, reloj=0)
        p.clock.run_for(600)
        p.evaluate(OCULTAR)
        p.clock.run_for(600)   # oculta: no cuenta aunque pase el segundo
        p.evaluate(MOSTRAR)
        p.clock.run_for(600)
        p.evaluate(OCULTAR)
        p.wait_for_timeout(250)
        self.assertEqual(p.cifras, [])
        p.evaluate(MOSTRAR)
        p.clock.run_for(1200)
        self.enviar(p)
        self.assertEqual(self.cuerpos(p)[0]["dias"][dia_utc()], {"dana-voss": {"visto": 1}})

    def test_visto_como_mucho_una_vez_por_minuto_y_creador(self):
        p = self.abrir(self.uno, reloj=0)
        p.clock.run_for(1200)
        for _ in range(3):   # varias rachas dentro del mismo minuto: una sola vista
            p.evaluate(OCULTAR)
            p.clock.run_for(100)
            p.evaluate(MOSTRAR)
            p.clock.run_for(1300)
        self.assertEqual(self.vistas(p), 1)
        p.evaluate(OCULTAR)
        p.clock.run_for(61000)
        p.evaluate(MOSTRAR)
        p.clock.run_for(1300)
        self.assertEqual(self.vistas(p), 2)

    def test_visto_no_cuenta_una_tarjeta_que_no_esta_en_pantalla(self):
        p = self.abrir(self.uno, reloj=0)
        p.evaluate("window.scrollTo(0, 3000)")
        p.wait_for_function("document.getElementById('d2barra').classList.contains('visible')")
        p.clock.run_for(1500)
        self.assertEqual(self.pendiente(p), {})

    # ------------------------------------------------------------------ hasta
    def test_hasta_quita_el_destacado_caducado_en_el_navegador_y_deja_los_demas(self):
        pasado_manana = datetime.combine(date.today() + timedelta(days=2), time(12, 0))
        p = self.abrir(self.caduca_uno, reloj=pasado_manana)
        self.assertEqual(p.locator("#destacado .d2c").count(), 1)
        self.assertEqual(p.locator("#destacado .d2c").get_attribute("data-id"), "iker")
        self.assertIn("on", p.locator("#destacado .d2c").get_attribute("class").split())
        self.assertEqual(p.locator("#destacado .d2pag").count(), 0, "con uno solo no hay flechas")
        self.assertEqual(p.locator("#destacado .d2pun i").count(), 0)
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.enviar(p)
        self.assertEqual(list(self.cuerpos(p)[0]["dias"].values())[0], {"iker": {"metafy": 1}})

    def test_hasta_hoy_mismo_ya_no_se_pinta_y_antes_si(self):
        p = self.abrir(self.caduca_uno)   # hoy < hasta (mañana)
        self.assertEqual(p.locator("#destacado .d2c").count(), 2)
        dia_hasta = datetime.combine(date.today() + timedelta(days=1), time(0, 30))
        p = self.abrir(self.caduca_uno, reloj=dia_hasta)   # el día «hasta», 00:30 hora local: ya no
        self.assertEqual(p.locator("#destacado .d2c").count(), 1)

    def test_si_caducan_todos_no_queda_banner_ni_barra(self):
        pasado_manana = datetime.combine(date.today() + timedelta(days=2), time(12, 0))
        p = self.abrir(self.caduca_todos, reloj=pasado_manana)
        self.assertEqual(p.locator("#destacado").count(), 0)
        self.assertEqual(p.locator("#d2barra").count(), 0)
        self.assertEqual(p.errores, [])
        self.enviar(p)
        self.assertEqual(p.cifras, [])

    # ------------------------------------------------------------------ nunca nada fuera del contrato
    def test_lo_guardado_roto_o_viejo_se_limpia_antes_de_enviar(self):
        p = self.abrir(self.dos)
        sucio = {dia_utc(): {"dana-voss": {"metafy": 9999, "visto": 0, "barra": -1, "otro": 5, "academia": 1.5, "guias": "3", "sesiones": 2},
                             "Mayusculas": {"metafy": 1}, "x" * 41: {"metafy": 1}, "iker": {"visto": 3}, "vacio": {}},
                 dia_utc(-3): {"dana-voss": {"metafy": 4}}, dia_utc(-2): {"iker": {"barra": 2}}, dia_utc(1): {"iker": {"metafy": 1}},
                 "ayer": {"iker": {"metafy": 1}}, "2026-13-45": {"iker": {"metafy": 1}}}
        p.evaluate("([k, v]) => localStorage.setItem(k, JSON.stringify(v))", [CLAVE, sucio])
        self.enviar(p)
        self.assertEqual(len(p.cifras), 1)
        cuerpo = self.cuerpos(p)[0]
        self.assertEqual(sin_contrato(p.cifras[0][1]), [])
        self.assertEqual(cuerpo["dias"], {dia_utc(): {"dana-voss": {"metafy": 500, "sesiones": 2}, "iker": {"visto": 3}}, dia_utc(-2): {"iker": {"barra": 2}}})
        self.assertEqual(self.pendiente(p), {})

    def test_localstorage_con_texto_roto_no_rompe_la_pagina(self):
        p = self.abrir(self.dos)
        p.evaluate(f"localStorage.setItem('{CLAVE}', '{{no es json')")
        self.clic(p, "#destacado .d2c.on .d2cta")
        self.enviar(p)
        self.assertEqual(self.cuerpos(p)[0]["dias"][dia_utc()], {"dana-voss": {"metafy": 1}})
        self.assertEqual(p.errores, [])

    def test_mas_de_diez_creadores_por_dia_se_reparten_en_envios(self):
        p = self.abrir(self.dos)
        dias = {dia_utc(-d): {f"creador-{i:02d}": {c: 500 for c in CONTADORES} for i in range(12)} for d in (0, 1, 2)}
        p.evaluate("([k, v]) => localStorage.setItem(k, JSON.stringify(v))", [CLAVE, dias])
        self.enviar(p)
        self.assertEqual(len(p.cifras), 1)
        self.assertEqual(sin_contrato(p.cifras[0][1]), [])
        enviado = self.cuerpos(p)[0]["dias"]
        self.assertTrue(all(len(v) == 10 for v in enviado.values()))
        resto = self.pendiente(p)
        self.assertEqual(sum(len(v) for v in resto.values()) + sum(len(v) for v in enviado.values()), 36, "lo que no cupo se queda pendiente")


class DestacadosSinNavegador(unittest.TestCase):
    DEST = {"nombre": "Dana", "linea": "Standard", "enlace": "https://metafy.gg/@dana"}

    def test_id_valido_o_vacio_y_hasta_valido_o_el_destacado_se_descarta(self):
        validos = guias_web.validar_destacados([dict(self.DEST, id="dana-voss", hasta="2026-12-31"), dict(self.DEST, id="Dana"), dict(self.DEST, id="x" * 41),
                                                dict(self.DEST, id=""), dict(self.DEST, id=5), self.DEST,
                                                dict(self.DEST, hasta="2026-02-30"), dict(self.DEST, hasta="31/12/2026"), dict(self.DEST, hasta=20261231)])
        self.assertEqual([(d["id"], d["hasta"]) for d in validos], [("dana-voss", "2026-12-31"), ("", ""), ("", ""), ("", ""), ("", ""), ("", "")])

    def test_el_html_lleva_data_id_data_hasta_y_data_cas_y_hasta_filtra_por_la_fecha_local(self):
        t = construir_learn.TEXTOS["es"]
        dest = guias_web.validar_destacados([dict(self.DEST, id="dana", hasta="2026-12-01", academia="https://metafy.gg/@dana/a", guias="https://metafy.gg/@dana/g"),
                                             dict(self.DEST, nombre="Iker", id="iker")])
        html = construir_learn.html_destacado(construir_learn.vigentes(dest, date(2026, 11, 30)), t)
        self.assertIn('data-id="dana" data-hasta="2026-12-01"', html)
        self.assertIn('data-cas="academia"', html)
        self.assertIn('data-cas="guias"', html)
        self.assertEqual(html.count("<article"), 2)
        quedan = construir_learn.vigentes(dest, date(2026, 12, 1))   # desde el día «hasta», fuera
        self.assertEqual([d["id"] for d in quedan], ["iker"])
        self.assertNotIn("Dana", construir_learn.html_destacado(quedan, t) + construir_learn.html_barra(quedan, t))
        self.assertEqual(construir_learn.html_destacado(construir_learn.vigentes(dest[:1], date(2027, 1, 1)), t), "")


if __name__ == "__main__":
    unittest.main()
