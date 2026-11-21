# INTERRUPTS.agc - interrupt handlers. The vector saved A and L with DXCH ARUPT; restore them the same way.

T3HAND          CAF     T3LOAD          # TIME3 counts centiseconds: overflow again after 100 (1 second)
                TS      TIME3
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
