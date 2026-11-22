// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// Contact form: validation in JavaScript, a draft kept while typing, sent messages kept in localStorage.
(function () {
    "use strict";
    var form = document.getElementById("contact");
    var DRAFT = "cityguide.draft", OUTBOX = "cityguide.outbox";
    var fields = ["name", "email", "topic", "message"];

    function rules(v) {
        return {
            name: v.name.trim().length < 2 ? "Please enter your name (2 letters or more)." : "",
            email: /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.email.trim()) ? "" : "Please enter a valid e-mail address.",
            topic: v.topic ? "" : "Please choose a topic.",
            message: v.message.trim().length < 10 ? "The message needs at least 10 characters." : ""
        };
    }
    function values() {
        var v = {};
        fields.forEach(function (f) { v[f] = form.elements[f].value; });
        return v;
    }
    function showErrors(errs) {
        var ok = true;
        fields.forEach(function (f) {
            document.getElementById(f + "-error").textContent = errs[f];
            form.elements[f].classList.toggle("invalid", !!errs[f]);
            if (errs[f]) ok = false;
        });
        return ok;
    }
    function outbox() { try { return JSON.parse(localStorage.getItem(OUTBOX) || "[]"); } catch (e) { return []; } }
    function renderOutbox() {
        var ol = document.getElementById("outbox");
        ol.innerHTML = "";
        outbox().forEach(function (m) {
            var li = document.createElement("li");
            li.textContent = m.when + " - " + m.topic + ": " + m.message.slice(0, 60);
            ol.append(li);
        });
    }

    // restore the draft
    try {
        var d = JSON.parse(localStorage.getItem(DRAFT) || "{}");
        fields.forEach(function (f) { if (d[f]) form.elements[f].value = d[f]; });
    } catch (e) { /* no draft */ }
    form.addEventListener("input", function () {
        localStorage.setItem(DRAFT, JSON.stringify(values()));
        document.getElementById("chars").textContent = form.elements.message.value.length + "/500";
    });
    form.addEventListener("reset", function () {
        localStorage.removeItem(DRAFT);
        showErrors({name: "", email: "", topic: "", message: ""});
    });
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        var v = values();
        if (!showErrors(rules(v))) return;
        var list = outbox();
        v.when = new Date().toLocaleString();
        list.unshift(v);
        localStorage.setItem(OUTBOX, JSON.stringify(list.slice(0, 20)));
        localStorage.removeItem(DRAFT);
        form.reset();
        document.getElementById("sent").hidden = false;
        renderOutbox();
    });
    renderOutbox();
})();
