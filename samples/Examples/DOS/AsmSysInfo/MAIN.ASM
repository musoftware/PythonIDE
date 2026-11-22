; (c) 2026 Musoftware - https://musoftwares.com - MIT License
;
; AsmSysInfo - a 16-bit DOS .COM program in MASM syntax (built by JWasm -bin, runs in DOSBox-X).
; A key-driven menu that asks DOS and the BIOS about the machine:
;   1  DOS version          INT 21h AH=30h
;   2  Today's date         INT 21h AH=2Ah
;   3  The time             INT 21h AH=2Ch
;   4  Memory / equipment   INT 12h (conventional memory in KB), INT 11h (equipment word: floppies, video)
;   5  Shout a line         INT 21h AH=0Ah (buffered input), then the text in upper case
;   Q  Quit                 INT 21h AH=4Ch
; Output goes through DOS (AH=09h / 02h), so "AsmSysInfo > OUT.TXT" works too. F5 can also step it in RAD IDE's
; 8086 emulator; Ctrl+F5 runs it in DOSBox-X.
        .model tiny
        .code
        org 100h

start:  mov dx, offset banner
        call puts
menu:   mov dx, offset menu_s
        call puts
        mov ah, 08h                 ; read a key without echo -> AL
        int 21h
        cmp al, 'a'                 ; lower -> upper case
        jb  nocase
        cmp al, 'z'
        ja  nocase
        sub al, 20h
nocase: mov dl, al                  ; echo the choice and a new line
        push ax
        mov ah, 02h
        int 21h
        call crlf
        pop ax
        cmp al, '1'
        je  dosver
        cmp al, '2'
        je  date
        cmp al, '3'
        je  time
        cmp al, '4'
        je  memory
        cmp al, '5'
        je  shout
        cmp al, 'Q'
        je  quit
        cmp al, 27                  ; Esc
        je  quit
        mov dx, offset bad_s
        call puts
        jmp menu

dosver: mov ah, 30h                 ; AL = major, AH = minor
        int 21h
        push ax
        mov dx, offset ver_s
        call puts
        pop ax
        push ax
        xor ah, ah
        call putnum
        mov dl, '.'
        call putc
        pop ax
        mov al, ah
        xor ah, ah
        cmp al, 10                  ; "6.22": two digits for the minor version
        jae ver2
        mov dl, '0'
        call putc
ver2:   call putnum
        call crlf
        jmp menu

date:   mov ah, 2Ah                 ; CX = year, DH = month, DL = day, AL = day of week (0 = Sunday)
        int 21h
        push cx
        push dx
        push ax                     ; AL = day of the week (INT 21h AH=09h changes AL)
        mov dx, offset date_s
        call puts
        pop ax
        xor ah, ah                  ; day name
        mov bl, 10
        mul bl                      ; AX = AL * 10: index into the day names (10 bytes each)
        mov dx, offset days
        add dx, ax
        call puts
        pop dx
        push dx
        mov al, dl
        xor ah, ah
        call put2
        mov dl, '/'
        call putc
        pop dx
        mov al, dh
        xor ah, ah
        call put2
        mov dl, '/'
        call putc
        pop ax
        call putnum
        call crlf
        jmp menu

time:   mov ah, 2Ch                 ; CH = hour, CL = minutes, DH = seconds
        int 21h
        push dx
        push cx
        mov dx, offset time_s
        call puts
        pop cx
        push cx
        mov al, ch
        xor ah, ah
        call put2
        mov dl, ':'
        call putc
        pop cx
        mov al, cl
        xor ah, ah
        call put2
        mov dl, ':'
        call putc
        pop dx
        mov al, dh
        xor ah, ah
        call put2
        call crlf
        jmp menu

memory: int 12h                     ; AX = conventional memory in KB
        push ax
        mov dx, offset mem_s
        call puts
        pop ax
        call putnum
        mov dx, offset kb_s
        call puts
        int 11h                     ; AX = equipment word
        push ax
        mov dx, offset flop_s
        call puts
        pop ax
        push ax
        test al, 1                  ; bit 0: floppy drives present, bits 6-7: count - 1
        jz nofl
        mov cl, 6
        shr al, cl
        and al, 3
        inc al
        jmp flp
nofl:   xor al, al
flp:    xor ah, ah
        call putnum
        call crlf
        mov dx, offset vid_s
        call puts
        pop ax
        mov cl, 4                   ; bits 4-5: initial video mode (3 = monochrome)
        shr al, cl
        and al, 3
        mov dx, offset color_s
        cmp al, 3
        jne vid
        mov dx, offset mono_s
vid:    call puts
        jmp menu

shout:  mov dx, offset ask_s
        call puts
        mov dx, offset inbuf        ; buffered input: [max][count][text...]
        mov ah, 0Ah
        int 21h
        call crlf
        mov si, offset inbuf + 2
        xor ch, ch
        mov cl, inbuf + 1
        jcxz shdone
up:     mov al, [si]
        cmp al, 'a'
        jb  upnext
        cmp al, 'z'
        ja  upnext
        sub al, 20h
        mov [si], al
upnext: inc si
        loop up
shdone: mov byte ptr [si], '$'
        mov dx, offset shout_s
        call puts
        mov dx, offset inbuf + 2
        call puts
        mov dl, '!'
        call putc
        call crlf
        jmp menu

quit:   mov dx, offset bye_s
        call puts
        mov ax, 4C00h
        int 21h

; ------------------------------------------------------------------ helpers
puts:   mov ah, 09h                 ; DS:DX = $-terminated text
        int 21h
        ret

putc:   mov ah, 02h                 ; DL = character
        int 21h
        ret

crlf:   mov dx, offset nl
        jmp puts

put2:   cmp ax, 10                  ; AX < 100 as two digits ("07")
        jae putnum
        push ax
        mov dl, '0'
        call putc
        pop ax
putnum: push bx                     ; AX = unsigned number in decimal
        push cx
        push dx
        mov bx, 10
        xor cx, cx
pn1:    xor dx, dx
        div bx
        push dx
        inc cx
        or ax, ax
        jnz pn1
pn2:    pop dx
        add dl, '0'
        mov ah, 02h
        int 21h
        loop pn2
        pop dx
        pop cx
        pop bx
        ret

; ------------------------------------------------------------------ data
banner  db 'AsmSysInfo - a .COM program written in 8086 assembly (RAD IDE)', 13, 10, '$'
menu_s  db 13, 10, '1 DOS version  2 Date  3 Time  4 Memory  5 Shout  Q Quit > $'
bad_s   db 'Unknown choice.', 13, 10, '$'
ver_s   db 'DOS version: $'
date_s  db 'Today is $'
days    db 'Sunday   $', 'Monday   $', 'Tuesday  $', 'Wednesday$', 'Thursday $', 'Friday   $', 'Saturday $'
time_s  db 'The time is $'
mem_s   db 'Conventional memory: $'
kb_s    db ' KB', 13, 10, '$'
flop_s  db 'Floppy drives: $'
vid_s   db 'Video: $'
color_s db 'colour', 13, 10, '$'
mono_s  db 'monochrome', 13, 10, '$'
ask_s   db 'Type a line: $'
shout_s db 'You said: $'
bye_s   db 'Goodbye!', 13, 10, '$'
nl      db 13, 10, '$'
inbuf   db 60, 0
        db 62 dup (0)
        end start
