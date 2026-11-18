/* ManaLab · página «Learn» (ML-324, WEB-08). Script clásico, sin dependencias.
 *
 * La página ya trae en el HTML la primera página de guías (24, «Más compradas») y el creador destacado: así las ve Google. Este script:
 *   1. pide la lista completa al servidor (https://registro-ia.eusebiog76.workers.dev/guias.json); si falla o no vale, usa la copia /learn/guias.json;
 *      si también falla, deja lo que trae el HTML;
 *   2. la VALIDA con las mismas reglas que la app (espejo de manalab_aprender_validar.py y de servidor_ia/guias.js; tools/guias_web.py es el espejo en
 *      Python y tools/test_pagina_learn_validacion.py comprueba que deciden lo mismo);
 *   3. maneja los filtros (tipo, creador, orden, búsqueda), la paginación de 24 con ?p=N y el contador;
 *   4. rota el creador destacado cada 8 s y enseña la barra fina cuando el banner ya no se ve.
 * Todo lo que viene de la red se inserta con esc() (nunca como HTML sin escapar); las portadas son perezosas y sin referrer.
 * También se puede cargar en Node (módulo CommonJS) para probar las funciones puras. */
(function (global) {
  "use strict";

  // ---------------------------------------------------------------- reglas de validación (las mismas que tools/guias_web.py)
  var MAX_ENLACE = 300, MAX_GUIAS = 2000, MAX_BYTES = 2 * 1024 * 1024, MAX_TITULO = 140, MAX_DESCRIPCION = 600, MAX_NOMBRE = 60, MAX_AUTORES = 5;
  var MAX_CANTIDAD = 10000000, MAX_MINUTOS = 100000, MAX_FECHA = 40, ESQUEMA = 1, MONEDA = "USD";
  var DOMINIOS_METAFY = ["metafy.gg"], HOSTS_PORTADAS = ["metafy.gg"];
  var PROHIBIDOS_ENLACE = /["'<>\\\s\u0000-\u001f\u007f]/;   // rompen un atributo HTML o los reinterpreta el navegador
  var INVALIDOS_TEXTO = /[\p{Cc}\p{Cf}\p{Zl}\p{Zp}\p{Cs}\p{Co}\p{Cn}]/u;   // control, invisibles, separadores, sustitutos, privados y sin asignar
  var RESENAS_MIN = 3, POR_PAGINA_DEFECTO = 24;

  function largo(texto) { return Array.from(texto).length; }   // caracteres reales, como len() en Python

  function enlaceHttps(enlace, dominios) {
    if (typeof enlace !== "string" || enlace.indexOf("https://") !== 0 || !/^[\x00-\x7f]+$/.test(enlace)) return false;
    if (enlace.length === 0 || enlace.length > MAX_ENLACE || PROHIBIDOS_ENLACE.test(enlace)) return false;
    var autoridad = enlace.slice(8).split(/[/?#]/, 1)[0];
    if (autoridad.indexOf("@") !== -1 || autoridad.indexOf(":") !== -1) return false;   // usuario, contraseña o puerto
    var host = autoridad.toLowerCase();
    if (!/^[a-z0-9.-]+$/.test(host) || host.split(".").indexOf("") !== -1) return false;
    return dominios.some(function (d) { return host === d || host.slice(-(d.length + 1)) === "." + d; });
  }

  function textoValido(valor, maximo, variasLineas) {
    if (typeof valor !== "string" || largo(valor) > maximo || valor.trim() === "") return false;
    return !INVALIDOS_TEXTO.test(variasLineas ? valor.replace(/[\n\t]/g, "") : valor);
  }

  function entero(valor, maximo) { return typeof valor === "number" && Number.isInteger(valor) && valor >= 0 && valor <= maximo; }
  function vacio(valor) { return valor === undefined || valor === null || valor === ""; }
  function esObjeto(valor) { return valor !== null && typeof valor === "object" && !Array.isArray(valor); }
  function tiene(objeto, campo) { return Object.prototype.hasOwnProperty.call(objeto, campo); }

  function autoresValidos(crudo) {
    if (!Array.isArray(crudo) || crudo.length > MAX_AUTORES) throw new Error("autores");
    return crudo.map(function (autor) {
      if (!esObjeto(autor) || !textoValido(autor.name, MAX_NOMBRE)) throw new Error("autor");
      return { name: autor.name.trim() };
    });
  }
  function precioValido(crudo) {
    if (crudo === undefined || crudo === null) return null;
    if (!esObjeto(crudo) || crudo.currency !== MONEDA || !entero(crudo.value_in_cents, MAX_CANTIDAD)) throw new Error("precio");
    return { value_in_cents: crudo.value_in_cents, currency: MONEDA };
  }
  function valoracionValida(crudo) {
    if (crudo === undefined || crudo === null) return null;
    if (typeof crudo !== "number" || !(crudo >= 1 && crudo <= 10)) throw new Error("valoracion");   // la comparación rechaza NaN
    return crudo;
  }
  function cantidad(guia, campo, maximo, porDefecto) {
    var valor = guia[campo];
    if (valor === undefined || valor === null) return porDefecto;
    if (!entero(valor, maximo)) throw new Error(campo);
    return valor;
  }

  /** Una guía normalizada con todos sus campos; lanza Error si algo no cuadra (esa guía se descarta). */
  function validarGuia(g) {
    if (!esObjeto(g)) throw new Error("no es un objeto");
    if (!textoValido(g.name, MAX_TITULO) || !enlaceHttps(g.url, DOMINIOS_METAFY)) throw new Error("título o enlace");
    var descripcion = vacio(g.description) ? null : g.description;
    if (descripcion !== null && !textoValido(descripcion, MAX_DESCRIPCION, true)) throw new Error("descripción");
    var portada = vacio(g.cover_url) ? null : g.cover_url;
    if (portada !== null && !enlaceHttps(portada, HOSTS_PORTADAS)) portada = null;   // portada mala: la guía sale sin portada
    var solo = tiene(g, "subscriber_only") ? g.subscriber_only : false;
    if (typeof solo !== "boolean") throw new Error("subscriber_only");
    return { name: g.name.trim(), description: (descripcion || "").trim(), url: g.url, cover_url: portada || "", price: precioValido(g.price),
      subscriber_only: solo, authors: autoresValidos(tiene(g, "authors") ? g.authors : []), average_rating: valoracionValida(g.average_rating),
      review_count: cantidad(g, "review_count", MAX_CANTIDAD, 0), total_reading_time_minutes: cantidad(g, "total_reading_time_minutes", MAX_MINUTOS, null),
      purchase_count: cantidad(g, "purchase_count", MAX_CANTIDAD, 0) };
  }

  /** La lista {v, actualizada, guias} con solo las guías válidas (sin repetir url, MAX_GUIAS como mucho); lanza Error si el encabezado no cuadra. */
  function validarLista(datos) {
    if (!esObjeto(datos) || datos.v !== ESQUEMA) throw new Error("esquema no soportado");
    if (typeof datos.actualizada !== "string" || datos.actualizada.length > MAX_FECHA || isNaN(Date.parse(datos.actualizada))) throw new Error("fecha no válida");
    if (!Array.isArray(datos.guias)) throw new Error("guias no es una lista");
    var guias = [], vistas = {};
    datos.guias.slice(0, MAX_GUIAS).forEach(function (cruda) {
      var guia;
      try { guia = validarGuia(cruda); } catch (e) { return; }   // una guía mala no tumba la lista
      if (!Object.prototype.hasOwnProperty.call(vistas, guia.url)) { vistas[guia.url] = true; guias.push(guia); }
    });
    return { v: ESQUEMA, actualizada: datos.actualizada, guias: guias };
  }

  // ---------------------------------------------------------------- orden, filtros y formato (los mismos que tools/construir_learn.py)
  function esc(texto) {
    return String(texto).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" }[c]; });
  }
  function plano(texto) { return texto.normalize("NFD").replace(/\p{Mn}/gu, "").toLowerCase(); }   // sin acentos y en minúsculas
  function comparar(a, b) { return a < b ? -1 : a > b ? 1 : 0; }   // orden de unidades UTF-16, como bytes UTF-16BE en Python
  function compras(a, b) {
    return (b.purchase_count - a.purchase_count) || comparar(plano(a.name), plano(b.name)) || comparar(a.url, b.url);
  }
  function ordenarCompradas(guias) { return guias.slice().sort(compras); }
  function esGratis(g) { return !g.subscriber_only && !(g.price && g.price.value_in_cents); }
  function valorada(g) { return g.review_count >= RESENAS_MIN && g.average_rating !== null; }
  var ORDENES = {
    compradas: compras,
    valoradas: function (a, b) {
      return (valorada(b) - valorada(a)) || (valorada(a) ? (b.average_rating - a.average_rating || b.review_count - a.review_count) : 0) || compras(a, b);
    },
    cortas: function (a, b) {
      var x = a.total_reading_time_minutes === null ? Infinity : a.total_reading_time_minutes, y = b.total_reading_time_minutes === null ? Infinity : b.total_reading_time_minutes;
      return ((x - y) || 0) || compras(a, b);
    }
  };
  /** Las guías que pasan los filtros {tipo, creador, busqueda}, en el orden `orden`. */
  function filtrar(guias, f, orden) {
    var buscar = plano((f.busqueda || "").trim());
    var tipo = f.tipo || "todas";
    var pasan = guias.filter(function (g) {
      var deTipo = tipo === "todas" || (tipo === "gratis" && esGratis(g)) || (tipo === "pago" && !g.subscriber_only && !!(g.price && g.price.value_in_cents)) ||
        (tipo === "suscriptores" && g.subscriber_only);
      var autores = g.authors.map(function (a) { return a.name; });
      return deTipo && (!f.creador || autores.indexOf(f.creador) !== -1) &&
        (!buscar || plano(g.name + " " + g.description + " " + autores.join(" ")).indexOf(buscar) !== -1);
    });
    return pasan.sort(ORDENES[orden] || compras);
  }

  function reemplazarN(texto, n) { return texto.replace("{n}", String(n)); }
  function unoOVarios(textos, n) { return n === 1 ? textos[0] : reemplazarN(textos[1], n); }
  function formatearPrecio(centimos, t) {
    var numero = centimos % 100 === 0 ? String(Math.floor(centimos / 100)) : Math.floor(centimos / 100) + t.decimal + ("0" + (centimos % 100)).slice(-2);
    return t.precio.replace("{n}", numero);
  }
  function formatearValoracion(valor, t) {
    var decimas = Math.floor(valor * 10 + 0.5);   // la misma aritmética que Python (toFixed no coincide en los empates)
    return Math.floor(decimas / 10) + t.decimal + (decimas % 10);
  }
  function paginasVisibles(actual, total) {
    var conjunto = {};
    [1, total, actual - 1, actual, actual + 1].forEach(function (n) { conjunto[n] = true; });
    if (actual <= 2) { conjunto[2] = true; conjunto[3] = true; }
    if (actual >= total - 1) { conjunto[total - 2] = true; conjunto[total - 1] = true; }
    var orden = Object.keys(conjunto).map(Number).filter(function (n) { return n >= 1 && n <= total; }).sort(function (a, b) { return a - b; });
    var salida = [], previo = null;
    orden.forEach(function (n) {
      if (previo !== null && n - previo === 2) salida.push(previo + 1);
      else if (previo !== null && n - previo > 2) salida.push(null);
      salida.push(n);
      previo = n;
    });
    return salida;
  }

  // ---------------------------------------------------------------- HTML (idéntico, carácter a carácter tras el análisis del navegador, al de construir_learn.py)
  var LIBRO = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5C6.5 4.5 9.5 4.5 12 6c2.5-1.5 5.5-1.5 8-.5v13c-2.5-1-5.5-1-8 .5-2.5-1.5-5.5-1.5-8-.5zM12 6v13"/></svg>';
  function htmlPrecio(g, t) {
    if (g.subscriber_only) return '<span class="precio sus">' + esc(t.sus) + "</span>";
    if (esGratis(g)) return '<span class="precio gratis">' + esc(t.gratis) + "</span>";
    return '<span class="precio">' + esc(formatearPrecio(g.price.value_in_cents, t)) + "</span>";
  }
  function htmlDatos(g, t) {
    var valor = "";
    if (g.review_count >= RESENAS_MIN && g.average_rating !== null) valor = "<b>" + formatearValoracion(g.average_rating, t) + "</b>";
    if (g.review_count > 0) { var r = esc(unoOVarios(t.res, g.review_count)); valor = valor ? valor + " · " + r : r; }
    var partes = valor ? ["<span>" + valor + "</span>"] : [];
    if (g.total_reading_time_minutes !== null) partes.push("<span>" + esc(reemplazarN(t.min, g.total_reading_time_minutes)) + "</span>");
    return partes.join("");
  }
  function htmlTarjeta(g, t) {
    var imagen = g.cover_url ? '<img alt="" decoding="async" loading="lazy" referrerpolicy="no-referrer" src="' + esc(g.cover_url) + '">' : "";
    var autores = g.authors.map(function (a) { return a.name; }).join(", ");
    var de = autores ? '<div class="a">' + esc(t.de.replace("{}", autores)) + "</div>" : "";
    return '<a class="guia" href="' + esc(g.url) + '" rel="noopener" target="_blank"><div class="port c0">' + LIBRO + imagen + htmlPrecio(g, t) + "</div>" +
      '<div class="cu"><div class="t">' + esc(g.name) + "</div>" + de + '<div class="m">' + htmlDatos(g, t) + "</div></div></a>";
  }
  function htmlPaginador(actual, total, t) {
    if (total <= 1) return "";
    function direccion(n) { return n === 1 ? "./" : "?p=" + n; }
    function flecha(n, signo, etiqueta) {
      if (n < 1 || n > total) return '<span class="apagado" aria-hidden="true">' + signo + "</span>";
      return '<a href="' + direccion(n) + '" aria-label="' + esc(etiqueta) + '" data-p="' + n + '">' + signo + "</a>";
    }
    var cuerpo = paginasVisibles(actual, total).map(function (n) {
      return n === null ? '<span aria-hidden="true">…</span>' : '<a href="' + direccion(n) + '" data-p="' + n + '"' + (n === actual ? ' aria-current="page"' : "") + ">" + n + "</a>";
    }).join("");
    return '<nav class="ap-pag" id="ap-pag" aria-label="' + esc(t.paginas) + '">' + flecha(actual - 1, "‹", t.ant) + cuerpo + flecha(actual + 1, "›", t.sig) + "</nav>";
  }
  function htmlCajaVacia(t) {
    return '<div class="ap-caja"><b>' + esc(t.vacio[0]) + "</b><span>" + esc(t.vacio[1]) + '</span><a class="boton prim" href="#descargar">' + esc(t.bajar) + "</a></div>";
  }
  function htmlCajaSinCoincidencias(t) {
    return '<div class="ap-caja"><b>' + esc(t.ninguna[0]) + '</b><button type="button" data-ap="limpiar">' + esc(t.ninguna[1]) + "</button></div>";
  }
  function htmlRejilla(pagina, t) { return pagina.map(function (g) { return htmlTarjeta(g, t); }).join(""); }

  var API = { validarLista: validarLista, validarGuia: validarGuia, enlaceHttps: enlaceHttps, textoValido: textoValido, ordenarCompradas: ordenarCompradas,
    filtrar: filtrar, paginasVisibles: paginasVisibles, htmlTarjeta: htmlTarjeta, htmlRejilla: htmlRejilla, htmlPaginador: htmlPaginador,
    formatearPrecio: formatearPrecio, formatearValoracion: formatearValoracion, plano: plano };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  if (typeof document === "undefined") return;
  global.ManaLabLearn = API;

  // ---------------------------------------------------------------- la página
  var doc = document, datos;
  try { datos = JSON.parse(doc.getElementById("learn-datos").textContent); } catch (e) { return; }
  var t = datos.t, POR_PAGINA = datos.porPagina || POR_PAGINA_DEFECTO;
  var reducir = global.matchMedia("(prefers-reduced-motion: reduce)");
  var $ = function (id) { return doc.getElementById(id); };

  // Una imagen de fuera (portada, foto, fondo) que no carga se quita y queda lo de debajo (el icono o las iniciales).
  function quitarRotas(raiz) {
    Array.prototype.forEach.call(raiz.querySelectorAll("img"), function (img) { if (img.complete && img.naturalWidth === 0 && img.getAttribute("src")) img.remove(); });
  }
  doc.addEventListener("error", function (e) { if (e.target && e.target.tagName === "IMG" && e.target.closest(".guia, .d2, .d2barra")) e.target.remove(); }, true);

  // ---- guías, filtros y paginación
  var estado = { guias: null, tipo: "todas", creador: "", orden: "compradas", busqueda: "", pagina: 1 };
  var rejilla = $("guias"), barra = $("ap-barra"), cuenta = $("ap-cuenta");
  // Hueco de anuncio de MDN de la rejilla (WEB-09): sale tras la octava guía y solo si hay alguna más después. Es el mismo nodo siempre (se
  // aparta mientras se repinta y se vuelve a poner), para que MDN no pida un anuncio nuevo con cada filtro o cada página.
  var GUIAS_ANTES_DEL_HUECO = 8;
  var huecoRejilla = rejilla.querySelector(".hueco-mdn");
  function huecoNuevo() {
    var otro = doc.querySelector(".hueco-mdn:not(.suelto)");   // el de debajo del paginador: se copia sin lo que MDN le puso
    if (!otro) return null;
    var copia = otro.cloneNode(true);
    copia.classList.add("suelto"); copia.removeAttribute("data-propio");
    var caja = copia.querySelector(".hm-caja");
    if (caja) { caja.removeAttribute("data-mdn-state"); caja.removeAttribute("style"); }
    return copia;
  }
  function apartarHueco() { if (huecoRejilla && huecoRejilla.parentNode) huecoRejilla.remove(); }
  function ponerHueco() {
    var tarjetas = rejilla.querySelectorAll(":scope > a.guia");
    if (tarjetas.length <= GUIAS_ANTES_DEL_HUECO) return;
    if (!huecoRejilla) huecoRejilla = huecoNuevo();
    if (huecoRejilla) tarjetas[GUIAS_ANTES_DEL_HUECO - 1].after(huecoRejilla);
  }

  function paginaDeLaUrl() { var p = parseInt(new URLSearchParams(global.location.search).get("p"), 10); return p >= 1 ? p : 1; }
  function igual(elemento, html) {
    var tmp = doc.createElement("template"); tmp.innerHTML = html;
    return tmp.innerHTML === elemento.innerHTML;
  }
  function poner(elemento, html) { if (!igual(elemento, html)) { elemento.innerHTML = html; quitarRotas(elemento); } }

  function rellenarCreadores() {
    var nombres = {};
    estado.guias.forEach(function (g) { g.authors.forEach(function (a) { nombres[a.name] = true; }); });
    var lista = Object.keys(nombres).sort(function (a, b) { return a.localeCompare(b, datos.idioma); });
    if (estado.creador && !nombres[estado.creador]) estado.creador = "";
    $("ap-creador").innerHTML = '<option value="">' + esc(t.creador) + "</option>" +
      lista.map(function (n) { return '<option value="' + esc(n) + '"' + (n === estado.creador ? " selected" : "") + ">" + esc(n) + "</option>"; }).join("");
  }

  function pintar() {
    var visibles = filtrar(estado.guias, estado, estado.orden);
    var total = Math.max(1, Math.ceil(visibles.length / POR_PAGINA));
    estado.pagina = Math.min(Math.max(estado.pagina, 1), total);
    var pagina = visibles.slice((estado.pagina - 1) * POR_PAGINA, estado.pagina * POR_PAGINA);
    var vacia = estado.guias.length === 0;
    barra.hidden = vacia;
    rejilla.classList.toggle("vacia", vacia || visibles.length === 0);
    apartarHueco();
    poner(rejilla, vacia ? htmlCajaVacia(t) : visibles.length === 0 ? htmlCajaSinCoincidencias(t) : htmlRejilla(pagina, t));
    ponerHueco();
    cuenta.textContent = unoOVarios(t.cuenta, visibles.length);
    var nav = $("ap-pag"), html = vacia || visibles.length === 0 ? "" : htmlPaginador(estado.pagina, total, t);
    if (!html) { if (nav) nav.remove(); return; }
    if (!nav) { rejilla.insertAdjacentHTML("afterend", html); return; }
    var tmp = doc.createElement("div"); tmp.innerHTML = html;
    if (tmp.firstChild.outerHTML !== nav.outerHTML) nav.replaceWith(tmp.firstChild);
  }

  function irAPagina(n, empujar) {
    estado.pagina = n;
    pintar();
    if (empujar) global.history.pushState({ p: estado.pagina }, "", estado.pagina === 1 ? global.location.pathname : "?p=" + estado.pagina);
  }
  function cambiarFiltro() { estado.pagina = 1; if (paginaDeLaUrl() !== 1) global.history.pushState({ p: 1 }, "", global.location.pathname); pintar(); }

  function activarFiltros() {
    rellenarCreadores();
    barra.addEventListener("click", function (e) {
      var boton = e.target.closest("button[data-tipo]");
      if (!boton) return;
      estado.tipo = boton.getAttribute("data-tipo");
      Array.prototype.forEach.call(barra.querySelectorAll("button[data-tipo]"), function (b) { b.setAttribute("aria-pressed", b === boton ? "true" : "false"); });
      cambiarFiltro();
    });
    $("ap-creador").addEventListener("change", function (e) { estado.creador = e.target.value; cambiarFiltro(); });
    $("ap-orden").addEventListener("change", function (e) { estado.orden = e.target.value; cambiarFiltro(); });
    $("ap-buscar").addEventListener("input", function (e) { estado.busqueda = e.target.value; cambiarFiltro(); });
    doc.getElementById("guias-seccion").addEventListener("click", function (e) {
      var enlace = e.target.closest("#ap-pag a[data-p]"), limpiar = e.target.closest("button[data-ap='limpiar']");
      if (limpiar) { limpiarFiltros(); return; }
      if (!enlace || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;   // abrir en otra pestaña funciona con el href (?p=N)
      e.preventDefault();
      irAPagina(parseInt(enlace.getAttribute("data-p"), 10), true);
      barra.scrollIntoView({ block: "start", behavior: reducir.matches ? "auto" : "smooth" });
    });
    global.addEventListener("popstate", function () { estado.pagina = paginaDeLaUrl(); pintar(); });
  }
  function limpiarFiltros() {
    estado.tipo = "todas"; estado.creador = ""; estado.busqueda = ""; estado.orden = "compradas";
    Array.prototype.forEach.call(barra.querySelectorAll("button[data-tipo]"), function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-tipo") === "todas" ? "true" : "false"); });
    $("ap-creador").value = ""; $("ap-orden").value = "compradas"; $("ap-buscar").value = "";
    cambiarFiltro();
  }

  // ---- la lista: servidor, copia y, si nada responde, el HTML tal cual
  function pedir(url) {
    var control = typeof AbortController === "function" ? new AbortController() : null;
    var plazo = control ? setTimeout(function () { control.abort(); }, 8000) : null;
    // petición simple (sin cabeceras propias, sin cookies ni referrer): el servidor solo responde con permiso CORS a https://manalab.es
    return fetch(url, { credentials: "omit", referrerPolicy: "no-referrer", signal: control ? control.signal : undefined }).then(function (r) {
      if (plazo) clearTimeout(plazo);
      if (!r.ok) throw new Error("http " + r.status);
      return r.text();
    }).then(function (texto) {
      if (texto.length > MAX_BYTES) throw new Error("demasiado grande");
      return validarLista(JSON.parse(texto));
    });
  }
  /** La primera lista con al menos una guía válida de [servidor, copia]; una lista válida pero vacía vale si ninguna otra tiene guías; null si ninguna responde. */
  function cargarLista() {
    var vacia = null;
    function probar(i) {
      var urls = [datos.servidor, datos.copia];
      if (i >= urls.length) return Promise.resolve(vacia);
      return pedir(urls[i]).then(function (lista) {
        if (lista.guias.length > 0) return lista;
        vacia = lista;
        return probar(i + 1);
      }, function () { return probar(i + 1); });
    }
    return probar(0);
  }

  function iniciarGuias() {
    quitarRotas(rejilla);
    cargarLista().then(function (lista) {
      if (!lista) { doc.documentElement.classList.add("learn-sin-lista"); barra.hidden = true; return; }   // nada responde: queda el HTML
      estado.guias = lista.guias;
      estado.pagina = paginaDeLaUrl();
      activarFiltros();
      doc.documentElement.classList.add("learn-js");
      pintar();
    });
  }

  // ---- creador destacado: rotación y barra fina (VIS-22 y VIS-23)
  function iniciarDestacados() {
    var d2 = $("destacado"), fina = $("d2barra");
    if (!d2 || !fina) return;
    var cuerpos = Array.prototype.slice.call(d2.querySelectorAll(".d2c")), n = cuerpos.length;
    var puntos = d2.querySelectorAll(".d2pun i"), etiquetaPuntos = d2.querySelector(".d2pun"), progreso = d2.querySelector(".d2prog i"), anuncio = d2.querySelector(".d2anuncio");
    var s = { indice: 0, ms: 0, encima: false, dentro: false, manual: false, barra: false, ventana: !doc.hidden, anunciando: 0 };
    var PASO = 100;

    function mostrar(i) {
      s.indice = (i + n) % n; s.ms = 0;
      cuerpos.forEach(function (c, k) {
        var activo = k === s.indice;
        c.classList.toggle("on", activo);
        if (activo) { c.removeAttribute("inert"); c.removeAttribute("aria-hidden"); } else { c.setAttribute("inert", ""); c.setAttribute("aria-hidden", "true"); }
      });
      Array.prototype.forEach.call(puntos, function (p, k) { p.classList.toggle("on", k === s.indice); });
      if (etiquetaPuntos) etiquetaPuntos.setAttribute("aria-label", (s.indice + 1) + " / " + n);
      if (progreso) progreso.style.transform = "scaleX(0)";
    }
    function anunciar() {   // el cambio a mano se anuncia a los lectores de pantalla; el automático, nunca
      if (!anuncio) return;
      anuncio.textContent = cuerpos[s.indice].querySelector(".d2nom").textContent + ", " + (s.indice + 1) + " / " + n;
      clearTimeout(s.anunciando);
      s.anunciando = setTimeout(function () { anuncio.textContent = ""; }, 1500);
    }
    function puedeRotar() { return n > 1 && !reducir.matches && !s.encima && !s.dentro && !s.manual && !s.barra && s.ventana && !doc.hidden; }
    function latido() {
      if (!puedeRotar()) return;
      s.ms += PASO;
      if (progreso) progreso.style.transform = "scaleX(" + Math.min(s.ms / datos.rotarMs, 1) + ")";
      if (s.ms >= datos.rotarMs) mostrar(s.indice + 1);
    }
    if (n > 1) {
      setInterval(latido, PASO);
      d2.addEventListener("mouseenter", function () { s.encima = true; });
      d2.addEventListener("mouseleave", function () { s.encima = false; });
      d2.addEventListener("focusin", function () { s.dentro = true; });
      d2.addEventListener("focusout", function (e) { if (!d2.contains(e.relatedTarget)) s.dentro = false; });
      global.addEventListener("blur", function () { s.ventana = false; });
      global.addEventListener("focus", function () { s.ventana = true; });
      doc.addEventListener("visibilitychange", function () { s.ventana = !doc.hidden; });
      d2.addEventListener("click", function (e) {
        var flecha = e.target.closest("button[data-d2]");
        if (!flecha) return;
        s.manual = true;   // deja de rotar hasta que el banner vuelva a entrar en la pantalla
        mostrar(s.indice + parseInt(flecha.getAttribute("data-d2"), 10));
        anunciar();
      });
    }

    // La barra fina: sale cuando el banner se ha ido entero por arriba (bajo la cabecera fija) y se va en cuanto vuelve a verse una parte.
    var cabecera = doc.querySelector(".cab");
    function ponerBarra(visible) {
      if (visible === s.barra) return;
      s.barra = visible;
      if (visible) {
        var c = cuerpos[s.indice];
        fina.querySelector(".n").textContent = c.querySelector(".d2nom").textContent;
        fina.querySelector(".d2cta").setAttribute("href", c.querySelector(".d2cta").getAttribute("href"));
        var f = fina.querySelector(".f"), foto = c.querySelector(".d2foto img");
        f.querySelectorAll("img").forEach(function (i) { i.remove(); });
        f.querySelector(".ini").textContent = c.querySelector(".d2foto .ini").textContent;
        if (foto) { var copia = foto.cloneNode(false); f.appendChild(copia); }
        fina.removeAttribute("inert"); fina.removeAttribute("aria-hidden"); fina.classList.add("visible");
      } else {
        fina.setAttribute("inert", ""); fina.setAttribute("aria-hidden", "true"); fina.classList.remove("visible");
        s.ms = 0; s.manual = false;   // la rotación sigue con el reloj a cero
      }
    }
    var observador = null;
    function observar() {
      var alto = cabecera ? Math.round(cabecera.getBoundingClientRect().height) : 69;
      doc.documentElement.style.setProperty("--alto-cab", alto + "px");
      if (observador) observador.disconnect();
      if (typeof IntersectionObserver !== "function") return;
      observador = new IntersectionObserver(function (entradas) {
        var e = entradas[entradas.length - 1];
        ponerBarra(!e.isIntersecting && e.boundingClientRect.bottom <= (e.rootBounds ? e.rootBounds.top : alto));
      }, { rootMargin: "-" + alto + "px 0px 0px 0px", threshold: [0] });
      observador.observe(d2);
    }
    observar();
    if (typeof ResizeObserver === "function" && cabecera) { var anterior = cabecera.getBoundingClientRect().height; new ResizeObserver(function () { var h = cabecera.getBoundingClientRect().height; if (h !== anterior) { anterior = h; observar(); } }).observe(cabecera); }
    quitarRotas(d2); quitarRotas(fina);
  }

  iniciarDestacados();
  iniciarGuias();
})(typeof window !== "undefined" ? window : globalThis);
