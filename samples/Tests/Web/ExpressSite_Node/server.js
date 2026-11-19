// Express Site - Express web site (RAD IDE App Gallery).
// RAD IDE starts it with the PORT environment variable; "npm start" uses 3000.
'use strict';
const path = require('path');
const fs = require('fs');
const express = require('express');

const app = express();
const PORT = Number(process.env.PORT) || 3000;
const DATA_FILE = path.join(__dirname, 'data', 'notes.json');

app.disable('x-powered-by');
app.use(express.json({ limit: '100kb' }));
app.use((req, res, next) => {
    res.set('X-Content-Type-Options', 'nosniff');
    console.log(`${req.method} ${req.url}`);
    next();
});
app.use(express.static(path.join(__dirname, 'public')));

// ---- a tiny JSON REST API: /api/notes (stored in data/notes.json)
function loadNotes() {
    try {
        return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
    } catch {
        return [];
    }
}

function saveNotes(notes) {
    fs.mkdirSync(path.dirname(DATA_FILE), { recursive: true });
    fs.writeFileSync(DATA_FILE, JSON.stringify(notes, null, 2));
}

app.get('/api/time', (req, res) => res.json({ time: new Date().toISOString() }));

app.get('/api/notes', (req, res) => res.json(loadNotes()));

app.post('/api/notes', (req, res) => {
    const text = typeof req.body.text === 'string' ? req.body.text.trim() : '';
    if (!text || text.length > 500) {
        return res.status(400).json({ error: 'text is required (1-500 characters)' });
    }
    const notes = loadNotes();
    const note = { id: notes.reduce((m, n) => Math.max(m, n.id), 0) + 1, text, created: new Date().toISOString() };
    notes.push(note);
    saveNotes(notes);
    res.status(201).json(note);
});

app.delete('/api/notes/:id', (req, res) => {
    const id = Number(req.params.id);
    const notes = loadNotes();
    const rest = notes.filter(n => n.id !== id);
    if (rest.length === notes.length) {
        return res.status(404).json({ error: 'not found' });
    }
    saveNotes(rest);
    res.status(204).end();
});

app.use((req, res) => res.status(404).sendFile(path.join(__dirname, 'public', '404.html')));

app.listen(PORT, '127.0.0.1', () => console.log(`Express Site listening on http://127.0.0.1:${PORT}/`));
