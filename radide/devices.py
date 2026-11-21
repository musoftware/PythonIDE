"""Device presets and foldable geometry shared by every designer (docs/CONTRACTS.md 10.8).

Pure Python - no Qt, no radide imports - so code generators, runtimes, tests and the Flutter designer can
import it without a QApplication.

Units are logical pixels (dp).  A device is described in *portrait* (height >= width); landscape swaps
the sizes and the insets come from ``land_insets``.

Foldables (``fold`` = "book" | "flip" | "dual") add:
    fold_axis  - "vertical" | "horizontal": direction of the fold / hinge line in portrait
    hinge      - width of the hinge in dp (0 = a seamless crease, the screen continues under it)
    cover      - (w, h) of the outer screen in portrait, used in the Folded posture (None = no cover)
    postures   - the postures the device supports (POSTURES)

Postures are the form property values ``Flat`` | ``HalfOpened`` | ``Folded``; ``posture_key()`` gives the
runtime spelling ``flat`` | ``half-opened`` | ``folded`` (RADIDE_POSTURE, layout-variant ``when`` keys).

Coordinates:
    screen coords    - (0, 0) = top-left of the whole screen (Flutter MediaQuery.displayFeatures, CSS
                       viewport segments)
    safe-area coords - (0, 0) = top-left of the safe area = the form's client area (control Left / Top)
"""
from __future__ import annotations

import os
from dataclasses import dataclass

ORIENTATIONS = ("Portrait", "Landscape")
POSTURES = ("Flat", "HalfOpened", "Folded")
DEFAULT_POSTURE = "Flat"
FOLD_KINDS = ("book", "flip", "dual")
MIN_DUAL_WIDTH = 600          # TwoPane "Auto": below this width (and without a hinge) one pane is shown


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    width: int                     # portrait width in dp (the inner / main screen of a foldable)
    height: int                    # portrait height in dp
    platform: str                  # android | ios
    insets: tuple                  # portrait safe-area insets (left, top, right, bottom)
    land_insets: tuple             # landscape safe-area insets (left, top, right, bottom)
    radius: int = 28               # screen corner radius
    cutout: str = "punch"          # punch | island | none  (camera cut-out drawn in the status bar)
    home_button: bool = False      # iPhone SE style chin with a round home button
    tablet: bool = False
    fold: str = ""                 # "" | book | flip | dual
    fold_axis: str = ""            # vertical | horizontal (in portrait)
    hinge: int = 0                 # hinge width in dp (0 = seamless crease)
    cover: tuple | None = None     # outer screen (w, h) in portrait, shown when Folded
    postures: tuple = ()           # supported postures (subset of POSTURES)
    avd: str = ""                  # Android emulator hardware profile (avdmanager -d) closest to it

    @property
    def foldable(self) -> bool:
        return bool(self.fold)


