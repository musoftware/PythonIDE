// RatingBar - web runtime of the RatingBar component package: radRating(element) turns
// <span class="rad-rating" data-value="3" data-max="5"> into clickable stars; a "change" event is raised.
function radRating(el) {
  if (!el) return;
  var max = parseInt(el.dataset.max || "5", 10), ro = el.dataset.readonly === "True" || el.dataset.readonly === "true";
  function draw() {
    var v = parseInt(el.dataset.value || "0", 10);
    el.innerHTML = "";
    for (var i = 1; i <= max; i++) {
      var s = document.createElement("span");
      s.textContent = "★";
      if (i <= v) s.className = "on";
      (function (n) {
        s.onclick = function () {
          if (ro) return;
          el.dataset.value = String(n === v && n === 1 ? 0 : n);
          draw();
          el.dispatchEvent(new Event("change"));
        };
      })(i);
      el.appendChild(s);
    }
  }
  el.reset = function () { el.dataset.value = "0"; draw(); el.dispatchEvent(new Event("change")); };
  draw();
}
