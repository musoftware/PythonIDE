"""16-bit assembly code generator: a DOS .COM program in the MASM / TASM / emu8086 dialect.

It writes straight into the video memory at B800:0000, reads the keyboard with INT 16h and the mouse with
INT 33h. RAD IDE's own 8086 assembler (radide/emu8086) builds it into a real .COM file (no toolchain to
install); JWasm / UASM / MASM / TASM build it too (``jwasm -bin -Fo=main.com main.asm``).

The user code goes in the handler procedures (``btnOK_Click proc``). Registers do not have to be kept: the
dispatcher saves them. Run-time API (registers in, registers out)::

    tui_set_text      BX = control, SI = offset of a 0-terminated string
    tui_get_text      BX = control                -> SI = offset of the control's text
    tui_set_value     BX = control, AX = value    (check box 0/1, option 1, list index, progress)
    tui_get_value     BX = control                -> AX
    tui_set_visible   BX = control, AX = 0/1
    tui_set_enabled   BX = control, AX = 0/1
    tui_show_screen   AX = screen
    tui_msgbox        SI = text, DI = title (0-terminated)
    tui_quit
    tui_key           (word) the key of a KeyPress event; set it to 0 to cancel the key
"""
from __future__ import annotations

import re

from .common import App, Regions, build_app, chunks, line_of

CM = ("; ", "")
TXLEN = 121
INVERSE = {"je": "jne", "jz": "jnz", "jne": "je", "jnz": "jz", "jb": "jae", "jnae": "jnb", "jc": "jnc",
           "jae": "jb", "jnb": "jnae", "jnc": "jc", "ja": "jbe", "jnbe": "jna", "jbe": "ja", "jna": "jnbe",
           "jl": "jge", "jnge": "jnl", "jge": "jl", "jnl": "jnge", "jg": "jle", "jnle": "jng", "jle": "jg",
           "jng": "jnle", "js": "jns", "jns": "js", "jo": "jno", "jno": "jo", "jp": "jnp", "jnp": "jp",
           "jpe": "jpo", "jpo": "jpe"}


def lit(b: bytes) -> str:
    """db operand list of CP437 bytes: 'abc', 196, 'def'"""
    parts: list[str] = []
    run = ""
    for x in b:
        if 32 <= x < 127 and x not in (39, 34, 59):
            run += chr(x)
        else:
            if run:
                parts.append(f"'{run}'")
                run = ""
            parts.append(str(x))
    if run:
        parts.append(f"'{run}'")
    return ", ".join(parts)


def _words(label: str, values: list) -> list[str]:
    out = []
    for i, ch in enumerate(chunks([str(v) for v in values], 16)):
        out.append(f"{label if i == 0 else '':<8} dw {', '.join(ch)}")
    return out


