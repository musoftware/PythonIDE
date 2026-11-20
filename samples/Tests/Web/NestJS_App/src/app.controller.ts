import { Controller, Get, Header } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  @Header('Content-Type', 'text/html; charset=utf-8')
  home(): string {
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>NestApp1</title>
<style>body{font-family:"Segoe UI",sans-serif;margin:40px;background:#f5f6f8}h1{color:#e0234e}</style></head>
<body><h1>NestApp1</h1><p>${this.appService.getHello()}</p>
<p><a href="/products">/products</a> (JSON) - <a href="/health">/health</a></p></body></html>`;
  }

  @Get('health')
  health() {
    return { status: 'ok', time: new Date().toISOString() };
  }
}
