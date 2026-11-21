"""Checksum toolkit for firmware / ECU images (docs/FIRMWARE.md "Checksums").

* algorithms.py - sum8/16/32 (bytes or LE/BE words; plain, inverted, two's complement), XOR, CRC-8/16/32 with
  any Rocksoft parameters (CRC catalogue presets), Adler-32, Fletcher-16/32.
* blocks.py     - user-defined checksum blocks (multi-range, skip ranges, stored value + complement copy,
  multipoint repeat), verify / correct with a report, shareable JSON profiles.
* finder.py     - tries the algorithms over candidate ranges of an original file to locate stored values.

Pure Python (numpy speeds up word sums when present).  Presets are generic algorithms, never claimed to be
a manufacturer's: a profile must be verified against the user's own original file.
"""
from .algorithms import PRESETS, AlgorithmError, compute, compute_parts, describe, resolve, short_name
from .blocks import (BlockResult, ChecksumBlock, blocks_from_json, blocks_to_json, correct, load_profile, report,
                     save_profile, verify)
from .finder import Candidate, FindResult, complement_pairs, find

__all__ = ["PRESETS", "AlgorithmError", "compute", "compute_parts", "describe", "resolve", "short_name",
           "BlockResult", "ChecksumBlock", "blocks_from_json", "blocks_to_json", "correct", "load_profile", "report",
           "save_profile", "verify", "Candidate", "FindResult", "complement_pairs", "find"]
