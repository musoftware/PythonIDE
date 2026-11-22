import { Injectable } from '@nestjs/common';
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
