<?php
/*
 * ShopSite - settings.
 *
 * Everything in app/ and data/ lives OUTSIDE the web root (public/), so the
 * browser can never download this file, the SQLite database or the sessions.
 */
return [
    // Shown in the header and the <title> of every page.
    'app_name' => 'ShopSite',

    // URL prefix when the site is not at the root of the domain, e.g. '/shop'.
    // Leave empty for http://localhost:8080/ (RAD IDE dev server) or a domain root.
    'base_url' => '',

    // Database engine: 'sqlite' (default - a file, no server needed) or 'mysql' (MySQL / MariaDB).
    // The environment variables APP_DB_DRIVER / APP_DB_HOST / APP_DB_PORT / APP_DB_NAME / APP_DB_USER /
    // APP_DB_PASSWORD override these settings (keep real passwords out of this file on a server).
    'db_driver' => getenv('APP_DB_DRIVER') ?: 'sqlite',

    // SQLite database file (created automatically with its tables on first use).
    'db_path' => dirname(__DIR__) . '/data/app.sqlite',

    // MySQL / MariaDB (the tables are created on first use; the database must exist).
    // RAD IDE: Databases dock > Local Servers > "Start local MariaDB/MySQL" starts a local server with
    // user 'radide' and database 'radide'; "Copy MariaDB/MySQL Password" copies its password.
    'mysql' => [
        'host' => getenv('APP_DB_HOST') ?: '127.0.0.1',
        'port' => (int) (getenv('APP_DB_PORT') ?: 3306),
        'dbname' => getenv('APP_DB_NAME') ?: 'radide',
        'user' => getenv('APP_DB_USER') ?: 'radide',
        'password' => getenv('APP_DB_PASSWORD') ?: '',
    ],

    // PHP session files are kept in the project so the app is self-contained.
    'session_path' => dirname(__DIR__) . '/data/sessions',
    'session_name' => 'APPSESSID',
    // Log out after this many seconds without a request.
    'session_idle_timeout' => 1800,

    // Login throttling: after this many failed attempts (per IP or per user name)
    // within the window, further attempts are refused until the window passes.
    'login_max_attempts' => 5,
    'login_window_seconds' => 900,

    'password_min_length' => 8,
    'products_per_page' => 10,
];
