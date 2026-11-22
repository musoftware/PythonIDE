# (c) 2026 Musoftware - https://musoftwares.com - MIT License
#
# GasGuessNumber - Form1 event handlers (GNU as, x64 Windows, Intel syntax, GUI Bridge).
# A guess-the-number game: Form1_Load / New game pick a secret number 1..100 from the CPU's time-stamp counter
# (RDTSC, then DIV by 100), Guess compares the typed number with it, shows "too high" / "too low" / "correct",
# counts the tries and keeps a ListBox of the guesses (sprintf + ListBox.AddItem). A number outside 1..100 gets a
# MsgBox. When the game is won the Guess button is disabled (rad_set_int ... Enabled, 0) until New game.
#
# GNU as removes the quotes of macro arguments: control and property names are written as words; a string of
# our own is passed in a register (lea rbx, [rip + buf]). Inside a handler RBX, RSI, RDI and R12 are ours.
        .intel_syntax noprefix
        .include "radgui_intel.inc"
        .include "Form1.inc"           # generated: the control IDs of Form1

        .data
        .p2align 3
secret: .quad 0                         # the number to guess
tries:  .quad 0
won:    .quad 0
fmt_hi: .asciz "%lld - too high"
fmt_lo: .asciz "%lld - too low"
fmt_ok: .asciz "%lld - correct!"
fmt_win: .asciz "Correct! You found %lld in %lld tries."
        .bss
buf:    .space 96

        .text
# new_secret: secret = (time-stamp counter mod 100) + 1, tries = 0, won = 0
new_secret:
        rdtsc                           # EDX:EAX = cycles since reset
        shl     rdx, 32
        or      rax, rdx
        xor     edx, edx
        mov     ecx, 100
        div     rcx                     # RDX = cycles mod 100
        inc     rdx
        mov     QWORD PTR [rip + secret], rdx
        mov     QWORD PTR [rip + tries], 0
        mov     QWORD PTR [rip + won], 0
        ret

# start_game: a new secret number and a clean form
start_game:
        sub     rsp, 8                  # keep RSP aligned (the macros align anyway)
        call    new_secret
        rad_set lblHint, Text, "Type a guess from 1 to 100."
        rad_set_int lblTries, Text, 0
        rad_call lstGuesses, Clear, ""
        rad_set txtGuess, Text, ""
        rad_set_int btnGuess, Enabled, 1
        add     rsp, 8
        ret

handler Form1_Load
        call    start_game
endhandler

handler btnNew_Click
        call    start_game
endhandler

handler btnGuess_Click
        cmp     QWORD PTR [rip + won], 0
        jne     guess_done
        rad_get_int txtGuess, Text      # RAX = the guess
        mov     rsi, rax
        cmp     rsi, 1
        jl      guess_range
        cmp     rsi, 100
        jg      guess_range
        inc     QWORD PTR [rip + tries]
        rad_set_int lblTries, Text, QWORD PTR [rip + tries]
        lea     rcx, [rip + buf]        # sprintf(buf, fmt, guess) - the format depends on the comparison
        mov     r8, rsi
        cmp     rsi, QWORD PTR [rip + secret]
        jg      guess_high
        jl      guess_low
        lea     rdx, [rip + fmt_ok]
        call    sprintf
        lea     rbx, [rip + buf]
        rad_call lstGuesses, AddItem, rbx
        mov     QWORD PTR [rip + won], 1
        lea     rcx, [rip + buf]
        lea     rdx, [rip + fmt_win]
        mov     r8, rsi
        mov     r9, QWORD PTR [rip + tries]
        call    sprintf
        lea     rbx, [rip + buf]
        rad_set lblHint, Text, rbx
        rad_set_int btnGuess, Enabled, 0
        jmp     guess_done
guess_high:
        lea     rdx, [rip + fmt_hi]
        call    sprintf
        rad_set lblHint, Text, "Too high - try a smaller number."
        jmp     guess_add
guess_low:
        lea     rdx, [rip + fmt_lo]
        call    sprintf
        rad_set lblHint, Text, "Too low - try a bigger number."
guess_add:
        lea     rbx, [rip + buf]
        rad_call lstGuesses, AddItem, rbx
        rad_set txtGuess, Text, ""
        jmp     guess_done
guess_range:
        rad_msgbox "Please type a whole number from 1 to 100."
guess_done:
endhandler
