# Laravel_Blog - a Laravel sample for RAD IDE

A small but complete Laravel 13 blog, made with the IDE's **New Project > Web > PHP Web Site > Laravel App**:

- **Posts CRUD** (`PostController`, resource routes): list with search and pages, show, create, edit, delete;
  validation (`$request->validate([...])`); only the author may edit or delete a post; drafts.
- **Comments** (`Comment` model, `hasMany` / `belongsTo`), from guests (name required) or signed-in users.
- **Authentication** with **Laravel Breeze** (Blade + Tailwind): register, login, password reset, profile.
- **Migrations + seeders + factories**: `posts`, `comments`; `DatabaseSeeder` makes a demo author
  (`demo@example.com` / `password`) with posts and comments.
- **Blade layout and components**: Breeze's `<x-app-layout>`, plus `<x-post-card :post="$post">` and
  `<x-alert type="info">` (`resources/views/components`), a form partial (`@include('posts.partials.form')`).
- **JSON API**: `/api/posts`, `/api/posts/{slug}`, `/api/status` (`routes/api.php`, `Api\PostApiController`).
- `config/blog.php` + `.env` keys (`BLOG_PER_PAGE` ...) and translations in `lang/en/blog.php`.

`vendor/`, `node_modules/`, `public/build/`, `.env` and the database are not part of the sample.

## Try it in RAD IDE

1. **File > Open Project** > `samples/Tests/Web/Laravel_Blog` (or copy the folder first).
2. The IDE sees a Laravel project that is not ready and offers to prepare it (Laravel panel >
   *Install Dependencies* does the same): `composer install`, `.env` from `.env.example`, `artisan key:generate`,
   `database/database.sqlite` + `artisan migrate --seed`, `npm install` + `npm run build` (Vite / Tailwind).
   PHP 8.3+ is chosen automatically (`web.php = "auto"`; Tools > PHP Versions... installs one).
3. **Ctrl+F5** runs it in the Preview (`php -S` with Laravel's `server.php` router behind the IDE's dev server:
   Requests log, live reload). **F5** runs it under **Xdebug**: put a breakpoint (F9) in
   `PostController::index` and open `/posts` in the Preview.
4. **Laravel panel** (View > Laravel Panel): *Artisan* lists every command with a form for its arguments
   (`make:model Tag -mcr`, `make:migration`, `migrate`, `db:seed` ...), *Routes* (`route:list`; double-click
   opens the controller method), *Tinker* (`Post::count()`, `$p = Post::first()`, `$p->comments`).
5. **IntelliSense from the project** (it follows your edits - add a route, view, config key or column and it
   is offered right away):
   - `route('` -> route names, `view('` -> views, `config('blog.` -> config keys, `__('blog.` -> translations,
     `env('` -> `.env` keys, `asset('` -> public files;
   - `$post->` -> columns (from the migrations / SQLite schema), relations (`user`, `comments`), accessors
     (`excerpt`); `Post::` -> query methods and scopes (`published`); `Post::where('` -> columns;
     `->with('` -> relations; `'title' => 'required|` -> validation rules;
   - Blade (`*.blade.php` open in the Blade language): `@fo` -> `@foreach` / `@forelse`, `<x-` -> components,
     `<x-alert` + space -> its props, `{{ $` -> the variables the controller passes (`$posts`, `$search`), and
     `$post->` inside `@foreach ($posts as $post)`;
   - **F12 / Ctrl+click** on `view('posts.index')`, `route('posts.show')`, `config('blog.per_page')`,
     `__('blog.created')`, `env('APP_KEY')` or `<x-post-card>` opens the target file at the right line.
   - intelephense also gets `_ide_helper.php` / `_ide_helper_models.php` (barryvdh/laravel-ide-helper,
     Laravel panel > *IDE Helper*) for facades and models.

## Without the IDE

```bat
composer install
copy .env.example .env
php artisan key:generate
type nul > database\database.sqlite
php artisan migrate --seed
npm install && npm run build
php artisan serve
```
