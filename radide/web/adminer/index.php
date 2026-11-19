<?php
/*
 * RAD IDE launcher for the bundled Adminer 6.3.0 (adminer.php - https://www.adminer.org/,
 * (c) Jakub Vrana, Apache License 2.0 or GPL 2.0, see LICENSE.txt).
 *
 * RAD IDE serves this folder with "php -S 127.0.0.1:<private port>" (radide/web_site/databases.py,
 * AdminerServer). The IDE passes a random token in the environment (RADIDE_ADMINER_TOKEN) and opens
 *     /?radide_auth=<token>&radide_driver=sqlite|server|pgsql&radide_server=..&radide_user=..&radide_db=..&radide_secret=<key>
 * which logs in without showing the login form. Passwords of MySQL/PostgreSQL connections are never put
 * in a URL: they are passed in RADIDE_ADMINER_SECRETS (JSON {key: password}) and looked up by key.
 * A normal manual login (real user name + password) keeps working.
 */
if (PHP_SAPI !== 'cli-server') {
    http_response_code(403);
    exit('This Adminer launcher is served by RAD IDE only.');
}

function radide_token()
{
    $t = getenv('RADIDE_ADMINER_TOKEN');
    return (is_string($t) && strlen($t) >= 16) ? $t : null;
}

function radide_secret($key)
{
    $all = json_decode((string) getenv('RADIDE_ADMINER_SECRETS'), true);
    return (is_array($all) && isset($all[$key])) ? (string) $all[$key] : '';
}

/** "<token>:<secret key>" when the session was opened by the IDE, else null. */
function radide_ide_password($password)
{
    $t = radide_token();
    if ($t === null || !is_string($password) || strncmp($password, $t . ':', strlen($t) + 1) !== 0) {
        return null;
    }
    return substr($password, strlen($t) + 1);
}

if (isset($_GET['radide_auth']) && radide_token() !== null
        && hash_equals(radide_token(), (string) $_GET['radide_auth'])) {
    $_POST['auth'] = array(
        'driver' => (string) (isset($_GET['radide_driver']) ? $_GET['radide_driver'] : 'sqlite'),
        'server' => (string) (isset($_GET['radide_server']) ? $_GET['radide_server'] : ''),
        'username' => (string) (isset($_GET['radide_user']) ? $_GET['radide_user'] : ''),
        'password' => radide_token() . ':' . (string) (isset($_GET['radide_secret']) ? $_GET['radide_secret'] : ''),
        'db' => (string) (isset($_GET['radide_db']) ? $_GET['radide_db'] : ''),
    );
    foreach (array_keys($_GET) as $k) {
        if (strncmp($k, 'radide_', 7) === 0) {
            unset($_GET[$k]);
        }
    }
    // Adminer builds its links and the after-login redirect from the request URI: drop our parameters.
    $qs = http_build_query($_GET);
    $_SERVER['QUERY_STRING'] = $qs;
    $_SERVER['REQUEST_URI'] = strtok($_SERVER['REQUEST_URI'], '?') . ($qs !== '' ? '?' . $qs : '');
}

function adminer_object()
{
    return new class extends \Adminer\Adminer {
        function name()
        {
            return "<a href='https://www.adminer.org/' target='_blank' rel='noreferrer noopener' id='h1'>Adminer</a>"
                . " <small style='font-weight:normal'>in RAD IDE</small>";
        }

        // The IDE's automatic login carries the random token instead of Adminer's CSRF form token.
        function verifyLoginToken()
        {
            // the login form normally creates the CSRF token; without it Adminer would report
            // "Session expired" instead of the real error when the database refuses the connection
            if (session_status() === PHP_SESSION_ACTIVE && empty($_SESSION['token'])) {
                $_SESSION['token'] = rand(1, 1e6);
            }
            return false;
        }

        function credentials()
        {
            $password = \Adminer\get_password();
            $key = radide_ide_password($password);
            if ($key !== null) {
                $password = radide_secret($key);
            }
            return array(\Adminer\SERVER, $_GET['username'], $password);
        }

        function login($login, $password)
        {
            if (radide_ide_password($password) !== null) {
                return true;
            }
            return parent::login($login, $password);
        }
    };
}

include __DIR__ . '/adminer.php';
