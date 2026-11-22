// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// QuickPoll front end: plain JavaScript (fetch + DOM, no framework). Lists the polls, creates new ones,
// votes and draws the results as bars. The interface switches between English and Arabic (RTL).
'use strict';

const TEXTS = {
    en: { title: 'QuickPoll', new: 'New poll', question: 'Question', options: 'Answers (one per line, 2-6)',
          create: 'Create poll', votes: 'votes', vote: 'Vote', del: 'Delete', none: 'No polls yet.', other: 'العربية' },
    ar: { title: 'تصويت سريع', new: 'تصويت جديد', question: 'السؤال', options: 'الإجابات (سطر لكل إجابة، من 2 إلى 6)',
          create: 'أنشئ التصويت', votes: 'صوت', vote: 'صوّت', del: 'حذف', none: 'لا توجد تصويتات بعد.', other: 'English' },
};
let lang = localStorage.getItem('qp-lang') || 'en';
const voterId = localStorage.getItem('qp-voter') || (() => {
    const id = Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('qp-voter', id);
    return id;
})();

const $ = (sel) => document.querySelector(sel);
const t = (k) => TEXTS[lang][k];

async function api(method, url, body) {
    const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-Voter': voterId },
        body: body ? JSON.stringify(body) : undefined,
    });
    const data = res.status === 204 ? null : await res.json();
    if (!res.ok) throw new Error((data && data.error) || res.statusText);
    return data;
}

function applyLanguage() {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
    document.querySelectorAll('[data-t]').forEach((el) => { el.textContent = t(el.dataset.t); });
    $('#lang').textContent = t('other');
    document.title = t('title');
}

function pollCard(p) {
    const card = document.createElement('article');
    card.className = 'card';
    const h = document.createElement('h3');
    h.textContent = p.question;
    h.dir = 'auto';
    card.append(h);
    p.options.forEach((opt, i) => {
        const pct = p.total ? Math.round((p.votes[i] * 100) / p.total) : 0;
        const row = document.createElement('div');
        row.className = 'option';
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = t('vote');
        btn.onclick = () => vote(p.id, i);
        const label = document.createElement('span');
        label.dir = 'auto';
        label.textContent = `${opt} - ${p.votes[i]} (${pct}%)`;
        const bar = document.createElement('div');
        bar.className = 'bar';
        bar.style.width = `${pct}%`;
        row.append(btn, label, bar);
        card.append(row);
    });
    const foot = document.createElement('p');
    foot.className = 'muted';
    foot.textContent = `${p.total} ${t('votes')} · `;
    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'link';
    del.textContent = t('del');
    del.onclick = async () => { await api('DELETE', `/api/polls/${p.id}`); load(); };
    foot.append(del);
    card.append(foot);
    return card;
}

async function load() {
    const polls = await api('GET', '/api/polls');
    const box = $('#polls');
    box.replaceChildren(...(polls.length ? polls.map(pollCard) : [Object.assign(document.createElement('p'),
        { className: 'muted', textContent: t('none') })]));
}

async function vote(id, option) {
    try { await api('POST', `/api/polls/${id}/vote`, { option }); } catch (e) { alert(e.message); }
    load();
}

$('#newPoll').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const f = ev.target;
    $('#error').textContent = '';
    try {
        await api('POST', '/api/polls', { question: f.question.value, options: f.options.value.split('\n') });
        f.reset();
        load();
    } catch (e) {
        $('#error').textContent = e.message;
    }
});

$('#lang').addEventListener('click', () => {
    lang = lang === 'en' ? 'ar' : 'en';
    localStorage.setItem('qp-lang', lang);
    applyLanguage();
    load();
});

applyLanguage();
load();
