{{> css_fuentes}}
:root{--bg:#f7f6f2;--fg:#1d1d22;--muted:#5c5c66;--acc:#6b4fbb;--card:#fff;--line:#e3e1d9}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans CJK JP","Noto Sans CJK KR","Noto Sans CJK SC",sans-serif}
main{max-width:820px;margin:0 auto;padding:32px 16px 48px}
header{border-bottom:2px solid var(--acc);padding-bottom:16px;margin-bottom:24px}
h1{margin:0 0 6px;font-size:2rem;color:var(--acc)}
.sub{margin:0;color:var(--muted)}
nav.indice{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 20px;margin-bottom:28px}
nav.indice h2{margin:0 0 8px;font-size:1.1rem}
nav.indice ol{margin:0;padding-left:20px;columns:2}
nav.indice a{color:var(--acc);text-decoration:none}
section{margin:0 0 32px;page-break-inside:avoid;break-inside:avoid}
section h2{font-size:1.4rem;margin:0 0 10px;padding-bottom:4px;border-bottom:1px solid var(--line)}
section h3{font-size:1.05rem;margin:16px 0 6px}
p{margin:0 0 10px}
ul,ol{margin:0 0 10px;padding-left:24px}
li{margin-bottom:4px}
figure{margin:14px 0 6px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px}
figure.video{margin:16px 0 8px}
figure.video video{display:block;width:100%;height:auto;aspect-ratio:16/9;border-radius:6px;background:#000}
figure.video figcaption{margin:8px 4px 2px;font-size:.9rem;color:var(--muted)}
figure.video .idioma-video{display:inline-block;margin-left:6px;padding:0 7px;border:1px solid var(--line);border-radius:10px;font-size:.78rem;white-space:nowrap}
.solo-pdf{display:none}
figure img{display:block;width:100%;height:auto;border-radius:6px}
nav.inicio{margin:0 0 14px;font-size:.9rem;display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px}nav.inicio a,footer nav a{color:var(--acc)}
nav.inicio a.descargar{background:var(--acc);color:var(--bg);font-weight:700;text-decoration:none;padding:6px 14px;border-radius:999px;white-space:nowrap}
main>nav.inicio:last-of-type{margin:28px 0 0}
footer nav{margin-bottom:8px}
footer{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);color:var(--muted);font-size:.85rem}
@page{size:A4;margin:16mm 14mm}
@media print{
  body{background:#fff;color:#000}
  main{max-width:none;padding:0}
  h1{color:#4b2fa0}
  section h2{color:#4b2fa0}
  nav.indice{background:#fff}
  nav.inicio,footer nav{display:none}
  figure{background:#fff}
  figure.video video{display:none}
  figure.video img.solo-pdf{display:block;width:62%;height:auto;margin:0 auto;border:1px solid #ccc;border-radius:6px}
  span.solo-pdf{display:block;margin-top:4px}
  a{color:inherit}
}

/* WEB-07, «La mesa de juego»: en pantalla las guías son siempre oscuras. La hoja de impresión (arriba) no cambia: el PDF sale claro. Todo lo nuevo, solo en pantalla. */
@media screen {
  :root { --bg: #0d100f; --fg: #ece6d6; --muted: #9a9484; --acc: #ece6d6; --card: #141917; --line: rgba(236, 230, 214, 0.16); --texto: #ece6d6; --texto2: #b9b2a1; --oro: #e2b45c; --linea2: rgba(236, 230, 214, 0.26);
    --f-display: "Marcellus", "Marcellus Reserva", Georgia, "Times New Roman", serif; --f-texto: "Geist", "Geist Reserva", "Segoe UI", system-ui, -apple-system, sans-serif; --f-mono: "Geist Mono", "Geist Mono Reserva", ui-monospace, "Cascadia Mono", Consolas, monospace; color-scheme: dark; }
  :root:lang(ja), :root:lang(zh), :root:lang(ko) { --f-display: "Yu Gothic UI", "Hiragino Sans", "Noto Sans CJK JP", "Noto Sans CJK KR", "Noto Sans CJK SC", "Malgun Gothic", "Microsoft YaHei", system-ui, sans-serif; --f-texto: var(--f-display); }
  body { background: radial-gradient(1300px 760px at 70% -6%, #22302a 0%, #0d100f 60%) no-repeat #0d100f; font: 17px/1.65 var(--f-texto); -webkit-font-smoothing: antialiased; }
  h1, h2 { font-family: var(--f-display); font-weight: 400; letter-spacing: 0.005em; }
  :lang(ja) h1, :lang(ja) h2, :lang(zh) h1, :lang(zh) h2, :lang(ko) h1, :lang(ko) h2 { font-weight: 600; }
  a { color: var(--fg); text-decoration-color: var(--linea2); text-underline-offset: 3px; }
  a:hover { text-decoration-color: currentColor; }
  a:focus-visible, summary:focus-visible { outline: 2px solid var(--fg); outline-offset: 2px; border-radius: 4px; }
  code { font-family: var(--f-mono); }
  /* ancho en em y no en ch: el ch de Geist y el de su tipo de reserva difieren y la columna saltaba al llegar la fuente (ML-417); 45.696em = 68ch de Geist a 17px. El japonés, chino y coreano no usan Geist y conservan los 68ch. */
  main { max-width: 45.696em; padding: 40px 20px 72px; }
  :lang(ja) main, :lang(zh) main, :lang(ko) main { max-width: 68ch; }
  header { border-bottom: 1px solid var(--line); padding-bottom: 22px; margin-bottom: 28px; }
  h1 { font-size: clamp(34px, 5vw, 48px); line-height: 1.08; color: var(--texto); margin-bottom: 10px; }
  .sub { color: var(--texto2); font-size: 18px; }
  nav.indice { border-radius: 8px; padding: 20px 24px; }
  nav.indice h2 { font-family: var(--f-texto); font-size: 13px; font-weight: 500; letter-spacing: 0.14em; text-transform: uppercase; color: var(--oro); margin-bottom: 12px; }
  nav.indice a { color: var(--texto2); text-decoration: none; }
  nav.indice a:hover { color: var(--texto); text-decoration: underline; }
  nav.indice li::marker { color: var(--muted); font-family: var(--f-mono); font-size: 13px; }
  section { margin-bottom: 48px; }
  section h2 { font-size: 28px; line-height: 1.2; padding-bottom: 10px; margin-bottom: 14px; color: var(--texto); }
  section h3 { font-family: var(--f-texto); font-weight: 600; font-size: 17px; color: var(--texto); }
  p, li { color: var(--texto2); }
  figure { border-radius: 10px; padding: 0; overflow: hidden; border-color: rgba(236, 230, 214, 0.34); box-shadow: 0 24px 50px rgba(0, 0, 0, 0.5); margin: 20px 0 10px; }
  figure img, figure.video video { border-radius: 0; }
  figure.video figcaption { padding: 0 12px 10px; }
  nav.inicio a, footer nav a { color: var(--texto2); }
  nav.inicio a.descargar { background: #ece6d6; color: #0d100f; border-radius: 4px; padding: 9px 16px; font-weight: 600; }
  nav.inicio a.descargar:hover { background: #fff; }
}
@media screen and (max-width: 560px) { nav.indice ol { columns: 1; } }
{{> css_toque}}
