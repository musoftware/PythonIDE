// RAD IDE snippets for Monaco (VS Code snippet syntax: $1, ${1:placeholder}, $0; a literal $ is \$).
// Loaded by editor.html; each language gets a completion provider with these items.
(function () {
  const S = (prefix, description, lines) => ({ prefix: prefix, description: description, body: lines.join('\n') });

  const HTML = [
    S('html5', 'HTML5 page', [
      '<!DOCTYPE html>', '<html lang="${1:en}">', '<head>', '    <meta charset="utf-8">',
      '    <meta name="viewport" content="width=device-width, initial-scale=1">', '    <title>${2:Page title}</title>',
      '    <link rel="stylesheet" href="${3:css/site.css}">', '</head>', '<body>', '    $0', '</body>', '</html>']),
    S('bootstrap5', 'HTML5 page with Bootstrap 5 (CDN)', [
      '<!DOCTYPE html>', '<html lang="en">', '<head>', '    <meta charset="utf-8">',
      '    <meta name="viewport" content="width=device-width, initial-scale=1">', '    <title>${1:Page title}</title>',
      '    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">',
      '</head>', '<body>', '    <div class="container py-4">', '        $0', '    </div>',
      '    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>',
      '</body>', '</html>']),
    S('linkcss', 'Stylesheet link', ['<link rel="stylesheet" href="${1:style.css}">']),
    S('scriptsrc', 'External script', ['<script src="${1:app.js}"${2: defer}></script>']),
    S('metavp', 'Viewport meta tag', ['<meta name="viewport" content="width=device-width, initial-scale=1">']),
    S('form', 'Form with a text field and submit button', [
      '<form method="${1|post,get|}" action="${2:}">', '    <label for="${3:name}">${4:Name}</label>',
      '    <input type="${5:text}" id="$3" name="$3" required>', '    <button type="submit">${6:Send}</button>', '</form>']),
    S('table', 'Table with header', [
      '<table>', '    <thead>', '        <tr><th>${1:Column 1}</th><th>${2:Column 2}</th></tr>', '    </thead>',
      '    <tbody>', '        <tr><td>$3</td><td>$4</td></tr>', '    </tbody>', '</table>']),
    S('nav', 'Navigation bar', [
      '<nav>', '    <ul>', '        <li><a href="${1:index.html}">${2:Home}</a></li>',
      '        <li><a href="${3:about.html}">${4:About}</a></li>', '    </ul>', '</nav>']),
    S('img', 'Image with alt text', ['<img src="${1:image.png}" alt="${2:description}">']),
    S('comment', 'HTML comment', ['<!-- $0 -->']),
  ];

  const PHP = [
    S('php', 'PHP block', ['<?php', '$0', '?>']),
    S('echo', 'Short echo tag', ['<?= ${1:\\$value} ?>']),
    S('h', 'Escaped echo (htmlspecialchars)', ['<?= htmlspecialchars(${1:\\$value}, ENT_QUOTES, \'UTF-8\') ?>']),
    S('if', 'if statement', ['if (${1:condition}) {', '    $0', '}']),
    S('ifelse', 'if / else', ['if (${1:condition}) {', '    $2', '} else {', '    $0', '}']),
    S('ifalt', 'if (alternative syntax for templates)', ['<?php if (${1:condition}): ?>', '    $0', '<?php endif; ?>']),
    S('foreach', 'foreach loop', ['foreach (${1:\\$items} as ${2:\\$item}) {', '    $0', '}']),
    S('foreachkv', 'foreach with key => value', ['foreach (${1:\\$items} as ${2:\\$key} => ${3:\\$value}) {', '    $0', '}']),
    S('foreachalt', 'foreach (alternative syntax for templates)', [
      '<?php foreach (${1:\\$items} as ${2:\\$item}): ?>', '    $0', '<?php endforeach; ?>']),
    S('for', 'for loop', ['for (\\$${1:i} = 0; \\$$1 < ${2:\\$count}; \\$$1++) {', '    $0', '}']),
    S('while', 'while loop', ['while (${1:condition}) {', '    $0', '}']),
    S('switch', 'switch statement', ['switch (${1:\\$value}) {', '    case ${2:1}:', '        $0', '        break;',
      '    default:', '        break;', '}']),
    S('match', 'match expression (PHP 8)', ['\\$${1:result} = match (${2:\\$value}) {', '    ${3:1} => ${4:\'one\'},',
      '    default => ${5:null},', '};']),
    S('function', 'function', ['function ${1:name}(${2:\\$arg}): ${3:void}', '{', '    $0', '}']),
    S('fn', 'arrow function', ['fn(${1:\\$x}) => ${0:\\$x}']),
    S('class', 'class with constructor', ['class ${1:Name}', '{', '    public function __construct(${2:private string \\$name})',
      '    {', '        $0', '    }', '}']),
    S('method', 'public method', ['public function ${1:name}(${2}): ${3:void}', '{', '    $0', '}']),
    S('try', 'try / catch', ['try {', '    $1', '} catch (${2:Exception} \\$e) {', '    ${0:error_log(\\$e->getMessage());}', '}']),
    S('include', 'include a file', ['include __DIR__ . \'/${1:header.php}\';']),
    S('require_once', 'require_once a file', ['require_once __DIR__ . \'/${1:config.php}\';']),
    S('session', 'start the session', ['if (session_status() !== PHP_SESSION_ACTIVE) {', '    session_start();', '}']),
    S('post', 'handle a POST request', ['if (\\$_SERVER[\'REQUEST_METHOD\'] === \'POST\') {',
      '    \\$${1:name} = trim(\\$_POST[\'$1\'] ?? \'\');', '    $0', '}']),
    S('get', 'read a GET parameter', ['\\$${1:id} = \\$_GET[\'$1\'] ?? ${2:null};']),
    S('redirect', 'redirect and exit', ['header(\'Location: ${1:index.php}\');', 'exit;']),
    S('pdosqlite', 'PDO connection (SQLite)', [
      '\\$pdo = new PDO(\'sqlite:\' . __DIR__ . \'/${1:data/app.db}\');',
      '\\$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);',
      '\\$pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);']),
    S('pdomysql', 'PDO connection (MySQL)', [
      '\\$pdo = new PDO(\'mysql:host=${1:localhost};dbname=${2:app};charset=utf8mb4\', \'${3:user}\', \'${4:password}\', [',
      '    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,', '    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,', ']);']),
    S('query', 'prepared SELECT (PDO)', [
      '\\$stmt = \\$pdo->prepare(\'SELECT ${1:*} FROM ${2:table} WHERE ${3:id} = ?\');',
      '\\$stmt->execute([${4:\\$id}]);', '\\$${5:rows} = \\$stmt->fetchAll();']),
    S('insert', 'prepared INSERT (PDO)', [
      '\\$stmt = \\$pdo->prepare(\'INSERT INTO ${1:table} (${2:name}) VALUES (?)\');',
      '\\$stmt->execute([${3:\\$name}]);', '\\$id = \\$pdo->lastInsertId();']),
    S('passwordhash', 'hash a password', ['\\$hash = password_hash(${1:\\$password}, PASSWORD_DEFAULT);']),
    S('passwordverify', 'verify a password', ['if (password_verify(${1:\\$password}, ${2:\\$hash})) {', '    $0', '}']),
    S('csrf', 'CSRF token (create + check)', [
      'if (empty(\\$_SESSION[\'csrf\'])) {', '    \\$_SESSION[\'csrf\'] = bin2hex(random_bytes(32));', '}',
      'if (\\$_SERVER[\'REQUEST_METHOD\'] === \'POST\' && !hash_equals(\\$_SESSION[\'csrf\'], \\$_POST[\'csrf\'] ?? \'\')) {',
      '    http_response_code(400);', '    exit(\'Invalid CSRF token\');', '}']),
    S('json', 'send a JSON response', ['header(\'Content-Type: application/json\');', 'echo json_encode(${1:\\$data});', 'exit;']),
    S('vardump', 'var_dump inside <pre>', ['echo \'<pre>\';', 'var_dump(${1:\\$value});', 'echo \'</pre>\';']),
    S('strict', 'declare(strict_types=1)', ['declare(strict_types=1);']),
  ];

  const CSS = [
    S('media', 'media query', ['@media (max-width: ${1:768px}) {', '    $0', '}']),
    S('flexcenter', 'flex: center content', ['display: flex;', 'align-items: center;', 'justify-content: center;']),
    S('grid', 'grid with columns', ['display: grid;', 'grid-template-columns: ${1:repeat(3, 1fr)};', 'gap: ${2:1rem};']),
    S('keyframes', '@keyframes animation', ['@keyframes ${1:fade} {', '    from { ${2:opacity: 0;} }', '    to { ${3:opacity: 1;} }', '}']),
    S('fontface', '@font-face', ['@font-face {', '    font-family: "${1:MyFont}";', '    src: url("${2:font.woff2}") format("woff2");', '}']),
    S('root', ':root custom properties', [':root {', '    --${1:main-color}: ${2:#0078d4};', '}']),
  ];

  window.RAD_SNIPPETS = { html: HTML, php: PHP.concat(HTML.filter(s => s.prefix !== 'comment')), css: CSS, scss: CSS, less: CSS };
})();
