/* ---------------- página Learn (WEB-08, ML-324): las guías de Metafy, el creador destacado y la barra fina */
:root { --alto-cab: 69px; }
html { scroll-padding-top: calc(var(--alto-cab) + 44px + 12px); }
.ap-cab { padding-block: 48px 26px; }
.ap-cab h1 { font-size: clamp(38px, 5.2vw, 60px); line-height: 1.06; margin: 14px 0 12px; }
.ap-cab p { font-size: 19px; line-height: 1.55; color: #cfc8b6; max-width: 56ch; margin: 0; }
.ap-bloque { padding-bottom: 28px; }
/* creador destacado: el banner de VIS-23 con la letra de la web. Todos los creadores comparten la celda: el alto es el del más alto */
.d2 { --escena: clamp(7em, 21%, 15em); font-size: 16px; position: relative; overflow: hidden; display: grid; grid-template-columns: minmax(0, 1fr);
  border: 1px solid rgba(236,230,214,.34); border-radius: 8px; background: #141917; box-shadow: inset 0 0 0 4px rgba(20,25,23,.9), inset 0 0 0 5px rgba(236,230,214,.1);
  transition: translate .18s ease, border-color .18s ease; }
.d2:hover { border-color: #ece6d6; translate: 0 -2px; }
.d2c { grid-area: 1 / 1; position: relative; isolation: isolate; display: grid; grid-template-columns: auto minmax(0, 1fr) var(--escena); gap: 0 1.33em; align-items: center;
  padding: 1.2em 1.4em 1.35em; opacity: 0; visibility: hidden; transition: opacity .4s ease, visibility 0s .4s; }
.d2c.on { opacity: 1; visibility: visible; transition: opacity .4s ease, visibility 0s; }
.d2esc { position: absolute; inset: 0; z-index: -1; pointer-events: none; background: radial-gradient(34em 16em at 86% 46%, rgba(52,84,68,.85) 0%, rgba(31,42,37,.5) 46%, rgba(20,25,23,0) 76%); }
.d2fondo { position: absolute; right: 0; top: 0; width: 54%; height: 100%; object-fit: cover; -webkit-mask-image: linear-gradient(to right, transparent, #000 55%); mask-image: linear-gradient(to right, transparent, #000 55%); }
.d2fondo + .d2zona { display: none; }
.d2esc:has(.d2fondo)::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, #141917 0 42%, rgba(20,25,23,.5) 100%); }
.d2zona { position: absolute; right: 0; top: 0; bottom: 0; width: calc(var(--escena) + 1.33em); }
.d2aba { position: absolute; left: 54%; bottom: 0; width: 42%; aspect-ratio: 5 / 7; translate: -50% 16%; }
.d2aba i { position: absolute; inset: 0; border-radius: 7%/5%; border: 1px solid rgba(236,230,214,.5); background: linear-gradient(160deg, #222b27, #141917); transform-origin: 50% 118%; box-shadow: -6px 4px 14px rgba(0,0,0,.45); transition: rotate .25s ease; }
.d2aba i:nth-child(1) { rotate: -34deg; } .d2aba i:nth-child(2) { rotate: -17deg; } .d2aba i:nth-child(3) { rotate: 0deg; z-index: 1; } .d2aba i:nth-child(4) { rotate: 17deg; } .d2aba i:nth-child(5) { rotate: 34deg; }
.d2aba i::before { content: ""; position: absolute; inset: 6%; border-radius: 5%/3.5%; border: 1px solid rgba(236,230,214,.16); }
.d2aba i:nth-child(3)::after { content: ""; position: absolute; left: 50%; top: 50%; width: 22%; aspect-ratio: 1; translate: -50% -50%; rotate: 45deg; border: 1px solid rgba(226,180,92,.75); }
.d2:hover .d2aba i:nth-child(1) { rotate: -40deg; } .d2:hover .d2aba i:nth-child(2) { rotate: -20deg; } .d2:hover .d2aba i:nth-child(4) { rotate: 20deg; } .d2:hover .d2aba i:nth-child(5) { rotate: 40deg; }
.d2foto, .d2barra .f { position: relative; border-radius: 50%; flex: none; display: grid; place-items: center; overflow: hidden; background: #1b211e; }
.d2foto { width: 6.13em; height: 6.13em; border: 1px solid rgba(236,230,214,.6); box-shadow: 0 0 0 3px #141917, 0 0 0 4px #e2b45c, 0 10px 22px rgba(0,0,0,.5); }
.d2foto .ini, .d2barra .f .ini { font: 400 1.6em/1 var(--f-display); color: #cfc8b6; }
.d2foto img, .d2barra .f img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.d2txt { min-width: 0; display: flex; flex-direction: column; align-items: flex-start; }
.d2nom { font: 400 1.87em/1.15 var(--f-display); max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: .2em; }
:lang(ja) .d2nom { font-weight: 600; font-size: 1.6em; }
.d2lin { color: #cfc8b6; font-size: .93em; margin-top: .15em; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.d2fra { color: #ece6d6; line-height: 1.4; margin-top: .5em; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; max-width: 100%; }
.d2acc { display: flex; align-items: center; flex-wrap: wrap; gap: .5em .93em; margin-top: .87em; }
.d2cta { display: inline-flex; align-items: center; gap: .5em; min-height: 44px; padding: 0 1.2em; border-radius: 4px; background: #ece6d6; color: #0d100f; font-weight: 600; white-space: nowrap; text-decoration: none; }
.d2c .d2cta::after { content: ""; position: absolute; inset: 0; }
.d2cta b { font-weight: 600; transition: translate .18s ease; } .d2:hover .d2cta b { translate: 3px 0; }
.d2cas { position: relative; z-index: 1; display: inline-flex; align-items: center; gap: .47em; color: #cfc8b6; font-size: .87em; white-space: nowrap; padding: .3em 0; border-bottom: 1px solid rgba(236,230,214,.3); text-decoration: none; }
.d2cas::before { content: ""; width: .4em; height: .4em; rotate: 45deg; background: #e2b45c; flex: none; }
.d2cas:hover { color: #ece6d6; border-bottom-color: #ece6d6; }
.d2pag { position: absolute; right: 1.07em; top: .87em; z-index: 2; display: flex; align-items: center; gap: .53em; }
.d2pag button { width: 32px; height: 32px; border: 1px solid rgba(236,230,214,.34); border-radius: 4px; background: rgba(20,25,23,.8); display: grid; place-items: center; color: #ece6d6; padding: 0; cursor: pointer; }
.d2pag button:hover { border-color: #ece6d6; }
.d2pag svg { width: 11px; height: 11px; fill: none; stroke: #ece6d6; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.d2pun { display: flex; gap: .47em; align-items: center; padding: 0 .2em; } .d2pun i { width: .5em; height: .5em; rotate: 45deg; border: 1px solid #8c8676; } .d2pun i.on { background: #ece6d6; border-color: #ece6d6; }
.d2anuncio { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.d2prog { position: absolute; left: 5px; right: 5px; bottom: 5px; height: 2px; background: rgba(236,230,214,.1); } .d2prog i { display: block; height: 100%; width: 100%; transform-origin: 0 50%; transform: scaleX(0); background: rgba(236,230,214,.6); }
@media (max-width: 700px) {
  .d2c { grid-template-columns: auto minmax(0, 1fr); gap: 0 14px; padding: 16px 16px 20px; align-items: start; }
  .d2zona { display: none; } .d2foto { width: 64px; height: 64px; margin-top: 30px; grid-row: 2 / span 2; }
  .d2txt { display: contents; } .d2txt > .eti { grid-column: 1 / -1; grid-row: 1; padding-right: 110px; margin-bottom: -22px; }
  .d2nom { white-space: normal; font-size: 26px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; margin-top: 30px; grid-column: 2; }
  .d2lin { grid-column: 2; white-space: normal; } .d2fra { grid-column: 1 / -1; margin-top: 14px; -webkit-line-clamp: 3; }
  .d2acc { grid-column: 1 / -1; } .d2cta { width: 100%; justify-content: center; } .d2cas { min-height: 44px; }
  .d2pag { right: 12px; top: 10px; }
  .d2fondo { width: 100%; opacity: .35; }
}
/* barra fina fija: sale cuando el banner ya no se ve; va pegada bajo la cabecera y no empuja nada. Oculta, lleva inert (no se llega con Tab) */
.d2barra { position: fixed; left: 0; right: 0; top: var(--alto-cab); z-index: 8; background: #141917; border-bottom: 1px solid rgba(236,230,214,.26); box-shadow: 0 10px 18px rgba(0,0,0,.5);
  opacity: 0; transform: translateY(-6px); pointer-events: none; transition: opacity .12s ease, transform .12s ease; }
.d2barra.visible { opacity: 1; transform: none; pointer-events: auto; transition: opacity .16s ease, transform .16s ease; }
.d2barra .envoltura { height: 44px; display: flex; align-items: center; gap: 12px; }
.d2barra .f { width: 28px; height: 28px; box-shadow: 0 0 0 2px #141917, 0 0 0 3px #e2b45c; border: 1px solid rgba(236,230,214,.6); font-size: 10px; }
.d2barra .n { font: 400 18px/1.2 var(--f-display); min-width: 3em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 0 1 auto; }
.d2barra .eti { flex: none; white-space: nowrap; font-size: 11px; }
.d2barra .d2cta { margin-left: auto; min-height: 30px; padding: 0 14px; font-size: 14px; flex: none; width: auto; }
/* en teléfono la etiqueta sigue entera: va encima del nombre y se quita la foto */
@media (max-width: 560px) { .d2barra .envoltura { display: grid; grid-template-columns: minmax(0, 1fr) auto; grid-template-rows: auto auto; gap: 2px 10px; align-content: center; } .d2barra .f { display: none; }
  .d2barra .eti { grid-area: 1 / 1; font-size: 10px; letter-spacing: .06em; } .d2barra .n { grid-area: 2 / 1; font-size: 16px; line-height: 1.1; } .d2barra .d2cta { grid-area: 1 / 2 / 3 / 3; padding: 0 10px; } }
/* «Para ti» vive en la app: aquí se cuenta y se ofrece la descarga */
.ap-app { display: flex; align-items: center; gap: 16px 28px; flex-wrap: wrap; padding: 18px 22px; border: 1px solid var(--linea); border-radius: 8px; background: rgba(236,230,214,.025); }
.ap-app p { margin: 0; flex: 1 1 320px; color: var(--texto2); font-size: 16px; line-height: 1.5; } .ap-app p b { color: var(--texto); font-weight: 600; }
/* filtros */
.ap-barra { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 12px; padding-block: 8px 18px; }
.ap-barra[hidden] { display: none; }
html:not(.learn-js) .ap-barra { visibility: hidden; }
.ap-seg { display: inline-flex; border: 1px solid var(--linea2); border-radius: 4px; overflow: hidden; }
.ap-seg button { min-height: 40px; padding: 0 14px; border: 0; border-left: 1px solid var(--linea2); background: none; color: var(--texto2); font: 500 14px var(--f-texto); cursor: pointer; } .ap-seg button:first-child { border-left: 0; }
.ap-seg button[aria-pressed="true"] { background: #ece6d6; color: #0d100f; font-weight: 600; }
.ap-campo { min-height: 40px; padding: 0 12px; border: 1px solid var(--linea2); border-radius: 4px; background: rgba(13,16,15,.7); color: var(--texto); font: 400 14px var(--f-texto); }
select.ap-campo { max-width: 100%; }
input.ap-campo { flex: 1 1 200px; min-width: 0; }
.ap-cuenta { margin-left: auto; font: 500 13px var(--f-mono); color: var(--apagado); white-space: nowrap; }
@media (max-width: 700px) { .ap-seg { width: 100%; } .ap-seg button { flex: 1; padding: 0 6px; font-size: 13px; } select.ap-campo { flex: 1 1 140px; min-width: 0; padding: 0 8px; font-size: 13px; } input.ap-campo { flex-basis: 100%; } .ap-cuenta { margin-left: 0; } }
/* rejilla de guías */
.ap-rej { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; }
.ap-rej.vacia { grid-template-columns: minmax(0, 1fr); }
@media (max-width: 1100px) { .ap-rej { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 800px) { .ap-rej { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; } }
.guia { display: flex; flex-direction: column; border: 1px solid var(--linea); border-radius: 6px; background: rgba(20,25,23,.86); overflow: hidden; min-width: 0; text-decoration: none; transition: translate .18s ease, border-color .18s ease; }
.guia:hover { border-color: #ece6d6; translate: 0 -3px; }
.port { aspect-ratio: 16 / 9; display: grid; place-items: center; position: relative; overflow: hidden; border-bottom: 1px solid var(--linea); }
.port svg { width: 34px; height: 34px; fill: none; stroke: rgba(236,230,214,.75); stroke-width: 1.4; stroke-linecap: round; stroke-linejoin: round; }
.port img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.c0 { background: linear-gradient(135deg, #1b211e, #141917); }
.precio { position: absolute; z-index: 1; right: 8px; top: 8px; padding: 3px 9px; border-radius: 4px; font: 600 13px var(--f-mono); background: rgba(13,16,15,.86); border: 1px solid rgba(236,230,214,.34); white-space: nowrap; }
.precio.gratis { background: #ece6d6; color: #0d100f; border-color: #ece6d6; font-family: var(--f-texto); } .precio.sus { border-style: dashed; font-family: var(--f-texto); }
.cu { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 5px; flex: 1; min-width: 0; }
.cu .t { font: 400 19px/1.22 var(--f-display); color: var(--texto); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
:lang(ja) .cu .t { font-weight: 600; font-size: 16px; }
.cu .a { font-size: 14px; color: var(--texto2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .cu .m { margin-top: auto; padding-top: 6px; display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 13px; color: var(--apagado); } .cu .m b { color: var(--texto); font: 500 13px var(--f-mono); }
@media (max-width: 560px) {
  .ap-rej { grid-template-columns: minmax(0, 1fr); gap: 10px; }
  .guia { flex-direction: row; } .port { flex: none; width: 132px; aspect-ratio: auto; border-bottom: 0; border-right: 1px solid var(--linea); }
  .precio { right: auto; left: 6px; top: 6px; font-size: 12px; padding: 2px 7px; } .cu { padding: 10px 12px; } .cu .t { font-size: 17px; }
}
@media (prefers-reduced-motion: reduce) { .guia, .d2, .d2aba i, .d2cta b { transition: none; } .guia:hover, .d2:hover { translate: none; } .d2prog { display: none; } .d2barra { transform: none; } }
/* sin guías, o ninguna que coincida */
.ap-caja { grid-column: 1 / -1; display: grid; justify-items: start; gap: 8px; padding: 26px 24px; border: 1px solid var(--linea2); border-radius: 8px; background: var(--panel); }
.ap-caja b { font: 400 22px/1.2 var(--f-display); } .ap-caja span { color: var(--texto2); }
.ap-caja button, .ap-caja .boton { margin-top: 6px; }
.ap-caja button { min-height: 44px; padding: 0 20px; border: 1px solid var(--linea2); border-radius: 4px; background: none; color: var(--texto); font: 500 15px var(--f-texto); cursor: pointer; }
/* paginador */
.ap-pag { display: flex; justify-content: center; align-items: center; gap: 6px; padding-block: 30px 12px; flex-wrap: wrap; }
.ap-pag a, .ap-pag > span { min-width: 44px; height: 44px; padding: 0 12px; display: grid; place-items: center; border: 1px solid var(--linea2); border-radius: 4px; font: 500 14px var(--f-mono); text-decoration: none; color: var(--texto); }
.ap-pag [aria-current] { background: #ece6d6; border-color: #ece6d6; color: #0d100f; } .ap-pag > span { border-color: transparent; color: var(--apagado); min-width: 24px; padding: 0; } .ap-pag .apagado { color: #6f6a5e; border: 1px solid var(--linea); min-width: 44px; }
.ap .apoyo { grid-template-columns: minmax(0, 1fr); }
