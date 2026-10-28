(function () {
  "use strict";
  // Mantiene al día el enlace directo al ZIP leyendo /version.json. Si algo falla, queda el href estático del HTML.
  var BASE = "https://github.com/EusebioG96/ManaLab/releases/download/";
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
      var a = document.querySelectorAll("a[data-descarga]");
      for (var i = 0; i < a.length; i++) a[i].setAttribute("href", u);
      var t = document.querySelectorAll("[data-version]");
      for (var j = 0; j < t.length; j++) t[j].textContent = v;
    }).catch(function () {});
  } catch (e) {}
})();
