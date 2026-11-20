import { Body, Controller, Get, Param, ParseIntPipe, Post } from '@nestjs/common';
import { Product, ProductsService } from './products.service';

@Controller('products')
export class ProductsController {
  constructor(private readonly products: ProductsService) {}

  @Get()
  findAll(): Product[] {
    return this.products.findAll();
  }

  @Get(':id')
  findOne(@Param('id', ParseIntPipe) id: number): Product {
    return this.products.findOne(id);
  }

  @Post()
  create(@Body() body: { name: string; price: number }): Product {
    return this.products.create({ name: body.name, price: Number(body.price) || 0 });
  }
}
