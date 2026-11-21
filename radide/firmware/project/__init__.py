"""ECU / firmware project (docs/FIRMWARE.md "ECU projects"): the original kept read-only (SHA-256), a working
copy, named versions with notes and diffs (map-level when a map pack exists), Build = working copy + corrected
checksums -> .bin / .hex / .s19, a modification report and IPS / BPS export / import.  Pure Python.

    python -m radide.firmware.project build|verify|correct|report|diff <folder> ...
"""
from .model import (BuildResult, DiffResult, EcuProject, EcuProjectError, Version, diff_ranges, is_ecu_project,
                    new_project)

__all__ = ["BuildResult", "DiffResult", "EcuProject", "EcuProjectError", "Version", "diff_ranges",
           "is_ecu_project", "new_project"]
