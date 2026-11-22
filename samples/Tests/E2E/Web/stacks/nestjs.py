# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store on NestJS 11 (TypeScript): New Project > Web > NestJS App; the generated products resource is turned
into the store (node:sqlite, Node 22.13+), static files from public/ (home page designed in the Design View)."""
TITLE = "NestJS 11 (TypeScript) + SQLite"
LANG, TEMPLATE, NAME = "nestjs-web", "nestjs-app", "NestStore"
TOOLS = ["node", "npm"]
WEBROOT = "public"
DB_FILE = "data/store.db"
DESIGN = "public/index.html"
DESIGN_TARGET = "#home"
ROUTES = {"home": "/", "products": "/products", "add": "/products/add", "edit": "/products/{id}/edit",
          "login": "/login", "logout": "/logout", "ar": "/ar.html", "api": "/api/products",
          "css": "/css/site.css", "js": "/js/app.js"}
DEBUG = {"file": "src/products/products.controller.ts", "match": "const rows = this.store.list(", "path": "/products"}
DEBUG_TIMEOUT = 300
INTELLI = {"file": "src/products/products.service.ts", "after": "list(q: string)", "type": "this.db.prep",
           "expect": "prepare", "timeout": 60, "settle": 5.0,
           "html_file": "public/index.html", "css_file": "public/css/site.css"}
PUBLISH_EXPECT = ["package.json", "src/main.ts", "src/products/products.controller.ts", "public/index.html",
                  "public/ar.html", "public/css/site.css"]
PUBLISH_FORBID = ["data/store.db"]
PUBLISH_EXCLUDES = ["node_modules", "dist"]
RUN_TIMEOUT = 1500
PUBLISHED_TIMEOUT = 600


def toolchain_check():
    import subprocess
    try:
        out = subprocess.run(["node", "-e", "require('node:sqlite');console.log('ok')"], capture_output=True,
                             text=True, timeout=30).stdout
    except OSError as e:
        return f"node: {e}"
    return "" if "ok" in out else "node:sqlite needs Node.js 22.13+"


def serve_published(dest, port, **_):
    """The host: npm install, nest build, node dist/main."""
    import os
    import shutil
    import subprocess
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    for argv in ([npm, "install", "--no-audit", "--no-fund"], [npm, "run", "build"]):
        r = subprocess.run(argv, cwd=str(dest), capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            return None, f"{' '.join(argv[1:])} failed in the published folder: {(r.stdout + r.stderr)[-400:]}", None
    return [shutil.which("node"), "dist/main.js"], str(dest), dict(os.environ, PORT=str(port), NODE_ENV="production")


DB_SQL = """-- RAD Store schema (Databases workspace)
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  price REAL NOT NULL DEFAULT 0
);
INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450);
"""

MAIN = """import { NestFactory } from '@nestjs/core';
import { NestExpressApplication } from '@nestjs/platform-express';
import { join } from 'path';
import { randomBytes } from 'crypto';
import { AppModule } from './app.module';

// in-memory sessions (cookie "sid") with a CSRF token
const sessions = new Map<string, Record<string, string>>();

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule);
  app.use((req: any, res: any, next: () => void) => {
    const m = /(?:^|;\\s*)sid=([a-f0-9]{32})/.exec(req.headers.cookie || '');
    let sid = m && sessions.has(m[1]) ? m[1] : '';
    if (!sid) {
      sid = randomBytes(16).toString('hex');
      sessions.set(sid, { csrf: randomBytes(16).toString('hex') });
      res.setHeader('Set-Cookie', `sid=${sid}; HttpOnly; SameSite=Lax; Path=/`);
    }
    req.session = sessions.get(sid);
    next();
  });
  app.useStaticAssets(join(process.cwd(), 'public'));
  await app.listen(process.env.PORT ?? 3000, '127.0.0.1');
  console.log(`Application is running on: ${await app.getUrl()}`);
}
bootstrap();
"""

APP_MODULE = """import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { ProductsModule } from './products/products.module';

