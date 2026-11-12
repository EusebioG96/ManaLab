
:root{--bg:#f7f6f2;--fg:#1d1d22;--muted:#5c5c66;--acc:#6b4fbb;--card:#fff;--line:#e3e1d9}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#16161b;--fg:#ecebf2;--muted:#a3a3b0;--acc:#a98bf0;--card:#1f1f26;--line:#33333d}}
:root[data-theme="dark"]{--bg:#16161b;--fg:#ecebf2;--muted:#a3a3b0;--acc:#a98bf0;--card:#1f1f26;--line:#33333d}
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

