# contenido.json: cambiar cosas de la app sin sacar versión

El archivo `contenido.json` está en la raíz de la web y se publica en `https://manalab.es/contenido.json`. La app lo descarga al abrir y cada 6 horas. No está en el sitemap y no lleva GoatCounter.

Contenido inicial:

```json
{"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "", "interruptores": {"banner_mdn": true}}
```

## Campos

- `v`: versión del esquema. Siempre `1`. Cualquier otro valor hace que la app ignore el archivo.
- `enlace_apoyo_metafy`: el enlace de apoyo a Metafy que enseña la app y, en la web, el botón grande «Apoyar en Metafy» del bloque «Apoya el proyecto» de las portadas en inglés y español (sin enlace, ese bloque no se genera). Vacío (`""`) = no hay enlace. Si se pone, debe empezar por `https://`, ser de `metafy.gg`, `www.metafy.gg` o `manalab.es` (o un subdominio), sin usuario ni puerto y con 300 caracteres como máximo.
- `enlace_suscripcion_ia`: el enlace de la suscripción del análisis con IA (5 € al mes) en Metafy. Mismas reglas que `enlace_apoyo_metafy`. También lo lee la web al generarse (`tools/construir_web.py`):
  - Vacío (`""`): en los botones «Suscribirme en Metafy» de las portadas sale, sin enlace, el texto «Suscripción en Metafy: muy pronto» (traducido). Nunca un botón muerto.
  - Con valor: esos botones (tarjeta de la IA en Funciones y sección de IA de las cuatro portadas) llevan ese enlace.
- `interruptores`: objeto con funciones que se encienden o apagan. Cada valor es `true`/`false` o un objeto `{"valor": true/false, "desde": "X.Y.Z", "hasta": "X.Y.Z"}`. `desde` y `hasta` son opcionales y limitan el interruptor a un rango de versiones de la app.
  - `banner_mdn`: el anuncio de Metafy al final del Panel.

El archivo entero no puede pasar de 64 KB.

## Ejemplos

Poner el enlace de Metafy:

```json
{"v": 1, "enlace_apoyo_metafy": "https://metafy.gg/@manalab", "enlace_suscripcion_ia": "", "interruptores": {"banner_mdn": true}}
```

Apagar el banner solo para la 2.3.3:

```json
{"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "", "interruptores": {"banner_mdn": {"valor": false, "desde": "2.3.3", "hasta": "2.3.3"}}}
```

## Si el archivo queda mal

Las apps lo ignoran y siguen con el último contenido bueno que tenían. Nada se rompe, pero tu cambio no llega a nadie hasta que lo arregles.

Poner el enlace de la suscripción a la IA (la web lo usa al regenerarse con `python3 tools/construir_web.py`; hay que hacer commit de los `.html`):

```json
{"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "https://metafy.gg/@manalab/ia", "interruptores": {"banner_mdn": true}}
```

## Antes de fusionar

Cada cambio en `contenido.json` pasa este test antes de fusionarse:

```
python3 -m pytest tools/test_contenido_remoto.py
```
