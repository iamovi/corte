(function () {
  var stage = document.getElementById("stage");
  var grid = document.getElementById("grid");
  var size = document.getElementById("size");
  var start = stage.textContent;

  var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" +
              ".,:;!?-\u2013\u2014'\"\u2018\u2019\u201C\u201D()/+=_\u2026\u00A9\u00B7";

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

  function fillLastRow() {
    var cols = getComputedStyle(grid).gridTemplateColumns.split(" ").filter(Boolean).length;
    if (!cols) return;
    var count = grid.querySelectorAll("button").length;
    var missing = (cols - (count % cols)) % cols;
    var fillers = grid.querySelectorAll(".cell-fill");
    if (fillers.length === missing) return;
    fillers.forEach(function (n) { n.remove(); });
    for (var i = 0; i < missing; i++) {
      var d = document.createElement("span");
      d.className = "cell-fill";
      d.setAttribute("aria-hidden", "true");
      grid.appendChild(d);
    }
  }
  fillLastRow();
  if (window.ResizeObserver) new ResizeObserver(fillLastRow).observe(grid);
  else window.addEventListener("resize", fillLastRow);

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
