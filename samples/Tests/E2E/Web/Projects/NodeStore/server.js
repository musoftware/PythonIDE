// RAD Store - Express + node:sqlite
'use strict';
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const express = require('express');
const { DatabaseSync } = require('node:sqlite');

const app = express();
const PORT = Number(process.env.PORT) || 3000;
fs.mkdirSync(path.join(__dirname, 'data'), { recursive: true });
const db = new DatabaseSync(path.join(__dirname, 'data', 'store.db'));
db.exec('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL DEFAULT 0)');
if (db.prepare('SELECT COUNT(*) AS n FROM products').get().n === 0) {
    db.exec("INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450)");
}

app.disable('x-powered-by');
app.use(express.urlencoded({ extended: false }));
app.use(express.static(path.join(__dirname, 'public')));

// ---- sessions (in memory) + CSRF
const sessions = new Map();
app.use((req, res, next) => {
    const m = /(?:^|;\s*)sid=([a-f0-9]{32})/.exec(req.headers.cookie || '');
    let sid = m && sessions.has(m[1]) ? m[1] : null;
    if (!sid) {
        sid = crypto.randomBytes(16).toString('hex');
        sessions.set(sid, { csrf: crypto.randomBytes(16).toString('hex') });
        res.setHeader('Set-Cookie', `sid=${sid}; HttpOnly; SameSite=Lax; Path=/`);
    }
    req.session = sessions.get(sid);
    next();
});
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
function csrf(req, res, next) {
    if (req.method === 'POST' && req.body.csrf !== req.session.csrf) return res.status(400).send('Bad CSRF token');
    next();
}
function requireLogin(req, res, next) {
    if (!req.session.user) return res.redirect('/login?next=' + encodeURIComponent(req.originalUrl));
    next();
}
function page(req, title, body) {
    const u = req.session.user;
    return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} - RAD Store</title><link rel="stylesheet" href="/css/site.css"></head><body>
<nav class="top"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar.html">العربية</a>
${u ? `<span class="user">${esc(u)}</span> <a href="/logout">Log out</a>` : '<a href="/login">Log in</a>'}</nav>
<main>${body}</main><script src="/js/app.js"></script></body></html>`;
}
function validate(b) {
    const errors = [];
    const name = String(b.name || '').trim();
    const price = Number(b.price);
    if (!name) errors.push('Name is required');
    if (b.price === undefined || b.price === '' || !Number.isFinite(price) || price < 0) errors.push('Price must be a positive number');
    return { errors, name, price };
}
function form(req, errors, name, price, extra = '') {
    return errors.map(e => `<p class="error">${esc(e)}</p>`).join('') +
        `<form method="post" class="product"><input type="hidden" name="csrf" value="${req.session.csrf}">
<label>Name <input name="name" value="${esc(name)}" required></label>
<label>Price <input name="price" value="${esc(price)}" type="number" step="0.01" min="0"></label>
<button type="submit">Save</button></form>${extra}`;
}

// ---- pages
app.get('/products', (req, res) => {
    const q = String(req.query.q || '');
    const rows = db.prepare('SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY id').all(`%${q}%`);
    const trs = rows.map(p => `<tr data-id="${p.id}"><td class="name">${esc(p.name)}</td><td>${p.price.toFixed(2)}</td>
<td>${req.session.user ? `<a href="/products/${p.id}/edit">Edit</a>` : ''}</td></tr>`).join('');
    res.send(page(req, 'Products', `<h1>Products</h1>
${req.session.user ? '<p><a class="btn" href="/products/add">Add product</a></p>' : ''}
<table id="products"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>${trs}</tbody></table>
<p class="count">${rows.length} products</p>`));
});

app.get('/products/add', requireLogin, (req, res) => res.send(page(req, 'Add product', '<h1>Add product</h1>' + form(req, [], '', ''))));
app.post('/products/add', requireLogin, csrf, (req, res) => {
    const v = validate(req.body);
    if (v.errors.length) return res.status(422).send(page(req, 'Add product', '<h1>Add product</h1>' + form(req, v.errors, v.name, req.body.price)));
    db.prepare('INSERT INTO products (name, price) VALUES (?, ?)').run(v.name, v.price);
    res.redirect('/products');
});

function findProduct(req, res, next) {
    req.product = db.prepare('SELECT * FROM products WHERE id = ?').get(Number(req.params.id));
    if (!req.product) return res.status(404).send('Not found');
    next();
}
const deleteForm = (req, id) => `<form method="post" action="/products/${id}/delete" class="delete">
<input type="hidden" name="csrf" value="${req.session.csrf}"><button type="submit">Delete</button></form>`;
app.get('/products/:id/edit', requireLogin, findProduct, (req, res) => res.send(page(req, 'Edit product',
    '<h1>Edit product</h1>' + form(req, [], req.product.name, req.product.price, deleteForm(req, req.product.id)))));
app.post('/products/:id/edit', requireLogin, csrf, findProduct, (req, res) => {
    const v = validate(req.body);
    if (v.errors.length) return res.status(422).send(page(req, 'Edit product', '<h1>Edit product</h1>' + form(req, v.errors, v.name, req.body.price)));
    db.prepare('UPDATE products SET name = ?, price = ? WHERE id = ?').run(v.name, v.price, req.product.id);
    res.redirect('/products');
});
app.post('/products/:id/delete', requireLogin, csrf, findProduct, (req, res) => {
    db.prepare('DELETE FROM products WHERE id = ?').run(req.product.id);
    res.redirect('/products');
});

// ---- login (demo account admin / secret)
const loginForm = (req, error) => `<h1>Log in</h1>${error ? `<p class="error">${esc(error)}</p>` : ''}
<form method="post" class="login"><input type="hidden" name="csrf" value="${req.session.csrf}">
<input type="hidden" name="next" value="${esc(req.query.next || '/products')}">
<label>User name <input name="username"></label><label>Password <input name="password" type="password"></label>
<button type="submit">Log in</button></form>`;
app.get('/login', (req, res) => res.send(page(req, 'Log in', loginForm(req, ''))));
app.post('/login', csrf, (req, res) => {
    const ok = req.body.username === 'admin' &&
        crypto.timingSafeEqual(Buffer.from(String(req.body.password || '').padEnd(32)), Buffer.from('secret'.padEnd(32)));
    if (!ok) return res.status(401).send(page(req, 'Log in', loginForm(req, 'Invalid user name or password')));
    req.session.user = 'admin';
    const next = String(req.body.next || '/products');
    res.redirect(next.startsWith('/') ? next : '/products');
});
app.get('/logout', (req, res) => { delete req.session.user; res.redirect('/'); });

// ---- JSON API
app.get('/api/products', (req, res) => res.json(db.prepare('SELECT id, name, price FROM products ORDER BY id').all()));

app.use((req, res) => res.status(404).sendFile(path.join(__dirname, 'public', '404.html')));

app.listen(PORT, '127.0.0.1', () => console.log(`RAD Store listening on http://127.0.0.1:${PORT}/`));
