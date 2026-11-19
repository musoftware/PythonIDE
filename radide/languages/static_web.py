"""HTML / CSS / JavaScript Site projects (docs/CONTRACTS.md 8.1): static files served by the IDE's own
DevServer (radide/web_site/server.py) with live reload - nothing to install."""
from __future__ import annotations

from ..web_site.project import WebSitePlugin, new_file_content
from .javascript import JS_KEYWORDS


class StaticWebPlugin(WebSitePlugin):
    id = "static-web"
    display_name = "HTML / CSS / JavaScript Site"
    code_ext = ".html"
    web_kind = "static"
    needs_interpreter = False
    default_template = "static-empty"
    tool_names: list[str] = []
    keywords = JS_KEYWORDS
    line_comments = ["//"]
    block_comment = ("<!--", "-->")

    def tool(self) -> str:
        return "built-in web server"

    def find_interpreter(self, configured: str = "") -> str:
        return ""

    def module_template(self, name: str) -> str:
        from pathlib import Path
        return new_file_content(Path(f"{name}.html"))

    def backend(self, server):
        return None                     # DevServer serves the files itself


PLUGIN = StaticWebPlugin()
