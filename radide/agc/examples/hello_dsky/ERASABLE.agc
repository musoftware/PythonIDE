# ERASABLE.agc - names of the special registers and the program's variables (erasable memory, bank E0).

A               EQUALS  0               # accumulator
L               EQUALS  1               # low accumulator (MP / DV results)
Q               EQUALS  2               # return address
EB              EQUALS  3
FB              EQUALS  4
Z               EQUALS  5               # program counter
BB              EQUALS  6
ZERO            EQUALS  7               # always 0
ARUPT           EQUALS  10              # interrupt save area for A (DXCH ARUPT saves A and L)
LRUPT           EQUALS  11
QRUPT           EQUALS  12
TIME1           EQUALS  25
TIME3           EQUALS  26              # T3RUPT when it overflows

                SETLOC  61              # first free erasable word after the counters

SECS            ERASE                   # the clock
MINS            ERASE
HOURS           ERASE
TICKED          ERASE                   # T3RUPT sets it to 1 every second
KEYIN           ERASE                   # last key code + 1 (0 = none waiting)
KEY             ERASE                   # key being handled
MODE            ERASE                   # 0 = idle, 1 = typing a verb, 2 = typing a noun
VERB            ERASE
NOUN            ERASE
DIGCNT          ERASE                   # digits typed so far
LAMPT           ERASE                   # 1 while the lamp test is shown
NUM             ERASE                   # PUTNUM: number to show
POS             ERASE                   # PUTNUM: first digit position
NDIG            ERASE                   # PUTNUM: how many digits
PIDX            ERASE                   # PUTNUM: index into PWRTAB
DIGIT           ERASE
FLCNT           ERASE                   # FLUSH: loop counter
FLOFF           ERASE                   # FLUSH: table offset
WORD            ERASE                   # FLUSH: relay word being built
TMP             ERASE
SAVEQ           ERASE
SAVEQ2          ERASE

# The display buffer: one 5-bit DSKY digit code per position.
#   0-1 PROG   2-3 VERB   4-5 NOUN   6-10 R1   11-15 R2   16-20 R3
CODES           ERASE   +20D            # positions 0-20
BLANKC          ERASE                   # 21: always 0 (no digit / no sign)
SIGN1           ERASE                   # 22: R1 plus sign (0 or 2000 octal)
SIGN2           ERASE                   # 23: R2 plus sign
SIGN3           ERASE                   # 24: R3 plus sign
