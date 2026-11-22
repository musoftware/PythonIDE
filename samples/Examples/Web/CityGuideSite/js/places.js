// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// The places list: data in JavaScript, filtering, favourites saved in localStorage (English and Arabic pages).
(function () {
    "use strict";
    var AR = window.LANG === "ar";
    var PLACES = [
        {id: "museum", en: ["City Museum", "History from the first settlers to today."], ar: ["متحف المدينة", "التاريخ من أوائل السكان حتى اليوم."], icon: "🏛"},
        {id: "park", en: ["River Park", "Walks, bikes and a big playground."], ar: ["حديقة النهر", "ممشى ودراجات وملعب كبير للأطفال."], icon: "🌳"},
        {id: "market", en: ["Old Market", "Spices, crafts and street food."], ar: ["السوق القديم", "توابل وحِرف يدوية وأكل شعبي."], icon: "🧺"},
        {id: "tower", en: ["TV Tower", "The best view of the whole city."], ar: ["برج التلفزيون", "أفضل منظر للمدينة كلها."], icon: "🗼"},
        {id: "library", en: ["Central Library", "Quiet reading rooms and free Wi-Fi."], ar: ["المكتبة المركزية", "قاعات قراءة هادئة وإنترنت مجاني."], icon: "📚"},
        {id: "beach", en: ["North Beach", "Swimming in summer, sunsets all year."], ar: ["الشاطئ الشمالي", "سباحة في الصيف وغروب طوال العام."], icon: "🏖"}
    ];
    var KEY = "cityguide.favourites";

    function loadFavs() {
        try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) { return []; }
    }
    function saveFavs(list) { localStorage.setItem(KEY, JSON.stringify(list)); }

    function render() {
        var q = document.getElementById("filter").value.trim().toLowerCase();
        var only = document.getElementById("onlyFav").checked;
        var favs = loadFavs();
        var ul = document.getElementById("places");
        ul.innerHTML = "";
        var shown = 0;
        PLACES.forEach(function (p) {
            var t = AR ? p.ar : p.en;
            var fav = favs.indexOf(p.id) >= 0;
            if (only && !fav) return;
            if (q && (t[0] + " " + t[1]).toLowerCase().indexOf(q) < 0) return;
            shown++;
            var li = document.createElement("li");
            var star = document.createElement("button");
            star.className = "star" + (fav ? " on" : "");
            star.textContent = fav ? "★" : "☆";
            star.title = AR ? "المفضلة" : "Favourite";
            star.onclick = function () {
                var list = loadFavs();
                var i = list.indexOf(p.id);
                if (i >= 0) list.splice(i, 1); else list.push(p.id);
                saveFavs(list);
                render();
            };
            var h = document.createElement("h3");
            h.textContent = p.icon + " " + t[0];
            var d = document.createElement("p");
            d.textContent = t[1];
            li.append(star, h, d);
            ul.append(li);
        });
        document.getElementById("count").textContent = AR ? (shown + " مكان") : (shown + " of " + PLACES.length + " places");
    }

    document.getElementById("filter").addEventListener("input", render);
    document.getElementById("onlyFav").addEventListener("change", render);
    render();
})();
