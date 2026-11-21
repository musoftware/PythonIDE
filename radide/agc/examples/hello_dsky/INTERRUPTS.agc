# INTERRUPTS.agc - interrupt handlers. The vector saved A and L with DXCH ARUPT; restore them the same way.

# The real AGC sounds the RUPT LOCK alarm (and restarts) when no interrupt happens for 140 ms, so T3RUPT
# comes every centisecond here and counts 100 of them for one second.
T3HAND          CAF     T3LOAD          # TIME3 overflows again at the next centisecond
                TS      TIME3
                INCR    CENTI
                CS      CENTI
                AD      D100            # 100 - CENTI: zero after one second
                EXTEND
                BZF     T3SEC
                DXCH    ARUPT
                RESUME
T3SEC           CA      ZERO
                TS      CENTI
                CAF     ONE
                TS      TICKED          # tell the main loop
                DXCH    ARUPT
                RESUME

KEYHAND         EXTEND
                READ    15              # channel 15: the 5-bit key code
                MASK    LOW5
                AD      ONE             # +1 so that 0 means "no key"
                TS      KEYIN
                DXCH    ARUPT
                RESUME
