# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store on CodeIgniter 4: New Project > Web > PHP > CodeIgniter 4 App (composer create-project, SQLite3).
Migration + seeder run with Spark, a model with validation rules, controllers, PHP views with csrf_field() (the
csrf filter on the POST routes), a session login and a JSON route; the home page is public/home.html."""
TITLE = "CodeIgniter 4 (composer create-project) + SQLite3"
LANG, TEMPLATE, NAME = "php-web", "codeigniter4", "CiStore"
TOOLS = ["php", "composer"]
WEBROOT = "public"
DB_FILE = "writable/database.db"
DESIGN = "public/home.html"
DESIGN_TARGET = "#home"
ROUTES = {"home": "/", "products": "/products", "add": "/products/add", "edit": "/products/{id}/edit",
          "login": "/login", "ar": "/ar.html", "api": "/api/products", "css": "/css/site.css", "js": "/js/app.js"}
REQUIRED_ERROR = "name field is required"
DEBUG = {"file": "app/Controllers/Products.php", "match": "$rows = $this->products->like(", "path": "/products"}
DEBUG_TIMEOUT = 300
INTELLI = {"file": "app/Controllers/Products.php", "after": "public function index()",
           "type": "return view('store/pro", "expect": "store/products", "timeout": 40,
           "html_file": "public/home.html", "css_file": "public/css/site.css"}
PUBLISH_EXPECT = ["spark", "composer.json", "app/Config/Routes.php", "app/Controllers/Products.php",
                  "app/Views/store/products.php", "public/index.php", "public/home.html", "vendor/autoload.php"]
PUBLISH_FORBID = ["writable/database.db"]
PUBLISH_EXCLUDES = ["writable/logs", "writable/cache", "writable/debugbar"]
RUN_TIMEOUT = 300
PUBLISHED_TIMEOUT = 180
DEV: list = []


def toolchain_check():
    import shutil
    return "" if shutil.which("composer") or shutil.which("composer.bat") else "Composer not found"


def _php(folder):
    from radide.web_site.frameworks.common import project_php
    return project_php(folder)


def after_create(j, win, project, folder):
    from pathlib import Path
    DEV[:] = [str(folder)]
    j.check((Path(folder) / "spark").is_file(), "composer create-project did not make the app")
    return f"CodeIgniter app, PHP {_php(folder)}"


def before_database(j, win, project, folder):
    """Spark > migrate (the products migration written in the editor)."""
    from radide.web_site.frameworks.codeigniter import spark
    code, out = spark(folder, ["migrate", "--all"], _php(folder), timeout=300)
    j.check(code == 0, f"spark migrate failed: {out[-800:]}")
    return "spark migrate --all"


def serve_published(dest, port, php="php", **_):
    """The host: spark migrate + db:seed, then php -S public/ with CodeIgniter's rewrite.php router."""
    from pathlib import Path
    from radide.web_site.frameworks.codeigniter import SYSTEM, spark
    php = _php(DEV[0]) if DEV else php
    dest = Path(dest)
    for d in ("writable/session", "writable/cache", "writable/logs"):
        (dest / d).mkdir(parents=True, exist_ok=True)
    for args in (["migrate", "--all"], ["db:seed", "StoreSeeder"]):
        code, out = spark(dest, args, php, timeout=300)
        if code != 0:
            return None, f"spark {' '.join(args)} failed on the published copy: {out[-500:]}", None
    import os
    env = dict(os.environ, app_baseURL=f"http://127.0.0.1:{port}/")      # the host's own URL (.env app.baseURL)
    return [php, "-S", f"127.0.0.1:{port}", "-t", str(dest / "public"), str(dest / SYSTEM / "rewrite.php")], \
        str(dest / "public"), env


DB_SQL = """-- RAD Store demo rows (the table comes from the migration)
INSERT INTO products (name, price, created_at, updated_at)
VALUES ('Laptop', 999.5, datetime('now'), datetime('now')), ('Phone', 450, datetime('now'), datetime('now'));
"""

MIGRATION = """<?php

namespace App\\Database\\Migrations;

use CodeIgniter\\Database\\Migration;

class CreateProducts extends Migration
{
    public function up()
    {
        $this->forge->addField([
            'id'         => ['type' => 'INTEGER', 'auto_increment' => true],
            'name'       => ['type' => 'VARCHAR', 'constraint' => 100],
            'price'      => ['type' => 'REAL', 'default' => 0],
            'created_at' => ['type' => 'DATETIME', 'null' => true],
            'updated_at' => ['type' => 'DATETIME', 'null' => true],
        ]);
        $this->forge->addKey('id', true);
        $this->forge->createTable('products');
    }

    public function down()
    {
        $this->forge->dropTable('products');
    }
}
"""

SEEDER = """<?php

namespace App\\Database\\Seeds;

use CodeIgniter\\Database\\Seeder;

class StoreSeeder extends Seeder
{
    public function run()
    {
        if ($this->db->table('products')->countAllResults() === 0) {
            $this->db->table('products')->insertBatch([
                ['name' => 'Laptop', 'price' => 999.5],
                ['name' => 'Phone', 'price' => 450],
            ]);
        }
    }
}
"""

