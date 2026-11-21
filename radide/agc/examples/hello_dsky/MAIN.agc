# MAIN.agc - HELLO DSKY: a small, original Apollo Guidance Computer program written for RAD IDE.
# Licence: public domain (CC0) - copy it, change it, learn from it.
#
# It runs in RAD IDE's AGC emulator and assembles with yaYUL (Virtual AGC) as well.
# What it does:
#   * shows VERB 16 NOUN 36 - "monitor decimal: AGC clock" - and counts the time since start:
#       R1 = hours, R2 = minutes, R3 = seconds (to hundredths, like the real N36)
#   * a tiny keyboard handler (the real one, PINBALL GAME BUTTONS AND LIGHTS, is ~10 000 words):
#       VERB 3 5 ENTR            lamp test (every digit 8, every lamp on)
#       VERB 1 6 NOUN 3 6 ENTR   back to the clock
#       any other verb / noun    OPR ERR lamp; RSET clears it
#
# yaYUL syntax: LABEL in column 1, then OPCODE and OPERAND; "#" starts a comment.
# Numbers are octal unless they contain 8 / 9 or end with D (decimal); DEC constants are decimal.

$ERASABLE.agc                           # erasable (RAM) assignments

                SETLOC  4000            # fixed-fixed memory: the interrupt vectors come first

                INHINT                  # 4000: GOJAM (power on / restart)
                TCF     START
                NOOP
                NOOP

                RESUME                  # 4004: T6RUPT (jet timing) - not used
                NOOP
                NOOP
                NOOP

                RESUME                  # 4010: T5RUPT (autopilot) - not used
                NOOP
                NOOP
                NOOP

                DXCH    ARUPT           # 4014: T3RUPT - TIME3 overflowed (once a second here)
                TCF     T3HAND
                NOOP
                NOOP

                RESUME                  # 4020: T4RUPT - not used
                NOOP
                NOOP
                NOOP

                DXCH    ARUPT           # 4024: KEYRUPT1 - a DSKY key was pressed
                TCF     KEYHAND
                NOOP
                NOOP

                RESUME                  # 4030: KEYRUPT2
                NOOP
                NOOP
                NOOP

                RESUME                  # 4034: UPRUPT
                NOOP
                NOOP
                NOOP

                RESUME                  # 4040: DOWNRUPT
                NOOP
                NOOP
                NOOP

                RESUME                  # 4044: RADAR RUPT
                NOOP
                NOOP
                NOOP

                RESUME                  # 4050: HANDRUPT
                NOOP
                NOOP
                NOOP

$INTERRUPTS.agc                         # T3RUPT and KEYRUPT1 handlers
$DISPLAY.agc                            # DSKY output: digit buffer -> channel 10 relay words
$KEYBOARD.agc                           # VERB / NOUN / ENTR handling

# ------------------------------------------------------------------ start-up
START           CA      ZERO            # clear the variables
                TS      SECS
                TS      MINS
                TS      HOURS
                TS      TICKED
                TS      KEYIN
                TS      MODE
                TS      LAMPT
                EXTEND
                WRITE   11              # all DSKY lamps off
                CAF     RELAY12
                EXTEND
                WRITE   10              # relay word 12: indicator lamps off

                CAF     D24             # clear the digit buffer (25 cells)
CLRLOOP         TS      TMP
                CA      ZERO
                INDEX   TMP
                TS      CODES
                CCS     TMP
                TCF     CLRLOOP

                CAF     V16             # VERB 16 NOUN 36
                TS      VERB
                CAF     N36
                TS      NOUN
                TC      SHOWVN
                TC      SHOWCLK
                CAF     T3LOAD          # first T3RUPT in one second
                TS      TIME3
                RELINT                  # interrupts on

# ------------------------------------------------------------------ main loop
MAIN            CA      KEYIN           # a key waiting?
                EXTEND
                BZF     NOKEY
                TC      DOKEY
NOKEY           CA      TICKED          # a second passed?
                EXTEND
                BZF     MAIN
                CA      ZERO
                TS      TICKED
                TC      TICK
                CA      LAMPT           # lamp test shows 8s: do not overwrite them
                EXTEND
                BZF     +2
                TCF     MAIN
                TC      SHOWCLK
                TCF     MAIN

# ------------------------------------------------------------------ the clock
TICK            INCR    SECS            # SECS = SECS + 1, carry into MINS and HOURS
                CA      SECS
                AD      NEG59
                EXTEND
                BZMF    TICKRET         # SECS <= 59
                CA      ZERO
                TS      SECS
                INCR    MINS
                CA      MINS
                AD      NEG59
                EXTEND
                BZMF    TICKRET
                CA      ZERO
                TS      MINS
                INCR    HOURS
TICKRET         RETURN

$CONSTANTS.agc                          # constants and tables (fixed memory)
