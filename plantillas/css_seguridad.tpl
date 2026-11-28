{{> css_fuentes}}
/* Misma identidad que la portada (ML-272): mesa oscura verdosa, hueso como color de acción, oro solo en antetítulos. */
:root {
  color-scheme: dark;
  --fondo: #0d100f; --fondo2: #111513; --panel: #141917; --panel2: #1b211e;
  --linea: rgba(236, 230, 214, 0.12); --linea2: rgba(236, 230, 214, 0.26);
  --texto: #ece6d6; --texto2: #b9b2a1; --apagado: #9a9484;
  --hueso: #ece6d6; --hueso-h: #ffffff;
  --oro: #e2b45c; --oro-suave: rgba(226, 180, 92, 0.12);
  --f-display: "Marcellus", "Marcellus Reserva", Georgia, "Times New Roman", serif;
  --f-texto: "Geist", "Geist Reserva", "Segoe UI", system-ui, -apple-system, sans-serif;
  --f-mono: "Geist Mono", "Geist Mono Reserva", ui-monospace, "Cascadia Mono", Consolas, monospace;
  --ancho: 1180px;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } * { animation: none !important; transition: none !important; } }
body { margin: 0; background: radial-gradient(1300px 760px at 70% -6%, #22302a 0%, #0d100f 60%) no-repeat var(--fondo); color: var(--texto); font: 16px/1.65 var(--f-texto); -webkit-font-smoothing: antialiased; }
a { color: var(--texto); text-decoration-color: var(--linea2); text-underline-offset: 3px; }
a:hover { text-decoration-color: currentColor; }
a:focus-visible, button:focus-visible, summary:focus-visible { outline: 2px solid var(--hueso); outline-offset: 2px; }
img { max-width: 100%; display: block; }
.envoltura { max-width: var(--ancho); margin: 0 auto; padding-left: max(20px, env(safe-area-inset-left, 0px)); padding-right: max(20px, env(safe-area-inset-right, 0px)); }
h1, h2 { font-family: var(--f-display); font-weight: 400; letter-spacing: 0.005em; text-wrap: balance; margin: 0; }
.eti { font: 500 13px/1.3 var(--f-texto); letter-spacing: 0.14em; text-transform: uppercase; color: var(--oro); }

{{> css_cabecera}}

/* pagina */
.portada { position: relative; overflow: hidden; padding-block: 64px 12px; }
.pagina { position: relative; max-width: 760px; margin: 0 auto; }
.portada h1 { font-size: clamp(34px, 5vw, 54px); line-height: 1.05; margin: 16px 0 18px; }
.lead { font-size: 18.5px; color: var(--texto2); margin: 0; max-width: 36em; }
.cuerpo { padding-block: 28px 80px; }
.cuerpo .pagina { display: grid; grid-template-columns: minmax(0, 1fr); gap: 0; }
/* sin caja: cada tarjeta se separa de la anterior por una línea */
.tarjeta { background: none; border: 0; border-top: 1px solid var(--linea); border-radius: 0; padding: 36px 0; scroll-margin-top: 84px; }
.tarjeta h2 { font-size: clamp(24px, 3vw, 32px); line-height: 1.12; margin: 0 0 16px; }
.tarjeta p, .tarjeta li { font-size: 17px; line-height: 1.6; }
.tarjeta p { margin: 0 0 12px; color: var(--texto2); }
.tarjeta p:last-child { margin-bottom: 0; }
.tarjeta ul, .tarjeta ol { list-style: none; margin: 0 0 14px; padding: 0; display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; color: var(--texto2); }
.tarjeta ul:last-child, .tarjeta ol:last-child { margin-bottom: 0; }
.tarjeta li { position: relative; padding-left: 36px; }
.tarjeta ul li::before { content: ""; position: absolute; left: 6px; top: 10px; width: 8px; height: 8px; transform: rotate(45deg); background: var(--hueso); }
.tarjeta ol { counter-reset: n; }
.tarjeta ol li { counter-increment: n; }
.tarjeta ol li::before { content: counter(n); position: absolute; left: 0; top: 2px; width: 24px; height: 24px; border-radius: 50%; border: 0; background: var(--hueso); color: var(--fondo); font: 600 13px/22px var(--f-mono); text-align: center; }
.tarjeta b { color: var(--texto); font-weight: 600; }
code { font: 0.88em var(--f-mono); background: var(--fondo); border: 1px solid var(--linea); border-radius: 6px; padding: 1px 6px; color: var(--texto); }
.cmd { margin: 10px 0 8px; background: #0a0c0b; border: 1px solid var(--linea); border-radius: 6px; padding: 12px 14px; overflow-x: auto; }
.cmd code { background: none; border: 0; padding: 0; font-size: 13.5px; white-space: pre; }
.firma { margin: 8px 4px 0; font: 400 20px var(--f-display); color: var(--texto); }

/* pie (el de la portada) */
footer { border-top: 1px solid var(--linea); padding-block: 36px; color: var(--apagado); font-size: 13.5px; }
footer a { color: var(--texto2); }
footer .envoltura { display: grid; gap: 14px; }
footer .fila { display: flex; flex-wrap: wrap; gap: 10px 24px; align-items: center; }
footer .guias { gap: 6px 16px; }
footer .guias a { color: inherit; }
footer .guias b { color: var(--texto2); font-weight: 600; }
footer .legal { max-width: 80ch; line-height: 1.6; margin: 0; }

@media (max-width: 900px) {
  .portada { padding-block: 40px 8px; }
}
@media (max-width: 480px) {
  .tarjeta { padding: 28px 0; }
  .tarjeta li { padding-left: 32px; }
  .lead { font-size: 17px; }
  .cmd code { white-space: pre-wrap; overflow-wrap: anywhere; }
}

{{> css_toque}}
