/* Huecos de anuncio de MDN (ML-325, WEB-09). Lo carga con `defer` toda página que tiene algún hueco, junto al script de MDN.
   MDN pone su anuncio dentro de cada `.hm-caja[data-mdn]` y marca el hueco con `data-mdn-state` (rendered, empty...). La hoja de estilos ya enseña el
   anuncio de casa (el enlace a Learn) cuando el estado es `empty`. Aquí solo se cubre lo que MDN no puede decir por sí mismo: que su script no haya
   llegado (bloqueado, sin red) o que siga sin respuesta pasado el plazo. El plazo sale de `data-plazo` (milisegundos) de esta misma etiqueta. */
(function () {
  "use strict";
  var etiqueta = document.currentScript;
  var plazo = etiqueta ? parseInt(etiqueta.getAttribute("data-plazo"), 10) : NaN;
  if (!(plazo > 0)) return;

  // Estados en los que MDN sigue esperando respuesta. `waiting` no cuenta: es un hueco que aún no se ha acercado a la pantalla y todavía no ha pedido nada.
  var EN_CURSO = { loading: true, retrying: true };

  function sinRespuesta(caja) {
    var estado = caja.getAttribute("data-mdn-state");
    return estado === null || EN_CURSO[estado] === true;
  }

  setTimeout(function () {
    Array.prototype.forEach.call(document.querySelectorAll(".hueco-mdn"), function (hueco) {
      var caja = hueco.querySelector(".hm-caja");
      // Si luego MDN pinta su anuncio, su contenido tapa el de casa: el hueco no cambia de tamaño.
      if (caja && sinRespuesta(caja)) hueco.setAttribute("data-propio", "");
    });
  }, plazo);
})();
