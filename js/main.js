(function () {
  var stage = document.getElementById("stage");
  var grid = document.getElementById("grid");
  var size = document.getElementById("size");
  var start = stage.textContent;

  var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" +
              ".,:;!?-\u2013\u2014'\"\u2018\u2019\u201C\u201D()/+=_\u2026";

  chars.split("").forEach(function (ch) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = ch;
    b.setAttribute("aria-label", "Add " + ch + " to the tester");
    b.addEventListener("click", function () {
      if (stage.textContent === start) stage.textContent = "";
      stage.textContent += ch;
    });
    grid.appendChild(b);
  });

  var buttons = document.querySelectorAll("#styleSwitch button");
  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      stage.style.fontWeight = btn.getAttribute("data-weight");
      stage.style.fontStyle = btn.getAttribute("data-style");
      buttons.forEach(function (o) {
        o.setAttribute("aria-pressed", o === btn ? "true" : "false");
      });
    });
  });

  size.addEventListener("input", function () {
    stage.style.setProperty("--k", size.value / 100);
  });

  stage.addEventListener("focus", function () {
    if (stage.textContent === start) {
      var r = document.createRange();
      r.selectNodeContents(stage);
      var s = window.getSelection();
      s.removeAllRanges();
      s.addRange(r);
    }
  });
})();
