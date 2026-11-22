// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Shared by every page: the footer clock.
document.addEventListener("DOMContentLoaded", function () {
    var el = document.getElementById("clock");
    if (el) {
        var tick = function () { el.textContent = new Date().toLocaleTimeString(document.documentElement.lang || "en"); };
        tick();
        setInterval(tick, 1000);
    }
});
