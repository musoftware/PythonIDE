<?php
/*
 * RAD IDE - RAD Hub worker for PHP modules.
 *
 *   php radworker.php <module file>        (cwd = project folder)
 *
 *   stdin : {"id": 7, "func": "add", "args": [2, 3]}
 *   stdout: {"id": 7, "result": 5}   or   {"id": 7, "error": "message"}
 * Anything the module prints (echo) is sent to stderr so stdout stays clean JSON lines.
 */
require_once __DIR__ . DIRECTORY_SEPARATOR . 'radgui.php';
$GLOBALS['__rad_out'] = STDERR;

$file = $argv[1] ?? '';
if ($file === '') {
    fwrite(STDERR, "usage: php radworker.php <module file>\n");
    exit(2);
}
$folder = getenv('RAD_PROJECT') ?: getcwd();
$path = (preg_match('/^([A-Za-z]:)?[\\\\\/]/', $file) ? $file : $folder . DIRECTORY_SEPARATOR . $file);

function rad__worker_reply(array $obj): void
{
    $text = json_encode($obj, JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION | JSON_PARTIAL_OUTPUT_ON_ERROR);
    if ($text === false) {
        $text = json_encode(['id' => $obj['id'] ?? null, 'error' => 'result is not JSON serializable']);
    }
    fwrite(STDOUT, $text . "\n");
    fflush(STDOUT);
}

$loadError = null;
$autoload = $folder . DIRECTORY_SEPARATOR . 'vendor' . DIRECTORY_SEPARATOR . 'autoload.php';
ob_start(function ($buf) { if ($buf !== '') fwrite(STDERR, $buf); return ''; }, 1);
try {
    if (is_file($autoload)) require_once $autoload;
    require_once $path;
} catch (\Throwable $t) {
    $loadError = $t->getMessage() . ' (line ' . $t->getLine() . ')';
    fwrite(STDERR, "[radworker] error loading $file: $loadError\n");
}
ob_end_flush();

while (($line = fgets(STDIN)) !== false) {
    $line = trim($line);
    if ($line === '') continue;
    $req = json_decode($line, true);
    if (!is_array($req)) {
        rad__worker_reply(['id' => null, 'error' => 'bad request: ' . json_last_error_msg()]);
        continue;
    }
    $id = $req['id'] ?? null;
    ob_start(function ($buf) { if ($buf !== '') fwrite(STDERR, $buf); return ''; }, 1);
    try {
        if ($loadError !== null) throw new RuntimeException("module $file failed to load: $loadError");
        $parts = explode('.', (string)($req['func'] ?? ''));
        $name = end($parts);
        if (!preg_match('/^\w+$/', $name) || !function_exists($name)) {
            throw new RuntimeException("function '$name' not found in $file");
        }
        $args = is_array($req['args'] ?? null) ? array_values($req['args']) : [];
        $result = $name(...$args);
        ob_end_flush();
        rad__worker_reply(['id' => $id, 'result' => $result]);
    } catch (\Throwable $t) {
        ob_end_flush();
        rad__worker_reply(['id' => $id, 'error' => $t->getMessage()]);
    }
}
