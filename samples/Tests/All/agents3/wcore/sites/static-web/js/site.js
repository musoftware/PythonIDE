// Site scripts
document.addEventListener('DOMContentLoaded', function () {
    var el = document.getElementById('clock');
    if (el) { setInterval(function () { el.textContent = new Date().toLocaleTimeString(); }, 1000); }
});
