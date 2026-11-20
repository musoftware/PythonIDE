# CodeIgniter Shop (RAD IDE sample)

A small but real **CodeIgniter 4.7** application to try RAD IDE's CodeIgniter support:

| Feature | Where |
|---|---|
| Products CRUD with validation (model rules, `is_unique` on update, flash messages, search, pagination) | `app/Controllers/Products.php`, `app/Models/ProductModel.php`, `app/Views/products/` |
| Simple login: `password_verify`, session id regenerated on sign-in, sign-out, an `auth` route filter | `app/Controllers/Auth.php`, `app/Filters/AuthFilter.php`, `app/Config/Filters.php` |
| CSRF protection for every POST form (`csrf_field()` is added by `form_open()`), except `api/*` | `app/Config/Filters.php` |
| Migrations + seeders (demo user and products) | `app/Database/Migrations/`, `app/Database/Seeds/` |
| A layout view with sections and a partial | `app/Views/layouts/main.php`, `app/Views/partials/flash.php` |
| A JSON API: `GET /api/products[?q=]`, `GET /api/products/{id}` | `app/Controllers/Api/Products.php` |
| Own config class, helper and language file | `app/Config/Shop.php`, `app/Helpers/shop_helper.php`, `app/Language/en/Shop.php` |

`vendor/` is not in the sample (Composer installs it) and neither is `.env` (copied from `.env.example`).

## Try it in RAD IDE

1. **File > Open Project** and choose this folder. The IDE offers **composer install** (it uses the site's
   PHP - Tools > PHP Versions... - and the portable Composer), creates `.env` and then offers
   **php spark migrate --all + db:seed DatabaseSeeder** (SQLite: `writable/database.db`).
2. **Ctrl+F5** runs the site in the Preview (CodeIgniter's `rewrite.php` behind the IDE's server: Requests list,
   live reload). Sign in with **admin@example.com / secret123**.
3. **F5** = debug: set a breakpoint (F9) in `Products::index` or in a view, reload the Preview - Locals,
   Call Stack, Watch, F10/F11 (Xdebug).
4. **View > CodeIgniter Panel**: *Spark* lists every `php spark` command - double-click for a form
   (make:controller, make:model, make:migration, migrate, db:seed ...; the new file opens), *Routes*
   (`php spark routes`, double-click = controller method, right-click > Open in Preview).
5. IntelliSense read from this project (and updated when you change it), inside the strings of:
   `view('` (app/Views), `url_to('` / `route_to('` / `redirect()->route('` (route names), `site_url('` /
   `base_url('` (paths), `lang('Shop.` (language keys), `config('` and `config('Shop')->` (config classes and
   properties), `helper('` + the functions of loaded helpers (`money(`), `service('`, `model('`, model fields
   in `->where('` / `$product['` / `insert(['` / `$allowedFields`, validation rules (`'required|...'`),
   `$this->section('`, `env('` and `'Products::edit'` handlers in Routes.php. **F12** on such a string opens
   the view / route / language line / config property / controller method.

Without the IDE: `composer install`, `copy .env.example .env`, `php spark migrate --all`,
`php spark db:seed DatabaseSeeder`, `php spark serve`.
