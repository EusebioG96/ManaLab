#!/usr/bin/env python3
"""Portada y novedades de la 3.0 (ML-281, RED-06): aviso de versión (W3), siete líneas de novedades (W4), pregunta frecuente nueva
(W2), cita de Luis Salvatto apagada (W1) y hueco del vídeo del lanzamiento. Comprueba sobre los archivos generados (sin red).

Uso:  python3 tools/test_portada_v3.py
"""
import html
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tools"))
import construir_web  # noqa: E402

PORTADAS = {"en": "index.html", "es": "es/index.html", "pt": "pt/index.html", "ja": "ja/index.html"}
NOVEDADES = {"en": "novedades/index.html", "es": "es/novedades/index.html"}
# (texto del aviso, texto del enlace, destino del enlace). pt y ja no tienen novedades en su idioma: van a las inglesas.
AVISOS = {
    "en": ("ManaLab 3.0 is out: a new look for your matches.", "See what's new", "/novedades/"),
    "es": ("Ya está ManaLab 3.0: tus partidas con un aspecto nuevo.", "Mira las novedades", "/es/novedades/"),
    "pt": ("Saiu o ManaLab 3.0: suas partidas de cara nova.", "Veja as novidades", "/novedades/"),
    "ja": ("ManaLab 3.0を公開しました。デザインを一新。", "新機能を見る", "/novedades/"),
}
LINEAS = {
    "en": ["A new look: your matches on a Magic table", "Replays on a 3D table, with the real cards",
           "A new overlay in three sizes, with a colorblind mode", "Logging starts on its own", "A deck box for every deck",
           "A summary when you finish your session", "A Learn section with Metafy guides"],
    "es": ["Un aspecto nuevo: tus partidas sobre una mesa de Magic", "Repeticiones en una mesa en 3D, con las cartas reales",
           "Un overlay nuevo en tres tamaños, con modo para daltónicos", "El registro arranca solo", "Una caja para cada mazo",
           "Un resumen al terminar la sesión", "Una sección Aprender con guías de Metafy"],
}
FAQ = {
    "en": ("How is ManaLab free?", "The tracker is free and always will be. The only paid part is the optional AI analysis of your losses, "
           "a membership on Metafy. In the Learn section you'll also find guides from Metafy."),
    "es": ("¿Cómo se mantiene gratis ManaLab?", "El tracker es gratis y lo seguirá siendo. Lo único de pago es el análisis opcional de tus "
           "derrotas con IA, una membresía en Metafy. En la sección Aprender verás además guías de Metafy."),
    "pt": ("Como o ManaLab é gratuito?", "O tracker é gratuito e vai continuar sendo. O único recurso pago é a análise opcional das suas "
           "derrotas com IA, uma assinatura na Metafy. Na seção Aprender você também encontra guias da Metafy."),
    "ja": ("ManaLabはなぜ無料なのですか？", "トラッカーは無料で、今後も無料です。有料なのは、任意で使えるAIによる敗因分析（Metafyのメンバーシップ）だけです。"
           "アプリ内ではMetafyのガイドも読めます。"),
}
CITAS = {"en": ["“I already started to use ManaLab and I really like it.”", "Luis Salvatto, Pro Tour champion and 2017–18 Player of the Year"],
         "es": ["«Ya he empezado a usar ManaLab y me gusta mucho.»", "Luis Salvatto, campeón de Pro Tour y Jugador del Año 2017-18."]}


def leer(relativa: str, raiz: Path = RAIZ) -> str:
    return (raiz / relativa).read_text(encoding="utf-8")


