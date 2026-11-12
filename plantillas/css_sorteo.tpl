
:root { --fondo:#0d0304; --panel:#1a0a0d; --texto:#f4eae4; --texto2:#c9b8b0; --oro:#e8b07c; --rojo:#c2363f; --linea:#3a1d22; }
body { margin:0; background:var(--fondo); color:var(--texto); font:16px/1.65 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width:760px; margin:0 auto; padding:40px 20px 80px; }
h1, h2.titulo { font-size:32px; margin:0 0 6px; color:var(--texto); }
h2 { font-size:22px; margin:36px 0 10px; color:var(--oro); }
h3 { font-size:17px; margin:22px 0 6px; }
p, li { color:var(--texto2); }
a { color:var(--oro); }
.idiomas { display:flex; gap:14px; margin:14px 0 26px; font-size:14px; }
.idiomas a { border:1px solid var(--linea); border-radius:999px; padding:4px 12px; text-decoration:none; }
.aviso { background:var(--panel); border:1px solid var(--linea); border-left:4px solid var(--rojo); border-radius:10px; padding:14px 18px; }
section[hidden] { display:none; }
hr { border:0; border-top:1px solid var(--linea); margin:48px 0; }
.volver { display:inline-block; margin-top:36px; font-size:14px; }
.resumen { background:var(--panel); border:1px solid var(--linea); border-left:4px solid var(--oro); border-radius:10px; padding:6px 20px 14px; margin:22px 0 8px; }
.resumen h2 { margin-top:16px; }
.resumen ul { margin:0; padding-left:20px; }
.boton-x { display:inline-block; margin-top:14px; background:var(--rojo); color:#fff5f0; text-decoration:none; font-weight:600; border-radius:999px; padding:10px 20px; }
.idiomas a[aria-current] { border-color:var(--oro); color:var(--texto); }
ol.bases li { margin:0 0 12px; }
ol.bases li strong { color:var(--texto); }

