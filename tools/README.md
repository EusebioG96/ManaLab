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
