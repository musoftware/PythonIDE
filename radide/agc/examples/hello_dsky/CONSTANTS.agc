# CONSTANTS.agc - constants and tables in fixed memory (the "rope"). CAF / CA / AD read them.

ONE             DEC     1
TWO             DEC     2
FOUR            DEC     4
FIVE            DEC     5
SIX             DEC     6
TEN             DEC     10
D11             DEC     11
D16             DEC     16
D20             DEC     20
D24             DEC     24
D35             DEC     35
D100            DEC     100
NEG9            DEC     -9
NEG59           DEC     -59
V16             DEC     16
N36             DEC     36
T3LOAD          OCT     37634           # 37777 - 99 + 1: TIME3 overflows after 100 centiseconds
LOW5            OCT     37
KVERB           OCT     21              # DSKY key codes
KRSET           OCT     22
KZERO           OCT     20
KENTR           OCT     34
KNOUN           OCT     37
PLUSBIT         OCT     2000            # relay-word sign bit (bit 11)
CODE8           OCT     35              # DSKY code of the digit 8
OPRBIT          OCT     100             # channel 11 bit 7: OPR ERR
LAMPS11         OCT     176             # channel 11 bits 2-7: COMP ACTY, UPLINK, TEMP, KEY REL, V/N, OPR ERR
RELAY12         OCT     30000           # relay word 12, no lamps
LAMPS12         OCT     30677           # relay word 12, PRIO DISP ... PROG lamps

PWRTAB          DEC     10000           # powers of ten for PUTNUM
                DEC     1000
                DEC     100
                DEC     10
                DEC     1

DIGTAB          OCT     25              # 5-bit DSKY codes of the digits 0-9
                OCT     3
                OCT     31
                OCT     33
                OCT     17
                OCT     36
                OCT     34
                OCT     23
                OCT     35
                OCT     37

# FLUSH table: relay bits (word number << 11), left position, right position, sign cell.
RWTAB           OCT     26000           # relay 11: PROG
                DEC     0
                DEC     1
                DEC     21
                OCT     24000           # relay 10: VERB
                DEC     2
                DEC     3
                DEC     21
                OCT     22000           # relay 9: NOUN
                DEC     4
                DEC     5
                DEC     21
                OCT     20000           # relay 8: R1 digit 1
                DEC     21
                DEC     6
                DEC     21
                OCT     16000           # relay 7: +R1, R1 digits 2-3
                DEC     7
                DEC     8
                DEC     22
                OCT     14000           # relay 6: R1 digits 4-5
                DEC     9
                DEC     10
                DEC     21
                OCT     12000           # relay 5: +R2, R2 digits 1-2
                DEC     11
                DEC     12
                DEC     23
                OCT     10000           # relay 4: R2 digits 3-4
                DEC     13
                DEC     14
                DEC     21
                OCT     06000           # relay 3: R2 digit 5, R3 digit 1
                DEC     15
                DEC     16
                DEC     21
                OCT     04000           # relay 2: +R3, R3 digits 2-3
                DEC     17
                DEC     18
                DEC     24
                OCT     02000           # relay 1: R3 digits 4-5
                DEC     19
                DEC     20
                DEC     21