_FOLD = POSTURES
DEVICES: dict[str, Device] = {d.id: d for d in [
    # --- phones and tablets (the first five are the original presets; keep their ids)
    Device("pixel", "Pixel / Medium phone (412 x 915)", 412, 915, "android", (0, 24, 0, 24), (0, 24, 0, 16),
           radius=34, cutout="punch", avd="medium_phone"),
    Device("small_phone", "Small phone (360 x 640)", 360, 640, "android", (0, 24, 0, 48), (0, 24, 0, 48),
           radius=18, cutout="none", avd="small_phone"),
    Device("tablet", "Tablet (800 x 1280)", 800, 1280, "android", (0, 24, 0, 48), (0, 24, 0, 48),
           radius=24, cutout="none", tablet=True, avd="medium_tablet"),
    Device("iphone_15", "iPhone 15 (393 x 852)", 393, 852, "ios", (0, 59, 0, 34), (59, 0, 59, 21),
           radius=55, cutout="island"),
    Device("iphone_se", "iPhone SE (375 x 667)", 375, 667, "ios", (0, 20, 0, 0), (0, 0, 0, 0),
           radius=0, cutout="none", home_button=True),
    Device("iphone_15_pro_max", "iPhone 15 Pro Max (430 x 932)", 430, 932, "ios", (0, 59, 0, 34),
           (59, 0, 59, 21), radius=55, cutout="island"),
    Device("galaxy_s20", "Galaxy S20 (360 x 800)", 360, 800, "android", (0, 24, 0, 16), (0, 24, 0, 16),
           radius=30, cutout="punch"),
    Device("ipad_mini", "iPad mini (744 x 1133)", 744, 1133, "ios", (0, 24, 0, 20), (0, 24, 0, 20),
           radius=24, cutout="none", tablet=True),
    # --- foldables (approximate dp; inner screen in portrait)
    Device("galaxy_z_fold6", "Galaxy Z Fold6 (882 x 1104, foldable)", 882, 1104, "android", (0, 24, 0, 16),
           (0, 24, 0, 16), radius=18, cutout="punch", fold="book", fold_axis="vertical", hinge=0,
           cover=(360, 880), postures=_FOLD, avd="7.6in Foldable"),
    Device("galaxy_z_flip6", "Galaxy Z Flip6 (412 x 1004, flip)", 412, 1004, "android", (0, 24, 0, 16),
           (0, 24, 0, 16), radius=30, cutout="punch", fold="flip", fold_axis="horizontal", hinge=0,
           cover=(300, 312), postures=_FOLD, avd="6.7in Foldable"),
    Device("pixel_fold", "Pixel Fold (701 x 841, foldable)", 701, 841, "android", (0, 24, 0, 16),
           (0, 24, 0, 16), radius=20, cutout="punch", fold="book", fold_axis="horizontal", hinge=0,
           cover=(411, 797), postures=_FOLD, avd="pixel_fold"),
    Device("pixel_9_pro_fold", "Pixel 9 Pro Fold (852 x 883, foldable)", 852, 883, "android", (0, 24, 0, 16),
           (0, 24, 0, 16), radius=20, cutout="punch", fold="book", fold_axis="vertical", hinge=0,
           cover=(443, 994), postures=_FOLD, avd="pixel_9_pro_fold"),
    Device("surface_duo2", "Surface Duo 2 (2 x 540 x 720, dual screen)", 720, 1106, "android", (0, 24, 0, 16),
           (0, 24, 0, 16), radius=12, cutout="none", fold="dual", fold_axis="horizontal", hinge=26,
           cover=(540, 720), postures=_FOLD),
]}
DEFAULT_DEVICE = "pixel"
FOLDABLE_IDS = tuple(d.id for d in DEVICES.values() if d.fold)
# Android emulator hardware profiles that are foldable, best first (foldable_avd() picks one that exists)
FOLDABLE_AVD_PROFILES = ("pixel_9_pro_fold", "pixel_fold", "7.6in Foldable", "8in Foldable", "6.7in Foldable")


# ====================================================================== basics
def device(device_id) -> Device:
    return DEVICES.get(str(device_id or ""), DEVICES[DEFAULT_DEVICE])


def landscape(orientation) -> bool:
    return str(orientation or "").lower().startswith("land")


def is_foldable(device_id) -> bool:
    return bool(device(device_id).fold)


def posture_name(posture) -> str:
    """Normalise any spelling (``half-opened``, ``halfOpened``, ``tabletop``, ``closed`` ...) to the form
    property value Flat | HalfOpened | Folded."""
    s = str(posture or "").strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    if s in ("halfopened", "halfopen", "half", "tabletop", "book", "posturehalfopened"):
        return "HalfOpened"
    if s in ("folded", "closed", "fold", "cover", "single"):
        return "Folded"
    return "Flat"


def posture_key(posture) -> str:
    """Runtime spelling: flat | half-opened | folded (RADIDE_POSTURE, layout variant ``when``)."""
    return {"Flat": "flat", "HalfOpened": "half-opened", "Folded": "folded"}[posture_name(posture)]


def postures(device_id) -> tuple:
    """Postures offered for the device (() for a normal phone)."""
    d = device(device_id)
    return tuple(d.postures) if d.fold else ()


def effective_posture(device_id, posture) -> str:
    """The posture that applies: always Flat for a device that does not fold."""
    p = posture_name(posture)
    return p if p in postures(device_id) else "Flat"


def _folded(device_id, posture) -> bool:
    d = device(device_id)
    return bool(d.fold and d.cover and effective_posture(device_id, posture) == "Folded")


# ====================================================================== sizes
def screen_size(device_id, orientation="Portrait", posture="Flat") -> tuple[int, int]:
    """Whole screen in dp for the orientation (Folded = the cover screen of a foldable)."""
    d = device(device_id)
    w, h = (d.cover if _folded(device_id, posture) else (d.width, d.height))
    return (h, w) if landscape(orientation) else (w, h)


def safe_insets(device_id, orientation="Portrait", posture="Flat") -> tuple[int, int, int, int]:
    d = device(device_id)
    return tuple(d.land_insets if landscape(orientation) else d.insets)


