// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// QuickPoll data store: polls kept in data/polls.json. Small and dependency free; every write goes to a
// temporary file first and is then renamed, so a crash never leaves a half-written file.
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const FILE = path.join(__dirname, '..', 'data', 'polls.json');

function load() {
    try { return JSON.parse(fs.readFileSync(FILE, 'utf8')); } catch { return []; }
}

function save(polls) {
    fs.mkdirSync(path.dirname(FILE), { recursive: true });
    const tmp = FILE + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(polls, null, 2));
    fs.renameSync(tmp, FILE);
}

/** A poll as the API shows it: voters are stored hashed and never sent back. */
function publicView(p) {
    const total = p.votes.reduce((a, b) => a + b, 0);
    return { id: p.id, question: p.question, options: p.options, votes: p.votes, total, created: p.created };
}

function all() { return load().sort((a, b) => b.id - a.id); }

function get(id) { return load().find((p) => p.id === id) || null; }

function create(question, options) {
    const polls = load();
    const poll = { id: polls.reduce((m, p) => Math.max(m, p.id), 0) + 1, question, options,
                   votes: options.map(() => 0), voters: [], created: new Date().toISOString() };
    polls.push(poll);
    save(polls);
    return poll;
}

function vote(id, option, voterId) {
    const polls = load();
    const poll = polls.find((p) => p.id === id);
    if (!poll) return { status: 404, error: 'poll not found' };
    if (!Number.isInteger(option) || option < 0 || option >= poll.options.length) {
        return { status: 400, error: 'option: index of an answer' };
    }
    const key = crypto.createHash('sha256').update(`${id}:${voterId}`).digest('hex').slice(0, 16);
    if (poll.voters.includes(key)) return { status: 409, error: 'you already voted in this poll' };
    poll.voters.push(key);
    poll.votes[option] += 1;
    save(polls);
    return { poll };
}

function remove(id) {
    const polls = load();
    const rest = polls.filter((p) => p.id !== id);
    if (rest.length === polls.length) return false;
    save(rest);
    return true;
}

module.exports = { all, get, create, vote, remove, publicView };
