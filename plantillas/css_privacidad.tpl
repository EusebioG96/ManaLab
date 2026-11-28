{{> css_fuentes}}
/* Misma identidad que la portada: mesa oscura verdosa, hueso como color de acción, oro solo en antetítulos (WEB-06). */
:root { color-scheme: dark; --fondo: #0d100f; --panel: #141917; --panel2: #1b211e; --linea: rgba(236, 230, 214, 0.12); --linea2: rgba(236, 230, 214, 0.26);
  --texto: #ece6d6; --texto2: #b9b2a1; --apagado: #9a9484; --hueso: #ece6d6; --oro: #e2b45c;
  --f-display: "Marcellus", "Marcellus Reserva", Georgia, "Times New Roman", serif; --f-texto: "Geist", "Geist Reserva", "Segoe UI", system-ui, -apple-system, sans-serif; --f-mono: "Geist Mono", "Geist Mono Reserva", ui-monospace, "Cascadia Mono", Consolas, monospace; }
:root:lang(ja), :root:lang(zh), :root:lang(ko) { --f-display: "Yu Gothic UI", "Hiragino Sans", "Noto Sans CJK JP", "Noto Sans CJK KR", "Noto Sans CJK SC", "Malgun Gothic", "Microsoft YaHei", system-ui, sans-serif; --f-texto: var(--f-display); }
* { box-sizing: border-box; }
body { margin: 0; background: radial-gradient(1300px 760px at 70% -6%, #22302a 0%, #0d100f 60%) no-repeat var(--fondo); color: var(--texto); font: 17px/1.65 var(--f-texto); -webkit-font-smoothing: antialiased; }
/* ancho en em y no en ch: el ch de Geist y el de su tipo de reserva difieren y la columna saltaba al llegar la fuente (ML-417); 45.696em = 68ch de Geist a 17px. El japonés conserva los 68ch. */
main { max-width: 45.696em; margin: 0 auto; padding: 48px 20px 96px; }
:lang(ja) main { max-width: 68ch; }
h1, h2.titulo { font: 400 clamp(32px, 5vw, 46px)/1.1 var(--f-display); margin: 0 0 10px; color: var(--texto); }
h2 { font: 400 26px/1.2 var(--f-display); margin: 44px 0 12px; color: var(--texto); }
h3 { font: 600 17px var(--f-texto); margin: 22px 0 6px; color: var(--texto); }
:lang(ja) h1, :lang(ja) h2 { font-weight: 600; }
p, li { color: var(--texto2); }
a { color: var(--texto); text-decoration-color: var(--linea2); text-underline-offset: 3px; }
a:hover { text-decoration-color: currentColor; }
a:focus-visible, button:focus-visible, summary:focus-visible { outline: 2px solid var(--hueso); outline-offset: 2px; border-radius: 4px; }
main > p:first-child a { font: 400 23px var(--f-display); text-decoration: none; }
code { font: 0.88em var(--f-mono); background: var(--panel2); border: 1px solid var(--linea); border-radius: 4px; padding: 1px 6px; color: var(--texto); overflow-wrap: anywhere; }
.idiomas { display: flex; flex-wrap: wrap; gap: 10px; margin: 14px 0 26px; }
.idiomas a { border: 1px solid var(--linea2); border-radius: 4px; padding: 6px 12px; font: 500 13px var(--f-mono); color: var(--texto2); text-decoration: none; }
.idiomas a:hover { color: var(--texto); border-color: var(--apagado); }
.idiomas a[aria-current] { background: var(--hueso); border-color: var(--hueso); color: var(--fondo); }
.aviso { background: var(--panel); border: 1px solid var(--linea2); border-radius: 8px; padding: 14px 18px; }
section[hidden] { display: none; }
hr { border: 0; border-top: 1px solid var(--linea); margin: 48px 0; }
.volver { display: inline-block; margin-top: 32px; /* 36 px de antes menos los 4 px de relleno de css_toque */  font-size: 14px; }
ul { list-style: none; padding-left: 0; }
ul li { position: relative; padding-left: 26px; margin-bottom: 10px; }
ul li::before { content: ""; position: absolute; left: 4px; top: 11px; width: 8px; height: 8px; transform: rotate(45deg); background: var(--hueso); }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
{{> css_toque}}