RUNTIME = r"""
; ===================================================================== RAD IDE text-mode runtime
tui_cur    dw 0
tui_foc    dw 0
tui_run    dw 1
tui_key    dw 0
tui_mouse  dw 0
tui_hc     dw 0
tui_mb     dw 0
tui_mx     dw 0
tui_my     dw 0
tui_mp     dw 0
tui_shape  dw 0607h
tui_dump   dw 0
p_x        dw 0
p_y        dw 0
p_w        dw 0
p_bh       dw 0
p_a        dw 0
p_h        dw 0
p_s        dw 0
p_m        dw 0
p_pad      dw 0
p_pre      dw 0
p_skip     dw 0
p_pw       dw 0
fc_t       dw 0
ls_x       dw 0
ls_y       dw 0
ls_w       dw 0
ls_h       dw 0
ls_top     dw 0
ls_a       dw 0
ls_sa      dw 0
nx_d       dw 0
nx_c       dw 0
nx_best    dw 0
nx_wrap    dw 0
hk_k       dw 0
hk_t       dw 0
ck_x       dw 0
ck_y       dw 0
dm_it      dw 0
mn_m       dw 0
mn_it      dw 0
mn_fire    dw 0
mb_t       dw 0
mb_s       dw 0
mb_tl      dw 0
mb_w       dw 0
mb_x       dw 0
mb_y       dw 0
bx_y0      dw 0
s_empty    db 0
s_chk_on   db '[X] ', 0
s_chk_off  db '[ ] ', 0
s_opt_on   db '(*) ', 0
s_opt_off  db '( ) ', 0
s_ok       db '  OK  ', 0
s_dumpname db 'SCREEN.BIN', 0
box_s      db 218, 196, 191, 179, 192, 217
box_d      db 201, 205, 187, 186, 200, 188
alt_tab    db 'QWERTYUIOP', 0, 0, 0, 0, 'ASDFGHJKL', 0, 0, 0, 0, 0, 'ZXCVBNM'
dig_tab    db '1234567890'

; ---- SI -> CX = length of the 0-terminated string
tui_strlen proc
    push si
    push ax
    xor cx, cx
sl_1:
    lodsb
    or al, al
    jz sl_2
    inc cx
    jmp sl_1
sl_2:
    pop ax
    pop si
    ret
tui_strlen endp

; ---- DI = offset of the cell p_x, p_y ; ES = video segment
tui_di proc
    push ax
    push dx
    mov ax, 0B800h
    mov es, ax
    mov ax, p_y
    mov dx, COLS
    mul dx
    add ax, p_x
    shl ax, 1
    mov di, ax
    pop dx
    pop ax
    ret
tui_di endp

; ---- AL = character, AH = attribute at p_x, p_y
tui_putc_xy proc
    push di
    call tui_di
    stosw
    pop di
    ret
tui_putc_xy endp

; ---- p_w cells of character AL (attribute p_a) at p_x, p_y
tui_fill proc
    push ax
    push bx
    push cx
    push di
    mov bl, al
    call tui_di
    mov cx, COLS
    sub cx, p_x
    cmp cx, p_w
    jle fl_c
    mov cx, p_w
fl_c:
    cmp cx, 0
    jle fl_r
    mov al, bl
    mov ah, byte ptr p_a
    rep stosw
fl_r:
    pop di
    pop cx
    pop bx
    pop ax
    ret
tui_fill endp

; ---- p_w cells at p_x, p_y: p_pad spaces, the p_pre string, the p_s string (from p_skip; p_pw: '*')
;      with mask p_m ('1' = attribute p_h), then spaces; attribute p_a
tui_put proc
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    call tui_di
    mov cx, COLS
    sub cx, p_x
    cmp cx, p_w
    jle tp_c1
    mov cx, p_w
tp_c1:
    cmp cx, 0
    jg tp_c2
    jmp tp_done
tp_c2:
    mov bx, p_pad
tp_pad:
    cmp bx, 0
    jle tp_pre
    mov al, ' '
    mov ah, byte ptr p_a
    stosw
    dec bx
    dec cx
    jnz tp_pad
    jmp tp_done
tp_pre:
    mov si, p_pre
    or si, si
    jz tp_text
tp_pre1:
    lodsb
    or al, al
    jz tp_text
    mov ah, byte ptr p_a
    stosw
    dec cx
    jnz tp_pre1
    jmp tp_done
tp_text:
    mov si, p_s
    add si, p_skip
    mov bx, p_m
tp_t1:
    mov al, [si]
    or al, al
    jz tp_fill
    inc si
    cmp word ptr p_pw, 0
    je tp_t2
    mov al, '*'
tp_t2:
    mov ah, byte ptr p_a
    or bx, bx
    jz tp_t3
    mov dl, [bx]
    or dl, dl
    jz tp_t3m
    inc bx
    cmp dl, '1'
    jne tp_t3
    mov ah, byte ptr p_h
    jmp tp_t3
tp_t3m:
    xor bx, bx
tp_t3:
    stosw
    dec cx
    jnz tp_t1
    jmp tp_done
tp_fill:
    mov al, ' '
    mov ah, byte ptr p_a
    rep stosw
tp_done:
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_put endp

; ---- box at p_x, p_y, p_w x p_bh, attribute p_a, filled; AL = 0 single, 1 double
tui_box proc
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    mov si, offset box_s
    or al, al
    jz bo_1
    mov si, offset box_d
bo_1:
    mov ax, p_y
    mov bx_y0, ax
    call tui_di
    mov ah, byte ptr p_a
    mov al, [si]
    stosw
    mov cx, p_w
    sub cx, 2
    mov al, [si+1]
    rep stosw
    mov al, [si+2]
    stosw
    mov dx, p_bh
    sub dx, 2
bo_2:
    cmp dx, 0
    jle bo_3
    inc word ptr p_y
    call tui_di
    mov ah, byte ptr p_a
    mov al, [si+3]
    stosw
    mov cx, p_w
    sub cx, 2
    mov al, ' '
    rep stosw
    mov al, [si+3]
    stosw
    dec dx
    jmp bo_2
bo_3:
    inc word ptr p_y
    call tui_di
    mov ah, byte ptr p_a
    mov al, [si+4]
    stosw
    mov cx, p_w
    sub cx, 2
    mov al, [si+1]
    rep stosw
    mov al, [si+5]
    stosw
    mov ax, bx_y0
    mov p_y, ax
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_box endp

; ---- SI = run-length data (count, character, attribute ... 0) -> the screen
tui_blit proc
    push ax
    push cx
    push si
    push di
    mov ax, 0B800h
    mov es, ax
    xor di, di
bl_1:
    lodsb
    or al, al
    jz bl_2
    xor ch, ch
    mov cl, al
    lodsw
    rep stosw
    jmp bl_1
bl_2:
    pop di
    pop si
    pop cx
    pop ax
    ret
tui_blit endp

; ---- AX = 0 hide / 1 show the mouse pointer (nested)
tui_mouse_show proc
    cmp word ptr tui_mouse, 0
    je ms_ret
    push ax
    push bx
    push cx
    push dx
    or ax, ax
    jz ms_hide
    dec word ptr tui_hc
    jnz ms_pop
    mov ax, 1
    int 33h
    jmp ms_pop
ms_hide:
    inc word ptr tui_hc
    cmp word ptr tui_hc, 1
    jne ms_pop
    mov ax, 2
    int 33h
ms_pop:
    pop dx
    pop cx
    pop bx
    pop ax
ms_ret:
    ret
tui_mouse_show endp

tui_poll_mouse proc
    push ax
    push bx
    push cx
    push dx
    mov word ptr tui_mb, 0
    cmp word ptr tui_mouse, 0
    je pm_ret
    mov ax, 3
    int 33h
    and bx, 7
    mov tui_mb, bx
    mov ax, cx
    mov cl, 3
    shr ax, cl
    mov tui_mx, ax
    mov ax, dx
    shr ax, cl
    mov tui_my, ax
pm_ret:
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_poll_mouse endp

; ---- AX (from INT 16h) -> key code: ASCII, or 256 + scan code
tui_norm_key proc
    cmp al, 0
    je nk_ext
    cmp al, 0E0h
    jne nk_asc
    cmp ah, 0
    je nk_asc
nk_ext:
    mov al, ah
    xor ah, ah
    add ax, 256
    ret
nk_asc:
    xor ah, ah
    ret
tui_norm_key endp

; ---- -> AX = key code (0 = none)
tui_read_key proc
    mov ah, 01h
    int 16h
    jz rk_none
    mov ah, 00h
    int 16h
    call tui_norm_key
    ret
rk_none:
    xor ax, ax
    ret
tui_read_key endp

; ---- -> AX = key (0 = none), CX = 1 when the left button went down (tui_mx, tui_my)
tui_get_event proc
    xor cx, cx
    cmp word ptr tui_mouse, 0
    jne ge_poll
    mov ah, 00h
    int 16h
    call tui_norm_key
    ret
ge_poll:
    call tui_read_key
    call tui_poll_mouse
    test word ptr tui_mb, 1
    jz ge_up
    cmp word ptr tui_mp, 0
    jne ge_ret
    mov word ptr tui_mp, 1
    mov cx, 1
    ret
ge_up:
    mov word ptr tui_mp, 0
ge_ret:
    ret
tui_get_event endp

; ---- AX = key code of Alt+letter -> AX = the letter (0 = not an Alt+letter / digit)
tui_alt_key proc
    push bx
    sub ax, 256
    cmp ax, 16
    jb ak_dig
    cmp ax, 50
    ja ak_dig
    mov bx, ax
    sub bx, 16
    mov al, alt_tab[bx]
    xor ah, ah
    pop bx
    ret
ak_dig:
    cmp ax, 120
    jb ak_none
    cmp ax, 129
    ja ak_none
    sub ax, 120
    mov bx, ax
    mov al, dig_tab[bx]
    xor ah, ah
    pop bx
    ret
ak_none:
    xor ax, ax
    pop bx
    ret
tui_alt_key endp

; ---- CX = min(length of p_s, p_w)
fc_len proc
    push si
    mov si, p_s
    call tui_strlen
    pop si
    cmp cx, p_w
    jbe fl_1
    mov cx, p_w
fl_1:
    ret
fc_len endp

; ---- BX = control: draw its live part
tui_face proc
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    xor ax, ax
    call tui_mouse_show
    mov si, bx
    shl si, 1
    cmp word ptr t_zi[si], 0
    jne fc_vis
    jmp fc_ret
fc_vis:
    mov ax, t_zt[si]
    cmp ax, 9
    jne fc_go
    jmp fc_ret
fc_go:
    mov fc_t, ax
    mov ax, t_za[si]
    mov p_a, ax
    mov ax, t_zb[si]
    mov p_h, ax
    cmp word ptr t_zn[si], 0
    jne fc_en
    mov ax, t_za[si]
    and ax, 0F0h
    or ax, 8
    mov p_a, ax
    mov p_h, ax
    jmp fc_at
fc_en:
    cmp bx, tui_foc
    jne fc_at
    cmp word ptr fc_t, 2
    jb fc_at
    cmp word ptr fc_t, 5
    ja fc_at
    mov ax, t_zf[si]
    mov p_a, ax
    mov ax, t_zg[si]
    mov p_h, ax
fc_at:
    mov ax, t_zx[si]
    mov p_x, ax
    mov ax, t_zy[si]
    mov p_y, ax
    mov ax, t_zw[si]
    mov p_w, ax
    xor ax, ax
    mov p_pad, ax
    mov p_pre, ax
    mov p_skip, ax
    mov p_pw, ax
    mov ax, t_txp[si]
    mov p_s, ax
    mov ax, t_hmp[si]
    mov p_m, ax
    mov ax, fc_t
    cmp ax, 1
    je fc_label
    cmp ax, 2
    je fc_button
    cmp ax, 3
    je fc_text
    cmp ax, 4
    je fc_check
    cmp ax, 5
    je fc_opt
    cmp ax, 6
    jne fc_n6
    jmp fc_list
fc_n6:
    cmp ax, 7
    jne fc_n7
    jmp fc_prog
fc_n7:
    jmp fc_draw
fc_label:
    call fc_len
    mov ax, t_zj[si]
    cmp ax, 1
    je fc_center
    cmp ax, 2
    jne fc_draw
    mov ax, p_w
    sub ax, cx
    mov p_pad, ax
    jmp fc_draw
fc_button:
    call fc_len
fc_center:
    mov ax, p_w
    sub ax, cx
    shr ax, 1
    mov p_pad, ax
    jmp fc_draw
fc_text:
    mov word ptr p_m, 0
    mov ax, p_a
    mov p_h, ax
    mov ax, t_zj[si]
    mov p_pw, ax
    cmp bx, tui_foc
    jne fc_draw
    push si
    mov si, p_s
    call tui_strlen
    pop si
    cmp cx, p_w
    jb fc_draw
    sub cx, p_w
    inc cx
    mov p_skip, cx
    jmp fc_draw
fc_check:
    mov ax, offset s_chk_off
    cmp word ptr t_zv[si], 0
    je fc_ck1
    mov ax, offset s_chk_on
fc_ck1:
    mov p_pre, ax
    jmp fc_draw
fc_opt:
    mov ax, offset s_opt_off
    cmp word ptr t_zv[si], 0
    je fc_op1
    mov ax, offset s_opt_on
fc_op1:
    mov p_pre, ax
fc_draw:
    call tui_put
    jmp fc_ret
fc_list:
    mov ax, t_zx[si]
    mov ls_x, ax
    mov ax, t_zy[si]
    mov ls_y, ax
    mov ax, t_zw[si]
    mov ls_w, ax
    mov ax, t_zh[si]
    mov ls_h, ax
    cmp word ptr t_zj[si], 0
    je fl_nb
    inc word ptr ls_x
    inc word ptr ls_y
    sub word ptr ls_w, 2
    sub word ptr ls_h, 2
fl_nb:
    mov ax, t_zv[si]
    mov dx, t_zp[si]
    cmp ax, 0
    jl fl_t2
    cmp ax, dx
    jge fl_t1
    mov dx, ax
fl_t1:
    mov cx, dx
    add cx, ls_h
    cmp ax, cx
    jl fl_t2
    mov dx, ax
    sub dx, ls_h
    inc dx
fl_t2:
    mov t_zp[si], dx
    mov ls_top, dx
    mov ax, t_zl[si]
    mov ls_sa, ax
    cmp word ptr t_zn[si], 0
    jne fl_sa
    mov ax, p_a
    mov ls_sa, ax
fl_sa:
    mov ax, p_a
    mov ls_a, ax
    mov ax, ls_x
    mov p_x, ax
    mov ax, ls_w
    mov p_w, ax
    mov word ptr p_m, 0
    xor cx, cx
fl_row:
    cmp cx, ls_h
    jl fl_row2
    jmp fc_ret
fl_row2:
    mov ax, ls_y
    add ax, cx
    mov p_y, ax
    mov dx, ls_top
    add dx, cx
    mov ax, ls_a
    mov p_a, ax
    mov word ptr p_s, offset s_empty
    cmp dx, t_z2[si]
    jge fl_draw
    mov di, t_z1[si]
    add di, dx
    shl di, 1
    mov ax, t_itp[di]
    mov p_s, ax
    cmp dx, t_zv[si]
    jne fl_draw
    mov ax, ls_sa
    mov p_a, ax
fl_draw:
    mov ax, p_a
    mov p_h, ax
    call tui_put
    inc cx
    jmp fl_row
fc_prog:
    mov cx, t_zm[si]
    cmp cx, 1
    jge fp_1
    mov cx, 1
fp_1:
    mov ax, t_zv[si]
    cmp ax, 0
    jge fp_2
    xor ax, ax
fp_2:
    cmp ax, cx
    jle fp_3
    mov ax, cx
fp_3:
    mul word ptr p_w
    div cx
    mov dx, ax
    call tui_di
    xor cx, cx
fp_4:
    cmp cx, p_w
    jge fc_ret
    mov al, 0B0h
    cmp cx, dx
    jge fp_5
    mov al, 0DBh
fp_5:
    mov ah, byte ptr p_a
    stosw
    inc cx
    jmp fp_4
fc_ret:
    mov ax, 1
    call tui_mouse_show
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_face endp

; ---- the text cursor in the focused text box (hidden otherwise)
tui_cursor proc
    push ax
    push bx
    push cx
    push dx
    push si
    mov bx, tui_foc
    or bx, bx
    jz cu_hide
    mov si, bx
    shl si, 1
    cmp word ptr t_zt[si], 3
    jne cu_hide
    push si
    mov si, t_txp[si]
    call tui_strlen
    pop si
    mov ax, t_zw[si]
    dec ax
    cmp cx, ax
    jbe cu_1
    mov cx, ax
cu_1:
    mov dx, t_zx[si]
    add dx, cx
    mov ax, t_zy[si]
    mov dh, al
    mov ah, 02h
    mov bh, 0
    int 10h
    mov ah, 01h
    mov cx, tui_shape
    int 10h
    jmp cu_ret
cu_hide:
    mov ah, 01h
    mov cx, 2000h
    int 10h
cu_ret:
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_cursor endp

tui_redraw proc
    push ax
    push bx
    push si
    xor ax, ax
    call tui_mouse_show
    mov si, tui_cur
    shl si, 1
    mov si, t_stp[si]
    call tui_blit
    mov bx, 1
rd_1:
    cmp bx, NC
    ja rd_2
    mov si, bx
    shl si, 1
    mov ax, t_zs[si]
    cmp ax, tui_cur
    jne rd_n
    call tui_face
rd_n:
    inc bx
    jmp rd_1
rd_2:
    call tui_cursor
    mov ax, 1
    call tui_mouse_show
    pop si
    pop bx
    pop ax
    ret
tui_redraw endp

; ---- BX = control -> AX = 1 when it can take the focus
tui_can_focus proc
    push si
    mov si, bx
    shl si, 1
    xor ax, ax
    cmp word ptr t_zo[si], 0
    jle cf_r
    cmp word ptr t_zi[si], 0
    je cf_r
    cmp word ptr t_zn[si], 0
    je cf_r
    mov ax, 1
cf_r:
    pop si
    ret
tui_can_focus endp

; ---- AX = screen
tui_show_screen proc
    push ax
    push bx
    push cx
    push si
    mov tui_cur, ax
    mov word ptr tui_foc, 0
    xor cx, cx
    mov bx, 1
ss_1:
    cmp bx, NC
    ja ss_2
    mov si, bx
    shl si, 1
    mov ax, t_zs[si]
    cmp ax, tui_cur
    jne ss_n
    call tui_can_focus
    or ax, ax
    jz ss_n
    or cx, cx
    jz ss_take
    mov ax, t_zo[si]
    push si
    mov si, cx
    shl si, 1
    cmp ax, t_zo[si]
    pop si
    jge ss_n
ss_take:
    mov cx, bx
ss_n:
    inc bx
    jmp ss_1
ss_2:
    mov tui_foc, cx
    call tui_redraw
    mov si, tui_cur
    shl si, 1
    test word ptr t_sv[si], 1
    jz ss_ret
    mov bx, tui_cur
    mov ax, 4
    call tui_fire_screen
ss_ret:
    pop si
    pop cx
    pop bx
    pop ax
    ret
tui_show_screen endp

; ---- BX = control (0 = none)
tui_focus proc
    push ax
    push bx
    mov ax, tui_foc
    mov tui_foc, bx
    push bx
    or ax, ax
    jz fo_1
    cmp ax, bx
    je fo_1
    mov bx, ax
    call tui_face
fo_1:
    pop bx
    or bx, bx
    jz fo_2
    call tui_face
fo_2:
    call tui_cursor
    pop bx
    pop ax
    ret
tui_focus endp

; ---- AX = 1 next / -1 previous control in tab order
tui_next proc
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    mov nx_d, ax
    xor cx, cx
    mov bx, tui_foc
    or bx, bx
    jz nx_0
    mov si, bx
    shl si, 1
    mov cx, t_zo[si]
nx_0:
    mov nx_c, cx
    mov word ptr nx_best, 0
    mov word ptr nx_wrap, 0
    mov bx, 1
nx_1:
    cmp bx, NC
    jbe nx_1b
    jmp nx_end
nx_1b:
    mov si, bx
    shl si, 1
    mov ax, t_zs[si]
    cmp ax, tui_cur
    jne nx_next
    call tui_can_focus
    or ax, ax
    jz nx_next
    mov dx, t_zo[si]
    cmp word ptr nx_d, 0
    jl nx_back
    cmp dx, nx_c
    jle nx_fw
    mov di, nx_best
    or di, di
    jz nx_fb
    shl di, 1
    cmp dx, t_zo[di]
    jge nx_fw
nx_fb:
    mov nx_best, bx
nx_fw:
    mov di, nx_wrap
    or di, di
    jz nx_fw2
    shl di, 1
    cmp dx, t_zo[di]
    jge nx_next
nx_fw2:
    mov nx_wrap, bx
    jmp nx_next
nx_back:
    cmp dx, nx_c
    jge nx_bw
    mov di, nx_best
    or di, di
    jz nx_bb
    shl di, 1
    cmp dx, t_zo[di]
    jle nx_bw
nx_bb:
    mov nx_best, bx
nx_bw:
    mov di, nx_wrap
    or di, di
    jz nx_bw2
    shl di, 1
    cmp dx, t_zo[di]
    jle nx_next
nx_bw2:
    mov nx_wrap, bx
nx_next:
    inc bx
    jmp nx_1
nx_end:
    mov bx, nx_best
    or bx, bx
    jnz nx_go
    mov bx, nx_wrap
nx_go:
    or bx, bx
    jz nx_ret
    call tui_focus
nx_ret:
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_next endp

; ---- BX = control: Enter / Space / click / hotkey
tui_activate proc
    push ax
    push bx
    push cx
    push si
    push di
    mov si, bx
    shl si, 1
    mov ax, t_zt[si]
    cmp ax, 2
    je ac_fire
    cmp ax, 6
    je ac_fire
    cmp ax, 4
    je ac_check
    cmp ax, 5
    je ac_opt
    jmp ac_ret
ac_check:
    mov ax, 1
    sub ax, t_zv[si]
    mov t_zv[si], ax
    call tui_face
    jmp ac_fire
ac_opt:
    mov cx, 1
ac_o1:
    cmp cx, NC
    ja ac_o3
    cmp cx, bx
    je ac_o2
    mov di, cx
    shl di, 1
    cmp word ptr t_zt[di], 5
    jne ac_o2
    mov ax, t_zs[di]
    cmp ax, t_zs[si]
    jne ac_o2
    mov ax, t_zr[di]
    cmp ax, t_zr[si]
    jne ac_o2
    cmp word ptr t_zv[di], 0
    je ac_o2
    mov word ptr t_zv[di], 0
    push bx
    mov bx, cx
    call tui_face
    pop bx
ac_o2:
    inc cx
    jmp ac_o1
ac_o3:
    mov word ptr t_zv[si], 1
    call tui_face
ac_fire:
    mov ax, 1
    call tui_fire
ac_ret:
    pop di
    pop si
    pop cx
    pop bx
    pop ax
    ret
tui_activate endp

; ---- BX = list box, AX = +1 / -1
tui_list_move proc
    push ax
    push cx
    push si
    mov si, bx
    shl si, 1
    mov cx, t_z2[si]
    or cx, cx
    jz lm_ret
    add ax, t_zv[si]
    cmp ax, 0
    jge lm_1
    xor ax, ax
lm_1:
    cmp ax, cx
    jl lm_2
    mov ax, cx
    dec ax
lm_2:
    cmp ax, t_zv[si]
    je lm_ret
    mov t_zv[si], ax
    call tui_face
    mov ax, 2
    call tui_fire
lm_ret:
    pop si
    pop cx
    pop ax
    ret
tui_list_move endp

; ---- AX = key code
tui_handle_key proc
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    mov tui_key, ax
    mov bx, tui_foc
    or bx, bx
    jz hk_1
    mov si, bx
    shl si, 1
    test word ptr t_ze[si], 4
    jz hk_1
    mov ax, 3
    call tui_fire
hk_1:
    cmp word ptr tui_key, 0
    jne hk_1b
    jmp hk_ret
hk_1b:
    mov si, tui_cur
    shl si, 1
    test word ptr t_sv[si], 4
    jz hk_2
    mov bx, tui_cur
    mov ax, 3
    call tui_fire_screen
hk_2:
    mov ax, tui_key
    or ax, ax
    jnz hk_2b
    jmp hk_ret
hk_2b:
    mov hk_k, ax
    mov bx, tui_foc
    xor cx, cx
    or bx, bx
    jz hk_3
    mov si, bx
    shl si, 1
    mov cx, t_zt[si]
hk_3:
    mov hk_t, cx
    cmp cx, 3
    je hk_tb
    jmp hk_keys
hk_tb:
    cmp ax, 8
    jne hk_tb2
    mov di, si
    mov si, t_txp[si]
    call tui_strlen
    or cx, cx
    jz hk_r1
    add si, cx
    dec si
    mov byte ptr [si], 0
    mov si, di
    call tui_face
    call tui_cursor
    test word ptr t_ze[si], 2
    jz hk_r1
    mov ax, 2
    call tui_fire
hk_r1:
    jmp hk_ret
hk_tb2:
    cmp ax, 32
    jb hk_keys
    cmp ax, 256
    jae hk_keys
    mov di, si
    mov si, t_txp[si]
    call tui_strlen
    cmp cx, t_zm[di]
    jae hk_r1
    add si, cx
    mov dx, hk_k
    mov [si], dl
    mov byte ptr [si+1], 0
    mov si, di
    call tui_face
    call tui_cursor
    test word ptr t_ze[si], 2
    jz hk_r1
    mov ax, 2
    call tui_fire
    jmp hk_ret
hk_keys:
    mov ax, hk_k
    cmp ax, 9
    jne hk_k1
    mov ax, 1
    call tui_next
    jmp hk_ret
hk_k1:
    cmp ax, 271
    jne hk_k2
    mov ax, -1
    call tui_next
    jmp hk_ret
hk_k2:
    cmp ax, 336
    je hk_down
    cmp ax, 333
    jne hk_k3
hk_down:
    mov ax, 1
    cmp word ptr hk_t, 6
    jne hk_dn2
    call tui_list_move
    jmp hk_ret
hk_dn2:
    call tui_next
    jmp hk_ret
hk_k3:
    cmp ax, 328
    je hk_up
    cmp ax, 331
    jne hk_k4
hk_up:
    mov ax, -1
    cmp word ptr hk_t, 6
    jne hk_up2
    call tui_list_move
    jmp hk_ret
hk_up2:
    call tui_next
    jmp hk_ret
hk_k4:
    cmp ax, 13
    jne hk_k5
    cmp word ptr hk_t, 3
    jne hk_en2
    mov ax, 1
    call tui_next
    jmp hk_ret
hk_en2:
    or bx, bx
    jz hk_rj
    call tui_activate
hk_rj:
    jmp hk_ret
hk_k5:
    cmp ax, 32
    jne hk_k6
    or bx, bx
    jz hk_rj
    cmp word ptr hk_t, 6
    je hk_rj
    call tui_activate
    jmp hk_ret
hk_k6:
    cmp ax, 27
    jne hk_k7
    mov si, tui_cur
    shl si, 1
    mov bx, t_sk[si]
    or bx, bx
    jz hk_esc2
    call tui_activate
    jmp hk_ret
hk_esc2:
    cmp word ptr t_se[si], 0
    je hk_rj
    mov word ptr tui_run, 0
    jmp hk_ret
hk_k7:
    cmp ax, 324
    jne hk_hot
    mov si, tui_cur
    shl si, 1
    mov ax, t_sm[si]
    or ax, ax
    jz hk_rj
    call tui_menu
    jmp hk_ret
hk_hot:
    xor dx, dx
    cmp ax, 256
    jbe hk_h2
    call tui_alt_key
    mov dx, ax
    or dx, dx
    jz hk_h2
    mov cx, 1
hk_m1:
    cmp cx, NM
    ja hk_h3
    mov di, cx
    shl di, 1
    mov ax, t_msc[di]
    cmp ax, tui_cur
    jne hk_m2
    cmp t_mky[di], dx
    jne hk_m2
    mov ax, cx
    call tui_menu
    jmp hk_ret
hk_m2:
    inc cx
    jmp hk_m1
hk_h2:
    or dx, dx
    jnz hk_h3
    mov ax, hk_k
    cmp ax, 256
    jae hk_rj
    cmp word ptr hk_t, 3
    je hk_rj
    cmp al, 'a'
    jb hk_upok
    cmp al, 'z'
    ja hk_upok
    sub al, 32
hk_upok:
    xor ah, ah
    mov dx, ax
hk_h3:
    mov cx, 1
hk_c1:
    cmp cx, NC
    ja hk_ret
    mov di, cx
    shl di, 1
    mov ax, t_zs[di]
    cmp ax, tui_cur
    jne hk_c2
    cmp t_zk[di], dx
    jne hk_c2
    mov bx, cx
    call tui_can_focus
    or ax, ax
    jz hk_c2
    call tui_focus
    mov ax, t_zt[di]
    cmp ax, 2
    je hk_cact
    cmp ax, 4
    je hk_cact
    cmp ax, 5
    jne hk_ret
hk_cact:
    call tui_activate
    jmp hk_ret
hk_c2:
    inc cx
    jmp hk_c1
hk_ret:
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_handle_key endp

; ---- CX = column, DX = row of a left click
tui_click proc
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    mov ck_x, cx
    mov ck_y, dx
    mov si, tui_cur
    shl si, 1
    mov bx, t_sb[si]
    or bx, bx
    jz ck_ctl
    mov di, bx
    shl di, 1
    mov ax, t_zy[di]
    cmp ax, ck_y
    jne ck_ctl
    mov cx, 1
ck_m1:
    cmp cx, NM
    jbe ck_m1b
    jmp ck_ret
ck_m1b:
    mov di, cx
    shl di, 1
    mov ax, t_msc[di]
    cmp ax, tui_cur
    jne ck_m2
    mov ax, ck_x
    cmp ax, t_mtx[di]
    jl ck_m2
    mov dx, t_mtx[di]
    add dx, t_mtl[di]
    cmp ax, dx
    jge ck_m2
    mov ax, cx
    call tui_menu
    jmp ck_ret
ck_m2:
    inc cx
    jmp ck_m1
ck_ctl:
    mov bx, NC
ck_c1:
    cmp bx, 1
    jge ck_c1b
    jmp ck_ret
ck_c1b:
    mov si, bx
    shl si, 1
    mov ax, t_zs[si]
    cmp ax, tui_cur
    jne ck_c2
    call tui_can_focus
    or ax, ax
    jz ck_c2
    mov ax, ck_x
    cmp ax, t_zx[si]
    jl ck_c2
    mov dx, t_zx[si]
    add dx, t_zw[si]
    cmp ax, dx
    jge ck_c2
    mov ax, ck_y
    cmp ax, t_zy[si]
    jl ck_c2
    mov dx, t_zy[si]
    add dx, t_zh[si]
    cmp ax, dx
    jge ck_c2
    call tui_focus
    mov ax, t_zt[si]
    cmp ax, 6
    je ck_list
    cmp ax, 3
    je ck_ret
    call tui_activate
    jmp ck_ret
ck_list:
    mov dx, t_zy[si]
    mov cx, t_zh[si]
    cmp word ptr t_zj[si], 0
    je ck_l1
    inc dx
    sub cx, 2
ck_l1:
    mov ax, ck_y
    sub ax, dx
    cmp ax, 0
    jl ck_ret
    cmp ax, cx
    jge ck_ret
    add ax, t_zp[si]
    cmp ax, t_z2[si]
    jge ck_ret
    cmp ax, t_zv[si]
    je ck_l2
    mov t_zv[si], ax
    call tui_face
    test word ptr t_ze[si], 2
    jz ck_l2
    mov ax, 2
    call tui_fire
ck_l2:
    mov ax, 1
    call tui_fire
    jmp ck_ret
ck_c2:
    dec bx
    jmp ck_c1
ck_ret:
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_click endp

; ---- AX = menu, CX = item, DX = +1 / -1 -> AX = next item that is not a separator (-1 = none)
tui_step proc
    push bx
    push cx
    push si
    push di
    mov si, ax
    shl si, 1
    mov bx, t_mic[si]
    mov ax, -1
    or bx, bx
    jz st_ret
    mov di, bx
st_1:
    add cx, dx
    cmp cx, 0
    jge st_2
    mov cx, bx
    dec cx
st_2:
    cmp cx, bx
    jl st_3
    xor cx, cx
st_3:
    push si
    mov ax, t_mi1[si]
    add ax, cx
    mov si, ax
    shl si, 1
    cmp word ptr t_isp[si], 0
    pop si
    jne st_4
    mov ax, cx
    jmp st_ret
st_4:
    dec di
    jnz st_1
    mov ax, -1
st_ret:
    pop di
    pop si
    pop cx
    pop bx
    ret
tui_step endp

; ---- AX = menu, CX = selected item: the open drop-down
tui_draw_menu proc
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    mov dm_it, cx
    push ax
    xor ax, ax
    call tui_mouse_show
    pop ax
    mov si, ax
    shl si, 1
    mov di, t_msc[si]
    shl di, 1
    mov bx, t_sb[di]
    shl bx, 1
    mov ax, t_mtx[si]
    mov p_x, ax
    mov ax, t_zy[bx]
    mov p_y, ax
    mov ax, t_mtl[si]
    mov p_w, ax
    mov ax, t_mtsp[si]
    mov p_s, ax
    mov ax, t_mtmp[si]
    mov p_m, ax
    mov ax, t_zl[bx]
    mov p_a, ax
    mov ax, t_zg[bx]
    mov p_h, ax
    xor ax, ax
    mov p_pad, ax
    mov p_pre, ax
    mov p_skip, ax
    mov p_pw, ax
    call tui_put
    mov ax, t_mdx[si]
    mov p_x, ax
    mov ax, t_mdy[si]
    mov p_y, ax
    mov ax, t_mdw[si]
    mov p_w, ax
    mov ax, t_mdh[si]
    mov p_bh, ax
    mov ax, t_za[bx]
    mov p_a, ax
    xor al, al
    call tui_box
    xor cx, cx
dm_1:
    cmp cx, t_mic[si]
    jl dm_1b
    jmp dm_done
dm_1b:
    mov di, t_mi1[si]
    add di, cx
    shl di, 1
    mov ax, t_mdy[si]
    inc ax
    add ax, cx
    mov p_y, ax
    cmp word ptr t_isp[di], 0
    je dm_item
    mov ax, t_mdx[si]
    mov p_x, ax
    mov ah, byte ptr t_za[bx]
    mov al, 0C3h
    call tui_putc_xy
    inc word ptr p_x
    mov ax, t_mdw[si]
    sub ax, 2
    mov p_w, ax
    mov ax, t_za[bx]
    mov p_a, ax
    mov al, 0C4h
    call tui_fill
    mov ax, t_mdx[si]
    add ax, t_mdw[si]
    dec ax
    mov p_x, ax
    mov ah, byte ptr t_za[bx]
    mov al, 0B4h
    call tui_putc_xy
    jmp dm_next
dm_item:
    mov ax, t_mdx[si]
    inc ax
    mov p_x, ax
    mov ax, t_mdw[si]
    sub ax, 2
    mov p_w, ax
    mov ax, t_ilp[di]
    mov p_s, ax
    mov ax, t_imp[di]
    mov p_m, ax
    mov ax, t_za[bx]
    mov p_a, ax
    mov ax, t_zb[bx]
    mov p_h, ax
    cmp cx, dm_it
    jne dm_draw
    mov ax, t_zl[bx]
    mov p_a, ax
    mov ax, t_zg[bx]
    mov p_h, ax
dm_draw:
    call tui_put
dm_next:
    inc cx
    jmp dm_1
dm_done:
    mov ax, 1
    call tui_mouse_show
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_draw_menu endp

; ---- AX = menu to open (F10 / Alt+letter / click): the menu loop
tui_menu proc
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    mov mn_m, ax
    mov cx, -1
    mov dx, 1
    call tui_step
    mov mn_it, ax
    mov word ptr mn_fire, 0
mn_loop:
    call tui_redraw
    mov ax, mn_m
    mov cx, mn_it
    call tui_draw_menu
mn_wait:
    call tui_get_event
    or ax, ax
    jz mn_wait1
    jmp mn_key
mn_wait1:
    or cx, cx
    jz mn_wait
    mov si, tui_cur
    shl si, 1
    mov bx, t_sb[si]
    shl bx, 1
    mov ax, tui_my
    cmp ax, t_zy[bx]
    jne mn_clbox
    mov cx, t_sm[si]
mn_clt:
    cmp cx, t_sl[si]
    jle mn_clt1
    jmp mn_close
mn_clt1:
    mov di, cx
    shl di, 1
    mov ax, tui_mx
    cmp ax, t_mtx[di]
    jl mn_clt2
    mov dx, t_mtx[di]
    add dx, t_mtl[di]
    cmp ax, dx
    jge mn_clt2
    mov ax, cx
    jmp mn_setm
mn_clt2:
    inc cx
    jmp mn_clt
mn_clbox:
    mov si, mn_m
    shl si, 1
    mov ax, tui_mx
    cmp ax, t_mdx[si]
    jg mn_cb1
    jmp mn_close
mn_cb1:
    mov dx, t_mdx[si]
    add dx, t_mdw[si]
    dec dx
    cmp ax, dx
    jl mn_cb2
    jmp mn_close
mn_cb2:
    mov ax, tui_my
    cmp ax, t_mdy[si]
    jg mn_cb3
    jmp mn_close
mn_cb3:
    mov dx, t_mdy[si]
    add dx, t_mdh[si]
    dec dx
    cmp ax, dx
    jl mn_cb4
    jmp mn_close
mn_cb4:
    sub ax, t_mdy[si]
    dec ax
    add ax, t_mi1[si]
    mov di, ax
    shl di, 1
    cmp word ptr t_isp[di], 0
    je mn_cb5
    jmp mn_wait
mn_cb5:
    mov mn_fire, ax
    jmp mn_close
mn_key:
    mov si, tui_cur
    shl si, 1
    cmp ax, 27
    jne mn_k0
    jmp mn_close
mn_k0:
    cmp ax, 324
    jne mn_k1
    jmp mn_close
mn_k1:
    cmp ax, 331
    jne mn_k2
    mov ax, mn_m
    dec ax
    cmp ax, t_sm[si]
    jge mn_setm
    mov ax, t_sl[si]
    jmp mn_setm
mn_k2:
    cmp ax, 333
    jne mn_k3
    mov ax, mn_m
    inc ax
    cmp ax, t_sl[si]
    jle mn_setm
    mov ax, t_sm[si]
mn_setm:
    mov mn_m, ax
    mov cx, -1
    mov dx, 1
    call tui_step
    mov mn_it, ax
    jmp mn_loop
mn_k3:
    cmp ax, 328
    jne mn_k4
    mov dx, -1
    jmp mn_move
mn_k4:
    cmp ax, 336
    jne mn_k5
    mov dx, 1
mn_move:
    mov ax, mn_m
    mov cx, mn_it
    call tui_step
    mov mn_it, ax
    jmp mn_loop
mn_k5:
    cmp ax, 13
    jne mn_k6
    mov ax, mn_it
    cmp ax, 0
    jge mn_en1
    jmp mn_wait
mn_en1:
    mov di, mn_m
    shl di, 1
    add ax, t_mi1[di]
    mov mn_fire, ax
    jmp mn_close
mn_k6:
    xor dx, dx
    cmp ax, 256
    jbe mn_k7
    call tui_alt_key
    mov dx, ax
    or dx, dx
    jnz mn_ak0
    jmp mn_wait
mn_ak0:
    mov cx, t_sm[si]
mn_ak:
    cmp cx, t_sl[si]
    jg mn_items
    mov di, cx
    shl di, 1
    cmp t_mky[di], dx
    jne mn_ak2
    mov ax, cx
    jmp mn_setm
mn_ak2:
    inc cx
    jmp mn_ak
mn_k7:
    cmp al, 'a'
    jb mn_k8
    cmp al, 'z'
    ja mn_k8
    sub al, 32
mn_k8:
    xor ah, ah
    mov dx, ax
mn_items:
    or dx, dx
    jnz mn_it0
    jmp mn_wait
mn_it0:
    mov si, mn_m
    shl si, 1
    xor cx, cx
mn_it1:
    cmp cx, t_mic[si]
    jl mn_it1b
    jmp mn_wait
mn_it1b:
    mov di, t_mi1[si]
    add di, cx
    shl di, 1
    cmp word ptr t_isp[di], 0
    jne mn_it2
    cmp t_iky[di], dx
    jne mn_it2
    mov ax, t_mi1[si]
    add ax, cx
    mov mn_fire, ax
    jmp mn_close
mn_it2:
    inc cx
    jmp mn_it1
mn_close:
    call tui_redraw
    mov bx, mn_fire
    or bx, bx
    jz mn_ret
    call tui_fire_menu
mn_ret:
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_menu endp

; ---- SI = text, DI = title: a message box with OK
tui_msgbox proc
    push ax
    push bx
    push cx
    push dx
    push si
    push di
    mov mb_t, di
    mov mb_s, si
    call tui_strlen
    mov ax, cx
    add ax, 4
    push si
    mov si, di
    call tui_strlen
    pop si
    mov mb_tl, cx
    mov dx, cx
    add dx, 6
    cmp dx, ax
    jle mb_1
    mov ax, dx
mb_1:
    cmp ax, 12
    jge mb_2
    mov ax, 12
mb_2:
    cmp ax, COLS
    jle mb_3
    mov ax, COLS
mb_3:
    mov mb_w, ax
    mov bx, COLS
    sub bx, ax
    shr bx, 1
    mov mb_x, bx
    mov bx, ROWS
    sub bx, 6
    shr bx, 1
    mov mb_y, bx
    xor ax, ax
    call tui_mouse_show
    mov ax, mb_x
    mov p_x, ax
    mov ax, mb_y
    mov p_y, ax
    mov ax, mb_w
    mov p_w, ax
    mov word ptr p_bh, 6
    mov word ptr p_a, 70h
    mov al, 1
    call tui_box
    xor ax, ax
    mov p_pad, ax
    mov p_pre, ax
    mov p_skip, ax
    mov p_pw, ax
    mov p_m, ax
    mov word ptr p_h, 70h
    mov cx, mb_tl
    or cx, cx
    jz mb_txt
    mov ax, mb_w
    sub ax, 6
    cmp cx, ax
    jle mb_t1
    mov cx, ax
mb_t1:
    mov ax, cx
    add ax, 2
    mov p_w, ax
    mov ax, mb_w
    sub ax, p_w
    shr ax, 1
    add ax, mb_x
    mov p_x, ax
    mov ax, mb_y
    mov p_y, ax
    mov word ptr p_pad, 1
    mov ax, mb_t
    mov p_s, ax
    call tui_put
    mov ax, p_x
    add ax, cx
    inc ax
    mov p_x, ax
    mov ax, 7020h
    call tui_putc_xy
    mov word ptr p_pad, 0
mb_txt:
    mov ax, mb_x
    add ax, 2
    mov p_x, ax
    mov ax, mb_y
    add ax, 2
    mov p_y, ax
    mov ax, mb_w
    sub ax, 4
    mov p_w, ax
    mov ax, mb_s
    mov p_s, ax
    call tui_put
    mov ax, mb_w
    sub ax, 6
    shr ax, 1
    add ax, mb_x
    mov p_x, ax
    mov ax, mb_y
    add ax, 4
    mov p_y, ax
    mov word ptr p_w, 6
    mov word ptr p_a, 2Fh
    mov word ptr p_h, 2Fh
    mov word ptr p_s, offset s_ok
    call tui_put
    mov ah, 01h
    mov cx, 2000h
    int 10h
    mov ax, 1
    call tui_mouse_show
mb_wait:
    call tui_get_event
    or cx, cx
    jnz mb_done
    cmp ax, 13
    je mb_done
    cmp ax, 27
    je mb_done
    cmp ax, 32
    jne mb_wait
mb_done:
    call tui_redraw
    pop di
    pop si
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_msgbox endp

; ---- BX = control, SI = 0-terminated text
tui_set_text proc
    push ax
    push cx
    push si
    push di
    push es
    mov di, bx
    shl di, 1
    mov word ptr t_hmp[di], 0
    mov di, t_txp[di]
    mov cx, TXLEN - 1
st_c1:
    lodsb
    or al, al
    jz st_c2
    mov [di], al
    inc di
    dec cx
    jnz st_c1
st_c2:
    mov byte ptr [di], 0
    mov di, bx
    shl di, 1
    mov ax, t_zs[di]
    cmp ax, tui_cur
    jne st_c3
    call tui_face
    call tui_cursor
st_c3:
    pop es
    pop di
    pop si
    pop cx
    pop ax
    ret
tui_set_text endp

; ---- BX = control -> SI = its text
tui_get_text proc
    push bx
    shl bx, 1
    mov si, t_txp[bx]
    pop bx
    ret
tui_get_text endp

; ---- BX = control -> AX = value
tui_get_value proc
    push bx
    shl bx, 1
    mov ax, t_zv[bx]
    pop bx
    ret
tui_get_value endp

; ---- BX = control, AX = value
tui_set_value proc
    push ax
    push cx
    push si
    push di
    mov si, bx
    shl si, 1
    cmp word ptr t_zt[si], 5
    jne sv_plain
    or ax, ax
    jz sv_plain
    mov cx, 1
sv_1:
    cmp cx, NC
    ja sv_2
    mov di, cx
    shl di, 1
    cmp word ptr t_zt[di], 5
    jne sv_n
    mov ax, t_zs[di]
    cmp ax, t_zs[si]
    jne sv_n
    mov ax, t_zr[di]
    cmp ax, t_zr[si]
    jne sv_n
    mov word ptr t_zv[di], 0
sv_n:
    inc cx
    jmp sv_1
sv_2:
    mov ax, 1
sv_plain:
    mov t_zv[si], ax
    mov ax, t_zs[si]
    cmp ax, tui_cur
    jne sv_ret
    call tui_redraw
sv_ret:
    pop di
    pop si
    pop cx
    pop ax
    ret
tui_set_value endp

; ---- BX = control, AX = 0 / 1 (CX = field: 0 visible, 1 enabled)
tui_set_flag proc
    push ax
    push si
    mov si, bx
    shl si, 1
    or cx, cx
    jnz sf_en
    mov t_zi[si], ax
    jmp sf_1
sf_en:
    mov t_zn[si], ax
sf_1:
    or ax, ax
    jnz sf_2
    cmp bx, tui_foc
    jne sf_2
    mov ax, 1
    call tui_next
    cmp bx, tui_foc
    jne sf_2
    mov word ptr tui_foc, 0
sf_2:
    mov ax, t_zs[si]
    cmp ax, tui_cur
    jne sf_ret
    call tui_redraw
sf_ret:
    pop si
    pop ax
    ret
tui_set_flag endp

tui_set_visible proc
    push cx
    xor cx, cx
    call tui_set_flag
    pop cx
    ret
tui_set_visible endp

tui_set_enabled proc
    push cx
    mov cx, 1
    call tui_set_flag
    pop cx
    ret
tui_set_enabled endp

tui_quit proc
    mov word ptr tui_run, 0
    ret
tui_quit endp

tui_do_dump proc
    push ax
    push bx
    push cx
    push dx
    xor ax, ax
    call tui_mouse_show
    mov ah, 3Ch
    xor cx, cx
    mov dx, offset s_dumpname
    int 21h
    jc dd_ret
    mov bx, ax
    push ds
    mov ax, 0B800h
    mov ds, ax
    xor dx, dx
    mov cx, COLS * ROWS * 2
    mov ah, 40h
    int 21h
    pop ds
    mov ah, 3Eh
    int 21h
dd_ret:
    pop dx
    pop cx
    pop bx
    pop ax
    ret
tui_do_dump endp

tui_main proc
@SPLASH@
    mov ax, 1
    call tui_show_screen
    cmp word ptr tui_dump, 0
    je ml_1
    call tui_do_dump
    mov word ptr tui_run, 0
ml_1:
    cmp word ptr tui_run, 0
    je ml_end
    call tui_get_event
    or ax, ax
    jz ml_2
    call tui_handle_key
ml_2:
    or cx, cx
    jz ml_1
    mov cx, tui_mx
    mov dx, tui_my
    call tui_click
    jmp ml_1
ml_end:
    xor ax, ax
    call tui_mouse_show
    ret
tui_main endp
"""

