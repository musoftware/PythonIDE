import { Body, Controller, Get, Param, ParseIntPipe, Post, Query, Req, Res } from '@nestjs/common';
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
