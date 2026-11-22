// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// The page talks to the REST API with fetch(): list, add, toggle done, delete.
const $ = (id) => document.getElementById(id);

async function api(method, url, body) {
    const r = await fetch(url, {method, headers: {"Content-Type": "application/json"},
                                body: body ? JSON.stringify(body) : undefined});
    if (!r.ok && r.status !== 204) throw new Error((await r.json()).detail || r.statusText);
    return r.status === 204 ? null : r.json();
}

async function refresh() {
    const url = $("hideDone").checked ? "/api/tasks?done=false" : "/api/tasks";
    const tasks = await api("GET", url);
    const s = await api("GET", "/api/stats");
    $("stats").textContent = `${s.open} open, ${s.done} done`;
    $("list").innerHTML = "";
    for (const t of tasks) {
        const li = document.createElement("li");
        li.className = `${t.priority}${t.done ? " done" : ""}`;
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = t.done;
        cb.onchange = async () => { await api("PATCH", `/api/tasks/${t.id}`, {done: cb.checked}); refresh(); };
        const span = document.createElement("span");
        span.textContent = t.title;
        const del = document.createElement("button");
        del.textContent = "x";
        del.title = "Delete";
        del.onclick = async () => { await api("DELETE", `/api/tasks/${t.id}`); refresh(); };
        li.append(cb, span, del);
        $("list").append(li);
    }
}

$("add").onsubmit = async (e) => {
    e.preventDefault();
    try {
        await api("POST", "/api/tasks", {title: $("title").value, priority: $("priority").value});
        $("title").value = "";
        refresh();
    } catch (err) { alert(err.message); }
};
$("hideDone").onchange = refresh;
refresh();
