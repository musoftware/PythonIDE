<?php
/*
 * RAD IDE - RAD Hub worker for PHP modules.
 *
 *   php radworker.php <module file>        (cwd = project folder)
 *
 *   stdin : {"id": 7, "func": "add", "args": [2, 3]}
 *   stdout: {"id": 7, "result": 5}   or   {"id": 7, "error": "message"}
 * radcall() inside a worker (RAD_WORKER=1) goes through stdout/stdin:
 *   stdout: {"id": "w1", "call": "Other.f", "args": [...]}  ->  stdin: {"id": "w1", "result": ...}
 * and keeps serving "func" requests while it waits (so call-backs cannot deadlock).
 * Anything the module prints (echo) is sent to stderr so stdout stays clean JSON lines.
 */
require_once __DIR__ . DIRECTORY_SEPARATOR . 'radgui.php';
$GLOBALS['__rad_worker'] = true;

$file = $argv[1] ?? '';
if ($file === '') {
    fwrite(STDERR, "usage: php radworker.php <module file>\n");
    exit(2);
}
$base = getenv('RAD_PROJECT') ?: getcwd();
$isAbs = preg_match('/^([A-Za-z]:)?[\\\\\/]/', $file);
$path = $isAbs ? $file : $base . DIRECTORY_SEPARATOR . $file;
// the module's own project folder (a referenced library may live outside RAD_PROJECT)
$folder = dirname($path);
$GLOBALS['__radw_file'] = $file;
$GLOBALS['__radw_load_error'] = null;
$GLOBALS['__radw_answers'] = [];
$GLOBALS['__radw_next'] = 1;

function rad__worker_send(array $obj): void
{
    $flags = JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION | JSON_PARTIAL_OUTPUT_ON_ERROR;
    $text = json_encode($obj, $flags);
    if ($text === false) {
        $text = json_encode(['id' => $obj['id'] ?? null, 'error' => 'result is not JSON serializable']);
    }
    fwrite(STDOUT, $text . "\n");
    fflush(STDOUT);
}

function rad__worker_stderr_start(): void
{
    ob_start(function ($buf) {
        if ($buf !== '') fwrite(STDERR, $buf);
        return '';
    }, 1);
}

/** Handle one stdin line: a request ("func") or the answer to one of our nested radcalls. */
function rad__worker_line(string $line): void
{
    $msg = json_decode($line, true);
    if (!is_array($msg)) {
        rad__worker_send(['id' => null, 'error' => 'bad request: ' . json_last_error_msg()]);
        return;
    }
    if (!array_key_exists('func', $msg)) {
        $GLOBALS['__radw_answers'][(string)($msg['id'] ?? '')] = $msg;
        return;
    }
    $id = $msg['id'] ?? null;
    $file = $GLOBALS['__radw_file'];
    rad__worker_stderr_start();
    try {
        if ($GLOBALS['__radw_load_error'] !== null) {
            throw new RuntimeException("module $file failed to load: " . $GLOBALS['__radw_load_error']);
        }
        $parts = explode('.', (string)$msg['func']);
        $name = end($parts);
        if (!preg_match('/^\w+$/', $name) || !function_exists($name)) {
            throw new RuntimeException("function '$name' not found in $file");
        }
        $args = is_array($msg['args'] ?? null) ? array_values($msg['args']) : [];
        $result = $name(...$args);
        ob_end_flush();
        rad__worker_send(['id' => $id, 'result' => $result]);
    } catch (\Throwable $t) {
        ob_end_flush();
        rad__worker_send(['id' => $id, 'error' => $t->getMessage()]);
    }
}

$GLOBALS['__rad_worker_call'] = function (string $name, array $args) {
    $id = 'w' . $GLOBALS['__radw_next']++;
    rad__worker_send(['id' => $id, 'call' => $name, 'args' => $args]);
    for (;;) {
        if (isset($GLOBALS['__radw_answers'][$id])) {
            $reply = $GLOBALS['__radw_answers'][$id];
            unset($GLOBALS['__radw_answers'][$id]);
            if (isset($reply['error'])) throw new RuntimeException("radcall $name: " . $reply['error']);
            return $reply['result'] ?? null;
        }
        $line = fgets(STDIN);
        if ($line === false) throw new RuntimeException("radcall $name: RAD Hub closed the worker's input");
        $line = trim($line);
        if ($line !== '') rad__worker_line($line);
    }
};
if (getenv('RAD_WORKER') !== '1') {
    unset($GLOBALS['__rad_worker_call']);       // outside the hub: radcall uses TCP (RAD_HUB)
}

// ------------------------------------------------------------------ load the module
rad__worker_stderr_start();
try {
    $autoload = $folder . DIRECTORY_SEPARATOR . 'vendor' . DIRECTORY_SEPARATOR . 'autoload.php';
    if (is_file($autoload)) require_once $autoload;
    // a form's code file may use functions of the project's modules: load those first
    $proj = @json_decode((string)@file_get_contents($folder . DIRECTORY_SEPARATOR . 'project.radproj'), true);
    $mods = is_array($proj['modules'] ?? null) ? $proj['modules'] : [];
    $lower = array_map('strtolower', $mods);
    if (!in_array(strtolower(basename($file)), $lower, true)) {
        foreach ($mods as $m) {
            if (strtolower(pathinfo($m, PATHINFO_EXTENSION)) === 'php') {
                try {
                    require_once $folder . DIRECTORY_SEPARATOR . $m;
                } catch (\Throwable $t) {
                    fwrite(STDERR, "[radworker] error loading $m: " . $t->getMessage() . "\n");
                }
            }
        }
    }
    rad_load_references($folder);           // libraries this project references
    require_once $path;
} catch (\Throwable $t) {
    $GLOBALS['__radw_load_error'] = $t->getMessage() . ' (line ' . $t->getLine() . ')';
    fwrite(STDERR, "[radworker] error loading $file: " . $GLOBALS['__radw_load_error'] . "\n");
}
ob_end_flush();

// ------------------------------------------------------------------ serve
while (($line = fgets(STDIN)) !== false) {
    $line = trim($line);
    if ($line !== '') rad__worker_line($line);
}
