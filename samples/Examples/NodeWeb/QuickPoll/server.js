// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// QuickPoll - an Express web site (RAD IDE example): create polls, vote, see live results.
// RAD IDE starts it with the PORT environment variable (F5); "npm start" uses 3000.
//
// REST API (JSON):
//   GET    /api/polls              all polls (newest first) with vote counts
//   POST   /api/polls              {"question": "...", "options": ["a", "b", ...]}  -> 201 + the poll
//   GET    /api/polls/:id          one poll
//   POST   /api/polls/:id/vote     {"option": <index>}  -> the poll with new counts (one vote per voter id)
//   DELETE /api/polls/:id          remove a poll
// Data: data/polls.json (written atomically: temp file + rename). The front end is public/ (fetch + DOM).
'use strict';
const path = require('path');
const express = require('express');
const store = require('./lib/store');

const app = express();
const PORT = Number(process.env.PORT) || 3000;

app.disable('x-powered-by');
app.use(express.json({ limit: '20kb' }));
app.use((req, res, next) => {
    res.set('X-Content-Type-Options', 'nosniff');
    console.log(`${req.method} ${req.url}`);
    next();
});
app.use(express.static(path.join(__dirname, 'public')));

/** Validation of a new poll: 3-200 characters, 2-6 different options of 1-80 characters. */
function validPoll(body) {
    const question = typeof body.question === 'string' ? body.question.trim() : '';
    const options = Array.isArray(body.options)
        ? body.options.map((o) => String(o).trim()).filter((o) => o) : [];
    if (question.length < 3 || question.length > 200) return { error: 'question: 3-200 characters' };
    if (options.length < 2 || options.length > 6) return { error: 'options: 2 to 6 answers' };
    if (options.some((o) => o.length > 80)) return { error: 'an option is longer than 80 characters' };
    if (new Set(options.map((o) => o.toLowerCase())).size !== options.length) return { error: 'options must differ' };
    return { question, options };
}

const voter = (req) => String(req.get('X-Voter') || req.ip);          // the front end sends a random id

app.get('/api/polls', (req, res) => res.json(store.all().map(store.publicView)));

app.post('/api/polls', (req, res) => {
    const v = validPoll(req.body || {});
    if (v.error) return res.status(400).json({ error: v.error });
    res.status(201).json(store.publicView(store.create(v.question, v.options)));
});

app.get('/api/polls/:id', (req, res) => {
    const poll = store.get(Number(req.params.id));
    if (!poll) return res.status(404).json({ error: 'poll not found' });
    res.json(store.publicView(poll));
});

app.post('/api/polls/:id/vote', (req, res) => {
    const result = store.vote(Number(req.params.id), Number(req.body && req.body.option), voter(req));
    if (result.error) return res.status(result.status).json({ error: result.error });
    res.json(store.publicView(result.poll));
});

app.delete('/api/polls/:id', (req, res) => {
    if (!store.remove(Number(req.params.id))) return res.status(404).json({ error: 'poll not found' });
    res.status(204).end();
});

app.use((req, res) => res.status(404).sendFile(path.join(__dirname, 'public', '404.html')));

app.listen(PORT, '127.0.0.1', () => console.log(`QuickPoll listening on http://127.0.0.1:${PORT}/`));
