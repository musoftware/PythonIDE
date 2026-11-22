# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store as a static HTML / CSS / JavaScript site: New Project > Web > HTML Bootstrap Site.

No server code: the catalogue is a JSON file the page's script renders (fetch), the home page is designed in the
Design View, the Arabic page is RTL; JavaScript is debugged in the Preview (js-debug attached to QtWebEngine)."""
TITLE = "Static HTML/CSS/JS (HTML Bootstrap Site)"
LANG, TEMPLATE, NAME = "static-web", "html-bootstrap", "StaticStore"
TOOLS = []
WEBROOT = "."
DB_FILE = None
DESIGN = "index.html"
DESIGN_TARGET = "main"
FEATURES = {"db": False, "auth": False, "crud": False, "api": True, "debug": True,
            "auth_skip": "a static site has no server-side login (no server code)",
            "crud_skip": "a static site has no server-side add/edit/delete (no server code)"}
ROUTES = {"home": "/index.html", "products": "/products.html", "ar": "/ar.html", "api": "/data/products.json",
          "css": "/assets/css/site.css", "js": "/assets/js/store.js"}
PREVIEW_ROWS = "#products tbody tr"
DEBUG = {"file": "assets/js/store.js", "match": "const rows = items.map", "path": "/products.html",
         "trigger": "preview"}
INTELLI = {"file": "assets/js/store.js", "after": "use strict", "type": "document.getElementBy",
           "expect": "getElementById", "html_file": "products.html", "css_file": "assets/css/site.css"}
PUBLISH_EXPECT = ["index.html", "products.html", "ar.html", "data/products.json", "assets/js/store.js",
                  "assets/css/site.css", "assets/vendor/bootstrap/css/bootstrap.min.css"]


def serve_published(dest, port, **_):
    import sys
    return [sys.executable, "-I", "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", str(dest)], \
        str(dest), None


PRODUCTS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Products | RAD Store</title>
    <link rel="stylesheet" href="assets/vendor/bootstrap/css/bootstrap.min.css">
    <link rel="stylesheet" href="assets/css/site.css">
</head>
<body>
<nav class="navbar navbar-dark bg-dark"><div class="container">
  <a class="navbar-brand" href="index.html">RAD Store</a>
  <a class="nav-link text-white" href="ar.html">العربية</a>
</div></nav>
<main class="container my-4">
  <h1>Products</h1>
  <noscript><p>Laptop, Phone (enable JavaScript for the live catalogue)</p></noscript>
  <p class="text-muted">Featured: Laptop and Phone.</p>
  <table class="table" id="products"><thead><tr><th>Name</th><th>Price</th></tr></thead><tbody></tbody></table>
  <p id="total"></p>
</main>
<script src="assets/js/store.js"></script>
</body>
</html>
"""

AR_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>متجر راد</title>
    <link rel="stylesheet" href="assets/vendor/bootstrap/css/bootstrap.rtl.min.css">
    <link rel="stylesheet" href="assets/css/site.css">
</head>
<body>
<main class="container my-4">
  <h1>مرحبا بكم في متجر راد</h1>
  <p>تصفح <a href="products.html">المنتجات</a>.</p>
</main>
</body>
</html>
"""

STORE_JS = """// RAD Store - renders the catalogue from data/products.json
'use strict';

async function loadProducts() {
    const res = await fetch('data/products.json');
    const items = await res.json();
    const rows = items.map(p => `<tr><td class="name">${p.name}</td><td>${p.price.toFixed(2)}</td></tr>`);
    document.querySelector('#products tbody').innerHTML = rows.join('');
    document.getElementById('total').textContent = `${items.length} products`;
}

document.addEventListener('DOMContentLoaded', loadProducts);
"""

PRODUCTS_JSON = """[
  {"id": 1, "name": "Laptop", "price": 999.5},
  {"id": 2, "name": "Phone", "price": 450},
  {"id": 3, "name": "Headphones", "price": 79.9}
]
"""


def after_create(j, win, project, folder):
    # the RTL Bootstrap build is not in the template: a user would add it next to the LTR one
    import re
    css = folder / "assets/vendor/bootstrap/css/bootstrap.min.css"
    rtl = folder / "assets/vendor/bootstrap/css/bootstrap.rtl.min.css"
    if css.exists() and not rtl.exists():
        rtl.write_text(css.read_text(encoding="utf-8"), encoding="utf-8")
    return "template home page kept (title/brand = project name)"


def files():
    return {"products.html": PRODUCTS_HTML, "ar.html": AR_HTML, "assets/js/store.js": STORE_JS,
            "data/products.json": PRODUCTS_JSON}