@Module({
  imports: [ProductsModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
"""

APP_CONTROLLER = """import { Controller, Get } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get('health')
  health() {
    return { status: 'ok', message: this.appService.getHello(), time: new Date().toISOString() };
  }
}
"""

SERVICE = """import { Injectable } from '@nestjs/common';
import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'fs';
import { join } from 'path';

export interface Product { id: number; name: string; price: number; }

@Injectable()
export class ProductsService {
  private readonly db: DatabaseSync;

  constructor() {
    mkdirSync(join(process.cwd(), 'data'), { recursive: true });
    this.db = new DatabaseSync(join(process.cwd(), 'data', 'store.db'));
    this.db.exec('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL DEFAULT 0)');
    const n = this.db.prepare('SELECT COUNT(*) AS n FROM products').get() as { n: number };
    if (n.n === 0) {
      this.db.exec("INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450)");
    }
  }

  list(q: string): Product[] {
    return this.db.prepare('SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY id').all(`%${q}%`) as unknown as Product[];
  }

  find(id: number): Product | undefined {
    return this.db.prepare('SELECT id, name, price FROM products WHERE id = ?').get(id) as unknown as Product | undefined;
  }

  add(name: string, price: number) { this.db.prepare('INSERT INTO products (name, price) VALUES (?, ?)').run(name, price); }

  update(id: number, name: string, price: number) {
    this.db.prepare('UPDATE products SET name = ?, price = ? WHERE id = ?').run(name, price, id);
  }

  remove(id: number) { this.db.prepare('DELETE FROM products WHERE id = ?').run(id); }

  validate(body: any): { errors: string[]; name: string; price: number } {
    const errors: string[] = [];
    const name = String(body?.name ?? '').trim();
    const price = Number(body?.price);
    if (!name) errors.push('Name is required');
    if (body?.price === undefined || body?.price === '' || !Number.isFinite(price) || price < 0) {
      errors.push('Price must be a positive number');
    }
    return { errors, name, price };
  }
}
"""

CONTROLLER = r"""import { Body, Controller, Get, Param, ParseIntPipe, Post, Query, Req, Res } from '@nestjs/common';
import type { Request, Response } from 'express';
import { timingSafeEqual } from 'crypto';
import { ProductsService } from './products.service';

const esc = (s: unknown) => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' } as any)[c]);
const sess = (req: Request) => (req as any).session as Record<string, string>;

function page(req: Request, title: string, body: string): string {
  const u = sess(req).user;
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)} - RAD Store</title><link rel="stylesheet" href="/css/site.css"></head><body>
<nav class="top"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar.html">العربية</a>
${u ? `<span class="user">${esc(u)}</span> <a href="/logout">Log out</a>` : '<a href="/login">Log in</a>'}</nav>
<main>${body}</main><script src="/js/app.js"></script></body></html>`;
}

function form(req: Request, errors: string[], name: unknown, price: unknown, extra = ''): string {
  return errors.map(e => `<p class="error">${esc(e)}</p>`).join('') +
    `<form method="post" class="product"><input type="hidden" name="csrf" value="${sess(req).csrf}">
<label>Name <input name="name" value="${esc(name)}" required></label>
<label>Price <input name="price" value="${esc(price)}" type="number" step="0.01" min="0"></label>
<button type="submit">Save</button></form>${extra}`;
}

@Controller()
export class ProductsController {
  constructor(private readonly store: ProductsService) {}

  private guard(req: Request, res: Response, body?: any): boolean {
    if (!sess(req).user) {
      res.redirect('/login?next=' + encodeURIComponent(req.originalUrl));
      return false;
    }
    if (req.method === 'POST' && body?.csrf !== sess(req).csrf) {
      res.status(400).send('Bad CSRF token');
      return false;
    }
    return true;
  }

  @Get('products')
  list(@Req() req: Request, @Res() res: Response, @Query('q') q = '') {
    const rows = this.store.list(q);
    const user = sess(req).user;
    const trs = rows.map(p => `<tr data-id="${p.id}"><td class="name">${esc(p.name)}</td><td>${p.price.toFixed(2)}</td>
<td>${user ? `<a href="/products/${p.id}/edit">Edit</a>` : ''}</td></tr>`).join('');
    res.type('html').send(page(req, 'Products', `<h1>Products</h1>
${user ? '<p><a class="btn" href="/products/add">Add product</a></p>' : ''}
<table id="products"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>${trs}</tbody></table>
<p class="count">${rows.length} products</p>`));
  }

  @Get('products/add')
  addForm(@Req() req: Request, @Res() res: Response) {
    if (!this.guard(req, res)) return;
    res.type('html').send(page(req, 'Add product', '<h1>Add product</h1>' + form(req, [], '', '')));
  }

  @Post('products/add')
  add(@Req() req: Request, @Res() res: Response, @Body() body: any) {
    if (!this.guard(req, res, body)) return;
    const v = this.store.validate(body);
    if (v.errors.length) {
      return res.status(422).type('html').send(page(req, 'Add product', '<h1>Add product</h1>' + form(req, v.errors, v.name, body.price)));
    }
    this.store.add(v.name, v.price);
    res.redirect('/products');
  }

  @Get('products/:id/edit')
  editForm(@Req() req: Request, @Res() res: Response, @Param('id', ParseIntPipe) id: number) {
    if (!this.guard(req, res)) return;
    const p = this.store.find(id);
    if (!p) return res.status(404).send('Not found');
    const del = `<form method="post" action="/products/${id}/delete" class="delete"><input type="hidden" name="csrf" value="${sess(req).csrf}"><button type="submit">Delete</button></form>`;
    res.type('html').send(page(req, 'Edit product', '<h1>Edit product</h1>' + form(req, [], p.name, p.price, del)));
  }

  @Post('products/:id/edit')
  edit(@Req() req: Request, @Res() res: Response, @Param('id', ParseIntPipe) id: number, @Body() body: any) {
    if (!this.guard(req, res, body)) return;
    if (!this.store.find(id)) return res.status(404).send('Not found');
    const v = this.store.validate(body);
    if (v.errors.length) {
      return res.status(422).type('html').send(page(req, 'Edit product', '<h1>Edit product</h1>' + form(req, v.errors, v.name, body.price)));
    }
    this.store.update(id, v.name, v.price);
    res.redirect('/products');
  }

  @Post('products/:id/delete')
  remove(@Req() req: Request, @Res() res: Response, @Param('id', ParseIntPipe) id: number, @Body() body: any) {
    if (!this.guard(req, res, body)) return;
    this.store.remove(id);
    res.redirect('/products');
  }

  private loginForm(req: Request, error: string): string {
    const next = String(req.query.next || '/products');
    return `<h1>Log in</h1>${error ? `<p class="error">${esc(error)}</p>` : ''}
<form method="post" class="login"><input type="hidden" name="csrf" value="${sess(req).csrf}">
<input type="hidden" name="next" value="${esc(next)}">
<label>User name <input name="username"></label><label>Password <input name="password" type="password"></label>
<button type="submit">Log in</button></form>`;
  }

  @Get('login')
  loginPage(@Req() req: Request, @Res() res: Response) {
    res.type('html').send(page(req, 'Log in', this.loginForm(req, '')));
  }

  @Post('login')
  login(@Req() req: Request, @Res() res: Response, @Body() body: any) {
    if (body?.csrf !== sess(req).csrf) return res.status(400).send('Bad CSRF token');
    const ok = body.username === 'admin' &&
      timingSafeEqual(Buffer.from(String(body.password ?? '').padEnd(32)), Buffer.from('secret'.padEnd(32)));
    if (!ok) return res.status(401).type('html').send(page(req, 'Log in', this.loginForm(req, 'Invalid user name or password')));
    sess(req).user = 'admin';
    const next = String(body.next || '/products');
    res.redirect(next.startsWith('/') ? next : '/products');
  }

  @Get('logout')
  logout(@Req() req: Request, @Res() res: Response) {
    delete sess(req).user;
    res.redirect('/');
  }

  @Get('api/products')
  api() {
    return this.store.list('');
  }
}
"""

MODULE = """import { Module } from '@nestjs/common';
import { ProductsController } from './products.controller';
import { ProductsService } from './products.service';

@Module({
  controllers: [ProductsController],
  providers: [ProductsService],
})
export class ProductsModule {}
"""

INDEX = """<!DOCTYPE html>
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
nav.top { background: #e0234e; padding: 10px 16px; }
nav.top a, nav.top .user { color: #fff; margin-inline-end: 14px; text-decoration: none; }
main { max-width: 900px; margin: 20px auto; padding: 0 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: start; }
.error { color: #b00020; font-weight: bold; }
.hero { padding: 40px 20px; background: linear-gradient(90deg, #e0234e, #f06292); color: #fff; border-radius: 12px; }
"""


def files():
    return {"src/main.ts": MAIN, "src/app.module.ts": APP_MODULE, "src/app.controller.ts": APP_CONTROLLER,
            "src/products/products.service.ts": SERVICE, "src/products/products.controller.ts": CONTROLLER,
            "src/products/products.module.ts": MODULE, "public/index.html": INDEX, "public/ar.html": AR,
            "public/css/site.css": CSS,
            "public/js/app.js": "// RAD Store\ndocument.addEventListener('DOMContentLoaded', () => { document.body.dataset.ready = '1'; });\n"}
