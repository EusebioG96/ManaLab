(function () {
  "use strict";
  var f = document.getElementById("form-contacto");
  if (!f) return;
  var estado = document.getElementById("contacto-estado");
  var boton = document.getElementById("contacto-enviar");
  var WORKER = "https://registro-ia.eusebiog76.workers.dev/contacto";
  f.addEventListener("submit", async function (e) {
    e.preventDefault();
    var en = document.documentElement.lang === "en";
    var d = new FormData(f);
    var datos = { nombre: d.get("nombre"), correo: d.get("correo"), tipo: d.get("tipo"), mensaje: d.get("mensaje"), web: d.get("web") };
    boton.disabled = true;
    estado.style.color = "";
    estado.textContent = en ? "Sending…" : "Enviando…";
    try {
      var r = await fetch(WORKER, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos) });
      var j = await r.json().catch(function () { return {}; });
      if (r.ok && j.ok) {
        f.reset();
        estado.textContent = en ? "Thanks! We'll reply by email." : "¡Gracias! Te responderemos por correo.";
      } else {
        throw new Error("rechazado");
      }
    } catch (err) {
      estado.style.color = "#ff9b9b";
      estado.textContent = en
        ? "It could not be sent. Try again later or write to manalab.app@gmail.com."
        : "No se pudo enviar. Inténtalo más tarde o escribe a manalab.app@gmail.com.";
    } finally {
      boton.disabled = false;
    }
  });
})();
