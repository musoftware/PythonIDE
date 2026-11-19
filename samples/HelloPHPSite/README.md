# HelloPHPSite

A complete PHP + SQLite data application created by the RAD IDE App Gallery
("PHP + SQLite Data App" template): user accounts, secure login and a
**Products** module with list / search / sort / pagination / add / edit / delete.

## Run it

In RAD IDE press **F5** (the dev server runs `php -S` with `public/` as the web root
and the Preview window opens). From a terminal:

```
php -S 127.0.0.1:8080 -t public
```

then open <http://127.0.0.1:8080/>, click **Register** and create the first account.
Requires PHP 8.1+ with the `pdo_sqlite` extension (`php -m` lists it). If it is not
enabled, add `extension=pdo_sqlite` to php.ini or run
`php -d extension=pdo_sqlite -S 127.0.0.1:8080 -t public`.

The database `data/app.sqlite` and its tables are created on the first request.
Open it in the IDE's **Databases** workspace (SQLite file) to browse the tables.

## Folders

| Path | What |
|---|---|
| `public/` | the web root - the only folder the browser can reach |
| `public/index.php` | home page / dashboard |
| `public/login.php`, `register.php`, `logout.php`, `account.php` | accounts |
| `public/products/` | the CRUD module: `index.php` (list + search), `create.php`, `edit.php`, `delete.php` |
| `public/assets/` | `css/site.css` (responsive, no framework), `js/site.js` |
| `app/bootstrap.php` | included by every page: settings, helpers, security headers, session |
| `app/config.php` | settings (app name, base URL, database path, timeouts) |
| `app/helpers.php` | `e()` escaping, `url()`, `redirect()`, flash messages, CSRF, layout |
| `app/db.php` | PDO connection + schema (`PRAGMA user_version` migrations) |
| `app/auth.php` | register, login, logout, change password, login throttling |
| `app/products.php` | product search / validation / create / update / delete |
| `app/views/` | `header.php`, `footer.php` (layout) and `product_form.php` |
| `data/` | `app.sqlite` and PHP session files (created at run time) |

## Security

- Passwords: `password_hash()` / `password_verify()` (bcrypt), re-hashed when PHP's default
  algorithm changes; minimum length 8.
- Sessions: `session_regenerate_id(true)` on login, logout and password change; strict mode,
  HttpOnly + SameSite=Lax cookies (Secure on HTTPS); idle timeout (30 min).
- **CSRF**: every POST form contains `csrf_field()` and every POST handler calls
  `verify_csrf()` (403 when the token is missing or wrong). Logout and delete are POST-only.
- SQL: **PDO prepared statements** with bound parameters everywhere; `ORDER BY` uses a
  whitelist; LIKE wildcards in searches are escaped.
- Output: everything printed goes through `e()` (`htmlspecialchars`).
- Login throttling: 5 failed attempts per IP or user name in 15 minutes locks further attempts;
  unknown users take the same time as wrong passwords.
- Headers: Content-Security-Policy (no inline scripts), X-Frame-Options, X-Content-Type-Options,
  Referrer-Policy. `display_errors` is off.
- `app/` and `data/` are outside the web root (plus `.htaccess` deny files for Apache hosts
  where the whole folder is uploaded).

## Add another module (e.g. Customers)

1. Add the table to `migrate()` in `app/db.php` under a new `if ($version < 2)` block.
2. Copy `app/products.php` to `app/customers.php`, rename the functions and fields, and
   `require` it in `app/bootstrap.php`.
3. Copy `public/products/` to `public/customers/` and `app/views/product_form.php`.
4. Add a link to `$nav` in `app/views/header.php`.

## Publish

Upload the whole folder and make `public/` the document root of the site (or use the IDE's
**Publish** command). If the site lives in a sub-folder, set `base_url` in `app/config.php`.
The `data/` folder must be writable by the web server.
