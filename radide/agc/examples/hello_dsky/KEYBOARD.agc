# KEYBOARD.agc - a very small "PINBALL": VERB nn, NOUN nn, ENTR, RSET.
# Key codes (channel 15, octal): 1-11 = digits 1-9, 20 = 0, 21 VERB, 22 RSET, 34 ENTR, 36 CLR, 37 NOUN.

DOKEY           CA      Q
                TS      SAVEQ
                CS      ONE
                AD      KEYIN           # undo the +1 of KEYHAND
                TS      KEY
                CA      ZERO
                TS      KEYIN

                CS      KEY             # which key?  (KEY - code = 0 when they match)
                AD      KVERB
                EXTEND
                BZF     GOTVERB
                CS      KEY
                AD      KNOUN
                EXTEND
                BZF     GOTNOUN
                CS      KEY
                AD      KENTR
                EXTEND
                BZF     GOTENTR
                CS      KEY
                AD      KRSET
                EXTEND
                BZF     GOTRSET
                CS      KEY
                AD      KZERO
                EXTEND
                BZF     GOTZERO
                CA      KEY             # 1-9?
                AD      NEG9
                EXTEND
                BZMF    GOTDIG
                TCF     KEYDONE         # CLR, KEY REL, + and - are ignored

GOTZERO         CA      ZERO
                TS      KEY
GOTDIG          CA      MODE            # digits only count after VERB or NOUN
                EXTEND
                BZF     KEYDONE
                CS      DIGCNT          # at most two digits: 2 - DIGCNT must stay above 0
                AD      TWO
                EXTEND
                BZMF    KEYDONE
                CS      MODE
                AD      ONE
                EXTEND
                BZF     VDIGIT          # MODE = 1: verb digit
                CA      NOUN            # NOUN = 10 x NOUN + digit
                EXTEND
                MP      TEN
                CA      L
                AD      KEY
                TS      NOUN
                CAF     FOUR            # buffer position 4 + DIGCNT
                TCF     SHOWDIG
VDIGIT          CA      VERB            # VERB = 10 x VERB + digit
                EXTEND
                MP      TEN
                CA      L
                AD      KEY
                TS      VERB
                CAF     TWO             # buffer position 2 + DIGCNT
SHOWDIG         AD      DIGCNT
                TS      TMP
                INDEX   KEY
                CAF     DIGTAB
                INDEX   TMP
                TS      CODES
                INCR    DIGCNT
                TC      FLUSH
                TCF     KEYDONE

GOTVERB         CAF     ONE             # start typing a verb: blank the two VERB digits
                TS      MODE
                CA      ZERO
                TS      VERB
                TS      DIGCNT
                TS      CODES +2
                TS      CODES +3
                TC      FLUSH
                TCF     KEYDONE

GOTNOUN         CAF     TWO             # start typing a noun
                TS      MODE
                CA      ZERO
                TS      NOUN
                TS      DIGCNT
                TS      CODES +4
                TS      CODES +5
                TC      FLUSH
                TCF     KEYDONE

GOTRSET         CA      ZERO            # RSET: OPR ERR off
                EXTEND
                WRITE   11
                TCF     KEYDONE

GOTENTR         CA      ZERO            # ENTR: do what VERB / NOUN say
                TS      MODE
                CS      VERB
                AD      D35
                EXTEND
                BZF     LAMPTEST
                CS      VERB
                AD      V16
                EXTEND
                BZF     +2
                TCF     OPRERR
                CS      NOUN
                AD      N36
                EXTEND
                BZF     CLOCK
OPRERR          CAF     OPRBIT          # unknown request: OPR ERR lamp (channel 11 bit 7)
                EXTEND
                WRITE   11
                TCF     KEYDONE

CLOCK           CA      ZERO            # V16 N36: lamps off, clock back
                TS      LAMPT
                EXTEND
                WRITE   11
                CAF     RELAY12
                EXTEND
                WRITE   10
                TC      SHOWVN
                TC      SHOWCLK
                TCF     KEYDONE

LAMPTEST        CAF     ONE             # V35: every digit 8, every lamp on
                TS      LAMPT
                CAF     D20
LTLOOP          TS      TMP
                CAF     CODE8
                INDEX   TMP
                TS      CODES
                CCS     TMP
                TCF     LTLOOP
                CAF     PLUSBIT
                TS      SIGN1
                TS      SIGN2
                TS      SIGN3
                TC      FLUSH
                CAF     LAMPS11         # channel 11 lamps
                EXTEND
                WRITE   11
                CAF     LAMPS12         # relay word 12 lamps
                EXTEND
                WRITE   10

KEYDONE         CA      SAVEQ
                TS      Q
                RETURN
