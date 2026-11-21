C     ORBIT TABLE - AN ORIGINAL PROGRAM IN THE STYLE OF THE 1960S,      ORBT0010
C     WRITTEN FOR RAD IDE (PUBLIC DOMAIN / CC0).  FORTRAN 66 FIXED FORM:ORBT0020
C       COLUMNS  1-5   STATEMENT NUMBER                                 ORBT0030
C       COLUMN   6     CONTINUATION MARK (ANY CHARACTER BUT BLANK OR 0) ORBT0040
C       COLUMNS  7-72  THE STATEMENT                                    ORBT0050
C       COLUMNS 73-80  CARD SEQUENCE NUMBER (IGNORED BY THE COMPILER)   ORBT0060
C     NAMES STARTING WITH I-N ARE INTEGER, ALL OTHERS REAL (IMPLICIT).  ORBT0070
C                                                                       ORBT0080
C     PART 1 - CIRCULAR ORBIT VELOCITY AND PERIOD FOR SIX ALTITUDES     ORBT0090
C     PART 2 - AN ELLIPTIC ORBIT: POSITION EVERY TENTH OF A PERIOD      ORBT0100
C              (KEPLER'S EQUATION SOLVED BY NEWTON'S METHOD)            ORBT0110
C     PART 3 - CLASSIFY THE ALTITUDES WITH A COMPUTED GO TO             ORBT0120
C                                                                       ORBT0130
      PROGRAM ORBITS                                                    ORBT0140
      COMMON /EARTH/ GM, RE, PI                                         ORBT0150
      DIMENSION ALT(6)                                                  ORBT0160
      DATA ALT /200.0, 400.0, 1000.0, 5000.0, 20200.0, 35786.0/         ORBT0170
      GM = 398600.44                                                    ORBT0180
      RE = 6378.14                                                      ORBT0190
      PI = 3.1415926536                                                 ORBT0200
C                                                                       ORBT0210
C     PART 1.  V = SQRT(GM/R),  T = 2 PI R / V                          ORBT0220
      WRITE (6,100)                                                     ORBT0230
  100 FORMAT (1X, 24HCIRCULAR ORBITS OF EARTH/                          ORBT0240
     1        1X, 8HALTITUDE, 4X, 8HVELOCITY, 4X, 8H  PERIOD/           ORBT0250
     2        1X, 8H    (KM), 4X, 8H  (KM/S), 4X, 8H   (MIN))           ORBT0260
      DO 10 I = 1, 6                                                    ORBT0270
      R = RE + ALT(I)                                                   ORBT0280
      V = SQRT(GM/R)                                                    ORBT0290
      T = 2.0*PI*R/V/60.0                                               ORBT0300
      WRITE (6,101) ALT(I), V, T                                        ORBT0310
  101 FORMAT (1X, F8.1, 4X, F8.3, 4X, F8.1)                             ORBT0320
   10 CONTINUE                                                          ORBT0330
C                                                                       ORBT0340
C     PART 2.  PERIGEE 300 KM, APOGEE 3000 KM ABOVE THE SURFACE         ORBT0350
      RP = RE + 300.0                                                   ORBT0360
      RA = RE + 3000.0                                                  ORBT0370
      A = (RP + RA)/2.0                                                 ORBT0380
      E = (RA - RP)/(RA + RP)                                           ORBT0390
      TPER = 2.0*PI*SQRT(A**3/GM)                                       ORBT0400
      WRITE (6,102) A, E, TPER/60.0                                     ORBT0410
  102 FORMAT (/1X, 22HELLIPTIC ORBIT  A (KM), F12.2/                    ORBT0420
     1         1X, 22H                E     , F12.5/                    ORBT0430
     2         1X, 22H          PERIOD (MIN), F12.2//                   ORBT0440
     3         1X, 5H TIME, 5X, 5HANGLE, 5X, 8HALTITUDE/                ORBT0450
     4         1X, 5H(MIN), 5X, 5H(DEG), 5X, 8H    (KM))                ORBT0460
      DO 20 K = 1, 10                                                   ORBT0470
      T = FLOAT(K-1)*TPER/10.0                                          ORBT0480
      XM = 2.0*PI*T/TPER                                                ORBT0490
      EA = ECCAN(XM, E)                                                 ORBT0500
      TA = 2.0*ATAN2(SQRT(1.0+E)*SIN(EA/2.0), SQRT(1.0-E)*COS(EA/2.0))  ORBT0510
C     ARITHMETIC IF: NEGATIVE -> 15, ZERO -> 16, POSITIVE -> 16         ORBT0520
      IF (TA) 15, 16, 16                                                ORBT0530
   15 TA = TA + 2.0*PI                                                  ORBT0540
   16 R = A*(1.0 - E*COS(EA))                                           ORBT0550
      H = R - RE                                                        ORBT0560
      DEG = TA*180.0/PI                                                 ORBT0570
      WRITE (6,103) T/60.0, DEG, H                                      ORBT0580
  103 FORMAT (1X, F5.1, 4X, F7.2, 4X, F8.1)                             ORBT0590
   20 CONTINUE                                                          ORBT0600
C                                                                       ORBT0610
C     PART 3.  GO TO (31, 32, 33), J  JUMPS TO THE J-TH LABEL           ORBT0620
      WRITE (6,104)                                                     ORBT0630
  104 FORMAT (/1X, 21HWHAT KIND OF ORBIT IS)                            ORBT0640
      DO 30 I = 1, 6                                                    ORBT0650
      J = 1                                                             ORBT0660
      IF (ALT(I) .GT. 2000.0) J = 2                                     ORBT0670
      IF (ALT(I) .GT. 35000.0) J = 3                                    ORBT0680
      GO TO (31, 32, 33), J                                             ORBT0690
   31 WRITE (6,105) ALT(I)                                              ORBT0700
  105 FORMAT (1X, F8.1, 20H KM  LOW EARTH ORBIT)                        ORBT0710
      GO TO 30                                                          ORBT0720
   32 WRITE (6,106) ALT(I)                                              ORBT0730
  106 FORMAT (1X, F8.1, 23H KM  MEDIUM EARTH ORBIT)                     ORBT0740
      GO TO 30                                                          ORBT0750
   33 WRITE (6,107) ALT(I)                                              ORBT0760
  107 FORMAT (1X, F8.1, 24H KM  GEOSTATIONARY ORBIT)                    ORBT0770
   30 CONTINUE                                                          ORBT0780
      STOP                                                              ORBT0790
      END                                                               ORBT0800
C                                                                       ORBT0810
      FUNCTION ECCAN(XM, E)                                             ORBT0820
C     ECCENTRIC ANOMALY: SOLVE  XM = EA - E*SIN(EA)  BY NEWTON ITERATIONORBT0830
      EA = XM                                                           ORBT0840
      DO 10 N = 1, 20                                                   ORBT0850
      F = EA - E*SIN(EA) - XM                                           ORBT0860
      D = F/(1.0 - E*COS(EA))                                           ORBT0870
      EA = EA - D                                                       ORBT0880
      IF (ABS(D) - 1.0E-6) 20, 20, 10                                   ORBT0890
   10 CONTINUE                                                          ORBT0900
   20 ECCAN = EA                                                        ORBT0910
      RETURN                                                            ORBT0920
      END                                                               ORBT0930
