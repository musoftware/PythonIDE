"""The shared Tools > Retro menu of the retro slices (ROM workbench, retro dev, emulators, graphics ...).

``retro_menu(win)`` returns the submenu (created once, kept as ``win.retro_menu``); ``section(win, title)``
returns a sub-submenu of it, so every slice adds its own group without fighting over one menu.
"""
from __future__ import annotations


def _tools_menu(win):
    mb = win.menuBar()
    return next((a.menu() for a in mb.actions() if a.menu() is not None and
                 a.text().replace("&", "") == "Tools"), None)


def retro_menu(win):
    m = getattr(win, "retro_menu", None)
    if m is not None:
        try:
            m.title()
            return m
        except RuntimeError:            # deleted C++ object
            pass
    tools = _tools_menu(win)
    if tools is None:
        tools = win.menuBar().addMenu("&Tools")
    m = next((a.menu() for a in tools.actions() if a.menu() is not None and
              a.text().replace("&", "") == "Retro"), None)
    if m is None:
        m = tools.addMenu("&Retro")
    win.retro_menu = m
    return m


def section(win, title: str):
    parent = retro_menu(win)
    m = next((a.menu() for a in parent.actions() if a.menu() is not None and
              a.text().replace("&", "") == title.replace("&", "")), None)
    return m or parent.addMenu(title)
