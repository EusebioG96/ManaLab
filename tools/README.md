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

## Comprobaciones

`python3 tools/seo_check.py` y `for t in tools/test_*.py; do python3 "$t"; done`.
