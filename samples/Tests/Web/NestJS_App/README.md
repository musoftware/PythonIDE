# NestJS_App

**nestjs-web (NestJS 11, TypeScript)** - New Project > Web > NestJS Web App > *NestJS App*: app module, controller,
service and a `products` resource (GET /products, GET /products/:id, POST /products, GET /health).

- **Ctrl+F5**: `npm install` (first run - node_modules was removed), then `nest start --watch` with the IDE's port.
- **F5**: `node --inspect -r ts-node/register src/main.ts` + vscode-js-debug: a breakpoint in
  `src/products/products.controller.ts` (`findAll`) stops when `/products` is opened. Tested.
- **Framework** dock: routes from `@Controller` / `@Get` ..., Nest CLI (`nest g controller|service|module|resource`),
  npm scripts. TypeScript IntelliSense from typescript-language-server.