def texto_plano(fragmento: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def construir_temporal(raiz_temporal: Path, con_video: bool) -> Path:
    """Copia lo mínimo para generar la web en una carpeta temporal (con o sin los archivos del vídeo del lanzamiento) y la genera."""
    shutil.copytree(RAIZ / "plantillas", raiz_temporal / "plantillas")
    for nombre in ("version.json", "contenido.json"):
        shutil.copy(RAIZ / nombre, raiz_temporal / nombre)
    if con_video:
        (raiz_temporal / "video").mkdir()
        (raiz_temporal / construir_web.VIDEO_LANZAMIENTO).write_bytes(b"x")
        (raiz_temporal / construir_web.POSTER_LANZAMIENTO).write_bytes(b"x")
    salida = raiz_temporal / "salida"
    construir_web.construir(raiz_temporal, salida)
    return salida


class TestAvisoDeVersion(unittest.TestCase):
    def test_las_cuatro_portadas_tienen_el_aviso_con_su_texto_y_enlace(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                pagina = leer(ruta)
                aviso = pagina[pagina.index('class="aviso-version"'):pagina.index("<header")]
                frase, enlace, destino = AVISOS[idioma]
                self.assertEqual(texto_plano(re.search(r"<b>(.*?)</b>", aviso).group(1)), frase)
                a = re.search(r'<a href="([^"]*)">(.*?)</a>', aviso)
                self.assertEqual(a.group(1), destino)
                self.assertEqual(texto_plano(a.group(2)).rstrip(" →"), enlace)

    def test_el_enlace_del_aviso_lleva_a_una_pagina_que_existe(self):
        for idioma, (_, _, destino) in AVISOS.items():
            with self.subTest(idioma=idioma):
                self.assertTrue((RAIZ / destino.strip("/") / "index.html").is_file(), destino)

    def test_ya_no_dice_2_3(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                pagina = leer(ruta)
                self.assertNotIn("ManaLab 2.3 ", pagina[pagina.index('class="aviso-version"'):pagina.index("<header")])


class TestNovedades(unittest.TestCase):
    def test_las_siete_lineas_en_orden_y_arriba_de_todo(self):
        for idioma, ruta in NOVEDADES.items():
            with self.subTest(idioma=idioma):
                pagina = leer(ruta)
                inicio = pagina.index('id="novedades-3-0"')
                self.assertLess(inicio, pagina.index('id="novedades"'))
                self.assertLess(pagina.index("<h1>"), inicio)
                seccion = pagina[inicio:pagina.index("</section>", inicio)]
                self.assertEqual([texto_plano(h) for h in re.findall(r"<h3>(.*?)</h3>", seccion)], LINEAS[idioma])


class TestPreguntaNueva(unittest.TestCase):
    @staticmethod
    def en_html(pagina: str, pregunta: str) -> list:
        return [texto_plano(a) for q, a in re.findall(r"<details[^>]*><summary>(.*?)</summary>(.*?)</details>", pagina, re.S)
                if texto_plano(q) == pregunta]

    @staticmethod
    def en_json(pagina: str, pregunta: str) -> list:
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', pagina, re.S).group(1))
        return [q["acceptedAnswer"]["text"] for n in ld["@graph"] if n["@type"] == "FAQPage" for q in n["mainEntity"] if q["name"] == pregunta]

    def test_esta_en_el_html_y_en_el_json_ld_de_las_cuatro_portadas_con_el_texto_aprobado(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                pagina = leer(ruta)
                pregunta, respuesta = FAQ[idioma]
                self.assertEqual(self.en_html(pagina, pregunta), [respuesta])
                self.assertEqual(self.en_json(pagina, pregunta), [respuesta])


FRASE_DATOS = {
    "en": "The Learn section asks a ManaLab server for the list of guides and loads covers from Metafy and photos from manalab.es, "
          "sending nothing of yours except the ManaLab version; the Metafy banner loads Metafy's ad script and turns off in Settings.",
    "es": "Aprender pide la lista de guías a un servidor de ManaLab y carga portadas de Metafy y fotos de manalab.es, sin enviar nada "
          "tuyo salvo la versión de ManaLab; el banner de Metafy carga el script de anuncios de Metafy y se apaga en Ajustes.",
    "pt": "A seção Aprender pede a lista de guias a um servidor do ManaLab e carrega capas da Metafy e fotos do manalab.es, sem enviar "
          "nada seu além da versão do ManaLab; o banner da Metafy carrega o script de anúncios da Metafy e se desliga em Configurações.",
    "ja": "「学ぶ」画面は、ガイド一覧をManaLabのサーバーに問い合わせ、Metafyからガイドの表紙を、manalab.esから写真を読み込みますが、"
          "ManaLabのバージョン以外は何も送信しません。Metafyのバナーは、Metafyの広告スクリプトを読み込み、設定でオフにできます。",
}
PREGUNTA_DATOS = {"en": "What data does it send?", "es": "¿Qué datos envía?", "pt": "Que dados ele envia?", "ja": "どんなデータを送信しますか？"}


class TestPreguntaDeDatos(unittest.TestCase):
    """ML-283: la respuesta de «¿qué datos envía?» nombra Aprender y el script de anuncios de Metafy, en el HTML y en el JSON-LD."""

    @staticmethod
    def respuestas(pagina, idioma):
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', pagina, re.S).group(1))
        en_json = [q["acceptedAnswer"]["text"] for n in ld["@graph"] if n["@type"] == "FAQPage" for q in n["mainEntity"]
                   if q["name"] == PREGUNTA_DATOS[idioma]]
        m = re.search(r"<summary>%s</summary>\s*<p>(.*?)</p>" % re.escape(PREGUNTA_DATOS[idioma]), pagina, re.S)
        return (html.unescape(re.sub(r"<[^>]+>", "", m.group(1))) if m else None), en_json

    def test_la_frase_esta_en_el_html_y_en_el_json_ld_de_cada_idioma(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                en_html, en_json = self.respuestas(leer(ruta), idioma)
                self.assertEqual(len(en_json), 1)
                self.assertIn(FRASE_DATOS[idioma], en_html)
                self.assertIn(FRASE_DATOS[idioma], en_json[0])
                self.assertEqual(en_html, en_json[0])


class TestCitaDeSalvatto(unittest.TestCase):
    def test_apagada_no_hay_rastro_en_ningun_html(self):
        self.assertFalse(construir_web.MOSTRAR_CITA_SALVATTO, "el interruptor debe estar apagado hasta que Eusebio lo decida")
        for ruta in sorted(RAIZ.rglob("*.html")):
            if ".git" in ruta.parts or "plantillas" in ruta.parts:
                continue
            with self.subTest(ruta=ruta.relative_to(RAIZ).as_posix()):
                self.assertNotIn("salvatto", ruta.read_text(encoding="utf-8").lower())

    def test_encendida_sale_en_en_y_es_y_solo_ahi(self):
        with mock.patch.object(construir_web, "MOSTRAR_CITA_SALVATTO", True), tempfile.TemporaryDirectory() as tmp:
            salida = construir_temporal(Path(tmp), con_video=False)
            for idioma, ruta in PORTADAS.items():
                pagina = leer(ruta, salida)
                with self.subTest(idioma=idioma):
                    if idioma in CITAS:
                        hero = pagina[pagina.index('<section class="portada"'):pagina.index("</section>")]
                        for frase in CITAS[idioma]:
                            self.assertIn(frase, texto_plano(hero))
                        self.assertLess(hero.index("hero-cta"), hero.index("Salvatto"), "va junto al botón de descarga")
                        self.assertNotIn("<a href", hero[hero.index("<figure"):hero.index("</figure>")], "sin enlace mientras el valor esté vacío")
                    else:
                        self.assertNotIn("Salvatto", pagina)

    def test_con_enlace_la_firma_lo_lleva(self):
        with mock.patch.object(construir_web, "MOSTRAR_CITA_SALVATTO", True), \
                mock.patch.object(construir_web, "ENLACE_CITA_SALVATTO", "https://x.com/ejemplo/status/1"), \
                tempfile.TemporaryDirectory() as tmp:
            pagina = leer("index.html", construir_temporal(Path(tmp), con_video=False))
            self.assertIn('<a href="https://x.com/ejemplo/status/1" rel="noopener" target="_blank">Luis Salvatto', pagina)

    def test_un_enlace_que_no_es_https_se_rechaza(self):
        with self.assertRaises(ValueError):
            construir_web.bloque_cita("en", True, "http://x.com/a")


class TestVideoDelLanzamiento(unittest.TestCase):
    def test_sin_los_archivos_se_queda_el_video_actual(self):
        for idioma, ruta in PORTADAS.items():
            with self.subTest(idioma=idioma):
                self.assertFalse(construir_web.hay_video_lanzamiento(RAIZ), "ya existe el vídeo de la 3.0: actualiza este test")
                self.assertIn("video/hero/manalab-hero-", leer(ruta))
                self.assertNotIn("manalab-3.0", leer(ruta))

    def test_con_los_archivos_las_cuatro_portadas_lo_usan_con_su_prefijo(self):
        prefijo = {"en": "", "es": "../", "pt": "/", "ja": "/"}
        with tempfile.TemporaryDirectory() as tmp:
            salida = construir_temporal(Path(tmp), con_video=True)
            for idioma, ruta in PORTADAS.items():
                pagina = leer(ruta, salida)
                p = prefijo[idioma]
                with self.subTest(idioma=idioma):
                    self.assertIn(f'<source src="{p}video/manalab-3.0.mp4" type="video/mp4"/>', pagina)
                    self.assertIn(f'poster="{p}video/manalab-3.0-poster.jpg"', pagina)
                    self.assertIn(f'<link rel="preload" as="image" href="{p}video/manalab-3.0-poster.jpg">', pagina)
                    self.assertNotIn("manalab-hero-", pagina)
                    self.assertNotIn("video/webm", pagina)

    def test_las_demas_paginas_no_cambian_con_el_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            salida = construir_temporal(Path(tmp), con_video=True)
            for relativa in construir_web.listar_paginas(RAIZ):
                if relativa.as_posix() not in PORTADAS.values():
                    with self.subTest(pagina=relativa.as_posix()):
                        self.assertEqual(leer(relativa.as_posix(), salida), leer(relativa.as_posix()))


if __name__ == "__main__":
    unittest.main()
