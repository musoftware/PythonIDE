# OrbitTable - an original Fortran 66 style program

Licence: public domain (CC0). Written for RAD IDE in the style of 1960s scientific code; it is not NASA code.

`ORBITS.f` is fixed form with card sequence numbers `ORBT0010`... in columns 73-80:

1. circular orbit speed and period for six altitudes (`V = SQRT(GM/R)`)
2. an elliptic orbit (perigee 300 km, apogee 3000 km): Kepler's equation solved by Newton's method in
   `FUNCTION ECCAN`, position every tenth of a period; arithmetic `IF (TA) 15, 16, 16`
3. a computed `GO TO (31, 32, 33), J` classifies the altitudes

Also: `COMMON`, `DATA`, implicit typing (I-N integer), Hollerith `FORMAT`s (`24HCIRCULAR ORBITS OF EARTH`).

## Try it

* Open the folder, **Ctrl+F5**: built with the `f66` preset (`gfortran -std=legacy -ffixed-form -fno-automatic
  -finit-local-zero`); the output must equal `expected_output.txt`.
* Tools > Retro > Legacy Fortran > Card Deck View on line 24 (a FORMAT card), Convert to Free Form... (diff preview; the result
  compiles as Fortran 90 and prints the same table), Explain Legacy Constructs.

Test: `samples/Tests/Retro/LegacyFortran/test_legacy_fortran.py`.