MODEL = """<?php

namespace App\\Models;

use CodeIgniter\\Model;

class ProductModel extends Model
{
    protected $table = 'products';
    protected $allowedFields = ['name', 'price'];
    protected $useTimestamps = true;
    protected $returnType = 'array';
    protected $validationRules = [
        'name'  => 'required|max_length[100]',
        'price' => 'required|numeric|greater_than_equal_to[0]',
    ];
}
"""

PRODUCTS = """<?php

namespace App\\Controllers;

use App\\Models\\ProductModel;

class Products extends BaseController
{
    private ProductModel $products;

    public function __construct()
    {
        $this->products = model(ProductModel::class);
    }

    private function guard()
    {
        return session('user') ? null : redirect()->to('/login?next=' . urlencode(current_url(true)->getPath()));
    }

    public function index()
    {
        $q = (string) $this->request->getGet('q');
        $rows = $this->products->like('name', $q)->orderBy('id')->findAll();
        return view('store/products', ['products' => $rows, 'q' => $q]);
    }

    public function add()
    {
        if ($r = $this->guard()) {
            return $r;
        }
        if ($this->request->is('post')) {
            $data = $this->request->getPost(['name', 'price']);
            if ($this->products->insert($data) === false) {
                return $this->response->setStatusCode(422)->setBody(view('store/form', [
                    'title' => 'Add product', 'errors' => $this->products->errors(), 'p' => $data, 'id' => null]));
            }
            return redirect()->to('/products');
        }
        return view('store/form', ['title' => 'Add product', 'errors' => [], 'p' => ['name' => '', 'price' => ''], 'id' => null]);
    }

    public function edit(int $id)
    {
        if ($r = $this->guard()) {
            return $r;
        }
        $row = $this->products->find($id);
        if (! $row) {
            throw \\CodeIgniter\\Exceptions\\PageNotFoundException::forPageNotFound();
        }
        if ($this->request->is('post')) {
            $data = $this->request->getPost(['name', 'price']);
            if ($this->products->update($id, $data) === false) {
                return $this->response->setStatusCode(422)->setBody(view('store/form', [
                    'title' => 'Edit product', 'errors' => $this->products->errors(), 'p' => $data, 'id' => $id]));
            }
            return redirect()->to('/products');
        }
        return view('store/form', ['title' => 'Edit product', 'errors' => [], 'p' => $row, 'id' => $id]);
    }

    public function delete(int $id)
    {
        if ($r = $this->guard()) {
            return $r;
        }
        $this->products->delete($id);
        return redirect()->to('/products');
    }

    public function api()
    {
        $rows = $this->products->select('id, name, price')->orderBy('id')->findAll();
        foreach ($rows as &$r) {
            $r['id'] = (int) $r['id'];
            $r['price'] = (float) $r['price'];
        }
        return $this->response->setJSON($rows);
    }

    public function home()
    {
        return $this->response->setBody(file_get_contents(FCPATH . 'home.html'));
    }
}
"""

AUTH = """<?php

namespace App\\Controllers;

class Auth extends BaseController
{
    public function login()
    {
        if ($this->request->is('post')) {
            if ($this->request->getPost('username') === 'admin'
                && hash_equals('secret', (string) $this->request->getPost('password'))) {
                session()->regenerate();
                session()->set('user', 'admin');
                $next = (string) $this->request->getPost('next');
                return redirect()->to(str_starts_with($next, '/') ? $next : '/products');
            }
            return $this->response->setStatusCode(401)->setBody(view('store/login', [
                'error' => 'Invalid user name or password', 'next' => $this->request->getPost('next')]));
        }
        return view('store/login', ['error' => '', 'next' => $this->request->getGet('next') ?? '/products']);
    }

    public function logout()
    {
        session()->remove('user');
        return redirect()->to('/');
    }
}
"""

ROUTES_PHP = """<?php

use CodeIgniter\\Router\\RouteCollection;

/**
 * @var RouteCollection $routes
 */
$routes->get('/', 'Products::home');
$routes->get('products', 'Products::index');
$routes->match(['GET', 'POST'], 'products/add', 'Products::add', ['filter' => 'csrf']);
$routes->match(['GET', 'POST'], 'products/(:num)/edit', 'Products::edit/$1', ['filter' => 'csrf']);
$routes->post('products/(:num)/delete', 'Products::delete/$1', ['filter' => 'csrf']);
$routes->match(['GET', 'POST'], 'login', 'Auth::login', ['filter' => 'csrf']);
$routes->post('logout', 'Auth::logout', ['filter' => 'csrf']);
$routes->get('api/products', 'Products::api');
"""