SPLASH = r"""    mov si, offset ts_0
    call tui_blit
    cmp word ptr tui_dump, 0
    jne sp_done
    mov cx, @TICKS@
    or cx, cx
    jnz sp_timed
    mov ah, 00h
    int 16h
    jmp sp_done
sp_timed:
    push es
    mov ax, 40h
    mov es, ax
    mov bx, es:[006Ch]
    pop es
sp_wait:
    mov ah, 01h
    int 16h
    jz sp_tick
    mov ah, 00h
    int 16h
    jmp sp_done
sp_tick:
    push es
    mov ax, 40h
    mov es, ax
    mov ax, es:[006Ch]
    pop es
    sub ax, bx
    cmp ax, cx
    jb sp_wait
sp_done:"""

START = r"""tui_start:
    mov bx, 80h
    mov cl, [bx]
    xor ch, ch
    mov si, 81h
cl_1:
    cmp cx, 1
    jl cl_3
    mov al, [si]
    cmp al, '/'
    jne cl_2
    mov al, [si+1]
    or al, 20h
    cmp al, 'd'
    jne cl_2
    mov word ptr tui_dump, 1
cl_2:
    inc si
    dec cx
    jmp cl_1
cl_3:
    mov ax, 0003h
    int 10h
@ROWSMODE@
    mov ah, 03h
    mov bh, 0
    int 10h
    mov tui_shape, cx
    mov ax, 0B800h
    mov es, ax
    cld
    mov ah, 01h
    mov cx, 2000h
    int 10h
    xor ax, ax
    int 33h
    cmp ax, 0FFFFh
    jne tui_nomouse
    mov word ptr tui_mouse, 1
    mov ax, 1
    int 33h
tui_nomouse:"""

