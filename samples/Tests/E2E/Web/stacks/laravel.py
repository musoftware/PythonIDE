# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store on Laravel: New Project > Web > PHP > Laravel App (composer create-project with PHP >= 8.3, SQLite).
Eloquent model + migration, a controller with $request->validate(), Blade views, a session login, a JSON route;
the home page is public/home.html (Design View) returned by the "/" route."""
TITLE = "Laravel (composer create-project) + SQLite"
LANG, TEMPLATE, NAME = "php-web", "laravel", "LaravelStore"
TOOLS = ["php", "composer"]
WEBROOT = "public"
DB_FILE = "database/database.sqlite"
DESIGN = "public/home.html"
DESIGN_TARGET = "#home"
ROUTES = {"home": "/", "products": "/products", "add": "/products/create", "edit": "/products/{id}/edit",
          "login": "/login", "ar": "/ar.html", "api": "/api/products", "css": "/css/site.css", "js": "/js/app.js"}
REQUIRED_ERROR = "name field is required"
DEBUG = {"file": "app/Http/Controllers/ProductController.php", "match": "$products = Product::query()",
         "path": "/products"}
DEBUG_TIMEOUT = 300
INTELLI = {"file": "app/Http/Controllers/ProductController.php", "after": "public function index(",
           "type": "return view('products.i", "expect": "products.index", "timeout": 40,
           "html_file": "public/home.html", "css_file": "public/css/site.css"}
PUBLISH_EXPECT = ["artisan", "composer.json", "routes/web.php", "app/Http/Controllers/ProductController.php",
                  "resources/views/products/index.blade.php", "public/index.php", "public/home.html",
                  "vendor/autoload.php"]
PUBLISH_FORBID = ["database/database.sqlite"]
PUBLISH_EXCLUDES = ["node_modules", "storage/logs", "storage/framework/cache/data", "storage/framework/views"]
RUN_TIMEOUT = 300
ALLOW_MODALS = ["Creating Laravel App"]
PUBLISHED_TIMEOUT = 180


def toolchain_check():
    from radide.web_site import php_toolchain as tc
    ok = [i for i in tc.detect_installs() if i.bits == 64 and tc.vtuple(i.version)[:2] >= (8, 3)]
    return "" if ok else "Laravel needs PHP >= 8.3 (none installed; the IDE would download PHP 8.4)"


def _php(folder):
    from radide.web_site.frameworks.common import project_php
    return project_php(folder)


def before_database(j, win, project, folder):
    """Artisan > migrate (the products migration written in the editor)."""
    from radide.web_site.frameworks.common import run_php
    code, out = run_php(folder, ["artisan", "migrate", "--force", "--no-interaction"], 300)
    j.check(code == 0, f"artisan migrate failed: {out[-800:]}")
    return "artisan migrate: " + " ".join(l.strip() for l in out.splitlines() if "products" in l)[:120]


def serve_published(dest, port, php="php", **_):
    """The host: .env, artisan migrate --seed, php -S with Laravel's router (document root public/)."""
    import subprocess
    from pathlib import Path
    from radide.web_site.frameworks.common import php_ext_args
    from radide.web_site.frameworks.laravel import SERVER_PHP
    php = _php(DEV[0]) if DEV else php
    dest = Path(dest)
    (dest / "database" / "database.sqlite").touch()
    for d in ("storage/framework/sessions", "storage/framework/views", "storage/framework/cache/data", "storage/logs"):
        (dest / d).mkdir(parents=True, exist_ok=True)
    r = subprocess.run([php, *php_ext_args(php), "artisan", "migrate", "--force", "--seed", "--no-interaction"],
                       cwd=str(dest), capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return None, f"artisan migrate --seed failed on the published copy: {(r.stdout + r.stderr)[-500:]}", None
    return [php, *php_ext_args(php), "-S", f"127.0.0.1:{port}", "-t", str(dest / "public"),
            str(dest / SERVER_PHP)], str(dest / "public"), None


DEV: list = []


def after_create(j, win, project, folder):
    from pathlib import Path
    DEV[:] = [str(folder)]
    j.check((Path(folder) / "artisan").is_file(), "composer create-project did not make the app")
    return f"Laravel app, PHP {_php(folder)}"


DB_SQL = """-- RAD Store demo rows (the table comes from the migration)
INSERT INTO products (name, price, created_at, updated_at)
VALUES ('Laptop', 999.5, datetime('now'), datetime('now')), ('Phone', 450, datetime('now'), datetime('now'));
"""

MIGRATION = """<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('products', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->decimal('price', 10, 2)->default(0);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('products');
    }
};
"""

MODEL = """<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Model;

class Product extends Model
{
    protected $fillable = ['name', 'price'];

    protected $casts = ['price' => 'float'];
}
"""

CONTROLLER = """<?php

namespace App\\Http\\Controllers;

use App\\Models\\Product;
use Illuminate\\Http\\Request;

class ProductController extends Controller
{
    private function guard(Request $request)
    {
        return session('user') ? null : redirect('/login?next=' . urlencode($request->getRequestUri()));
    }

    private function rules(): array
    {
        return ['name' => 'required|string|max:100', 'price' => 'required|numeric|min:0'];
    }

    public function index(Request $request)
    {
        $products = Product::query()->where('name', 'like', '%' . $request->query('q', '') . '%')->orderBy('id')->get();
        return view('products.index', ['products' => $products, 'q' => $request->query('q', '')]);
    }

    public function create(Request $request)
    {
        return $this->guard($request) ?? view('products.form', ['product' => null]);
    }

    public function store(Request $request)
    {
        if ($r = $this->guard($request)) {
            return $r;
        }
        Product::create($request->validate($this->rules()));
        return redirect('/products');
    }

    public function edit(Request $request, Product $product)
    {
        return $this->guard($request) ?? view('products.form', ['product' => $product]);
    }

    public function update(Request $request, Product $product)
    {
        if ($r = $this->guard($request)) {
            return $r;
        }
        $product->update($request->validate($this->rules()));
        return redirect('/products');
    }

    public function destroy(Request $request, Product $product)
    {
        if ($r = $this->guard($request)) {
            return $r;
        }
        $product->delete();
        return redirect('/products');
    }

    public function api()
    {
        return response()->json(Product::orderBy('id')->get(['id', 'name', 'price']));
    }
}
"""

SESSION_CTRL = """<?php

namespace App\\Http\\Controllers;

use Illuminate\\Http\\Request;

class SessionController extends Controller
{
    public function create(Request $request)
    {
        return view('login', ['next' => $request->query('next', '/products'), 'error' => '']);
    }

    public function store(Request $request)
    {
        if ($request->input('username') === 'admin' && hash_equals('secret', (string) $request->input('password'))) {
            $request->session()->regenerate();
            session(['user' => 'admin']);
            $next = (string) $request->input('next', '/products');
            return redirect(str_starts_with($next, '/') ? $next : '/products');
        }
        return response()->view('login', ['next' => $request->input('next'), 'error' => 'Invalid user name or password'], 401);
    }

    public function destroy(Request $request)
    {
        $request->session()->forget('user');
        return redirect('/');
    }
}
"""

WEB_ROUTES = """<?php

use App\\Http\\Controllers\\ProductController;
use App\\Http\\Controllers\\SessionController;
use Illuminate\\Support\\Facades\\Route;

Route::get('/', fn () => response()->file(public_path('home.html')));

Route::resource('products', ProductController::class)->except(['show']);

Route::get('/login', [SessionController::class, 'create'])->name('login');
Route::post('/login', [SessionController::class, 'store']);
Route::post('/logout', [SessionController::class, 'destroy'])->name('logout');

Route::get('/api/products', [ProductController::class, 'api']);
"""

SEEDER = """<?php

namespace Database\\Seeders;

use App\\Models\\Product;
use Illuminate\\Database\\Seeder;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        if (Product::count() === 0) {
            Product::create(['name' => 'Laptop', 'price' => 999.5]);
            Product::create(['name' => 'Phone', 'price' => 450]);
        }
    }
}
"""

LAYOUT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>@yield('title', 'RAD Store') - RAD Store</title>
<link rel="stylesheet" href="{{ asset('css/site.css') }}">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="{{ route('products.index') }}">Products</a> <a href="/ar.html">العربية</a>
@if (session('user'))
  <span class="user">{{ session('user') }}</span>
  <form method="post" action="{{ route('logout') }}" style="display:inline">@csrf<button type="submit">Log out</button></form>
@else
  <a href="{{ route('login') }}">Log in</a>
@endif
</nav>
<main>@yield('content')</main>
<script src="{{ asset('js/app.js') }}"></script>
</body>
</html>
"""

INDEX_VIEW = """@extends('layouts.store')
@section('title', 'Products')
@section('content')
<h1>Products</h1>
<form method="get" class="search"><input name="q" value="{{ $q }}" placeholder="Search"><button>Search</button></form>
@if (session('user'))<p><a class="btn" href="{{ route('products.create') }}">Add product</a></p>@endif
<table id="products"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>
@foreach ($products as $p)
<tr data-id="{{ $p->id }}"><td class="name">{{ $p->name }}</td><td>{{ number_format($p->price, 2) }}</td>
<td>@if (session('user'))<a href="{{ route('products.edit', $p) }}">Edit</a>@endif</td></tr>
@endforeach
</tbody></table>
<p class="count">{{ $products->count() }} products</p>
@endsection
"""

FORM_VIEW = """@extends('layouts.store')
@section('title', $product ? 'Edit product' : 'Add product')
@section('content')
<h1>{{ $product ? 'Edit product' : 'Add product' }}</h1>
@foreach ($errors->all() as $e)<p class="error">{{ $e }}</p>@endforeach
<form method="post" action="{{ $product ? route('products.update', $product) : route('products.store') }}" class="product">
  @csrf
  @if ($product) @method('PUT') @endif
  <label>Name <input name="name" value="{{ old('name', $product?->name) }}"></label>
  <label>Price <input name="price" value="{{ old('price', $product?->price) }}" type="number" step="0.01" min="0"></label>
  <button type="submit">Save</button>
</form>
@if ($product)
<form method="post" action="{{ route('products.destroy', $product) }}?confirm=delete" class="delete">
  @csrf @method('DELETE')<button type="submit">Delete</button>
</form>
@endif
@endsection
"""

LOGIN_VIEW = """@extends('layouts.store')
@section('title', 'Log in')
@section('content')
<h1>Log in</h1>
@if ($error)<p class="error">{{ $error }}</p>@endif
<form method="post" action="/login" class="login">
  @csrf
  <input type="hidden" name="next" value="{{ $next }}">
  <label>User name <input name="username"></label>
  <label>Password <input name="password" type="password"></label>
  <button type="submit">Log in</button>
</form>
@endsection
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
nav.top { background: #f53003; padding: 10px 16px; }
nav.top a, nav.top .user { color: #fff; margin-inline-end: 14px; text-decoration: none; }
main { max-width: 900px; margin: 20px auto; padding: 0 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: start; }
.error { color: #b00020; font-weight: bold; }
.hero { padding: 40px 20px; background: linear-gradient(90deg, #c62828, #f53003); color: #fff; border-radius: 12px; }
"""


def files():
    return {"database/migrations/2026_01_01_000000_create_products_table.php": MIGRATION,
            "app/Models/Product.php": MODEL, "app/Http/Controllers/ProductController.php": CONTROLLER,
            "app/Http/Controllers/SessionController.php": SESSION_CTRL, "routes/web.php": WEB_ROUTES,
            "database/seeders/DatabaseSeeder.php": SEEDER, "resources/views/layouts/store.blade.php": LAYOUT,
            "resources/views/products/index.blade.php": INDEX_VIEW, "resources/views/products/form.blade.php": FORM_VIEW,
            "resources/views/login.blade.php": LOGIN_VIEW, "public/home.html": HOME, "public/ar.html": AR,
            "public/css/site.css": CSS,
            "public/js/app.js": "// RAD Store\ndocument.addEventListener('DOMContentLoaded', () => { document.body.dataset.ready = '1'; });\n"}