def safe_area_size(device_id, orientation="Portrait", posture="Flat") -> tuple[int, int]:
    """The form's Width / Height for a device + orientation + posture (screen minus the safe-area insets)."""
    w, h = screen_size(device_id, orientation, posture)
    left, top, right, bottom = safe_insets(device_id, orientation, posture)
    return w - left - right, h - top - bottom


# ====================================================================== hinge / fold
def fold_axis(device_id, orientation="Portrait", posture="Flat") -> str:
    """Direction of the fold line on screen for this orientation: vertical | horizontal | "" (none /
    folded)."""
    d = device(device_id)
    if not d.fold or _folded(device_id, posture):
        return ""
    if not landscape(orientation):
        return d.fold_axis
    return "horizontal" if d.fold_axis == "vertical" else "vertical"


def hinge_screen_rect(device_id, orientation="Portrait", posture="Flat") -> tuple | None:
    """(x, y, w, h) of the hinge / crease in screen coords, or None (not foldable / Folded).
    A seamless crease has width (or height) 0."""
    axis = fold_axis(device_id, orientation, posture)
    if not axis:
        return None
    d = device(device_id)
    sw, sh = screen_size(device_id, orientation, posture)
    hw = max(0, int(d.hinge))
    if axis == "vertical":
        return ((sw - hw) // 2, 0, hw, sh)
    return (0, (sh - hw) // 2, sw, hw)


def hinge_rect(device_id, orientation="Portrait", posture="Flat") -> tuple | None:
    """(x, y, w, h) of the hinge / crease in safe-area coords (the form's client area), clipped to the
    safe area, or None.  Contract 1.6 of docs/plans/MOTION_VARIANTS_FOLDABLES.md."""
    r = hinge_screen_rect(device_id, orientation, posture)
    if r is None:
        return None
    il, it, _ir, _ib = safe_insets(device_id, orientation, posture)
    w, h = safe_area_size(device_id, orientation, posture)
    x, y, hw, hh = r
    if fold_axis(device_id, orientation, posture) == "vertical":
        return (x - il, 0, hw, h)
    return (0, y - it, w, hh)


def is_separating(device_id, posture="Flat") -> bool:
    """True when the fold splits the screen into two logical areas: a dual-screen hinge (unless Folded)
    or a fold that is half opened (Android FoldingFeature.isSeparating)."""
    d = device(device_id)
    if not d.fold or _folded(device_id, posture):
        return False
    return d.fold == "dual" or effective_posture(device_id, posture) == "HalfOpened"


def span(device_id, orientation="Portrait", posture="Flat") -> str:
    """dual when the app spans two separated screen areas, else single (layout variant ``when.span``)."""
    return "dual" if is_separating(device_id, posture) else "single"


def segments(device_id, orientation="Portrait", posture="Flat") -> list[tuple]:
    """Screen areas in screen coords (CSS viewport segments): one rect, or two around a separating fold."""
    sw, sh = screen_size(device_id, orientation, posture)
    r = hinge_screen_rect(device_id, orientation, posture)
    if r is None or not is_separating(device_id, posture):
        return [(0, 0, sw, sh)]
    x, y, w, h = r
    if fold_axis(device_id, orientation, posture) == "vertical":
        return [(0, 0, x, sh), (x + w, 0, sw - x - w, sh)]
    return [(0, 0, sw, y), (0, y + h, sw, sh - y - h)]


def display_features(device_id, orientation="Portrait", posture="Flat") -> list[dict]:
    """Flutter-style display features (MediaQueryData.displayFeatures) in screen coords:
    [{"type": "hinge" | "fold", "bounds": [x, y, w, h], "state": "postureFlat" | "postureHalfOpened"}]."""
    r = hinge_screen_rect(device_id, orientation, posture)
    if r is None:
        return []
    d = device(device_id)
    state = "postureHalfOpened" if effective_posture(device_id, posture) == "HalfOpened" else "postureFlat"
    return [{"type": "hinge" if d.fold == "dual" else "fold", "bounds": list(r), "state": state}]


def rect_crosses(rect, hinge, margin: int = 0) -> bool:
    """True when *rect* (x, y, w, h) lies on both sides of (or inside) the *hinge* band."""
    if hinge is None:
        return False
    x, y, w, h = (int(v) for v in rect)
    hx, hy, hw, hh = (int(v) for v in hinge)
    if hw <= hh:                                   # vertical band
        if y + h <= hy or y >= hy + hh:
            return False
        return x < hx + hw - margin and x + w > hx + margin if hw else x < hx < x + w
    if x + w <= hx or x >= hx + hw:
        return False
    return y < hy + hh - margin and y + h > hy + margin if hh else y < hy < y + h


# ====================================================================== TwoPane
def two_pane(width, height, mode="Auto", ratio=0.5, single="Start", hinge=None, hinge_aware=True,
             min_dual: int = MIN_DUAL_WIDTH) -> dict:
    """Split a TwoPane box of *width* x *height* (contract in docs/CONTRACTS.md 10.8).

    hinge - the hinge band relative to the box (x, y, w, h), or None; used when *hinge_aware*.
    Returns {"mode": "horizontal" | "vertical" | "single", "split": "hinge" | "ratio" | "single",
             "panes": [rect, rect | None], "shown": None | 0 | 1}; rects are (x, y, w, h) in the box.
    In single mode panes[0] is the shown pane's rect (the whole box) and panes[1] is None.
    """
    w, h = max(0, int(width)), max(0, int(height))
    mode = str(mode or "Auto").capitalize()
    try:
        ratio = min(0.95, max(0.05, float(ratio)))
    except (TypeError, ValueError):
        ratio = 0.5
    shown = 1 if str(single or "Start").lower() == "end" else 0
    if hinge_aware and hinge is not None:
        hx, hy, hw, hh = (int(v) for v in hinge)
        vertical_band = hw <= hh
        inside = (0 < hx and hx + hw < w) if vertical_band else (0 < hy and hy + hh < h)
        crosses = (hy < h and hy + hh > 0) if vertical_band else (hx < w and hx + hw > 0)
        want = "horizontal" if vertical_band else "vertical"
        if inside and crosses and mode in ("Auto", want.capitalize()):
            if vertical_band:
                return {"mode": "horizontal", "split": "hinge", "shown": None,
                        "panes": [(0, 0, hx, h), (hx + hw, 0, w - hx - hw, h)]}
            return {"mode": "vertical", "split": "hinge", "shown": None,
                    "panes": [(0, 0, w, hy), (0, hy + hh, w, h - hy - hh)]}
    if mode == "Auto":
        if w < min_dual:
            return {"mode": "single", "split": "single", "shown": shown, "panes": [(0, 0, w, h), None]}
        mode = "Horizontal"
    if mode == "Vertical":
        a = int(h * ratio + 0.5)          # half rounds up (same as Dart roundToDouble)
        return {"mode": "vertical", "split": "ratio", "shown": None, "panes": [(0, 0, w, a), (0, a, w, h - a)]}
    a = int(w * ratio + 0.5)
    return {"mode": "horizontal", "split": "ratio", "shown": None, "panes": [(0, 0, a, h), (a, 0, w - a, h)]}


# ====================================================================== runtime simulation (contract 1.7)
def env_state(environ=None) -> dict:
    """Posture / span / hinge requested through RADIDE_POSTURE, RADIDE_SPAN and RADIDE_HINGE (x,y,w,h in
    window coords) - how desktop runtimes simulate a foldable.  Missing values are None."""
    env = os.environ if environ is None else environ
    out = {"posture": None, "span": None, "hinge": None}
    if env.get("RADIDE_POSTURE"):
        out["posture"] = posture_key(env["RADIDE_POSTURE"])
    if env.get("RADIDE_SPAN"):
        out["span"] = "dual" if str(env["RADIDE_SPAN"]).strip().lower() in ("dual", "2", "spanned") else "single"
    try:
        parts = [int(float(v)) for v in str(env.get("RADIDE_HINGE", "")).split(",") if v.strip()]
        if len(parts) == 4:
            out["hinge"] = tuple(parts)
    except ValueError:
        pass
    return out


def device_rows(include_foldables: bool = True) -> list[tuple]:
    """(id, name, width, height, platform, status bar, bottom inset, radius, fold) for simple device lists
    (the Flutter designer, SuperPreview)."""
    return [(d.id, d.name, d.width, d.height, d.platform, d.insets[1], d.insets[3], d.radius, d.fold)
            for d in DEVICES.values() if include_foldables or not d.fold]


__all__ = ["Device", "DEVICES", "DEFAULT_DEVICE", "ORIENTATIONS", "POSTURES", "DEFAULT_POSTURE", "FOLD_KINDS",
           "FOLDABLE_IDS", "FOLDABLE_AVD_PROFILES", "MIN_DUAL_WIDTH", "device", "landscape", "is_foldable",
           "posture_name", "posture_key", "postures", "effective_posture", "screen_size", "safe_insets",
           "safe_area_size", "fold_axis", "hinge_screen_rect", "hinge_rect", "is_separating", "span",
           "segments", "display_features", "rect_crosses", "two_pane", "env_state", "device_rows"]
