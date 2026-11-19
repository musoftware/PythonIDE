<?php
/*
 * RAD IDE - GUI Bridge client for PHP.
 *
 * The IDE draws the forms; this program talks to it over stdin/stdout
 * (protocol in docs/CONTRACTS.md, section 1).
 *
 *   rad_set($obj, $prop, $value)          rad_set("lblOut", "Caption", "Hi")
 *   rad_get($obj, $prop)       : string   rad_get("txtA", "Text")
 *   rad_num($obj, $prop)       : float    property as a number
 *   rad_call($obj, $method, ...$args)     rad_call("lstLog", "AddItem", "line")
 *   rad_msgbox($text)   rad_input($prompt) : string
 *   rad_show($form)     rad_hide($form)    rad_end()
 *   radcall("Module.func", ...$args)      call a function of any project module (RAD Hub)
 * Handlers are functions named <Control>_<Event>($e); $e is an array with
 * X, Y, Button, KeyCode, KeyChar, args (mouse/key events, otherwise zeros).
 */

if (defined('RADGUI_LOADED')) {
    return;
}
define('RADGUI_LOADED', true);

$GLOBALS['__rad_out'] = STDOUT;
$GLOBALS['__rad_worker'] = false;   // set by radworker.php: no GUI protocol in a worker
$GLOBALS['__rad_ended'] = false;

function rad__line($v): string
{
    if ($v === true) return 'True';
    if ($v === false) return 'False';
    if ($v === null) return '';
    if (is_array($v) || is_object($v)) $v = json_encode($v);
    return preg_replace('/\r\n|\r|\n/', ' ', (string)$v);
}

function rad__send(string $text): void
{
    if (!empty($GLOBALS['__rad_worker'])) {
        throw new RuntimeException("'" . strtok($text, ' ') . "' is not available here: this module runs in a " .
            'RAD Hub worker (called with radcall), which has no form. Return a value instead.');
    }
    $out = $GLOBALS['__rad_out'];
    fwrite($out, $text . "\n");
    fflush($out);
}

function rad__read(): string
{
    $line = fgets(STDIN);
    if ($line === false) return '';
    return rtrim($line, "\r\n");
}

function rad_set(string $obj, string $prop, $value): void
{
    rad__send("SET $obj $prop " . rad__line($value));
}

function rad_get(string $obj, string $prop): string
{
    rad__send("GET $obj $prop");
    return rad__read();
}

function rad_num(string $obj, string $prop): float
{
    $s = str_replace(',', '.', trim(rad_get($obj, $prop)));
    return is_numeric($s) ? (float)$s : 0.0;
}

function rad_call(string $obj, string $method, ...$args): string
{
    $a = array_map(fn($x) => str_replace("\t", ' ', rad__line($x)), $args);
    rad__send("CALL $obj $method" . (count($a) ? ' ' . implode("\t", $a) : ''));
    return rad__read();
}

function rad_msgbox($text): string
{
    rad__send('MSGBOX ' . rad__line($text));
    return rad__read();
}

function rad_input(string $prompt): string
{
    rad__send('INPUT ' . rad__line($prompt));
    return rad__read();
}

function rad_show(string $form): void { rad__send("SHOW $form"); }
function rad_hide(string $form): void { rad__send("HIDE $form"); }

function rad_end(): void
{
    if (!$GLOBALS['__rad_ended']) {
        $GLOBALS['__rad_ended'] = true;
        rad__send('END');
    }
}

