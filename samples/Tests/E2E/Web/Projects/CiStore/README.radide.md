# CiStore (CodeIgniter 4.7.6)

Created by RAD IDE with `composer create-project codeigniter4/appstarter`.

- **Run**: F5 (debug, Xdebug breakpoints in controllers / models / views) or Ctrl+F5 - the site runs with
  `public/index.php` + CodeIgniter's `rewrite.php` (what `php spark serve` does) behind the IDE's server
  (Preview, Requests, live reload).
- **Spark**: View > CodeIgniter (Spark commands with forms, Routes - double-click opens the controller).
- **Database**: SQLite3 (`writable/database.db`); settings in `.env`.
- IntelliSense: view(), route_to()/url_to(), lang(), config(), helper(), service(), model fields - read from
  this project; F12 on such a string opens its file.
