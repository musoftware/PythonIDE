<?php
/*
 * {{APP_NAME}} - settings.
 *
 * Everything in app/ and data/ lives OUTSIDE the web root (public/), so the
 * browser can never download this file, the SQLite database or the sessions.
 */
return [
    // Shown in the header and the <title> of every page.
    'app_name' => '{{APP_NAME}}',

    // URL prefix when the site is not at the root of the domain, e.g. '/shop'.
    // Leave empty for http://localhost:8080/ (RAD IDE dev server) or a domain root.
    'base_url' => '',

    // SQLite database file (created automatically with its tables on first use).
    'db_path' => dirname(__DIR__) . '/data/app.sqlite',

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