LAYOUT_TOP = """<?php /** @var string $title */ ?><!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= esc($title ?? 'RAD Store') ?> - RAD Store</title>
<link rel="stylesheet" href="/css/site.css">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar.html">العربية</a>
<?php if (session('user')): ?>
  <span class="user"><?= esc(session('user')) ?></span>
  <form method="post" action="/logout" style="display:inline"><?= csrf_field() ?><button type="submit">Log out</button></form>
<?php else: ?>
  <a href="/login">Log in</a>
<?php endif ?>
</nav>
<main>
"""

LAYOUT_BOTTOM = """</main>
<script src="/js/app.js"></script>
</body>
</html>
"""

PRODUCTS_VIEW = """<?= view('store/top', ['title' => 'Products']) ?>
<h1>Products</h1>
<form method="get" class="search"><input name="q" value="<?= esc($q) ?>" placeholder="Search"><button>Search</button></form>
<?php if (session('user')): ?><p><a class="btn" href="/products/add">Add product</a></p><?php endif ?>
<table id="products"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>
<?php foreach ($products as $p): ?>
<tr data-id="<?= (int) $p['id'] ?>"><td class="name"><?= esc($p['name']) ?></td><td><?= number_format((float) $p['price'], 2) ?></td>
<td><?php if (session('user')): ?><a href="/products/<?= (int) $p['id'] ?>/edit">Edit</a><?php endif ?></td></tr>
<?php endforeach ?>
</tbody></table>
<p class="count"><?= count($products) ?> products</p>
<?= view('store/bottom') ?>
"""

FORM_VIEW = """<?= view('store/top', ['title' => $title]) ?>
<h1><?= esc($title) ?></h1>
<?php foreach ($errors as $e): ?><p class="error"><?= esc($e) ?></p><?php endforeach ?>
<form method="post" class="product">
  <?= csrf_field() ?>
  <label>Name <input name="name" value="<?= esc($p['name'] ?? '') ?>"></label>
  <label>Price <input name="price" value="<?= esc((string) ($p['price'] ?? '')) ?>" type="number" step="0.01" min="0"></label>
  <button type="submit">Save</button>
</form>
<?php if ($id): ?>
<form method="post" action="/products/<?= (int) $id ?>/delete" class="delete">
  <?= csrf_field() ?><button type="submit">Delete</button>
</form>
<?php endif ?>
<?= view('store/bottom') ?>
"""

LOGIN_VIEW = """<?= view('store/top', ['title' => 'Log in']) ?>
<h1>Log in</h1>
<?php if ($error): ?><p class="error"><?= esc($error) ?></p><?php endif ?>
<form method="post" action="/login" class="login">
  <?= csrf_field() ?>
  <input type="hidden" name="next" value="<?= esc((string) $next) ?>">
  <label>User name <input name="username"></label>
  <label>Password <input name="password" type="password"></label>
  <button type="submit">Log in</button>
</form>
<?= view('store/bottom') ?>
"""

HOME = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAD Store</title>
<link rel="stylesheet" href="/css/site.css">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar.html">العربية</a> <a href="/login">Log in</a></nav>
<main id="home">
</main>
<script src="/js/app.js"></script>
</body>
</html>
"""

AR = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>متجر راد</title><link rel="stylesheet" href="/css/site.css"></head>
<body>
<nav class="top"><a href="/">English</a> <a href="/products">المنتجات</a></nav>
<main><h1>مرحبا بكم في متجر راد</h1><p>أفضل الأجهزة بأفضل الأسعار.</p></main>
</body>
</html>
"""

CSS = """/* RAD Store */
body { font-family: "Segoe UI", Tahoma, sans-serif; margin: 0; background: #f6f7fb; color: #222; }
nav.top { background: #dd4814; padding: 10px 16px; }
nav.top a, nav.top .user { color: #fff; margin-inline-end: 14px; text-decoration: none; }
main { max-width: 900px; margin: 20px auto; padding: 0 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: start; }
.error { color: #b00020; font-weight: bold; }
.hero { padding: 40px 20px; background: linear-gradient(90deg, #a83510, #dd4814); color: #fff; border-radius: 12px; }
"""


def files():
    return {"app/Database/Migrations/2026-01-01-000000_CreateProducts.php": MIGRATION,
            "app/Database/Seeds/StoreSeeder.php": SEEDER, "app/Models/ProductModel.php": MODEL,
            "app/Controllers/Products.php": PRODUCTS, "app/Controllers/Auth.php": AUTH,
            "app/Config/Routes.php": ROUTES_PHP, "app/Views/store/top.php": LAYOUT_TOP,
            "app/Views/store/bottom.php": LAYOUT_BOTTOM, "app/Views/store/products.php": PRODUCTS_VIEW,
            "app/Views/store/form.php": FORM_VIEW, "app/Views/store/login.php": LOGIN_VIEW,
            "public/home.html": HOME, "public/ar.html": AR, "public/css/site.css": CSS,
            "public/js/app.js": "// RAD Store\ndocument.addEventListener('DOMContentLoaded', () => { document.body.dataset.ready = '1'; });\n"}
