/* ManaLab · cifras de los creadores destacados de la página «Learn» (ML-333). Script clásico, sin dependencias y sin globales.
 *
 * Cuenta, por creador destacado, cuántas veces se vio y cuántos clics recibió, y lo manda a un servidor de ManaLab (Cloudflare) solo como
 * totales por día. Solo cuenta a los creadores con data-id en su tarjeta (lo escribe tools/construir_learn.py desde contenido.json); sin id no
 * se cuenta nada. Contadores: visto (tarjeta visible al menos al 50 % durante 1 s seguido, como mucho una vez por minuto y creador y nunca con
 * la pestaña oculta), metafy (botón o tarjeta), academia, guias, sesiones (las casillas) y barra (clic en la barra fina; no suma en metafy).
 *
 * Lo pendiente vive en localStorage (si falla, en memoria) y solo se borra lo que el servidor aceptó (204) o rechazó por mal formado (400);
 * 429, una red caída o cualquier otra respuesta lo conservan. Los días de hace más de 2 días se tiran. Envío: al ocultarse la página
 * y cada hora si sigue abierta. El servidor solo admite el origen https://manalab.es: en local contesta 403 y no pasa nada. */
(function (global) {
  "use strict";
  if (typeof document === "undefined") return;

  var DIRECCION = "https://registro-ia.eusebiog76.workers.dev/cifras-destacados";   // POST, contrato v1 (ver docs/contenido_remoto.md)
  var CLAVE = "manalab_cifras_destacados_v1";                                          // localStorage: lo pendiente por enviar
  var CONTADORES = ["visto", "metafy", "academia", "guias", "sesiones", "barra"];
  var CASILLAS = ["academia", "guias", "sesiones"];                                    // los contadores que son enlaces opcionales a Metafy
  var MAX_NUMERO = 500, MAX_CREADORES_DIA = 10, MAX_BYTES = 4000, DIAS_MAX = 2;        // límites del contrato (el cuerpo, por debajo de 4 KB)
  var VISTO_MS = 1000, VISTO_ENTRE_MS = 60000, ENVIO_MS = 3600000;                     // 1 s visible; 1 vista por minuto y creador; 1 envío por hora
  var PATRON_ID = /^[a-z0-9-]{1,40}$/, PATRON_DIA = /^\d{4}-\d{2}-\d{2}$/;
  var doc = document;

  // El estado de la página, en un solo objeto: memoria (si no hay localStorage), envío en curso, freno tras un 429 y la vigilancia de «visto».
  var E = { memoria: {}, enviando: false, noAntes: 0, ultimoVisto: {}, vigilando: "", temporizador: 0, razon: {} };

  function esObjeto(valor) { return valor !== null && typeof valor === "object" && !Array.isArray(valor); }
  function diaUtc(ms) { return new Date(ms).toISOString().slice(0, 10); }
  function diasAtras(dia) { return Math.round((Date.parse(diaUtc(Date.now())) - Date.parse(dia)) / 86400000); }

  /** Lo pendiente, reducido a lo que admite el contrato: días AAAA-MM-DD de hoy a hace 2 días, ids válidos, solo los 6 contadores, enteros 1..500. */
  function limpiar(crudo) {
    var salida = {};
    if (!esObjeto(crudo)) return salida;
    Object.keys(crudo).forEach(function (dia) {
      var edad = PATRON_DIA.test(dia) && !isNaN(Date.parse(dia)) ? diasAtras(dia) : -1;
      if (edad < 0 || edad > DIAS_MAX || !esObjeto(crudo[dia])) return;
      Object.keys(crudo[dia]).forEach(function (id) {
        if (!PATRON_ID.test(id) || !esObjeto(crudo[dia][id])) return;
        CONTADORES.forEach(function (c) {
          var n = crudo[dia][id][c];
          if (typeof n !== "number" || !Number.isInteger(n) || n < 1) return;
          salida[dia] = salida[dia] || {};
          salida[dia][id] = salida[dia][id] || {};
          salida[dia][id][c] = Math.min(n, MAX_NUMERO);
        });
      });
    });
    return salida;
  }
  function leer() {
    try {
      var texto = global.localStorage.getItem(CLAVE);
      if (texto !== null) return limpiar(JSON.parse(texto));
    } catch (error) { /* silencio: sin localStorage o con texto roto se usa la memoria */ }
    return limpiar(E.memoria);
  }
  function guardar(dias) {
    E.memoria = dias;
    try { global.localStorage.setItem(CLAVE, JSON.stringify(dias)); } catch (error) { /* silencio: queda en memoria */ }
  }

  /** Suma 1 al contador de ese creador en el día de hoy (UTC). Sin id válido o con un contador desconocido no hace nada. */
  function contar(id, contador) {
    if (!PATRON_ID.test(id || "") || CONTADORES.indexOf(contador) < 0) return;
    var dias = leer(), dia = diaUtc(Date.now());
    dias[dia] = dias[dia] || {};
    dias[dia][id] = dias[dia][id] || {};
    dias[dia][id][contador] = Math.min((dias[dia][id][contador] || 0) + 1, MAX_NUMERO);
    guardar(dias);
  }

  /** El cuerpo del POST con lo pendiente (como mucho 10 creadores por día y menos de 4 KB; lo que no cabe se queda para otro envío). null si no hay nada. */
  function armarCuerpo(dias) {
    var cuerpo = { v: 1, superficie: "web", dias: {} }, hay = false;
    var ordenados = Object.keys(dias).sort();
    for (var i = 0; i < ordenados.length; i++) {
      var dia = ordenados[i], ids = Object.keys(dias[dia]).sort().slice(0, MAX_CREADORES_DIA), parcial = {};
      ids.forEach(function (id) { parcial[id] = dias[dia][id]; });
      if (!ids.length) continue;
      cuerpo.dias[dia] = parcial;
      if (JSON.stringify(cuerpo).length > MAX_BYTES) { delete cuerpo.dias[dia]; break; }
      hay = true;
    }
    return hay ? { dias: cuerpo.dias, texto: JSON.stringify(cuerpo) } : null;
  }

  /** Quita de lo pendiente lo que se acaba de enviar (lo que se sumó mientras tanto se conserva). */
  function restar(enviado) {
    var dias = leer();
    Object.keys(enviado).forEach(function (dia) {
      Object.keys(enviado[dia]).forEach(function (id) {
        Object.keys(enviado[dia][id]).forEach(function (c) {
          if (!dias[dia] || !dias[dia][id] || !dias[dia][id][c]) return;
          dias[dia][id][c] -= enviado[dia][id][c];
          if (dias[dia][id][c] <= 0) delete dias[dia][id][c];
        });
        if (dias[dia] && dias[dia][id] && !Object.keys(dias[dia][id]).length) delete dias[dia][id];
      });
      if (dias[dia] && !Object.keys(dias[dia]).length) delete dias[dia];
    });
    guardar(dias);
  }

  /** Manda lo pendiente. Se llama al ocultarse la página y cada hora. 204 y 400 borran lo enviado; 429 frena una hora; lo demás lo conserva. */
  function enviar() {
    if (E.enviando || Date.now() < E.noAntes) return;
    var dias = leer();
    guardar(dias);   // de paso se tiran los días de hace más de 2 días
    var pedido = armarCuerpo(dias), promesa;
    if (!pedido || typeof global.fetch !== "function") return;
    E.enviando = true;
    try {
      promesa = global.fetch(DIRECCION, { method: "POST", keepalive: true, headers: { "Content-Type": "application/json" }, credentials: "omit",
                                          referrerPolicy: "no-referrer", body: pedido.texto });
    } catch (error) { E.enviando = false; return; }   // silencio: no se pudo ni empezar; queda pendiente
    promesa.then(function (r) {
      if (r.status === 204 || r.status === 400) restar(pedido.dias);
      else if (r.status === 429) E.noAntes = Date.now() + ENVIO_MS;
      // silencio: cualquier otra respuesta (403 en local, 5xx) deja lo pendiente como está
    }, function () { /* silencio: red caída; se conserva y se reintenta en el siguiente envío */ }).then(function () { E.enviando = false; });
  }

  function idActivo() { var a = doc.querySelector("#destacado .d2c.on"); return a ? a.getAttribute("data-id") || "" : ""; }

  /** Un clic (o clic central) en un enlace del banner o de la barra fina. La barra cuenta solo «barra», nunca «metafy». */
  function alClic(e) {
    var enlace = e.target && e.target.closest ? e.target.closest("a") : null;
    if (!enlace || (e.type === "auxclick" && e.button !== 1)) return;
    if (enlace.closest("#d2barra")) { if (enlace.classList.contains("d2cta")) contar(idActivo(), "barra"); return; }
    var tarjeta = enlace.closest("#destacado .d2c[data-id]");
    if (!tarjeta) return;
    var id = tarjeta.getAttribute("data-id"), casilla = enlace.getAttribute("data-cas");
    if (enlace.classList.contains("d2cta")) contar(id, "metafy");
    else if (enlace.classList.contains("d2cas") && CASILLAS.indexOf(casilla) >= 0) contar(id, casilla);
  }

  // ---- «visto»: la tarjeta activa, visible al menos al 50 % y con la pestaña a la vista, durante 1 s seguido
  function cancelarVisto() { clearTimeout(E.temporizador); E.temporizador = 0; E.vigilando = ""; }
  function evaluarVisto() {
    var id = idActivo(), visible = id !== "" && E.razon[id] === true && doc.visibilityState === "visible";
    if (visible && E.vigilando === id) return;   // ya está en cuenta atrás (o ya contada en esta racha)
    cancelarVisto();
    if (!visible) return;
    E.vigilando = id;
    E.temporizador = setTimeout(function () {
      E.temporizador = 0;
      var ahora = Date.now();
      if (ahora - (E.ultimoVisto[id] || -Infinity) < VISTO_ENTRE_MS) return;   // como mucho una vista por minuto y creador
      E.ultimoVisto[id] = ahora;
      contar(id, "visto");
    }, VISTO_MS);
  }
  function vigilarVisto(banner) {
    if (typeof IntersectionObserver !== "function") return;   // sin él no se cuenta «visto» (mejor no contar que contar de más)
    var io = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) { E.razon[e.target.getAttribute("data-id")] = e.intersectionRatio >= 0.5; });
      evaluarVisto();
    }, { threshold: [0, 0.25, 0.5, 0.75, 1] });
    Array.prototype.forEach.call(banner.querySelectorAll(".d2c[data-id]"), function (t) { io.observe(t); });
    if (typeof MutationObserver === "function") new MutationObserver(evaluarVisto).observe(banner, { subtree: true, attributes: true, attributeFilter: ["class"] });
  }

  var banner = doc.getElementById("destacado");
  if (banner) vigilarVisto(banner);
  doc.addEventListener("click", alClic, true);
  doc.addEventListener("auxclick", alClic, true);
  doc.addEventListener("visibilitychange", function () { if (doc.visibilityState === "hidden") enviar(); evaluarVisto(); });
  global.addEventListener("pagehide", enviar);
  setInterval(enviar, ENVIO_MS);
})(typeof window !== "undefined" ? window : globalThis);