EXIT = r"""    call tui_main
    mov ax, 0003h
    int 10h
    mov ax, 4C00h
    int 21h"""

ROWSMODE = {25: "", 43: "    mov ax, 1112h\n    mov bl, 0\n    int 10h",
            50: "    mov ax, 1112h\n    mov bl, 0\n    int 10h"}


def generate(screens, old_text: str = "", app: App | None = None, relax_jumps: bool = True) -> tuple[str, list[str]]:
    """(source of main.asm, warnings)."""
    app = app or build_app(screens)
    rg = Regions(old_text, CM)
    out: list[str] = []
    w = out.append
    w(f"; {app.screens[0].name} - DOS text-mode program generated by RAD IDE (Text-Mode Designer)")
    w("; Do not edit outside the USER CODE regions: the rest is rewritten when the screens change.")
    w("; Build: RAD IDE (F5, its own 8086 assembler -> main.com), or jwasm -bin -Fo=main.com main.asm,")
    w(";        or tasm main.asm + tlink /t main.obj")
    w("")
    w(".model tiny")
    w(".code")
    w("org 100h")
    w("")
    w("tui_entry:")
    w("    jmp tui_start")
    w("")
    w(f"COLS    equ {app.cols}")
    w(f"ROWS    equ {app.rows}")
    w(f"NC      equ {len(app.ctls)}")
    w(f"NM      equ {len(app.menus)}")
    w(f"TXLEN   equ {TXLEN}")
    for s in app.screens:
        w(f"{s.name:<8} equ {s.index}")
    for c in app.ctls:
        w(f"{c.name:<8} equ {c.index}")
    w("")
    w(rg.region("declarations", "; your variables (name db / dw ...) and constants (name equ ...)"))
    w("")
    w(";  ----- control tables (index 0 unused)")
    cs = app.ctls
    fields = [("t_zt", "code"), ("t_zs", "screen"), ("t_zx", "x"), ("t_zy", "y"), ("t_zw", "w"), ("t_zh", "h"),
              ("t_za", "a"), ("t_zb", "ha"), ("t_zf", "fa"), ("t_zg", "fha"), ("t_zl", "sa"), ("t_zv", "value"),
              ("t_zm", "max"), ("t_zo", "tab"), ("t_zk", "hotkey"), ("t_zr", "group"), ("t_ze", "events"),
              ("t_zi", "visible"), ("t_zn", "enabled"), ("t_zj", "flag"), ("t_z1", "first_item")]
    for label, attr_ in fields:
        out.extend(_words(label, [0] + [getattr(c, attr_) for c in cs]))
    out.extend(_words("t_zp", [0] * (len(cs) + 1)))
    out.extend(_words("t_z2", [0] + [len(c.items) for c in cs]))
    out.extend(_words("t_txp", [0] + [f"offset tx_{c.index}" for c in cs]))
    out.extend(_words("t_hmp", [0] + [f"offset hm_{c.index}" if "1" in c.mask else 0 for c in cs]))
    for c in cs:
        body = (lit(c.text[:TXLEN - 1]) + ", " if c.text else "")
        pad = TXLEN - 1 - len(c.text[:TXLEN - 1])
        w(f"tx_{c.index:<5} db {body}0" + (f", {pad} dup(0)" if pad > 0 else ""))
        if "1" in c.mask:
            w(f"hm_{c.index:<5} db '{c.mask}', 0")
    items = [(c.first_item + k, it) for c in cs for k, it in enumerate(c.items)]
    slots = max([0] + [i for i, _ in items])
    imap = dict(items)
    out.extend(_words("t_itp", [0] + [f"offset it_{i}" if i in imap else 0 for i in range(1, slots + 1)]))
    for i, it in items:
        w(f"it_{i:<5} db {lit(it) + ', ' if it else ''}0")
    w(";  ----- menus")
    ms = app.menus
    mf = [("t_msc", lambda m: m.screen), ("t_mtx", lambda m: m.title_x), ("t_mtl", lambda m: len(m.title)),
          ("t_mky", lambda m: m.hotkey), ("t_mdx", lambda m: m.box[0]), ("t_mdy", lambda m: m.box[1]),
          ("t_mdw", lambda m: m.box[2]), ("t_mdh", lambda m: m.box[3]), ("t_mi1", lambda m: m.first_item),
          ("t_mic", lambda m: m.count), ("t_mtsp", lambda m: f"offset mt_{m.index}"),
          ("t_mtmp", lambda m: f"offset mm_{m.index}")]
    for label, f in mf:
        out.extend(_words(label, [0] + [f(m) for m in ms]))
    for m in ms:
        w(f"mt_{m.index:<5} db {lit(m.title)}, 0")
        w(f"mm_{m.index:<5} db '{m.mask}', 0")
    its = app.items
    out.extend(_words("t_ilp", [0] + [f"offset il_{i.index}" if not i.sep else 0 for i in its]))
    out.extend(_words("t_imp", [0] + [f"offset im_{i.index}" if not i.sep else 0 for i in its]))
    out.extend(_words("t_isp", [0] + [1 if i.sep else 0 for i in its]))
    out.extend(_words("t_iky", [0] + [i.hotkey for i in its]))
    for i in its:
        if not i.sep:
            w(f"il_{i.index:<5} db {lit(i.line)}, 0")
            w(f"im_{i.index:<5} db '{i.mask}', 0")
    w(";  ----- screens")
    ss = app.screens
    for label, f in [("t_se", lambda s: s.esc_quits), ("t_sk", lambda s: s.cancel), ("t_sv", lambda s: s.events),
                     ("t_sb", lambda s: s.bar), ("t_sm", lambda s: s.menu_first), ("t_sl", lambda s: s.menu_last),
                     ("t_stp", lambda s: f"offset ts_{s.index}")]:
        out.extend(_words(label, [0] + [f(s) for s in ss]))
    sp = app.splash()
    if sp:
        _runs(w, "ts_0", sp.splash_runs)
    for s in ss:
        _runs(w, f"ts_{s.index}", s.runs)
    rt = RUNTIME.replace("@SPLASH@", SPLASH.replace("@TICKS@", str(sp.splash_seconds * 18)) if sp else "")
    out.append(rt)
    # dispatch
    w("; ---- BX = control, AX = event (1 Click, 2 Change, 3 KeyPress)")
    _dispatch(w, "tui_fire", [(h.target * 4 + {"Click": 1, "Change": 2, "KeyPress": 3}[h.event], h.key)
                              for h in app.ctl_handlers()], "mov cx, bx\n    shl cx, 1\n    shl cx, 1\n    add cx, ax")
    w("; ---- BX = menu item")
    _dispatch(w, "tui_fire_menu", [(h.target, h.key) for h in app.menu_handlers()], "mov cx, bx")
    w("; ---- BX = screen, AX = event (4 Load, 3 KeyPress)")
    _dispatch(w, "tui_fire_screen", [(h.target * 8 + (4 if h.event == "Load" else 3), h.key)
                                     for h in app.screen_handlers()],
              "mov cx, bx\n    shl cx, 1\n    shl cx, 1\n    shl cx, 1\n    add cx, ax")
    w("")
    w("; ===================================================================== event handlers")
    w(rg.region("general", "; your own procedures"))
    w("")
    for h in app.handlers:
        w(f"{h.key} proc")
        w(rg.region(h.key, ""))
        w("    ret")
        w(f"{h.key} endp")
        w("")
    w(rg.orphans("; "))
    w("")
    w(START.replace("@ROWSMODE@", ROWSMODE.get(app.rows, "")))
    w(rg.region("startup", "; code that runs before the first screen is shown"))
    w(EXIT)
    w("")
    w("end tui_entry")
    text = "\n".join(out).replace("\r", "") + "\n"
    if relax_jumps:
        text = relax(text)
    return text, list(app.warnings)


