// Client side of Express Site: talks to the /api routes of server.js.
const list = document.getElementById('notes');

async function refresh() {
    const notes = await (await fetch('/api/notes')).json();
    list.replaceChildren(...notes.map(n => {
        const li = document.createElement('li');
        li.textContent = n.text + ' ';
        const del = document.createElement('button');
        del.textContent = 'Delete';
        del.onclick = async () => { await fetch('/api/notes/' + n.id, { method: 'DELETE' }); refresh(); };
        li.appendChild(del);
        return li;
    }));
}

document.getElementById('note-form').addEventListener('submit', async ev => {
    ev.preventDefault();
    const input = document.getElementById('note-text');
    await fetch('/api/notes', { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ text: input.value }) });
    input.value = '';
    refresh();
});

fetch('/api/time').then(r => r.json()).then(d => { document.getElementById('time').textContent = d.time; });
refresh();
