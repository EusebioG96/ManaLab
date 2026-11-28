(function () {
  "use strict";
  // Menú móvil de la cabecera (<details class="menu">): se cierra con Esc (y el foco vuelve al botón) y al pulsar fuera.
  // Sin este archivo el menú sigue funcionando: se abre y se cierra con su botón y al elegir un enlace.
  function abierto() { return document.querySelector("details.menu[open]"); }

  document.addEventListener("keydown", function (e) {
    var menu = abierto();
    if (e.key !== "Escape" || !menu) return;
    menu.removeAttribute("open");
    var boton = menu.querySelector("summary");
    if (boton) boton.focus();   // sin esto el foco se queda en un enlace que ya no se ve
  });

  document.addEventListener("click", function (e) {
    var menu = abierto();
    if (menu && !menu.contains(e.target)) menu.removeAttribute("open");   // el foco se queda donde el usuario ha pulsado
  });
})();