def _runs(w, label: str, runs) -> None:
    flat = [f"{n}, {c}, {a}" for n, c, a in runs]
    for i, ch in enumerate(chunks(flat, 12)):
        w(f"{label if i == 0 else '':<8} db {', '.join(ch)}")
    w("         db 0")


def _dispatch(w, name: str, cases: list[tuple[int, str]], key_code: str) -> None:
    w(f"{name} proc")
    regs = ["ax", "bx", "cx", "dx", "si", "di", "bp", "es"]
    for r in regs:
        w(f"    push {r}")
    if cases:
        w("    " + key_code)
        for k, (code, proc) in enumerate(cases):
            w(f"    cmp cx, {code}")
            w(f"    jne {name}_{k}")
            w(f"    call {proc}")
            w(f"    jmp {name}_x")
            w(f"{name}_{k}:")
    w(f"{name}_x:")
    for r in reversed(regs):
        w(f"    pop {r}")
    w("    ret")
    w(f"{name} endp")


_JCC = re.compile(r"^(\s*)(j[a-z]{1,4})\s+([A-Za-z_@?$][\w@?$]*)\s*$", re.I)


def relax(text: str, max_rounds: int = 30) -> str:
    """Rewrite the conditional jumps that are out of range (8086 jumps are short) as
    ``j<not cc> skip / jmp target / skip:`` - assembling with RAD IDE's 8086 assembler to find them."""
    try:
        from ....emu8086.assembler import assemble
    except ImportError:
        return text
    n = 0
    for _ in range(max_rounds):
        prog = assemble(text, "main.asm")
        bad = sorted({d.line for d in prog.errors if getattr(d, "code", "") == "E-JUMP-RANGE"}, reverse=True)
        if not bad:
            break
        lines = text.split("\n")
        for ln in bad:
            i = ln - 1
            if not (0 <= i < len(lines)):
                continue
            m = _JCC.match(lines[i])
            if not m or m.group(2).lower() not in INVERSE:
                continue
            n += 1
            ind, op, target = m.groups()
            lines[i:i + 1] = [f"{ind}{INVERSE[op.lower()]} tui_r{n}", f"{ind}jmp {target}", f"tui_r{n}:"]
        text = "\n".join(lines)
    return text


def handler_line(text: str, key: str) -> int:
    return line_of(text, rf"^{key}\s+proc\b")


def handler_name(key: str) -> str:
    return key
