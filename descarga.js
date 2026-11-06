(function () {
  "use strict";
  // 1) Mantiene al día el enlace directo al ZIP y la versión leyendo /version.json. Si algo falla, queda el href estático del HTML.
  // 2) En teléfono (pantalla estrecha Y táctil, sin mirar el agente de usuario) cambia el bloque de descarga por «Envíate el enlace».
  var BASE = "https://github.com/EusebioG96/ManaLab/releases/download/";
  var ultima = null;   // {u, v} ya validados, para aplicarlos también a lo que se inserte después

  function aplicar(raiz) {
    if (!ultima) return;
    var a = raiz.querySelectorAll("a[data-descarga]");
    for (var i = 0; i < a.length; i++) a[i].setAttribute("href", ultima.u);
    var t = raiz.querySelectorAll("[data-version]");
    for (var j = 0; j < t.length; j++) t[j].textContent = ultima.v;
  }

  try {
    fetch("/version.json", { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error("http");
      return r.json();
    }).then(function (d) {
      var v = d && typeof d.version === "string" ? d.version : "";
      var u = d && typeof d.descarga === "string" ? d.descarga : "";
      var ok = /^\d{1,4}\.\d{1,5}\.\d{1,6}$/.test(v) && d.tag === "v" + v &&
        u === BASE + "v" + v + "/ManaLab-" + v + "-portable.zip";
      if (!ok) return;
      ultima = { u: u, v: v };
      aplicar(document);
    }).catch(function () {});
  } catch (e) {}

  /* ---------------- teléfono */
  function contar(ruta, titulo) {
    try {
      var g = window.goatcounter;
      if (g && typeof g.count === "function") g.count({ event: true, path: ruta, title: titulo });
    } catch (e) {}
  }

  function copiar(texto) {
    return new Promise(function (ok, mal) {
      function viejo() {
        try {
          var t = document.createElement("textarea");
          t.value = texto; t.setAttribute("readonly", ""); t.style.cssText = "position:fixed;top:0;left:0;opacity:0";
          document.body.appendChild(t); t.select(); t.setSelectionRange(0, texto.length);
          var r = document.execCommand("copy");
          document.body.removeChild(t);
          if (r) ok(); else mal(new Error("copy"));
        } catch (e) { mal(e); }
      }
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(texto).then(ok, viejo);
        else viejo();
      } catch (e) { viejo(); }
    });
  }

  function montar(caja) {
    var boton = caja.querySelector("[data-compartir]"), estado = caja.querySelector(".movil-estado");
    var zip = caja.querySelector(".movil-zip a"), temporizador = null;
    function decir(texto) {
      estado.textContent = texto;
      clearTimeout(temporizador);
      temporizador = setTimeout(function () { estado.textContent = ""; }, 5000);
    }
    function copiado() {
      var url = boton.getAttribute("data-url");
      copiar(url).then(function () { decir(boton.getAttribute("data-copiado")); }, function () { decir(url); });
    }
    boton.addEventListener("click", function () {
      contar("compartir-movil", boton.getAttribute("data-titulo"));
      var url = boton.getAttribute("data-url"), p;
      try { p = navigator.share ? navigator.share({ title: "ManaLab", url: url }) : null; } catch (e) { p = Promise.reject(e); }
      if (!p) { copiado(); return; }
      // cancelar el menú de compartir (AbortError) no es un error: ni se copia ni se avisa
      p.then(function () {}, function (e) { if (!e || e.name !== "AbortError") copiado(); });
    });
    zip.addEventListener("click", function () { contar("descarga-movil", zip.getAttribute("data-titulo")); });
  }

  var enlace = document.getElementById("enlace-descarga"), plantilla = document.getElementById("bloque-movil");
  var ancla = document.getElementById("descargar");
  var avisos = document.querySelectorAll("a[data-a-bloque]");
  var caja = null;

  function modo(movil) {
    if (!enlace || !plantilla) return;
    var p = enlace.parentNode;
    if (movil && !caja) {
      caja = plantilla.content.firstElementChild.cloneNode(true);
      p.parentNode.insertBefore(caja, p.nextSibling);
      p.hidden = true;
      // el ancla #descargar pasa al bloque para que el botón «Descargar» deje a la vista justo lo que importa
      if (ancla && ancla.id === "descargar") { ancla.removeAttribute("id"); caja.id = "descargar"; }
      aplicar(caja);
      montar(caja);
      // el aviso superior lleva al bloque en lugar de bajar el ZIP
      for (var i = 0; i < avisos.length; i++) {
        var a = avisos[i];
        a.setAttribute("data-original", a.getAttribute("href"));
        a.setAttribute("href", "#descargar");
        a.removeAttribute("download"); a.removeAttribute("data-descarga"); a.removeAttribute("data-goatcounter-click");
      }
    } else if (!movil && caja) {
      if (caja.id === "descargar" && ancla) { caja.removeAttribute("id"); ancla.id = "descargar"; }
      caja.parentNode.removeChild(caja); caja = null;
      p.hidden = false;
      for (var j = 0; j < avisos.length; j++) {
        var b = avisos[j];
        b.setAttribute("href", b.getAttribute("data-original")); b.removeAttribute("data-original");
        b.setAttribute("download", ""); b.setAttribute("data-descarga", ""); b.setAttribute("data-goatcounter-click", "descarga");
      }
      aplicar(document);
    }
  }

  try {
    if (window.matchMedia) {
      var mq = window.matchMedia("(max-width: 767px) and (pointer: coarse)");
      modo(mq.matches);
      if (mq.addEventListener) mq.addEventListener("change", function (e) { modo(e.matches); });
      else if (mq.addListener) mq.addListener(function (e) { modo(e.matches); });
    }
  } catch (e) {}
})();
