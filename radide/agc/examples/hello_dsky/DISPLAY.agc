# DISPLAY.agc - the DSKY is driven through output channel 10 with "relay words":
#   bits 15-12 = relay word number (1-12), bit 11 = a sign bit, bits 10-6 = left digit, bits 5-1 = right digit.
# The program keeps one digit code per position in CODES and FLUSH writes all 11 relay words.

# SHOWVN - VERB and NOUN into the buffer (PROG stays blank) and onto the DSKY.
SHOWVN          CA      Q
                TS      SAVEQ2
                CA      VERB
                TS      NUM
                CAF     TWO             # position 2 = first VERB digit
                TS      POS
                CAF     TWO
                TS      NDIG
                TC      PUTNUM
                CA      NOUN
                TS      NUM
                CAF     FOUR            # position 4 = first NOUN digit
                TS      POS
                CAF     TWO
                TS      NDIG
                TC      PUTNUM
                TC      FLUSH
                CA      SAVEQ2
                TS      Q
                RETURN

# SHOWCLK - R1 = hours, R2 = minutes, R3 = seconds x 100 (the N36 format), all with a + sign.
SHOWCLK         CA      Q
                TS      SAVEQ2
                CA      HOURS
                TS      NUM
                CAF     SIX             # R1 starts at position 6
                TS      POS
                CAF     FIVE
                TS      NDIG
                TC      PUTNUM
                CA      MINS
                TS      NUM
                CAF     D11             # R2 starts at position 11
                TS      POS
                CAF     FIVE
                TS      NDIG
                TC      PUTNUM
                CA      SECS
                EXTEND
                MP      D100            # (A, L) = SECS x 100: small integers end up in L
                CA      L
                TS      NUM
                CAF     D16             # R3 starts at position 16
                TS      POS
                CAF     FIVE
                TS      NDIG
                TC      PUTNUM
                CAF     PLUSBIT
                TS      SIGN1
                TS      SIGN2
                TS      SIGN3
                TC      FLUSH
                CA      SAVEQ2
                TS      Q
                RETURN

# PUTNUM - write NUM as NDIG decimal digits (2 or 5) at buffer position POS. Uses repeated subtraction of
# the powers of ten in PWRTAB (the AGC has DV, but it divides fractions - subtraction is easier to follow).
PUTNUM          CAF     FIVE
                EXTEND
                SU      NDIG            # PIDX = 5 - NDIG: 0 for 5 digits (10000), 3 for 2 digits (10)
                TS      PIDX
PNLOOP          CA      ZERO
                TS      DIGIT
PNSUB           INDEX   PIDX
                CS      PWRTAB          # A = -power
                AD      NUM             # A = NUM - power
                EXTEND
                BZMF    PNMAYBE         # NUM <= power
PNTAKE          TS      NUM             # NUM = NUM - power, one more in this digit
                INCR    DIGIT
                TCF     PNSUB
PNMAYBE         EXTEND
                BZF     PNEQ            # exactly equal (ones' complement: -0)
                TCF     PNSTORE
PNEQ            CA      ZERO
                TCF     PNTAKE
PNSTORE         INDEX   DIGIT           # digit -> 5-bit DSKY code
                CAF     DIGTAB
                INDEX   POS
                TS      CODES
                INCR    POS
                INCR    PIDX
                CS      PIDX
                AD      FIVE            # done when PIDX = 5
                EXTEND
                BZF     PNDONE
                TCF     PNLOOP
PNDONE          RETURN

# FLUSH - send the 11 relay words described by RWTAB (4 words per entry: relay bits, left position,
# right position, sign cell). CCS counts the entries down: 10, 9, ... 0.
FLUSH           CAF     TEN
FLLOOP          TS      FLCNT
                DOUBLE
                DOUBLE                  # A = 4 x entry number
                TS      FLOFF
                INDEX   FLOFF
                CAF     RWTAB           # relay word number in bits 15-12
                TS      WORD
                INDEX   FLOFF
                CAF     RWTAB +1        # left digit position
                TS      TMP
                INDEX   TMP
                CA      CODES
                DOUBLE                  # x 32: into bits 10-6
                DOUBLE
                DOUBLE
                DOUBLE
                DOUBLE
                AD      WORD
                TS      WORD
                INDEX   FLOFF
                CAF     RWTAB +2        # right digit position
                TS      TMP
                INDEX   TMP
                CA      CODES
                AD      WORD
                TS      WORD
                INDEX   FLOFF
                CAF     RWTAB +3        # sign cell (0 or 2000 octal)
                TS      TMP
                INDEX   TMP
                CA      CODES
                AD      WORD
                EXTEND
                WRITE   10              # out to the DSKY
                CCS     FLCNT
                TCF     FLLOOP
                RETURN
