# contenido.json: cambiar cosas de la app sin sacar versión

El archivo `contenido.json` está en la raíz de la web y se publica en `https://manalab.es/contenido.json`. La app lo descarga al abrir y cada 6 horas. No está en el sitemap y no lleva GoatCounter.

Contenido inicial:

```json
{"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "", "interruptores": {"banner_mdn": true}}
```

## Campos

- `v`: versión del esquema. Siempre `1`. Cualquier otro valor hace que la app ignore el archivo.
- `enlace_apoyo_metafy`: el enlace de apoyo a Metafy que enseña la app y, en la web, el botón grande «Apoyar en Metafy» del bloque «Apoya el proyecto» de las portadas en inglés y español (sin enlace, ese bloque no se genera). Vacío (`""`) = no hay enlace. Si se pone, debe empezar por `https://`, ser de `metafy.gg`, `www.metafy.gg` o `manalab.es` (o un subdominio), sin usuario ni puerto y con 300 caracteres como máximo.
- `enlace_suscripcion_ia`: el enlace de la suscripción del análisis con IA (6 $ al mes) en Metafy. Mismas reglas que `enlace_apoyo_metafy`. También lo lee la web al generarse (`tools/construir_web.py`):
  - Vacío (`""`): en los botones «Suscribirme en Metafy» de las portadas sale, sin enlace, el texto «Suscripción en Metafy: muy pronto» (traducido). Nunca un botón muerto.
  - Con valor: esos botones (tarjeta de la IA en Funciones y sección de IA de las cuatro portadas) llevan ese enlace.
- `interruptores`: objeto con funciones que se encienden o apagan. Cada valor es `true`/`false` o un objeto `{"valor": true/false, "desde": "X.Y.Z", "hasta": "X.Y.Z"}`. `desde` y `hasta` son opcionales y limitan el interruptor a un rango de versiones de la app.
  - `banner_mdn`: el anuncio de Metafy al final del Panel.
- `coaches`: la lista gratuita de coaches. **La versión 3.0 de la app no los enseña**: la app los acepta y los valida, pero no salen en ninguna pantalla, así que poner un coach aquí no lo hace visible. El campo queda para el futuro, por si se amplía el cupo de creadores (el código de la app se conserva). Opcional. Máximo 100; los de más se ignoran. Cada coach es un objeto con:
  - `nombre`: hasta 60 caracteres.
  - `linea`: hasta 80 caracteres. Por ejemplo «Standard y Pioneer · ES/EN».
  - `enlace`: su perfil en Metafy. Empieza por `https://`, es de `metafy.gg` o un subdominio, sin usuario, contraseña ni puerto, y tiene 300 caracteres como máximo.
  - `foto`: opcional. Ver «Fotos» más abajo.
- `destacados`: los creadores que pagan y **la única lista que se ve en la app** (pantalla Aprender). Opcional. Máximo 10; los de más se ignoran. Cada uno lleva lo mismo que un coach (`nombre`, `linea`, `enlace`, `foto`) y, además, tres enlaces opcionales a Metafy con las mismas reglas que `enlace`: `academia`, `guias` y `sesiones`. Un enlace vacío (`""`) o ausente es «no hay».
  - `frase`: opcional. Una frase del creador sobre lo que ofrece, en el idioma en que la escriba (no se traduce). Texto plano de 140 caracteres como máximo, sin caracteres de control ni invisibles. Sin frase (o si no vale), el banner sale sin ella.
  - `fondo`: opcional. Una imagen suya para el banner de «Aprender» (WebP de 1200×430 px, 120 kB como máximo; súbela a `coaches/fondos/<nombre>.webp`). Mismas reglas que `foto`: `https` de `manalab.es`, ruta terminada en `.webp`, `.png` o `.jpg`, sin parámetros. Sin fondo (o si no vale), sale el abanico de cartas.
  - La web también los usa (página «Learn»): `tools/construir_web.py` escribe el primero en el HTML al generarse y `learn/learn.js` rota todos cada 8 segundos. Con `destacados` vacío, la página no lleva banner ni barra fina. Cambiar la lista exige regenerar la web (`python3 tools/construir_web.py`) y publicarla.
  - Con un solo destacado no hay contador ni rotación.
  - Con varios, rotan cada 8 segundos y el primero cambia en cada apertura de la app.
