# Herramientas de la web

## Las páginas se generan desde plantillas (ML-197)

Los `.html` del repositorio **no se editan a mano**: salen de `plantillas/` con `tools/construir_web.py`.
`tools/test_construir_web.py` falla si un `.html` no coincide con lo que generan las plantillas.

| Qué | Dónde |
| --- | --- |
| Contenido de cada página (cabecera `<head>`, texto, scripts) | `plantillas/paginas/<ruta>.pagina`, que se publica en `<ruta>.html` |
| Cabecera de la web (`cabecera_en`, `_es`, `_pt`, `_ja`, `_guia`) | `plantillas/cabecera_<idioma>.tpl` |
| Pie de la web (`pie_en`, `_es`, `_pt`, `_ja`, `_guia`) | `plantillas/pie_<idioma>.tpl` |
| CSS (`css_sitio`, `css_seguridad`, `css_guia`, `css_sorteo`, `css_privacidad`) | `plantillas/css_<grupo>.tpl` |

Una página inserta una plantilla con `{{> pie_es}}`. Si las páginas de un mismo grupo difieren en alguna
parte (por ejemplo, el enlace de «Preguntas» del pie, o una regla de CSS propia de la portada), esa parte es un
**hueco** `{{@N}}` en la plantilla, con sus variantes en `plantillas/<plantilla>/N.<variante>.txt`; la página elige
la variante con `{{> pie_es 2=b}}` (sin indicar nada, la `a`).

### Cambiar un enlace del pie

1. Edita el pie del idioma: `plantillas/pie_es.tpl` (o `pie_en.tpl`, `pie_pt.tpl`, `pie_ja.tpl`, `pie_guia.tpl`).
   Si el enlace está en un hueco, edita su variante en `plantillas/pie_es/N.<variante>.txt`.
2. Regenera: `python3 tools/construir_web.py`.
3. Comprueba: `python3 tools/test_construir_web.py` y `python3 tools/seo_check.py`.
4. Haz commit de las plantillas **y** de los `.html` que hayan cambiado.

`python3 tools/construir_web.py --comprobar` dice qué páginas están desactualizadas sin escribir nada.

### Cambiar un enlace de la cabecera (ML-272)

La cabecera (`cabecera_es`, `_en`, `_pt`, `_ja`) lleva dos copias de los enlaces de sección y de los botones de idioma:
la fila de escritorio y, al final, el menú de teléfono `<details class="menu">` (sin JavaScript, solo visible por debajo de
900 px). Si cambias un enlace, cámbialo en las dos copias de la misma variante; `tools/test_linea_visual_base.py` falla si
no coinciden. La copia del menú no lleva `id`.

### Enlaces de Metafy (ML-274)

Los enlaces de Metafy salen solo de `contenido.json` (`enlace_suscripcion_ia` y `enlace_apoyo_metafy`; ver `docs/contenido_remoto.md`).
En una página se escriben como bloques, no como enlaces:

- `{{SUSCRIPCION_IA clase="" estilo="" medicion="metafy-ia-es" texto="…" pronto="…"}}`: con enlace, el botón de suscripción;
  sin enlace, el texto `pronto` (sin enlace, nunca un botón muerto).
- `{{APOYO_METAFY eti="…" titulo="…" texto="…" boton="…" medicion="…"}}`: el bloque «Apoya el proyecto» con el botón grande
  `.b-metafy` y el logotipo `img/metafy.svg`; sin enlace no genera nada.

Para poner un enlace: edita `contenido.json`, ejecuta `python3 tools/construir_web.py` y haz commit de los `.html`.

### Eventos de descarga de GoatCounter (ML-280)

Cada botón de descarga envía un evento propio: `<tipo>-<página>-<idioma>[-<posición>]` (tipo `descarga`, `descarga-movil` o
`compartir-movil`; p. ej. `descarga-portada-es-hero`, `descarga-magic-online-en`, `compartir-movil-coaches-pt`). En las plantillas no
se escribe el nombre: se pone `{{EVENTO:descarga}}` o `{{EVENTO:descarga:hero}}` (con posición si la página tiene varios botones) y
`construir_web.py` lo completa con la página y el idioma de la ruta. `tools/test_eventos_descarga.py` vigila el patrón y que no se repita ningún nombre.

### Enlace por correo en el teléfono (ML-295)

Las cuatro portadas llevan en su `<template id="bloque-movil">` la marca `{{CORREO_MOVIL txt="…"}}`. Con `URL_ENLACE_CORREO = ""` en
`tools/construir_web.py` (el valor actual) genera el párrafo de siempre; con la dirección del servidor (`POST /enlace-descarga`, ver
`servidor_ia/LEEME.txt` del repositorio de la app) genera el campo de correo con los textos de `TEXTOS_CORREO`. Para activarlo: pon la
dirección, `python3 tools/construir_web.py` y commit de los `.html`. Evento: `correo-movil-portada-<idioma>`. Lo vigila `tools/test_correo_movil.py`.

### Versión y enlaces de descarga

`version.json` es la única fuente de la versión actual. Las plantillas y páginas no llevan números de versión: donde
hace falta «la versión actual» (texto `<span data-version>`, enlaces `releases/download/vX.Y.Z/ManaLab-X.Y.Z-portable.zip`,
manual `ManaLab-manual-en.pdf`, `softwareVersion` del JSON-LD) escriben `{{VERSION}}`, y `construir_web.py` lo sustituye
por el campo `version` de `version.json`. Las menciones a versiones pasadas (historial de novedades) se escriben tal cual.

`tools/generar_version_json.py` (workflow `version_json.yml`, al publicar una release) escribe `version.json` y regenera
las 31 páginas; el workflow hace commit de `version.json` y de los `.html` que cambian. Nunca se editan plantillas para
subir de versión. `tools/test_version_unica.py` falla si alguna página trae una versión de descarga distinta de la actual.

## Comprobaciones

`python3 tools/seo_check.py` y `for t in tools/test_*.py; do python3 "$t"; done`.

### Portada y novedades de la 3.0 (ML-281)

- **Aviso de versión** (`<div class="aviso-version">` arriba de las cuatro portadas): se cambia a mano en `plantillas/paginas/{,es/,pt/,ja/}index.pagina`.
  pt y ja enlazan a las novedades en inglés (`/novedades/`), porque no hay novedades en su idioma.
- **Vídeo del lanzamiento**: `tools/construir_web.py` (`VIDEO_LANZAMIENTO`, `POSTER_LANZAMIENTO`). Cuando existan los dos archivos
  `video/manalab-3.0.mp4` y `video/manalab-3.0-poster.jpg`, las cuatro portadas los usan en el héroe (solo MP4, sin WebM) al regenerar; no hay
  que tocar plantillas. Mientras falte alguno, se queda el vídeo actual (`video/hero/`). Para activarlo: subir los dos archivos y ejecutar
  `python3 tools/construir_web.py`.
- **Cita de Luis Salvatto** (portadas en inglés y español): `MOSTRAR_CITA_SALVATTO` en `tools/construir_web.py`, **apagado**. Apagado no hay
  ni rastro en el HTML. Para encenderlo: ponerlo en `True`, rellenar `ENLACE_CITA_SALVATTO` con la dirección https de su post (vacío = la
  firma sale sin enlace) y regenerar.
- **Conexiones de la app** (`/safety/`, `/es/seguridad/`, `/privacy/`): `tools/test_conexiones_listadas.py` lleva la lista de hosts de la app;
  si la app habla con un host nuevo, se añade ahí y a las páginas.
