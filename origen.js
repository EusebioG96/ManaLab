(function () {
  "use strict";
  // ML-379: añade el origen de la visita (campaña UTM o clase de referente) al nombre de los eventos de descarga de GoatCounter.
  // Es el único sitio que lo hace: descarga.js le pide el nombre (window.manalabOrigen.de) y los botones con data-goatcounter-click
  // lo reciben antes de que count.js los lea. Solo se guarda una palabra corta por pestaña; nada que identifique a nadie.
  var CLAVE = "manalab_origen";      // sessionStorage: origen de la primera página vista de la visita
  var MAX = 30;                      // largo máximo del origen dentro del nombre del evento
  var EVENTOS = /^(descarga|correo-movil|compartir-movil)-/;
  var SUFIJO = /-(utm-[a-z0-9_]+|ref-[a-z]+)$/;
  var DOMINIOS = [["x", /(^|\.)(t\.co|x\.com|twitter\.com)$/], ["google", /(^|\.)google\.[a-z.]+$/],
    ["metafy", /(^|\.)metafy\.gg$/], ["instagram", /(^|\.)instagram\.com$/]];
  var memoria = null;                // por si sessionStorage no se puede usar

  function normalizar(texto) {
    return String(texto || "").toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "").slice(0, MAX).replace(/_+$/, "");
  }

  function deLaUrl(busqueda) {
    try {
      var p = new URLSearchParams(busqueda);
      return normalizar(p.get("utm_campaign")) || normalizar(p.get("utm_source"));
    } catch (e) { return ""; }
  }

  function claseDelReferente(referente, anfitrion) {
    var host = "";
    try { host = referente ? new URL(referente).hostname.toLowerCase() : ""; } catch (e) { host = ""; }
    if (!host || host === anfitrion) return "directo";
    for (var i = 0; i < DOMINIOS.length; i++) if (DOMINIOS[i][1].test(host)) return DOMINIOS[i][0];
    return "otro";
  }

  /* «utm-<campaña>» si la dirección trae utm_campaign (o, si no, utm_source); si no, «ref-<clase>» según document.referrer */
  function calcular(busqueda, referente, anfitrion) {
    var utm = deLaUrl(busqueda);
    return utm ? "utm-" + utm : "ref-" + claseDelReferente(referente, anfitrion);
  }

  function origen() {
    try {
      var guardado = window.sessionStorage.getItem(CLAVE);
      if (guardado && /^(utm-[a-z0-9_]+|ref-[a-z]+)$/.test(guardado)) return guardado;
    } catch (e) { /* silencio: sin sessionStorage se usa la copia en memoria */ }
    if (memoria) return memoria;
    memoria = calcular(location.search, document.referrer, location.hostname.toLowerCase());
    try { window.sessionStorage.setItem(CLAVE, memoria); } catch (e) { /* silencio: queda en memoria */ }
    return memoria;
  }

  /* «descarga-portada-ja-hero» -> «descarga-portada-ja-hero-utm-x»; lo que no es de descarga o ya lleva origen se devuelve igual */
  function conOrigen(nombre) {
    if (typeof nombre !== "string" || !EVENTOS.test(nombre) || SUFIJO.test(nombre)) return nombre;
    return nombre + "-" + origen();
  }

  function marcar(e) {
    var el = e.target && e.target.closest ? e.target.closest("[data-goatcounter-click]") : null;
    if (!el) return;
    el.setAttribute("data-goatcounter-click", conOrigen(el.getAttribute("data-goatcounter-click")));
    if (el.hasAttribute("data-goatcounter-title")) el.setAttribute("data-goatcounter-title", conOrigen(el.getAttribute("data-goatcounter-title")));
  }

  origen();   // se fija con la primera página vista; las siguientes páginas de la visita lo reutilizan
  // en la fase de captura: corre antes que los oyentes de count.js, que leen el atributo al hacer clic
  document.addEventListener("click", marcar, true);
  document.addEventListener("auxclick", marcar, true);
  window.manalabOrigen = { de: conOrigen, calcular: calcular };
})();