// ------------------------------------------------------------------ RAD Hub client
/** Call "<Module>.<function>" in any language of the project; returns the JSON result. */
function radcall(string $name, ...$args)
{
    static $sock = null, $nextId = 1;
    if (isset($GLOBALS['__rad_worker_call'])) {        // inside a RAD Hub worker: via stdout/stdin
        return ($GLOBALS['__rad_worker_call'])($name, $args);
    }
    if ($sock === null || feof($sock)) {
        $addr = getenv('RAD_HUB') ?: '';
        if ($addr === '' || strrpos($addr, ':') === false) {
            throw new RuntimeException('radcall: RAD Hub is not running (RAD_HUB is not set)');
        }
        $sock = @stream_socket_client("tcp://$addr", $errno, $errstr, 10);
        if (!$sock) {
            $sock = null;
            throw new RuntimeException("radcall: cannot connect to RAD Hub at $addr: $errstr");
        }
        stream_set_timeout($sock, 60);
    }
    $id = $nextId++;
    $req = json_encode(['id' => $id, 'call' => $name, 'args' => $args],
                       JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION);
    fwrite($sock, $req . "\n");
    $line = fgets($sock);
    if ($line === false) {
        $sock = null;
        throw new RuntimeException("radcall $name: RAD Hub closed the connection or timed out");
    }
    $reply = json_decode($line, true);
    if (!is_array($reply)) {
        throw new RuntimeException("radcall $name: bad reply from RAD Hub: $line");
    }
    if (isset($reply['error'])) {
        throw new RuntimeException("radcall $name: " . $reply['error']);
    }
    return $reply['result'] ?? null;
}

// ------------------------------------------------------------------ main loop
function rad__event_args(string $rest): array
{
    $p = $rest === '' ? [] : explode(' ', $rest);
    $n = fn($i) => isset($p[$i]) && is_numeric($p[$i]) ? $p[$i] + 0 : 0;
    return ['X' => $n(0), 'Y' => $n(1), 'Button' => $n(2), 'KeyCode' => $n(3),
            'KeyChar' => count($p) > 4 ? implode(' ', array_slice($p, 4)) : '', 'args' => $rest];
}

/** Include the reference proxies (<Lib>.ref.php) of a project folder: they define the classes
 *  <Lib> (MathLib::Add(2, 3)) and functions <Lib>_<name> of referenced library projects. */
function rad_load_references(string $folder): void
{
    $refs = glob(rtrim($folder, '\/') . DIRECTORY_SEPARATOR . '*.ref.php') ?: [];
    sort($refs);
    foreach ($refs as $r) {
        try {
            require_once $r;
        } catch (\Throwable $t) {
            fwrite(STDERR, '[error loading reference ' . basename($r) . '] ' . $t->getMessage() . "\n");
        }
    }
}

/** Entry point of the generated _radmain.php: load the code files, then serve events. */
function rad_run_main(array $files): void
{
    ob_implicit_flush(true);
    while (ob_get_level() > 0) ob_end_flush();
    $autoload = getcwd() . DIRECTORY_SEPARATOR . 'vendor' . DIRECTORY_SEPARATOR . 'autoload.php';
    if (is_file($autoload)) require_once $autoload;          // composer packages
    rad_load_references(getcwd());
    foreach ($files as $f) {
        try {
            require_once $f;
        } catch (\Throwable $t) {
            fwrite(STDERR, "[error loading $f] " . $t->getMessage() . ' (line ' . $t->getLine() . ")\n");
        }
    }
    while (($line = fgets(STDIN)) !== false) {
        $line = rtrim($line, "\r\n");
        if (strtoupper(trim($line)) === 'QUIT') break;
        if (strncmp($line, 'EVENT ', 6) !== 0) continue;
        $parts = explode(' ', $line, 4);
        $name = ($parts[1] ?? '') . '_' . ($parts[2] ?? '');
        try {
            if (preg_match('/^\w+$/', $name) && function_exists($name)) {
                $name(rad__event_args($parts[3] ?? ''));
            }
        } catch (\Throwable $t) {
            fwrite(STDERR, "[$name] " . get_class($t) . ': ' . $t->getMessage() . ' in ' .
                   basename($t->getFile()) . ' line ' . $t->getLine() . "\n");
        } finally {
            rad__send('DONE');
        }
        if ($GLOBALS['__rad_ended']) break;
    }
}
