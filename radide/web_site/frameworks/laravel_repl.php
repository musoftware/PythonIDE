<?php
// RAD IDE - Tinker console (radide/features/php_frameworks.py).
// A persistent PHP REPL inside the booted Laravel application: variables survive between commands, like
// `php artisan tinker`, but it talks over plain pipes (one JSON request per line) so it works on Windows
// without a terminal. Usage: php laravel_repl.php <project folder>
// Request:  {"code": "Post::count()"}\n      Reply: output lines, then "__RADIDE_DONE__".

$__base = $argv[1] ?? getcwd();
chdir($__base);
require $__base . '/vendor/autoload.php';
$app = require $__base . '/bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

// short model names as in tinker: Post::count() instead of App\Models\Post::count()
foreach (glob($__base . '/app/Models/*.php') ?: [] as $__f) {
    $__short = basename($__f, '.php');
    $__class = 'App\\Models\\' . $__short;
    if (!class_exists($__short, false) && class_exists($__class)) {
        class_alias($__class, $__short);
    }
}
unset($__f, $__short, $__class);

function __radide_present($v, int $depth = 0): string
{
    if ($v === null) return 'null';
    if (is_bool($v)) return $v ? 'true' : 'false';
    if (is_int($v) || is_float($v)) return var_export($v, true);
    if (is_string($v)) return var_export($v, true);
    $flags = JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PARTIAL_OUTPUT_ON_ERROR;
    if (is_array($v)) return json_encode($v, $flags) ?: print_r($v, true);
    if ($v instanceof Illuminate\Database\Eloquent\Model || $v instanceof Illuminate\Contracts\Support\Arrayable) {
        return get_class($v) . ' ' . (json_encode($v->toArray(), $flags) ?: '{...}');
    }
    if ($v instanceof Closure) return 'Closure';
    if ($v instanceof DateTimeInterface) return get_class($v) . ' ' . $v->format(DATE_ATOM);
    if ($v instanceof JsonSerializable) return get_class($v) . ' ' . json_encode($v, $flags);
    if (method_exists($v, '__toString')) return get_class($v) . ' ' . var_export((string) $v, true);
    return get_class($v) . ' ' . substr(print_r($v, true), 0, 4000);
}

fwrite(STDOUT, "Laravel " . $app->version() . " (PHP " . PHP_VERSION . ") - type PHP; variables are kept.\n__RADIDE_DONE__\n");
fflush(STDOUT);

while (($__line = fgets(STDIN)) !== false) {
    $__req = json_decode($__line, true);
    if (!is_array($__req)) {
        continue;
    }
    $__code = rtrim(trim((string) ($__req['code'] ?? '')), "; \t\n\r");
    if ($__code === 'exit' || $__code === 'quit') {
        break;
    }
    ob_start();
    try {
        try {
            $__result = eval('return ' . $__code . ';');
            $__has = true;
        } catch (ParseError $__e) {
            $__has = false;
            eval($__code . ';');
        }
        $__out = ob_get_clean();
        echo $__out;
        if ($__out !== '' && substr($__out, -1) !== "\n") echo "\n";
        if ($__has) echo '=> ' . __radide_present($__result) . "\n";
    } catch (Throwable $__e) {
        $__out = ob_get_clean();
        echo $__out;
        echo get_class($__e) . ': ' . $__e->getMessage() . "\n";
    }
    echo "__RADIDE_DONE__\n";
    fflush(STDOUT);
}