- Los textos (`nombre`, `linea`) no pueden llevar caracteres de control, invisibles (ancho cero, por ejemplo) ni marcas que inviertan el sentido del texto. Los enlaces no pueden llevar comillas, ángulos (`<` `>`) ni barra invertida.

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

Dejar un coach en el archivo (datos inventados, solo de ejemplo). La app 3.0 lo valida pero no lo enseña; para que alguien salga en la app, ponlo en `destacados`:

```json
{"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "", "interruptores": {"banner_mdn": true}, "coaches": [{"nombre": "Ana Ejemplo", "linea": "Standard y Pioneer · ES/EN", "enlace": "https://metafy.gg/@ana-ejemplo", "foto": "https://manalab.es/coaches/fotos/ana-ejemplo.webp"}, {"nombre": "Luis Prueba", "linea": "Draft · ES", "enlace": "https://metafy.gg/@luis-prueba"}]}
```

Poner un destacado, que sí se ve en la app (datos inventados, solo de ejemplo):

```json
{"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "", "interruptores": {"banner_mdn": true}, "destacados": [{"nombre": "Marta Ejemplo", "linea": "Standard · ES/EN", "enlace": "https://metafy.gg/@marta-ejemplo", "foto": "https://manalab.es/coaches/fotos/marta-ejemplo.webp", "academia": "https://metafy.gg/@marta-ejemplo/academy", "guias": "https://metafy.gg/@marta-ejemplo/guides", "sesiones": "https://metafy.gg/@marta-ejemplo/sessions"}]}
```

## Fotos de destacados (y de coaches, si algún día se enseñan)

- Medidas: 160×160 píxeles, formato WebP, 20 kB como máximo.
- Se suben a esta web, en `coaches/fotos/<nombre>.webp` (por ejemplo `coaches/fotos/ana-ejemplo.webp`). Nombre en minúsculas, sin espacios.
- En el JSON, `foto` es la dirección completa: `https://manalab.es/coaches/fotos/ana-ejemplo.webp`.
- Reglas: `https`, host `manalab.es`, ruta terminada en `.webp`, `.png` o `.jpg`, sin parámetros (`?...`) ni ancla (`#...`).
- `foto` es opcional. Sin foto (ausente, `null` o `""`), la app enseña al destacado sin ella.
- Sube la foto y haz commit antes de poner su dirección en `contenido.json`.

## Añadir, quitar y ordenar

- Añadir: pon un objeto nuevo en la lista `destacados` (la que se ve). En `coaches` también se acepta, pero la app 3.0 no lo enseña.
- Quitar: borra su objeto de la lista.
- Ordenar: la app enseña los destacados en el mismo orden que el archivo (rotan, ver arriba). El primero del archivo es el primero de la app.
- Revisa las comas entre objetos. Una coma de más o de menos deja el archivo mal (ver «Si el archivo queda mal»).

## Si el archivo queda mal

Las apps lo ignoran y siguen con el último contenido bueno que tenían. Nada se rompe, pero tu cambio no llega a nadie hasta que lo arregles.

Si el archivo es válido pero un elemento de `coaches` o de `destacados` no lo es, la app no lo tira entero:

- Foto mala (otro dominio, `http`, extensión rara, con parámetros): el destacado se enseña igualmente, sin foto (un coach también se acepta sin ella, aunque la app 3.0 no los enseñe).
- Cualquier otro campo malo (nombre o línea vacíos o demasiado largos, enlace que no es de Metafy, un enlace extra malo): ese elemento no sale. Los demás sí.
- Más de 100 coaches o más de 10 destacados: los de más no salen.
- Si `coaches` o `destacados` no es una lista, no sale ninguno.

El test es más estricto que la app: marca como error también la foto mala, para que no llegue al archivo publicado.

Poner el enlace de la suscripción a la IA (la web lo usa al regenerarse con `python3 tools/construir_web.py`; hay que hacer commit de los `.html`):

```json
{"v": 1, "enlace_apoyo_metafy": "", "enlace_suscripcion_ia": "https://metafy.gg/@manalab/ia", "interruptores": {"banner_mdn": true}}
```

## Antes de fusionar

Cada cambio en `contenido.json` pasa este test antes de fusionarse:

```
python3 -m unittest discover -s tools -p "test_contenido_remoto.py"
```
