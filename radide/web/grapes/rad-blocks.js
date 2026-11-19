/* RAD IDE Design View: protected code component (PHP / script blocks) and the Toolbox blocks
   (HTML, Layout, Bootstrap, PHP). Loaded as a GrapesJS plugin by designer.js. */
(function () {
  'use strict';

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  window.radEsc = esc;

  function ico(text) {
    return '<svg viewBox="0 0 48 32" width="48" height="32"><rect x="1" y="1" width="46" height="30" rx="4" ' +
      'fill="none" stroke="currentColor" stroke-width="1.5"/><text x="24" y="21" text-anchor="middle" ' +
      'font-family="Segoe UI, sans-serif" font-size="12" fill="currentColor">' + esc(text) + '</text></svg>';
  }

  function raw(code, label) {
    return '<rad-raw data-rad-code="' + esc(code) + '" data-rad-label="' + esc(label || code) + '"></rad-raw>';
  }

  const LAYOUT_CSS = '<style>.rad-section{padding:40px 20px}.rad-container{max-width:1140px;margin:0 auto;padding:0 15px}' +
    '.rad-row{display:flex;flex-wrap:wrap;gap:16px}.rad-col{flex:1 1 0;min-width:160px;min-height:60px;padding:10px}' +
    '.rad-header{display:flex;align-items:center;justify-content:space-between;padding:12px 20px;background:#222;color:#fff}' +
    '.rad-header a{color:#fff;margin-left:16px;text-decoration:none}' +
    '.rad-footer{padding:20px;text-align:center;background:#f2f2f2;color:#555}</style>';

  function radRaw(editor) {
    const dc = editor.DomComponents;
    dc.addType('rad-raw', {
      isComponent: el => el.tagName === 'RAD-RAW',
      model: {
        defaults: {
          tagName: 'rad-raw', droppable: false, editable: false, stylable: false, copyable: true,
          draggable: true, removable: true, highlightable: true, traits: [], name: 'Code',
          attributes: { contenteditable: 'false' },
        },
        init() {
          const a = this.getAttributes();
          const lbl = a['data-rad-label'] || 'code';
          this.set('name', (lbl.indexOf('<script') === 0 ? 'Script: ' : lbl.indexOf('<style') === 0 ? 'Style: ' : 'PHP: ') +
            lbl.slice(0, 40));
        },
        toHTML() {
          const a = this.getAttributes();
          if (a['data-rad-code'] != null)
            return '<rad-raw data-rad-code="' + esc(a['data-rad-code']) + '"></rad-raw>';
          return '<rad-raw data-rad-id="' + esc(a['data-rad-id'] || '') + '"></rad-raw>';
        },
      },
      view: {
        events: { dblclick: 'onEdit' },
        onEdit(ev) {
          ev && ev.stopPropagation();
          const a = this.model.getAttributes();
          if (window.radEditRaw) window.radEditRaw(this.model.cid, a['data-rad-id'] || '', a['data-rad-code'] == null ? null : a['data-rad-code']);
        },
      },
    });
  }

  function radBlocks(editor) {
    radRaw(editor);
    const bm = editor.BlockManager;
    const add = (id, label, category, content, icon) =>
      bm.add('rad-' + id, { label, category, content, media: ico(icon || label) });

    // ---------------------------------------------------------------- HTML
    const H = 'HTML';
    add('h1', 'Heading 1', H, '<h1>Heading 1</h1>', 'H1');
    add('h2', 'Heading 2', H, '<h2>Heading 2</h2>', 'H2');
    add('h3', 'Heading 3', H, '<h3>Heading 3</h3>', 'H3');
    add('p', 'Paragraph', H, '<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>', 'P');
    add('ul', 'Bulleted list', H, '<ul><li>Item one</li><li>Item two</li><li>Item three</li></ul>', 'UL');
    add('ol', 'Numbered list', H, '<ol><li>First</li><li>Second</li><li>Third</li></ol>', 'OL');
    add('quote', 'Quote', H, '<blockquote>A wise quotation.</blockquote>', '“ ”');
    add('hr', 'Horizontal line', H, '<hr/>', 'HR');
    add('a', 'Hyperlink', H, '<a href="#">Link text</a>', 'A');
    add('btn', 'Button', H, '<button type="button">Button</button>', 'BTN');
    add('table', 'Table', H,
      '<table border="1" style="border-collapse:collapse"><thead><tr><th>Header 1</th><th>Header 2</th></tr></thead>' +
      '<tbody><tr><td>Cell</td><td>Cell</td></tr><tr><td>Cell</td><td>Cell</td></tr></tbody></table>', 'TBL');
    add('div', 'Div', H, '<div style="padding:10px;min-height:50px"></div>', 'DIV');
    add('span', 'Span', H, '<span>text</span>', 'SPAN');
    add('iframe', 'Inline frame', H, '<iframe src="about:blank" width="400" height="300"></iframe>', 'IFR');

    // ---------------------------------------------------------------- Layout
    const L = 'Layout';
    add('section', 'Section', L, LAYOUT_CSS + '<section class="rad-section"><div class="rad-container"><h2>Section title</h2><p>Section text.</p></div></section>', 'SEC');
    add('container', 'Container', L, LAYOUT_CSS + '<div class="rad-container"></div>', 'BOX');
    add('cols2', '2 Columns', L, LAYOUT_CSS + '<div class="rad-row"><div class="rad-col"></div><div class="rad-col"></div></div>', '| |');
    add('cols3', '3 Columns', L, LAYOUT_CSS + '<div class="rad-row"><div class="rad-col"></div><div class="rad-col"></div><div class="rad-col"></div></div>', '|||');
    add('header', 'Header + nav', L, LAYOUT_CSS + '<header class="rad-header"><strong>My Site</strong><nav><a href="index.php">Home</a><a href="about.php">About</a><a href="contact.php">Contact</a></nav></header>', 'HDR');
    add('footer', 'Footer', L, LAYOUT_CSS + '<footer class="rad-footer">&copy; My Site</footer>', 'FTR');
    add('article', 'Article', L, '<article><h2>Article title</h2><p>Article text.</p></article>', 'ART');
    add('aside', 'Sidebar (aside)', L, '<aside style="padding:10px;min-height:80px"></aside>', 'ASD');

    // ---------------------------------------------------------------- Bootstrap 5 (needs bootstrap.css: toolbar "Bootstrap")
    const B = 'Bootstrap';
    add('bs-navbar', 'Navbar', B,
      '<nav class="navbar navbar-expand-lg navbar-dark bg-dark"><div class="container"><a class="navbar-brand" href="#">Brand</a>' +
      '<ul class="navbar-nav me-auto"><li class="nav-item"><a class="nav-link active" href="#">Home</a></li>' +
      '<li class="nav-item"><a class="nav-link" href="#">About</a></li><li class="nav-item"><a class="nav-link" href="#">Contact</a></li></ul></div></nav>', 'NAV');
    add('bs-hero', 'Hero', B,
      '<div class="p-5 mb-4 bg-light rounded-3"><div class="container py-4"><h1 class="display-5 fw-bold">Hello, world</h1>' +
      '<p class="col-md-8 fs-5">A big welcome message.</p><a class="btn btn-primary btn-lg" href="#">Get started</a></div></div>', 'HERO');
    add('bs-grid', 'Grid row (3)', B,
      '<div class="container"><div class="row"><div class="col-md-4"><p>Column</p></div><div class="col-md-4"><p>Column</p></div>' +
      '<div class="col-md-4"><p>Column</p></div></div></div>', 'ROW');
    add('bs-card', 'Card', B,
      '<div class="card" style="width:18rem"><div class="card-body"><h5 class="card-title">Card title</h5>' +
      '<p class="card-text">Some quick example text.</p><a href="#" class="btn btn-primary">Go somewhere</a></div></div>', 'CARD');
    add('bs-btn', 'Button', B, '<a href="#" class="btn btn-primary">Primary</a>', 'BTN');
    add('bs-alert', 'Alert', B, '<div class="alert alert-info" role="alert">A simple info alert.</div>', '!');
    add('bs-badge', 'Badge', B, '<span class="badge bg-secondary">New</span>', 'BDG');
    add('bs-table', 'Table', B,
      '<table class="table table-striped"><thead><tr><th>#</th><th>Name</th><th>Email</th></tr></thead>' +
      '<tbody><tr><td>1</td><td>Ali</td><td>ali@example.com</td></tr><tr><td>2</td><td>Mona</td><td>mona@example.com</td></tr></tbody></table>', 'TBL');
    add('bs-form', 'Login form', B,
      '<form method="post" class="p-3" style="max-width:360px"><div class="mb-3"><label class="form-label" for="email">Email</label>' +
      '<input class="form-control" type="email" id="email" name="email"/></div><div class="mb-3"><label class="form-label" for="password">Password</label>' +
      '<input class="form-control" type="password" id="password" name="password"/></div><button class="btn btn-primary" type="submit">Sign in</button></form>', 'FORM');

    // ---------------------------------------------------------------- PHP (protected code blocks)
    const P = 'PHP';
    add('php-echo', 'Echo', P, raw('<?= htmlspecialchars($value) ?>'), '<?=');
    add('php-code', 'PHP block', P, raw('<?php\n// code\n?>', '<?php // code ?>'), 'PHP');
    add('php-include', 'Include', P, raw("<?php include __DIR__ . '/header.php'; ?>"), 'INC');
    add('php-if', 'If / endif', P,
      raw('<?php if ($condition): ?>') + '<p>Shown when the condition is true.</p>' + raw('<?php endif; ?>'), 'IF');
    add('php-foreach', 'Foreach list', P,
      '<ul>' + raw('<?php foreach ($items as $item): ?>') + '<li>' + raw('<?= htmlspecialchars($item) ?>') + '</li>' +
      raw('<?php endforeach; ?>') + '</ul>', 'FOR');
  }

  window.radBlocks = radBlocks;
})();
