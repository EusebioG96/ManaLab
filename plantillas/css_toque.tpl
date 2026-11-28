/* Objetivos táctiles de 24 px como mínimo (WCAG 2.5.8, ML-417) sin cambiar el aspecto: el relleno vertical agranda el área que se toca
   y el margen negativo igual lo compensa, así que ni una línea se mueve (en un enlace en línea el margen vertical no cuenta y no estorba).
   Cada selector es un contexto donde el enlace va solo (pie, índice, barra de la guía, llamadas bajo un texto); los enlaces dentro de una frase
   quedan fuera porque la norma los exime, y los que tienen clase (botones) ya traen su relleno. :where() deja los selectores sin peso para que
   cualquier regla propia gane: en móvil el pie y el ZIP ya tienen min-height: 44px y devuelven este relleno a 0.
   tools/test_objetivos_tactiles_navegador.py recorre todas las páginas y avisa de los que falten. */
:where(footer a:not([class]), nav.indice li a, nav.inicio a:not([class]), a.enlace-sec, a.enlace-man, a.volver, .movil-zip a, .nota-hero a, .enlaces a, p > a:only-child:not([class])) { padding-block: 4px; margin-block: -4px; }
:where(p.nota-smartscreen a) { padding-block: 5px; margin-block: -5px; }
:where(footer a:not([class]), nav.indice li a, nav.inicio a:not([class])) { min-width: 24px; }
/* en línea el ancho mínimo no cuenta (en coreano un enlace de una sola letra, «덱», medía 16 px): como bloque en línea sí, y la letra se queda donde estaba */
:where(nav.indice li a) { display: inline-block; vertical-align: top; }
