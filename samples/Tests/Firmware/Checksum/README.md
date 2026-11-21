# Checksum toolkit tests

`radide/firmware/checksum` (docs/FIRMWARE.md "Checksums"). Only synthetic data is used: random bytes, plus the
demo image from `radide/firmware/project/synth.py`. No manufacturer firmware is used.

```
python samples/Tests/Firmware/Checksum/test_checksum_core.py
```

* **Algorithm presets** are checked against the CRC RevEng catalogue check values over `"123456789"`:
  * CRC-8 / 16 / 32 variants and Adler-32;
  * the custom CRC-5/USB, CRC-7/MMC, CRC-12/DECT, CRC-24/OPENPGP and CRC-64/XZ;
  * sums, XOR and Fletcher-16 / 32.
* **Fast paths** (zlib, `binascii.crc_hqx`) give the same results as the generic engine. Multi-part CRCs give
  the same results as the whole data.
* **Blocks:**
  * multi-range with a skip range;
  * complement copy;
  * `fillFF`;
  * multipoint repeat;
  * verify and correct, with a report that lists the recalculated blocks;
  * profile JSON round trip.
* **Finder:**
  * sum16 BE stored at the end of its region;
  * CRC-16 with a complement pair (ranked first);
  * CRC-32 over two ranges around a skipped hole;
  * header checksum before its range (LE);
  * a 32-bit two's-complement sum with its complement copy;
  * cross-check with a second image;
  * correction after edits.

Last run: 65/65 passed.
