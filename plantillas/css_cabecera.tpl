/* ---------------- cabecera (ML-329: única copia; la insertan css_sitio y css_seguridad con {{> css_cabecera}}) */
body::before { content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 10; background: rgba(13, 16, 15, 0.94); }
.cab { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 9; background: rgba(13, 16, 15, 0.86); backdrop-filter: blur(12px); border-bottom: 1px solid var(--linea); }
.cab .envoltura { position: relative; display: flex; align-items: center; gap: 18px 26px; padding-block: 14px; }
.marca { display: flex; align-items: center; gap: 10px; text-decoration: none; color: var(--texto); margin-right: auto; }
.marca img { width: 36px; height: 36px; }
.marca b { font: 400 23px/1 var(--f-display); letter-spacing: 0.01em; }
.cab nav { display: flex; gap: 22px; }
.cab .menu-caja nav { display: grid; gap: 0; }
.cab nav a { color: var(--texto2); text-decoration: none; font-size: 15px; }
.cab nav a:hover { color: var(--texto); }
/* un enlace del menú de escritorio nunca se parte en dos líneas: si la fila no cabe, la cabecera pasa al menú de teléfono (más abajo) */
.cab .envoltura > nav a, .cab .idioma { white-space: nowrap; }
.idioma { border: 1px solid var(--linea2); background: none; color: var(--texto2); border-radius: 4px; min-height: 34px; padding: 0 12px; font: 500 13px var(--f-mono); letter-spacing: 0; cursor: pointer; }
.idioma:hover { color: var(--texto); border-color: var(--apagado); }
.boton { display: inline-flex; align-items: center; gap: 10px; border-radius: 4px; min-height: 40px; padding: 0 18px; font: 500 14px var(--f-texto); text-decoration: none; border: 1px solid transparent; cursor: pointer; transition: background .15s, transform .1s; white-space: nowrap; }
.boton:active { transform: translateY(1px); }
.boton.prim { background: var(--hueso); color: var(--fondo); }
.boton.prim:hover { background: var(--hueso-h); }
.boton.sec { background: transparent; border-color: rgba(236, 230, 214, 0.34); color: var(--texto); }
.boton.sec:hover { border-color: var(--hueso); }
.boton svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.boton.descarga, .hero-cta .boton, .final-caja .boton, .paso .boton { min-height: 48px; padding: 0 26px; font-size: 16px; font-weight: 600; }
.cab .boton, .cab .boton.descarga { min-height: 40px; padding: 0 16px; font-size: 14px; font-weight: 500; }

/* menú de teléfono (WEB-02): <details> sin JavaScript; solo se ve por debajo de 900 px */
.menu { display: none; }
.menu > summary::-webkit-details-marker { display: none; }
.cab .menu-caja nav a { display: block; padding: 13px 0; border-top: 1px solid var(--linea); font-size: 17px; color: var(--texto); text-decoration: none; }
.menu > summary { cursor: pointer; list-style: none; width: 40px; height: 40px; display: grid; place-items: center; border: 1px solid var(--linea2); border-radius: 4px; color: var(--texto); }
.menu > summary svg { display: block; width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; }
.menu[open] > summary { background: var(--hueso); color: var(--fondo); border-color: var(--hueso); }
.menu-caja { position: absolute; left: 0; right: 0; top: 100%; max-height: calc(100vh - 72px); max-height: calc(100dvh - 72px); overflow-y: auto; overscroll-behavior: contain; padding: 0 20px 18px; background: var(--fondo); border-bottom: 1px solid var(--linea2); box-shadow: 0 30px 40px rgba(0, 0, 0, 0.5); }
.menu-idiomas { display: flex; flex-wrap: wrap; gap: 8px; padding-top: 14px; border-top: 1px solid var(--linea); }
.menu-idiomas .idioma { display: inline-grid; min-height: 40px; padding: 0 14px; }
a.idioma { text-decoration: none; display: inline-grid; place-items: center; }
@media (max-width: 900px) {
  .cab .envoltura { gap: 10px 12px; }
  .cab .envoltura > nav, .cab .envoltura > .idioma { display: none; }
  .menu { display: block; }
}
/* desde 640 px (tableta y escritorio con el menú compacto) la caja no se estira de lado a lado: ancho de tarjeta, pegada a la derecha, bajo el botón */
@media (min-width: 640px) {
  .menu-caja { left: auto; width: 380px; max-width: 100%; border-left: 1px solid var(--linea2); }
}
/* a 380 px o menos no cabe el nombre junto a «Descargar» y el menú: queda el logotipo */
@media (max-width: 380px) { .marca span { display: none; } }
