; dabg - disassembled by RAD IDE (NES / Famicom, ca65)
; Source file: dabg.nes (a copy is in rom/), SHA-1 76d4a2216426654d734bbdce9b487a9b3bc1d98d
;   Format: NES 2.0
;   Mapper: 0
;   PRG ROM: 32K
;   CHR ROM: none (CHR RAM)
;   Mirroring: horizontal
;   Battery: no
;   Trainer: no
;   File size: 32784 bytes
; Building this file gives back the original bytes: F5 / Build prints the rebuild check, and
; Tools > Retro > Retro Development > Rebuild Check compares again. Code the tracer did not reach
; stays data (.byte): add hints in hints.json and use Re-disassemble with Hints (same menu), or
; simply edit the code - it is ordinary ca65 source.

.setcpu "6502"

; ---- hardware registers used by the program
PPUCTRL = $2000    ; PPU control: NMI enable (bit 7), sprite size, pattern tables, VRAM increment, nametable.
PPUMASK = $2001    ; PPU mask: show background / sprites, left 8 pixels, greyscale, colour emphasis.
PPUSTATUS = $2002    ; PPU status: bit 7 vblank, bit 6 sprite 0 hit; reading resets the PPUADDR latch.
OAMADDR = $2003    ; Sprite memory (OAM) address.
PPUSCROLL = $2005    ; Scroll position: write X, then Y.
PPUADDR = $2006    ; VRAM address: write the high byte, then the low byte.
PPUDATA = $2007    ; VRAM data at PPUADDR (the address then moves by 1 or 32).
SQ1_VOL = $4000    ; Pulse 1: duty, loop, constant volume, volume.
SQ1_SWEEP = $4001    ; Pulse 1 sweep unit.
SQ1_LO = $4002    ; Pulse 1 timer low byte.
SQ1_HI = $4003    ; Pulse 1 length counter / timer high bits.
SQ2_VOL = $4004    ; Pulse 2: duty, loop, constant volume, volume.
SQ2_SWEEP = $4005    ; Pulse 2 sweep unit.
SQ2_HI = $4007    ; Pulse 2 length counter / timer high bits.
TRI_LINEAR = $4008    ; Triangle linear counter.
NOISE_VOL = $400C    ; Noise volume / envelope.
NOISE_LO = $400E    ; Noise mode and period.
NOISE_HI = $400F    ; Noise length counter.
DMC_RAW = $4011    ; DMC direct 7-bit output level.
OAMDMA = $4014    ; Sprite DMA: write the page number ($02 copies $0200-$02FF to OAM).
SND_CHN = $4015    ; Sound channels enable / status.
JOY1 = $4016    ; Controller 1: write 1 then 0 to latch the buttons, then read 8 times (A B Select Start Up Down Left Right).
JOY2 = $4017    ; Controller 2 (read); APU frame counter (write).


.segment "HEADER"
        .byte $4E,$45,$53,$1A,$02,$00,$00,$08   
        .byte $00,$00,$00,$07,$00,$00,$00,$00   

.segment "PRG"
L8000:
        lda a:$0014                             ; 8000
        sta a:$0018                             ; 8003
        lda a:$0015                             ; 8006
        sta a:$0019                             ; 8009
        lda a:$0016                             ; 800C
        sta a:$001A                             ; 800F
        lda a:$0017                             ; 8012
        sta a:$001B                             ; 8015
        ldx #$01                                ; 8018
        stx JOY1                                ; 801A
        dex                                     ; 801D
        stx JOY1                                ; 801E
        jsr L80B4                               ; 8021
        lda a:$0016                             ; 8024
        sta a:$0014                             ; 8027
        lda a:$0017                             ; 802A
        sta a:$0015                             ; 802D
        lda #$00                                ; 8030
        sta a:$0016                             ; 8032
        sta a:$0017                             ; 8035
        lda a:$0012                             ; 8038
        beq L8040                               ; 803B
        jsr L80B4                               ; 803D
L8040:
        lda a:$0011                             ; 8040
        bne L8046                               ; 8043
        rts                                     ; 8045
L8046:
        lda a:$0014                             ; 8046
        and #$10                                ; 8049
        beq L8050                               ; 804B
        jmp Reset                               ; 804D
L8050:
        lda #$00                                ; 8050
        sta a:$0014                             ; 8052
        ldx #$00                                ; 8055
L8057:
        lda $0491,x                             ; 8057
        beq L8082                               ; 805A
        lda $0459,x                             ; 805C
        cmp a:$004C                             ; 805F
        bne L8082                               ; 8062
        lda $049F,x                             ; 8064
        bne L8082                               ; 8067
        lda a:$0013                             ; 8069
        and #$08                                ; 806C
        asl                                     ; 806E
        asl                                     ; 806F
        asl                                     ; 8070
        sta a:$0014                             ; 8071
        lda a:$0048                             ; 8074
        cmp $044B,x                             ; 8077
        lda #$00                                ; 807A
        adc #$00                                ; 807C
        sta a:$0072                             ; 807E
        rts                                     ; 8081
L8082:
        inx                                     ; 8082
        cpx #$0E                                ; 8083
        bne L8057                               ; 8085
        lda a:$0048                             ; 8087
        lsr                                     ; 808A
        lsr                                     ; 808B
        lsr                                     ; 808C
        lsr                                     ; 808D
        sta $00                                 ; 808E
        lda a:$004C                             ; 8090
        clc                                     ; 8093
        adc #$10                                ; 8094
        and #$F0                                ; 8096
        ora $00                                 ; 8098
        tay                                     ; 809A
        lda $0700,y                             ; 809B
        bne L80A8                               ; 809E
        lda a:$0072                             ; 80A0
        eor #$01                                ; 80A3
        sta a:$0072                             ; 80A5
L80A8:
        ldx a:$0072                             ; 80A8
        lda L80B2,x                             ; 80AB
        sta a:$0014                             ; 80AE
        rts                                     ; 80B1
L80B2:
        .byte $01,$02                           ; 80B2 ..
L80B4:
        lda #$01                                ; 80B4
        sta a:$0017                             ; 80B6
L80B9:
        lda JOY1                                ; 80B9
        and #$03                                ; 80BC
        cmp #$01                                ; 80BE
        rol a:$0016                             ; 80C0
        lda JOY2                                ; 80C3
        and #$03                                ; 80C6
        cmp #$01                                ; 80C8
        rol a:$0017                             ; 80CA
        bcc L80B9                               ; 80CD
        rts                                     ; 80CF
L80D0:
        lda a:$0013                             ; 80D0
L80D3:
        cmp a:$0013                             ; 80D3
        beq L80D3                               ; 80D6
        rts                                     ; 80D8
        .byte $48,$48,$4A,$4A,$4A,$4A,$AA,$BD   ; 80D9 HHJJJJ..
        .byte $F2,$80,$8D,$07,$20,$68,$29,$0F   ; 80E1 .... h).
        .byte $AA,$BD,$F2,$80,$8D,$07,$20,$68   ; 80E9 ...... h
        .byte $60,$30,$31,$32,$33,$34,$35,$36   ; 80F1 `0123456
        .byte $37,$38,$39,$41,$42,$43,$44,$45   ; 80F9 789ABCDE
        .byte $46,$C9,$0A,$B0,$07,$18,$69,$30   ; 8101 F.....i0
        .byte $8D,$07,$20,$60,$C9,$C8,$90,$0B   ; 8109 .. `....
        .byte $A2,$32,$8E,$07,$20,$38,$E9,$C8   ; 8111 .2.. 8..
        .byte $4C,$28,$81,$C9,$64,$90,$08,$A2   ; 8119 L(..d...
        .byte $31,$8E,$07,$20,$38,$E9,$64,$A2   ; 8121 1.. 8.d.
        .byte $30,$C9,$0A,$90,$06,$E9,$0A,$E8   ; 8129 0.......
        .byte $4C,$2A,$81,$8E,$07,$20,$18,$69   ; 8131 L*... .i
        .byte $30,$8D,$07,$20,$60               ; 8139 0.. `
L813E:
        ldx #$20                                ; 813E
        ldy #$00                                ; 8140
        stx PPUADDR                             ; 8142
        sty PPUADDR                             ; 8145
        ldx #$40                                ; 8148
        ldy #$04                                ; 814A
        lda #$20                                ; 814C
L814E:
        sta PPUDATA                             ; 814E
        inx                                     ; 8151
        bne L814E                               ; 8152
        dey                                     ; 8154
        bne L814E                               ; 8155
        ldy #$40                                ; 8157
        lda #$00                                ; 8159
L815B:
        dey                                     ; 815B
        bne L815B                               ; 815C
        sta PPUSCROLL                           ; 815E
        sta PPUSCROLL                           ; 8161
        rts                                     ; 8164
L8165:
        jsr L8000                               ; 8165
        lda a:$0014                             ; 8168
        ora a:$0015                             ; 816B
        ora a:$0016                             ; 816E
        ora a:$0017                             ; 8171
        beq L8165                               ; 8174
        lda a:$0018                             ; 8176
        ora a:$0019                             ; 8179
        ora a:$001A                             ; 817C
        ora a:$001B                             ; 817F
        bne L8165                               ; 8182
        rts                                     ; 8184
L8185:
        pla                                     ; 8185
        sta $02                                 ; 8186
        pla                                     ; 8188
        sta $03                                 ; 8189
L818B:
        ldy #$01                                ; 818B
        lda ($02),y                             ; 818D
        inc $02                                 ; 818F
        bne L8195                               ; 8191
        inc $03                                 ; 8193
L8195:
        ora #$00                                ; 8195
        beq L819F                               ; 8197
        sta PPUDATA                             ; 8199
        jmp L818B                               ; 819C
L819F:
        inc $02                                 ; 819F
        bne L81A5                               ; 81A1
        inc $03                                 ; 81A3
L81A5:
        jmp ($0002)                             ; 81A5
L81A8:
        lda $10                                 ; 81A8
        and #$B8                                ; 81AA
        ldx #$05                                ; 81AC
        ldy #$00                                ; 81AE
L81B0:
        asl                                     ; 81B0
        bcc L81B4                               ; 81B1
        iny                                     ; 81B3
L81B4:
        dex                                     ; 81B4
        bne L81B0                               ; 81B5
        tya                                     ; 81B7
        lsr                                     ; 81B8
        lda $10                                 ; 81B9
        rol                                     ; 81BB
        sta $10                                 ; 81BC
        rts                                     ; 81BE
L81BF:
        .byte $01,$02,$04,$08,$10,$20,$40,$80   ; 81BF ..... @.
        .byte $FE,$FD,$FB,$F7,$EF,$DF,$BF,$7F   ; 81C7 ........
        .byte $84,$04,$85,$05,$B9,$51,$D2,$08   ; 81CF .....Q..
        .byte $10,$05,$49,$FF,$18,$69,$01,$A4   ; 81D7 ..I..i..
        .byte $05,$20,$73,$D1,$84,$00,$85,$01   ; 81DF . s.....
        .byte $28,$10,$0D,$38,$A9,$00,$E5,$00   ; 81E7 (..8....
        .byte $85,$00,$A9,$00,$E5,$01,$85,$01   ; 81EF ........
        .byte $A4,$04,$B9,$49,$D2,$08,$10,$05   ; 81F7 ...I....
        .byte $49,$FF,$18,$69,$01,$A4,$05,$20   ; 81FF I..i... 
        .byte $73,$D1,$84,$02,$85,$03,$28,$10   ; 8207 s.....(.
        .byte $0D,$38,$A9,$00,$E5,$02,$85,$02   ; 820F .8......
        .byte $A9,$00,$E5,$03,$85,$03,$60       ; 8217 ......`
L821E:
        .byte $00,$80,$00,$80                   ; 821E ....
L8222:
        .byte $00,$00,$01,$01                   ; 8222 ....
L8226:
        lda #$00                                ; 8226
        sta $50,x                               ; 8228
        sta $54,x                               ; 822A
        sta $58,x                               ; 822C
        lda $42                                 ; 822E
        bne L8240                               ; 8230
        lda $0382                               ; 8232
        sec                                     ; 8235
        sbc #$04                                ; 8236
        sta $48,x                               ; 8238
        lda $0386                               ; 823A
        sta $4C,x                               ; 823D
        rts                                     ; 823F
L8240:
        lda #$00                                ; 8240
        sta $4C,x                               ; 8242
        lda $41                                 ; 8244
        clc                                     ; 8246
        adc #$80                                ; 8247
        sta $48,x                               ; 8249
        rts                                     ; 824B
L824C:
        lda $11                                 ; 824C
        beq L8256                               ; 824E
        lda #$45                                ; 8250
        sta $10                                 ; 8252
        sta $13                                 ; 8254
L8256:
        jsr L80D0                               ; 8256
        bit PPUSTATUS                           ; 8259
        lda $41                                 ; 825C
        sta PPUSCROLL                           ; 825E
        lda #$00                                ; 8261
        sta PPUSCROLL                           ; 8263
        lda $42                                 ; 8266
        and #$03                                ; 8268
        tax                                     ; 826A
        lda $40                                 ; 826B
        clc                                     ; 826D
        adc L821E,x                             ; 826E
        sta $40                                 ; 8271
        lda $41                                 ; 8273
        adc L8222,x                             ; 8275
        sta $41                                 ; 8278
        jsr L8000                               ; 827A
        lda $13                                 ; 827D
        and #$03                                ; 827F
        bne L8295                               ; 8281
        inc $03CC                               ; 8283
        lda $44                                 ; 8286
        ora $45                                 ; 8288
        ora $46                                 ; 828A
        ora $47                                 ; 828C
        beq L8295                               ; 828E
        lda #$00                                ; 8290
        sta $03CC                               ; 8292
L8295:
        lda $03CC                               ; 8295
        cmp #$96                                ; 8298
        bcc L82A4                               ; 829A
        lda $04E8                               ; 829C
        bne L82A4                               ; 829F
        jmp LA9B1                               ; 82A1
L82A4:
        ldx #$00                                ; 82A4
L82A6:
        lda $44,x                               ; 82A6
        bne L82BA                               ; 82A8
        lda $14,x                               ; 82AA
        cmp #$C0                                ; 82AC
        bne L82BA                               ; 82AE
        jsr L8226                               ; 82B0
        jsr ResetPlayerX                        ; 82B3
        lda #$01                                ; 82B6
        sta $44,x                               ; 82B8
L82BA:
        inx                                     ; 82BA
        cpx #$04                                ; 82BB
        bne L82A6                               ; 82BD
        lda $14                                 ; 82BF
        ora $15                                 ; 82C1
        ora $16                                 ; 82C3
        ora $17                                 ; 82C5
        and #$10                                ; 82C7
        bne L82CE                               ; 82C9
        jmp L83C3                               ; 82CB
L82CE:
        jsr LDCE6                               ; 82CE
        lda $18                                 ; 82D1
        ora $19                                 ; 82D3
        and #$10                                ; 82D5
        bne L82DC                               ; 82D7
        jmp L83C3                               ; 82D9
L82DC:
        jsr LD554                               ; 82DC
        jsr LD3CE                               ; 82DF
        jsr LC210                               ; 82E2
        lda #$64                                ; 82E5
        sta $0200                               ; 82E7
        sta $0204                               ; 82EA
        sta $0208                               ; 82ED
        sta $020C                               ; 82F0
        sta $0210                               ; 82F3
        sta $0214                               ; 82F6
        lda #$6C                                ; 82F9
        sta $0203                               ; 82FB
        lda #$74                                ; 82FE
        sta $0207                               ; 8300
        lda #$7C                                ; 8303
        sta $020B                               ; 8305
        lda #$84                                ; 8308
        sta $020F                               ; 830A
        lda #$8C                                ; 830D
        sta $0213                               ; 830F
        lda #$94                                ; 8312
        sta $0217                               ; 8314
        lda #$00                                ; 8317
        sta $0202                               ; 8319
        sta $0206                               ; 831C
        sta $020A                               ; 831F
        sta $020E                               ; 8322
        sta $0212                               ; 8325
        sta $0216                               ; 8328
        lda #$50                                ; 832B
        sta $0201                               ; 832D
        lda #$41                                ; 8330
        sta $0205                               ; 8332
        lda #$55                                ; 8335
        sta $0209                               ; 8337
        lda #$53                                ; 833A
        sta $020D                               ; 833C
        lda #$45                                ; 833F
        sta $0211                               ; 8341
        lda #$44                                ; 8344
        sta $0215                               ; 8346
        jsr L80D0                               ; 8349
        lda #$80                                ; 834C
        sta PPUCTRL                             ; 834E
        lda #$02                                ; 8351
        sta OAMDMA                              ; 8353
        lda #$1F                                ; 8356
        sta PPUMASK                             ; 8358
L835B:
        jsr L8000                               ; 835B
        stx $E0                                 ; 835E
        jsr LD3CE                               ; 8360
        ldx $E0                                 ; 8363
        lda $14                                 ; 8365
        ora $15                                 ; 8367
        ora $16                                 ; 8369
        ora $17                                 ; 836B
        cmp #$30                                ; 836D
        bne L8374                               ; 836F
        jmp LA9B1                               ; 8371
L8374:
        and #$10                                ; 8374
        bne L835B                               ; 8376
        ldx #$0F                                ; 8378
L837A:
        jsr L80D0                               ; 837A
        stx $E0                                 ; 837D
        jsr LD3CE                               ; 837F
        ldx $E0                                 ; 8382
        dex                                     ; 8384
        bne L837A                               ; 8385
L8387:
        jsr L8000                               ; 8387
        stx $E0                                 ; 838A
        jsr LD3CE                               ; 838C
        ldx $E0                                 ; 838F
        lda $14                                 ; 8391
        ora $15                                 ; 8393
        and #$10                                ; 8395
        beq L8387                               ; 8397
L8399:
        jsr L8000                               ; 8399
        lda $14                                 ; 839C
        ora $15                                 ; 839E
        ora $16                                 ; 83A0
        ora $17                                 ; 83A2
        and #$10                                ; 83A4
        bne L8399                               ; 83A6
        ldx #$0F                                ; 83A8
L83AA:
        jsr L80D0                               ; 83AA
        dex                                     ; 83AD
        bne L83AA                               ; 83AE
        jsr LDCE6                               ; 83B0
        lda #$01                                ; 83B3
        sta $034D                               ; 83B5
        jsr LC210                               ; 83B8
        jsr L80D0                               ; 83BB
        lda #$88                                ; 83BE
        sta PPUCTRL                             ; 83C0
L83C3:
        lda #$01                                ; 83C3
        sta $DB                                 ; 83C5
        jsr LA914                               ; 83C7
        inc $04DF                               ; 83CA
        lda $04DF                               ; 83CD
        cmp #$3C                                ; 83D0
        bne L83E8                               ; 83D2
        lda #$00                                ; 83D4
        sta $04DF                               ; 83D6
        lda $04CA                               ; 83D9
        cmp #$02                                ; 83DC
        bne L83E8                               ; 83DE
        lda $04CB                               ; 83E0
        beq L83E8                               ; 83E3
        dec $04CB                               ; 83E5
L83E8:
        lda $04F0                               ; 83E8
        beq L83F0                               ; 83EB
        jmp L8429                               ; 83ED
L83F0:
        ldy $43                                 ; 83F0
        lda $0700,y                             ; 83F2
        bne L83FA                               ; 83F5
        jmp L841D                               ; 83F7
L83FA:
        cmp #$19                                ; 83FA
        bne L841A                               ; 83FC
        tya                                     ; 83FE
        and #$0F                                ; 83FF
        asl                                     ; 8401
        asl                                     ; 8402
        asl                                     ; 8403
        asl                                     ; 8404
        clc                                     ; 8405
        adc #$04                                ; 8406
        sta $00                                 ; 8408
        tya                                     ; 840A
        and #$F0                                ; 840B
        clc                                     ; 840D
        adc #$04                                ; 840E
        sta $01                                 ; 8410
        lda #$1E                                ; 8412
        jsr LCFB3                               ; 8414
        jmp L841D                               ; 8417
L841A:
        jsr L8506                               ; 841A
L841D:
        inc $43                                 ; 841D
        lda $43                                 ; 841F
        cmp #$F0                                ; 8421
        bcc L8429                               ; 8423
        lda #$00                                ; 8425
        sta $43                                 ; 8427
L8429:
        jsr LC210                               ; 8429
        lda $04EE                               ; 842C
        bne L8434                               ; 842F
        jsr L9A08                               ; 8431
L8434:
        lda $04EE                               ; 8434
        beq L844B                               ; 8437
        lda $44                                 ; 8439
        clc                                     ; 843B
        adc $45                                 ; 843C
        clc                                     ; 843E
        adc $46                                 ; 843F
        clc                                     ; 8441
        adc $47                                 ; 8442
        cmp #$01                                ; 8444
        bne L844B                               ; 8446
        jmp LBA19                               ; 8448
L844B:
        ldx #$00                                ; 844B
L844D:
        lda $44,x                               ; 844D
        beq L8454                               ; 844F
        jsr L8717                               ; 8451
L8454:
        inx                                     ; 8454
        cpx #$04                                ; 8455
        bne L844D                               ; 8457
        jsr L9427                               ; 8459
        jsr L95AA                               ; 845C
        lda $12                                 ; 845F
        bne L846E                               ; 8461
        lda $42                                 ; 8463
        bne L846A                               ; 8465
        jsr L853A                               ; 8467
L846A:
        lda $42                                 ; 846A
        beq L8471                               ; 846C
L846E:
        jsr L8661                               ; 846E
L8471:
        lda $03CB                               ; 8471
        beq L847E                               ; 8474
        lda #$0E                                ; 8476
        jsr LD37A                               ; 8478
        dec $03CB                               ; 847B
L847E:
        jsr LCE74                               ; 847E
        jsr LD04D                               ; 8481
        lda $04CA                               ; 8484
        cmp #$01                                ; 8487
        bne L8494                               ; 8489
        lda $13                                 ; 848B
        bne L8494                               ; 848D
        lda #$02                                ; 848F
        jsr LD007                               ; 8491
L8494:
        lda $04F1                               ; 8494
        beq L84B8                               ; 8497
        lda $13                                 ; 8499
        bne L84B8                               ; 849B
        lda $04F1                               ; 849D
        cmp #$01                                ; 84A0
        bne L84AB                               ; 84A2
        jsr L95D1                               ; 84A4
        and #$03                                ; 84A7
        bne L84B8                               ; 84A9
L84AB:
        jsr L95D1                               ; 84AB
        lsr                                     ; 84AE
        and #$03                                ; 84AF
        clc                                     ; 84B1
        adc #$04                                ; 84B2
        tax                                     ; 84B4
        jsr LD007                               ; 84B5
L84B8:
        jsr LD3CE                               ; 84B8
        lda $04CB                               ; 84BB
        bne L84CD                               ; 84BE
        inc $04DE                               ; 84C0
        lda $04DE                               ; 84C3
        cmp #$0A                                ; 84C6
        bcc L84CD                               ; 84C8
        jmp LB44E                               ; 84CA
L84CD:
        ldx #$00                                ; 84CD
L84CF:
        lda $039E,x                             ; 84CF
        beq L84ED                               ; 84D2
        lda $13                                 ; 84D4
        cmp $0394,x                             ; 84D6
        bne L84ED                               ; 84D9
        ldy $038A,x                             ; 84DB
        lda $039E,x                             ; 84DE
        bpl L84E5                               ; 84E1
        lda #$00                                ; 84E3
L84E5:
        jsr L92CB                               ; 84E5
        lda #$00                                ; 84E8
        sta $039E,x                             ; 84EA
L84ED:
        inx                                     ; 84ED
        cpx #$0A                                ; 84EE
        bne L84CF                               ; 84F0
        lda #$1E                                ; 84F2
        sta PPUMASK                             ; 84F4
        jmp L8256                               ; 84F7
        .byte $47,$61,$6D,$65,$20,$70,$61,$75   ; 84FA Game pau
        .byte $73,$65,$64,$00                   ; 8502 sed.
L8506:
        cmp #$0A                                ; 8506
        bne L850E                               ; 8508
        lda #$1A                                ; 850A
        bne L8527                               ; 850C
L850E:
        cmp #$0B                                ; 850E
        bne L8516                               ; 8510
        lda #$1B                                ; 8512
        bne L8527                               ; 8514
L8516:
        cmp #$1A                                ; 8516
        bne L851E                               ; 8518
        lda #$0A                                ; 851A
        bne L8527                               ; 851C
L851E:
        cmp #$1B                                ; 851E
        bne L8526                               ; 8520
        lda #$0B                                ; 8522
        bne L8527                               ; 8524
L8526:
        rts                                     ; 8526
L8527:
        sty $08                                 ; 8527
        jsr L92CB                               ; 8529
        ldy $08                                 ; 852C
        jsr L93EF                               ; 852E
        eor $0660,y                             ; 8531
        sta $0660,y                             ; 8534
        ldy $08                                 ; 8537
        rts                                     ; 8539
L853A:
        lda #$09                                ; 853A
        sta $AD                                 ; 853C
        sta $C9                                 ; 853E
        lda #$0A                                ; 8540
        sta $AE                                 ; 8542
        sta $CA                                 ; 8544
        lda #$19                                ; 8546
        sta $AF                                 ; 8548
        sta $CB                                 ; 854A
        lda #$1A                                ; 854C
        sta $B0                                 ; 854E
        sta $CC                                 ; 8550
        lda #$20                                ; 8552
        sta $B1                                 ; 8554
        sta $CD                                 ; 8556
        sta $B3                                 ; 8558
        sta $CF                                 ; 855A
        sta $B4                                 ; 855C
        sta $D0                                 ; 855E
        sta $B5                                 ; 8560
        sta $D1                                 ; 8562
        sta $B6                                 ; 8564
        sta $D2                                 ; 8566
        sta $B7                                 ; 8568
        sta $D3                                 ; 856A
        lda $44                                 ; 856C
        beq L85A1                               ; 856E
        ldx #$00                                ; 8570
        lda #$04                                ; 8572
L8574:
        cpx $7A                                 ; 8574
        bcc L857A                               ; 8576
        lda #$02                                ; 8578
L857A:
        sta $AD,x                               ; 857A
        inx                                     ; 857C
        cpx #$04                                ; 857D
        bne L8574                               ; 857F
        lda $76                                 ; 8581
        clc                                     ; 8583
        adc #$30                                ; 8584
        sta $AD,x                               ; 8586
        lda $036B                               ; 8588
        sta $B3                                 ; 858B
        lda $036A                               ; 858D
        sta $B4                                 ; 8590
        lda $0369                               ; 8592
        sta $B5                                 ; 8595
        lda $0368                               ; 8597
        sta $B6                                 ; 859A
        lda $0367                               ; 859C
        sta $B7                                 ; 859F
L85A1:
        lda $45                                 ; 85A1
        beq L85D6                               ; 85A3
        ldx #$00                                ; 85A5
        lda #$04                                ; 85A7
L85A9:
        cpx $7B                                 ; 85A9
        bcc L85AF                               ; 85AB
        lda #$02                                ; 85AD
L85AF:
        sta $C9,x                               ; 85AF
        inx                                     ; 85B1
        cpx #$04                                ; 85B2
        bne L85A9                               ; 85B4
        lda $77                                 ; 85B6
        clc                                     ; 85B8
        adc #$30                                ; 85B9
        sta $C9,x                               ; 85BB
        lda $0370                               ; 85BD
        sta $CF                                 ; 85C0
        lda $036F                               ; 85C2
        sta $D0                                 ; 85C5
        lda $036E                               ; 85C7
        sta $D1                                 ; 85CA
        lda $036D                               ; 85CC
        sta $D2                                 ; 85CF
        lda $036C                               ; 85D1
        sta $D3                                 ; 85D4
L85D6:
        lda $04CA                               ; 85D6
        cmp #$04                                ; 85D9
        bcs L85FC                               ; 85DB
        clc                                     ; 85DD
        adc #$13                                ; 85DE
        sta $C4                                 ; 85E0
        ldx $04CB                               ; 85E2
        lda L85FD,x                             ; 85E5
        pha                                     ; 85E8
        and #$F0                                ; 85E9
        lsr                                     ; 85EB
        lsr                                     ; 85EC
        lsr                                     ; 85ED
        lsr                                     ; 85EE
        clc                                     ; 85EF
        adc #$30                                ; 85F0
        sta $C5                                 ; 85F2
        pla                                     ; 85F4
        and #$0F                                ; 85F5
        clc                                     ; 85F7
        adc #$30                                ; 85F8
        sta $C6                                 ; 85FA
L85FC:
        rts                                     ; 85FC
L85FD:
        .byte $00,$01,$02,$03,$04,$05,$06,$07   ; 85FD ........
        .byte $08,$09,$10,$11,$12,$13,$14,$15   ; 8605 ........
        .byte $16,$17,$18,$19,$20,$21,$22,$23   ; 860D .... !"#
        .byte $24,$25,$26,$27,$28,$29,$30,$31   ; 8615 $%&'()01
        .byte $32,$33,$34,$35,$36,$37,$38,$39   ; 861D 23456789
        .byte $40,$41,$42,$43,$44,$45,$46,$47   ; 8625 @ABCDEFG
        .byte $48,$49,$50,$51,$52,$53,$54,$55   ; 862D HIPQRSTU
        .byte $56,$57,$58,$59,$60,$61,$62,$63   ; 8635 VWXY`abc
        .byte $64,$65,$66,$67,$68,$69,$70,$71   ; 863D defghipq
        .byte $72,$73,$74,$75,$76,$77,$78,$79   ; 8645 rstuvwxy
        .byte $80,$81,$82,$83,$84,$85,$86,$87   ; 864D ........
        .byte $88,$89,$90,$91,$92,$93,$94,$95   ; 8655 ........
        .byte $96,$97,$98,$99                   ; 865D ....
L8661:
        ldx #$00                                ; 8661
        jsr L86C8                               ; 8663
        ldx #$01                                ; 8666
        jsr L86C8                               ; 8668
        ldx #$02                                ; 866B
        jsr L86C8                               ; 866D
        ldx #$03                                ; 8670
        jsr L86C8                               ; 8672
        ldy $DF                                 ; 8675
        lda #$01                                ; 8677
        sta $0202,y                             ; 8679
        sta $0206,y                             ; 867C
        sta $020A,y                             ; 867F
        lda #$D8                                ; 8682
        sta $0203,y                             ; 8684
        lda #$E0                                ; 8687
        sta $0207,y                             ; 8689
        lda #$E8                                ; 868C
        sta $020B,y                             ; 868E
        lda #$14                                ; 8691
        sta $0200,y                             ; 8693
        sta $0204,y                             ; 8696
        sta $0208,y                             ; 8699
        ldx $04CA                               ; 869C
        lda L870E,x                             ; 869F
        sta $0201,y                             ; 86A2
        ldx $04CB                               ; 86A5
        lda L85FD,x                             ; 86A8
        pha                                     ; 86AB
        and #$F0                                ; 86AC
        lsr                                     ; 86AE
        lsr                                     ; 86AF
        lsr                                     ; 86B0
        lsr                                     ; 86B1
        clc                                     ; 86B2
        adc #$C0                                ; 86B3
        sta $0205,y                             ; 86B5
        pla                                     ; 86B8
        and #$0F                                ; 86B9
        clc                                     ; 86BB
        adc #$C0                                ; 86BC
        sta $0209,y                             ; 86BE
        tya                                     ; 86C1
        clc                                     ; 86C2
        adc #$0C                                ; 86C3
        sta $DF                                 ; 86C5
        rts                                     ; 86C7
L86C8:
        lda $44,x                               ; 86C8
        beq L8708                               ; 86CA
        ldy $DF                                 ; 86CC
        lda #$01                                ; 86CE
        sta $0202,y                             ; 86D0
        sta $0206,y                             ; 86D3
        lda #$10                                ; 86D6
        sta $0203,y                             ; 86D8
        lda #$1A                                ; 86DB
        sta $0207,y                             ; 86DD
        txa                                     ; 86E0
        asl                                     ; 86E1
        asl                                     ; 86E2
        asl                                     ; 86E3
        clc                                     ; 86E4
        adc #$14                                ; 86E5
        sta $0200,y                             ; 86E7
        sta $0204,y                             ; 86EA
        stx $00                                 ; 86ED
        lda $7A,x                               ; 86EF
        tax                                     ; 86F1
        lda L8709,x                             ; 86F2
        ldx $00                                 ; 86F5
        sta $0201,y                             ; 86F7
        lda $76,x                               ; 86FA
        clc                                     ; 86FC
        adc #$D0                                ; 86FD
        sta $0205,y                             ; 86FF
        tya                                     ; 8702
        clc                                     ; 8703
        adc #$08                                ; 8704
        sta $DF                                 ; 8706
L8708:
        rts                                     ; 8708
L8709:
        .byte $00,$CA,$CB,$2F,$93               ; 8709 .../.
L870E:
        .byte $4A,$5A,$4B,$5B                   ; 870E JZK[
L8712:
        lda #$00                                ; 8712
        sta $44,x                               ; 8714
        rts                                     ; 8716
L8717:
        lda $64,x                               ; 8717
        beq L8751                               ; 8719
        lda $58,x                               ; 871B
        clc                                     ; 871D
        adc #$20                                ; 871E
        bcc L8724                               ; 8720
        inc $54,x                               ; 8722
L8724:
        sta $58,x                               ; 8724
        lda $50,x                               ; 8726
        clc                                     ; 8728
        adc $58,x                               ; 8729
        sta $50,x                               ; 872B
        lda $4C,x                               ; 872D
        adc $54,x                               ; 872F
        sta $4C,x                               ; 8731
        cmp #$F4                                ; 8733
        bcc L874E                               ; 8735
; player fell off / died: one life less
LoseLife:
        nop                                     ; RAD IDE mod: infinite lives (was dec $76,x)
        nop
        lda $76,x                               ; 8739
        bne L8740                               ; 873B
        jmp L8712                               ; 873D
L8740:
        lda #$00                                ; 8740
        sta $64,x                               ; 8742
        jsr L8226                               ; 8744
        lda #$3C                                ; 8747
        sta $5C,x                               ; 8749
        jsr L8DBC                               ; 874B
L874E:
        jmp L8C14                               ; 874E
L8751:
        lda #$FF                                ; 8751
        sta $71                                 ; 8753
        lda $035F,x                             ; 8755
        beq L8768                               ; 8758
        lda $035B,x                             ; 875A
        sta $71                                 ; 875D
        lda $13                                 ; 875F
        and #$03                                ; 8761
        bne L8768                               ; 8763
        dec $035F,x                             ; 8765
L8768:
        lda $14,x                               ; 8768
        sta $00                                 ; 876A
        lda $54,x                               ; 876C
        ora $58,x                               ; 876E
        beq WalkOrRun                           ; 8770
        lda $6C,x                               ; 8772
        sta $00                                 ; 8774
WalkOrRun:
        ldy #$02                                ; 8776
        lda $00                                 ; 8778
        and #$40                                ; 877A
        beq L8780                               ; 877C
        ldy #$04                                ; 877E
L8780:
        sty $00                                 ; 8780
        lda $14,x                               ; 8782
        and #$02                                ; 8784
        beq L87B0                               ; 8786
        lda $48,x                               ; 8788
        sec                                     ; 878A
        sbc $00                                 ; 878B
        lsr                                     ; 878D
        lsr                                     ; 878E
        lsr                                     ; 878F
        lsr                                     ; 8790
        sta $01                                 ; 8791
        lda $4C,x                               ; 8793
        clc                                     ; 8795
        adc #$08                                ; 8796
        and #$F0                                ; 8798
        ora $01                                 ; 879A
        tay                                     ; 879C
        lda $0700,y                             ; 879D
        jsr L9069                               ; 87A0
        bne L87B0                               ; 87A3
        lda $48,x                               ; 87A5
        sec                                     ; 87A7
        sbc $00                                 ; 87A8
        sta $48,x                               ; 87AA
        lda #$01                                ; 87AC
        sta $72,x                               ; 87AE
L87B0:
        lda $14,x                               ; 87B0
        and #$01                                ; 87B2
        beq L87E1                               ; 87B4
        lda $48,x                               ; 87B6
        clc                                     ; 87B8
        adc #$07                                ; 87B9
        clc                                     ; 87BB
        adc $00                                 ; 87BC
        lsr                                     ; 87BE
        lsr                                     ; 87BF
        lsr                                     ; 87C0
        lsr                                     ; 87C1
        sta $01                                 ; 87C2
        lda $4C,x                               ; 87C4
        clc                                     ; 87C6
        adc #$08                                ; 87C7
        and #$F0                                ; 87C9
        ora $01                                 ; 87CB
        tay                                     ; 87CD
        lda $0700,y                             ; 87CE
        jsr L9069                               ; 87D1
        bne L87E1                               ; 87D4
        lda $48,x                               ; 87D6
        clc                                     ; 87D8
        adc $00                                 ; 87D9
        sta $48,x                               ; 87DB
        lda #$00                                ; 87DD
        sta $72,x                               ; 87DF
L87E1:
        lda $14,x                               ; 87E1
        and #$20                                ; 87E3
        beq L87FD                               ; 87E5
        jsr LD33B                               ; 87E7
        lda $04E8                               ; 87EA
        beq L87F2                               ; 87ED
        jmp LC31B                               ; 87EF
L87F2:
        lda $13                                 ; 87F2
        beq L87FD                               ; 87F4
        sta $10                                 ; 87F6
        pla                                     ; 87F8
        pla                                     ; 87F9
        jmp L8DFD                               ; 87FA
L87FD:
        lda $50,x                               ; 87FD
        clc                                     ; 87FF
        adc $58,x                               ; 8800
        bcc L8806                               ; 8802
        inc $4C,x                               ; 8804
L8806:
        sta $50,x                               ; 8806
        lda $54,x                               ; 8808
        bmi L8810                               ; 880A
        cmp #$08                                ; 880C
        bcs L881B                               ; 880E
L8810:
        lda $58,x                               ; 8810
        clc                                     ; 8812
        adc #$20                                ; 8813
        bcc L8819                               ; 8815
        inc $54,x                               ; 8817
L8819:
        sta $58,x                               ; 8819
L881B:
        lda $54,x                               ; 881B
        bpl L8840                               ; 881D
        lda $48,x                               ; 881F
        clc                                     ; 8821
        adc #$04                                ; 8822
        lsr                                     ; 8824
        lsr                                     ; 8825
        lsr                                     ; 8826
        lsr                                     ; 8827
        sta $01                                 ; 8828
        lda $4C,x                               ; 882A
        clc                                     ; 882C
        adc $54,x                               ; 882D
        and #$F0                                ; 882F
        ora $01                                 ; 8831
        tay                                     ; 8833
        lda $0700,y                             ; 8834
        jsr L9069                               ; 8837
        beq L8840                               ; 883A
        lda #$00                                ; 883C
        sta $54,x                               ; 883E
L8840:
        lda $4C,x                               ; 8840
        clc                                     ; 8842
        adc $54,x                               ; 8843
        sta $4C,x                               ; 8845
        lda $71                                 ; 8847
        cmp #$01                                ; 8849
        bne L8859                               ; 884B
        lda $14,x                               ; 884D
        and #$40                                ; 884F
        beq L8859                               ; 8851
        lda $13                                 ; 8853
        and #$07                                ; 8855
        beq L8865                               ; 8857
L8859:
        lda $14,x                               ; 8859
        and #$40                                ; 885B
        beq L88D5                               ; 885D
        lda $18,x                               ; 885F
        and #$40                                ; 8861
        bne L88D5                               ; 8863
L8865:
        lda #$04                                ; 8865
        jsr LD37A                               ; 8867
        lda $71                                 ; 886A
        cmp #$04                                ; 886C
        bne L8873                               ; 886E
        jmp L8B4C                               ; 8870
L8873:
        jsr L9592                               ; 8873
        bcc L88D5                               ; 8876
        sty $00                                 ; 8878
        ldy $72,x                               ; 887A
        lda L8CB5,y                             ; 887C
        ldy $00                                 ; 887F
        clc                                     ; 8881
        adc $48,x                               ; 8882
        sta $03D3,y                             ; 8884
        ldy $72,x                               ; 8887
        lda L8CB7,y                             ; 8889
        ldy $00                                 ; 888C
        sta $0403,y                             ; 888E
        lda #$00                                ; 8891
        sta $041B,y                             ; 8893
        sta $040F,y                             ; 8896
        sta $0427,y                             ; 8899
        sta $03F7,y                             ; 889C
        sta $03F7,y                             ; 889F
        lda $4C,x                               ; 88A2
        clc                                     ; 88A4
        adc #$04                                ; 88A5
        sta $03EB,y                             ; 88A7
        lda #$08                                ; 88AA
        sta $01                                 ; 88AC
        lda $71                                 ; 88AE
        cmp #$02                                ; 88B0
        bne L88B8                               ; 88B2
        lda #$0C                                ; 88B4
        sta $01                                 ; 88B6
L88B8:
        lda $71                                 ; 88B8
        cmp #$01                                ; 88BA
        bne L88C9                               ; 88BC
        jsr LC21E                               ; 88BE
        and #$03                                ; 88C1
        sec                                     ; 88C3
        sbc #$02                                ; 88C4
        sta $041B,y                             ; 88C6
L88C9:
        lda #$C0                                ; 88C9
        ora $01                                 ; 88CB
        sta $043F,y                             ; 88CD
        lda #$0F                                ; 88D0
        sta $0433,y                             ; 88D2
L88D5:
        lda $54,x                               ; 88D5
        bpl L88EA                               ; 88D7
        lda $14,x                               ; 88D9
        and #$80                                ; 88DB
        bne L88EA                               ; 88DD
        lda $0363,x                             ; 88DF
        bne L88EA                               ; 88E2
        lda #$00                                ; 88E4
        sta $54,x                               ; 88E6
        sta $58,x                               ; 88E8
L88EA:
        lda $60,x                               ; 88EA
        beq L88F0                               ; 88EC
        dec $60,x                               ; 88EE
L88F0:
        lda $48,x                               ; 88F0
        clc                                     ; 88F2
        adc #$04                                ; 88F3
        lsr                                     ; 88F5
        lsr                                     ; 88F6
        lsr                                     ; 88F7
        lsr                                     ; 88F8
        sta $70                                 ; 88F9
        sta $00                                 ; 88FB
        pha                                     ; 88FD
        lda $4C,x                               ; 88FE
        clc                                     ; 8900
        adc #$0F                                ; 8901
        and #$F0                                ; 8903
        ora $00                                 ; 8905
        tay                                     ; 8907
        sty $0B                                 ; 8908
        lda $0700,y                             ; 890A
        cmp #$08                                ; 890D
        bne L8923                               ; 890F
        lda #$00                                ; 8911
        jsr L92CB                               ; 8913
        lda #$03                                ; 8916
        jsr LD007                               ; 8918
        lda #$0E                                ; 891B
        jsr LD37A                               ; 891D
        jmp L8A4C                               ; 8920
L8923:
        cmp #$12                                ; 8923
        bne L8953                               ; 8925
        lda $68,x                               ; 8927
        beq L892E                               ; 8929
        jmp L8A4C                               ; 892B
L892E:
        lda #$14                                ; 892E
        sta $68,x                               ; 8930
        jsr LA09C                               ; 8932
        ldy $04C9                               ; 8935
        bmi L8950                               ; 8938
        lda $0B                                 ; 893A
        and #$F0                                ; 893C
        sec                                     ; 893E
        sbc #$20                                ; 893F
        sta $0459,y                             ; 8941
        lda $0B                                 ; 8944
        asl                                     ; 8946
        asl                                     ; 8947
        asl                                     ; 8948
        asl                                     ; 8949
        clc                                     ; 894A
        adc #$04                                ; 894B
        sta $044B,y                             ; 894D
L8950:
        jmp L8A4C                               ; 8950
L8953:
        cmp #$14                                ; 8953
        bne L89BE                               ; 8955
        lda $68,x                               ; 8957
        beq L895E                               ; 8959
        jmp L8A4C                               ; 895B
L895E:
        lda #$28                                ; 895E
        sta $68,x                               ; 8960
        jsr L80D0                               ; 8962
        lda #$00                                ; 8965
        sta PPUMASK                             ; 8967
        ldy #$00                                ; 896A
L896C:
        sty $09                                 ; 896C
        lda $0700,y                             ; 896E
        jsr L8506                               ; 8971
        lda $7E                                 ; 8974
        beq L89A2                               ; 8976
        sta PPUADDR                             ; 8978
        lda $82                                 ; 897B
        sta PPUADDR                             ; 897D
        lda $8E                                 ; 8980
        sta PPUDATA                             ; 8982
        lda $92                                 ; 8985
        sta PPUDATA                             ; 8987
        lda $86                                 ; 898A
        sta PPUADDR                             ; 898C
        lda $8A                                 ; 898F
        sta PPUADDR                             ; 8991
        lda $96                                 ; 8994
        sta PPUDATA                             ; 8996
        lda $9A                                 ; 8999
        sta PPUDATA                             ; 899B
        lda #$00                                ; 899E
        sta $7E                                 ; 89A0
L89A2:
        ldy $09                                 ; 89A2
        iny                                     ; 89A4
        cpy #$F0                                ; 89A5
        bne L896C                               ; 89A7
        lda $41                                 ; 89A9
        sta PPUSCROLL                           ; 89AB
        lda #$00                                ; 89AE
        sta PPUSCROLL                           ; 89B0
        jsr L80D0                               ; 89B3
        lda #$1E                                ; 89B6
        sta PPUMASK                             ; 89B8
        jmp L8A4C                               ; 89BB
L89BE:
        lda $0700,y                             ; 89BE
        cmp #$09                                ; 89C1
        bne L89F9                               ; 89C3
        sty $01                                 ; 89C5
        jsr L93EF                               ; 89C7
        sta $00                                 ; 89CA
        and $0660,y                             ; 89CC
        bne L89F9                               ; 89CF
        lda $00                                 ; 89D1
        ora $0660,y                             ; 89D3
        sta $0660,y                             ; 89D6
        ldy $01                                 ; 89D9
        lda #$00                                ; 89DB
        jsr L9381                               ; 89DD
        lda $04CA                               ; 89E0
        cmp #$03                                ; 89E3
        bne L89EF                               ; 89E5
        lda $04CB                               ; 89E7
        beq L89EF                               ; 89EA
        dec $04CB                               ; 89EC
L89EF:
        lda #$0E                                ; 89EF
        jsr LD37A                               ; 89F1
        lda #$01                                ; 89F4
        jsr L8D2A                               ; 89F6
L89F9:
        lda $0700,y                             ; 89F9
        cmp #$10                                ; 89FC
        bne L8A24                               ; 89FE
        lda $68,x                               ; 8A00
        beq L8A07                               ; 8A02
        jmp L8A4C                               ; 8A04
L8A07:
        dey                                     ; 8A07
        lda $0700,y                             ; 8A08
        cmp #$10                                ; 8A0B
        beq L8A15                               ; 8A0D
        cmp #$11                                ; 8A0F
        beq L8A15                               ; 8A11
        bne L8A07                               ; 8A13
L8A15:
        jsr L8B87                               ; 8A15
        lda #$3C                                ; 8A18
        sta $68,x                               ; 8A1A
        lda #$10                                ; 8A1C
        jsr LD37A                               ; 8A1E
        jmp L8A4C                               ; 8A21
L8A24:
        cmp #$11                                ; 8A24
        bne L8A4C                               ; 8A26
        lda $68,x                               ; 8A28
        beq L8A2F                               ; 8A2A
        jmp L8A4C                               ; 8A2C
L8A2F:
        iny                                     ; 8A2F
        lda $0700,y                             ; 8A30
        cmp #$10                                ; 8A33
        beq L8A3D                               ; 8A35
        cmp #$11                                ; 8A37
        beq L8A3D                               ; 8A39
        bne L8A2F                               ; 8A3B
L8A3D:
        jsr L8B87                               ; 8A3D
        lda #$3C                                ; 8A40
        sta $68,x                               ; 8A42
        lda #$10                                ; 8A44
        jsr LD37A                               ; 8A46
        jmp L8A4C                               ; 8A49
L8A4C:
        pla                                     ; 8A4C
        sta $00                                 ; 8A4D
        lda $71,x                               ; 8A4F
        cmp #$03                                ; 8A51
        bne L8A64                               ; 8A53
        lda $14,x                               ; 8A55
        and #$80                                ; 8A57
        beq L8A64                               ; 8A59
        lda $18,x                               ; 8A5B
        and #$80                                ; 8A5D
        bne L8A64                               ; 8A5F
        jmp L8ABE                               ; 8A61
L8A64:
        lda $4C,x                               ; 8A64
        clc                                     ; 8A66
        adc #$10                                ; 8A67
        and #$F0                                ; 8A69
        ora $00                                 ; 8A6B
        tay                                     ; 8A6D
        lda $0700,y                             ; 8A6E
        cmp #$1B                                ; 8A71
        beq L8A79                               ; 8A73
        cmp #$17                                ; 8A75
        bne L8A85                               ; 8A77
L8A79:
        lda $14,x                               ; 8A79
        and #$84                                ; 8A7B
        cmp #$84                                ; 8A7D
        beq L8ACD                               ; 8A7F
        lda $60,x                               ; 8A81
        bne L8AD1                               ; 8A83
L8A85:
        lda $54,x                               ; 8A85
        bpl L8A8C                               ; 8A87
        jmp L8B2F                               ; 8A89
L8A8C:
        lda $70                                 ; 8A8C
        sta $00                                 ; 8A8E
        lda $4C,x                               ; 8A90
        clc                                     ; 8A92
        adc #$10                                ; 8A93
        and #$F0                                ; 8A95
        ora $00                                 ; 8A97
        tay                                     ; 8A99
        sty $00                                 ; 8A9A
        lda $0700,y                             ; 8A9C
        cmp #$15                                ; 8A9F
        bcc L8AD1                               ; 8AA1
        lda $4C,x                               ; 8AA3
        and #$F0                                ; 8AA5
        sta $4C,x                               ; 8AA7
        lda $14,x                               ; 8AA9
        and #$40                                ; 8AAB
        sta $6C,x                               ; 8AAD
        lda #$00                                ; 8AAF
        sta $54,x                               ; 8AB1
        sta $58,x                               ; 8AB3
        sta $0363,x                             ; 8AB5
        lda $14,x                               ; 8AB8
        and #$80                                ; 8ABA
        beq L8AD1                               ; 8ABC
L8ABE:
        lda #$00                                ; 8ABE
        jsr LD37A                               ; 8AC0
        lda #$FC                                ; 8AC3
        sta $54,x                               ; 8AC5
        lda #$00                                ; 8AC7
        sta $58,x                               ; 8AC9
        beq L8AD1                               ; 8ACB
L8ACD:
        lda #$0D                                ; 8ACD
        sta $60,x                               ; 8ACF
L8AD1:
        ldy $0B                                 ; 8AD1
        lda $0700,y                             ; 8AD3
        cmp #$02                                ; 8AD6
        bne L8B00                               ; 8AD8
        lda #$07                                ; 8ADA
        jsr L92CB                               ; 8ADC
        lda $13                                 ; 8ADF
        clc                                     ; 8AE1
        adc #$04                                ; 8AE2
        sta $00                                 ; 8AE4
        lda #$02                                ; 8AE6
        jsr L9400                               ; 8AE8
        lda #$FB                                ; 8AEB
        sta $54,x                               ; 8AED
        lda #$50                                ; 8AEF
        sta $58,x                               ; 8AF1
        lda #$01                                ; 8AF3
        sta $0363,x                             ; 8AF5
        lda #$08                                ; 8AF8
        jsr LD37A                               ; 8AFA
        jmp L8B19                               ; 8AFD
L8B00:
        cmp #$01                                ; 8B00
        bne L8B0C                               ; 8B02
        txa                                     ; 8B04
        tay                                     ; 8B05
        jsr L8CF9                               ; 8B06
        jmp L8B19                               ; 8B09
L8B0C:
        cmp #$13                                ; 8B0C
        bne L8B19                               ; 8B0E
        lda #$01                                ; 8B10
        sta $64,x                               ; 8B12
        lda #$0F                                ; 8B14
        jsr LD37A                               ; 8B16
L8B19:
        lda $42                                 ; 8B19
        beq L8B2F                               ; 8B1B
        lda $48,x                               ; 8B1D
        sec                                     ; 8B1F
        sbc $41                                 ; 8B20
        cmp #$1A                                ; 8B22
        bcs L8B2F                               ; 8B24
        lda #$01                                ; 8B26
        sta $64,x                               ; 8B28
        lda #$0F                                ; 8B2A
        jsr LD37A                               ; 8B2C
L8B2F:
        lda $5C,x                               ; 8B2F
        beq L8B35                               ; 8B31
        dec $5C,x                               ; 8B33
L8B35:
        lda $68,x                               ; 8B35
        beq L8B3B                               ; 8B37
        dec $68,x                               ; 8B39
L8B3B:
        jsr L8BB8                               ; 8B3B
        bcc L8B45                               ; 8B3E
        txa                                     ; 8B40
        tay                                     ; 8B41
        jsr L8CF9                               ; 8B42
L8B45:
        jmp L8C14                               ; 8B45
        .byte $03,$FD                           ; 8B48 ..
L8B4A:
        .byte $0C,$E4                           ; 8B4A ..
L8B4C:
        stx $E0                                 ; 8B4C
        jsr L9A88                               ; 8B4E
        bcc L8B82                               ; 8B51
        ldy $E0                                 ; 8B53
        lda a:$0072,y                           ; 8B55
        sta $03                                 ; 8B58
        and #$01                                ; 8B5A
        ora #$0A                                ; 8B5C
        sta $0491,x                             ; 8B5E
        lda #$02                                ; 8B61
        sta $04AD,x                             ; 8B63
        lda a:$0048,y                           ; 8B66
        ldy $03                                 ; 8B69
        clc                                     ; 8B6B
        adc L8B4A,y                             ; 8B6C
        sta $044B,x                             ; 8B6F
        ldy $E0                                 ; 8B72
        lda a:$004C,y                           ; 8B74
        clc                                     ; 8B77
        adc #$04                                ; 8B78
        sta $0459,x                             ; 8B7A
        lda #$05                                ; 8B7D
        sta $04BB,x                             ; 8B7F
L8B82:
        ldx $E0                                 ; 8B82
        jmp L88D5                               ; 8B84
L8B87:
        tya                                     ; 8B87
        pha                                     ; 8B88
        asl                                     ; 8B89
        asl                                     ; 8B8A
        asl                                     ; 8B8B
        asl                                     ; 8B8C
        clc                                     ; 8B8D
        adc #$04                                ; 8B8E
        sta $48,x                               ; 8B90
        pla                                     ; 8B92
        and #$F0                                ; 8B93
        sta $4C,x                               ; 8B95
        rts                                     ; 8B97
L8B98:
        .byte $18,$19,$18,$1A,$3F,$1C,$3F,$1D   ; 8B98 ....?.?.
        .byte $11,$12,$11,$12,$14,$14,$14,$14   ; 8BA0 ........
        .byte $15,$15,$15,$15,$16,$17,$16,$17   ; 8BA8 ........
        .byte $1E,$1E,$1E,$1E,$5D,$5E,$5D,$5F   ; 8BB0 ....]^]_
L8BB8:
        lda $4C,x                               ; 8BB8
        clc                                     ; 8BBA
        adc #$08                                ; 8BBB
        lsr                                     ; 8BBD
        lsr                                     ; 8BBE
        and #$38                                ; 8BBF
        sta $E0                                 ; 8BC1
        lda $48,x                               ; 8BC3
        clc                                     ; 8BC5
        adc #$04                                ; 8BC6
        lsr                                     ; 8BC8
        lsr                                     ; 8BC9
        lsr                                     ; 8BCA
        lsr                                     ; 8BCB
        lsr                                     ; 8BCC
        ora $E0                                 ; 8BCD
        tay                                     ; 8BCF
        lda $06C0,y                             ; 8BD0
        beq L8C07                               ; 8BD3
        ldy #$00                                ; 8BD5
L8BD7:
        lda $043F,y                             ; 8BD7
        and #$80                                ; 8BDA
        cmp #$80                                ; 8BDC
        bne L8C02                               ; 8BDE
        lda $03D3,y                             ; 8BE0
        sta $E9                                 ; 8BE3
        lda $03EB,y                             ; 8BE5
        sta $E7                                 ; 8BE8
        lda $48,x                               ; 8BEA
        sta $EA                                 ; 8BEC
        lda $4C,x                               ; 8BEE
        sta $E8                                 ; 8BF0
        lda #$08                                ; 8BF2
        sta $EB                                 ; 8BF4
        sta $EC                                 ; 8BF6
        sta $ED                                 ; 8BF8
        asl                                     ; 8BFA
        sta $EE                                 ; 8BFB
        jsr L8CC9                               ; 8BFD
        bcs L8C09                               ; 8C00
L8C02:
        iny                                     ; 8C02
        cpy #$0C                                ; 8C03
        bne L8BD7                               ; 8C05
L8C07:
        clc                                     ; 8C07
        rts                                     ; 8C08
L8C09:
        lda $5C,x                               ; 8C09
        bne L8C13                               ; 8C0B
        lda #$00                                ; 8C0D
        sta $043F,y                             ; 8C0F
        sec                                     ; 8C12
L8C13:
        rts                                     ; 8C13
L8C14:
        lda $5C,x                               ; 8C14
        beq L8C1F                               ; 8C16
        lda $13                                 ; 8C18
        and #$01                                ; 8C1A
        beq L8C1F                               ; 8C1C
        rts                                     ; 8C1E
L8C1F:
        lda #$00                                ; 8C1F
        ldy $72,x                               ; 8C21
        beq L8C27                               ; 8C23
        lda #$40                                ; 8C25
L8C27:
        sta $00                                 ; 8C27
        txa                                     ; 8C29
        lsr                                     ; 8C2A
        bcc L8C33                               ; 8C2B
        lda $00                                 ; 8C2D
        ora #$02                                ; 8C2F
        sta $00                                 ; 8C31
L8C33:
        lda $035F,x                             ; 8C33
        beq L8C3E                               ; 8C36
        lda $00                                 ; 8C38
        ora #$03                                ; 8C3A
        sta $00                                 ; 8C3C
L8C3E:
        ldy $DF                                 ; 8C3E
        lda $4C,x                               ; 8C40
        sec                                     ; 8C42
        sbc #$01                                ; 8C43
        sta $0200,y                             ; 8C45
        clc                                     ; 8C48
        adc #$06                                ; 8C49
        sta $0208,y                             ; 8C4B
        clc                                     ; 8C4E
        adc #$02                                ; 8C4F
        sta $0204,y                             ; 8C51
        lda $00                                 ; 8C54
        sta $0202,y                             ; 8C56
        sta $0206,y                             ; 8C59
        sta $020A,y                             ; 8C5C
        lda $034F,x                             ; 8C5F
        sta $0201,y                             ; 8C62
        sty $01                                 ; 8C65
        lda $0353,x                             ; 8C67
        asl                                     ; 8C6A
        asl                                     ; 8C6B
        sta $00                                 ; 8C6C
        tay                                     ; 8C6E
        lda $14,x                               ; 8C6F
        and #$03                                ; 8C71
        beq L8C7F                               ; 8C73
        lda $13                                 ; 8C75
        lsr                                     ; 8C77
        lsr                                     ; 8C78
        and #$03                                ; 8C79
        clc                                     ; 8C7B
        adc $00                                 ; 8C7C
        tay                                     ; 8C7E
L8C7F:
        lda L8B98,y                             ; 8C7F
        ldy $01                                 ; 8C82
        sta $0205,y                             ; 8C84
        lda $0357,x                             ; 8C87
        ora #$20                                ; 8C8A
        sta $0209,y                             ; 8C8C
        lda $48,x                               ; 8C8F
        sec                                     ; 8C91
        sbc $41                                 ; 8C92
        sta $0203,y                             ; 8C94
        sta $0207,y                             ; 8C97
        sty $01                                 ; 8C9A
        lda $72,x                               ; 8C9C
        tay                                     ; 8C9E
        lda L8CB5,y                             ; 8C9F
        ldy $01                                 ; 8CA2
        clc                                     ; 8CA4
        adc $48,x                               ; 8CA5
        sec                                     ; 8CA7
        sbc $41                                 ; 8CA8
        sta $020B,y                             ; 8CAA
        tya                                     ; 8CAD
        clc                                     ; 8CAE
        adc #$10                                ; 8CAF
        tay                                     ; 8CB1
        sty $DF                                 ; 8CB2
        rts                                     ; 8CB4
L8CB5:
        .byte $08,$F8                           ; 8CB5 ..
L8CB7:
        .byte $06,$FA,$B5,$48,$95,$E9,$B5,$4C   ; 8CB7 ...H...L
        .byte $95,$E7,$A9,$08,$85,$EB,$A9,$10   ; 8CBF ........
        .byte $85,$ED                           ; 8CC7 ..
L8CC9:
        lda $EC                                 ; 8CC9
        sec                                     ; 8CCB
        sbc #$01                                ; 8CCC
        sta $EF                                 ; 8CCE
        clc                                     ; 8CD0
        adc $EB                                 ; 8CD1
        sta $F0                                 ; 8CD3
        lda $E9                                 ; 8CD5
        sbc $EA                                 ; 8CD7
        sbc $EF                                 ; 8CD9
        adc $F0                                 ; 8CDB
        bcc L8CF7                               ; 8CDD
        lda $EE                                 ; 8CDF
        sec                                     ; 8CE1
        sbc #$01                                ; 8CE2
        sta $EF                                 ; 8CE4
        clc                                     ; 8CE6
        adc $ED                                 ; 8CE7
        sta $F0                                 ; 8CE9
        lda $E7                                 ; 8CEB
        sbc $E8                                 ; 8CED
        sbc $EF                                 ; 8CEF
        adc $F0                                 ; 8CF1
        bcc L8CF7                               ; 8CF3
        sec                                     ; 8CF5
        rts                                     ; 8CF6
L8CF7:
        clc                                     ; 8CF7
        rts                                     ; 8CF8
L8CF9:
        txa                                     ; 8CF9
        pha                                     ; 8CFA
        lda a:$007A,y                           ; 8CFB
        beq L8D27                               ; 8CFE
        lda a:$005C,y                           ; 8D00
        bne L8D27                               ; 8D03
        sty $E0                                 ; 8D05
        lda #$06                                ; 8D07
        jsr LD37A                               ; 8D09
        ldy $E0                                 ; 8D0C
        stx $DE                                 ; 8D0E
        pha                                     ; 8D10
        tya                                     ; 8D11
        tax                                     ; 8D12
        dec $7A,x                               ; 8D13
        pla                                     ; 8D15
        ldx $DE                                 ; 8D16
        lda #$3C                                ; 8D18
        sta a:$005C,y                           ; 8D1A
        lda a:$007A,y                           ; 8D1D
        bne L8D27                               ; 8D20
        lda #$01                                ; 8D22
        sta a:$0064,y                           ; 8D24
L8D27:
        pla                                     ; 8D27
        tax                                     ; 8D28
        rts                                     ; 8D29
L8D2A:
        tay                                     ; 8D2A
        lda L85FD,y                             ; 8D2B
        pha                                     ; 8D2E
        and #$0F                                ; 8D2F
        sta $E0                                 ; 8D31
        pla                                     ; 8D33
        lsr                                     ; 8D34
        lsr                                     ; 8D35
        lsr                                     ; 8D36
        lsr                                     ; 8D37
        sta $E1                                 ; 8D38
        ldy L8D97,x                             ; 8D3A
        tya                                     ; 8D3D
        pha                                     ; 8D3E
        lda $0369,y                             ; 8D3F
        pha                                     ; 8D42
        lda $0367,y                             ; 8D43
        clc                                     ; 8D46
        adc $E0                                 ; 8D47
        sta $0367,y                             ; 8D49
        lda $0368,y                             ; 8D4C
        clc                                     ; 8D4F
        adc $E1                                 ; 8D50
        sta $0368,y                             ; 8D52
L8D55:
        lda $0367,y                             ; 8D55
        cmp #$3A                                ; 8D58
        bcc L8D6D                               ; 8D5A
        sec                                     ; 8D5C
        sbc #$0A                                ; 8D5D
        sta $0367,y                             ; 8D5F
        stx $DE                                 ; 8D62
        pha                                     ; 8D64
        tya                                     ; 8D65
        tax                                     ; 8D66
        inc $0368,x                             ; 8D67
        pla                                     ; 8D6A
        ldx $DE                                 ; 8D6B
L8D6D:
        iny                                     ; 8D6D
        cpy #$05                                ; 8D6E
        beq L8D76                               ; 8D70
        cpy #$0A                                ; 8D72
        bne L8D55                               ; 8D74
L8D76:
        pla                                     ; 8D76
        sta $E0                                 ; 8D77
        pla                                     ; 8D79
        tay                                     ; 8D7A
        lda $E0                                 ; 8D7B
        cmp $0369,y                             ; 8D7D
        beq L8D8D                               ; 8D80
        lda $0369,y                             ; 8D82
        cmp #$30                                ; 8D85
        beq L8D8E                               ; 8D87
        cmp #$35                                ; 8D89
        beq L8D8E                               ; 8D8B
L8D8D:
        rts                                     ; 8D8D
L8D8E:
        lda $76,x                               ; 8D8E
        cmp #$09                                ; 8D90
        beq L8D96                               ; 8D92
        inc $76,x                               ; 8D94
L8D96:
        rts                                     ; 8D96
L8D97:
        .byte $00,$05,$0A,$0F                   ; 8D97 ....
; lives at the start of a game
ResetPlayerX:
        lda #$03                                ; 8D9B
        sta $76,x                               ; 8D9D
        ldy L8D97,x                             ; 8D9F
        lda #$30                                ; 8DA2
        sta $0367,y                             ; 8DA4
        sta $0368,y                             ; 8DA7
        sta $0369,y                             ; 8DAA
        sta $036A,y                             ; 8DAD
        sta $036B,y                             ; 8DB0
        lda #$08                                ; 8DB3
        sta $0357,x                             ; 8DB5
        lda #$00                                ; 8DB8
        sta $64,x                               ; 8DBA
L8DBC:
        lda #$04                                ; 8DBC
        sta $7A,x                               ; 8DBE
        lda $DC                                 ; 8DC0
        cmp #$01                                ; 8DC2
        bcc L8DC8                               ; 8DC4
        dec $7A,x                               ; 8DC6
L8DC8:
        rts                                     ; 8DC8
        .byte $A2,$00,$20,$9B,$8D,$E8,$20,$9B   ; 8DC9 .. ... .
        .byte $8D,$E8,$20,$9B,$8D,$E8,$20,$9B   ; 8DD1 .. ... .
        .byte $8D,$A9,$06,$8D,$4F,$03,$0A,$8D   ; 8DD9 ....O...
        .byte $50,$03,$A9,$00,$8D,$53,$03,$8D   ; 8DE1 P....S..
        .byte $54,$03,$A9,$07,$8D,$55,$03,$8D   ; 8DE9 T....U..
        .byte $56,$03,$A9,$07,$8D,$51,$03,$A9   ; 8DF1 V....Q..
        .byte $04,$8D,$52,$03                   ; 8DF9 ..R.
L8DFD:
        lda $04EF                               ; 8DFD
        bne L8E13                               ; 8E00
        lda $04ED                               ; 8E02
        beq L8E0A                               ; 8E05
        jmp LB8F8                               ; 8E07
L8E0A:
        lda $DD                                 ; 8E0A
        cmp #$34                                ; 8E0C
        bne L8E13                               ; 8E0E
        jmp LA9B1                               ; 8E10
L8E13:
        lda $11                                 ; 8E13
        beq L8E20                               ; 8E15
        lda $DD                                 ; 8E17
        cmp #$03                                ; 8E19
        bne L8E20                               ; 8E1B
        jmp Reset                               ; 8E1D
L8E20:
        jsr LD33B                               ; 8E20
        jsr LDCE6                               ; 8E23
        jsr LC210                               ; 8E26
        ldx #$00                                ; 8E29
        txa                                     ; 8E2B
L8E2C:
        sta $0600,x                             ; 8E2C
        inx                                     ; 8E2F
        bne L8E2C                               ; 8E30
        sta $43                                 ; 8E32
        ldx #$00                                ; 8E34
L8E36:
        lda #$00                                ; 8E36
        sta $54,x                               ; 8E38
        sta $58,x                               ; 8E3A
        sta $0363,x                             ; 8E3C
        sta $50,x                               ; 8E3F
        sta $54,x                               ; 8E41
        sta $58,x                               ; 8E43
        sta $5C,x                               ; 8E45
        sta $68,x                               ; 8E47
        sta $035B,x                             ; 8E49
        sta $035F,x                             ; 8E4C
        lda #$04                                ; 8E4F
        ldy $DC                                 ; 8E51
        cpy #$01                                ; 8E53
        bcc L8E59                               ; 8E55
        lda #$03                                ; 8E57
L8E59:
        sta $7A,x                               ; 8E59
        inx                                     ; 8E5B
        cpx #$04                                ; 8E5C
        bne L8E36                               ; 8E5E
        lda #$00                                ; 8E60
        sta $03CC                               ; 8E62
        sta $04EB                               ; 8E65
        sta $04DC                               ; 8E68
        sta $04DE                               ; 8E6B
        sta $04DF                               ; 8E6E
        sta $72                                 ; 8E71
        sta $74                                 ; 8E73
        sta $04EF                               ; 8E75
        sta $40                                 ; 8E78
        sta $41                                 ; 8E7A
        sta $04F0                               ; 8E7C
        tax                                     ; 8E7F
L8E80:
        sta $0459,x                             ; 8E80
        sta $0467,x                             ; 8E83
        sta $0475,x                             ; 8E86
        sta $0483,x                             ; 8E89
        sta $04BB,x                             ; 8E8C
        sta $0491,x                             ; 8E8F
        sta $049F,x                             ; 8E92
        sta $04AD,x                             ; 8E95
        inx                                     ; 8E98
        cpx #$0E                                ; 8E99
        bne L8E80                               ; 8E9B
        tax                                     ; 8E9D
L8E9E:
        sta $043F,x                             ; 8E9E
        inx                                     ; 8EA1
        cpx #$0C                                ; 8EA2
        bne L8E9E                               ; 8EA4
        tax                                     ; 8EA6
L8EA7:
        sta $03B2,x                             ; 8EA7
        inx                                     ; 8EAA
        cpx #$05                                ; 8EAB
        bne L8EA7                               ; 8EAD
        tax                                     ; 8EAF
L8EB0:
        sta $0394,x                             ; 8EB0
        sta $039E,x                             ; 8EB3
        inx                                     ; 8EB6
        cpx #$0A                                ; 8EB7
        bne L8EB0                               ; 8EB9
        tax                                     ; 8EBB
L8EBC:
        sta $0680,x                             ; 8EBC
        inx                                     ; 8EBF
        cpx #$40                                ; 8EC0
        bne L8EBC                               ; 8EC2
        lda #$00                                ; 8EC4
        sta $42                                 ; 8EC6
        lda #$20                                ; 8EC8
        sta $49                                 ; 8ECA
        lda #$28                                ; 8ECC
        sta $48                                 ; 8ECE
        lda #$D0                                ; 8ED0
        sta $4C                                 ; 8ED2
        sta $4D                                 ; 8ED4
        sta $4E                                 ; 8ED6
        sta $4F                                 ; 8ED8
        lda #$22                                ; 8EDA
        sta $4A                                 ; 8EDC
        lda #$26                                ; 8EDE
        sta $4B                                 ; 8EE0
        lda #$01                                ; 8EE2
        sta $73                                 ; 8EE4
        lda #$00                                ; 8EE6
        sta PPUMASK                             ; 8EE8
        lda $DD                                 ; 8EEB
        jsr LBD82                               ; 8EED
        jsr L9074                               ; 8EF0
        lda $04E8                               ; 8EF3
        ora $04EB                               ; 8EF6
        beq L8F22                               ; 8EF9
        lda $04E9                               ; 8EFB
        asl                                     ; 8EFE
        asl                                     ; 8EFF
        asl                                     ; 8F00
        asl                                     ; 8F01
        sta $49                                 ; 8F02
        clc                                     ; 8F04
        adc #$08                                ; 8F05
        sta $48                                 ; 8F07
        sec                                     ; 8F09
        sbc #$04                                ; 8F0A
        sta $4A                                 ; 8F0C
        clc                                     ; 8F0E
        adc #$02                                ; 8F0F
        sta $4B                                 ; 8F11
        lda $04EA                               ; 8F13
        asl                                     ; 8F16
        asl                                     ; 8F17
        asl                                     ; 8F18
        asl                                     ; 8F19
        sta $4C                                 ; 8F1A
        sta $4D                                 ; 8F1C
        sta $4E                                 ; 8F1E
        sta $4F                                 ; 8F20
L8F22:
        jsr L80D0                               ; 8F22
        lda #$1E                                ; 8F25
        sta PPUMASK                             ; 8F27
        inc $DD                                 ; 8F2A
        lda $04CA                               ; 8F2C
        cmp #$03                                ; 8F2F
        bne L8F45                               ; 8F31
        ldx #$00                                ; 8F33
        stx $04CB                               ; 8F35
L8F38:
        lda $0700,x                             ; 8F38
        cmp #$09                                ; 8F3B
        bne L8F42                               ; 8F3D
        inc $04CB                               ; 8F3F
L8F42:
        inx                                     ; 8F42
        bne L8F38                               ; 8F43
L8F45:
        lda $48                                 ; 8F45
        sta $0382                               ; 8F47
        lda $4C                                 ; 8F4A
        sta $0386                               ; 8F4C
        ldy #$00                                ; 8F4F
L8F51:
        lda $0700,y                             ; 8F51
        cmp #$0C                                ; 8F54
        bcc L8F81                               ; 8F56
        cmp #$10                                ; 8F58
        bcs L8F81                               ; 8F5A
        pha                                     ; 8F5C
        jsr L9A88                               ; 8F5D
        pla                                     ; 8F60
        bcc L8F81                               ; 8F61
        sec                                     ; 8F63
        sbc #$0C                                ; 8F64
        clc                                     ; 8F66
        adc #$04                                ; 8F67
        sta $04AD,x                             ; 8F69
        tya                                     ; 8F6C
        and #$0F                                ; 8F6D
        asl                                     ; 8F6F
        asl                                     ; 8F70
        asl                                     ; 8F71
        asl                                     ; 8F72
        sta $044B,x                             ; 8F73
        tya                                     ; 8F76
        and #$F0                                ; 8F77
        sta $0459,x                             ; 8F79
        lda #$0A                                ; 8F7C
        sta $0491,x                             ; 8F7E
L8F81:
        iny                                     ; 8F81
        cpy #$F0                                ; 8F82
        bne L8F51                               ; 8F84
        jsr LD33B                               ; 8F86
        lda #$00                                ; 8F89
        jsr LD504                               ; 8F8B
        jmp L824C                               ; 8F8E
L8F91:
        .byte $20                               ; 8F91  
L8F92:
        .byte $20                               ; 8F92  
L8F93:
        .byte $20                               ; 8F93  
L8F94:
        .byte $20,$20,$20,$84,$84,$20,$20,$94   ; 8F94    ..  .
        .byte $95,$20,$20,$B4,$B5,$C4,$C5,$C4   ; 8F9C .  .....
        .byte $C5,$D0,$D1,$E0,$E1,$D1,$D2,$E1   ; 8FA4 ........
        .byte $E2,$20,$20,$A4,$A5,$D4,$D5,$D4   ; 8FAC .  .....
        .byte $D5,$E4,$E5,$E4,$E5,$85,$85,$85   ; 8FB4 ........
        .byte $85,$93,$93,$20,$20,$20,$20,$20   ; 8FBC ...     
        .byte $20,$20,$20,$20,$20,$20,$20,$20   ; 8FC4         
        .byte $20,$20,$20,$20,$20,$B0,$B1,$B0   ; 8FCC      ...
        .byte $B1,$B2,$B3,$B2,$B3,$20,$20,$83   ; 8FD4 .....  .
        .byte $83,$20,$20,$82,$82,$E6,$E7,$E6   ; 8FDC .  .....
        .byte $E7,$89,$8A,$8B,$8C,$90,$91,$20   ; 8FE4 ....... 
        .byte $20,$91,$91,$20,$20,$91,$92,$20   ; 8FEC  ..  .. 
        .byte $20,$99,$9A,$9B,$9C,$86,$86,$86   ; 8FF4  .......
        .byte $86,$96,$96,$20,$20,$DA,$DB,$EA   ; 8FFC ...  ...
        .byte $EB,$DB,$DB,$EB,$EB,$DB,$DC,$EB   ; 9004 ........
        .byte $EC,$DA,$DC,$EA,$EC,$EA,$EB,$EA   ; 900C ........
        .byte $EB,$EB,$EB,$EB,$EB,$EB,$EC,$EB   ; 9014 ........
        .byte $EC,$EA,$EC,$EA,$EC               ; 901C .....
L9021:
        .byte $00,$01,$02,$03,$04,$00,$00,$02   ; 9021 ........
        .byte $08,$09,$0A,$0B,$0C,$0D,$0E,$0F   ; 9029 ........
        .byte $10,$11,$12,$13,$14,$15,$17,$17   ; 9031 ........
        .byte $17,$19,$1A,$1B,$15,$15,$15,$15   ; 9039 ........
        .byte $15,$15,$15,$15                   ; 9041 ....
L9045:
        .byte $00,$00,$00,$00,$00,$00,$00,$00   ; 9045 ........
        .byte $01,$01,$02,$02,$00,$00,$00,$00   ; 904D ........
        .byte $00,$00,$00,$00,$00,$04,$00,$00   ; 9055 ........
        .byte $00,$04,$06,$02,$05,$05,$05,$05   ; 905D ........
        .byte $05,$05,$05,$05                   ; 9065 ....
L9069:
        sty $E2                                 ; 9069
        tay                                     ; 906B
        lda L9045,y                             ; 906C
        ldy $E2                                 ; 906F
        and #$04                                ; 9071
        rts                                     ; 9073
L9074:
        lda $04E8                               ; 9074
        beq L907C                               ; 9077
        jmp L90EB                               ; 9079
L907C:
        lda #$00                                ; 907C
        sta $034E                               ; 907E
        tax                                     ; 9081
L9082:
        sta $0700,x                             ; 9082
        inx                                     ; 9085
        bne L9082                               ; 9086
        lda $04E6                               ; 9088
        beq L9090                               ; 908B
        jmp L90E3                               ; 908D
L9090:
        lda #$0C                                ; 9090
        sta $00                                 ; 9092
L9094:
        jsr L81A8                               ; 9094
        and #$0C                                ; 9097
        beq L90D2                               ; 9099
        inc $034E                               ; 909B
        lda $00                                 ; 909E
        cmp #$01                                ; 90A0
        bne L90A7                               ; 90A2
        jmp L90D2                               ; 90A4
L90A7:
        asl                                     ; 90A7
        asl                                     ; 90A8
        asl                                     ; 90A9
        asl                                     ; 90AA
        sta $02                                 ; 90AB
        jsr LC21E                               ; 90AD
        clc                                     ; 90B0
        ror                                     ; 90B1
        ror                                     ; 90B2
        ror                                     ; 90B3
        and #$0F                                ; 90B4
        ora $02                                 ; 90B6
        tax                                     ; 90B8
        lda #$04                                ; 90B9
        sta $01                                 ; 90BB
L90BD:
        lda #$17                                ; 90BD
        sta $0700,x                             ; 90BF
        txa                                     ; 90C2
        and #$F0                                ; 90C3
        sta $02                                 ; 90C5
        inx                                     ; 90C7
        txa                                     ; 90C8
        and #$0F                                ; 90C9
        ora $02                                 ; 90CB
        tax                                     ; 90CD
        dec $01                                 ; 90CE
        bne L90BD                               ; 90D0
L90D2:
        dec $00                                 ; 90D2
        bne L9094                               ; 90D4
        lda $034E                               ; 90D6
        cmp #$05                                ; 90D9
        bcs L90E0                               ; 90DB
        jmp L9074                               ; 90DD
L90E0:
        jsr L90F5                               ; 90E0
L90E3:
        lda $04E7                               ; 90E3
        beq L90EB                               ; 90E6
        jsr LC12A                               ; 90E8
L90EB:
        jsr LAF3A                               ; 90EB
        jsr L917A                               ; 90EE
        jsr L923D                               ; 90F1
        rts                                     ; 90F4
L90F5:
        lda #$15                                ; 90F5
        ldx #$00                                ; 90F7
L90F9:
        sta $07E1,x                             ; 90F9
        inx                                     ; 90FC
        cpx #$0E                                ; 90FD
        bne L90F9                               ; 90FF
        lda $11                                 ; 9101
        bne L910D                               ; 9103
        lda #$00                                ; 9105
        sta $07E7                               ; 9107
        sta $07E8                               ; 910A
L910D:
        rts                                     ; 910D
L910E:
        lda #$0A                                ; 910E
        sta $00                                 ; 9110
L9112:
        jsr L81A8                               ; 9112
        lsr                                     ; 9115
        lsr                                     ; 9116
        tax                                     ; 9117
        and #$0F                                ; 9118
        cmp #$0F                                ; 911A
        beq L9137                               ; 911C
        txa                                     ; 911E
        sec                                     ; 911F
        sbc #$E0                                ; 9120
        tax                                     ; 9122
        lda $0700,x                             ; 9123
        bne L9137                               ; 9126
        lda $0701,x                             ; 9128
        bne L9137                               ; 912B
        lda #$05                                ; 912D
        sta $0700,x                             ; 912F
        lda #$06                                ; 9132
        sta $0701,x                             ; 9134
L9137:
        dec $00                                 ; 9137
        bne L9112                               ; 9139
        rts                                     ; 913B
L913C:
        cmp #$15                                ; 913C
        beq L9148                               ; 913E
        cmp #$1C                                ; 9140
        bcc L914A                               ; 9142
        cmp #$24                                ; 9144
        bcs L914A                               ; 9146
L9148:
        sec                                     ; 9148
        rts                                     ; 9149
L914A:
        clc                                     ; 914A
        rts                                     ; 914B
L914C:
        lda $00                                 ; 914C
        sec                                     ; 914E
        sbc #$10                                ; 914F
        sta $00                                 ; 9151
        tax                                     ; 9153
        cpx #$30                                ; 9154
        bcc L9179                               ; 9156
        lda $01                                 ; 9158
        sec                                     ; 915A
        sbc #$10                                ; 915B
        sta $01                                 ; 915D
L915F:
        lda $0700,x                             ; 915F
        cmp #$15                                ; 9162
        bne L9179                               ; 9164
        inx                                     ; 9166
        cpx $01                                 ; 9167
        bne L915F                               ; 9169
        ldx $00                                 ; 916B
        lda #$1D                                ; 916D
L916F:
        sta $0700,x                             ; 916F
        inx                                     ; 9172
        cpx $01                                 ; 9173
        bne L916F                               ; 9175
        beq L914C                               ; 9177
L9179:
        rts                                     ; 9179
L917A:
        jsr L910E                               ; 917A
        ldx #$00                                ; 917D
        stx $00                                 ; 917F
L9181:
        txa                                     ; 9181
        and #$0F                                ; 9182
        tay                                     ; 9184
        lda $0700,x                             ; 9185
        cmp #$17                                ; 9188
        bne L91A4                               ; 918A
        cpy #$00                                ; 918C
        beq L9198                               ; 918E
        lda $06FF,x                             ; 9190
        beq L9198                               ; 9193
        inc $0700,x                             ; 9195
L9198:
        cpy #$0F                                ; 9198
        beq L91A4                               ; 919A
        lda $0701,x                             ; 919C
        beq L91A4                               ; 919F
        dec $0700,x                             ; 91A1
L91A4:
        inx                                     ; 91A4
        cpx #$F0                                ; 91A5
        bcc L9181                               ; 91A7
        ldx #$E0                                ; 91A9
L91AB:
        lda $0700,x                             ; 91AB
        cmp #$15                                ; 91AE
        bne L91BF                               ; 91B0
        lda $00                                 ; 91B2
        bne L91B8                               ; 91B4
        stx $00                                 ; 91B6
L91B8:
        lda #$1D                                ; 91B8
        sta $0700,x                             ; 91BA
        bne L91D0                               ; 91BD
L91BF:
        lda $00                                 ; 91BF
        beq L91D0                               ; 91C1
        stx $01                                 ; 91C3
        txa                                     ; 91C5
        pha                                     ; 91C6
        jsr L914C                               ; 91C7
        lda #$00                                ; 91CA
        sta $00                                 ; 91CC
        pla                                     ; 91CE
        tax                                     ; 91CF
L91D0:
        inx                                     ; 91D0
        cpx #$F0                                ; 91D1
        bne L91AB                               ; 91D3
        lda $00                                 ; 91D5
        beq L91DE                               ; 91D7
        stx $01                                 ; 91D9
        jsr L914C                               ; 91DB
L91DE:
        ldx #$EF                                ; 91DE
L91E0:
        lda $0700,x                             ; 91E0
        cmp #$1D                                ; 91E3
        bne L9233                               ; 91E5
        txa                                     ; 91E7
        pha                                     ; 91E8
        and #$F0                                ; 91E9
        sta $00                                 ; 91EB
        pla                                     ; 91ED
        clc                                     ; 91EE
        adc #$01                                ; 91EF
        and #$0F                                ; 91F1
        ora $00                                 ; 91F3
        tay                                     ; 91F5
        lda #$00                                ; 91F6
        sta $01                                 ; 91F8
        lda $0700,y                             ; 91FA
        jsr L913C                               ; 91FD
        rol $01                                 ; 9200
        txa                                     ; 9202
        sec                                     ; 9203
        sbc #$01                                ; 9204
        and #$0F                                ; 9206
        ora $00                                 ; 9208
        tay                                     ; 920A
        lda $0700,y                             ; 920B
        jsr L913C                               ; 920E
        rol $01                                 ; 9211
        ldy $01                                 ; 9213
        lda L9239,y                             ; 9215
        sta $0700,x                             ; 9218
        cpx #$E0                                ; 921B
        bcs L9233                               ; 921D
        lda $0710,x                             ; 921F
        cmp #$1C                                ; 9222
        bcc L9233                               ; 9224
        cmp #$24                                ; 9226
        bcs L9233                               ; 9228
        lda $0710,x                             ; 922A
        clc                                     ; 922D
        adc #$04                                ; 922E
        sta $0710,x                             ; 9230
L9233:
        dex                                     ; 9233
        cpx #$2F                                ; 9234
        bne L91E0                               ; 9236
        rts                                     ; 9238
L9239:
        .byte $1F,$1E,$1C,$1D                   ; 9239 ....
L923D:
        lda #$00                                ; 923D
        sta PPUSCROLL                           ; 923F
        sta PPUSCROLL                           ; 9242
        tax                                     ; 9245
L9246:
        sta $0680,x                             ; 9246
        inx                                     ; 9249
        cpx #$40                                ; 924A
        bne L9246                               ; 924C
        lda #$20                                ; 924E
        sta PPUADDR                             ; 9250
        lda #$00                                ; 9253
        sta PPUADDR                             ; 9255
        tax                                     ; 9258
L9259:
        lda #$10                                ; 9259
        sta $00                                 ; 925B
L925D:
        lda $0700,x                             ; 925D
        asl                                     ; 9260
        asl                                     ; 9261
        tay                                     ; 9262
        lda L8F91,y                             ; 9263
        sta PPUDATA                             ; 9266
        lda L8F92,y                             ; 9269
        sta PPUDATA                             ; 926C
        inx                                     ; 926F
        dec $00                                 ; 9270
        bne L925D                               ; 9272
        txa                                     ; 9274
        sec                                     ; 9275
        sbc #$10                                ; 9276
        tax                                     ; 9278
        lda #$10                                ; 9279
        sta $00                                 ; 927B
L927D:
        txa                                     ; 927D
        lda $0700,x                             ; 927E
        pha                                     ; 9281
        pha                                     ; 9282
        tay                                     ; 9283
        lda L9021,y                             ; 9284
        sta $0700,x                             ; 9287
        pla                                     ; 928A
        asl                                     ; 928B
        asl                                     ; 928C
        tay                                     ; 928D
        lda L8F93,y                             ; 928E
        sta PPUDATA                             ; 9291
        lda L8F94,y                             ; 9294
        sta PPUDATA                             ; 9297
        pla                                     ; 929A
        tay                                     ; 929B
        lda L9045,y                             ; 929C
        pha                                     ; 929F
        txa                                     ; 92A0
        tay                                     ; 92A1
        pla                                     ; 92A2
        and #$03                                ; 92A3
        beq L92AC                               ; 92A5
        ora #$80                                ; 92A7
        jsr L9381                               ; 92A9
L92AC:
        inx                                     ; 92AC
        dec $00                                 ; 92AD
        bne L927D                               ; 92AF
        cpx #$F0                                ; 92B1
        bne L9259                               ; 92B3
        ldx #$00                                ; 92B5
L92B7:
        lda $0680,x                             ; 92B7
        sta PPUDATA                             ; 92BA
        inx                                     ; 92BD
        cpx #$40                                ; 92BE
        bne L92B7                               ; 92C0
        lda #$00                                ; 92C2
        sta PPUSCROLL                           ; 92C4
        sta PPUSCROLL                           ; 92C7
        rts                                     ; 92CA
L92CB:
        sty $01                                 ; 92CB
        stx $02                                 ; 92CD
        cmp #$FF                                ; 92CF
        bne L92E2                               ; 92D1
        jsr L93EF                               ; 92D3
        ora $0660,y                             ; 92D6
        sta $0660,y                             ; 92D9
        ldy $01                                 ; 92DC
        lda #$00                                ; 92DE
        beq L92E5                               ; 92E0
L92E2:
        sta $0700,y                             ; 92E2
L92E5:
        sty $00                                 ; 92E5
        asl                                     ; 92E7
        asl                                     ; 92E8
        tax                                     ; 92E9
        ldy #$00                                ; 92EA
L92EC:
        lda a:$007E,y                           ; 92EC
        beq L92FC                               ; 92EF
        iny                                     ; 92F1
        cpy #$04                                ; 92F2
        bne L92EC                               ; 92F4
        ldy $01                                 ; 92F6
        ldx $02                                 ; 92F8
        clc                                     ; 92FA
        rts                                     ; 92FB
L92FC:
        lda L8F91,x                             ; 92FC
        sta a:$008E,y                           ; 92FF
        lda L8F92,x                             ; 9302
        sta a:$0092,y                           ; 9305
        lda L8F93,x                             ; 9308
        sta a:$0096,y                           ; 930B
        lda L8F94,x                             ; 930E
        sta a:$009A,y                           ; 9311
        tya                                     ; 9314
        tax                                     ; 9315
        lda $00                                 ; 9316
        pha                                     ; 9318
        lsr                                     ; 9319
        lsr                                     ; 931A
        and #$3C                                ; 931B
        lsr                                     ; 931D
        tay                                     ; 931E
        pla                                     ; 931F
        and #$0F                                ; 9320
        asl                                     ; 9322
        sta $00                                 ; 9323
        lda L9345,y                             ; 9325
        sta $7E,x                               ; 9328
        lda L9346,y                             ; 932A
        sta $86,x                               ; 932D
        lda L9363,y                             ; 932F
        clc                                     ; 9332
        adc $00                                 ; 9333
        sta $82,x                               ; 9335
        lda L9364,y                             ; 9337
        clc                                     ; 933A
        adc $00                                 ; 933B
        sta $8A,x                               ; 933D
        sec                                     ; 933F
        ldy $01                                 ; 9340
        ldx $02                                 ; 9342
        rts                                     ; 9344
L9345:
        .byte $20                               ; 9345  
L9346:
        .byte $20,$20,$20,$20,$20,$20,$20,$21   ; 9346        !
        .byte $21,$21,$21,$21,$21,$21,$21,$22   ; 934E !!!!!!!"
        .byte $22,$22,$22,$22,$22,$22,$22,$23   ; 9356 """""""#
        .byte $23,$23,$23,$23,$23               ; 935E #####
L9363:
        .byte $00                               ; 9363 .
L9364:
        .byte $20,$40,$60,$80,$A0,$C0,$E0,$00   ; 9364  @`.....
        .byte $20,$40,$60,$80,$A0,$C0,$E0,$00   ; 936C  @`.....
        .byte $20,$40,$60,$80,$A0,$C0,$E0,$00   ; 9374  @`.....
        .byte $20,$40,$60,$80,$A0               ; 937C  @`..
L9381:
        stx $07                                 ; 9381
        sta $06                                 ; 9383
        and #$03                                ; 9385
        tax                                     ; 9387
        lda L93E3,x                             ; 9388
        sta $05                                 ; 938B
        ldx #$00                                ; 938D
        tya                                     ; 938F
        lsr                                     ; 9390
        bcc L9394                               ; 9391
        inx                                     ; 9393
L9394:
        tya                                     ; 9394
        and #$10                                ; 9395
        beq L939B                               ; 9397
        inx                                     ; 9399
        inx                                     ; 939A
L939B:
        lda $05                                 ; 939B
        and L93E7,x                             ; 939D
        sta $05                                 ; 93A0
        tya                                     ; 93A2
        and #$E0                                ; 93A3
        lsr                                     ; 93A5
        lsr                                     ; 93A6
        sta $04                                 ; 93A7
        tya                                     ; 93A9
        and #$0E                                ; 93AA
        lsr                                     ; 93AC
        ora $04                                 ; 93AD
        tay                                     ; 93AF
        lda $0680,y                             ; 93B0
        and L93EB,x                             ; 93B3
        ora $05                                 ; 93B6
        sta $0680,y                             ; 93B8
        sta $05                                 ; 93BB
        ldx $07                                 ; 93BD
        bit $06                                 ; 93BF
        bpl L93C4                               ; 93C1
        rts                                     ; 93C3
L93C4:
        ldx #$00                                ; 93C4
L93C6:
        lda $9E,x                               ; 93C6
        beq L93D1                               ; 93C8
        inx                                     ; 93CA
        cpx #$05                                ; 93CB
        bne L93C6                               ; 93CD
        clc                                     ; 93CF
        rts                                     ; 93D0
L93D1:
        lda $05                                 ; 93D1
        sta $A8,x                               ; 93D3
        lda #$23                                ; 93D5
        sta $9E,x                               ; 93D7
        tya                                     ; 93D9
        clc                                     ; 93DA
        adc #$C0                                ; 93DB
        sta $A3,x                               ; 93DD
        sec                                     ; 93DF
        ldx $07                                 ; 93E0
        rts                                     ; 93E2
L93E3:
        .byte $00,$55,$AA,$FF                   ; 93E3 .U..
L93E7:
        .byte $03,$0C,$30,$C0                   ; 93E7 ..0.
L93EB:
        .byte $FC,$F3,$CF,$3F                   ; 93EB ...?
L93EF:
        tya                                     ; 93EF
        pha                                     ; 93F0
        lsr                                     ; 93F1
        lsr                                     ; 93F2
        lsr                                     ; 93F3
        sta $E1                                 ; 93F4
        pla                                     ; 93F6
        and #$07                                ; 93F7
        tay                                     ; 93F9
        lda L81BF,y                             ; 93FA
        ldy $E1                                 ; 93FD
        rts                                     ; 93FF
L9400:
        sta $01                                 ; 9400
        sty $02                                 ; 9402
        ldy #$00                                ; 9404
L9406:
        lda $039E,y                             ; 9406
        beq L9414                               ; 9409
        iny                                     ; 940B
        cpy #$0A                                ; 940C
        bne L9406                               ; 940E
        ldy $02                                 ; 9410
        clc                                     ; 9412
        rts                                     ; 9413
L9414:
        lda $00                                 ; 9414
        sta $0394,y                             ; 9416
        lda $01                                 ; 9419
        sta $039E,y                             ; 941B
        lda $02                                 ; 941E
        sta $038A,y                             ; 9420
        ldy $02                                 ; 9423
        sec                                     ; 9425
        rts                                     ; 9426
L9427:
        lda #$00                                ; 9427
        sta $00                                 ; 9429
        tax                                     ; 942B
L942C:
        sta $06C0,x                             ; 942C
        sta $06C8,x                             ; 942F
        sta $06D0,x                             ; 9432
        sta $06D8,x                             ; 9435
        sta $06E0,x                             ; 9438
        sta $06E8,x                             ; 943B
        sta $06F0,x                             ; 943E
        sta $06F8,x                             ; 9441
        inx                                     ; 9444
        cpx #$08                                ; 9445
        bne L942C                               ; 9447
        ldy $DF                                 ; 9449
L944B:
        ldx $00                                 ; 944B
        lda $043F,x                             ; 944D
        bmi L9455                               ; 9450
        jmp L9576                               ; 9452
L9455:
        lda $03DF,x                             ; 9455
        clc                                     ; 9458
        adc $040F,x                             ; 9459
        sta $03DF,x                             ; 945C
        lda $03D3,x                             ; 945F
        adc $0403,x                             ; 9462
        sta $03D3,x                             ; 9465
        lda $03F7,x                             ; 9468
        clc                                     ; 946B
        adc $0427,x                             ; 946C
        sta $03F7,x                             ; 946F
        lda $03EB,x                             ; 9472
        adc $041B,x                             ; 9475
        sta $03EB,x                             ; 9478
        sty $E1                                 ; 947B
        lda $03EB,x                             ; 947D
        lsr                                     ; 9480
        lsr                                     ; 9481
        and #$38                                ; 9482
        sta $01                                 ; 9484
        lda $03D3,x                             ; 9486
        and #$E0                                ; 9489
        lsr                                     ; 948B
        sta $02                                 ; 948C
        lsr                                     ; 948E
        lsr                                     ; 948F
        lsr                                     ; 9490
        lsr                                     ; 9491
        ora $01                                 ; 9492
        tay                                     ; 9494
        lda #$01                                ; 9495
        sta $06C0,y                             ; 9497
        lda $02                                 ; 949A
        clc                                     ; 949C
        adc #$07                                ; 949D
        and #$70                                ; 949F
        cmp $02                                 ; 94A1
        bne L94B1                               ; 94A3
        lsr                                     ; 94A5
        lsr                                     ; 94A6
        lsr                                     ; 94A7
        lsr                                     ; 94A8
        ora $01                                 ; 94A9
        tay                                     ; 94AB
        lda #$01                                ; 94AC
        sta $06C0,y                             ; 94AE
L94B1:
        lda $03EB,x                             ; 94B1
        clc                                     ; 94B4
        adc #$07                                ; 94B5
        lsr                                     ; 94B7
        lsr                                     ; 94B8
        and #$38                                ; 94B9
        sta $01                                 ; 94BB
        lda $03D3,x                             ; 94BD
        clc                                     ; 94C0
        adc #$04                                ; 94C1
        lsr                                     ; 94C3
        lsr                                     ; 94C4
        lsr                                     ; 94C5
        lsr                                     ; 94C6
        lsr                                     ; 94C7
        ora $01                                 ; 94C8
        tay                                     ; 94CA
        lda #$01                                ; 94CB
        sta $06C0,y                             ; 94CD
        lda $03D3,x                             ; 94D0
        clc                                     ; 94D3
        adc #$04                                ; 94D4
        lsr                                     ; 94D6
        lsr                                     ; 94D7
        lsr                                     ; 94D8
        lsr                                     ; 94D9
        sta $01                                 ; 94DA
        lda $03EB,x                             ; 94DC
        and #$F0                                ; 94DF
        ora $01                                 ; 94E1
        tay                                     ; 94E3
        lda $0700,y                             ; 94E4
        cmp #$04                                ; 94E7
        bne L9510                               ; 94E9
        lda $0403,x                             ; 94EB
        eor #$FF                                ; 94EE
        clc                                     ; 94F0
        adc #$01                                ; 94F1
        sta $0403,x                             ; 94F3
        lda $0433,x                             ; 94F6
        clc                                     ; 94F9
        adc #$0C                                ; 94FA
        sta $0433,x                             ; 94FC
        jsr L95D1                               ; 94FF
        sta $0427,x                             ; 9502
        jsr L95D1                               ; 9505
        and #$01                                ; 9508
        sec                                     ; 950A
        sbc #$01                                ; 950B
        sta $041B,x                             ; 950D
L9510:
        lda $043F,x                             ; 9510
        and #$0F                                ; 9513
        cmp #$0C                                ; 9515
        bne L953C                               ; 9517
        lda $0433,x                             ; 9519
        cmp #$01                                ; 951C
        bne L953C                               ; 951E
        lda $00                                 ; 9520
        pha                                     ; 9522
        lda $03D3,x                             ; 9523
        sta $00                                 ; 9526
        lda $03EB,x                             ; 9528
        sta $01                                 ; 952B
        lda #$0E                                ; 952D
        ldy $04EE                               ; 952F
        beq L9536                               ; 9532
        lda #$1E                                ; 9534
L9536:
        jsr LCFB3                               ; 9536
        pla                                     ; 9539
        sta $00                                 ; 953A
L953C:
        ldy $E1                                 ; 953C
        lda $03EB,x                             ; 953E
        sta $0200,y                             ; 9541
        lda #$00                                ; 9544
        sta $0202,y                             ; 9546
        lda $043F,x                             ; 9549
        and #$40                                ; 954C
        bne L9555                               ; 954E
        lda #$01                                ; 9550
        sta $0202,y                             ; 9552
L9555:
        lda $043F,x                             ; 9555
        and #$0F                                ; 9558
        ora #$30                                ; 955A
        sta $0201,y                             ; 955C
        lda $03D3,x                             ; 955F
        sec                                     ; 9562
        sbc $41                                 ; 9563
        sta $0203,y                             ; 9565
        dec $0433,x                             ; 9568
        bne L9572                               ; 956B
        lda #$00                                ; 956D
        sta $043F,x                             ; 956F
L9572:
        iny                                     ; 9572
        iny                                     ; 9573
        iny                                     ; 9574
        iny                                     ; 9575
L9576:
        inc $00                                 ; 9576
        lda $00                                 ; 9578
        cmp #$0C                                ; 957A
        beq L9581                               ; 957C
        jmp L944B                               ; 957E
L9581:
        lda #$00                                ; 9581
        sta $0200,y                             ; 9583
        sta $0202,y                             ; 9586
        sta $0201,y                             ; 9589
        sta $0203,y                             ; 958C
        sty $DF                                 ; 958F
        rts                                     ; 9591
L9592:
        pha                                     ; 9592
        ldy #$00                                ; 9593
L9595:
        lda $043F,y                             ; 9595
        bpl L95A2                               ; 9598
        iny                                     ; 959A
        cpy #$0C                                ; 959B
        bne L9595                               ; 959D
        pla                                     ; 959F
        clc                                     ; 95A0
        rts                                     ; 95A1
L95A2:
        lda #$00                                ; 95A2
        sta $041B,y                             ; 95A4
        pla                                     ; 95A7
        sec                                     ; 95A8
        rts                                     ; 95A9
L95AA:
        ldx #$00                                ; 95AA
L95AC:
        jsr L95B7                               ; 95AC
        inx                                     ; 95AF
        cpx #$0E                                ; 95B0
        beq L95CF                               ; 95B2
        jmp L95AC                               ; 95B4
L95B7:
        lda #$02                                ; 95B7
        sta $F4                                 ; 95B9
        lda #$08                                ; 95BB
        sta $F1                                 ; 95BD
        lda $0491,x                             ; 95BF
        and #$3E                                ; 95C2
        beq L95CF                               ; 95C4
        tay                                     ; 95C6
        lda L9C19,y                             ; 95C7
        pha                                     ; 95CA
        lda L9C18,y                             ; 95CB
        pha                                     ; 95CE
L95CF:
        rts                                     ; 95CF
        .byte $60                               ; 95D0 `
L95D1:
        stx $E0                                 ; 95D1
        jsr L81A8                               ; 95D3
        ldx $E0                                 ; 95D6
        rts                                     ; 95D8
        .byte $85,$00,$0A,$85,$01,$BD,$91,$04   ; 95D9 ........
        .byte $29,$01,$85,$02,$20,$92,$95,$90   ; 95E1 )... ...
        .byte $78,$BD,$4B,$04,$99,$D3,$03,$BD   ; 95E9 x.K.....
        .byte $59,$04,$18,$69,$04,$99,$EB,$03   ; 95F1 Y..i....
        .byte $A5,$00,$09,$80,$99,$3F,$04,$86   ; 95F9 .....?..
        .byte $03,$A5,$01,$05,$02,$AA,$BD,$E8   ; 9601 ........
        .byte $96,$99,$03,$04,$A6,$00,$BD,$02   ; 9609 ........
        .byte $97,$99,$33,$04,$A6,$03,$A9,$00   ; 9611 ..3.....
        .byte $99,$1B,$04,$99,$0F,$04,$99,$27   ; 9619 .......'
        .byte $04,$99,$DF,$03,$99,$F7,$03,$A5   ; 9621 ........
        .byte $00,$C9,$04,$D0,$0F,$A9,$FC,$99   ; 9629 ........
        .byte $1B,$04,$BD,$59,$04,$30,$05,$A9   ; 9631 ...Y.0..
        .byte $04,$99,$1B,$04,$A5,$00,$C9,$09   ; 9639 ........
        .byte $D0,$10,$A9,$FC,$99,$1B,$04,$A5   ; 9641 ........
        .byte $13,$29,$40,$F0,$05,$A9,$04,$99   ; 9649 .)@.....
        .byte $1B,$04,$B9,$D3,$03,$18,$79,$03   ; 9651 ......y.
        .byte $04,$18,$79,$03,$04,$99,$D3,$03   ; 9659 ..y.....
        .byte $38,$60,$85,$05,$84,$04,$C0,$FF   ; 9661 8`......
        .byte $D0,$06,$A5,$13,$29,$01,$85,$04   ; 9669 ....)...
        .byte $A4,$04,$B9,$44,$00,$D0,$05,$98   ; 9671 ...D....
        .byte $49,$01,$85,$04,$20,$92,$95,$90   ; 9679 I... ...
        .byte $65,$BD,$4B,$04,$99,$D3,$03,$85   ; 9681 e.K.....
        .byte $00,$BD,$59,$04,$18,$69,$04,$99   ; 9689 ..Y..i..
        .byte $EB,$03,$85,$01,$A5,$05,$09,$80   ; 9691 ........
        .byte $99,$3F,$04,$86,$06,$A5,$05,$AA   ; 9699 .?......
        .byte $BD,$E8,$96,$0A,$0A,$85,$07,$A6   ; 96A1 ........
        .byte $05,$BD,$02,$97,$0A,$99,$33,$04   ; 96A9 ......3.
        .byte $A6,$04,$B5,$48,$85,$02,$B5,$4C   ; 96B1 ...H...L
        .byte $18,$69,$04,$85,$03,$A6,$06,$84   ; 96B9 .i......
        .byte $06,$20,$A1,$D1,$A8,$A5,$07,$20   ; 96C1 . ..... 
        .byte $CF,$81,$A4,$06,$A9,$00,$99,$F7   ; 96C9 ........
        .byte $03,$A5,$00,$99,$0F,$04,$A5,$01   ; 96D1 ........
        .byte $99,$03,$04,$A5,$02,$99,$27,$04   ; 96D9 ......'.
        .byte $A5,$03,$99,$1B,$04,$38,$60,$00   ; 96E1 .....8`.
        .byte $00,$02,$FE,$03,$FD,$02,$FE,$00   ; 96E9 ........
        .byte $00,$05,$FB,$03,$FD,$02,$FE,$02   ; 96F1 ........
        .byte $FE,$04,$FC,$05,$FB,$03,$FD,$03   ; 96F9 ........
        .byte $FD,$00,$28,$14,$14,$14,$14,$14   ; 9701 ..(.....
        .byte $14,$14,$14,$14,$14,$0A,$BD,$91   ; 9709 ........
        .byte $04,$C9,$40,$90,$10,$38,$E9,$40   ; 9711 ..@..8.@
        .byte $9D,$91,$04,$84,$E0,$A9,$0D,$20   ; 9719 ....... 
        .byte $7A,$D3,$A4,$E0,$60,$A9,$02,$9D   ; 9721 z...`...
        .byte $9F,$04,$A9,$C8,$9D,$BB,$04,$84   ; 9729 ........
        .byte $E0,$A9,$05,$20,$7A,$D3,$A4,$E0   ; 9731 ... z...
        .byte $60,$A9,$00,$9D,$91,$04,$9D,$9F   ; 9739 `.......
        .byte $04,$CE,$DC,$04,$A5,$F1,$C9,$10   ; 9741 ........
        .byte $D0,$1E,$A9,$0A,$9D,$91,$04,$A9   ; 9749 ........
        .byte $03,$9D,$AD,$04,$A9,$0C,$9D,$BB   ; 9751 ........
        .byte $04,$A9,$FD,$99,$54,$00,$A9,$00   ; 9759 ....T...
        .byte $99,$58,$00,$A9,$0A,$99,$63,$03   ; 9761 .X....c.
        .byte $AD,$CA,$04,$D0,$08,$AD,$CB,$04   ; 9769 ........
        .byte $F0,$03,$CE,$CB,$04,$60,$A0,$00   ; 9771 .....`..
        .byte $B9,$48,$00,$85,$E9,$B9,$4C,$00   ; 9779 .H....L.
        .byte $85,$E7,$BD,$4B,$04,$85,$EA,$BD   ; 9781 ...K....
        .byte $59,$04,$85,$E8,$A5,$F1,$85,$EC   ; 9789 Y.......
        .byte $A9,$08,$85,$EB,$0A,$85,$ED,$85   ; 9791 ........
        .byte $EE,$20,$C9,$8C,$90,$09,$BD,$9F   ; 9799 . ......
        .byte $04,$C9,$02,$F0,$08,$D0,$29,$C8   ; 97A1 ......).
        .byte $C0,$04,$D0,$CC,$60,$86,$E2,$84   ; 97A9 ....`...
        .byte $E3,$BD,$91,$04,$29,$3E,$4A,$A8   ; 97B1 ....)>J.
        .byte $B9,$4E,$9C,$A6,$E3,$20,$2A,$8D   ; 97B9 .N... *.
        .byte $A9,$07,$20,$7A,$D3,$A6,$E2,$A4   ; 97C1 .. z....
        .byte $E3,$18,$20,$3A,$97,$4C,$A8,$97   ; 97C9 .. :.L..
        .byte $A5,$F1,$C9,$08,$F0,$0F,$BD,$91   ; 97D1 ........
        .byte $04,$29,$3E,$4A,$C9,$09,$F0,$11   ; 97D9 .)>J....
        .byte $20,$F9,$8C,$D0,$C2,$A5,$DC,$C9   ; 97E1  .......
        .byte $01,$90,$BC,$20,$F9,$8C,$4C,$A8   ; 97E9 ... ..L.
        .byte $97,$B9,$54,$00,$30,$F5,$C9,$01   ; 97F1 ..T.0...
        .byte $B0,$B3,$B9,$58,$00,$D0,$AE,$F0   ; 97F9 ...X....
        .byte $EA,$BD,$59,$04,$18,$69,$08,$4A   ; 9801 ..Y..i.J
        .byte $4A,$29,$38,$85,$E0,$BD,$4B,$04   ; 9809 J)8...K.
        .byte $18,$69,$04,$4A,$4A,$4A,$4A,$4A   ; 9811 .i.JJJJJ
        .byte $05,$E0,$A8,$B9,$C0,$06,$F0,$36   ; 9819 .......6
        .byte $A0,$00,$B9,$3F,$04,$29,$C0,$C9   ; 9821 ...?.)..
        .byte $C0,$D0,$26,$B9,$D3,$03,$85,$E9   ; 9829 ..&.....
        .byte $B9,$EB,$03,$85,$E7,$BD,$4B,$04   ; 9831 ......K.
        .byte $85,$EA,$BD,$59,$04,$85,$E8,$A5   ; 9839 ...Y....
        .byte $F1,$85,$EC,$A9,$08,$85,$EB,$85   ; 9841 ........
        .byte $ED,$0A,$85,$EE,$20,$C9,$8C,$B0   ; 9849 .... ...
        .byte $07,$C8,$C0,$0C,$D0,$CC,$18,$60   ; 9851 .......`
        .byte $A9,$00,$99,$3F,$04,$38,$60,$A4   ; 9859 ...?.8`.
        .byte $DC,$C0,$01,$69,$00,$85,$00,$A5   ; 9861 ...i....
        .byte $F1,$85,$01,$C6,$01,$BD,$91,$04   ; 9869 ........
        .byte $29,$01,$F0,$0D,$A5,$00,$49,$FF   ; 9871 ).....I.
        .byte $18,$69,$01,$85,$00,$A9,$00,$85   ; 9879 .i......
        .byte $01,$BD,$4B,$04,$18,$65,$01,$18   ; 9881 ..K..e..
        .byte $65,$00,$4A,$4A,$4A,$4A,$85,$01   ; 9889 e.JJJJ..
        .byte $BD,$59,$04,$18,$69,$08,$29,$F0   ; 9891 .Y..i.).
        .byte $05,$01,$A8,$B9,$00,$07,$20,$69   ; 9899 ...... i
        .byte $90,$F0,$02,$38,$60,$BD,$4B,$04   ; 98A1 ...8`.K.
        .byte $18,$65,$00,$9D,$4B,$04,$18,$60   ; 98A9 .e..K..`
        .byte $90,$3E,$BD,$4B,$04,$4A,$4A,$4A   ; 98B1 .>.K.JJJ
        .byte $4A,$85,$00,$BD,$59,$04,$18,$69   ; 98B9 J...Y..i
        .byte $0F,$29,$F0,$05,$00,$A8,$B9,$00   ; 98C1 .)......
        .byte $07,$C9,$03,$D0,$1B,$A9,$FE,$9D   ; 98C9 ........
        .byte $75,$04,$A9,$00,$9D,$83,$04,$BD   ; 98D1 u.......
        .byte $91,$04,$29,$01,$A8,$BD,$4B,$04   ; 98D9 ..)...K.
        .byte $18,$79,$F2,$98,$9D,$4B,$04,$60   ; 98E1 .y...K.`
        .byte $BD,$91,$04,$49,$01,$9D,$91,$04   ; 98E9 ...I....
        .byte $60,$04,$FA,$BD,$67,$04,$18,$7D   ; 98F1 `...g..}
        .byte $83,$04,$90,$03,$FE,$59,$04,$9D   ; 98F9 .....Y..
        .byte $67,$04,$BD,$75,$04,$30,$04,$C9   ; 9901 g..u.0..
        .byte $08,$B0,$0E,$BD,$83,$04,$18,$69   ; 9909 .......i
        .byte $20,$90,$03,$FE,$75,$04,$9D,$83   ; 9911  ...u...
        .byte $04,$BD,$59,$04,$18,$7D,$75,$04   ; 9919 ..Y..}u.
        .byte $9D,$59,$04,$60,$A9,$00,$9D,$91   ; 9921 .Y.`....
        .byte $04,$9D,$9F,$04,$CE,$DC,$04,$60   ; 9929 .......`
        .byte $BD,$59,$04,$85,$00,$20,$F4,$98   ; 9931 .Y... ..
        .byte $BD,$75,$04,$30,$1E,$BD,$59,$04   ; 9939 .u.0..Y.
        .byte $C5,$00,$B0,$17,$AD,$CA,$04,$D0   ; 9941 ........
        .byte $DB,$86,$00,$20,$A8,$81,$A6,$00   ; 9949 ... ....
        .byte $9D,$4B,$04,$29,$01,$5D,$91,$04   ; 9951 .K.).]..
        .byte $9D,$91,$04,$60,$BD,$59,$04,$85   ; 9959 ...`.Y..
        .byte $00,$20,$F4,$98,$BD,$75,$04,$30   ; 9961 . ...u.0
        .byte $1E,$BD,$59,$04,$C5,$00,$B0,$17   ; 9969 ..Y.....
        .byte $AD,$CA,$04,$D0,$AF,$86,$00,$20   ; 9971 ....... 
        .byte $A8,$81,$A6,$00,$9D,$4B,$04,$29   ; 9979 .....K.)
        .byte $01,$5D,$91,$04,$9D,$91,$04,$BD   ; 9981 .]......
        .byte $4B,$04,$18,$69,$04,$BC,$75,$04   ; 9989 K..i..u.
        .byte $30,$2A,$4A,$4A,$4A,$4A,$85,$00   ; 9991 0*JJJJ..
        .byte $BD,$59,$04,$18,$69,$10,$29,$F0   ; 9999 .Y..i.).
        .byte $05,$00,$A8,$B9,$00,$07,$C9,$15   ; 99A1 ........
        .byte $90,$12,$BD,$59,$04,$29,$F0,$9D   ; 99A9 ...Y.)..
        .byte $59,$04,$A9,$00,$9D,$75,$04,$9D   ; 99B1 Y....u..
        .byte $83,$04,$38,$60,$18,$60,$BD,$59   ; 99B9 ..8`.`.Y
        .byte $04,$85,$00,$20,$F4,$98,$BD,$75   ; 99C1 ... ...u
        .byte $04,$30,$21,$BD,$59,$04,$C5,$00   ; 99C9 .0!.Y...
        .byte $B0,$1A,$AD,$CA,$04,$F0,$03,$4C   ; 99D1 .......L
        .byte $25,$99,$86,$00,$20,$A8,$81,$A6   ; 99D9 %... ...
        .byte $00,$9D,$4B,$04,$29,$01,$5D,$91   ; 99E1 ..K.).].
        .byte $04,$9D,$91,$04,$A9,$00,$85,$01   ; 99E9 ........
        .byte $BD,$4B,$04,$48,$20,$8E,$99,$26   ; 99F1 .K.H ..&
        .byte $01,$68,$18,$69,$0F,$20,$8E,$99   ; 99F9 .h.i. ..
        .byte $26,$01,$A5,$01,$C9,$01,$60       ; 9A01 &.....`
L9A08:
        lda $13                                 ; 9A08
        and #$1F                                ; 9A0A
        bne L9A87                               ; 9A0C
        lda $04DC                               ; 9A0E
        cmp $04DD                               ; 9A11
        bcs L9A87                               ; 9A14
        jsr L81A8                               ; 9A16
        lsr                                     ; 9A19
        lsr                                     ; 9A1A
        and #$0F                                ; 9A1B
        tax                                     ; 9A1D
        lda $04CC,x                             ; 9A1E
        sta $00                                 ; 9A21
        jsr L9A88                               ; 9A23
        bcc L9A87                               ; 9A26
        lda $00                                 ; 9A28
        pha                                     ; 9A2A
        and #$1F                                ; 9A2B
        asl                                     ; 9A2D
        sta $0491,x                             ; 9A2E
        cmp #$18                                ; 9A31
        bne L9A3A                               ; 9A33
        ora #$40                                ; 9A35
        sta $0491,x                             ; 9A37
L9A3A:
        cmp #$30                                ; 9A3A
        bne L9A43                               ; 9A3C
        ora #$40                                ; 9A3E
        sta $0491,x                             ; 9A40
L9A43:
        cmp #$1A                                ; 9A43
        bne L9A4C                               ; 9A45
        ora #$80                                ; 9A47
        sta $0491,x                             ; 9A49
L9A4C:
        cmp #$20                                ; 9A4C
        bne L9A55                               ; 9A4E
        ora #$40                                ; 9A50
        sta $0491,x                             ; 9A52
L9A55:
        cmp #$32                                ; 9A55
        bne L9A5E                               ; 9A57
        ora #$C0                                ; 9A59
        sta $0491,x                             ; 9A5B
L9A5E:
        jsr L95D1                               ; 9A5E
        lsr                                     ; 9A61
        bcc L9A67                               ; 9A62
        inc $0491,x                             ; 9A64
L9A67:
        pla                                     ; 9A67
        and #$E0                                ; 9A68
        sta $04AD,x                             ; 9A6A
        lda #$00                                ; 9A6D
        sta $0459,x                             ; 9A6F
        sta $0467,x                             ; 9A72
        sta $0475,x                             ; 9A75
        sta $0483,x                             ; 9A78
        sta $04BB,x                             ; 9A7B
        jsr L95D1                               ; 9A7E
        sta $044B,x                             ; 9A81
        inc $04DC                               ; 9A84
L9A87:
        rts                                     ; 9A87
L9A88:
        pha                                     ; 9A88
        ldx #$00                                ; 9A89
L9A8B:
        lda $0491,x                             ; 9A8B
        beq L9A98                               ; 9A8E
        inx                                     ; 9A90
        cpx #$0E                                ; 9A91
        bne L9A8B                               ; 9A93
        pla                                     ; 9A95
        clc                                     ; 9A96
        rts                                     ; 9A97
L9A98:
        pla                                     ; 9A98
        sec                                     ; 9A99
        rts                                     ; 9A9A
        .byte $BD,$9F,$04,$C9,$02,$D0,$36,$A4   ; 9A9B ......6.
        .byte $DF,$BD,$59,$04,$38,$E9,$01,$99   ; 9AA3 ..Y.8...
        .byte $00,$02,$18,$69,$08,$99,$04,$02   ; 9AAB ...i....
        .byte $A9,$01,$99,$02,$02,$99,$06,$02   ; 9AB3 ........
        .byte $A9,$41,$99,$01,$02,$A9,$51,$99   ; 9ABB .A....Q.
        .byte $05,$02,$BD,$4B,$04,$38,$E5,$41   ; 9AC3 ...K.8.A
        .byte $99,$03,$02,$99,$07,$02,$98,$18   ; 9ACB ........
        .byte $69,$08,$85,$DF,$60,$A0,$01,$BD   ; 9AD3 i...`...
        .byte $91,$04,$29,$01,$F0,$02,$A0,$41   ; 9ADB ..)....A
        .byte $84,$00,$A4,$DF,$BD,$59,$04,$38   ; 9AE3 .....Y.8
        .byte $E9,$01,$99,$00,$02,$18,$69,$06   ; 9AEB ......i.
        .byte $99,$08,$02,$18,$69,$02,$99,$04   ; 9AF3 ....i...
        .byte $02,$A5,$00,$99,$02,$02,$99,$06   ; 9AFB ........
        .byte $02,$99,$0A,$02,$A5,$F3,$C9,$09   ; 9B03 ........
        .byte $D0,$0D,$A5,$13,$29,$40,$F0,$07   ; 9B0B ....)@..
        .byte $A5,$00,$09,$80,$99,$0A,$02,$A5   ; 9B13 ........
        .byte $F4,$99,$01,$02,$84,$01,$A5,$F2   ; 9B1B ........
        .byte $0A,$0A,$85,$00,$A8,$A5,$13,$4A   ; 9B23 .......J
        .byte $4A,$29,$03,$18,$65,$00,$A8,$B9   ; 9B2B J)..e...
        .byte $98,$8B,$A4,$01,$99,$05,$02,$A5   ; 9B33 ........
        .byte $F3,$09,$20,$99,$09,$02,$BD,$4B   ; 9B3B .. ....K
        .byte $04,$38,$E5,$41,$99,$03,$02,$99   ; 9B43 .8.A....
        .byte $07,$02,$84,$01,$BD,$91,$04,$29   ; 9B4B .......)
        .byte $01,$A8,$B9,$B5,$8C,$A4,$01,$18   ; 9B53 ........
        .byte $7D,$4B,$04,$38,$E5,$41,$99,$0B   ; 9B5B }K.8.A..
        .byte $02,$98,$18,$69,$10,$A8,$84,$DF   ; 9B63 ...i....
        .byte $60,$84,$00,$C8,$84,$01,$C8,$84   ; 9B6B `.......
        .byte $02,$C8,$84,$03,$85,$05,$A0,$01   ; 9B73 ........
        .byte $A5,$05,$29,$02,$D0,$25,$46,$05   ; 9B7B ..)..%F.
        .byte $90,$08,$A5,$13,$29,$04,$F0,$09   ; 9B83 ....)...
        .byte $D0,$19,$BD,$91,$04,$29,$01,$F0   ; 9B8B .....)..
        .byte $12,$A4,$00,$A5,$02,$84,$02,$85   ; 9B93 ........
        .byte $00,$A4,$01,$A5,$03,$84,$03,$85   ; 9B9B ........
        .byte $01,$A0,$41,$84,$04,$BD,$9F,$04   ; 9BA3 ..A.....
        .byte $C9,$02,$D0,$16,$A4,$00,$A5,$01   ; 9BAB ........
        .byte $84,$01,$85,$00,$A4,$02,$A5,$03   ; 9BB3 ........
        .byte $84,$03,$85,$02,$A5,$04,$09,$80   ; 9BBB ........
        .byte $85,$04,$A4,$DF,$BD,$59,$04,$99   ; 9BC3 .....Y..
        .byte $00,$02,$99,$08,$02,$18,$69,$08   ; 9BCB ......i.
        .byte $99,$04,$02,$99,$0C,$02,$A5,$04   ; 9BD3 ........
        .byte $99,$02,$02,$99,$06,$02,$99,$0A   ; 9BDB ........
        .byte $02,$99,$0E,$02,$A5,$00,$99,$01   ; 9BE3 ........
        .byte $02,$A5,$01,$99,$05,$02,$A5,$02   ; 9BEB ........
        .byte $99,$09,$02,$A5,$03,$99,$0D,$02   ; 9BF3 ........
        .byte $BD,$4B,$04,$38,$E5,$41,$99,$03   ; 9BFB .K.8.A..
        .byte $02,$99,$07,$02,$18,$69,$08,$99   ; 9C03 .....i..
        .byte $0B,$02,$99,$0F,$02,$98,$18,$69   ; 9C0B .......i
        .byte $10,$A8,$84,$DF,$60               ; 9C13 ....`
L9C18:
        .byte $CF                               ; 9C18 .
L9C19:
        .byte $95,$42,$9F,$9D,$A3,$FC,$A3,$3D   ; 9C19 .B.....=
        .byte $A4,$97,$A1,$D6,$A0,$35,$A1,$8E   ; 9C21 .....5..
        .byte $A4,$F3,$A4,$6B,$A6,$DD,$A6,$5B   ; 9C29 ...k...[
        .byte $A7,$20,$A8,$8D,$A8,$8D,$A8,$8D   ; 9C31 . ......
        .byte $A8,$78,$9C,$DF,$A5,$0E,$A6,$11   ; 9C39 .x......
        .byte $A0,$50,$A0,$2E,$A5,$2E,$A5,$A8   ; 9C41 .P......
        .byte $A7,$7F,$9F,$BA,$9F,$00,$03,$05   ; 9C49 ........
        .byte $07,$0A,$00,$0F,$0C,$0A,$0A,$14   ; 9C51 ........
        .byte $14,$0E,$0D,$12,$18,$14,$28,$0A   ; 9C59 ......(.
        .byte $0F,$0A,$1B,$14,$14,$14,$14,$07   ; 9C61 ........
        .byte $BD,$BB,$04,$F0,$0A,$DE,$BB,$04   ; 9C69 ........
        .byte $D0,$05,$A9,$00,$9D,$9F,$04,$60   ; 9C71 .......`
        .byte $BD,$9F,$04,$F0,$03,$4C,$20,$9D   ; 9C79 .....L .
        .byte $A9,$04,$20,$60,$98,$A5,$13,$29   ; 9C81 .. `...)
        .byte $03,$D0,$28,$AD,$DD,$04,$C9,$01   ; 9C89 ..(.....
        .byte $F0,$09,$20,$D1,$95,$29,$07,$F0   ; 9C91 .. ..)..
        .byte $09,$D0,$18,$20,$D1,$95,$29,$03   ; 9C99 ... ..).
        .byte $D0,$11,$BD,$4B,$04,$48,$18,$69   ; 9CA1 ...K.H.i
        .byte $0C,$9D,$4B,$04,$20,$9C,$A0,$68   ; 9CA9 ..K. ..h
        .byte $9D,$4B,$04,$BD,$91,$04,$29,$01   ; 9CB1 .K....).
        .byte $A8,$F0,$09,$BD,$4B,$04,$C9,$0A   ; 9CB9 ....K...
        .byte $B0,$5D,$90,$07,$BD,$4B,$04,$C9   ; 9CC1 .]...K..
        .byte $DE,$90,$54,$B9,$93,$9E,$9D,$4B   ; 9CC9 ..T....K
        .byte $04,$BD,$91,$04,$49,$01,$9D,$91   ; 9CD1 ....I...
        .byte $04,$A9,$3C,$9D,$BB,$04,$A9,$01   ; 9CD9 ..<.....
        .byte $9D,$9F,$04,$84,$E1,$20,$D1,$95   ; 9CE1 ..... ..
        .byte $4A,$18,$69,$50,$9D,$59,$04,$86   ; 9CE9 J.iP.Y..
        .byte $E0,$20,$88,$9A,$90,$29,$A4,$E1   ; 9CF1 . ...)..
        .byte $B9,$95,$9E,$9D,$4B,$04,$A4,$E0   ; 9CF9 ....K...
        .byte $B9,$91,$04,$29,$01,$09,$0A,$9D   ; 9D01 ...)....
        .byte $91,$04,$A9,$02,$9D,$AD,$04,$B9   ; 9D09 ........
        .byte $59,$04,$18,$69,$04,$9D,$59,$04   ; 9D11 Y..i..Y.
        .byte $A9,$14,$9D,$BB,$04,$98,$AA,$A0   ; 9D19 ........
        .byte $00,$B9,$91,$04,$10,$6A,$29,$3E   ; 9D21 .....j)>
        .byte $C9,$0A,$D0,$64,$B9,$AD,$04,$C9   ; 9D29 ...d....
        .byte $02,$D0,$5D,$B9,$4B,$04,$85,$E9   ; 9D31 ..].K...
        .byte $B9,$59,$04,$85,$E7,$BD,$4B,$04   ; 9D39 .Y....K.
        .byte $85,$EA,$BD,$59,$04,$85,$E8,$A9   ; 9D41 ...Y....
        .byte $10,$85,$EB,$85,$ED,$A9,$18,$85   ; 9D49 ........
        .byte $EC,$85,$EE,$20,$C9,$8C,$90,$38   ; 9D51 ... ...8
        .byte $A9,$00,$99,$91,$04,$A9,$0A,$9D   ; 9D59 ........
        .byte $BB,$04,$A9,$01,$9D,$9F,$04,$FE   ; 9D61 ........
        .byte $AD,$04,$BD,$AD,$04,$C9,$04,$90   ; 9D69 ........
        .byte $16,$84,$E0,$A9,$0B,$20,$7A,$D3   ; 9D71 ..... z.
        .byte $A9,$0C,$20,$7A,$D3,$A9,$FE,$9D   ; 9D79 .. z....
        .byte $75,$04,$A4,$E0,$4C,$91,$9D,$84   ; 9D81 u...L...
        .byte $E0,$A9,$0D,$20,$7A,$D3,$A4,$E0   ; 9D89 ... z...
        .byte $C8,$C0,$0E,$D0,$8C,$BD,$AD,$04   ; 9D91 ........
        .byte $C9,$04,$90,$17,$20,$31,$99,$A9   ; 9D99 .... 1..
        .byte $01,$9D,$9F,$04,$A9,$0A,$9D,$BB   ; 9DA1 ........
        .byte $04,$BD,$59,$04,$C9,$F0,$90,$03   ; 9DA9 ..Y.....
        .byte $4C,$3A,$97,$BD,$91,$04,$D0,$03   ; 9DB1 L:......
        .byte $4C,$80,$9E,$20,$69,$9C,$A4,$DF   ; 9DB9 L.. i...
        .byte $BD,$59,$04,$99,$00,$02,$99,$04   ; 9DC1 .Y......
        .byte $02,$99,$08,$02,$18,$69,$08,$99   ; 9DC9 .....i..
        .byte $0C,$02,$99,$10,$02,$99,$14,$02   ; 9DD1 ........
        .byte $18,$69,$08,$99,$18,$02,$99,$1C   ; 9DD9 .i......
        .byte $02,$99,$20,$02,$A9,$01,$85,$01   ; 9DE1 .. .....
        .byte $BD,$91,$04,$29,$01,$85,$00,$48   ; 9DE9 ...)...H
        .byte $86,$E0,$A2,$00,$68,$F0,$06,$A2   ; 9DF1 ....h...
        .byte $09,$A9,$41,$85,$01,$A5,$01,$99   ; 9DF9 ..A.....
        .byte $02,$02,$99,$06,$02,$99,$0A,$02   ; 9E01 ........
        .byte $99,$0E,$02,$99,$12,$02,$99,$16   ; 9E09 ........
        .byte $02,$99,$1A,$02,$99,$1E,$02,$99   ; 9E11 ........
        .byte $22,$02,$BD,$81,$9E,$99,$01,$02   ; 9E19 ".......
        .byte $BD,$82,$9E,$99,$05,$02,$BD,$83   ; 9E21 ........
        .byte $9E,$99,$09,$02,$BD,$84,$9E,$99   ; 9E29 ........
        .byte $0D,$02,$BD,$85,$9E,$99,$11,$02   ; 9E31 ........
        .byte $BD,$86,$9E,$99,$15,$02,$BD,$87   ; 9E39 ........
        .byte $9E,$99,$19,$02,$BD,$88,$9E,$99   ; 9E41 ........
        .byte $1D,$02,$BD,$89,$9E,$99,$21,$02   ; 9E49 ......!.
        .byte $A6,$E0,$BD,$4B,$04,$38,$E5,$41   ; 9E51 ...K.8.A
        .byte $99,$03,$02,$99,$0F,$02,$99,$1B   ; 9E59 ........
        .byte $02,$18,$69,$08,$99,$07,$02,$99   ; 9E61 ..i.....
        .byte $13,$02,$99,$1F,$02,$18,$69,$08   ; 9E69 ......i.
        .byte $99,$0B,$02,$99,$17,$02,$99,$23   ; 9E71 .......#
        .byte $02,$98,$18,$69,$24,$85,$DF,$60   ; 9E79 ...i$..`
        .byte $70,$71,$72,$80,$81,$82,$90,$91   ; 9E81 pqr.....
        .byte $92,$72,$71,$70,$82,$81,$80,$92   ; 9E89 .rqp....
        .byte $91,$90,$E8,$00,$D8,$18,$06,$F1   ; 9E91 ........
        .byte $BD,$BB,$04,$D0,$10,$BD,$91,$04   ; 9E99 ........
        .byte $29,$01,$A8,$BD,$4B,$04,$18,$79   ; 9EA1 )...K..y
        .byte $DC,$9E,$9D,$4B,$04,$20,$77,$97   ; 9EA9 ...K. w.
        .byte $20,$02,$98,$90,$0A,$BD,$91,$04   ; 9EB1  .......
        .byte $30,$05,$49,$81,$9D,$91,$04,$BD   ; 9EB9 0.I.....
        .byte $4B,$04,$C9,$10,$90,$0F,$C9,$F0   ; 9EC1 K.......
        .byte $B0,$0B,$20,$69,$9C,$A0,$64,$A9   ; 9EC9 .. i..d.
        .byte $02,$20,$6C,$9B,$60,$A9,$00,$9D   ; 9ED1 . l.`...
        .byte $91,$04,$60,$04,$FC,$A4,$DF,$BD   ; 9ED9 ..`.....
        .byte $59,$04,$99,$00,$02,$99,$04,$02   ; 9EE1 Y.......
        .byte $18,$69,$08,$99,$08,$02,$99,$0C   ; 9EE9 .i......
        .byte $02,$A9,$01,$99,$02,$02,$A9,$41   ; 9EF1 .......A
        .byte $99,$06,$02,$A9,$81,$99,$0A,$02   ; 9EF9 ........
        .byte $A9,$C1,$99,$0E,$02,$A9,$0C,$38   ; 9F01 .......8
        .byte $FD,$BB,$04,$4A,$4A,$18,$69,$61   ; 9F09 ...JJ.ia
        .byte $99,$01,$02,$99,$05,$02,$99,$09   ; 9F11 ........
        .byte $02,$99,$0D,$02,$BD,$4B,$04,$38   ; 9F19 .....K.8
        .byte $E5,$41,$99,$03,$02,$99,$0B,$02   ; 9F21 .A......
        .byte $18,$69,$08,$99,$07,$02,$99,$0F   ; 9F29 .i......
        .byte $02,$98,$18,$69,$10,$85,$DF,$DE   ; 9F31 ...i....
        .byte $BB,$04,$D0,$05,$A9,$00,$9D,$91   ; 9F39 ........
        .byte $04,$60,$A9,$01,$85,$F2,$A9,$01   ; 9F41 .`......
        .byte $85,$F3,$20,$7E,$A8,$20,$5D,$99   ; 9F49 .. ~. ].
        .byte $BD,$91,$04,$F0,$29,$90,$19,$BD   ; 9F51 ....)...
        .byte $9F,$04,$D0,$14,$A9,$02,$20,$60   ; 9F59 ...... `
        .byte $98,$20,$B1,$98,$20,$D1,$95,$29   ; 9F61 . .. ..)
        .byte $0F,$D0,$05,$A9,$01,$20,$D9,$95   ; 9F69 ..... ..
        .byte $20,$77,$97,$BD,$91,$04,$F0,$06   ; 9F71  w......
        .byte $20,$69,$9C,$20,$9B,$9A,$60,$06   ; 9F79  i. ..`.
        .byte $F1,$20,$7E,$A8,$20,$BF,$99,$90   ; 9F81 . ~. ...
        .byte $1C,$BD,$91,$04,$F0,$2B,$A9,$01   ; 9F89 .....+..
        .byte $20,$60,$98,$20,$B1,$98,$BD,$9F   ; 9F91  `. ....
        .byte $04,$D0,$0A,$20,$D1,$95,$29,$0F   ; 9F99 ... ..).
        .byte $D0,$03,$20,$27,$A7,$20,$77,$97   ; 9FA1 .. '. w.
        .byte $BD,$91,$04,$F0,$0C,$20,$69,$9C   ; 9FA9 ..... i.
        .byte $A5,$13,$A0,$B4,$A9,$02,$20,$6C   ; 9FB1 ...... l
        .byte $9B,$60,$A9,$01,$85,$F2,$A9,$0A   ; 9FB9 .`......
        .byte $85,$F3,$20,$7E,$A8,$20,$5D,$99   ; 9FC1 .. ~. ].
        .byte $BD,$91,$04,$F0,$43,$90,$26,$BD   ; 9FC9 ....C.&.
        .byte $9F,$04,$D0,$21,$A9,$03,$20,$60   ; 9FD1 ...!.. `
        .byte $98,$20,$B1,$98,$20,$D1,$95,$29   ; 9FD9 . .. ..)
        .byte $0F,$D0,$12,$BD,$91,$04,$48,$29   ; 9FE1 ......H)
        .byte $FE,$9D,$91,$04,$A9,$0A,$20,$D9   ; 9FE9 ...... .
        .byte $95,$68,$9D,$91,$04,$20,$77,$97   ; 9FF1 .h... w.
        .byte $BD,$91,$04,$F0,$13,$20,$69,$9C   ; 9FF9 ..... i.
        .byte $BD,$91,$04,$48,$29,$FE,$9D,$91   ; A001 ...H)...
        .byte $04,$20,$9B,$9A,$68,$9D,$91,$04   ; A009 . ..h...
        .byte $60,$A9,$01,$85,$F2,$A9,$06,$85   ; A011 `.......
        .byte $F3,$20,$7E,$A8,$20,$5D,$99,$BD   ; A019 . ~. ]..
        .byte $91,$04,$F0,$2B,$90,$1B,$BD,$9F   ; A021 ...+....
        .byte $04,$D0,$16,$A9,$02,$20,$60,$98   ; A029 ..... `.
        .byte $20,$B1,$98,$20,$D1,$95,$29,$0F   ; A031  .. ..).
        .byte $D0,$07,$A9,$06,$A0,$FF,$20,$63   ; A039 ...... c
        .byte $96,$20,$77,$97,$BD,$91,$04,$F0   ; A041 . w.....
        .byte $06,$20,$69,$9C,$20,$9B,$9A,$60   ; A049 . i. ..`
        .byte $A9,$01,$85,$F2,$A9,$0C,$85,$F3   ; A051 ........
        .byte $20,$7E,$A8,$20,$5D,$99,$BD,$91   ; A059  ~. ]...
        .byte $04,$F0,$37,$90,$27,$BD,$9F,$04   ; A061 ..7.'...
        .byte $D0,$22,$A9,$02,$20,$60,$98,$20   ; A069 .".. `. 
        .byte $B1,$98,$20,$D1,$95,$29,$0F,$D0   ; A071 .. ..)..
        .byte $13,$A5,$13,$29,$40,$F0,$02,$A9   ; A079 ...)@...
        .byte $01,$A8,$B9,$44,$00,$F0,$05,$A9   ; A081 ...D....
        .byte $0C,$20,$63,$96,$20,$77,$97,$BD   ; A089 . c. w..
        .byte $91,$04,$F0,$06,$20,$69,$9C,$20   ; A091 .... i. 
        .byte $9B,$9A,$60                       ; A099 ..`
LA09C:
        txa                                     ; A09C
        tay                                     ; A09D
        lda #$FF                                ; A09E
        sta $04C9                               ; A0A0
        jsr L9A88                               ; A0A3
        php                                     ; A0A6
        bcc LA0D3                               ; A0A7
        lda #$0A                                ; A0A9
        sta $0491,x                             ; A0AB
        lda $0459,y                             ; A0AE
        sta $0459,x                             ; A0B1
        lda #$FF                                ; A0B4
        sta $0475,x                             ; A0B6
        lda #$00                                ; A0B9
        sta $0467,x                             ; A0BB
        sta $0483,x                             ; A0BE
        sta $04BB,x                             ; A0C1
        sta $04AD,x                             ; A0C4
        lda $044B,y                             ; A0C7
        sta $044B,x                             ; A0CA
        stx $04C9                               ; A0CD
        inc $04DC                               ; A0D0
LA0D3:
        tya                                     ; A0D3
        tax                                     ; A0D4
        plp                                     ; A0D5
        rts                                     ; A0D6
        .byte $A9,$06,$85,$F2,$0A,$85,$F3,$A9   ; A0D7 ........
        .byte $0E,$85,$F4,$20,$5D,$99,$BD,$91   ; A0DF ... ]...
        .byte $04,$D0,$03,$4C,$35,$A1,$BD,$75   ; A0E7 ...L5..u
        .byte $04,$30,$15,$C9,$02,$90,$11,$20   ; A0EF .0..... 
        .byte $D1,$95,$29,$07,$D0,$0A,$A9,$FE   ; A0F7 ..).....
        .byte $9D,$75,$04,$A9,$50,$9D,$83,$04   ; A0FF .u..P...
        .byte $20,$7E,$A8,$BD,$9F,$04,$D0,$18   ; A107  ~......
        .byte $A9,$02,$20,$60,$98,$20,$B1,$98   ; A10F .. `. ..
        .byte $A5,$13,$29,$07,$D0,$0A,$20,$D1   ; A117 ..)... .
        .byte $95,$29,$0F,$D0,$03,$20,$9C,$A0   ; A11F .)... ..
        .byte $20,$77,$97,$BD,$91,$04,$F0,$06   ; A127  w......
        .byte $20,$69,$9C,$20,$9B,$9A,$60,$A9   ; A12F  i. ..`.
        .byte $06,$85,$F2,$A9,$09,$85,$F3,$A9   ; A137 ........
        .byte $03,$85,$F4,$20,$5D,$99,$BD,$91   ; A13F ... ]...
        .byte $04,$D0,$03,$4C,$97,$A1,$BD,$75   ; A147 ...L...u
        .byte $04,$30,$15,$C9,$02,$90,$11,$20   ; A14F .0..... 
        .byte $D1,$95,$29,$07,$D0,$0A,$A9,$FE   ; A157 ..).....
        .byte $9D,$75,$04,$A9,$50,$9D,$83,$04   ; A15F .u..P...
        .byte $20,$7E,$A8,$BD,$9F,$04,$D0,$1A   ; A167  ~......
        .byte $A9,$02,$20,$60,$98,$20,$B1,$98   ; A16F .. `. ..
        .byte $A5,$13,$29,$07,$D0,$0C,$20,$D1   ; A177 ..)... .
        .byte $95,$29,$0F,$D0,$05,$A9,$09,$20   ; A17F .)..... 
        .byte $D9,$95,$20,$77,$97,$BD,$91,$04   ; A187 .. w....
        .byte $F0,$06,$20,$69,$9C,$20,$9B,$9A   ; A18F .. i. ..
        .byte $60,$BD,$AD,$04,$C9,$02,$D0,$03   ; A197 `.......
        .byte $4C,$97,$9E,$C9,$03,$D0,$03,$4C   ; A19F L......L
        .byte $DE,$9E,$C9,$04,$90,$03,$4C,$16   ; A1A7 ......L.
        .byte $A3,$D0,$03,$4C,$DE,$9E,$20,$5D   ; A1AF ...L.. ]
        .byte $99,$90,$15,$BD,$4B,$04,$85,$00   ; A1B7 ....K...
        .byte $BD,$59,$04,$18,$69,$08,$85,$01   ; A1BF .Y..i...
        .byte $A9,$14,$20,$B3,$CF,$4C,$25,$99   ; A1C7 .. ..L%.
        .byte $BD,$59,$04,$C9,$EF,$90,$03,$4C   ; A1CF .Y.....L
        .byte $25,$99,$A4,$DF,$BD,$AD,$04,$D0   ; A1D7 %.......
        .byte $23,$BD,$59,$04,$18,$69,$07,$99   ; A1DF #.Y..i..
        .byte $00,$02,$A9,$01,$99,$02,$02,$A9   ; A1E7 ........
        .byte $3C,$99,$01,$02,$BD,$4B,$04,$38   ; A1EF <....K.8
        .byte $E5,$41,$99,$03,$02,$98,$18,$69   ; A1F7 .A.....i
        .byte $04,$85,$DF,$60,$BD,$59,$04,$99   ; A1FF ...`.Y..
        .byte $00,$02,$18,$69,$08,$99,$04,$02   ; A207 ...i....
        .byte $A9,$01,$99,$02,$02,$99,$06,$02   ; A20F ........
        .byte $A9,$75,$99,$01,$02,$A9,$85,$99   ; A217 .u......
        .byte $05,$02,$BD,$75,$04,$30,$12,$A9   ; A21F ...u.0..
        .byte $81,$99,$02,$02,$99,$06,$02,$A9   ; A227 ........
        .byte $85,$99,$01,$02,$A9,$75,$99,$05   ; A22F .....u..
        .byte $02,$BD,$4B,$04,$38,$E5,$41,$99   ; A237 ..K.8.A.
        .byte $03,$02,$99,$07,$02,$98,$18,$69   ; A23F .......i
        .byte $08,$85,$DF,$60,$C0,$01,$F0,$32   ; A247 ...`...2
        .byte $BD,$91,$04,$29,$01,$A8,$BD,$4B   ; A24F ...)...K
        .byte $04,$18,$79,$B9,$A2,$9D,$4B,$04   ; A257 ..y...K.
        .byte $18,$79,$BB,$A2,$4A,$4A,$4A,$4A   ; A25F .y..JJJJ
        .byte $85,$00,$BD,$59,$04,$29,$F0,$05   ; A267 ...Y.)..
        .byte $00,$A8,$B9,$00,$07,$C9,$15,$90   ; A26F ........
        .byte $08,$BD,$91,$04,$49,$01,$9D,$91   ; A277 ....I...
        .byte $04,$60,$BD,$91,$04,$49,$01,$29   ; A27F .`...I.)
        .byte $01,$A8,$BD,$59,$04,$18,$79,$B9   ; A287 ...Y..y.
        .byte $A2,$9D,$59,$04,$29,$F0,$85,$00   ; A28F ..Y.)...
        .byte $BD,$4B,$04,$4A,$4A,$4A,$4A,$05   ; A297 .K.JJJJ.
        .byte $00,$A8,$B9,$11,$07,$C9,$15,$B0   ; A29F ........
        .byte $08,$B9,$0F,$07,$C9,$15,$B0,$01   ; A2A7 ........
        .byte $60,$BD,$91,$04,$49,$01,$9D,$91   ; A2AF `...I...
        .byte $04,$60,$01,$FF,$0F,$00,$A0,$00   ; A2B7 .`......
        .byte $20,$C7,$A2,$C8,$20,$C7,$A2,$60   ; A2BF  ... ..`
        .byte $B9,$44,$00,$F0,$24,$B9,$48,$00   ; A2C7 .D..$.H.
        .byte $85,$E9,$B9,$4C,$00,$85,$E7,$BD   ; A2CF ...L....
        .byte $4B,$04,$85,$EA,$BD,$59,$04,$85   ; A2D7 K....Y..
        .byte $E8,$A9,$10,$85,$EC,$85,$ED,$85   ; A2DF ........
        .byte $EE,$4A,$85,$EB,$20,$C9,$8C,$B0   ; A2E7 .J.. ...
        .byte $01,$60,$B9,$64,$00,$D0,$FA,$B9   ; A2EF .`.d....
        .byte $54,$00,$30,$F5,$A9,$FE,$99,$54   ; A2F7 T.0....T
        .byte $00,$A9,$00,$99,$58,$00,$A9,$01   ; A2FF ....X...
        .byte $99,$63,$03,$BD,$59,$04,$38,$E9   ; A307 .c..Y.8.
        .byte $10,$99,$4C,$00,$E6,$04,$60,$38   ; A30F ..L...`8
        .byte $E9,$04,$48,$29,$01,$85,$00,$A9   ; A317 ..H)....
        .byte $00,$85,$04,$68,$4A,$85,$01,$D0   ; A31F ...hJ...
        .byte $03,$20,$BD,$A2,$A4,$00,$20,$4B   ; A327 . .... K
        .byte $A2,$A5,$01,$F0,$0C,$A0,$7C,$A9   ; A32F ......|.
        .byte $00,$06,$F1,$20,$6C,$9B,$4C,$77   ; A337 ... l.Lw
        .byte $97,$A4,$DF,$BD,$59,$04,$99,$00   ; A33F ....Y...
        .byte $02,$99,$04,$02,$18,$69,$08,$99   ; A347 .....i..
        .byte $08,$02,$99,$0C,$02,$A9,$01,$99   ; A34F ........
        .byte $02,$02,$99,$0E,$02,$A9,$41,$99   ; A357 ......A.
        .byte $06,$02,$99,$0A,$02,$BD,$4B,$04   ; A35F ......K.
        .byte $38,$E5,$41,$99,$03,$02,$99,$0F   ; A367 8.A.....
        .byte $02,$18,$69,$08,$99,$07,$02,$99   ; A36F ..i.....
        .byte $0B,$02,$A5,$13,$29,$10,$18,$69   ; A377 ....)..i
        .byte $74,$99,$09,$02,$99,$0D,$02,$A9   ; A37F t.......
        .byte $73,$99,$01,$02,$99,$05,$02,$98   ; A387 s.......
        .byte $18,$69,$10,$85,$DF,$A5,$04,$F0   ; A38F .i......
        .byte $05,$A9,$08,$20,$7A,$D3,$60,$A9   ; A397 ... z.`.
        .byte $05,$85,$F2,$A9,$02,$85,$F3,$20   ; A39F ....... 
        .byte $7E,$A8,$BD,$9F,$04,$D0,$08,$A9   ; A3A7 ~.......
        .byte $02,$20,$60,$98,$20,$B1,$98,$20   ; A3AF . `. .. 
        .byte $5D,$99,$90,$33,$BD,$91,$04,$F0   ; A3B7 ]..3....
        .byte $3C,$BD,$9F,$04,$D0,$29,$20,$D1   ; A3BF <....) .
        .byte $95,$09,$FC,$9D,$75,$04,$20,$D1   ; A3C7 ....u. .
        .byte $95,$09,$80,$9D,$83,$04,$20,$D1   ; A3CF ...... .
        .byte $95,$48,$0A,$90,$08,$BD,$91,$04   ; A3D7 .H......
        .byte $49,$01,$9D,$91,$04,$68,$29,$0B   ; A3DF I....h).
        .byte $D0,$05,$A9,$02,$20,$D9,$95,$20   ; A3E7 .... .. 
        .byte $77,$97,$BD,$91,$04,$F0,$06,$20   ; A3EF w...... 
        .byte $69,$9C,$20,$9B,$9A,$60,$A9,$00   ; A3F7 i. ..`..
        .byte $85,$F2,$A9,$09,$85,$F3,$A9,$03   ; A3FF ........
        .byte $85,$F4,$20,$7E,$A8,$20,$5D,$99   ; A407 .. ~. ].
        .byte $BD,$91,$04,$F0,$29,$90,$19,$BD   ; A40F ....)...
        .byte $9F,$04,$D0,$14,$A9,$01,$20,$60   ; A417 ...... `
        .byte $98,$20,$B1,$98,$20,$D1,$95,$29   ; A41F . .. ..)
        .byte $0F,$D0,$05,$A9,$09,$20,$D9,$95   ; A427 ..... ..
        .byte $20,$77,$97,$BD,$91,$04,$F0,$06   ; A42F  w......
        .byte $20,$69,$9C,$20,$9B,$9A,$60,$A9   ; A437  i. ..`.
        .byte $00,$85,$F2,$A9,$09,$85,$F3,$20   ; A43F ....... 
        .byte $7E,$A8,$20,$5D,$99,$BD,$91,$04   ; A447 ~. ]....
        .byte $F0,$3D,$90,$2D,$20,$D1,$95,$29   ; A44F .=.- ..)
        .byte $03,$D0,$62,$BD,$9F,$04,$D0,$21   ; A457 ..b....!
        .byte $A9,$01,$20,$60,$98,$20,$B1,$98   ; A45F .. `. ..
        .byte $20,$D1,$95,$29,$0F,$D0,$12,$A9   ; A467  ..)....
        .byte $09,$20,$D9,$95,$A9,$02,$20,$D9   ; A46F . .... .
        .byte $95,$BD,$91,$04,$49,$01,$9D,$91   ; A477 ....I...
        .byte $04,$20,$77,$97,$BD,$91,$04,$F0   ; A47F . w.....
        .byte $06,$20,$69,$9C,$20,$9B,$9A,$60   ; A487 . i. ..`
        .byte $A9,$06,$85,$F2,$A9,$04,$85,$F3   ; A48F ........
        .byte $A9,$05,$85,$F4,$20,$7E,$A8,$BD   ; A497 .... ~..
        .byte $59,$04,$18,$69,$10,$9D,$59,$04   ; A49F Y..i..Y.
        .byte $20,$5D,$99,$90,$10,$20,$D1,$95   ; A4A7  ]... ..
        .byte $09,$FC,$9D,$75,$04,$20,$D1,$95   ; A4AF ...u. ..
        .byte $09,$80,$9D,$83,$04,$BD,$59,$04   ; A4B7 ......Y.
        .byte $38,$E9,$10,$9D,$59,$04,$BD,$91   ; A4BF 8...Y...
        .byte $04,$F0,$29,$90,$19,$BD,$9F,$04   ; A4C7 ..).....
        .byte $D0,$14,$A9,$02,$20,$60,$98,$20   ; A4CF .... `. 
        .byte $B1,$98,$20,$D1,$95,$29,$0F,$D0   ; A4D7 .. ..)..
        .byte $05,$A9,$04,$20,$D9,$95,$20,$77   ; A4DF ... .. w
        .byte $97,$BD,$91,$04,$F0,$06,$20,$69   ; A4E7 ...... i
        .byte $9C,$20,$9B,$9A,$60,$06,$F1,$20   ; A4EF . ..`.. 
        .byte $7E,$A8,$20,$BF,$99,$BD,$91,$04   ; A4F7 ~. .....
        .byte $F0                               ; A4FF .
LA500:
        and #$BD                                ; A500
        .byte $9F,$04,$D0,$08,$A9,$01,$20,$60   ; A502 ...... `
        .byte $98,$20,$B1,$98,$20,$77,$97,$BD   ; A50A . .. w..
        .byte $91,$04,$F0,$14,$20,$69,$9C,$A5   ; A512 .... i..
        .byte $13,$4A,$4A,$4A,$29,$03,$A8,$B9   ; A51A .JJJ)...
        .byte $2B,$A5,$A8,$A9,$00,$20,$6C,$9B   ; A522 +.... l.
        .byte $60,$A0,$A4,$A8,$A4,$06,$F1,$20   ; A52A `...... 
        .byte $7E,$A8,$BD,$9F,$04,$85,$0A,$C9   ; A532 ~.......
        .byte $03,$D0,$0C,$BD,$59,$04,$C9,$E8   ; A53A ....Y...
        .byte $90,$05,$A9,$00,$9D,$9F,$04,$BD   ; A542 ........
        .byte $91,$04,$D0,$03,$4C,$DF,$A5,$29   ; A54A ....L..)
        .byte $3E,$C9,$2E,$D0,$0D,$BD,$9F,$04   ; A552 >.......
        .byte $D0,$1C,$A9,$01,$20,$60,$98,$4C   ; A55A .... `.L
        .byte $78,$A5,$BD,$4B,$04,$C9,$18,$B0   ; A562 x..K....
        .byte $03,$FE,$4B,$04,$BD,$4B,$04,$C9   ; A56A ..K..K..
        .byte $E8,$90,$03,$DE,$4B,$04,$A5,$0A   ; A572 ....K...
        .byte $C9,$02,$F0,$06,$20,$31,$99,$4C   ; A57A .... 1.L
        .byte $87,$A5,$20,$BF,$99,$A5,$0A,$D0   ; A582 .. .....
        .byte $11,$BD,$59,$04,$C9,$20,$90,$0A   ; A58A ..Y.. ..
        .byte $A9,$FE,$9D,$75,$04,$A9,$00,$9D   ; A592 ...u....
        .byte $83,$04,$BD,$9F,$04,$D0,$25,$BD   ; A59A ......%.
        .byte $4B,$04,$18,$69,$04,$4A,$4A,$4A   ; A5A2 K..i.JJJ
        .byte $4A,$85,$00,$A0,$00,$B9,$48,$00   ; A5AA J.....H.
        .byte $4A,$4A,$4A,$4A,$C5,$00,$F0,$07   ; A5B2 JJJJ....
        .byte $C8,$C0,$02,$D0,$F0,$F0,$05,$A9   ; A5BA ........
        .byte $03,$9D,$9F,$04,$20,$77,$97,$BD   ; A5C2 .... w..
        .byte $91,$04,$F0,$11,$BD,$9F,$04,$C9   ; A5CA ........
        .byte $03,$F0,$03,$20,$69,$9C,$A0,$CC   ; A5D2 ... i...
        .byte $A9,$02,$20,$6C,$9B,$60,$06,$F1   ; A5DA .. l.`..
        .byte $20,$7E,$A8,$20,$BF,$99,$90,$12   ; A5E2  ~. ....
        .byte $BD,$91,$04,$F0,$1F,$BD,$9F,$04   ; A5EA ........
        .byte $D0,$08,$A9,$04,$20,$60,$98,$20   ; A5F2 .... `. 
        .byte $B1,$98,$20,$77,$97,$BD,$91,$04   ; A5FA .. w....
        .byte $F0,$0A,$20,$69,$9C,$A0,$B8,$A9   ; A602 .. i....
        .byte $02,$20,$6C,$9B,$60,$06,$F1,$20   ; A60A . l.`.. 
        .byte $7E,$A8,$BD,$9F,$04,$D0,$08,$A9   ; A612 ~.......
        .byte $02,$20,$60,$98,$20,$B1,$98,$20   ; A61A . `. .. 
        .byte $BF,$99,$90,$33,$BD,$91,$04,$F0   ; A622 ...3....
        .byte $40,$BD,$9F,$04,$D0,$29,$20,$D1   ; A62A @....) .
        .byte $95,$09,$F8,$9D,$75,$04,$20,$D1   ; A632 ....u. .
        .byte $95,$09,$80,$9D,$83,$04,$20,$D1   ; A63A ...... .
        .byte $95,$48,$0A,$90,$08,$BD,$91,$04   ; A642 .H......
        .byte $49,$01,$9D,$91,$04,$68,$29,$0B   ; A64A I....h).
        .byte $D0,$05,$A9,$02,$20,$D9,$95,$20   ; A652 .... .. 
        .byte $77,$97,$BD,$91,$04,$F0,$0A,$20   ; A65A w...... 
        .byte $69,$9C,$A0,$BC,$A9,$02,$20,$6C   ; A662 i..... l
        .byte $9B,$60,$06,$F1,$20,$7E,$A8,$20   ; A66A .`.. ~. 
        .byte $BF,$99,$BD,$91,$04,$F0,$64,$BD   ; A672 ......d.
        .byte $9F,$04,$D0,$08,$A9,$04,$20,$60   ; A67A ...... `
        .byte $98,$20,$B1,$98,$BD,$59,$04,$18   ; A682 . ...Y..
        .byte $69,$08,$4A,$4A,$29,$38,$85,$E0   ; A68A i.JJ)8..
        .byte $BD,$4B,$04,$18,$69,$0C,$4A,$4A   ; A692 .K..i.JJ
        .byte $4A,$4A,$4A,$05,$E0,$A8,$29,$0F   ; A69A JJJ...).
        .byte $48,$F0,$0D,$B9,$BF,$06,$F0,$08   ; A6A2 H.......
        .byte $BD,$91,$04,$29,$FE,$9D,$91,$04   ; A6AA ...)....
        .byte $68,$C9,$0F,$F0,$0D,$B9,$C1,$06   ; A6B2 h.......
        .byte $F0,$08,$BD,$91,$04,$09,$01,$9D   ; A6BA ........
        .byte $91,$04,$20,$77,$97,$BD,$91,$04   ; A6C2 .. w....
        .byte $F0,$11,$20,$69,$9C,$A5,$13,$4A   ; A6CA .. i...J
        .byte $29,$04,$18,$69,$68,$A8,$A9,$00   ; A6D2 )..ih...
        .byte $20,$6C,$9B,$60,$06,$F1,$20,$7E   ; A6DA  l.`.. ~
        .byte $A8,$20,$BF,$99,$90,$2C,$BD,$91   ; A6E2 . ...,..
        .byte $04,$F0,$39,$BD,$9F,$04,$D0,$22   ; A6EA ..9...."
        .byte $A9,$02,$20,$60,$98,$20,$B1,$98   ; A6F2 .. `. ..
        .byte $A5,$13,$29,$3F,$D0,$14,$20,$D1   ; A6FA ..)?.. .
        .byte $95,$29,$01,$D0,$0D,$A9,$01,$9D   ; A702 .)......
        .byte $9F,$04,$A9,$0A,$9D,$BB,$04,$20   ; A70A ....... 
        .byte $27,$A7,$20,$77,$97,$BD,$91,$04   ; A712 '. w....
        .byte $F0,$0A,$20,$69,$9C,$A0,$78,$A9   ; A71A .. i..x.
        .byte $00,$20,$6C,$9B,$60,$8A,$A8,$20   ; A722 . l.`.. 
        .byte $88,$9A,$08,$90,$29,$A9,$0A,$9D   ; A72A ....)...
        .byte $91,$04,$A9,$01,$9D,$AD,$04,$B9   ; A732 ........
        .byte $59,$04,$9D,$59,$04,$A9,$FC,$9D   ; A73A Y..Y....
        .byte $75,$04,$A9,$00,$9D,$67,$04,$9D   ; A742 u....g..
        .byte $83,$04,$9D,$BB,$04,$B9,$4B,$04   ; A74A ......K.
        .byte $9D,$4B,$04,$EE,$DC,$04,$98,$AA   ; A752 .K......
        .byte $28,$60,$06,$F1,$20,$7E,$A8,$BD   ; A75A (`.. ~..
        .byte $9F,$04,$D0,$12,$A5,$13,$29,$3F   ; A762 ......)?
        .byte $D0,$0C,$20,$D1,$95,$29,$01,$D0   ; A76A .. ..)..
        .byte $05,$A9,$FE,$9D,$75,$04,$20,$BF   ; A772 ....u. .
        .byte $99,$90,$12,$BD,$91,$04,$F0,$26   ; A77A .......&
        .byte $BD,$9F,$04,$D0,$08,$A9,$02,$20   ; A782 ....... 
        .byte $60,$98,$20,$B1,$98,$20,$77,$97   ; A78A `. .. w.
        .byte $BD,$91,$04,$F0,$11,$20,$69,$9C   ; A792 ..... i.
        .byte $A5,$13,$4A,$29,$04,$18,$69,$AC   ; A79A ..J)..i.
        .byte $A8,$A9,$00,$20,$6C,$9B,$60,$06   ; A7A2 ... l.`.
        .byte $F1,$20,$7E,$A8,$20,$BF,$99,$90   ; A7AA . ~. ...
        .byte $11,$BD,$9F,$04,$D0,$30,$A9,$FB   ; A7B2 .....0..
        .byte $9D,$75,$04,$A9,$00,$9D,$83,$04   ; A7BA .u......
        .byte $D0,$24,$BD,$91,$04,$F0,$57,$BD   ; A7C2 .$....W.
        .byte $9F,$04,$D0,$1A,$A9,$02,$20,$60   ; A7CA ...... `
        .byte $98,$90,$13,$A9,$FC,$9D,$75,$04   ; A7D2 ......u.
        .byte $A9,$00,$9D,$83,$04,$A9,$04,$20   ; A7DA ....... 
        .byte $D9,$95,$38,$20,$B1,$98,$BD,$75   ; A7E2 ..8 ...u
        .byte $04,$30,$1A,$C9,$02,$90,$16,$BD   ; A7EA .0......
        .byte $9F,$04,$D0,$11,$20,$D1,$95,$29   ; A7F2 .... ..)
        .byte $07,$D0,$0A,$A9,$FE,$9D,$75,$04   ; A7FA ......u.
        .byte $A9,$50,$9D,$83,$04,$20,$77,$97   ; A802 .P... w.
        .byte $BD,$91,$04,$F0,$11,$20,$69,$9C   ; A80A ..... i.
        .byte $A5,$13,$4A,$29,$04,$18,$69,$AC   ; A812 ..J)..i.
        .byte $A8,$A9,$00,$20,$6C,$9B,$60,$06   ; A81A ... l.`.
        .byte $F1,$20,$7E,$A8,$20,$BF,$99,$90   ; A822 . ~. ...
        .byte $12,$BD,$91,$04,$F0,$27,$BD,$9F   ; A82A .....'..
        .byte $04,$D0,$08,$A9,$01,$20,$60,$98   ; A832 ..... `.
        .byte $20,$B1,$98,$20,$77,$97,$BD,$91   ; A83A  .. w...
        .byte $04,$F0,$12,$20,$69,$9C,$A0,$88   ; A842 ... i...
        .byte $A5,$13,$29,$08,$F0,$02,$A0,$8C   ; A84A ..).....
        .byte $A9,$00,$20,$6C,$9B,$60,$A5,$44   ; A852 .. l.`.D
        .byte $18,$65,$45,$F0,$1E,$C9,$02,$F0   ; A85A .eE.....
        .byte $1A,$A0,$00,$B9,$44,$00,$D0,$07   ; A862 ....D...
        .byte $E8,$B9,$44,$00,$D0,$01,$60,$5E   ; A86A ..D...`^
        .byte $91,$04,$BD,$4B,$04,$D5,$48,$3E   ; A872 ...K..H>
        .byte $91,$04,$60,$60,$BD,$9F,$04,$C9   ; A87A ..``....
        .byte $02,$F0,$08,$20,$02,$98,$90,$03   ; A882 ... ....
        .byte $20,$0F,$97,$60,$06,$F1,$BD,$91   ; A88A  ..`....
        .byte $04,$29,$3E,$4A,$38,$E9,$0E,$85   ; A892 .)>J8...
        .byte $08,$20,$7E,$A8,$A5,$13,$29,$20   ; A89A . ~...) 
        .byte $D0,$06,$20,$D1,$95,$9D,$AD,$04   ; A8A2 .. .....
        .byte $A5,$08,$C9,$01,$D0,$1F,$BD,$9F   ; A8AA ........
        .byte $04,$D0,$1A,$20,$D1,$95,$29,$0F   ; A8B2 ... ..).
        .byte $D0,$13,$BD,$4B,$04,$48,$18,$69   ; A8BA ...K.H.i
        .byte $04,$9D,$4B,$04,$A9,$04,$20,$D9   ; A8C2 ..K... .
        .byte $95,$68,$9D,$4B,$04,$20,$31,$99   ; A8CA .h.K. 1.
        .byte $BD,$59,$04,$DD,$AD,$04,$90,$05   ; A8D2 .Y......
        .byte $A9,$FF,$9D,$75,$04,$20,$69,$9C   ; A8DA ...u. i.
        .byte $BD,$91,$04,$F0,$2C,$BD,$9F,$04   ; A8E2 ....,...
        .byte $D0,$0F,$A9,$02,$A4,$08,$C0,$02   ; A8EA ........
        .byte $D0,$01,$0A,$20,$60,$98,$20,$B1   ; A8F2 ... `. .
        .byte $98,$20,$77,$97,$BD,$91,$04,$F0   ; A8FA . w.....
        .byte $10,$20,$69,$9C,$A5,$08,$0A,$0A   ; A902 . i.....
        .byte $18,$69,$94,$A8,$A9,$00,$20,$6C   ; A90A .i.... l
        .byte $9B,$60                           ; A912 .`
LA914:
        jsr L81A8                               ; A914
        and #$07                                ; A917
        tax                                     ; A919
        jsr L95D1                               ; A91A
        and #$07                                ; A91D
        tay                                     ; A91F
        lda $044B,x                             ; A920
        sta $00                                 ; A923
        lda $0459,x                             ; A925
        sta $01                                 ; A928
        lda $0467,x                             ; A92A
        sta $02                                 ; A92D
        lda $0475,x                             ; A92F
        sta $03                                 ; A932
        lda $0483,x                             ; A934
        sta $04                                 ; A937
        lda $0491,x                             ; A939
        sta $05                                 ; A93C
        lda $049F,x                             ; A93E
        sta $06                                 ; A941
        lda $04AD,x                             ; A943
        sta $07                                 ; A946
        lda $04BB,x                             ; A948
        sta $08                                 ; A94B
        lda $044B,y                             ; A94D
        sta $044B,x                             ; A950
        lda $0459,y                             ; A953
        sta $0459,x                             ; A956
        lda $0467,y                             ; A959
        sta $0467,x                             ; A95C
        lda $0475,y                             ; A95F
        sta $0475,x                             ; A962
        lda $0483,y                             ; A965
        sta $0483,x                             ; A968
        lda $0491,y                             ; A96B
        sta $0491,x                             ; A96E
        lda $049F,y                             ; A971
        sta $049F,x                             ; A974
        lda $04AD,y                             ; A977
        sta $04AD,x                             ; A97A
        lda $04BB,y                             ; A97D
        sta $04BB,x                             ; A980
        lda $00                                 ; A983
        sta $044B,y                             ; A985
        lda $01                                 ; A988
        sta $0459,y                             ; A98A
        lda $02                                 ; A98D
        sta $0467,y                             ; A98F
        lda $03                                 ; A992
        sta $0475,y                             ; A994
        lda $04                                 ; A997
        sta $0483,y                             ; A999
        lda $05                                 ; A99C
        sta $0491,y                             ; A99E
        lda $06                                 ; A9A1
        sta $049F,y                             ; A9A3
        lda $07                                 ; A9A6
        sta $04AD,y                             ; A9A8
        lda $08                                 ; A9AB
        sta $04BB,y                             ; A9AD
        rts                                     ; A9B0
LA9B1:
        jsr LD33B                               ; A9B1
        lda #$00                                ; A9B4
        sta $DB                                 ; A9B6
        sta $DD                                 ; A9B8
        sta $04E8                               ; A9BA
        sta $04ED                               ; A9BD
        sta $04EE                               ; A9C0
        sta $04F1                               ; A9C3
        sta $03CD                               ; A9C6
        lda #$00                                ; A9C9
        sta $DC                                 ; A9CB
        lda #$00                                ; A9CD
        sta PPUMASK                             ; A9CF
        sta PPUSCROLL                           ; A9D2
        sta PPUSCROLL                           ; A9D5
        jsr LC210                               ; A9D8
        lda #$2D                                ; A9DB
        sta $00                                 ; A9DD
        lda #$AA                                ; A9DF
        sta $01                                 ; A9E1
        lda $12                                 ; A9E3
        beq LA9EF                               ; A9E5
        lda #$DB                                ; A9E7
        sta $00                                 ; A9E9
        lda #$AB                                ; A9EB
        sta $01                                 ; A9ED
LA9EF:
        lda #$20                                ; A9EF
        sta PPUADDR                             ; A9F1
        lda #$00                                ; A9F4
        sta PPUADDR                             ; A9F6
        jsr LC248                               ; A9F9
        lda #$00                                ; A9FC
        sta PPUSCROLL                           ; A9FE
        sta PPUSCROLL                           ; AA01
        jsr L80D0                               ; AA04
        lda #$1E                                ; AA07
        sta PPUMASK                             ; AA09
        jsr L8165                               ; AA0C
        jsr LADDB                               ; AA0F
        jsr L80D0                               ; AA12
        ldy #$00                                ; AA15
        jsr LADEC                               ; AA17
        asl                                     ; AA1A
        tax                                     ; AA1B
        lda $13                                 ; AA1C
        beq LAA22                               ; AA1E
        ora #$01                                ; AA20
LAA22:
        sta $10                                 ; AA22
        lda LAD8E,x                             ; AA24
        pha                                     ; AA27
        lda LAD8D,x                             ; AA28
        pha                                     ; AA2B
        rts                                     ; AA2C
        .byte $04,$00,$9E,$20,$00,$8D,$E9,$8E   ; AA2D ... ....
        .byte $00,$8F,$FB,$20,$03,$9D,$1D,$1D   ; AA35 ... ....
        .byte $C1,$FD,$1E,$02,$C0,$1D,$C1,$FE   ; AA3D ........
        .byte $1E,$FE,$1D,$03,$C1,$1E,$1E,$C0   ; AA45 ........
        .byte $FE,$1D,$01,$C1,$9F,$FB,$20,$14   ; AA4D ...... .
        .byte $9D,$1D,$1E,$C2,$C1,$1E,$1E,$C0   ; AA55 ........
        .byte $C3,$1E,$C2,$C1,$1E,$1E,$1D,$1E   ; AA5D ........
        .byte $1E,$C2,$C1,$1E,$1D,$FE,$1E,$01   ; AA65 ........
        .byte $1D,$9F,$FB,$20,$07,$9D,$1D,$1E   ; AA6D ... ....
        .byte $1E,$C2,$C1,$1E,$1D,$FE,$1E,$03   ; AA75 ........
        .byte $1D,$1E,$1E,$1D,$FE,$1E,$02,$1D   ; AA7D ........
        .byte $1E,$1D,$FD,$1E,$00,$9F,$FB,$20   ; AA85 ....... 
        .byte $01,$9D,$1D,$FE,$1E,$02,$1D,$1E   ; AA8D ........
        .byte $1D,$FE,$1E,$09,$1D,$1E,$1E,$1D   ; AA95 ........
        .byte $1E,$1E,$C0,$C3,$1E,$1D,$FD,$1E   ; AA9D ........
        .byte $00,$9F,$FB,$20,$01,$9D,$1D,$FE   ; AAA5 ... ....
        .byte $1E,$01,$1D,$1E,$FC,$1D,$01,$1E   ; AAAD ........
        .byte $1E,$FE,$1D,$04,$9E,$1E,$1E,$1D   ; AAB5 ........
        .byte $1E,$FE,$1D,$00,$9F,$FB,$20,$01   ; AABD ...... .
        .byte $9D,$1D,$FE,$1E,$02,$1D,$1E,$1D   ; AAC5 ........
        .byte $FE,$1E,$09,$1D,$1E,$1E,$1D,$1E   ; AACD ........
        .byte $1E,$C2,$C1,$1E,$1D,$FE,$1E,$01   ; AAD5 ........
        .byte $1D,$9F,$FB,$20,$07,$9D,$1D,$1E   ; AADD ... ....
        .byte $1E,$C0,$C3,$1E,$1D,$FE,$1E,$03   ; AAE5 ........
        .byte $1D,$1E,$1E,$1D,$FE,$1E,$02,$1D   ; AAED ........
        .byte $1E,$1D,$FE,$1E,$01,$1D,$9F,$FB   ; AAF5 ........
        .byte $20,$07,$9D,$1D,$1E,$C0,$C3,$1E   ; AAFD  .......
        .byte $1E,$1D,$FE,$1E,$09,$1D,$1E,$1E   ; AB05 ........
        .byte $1D,$1E,$1E,$C0,$C3,$1E,$1D,$FE   ; AB0D ........
        .byte $1E,$01,$1D,$9F,$FB,$20,$03,$9D   ; AB15 ..... ..
        .byte $1D,$1D,$C3,$FE,$1E,$00,$1D,$FE   ; AB1D ........
        .byte $1E,$02,$1D,$1E,$1E,$FE,$1D,$03   ; AB25 ........
        .byte $C3,$1E,$1E,$C2,$FE,$1D,$01,$C3   ; AB2D ........
        .byte $9F,$FB,$20,$00,$AD,$E9,$AE,$00   ; AB35 .. .....
        .byte $AF,$D7,$20,$0D,$22,$44,$6F,$75   ; AB3D .. ."Dou
        .byte $62,$6C,$65,$20,$41,$63,$74,$69   ; AB45 ble Acti
        .byte $6F,$6E,$EB,$20,$0C,$42,$6C,$61   ; AB4D on. .Bla
        .byte $73,$74,$65,$72,$20,$47,$75,$79   ; AB55 ster Guy
        .byte $73,$22,$F7,$20,$00,$0B,$E2,$20   ; AB5D s". ... 
        .byte $00,$1B,$E8,$20,$00,$0C,$FD,$20   ; AB65 ... ... 
        .byte $02,$90,$91,$92,$E9,$20,$00,$1C   ; AB6D ..... ..
        .byte $F1,$20,$04,$20,$43,$61,$72,$74   ; AB75 . . Cart
        .byte $F8,$20,$02,$90,$91,$92,$FC,$20   ; AB7D . ..... 
        .byte $00,$0B,$F9,$20,$06,$45,$64,$69   ; AB85 ... .Edi
        .byte $74,$69,$6F,$6E,$F1,$20,$00,$1B   ; AB8D tion. ..
        .byte $E8,$20,$00,$0C,$FD,$20,$02,$90   ; AB95 . ... ..
        .byte $91,$92,$FC,$20,$0B,$50,$72,$65   ; AB9D ... .Pre
        .byte $73,$73,$20,$53,$74,$61,$72,$74   ; ABA5 ss Start
        .byte $21,$FA,$20,$00,$1C,$E3,$20,$02   ; ABAD !. ... .
        .byte $90,$91,$92,$B9,$20,$11,$12,$32   ; ABB5 .... ..2
        .byte $30,$31,$34,$20,$4E,$6F,$76,$61   ; ABBD 014 Nova
        .byte $53,$71,$75,$69,$72,$72,$65,$6C   ; ABC5 Squirrel
        .byte $F3,$20,$00,$90,$F1,$91,$00,$92   ; ABCD . ......
        .byte $DA,$20,$C2,$00,$00,$00,$04,$00   ; ABD5 . ......
        .byte $9E,$20,$00,$8D,$E9,$8E,$00,$8F   ; ABDD . ......
        .byte $FB,$20,$04,$9D,$1E,$C0,$1D,$C1   ; ABE5 . ......
        .byte $FE,$1E,$02,$C0,$1D,$C1,$FE,$1E   ; ABED ........
        .byte $FE,$1D,$03,$C1,$1E,$1E,$C0,$FE   ; ABF5 ........
        .byte $1D,$01,$C1,$9F,$FB,$20,$14,$9D   ; ABFD ..... ..
        .byte $C0,$C3,$1E,$C2,$C1,$1E,$C0,$C3   ; AC05 ........
        .byte $1E,$C2,$C1,$1E,$1E,$1D,$1E,$1E   ; AC0D ........
        .byte $C2,$C1,$1E,$1D,$FE,$1E,$01,$1D   ; AC15 ........
        .byte $9F,$FB,$20,$01,$9D,$1D,$FE,$1E   ; AC1D .. .....
        .byte $02,$1D,$1E,$1D,$FE,$1E,$03,$1D   ; AC25 ........
        .byte $1E,$1E,$1D,$FE,$1E,$02,$1D,$1E   ; AC2D ........
        .byte $1D,$FD,$1E,$00,$9F,$FB,$20,$01   ; AC35 ...... .
        .byte $9D,$1D,$FE,$1E,$02,$1D,$1E,$1D   ; AC3D ........
        .byte $FE,$1E,$09,$1D,$1E,$1E,$1D,$1E   ; AC45 ........
        .byte $1E,$C0,$C3,$1E,$1D,$FD,$1E,$00   ; AC4D ........
        .byte $9F,$FB,$20,$01,$9D,$1D,$FE,$1E   ; AC55 .. .....
        .byte $01,$1D,$1E,$FC,$1D,$01,$1E,$1E   ; AC5D ........
        .byte $FE,$1D,$04,$9E,$1E,$1E,$1D,$1E   ; AC65 ........
        .byte $FE,$1D,$00,$9F,$FB,$20,$01,$9D   ; AC6D ..... ..
        .byte $1D,$FE,$1E,$02,$1D,$1E,$1D,$FE   ; AC75 ........
        .byte $1E,$09,$1D,$1E,$1E,$1D,$1E,$1E   ; AC7D ........
        .byte $C2,$C1,$1E,$1D,$FE,$1E,$01,$1D   ; AC85 ........
        .byte $9F,$FB,$20,$07,$9D,$1D,$1E,$1D   ; AC8D .. .....
        .byte $1E,$1D,$1E,$1D,$FE,$1E,$03,$1D   ; AC95 ........
        .byte $1E,$1E,$1D,$FE,$1E,$02,$1D,$1E   ; AC9D ........
        .byte $1D,$FE,$1E,$01,$1D,$9F,$FB,$20   ; ACA5 ....... 
        .byte $07,$9D,$C2,$C1,$1E,$1D,$1E,$1E   ; ACAD ........
        .byte $1D,$FE,$1E,$09,$1D,$1E,$1E,$1D   ; ACB5 ........
        .byte $1E,$1E,$C0,$C3,$1E,$1D,$FE,$1E   ; ACBD ........
        .byte $01,$1D,$9F,$FB,$20,$07,$9D,$1E   ; ACC5 .... ...
        .byte $C2,$1D,$1E,$1D,$1E,$1D,$FE,$1E   ; ACCD ........
        .byte $02,$1D,$1E,$1E,$FE,$1D,$03,$C3   ; ACD5 ........
        .byte $1E,$1E,$C2,$FE,$1D,$01,$C3,$9F   ; ACDD ........
        .byte $FB,$20,$00,$AD,$E9,$AE,$00,$AF   ; ACE5 . ......
        .byte $D7,$20,$10,$22,$51,$75,$61,$64   ; ACED . ."Quad
        .byte $72,$75,$70,$6C,$65,$20,$41,$63   ; ACF5 ruple Ac
        .byte $74,$69,$6F,$6E,$EE,$20,$0C,$42   ; ACFD tion. .B
        .byte $6C,$61,$73,$74,$65,$72,$20,$47   ; AD05 laster G
        .byte $75,$79,$73,$22,$F7,$20,$00,$0B   ; AD0D uys". ..
        .byte $E2,$20,$00,$1B,$E8,$20,$00,$0C   ; AD15 . ... ..
        .byte $FD,$20,$02,$90,$91,$92,$E9,$20   ; AD1D . ..... 
        .byte $00,$1C,$F1,$20,$04,$50,$61,$72   ; AD25 ... .Par
        .byte $74,$79,$F8,$20,$02,$90,$91,$92   ; AD2D ty. ....
        .byte $FC,$20,$00,$0B,$F9,$20,$06,$45   ; AD35 . ... .E
        .byte $64,$69,$74,$69,$6F,$6E,$F1,$20   ; AD3D dition. 
        .byte $00,$1B,$E8,$20,$00,$0C,$FD,$20   ; AD45 ... ... 
        .byte $02,$90,$91,$92,$FC,$20,$0B,$50   ; AD4D ..... .P
        .byte $72,$65,$73,$73,$20,$53,$74,$61   ; AD55 ress Sta
        .byte $72,$74,$21,$FA,$20,$00,$1C,$E3   ; AD5D rt!. ...
        .byte $20,$02,$90,$91,$92,$B9,$20,$11   ; AD65  ..... .
        .byte $12,$32,$30,$31,$36,$20,$4E,$6F   ; AD6D .2016 No
        .byte $76,$61,$53,$71,$75,$69,$72,$72   ; AD75 vaSquirr
        .byte $65,$6C,$F3,$20,$00,$90,$F1,$91   ; AD7D el. ....
        .byte $00,$92,$DA,$20,$C2,$00,$00,$00   ; AD85 ... ....
LAD8D:
        .byte $E8                               ; AD8D .
LAD8E:
        .byte $B7,$F8,$C2,$CA,$B0,$9E,$B2,$96   ; AD8E ........
        .byte $AD,$6C,$FC,$FF                   ; AD96 .l..
LAD9A:
        .byte $05,$22,$8A,$50,$6C,$61,$79,$20   ; AD9A .".Play 
        .byte $47,$61,$6D,$65,$00,$22,$AA,$4C   ; ADA2 Game.".L
        .byte $65,$76,$65,$6C,$20,$45,$64,$69   ; ADAA evel Edi
        .byte $74,$00,$22,$CA,$48,$6F,$77,$20   ; ADB2 t.".How 
        .byte $54,$6F,$20,$50,$6C,$61,$79,$00   ; ADBA To Play.
        .byte $22,$EA,$43,$72,$65,$64,$69,$74   ; ADC2 ".Credit
        .byte $73,$00,$23,$0A,$45,$78,$69,$74   ; ADCA s.#.Exit
        .byte $20,$74,$6F,$20,$6D,$65,$6E,$75   ; ADD2  to menu
        .byte $00                               ; ADDA .
LADDB:
        lda $14                                 ; ADDB
        beq LADE3                               ; ADDD
        lda #$01                                ; ADDF
        sta $44                                 ; ADE1
LADE3:
        lda $15                                 ; ADE3
        beq LADEB                               ; ADE5
        lda #$01                                ; ADE7
        sta $45                                 ; ADE9
LADEB:
        rts                                     ; ADEB
LADEC:
        ldx LAD9A,y                             ; ADEC
        stx $01                                 ; ADEF
        jsr LAEAC                               ; ADF1
LADF4:
        lda #$00                                ; ADF4
        sta PPUSCROLL                           ; ADF6
        sta PPUSCROLL                           ; ADF9
        jsr L80D0                               ; ADFC
        iny                                     ; ADFF
        dex                                     ; AE00
        bmi LAE1D                               ; AE01
        lda LAD9A,y                             ; AE03
        sta PPUADDR                             ; AE06
        iny                                     ; AE09
        lda LAD9A,y                             ; AE0A
        sta PPUADDR                             ; AE0D
        iny                                     ; AE10
LAE11:
        lda LAD9A,y                             ; AE11
        beq LADF4                               ; AE14
        sta PPUDATA                             ; AE16
        iny                                     ; AE19
        jmp LAE11                               ; AE1A
LAE1D:
        jsr LC210                               ; AE1D
        lda #$00                                ; AE20
        sta $00                                 ; AE22
LAE24:
        jsr L8000                               ; AE24
        jsr LADDB                               ; AE27
        lda $14                                 ; AE2A
        ora $15                                 ; AE2C
        ora $16                                 ; AE2E
        ora $17                                 ; AE30
        and #$08                                ; AE32
        beq LAE4C                               ; AE34
        lda $18                                 ; AE36
        ora $19                                 ; AE38
        ora $1A                                 ; AE3A
        ora $1B                                 ; AE3C
        and #$08                                ; AE3E
        bne LAE4C                               ; AE40
        dec $00                                 ; AE42
        bpl LAE4C                               ; AE44
        lda $01                                 ; AE46
        sta $00                                 ; AE48
        dec $00                                 ; AE4A
LAE4C:
        lda $14                                 ; AE4C
        ora $15                                 ; AE4E
        ora $16                                 ; AE50
        ora $17                                 ; AE52
        and #$04                                ; AE54
        beq LAE70                               ; AE56
        lda $18                                 ; AE58
        ora $19                                 ; AE5A
        ora $1A                                 ; AE5C
        ora $1B                                 ; AE5E
        and #$04                                ; AE60
        bne LAE70                               ; AE62
        inc $00                                 ; AE64
        lda $00                                 ; AE66
        cmp $01                                 ; AE68
        bcc LAE70                               ; AE6A
        lda #$00                                ; AE6C
        sta $00                                 ; AE6E
LAE70:
        lda #$40                                ; AE70
        sta $0203                               ; AE72
        lda $00                                 ; AE75
        asl                                     ; AE77
        asl                                     ; AE78
        asl                                     ; AE79
        clc                                     ; AE7A
        adc #$9F                                ; AE7B
        sta $0200                               ; AE7D
        sta $02                                 ; AE80
        lda #$28                                ; AE82
        sta $0201                               ; AE84
        lda #$00                                ; AE87
        sta $0202                               ; AE89
        lda $14                                 ; AE8C
        ora $15                                 ; AE8E
        ora $16                                 ; AE90
        ora $17                                 ; AE92
        and #$90                                ; AE94
        beq LAEA0                               ; AE96
        lda $18                                 ; AE98
        ora $19                                 ; AE9A
        and #$90                                ; AE9C
        beq LAEA6                               ; AE9E
LAEA0:
        jsr L80D0                               ; AEA0
        jmp LAE24                               ; AEA3
LAEA6:
        jsr LC210                               ; AEA6
        lda $00                                 ; AEA9
        rts                                     ; AEAB
LAEAC:
        lda #$00                                ; AEAC
        sta PPUSCROLL                           ; AEAE
        sta PPUSCROLL                           ; AEB1
        jsr L80D0                               ; AEB4
        lda #$22                                ; AEB7
        sta PPUADDR                             ; AEB9
        lda #$8A                                ; AEBC
        sta PPUADDR                             ; AEBE
        jsr LAEF5                               ; AEC1
        lda #$22                                ; AEC4
        sta PPUADDR                             ; AEC6
        lda #$AA                                ; AEC9
        sta PPUADDR                             ; AECB
        jsr LAEF5                               ; AECE
        lda #$22                                ; AED1
        sta PPUADDR                             ; AED3
        lda #$CA                                ; AED6
        sta PPUADDR                             ; AED8
        jsr LAEF5                               ; AEDB
        lda #$22                                ; AEDE
        sta PPUADDR                             ; AEE0
        lda #$EA                                ; AEE3
        sta PPUADDR                             ; AEE5
        jsr LAEF5                               ; AEE8
        lda #$23                                ; AEEB
        sta PPUADDR                             ; AEED
        lda #$0A                                ; AEF0
        sta PPUADDR                             ; AEF2
LAEF5:
        lda #$20                                ; AEF5
        sta PPUDATA                             ; AEF7
        sta PPUDATA                             ; AEFA
        sta PPUDATA                             ; AEFD
        sta PPUDATA                             ; AF00
        sta PPUDATA                             ; AF03
        sta PPUDATA                             ; AF06
        sta PPUDATA                             ; AF09
        sta PPUDATA                             ; AF0C
        sta PPUDATA                             ; AF0F
        sta PPUDATA                             ; AF12
        sta PPUDATA                             ; AF15
        sta PPUDATA                             ; AF18
        rts                                     ; AF1B
        .byte $20,$D0,$80,$20,$00,$80,$88,$F0   ; AF1C  .. ....
        .byte $14,$A5,$14,$05,$15,$05,$16,$05   ; AF24 ........
        .byte $17,$F0,$ED,$A5,$18,$05,$19,$05   ; AF2C ........
        .byte $1A,$05,$1B,$D0,$E3,$60           ; AF34 .....`
LAF3A:
        lda $11                                 ; AF3A
        beq LAF3F                               ; AF3C
        rts                                     ; AF3E
LAF3F:
        lda $04ED                               ; AF3F
        beq LAF4E                               ; AF42
        lda #$09                                ; AF44
        sta $76                                 ; AF46
        sta $77                                 ; AF48
        sta $78                                 ; AF4A
        sta $79                                 ; AF4C
LAF4E:
        jsr L80D0                               ; AF4E
        lda #$00                                ; AF51
        sta PPUMASK                             ; AF53
        jsr L813E                               ; AF56
        lda #$20                                ; AF59
        sta PPUADDR                             ; AF5B
        lda #$C8                                ; AF5E
        sta PPUADDR                             ; AF60
        jsr L8185                               ; AF63
        and $4E20,x                             ; AF66
        eor $58                                 ; AF69
        .byte $54,$20,$4C,$45,$56,$45,$4C,$20   ; AF6B T LEVEL 
        .byte $3D,$00,$A9,$21,$8D,$06,$20,$A9   ; AF73 =..!.. .
        .byte $2A,$8D,$06,$20,$20,$85,$81,$4C   ; AF7B *..  ..L
        .byte $65,$76,$65,$6C,$3A,$20,$00,$AD   ; AF83 evel: ..
        .byte $E8,$04,$D0,$08,$A5,$DD,$18,$69   ; AF8B .......i
        .byte $01,$20,$02,$81,$AD,$E8,$04,$F0   ; AF93 . ......
        .byte $0A,$20,$85,$81,$43,$75,$73,$74   ; AF9B . ..Cust
        .byte $6F,$6D,$00,$A9,$21,$8D,$06,$20   ; AFA3 om..!.. 
        .byte $A9,$6A,$8D,$06,$20,$20,$85,$81   ; AFAB .j..  ..
        .byte $4C,$69,$76,$65,$73,$3A,$20,$00   ; AFB3 Lives: .
        .byte $A5,$12,$F0,$20,$A2,$00,$B5,$44   ; AFBB ... ...D
        .byte $F0,$08,$B5,$76,$20,$02,$81,$4C   ; AFC3 ...v ..L
        .byte $D2,$AF,$A9,$2D,$8D,$07,$20,$A9   ; AFCB ...-.. .
        .byte $20,$8D,$07,$20,$E8,$E0,$04,$D0   ; AFD3  .. ....
        .byte $E5,$4C,$F6,$AF,$A5,$44,$F0,$0A   ; AFDB .L...D..
        .byte $A5,$76,$20,$02,$81,$A9,$20,$8D   ; AFE3 .v ... .
        .byte $07,$20,$A5,$45,$F0,$05,$A5,$77   ; AFEB . .E...w
        .byte $20,$02,$81,$A9,$21,$8D,$06,$20   ; AFF3  ...!.. 
        .byte $A9,$A7,$8D,$06,$20,$20,$30,$B0   ; AFFB ....  0.
        .byte $A9,$00,$8D,$05,$20,$8D,$05,$20   ; B003 .... .. 
        .byte $20,$D0,$80,$A9,$1E,$8D,$01,$20   ; B00B  ...... 
        .byte $A0,$64,$20,$1C,$AF,$A5,$14,$05   ; B013 .d .....
        .byte $15,$05,$16,$05,$17,$29,$10,$F0   ; B01B .....)..
        .byte $06,$20,$00,$80,$4C,$18,$B0,$A9   ; B023 . ..L...
        .byte $00,$8D,$01,$20,$60,$AD,$CA,$04   ; B02B ... `...
        .byte $0A,$AA,$BD,$3F,$B0,$48,$BD,$3E   ; B033 ...?.H.>
        .byte $B0,$48,$60,$45,$B0,$7B,$B0,$9A   ; B03B .H`E.{..
        .byte $B0,$B9,$B0,$20,$85,$81,$44,$65   ; B043 ... ..De
        .byte $66,$65,$61,$74,$20,$00,$AD,$EE   ; B04B feat ...
        .byte $04,$D0,$13,$AD,$CB,$04,$20,$02   ; B053 ...... .
        .byte $81,$20,$85,$81,$20,$65,$6E,$65   ; B05B . .. ene
        .byte $6D,$69,$65,$73,$00,$60,$20,$85   ; B063 mies.` .
        .byte $81,$65,$76,$65,$72,$79,$6F,$6E   ; B06B .everyon
        .byte $65,$20,$65,$6C,$73,$65,$21,$00   ; B073 e else!.
        .byte $60,$20,$85,$81,$43,$6F,$6C,$6C   ; B07B ` ..Coll
        .byte $65,$63,$74,$20,$00,$AD,$CB,$04   ; B083 ect ....
        .byte $20,$02,$81,$20,$85,$81,$20,$64   ; B08B  .. .. d
        .byte $6F,$6C,$6C,$61,$72,$73,$00,$60   ; B093 ollars.`
        .byte $20,$85,$81,$53,$75,$72,$76,$69   ; B09B  ..Survi
        .byte $76,$65,$20,$00,$AD,$CB,$04,$20   ; B0A3 ve .... 
        .byte $02,$81,$20,$85,$81,$20,$73,$65   ; B0AB .. .. se
        .byte $63,$6F,$6E,$64,$73,$00,$60,$20   ; B0B3 conds.` 
        .byte $85,$81,$47,$72,$65,$65,$6E,$20   ; B0BB ..Green 
        .byte $74,$6F,$20,$72,$65,$64,$00,$60   ; B0C3 to red.`
        .byte $20,$D0,$80,$A9,$00,$8D,$01,$20   ; B0CB  ...... 
        .byte $20,$3E,$81,$A9,$20,$8D,$06,$20   ; B0D3  >.. .. 
        .byte $A9,$88,$8D,$06,$20,$20,$85,$81   ; B0DB ....  ..
        .byte $44,$6F,$75,$62,$6C,$65,$20,$41   ; B0E3 Double A
        .byte $63,$74,$69,$6F,$6E,$00,$A9,$20   ; B0EB ction.. 
        .byte $8D,$06,$20,$A9,$A9,$8D,$06,$20   ; B0F3 .. .... 
        .byte $20,$85,$81,$42,$6C,$61,$73,$74   ; B0FB  ..Blast
        .byte $65,$72,$20,$47,$75,$79,$73,$00   ; B103 er Guys.
        .byte $A9,$21,$8D,$06,$20,$A9,$02,$8D   ; B10B .!.. ...
        .byte $06,$20,$20,$85,$81,$43,$6F,$6D   ; B113 .  ..Com
        .byte $70,$6C,$65,$74,$65,$20,$74,$68   ; B11B plete th
        .byte $65,$20,$6F,$62,$6A,$65,$63,$74   ; B123 e object
        .byte $69,$76,$65,$73,$20,$66,$6F,$72   ; B12B ives for
        .byte $00,$A9,$21,$8D,$06,$20,$A9,$22   ; B133 ..!.. ."
        .byte $8D,$06,$20,$20,$85,$81,$65,$61   ; B13B ..  ..ea
        .byte $63,$68,$20,$6C,$65,$76,$65,$6C   ; B143 ch level
        .byte $20,$74,$6F,$20,$6D,$6F,$76,$65   ; B14B  to move
        .byte $20,$6F,$6E,$20,$74,$6F,$20,$74   ; B153  on to t
        .byte $68,$65,$00,$A9,$21,$8D,$06,$20   ; B15B he..!.. 
        .byte $A9,$42,$8D,$06,$20,$20,$85,$81   ; B163 .B..  ..
        .byte $6E,$65,$78,$74,$20,$6F,$6E,$65   ; B16B next one
        .byte $2C,$20,$77,$68,$69,$6C,$65,$20   ; B173 , while 
        .byte $61,$76,$6F,$69,$64,$69,$6E,$67   ; B17B avoiding
        .byte $20,$61,$6E,$79,$00,$A9,$21,$8D   ; B183  any..!.
        .byte $06,$20,$A9,$62,$8D,$06,$20,$20   ; B18B . .b..  
        .byte $85,$81,$68,$61,$7A,$61,$72,$64   ; B193 ..hazard
        .byte $73,$20,$6C,$69,$6B,$65,$20,$65   ; B19B s like e
        .byte $6E,$65,$6D,$79,$20,$62,$75,$6C   ; B1A3 nemy bul
        .byte $6C,$65,$74,$73,$2E,$00,$A9,$21   ; B1AB lets...!
        .byte $8D,$06,$20,$A9,$82,$8D,$06,$20   ; B1B3 .. .... 
        .byte $20,$85,$81,$50,$6C,$61,$79,$65   ; B1BB  ..Playe
        .byte $72,$73,$20,$63,$61,$6E,$20,$6A   ; B1C3 rs can j
        .byte $6F,$69,$6E,$20,$69,$6E,$20,$61   ; B1CB oin in a
        .byte $74,$20,$61,$6E,$79,$00,$A9,$21   ; B1D3 t any..!
        .byte $8D,$06,$20,$A9,$A2,$8D,$06,$20   ; B1DB .. .... 
        .byte $20,$85,$81,$74,$69,$6D,$65,$20   ; B1E3  ..time 
        .byte $62,$79,$20,$70,$72,$65,$73,$73   ; B1EB by press
        .byte $69,$6E,$67,$20,$41,$20,$61,$6E   ; B1F3 ing A an
        .byte $64,$20,$42,$2E,$00,$A9,$22,$8D   ; B1FB d B...".
        .byte $06,$20,$A9,$08,$8D,$06,$20,$20   ; B203 . ....  
        .byte $85,$81,$41,$2D,$4A,$75,$6D,$70   ; B20B ..A-Jump
        .byte $00,$A9,$22,$8D,$06,$20,$A9,$28   ; B213 ..".. .(
        .byte $8D,$06,$20,$20,$85,$81,$42,$2D   ; B21B ..  ..B-
        .byte $53,$68,$6F,$6F,$74,$00,$A9,$22   ; B223 Shoot.."
        .byte $8D,$06,$20,$A9,$48,$8D,$06,$20   ; B22B .. .H.. 
        .byte $20,$85,$81,$53,$74,$61,$72,$74   ; B233  ..Start
        .byte $2D,$50,$61,$75,$73,$65,$00,$A9   ; B23B -Pause..
        .byte $22,$8D,$06,$20,$A9,$68,$8D,$06   ; B243 ".. .h..
        .byte $20,$20,$85,$81,$53,$65,$6C,$65   ; B24B   ..Sele
        .byte $63,$74,$2D,$53,$6B,$69,$70,$20   ; B253 ct-Skip 
        .byte $6C,$65,$76,$65,$6C,$00,$A9,$22   ; B25B level.."
        .byte $8D,$06,$20,$A9,$C2,$8D,$06,$20   ; B263 .. .... 
        .byte $20,$85,$81,$50,$72,$65,$73,$73   ; B26B  ..Press
        .byte $20,$61,$6E,$79,$74,$68,$69,$6E   ; B273  anythin
        .byte $67,$20,$74,$6F,$20,$63,$6F,$6E   ; B27B g to con
        .byte $74,$69,$6E,$75,$65,$00,$A9,$00   ; B283 tinue...
        .byte $8D,$05,$20,$8D,$05,$20,$20,$D0   ; B28B .. ..  .
        .byte $80,$A9,$1E,$8D,$01,$20,$20,$65   ; B293 .....  e
        .byte $81,$4C,$B1,$A9,$20,$D0,$80,$A9   ; B29B .L.. ...
        .byte $00,$8D,$01,$20,$20,$3E,$81,$A9   ; B2A3 ...  >..
        .byte $20,$8D,$06,$20,$A9,$88,$8D,$06   ; B2AB  .. ....
        .byte $20,$20,$85,$81,$44,$6F,$75,$62   ; B2B3   ..Doub
        .byte $6C,$65,$20,$41,$63,$74,$69,$6F   ; B2BB le Actio
        .byte $6E,$00,$A9,$20,$8D,$06,$20,$A9   ; B2C3 n.. .. .
        .byte $A9,$8D,$06,$20,$20,$85,$81,$42   ; B2CB ...  ..B
        .byte $6C,$61,$73,$74,$65,$72,$20,$47   ; B2D3 laster G
        .byte $75,$79,$73,$00,$A9,$21,$8D,$06   ; B2DB uys..!..
        .byte $20,$A9,$02,$8D,$06,$20,$20,$85   ; B2E3  ....  .
        .byte $81,$4E,$65,$61,$72,$6C,$79,$20   ; B2EB .Nearly 
        .byte $65,$76,$65,$72,$79,$74,$68,$69   ; B2F3 everythi
        .byte $6E,$67,$00,$A9,$21,$8D,$06,$20   ; B2FB ng..!.. 
        .byte $A9,$23,$8D,$06,$20,$20,$85,$81   ; B303 .#..  ..
        .byte $62,$79,$20,$4E,$6F,$76,$61,$53   ; B30B by NovaS
        .byte $71,$75,$69,$72,$72,$65,$6C,$00   ; B313 quirrel.
        .byte $A9,$21,$8D,$06,$20,$A9,$43,$8D   ; B31B .!.. .C.
        .byte $06,$20,$20,$85,$81,$28,$4E,$6F   ; B323 .  ..(No
        .byte $76,$61,$53,$71,$75,$69,$72,$72   ; B32B vaSquirr
        .byte $65,$6C,$2E,$63,$6F,$6D,$29,$00   ; B333 el.com).
        .byte $A9,$21,$8D,$06,$20,$A9,$82,$8D   ; B33B .!.. ...
        .byte $06,$20,$20,$85,$81,$53,$6F,$75   ; B343 .  ..Sou
        .byte $6E,$64,$20,$61,$6E,$64,$20,$74   ; B34B nd and t
        .byte $72,$69,$67,$20,$63,$6F,$64,$65   ; B353 rig code
        .byte $2C,$20,$73,$6F,$6D,$65,$00,$A9   ; B35B , some..
        .byte $21,$8D,$06,$20,$A9,$A3,$8D,$06   ; B363 !.. ....
        .byte $20,$20,$85,$81,$73,$6F,$75,$6E   ; B36B   ..soun
        .byte $64,$73,$20,$26,$20,$73,$70,$72   ; B373 ds & spr
        .byte $69,$74,$65,$73,$20,$62,$79,$20   ; B37B ites by 
        .byte $54,$65,$70,$70,$6C,$65,$73,$00   ; B383 Tepples.
        .byte $A9,$21,$8D,$06,$20,$A9,$C3,$8D   ; B38B .!.. ...
        .byte $06,$20,$20,$85,$81,$28,$50,$69   ; B393 .  ..(Pi
        .byte $6E,$45,$69,$67,$68,$74,$2E,$63   ; B39B nEight.c
        .byte $6F,$6D,$29,$00,$A9,$22,$8D,$06   ; B3A3 om).."..
        .byte $20,$A9,$02,$8D,$06,$20,$20,$85   ; B3AB  ....  .
        .byte $81,$4D,$75,$73,$69,$63,$20,$69   ; B3B3 .Music i
        .byte $73,$20,$61,$20,$68,$65,$61,$76   ; B3BB s a heav
        .byte $69,$6C,$79,$20,$65,$64,$69,$74   ; B3C3 ily edit
        .byte $65,$64,$00,$A9,$22,$8D,$06,$20   ; B3CB ed..".. 
        .byte $A9,$23,$8D,$06,$20,$20,$85,$81   ; B3D3 .#..  ..
        .byte $76,$65,$72,$73,$69,$6F,$6E,$20   ; B3DB version 
        .byte $6F,$66,$20,$4D,$6F,$72,$6E,$69   ; B3E3 of Morni
        .byte $6E,$67,$20,$4D,$6F,$6F,$64,$00   ; B3EB ng Mood.
        .byte $A9,$23,$8D,$06,$20,$A9,$28,$8D   ; B3F3 .#.. .(.
        .byte $06,$20,$20,$85,$81,$42,$75,$69   ; B3FB .  ..Bui
        .byte $6C,$74,$20,$20,$37,$2F,$32,$2F   ; B403 lt  7/2/
        .byte $32,$30,$31,$36,$00,$A9,$22,$8D   ; B40B 2016..".
        .byte $06,$20,$A9,$A2,$8D,$06,$20,$20   ; B413 . ....  
        .byte $85,$81,$50,$72,$65,$73,$73,$20   ; B41B ..Press 
        .byte $61,$6E,$79,$74,$68,$69,$6E,$67   ; B423 anything
        .byte $20,$74,$6F,$20,$63,$6F,$6E,$74   ; B42B  to cont
        .byte $69,$6E,$75,$65,$00,$A9,$00,$8D   ; B433 inue....
        .byte $05,$20,$8D,$05,$20,$20,$D0,$80   ; B43B . ..  ..
        .byte $A9,$1E,$8D,$01,$20,$20,$65,$81   ; B443 ....  e.
        .byte $4C,$B1,$A9                       ; B44B L..
LB44E:
        lda #$00                                ; B44E
        sta $DB                                 ; B450
        lda #$00                                ; B452
        sta $54                                 ; B454
        sta $55                                 ; B456
        sta $58                                 ; B458
        sta $59                                 ; B45A
LB45C:
        jsr L80D0                               ; B45C
        jsr LC210                               ; B45F
        jsr LB4BF                               ; B462
        jsr LD3CE                               ; B465
        ldx #$00                                ; B468
        stx $0F                                 ; B46A
LB46C:
        jsr LB493                               ; B46C
        bcc LB473                               ; B46F
        inc $0F                                 ; B471
LB473:
        inx                                     ; B473
        cpx #$04                                ; B474
        bne LB46C                               ; B476
        lda $0F                                 ; B478
        cmp #$04                                ; B47A
        bne LB45C                               ; B47C
        lda $04E8                               ; B47E
        bne LB486                               ; B481
        jmp L8DFD                               ; B483
LB486:
        lda $04ED                               ; B486
        beq LB48E                               ; B489
        jmp LB8F8                               ; B48B
LB48E:
        jmp LC31B                               ; B48E
LB491:
        sec                                     ; B491
        rts                                     ; B492
LB493:
        lda $44,x                               ; B493
        beq LB491                               ; B495
        lda $4C,x                               ; B497
        cmp #$08                                ; B499
        bcc LB491                               ; B49B
        lda $50,x                               ; B49D
        sec                                     ; B49F
        sbc $58,x                               ; B4A0
        bcs LB4A6                               ; B4A2
        inc $4C,x                               ; B4A4
LB4A6:
        sta $50,x                               ; B4A6
        lda $58,x                               ; B4A8
        clc                                     ; B4AA
        adc #$20                                ; B4AB
        bcc LB4B1                               ; B4AD
        inc $54,x                               ; B4AF
LB4B1:
        sta $58,x                               ; B4B1
        lda $4C,x                               ; B4B3
        sec                                     ; B4B5
        sbc $54,x                               ; B4B6
        sta $4C,x                               ; B4B8
        jsr L8C14                               ; B4BA
        clc                                     ; B4BD
        rts                                     ; B4BE
LB4BF:
        lda $0340                               ; B4BF
        sec                                     ; B4C2
        sbc #$05                                ; B4C3
        sta $0340                               ; B4C5
        lda $0341                               ; B4C8
        sbc #$00                                ; B4CB
        sta $0341                               ; B4CD
        bmi LB4D3                               ; B4D0
        rts                                     ; B4D2
LB4D3:
        lda #$00                                ; B4D3
        sta $0341                               ; B4D5
        sta $0340                               ; B4D8
        jsr LD554                               ; B4DB
        rts                                     ; B4DE
        .byte $00,$19,$22,$36,$45,$60,$6F,$8A   ; B4DF .."6E`o.
        .byte $9D,$AA,$50,$6C,$61,$79,$65,$72   ; B4E7 ..Player
        .byte $5F,$31,$2C,$20,$50,$6C,$61,$79   ; B4EF _1, Play
        .byte $65,$72,$5F,$32,$2C,$20,$42,$6F   ; B4F7 er_2, Bo
        .byte $74,$68,$00,$4F,$72,$69,$67,$69   ; B4FF th.Origi
        .byte $6E,$61,$6C,$00,$43,$6F,$2D,$6F   ; B507 nal.Co-o
        .byte $70,$2C,$20,$53,$63,$6F,$72,$65   ; B50F p, Score
        .byte $2C,$20,$46,$69,$67,$68,$74,$00   ; B517 , Fight.
        .byte $4E,$6F,$72,$6D,$61,$6C,$2C,$20   ; B51F Normal, 
        .byte $48,$61,$72,$64,$65,$72,$00,$31   ; B527 Harder.1
        .byte $20,$35,$20,$39,$20,$31,$33,$20   ; B52F  5 9 13 
        .byte $31,$37,$20,$32,$31,$20,$32,$35   ; B537 17 21 25
        .byte $20,$32,$39,$20,$42,$6F,$6E,$75   ; B53F  29 Bonu
        .byte $73,$00,$33,$33,$20,$33,$37,$20   ; B547 s.33 37 
        .byte $34,$31,$20,$34,$35,$20,$34,$39   ; B54F 41 45 49
        .byte $00,$33,$20,$39,$20,$31,$34,$20   ; B557 .3 9 14 
        .byte $31,$38,$20,$32,$31,$20,$32,$32   ; B55F 18 21 22
        .byte $20,$32,$37,$20,$33,$30,$20,$45   ; B567  27 30 E
        .byte $64,$69,$74,$00,$4F,$66,$66,$2C   ; B56F dit.Off,
        .byte $20,$4C,$6F,$77,$2C,$20,$50,$6F   ; B577  Low, Po
        .byte $77,$65,$72,$75,$70,$73,$00,$43   ; B57F werups.C
        .byte $61,$6E,$63,$65,$6C,$2C,$20,$45   ; B587 ancel, E
        .byte $78,$69,$74,$00,$53,$61,$6D,$65   ; B58F xit.Same
        .byte $2C,$20,$4E,$65,$77,$2C,$20,$45   ; B597 , New, E
        .byte $78,$69,$74,$00,$00,$01,$01,$02   ; B59F xit.....
        .byte $03,$03,$03,$04,$05,$06,$00,$0F   ; B5A7 ........
        .byte $1F,$31,$44,$55,$66,$57,$68,$6F   ; B5AF .1DUfWho
        .byte $27,$73,$20,$70,$6C,$61,$79,$69   ; B5B7 's playi
        .byte $6E,$67,$3F,$00,$57,$68,$61,$74   ; B5BF ng?.What
        .byte $20,$67,$61,$6D,$65,$20,$6D,$6F   ; B5C7  game mo
        .byte $64,$65,$3F,$00,$57,$68,$69,$63   ; B5CF de?.Whic
        .byte $68,$20,$64,$69,$66,$66,$69,$63   ; B5D7 h diffic
        .byte $75,$6C,$74,$79,$3F,$00,$4C,$65   ; B5DF ulty?.Le
        .byte $76,$65,$6C,$20,$74,$6F,$20,$73   ; B5E7 vel to s
        .byte $74,$61,$72,$74,$20,$61,$74,$3F   ; B5EF tart at?
        .byte $00,$45,$6E,$61,$62,$6C,$65,$20   ; B5F7 .Enable 
        .byte $70,$6F,$77,$65,$72,$75,$70,$73   ; B5FF powerups
        .byte $3F,$00,$45,$78,$69,$74,$20,$74   ; B607 ?.Exit t
        .byte $68,$65,$20,$65,$64,$69,$74,$6F   ; B60F he edito
        .byte $72,$3F,$00,$50,$6C,$61,$79,$20   ; B617 r?.Play 
        .byte $61,$67,$61,$69,$6E,$20,$6F,$6E   ; B61F again on
        .byte $20,$73,$61,$6D,$65,$20,$6C,$65   ; B627  same le
        .byte $76,$65,$6C,$3F,$00,$85,$04,$84   ; B62F vel?....
        .byte $06,$8A,$48,$20,$D0,$80,$A9,$00   ; B637 ..H ....
        .byte $8D,$01,$20,$85,$07,$A9,$80,$8D   ; B63F .. .....
        .byte $00,$20,$A9,$20,$8D,$06,$20,$A9   ; B647 . . .. .
        .byte $84,$8D,$06,$20,$A9,$2D,$8D,$07   ; B64F ... .-..
        .byte $20,$A9,$20,$8D,$07,$20,$BD,$A3   ; B657  . .. ..
        .byte $B5,$AA,$BD,$AD,$B5,$AA,$BD,$B4   ; B65F ........
        .byte $B5,$F0,$06,$8D,$07,$20,$E8,$D0   ; B667 ..... ..
        .byte $F5,$A2,$0A,$20,$C3,$B7,$20,$D0   ; B66F ... .. .
        .byte $80,$A5,$04,$0A,$18,$69,$08,$48   ; B677 .....i.H
        .byte $48,$0A,$0A,$0A,$85,$09,$68,$18   ; B67F H.....h.
        .byte $69,$02,$20,$CC,$B7,$20,$C1,$B7   ; B687 i. .. ..
        .byte $68,$85,$08,$20,$CC,$B7,$68,$AA   ; B68F h.. ..h.
        .byte $BD,$DF,$B4,$AA,$86,$05,$86,$E5   ; B697 ........
        .byte $A0,$01,$BD,$E9,$B4,$F0,$1B,$C9   ; B69F ........
        .byte $20,$D0,$0B,$48,$E8,$8A,$CA,$99   ; B6A7  ..H....
        .byte $E5,$00,$E6,$07,$C8,$68,$C9,$5F   ; B6AF .....h._
        .byte $D0,$02,$A9,$20,$8D,$07,$20,$E8   ; B6B7 ... .. .
        .byte $D0,$E0,$2C,$02,$20,$A9,$00,$8D   ; B6BF ..,. ...
        .byte $05,$20,$8D,$05,$20,$20,$D0,$80   ; B6C7 . ..  ..
        .byte $A9,$1E,$8D,$01,$20,$20,$10,$C2   ; B6CF ....  ..
        .byte $A6,$06,$B5,$E5,$AA,$A4,$DF,$A9   ; B6D7 ........
        .byte $1D,$99,$01,$02,$A9,$23,$99,$02   ; B6DF .....#..
        .byte $02,$8A,$38,$E5,$E5,$0A,$0A,$0A   ; B6E7 ..8.....
        .byte $18,$69,$10,$99,$03,$02,$A5,$09   ; B6EF .i......
        .byte $38,$E9,$01,$99,$00,$02,$C8,$C8   ; B6F7 8.......
        .byte $C8,$C8,$E8,$BD,$E9,$B4,$F0,$0A   ; B6FF ........
        .byte $C9,$20,$F0,$06,$C9,$2C,$F0,$02   ; B707 . ...,..
        .byte $D0,$CD,$20,$00,$80,$A5,$14,$05   ; B70F .. .....
        .byte $15,$05,$16,$05,$17,$85,$14,$A5   ; B717 ........
        .byte $18,$05,$19,$05,$1A,$05,$1B,$85   ; B71F ........
        .byte $18,$A5,$14,$29,$02,$F0,$0E,$A5   ; B727 ...)....
        .byte $18,$29,$02,$D0,$08,$C6,$06,$10   ; B72F .)......
        .byte $04,$A5,$07,$85,$06,$A5,$14,$29   ; B737 .......)
        .byte $01,$F0,$12,$A5,$18,$29,$01,$D0   ; B73F .....)..
        .byte $0C,$E6,$06,$A5,$07,$C5,$06,$B0   ; B747 ........
        .byte $04,$A9,$00,$85,$06,$A5,$14,$29   ; B74F .......)
        .byte $80,$F0,$09,$A5,$18,$29,$80,$D0   ; B757 .....)..
        .byte $03,$4C,$7F,$B7,$A5,$14,$29,$40   ; B75F .L....)@
        .byte $F0,$10,$A5,$18,$29,$40,$D0,$0A   ; B767 ....)@..
        .byte $20,$10,$C2,$A9,$88,$8D,$00,$20   ; B76F  ...... 
        .byte $18,$60,$20,$D0,$80,$4C,$D4,$B6   ; B777 .` ..L..
        .byte $20,$10,$C2,$20,$D0,$80,$A9,$00   ; B77F  .. ....
        .byte $8D,$01,$20,$A5,$08,$20,$CC,$B7   ; B787 .. .. ..
        .byte $A6,$06,$B5,$E5,$AA,$BD,$E9,$B4   ; B78F ........
        .byte $F0,$14,$C9,$20,$F0,$10,$C9,$5F   ; B797 ... ..._
        .byte $D0,$02,$A9,$20,$C9,$2C,$F0,$06   ; B79F ... .,..
        .byte $8D,$07,$20,$E8,$D0,$E7,$20,$C1   ; B7A7 .. ... .
        .byte $B7,$A9,$88,$8D,$00,$20,$A9,$00   ; B7AF ..... ..
        .byte $8D,$05,$20,$8D,$05,$20,$A5,$06   ; B7B7 .. .. ..
        .byte $38,$60,$A2,$20,$A9,$20,$8D,$07   ; B7BF 8`. . ..
        .byte $20,$CA,$D0,$FA,$60,$48,$A9,$08   ; B7C7  ...`H..
        .byte $85,$01,$68,$0A,$0A,$0A,$0A,$26   ; B7CF ..h....&
        .byte $01,$0A,$26,$01,$18,$69,$02,$48   ; B7D7 ..&..i.H
        .byte $A5,$01,$8D,$06,$20,$68,$8D,$06   ; B7DF .... h..
        .byte $20,$60,$20,$D0,$80,$A9,$00,$8D   ; B7E7  ` .....
        .byte $01,$20,$20,$3E,$81,$20,$10,$C2   ; B7EF .  >. ..
        .byte $20,$D0,$80,$A5,$12,$F0,$03,$4C   ; B7F7  ......L
        .byte $9F,$BA,$A5,$45,$0A,$05,$44,$A8   ; B7FF ...E..D.
        .byte $88,$A9,$00,$A2,$00,$20,$34,$B6   ; B807 ..... 4.
        .byte $B0,$03,$4C,$B1,$A9,$48,$18,$69   ; B80F ..L..H.i
        .byte $01,$48,$A9,$00,$85,$44,$85,$45   ; B817 .H...D.E
        .byte $68,$4A,$26,$44,$4A,$26,$45,$68   ; B81F hJ&DJ&Eh
        .byte $C9,$02,$D0,$03,$4C,$83,$B8,$A9   ; B827 ....L...
        .byte $01,$A2,$01,$A0,$00,$20,$34,$B6   ; B82F ..... 4.
        .byte $90,$C1,$A9,$02,$A2,$03,$A4,$DC   ; B837 ........
        .byte $20,$34,$B6,$B0,$0C,$A5,$44,$18   ; B83F  4....D.
        .byte $65,$45,$C9,$02,$D0,$E1,$4C,$83   ; B847 eE....L.
        .byte $B8,$85,$DC,$A9,$03,$8D,$EF,$04   ; B84F ........
        .byte $A2,$04,$A0,$00,$20,$34,$B6,$90   ; B857 .... 4..
        .byte $D9,$C9,$08,$F0,$07,$0A,$0A,$85   ; B85F ........
        .byte $DD,$4C,$C9,$8D,$A9,$03,$8D,$EF   ; B867 .L......
        .byte $04,$A2,$05,$A0,$00,$20,$34,$B6   ; B86F ..... 4.
        .byte $90,$D9,$0A,$0A,$18,$69,$20,$85   ; B877 .....i .
        .byte $DD,$4C,$C9,$8D,$A9,$01,$A2,$02   ; B87F .L......
        .byte $A0,$00,$8C,$CE,$03,$8C,$CF,$03   ; B887 ........
        .byte $8C,$D0,$03,$8C,$ED,$04,$8C,$EE   ; B88F ........
        .byte $04,$20,$34,$B6,$B0,$03,$4C,$FA   ; B897 . 4...L.
        .byte $B7,$F0,$97,$C9,$02,$F0,$22,$A9   ; B89F ......".
        .byte $02,$8D,$ED,$04,$A2,$07,$A0,$00   ; B8A7 ........
        .byte $20,$34,$B6,$90,$CF,$8D,$F1,$04   ; B8AF  4......
        .byte $A9,$03,$8D,$EF,$04,$A2,$06,$A0   ; B8B7 ........
        .byte $00,$20,$34,$B6,$90,$E1,$4C,$E0   ; B8BF . 4...L.
        .byte $B8,$A9,$02,$8D,$EE,$04,$A2,$07   ; B8C7 ........
        .byte $A0,$02,$20,$34,$B6,$90,$AD,$8D   ; B8CF .. 4....
        .byte $F1,$04,$A9,$00,$85,$DD,$4C,$C9   ; B8D7 ......L.
        .byte $8D,$C9,$08,$D0,$03,$4C,$F9,$C2   ; B8DF .....L..
        .byte $AA,$BD,$F0,$B8,$85,$DD,$4C,$C9   ; B8E7 ......L.
        .byte $8D,$02,$08,$0D,$11,$14,$15,$1A   ; B8EF ........
        .byte $1D                               ; B8F7 .
LB8F8:
        jsr LD33B                               ; B8F8
        jsr L80D0                               ; B8FB
        lda #$00                                ; B8FE
        sta PPUMASK                             ; B900
        jsr L813E                               ; B903
        lda $12                                 ; B906
        beq LB90D                               ; B908
        jmp LB95F                               ; B90A
LB90D:
        lda #$32                                ; B90D
        sta $0A                                 ; B90F
        ldx #$00                                ; B911
LB913:
        lda $0367,x                             ; B913
        cmp $036C,x                             ; B916
        bne LB937                               ; B919
        inx                                     ; B91B
        cpx #$05                                ; B91C
        bne LB913                               ; B91E
        lda #$21                                ; B920
        sta PPUADDR                             ; B922
        lda #$C8                                ; B925
        sta PPUADDR                             ; B927
        jsr L8185                               ; B92A
        lsr $424F                               ; B92D
        .byte $4F,$44,$59,$00,$4C,$55,$B9       ; B930 ODY.LU.
LB937:
        bcc LB93B                               ; B937
        dec $0A                                 ; B939
LB93B:
        lda #$21                                ; B93B
        sta PPUADDR                             ; B93D
        lda #$C8                                ; B940
        sta PPUADDR                             ; B942
        jsr L8185                               ; B945
        bvc LB996                               ; B948
        eor ($59,x)                             ; B94A
        eor $52                                 ; B94C
        jsr LA500                               ; B94E
        asl                                     ; B951
        sta PPUDATA                             ; B952
        jsr L8185                               ; B955
        jsr $4957                               ; B958
        lsr $2153                               ; B95B
        brk                                     ; B95E
LB95F:
        lda #$22                                ; B95F
        sta PPUADDR                             ; B961
        lda #$05                                ; B964
        sta PPUADDR                             ; B966
        jsr L8185                               ; B969
        .byte $53,$63,$6F,$72,$65,$73,$3A,$20   ; B96C Scores: 
        .byte $00,$A2,$04,$BD,$67,$03,$8D,$07   ; B974 ....g...
        .byte $20,$CA,$10,$F7,$A9,$22,$8D,$06   ; B97C  ...."..
        .byte $20,$A9,$2D,$8D,$06,$20,$A2,$09   ; B984  .-.. ..
        .byte $BD,$67,$03,$8D,$07,$20,$CA,$E0   ; B98C .g... ..
        .byte $05,$10                           ; B994 ..
LB996:
        sbc $A5,x                               ; B996
        .byte $12,$F0,$2E,$A9,$22,$8D,$06,$20   ; B998 ....".. 
        .byte $A9,$4D,$8D,$06,$20,$A2,$0E,$BD   ; B9A0 .M.. ...
        .byte $67,$03,$8D,$07,$20,$CA,$E0,$0A   ; B9A8 g... ...
        .byte $10,$F5,$A9,$22,$8D,$06,$20,$A9   ; B9B0 ...".. .
        .byte $6D,$8D,$06,$20,$A2,$13,$BD,$67   ; B9B8 m.. ...g
        .byte $03,$8D,$07,$20,$CA,$E0,$0F,$10   ; B9C0 ... ....
        .byte $F5,$AD,$E8,$04,$F0,$19,$A9,$00   ; B9C8 ........
        .byte $8D,$05,$20,$8D,$05,$20,$20,$3B   ; B9D0 .. ..  .
        .byte $D3,$20,$D0,$80,$A9,$1E,$8D,$01   ; B9D8 . ......
        .byte $20,$20,$65,$81,$4C,$1B,$C3,$A9   ; B9E0   e.L...
        .byte $00,$A2,$09,$A0,$00,$20,$34,$B6   ; B9E8 ..... 4.
        .byte $B0,$03,$4C,$B1,$A9,$C9,$02,$D0   ; B9F0 ..L.....
        .byte $03,$4C,$B1,$A9,$C9,$01,$F0,$08   ; B9F8 .L......
        .byte $EE,$EF,$04,$C6,$DD,$4C,$C9,$8D   ; BA00 .....L..
        .byte $A9,$01,$8D,$EF,$04,$A2,$06,$A0   ; BA08 ........
        .byte $00,$20,$34,$B6,$90,$D1,$4C,$E0   ; BA10 . 4...L.
        .byte $B8                               ; BA18 .
LBA19:
        jsr LD33B                               ; BA19
        jsr L80D0                               ; BA1C
        lda #$00                                ; BA1F
        sta PPUMASK                             ; BA21
        jsr L813E                               ; BA24
        ldy #$31                                ; BA27
        ldx #$00                                ; BA29
LBA2B:
        lda $44,x                               ; BA2B
        bne LBA33                               ; BA2D
        inx                                     ; BA2F
        iny                                     ; BA30
        bne LBA2B                               ; BA31
LBA33:
        sty $0A                                 ; BA33
        lda #$21                                ; BA35
        sta PPUADDR                             ; BA37
        lda #$88                                ; BA3A
        sta PPUADDR                             ; BA3C
        jsr L8185                               ; BA3F
        bvc LBA90                               ; BA42
        eor ($59,x)                             ; BA44
        eor $52                                 ; BA46
        jsr LA500                               ; BA48
        asl                                     ; BA4B
        sta PPUDATA                             ; BA4C
        jsr L8185                               ; BA4F
        jsr $4957                               ; BA52
        lsr $2153                               ; BA55
        brk                                     ; BA58
        .byte $A9,$22,$8D,$06,$20,$A9,$02,$8D   ; BA59 .".. ...
        .byte $06,$20,$20,$85,$81,$50,$72,$65   ; BA61 .  ..Pre
        .byte $73,$73,$20,$61,$6E,$79,$74,$68   ; BA69 ss anyth
        .byte $69,$6E,$67,$20,$74,$6F,$20,$63   ; BA71 ing to c
        .byte $6F,$6E,$74,$69,$6E,$75,$65,$00   ; BA79 ontinue.
        .byte $A9,$00,$8D,$05,$20,$8D,$05,$20   ; BA81 .... .. 
        .byte $20,$D0,$80,$A9,$1E,$8D,$01       ; BA89  ......
LBA90:
        jsr $1EA2                               ; BA90
LBA93:
        jsr L80D0                               ; BA93
        dex                                     ; BA96
        bne LBA93                               ; BA97
        jsr L8165                               ; BA99
        jmp LA9B1                               ; BA9C
        .byte $AD,$F5,$04,$0D,$F6,$04,$0D,$F7   ; BA9F ........
        .byte $04,$0D,$F8,$04,$F0,$0C,$A2,$03   ; BAA7 ........
        .byte $BD,$F5,$04,$15,$44,$95,$44,$CA   ; BAAF ....D.D.
        .byte $10,$F6,$20,$D0,$80,$A9,$00,$8D   ; BAB7 .. .....
        .byte $01,$20,$20,$3E,$81,$A9,$21,$8D   ; BABF .  >..!.
        .byte $06,$20,$A9,$07,$8D,$06,$20,$20   ; BAC7 . ....  
        .byte $85,$81,$57,$68,$6F,$20,$77,$61   ; BACF ..Who wa
        .byte $6E,$74,$73,$20,$74,$6F,$20,$70   ; BAD7 nts to p
        .byte $6C,$61,$79,$3F,$00,$A9,$21,$8D   ; BADF lay?..!.
        .byte $06,$20,$A9,$47,$8D,$06,$20,$20   ; BAE7 . .G..  
        .byte $85,$81,$41,$3A,$4A,$6F,$69,$6E   ; BAEF ..A:Join
        .byte $20,$69,$6E,$2C,$20,$42,$3A,$4C   ; BAF7  in, B:L
        .byte $65,$61,$76,$65,$00,$A9,$21,$8D   ; BAFF eave..!.
        .byte $06,$20,$A9,$85,$8D,$06,$20,$20   ; BB07 . ....  
        .byte $85,$81,$50,$72,$65,$73,$73,$20   ; BB0F ..Press 
        .byte $53,$74,$61,$72,$74,$20,$77,$68   ; BB17 Start wh
        .byte $65,$6E,$20,$72,$65,$61,$64,$79   ; BB1F en ready
        .byte $00,$20,$00,$80,$A5,$14,$05,$15   ; BB27 . ......
        .byte $05,$16,$05,$17,$D0,$F3,$20,$D0   ; BB2F ...... .
        .byte $80,$A9,$22,$8D,$06,$20,$A9,$0A   ; BB37 ..".. ..
        .byte $8D,$06,$20,$20,$85,$81,$50,$6C   ; BB3F ..  ..Pl
        .byte $61,$79,$65,$72,$73,$3A,$20,$00   ; BB47 ayers: .
        .byte $20,$C9,$BB,$A9,$00,$8D,$05,$20   ; BB4F  ...... 
        .byte $8D,$05,$20,$A9,$1E,$8D,$01,$20   ; BB57 .. .... 
        .byte $20,$00,$80,$A2,$03,$B5,$14,$29   ; BB5F  ......)
        .byte $80,$F0,$04,$A9,$01,$95,$44,$B5   ; BB67 ......D.
        .byte $14,$29,$40,$F0,$02,$56,$44,$B5   ; BB6F .)@..VD.
        .byte $44,$9D,$F5,$04,$CA,$10,$E6,$A5   ; BB77 D.......
        .byte $14,$05,$15,$05,$16,$05,$17,$29   ; BB7F .......)
        .byte $10,$D0,$03,$4C,$35,$BB,$20,$D0   ; BB87 ...L5. .
        .byte $80,$A9,$00,$8D,$01,$20,$20,$3E   ; BB8F .....  >
        .byte $81,$A9,$21,$8D,$06,$20,$A9,$02   ; BB97 ..!.. ..
        .byte $8D,$06,$20,$20,$C9,$BB,$A9,$00   ; BB9F ..  ....
        .byte $8D,$05,$20,$8D,$05,$20,$A5,$44   ; BBA7 .. .. .D
        .byte $18,$65,$45,$18,$65,$46,$18,$65   ; BBAF .eE.eF.e
        .byte $47,$85,$00,$D0,$03,$4C,$B1,$A9   ; BBB7 G....L..
        .byte $C9,$01,$D0,$03,$4C,$2E,$B8,$4C   ; BBBF ....L..L
        .byte $83,$B8,$A2,$00,$A0,$31,$B5,$44   ; BBC7 .....1.D
        .byte $D0,$07,$A9,$20,$8D,$07,$20,$D0   ; BBCF ... .. .
        .byte $03,$8C,$07,$20,$C8,$E8,$E0,$04   ; BBD7 ... ....
        .byte $D0,$EC,$60,$10,$42,$01,$01,$01   ; BBDF ..`.B...
        .byte $01,$00,$00,$1C,$01,$01,$01,$02   ; BBE7 ........
        .byte $02,$00,$00,$24,$02,$01,$01,$02   ; BBEF ...$....
        .byte $03,$00,$00,$3A,$03,$01,$02,$02   ; BBF7 ...:....
        .byte $03,$00,$00,$1D,$02,$02,$02,$01   ; BBFF ........
        .byte $01,$82,$BE,$18,$02,$06,$06,$02   ; BC07 ........
        .byte $02,$00,$00,$1D,$02,$08,$08,$03   ; BC0F ........
        .byte $01,$00,$00,$24,$06,$05,$01,$01   ; BC17 ...$....
        .byte $01,$65,$BE,$24,$03,$08,$08,$03   ; BC1F .e.$....
        .byte $03,$9D,$BE,$15,$04,$09,$02,$02   ; BC27 ........
        .byte $02,$B9,$BE,$10,$04,$01,$05,$05   ; BC2F ........
        .byte $05,$65,$BE,$1C,$01,$08,$08,$03   ; BC37 .e......
        .byte $06,$11,$BF,$03,$02,$03,$03,$02   ; BC3F ........
        .byte $02,$31,$BF,$24,$0A,$09,$09,$0A   ; BC47 .1.$....
        .byte $0A,$8F,$BF,$24,$02,$0E,$07,$0C   ; BC4F ...$....
        .byte $01,$00,$00,$19,$02,$0A,$02,$0A   ; BC57 ........
        .byte $01,$11,$BF,$18,$05,$02,$02,$02   ; BC5F ........
        .byte $02,$7C,$BF,$24,$02,$09,$09,$0A   ; BC67 .|.$....
        .byte $0A,$7C,$BF,$11,$02,$0F,$0F,$08   ; BC6F .|......
        .byte $08,$00,$00,$03,$02,$0E,$0E,$0F   ; BC77 ........
        .byte $0F,$31,$BF,$24,$04,$0B,$0B,$0B   ; BC7F .1.$....
        .byte $0B,$00,$00,$20,$04,$03,$0C,$03   ; BC87 ... ....
        .byte $09,$E1,$BE,$20,$07,$01,$01,$01   ; BC8F ... ....
        .byte $01,$7C,$BF,$15,$02,$0D,$0D,$03   ; BC97 .|......
        .byte $0E,$00,$00,$19,$04,$0A,$0A,$0A   ; BC9F ........
        .byte $0A,$69,$BF,$10,$04,$0C,$0C,$0D   ; BCA7 .i......
        .byte $0B,$A2,$BF,$1C,$02,$0B,$0B,$06   ; BCAF ........
        .byte $06,$82,$BE,$44,$05,$0A,$0A,$0A   ; BCB7 ...D....
        .byte $0A,$8F,$BF,$03,$04,$0C,$0C,$04   ; BCBF ........
        .byte $04,$A2,$BF,$2C,$07,$0C,$0C,$0C   ; BCC7 ...,....
        .byte $0C,$A2,$BF,$11,$07,$0A,$0A,$0A   ; BCCF ........
        .byte $0A,$11,$BF,$00,$00,$11,$11,$11   ; BCD7 ........
        .byte $11,$E3,$BF,$10,$0A,$14,$14,$01   ; BCDF ........
        .byte $01,$00,$00,$18,$0A,$12,$12,$09   ; BCE7 ........
        .byte $09,$00,$00,$10,$02,$14,$14,$14   ; BCEF ........
        .byte $14,$75,$C0,$11,$02,$01,$01,$02   ; BCF7 .u......
        .byte $02,$A7,$C0,$20,$02,$0C,$0C,$01   ; BCFF ... ....
        .byte $01,$8F,$C0,$28,$04,$16,$16,$16   ; BD07 ...(....
        .byte $16,$00,$00,$19,$05,$07,$07,$03   ; BD0F ........
        .byte $03,$29,$C0,$18,$03,$0B,$0B,$0D   ; BD17 .)......
        .byte $0D,$0F,$C0,$24,$12,$15,$15,$03   ; BD1F ...$....
        .byte $03,$E7,$BF,$19,$12,$13,$13,$02   ; BD27 ........
        .byte $02,$82,$BE,$03,$22,$1A,$1A,$1A   ; BD2F ...."...
        .byte $1A,$31,$BF,$03,$05,$12,$12,$12   ; BD37 .1......
        .byte $12,$A2,$BF,$18,$04,$13,$13,$17   ; BD3F ........
        .byte $17,$C5,$C0,$10,$14,$18,$18,$0F   ; BD47 ........
        .byte $0F,$FB,$BF,$24,$05,$13,$13,$13   ; BD4F ...$....
        .byte $13,$29,$C0,$18,$05,$15,$15,$15   ; BD57 .)......
        .byte $15,$11,$BF,$15,$04,$15,$15,$06   ; BD5F ........
        .byte $06,$43,$C0,$18,$02,$18,$18,$18   ; BD67 .C......
        .byte $18,$FB,$BF,$2C,$02,$0B,$0B,$19   ; BD6F ...,....
        .byte $19,$5B,$C0,$04,$21,$11,$11,$11   ; BD77 .[..!...
        .byte $11,$E3,$BF                       ; BD7F ...
LBD82:
        ldy $04E8                               ; BD82
        bne LBDA9                               ; BD85
        pha                                     ; BD87
        lda #$00                                ; BD88
        sta $01                                 ; BD8A
        pla                                     ; BD8C
        asl                                     ; BD8D
        asl                                     ; BD8E
        asl                                     ; BD8F
        rol $01                                 ; BD90
        clc                                     ; BD92
        adc #$E2                                ; BD93
        sta $00                                 ; BD95
        lda $01                                 ; BD97
        adc #$BB                                ; BD99
        sta $01                                 ; BD9B
        ldy #$00                                ; BD9D
LBD9F:
        lda ($00),y                             ; BD9F
        sta $04E0,y                             ; BDA1
        iny                                     ; BDA4
        cpy #$08                                ; BDA5
        bne LBD9F                               ; BDA7
LBDA9:
        lda $04E0                               ; BDA9
        pha                                     ; BDAC
        lsr                                     ; BDAD
        lsr                                     ; BDAE
        sta $04CB                               ; BDAF
        inc $04CB                               ; BDB2
        lda $04ED                               ; BDB5
        beq LBDC5                               ; BDB8
        lda $04CB                               ; BDBA
        asl                                     ; BDBD
        clc                                     ; BDBE
        adc $04CB                               ; BDBF
        sta $04CB                               ; BDC2
LBDC5:
        pla                                     ; BDC5
        and #$03                                ; BDC6
        sta $04CA                               ; BDC8
        lda $04E2                               ; BDCB
        sta $00                                 ; BDCE
        lda $04E3                               ; BDD0
        sta $01                                 ; BDD3
        lda $04E4                               ; BDD5
        sta $02                                 ; BDD8
        lda $04E5                               ; BDDA
        sta $03                                 ; BDDD
        lda $04E1                               ; BDDF
        pha                                     ; BDE2
        and #$07                                ; BDE3
        sta $04DD                               ; BDE5
        inc $04DD                               ; BDE8
        pla                                     ; BDEB
        ldx #$00                                ; BDEC
        ldy #$00                                ; BDEE
        and #$08                                ; BDF0
        tax                                     ; BDF2
LBDF3:
        lda LBE2F,x                             ; BDF3
        sty $04                                 ; BDF6
        tay                                     ; BDF8
        lda a:$0000,y                           ; BDF9
        ldy $04                                 ; BDFC
        sta $04CC,y                             ; BDFE
        inx                                     ; BE01
        iny                                     ; BE02
        cpy #$10                                ; BE03
        bne LBDF3                               ; BE05
        lda $04E1                               ; BE07
        and #$F0                                ; BE0A
        cmp #$40                                ; BE0C
        bne LBE14                               ; BE0E
        inc $04F0                               ; BE10
        rts                                     ; BE13
LBE14:
        cmp #$10                                ; BE14
        bne LBE1C                               ; BE16
        lda #$01                                ; BE18
        sta $42                                 ; BE1A
LBE1C:
        cmp #$20                                ; BE1C
        bne LBE25                               ; BE1E
        lda #$02                                ; BE20
        sta $42                                 ; BE22
        rts                                     ; BE24
LBE25:
        cmp #$30                                ; BE25
        bne LBE2E                               ; BE27
        lda #$03                                ; BE29
        sta $42                                 ; BE2B
        rts                                     ; BE2D
LBE2E:
        rts                                     ; BE2E
LBE2F:
        .byte $00,$00,$00,$00,$01,$01,$01,$01   ; BE2F ........
        .byte $02,$02,$02,$02,$03,$03,$03,$03   ; BE37 ........
        .byte $00,$00,$00,$00,$00,$01,$01,$01   ; BE3F ........
        .byte $01,$01,$02,$02,$02,$03,$03,$03   ; BE47 ........
LBE4F:
        .byte $00,$01,$02,$03,$15,$04,$17,$09   ; BE4F ........
        .byte $0A,$1A,$0B,$1B,$10,$11,$12,$13   ; BE57 ........
        .byte $0C,$0D,$0E,$0F,$19,$14,$A0,$D4   ; BE5F ........
        .byte $4F,$A1,$3D,$A1,$03,$AE,$03,$B2   ; BE67 O.=.....
        .byte $3B,$B2,$03,$BD,$03,$C3,$39,$C3   ; BE6F ......9.
        .byte $03,$CC,$03,$D4,$37,$D4,$03,$DB   ; BE77 ....7...
        .byte $03,$D7,$00,$B1,$D4,$33,$A1,$20   ; BE7F .....3. 
        .byte $91,$01,$EB,$23,$DC,$02,$D7,$04   ; BE87 ...#....
        .byte $B9,$04,$BA,$62,$87,$04,$84,$62   ; BE8F ...b...b
        .byte $56,$62,$59,$04,$A3,$00,$E1,$24   ; BE97 VbY....$
        .byte $E8,$23,$ED,$21,$C5,$63,$A0,$63   ; BE9F .#.!.c.c
        .byte $90,$20,$80,$01,$83,$21,$45,$94   ; BEA7 . ...!E.
        .byte $46,$64,$97,$63,$6A,$62,$DE,$01   ; BEAF Fd.cjb..
        .byte $D2,$00,$E1,$2C,$A0,$64,$A6,$63   ; BEB7 ...,.d.c
        .byte $C7,$61,$CA,$61,$D7,$01,$D8,$01   ; BEBF .a.a....
        .byte $D9,$01,$DA,$01,$D2,$01,$AE,$61   ; BEC7 .......a
        .byte $8A,$61,$85,$63,$75,$03,$74,$20   ; BECF .a.cu.t 
        .byte $71,$62,$54,$61,$57,$62,$78,$05   ; BED7 qbTaWbx.
        .byte $92,$00,$E1,$23,$D4,$02,$E7,$22   ; BEDF ...#..."
        .byte $C9,$91,$CA,$61,$CC,$91,$EC,$22   ; BEE7 ...a..."
        .byte $BA,$02,$93,$64,$83,$D1,$04,$71   ; BEEF ...d...q
        .byte $66,$62,$D3,$02,$63,$04,$68,$60   ; BEF7 fb..c.h`
        .byte $59,$61,$8A,$62,$7B,$02,$43,$61   ; BEFF Ya.b{.Ca
        .byte $20,$62,$24,$62,$2A,$62,$1B,$02   ; BF07  b$b*b..
        .byte $D2,$00,$E2,$26,$73,$68,$63,$02   ; BF0F ...&shc.
        .byte $64,$30,$B4,$60,$A4,$02,$9F,$04   ; BF17 d0.`....
        .byte $9D,$60,$8C,$04,$8D,$05,$AE,$60   ; BF1F .`.....`
        .byte $BD,$60,$CC,$60,$CB,$05,$D9,$62   ; BF27 .`.`...b
        .byte $D4,$00,$E1,$60,$E2,$D1,$0C,$E6   ; BF2F ...`....
        .byte $04,$D6,$02,$93,$D7,$29,$83,$69   ; BF37 .....).i
        .byte $4C,$60,$5C,$D7,$20,$55,$D7,$05   ; BF3F L`.. U..
        .byte $52,$D7,$60,$53,$07,$73,$07,$6C   ; BF47 R.`S.s.l
        .byte $60,$76,$A5,$C3,$62,$A3,$62,$C7   ; BF4F `v..b.b.
        .byte $65,$A7,$65,$63,$67,$43,$67,$44   ; BF57 e.ecgCgD
        .byte $94,$34,$D7,$05,$36,$01,$3A,$01   ; BF5F .4..6.:.
        .byte $B4,$00,$E0,$2A,$29,$D7,$A0,$A2   ; BF67 ...*)...
        .byte $6A,$76,$66,$46,$68,$56,$D6,$20   ; BF6F jvfFhV. 
        .byte $8C,$D6,$20,$84,$00,$20,$99,$81   ; BF77 .. .. ..
        .byte $61,$83,$21,$D1,$D4,$1B,$29,$D4   ; BF7F a.!...).
        .byte $96,$B8,$D4,$15,$C1,$02,$C4,$00   ; BF87 ........
        .byte $E3,$2B,$8E,$96,$88,$26,$38,$95   ; BF8F .+...&8.
        .byte $38,$26,$28,$D1,$06,$D5,$02,$B4   ; BF97 8&(.....
        .byte $62,$D3,$00,$E1,$2D,$D1,$D7,$0C   ; BF9F b...-...
        .byte $B2,$27,$B4,$62,$90,$20,$BC,$22   ; BFA7 .'.b. ."
        .byte $AF,$20,$CE,$92,$9D,$60,$83,$21   ; BFAF . ...`.!
        .byte $87,$26,$63,$91,$52,$90,$D5,$02   ; BFB7 .&c.R...
        .byte $55,$60,$56,$21,$5A,$22,$5C,$92   ; BFBF U`V!Z"..
        .byte $36,$91,$35,$D3,$10,$3A,$91,$29   ; BFC7 6.5..:.)
        .byte $90,$26,$60,$28,$D7,$50,$76,$D7   ; BFCF .&`(.Pv.
        .byte $04,$76,$D7,$30,$A3,$D7,$0B,$BB   ; BFD7 .v.0....
        .byte $D7,$10,$D3,$00,$E1,$2D,$D4,$00   ; BFDF .....-..
        .byte $E0,$2C,$D3,$02,$D4,$26,$C4,$23   ; BFE7 .,...&.#
        .byte $B6,$02,$AA,$62,$9B,$02,$9D,$62   ; BFEF ...b...b
        .byte $8F,$02,$B4,$00,$E0,$D1,$0F,$51   ; BFF7 .......Q
        .byte $99,$93,$95,$25,$9C,$54,$20,$86   ; BFFF ...%.T .
        .byte $20,$B7,$23,$8B,$D4,$63,$7C,$00   ; C007  .#..c|.
        .byte $EA,$DF,$04,$B0,$2C,$80,$93,$71   ; C00F ....,..q
        .byte $DF,$05,$57,$92,$57,$25,$4C,$20   ; C017 ..W.W%L 
        .byte $4C,$0D,$A4,$0C,$A7,$0E,$AA,$02   ; C01F L.......
        .byte $A8,$00,$C2,$D9,$22,$95,$D9,$22   ; C027 ....".."
        .byte $68,$D9,$22,$3B,$D9,$22,$CB,$D8   ; C02F h.".."..
        .byte $22,$98,$D8,$22,$65,$D8,$22,$32   ; C037 ".."e."2
        .byte $D8,$22,$B3,$00,$E2,$22,$C7,$92   ; C03F ."..."..
        .byte $B7,$02,$B9,$D4,$22,$7C,$94,$72   ; C047 ...."|.r
        .byte $D4,$32,$D3,$0D,$63,$0D,$AB,$0D   ; C04F .2..c...
        .byte $75,$10,$D4,$00,$E2,$25,$C3,$D4   ; C057 u....%..
        .byte $33,$E8,$D2,$06,$C7,$57,$B8,$D3   ; C05F 3....W..
        .byte $05,$A9,$D3,$03,$B9,$53,$AA,$51   ; C067 .....S.Q
        .byte $2E,$40,$37,$47,$B3,$00,$E0,$23   ; C06F .@7G...#
        .byte $B0,$93,$D2,$02,$D8,$DF,$07,$E8   ; C077 ........
        .byte $27,$8D,$D4,$62,$B2,$65,$A5,$02   ; C07F '..b.e..
        .byte $84,$62,$87,$92,$88,$10,$D3,$00   ; C087 .b......
        .byte $E1,$43,$EB,$53,$D4,$02,$DB,$02   ; C08F .C.S....
        .byte $C5,$D9,$22,$C8,$D8,$22,$B4,$72   ; C097 .."..".r
        .byte $B9,$82,$93,$74,$98,$84,$D4,$00   ; C09F ...t....
        .byte $D1,$D4,$17,$C4,$02,$B6,$D4,$12   ; C0A7 ........
        .byte $A7,$21,$A6,$14,$A2,$81,$81,$83   ; C0AF .!......
        .byte $67,$14,$98,$02,$9B,$D4,$12,$8B   ; C0B7 g.......
        .byte $D1,$02,$6A,$73,$C2,$00,$E2,$2C   ; C0BF ..js...,
        .byte $D6,$02,$BE,$92,$CD,$91,$DC,$90   ; C0C7 ........
        .byte $B5,$62,$A5,$02,$9A,$62,$79,$91   ; C0CF .b...by.
        .byte $76,$62,$48,$92,$49,$62,$D4,$00   ; C0D7 vbH.Ib..
        .byte $E2,$2B,$D2,$01,$DD,$01,$62,$96   ; C0DF .+....b.
        .byte $63,$90,$6D,$96,$6C,$90,$84,$77   ; C0E7 c.m.l..w
        .byte $C6,$83,$D4,$00,$E2,$2B,$D5,$02   ; C0EF .....+..
        .byte $B5,$D4,$22,$AB,$D4,$32,$E8,$D1   ; C0F7 .."..2..
        .byte $02,$9C,$02,$81,$22,$52,$63,$56   ; C0FF ...."RcV
        .byte $72,$D4,$00,$E1,$2D,$D1,$D1,$0D   ; C107 r...-...
        .byte $E8,$D1,$03,$D8,$63,$B1,$74,$B7   ; C10F ....c.t.
        .byte $83,$A0,$84,$96,$74,$82,$83,$86   ; C117 ....t...
        .byte $83,$74,$73,$6A,$73,$57,$83,$44   ; C11F .tsjsW.D
        .byte $73,$C8,$00                       ; C127 s..
LC12A:
        lda $04E6                               ; C12A
        sta $06                                 ; C12D
        lda $04E7                               ; C12F
        sta $07                                 ; C132
        lda #$01                                ; C134
        sta $04EB                               ; C136
        ldy #$00                                ; C139
LC13B:
        lda ($06),y                             ; C13B
        sta $00                                 ; C13D
        iny                                     ; C13F
        lda ($06),y                             ; C140
        bne LC155                               ; C142
        lda $00                                 ; C144
        pha                                     ; C146
        and #$0F                                ; C147
        sta $04E9                               ; C149
        pla                                     ; C14C
        lsr                                     ; C14D
        lsr                                     ; C14E
        lsr                                     ; C14F
        lsr                                     ; C150
        sta $04EA                               ; C151
        rts                                     ; C154
LC155:
        iny                                     ; C155
        pha                                     ; C156
        and #$0F                                ; C157
        sta $01                                 ; C159
        tax                                     ; C15B
        lda LBE4F,x                             ; C15C
        sta $08                                 ; C15F
        pla                                     ; C161
        and #$F0                                ; C162
        lsr                                     ; C164
        lsr                                     ; C165
        lsr                                     ; C166
        sty $02                                 ; C167
        jsr LC171                               ; C169
        ldy $02                                 ; C16C
        jmp LC13B                               ; C16E
LC171:
        tax                                     ; C171
        lsr                                     ; C172
        sta $03                                 ; C173
        lda LC183,x                             ; C175
        pha                                     ; C178
        lda LC182,x                             ; C179
        pha                                     ; C17C
        lda $03                                 ; C17D
        ldx $00                                 ; C17F
        rts                                     ; C181
LC182:
        .byte $9D                               ; C182 .
LC183:
        .byte $C1,$A3,$C1,$B0,$C1,$B0,$C1,$B0   ; C183 ........
        .byte $C1,$B0,$C1,$B0,$C1,$B0,$C1,$B0   ; C18B ........
        .byte $C1,$C2,$C1,$C2,$C1,$C2,$C1,$C2   ; C193 ........
        .byte $C1,$DA,$C1,$A5,$08,$9D,$00,$07   ; C19B ........
        .byte $60,$84,$E1,$A4,$01,$B9,$5F,$BE   ; C1A3 `....._.
        .byte $A4,$E1,$9D,$00,$07,$60,$38,$E9   ; C1AB .....`8.
        .byte $02,$A8,$B9,$09,$C2,$A4,$01,$C8   ; C1B3 ........
        .byte $9D,$00,$07,$E8,$88,$D0,$F9,$60   ; C1BB .......`
        .byte $38,$E9,$09,$A8,$B9,$09,$C2,$A4   ; C1C3 8.......
        .byte $01,$C8,$9D,$00,$07,$48,$8A,$38   ; C1CB .....H.8
        .byte $E9,$F0,$AA,$68,$88,$D0,$F3,$60   ; C1D3 ...h...`
        .byte $E6,$02,$B1,$06,$48,$29,$0F,$85   ; C1DB ....H)..
        .byte $04,$68,$4A,$4A,$4A,$4A,$85,$05   ; C1E3 .hJJJJ..
        .byte $E6,$04,$E6,$05,$A4,$04,$A5,$08   ; C1EB ........
        .byte $86,$00,$9D,$00,$07,$E8,$88,$D0   ; C1F3 ........
        .byte $F9,$A5,$00,$A6,$00,$38,$E9,$F0   ; C1FB .....8..
        .byte $AA,$C6,$05,$D0,$E7,$60,$15,$00   ; C203 .....`..
        .byte $0A,$1A,$17,$0B,$1B               ; C20B .....
LC210:
        lda #$F0                                ; C210
        ldx #$00                                ; C212
LC214:
        sta $0200,x                             ; C214
        inx                                     ; C217
        inx                                     ; C218
        inx                                     ; C219
        inx                                     ; C21A
        bne LC214                               ; C21B
        rts                                     ; C21D
LC21E:
        jsr LC229                               ; C21E
        jsr LC23C                               ; C221
        lda $1C                                 ; C224
        eor $1E                                 ; C226
        rts                                     ; C228
LC229:
        lda $1D                                 ; C229
        asl                                     ; C22B
        asl                                     ; C22C
        eor $1D                                 ; C22D
        asl                                     ; C22F
        eor $1D                                 ; C230
        asl                                     ; C232
        asl                                     ; C233
        eor $1D                                 ; C234
        asl                                     ; C236
        rol $1C                                 ; C237
        rol $1D                                 ; C239
        rts                                     ; C23B
LC23C:
        lda $1F                                 ; C23C
        asl                                     ; C23E
        eor $1F                                 ; C23F
        asl                                     ; C241
        asl                                     ; C242
        ror $1E                                 ; C243
        rol $1F                                 ; C245
        rts                                     ; C247
LC248:
        ldy #$00                                ; C248
        lda ($00),y                             ; C24A
        inc $00                                 ; C24C
        bne LC252                               ; C24E
        inc $01                                 ; C250
LC252:
        sta $03                                 ; C252
        lda ($00),y                             ; C254
        inc $00                                 ; C256
        bne LC25C                               ; C258
        inc $01                                 ; C25A
LC25C:
        sta $02                                 ; C25C
        lda $02                                 ; C25E
        beq LC264                               ; C260
        inc $03                                 ; C262
LC264:
        ldy $00                                 ; C264
        lda #$00                                ; C266
        sta $00                                 ; C268
LC26A:
        lda ($00),y                             ; C26A
        bmi LC28F                               ; C26C
        iny                                     ; C26E
        bne LC273                               ; C26F
        inc $01                                 ; C271
LC273:
        tax                                     ; C273
        inx                                     ; C274
LC275:
        lda ($00),y                             ; C275
        iny                                     ; C277
        bne LC27C                               ; C278
        inc $01                                 ; C27A
LC27C:
        sta PPUDATA                             ; C27C
        dec $02                                 ; C27F
        bne LC287                               ; C281
        dec $03                                 ; C283
        beq LC28C                               ; C285
LC287:
        dex                                     ; C287
        bne LC275                               ; C288
        beq LC26A                               ; C28A
LC28C:
        sty $00                                 ; C28C
        rts                                     ; C28E
LC28F:
        iny                                     ; C28F
        bne LC294                               ; C290
        inc $01                                 ; C292
LC294:
        tax                                     ; C294
        dex                                     ; C295
        lda ($00),y                             ; C296
        iny                                     ; C298
        bne LC29D                               ; C299
        inc $01                                 ; C29B
LC29D:
        sta PPUDATA                             ; C29D
        dec $02                                 ; C2A0
        bne LC2A8                               ; C2A2
        dec $03                                 ; C2A4
        beq LC28C                               ; C2A6
LC2A8:
        inx                                     ; C2A8
        bne LC29D                               ; C2A9
        beq LC26A                               ; C2AB
LC2AD:
        .byte $17,$15,$01,$02,$03,$04,$09,$19   ; C2AD ........
        .byte $0A,$1A,$0B,$1B,$0C,$0D,$0E,$0F   ; C2B5 ........
        .byte $10,$11,$12,$13,$14,$00,$00,$00   ; C2BD ........
LC2C5:
        .byte $20,$FF,$FD,$FE,$FC,$00,$00,$00   ; C2C5  .......
        .byte $00,$24,$85,$93,$FB,$FA,$F9,$F8   ; C2CD .$......
        .byte $F4,$F5,$83,$F6,$81,$80,$F0,$F0   ; C2D5 ........
        .byte $F0,$F3,$86,$96,$20,$00,$80,$A5   ; C2DD .... ...
        .byte $15,$05,$14,$05,$16,$05,$17,$85   ; C2E5 ........
        .byte $14,$A5,$19,$05,$18,$05,$1A,$05   ; C2ED ........
        .byte $1B,$85,$18,$60,$A2,$00,$8A,$9D   ; C2F5 ...`....
        .byte $00,$07,$E8,$D0,$FA,$AA,$9D,$60   ; C2FD .......`
        .byte $06,$E8,$E0,$20,$D0,$F8,$A9,$00   ; C305 ... ....
        .byte $8D,$F2,$04,$8D,$F3,$04,$8D,$F4   ; C30D ........
        .byte $04,$A9,$01,$8D,$E8,$04           ; C315 ......
LC31B:
        jsr LC210                               ; C31B
        jsr L80D0                               ; C31E
        jsr LD33B                               ; C321
        lda #$00                                ; C324
        sta PPUMASK                             ; C326
        sta PPUSCROLL                           ; C329
        sta PPUSCROLL                           ; C32C
        jsr L813E                               ; C32F
        ldx #$00                                ; C332
LC334:
        ldy $0700,x                             ; C334
        lda L9021,y                             ; C337
        sta $0700,x                             ; C33A
        inx                                     ; C33D
        bne LC334                               ; C33E
        ldy #$00                                ; C340
LC342:
        sty $09                                 ; C342
        jsr L93EF                               ; C344
        and $0660,y                             ; C347
        beq LC354                               ; C34A
        ldy $09                                 ; C34C
        lda $0700,y                             ; C34E
        jsr L8506                               ; C351
LC354:
        ldy $09                                 ; C354
        iny                                     ; C356
        cpy #$F0                                ; C357
        bne LC342                               ; C359
        lda #$00                                ; C35B
        tax                                     ; C35D
LC35E:
        sta $7E,x                               ; C35E
        inx                                     ; C360
        cpx #$20                                ; C361
        bne LC35E                               ; C363
        lda #$20                                ; C365
        sta PPUADDR                             ; C367
        lda #$A7                                ; C36A
        sta PPUADDR                             ; C36C
        lda #$10                                ; C36F
        jsr LCDA9                               ; C371
        lda #$22                                ; C374
        sta PPUADDR                             ; C376
        lda #$A7                                ; C379
        sta PPUADDR                             ; C37B
        lda #$90                                ; C37E
        jsr LCDA9                               ; C380
        lda #$22                                ; C383
        sta PPUADDR                             ; C385
        lda #$E9                                ; C388
        sta PPUADDR                             ; C38A
        ldx #$00                                ; C38D
LC38F:
        cpx #$08                                ; C38F
        bne LC39D                               ; C391
        lda #$23                                ; C393
        sta PPUADDR                             ; C395
        lda #$09                                ; C398
        sta PPUADDR                             ; C39A
LC39D:
        cpx #$10                                ; C39D
        bne LC3AB                               ; C39F
        lda #$23                                ; C3A1
        sta PPUADDR                             ; C3A3
        lda #$29                                ; C3A6
        sta PPUADDR                             ; C3A8
LC3AB:
        ldy LC2AD,x                             ; C3AB
        lda LC2C5,y                             ; C3AE
        sta PPUDATA                             ; C3B1
        lda #$20                                ; C3B4
        sta PPUDATA                             ; C3B6
        inx                                     ; C3B9
        cpx #$18                                ; C3BA
        bne LC38F                               ; C3BC
        lda $04ED                               ; C3BE
        ora $04EE                               ; C3C1
        beq LC3DA                               ; C3C4
        lda #$20                                ; C3C6
        sta PPUADDR                             ; C3C8
        lda #$6D                                ; C3CB
        sta PPUADDR                             ; C3CD
        jsr L8185                               ; C3D0
        lsr $65,x                               ; C3D3
        .byte $72,$73,$75,$73,$00               ; C3D5 rsus.
LC3DA:
        lda #$20                                ; C3DA
        sta PPUADDR                             ; C3DC
        lda #$8A                                ; C3DF
        sta PPUADDR                             ; C3E1
        jsr L8185                               ; C3E4
        jmp $7665                               ; C3E7
        .byte $65,$6C,$20,$53,$74,$75,$64,$69   ; C3EA el Studi
        .byte $6F,$00,$A9,$21,$8D,$06,$20,$A9   ; C3F2 o..!.. .
        .byte $81,$8D,$06,$20,$20,$85,$81,$2D   ; C3FA ...  ..-
        .byte $4D,$41,$49,$4E,$2D,$00,$A9,$21   ; C402 MAIN-..!
        .byte $8D,$06,$20,$A9,$C2,$8D,$06,$20   ; C40A .. .... 
        .byte $20,$85,$81,$50,$6C,$61,$79,$00   ; C412  ..Play.
        .byte $A9,$22,$8D,$06,$20,$A9,$01,$8D   ; C41A .".. ...
        .byte $06,$20,$20,$85,$81,$53,$70,$61   ; C422 .  ..Spa
        .byte $77,$6E,$00,$A9,$22,$8D,$06,$20   ; C42A wn..".. 
        .byte $A9,$41,$8D,$06,$20,$20,$85,$81   ; C432 .A..  ..
        .byte $53,$65,$74,$75,$70,$00,$A9,$22   ; C43A Setup.."
        .byte $8D,$06,$20,$A9,$82,$8D,$06,$20   ; C442 .. .... 
        .byte $20,$85,$81,$51,$75,$69,$74,$00   ; C44A  ..Quit.
        .byte $A2,$00,$86,$00,$A4,$00,$B9,$89   ; C452 ........
        .byte $CD,$8D,$06,$20,$B9,$8A,$CD,$8D   ; C45A ... ....
        .byte $06,$20,$C8,$C8,$C0,$20,$F0,$21   ; C462 . ... .!
        .byte $84,$00,$A9,$BD,$8D,$07,$20,$48   ; C46A ...... H
        .byte $A9,$10,$85,$01,$BC,$00,$07,$B9   ; C472 ........
        .byte $C5,$C2,$8D,$07,$20,$E8,$C6,$01   ; C47A .... ...
        .byte $D0,$F2,$68,$8D,$07,$20,$4C,$56   ; C482 ..h.. LV
        .byte $C4,$A9,$23,$8D,$06,$20,$A9,$C0   ; C48A ..#.. ..
        .byte $8D,$06,$20,$A2,$40,$A9,$00,$8D   ; C492 .. .@...
        .byte $07,$20,$CA,$D0,$FA,$A9,$00,$8D   ; C49A . ......
        .byte $05,$20,$8D,$05,$20,$20,$D0,$80   ; C4A2 . ..  ..
        .byte $A9,$00,$8D,$05,$20,$8D,$05,$20   ; C4AA .... .. 
        .byte $A9,$1E,$8D,$01,$20,$20,$D0,$80   ; C4B2 ....  ..
        .byte $4C,$C9,$C4,$AD,$F3,$04,$0A,$0A   ; C4BA L.......
        .byte $0A,$0A,$0D,$F2,$04,$AA,$60,$20   ; C4C2 ......` 
        .byte $E1,$C2,$A5,$14,$29,$0F,$85,$00   ; C4CA ....)...
        .byte $A5,$18,$29,$0F,$C5,$00,$D0,$1E   ; C4D2 ..).....
        .byte $AD,$EC,$04,$C9,$10,$90,$0C,$A5   ; C4DA ........
        .byte $13,$29,$03,$D0,$06,$A5,$18,$29   ; C4E2 .).....)
        .byte $F0,$85,$18,$AD,$EC,$04,$30,$0B   ; C4EA ......0.
        .byte $EE,$EC,$04,$4C,$FD,$C4,$A9,$00   ; C4F2 ...L....
        .byte $8D,$EC,$04,$A5,$14,$29,$02,$F0   ; C4FA .....)..
        .byte $09,$A5,$18,$29,$02,$D0,$03,$CE   ; C502 ...)....
        .byte $F2,$04,$A5,$14,$29,$01,$F0,$09   ; C50A ....)...
        .byte $A5,$18,$29,$01,$D0,$03,$EE,$F2   ; C512 ..).....
        .byte $04,$A5,$14,$29,$08,$F0,$10,$A5   ; C51A ...)....
        .byte $18,$29,$08,$D0,$0A,$CE,$F3,$04   ; C522 .)......
        .byte $10,$05,$A9,$0E,$8D,$F3,$04,$A5   ; C52A ........
        .byte $14,$29,$04,$F0,$15,$A5,$18,$29   ; C532 .).....)
        .byte $04,$D0,$0F,$EE,$F3,$04,$AD,$F3   ; C53A ........
        .byte $04,$C9,$0F,$D0,$05,$A9,$00,$8D   ; C542 ........
        .byte $F3,$04,$A5,$14,$29,$40,$F0,$25   ; C54A ....)@.%
        .byte $A5,$18,$29,$40,$D0,$1F,$20,$BD   ; C552 ..)@.. .
        .byte $C4,$BD,$00,$07,$D0,$03,$4C,$BF   ; C55A ......L.
        .byte $CC,$A0,$00,$D9,$AD,$C2,$F0,$07   ; C562 ........
        .byte $C8,$C0,$18,$D0,$F6,$F0,$06,$8C   ; C56A ........
        .byte $F4,$04,$4C,$BF,$CC,$A5,$14,$29   ; C572 ..L....)
        .byte $10,$F0,$09,$A5,$18,$29,$10,$D0   ; C57A .....)..
        .byte $03,$4C,$22,$C6,$A5,$18,$49,$FF   ; C582 .L"...I.
        .byte $25,$14,$29,$0F,$85,$00,$AD,$F2   ; C58A %.).....
        .byte $04,$29,$0F,$8D,$F2,$04,$AD,$F3   ; C592 .)......
        .byte $04,$29,$0F,$8D,$F3,$04,$A5,$14   ; C59A .)......
        .byte $29,$80,$F0,$47,$A5,$18,$29,$80   ; C5A2 )..G..).
        .byte $49,$80,$05,$00,$F0,$3D,$20,$BD   ; C5AA I....= .
        .byte $C4,$BD,$00,$07,$D0,$0C,$AC,$F4   ; C5B2 ........
        .byte $04,$B9,$AD,$C2,$9D,$00,$07,$4C   ; C5BA .......L
        .byte $C9,$C5,$A9,$00,$9D,$00,$07,$AA   ; C5C2 ........
        .byte $AD,$F3,$04,$0A,$A8,$B9,$89,$CD   ; C5CA ........
        .byte $8D,$06,$20,$B9,$8A,$CD,$38,$6D   ; C5D2 .. ...8m
        .byte $F2,$04,$8D,$06,$20,$BD,$C5,$C2   ; C5DA .... ...
        .byte $8D,$07,$20,$A9,$00,$8D,$05,$20   ; C5E2 .. .... 
        .byte $8D,$05,$20,$AD,$F3,$04,$0A,$0A   ; C5EA .. .....
        .byte $0A,$18,$69,$2F,$8D,$00,$02,$AD   ; C5F2 ..i/....
        .byte $F2,$04,$0A,$0A,$0A,$18,$69,$40   ; C5FA ......i@
        .byte $8D,$03,$02,$A9,$4D,$8D,$01,$02   ; C602 ....M...
        .byte $A5,$13,$4A,$6A,$29,$80,$8D,$02   ; C60A ..Jj)...
        .byte $02,$A9,$00,$8D,$09,$02,$18,$20   ; C612 ....... 
        .byte $52,$CD,$20,$D0,$80,$4C,$C9,$C4   ; C61A R. ..L..
        .byte $A9,$00,$85,$00,$8D,$DE,$04,$20   ; C622 ....... 
        .byte $00,$80,$A9,$00,$85,$44,$85,$45   ; C62A .....D.E
        .byte $20,$DB,$AD,$20,$E4,$C2,$A5,$14   ; C632  .. ....
        .byte $29,$08,$F0,$0E,$A5,$18,$29,$08   ; C63A ).....).
        .byte $D0,$08,$C6,$00,$10,$04,$A9,$03   ; C642 ........
        .byte $85,$00,$A5,$14,$29,$04,$F0,$12   ; C64A ....)...
        .byte $A5,$18,$29,$04,$D0,$0C,$E6,$00   ; C652 ..).....
        .byte $A5,$00,$C9,$04,$D0,$04,$A9,$00   ; C65A ........
        .byte $85,$00,$A5,$14,$29,$80,$F0,$13   ; C662 ....)...
        .byte $A5,$18,$29,$80,$D0,$0D,$A5,$00   ; C66A ..).....
        .byte $0A,$AA,$BD,$AB,$C6,$48,$BD,$AA   ; C672 .....H..
        .byte $C6,$48,$60,$A5,$14,$29,$40,$F0   ; C67A .H`..)@.
        .byte $09,$A5,$18,$29,$40,$D0,$03,$4C   ; C682 ...)@..L
        .byte $C9,$C4,$A9,$30,$8D,$0B,$02,$A9   ; C68A ...0....
        .byte $4C,$8D,$09,$02,$A9,$40,$8D,$0A   ; C692 L....@..
        .byte $02,$A5,$00,$0A,$0A,$0A,$0A,$18   ; C69A ........
        .byte $69,$70,$8D,$08,$02,$4C,$29,$C6   ; C6A2 ip...L).
        .byte $C0,$C6,$B1,$C6,$F8,$C7,$D1,$C6   ; C6AA ........
        .byte $AD,$F2,$04,$8D,$E9,$04,$AD,$F3   ; C6B2 ........
        .byte $04,$8D,$EA,$04,$4C,$C9,$C4,$EE   ; C6BA ....L...
        .byte $EF,$04,$AD,$ED,$04,$F0,$06,$A9   ; C6C2 ........
        .byte $01,$85,$44,$85,$45,$4C,$C9,$8D   ; C6CA ..D.EL..
        .byte $20,$D0,$80,$A9,$00,$8D,$01,$20   ; C6D2  ...... 
        .byte $20,$3E,$81,$20,$10,$C2,$20,$D0   ; C6DA  >. .. .
        .byte $80,$A9,$00,$A2,$08,$A0,$00,$20   ; C6E2 ....... 
        .byte $34,$B6,$F0,$03,$4C,$B1,$A9,$4C   ; C6EA 4...L..L
        .byte $1B,$C3,$4E,$6F,$6E,$65,$00,$57   ; C6F2 ..None.W
        .byte $61,$6C,$6B,$65,$72,$00,$4A,$75   ; C6FA alker.Ju
        .byte $6D,$70,$79,$00,$44,$69,$61,$67   ; C702 mpy.Diag
        .byte $53,$68,$6F,$6F,$74,$00,$57,$61   ; C70A Shoot.Wa
        .byte $69,$74,$53,$68,$6F,$6F,$74,$00   ; C712 itShoot.
        .byte $42,$6F,$6D,$62,$00,$46,$6C,$79   ; C71A Bomb.Fly
        .byte $42,$6F,$6D,$62,$65,$72,$00,$46   ; C722 Bomber.F
        .byte $6C,$79,$44,$69,$61,$67,$00,$46   ; C72A lyDiag.F
        .byte $6C,$6F,$61,$74,$53,$68,$6F,$6F   ; C732 loatShoo
        .byte $74,$56,$00,$50,$6C,$6F,$64,$64   ; C73A tV.Plodd
        .byte $65,$72,$00,$53,$6E,$65,$61,$6B   ; C742 er.Sneak
        .byte $65,$72,$00,$56,$6F,$6C,$63,$61   ; C74A er.Volca
        .byte $6E,$6F,$00,$47,$69,$61,$6E,$61   ; C752 no.Giana
        .byte $20,$4F,$77,$6C,$00,$54,$6F,$61   ; C75A  Owl.Toa
        .byte $73,$74,$62,$6F,$74,$00,$42,$75   ; C762 stbot.Bu
        .byte $72,$67,$65,$72,$31,$00,$42,$75   ; C76A rger1.Bu
        .byte $72,$67,$65,$72,$32,$00,$42,$75   ; C772 rger2.Bu
        .byte $72,$67,$65,$72,$33,$00,$42,$69   ; C77A rger3.Bi
        .byte $6C,$6C,$20,$4E,$79,$65,$00,$52   ; C782 ll Nye.R
        .byte $6F,$6C,$6C,$42,$61,$6C,$6C,$00   ; C78A ollBall.
        .byte $4A,$75,$6D,$70,$42,$61,$6C,$6C   ; C792 JumpBall
        .byte $00,$54,$72,$69,$67,$57,$61,$6C   ; C79A .TrigWal
        .byte $6B,$00,$54,$72,$69,$67,$42,$6F   ; C7A2 k.TrigBo
        .byte $6D,$62,$00,$53,$6D,$61,$73,$68   ; C7AA mb.Smash
        .byte $20,$53,$74,$61,$74,$69,$63,$00   ; C7B2  Static.
        .byte $53,$6D,$61,$73,$68,$20,$4D,$6F   ; C7BA Smash Mo
        .byte $76,$65,$00,$46,$6C,$61,$70,$70   ; C7C2 ve.Flapp
        .byte $79,$20,$4F,$77,$6C,$00,$50,$6F   ; C7CA y Owl.Po
        .byte $74,$69,$6F,$6E,$00,$53,$70,$65   ; C7D2 tion.Spe
        .byte $61,$72,$73,$00,$00,$05,$0C,$12   ; C7DA ars.....
        .byte $1C,$26,$2B,$35,$3D,$49,$51,$59   ; C7E2 .&+5=IQY
        .byte $61,$6B,$74,$7C,$84,$8C,$95,$9E   ; C7EA akt|....
        .byte $A7,$B0,$B9,$C6,$D1,$DC,$E3,$20   ; C7F2 ....... 
        .byte $D0,$80,$20,$10,$C2,$A9,$00,$8D   ; C7FA .. .....
        .byte $01,$20,$20,$3E,$81,$A9,$20,$8D   ; C802 .  >.. .
        .byte $06,$20,$A9,$6A,$8D,$06,$20,$20   ; C80A . .j..  
        .byte $85,$81,$4C,$65,$76,$65,$6C,$20   ; C812 ..Level 
        .byte $53,$65,$74,$75,$70,$00,$A9,$20   ; C81A Setup.. 
        .byte $8D,$06,$20,$A9,$89,$8D,$06,$20   ; C822 .. .... 
        .byte $20,$85,$81,$2D,$2D,$2D,$2D,$2D   ; C82A  ..-----
        .byte $2D,$2D,$2D,$2D,$2D,$2D,$2D,$2D   ; C832 --------
        .byte $00,$A9,$20,$8D,$06,$20,$A9,$CD   ; C83A .. .. ..
        .byte $8D,$06,$20,$20,$85,$81,$47,$6F   ; C842 ..  ..Go
        .byte $61,$6C,$00,$A9,$21,$8D,$06,$20   ; C84A al..!.. 
        .byte $A9,$07,$8D,$06,$20,$20,$85,$81   ; C852 ....  ..
        .byte $54,$79,$70,$65,$3A,$00,$A9,$21   ; C85A Type:..!
        .byte $8D,$06,$20,$A9,$25,$8D,$06,$20   ; C862 .. .%.. 
        .byte $20,$85,$81,$41,$6D,$6F,$75,$6E   ; C86A  ..Amoun
        .byte $74,$3A,$00,$A9,$21,$8D,$06,$20   ; C872 t:..!.. 
        .byte $A9,$6C,$8D,$06,$20,$20,$85,$81   ; C87A .l..  ..
        .byte $45,$6E,$65,$6D,$69,$65,$73,$00   ; C882 Enemies.
        .byte $A9,$21,$8D,$06,$20,$A9,$A5,$8D   ; C88A .!.. ...
        .byte $06,$20,$20,$85,$81,$45,$6E,$65   ; C892 .  ..Ene
        .byte $6D,$79,$31,$3A,$00,$A9,$21,$8D   ; C89A my1:..!.
        .byte $06,$20,$A9,$C5,$8D,$06,$20,$20   ; C8A2 . ....  
        .byte $85,$81,$45,$6E,$65,$6D,$79,$32   ; C8AA ..Enemy2
        .byte $3A,$00,$A9,$21,$8D,$06,$20,$A9   ; C8B2 :..!.. .
        .byte $E5,$8D,$06,$20,$20,$85,$81,$45   ; C8BA ...  ..E
        .byte $6E,$65,$6D,$79,$33,$3A,$00,$A9   ; C8C2 nemy3:..
        .byte $22,$8D,$06,$20,$A9,$05,$8D,$06   ; C8CA ".. ....
        .byte $20,$20,$85,$81,$45,$6E,$65,$6D   ; C8D2   ..Enem
        .byte $79,$34,$3A,$00,$A9,$22,$8D,$06   ; C8DA y4:.."..
        .byte $20,$A9,$25,$8D,$06,$20,$20,$85   ; C8E2  .%..  .
        .byte $81,$44,$69,$73,$74,$72,$2E,$3A   ; C8EA .Distr.:
        .byte $00,$A9,$22,$8D,$06,$20,$A9,$46   ; C8F2 ..".. .F
        .byte $8D,$06,$20,$20,$85,$81,$48,$61   ; C8FA ..  ..Ha
        .byte $72,$64,$3F,$3A,$00,$A9,$22,$8D   ; C902 rd?:..".
        .byte $06,$20,$A9,$68,$8D,$06,$20,$20   ; C90A . .h..  
        .byte $85,$81,$4D,$61,$78,$3A,$00,$A9   ; C912 ..Max:..
        .byte $22,$8D,$06,$20,$A9,$85,$8D,$06   ; C91A ".. ....
        .byte $20,$20,$85,$81,$45,$66,$66,$65   ; C922   ..Effe
        .byte $63,$74,$3A,$00,$A2,$00,$86,$00   ; C92A ct:.....
        .byte $8A,$48,$20,$4D,$CB,$68,$AA,$E8   ; C932 .H M.h..
        .byte $E0,$0A,$D0,$F4,$20,$D0,$80,$A9   ; C93A .... ...
        .byte $00,$8D,$05,$20,$8D,$05,$20,$A9   ; C942 ... .. .
        .byte $1E,$8D,$01,$20,$20,$D0,$80,$20   ; C94A ...  .. 
        .byte $E1,$C2,$A5,$14,$29,$80,$F0,$26   ; C952 ....)..&
        .byte $A5,$18,$29,$80,$D0,$20,$A6,$00   ; C95A ..).. ..
        .byte $E0,$02,$90,$1A,$E0,$05,$B0,$16   ; C962 ........
        .byte $BD,$E0,$04,$9D,$E1,$04,$A5,$00   ; C96A ........
        .byte $18,$69,$01,$20,$4D,$CB,$A9,$00   ; C972 .i. M...
        .byte $8D,$05,$20,$8D,$05,$20,$A5,$14   ; C97A .. .. ..
        .byte $29,$02,$F0,$27,$A5,$18,$29,$02   ; C982 )..'..).
        .byte $D0,$21,$A6,$00,$20,$5A,$CA,$38   ; C98A .!.. Z.8
        .byte $E9,$01,$10,$06,$BD,$1B,$CB,$38   ; C992 .......8
        .byte $E9,$01,$A6,$00,$20,$7E,$CA,$8A   ; C99A .... ~..
        .byte $20,$4D,$CB,$A9,$00,$8D,$05,$20   ; C9A2  M..... 
        .byte $8D,$05,$20,$A5,$14,$29,$01,$F0   ; C9AA .. ..)..
        .byte $26,$A5,$18,$29,$01,$D0,$20,$A6   ; C9B2 &..).. .
        .byte $00,$20,$5A,$CA,$18,$69,$01,$DD   ; C9BA . Z..i..
        .byte $1B,$CB,$90,$02,$A9,$00,$A6,$00   ; C9C2 ........
        .byte $20,$7E,$CA,$8A,$20,$4D,$CB,$A9   ; C9CA  ~.. M..
        .byte $00,$8D,$05,$20,$8D,$05,$20,$A5   ; C9D2 ... .. .
        .byte $14,$29,$08,$F0,$0E,$A5,$18,$29   ; C9DA .).....)
        .byte $08,$D0,$08,$C6,$00,$10,$04,$A9   ; C9E2 ........
        .byte $09,$85,$00,$A5,$14,$29,$04,$F0   ; C9EA .....)..
        .byte $12,$A5,$18,$29,$04,$D0,$0C,$E6   ; C9F2 ...)....
        .byte $00,$A5,$00,$C9,$0A,$D0,$04,$A9   ; C9FA ........
        .byte $00,$85,$00,$20,$10,$C2,$A5,$14   ; CA02 ... ....
        .byte $29,$40,$F0,$09,$A5,$18,$29,$40   ; CA0A )@....)@
        .byte $D0,$03,$4C,$1B,$C3,$A9,$58,$8D   ; CA12 ..L...X.
        .byte $03,$02,$A9,$4D,$8D,$01,$02,$A5   ; CA1A ...M....
        .byte $13,$4A,$6A,$29,$80,$8D,$02,$02   ; CA22 .Jj)....
        .byte $A5,$00,$0A,$0A,$0A,$18,$69,$3F   ; CA2A ......i?
        .byte $8D,$00,$02,$A4,$00,$C0,$02,$90   ; CA32 ........
        .byte $06,$18,$69,$18,$8D,$00,$02,$A6   ; CA3A ..i.....
        .byte $00,$E0,$02,$90,$10,$E0,$06,$B0   ; CA42 ........
        .byte $0C,$A5,$00,$48,$BD,$E0,$04,$20   ; CA4A ...H... 
        .byte $C9,$CD,$68,$85,$00,$4C,$4E,$C9   ; CA52 ..h..LN.
        .byte $85,$01,$8A,$0A,$A8,$B9,$6B,$CA   ; CA5A ......k.
        .byte $48,$B9,$6A,$CA,$48,$A5,$01,$60   ; CA62 H.j.H..`
        .byte $A1,$CA,$A7,$CA,$AD,$CA,$AD,$CA   ; CA6A ........
        .byte $AD,$CA,$AD,$CA,$B1,$CA,$B8,$CA   ; CA72 ........
        .byte $BB,$CA,$C1,$CA,$85,$01,$8A,$0A   ; CA7A ........
        .byte $A8,$B9,$8F,$CA,$48,$B9,$8E,$CA   ; CA82 ....H...
        .byte $48,$A5,$01,$60,$C9,$CA,$D6,$CA   ; CA8A H..`....
        .byte $E5,$CA,$E5,$CA,$E5,$CA,$E5,$CA   ; CA92 ........
        .byte $E9,$CA,$F9,$CA,$FC,$CA,$09,$CB   ; CA9A ........
        .byte $AD,$E0,$04,$29,$03,$60,$AD,$E0   ; CAA2 ...).`..
        .byte $04,$4A,$4A,$60,$BD,$E0,$04,$60   ; CAAA .JJ`...`
        .byte $AD,$E1,$04,$4A,$4A,$4A,$60,$A5   ; CAB2 ...JJJ`.
        .byte $DC,$60,$AD,$E1,$04,$29,$07,$60   ; CABA .`...).`
        .byte $AD,$E1,$04,$4A,$4A,$4A,$4A,$60   ; CAC2 ...JJJJ`
        .byte $85,$02,$AD,$E0,$04,$29,$FC,$05   ; CACA .....)..
        .byte $02,$8D,$E0,$04,$60,$0A,$0A,$85   ; CAD2 ....`...
        .byte $02,$AD,$E0,$04,$29,$03,$05,$02   ; CADA ....)...
        .byte $8D,$E0,$04,$60,$9D,$E0,$04,$60   ; CAE2 ...`...`
        .byte $0A,$0A,$0A,$85,$02,$AD,$E1,$04   ; CAEA ........
        .byte $29,$F7,$05,$02,$8D,$E1,$04,$60   ; CAF2 )......`
        .byte $85,$DC,$60,$85,$02,$AD,$E1,$04   ; CAFA ..`.....
        .byte $29,$F8,$05,$02,$8D,$E1,$04,$60   ; CB02 )......`
        .byte $0A,$0A,$0A,$0A,$85,$02,$AD,$E1   ; CB0A ........
        .byte $04,$29,$0F,$05,$02,$8D,$E1,$04   ; CB12 .)......
        .byte $60,$04,$20,$1B,$1B,$1B,$1B,$02   ; CB1A `. .....
        .byte $02,$08,$05,$4E,$6F,$6E,$65,$20   ; CB22 ...None 
        .byte $20,$20,$20,$53,$63,$72,$6F,$6C   ; CB2A    Scrol
        .byte $6C,$20,$31,$53,$63,$72,$6F,$6C   ; CB32 l 1Scrol
        .byte $6C,$20,$32,$53,$63,$72,$6F,$6C   ; CB3A l 2Scrol
        .byte $6C,$20,$33,$4E,$6F,$20,$43,$79   ; CB42 l 3No Cy
        .byte $63,$6C,$65,$C9,$09,$90,$1E,$A9   ; CB4A cle.....
        .byte $22,$8D,$06,$20,$A9,$8C,$8D,$06   ; CB52 ".. ....
        .byte $20,$AD,$E1,$04,$29,$F0,$4A,$AA   ; CB5A  ...).J.
        .byte $A0,$08,$BD,$25,$CB,$8D,$07,$20   ; CB62 ...%... 
        .byte $E8,$88,$D0,$F6,$60,$C9,$08,$90   ; CB6A ....`...
        .byte $15,$A9,$22,$8D,$06,$20,$A9,$6C   ; CB72 ..".. .l
        .byte $8D,$06,$20,$AD,$E1,$04,$29,$07   ; CB7A .. ...).
        .byte $18,$69,$01,$4C,$D9,$80,$C9,$07   ; CB82 .i.L....
        .byte $90,$30,$A9,$22,$8D,$06,$20,$A9   ; CB8A .0.".. .
        .byte $4C,$8D,$06,$20,$A5,$DC,$0A,$0A   ; CB92 L.. ....
        .byte $AA,$BD,$B4,$CB,$8D,$07,$20,$BD   ; CB9A ...... .
        .byte $B5,$CB,$8D,$07,$20,$BD,$B6,$CB   ; CBA2 .... ...
        .byte $8D,$07,$20,$BD,$B7,$CB,$8D,$07   ; CBAA .. .....
        .byte $20,$60,$45,$61,$73,$79,$48,$61   ; CBB2  `EasyHa
        .byte $72,$64,$C9,$06,$90,$47,$A9,$22   ; CBBA rd...G."
        .byte $8D,$06,$20,$A9,$2C,$8D,$06,$20   ; CBC2 .. .,.. 
        .byte $AD,$E1,$04,$29,$08,$F0,$1C,$A0   ; CBCA ...)....
        .byte $20,$A9,$35,$8D,$07,$20,$8C,$07   ; CBD2  .5.. ..
        .byte $20,$8D,$07,$20,$A9,$33,$8C,$07   ; CBDA  .. .3..
        .byte $20,$8D,$07,$20,$8C,$07,$20,$8D   ; CBE2  .. .. .
        .byte $07,$20,$60,$A0,$20,$A9,$34,$8D   ; CBEA . `. .4.
        .byte $07,$20,$8C,$07,$20,$8D,$07,$20   ; CBF2 . .. .. 
        .byte $8C,$07,$20,$8D,$07,$20,$8C,$07   ; CBFA .. .. ..
        .byte $20,$8D,$07,$20,$60,$C9,$02,$90   ; CC02  .. `...
        .byte $49,$38,$E9,$02,$48,$0A,$AA,$BD   ; CC0A I8..H...
        .byte $4C,$CC,$8D,$06,$20,$BD,$4D,$CC   ; CC12 L... .M.
        .byte $8D,$06,$20,$68,$AA,$BD,$E2,$04   ; CC1A .. h....
        .byte $AA,$BC,$DE,$C7,$B9,$F4,$C6,$F0   ; CC22 ........
        .byte $06,$8D,$07,$20,$C8,$D0,$F5,$A9   ; CC2A ... ....
        .byte $20,$8D,$07,$20,$8D,$07,$20,$8D   ; CC32  .. .. .
        .byte $07,$20,$8D,$07,$20,$8D,$07,$20   ; CC3A . .. .. 
        .byte $8D,$07,$20,$8D,$07,$20,$8D,$07   ; CC42 .. .. ..
        .byte $20,$60,$21,$AC,$21,$CC,$21,$EC   ; CC4A  `!.!.!.
        .byte $22,$0C,$C9,$01,$90,$1A,$A9,$21   ; CC52 "......!
        .byte $8D,$06,$20,$A9,$2C,$8D,$06,$20   ; CC5A .. .,.. 
        .byte $AD,$E0,$04,$4A,$4A,$18,$69,$01   ; CC62 ...JJ.i.
        .byte $A8,$B9,$FD,$85,$20,$D9,$80,$60   ; CC6A .... ..`
        .byte $A9,$21,$8D,$06,$20,$A9,$0C,$8D   ; CC72 .!.. ...
        .byte $06,$20,$AD,$E0,$04,$29,$03,$0A   ; CC7A . ...)..
        .byte $85,$E0,$0A,$0A,$18,$65,$E0,$AA   ; CC82 .....e..
        .byte $A0,$0A,$BD,$97,$CC,$8D,$07,$20   ; CC8A ....... 
        .byte $E8,$88,$D0,$F6,$60,$4B,$69,$6C   ; CC92 ....`Kil
        .byte $6C,$20,$61,$6C,$6C,$20,$20,$47   ; CC9A l all  G
        .byte $65,$74,$20,$6D,$6F,$6E,$65,$79   ; CCA2 et money
        .byte $20,$53,$75,$72,$76,$69,$76,$65   ; CCAA  Survive
        .byte $20,$20,$20,$47,$72,$65,$65,$6E   ; CCB2    Green
        .byte $2D,$3E,$52,$65,$64,$A9,$00,$8D   ; CCBA ->Red...
        .byte $7C,$03,$20,$E1,$C2,$A5,$14,$29   ; CCC2 |. ....)
        .byte $08,$F0,$17,$A5,$18,$29,$08,$D0   ; CCCA .....)..
        .byte $11,$AD,$F4,$04,$38,$E9,$08,$8D   ; CCD2 ....8...
        .byte $F4,$04,$10,$06,$18,$69,$18,$8D   ; CCDA .....i..
        .byte $F4,$04,$A5,$14,$29,$04,$F0,$19   ; CCE2 ....)...
        .byte $A5,$18,$29,$04,$D0,$13,$AD,$F4   ; CCEA ..).....
        .byte $04,$18,$69,$08,$8D,$F4,$04,$C9   ; CCF2 ..i.....
        .byte $18,$90,$06,$38,$E9,$18,$8D,$F4   ; CCFA ...8....
        .byte $04,$A5,$14,$29,$02,$F0,$10,$A5   ; CD02 ...)....
        .byte $18,$29,$02,$D0,$0A,$CE,$F4,$04   ; CD0A .)......
        .byte $10,$05,$A9,$17,$8D,$F4,$04,$A5   ; CD12 ........
        .byte $14,$29,$01,$F0,$15,$A5,$18,$29   ; CD1A .).....)
        .byte $01,$D0,$0F,$EE,$F4,$04,$AD,$F4   ; CD22 ........
        .byte $04,$C9,$18,$90,$05,$A9,$00,$8D   ; CD2A ........
        .byte $F4,$04,$A5,$14,$29,$80,$F0,$09   ; CD32 ....)...
        .byte $A5,$18,$29,$80,$D0,$03,$4C,$C9   ; CD3A ..)...L.
        .byte $C4,$A5,$14,$38,$20,$52,$CD,$EE   ; CD42 ...8 R..
        .byte $7C,$03,$20,$D0,$80,$4C,$C4,$CC   ; CD4A |. ..L..
        .byte $08,$AD,$F4,$04,$29,$07,$0A,$0A   ; CD52 ....)...
        .byte $0A,$0A,$18,$69,$48,$8D,$07,$02   ; CD5A ...iH...
        .byte $A9,$4D,$8D,$05,$02,$A5,$13,$4A   ; CD62 .M.....J
        .byte $6A,$29,$80,$28,$90,$02,$09,$01   ; CD6A j).(....
        .byte $8D,$06,$02,$AD,$7C,$03,$4A,$4A   ; CD72 ....|.JJ
        .byte $29,$07,$AA,$AD,$F4,$04,$29,$F8   ; CD7A ).....).
        .byte $18,$69,$B7,$8D,$04,$02,$60,$20   ; CD82 .i....` 
        .byte $C7,$20,$E7,$21,$07,$21,$27,$21   ; CD8A . .!.!'!
        .byte $47,$21,$67,$21,$87,$21,$A7,$21   ; CD92 G!g!.!.!
        .byte $C7,$21,$E7,$22,$07,$22,$27,$22   ; CD9A .!."."'"
        .byte $47,$22,$67,$22,$87,$22,$A7       ; CDA2 G"g".".
LCDA9:
        sta $01                                 ; CDA9
        and #$1F                                ; CDAB
        tax                                     ; CDAD
        lda #$DE                                ; CDAE
        bit $01                                 ; CDB0
        bpl LCDB6                               ; CDB2
        lda #$EE                                ; CDB4
LCDB6:
        pha                                     ; CDB6
        sta PPUDATA                             ; CDB7
        lda #$BE                                ; CDBA
LCDBC:
        sta PPUDATA                             ; CDBC
        dex                                     ; CDBF
        bne LCDBC                               ; CDC0
        pla                                     ; CDC2
        ora #$0F                                ; CDC3
        sta PPUDATA                             ; CDC5
        rts                                     ; CDC8
        .byte $A0,$04,$84,$DF,$0A,$A8,$B9,$3F   ; CDC9 .......?
        .byte $CE,$D0,$01,$60,$85,$0F,$A9,$00   ; CDD1 ...`....
        .byte $85,$40,$85,$41,$B9,$3E,$CE,$85   ; CDD9 .@.A.>..
        .byte $04,$4A,$4A,$4A,$4A,$85,$0E,$A9   ; CDE1 .JJJJ...
        .byte $02,$85,$F4,$A9,$00,$8D,$91,$04   ; CDE9 ........
        .byte $8D,$9F,$04,$8D,$AD,$04,$A9,$C8   ; CDF1 ........
        .byte $8D,$4B,$04,$A9,$64,$8D,$59,$04   ; CDF9 .K..d.Y.
        .byte $A2,$00,$A5,$04,$29,$01,$F0,$07   ; CE01 ....)...
        .byte $A4,$0F,$A5,$0E,$4C,$6C,$9B,$A5   ; CE09 ....Ll..
        .byte $04,$29,$02,$F0,$17,$A4,$DF,$A9   ; CE11 .)......
        .byte $C8,$99,$03,$02,$A9,$64,$99,$00   ; CE19 .....d..
        .byte $02,$A5,$0F,$99,$01,$02,$A9,$01   ; CE21 ........
        .byte $99,$02,$02,$60,$A5,$0F,$29,$0F   ; CE29 ...`..).
        .byte $85,$F2,$A5,$0F,$4A,$4A,$4A,$4A   ; CE31 ....JJJJ
        .byte $85,$F3,$4C,$9B,$9A,$00,$00,$00   ; CE39 ..L.....
        .byte $11,$00,$25,$00,$90,$00,$90,$02   ; CE41 ..%.....
        .byte $3C,$00,$C6,$00,$96,$00,$46,$01   ; CE49 <.....F.
        .byte $A4,$01,$68,$01,$78,$01,$AC,$01   ; CE51 ..h.x...
        .byte $88,$01,$94,$01,$98,$01,$9C,$00   ; CE59 ........
        .byte $00,$01,$B8,$01,$BC,$00,$61,$00   ; CE61 ......a.
        .byte $C1,$01,$CC,$01,$CC,$01,$AC,$01   ; CE69 ........
        .byte $B4,$00,$A1                       ; CE71 ...
LCE74:
        ldx #$00                                ; CE74
LCE76:
        lda $03B2,x                             ; CE76
        bne LCE7E                               ; CE79
        jmp LCF97                               ; CE7B
LCE7E:
        sta $00                                 ; CE7E
        lsr                                     ; CE80
        sta $01                                 ; CE81
        ldy $DF                                 ; CE83
        lda $13                                 ; CE85
        and #$01                                ; CE87
        beq LCEFE                               ; CE89
        lda $03AD,x                             ; CE8B
        sta $0200,y                             ; CE8E
        lda #$03                                ; CE91
        sta $0202,y                             ; CE93
        lda #$60                                ; CE96
        sta $0201,y                             ; CE98
        lda $03A8,x                             ; CE9B
        sec                                     ; CE9E
        sbc $41                                 ; CE9F
        sta $0203,y                             ; CEA1
        lda $03AD,x                             ; CEA4
        clc                                     ; CEA7
        adc $00                                 ; CEA8
        sta $0204,y                             ; CEAA
        lda #$03                                ; CEAD
        sta $0206,y                             ; CEAF
        lda #$60                                ; CEB2
        sta $0205,y                             ; CEB4
        lda $03A8,x                             ; CEB7
        sec                                     ; CEBA
        sbc $41                                 ; CEBB
        sta $0207,y                             ; CEBD
        lda $03AD,x                             ; CEC0
        sta $0208,y                             ; CEC3
        lda #$03                                ; CEC6
        sta $020A,y                             ; CEC8
        lda #$60                                ; CECB
        sta $0209,y                             ; CECD
        lda $03A8,x                             ; CED0
        clc                                     ; CED3
        adc $00                                 ; CED4
        sec                                     ; CED6
        sbc $41                                 ; CED7
        sta $020B,y                             ; CED9
        lda $03AD,x                             ; CEDC
        clc                                     ; CEDF
        adc $00                                 ; CEE0
        sta $020C,y                             ; CEE2
        lda #$03                                ; CEE5
        sta $020E,y                             ; CEE7
        lda #$60                                ; CEEA
        sta $020D,y                             ; CEEC
        lda $03A8,x                             ; CEEF
        clc                                     ; CEF2
        adc $00                                 ; CEF3
        sec                                     ; CEF5
        sbc $41                                 ; CEF6
        sta $020F,y                             ; CEF8
        jmp LCF74                               ; CEFB
LCEFE:
        lda $03AD,x                             ; CEFE
        clc                                     ; CF01
        adc $01                                 ; CF02
        sta $0200,y                             ; CF04
        lda #$03                                ; CF07
        sta $0202,y                             ; CF09
        lda #$60                                ; CF0C
        sta $0201,y                             ; CF0E
        lda $03A8,x                             ; CF11
        sec                                     ; CF14
        sbc $41                                 ; CF15
        sta $0203,y                             ; CF17
        lda $03AD,x                             ; CF1A
        sta $0204,y                             ; CF1D
        lda #$03                                ; CF20
        sta $0206,y                             ; CF22
        lda #$60                                ; CF25
        sta $0205,y                             ; CF27
        lda $03A8,x                             ; CF2A
        clc                                     ; CF2D
        adc $01                                 ; CF2E
        sec                                     ; CF30
        sbc $41                                 ; CF31
        sta $0207,y                             ; CF33
        lda $03AD,x                             ; CF36
        clc                                     ; CF39
        adc $01                                 ; CF3A
        sta $0208,y                             ; CF3C
        lda #$03                                ; CF3F
        sta $020A,y                             ; CF41
        lda #$60                                ; CF44
        sta $0209,y                             ; CF46
        lda $03A8,x                             ; CF49
        clc                                     ; CF4C
        adc $00                                 ; CF4D
        sec                                     ; CF4F
        sbc $41                                 ; CF50
        sta $020B,y                             ; CF52
        lda $03AD,x                             ; CF55
        clc                                     ; CF58
        adc $00                                 ; CF59
        sta $020C,y                             ; CF5B
        lda #$03                                ; CF5E
        sta $020E,y                             ; CF60
        lda #$60                                ; CF63
        sta $020D,y                             ; CF65
        lda $03A8,x                             ; CF68
        clc                                     ; CF6B
        adc $01                                 ; CF6C
        sec                                     ; CF6E
        sbc $41                                 ; CF6F
        sta $020F,y                             ; CF71
LCF74:
        tya                                     ; CF74
        clc                                     ; CF75
        adc #$20                                ; CF76
        tay                                     ; CF78
        sty $DF                                 ; CF79
        jsr LCFD5                               ; CF7B
        inc $03B2,x                             ; CF7E
        inc $03B2,x                             ; CF81
        dec $03A8,x                             ; CF84
        dec $03AD,x                             ; CF87
        dec $03B7,x                             ; CF8A
        lda $03B7,x                             ; CF8D
        bne LCF97                               ; CF90
        lda #$00                                ; CF92
        sta $03B2,x                             ; CF94
LCF97:
        inx                                     ; CF97
        cpx #$05                                ; CF98
        beq LCF9F                               ; CF9A
        jmp LCE76                               ; CF9C
LCF9F:
        rts                                     ; CF9F
LCFA0:
        pha                                     ; CFA0
        ldy #$00                                ; CFA1
LCFA3:
        lda $03B2,y                             ; CFA3
        beq LCFB0                               ; CFA6
        iny                                     ; CFA8
        cpy #$05                                ; CFA9
        bne LCFA3                               ; CFAB
        pla                                     ; CFAD
        clc                                     ; CFAE
        rts                                     ; CFAF
LCFB0:
        pla                                     ; CFB0
        sec                                     ; CFB1
        rts                                     ; CFB2
LCFB3:
        jsr LCFA0                               ; CFB3
        bcc LCFD4                               ; CFB6
        sta $03B7,y                             ; CFB8
        lda $00                                 ; CFBB
        sta $03A8,y                             ; CFBD
        lda $01                                 ; CFC0
        sta $03AD,y                             ; CFC2
        lda #$01                                ; CFC5
        sta $03B2,y                             ; CFC7
        lda #$0B                                ; CFCA
        jsr LD37A                               ; CFCC
        lda #$0C                                ; CFCF
        jsr LD37A                               ; CFD1
LCFD4:
        rts                                     ; CFD4
LCFD5:
        ldy #$00                                ; CFD5
LCFD7:
        lda a:$0048,y                           ; CFD7
        sta $E9                                 ; CFDA
        lda a:$004C,y                           ; CFDC
        sta $E7                                 ; CFDF
        lda $03A8,x                             ; CFE1
        sta $EA                                 ; CFE4
        lda $03AD,x                             ; CFE6
        sta $E8                                 ; CFE9
        lda #$08                                ; CFEB
        sta $EB                                 ; CFED
        asl                                     ; CFEF
        sta $ED                                 ; CFF0
        lda $03B2,x                             ; CFF2
        sta $EC                                 ; CFF5
        sta $EE                                 ; CFF7
        jsr L8CC9                               ; CFF9
        bcc LD001                               ; CFFC
        jsr L8CF9                               ; CFFE
LD001:
        iny                                     ; D001
        cpy #$04                                ; D002
        bne LCFD7                               ; D004
        rts                                     ; D006
LD007:
        sta $00                                 ; D007
        ldy #$00                                ; D009
LD00B:
        lda $03C8,y                             ; D00B
        beq LD017                               ; D00E
        iny                                     ; D010
        cpy #$03                                ; D011
        bne LD00B                               ; D013
        clc                                     ; D015
        rts                                     ; D016
LD017:
        lda #$00                                ; D017
        sta $03C2,y                             ; D019
        lda $00                                 ; D01C
        ora #$80                                ; D01E
        sta $03C8,y                             ; D020
        sty $00                                 ; D023
        jsr L95D1                               ; D025
        ldy $00                                 ; D028
        pha                                     ; D02A
        and #$F0                                ; D02B
        clc                                     ; D02D
        adc #$04                                ; D02E
        sta $03BC,y                             ; D030
        stx $01                                 ; D033
        pla                                     ; D035
        and #$01                                ; D036
        tax                                     ; D038
        lda LD049,x                             ; D039
        sta $03C5,y                             ; D03C
        lda LD04B,x                             ; D03F
        sta $03BF,y                             ; D042
        ldx $01                                 ; D045
        sec                                     ; D047
        rts                                     ; D048
LD049:
        .byte $01,$FF                           ; D049 ..
LD04B:
        .byte $00,$E0                           ; D04B ..
LD04D:
        lda #$00                                ; D04D
        sta $00                                 ; D04F
LD051:
        ldx $00                                 ; D051
        lda $03C8,x                             ; D053
        bpl LD0B3                               ; D056
        ldy $DF                                 ; D058
        and #$0F                                ; D05A
        ora #$40                                ; D05C
        sta $0201,y                             ; D05E
        ora #$50                                ; D061
        sta $0205,y                             ; D063
        lda $03BC,x                             ; D066
        clc                                     ; D069
        adc $03C2,x                             ; D06A
        sta $03BC,x                             ; D06D
        lda $03BF,x                             ; D070
        clc                                     ; D073
        adc $03C5,x                             ; D074
        sta $03BF,x                             ; D077
        lda $03BF,x                             ; D07A
        sta $0200,y                             ; D07D
        clc                                     ; D080
        adc #$08                                ; D081
        sta $0204,y                             ; D083
        lda #$03                                ; D086
        sta $0202,y                             ; D088
        sta $0206,y                             ; D08B
        lda $03BC,x                             ; D08E
        sec                                     ; D091
        sbc $41                                 ; D092
        sta $0203,y                             ; D094
        sta $0207,y                             ; D097
        lda $03BF,x                             ; D09A
        cmp #$F1                                ; D09D
        bcc LD0A8                               ; D09F
        lda #$00                                ; D0A1
        sta $03C8,x                             ; D0A3
        beq LD0AB                               ; D0A6
LD0A8:
        jsr LD0BE                               ; D0A8
LD0AB:
        lda $DF                                 ; D0AB
        clc                                     ; D0AD
        adc #$08                                ; D0AE
        sta $DF                                 ; D0B0
        tay                                     ; D0B2
LD0B3:
        inc $00                                 ; D0B3
        lda $00                                 ; D0B5
        cmp #$03                                ; D0B7
        bne LD051                               ; D0B9
        sty $DF                                 ; D0BB
        rts                                     ; D0BD
LD0BE:
        ldy #$00                                ; D0BE
LD0C0:
        lda a:$0048,y                           ; D0C0
        sta $E9                                 ; D0C3
        lda a:$004C,y                           ; D0C5
        sta $E7                                 ; D0C8
        lda $03BC,x                             ; D0CA
        sta $EA                                 ; D0CD
        lda $03BF,x                             ; D0CF
        sta $E8                                 ; D0D2
        lda #$08                                ; D0D4
        sta $EB                                 ; D0D6
        sta $EC                                 ; D0D8
        asl                                     ; D0DA
        sta $ED                                 ; D0DB
        sta $EE                                 ; D0DD
        jsr L8CC9                               ; D0DF
        bcs LD0EA                               ; D0E2
        iny                                     ; D0E4
        cpy #$04                                ; D0E5
        bne LD0C0                               ; D0E7
        rts                                     ; D0E9
LD0EA:
        stx $E2                                 ; D0EA
        lda #$01                                ; D0EC
        sta $03CB                               ; D0EE
        lda $03C8,x                             ; D0F1
        pha                                     ; D0F4
        lda #$00                                ; D0F5
        sta $03C8,x                             ; D0F7
        pla                                     ; D0FA
        and #$07                                ; D0FB
        asl                                     ; D0FD
        tax                                     ; D0FE
        lda LD10B,x                             ; D0FF
        pha                                     ; D102
        lda LD10A,x                             ; D103
        pha                                     ; D106
        ldx $E2                                 ; D107
        rts                                     ; D109
LD10A:
        .byte $19                               ; D10A .
LD10B:
        .byte $D1,$19,$D1,$45,$D1,$60,$D1,$24   ; D10B ...E.`.$
        .byte $D1,$2F,$D1,$19,$D1,$3A,$D1,$A9   ; D113 ./...:..
        .byte $03,$99,$5B,$03,$A9,$32,$99,$5F   ; D11B ..[..2._
        .byte $03,$60,$A9,$01,$99,$5B,$03,$A9   ; D123 .`...[..
        .byte $32,$99,$5F,$03,$60,$A9,$02,$99   ; D12B 2._.`...
        .byte $5B,$03,$A9,$32,$99,$5F,$03,$60   ; D133 [..2._.`
        .byte $A9,$04,$99,$5B,$03,$A9,$32,$99   ; D13B ...[..2.
        .byte $5F,$03,$60,$AD,$CA,$04,$C9,$01   ; D143 _.`.....
        .byte $D0,$08,$AD,$CB,$04,$F0,$03,$CE   ; D14B ........
        .byte $CB,$04,$86,$E0,$98,$AA,$A9,$01   ; D153 ........
        .byte $20,$2A,$8D,$A6,$E0,$60,$B9,$7A   ; D15B  *...`.z
        .byte $00,$C9,$04,$B0,$0A,$86,$DE,$48   ; D163 .......H
        .byte $98,$AA,$F6,$7A,$68,$A6,$DE,$60   ; D16B ...zh..`
        .byte $4A,$85,$E0,$84,$E1,$A9,$00,$A0   ; D173 J.......
        .byte $08,$90,$03,$18,$65,$E1,$6A,$66   ; D17B ....e.jf
        .byte $E0,$88,$D0,$F5,$A4,$E0,$60,$84   ; D183 ......`.
        .byte $01,$A0,$01,$84,$00,$0A,$B0,$04   ; D18B ........
        .byte $C5,$01,$90,$03,$E5,$01,$38,$26   ; D193 ......8&
        .byte $00,$90,$F2,$A5,$00,$60,$A5,$03   ; D19B .....`..
        .byte $C5,$01,$D0,$0D,$A5,$02,$C5,$00   ; D1A3 ........
        .byte $A9,$00,$85,$01,$B0,$02,$A9,$10   ; D1AB ........
        .byte $60,$A5,$02,$C5,$00,$D0,$13,$A5   ; D1B3 `.......
        .byte $03,$C5,$01,$A9,$FF,$85,$03,$A9   ; D1BB ........
        .byte $00,$85,$01,$A9,$18,$90,$02,$A9   ; D1C3 ........
        .byte $08,$60,$38,$A5,$03,$E5,$01,$B0   ; D1CB .`8.....
        .byte $04,$49,$FF,$69,$01,$85,$01,$A9   ; D1D3 .I.i....
        .byte $00,$2A,$85,$04,$38,$A5,$02,$E5   ; D1DB .*..8...
        .byte $00,$B0,$04,$49,$FF,$69,$01,$85   ; D1E3 ...I.i..
        .byte $00,$26,$04,$A5,$01,$C5,$00,$90   ; D1EB .&......
        .byte $06,$A4,$00,$84,$01,$85,$00,$26   ; D1F3 .......&
        .byte $04,$A5,$01,$85,$03,$A4,$00,$84   ; D1FB ........
        .byte $02,$20,$8A,$D1,$85,$00,$A0,$04   ; D203 . ......
        .byte $D9,$34,$D2,$B0,$03,$88,$D0,$F8   ; D20B .4......
        .byte $98,$85,$01,$46,$04,$90,$04,$49   ; D213 ...F...I
        .byte $FF,$69,$08,$46,$04,$B0,$04,$49   ; D21B .i.F...I
        .byte $FF,$69,$11,$46,$04,$B0,$04,$49   ; D223 .i.F...I
        .byte $FF,$69,$21,$C9,$20,$90,$02,$A9   ; D22B .i!. ...
        .byte $00,$60,$19,$4E,$89,$D2,$00,$32   ; D233 .`.N...2
        .byte $62,$8E,$B5,$D5,$ED,$FB,$00,$FB   ; D23B b.......
        .byte $ED,$D5,$B5,$8E,$62,$32,$00,$0C   ; D243 ....b2..
        .byte $18,$24,$2D,$35,$3B,$3F,$40,$3F   ; D24B .$-5.?@?
        .byte $3B,$35,$2D,$24,$18,$0C,$00,$F4   ; D253 .5-$....
        .byte $E8,$DC,$D3,$CB,$C5,$C1,$C0,$C1   ; D25B ........
        .byte $C5,$CB,$D3,$DC,$E8,$F4,$00,$0C   ; D263 ........
        .byte $18,$24,$2D,$35,$3B,$3F           ; D26B .$-5.?
LD271:
        ldx $F9                                 ; D271
LD273:
        ldy #$00                                ; D273
        lda ($F5),y                             ; D275
        inc $F5                                 ; D277
        bne LD27D                               ; D279
        inc $F6                                 ; D27B
LD27D:
        cmp #$82                                ; D27D
        bcc LD2BB                               ; D27F
        beq LD2A1                               ; D281
        cmp #$84                                ; D283
        bcs LD2AF                               ; D285
        txa                                     ; D287
        sec                                     ; D288
        sbc $F9                                 ; D289
        tay                                     ; D28B
LD28C:
        lda #$10                                ; D28C
        sta $01                                 ; D28E
LD290:
        lda $0200,y                             ; D290
        sta $0200,x                             ; D293
        inx                                     ; D296
        iny                                     ; D297
        dec $01                                 ; D298
        bne LD290                               ; D29A
LD29C:
        cpx $FA                                 ; D29C
        bcc LD273                               ; D29E
        rts                                     ; D2A0
LD2A1:
        txa                                     ; D2A1
        cmp $F9                                 ; D2A2
        bne LD2A8                               ; D2A4
        lda $FA                                 ; D2A6
LD2A8:
        sec                                     ; D2A8
        sbc #$10                                ; D2A9
        tay                                     ; D2AB
        jmp LD28C                               ; D2AC
LD2AF:
        pha                                     ; D2AF
        jsr LD2EF                               ; D2B0
        pla                                     ; D2B3
        lsr                                     ; D2B4
        jsr LD2EF                               ; D2B5
        jmp LD29C                               ; D2B8
LD2BB:
        jsr LD2EB                               ; D2BB
        ldy #$00                                ; D2BE
        lda ($F5),y                             ; D2C0
        inc $F5                                 ; D2C2
        bne LD2C8                               ; D2C4
        inc $F6                                 ; D2C6
LD2C8:
        cmp #$82                                ; D2C8
        bcs LD2D2                               ; D2CA
        jsr LD2EB                               ; D2CC
        jmp LD29C                               ; D2CF
LD2D2:
        ldy #$08                                ; D2D2
        and #$01                                ; D2D4
        beq LD2DA                               ; D2D6
        lda #$FF                                ; D2D8
LD2DA:
        sta $00                                 ; D2DA
LD2DC:
        lda $01F8,x                             ; D2DC
        eor $00                                 ; D2DF
        sta $0200,x                             ; D2E1
        inx                                     ; D2E4
        dey                                     ; D2E5
        bne LD2DC                               ; D2E6
        jmp LD29C                               ; D2E8
LD2EB:
        ora #$00                                ; D2EB
        bpl LD2FF                               ; D2ED
LD2EF:
        ldy #$08                                ; D2EF
        and #$01                                ; D2F1
        beq LD2F7                               ; D2F3
        lda #$FF                                ; D2F5
LD2F7:
        sta $0200,x                             ; D2F7
        inx                                     ; D2FA
        dey                                     ; D2FB
        bne LD2F7                               ; D2FC
        rts                                     ; D2FE
LD2FF:
        sec                                     ; D2FF
        rol                                     ; D300
        sta $00                                 ; D301
        lda #$00                                ; D303
LD305:
        bcs LD30A                               ; D305
        lda ($F5),y                             ; D307
        iny                                     ; D309
LD30A:
        sta $0200,x                             ; D30A
        inx                                     ; D30D
        asl $00                                 ; D30E
        bne LD305                               ; D310
        clc                                     ; D312
        tya                                     ; D313
        adc $F5                                 ; D314
        sta $F5                                 ; D316
        bcc LD31C                               ; D318
        inc $F6                                 ; D31A
LD31C:
        rts                                     ; D31C
        .byte $A9,$45,$85,$10,$85,$1C,$85,$1D   ; D31D .E......
        .byte $85,$1E,$85,$1F,$A9,$00,$85,$DD   ; D325 ........
        .byte $85,$45,$A9,$01,$85,$44,$85,$11   ; D32D .E...D..
        .byte $8D,$EF,$04,$4C,$C9,$8D           ; D335 ...L..
LD33B:
        lda #$0F                                ; D33B
        sta SND_CHN                             ; D33D
        lda #$30                                ; D340
        sta SQ1_VOL                             ; D342
        sta SQ2_VOL                             ; D345
        sta NOISE_VOL                           ; D348
        sta $32                                 ; D34B
        sta $3A                                 ; D34D
        sta $36                                 ; D34F
        lda #$80                                ; D351
        sta TRI_LINEAR                          ; D353
        lda #$08                                ; D356
        sta SQ1_SWEEP                           ; D358
        sta SQ2_SWEEP                           ; D35B
        lda #$00                                ; D35E
        sta SQ1_HI                              ; D360
        sta SQ2_HI                              ; D363
        sta NOISE_HI                            ; D366
        sta $33                                 ; D369
        sta $37                                 ; D36B
        sta $3B                                 ; D36D
        sta $3F                                 ; D36F
        sta $034D                               ; D371
        lda #$40                                ; D374
        sta DMC_RAW                             ; D376
        rts                                     ; D379
LD37A:
        asl                                     ; D37A
        asl                                     ; D37B
        tay                                     ; D37C
        lda LD71E,y                             ; D37D
        sta $00                                 ; D380
        lda LD71F,y                             ; D382
        sta $01                                 ; D385
        lda LD720,y                             ; D387
        and #$0C                                ; D38A
        sta $02                                 ; D38C
        lda LD720,y                             ; D38E
        lsr                                     ; D391
        lsr                                     ; D392
        lsr                                     ; D393
        lsr                                     ; D394
        sta $04                                 ; D395
        lda LD721,y                             ; D397
        sta $03                                 ; D39A
        lda $02                                 ; D39C
        bne LD3AA                               ; D39E
        lda $37                                 ; D3A0
        cmp $33                                 ; D3A2
        bcs LD3AA                               ; D3A4
        lda #$04                                ; D3A6
        sta $02                                 ; D3A8
LD3AA:
        ldy $02                                 ; D3AA
        lda $03                                 ; D3AC
        cmp a:$0033,y                           ; D3AE
        bcs LD3B4                               ; D3B1
        rts                                     ; D3B3
LD3B4:
        lda $00                                 ; D3B4
        sta a:$0020,y                           ; D3B6
        lda $01                                 ; D3B9
        sta a:$0021,y                           ; D3BB
        lda $03                                 ; D3BE
        sta a:$0033,y                           ; D3C0
        lda $04                                 ; D3C3
        sta $0311,y                             ; D3C5
        lda #$00                                ; D3C8
        sta $0321,y                             ; D3CA
        rts                                     ; D3CD
LD3CE:
        jsr LD55A                               ; D3CE
        ldx #$0C                                ; D3D1
LD3D3:
        jsr LD6C9                               ; D3D3
        jsr LD3E0                               ; D3D6
        dex                                     ; D3D9
        dex                                     ; D3DA
        dex                                     ; D3DB
        dex                                     ; D3DC
        bpl LD3D3                               ; D3DD
        rts                                     ; D3DF
LD3E0:
        lda $33,x                               ; D3E0
        bne LD3F6                               ; D3E2
        lda $02                                 ; D3E4
        bne LD42D                               ; D3E6
        cpx #$08                                ; D3E8
        beq LD3EE                               ; D3EA
        lda #$30                                ; D3EC
LD3EE:
        sta SQ1_VOL,x                           ; D3EE
        lda #$FF                                ; D3F1
        sta $32,x                               ; D3F3
        rts                                     ; D3F5
LD3F6:
        dec $0321,x                             ; D3F6
        bpl LD43D                               ; D3F9
        lda $0311,x                             ; D3FB
        sta $0321,x                             ; D3FE
        lda $21,x                               ; D401
        sta $01                                 ; D403
        lda $20,x                               ; D405
        sta $00                                 ; D407
        clc                                     ; D409
        adc #$02                                ; D40A
        sta $20,x                               ; D40C
        bcc LD412                               ; D40E
        inc $21,x                               ; D410
LD412:
        ldy #$00                                ; D412
        lda $02                                 ; D414
        and #$0F                                ; D416
        sta $04                                 ; D418
        lda ($00),y                             ; D41A
        and #$0F                                ; D41C
        cmp $04                                 ; D41E
        bcc LD42B                               ; D420
        lda ($00),y                             ; D422
        sta $02                                 ; D424
        iny                                     ; D426
        lda ($00),y                             ; D427
        sta $03                                 ; D429
LD42B:
        dec $33,x                               ; D42B
LD42D:
        lda $02                                 ; D42D
        ora #$30                                ; D42F
        cpx #$0C                                ; D431
        bne LD43E                               ; D433
        sta NOISE_VOL                           ; D435
        lda $03                                 ; D438
        sta NOISE_LO                            ; D43A
LD43D:
        rts                                     ; D43D
LD43E:
        sta SQ1_VOL,x                           ; D43E
        ldy $03                                 ; D441
        lda LD456,y                             ; D443
        sta SQ1_LO,x                            ; D446
        lda LD4A6,y                             ; D449
        cmp $32,x                               ; D44C
        beq LD455                               ; D44E
        sta $32,x                               ; D450
        sta SQ1_HI,x                            ; D452
LD455:
        rts                                     ; D455
LD456:
        .byte $F1,$7F,$13,$AD,$4D,$F3,$9D,$4C   ; D456 ....M..L
        .byte $00,$B8,$74,$34,$F8,$BF,$89,$56   ; D45E ..t4...V
        .byte $26,$F9,$CE,$A6,$80,$5C,$3A,$1A   ; D466 &.....:.
        .byte $FB,$DF,$C4,$AB,$93,$7C,$67,$52   ; D46E .....|gR
        .byte $3F,$2D,$1C,$0C,$FD,$EF,$E1,$D5   ; D476 ?-......
        .byte $C9,$BD,$B3,$A9,$9F,$96,$8E,$86   ; D47E ........
        .byte $7E,$77,$70,$6A,$64,$5E,$59,$54   ; D486 ~wpjd^YT
        .byte $4F,$4B,$46,$42,$3F,$3B,$38,$34   ; D48E OKFB?.84
        .byte $31,$2F,$2C,$29,$27,$25,$23,$21   ; D496 1/,)'%#!
        .byte $1F,$1D,$1B,$1A,$18,$17,$15,$14   ; D49E ........
LD4A6:
        .byte $07,$07,$07,$06,$06,$05,$05,$05   ; D4A6 ........
        .byte $05,$04,$04,$04,$03,$03,$03,$03   ; D4AE ........
        .byte $03,$02,$02,$02,$02,$02,$02,$02   ; D4B6 ........
        .byte $01,$01,$01,$01,$01,$01,$01,$01   ; D4BE ........
        .byte $01,$01,$01,$01,$00,$00,$00,$00   ; D4C6 ........
        .byte $00,$00,$00,$00,$00,$00,$00,$00   ; D4CE ........
        .byte $00,$00,$00,$00,$00,$00,$00,$00   ; D4D6 ........
        .byte $00,$00,$00,$00,$00,$00,$00,$00   ; D4DE ........
        .byte $00,$00,$00,$00,$00,$00,$00,$00   ; D4E6 ........
        .byte $00,$00,$00,$00,$00,$00,$00,$00   ; D4EE ........
LD4F6:
        .byte $16,$B8                           ; D4F6 ..
LD4F8:
        .byte $0E,$0B,$D7,$FF                   ; D4F8 ....
LD4FC:
        .byte $01,$02,$03,$04,$06,$08,$0C,$10   ; D4FC ........
LD504:
        asl                                     ; D504
        tax                                     ; D505
        lda LD8D8,x                             ; D506
        sta $30                                 ; D509
        sta $0342                               ; D50B
        lda LD8D9,x                             ; D50E
        sta $31                                 ; D511
        sta $0343                               ; D513
        ldx #$0C                                ; D516
        stx $034D                               ; D518
LD51B:
        lda #$FF                                ; D51B
        sta $031E,x                             ; D51D
        lda #$FA                                ; D520
        sta $22,x                               ; D522
        lda #$D4                                ; D524
        sta $23,x                               ; D526
        lda #$00                                ; D528
        sta $031F,x                             ; D52A
        sta $0320,x                             ; D52D
        sta $030E,x                             ; D530
        sta $0310,x                             ; D533
        dex                                     ; D536
        dex                                     ; D537
        dex                                     ; D538
        dex                                     ; D539
        bpl LD51B                               ; D53A
        lda #$00                                ; D53C
        sta $034C                               ; D53E
        lda #$FF                                ; D541
        sta $033E                               ; D543
        sta $033F                               ; D546
        lda #$2C                                ; D549
        sta $0340                               ; D54B
        lda #$01                                ; D54E
        sta $0341                               ; D550
        rts                                     ; D553
LD554:
        lda #$00                                ; D554
        sta $034D                               ; D556
        rts                                     ; D559
LD55A:
        lda $034D                               ; D55A
        beq LD574                               ; D55D
        lda $0340                               ; D55F
        clc                                     ; D562
        adc $033E                               ; D563
        sta $033E                               ; D566
        lda $0341                               ; D569
        adc $033F                               ; D56C
        sta $033F                               ; D56F
        bcs LD575                               ; D572
LD574:
        rts                                     ; D574
LD575:
        ldy #$00                                ; D575
        lda $033E                               ; D577
        sbc LD4F6,y                             ; D57A
        sta $033E                               ; D57D
        lda $033F                               ; D580
        sbc LD4F8,y                             ; D583
        sta $033F                               ; D586
        lda $034C                               ; D589
        beq LD594                               ; D58C
        dec $034C                               ; D58E
        jmp LD628                               ; D591
LD594:
        ldy #$00                                ; D594
        lda ($30),y                             ; D596
        inc $30                                 ; D598
        bne LD59E                               ; D59A
        inc $31                                 ; D59C
LD59E:
        sta $00                                 ; D59E
        cmp #$30                                ; D5A0
        bcc LD5B7                               ; D5A2
        and #$03                                ; D5A4
        sta $0341                               ; D5A6
        lda ($30),y                             ; D5A9
        inc $30                                 ; D5AB
        bne LD5B1                               ; D5AD
        inc $31                                 ; D5AF
LD5B1:
        sta $0340                               ; D5B1
        jmp LD594                               ; D5B4
LD5B7:
        cmp #$20                                ; D5B7
        bcc LD5F2                               ; D5B9
        beq LD61D                               ; D5BB
        cmp #$21                                ; D5BD
        bne LD5CD                               ; D5BF
        lda #$00                                ; D5C1
        sta $034D                               ; D5C3
        sta $0341                               ; D5C6
        sta $0340                               ; D5C9
        rts                                     ; D5CC
LD5CD:
        cmp #$22                                ; D5CD
        bne LD5DE                               ; D5CF
        lda $30                                 ; D5D1
        sta $0342                               ; D5D3
        lda $31                                 ; D5D6
        sta $0343                               ; D5D8
        jmp LD594                               ; D5DB
LD5DE:
        cmp #$23                                ; D5DE
        bne LD5EF                               ; D5E0
        lda $0342                               ; D5E2
        sta $30                                 ; D5E5
        lda $0343                               ; D5E7
        sta $31                                 ; D5EA
        jmp LD594                               ; D5EC
LD5EF:
        jmp LD628                               ; D5EF
LD5F2:
        and #$03                                ; D5F2
        asl                                     ; D5F4
        asl                                     ; D5F5
        tax                                     ; D5F6
        lda #$00                                ; D5F7
        sta $0310,x                             ; D5F9
        lda ($30),y                             ; D5FC
        sta $031E,x                             ; D5FE
        iny                                     ; D601
        lda ($30),y                             ; D602
        sta $031F,x                             ; D604
        iny                                     ; D607
        lda ($30),y                             ; D608
        sta $0320,x                             ; D60A
        tya                                     ; D60D
        sec                                     ; D60E
        adc $30                                 ; D60F
        sta $30                                 ; D611
        bcc LD617                               ; D613
        inc $31                                 ; D615
LD617:
        jsr LD6AE                               ; D617
        jmp LD594                               ; D61A
LD61D:
        lda ($30),y                             ; D61D
        inc $30                                 ; D61F
        bne LD625                               ; D621
        inc $31                                 ; D623
LD625:
        sta $034C                               ; D625
LD628:
        ldx #$0C                                ; D628
LD62A:
        lda $0310,x                             ; D62A
        bne LD68A                               ; D62D
LD62F:
        lda ($22,x)                             ; D62F
        cmp #$FF                                ; D631
        bne LD63A                               ; D633
        jsr LD6AE                               ; D635
        lda ($22,x)                             ; D638
LD63A:
        inc $22,x                               ; D63A
        bne LD640                               ; D63C
        inc $23,x                               ; D63E
LD640:
        cmp #$D8                                ; D640
        bcc LD652                               ; D642
        lda ($22,x)                             ; D644
        sta $0320,x                             ; D646
        inc $22,x                               ; D649
        bne LD62F                               ; D64B
        inc $23,x                               ; D64D
        jmp LD62F                               ; D64F
LD652:
        pha                                     ; D652
        and #$07                                ; D653
        tay                                     ; D655
        lda LD4FC,y                             ; D656
        sta $0310,x                             ; D659
        pla                                     ; D65C
        lsr                                     ; D65D
        lsr                                     ; D65E
        lsr                                     ; D65F
        cmp #$19                                ; D660
        bcc LD66E                               ; D662
        beq LD66B                               ; D664
        lda #$00                                ; D666
        sta $030E,x                             ; D668
LD66B:
        jmp LD68A                               ; D66B
LD66E:
        cpx #$0C                                ; D66E
        beq LD694                               ; D670
        adc $031F,x                             ; D672
        sta $030F,x                             ; D675
        lda $0320,x                             ; D678
        asl                                     ; D67B
        asl                                     ; D67C
        tay                                     ; D67D
        lda LD8BC,y                             ; D67E
        asl                                     ; D681
        asl                                     ; D682
        asl                                     ; D683
        asl                                     ; D684
        ora #$0C                                ; D685
        sta $030E,x                             ; D687
LD68A:
        dec $0310,x                             ; D68A
        dex                                     ; D68D
        dex                                     ; D68E
        dex                                     ; D68F
        dex                                     ; D690
        bpl LD62A                               ; D691
        rts                                     ; D693
LD694:
        stx $05                                 ; D694
        asl                                     ; D696
        pha                                     ; D697
        tax                                     ; D698
        lda LD8B6,x                             ; D699
        jsr LD37A                               ; D69C
        pla                                     ; D69F
        tax                                     ; D6A0
        lda LD8B7,x                             ; D6A1
        bmi LD6A9                               ; D6A4
        jsr LD37A                               ; D6A6
LD6A9:
        ldx $05                                 ; D6A9
        jmp LD68A                               ; D6AB
LD6AE:
        lda $031E,x                             ; D6AE
        asl                                     ; D6B1
        bcc LD6BD                               ; D6B2
        lda #$FA                                ; D6B4
        sta $22,x                               ; D6B6
        lda #$D4                                ; D6B8
        sta $23,x                               ; D6BA
        rts                                     ; D6BC
LD6BD:
        tay                                     ; D6BD
        lda LD8DA,y                             ; D6BE
        sta $22,x                               ; D6C1
        lda LD8DB,y                             ; D6C3
        sta $23,x                               ; D6C6
        rts                                     ; D6C8
LD6C9:
        lda $034D                               ; D6C9
        beq LD6D7                               ; D6CC
        lda $030E,x                             ; D6CE
        lsr                                     ; D6D1
        lsr                                     ; D6D2
        lsr                                     ; D6D3
        lsr                                     ; D6D4
        bne LD6DC                               ; D6D5
LD6D7:
        lda #$00                                ; D6D7
        sta $02                                 ; D6D9
        rts                                     ; D6DB
LD6DC:
        sta $02                                 ; D6DC
        lda $0320,x                             ; D6DE
        asl                                     ; D6E1
        asl                                     ; D6E2
        tay                                     ; D6E3
        lda $02                                 ; D6E4
        eor LD8BC,y                             ; D6E6
        and #$0F                                ; D6E9
        eor LD8BC,y                             ; D6EB
        sta $02                                 ; D6EE
        lda $030E,x                             ; D6F0
        sec                                     ; D6F3
        sbc LD8BD,y                             ; D6F4
        bcc LD6D7                               ; D6F7
        sta $030E,x                             ; D6F9
        lda $030F,x                             ; D6FC
        sta $03                                 ; D6FF
        lda LD8BE,y                             ; D701
        bpl LD71D                               ; D704
        lda $0310,x                             ; D706
        bne LD71D                               ; D709
        clc                                     ; D70B
        lda $033E                               ; D70C
        adc #$0B                                ; D70F
        lda $033F                               ; D711
        adc #$07                                ; D714
        bcc LD71D                               ; D716
        lda #$00                                ; D718
        sta $030E,x                             ; D71A
LD71D:
        rts                                     ; D71D
LD71E:
        .byte $62                               ; D71E b
LD71F:
        .byte $D7                               ; D71F .
LD720:
        .byte $00                               ; D720 .
LD721:
        .byte $0A,$4A,$D8,$08,$02,$4E,$D8,$08   ; D721 .J...N..
        .byte $04,$56,$D8,$0C,$02,$9E,$D7,$00   ; D729 .V......
        .byte $06,$AA,$D7,$00,$0A,$BE,$D7,$00   ; D731 ........
        .byte $0A,$0E,$D8,$00,$0A,$76,$D7,$00   ; D739 .....v..
        .byte $14,$5A,$D8,$0C,$07,$68,$D8,$0C   ; D741 .Z...h..
        .byte $03,$78,$D8,$10,$0F,$96,$D8,$3C   ; D749 .x.....<
        .byte $10,$22,$D8,$00,$0A,$36,$D8,$00   ; D751 ."...6..
        .byte $0A,$D2,$D7,$00,$14,$FA,$D7,$00   ; D759 ........
        .byte $0A,$4F,$20,$4F,$21,$4F,$22,$4F   ; D761 .O O!O"O
        .byte $23,$4F,$24,$4F,$25,$4F,$26,$4F   ; D769 #O$O%O&O
        .byte $27,$4F,$28,$4F,$29,$4F,$20,$4F   ; D771 'O(O)O O
        .byte $21,$4F,$20,$4F,$21,$4F,$22,$4F   ; D779 !O O!O"O
        .byte $23,$4F,$22,$4F,$23,$4F,$24,$4F   ; D781 #O"O#O$O
        .byte $25,$4F,$24,$4F,$25,$4F,$26,$4F   ; D789 %O$O%O&O
        .byte $27,$4F,$26,$4F,$27,$4F,$28,$4F   ; D791 'O&O'O(O
        .byte $29,$4F,$28,$4F,$29,$8F,$20,$8F   ; D799 )O(O). .
        .byte $21,$8F,$22,$8F,$23,$8F,$22,$8F   ; D7A1 !.".#.".
        .byte $21,$4F,$20,$4F,$21,$40,$22,$40   ; D7A9 !O O!@"@
        .byte $23,$4F,$24,$4F,$2F,$4F,$26,$4F   ; D7B1 #O$O/O&O
        .byte $2F,$4F,$28,$4F,$2F,$4F,$10,$4F   ; D7B9 /O(O/O.O
        .byte $11,$40,$12,$40,$13,$4F,$14,$4F   ; D7C1 .@.@.O.O
        .byte $1F,$4F,$16,$4F,$1F,$4F,$18,$4F   ; D7C9 .O.O.O.O
        .byte $1F,$4F,$10,$4F,$11,$4F,$10,$4F   ; D7D1 .O.O.O.O
        .byte $11,$40,$12,$40,$13,$40,$12,$40   ; D7D9 .@.@.@.@
        .byte $13,$4F,$14,$4F,$1F,$4F,$14,$4F   ; D7E1 .O.O.O.O
        .byte $24,$4F,$16,$4F,$1F,$4F,$16,$4F   ; D7E9 $O.O.O.O
        .byte $25,$4F,$18,$4F,$1F,$4F,$18,$4F   ; D7F1 %O.O.O.O
        .byte $26,$8F,$20,$80,$20,$8F,$20,$80   ; D7F9 &. . . .
        .byte $20,$8F,$20,$88,$20,$86,$20,$84   ; D801  . . . .
        .byte $20,$82,$20,$81,$20,$4F,$20,$4F   ; D809  . . O O
        .byte $21,$40,$22,$40,$23,$4F,$24,$4F   ; D811 !@"@#O$O
        .byte $2F,$40,$26,$40,$2F,$4F,$28,$4F   ; D819 /@&@/O(O
        .byte $2F,$4F,$20,$4F,$18,$4F,$10,$4F   ; D821 /O O.O.O
        .byte $16,$4F,$20,$4F,$14,$4F,$10,$4F   ; D829 .O O.O.O
        .byte $12,$4F,$20,$4F,$10,$4F,$20,$4F   ; D831 .O O.O O
        .byte $20,$40,$20,$40,$20,$4F,$23,$4F   ; D839  @ @ O#O
        .byte $23,$40,$26,$40,$26,$4F,$26,$4F   ; D841 #@&@&O&O
        .byte $27,$8F,$26,$8F,$25,$8F,$1F,$8F   ; D849 '.&.%...
        .byte $1B,$8F,$18,$82,$15,$06,$03,$04   ; D851 ........
        .byte $83,$0A,$55,$08,$84,$06,$04,$04   ; D859 ..U.....
        .byte $84,$03,$04,$02,$04,$01,$04,$08   ; D861 ........
        .byte $04,$08,$0E,$04,$0E,$05,$0E,$04   ; D869 ........
        .byte $0E,$03,$0E,$02,$0E,$01,$0E,$8F   ; D871 ........
        .byte $12,$4F,$0F,$8E,$0C,$0E,$0E,$8D   ; D879 .O......
        .byte $0C,$4C,$0A,$8B,$0B,$0A,$09,$89   ; D881 .L......
        .byte $06,$48,$08,$87,$07,$06,$05,$84   ; D889 .H......
        .byte $06,$42,$04,$81,$03,$0F,$0E,$0E   ; D891 .B......
        .byte $0D,$0D,$0E,$0C,$0E,$0B,$0E,$0A   ; D899 ........
        .byte $0F,$09,$0E,$08,$0E,$07,$0F,$06   ; D8A1 ........
        .byte $0E,$05,$0F,$04,$0E,$03,$0F,$02   ; D8A9 ........
        .byte $0E,$01,$0F,$01,$0F               ; D8B1 .....
LD8B6:
        .byte $0A                               ; D8B6 .
LD8B7:
        .byte $02,$01,$09,$03,$FF               ; D8B7 .....
LD8BC:
        .byte $88                               ; D8BC .
LD8BD:
        .byte $00                               ; D8BD .
LD8BE:
        .byte $00,$00,$47,$04,$00,$00,$86,$01   ; D8BE ..G.....
        .byte $00,$00,$87,$02,$00,$00,$87,$06   ; D8C6 ........
        .byte $00,$00,$05,$00,$00,$00,$88,$04   ; D8CE ........
        .byte $00,$00                           ; D8D6 ..
LD8D8:
        .byte $E8                               ; D8D8 .
LD8D9:
        .byte $D8                               ; D8D9 .
LD8DA:
        .byte $A4                               ; D8DA .
LD8DB:
        .byte $D9,$38,$D9,$4B,$D9,$5E,$D9,$75   ; D8DB .8.K.^.u
        .byte $D9,$8E,$D9,$A2,$D9,$32,$1C,$01   ; D8E3 .....2..
        .byte $06,$1B,$01,$02,$06,$1B,$00,$03   ; D8EB ........
        .byte $00,$00,$00,$00,$01,$1B,$01,$20   ; D8F3 ....... 
        .byte $1F,$00,$02,$1B,$01,$20,$1F,$00   ; D8FB ..... ..
        .byte $03,$1B,$01,$20,$1F,$00,$04,$1B   ; D903 ... ....
        .byte $01,$20,$1F,$22,$03,$00,$00,$00   ; D90B . ."....
        .byte $00,$01,$1B,$01,$01,$05,$1B,$01   ; D913 ........
        .byte $20,$1F,$00,$02,$1B,$01,$20,$1F   ; D91B  ..... .
        .byte $00,$03,$1B,$01,$01,$06,$1B,$01   ; D923 ........
        .byte $20,$1F,$03,$06,$00,$00,$00,$04   ; D92B  .......
        .byte $1B,$01,$20,$1F,$23,$79,$D0,$41   ; D933 .. .#y.A
        .byte $D0,$50,$58,$69,$D0,$41,$D0,$31   ; D93B .PXi.A.1
        .byte $41,$D0,$50,$D0,$50,$69,$7B,$43   ; D943 A.P.Pi{C
        .byte $79,$D0,$41,$D0,$50,$58,$69,$D0   ; D94B y.A.PXi.
        .byte $41,$D0,$31,$41,$D0,$50,$D0,$50   ; D953 A.1A.P.P
        .byte $69,$33,$43,$59,$78,$41,$48,$50   ; D95B i3CYxAHP
        .byte $58,$69,$58,$40,$D0,$40,$69,$41   ; D963 XiX@.@iA
        .byte $30,$41,$30,$51,$69,$40,$D0,$40   ; D96B 0A0Qi@.@
        .byte $50,$69,$59,$78,$40,$40,$48,$50   ; D973 PiYx@@HP
        .byte $58,$69,$58,$40,$D0,$40,$40,$D0   ; D97B XiX@.@@.
        .byte $41,$30,$41,$30,$69,$79,$40,$D0   ; D983 A0A0iy@.
        .byte $40,$50,$69,$D1,$D0,$19,$D0,$31   ; D98B @Pi....1
        .byte $41,$D0,$69,$D1,$D0,$19,$D0,$31   ; D993 A.i....1
        .byte $D1,$D0,$51,$D1,$69,$D1,$FF,$D5   ; D99B ..Q.i...
        .byte $FF,$00,$00,$01,$09,$00,$00,$01   ; D9A3 ........
        .byte $09,$09,$01,$FF                   ; D9AB ....
Reset:
        lda #$00                                ; D9AF
        sta PPUCTRL                             ; D9B1
        sta PPUMASK                             ; D9B4
        sei                                     ; D9B7
        ldx #$FF                                ; D9B8
        txs                                     ; D9BA
LD9BB:
        lda PPUSTATUS                           ; D9BB
        bpl LD9BB                               ; D9BE
LD9C0:
        lda PPUSTATUS                           ; D9C0
        bpl LD9C0                               ; D9C3
        lda #$00                                ; D9C5
        sta SND_CHN                             ; D9C7
        lda #$3F                                ; D9CA
        sta PPUADDR                             ; D9CC
        lda #$00                                ; D9CF
        sta PPUADDR                             ; D9D1
        ldx #$00                                ; D9D4
LD9D6:
        lda #$31                                ; D9D6
        sta PPUDATA                             ; D9D8
        lda #$0F                                ; D9DB
        sta PPUDATA                             ; D9DD
        lda LDCFB,x                             ; D9E0
        sta PPUDATA                             ; D9E3
        lda #$30                                ; D9E6
        sta PPUDATA                             ; D9E8
        inx                                     ; D9EB
        cpx #$08                                ; D9EC
        bne LD9D6                               ; D9EE
        lda #$3F                                ; D9F0
        sta PPUADDR                             ; D9F2
        lda #$07                                ; D9F5
        sta PPUADDR                             ; D9F7
        lda #$17                                ; D9FA
        sta PPUDATA                             ; D9FC
        jsr LDA5C                               ; D9FF
        ldx #$00                                ; DA02
        txa                                     ; DA04
LDA05:
        sta $00,x                               ; DA05
        sta $0100,x                             ; DA07
        sta $0300,x                             ; DA0A
        sta $0400,x                             ; DA0D
        sta $0500,x                             ; DA10
        sta $0600,x                             ; DA13
        sta $0700,x                             ; DA16
        inx                                     ; DA19
        bne LDA05                               ; DA1A
        ldx #$01                                ; DA1C
        stx JOY1                                ; DA1E
        dex                                     ; DA21
        stx JOY1                                ; DA22
        jsr L80B4                               ; DA25
        jsr L80B4                               ; DA28
        jsr L80B4                               ; DA2B
        lda $16                                 ; DA2E
        cmp #$10                                ; DA30
        bne LDA3C                               ; DA32
        lda $17                                 ; DA34
        cmp #$20                                ; DA36
        bne LDA3C                               ; DA38
        inc $12                                 ; DA3A
LDA3C:
        lda #$21                                ; DA3C
        sta $E4                                 ; DA3E
        lda #$69                                ; DA40
        sta $10                                 ; DA42
        lda #$5A                                ; DA44
        sta $1C                                 ; DA46
        lda #$A5                                ; DA48
        sta $1D                                 ; DA4A
        lda #$53                                ; DA4C
        sta $1E                                 ; DA4E
        lda #$76                                ; DA50
        sta $1F                                 ; DA52
        lda #$88                                ; DA54
        sta PPUCTRL                             ; DA56
        jmp LA9B1                               ; DA59
LDA5C:
        lda #$40                                ; DA5C
        sta $0F                                 ; DA5E
        lda #$00                                ; DA60
        sta PPUADDR                             ; DA62
        sta PPUADDR                             ; DA65
        lda #$07                                ; DA68
        sta $F5                                 ; DA6A
        lda #$DD                                ; DA6C
        sta $F6                                 ; DA6E
        lda #$00                                ; DA70
        sta $F9                                 ; DA72
        lda #$80                                ; DA74
        sta $FA                                 ; DA76
LDA78:
        jsr LD271                               ; DA78
        ldx #$00                                ; DA7B
LDA7D:
        lda $0200,x                             ; DA7D
        sta PPUDATA                             ; DA80
        inx                                     ; DA83
        cpx #$80                                ; DA84
        bne LDA7D                               ; DA86
        dec $0F                                 ; DA88
        bne LDA78                               ; DA8A
        rts                                     ; DA8C
NMI:
        pha                                     ; DA8D
        inc $13                                 ; DA8E
        lda #$00                                ; DA90
        sta OAMADDR                             ; DA92
        sta $DF                                 ; DA95
        lda #$02                                ; DA97
        sta OAMDMA                              ; DA99
        lda $DB                                 ; DA9C
        bne LDAA2                               ; DA9E
        pla                                     ; DAA0
        rti                                     ; DAA1
LDAA2:
        dec $DB                                 ; DAA2
        lda #$3F                                ; DAA4
        sta PPUADDR                             ; DAA6
        lda #$1E                                ; DAA9
        sta PPUADDR                             ; DAAB
        lda $E4                                 ; DAAE
        sta PPUDATA                             ; DAB0
        lda $13                                 ; DAB3
        and #$01                                ; DAB5
        beq LDAC8                               ; DAB7
        lda $E4                                 ; DAB9
        clc                                     ; DABB
        adc #$01                                ; DABC
        sta $E4                                 ; DABE
        cmp #$2C                                ; DAC0
        bne LDAC8                               ; DAC2
        lda #$21                                ; DAC4
        sta $E4                                 ; DAC6
LDAC8:
        lda $9E                                 ; DAC8
        beq LDADD                               ; DACA
        sta PPUADDR                             ; DACC
        lda $A3                                 ; DACF
        sta PPUADDR                             ; DAD1
        lda $A8                                 ; DAD4
        sta PPUDATA                             ; DAD6
        lda #$00                                ; DAD9
        sta $9E                                 ; DADB
LDADD:
        lda $9F                                 ; DADD
        beq LDAF2                               ; DADF
        sta PPUADDR                             ; DAE1
        lda $A4                                 ; DAE4
        sta PPUADDR                             ; DAE6
        lda $A9                                 ; DAE9
        sta PPUDATA                             ; DAEB
        lda #$00                                ; DAEE
        sta $9F                                 ; DAF0
LDAF2:
        lda $A0                                 ; DAF2
        beq LDB07                               ; DAF4
        sta PPUADDR                             ; DAF6
        lda $A5                                 ; DAF9
        sta PPUADDR                             ; DAFB
        lda $AA                                 ; DAFE
        sta PPUDATA                             ; DB00
        lda #$00                                ; DB03
        sta $A0                                 ; DB05
LDB07:
        lda $A1                                 ; DB07
        beq LDB1C                               ; DB09
        sta PPUADDR                             ; DB0B
        lda $A6                                 ; DB0E
        sta PPUADDR                             ; DB10
        lda $AB                                 ; DB13
        sta PPUDATA                             ; DB15
        lda #$00                                ; DB18
        sta $A1                                 ; DB1A
LDB1C:
        lda $A2                                 ; DB1C
        beq LDB31                               ; DB1E
        sta PPUADDR                             ; DB20
        lda $A7                                 ; DB23
        sta PPUADDR                             ; DB25
        lda $AC                                 ; DB28
        sta PPUDATA                             ; DB2A
        lda #$00                                ; DB2D
        sta $A2                                 ; DB2F
LDB31:
        lda $7E                                 ; DB31
        beq LDB5F                               ; DB33
        sta PPUADDR                             ; DB35
        lda $82                                 ; DB38
        sta PPUADDR                             ; DB3A
        lda $8E                                 ; DB3D
        sta PPUDATA                             ; DB3F
        lda $92                                 ; DB42
        sta PPUDATA                             ; DB44
        lda $86                                 ; DB47
        sta PPUADDR                             ; DB49
        lda $8A                                 ; DB4C
        sta PPUADDR                             ; DB4E
        lda $96                                 ; DB51
        sta PPUDATA                             ; DB53
        lda $9A                                 ; DB56
        sta PPUDATA                             ; DB58
        lda #$00                                ; DB5B
        sta $7E                                 ; DB5D
LDB5F:
        lda $7F                                 ; DB5F
        beq LDB8D                               ; DB61
        sta PPUADDR                             ; DB63
        lda $83                                 ; DB66
        sta PPUADDR                             ; DB68
        lda $8F                                 ; DB6B
        sta PPUDATA                             ; DB6D
        lda $93                                 ; DB70
        sta PPUDATA                             ; DB72
        lda $87                                 ; DB75
        sta PPUADDR                             ; DB77
        lda $8B                                 ; DB7A
        sta PPUADDR                             ; DB7C
        lda $97                                 ; DB7F
        sta PPUDATA                             ; DB81
        lda $9B                                 ; DB84
        sta PPUDATA                             ; DB86
        lda #$00                                ; DB89
        sta $7F                                 ; DB8B
LDB8D:
        lda $80                                 ; DB8D
        beq LDBBB                               ; DB8F
        sta PPUADDR                             ; DB91
        lda $84                                 ; DB94
        sta PPUADDR                             ; DB96
        lda $90                                 ; DB99
        sta PPUDATA                             ; DB9B
        lda $94                                 ; DB9E
        sta PPUDATA                             ; DBA0
        lda $88                                 ; DBA3
        sta PPUADDR                             ; DBA5
        lda $8C                                 ; DBA8
        sta PPUADDR                             ; DBAA
        lda $98                                 ; DBAD
        sta PPUDATA                             ; DBAF
        lda $9C                                 ; DBB2
        sta PPUDATA                             ; DBB4
        lda #$00                                ; DBB7
        sta $80                                 ; DBB9
LDBBB:
        lda $81                                 ; DBBB
        beq LDBE9                               ; DBBD
        sta PPUADDR                             ; DBBF
        lda $85                                 ; DBC2
        sta PPUADDR                             ; DBC4
        lda $91                                 ; DBC7
        sta PPUDATA                             ; DBC9
        lda $95                                 ; DBCC
        sta PPUDATA                             ; DBCE
        lda $89                                 ; DBD1
        sta PPUADDR                             ; DBD3
        lda $8D                                 ; DBD6
        sta PPUADDR                             ; DBD8
        lda $99                                 ; DBDB
        sta PPUDATA                             ; DBDD
        lda $9D                                 ; DBE0
        sta PPUDATA                             ; DBE2
        lda #$00                                ; DBE5
        sta $81                                 ; DBE7
LDBE9:
        lda $42                                 ; DBE9
        beq LDBF0                               ; DBEB
        jmp LDC45                               ; DBED
LDBF0:
        lda $12                                 ; DBF0
        beq LDBF7                               ; DBF2
        jmp LDC45                               ; DBF4
LDBF7:
        lda #$20                                ; DBF7
        sta PPUADDR                             ; DBF9
        lda #$42                                ; DBFC
        sta PPUADDR                             ; DBFE
        jsr LDC59                               ; DC01
        lda #$20                                ; DC04
        sta PPUADDR                             ; DC06
        lda #$62                                ; DC09
        sta PPUADDR                             ; DC0B
        lda $C9                                 ; DC0E
        sta PPUDATA                             ; DC10
        lda $CA                                 ; DC13
        sta PPUDATA                             ; DC15
        lda $CB                                 ; DC18
        sta PPUDATA                             ; DC1A
        lda $CC                                 ; DC1D
        sta PPUDATA                             ; DC1F
        lda $CD                                 ; DC22
        sta PPUDATA                             ; DC24
        lda $CE                                 ; DC27
        sta PPUDATA                             ; DC29
        lda $CF                                 ; DC2C
        sta PPUDATA                             ; DC2E
        lda $D0                                 ; DC31
        sta PPUDATA                             ; DC33
        lda $D1                                 ; DC36
        sta PPUDATA                             ; DC38
        lda $D2                                 ; DC3B
        sta PPUDATA                             ; DC3D
        lda $D3                                 ; DC40
        sta PPUDATA                             ; DC42
LDC45:
        bit PPUSTATUS                           ; DC45
        lda $41                                 ; DC48
        sta PPUSCROLL                           ; DC4A
        lda #$00                                ; DC4D
        sta PPUSCROLL                           ; DC4F
        lda #$88                                ; DC52
        sta PPUCTRL                             ; DC54
        pla                                     ; DC57
        rti                                     ; DC58
LDC59:
        lda $AD                                 ; DC59
        sta PPUDATA                             ; DC5B
        lda $AE                                 ; DC5E
        sta PPUDATA                             ; DC60
        lda $AF                                 ; DC63
        sta PPUDATA                             ; DC65
        lda $B0                                 ; DC68
        sta PPUDATA                             ; DC6A
        lda $B1                                 ; DC6D
        sta PPUDATA                             ; DC6F
        lda $B2                                 ; DC72
        sta PPUDATA                             ; DC74
        lda $B3                                 ; DC77
        sta PPUDATA                             ; DC79
        lda $B4                                 ; DC7C
        sta PPUDATA                             ; DC7E
        lda $B5                                 ; DC81
        sta PPUDATA                             ; DC83
        lda $B6                                 ; DC86
        sta PPUDATA                             ; DC88
        lda $B7                                 ; DC8B
        sta PPUDATA                             ; DC8D
        lda $B8                                 ; DC90
        sta PPUDATA                             ; DC92
        lda $B9                                 ; DC95
        sta PPUDATA                             ; DC97
        lda $BA                                 ; DC9A
        sta PPUDATA                             ; DC9C
        lda $BB                                 ; DC9F
        sta PPUDATA                             ; DCA1
        lda $BC                                 ; DCA4
        sta PPUDATA                             ; DCA6
        lda $BD                                 ; DCA9
        sta PPUDATA                             ; DCAB
        lda $BE                                 ; DCAE
        sta PPUDATA                             ; DCB0
        lda $BF                                 ; DCB3
        sta PPUDATA                             ; DCB5
        lda $C0                                 ; DCB8
        sta PPUDATA                             ; DCBA
        lda $C1                                 ; DCBD
        sta PPUDATA                             ; DCBF
        lda $C2                                 ; DCC2
        sta PPUDATA                             ; DCC4
        lda $C3                                 ; DCC7
        sta PPUDATA                             ; DCC9
        lda $C4                                 ; DCCC
        sta PPUDATA                             ; DCCE
        lda $C5                                 ; DCD1
        sta PPUDATA                             ; DCD3
        lda $C6                                 ; DCD6
        sta PPUDATA                             ; DCD8
        lda $C7                                 ; DCDB
        sta PPUDATA                             ; DCDD
        lda $C8                                 ; DCE0
        sta PPUDATA                             ; DCE2
        rts                                     ; DCE5
LDCE6:
        lda #$20                                ; DCE6
        ldx #$00                                ; DCE8
LDCEA:
        sta $AD,x                               ; DCEA
        inx                                     ; DCEC
        cpx #$1C                                ; DCED
        bne LDCEA                               ; DCEF
        ldx #$00                                ; DCF1
LDCF3:
        sta $C9,x                               ; DCF3
        inx                                     ; DCF5
        cpx #$0C                                ; DCF6
        bne LDCF3                               ; DCF8
        rts                                     ; DCFA
LDCFB:
        .byte $16,$29,$03,$28,$01,$16,$27,$21   ; DCFB .).(..'!
        .byte $31,$36,$38,$23,$81,$00,$FF,$81   ; DD03 168#....
        .byte $FD,$E1,$E7,$FF,$E7,$FF,$1C,$3C   ; DD0B .......<
        .byte $7E,$FF,$7E,$3C,$10,$00,$3C,$5A   ; DD13 ~.~<..<Z
        .byte $7E,$66,$3C,$00,$08,$36,$6B,$49   ; DD1B ~f<..6kI
        .byte $41,$22,$14,$08,$80,$08,$36,$6B   ; DD23 A"....6k
        .byte $49,$41,$22,$14,$08,$10,$00,$10   ; DD2B IA".....
        .byte $30,$38,$18,$08,$00,$08,$36,$6B   ; DD33 08....6k
        .byte $49,$41,$22,$14,$08,$08,$00,$14   ; DD3B IA".....
        .byte $36,$3E,$1C,$08,$00,$68,$38,$FE   ; DD43 6>...h8.
        .byte $7C,$38,$10,$30,$00,$10,$7C,$38   ; DD4B |8.0..|8
        .byte $10,$00,$00,$00,$18,$38,$7F,$FF   ; DD53 .....8..
        .byte $7F,$38,$18,$40,$00,$10,$30,$7E   ; DD5B .8.@..0~
        .byte $30,$10,$00,$0B,$10,$38,$7C,$FE   ; DD63 0....8|.
        .byte $38,$06,$00,$10,$38,$7C,$10,$00   ; DD6B 8...8|..
        .byte $84,$01,$00,$65,$55,$65,$45,$47   ; DD73 ...eUeEG
        .byte $00,$80,$01,$00,$75,$45,$77,$15   ; DD7B ....uEw.
        .byte $75,$00,$80,$00,$3C,$42,$81,$BF   ; DD83 u...<B..
        .byte $81,$FF,$7E,$3C,$00,$00,$3C,$7E   ; DD8B ..~<..<~
        .byte $40,$7E,$76,$3C,$00,$1C,$3C,$7E   ; DD93 @~v<..<~
        .byte $FF,$7E,$3C,$10,$00,$3C,$5A,$7E   ; DD9B .~<..<Z~
        .byte $6E,$3C,$00,$00,$AA,$55,$AA,$55   ; DDA3 n<...U.U
        .byte $AA,$55,$AA,$55,$82,$80,$00,$AA   ; DDAB .U.U....
        .byte $55,$AA,$55,$AA,$55,$AA,$55,$00   ; DDB3 U.U.U.U.
        .byte $AA,$55,$AA,$55,$AA,$55,$AA,$55   ; DDBB .U.U.U.U
        .byte $80,$08,$FF,$C3,$A5,$99,$A5,$C3   ; DDC3 ........
        .byte $FF,$82,$00,$00,$18,$1C,$FE,$FF   ; DDCB ........
        .byte $FE,$1C,$18,$40,$00,$08,$0C,$7E   ; DDD3 ...@...~
        .byte $0C,$08,$00,$08,$3C,$42,$99,$85   ; DDDB ....<B..
        .byte $99,$42,$3C,$80,$00,$3C,$6A,$D5   ; DDE3 .B<..<j.
        .byte $BF,$D5,$AB,$56,$3C,$00,$00,$28   ; DDEB ...V<..(
        .byte $54,$00,$54,$22,$14,$00,$00,$08   ; DDF3 T.T"....
        .byte $1C,$2A,$18,$0C,$2A,$1C,$08,$80   ; DDFB .*..*...
        .byte $1C,$3C,$7E,$FF,$7E,$3C,$10,$00   ; DE03 .<~.~<..
        .byte $3C,$6E,$62,$7E,$3C,$00,$00,$08   ; DE0B <nb~<...
        .byte $1C,$2A,$18,$0C,$2A,$1C,$08,$3E   ; DE13 .*..*..>
        .byte $60,$C0,$60,$84,$84,$05,$00,$04   ; DE1B `.`.....
        .byte $0A,$0E,$0A,$00,$80,$01,$00,$0C   ; DE23 ........
        .byte $4A,$EC,$4A,$0C,$00,$80,$13,$24   ; DE2B J.J....$
        .byte $43,$A4,$18,$24,$17,$18,$3C,$18   ; DE33 C..$..<.
        .byte $00,$00,$22,$E2,$42,$24,$18,$24   ; DE3B ..".B$.$
        .byte $22,$66,$47,$1C,$3C,$18,$00,$87   ; DE43 "fG.<...
        .byte $86,$85,$84,$72,$18,$00,$18,$00   ; DE4B ...r....
        .byte $80,$6F,$24,$00,$80,$03,$36,$FF   ; DE53 .o$...6.
        .byte $66,$FF,$6C,$00,$80,$00,$08,$1C   ; DE5B f.l.....
        .byte $2A,$18,$0C,$2A,$1C,$08,$80,$00   ; DE63 *..*....
        .byte $44,$A4,$48,$08,$10,$12,$25,$22   ; DE6B D.H...%"
        .byte $80,$04,$70,$C8,$C1,$6E,$CC,$78   ; DE73 ..p..n.x
        .byte $00,$80,$0F,$18,$08,$10,$00,$80   ; DE7B ........
        .byte $1C,$0C,$18,$30,$18,$0C,$80,$1C   ; DE83 ...0....
        .byte $30,$18,$0C,$18,$30,$80,$03,$08   ; DE8B 0...0...
        .byte $2A,$1C,$2A,$08,$00,$80,$25,$00   ; DE93 *.*...%.
        .byte $08,$3E,$08,$00,$80,$78,$00,$18   ; DE9B .>...x..
        .byte $08,$10,$80,$67,$00,$7E,$00,$80   ; DEA3 ...g.~..
        .byte $7A,$00,$18,$00,$80,$55,$04,$08   ; DEAB z....U..
        .byte $10,$20,$80,$04,$3C,$66,$6E,$76   ; DEB3 . ..<fnv
        .byte $66,$3C,$00,$80,$1E,$18,$38,$18   ; DEBB f<....8.
        .byte $00,$80,$00,$3C,$46,$06,$1C,$30   ; DEC3 ...<F..0
        .byte $60,$7E,$00,$80,$00,$7E,$0C,$18   ; DECB `~...~..
        .byte $3C,$06,$46,$3C,$00,$80,$02,$0E   ; DED3 <.F<....
        .byte $16,$26,$46,$7F,$06,$00,$80,$08   ; DEDB .&F.....
        .byte $7E,$60,$7C,$06,$46,$3C,$00,$80   ; DEE3 ~`|.F<..
        .byte $04,$1C,$30,$60,$7C,$66,$3C,$00   ; DEEB ..0`|f<.
        .byte $80,$26,$7E,$06,$0C,$18,$00,$80   ; DEF3 .&~.....
        .byte $24,$3C,$66,$3C,$66,$3C,$00,$80   ; DEFB $<f<f<..
        .byte $20,$3C,$66,$3E,$06,$0C,$38,$00   ; DF03  <f>..8.
        .byte $80,$2A,$00,$18,$00,$18,$00,$80   ; DF0B .*......
        .byte $28,$00,$18,$00,$18,$08,$10,$80   ; DF13 (.......
        .byte $01,$00,$0C,$18,$30,$18,$0C,$00   ; DF1B ....0...
        .byte $80,$43,$00,$7E,$00,$7E,$00,$80   ; DF23 .C.~.~..
        .byte $01,$00,$30,$18,$0C,$18,$30,$00   ; DF2B ..0...0.
        .byte $80,$00,$3C,$46,$06,$0C,$18,$00   ; DF33 ..<F....
        .byte $18,$00,$80,$08,$3C,$42,$99,$A5   ; DF3B ....<B..
        .byte $9A,$40,$3C,$80,$26,$3C,$66,$7E   ; DF43 .@<.&<f~
        .byte $66,$00,$80,$24,$7C,$66,$7C,$66   ; DF4B f..$|f|f
        .byte $7C,$00,$80,$18,$3C,$62,$60,$62   ; DF53 |...<b`b
        .byte $3C,$00,$80,$3C,$7C,$66,$7C,$00   ; DF5B <..<|f|.
        .byte $80,$24,$7E,$60,$7C,$60,$7E,$00   ; DF63 .$~`|`~.
        .byte $80,$26,$7E,$60,$7C,$60,$00,$80   ; DF6B .&~`|`..
        .byte $04,$3C,$62,$60,$6E,$66,$3C,$00   ; DF73 .<b`nf<.
        .byte $80,$66,$66,$7E,$66,$00,$80,$7E   ; DF7B .ff~f..~
        .byte $18,$00,$80,$74,$06,$66,$3C,$00   ; DF83 ...t.f<.
        .byte $80,$00,$66,$6C,$78,$70,$78,$6C   ; DF8B ..flxpxl
        .byte $66,$00,$80,$7C,$60,$7E,$00,$80   ; DF93 f..|`~..
        .byte $02,$83,$C7,$EF,$BB,$93,$83,$00   ; DF9B ........
        .byte $80,$00,$61,$71,$79,$5D,$4F,$47   ; DFA3 ..aqy]OG
        .byte $43,$00,$80,$3C,$3C,$66,$3C,$00   ; DFAB C..<<f<.
        .byte $80,$26,$7C,$66,$7C,$60,$00,$80   ; DFB3 .&|f|`..
        .byte $3C,$3C,$66,$3C,$06,$80,$26,$7C   ; DFBB <<f<..&|
        .byte $66,$7C,$66,$00,$80,$00,$1C,$32   ; DFC3 f|f....2
        .byte $38,$1C,$0E,$26,$1C,$00,$80,$3E   ; DFCB 8..&...>
        .byte $7E,$18,$00,$80,$7C,$66,$3C,$00   ; DFD3 ~...|f<.
        .byte $80,$78,$66,$64,$78,$00,$80,$78   ; DFDB .xfdx..x
        .byte $DB,$DA,$FC,$00,$80,$66,$66,$3C   ; DFE3 .....ff<
        .byte $66,$00,$80,$66,$66,$3C,$18,$00   ; DFEB f..ff<..
        .byte $80,$00,$7E,$06,$0C,$18,$30,$60   ; DFF3 ..~...0`
        .byte $7E,$00,$80,$3E,$1C,$18,$1C,$80   ; DFFB ~..>....
        .byte $55,$20,$10,$08,$04,$80,$3E,$38   ; E003 U ....>8
        .byte $18,$38,$80,$0F,$08,$14,$22,$00   ; E00B .8....".
        .byte $80,$7E,$00,$FF,$80,$0F,$10,$20   ; E013 .~..... 
        .byte $30,$00,$80,$40,$00,$3C,$06,$3E   ; E01B 0..@.<.>
        .byte $66,$3E,$00,$80,$4C,$60,$7C,$66   ; E023 f>..L`|f
        .byte $7C,$00,$80,$40,$00,$3C,$62,$60   ; E02B |..@.<b`
        .byte $62,$3C,$00,$80,$4C,$06,$3E,$66   ; E033 b<..L.>f
        .byte $3E,$00,$80,$40,$00,$3C,$66,$7E   ; E03B >..@.<f~
        .byte $60,$3C,$00,$80,$0E,$0E,$18,$3C   ; E043 `<.....<
        .byte $18,$00,$80,$48,$00,$3E,$66,$3E   ; E04B ...H.>f>
        .byte $06,$3C,$80,$4E,$60,$7C,$66,$00   ; E053 .<.N`|f.
        .byte $80,$1E,$18,$00,$18,$00,$80,$1C   ; E05B ........
        .byte $06,$00,$06,$26,$1C,$80,$40,$60   ; E063 ...&..@`
        .byte $66,$6C,$78,$6C,$66,$00,$80,$3E   ; E06B flxlf..>
        .byte $38,$18,$00,$80,$4E,$00,$FE,$DB   ; E073 8...N...
        .byte $00,$80,$4E,$00,$7C,$66,$00,$80   ; E07B ..N.|f..
        .byte $4C,$00,$3C,$66,$3C,$00,$80,$4C   ; E083 L.<f<..L
        .byte $00,$7C,$66,$7C,$60,$80,$4C,$00   ; E08B .|f|`.L.
        .byte $3E,$66,$3E,$06,$80,$46,$00,$36   ; E093 >f>..F.6
        .byte $3E,$30,$00,$80,$40,$00,$3E,$60   ; E09B >0..@.>`
        .byte $3C,$06,$7C,$00,$80,$4C,$18,$3C   ; E0A3 <.|..L.<
        .byte $18,$0C,$00,$80,$5C,$00,$66,$3E   ; E0AB ......f>
        .byte $00,$80,$58,$00,$66,$64,$78,$00   ; E0B3 ..X.fdx.
        .byte $80,$58,$00,$DB,$DA,$FC,$00,$80   ; E0BB .X......
        .byte $52,$00,$66,$3C,$66,$00,$80,$58   ; E0C3 R.f<f..X
        .byte $00,$66,$3E,$06,$3C,$80,$40,$00   ; E0CB .f>.<.@.
        .byte $7E,$0C,$18,$30,$7E,$00,$80,$24   ; E0D3 ~..0~..$
        .byte $1C,$30,$E0,$30,$1C,$00,$80,$7F   ; E0DB .0.0....
        .byte $18,$80,$24,$E0,$30,$1C,$30,$E0   ; E0E3 ..$.0.0.
        .byte $00,$80,$1F,$32,$4C,$00,$80,$01   ; E0EB ...2L...
        .byte $00,$01,$02,$44,$28,$10,$00,$80   ; E0F3 ...D(...
        .byte $3E,$FF,$81,$FF,$83,$61,$00,$30   ; E0FB >....a.0
        .byte $24,$0C,$00,$48,$00,$42,$00,$81   ; E103 $..H.B..
        .byte $00,$24,$2A,$10,$28,$44,$82,$FE   ; E10B .$*.(D..
        .byte $0A,$82,$10,$92,$38,$7C,$00,$00   ; E113 ....8|..
        .byte $04,$09,$34,$6A,$54,$2A,$56,$2C   ; E11B ..4jT*V,
        .byte $07,$04,$09,$00,$21,$00,$2B,$10   ; E123 ....!.+.
        .byte $38,$7C,$FE,$2A,$00,$10,$38,$7C   ; E12B 8|.*..8|
        .byte $00,$00,$55,$80,$01,$80,$01,$80   ; E133 ..U.....
        .byte $01,$AA,$00,$FE,$81,$80,$81,$80   ; E13B ........
        .byte $81,$80,$D5,$00,$55,$80,$01,$80   ; E143 ....U...
        .byte $01,$80,$01,$AA,$00,$FE,$D5,$AA   ; E14B ........
        .byte $D5,$AA,$D5,$AA,$D5,$84,$84,$5F   ; E153 ......._
        .byte $FF,$C0,$3F,$00,$7F,$40,$FF,$03   ; E15B ..?..@..
        .byte $01,$03,$01,$03,$01,$00,$00,$FE   ; E163 ........
        .byte $FC,$FE,$FC,$FE,$FC,$FE,$7C,$C0   ; E16B ......|.
        .byte $EA,$FF,$7C,$7F,$55,$00,$00,$03   ; E173 ..|.U...
        .byte $01,$03,$01,$03,$01,$AB,$FF,$83   ; E17B ........
        .byte $55,$FF,$C0,$CF,$CC,$33,$00,$7F   ; E183 U....3..
        .byte $70,$77,$55,$FF,$00,$FF,$00,$33   ; E18B pwU....3
        .byte $00,$FF,$00,$FF,$55,$FF,$01,$F1   ; E193 ....U...
        .byte $11,$33,$00,$FE,$0E,$EE,$07,$FF   ; E19B .3......
        .byte $80,$FF,$7F,$00,$1F,$00,$7F,$00   ; E1A3 ........
        .byte $17,$FF,$00,$FF,$00,$1F,$00,$FF   ; E1AB ........
        .byte $00,$07,$FF,$01,$FF,$FE,$00,$1F   ; E1B3 ........
        .byte $00,$FE,$00,$17,$55,$00,$55,$00   ; E1BB ....U.U.
        .byte $1F,$00,$55,$00,$20,$FF,$80,$FF   ; E1C3 ..U. ...
        .byte $08,$07,$08,$FF,$2F,$00,$7F,$00   ; E1CB ..../...
        .byte $20,$FF,$01,$FF,$10,$E0,$10,$FF   ; E1D3  .......
        .byte $2F,$00,$FE,$00,$07,$FF,$AA,$FF   ; E1DB /.......
        .byte $55,$00,$1F,$00,$55,$00,$84,$84   ; E1E3 U...U...
        .byte $11,$0F,$3F,$7F,$FF,$84,$CC,$79   ; E1EB ..?....y
        .byte $00,$7B,$33,$18,$FE,$FD,$FF,$D0   ; E1F3 .{3.....
        .byte $D9,$59,$18,$0E,$11,$01,$2F,$27   ; E1FB .Y..../'
        .byte $A7,$54,$CD,$FF,$7F,$3F,$0F,$5F   ; E203 .T...?._
        .byte $32,$00,$1C,$19,$99,$FF,$FE,$F0   ; E20B 2.......
        .byte $1C,$E7,$67,$01,$0E,$70,$7F,$CC   ; E213 ..g..p..
        .byte $7F,$77,$08,$FF,$FE,$FC,$F8,$FC   ; E21B .w......
        .byte $FE,$FF,$81,$7F,$11,$83,$07,$FF   ; E223 ........
        .byte $AA,$FF,$7F,$00,$1F,$00,$7F,$00   ; E22B ........
        .byte $17,$FF,$AA,$FF,$00,$1F,$00,$FF   ; E233 ........
        .byte $00,$07,$FF,$AB,$FF,$FE,$00,$1F   ; E23B ........
        .byte $00,$FE,$00,$17,$55,$11,$55,$00   ; E243 ....U.U.
        .byte $1F,$00,$55,$00,$72,$00,$FF,$80   ; E24B ..U.r...
        .byte $FF,$7A,$00,$7F,$00,$72,$00,$FF   ; E253 .z...r..
        .byte $01,$FF,$7A,$00,$FE,$00,$07,$FF   ; E25B ..z.....
        .byte $BB,$FF,$55,$00,$1F,$00,$55,$00   ; E263 ..U...U.
        .byte $84,$84,$84,$84,$84,$84,$66,$CC   ; E26B ......f.
        .byte $CF,$C0,$FF,$66,$77,$70,$7F,$00   ; E273 ...fwp..
        .byte $66,$00,$FF,$00,$FF,$83,$66,$11   ; E27B f.....f.
        .byte $F1,$01,$FF,$83,$01,$00,$02,$04   ; E283 ........
        .byte $0F,$04,$02,$00,$00,$20,$00,$40   ; E28B ..... .@
        .byte $00,$40,$00,$20,$08,$67,$00,$F0   ; E293 .@. .g..
        .byte $00,$00,$04,$00,$02,$00,$02,$00   ; E29B ........
        .byte $04,$10,$67,$00,$0F,$00,$00,$20   ; E2A3 ..g.... 
        .byte $00,$40,$00,$40,$00,$20,$08,$01   ; E2AB .@.@. ..
        .byte $00,$40,$20,$F0,$20,$40,$00,$00   ; E2B3 .@ . @..
        .byte $04,$00,$02,$00,$02,$00,$04,$10   ; E2BB ........
        .byte $0D,$01,$03,$05,$01,$00,$7E,$00   ; E2C3 ......~.
        .byte $FF,$0D,$80,$C0,$A0,$80,$00,$7E   ; E2CB .......~
        .byte $00,$FF,$84,$84,$84,$84,$84,$84   ; E2D3 ........
        .byte $84,$00,$AB,$D5,$AB,$D5,$AB,$D5   ; E2DB ........
        .byte $AB,$D5,$7F,$7E,$00,$FF,$55,$AA   ; E2E3 ...~..U.
        .byte $55,$AA,$55,$AA,$FF,$3E,$00,$FF   ; E2EB U.U..>..
        .byte $00,$00,$FF,$D5,$AB,$D5,$AB,$D5   ; E2F3 ........
        .byte $AB,$D5,$3F,$00,$7E,$00,$01,$03   ; E2FB ..?.~...
        .byte $07,$0F,$1F,$3F,$7F,$FF,$81,$00   ; E303 ...?....
        .byte $80,$C0,$E0,$F0,$F8,$FC,$FE,$FF   ; E30B ........
        .byte $81,$00,$FF,$7F,$3F,$1F,$0F,$07   ; E313 ....?...
        .byte $03,$01,$81,$00,$FF,$FE,$FC,$F8   ; E31B ........
        .byte $F0,$E0,$C0,$80,$81,$00,$00,$23   ; E323 .......#
        .byte $44,$FC,$44,$23,$00,$03,$5B,$00   ; E32B D.D#..[.
        .byte $03,$00,$00,$00,$C4,$22,$3F,$22   ; E333 ....."?"
        .byte $C4,$00,$C0,$5B,$00,$C0,$00,$84   ; E33B ...[....
        .byte $84,$84,$84,$84,$84,$84,$00,$FF   ; E343 ........
        .byte $D5,$AA,$D5,$AA,$D5,$AA,$FF,$3E   ; E34B .......>
        .byte $00,$7F,$00,$00,$FF,$55,$AB,$55   ; E353 .....U.U
        .byte $AB,$55,$AB,$FF,$3E,$00,$FE,$00   ; E35B .U..>...
        .byte $00,$AB,$D5,$AB,$D5,$AB,$D5,$AB   ; E363 ........
        .byte $FF,$7E,$7E,$00,$00,$00,$01,$0F   ; E36B .~~.....
        .byte $1F,$3F,$7F,$3F,$0F,$82,$07,$00   ; E373 .?.?....
        .byte $C0,$F1,$FB,$FF,$82,$65,$00,$C0   ; E37B .....e..
        .byte $E0,$F8,$82,$84,$20,$03,$04,$00   ; E383 .... ...
        .byte $01,$00,$01,$00,$00,$20,$00,$40   ; E38B ..... .@
        .byte $00,$40,$00,$20,$08,$20,$C0,$20   ; E393 .@. . . 
        .byte $40,$80,$00,$80,$00,$00,$04,$00   ; E39B @.......
        .byte $02,$00,$02,$00,$04,$10,$84,$84   ; E3A3 ........
        .byte $84,$84,$38,$7F,$80,$88,$CF,$FF   ; E3AB ..8.....
        .byte $38,$00,$7F,$77,$30,$4F,$38,$FF   ; E3B3 8..w0O8.
        .byte $00,$88,$CF,$FF,$38,$00,$FF,$77   ; E3BB ....8..w
        .byte $B0,$CF,$38,$FE,$01,$89,$CF,$FF   ; E3C3 ..8.....
        .byte $38,$00,$FE,$76,$B0,$CE,$00,$AB   ; E3CB 8..v....
        .byte $D5,$AA,$D5,$AA,$D5,$AA,$D5,$3E   ; E3D3 .......>
        .byte $7E,$7F,$7E,$00,$FF,$D5,$AA,$D5   ; E3DB ~.~.....
        .byte $AA,$D5,$AA,$D5,$3E,$00,$7F,$7E   ; E3E3 ....>..~
        .byte $00,$FF,$55,$AB,$55,$AB,$55,$AB   ; E3EB ..U.U.U.
        .byte $D5,$3E,$00,$FE,$7E,$01,$1F,$7F   ; E3F3 .>..~...
        .byte $FF,$7F,$3F,$1F,$00,$82,$70,$FF   ; E3FB ..?...p.
        .byte $DF,$8F,$03,$00,$82,$71,$F0,$E0   ; E403 .....q..
        .byte $80,$00,$82,$84,$20,$03,$04,$03   ; E40B .... ...
        .byte $01,$05,$03,$01,$1C,$30,$60,$C0   ; E413 .....0`.
        .byte $E0,$78,$04,$C0,$A0,$80,$C0,$20   ; E41B .x..... 
        .byte $C0,$00,$1C,$0C,$06,$03,$07,$1E   ; E423 ........
        .byte $00,$00,$03,$04,$0E,$04,$00,$03   ; E42B ........
        .byte $00,$00,$20,$00,$40,$00,$40,$00   ; E433 .. .@.@.
        .byte $20,$08,$01,$C0,$00,$20,$70,$20   ; E43B  .... p 
        .byte $C0,$00,$00,$04,$00,$02,$00,$02   ; E443 ........
        .byte $00,$04,$10,$84,$84,$81,$08,$7F   ; E44B ........
        .byte $3E,$6F,$7F,$7B,$3F,$7F,$81,$08   ; E453 >o.{?...
        .byte $FF,$BE,$EF,$FF,$FB,$BF,$FF,$81   ; E45B ........
        .byte $08,$FE,$BE,$EE,$FE,$FA,$BE,$FE   ; E463 ........
        .byte $00,$AB,$55,$AB,$55,$AB,$55,$AB   ; E46B ..U.U.U.
        .byte $D5,$3E,$7E,$FE,$7E,$00,$AB,$D5   ; E473 .>~.~...
        .byte $AA,$D5,$AA,$D5,$AA,$FF,$3E,$7E   ; E47B ......>~
        .byte $7F,$00,$00,$AB,$55,$AB,$55,$AB   ; E483 ....U.U.
        .byte $55,$AB,$FF,$3E,$7E,$FE,$00,$0F   ; E48B U..>~...
        .byte $FF,$81,$7E,$00,$1F,$00,$7E,$00   ; E493 ..~...~.
        .byte $0F,$FF,$AB,$FF,$00,$1F,$00,$54   ; E49B .......T
        .byte $00,$0F,$55,$01,$55,$00,$1F,$00   ; E4A3 ..U.U...
        .byte $54,$00,$04,$3F,$7F,$FF,$8F,$DF   ; E4AB T..?....
        .byte $7E,$3C,$21,$03,$01,$71,$21,$23   ; E4B3 ~<!..q!#
        .byte $00,$61,$00,$20,$7C,$20,$00,$48   ; E4BB .a. | .H
        .byte $00,$42,$00,$81,$00,$24,$61,$00   ; E4C3 .B...$a.
        .byte $04,$3E,$04,$00,$48,$00,$42,$00   ; E4CB .>..H.B.
        .byte $81,$00,$24,$70,$00,$22,$55,$88   ; E4D3 ..$p."U.
        .byte $FF,$78,$00,$22,$77,$00,$84,$0F   ; E4DB .x."w...
        .byte $7E,$C3,$7E,$00,$00,$00,$3C,$00   ; E4E3 ~.~...<.
        .byte $18,$3C,$18,$3C,$18,$0F,$7E,$C3   ; E4EB .<.<..~.
        .byte $7E,$00,$10,$00,$3C,$00,$42,$FF   ; E4F3 ~...<.B.
        .byte $42,$00,$0F,$FF,$81,$7E,$00,$20   ; E4FB B....~. 
        .byte $00,$7E,$18,$3C,$18,$3C,$18,$0F   ; E503 .~.<.<..
        .byte $FF,$81,$7E,$00,$20,$00,$7E,$00   ; E50B ..~. .~.
        .byte $42,$FF,$42,$00,$40,$00,$42,$E7   ; E513 B.B.@.B.
        .byte $42,$00,$18,$00,$5B,$00,$18,$00   ; E51B B...[...
        .byte $70,$00,$7E,$42,$7E,$18,$79,$00   ; E523 p.~B~.y.
        .byte $3C,$00,$71,$00,$18,$3C,$00,$7E   ; E52B <.q..<.~
        .byte $00,$7E,$71,$00,$22,$77,$FF,$78   ; E533 .~q."w.x
        .byte $00,$22,$77,$00,$84,$1C,$3C,$7E   ; E53B ."w...<~
        .byte $FF,$7E,$3C,$10,$00,$3C,$5A,$7E   ; E543 .~<..<Z~
        .byte $76,$3C,$00,$00,$3C,$42,$81,$BF   ; E54B v<..<B..
        .byte $81,$FF,$7E,$3C,$00,$00,$3C,$7E   ; E553 ..~<..<~
        .byte $40,$7E,$76,$3C,$00,$0C,$FF,$81   ; E55B @~v<....
        .byte $95,$FF,$7E,$3C,$00,$00,$7E,$6A   ; E563 ..~<..~j
        .byte $00,$7E,$76,$3C,$00,$10,$3C,$7E   ; E56B .~v<..<~
        .byte $FF,$A3,$9D,$42,$3C,$00,$00,$3C   ; E573 ...B<..<
        .byte $6A,$7E,$5C,$62,$3C,$00,$1C,$3C   ; E57B j~.b<..<
        .byte $7E,$FF,$7E,$3C,$00,$00,$3C,$7E   ; E583 ~.~<..<~
        .byte $48,$7E,$76,$3C,$00,$1C,$3C,$7E   ; E58B H~v<..<~
        .byte $FF,$7E,$3C,$00,$00,$3C,$08,$5A   ; E593 .~<..<.Z
        .byte $7E,$76,$3C,$00,$1C,$3C,$7E,$FF   ; E59B ~v<..<~.
        .byte $7E,$3C,$00,$00,$3C,$5A,$7E,$5A   ; E5A3 ~<..<Z~Z
        .byte $66,$3C,$00,$81,$00,$00,$7E,$5A   ; E5AB f<....~Z
        .byte $7E,$5A,$66,$7E,$00,$81,$14,$00   ; E5B3 ~Zf~....
        .byte $7E,$5A,$7E,$66,$00,$81,$00,$00   ; E5BB ~Z~f....
        .byte $7E,$48,$5A,$7E,$5A,$66,$00,$07   ; E5C3 ~HZ~Zf..
        .byte $FF,$81,$A5,$81,$FF,$08,$00,$7E   ; E5CB .......~
        .byte $5A,$7E,$66,$7E,$00,$1E,$3C,$7E   ; E5D3 Z~f~..<~
        .byte $FF,$7E,$10,$00,$3C,$6A,$7E,$00   ; E5DB .~..<j~.
        .byte $1C,$00,$1C,$3C,$7E,$FF,$7E,$3C   ; E5E3 ...<~.~<
        .byte $10,$00,$3C,$6A,$7E,$42,$3C,$00   ; E5EB ..<j~B<.
        .byte $08,$3C,$3E,$FF,$F5,$FF,$7E,$3C   ; E5F3 .<>...~<
        .byte $08,$80,$7C,$60,$5E,$60,$3C,$00   ; E5FB ..|`^`<.
        .byte $84,$84,$10,$44,$47,$42,$62,$1E   ; E603 ...DGBb.
        .byte $24,$6E,$53,$38,$3C,$1C,$00,$10   ; E60B $nS8<...
        .byte $22,$47,$42,$46,$3C,$46,$63,$13   ; E613 "GBF<Fc.
        .byte $1C,$38,$3C,$38,$00,$38,$A5,$42   ; E61B .8<8.8.B
        .byte $3C,$24,$66,$3B,$18,$3C,$00,$10   ; E623 <$f..<..
        .byte $44,$47,$42,$66,$3C,$42,$7E,$50   ; E62B DGBf<B~P
        .byte $38,$3C,$18,$00,$3C,$00,$1E,$44   ; E633 8<..<..D
        .byte $47,$42,$7E,$5E,$38,$3C,$00,$10   ; E63B GB~^8<..
        .byte $44,$47,$42,$7E,$10,$08,$7E,$57   ; E643 DGB~..~W
        .byte $38,$3C,$00,$10,$44,$47,$42,$7E   ; E64B 8<..DGB~
        .byte $08,$10,$7E,$57,$38,$3C,$00,$00   ; E653 ..~W8<..
        .byte $44,$47,$42,$24,$18,$24,$44,$66   ; E65B DGB$.$Df
        .byte $47,$38,$3C,$18,$00,$00,$44,$47   ; E663 G8<...DG
        .byte $42,$24,$18,$25,$42,$60,$47,$38   ; E66B B$.%B`G8
        .byte $3C,$18,$00,$00,$44,$47,$42,$24   ; E673 <...DGB$
        .byte $18,$64,$84,$46,$47,$38,$3C,$18   ; E67B .d.FG8<.
        .byte $00,$83,$10,$24,$43,$A4,$18,$24   ; E683 ...$C..$
        .byte $44,$04,$17,$18,$3C,$18,$00,$10   ; E68B D...<...
        .byte $24,$43,$A4,$18,$24,$22,$20,$17   ; E693 $C..$" .
        .byte $18,$3C,$18,$00,$00,$44,$47,$42   ; E69B .<...DGB
        .byte $7C,$18,$3C,$66,$18,$4C,$38,$3C   ; E6A3 |.<f.L8<
        .byte $00,$18,$00,$84,$84,$40,$00,$FE   ; E6AB .....@..
        .byte $82,$BE,$A0,$E0,$00,$65,$00,$7C   ; E6B3 .....e.|
        .byte $40,$00,$00,$20,$40,$FE,$82,$FE   ; E6BB @.. @...
        .byte $80,$C0,$00,$67,$00,$7C,$00,$00   ; E6C3 ...g.|..
        .byte $20,$40,$FE,$C0,$A0,$80,$E0,$00   ; E6CB  @......
        .byte $1F,$00,$3E,$00,$00,$3C,$42,$CE   ; E6D3 ..>..<B.
        .byte $C2,$BC,$80,$E0,$00,$07,$00,$3C   ; E6DB .......<
        .byte $30,$3C,$00,$00,$60,$F0,$FE,$BA   ; E6E3 0<..`...
        .byte $BE,$A0,$E0,$00,$05,$00,$60,$30   ; E6EB ......`0
        .byte $54,$40,$00,$00,$F0,$90,$9F,$E1   ; E6F3 T@......
        .byte $5F,$50,$70,$00,$25,$00,$60,$1E   ; E6FB _Pp.%.`.
        .byte $20,$00,$48,$00,$FE,$BE,$A0,$E0   ; E703  .H.....
        .byte $00,$49,$00,$2A,$6A,$40,$00,$00   ; E70B .I.*j@..
        .byte $00,$FF,$81,$BF,$A8,$B0,$E0,$00   ; E713 ........
        .byte $4D,$00,$7E,$40,$00,$00,$04,$0A   ; E71B M.~@....
        .byte $14,$28,$50,$A8,$50,$30,$00,$00   ; E723 .(P.P0..
        .byte $04,$08,$10,$20,$40,$20,$00,$00   ; E72B ... @ ..
        .byte $00,$18,$14,$92,$F1,$92,$14,$18   ; E733 ........
        .byte $40,$00,$08,$0C,$0E,$0C,$08,$00   ; E73B @.......
        .byte $00,$FF,$85,$8B,$E5,$5F,$50,$70   ; E743 ....._Pp
        .byte $00,$05,$00,$7A,$74,$1A,$20,$00   ; E74B ...zt. .
        .byte $00,$FF,$F7,$EF,$F7,$5F,$90,$F0   ; E753 ....._..
        .byte $00,$01,$00,$0A,$14,$0A,$20,$60   ; E75B ...... `
        .byte $00,$84,$84,$08,$36,$6B,$49,$41   ; E763 ....6kIA
        .byte $22,$14,$08,$08,$00,$14,$34,$38   ; E76B ".....48
        .byte $18,$08,$00,$84,$08,$00,$18,$24   ; E773 .......$
        .byte $42,$24,$18,$00,$49,$00,$18,$3C   ; E77B B$..I..<
        .byte $18,$00,$41,$00,$3C,$42,$24,$18   ; E783 ..A.<B$.
        .byte $00,$63,$00,$3C,$18,$00,$80,$18   ; E78B .c.<....
        .byte $3E,$00,$55,$00,$3E,$00,$00,$00   ; E793 >.U.>...
        .byte $02,$00,$08,$80,$00,$20,$00,$00   ; E79B ..... ..
        .byte $00,$20,$00,$80,$08,$00,$02,$00   ; E7A3 . ......
        .byte $41,$00,$FF,$D5,$AB,$FF,$00,$5D   ; E7AB A......]
        .byte $00,$FF,$00,$00,$00,$08,$18,$64   ; E7B3 .......d
        .byte $26,$18,$10,$00,$6B,$00,$18,$00   ; E7BB &...k...
        .byte $18,$2A,$00,$55,$00,$2A,$00,$82   ; E7C3 .*.U.*..
        .byte $08,$18,$42,$18,$A5,$18,$42,$18   ; E7CB ..B...B.
        .byte $08,$18,$42,$00,$99,$00,$42,$18   ; E7D3 ..B...B.
        .byte $08,$00,$5A,$24,$42,$24,$5A,$00   ; E7DB ..Z$B$Z.
        .byte $49,$00,$18,$3C,$18,$00,$00,$00   ; E7E3 I..<....
        .byte $18,$D4,$12,$D1,$12,$D4,$18,$40   ; E7EB .......@
        .byte $00,$08,$0C,$0E,$0C,$08,$00,$00   ; E7F3 ........
        .byte $7E,$FF,$C3,$C1,$C3,$C1,$EB,$7E   ; E7FB ~......~
        .byte $00,$00,$7E,$7C,$7E,$7C,$7E,$54   ; E803 ..~|~|~T
        .byte $00,$0E,$06,$09,$3C,$7E,$3C,$03   ; E80B ....<~<.
        .byte $06,$09,$01,$21,$20,$00,$84,$84   ; E813 ...! ...
        .byte $13,$24,$43,$A4,$18,$24,$17,$18   ; E81B .$C..$..
        .byte $3C,$18,$00,$84,$3F,$FF,$81,$00   ; E823 <...?...
        .byte $FF,$81,$95,$A9,$95,$A9,$95,$A9   ; E82B ........
        .byte $00,$FF,$89,$95,$A3,$D5,$D7,$D5   ; E833 ........
        .byte $A5,$02,$FF,$81,$89,$9D,$AA,$A9   ; E83B ........
        .byte $99,$30,$FF,$81,$B7,$EB,$C9,$C1   ; E843 .0......
        .byte $38,$FF,$81,$94,$B6,$BE,$30,$FF   ; E84B 8.....0.
        .byte $81,$85,$8B,$95,$A9,$38,$FF,$81   ; E853 .....8..
        .byte $85,$89,$91,$0C,$FF,$81,$85,$83   ; E85B ........
        .byte $BD,$FF,$04,$FF,$91,$BD,$93,$83   ; E863 ........
        .byte $81,$B1,$29,$FF,$81,$99,$FF,$99   ; E86B ..).....
        .byte $3F,$FF,$81,$34,$FF,$81,$FF,$C3   ; E873 ?..4....
        .byte $C1,$38,$FF,$81,$7E,$7C,$7E,$84   ; E87B .8..~|~.
        .byte $84,$00,$3C,$6A,$D5,$BF,$D5,$AB   ; E883 ..<j....
        .byte $56,$3C,$00,$00,$28,$54,$00,$54   ; E88B V<..(T.T
        .byte $22,$14,$00,$1C,$3C,$7E,$FF,$7E   ; E893 "...<~.~
        .byte $3C,$10,$00,$3C,$6E,$62,$7E,$3C   ; E89B <..<nb~<
        .byte $00,$08,$08,$0C,$06,$FF,$06,$0C   ; E8A3 ........
        .byte $08,$80,$01,$00,$3C,$00,$3C,$00   ; E8AB ....<.<.
        .byte $3C,$00,$00,$FF,$3C,$C3,$3C,$C3   ; E8B3 <...<.<.
        .byte $3C,$FF,$00,$84,$84,$84,$7E,$81   ; E8BB <.....~.
        .byte $FF,$00,$95,$A9,$95,$A9,$95,$A9   ; E8C3 ........
        .byte $81,$FF,$00,$A5,$AB,$EB,$AB,$C5   ; E8CB ........
        .byte $A9,$91,$FF,$20,$99,$95,$55,$B9   ; E8D3 ... ..U.
        .byte $91,$81,$FF,$06,$C1,$A3,$95,$89   ; E8DB ........
        .byte $81,$FF,$0E,$BE,$9D,$89,$81,$FF   ; E8E3 ........
        .byte $06,$D1,$A9,$D1,$B1,$81,$FF,$0E   ; E8EB ........
        .byte $A1,$41,$A1,$81,$FF,$66,$FF,$BD   ; E8F3 .A...f..
        .byte $81,$FF,$3E,$A1,$81,$FF,$0E,$A5   ; E8FB ..>.....
        .byte $C3,$81,$D5,$FF,$7E,$81,$FF,$06   ; E903 ....~...
        .byte $C3,$C1,$EB,$FF,$81,$FF,$0E,$7C   ; E90B .......|
        .byte $7E,$54,$81,$FF,$84,$84,$00,$08   ; E913 ~T......
        .byte $1C,$2A,$18,$0C,$2A,$1C,$08,$80   ; E91B .*..*...
        .byte $00,$08,$1C,$2A,$18,$0C,$2A,$1C   ; E923 ...*..*.
        .byte $08,$3E,$60,$C0,$60,$07,$18,$3C   ; E92B .>`.`..<
        .byte $7E,$DB,$18,$80,$12,$24,$63,$A4   ; E933 ~....$c.
        .byte $3C,$24,$36,$17,$18,$1C,$18,$00   ; E93B <$6.....
        .byte $10,$24,$43,$A4,$3C,$24,$44,$26   ; E943 .$C.<$D&
        .byte $17,$18,$3C,$18,$00,$10,$24,$43   ; E94B ..<...$C
        .byte $A4,$3C,$25,$22,$30,$17,$18,$3C   ; E953 .<%"0..<
        .byte $18,$00,$86,$79,$00,$03,$07,$82   ; E95B ...y....
        .byte $61,$00,$03,$07,$0F,$1F,$82,$05   ; E963 a.......
        .byte $00,$03,$0F,$1F,$3F,$7F,$82,$1F   ; E96B ....?...
        .byte $3F,$7F,$C0,$1F,$00,$3F,$7F,$7C   ; E973 ?....?.|
        .byte $C0,$6A,$3F,$7C,$7F,$15,$00,$00   ; E97B .j?|....
        .byte $FC,$FE,$03,$01,$03,$01,$03,$01   ; E983 ........
        .byte $20,$00,$FC,$FE,$FC,$FE,$FC,$FE   ; E98B  .......
        .byte $00,$03,$01,$03,$01,$03,$01,$AA   ; E993 ........
        .byte $FC,$00,$FC,$FE,$FC,$FE,$FC,$FE   ; E99B ........
        .byte $54,$00,$02,$03,$0F,$1C,$30,$20   ; E9A3 T.....0 
        .byte $40,$7F,$0A,$00,$03,$0F,$1F,$3F   ; E9AB @......?
        .byte $00,$7D,$01,$03,$80,$04,$C0,$F0   ; E9B3 .}......
        .byte $38,$0E,$1E,$02,$FE,$10,$00,$C0   ; E9BB 8.......
        .byte $F0,$EC,$E0,$FC,$00,$78,$80,$E0   ; E9C3 .....x..
        .byte $10,$F0,$7C,$00,$E0,$00,$02,$03   ; E9CB ..|.....
        .byte $0F,$1C,$30,$20,$40,$7F,$0A,$00   ; E9D3 ..0 @...
        .byte $03,$0F,$1F,$3F,$00,$20,$03,$06   ; E9DB ...?. ..
        .byte $1C,$18,$36,$31,$0F,$78,$00,$08   ; E9E3 ..61.x..
        .byte $0E,$00,$04,$C0,$F0,$38,$0E,$1E   ; E9EB .....8..
        .byte $02,$FE,$10,$00,$C0,$F0,$EC,$E0   ; E9F3 ........
        .byte $FC,$00,$20,$C0,$60,$30,$3E,$19   ; E9FB .. .`0>.
        .byte $33,$3C,$78,$00,$06,$0C,$00,$07   ; EA03 3<x.....
        .byte $00,$07,$0F,$1F,$3F,$80,$20,$FC   ; EA0B ....?. .
        .byte $FF,$80,$87,$83,$81,$80,$6F,$00   ; EA13 ......o.
        .byte $7F,$1D,$00,$E0,$F0,$F8,$75,$00   ; EA1B ......u.
        .byte $E0,$F0,$20,$FF,$80,$FF,$08,$07   ; EA23 .. .....
        .byte $08,$FF,$2F,$00,$7F,$00,$32,$7F   ; EA2B ../...2.
        .byte $80,$E6,$FF,$7F,$3E,$00,$7F,$00   ; EA33 ....>...
        .byte $48,$00,$7C,$FE,$7C,$44,$82,$42   ; EA3B H.|.|D.B
        .byte $38,$00,$7C,$00,$38,$7C,$0C,$00   ; EA43 8.|.8|..
        .byte $19,$3E,$3C,$3E,$19,$4C,$00,$11   ; EA4B .><>.L..
        .byte $D7,$11,$00,$0C,$00,$FE,$1D,$0F   ; EA53 ........
        .byte $1D,$FE,$4C,$00,$E6,$F6,$E6,$00   ; EA5B ..L.....
        .byte $55,$E4,$EF,$FF,$7F,$40,$03,$00   ; EA63 U....@..
        .byte $03,$07,$06,$07,$00,$2F,$3F,$7F   ; EA6B ...../?.
        .byte $FF,$23,$00,$1F,$0F,$03,$00,$55   ; EA73 .#.....U
        .byte $13,$FB,$FF,$FE,$40,$E0,$00,$30   ; EA7B ....@..0
        .byte $70,$60,$70,$00,$3F,$FE,$FF,$23   ; EA83 p`p.?..#
        .byte $00,$F8,$F0,$C0,$00,$00,$00,$03   ; EA8B ........
        .byte $0E,$35,$6A,$55,$AA,$D5,$40,$00   ; EA93 .5jU..@.
        .byte $01,$0A,$15,$2A,$55,$2A,$30,$FA   ; EA9B ...*U*0.
        .byte $FF,$AF,$D5,$7A,$0F,$00,$05,$20   ; EAA3 ...z... 
        .byte $55,$0A,$50,$2A,$05,$00,$00,$00   ; EAAB U.P*....
        .byte $C0,$B0,$5C,$AA,$56,$AB,$55,$40   ; EAB3 ....V.U@
        .byte $00,$40,$A0,$54,$A8,$54,$AA,$30   ; EABB .@.T.T.0
        .byte $AF,$FF,$FB,$55,$AE,$F0,$00,$50   ; EAC3 ...U...P
        .byte $0A,$54,$A0,$04,$AA,$50,$00,$48   ; EACB .T...P.H
        .byte $3F,$23,$30,$38,$3F,$1F,$49,$00   ; EAD3 ?#08?.I.
        .byte $1C,$0F,$07,$00,$43,$80,$84,$0F   ; EADB ....C...
        .byte $07,$03,$6F,$7F,$FF,$48,$F8,$10   ; EAE3 ..o..H..
        .byte $F8,$DC,$FC,$F0,$08,$F0,$00,$E0   ; EAEB ........
        .byte $F0,$F8,$C0,$E0,$72,$00,$FF,$80   ; EAF3 ....r...
        .byte $FF,$7A,$00,$7F,$00,$32,$7F,$80   ; EAFB .z...2..
        .byte $99,$FF,$7F,$3E,$00,$7F,$00,$64   ; EB03 ...>...d
        .byte $82,$C6,$FE,$BA,$7C,$62,$7C,$38   ; EB0B ....|b|8
        .byte $00,$7C,$00,$10,$01,$07,$03,$C3   ; EB13 .|......
        .byte $E3,$FF,$F7,$00,$FE,$F8,$FE,$FF   ; EB1B ........
        .byte $BF,$9F,$E3,$00,$5C,$00,$E0,$C0   ; EB23 ........
        .byte $80,$6C,$00,$C0,$80,$00,$7D,$00   ; EB2B .l....}.
        .byte $0C,$70,$00,$04,$0E,$0F,$0B,$00   ; EB33 .p......
        .byte $30,$43,$40,$60,$03,$00,$7F,$00   ; EB3B 0C@`....
        .byte $10,$0F,$0C,$0F,$00,$7F,$D5,$7F   ; EB43 ........
        .byte $7D,$00,$30,$70,$00,$20,$70,$F0   ; EB4B }.0p. p.
        .byte $E0,$10,$0E,$CB,$00,$C0,$00,$FE   ; EB53 ........
        .byte $00,$10,$F0,$30,$F0,$00,$FE,$55   ; EB5B ...0...U
        .byte $FE,$7D,$00,$0C,$70,$00,$04,$0E   ; EB63 .}..p...
        .byte $0F,$0B,$00,$30,$23,$20,$60,$03   ; EB6B ...0# `.
        .byte $00,$7F,$00,$10,$0F,$0C,$0F,$00   ; EB73 ........
        .byte $7F,$AA,$7F,$7D,$00,$30,$70,$00   ; EB7B ...}.0p.
        .byte $20,$70,$F0,$E0,$10,$09,$CF,$00   ; EB83  p......
        .byte $C0,$00,$FE,$00,$10,$F0,$30,$F0   ; EB8B ......0.
        .byte $00,$FE,$AB,$FE,$08,$1C,$18,$10   ; EB93 ........
        .byte $20,$18,$07,$01,$08,$03,$07,$0F   ; EB9B  .......
        .byte $1F,$07,$01,$00,$40,$03,$23,$1F   ; EBA3 ....@.#.
        .byte $C3,$FE,$F8,$F0,$40,$FF,$DF,$E1   ; EBAB ....@...
        .byte $FC,$F8,$F0,$00,$73,$E0,$C0,$00   ; EBB3 ....s...
        .byte $37,$00,$C0,$00,$08,$36,$6B,$49   ; EBBB 7....6kI
        .byte $41,$22,$14,$08,$08,$00,$14,$36   ; EBC3 A".....6
        .byte $3E,$1C,$08,$00,$05,$00,$03,$0F   ; EBCB >.......
        .byte $3F,$7F,$FF,$40,$00,$03,$0F,$3B   ; EBD3 ?..@....
        .byte $3F,$6F,$7D,$04,$FF,$8F,$80,$F0   ; EBDB ?o}.....
        .byte $FF,$7F,$0F,$00,$0F,$70,$7F,$0F   ; EBE3 .....p..
        .byte $70,$7F,$0F,$00,$05,$00,$C0,$F0   ; EBEB p.......
        .byte $FC,$FE,$FF,$40,$00,$C0,$F0,$BC   ; EBF3 ...@....
        .byte $F4,$FE,$DE,$04,$FF,$F1,$01,$0F   ; EBFB ........
        .byte $FF,$FE,$F0,$00,$F0,$0E,$FE,$F0   ; EC03 ........
        .byte $0E,$FE,$F0,$00,$00,$00,$03,$0E   ; EC0B ........
        .byte $35,$6E,$55,$BA,$D7,$40,$00,$03   ; EC13 5nU..@..
        .byte $0F,$3B,$3F,$6F,$7D,$00,$FA,$8F   ; EC1B ..?o}...
        .byte $80,$F0,$AF,$D5,$7A,$0F,$00,$0F   ; EC23 ....z...
        .byte $70,$7F,$0F,$70,$7F,$0F,$00,$00   ; EC2B p..p....
        .byte $00,$C0,$B0,$5C,$EA,$5E,$AB,$75   ; EC33 .....^.u
        .byte $40,$00,$C0,$F0,$BC,$F4,$FE,$DE   ; EC3B @.......
        .byte $00,$AF,$F1,$01,$0F,$FB,$55,$AE   ; EC43 ......U.
        .byte $F0,$00,$F0,$0E,$FE,$F0,$0E,$FE   ; EC4B ........
        .byte $F0,$00,$00,$00,$03,$0C,$30,$44   ; EC53 ......0D
        .byte $40,$90,$82,$40,$00,$03,$0F,$3B   ; EC5B @..@....
        .byte $3F,$6F,$7D,$30,$F0,$FF,$8F,$80   ; EC63 ?o}0....
        .byte $70,$0F,$00,$0F,$20,$55,$0A,$70   ; EC6B p... U.p
        .byte $7F,$0F,$00,$00,$00,$C0,$30,$0C   ; EC73 ......0.
        .byte $42,$0A,$01,$21,$40,$00,$C0,$F0   ; EC7B B..!@...
        .byte $BC,$F4,$FE,$DE,$30,$0F,$FF,$F1   ; EC83 ....0...
        .byte $01,$0E,$F0,$00,$F0,$0A,$54,$A0   ; EC8B ......T.
        .byte $0E,$FE,$F0,$00,$00,$03,$0C,$1E   ; EC93 ........
        .byte $26,$46,$64,$70,$F0,$01,$00,$03   ; EC9B &Fdp....
        .byte $01,$19,$39,$1B,$0F,$00,$AA,$FF   ; ECA3 ..9.....
        .byte $7F,$39,$19,$0B,$08,$07,$40,$7F   ; ECAB .9....@.
        .byte $3F,$17,$06,$04,$07,$00,$04,$C0   ; ECB3 ?.......
        .byte $30,$08,$44,$62,$01,$3F,$00,$00   ; ECBB 0.Db.?..
        .byte $C0,$F0,$B8,$9C,$FC,$FE,$C0,$04   ; ECC3 ........
        .byte $8B,$C1,$FE,$FC,$F0,$F8,$F0,$42   ; ECCB .......B
        .byte $FE,$F8,$F0,$C0,$00,$80,$00,$03   ; ECD3 ........
        .byte $0E,$16,$26,$63,$72,$70,$D0,$00   ; ECDB ..&crp..
        .byte $00,$01,$09,$19,$1C,$0D,$0F,$2F   ; ECE3 ......./
        .byte $00,$AA,$FF,$7F,$3C,$1C,$04,$02   ; ECEB ....<...
        .byte $01,$44,$7F,$3F,$1B,$03,$01,$00   ; ECF3 .D.?....
        .byte $04,$C0,$30,$08,$24,$32,$01,$1F   ; ECFB ..0.$2..
        .byte $00,$00,$C0,$F0,$D8,$CC,$FC,$FE   ; ED03 ........
        .byte $E0,$00,$8B,$C1,$FE,$FC,$F0,$C0   ; ED0B ........
        .byte $20,$E0,$40,$FE,$F8,$70,$40,$00   ; ED13  .@..p@.
        .byte $C0,$20,$00,$03,$0F,$13,$31,$79   ; ED1B . ....1y
        .byte $59,$48,$CC,$40,$00,$0C,$0E,$06   ; ED23 YH.@....
        .byte $26,$37,$33,$02,$95,$FF,$7F,$3E   ; ED2B &73....>
        .byte $1F,$0F,$07,$43,$7F,$3F,$1F,$0E   ; ED33 ...C.?..
        .byte $00,$00,$C0,$30,$08,$94,$9A,$1A   ; ED3B ...0....
        .byte $01,$0F,$00,$00,$C0,$F0,$68,$64   ; ED43 ......hd
        .byte $FC,$FE,$F0,$04,$45,$E1,$FE,$7C   ; ED4B ....E..|
        .byte $30,$88,$78,$04,$FF,$FE,$FC,$B0   ; ED53 0.x.....
        .byte $C0,$70,$08,$34,$01,$00,$01,$02   ; ED5B .p.4....
        .byte $06,$1C,$00,$01,$00,$01,$03,$00   ; ED63 ........
        .byte $78,$2A,$54,$29,$2F,$37,$03,$07   ; ED6B x*T)/7..
        .byte $00,$07,$17,$2F,$1E,$11,$00,$01   ; ED73 .../....
        .byte $00,$00,$B0,$E8,$8C,$9E,$1F,$0F   ; ED7B ........
        .byte $96,$1C,$00,$00,$10,$78,$74,$FE   ; ED83 .....xt.
        .byte $F8,$FC,$F8,$00,$0C,$38,$E8,$D0   ; ED8B .....8..
        .byte $E0,$80,$00,$80,$03,$F8,$D0,$30   ; ED93 .......0
        .byte $60,$80,$00,$34,$01,$00,$01,$02   ; ED9B `..4....
        .byte $06,$1C,$00,$01,$00,$01,$03,$00   ; EDA3 ........
        .byte $78,$2A,$54,$29,$2F,$3C,$1E,$00   ; EDAB x*T)/<..
        .byte $01,$07,$17,$2F,$1E,$10,$04,$00   ; EDB3 .../....
        .byte $00,$B0,$E8,$8C,$9E,$1F,$0F,$96   ; EDBB ........
        .byte $1C,$00,$00,$10,$78,$74,$FE,$F8   ; EDC3 ....xt..
        .byte $FC,$F8,$00,$0C,$38,$E8,$F0,$C0   ; EDCB ....8...
        .byte $70,$C0,$00,$07,$F8,$D0,$30,$C0   ; EDD3 p.....0.
        .byte $00,$00,$3F,$35,$1A,$0D,$0A,$0D   ; EDDB ..?5....
        .byte $08,$38,$01,$00,$15,$0A,$05,$02   ; EDE3 .8......
        .byte $05,$07,$20,$73,$C4,$C0,$C1,$C0   ; EDEB .. s....
        .byte $61,$3F,$20,$3C,$7B,$7F,$7E,$7F   ; EDF3 a? <{.~.
        .byte $3E,$00,$00,$FC,$54,$A8,$50,$B0   ; EDFB >...T.P.
        .byte $50,$90,$1C,$01,$00,$50,$A0,$40   ; EE03 P....P.@
        .byte $A0,$40,$E0,$00,$86,$42,$47,$41   ; EE0B .@...BGA
        .byte $83,$01,$86,$FC,$00,$78,$BC,$B8   ; EE13 .....x..
        .byte $BE,$7C,$FE,$78,$00,$05,$03,$0F   ; EE1B .|.x....
        .byte $1C,$30,$60,$C0,$05,$00,$03,$0F   ; EE23 .0`.....
        .byte $1F,$3F,$7F,$50,$C0,$60,$30,$1A   ; EE2B .?.P.`0.
        .byte $0D,$03,$50,$7F,$3F,$1F,$05,$02   ; EE33 ..P.?...
        .byte $00,$00,$C0,$F0,$38,$0C,$06,$02   ; EE3B ....8...
        .byte $05,$03,$08,$00,$C0,$F0,$F8,$FC   ; EE43 ........
        .byte $FA,$FC,$00,$05,$0B,$16,$2A,$54   ; EE4B ......*T
        .byte $A8,$70,$C0,$00,$FA,$F4,$E8,$D4   ; EE53 .p......
        .byte $A8,$50,$80,$00,$00,$00,$0F,$1F   ; EE5B .P......
        .byte $31,$3F,$7F,$FF,$DF,$60,$00,$0E   ; EE63 1?...`..
        .byte $00,$0A,$4A,$60,$00,$C0,$C7,$6F   ; EE6B ..J`...o
        .byte $67,$63,$30,$18,$07,$00,$7F,$78   ; EE73 gc0....x
        .byte $37,$3B,$3C,$1F,$07,$00,$00,$00   ; EE7B 7.<.....
        .byte $F0,$F8,$8C,$FC,$FE,$FD,$F9,$60   ; EE83 .......`
        .byte $00,$70,$00,$50,$52,$06,$00,$03   ; EE8B .p.PR...
        .byte $E5,$F2,$E6,$CA,$14,$38,$E0,$00   ; EE93 .....8..
        .byte $FC,$1A,$EC,$D8,$34,$E8,$C0,$00   ; EE9B ....4...
        .byte $04,$3C,$66,$6E,$76,$66,$3C,$00   ; EEA3 .<fnvf<.
        .byte $80,$1E,$18,$38,$18,$00,$80,$00   ; EEAB ...8....
        .byte $3C,$46,$06,$1C,$30,$60,$7E,$00   ; EEB3 <F..0`~.
        .byte $80,$00,$7E,$0C,$18,$3C,$06,$46   ; EEBB ..~..<.F
        .byte $3C,$00,$80,$02,$0E,$16,$26,$46   ; EEC3 <.....&F
        .byte $7F,$06,$00,$80,$08,$7E,$60,$7C   ; EECB .....~`|
        .byte $06,$46,$3C,$00,$80,$04,$1C,$30   ; EED3 .F<....0
        .byte $60,$7C,$66,$3C,$00,$80,$26,$7E   ; EEDB `|f<..&~
        .byte $06,$0C,$18,$00,$80,$24,$3C,$66   ; EEE3 .....$<f
        .byte $3C,$66,$3C,$00,$80,$20,$3C,$66   ; EEEB <f<.. <f
        .byte $3E,$06,$0C,$38,$00,$80,$08,$36   ; EEF3 >..8...6
        .byte $6B,$49,$41,$22,$14,$08,$5B,$00   ; EEFB kIA"..[.
        .byte $20,$00,$08,$36,$6B,$49,$41,$22   ; EF03  ..6kIA"
        .byte $14,$08,$19,$00,$10,$30,$10,$00   ; EF0B .....0..
        .byte $00,$00,$0F,$1F,$31,$3F,$7F,$FF   ; EF13 ....1?..
        .byte $DF,$60,$00,$0E,$00,$0E,$4A,$60   ; EF1B .`....J`
        .byte $00,$C0,$C3,$C7,$CF,$C7,$C0,$E0   ; EF23 ........
        .byte $FF,$02,$7F,$7C,$7B,$77,$78,$7F   ; EF2B ...|{wx.
        .byte $00,$00,$00,$F0,$F8,$8C,$FC,$FE   ; EF33 ........
        .byte $FD,$F9,$60,$00,$70,$00,$70,$52   ; EF3B ..`.p.pR
        .byte $06,$00,$03,$C5,$E3,$F5,$E3,$05   ; EF43 ........
        .byte $0B,$FF,$00,$FC,$3A,$DC,$EA,$1C   ; EF4B ....:...
        .byte $FA,$F4,$00,$81,$04,$C3,$99,$91   ; EF53 ........
        .byte $89,$99,$C3,$FF,$81,$1E,$E7,$C7   ; EF5B ........
        .byte $E7,$FF,$81,$00,$C3,$B9,$F9,$E3   ; EF63 ........
        .byte $CF,$9F,$81,$FF,$81,$00,$81,$F3   ; EF6B ........
        .byte $E7,$C3,$F9,$B9,$C3,$FF,$81,$02   ; EF73 ........
        .byte $F1,$E9,$D9,$B9,$80,$F9,$FF,$81   ; EF7B ........
        .byte $08,$81,$9F,$83,$F9,$B9,$C3,$FF   ; EF83 ........
        .byte $81,$04,$E3,$CF,$9F,$83,$99,$C3   ; EF8B ........
        .byte $FF,$81,$26,$81,$F9,$F3,$E7,$FF   ; EF93 ..&.....
        .byte $81,$24,$C3,$99,$C3,$99,$C3,$FF   ; EF9B .$......
        .byte $81,$20,$C3,$99,$C1,$F9,$F3,$C7   ; EFA3 . ......
        .byte $FF,$84,$84,$84,$84,$84,$84,$84   ; EFAB ........
        .byte $84,$84,$84,$84,$84,$84,$84,$84   ; EFB3 ........
        .byte $84,$84,$84,$84,$84,$84,$84,$84   ; EFBB ........
        .byte $84,$84,$84,$84,$84,$84,$84,$84   ; EFC3 ........
        .byte $84,$84,$84,$84,$84,$84,$84       ; EFCB .......
IRQ:
        rti                                     ; EFD2
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; EFD3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; EFDB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; EFE3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; EFEB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; EFF3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; EFFB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F003 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F00B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F013 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F01B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F023 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F02B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F033 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F03B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F043 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F04B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F053 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F05B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F063 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F06B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F073 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F07B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F083 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F08B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F093 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F09B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F0FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F103 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F10B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F113 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F11B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F123 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F12B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F133 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F13B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F143 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F14B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F153 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F15B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F163 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F16B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F173 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F17B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F183 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F18B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F193 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F19B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F1FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F203 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F20B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F213 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F21B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F223 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F22B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F233 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F23B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F243 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F24B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F253 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F25B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F263 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F26B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F273 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F27B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F283 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F28B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F293 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F29B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F2FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F303 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F30B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F313 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F31B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F323 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F32B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F333 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F33B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F343 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F34B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F353 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F35B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F363 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F36B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F373 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F37B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F383 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F38B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F393 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F39B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F3FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F403 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F40B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F413 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F41B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F423 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F42B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F433 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F43B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F443 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F44B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F453 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F45B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F463 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F46B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F473 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F47B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F483 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F48B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F493 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F49B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F4FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F503 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F50B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F513 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F51B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F523 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F52B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F533 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F53B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F543 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F54B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F553 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F55B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F563 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F56B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F573 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F57B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F583 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F58B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F593 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F59B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F5FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F603 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F60B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F613 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F61B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F623 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F62B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F633 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F63B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F643 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F64B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F653 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F65B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F663 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F66B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F673 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F67B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F683 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F68B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F693 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F69B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F6FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F703 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F70B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F713 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F71B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F723 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F72B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F733 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F73B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F743 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F74B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F753 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F75B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F763 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F76B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F773 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F77B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F783 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F78B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F793 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F79B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F7FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F803 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F80B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F813 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F81B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F823 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F82B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F833 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F83B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F843 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F84B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F853 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F85B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F863 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F86B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F873 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F87B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F883 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F88B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F893 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F89B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F8FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F903 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F90B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F913 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F91B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F923 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F92B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F933 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F93B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F943 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F94B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F953 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F95B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F963 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F96B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F973 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F97B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F983 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F98B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F993 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F99B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9A3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9AB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9B3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9BB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9C3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9CB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9D3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9DB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9E3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9EB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9F3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; F9FB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA03 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA0B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA13 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA1B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA23 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA2B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA33 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA3B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA43 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA4B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA53 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA5B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA63 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA6B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA73 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA7B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA83 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA8B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA93 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FA9B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FAA3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FAAB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FAB3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FABB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FAC3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FACB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FAD3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FADB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FAE3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FAEB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FAF3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FAFB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB03 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB0B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB13 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB1B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB23 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB2B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB33 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB3B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB43 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB4B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB53 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB5B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB63 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB6B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB73 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB7B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB83 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB8B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB93 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FB9B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBA3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBAB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBB3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBBB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBC3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBCB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBD3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBDB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBE3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBEB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBF3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FBFB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC03 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC0B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC13 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC1B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC23 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC2B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC33 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC3B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC43 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC4B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC53 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC5B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC63 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC6B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC73 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC7B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC83 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC8B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC93 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FC9B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCA3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCAB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCB3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCBB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCC3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCCB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCD3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCDB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCE3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCEB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCF3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FCFB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD03 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD0B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD13 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD1B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD23 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD2B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD33 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD3B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD43 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD4B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD53 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD5B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD63 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD6B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD73 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD7B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD83 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD8B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD93 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FD9B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDA3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDAB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDB3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDBB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDC3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDCB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDD3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDDB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDE3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDEB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDF3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FDFB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE03 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE0B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE13 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE1B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE23 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE2B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE33 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE3B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE43 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE4B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE53 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE5B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE63 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE6B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE73 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE7B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE83 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE8B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE93 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FE9B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEA3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEAB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEB3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEBB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEC3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FECB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FED3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEDB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEE3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEEB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEF3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FEFB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF03 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF0B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF13 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF1B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF23 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF2B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF33 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF3B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF43 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF4B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF53 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF5B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF63 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF6B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF73 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF7B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF83 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF8B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF93 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FF9B ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFA3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFAB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFB3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFBB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFC3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFCB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFD3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFDB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFE3 ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF   ; FFEB ........
        .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF       ; FFF3 .......
        .word NMI                               ; FFFA NMI vector
        .word Reset                             ; FFFC Reset vector
        .word IRQ                               ; FFFE IRQ vector
