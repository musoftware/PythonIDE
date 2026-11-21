"""Calibration maps of firmware binaries (docs/FIRMWARE.md "Calibration maps").

Pure Python + numpy:

* ``model``  - MapDef / AxisDef / MapPack (JSON ``<file>.maps.json``, CSV), data types, Excel text.
* ``finder`` - ``find_maps(data)``: potential maps (Bosch-style headers, axes + values, 8/16/32-bit, float,
               signed, LE / BE, row / column order, axis-less blocks), ``value_profile`` for the 2D view.
* ``ops``    - editing operations (set, +/- %, add, multiply, interpolate, smooth, paste), write-back, ori/mod
               differences, compare / copy maps between binaries.
* ``a2l``    - ASAM ASAP2 (A2L) import of the common subset and export.
* ``tsini``  - TunerStudio ini (rusEFI, Speeduino) -> map pack; .msq tune -> calibration image.
* ``synth``  - synthetic images with known maps (tests / demos).

Qt: ``views`` (table model, 2D chart, 3D surface, file graph), ``editor`` (MapEditor), ``dialogs``,
``document`` (MapsDocument, CompareDocument) - used by radide/features/firmware_maps.py.
"""
from .model import AxisDef, MapDef, MapPack, pack_path_for
from .finder import Candidate, find_maps

__all__ = ["AxisDef", "MapDef", "MapPack", "pack_path_for", "Candidate", "find_maps"]
