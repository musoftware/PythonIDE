# StarterSite

PHP Starter Site (RAD IDE App Gallery): shared layout includes, Home / About / Contact pages and a
contact form (validation, CSRF token, honeypot against bots; messages saved to `data/messages.jsonl`).

- Run: **F5** in RAD IDE, or `php -S 127.0.0.1:8080 -t public`.
- `public/` is the web root; `app/` (bootstrap + views) and `data/` stay private.
- Add a page: copy `public/about.php`, then add it to `$pages` in `app/bootstrap.php`.
