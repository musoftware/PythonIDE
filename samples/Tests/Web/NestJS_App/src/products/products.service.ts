import { Injectable, NotFoundException } from '@nestjs/common';

export interface Product { id: number; name: string; price: number; }

@Injectable()
export class ProductsService {
  private readonly products: Product[] = [
    { id: 1, name: 'Keyboard', price: 25 },
    { id: 2, name: 'Mouse', price: 12.5 },
  ];

  findAll(): Product[] {
    return this.products;
  }

  findOne(id: number): Product {
    const p = this.products.find((x) => x.id === id);
    if (!p) throw new NotFoundException(`Product ${id} not found`);
    return p;
  }

  create(data: Omit<Product, 'id'>): Product {
    const p = { id: this.products.length + 1, ...data };
    this.products.push(p);
    return p;
  }
}
