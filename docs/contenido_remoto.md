# contenido.json: cambiar cosas de la app sin sacar versión

El archivo `contenido.json` está en la raíz de la web y se publica en `https://manalab.es/contenido.json`. La app lo descarga al abrir y cada 6 horas. No está en el sitemap y no lleva GoatCounter.

Contenido inicial:

```json
{"v": 1, "enlace_apoyo_metafy": "", "interruptores": {"banner_mdn": true}}
```

## Campos

- `v`: versión del esquema. Siempre `1`. Cualquier otro valor hace que la app ignore el archivo.
- `enlace_apoyo_metafy`: el enlace de apoyo a Metafy que enseña la app. Vacío (`""`) = no hay enlace. Si se pone, debe empezar por `https://`, ser de `metafy.gg`, `www.metafy.gg` o `manalab.es` (o un subdominio), sin usuario ni puerto y con 300 caracteres como máximo.
- `interruptores`: objeto con funciones que se encienden o apagan. Cada valor es `true`/`false` o un objeto `{"valor": true/false, "desde": "X.Y.Z", "hasta": "X.Y.Z"}`. `desde` y `hasta` son opcionales y limitan el interruptor a un rango de versiones de la app.
  - `banner_mdn`: el anuncio de Metafy al final del Panel.

El archivo entero no puede pasar de 64 KB.

## Ejemplos

Poner el enlace de Metafy:

```json
{"v": 1, "enlace_apoyo_metafy": "https://metafy.gg/@manalab", "interruptores": {"banner_mdn": true}}
```

Apagar el banner solo para la 2.3.3:

```json
{"v": 1, "enlace_apoyo_metafy": "", "interruptores": {"banner_mdn": {"valor": false, "desde": "2.3.3", "hasta": "2.3.3"}}}
```

## Si el archivo queda mal

Las apps lo ignoran y siguen con el último contenido bueno que tenían. Nada se rompe, pero tu cambio no llega a nadie hasta que lo arregles.

## Antes de fusionar

Cada cambio en `contenido.json` pasa este test antes de fusionarse:

```
python3 -m pytest tools/test_contenido_remoto.py
```
