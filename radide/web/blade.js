// Laravel Blade language for Monaco (RAD IDE, radide/features/php_frameworks.py injects this file).
// HTML + {{ echo }}, {!! raw !!}, {{-- comments --}}, @directives (args tokenized as PHP), @php ... @endphp,
// <x-components>, <script> / <style> blocks embedded as JavaScript / CSS.
(function () {
  if (window.__radBlade || !window.monaco) return;
  window.__radBlade = true;
  const L = monaco.languages;
  if (!L.getLanguages().some(l => l.id === 'blade'))
    L.register({ id: 'blade', aliases: ['Blade', 'Laravel Blade'], extensions: ['.blade.php'] });

  const phpKeywords = ['abstract', 'and', 'array', 'as', 'break', 'callable', 'case', 'catch', 'class', 'clone',
    'const', 'continue', 'declare', 'default', 'do', 'echo', 'else', 'elseif', 'empty', 'enum', 'extends', 'false',
    'final', 'finally', 'fn', 'for', 'foreach', 'function', 'global', 'if', 'implements', 'include', 'instanceof',
    'insteadof', 'interface', 'isset', 'list', 'match', 'namespace', 'new', 'null', 'or', 'print', 'private',
    'protected', 'public', 'readonly', 'require', 'return', 'static', 'switch', 'throw', 'trait', 'true', 'try',
    'unset', 'use', 'var', 'while', 'xor', 'yield'];

  // PHP expression rules shared by {{ }}, {!! !!}, @directive( ) and @php blocks
  const phpExpr = [
    [/\$[a-zA-Z_]\w*/, 'variable'],
    [/[a-zA-Z_]\w*(?=\s*\()/, { cases: { '@phpKeywords': 'keyword', '@default': 'function' } }],
    [/[A-Z]\w*(?=::)/, 'type.identifier'],
    [/[a-zA-Z_]\w*/, { cases: { '@phpKeywords': 'keyword', '@default': 'identifier' } }],
    [/\d+(\.\d+)?/, 'number'],
    [/'([^'\\]|\\.)*'/, 'string'],
    [/"([^"\\]|\\.)*"/, 'string'],
    [/->|=>|::|\?\?|[-+*\/%=!<>&|.?:]+/, 'operator'],
    [/[;,]/, 'delimiter'],
  ];

  L.setMonarchTokensProvider('blade', {
    defaultToken: '',
    tokenPostfix: '.blade',
    ignoreCase: true,
    phpKeywords: phpKeywords,
    tokenizer: {
      root: [
        [/\{\{--/, 'comment.blade', '@bladeComment'],
        [/@\{\{/, ''],                                            // escaped: @{{ shown as is
        [/\{\{/, { token: 'delimiter.blade', next: '@echo' }],
        [/\{!!/, { token: 'delimiter.blade', next: '@raw' }],
        [/@(php)\b(?!\s*\()/, { token: 'keyword.blade', next: '@phpBlock' }],
        [/@(verbatim)\b/, { token: 'keyword.blade', next: '@verbatim' }],
        [/(^|\s|>)(@[a-zA-Z_]\w*)(\s*)(\()/, ['', 'keyword.blade', '', { token: 'delimiter.parenthesis.blade', next: '@directiveArgs' }]],
        [/@[a-zA-Z_]\w*/, 'keyword.blade'],
        [/<!--/, 'comment', '@htmlComment'],
        [/<!DOCTYPE/, 'metatag', '@doctype'],
        [/(<)(script)/, ['delimiter', { token: 'tag', next: '@script' }]],
        [/(<)(style)/, ['delimiter', { token: 'tag', next: '@style' }]],
        [/(<\/?)(x-[\w.:-]+)/, ['delimiter', { token: 'type.identifier.component', next: '@tag' }]],
        [/(<\/?)([\w\-:]+)/, ['delimiter', { token: 'tag', next: '@tag' }]],
        [/<\/?/, 'delimiter'],
        [/[^<@{]+/, ''],
        [/[@{]/, ''],
      ],
      bladeComment: [[/--\}\}/, 'comment.blade', '@pop'], [/./, 'comment.blade']],
      htmlComment: [[/-->/, 'comment', '@pop'], [/[^-]+/, 'comment'], [/./, 'comment']],
      doctype: [[/[^>]+/, 'metatag.content'], [/>/, 'metatag', '@pop']],
      echo: [[/\}\}/, { token: 'delimiter.blade', next: '@pop' }], ...phpExpr, [/\s+/, ''], [/./, '']],
      raw: [[/!!\}/, { token: 'delimiter.blade', next: '@pop' }], ...phpExpr, [/\s+/, ''], [/./, '']],
      directiveArgs: [
        [/\(/, { token: 'delimiter.parenthesis.blade', next: '@directiveArgs' }],
        [/\)/, { token: 'delimiter.parenthesis.blade', next: '@pop' }],
        ...phpExpr, [/\s+/, ''], [/./, ''],
      ],
      phpBlock: [[/[@]endphp\b/, { token: 'keyword.blade', next: '@pop' }], [/\/\/.*$/, 'comment'], ...phpExpr,
                 [/\s+/, ''], [/./, '']],
      verbatim: [[/[@]endverbatim\b/, { token: 'keyword.blade', next: '@pop' }], [/[^@]+/, ''], [/@/, '']],
      tag: [
        [/\{\{--/, 'comment.blade', '@bladeComment'],
        [/\{\{/, { token: 'delimiter.blade', next: '@echo' }],
        [/\{!!/, { token: 'delimiter.blade', next: '@raw' }],
        [/(^|\s)(@[a-zA-Z_]\w*)(\s*)(\()/, ['', 'keyword.blade', '', { token: 'delimiter.parenthesis.blade', next: '@directiveArgs' }]],
        [/@[a-zA-Z_]\w*/, 'keyword.blade'],
        [/(:[\w.\-:]+)(\s*=\s*)(")/, ['attribute.name.bound', 'delimiter', { token: 'string', next: '@boundAttr' }]],
        [/"([^"]*)"/, 'attribute.value'],
        [/'([^']*)'/, 'attribute.value'],
        [/[\w\-:.]+/, 'attribute.name'],
        [/=/, 'delimiter'],
        [/\/?>/, { token: 'delimiter', next: '@pop' }],
        [/\s+/, ''],
      ],
      boundAttr: [[/"/, { token: 'string', next: '@pop' }], ...phpExpr, [/\s+/, ''], [/./, '']],
      script: [
        [/[^>]*>/, { token: 'delimiter', next: '@scriptBody', nextEmbedded: 'text/javascript' }],
      ],
      scriptBody: [[/<\/script\s*>/, { token: 'tag', next: '@popall', nextEmbedded: '@pop' }]],
      style: [
        [/[^>]*>/, { token: 'delimiter', next: '@styleBody', nextEmbedded: 'text/css' }],
      ],
      styleBody: [[/<\/style\s*>/, { token: 'tag', next: '@popall', nextEmbedded: '@pop' }]],
    },
  });

  L.setLanguageConfiguration('blade', {
    wordPattern: /(-?\d*\.\d\w*)|([^\`\~\!\#\%\^\&\*\(\)\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)/g,
    comments: { blockComment: ['{{--', '--}}'] },
    brackets: [['<!--', '-->'], ['{{--', '--}}'], ['{{', '}}'], ['{!!', '!!}'], ['<', '>'], ['(', ')'], ['[', ']'], ['{', '}']],
    autoClosingPairs: [{ open: '{{--', close: ' --}}' }, { open: '{!!', close: ' !!}' }, { open: '{', close: '}' },
      { open: '[', close: ']' }, { open: '(', close: ')' }, { open: '"', close: '"' }, { open: "'", close: "'" }],
    surroundingPairs: [{ open: '"', close: '"' }, { open: "'", close: "'" }, { open: '<', close: '>' },
      { open: '{', close: '}' }, { open: '(', close: ')' }],
    folding: { markers: { start: /^\s*(<!--\s*#region\b.*-->|@(if|foreach|forelse|for|while|section|push|auth|guest|can|unless|isset|empty|switch|component|slot|php|once|env|production|error)\b)/,
                          end: /^\s*(<!--\s*#endregion\b.*-->|@(endif|endforeach|endforelse|endfor|endwhile|endsection|stop|show|endpush|endauth|endguest|endcan|endunless|endisset|endempty|endswitch|endcomponent|endslot|endphp|endonce|endenv|endproduction|enderror)\b)/ } },
    onEnterRules: [],
  });
})();
