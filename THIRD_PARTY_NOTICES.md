# Third-party components

RAD IDE's own code is under the MIT License (see `LICENSE`, © Musoftware - https://musoftwares.com).
It uses and bundles components that keep their own licenses:

| Component | Where | License |
| --- | --- | --- |
| PyQt6, PyQt6-WebEngine (Riverbank) | Python dependency | GPL v3 (or commercial) |
| Qt 6 / QtWebEngine (Chromium) | via PyQt6 | LGPL v3 / GPL, Chromium BSD-style |
| Monaco Editor | `radide/web/monaco/` | MIT |
| monaco-vim | `radide/web/monaco-vim/` | MIT |
| GrapesJS | `radide/web/grapes/` | BSD-3-Clause |
| emmet-monaco-es | `radide/web/emmet/` | MIT |
| Adminer | `radide/web/adminer/` | Apache 2.0 / GPL v2 |
| Bootstrap | `radide/web_site/templates/html-bootstrap/assets/vendor/bootstrap/` | MIT |
| Python packages in `requirements.txt` | Python dependencies | their own licenses (mostly MIT/BSD/Apache) |

**Important when you distribute RAD IDE as a program (e.g. an installer):** PyQt6 is GPL v3, so a
distribution that includes PyQt6 must as a whole respect the GPL v3 (source available, same freedoms).
The MIT license of RAD IDE's own code is compatible with that. The credit to Musoftware
(https://musoftwares.com) required by `LICENSE` must stay in every copy.
