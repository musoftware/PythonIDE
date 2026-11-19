"""Web workspace (docs/CONTRACTS.md section 8): web site projects, development server, design view,
databases, publish, reports, SuperPreview and App Gallery.

- ``radide.web_site.project`` - is_website / site_root / start_page / list_files / templates (no UI)
- ``radide.web_site.server``  - DevServer (PHP built-in server, static files, Node.js) with request log
  and live reload
- ``radide.features.web_workspace`` - IDE integration: folder tree in Solution Explorer, Preview and
  Requests docks, ``win.open_file(path)``, Run/Stop, Site menu.

Hooks for other features (all on the main window ``win``)::

    win.web_server            # the running DevServer or None
    win.web_preview           # PreviewPane: .open_url(url), .reload(), .view (QWebEngineView), .show_dock()
    win.web_requests          # RequestsPane (the Requests dock)
    win.web_signals           # QObject: siteOpened(project), serverStarted(server), serverStopped(),
                              #          request(dict), reloaded(int)
    win.site_menu             # the "Site" menu (add your actions to it)
    win.open_file(path, line=None)
    win.run_website(project=None) / win.stop_website()
"""
from __future__ import annotations

from .project import (is_website, list_files, site_root, start_page, url_path_for,  # noqa: F401
                      web_config)

__all__ = ["is_website", "list_files", "site_root", "start_page", "url_path_for", "web_config"]
