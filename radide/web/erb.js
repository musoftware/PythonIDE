// ERB (Embedded Ruby) language for Monaco - Rails / Sinatra views (radide/features/rails_ide.py injects this file).
// HTML + <%# comments %>, <%= output %>, <% code %>, <%- -%> trimming; the Ruby inside is tokenized by Monaco's
// own Ruby language (nextEmbedded), <script> / <style> blocks as JavaScript / CSS.
(function () {
  if (window.__radErb || !window.monaco) return;
  window.__radErb = true;
  const L = monaco.languages;
  if (!L.getLanguages().some(l => l.id === 'erb'))
    L.register({ id: 'erb', aliases: ['ERB', 'Embedded Ruby', 'erb'], extensions: ['.erb', '.rhtml'] });

  const erbOpen = [
    [/<%#/, 'comment.erb', '@erbComment'],
    [/<%%/, ''],                                                     // escaped: literal <%
    [/<%[=-]?/, { token: 'delimiter.erb', next: '@erbRuby', nextEmbedded: 'ruby' }],
  ];

  L.setMonarchTokensProvider('erb', {
    defaultToken: '',
    tokenPostfix: '.erb',
    ignoreCase: true,
    tokenizer: {
      root: [
        ...erbOpen,
        [/<!--/, 'comment', '@htmlComment'],
        [/<!DOCTYPE/, 'metatag', '@doctype'],
        [/(<)(script)/, ['delimiter', { token: 'tag', next: '@script' }]],
        [/(<)(style)/, ['delimiter', { token: 'tag', next: '@style' }]],
        [/(<\/?)([\w\-:]+)/, ['delimiter', { token: 'tag', next: '@tag' }]],
        [/<\/?/, 'delimiter'],
        [/[^<]+/, ''],
      ],
      erbComment: [[/-?%>/, 'comment.erb', '@pop'], [/[^%-]+/, 'comment.erb'], [/./, 'comment.erb']],
      // the Ruby segment: everything up to %> goes to the embedded Ruby tokenizer
      erbRuby: [
        [/-?%>/, { token: 'delimiter.erb', next: '@pop', nextEmbedded: '@pop' }],
        [/[^%-]+/, ''],
        [/[%-]/, ''],
      ],
      htmlComment: [[/-->/, 'comment', '@pop'], [/[^-]+/, 'comment'], [/./, 'comment']],
      doctype: [[/[^>]+/, 'metatag.content'], [/>/, 'metatag', '@pop']],
      tag: [
        ...erbOpen,
        [/"/, { token: 'attribute.value', next: '@attrDouble' }],
        [/'/, { token: 'attribute.value', next: '@attrSingle' }],
        [/[\w\-:.@]+/, 'attribute.name'],
        [/=/, 'delimiter'],
        [/\/?>/, { token: 'delimiter', next: '@pop' }],
        [/\s+/, ''],
      ],
      attrDouble: [...erbOpen, [/"/, { token: 'attribute.value', next: '@pop' }], [/[^"<]+/, 'attribute.value'],
                   [/</, 'attribute.value']],
      attrSingle: [...erbOpen, [/'/, { token: 'attribute.value', next: '@pop' }], [/[^'<]+/, 'attribute.value'],
                   [/</, 'attribute.value']],
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

  L.setLanguageConfiguration('erb', {
    wordPattern: /(-?\d*\.\d\w*)|([^\`\~\!\#\%\^\&\*\(\)\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\s]+[?!]?)/g,
    comments: { blockComment: ['<%#', '%>'] },
    brackets: [['<!--', '-->'], ['<%', '%>'], ['<', '>'], ['(', ')'], ['[', ']'], ['{', '}']],
    autoClosingPairs: [{ open: '<%', close: ' %>' }, { open: '{', close: '}' }, { open: '[', close: ']' },
      { open: '(', close: ')' }, { open: '"', close: '"' }, { open: "'", close: "'" }],
    surroundingPairs: [{ open: '"', close: '"' }, { open: "'", close: "'" }, { open: '<', close: '>' },
      { open: '{', close: '}' }, { open: '(', close: ')' }],
    folding: { markers: { start: /^\s*(<!--\s*#region\b.*-->|<%[-=]?.*\b(do|if|unless|each|case)\b.*%>)/,
                          end: /^\s*(<!--\s*#endregion\b.*-->|<%-?\s*end\s*-?%>)/ } },
  });
})();
