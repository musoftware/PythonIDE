"""8086 Assembly (Emulator) - 16-bit DOS assembly the way university courses teach it (emu8086 / DOSBox + MASM /
TASM), run inside RAD IDE's own 8086 emulator (radide/emu8086): nothing to install.

* New Project > Assembly (or Other) > 8086 Assembly (Emulator): COM program, EXE program, emu8086.inc helpers,
  text-mode colours, keyboard game.
* F5 assembles the startup file (errors go to the Error List, in Arabic when the IDE is in Arabic) and opens
  the "8086 Emulator" dock paused at the first instruction: F10 / F11 / Shift+F11 step, breakpoints in the
  editor, registers with H/L halves, flags as check boxes, memory, stack, variables, listing, speed slider and
  Step Back (reverse debugging). Ctrl+F5 runs at full speed without stopping.
* ``python -m radide.emu8086 main.asm`` runs a program headless (tests, tutorials).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from ..model import Project
from .base import Completion, LanguagePlugin, RunSpec

DIRECTIVES = [".model", ".stack", ".data", ".code", ".startup", ".exit", "segment", "ends", "assume", "proc",
              "endp", "end", "org", "db", "dw", "dd", "dq", "dup", "equ", "macro", "endm", "local", "include",
              "offset", "seg", "ptr", "byte", "word", "dword", "near", "far", "short", "label", "even", "align",
              "rept", "tiny", "small", "medium", "compact", "large", "huge", "type", "length", "size", "low",
              "high", "mod", "shl", "shr", "and", "or", "xor", "not"]
INSTRUCTIONS = ["mov", "add", "adc", "sub", "sbb", "cmp", "inc", "dec", "neg", "mul", "imul", "div", "idiv",
                "and", "or", "xor", "not", "test", "shl", "sal", "shr", "sar", "rol", "ror", "rcl", "rcr",
                "push", "pop", "pushf", "popf", "pusha", "popa", "xchg", "lea", "lds", "les", "lahf", "sahf",
                "cbw", "cwd", "jmp", "call", "ret", "retf", "iret", "int", "into", "loop", "loope", "loopz",
                "loopne", "loopnz", "jcxz", "je", "jz", "jne", "jnz", "ja", "jnbe", "jae", "jnb", "jnc", "jb",
                "jnae", "jc", "jbe", "jna", "jg", "jnle", "jge", "jnl", "jl", "jnge", "jle", "jng", "jo", "jno",
                "js", "jns", "jp", "jpe", "jnp", "jpo", "movsb", "movsw", "cmpsb", "cmpsw", "scasb", "scasw",
                "lodsb", "lodsw", "stosb", "stosw", "rep", "repe", "repz", "repne", "repnz", "clc", "stc", "cmc",
                "cld", "std", "cli", "sti", "hlt", "nop", "in", "out", "xlat", "xlatb", "aaa", "aas", "aam",
                "aad", "daa", "das", "wait", "lock", "enter", "leave"]
REGISTERS = ["ax", "bx", "cx", "dx", "ah", "al", "bh", "bl", "ch", "cl", "dh", "dl", "si", "di", "bp", "sp",
             "cs", "ds", "es", "ss", "@data", "@code"]
MACROS = ["print", "printn", "putc", "gotoxy", "cursoroff", "cursoron", "define_print_num", "define_print_num_uns",
          "define_scan_num", "define_print_string", "define_get_string", "define_clear_screen", "define_pthis",
          "print_num", "print_num_uns", "scan_num", "print_string", "get_string", "clear_screen", "pthis"]

# Short descriptions written for RAD IDE (English, Arabic). Reference: the Intel 8086 Family User's Manual.
DOCS: dict[str, tuple[str, str]] = {
    "mov": ("mov dest, src - copy src into dest (flags unchanged). Not memory to memory; segment registers only "
            "from a register or memory.", "نسخ المصدر إلى الوجهة دون تغيير الأعلام. لا يجوز من ذاكرة إلى ذاكرة."),
    "add": ("add dest, src - dest = dest + src. Sets CF, ZF, SF, OF, AF, PF.", "جمع: الوجهة = الوجهة + المصدر."),
    "adc": ("adc dest, src - dest = dest + src + CF (add with carry, for numbers wider than 16 bits).",
            "جمع مع الحمل CF."),
    "sub": ("sub dest, src - dest = dest - src. CF = 1 when an unsigned borrow happened.",
            "طرح: الوجهة = الوجهة - المصدر."),
    "sbb": ("sbb dest, src - dest = dest - src - CF (subtract with borrow).", "طرح مع الاستلاف CF."),
    "cmp": ("cmp a, b - computes a - b only to set the flags (a is unchanged); follow it with a conditional jump.",
            "مقارنة: تحسب a - b لضبط الأعلام فقط، وتليها تعليمة قفز شرطي."),
    "inc": ("inc x - x = x + 1 (CF unchanged).", "زيادة بمقدار 1."),
    "dec": ("dec x - x = x - 1 (CF unchanged).", "إنقاص بمقدار 1."),
    "neg": ("neg x - x = 0 - x (two's complement).", "عكس الإشارة."),
    "mul": ("mul src - unsigned: byte: AX = AL * src; word: DX:AX = AX * src.",
            "ضرب بدون إشارة: بايت AX = AL * المصدر، كلمة DX:AX = AX * المصدر."),
    "imul": ("imul src - signed multiply, like mul.", "ضرب بإشارة."),
    "div": ("div src - unsigned: byte: AL = AX / src, AH = remainder; word: AX = DX:AX / src, DX = remainder. "
            "Clear DX (xor dx, dx) before a word division!", "قسمة بدون إشارة. صفّر DX قبل قسمة الكلمة!"),
    "idiv": ("idiv src - signed divide, like div (use cbw / cwd to extend the sign first).",
             "قسمة بإشارة (استخدم cbw أو cwd أولاً)."),
    "and": ("and dest, src - bitwise AND (clears bits). CF = OF = 0.", "عملية AND على البتات."),
    "or": ("or dest, src - bitwise OR (sets bits).", "عملية OR على البتات."),
    "xor": ("xor dest, src - bitwise XOR; xor ax, ax sets AX to 0.", "عملية XOR؛ xor ax, ax تصفّر AX."),
    "not": ("not x - inverts every bit (flags unchanged).", "عكس كل البتات."),
    "test": ("test a, b - AND only for the flags (e.g. test al, 1 / jz even).", "AND لضبط الأعلام فقط."),
    "shl": ("shl x, count - shift left (multiply by 2 per bit); the last bit out goes to CF.",
            "إزاحة لليسار (ضرب في 2)."),
    "sal": ("sal x, count - same as shl.", "مثل shl."),
    "shr": ("shr x, count - logical shift right (unsigned divide by 2).", "إزاحة منطقية لليمين (قسمة على 2)."),
    "sar": ("sar x, count - arithmetic shift right (keeps the sign).", "إزاحة حسابية لليمين تحافظ على الإشارة."),
    "rol": ("rol x, count - rotate left.", "تدوير لليسار."),
    "ror": ("ror x, count - rotate right.", "تدوير لليمين."),
    "rcl": ("rcl x, count - rotate left through CF.", "تدوير لليسار عبر CF."),
    "rcr": ("rcr x, count - rotate right through CF.", "تدوير لليمين عبر CF."),
    "push": ("push src - SP = SP - 2, then store the word at SS:SP.", "دفع كلمة إلى المكدس."),
    "pop": ("pop dest - load the word at SS:SP, then SP = SP + 2.", "سحب كلمة من المكدس."),
    "xchg": ("xchg a, b - swap the two operands.", "تبديل قيمتي المعاملين."),
    "lea": ("lea reg, mem - load the address (offset) of mem, not its value.",
            "تحميل عنوان (إزاحة) الذاكرة وليس قيمتها."),
    "jmp": ("jmp label - jump always.", "قفز غير مشروط."),
    "call": ("call proc - push the return address and jump to the procedure.", "استدعاء إجراء."),
    "ret": ("ret - return from a procedure (pops the return address).", "رجوع من الإجراء."),
    "int": ("int n - call interrupt n. int 21h = DOS (AH = function), int 10h = video BIOS, int 16h = keyboard.",
            "استدعاء مقاطعة: 21h لنظام DOS و 10h للشاشة و 16h للوحة المفاتيح."),
    "loop": ("loop label - CX = CX - 1; jump when CX is not 0.", "إنقاص CX والقفز إن لم يصبح صفراً."),
    "je": ("je / jz label - jump when equal (ZF = 1).", "قفز عند التساوي."),
    "jne": ("jne / jnz label - jump when not equal (ZF = 0).", "قفز عند عدم التساوي."),
    "ja": ("ja label - jump when above (unsigned >).", "قفز عند الأكبر (بدون إشارة)."),
    "jb": ("jb label - jump when below (unsigned <, CF = 1).", "قفز عند الأصغر (بدون إشارة)."),
    "jg": ("jg label - jump when greater (signed >).", "قفز عند الأكبر (بإشارة)."),
    "jl": ("jl label - jump when less (signed <).", "قفز عند الأصغر (بإشارة)."),
    "jge": ("jge label - jump when greater or equal (signed).", "قفز عند الأكبر أو المساوي (بإشارة)."),
    "jle": ("jle label - jump when less or equal (signed).", "قفز عند الأصغر أو المساوي (بإشارة)."),
    "jae": ("jae label - jump when above or equal (unsigned, CF = 0).", "قفز عند الأكبر أو المساوي (بدون إشارة)."),
    "jbe": ("jbe label - jump when below or equal (unsigned).", "قفز عند الأصغر أو المساوي (بدون إشارة)."),
    "jcxz": ("jcxz label - jump when CX = 0.", "قفز إذا كان CX = 0."),
    "movsb": ("movsb - copy the byte DS:[SI] to ES:[DI], then SI and DI move by 1 (rep movsb copies CX bytes).",
              "نسخ بايت من DS:[SI] إلى ES:[DI]."),
    "stosb": ("stosb - store AL at ES:[DI]; DI moves by 1.", "تخزين AL في ES:[DI]."),
    "lodsb": ("lodsb - load the byte DS:[SI] into AL; SI moves by 1.", "تحميل بايت من DS:[SI] إلى AL."),
    "cmpsb": ("cmpsb - compare DS:[SI] with ES:[DI] (repe cmpsb compares strings).", "مقارنة سلسلتين."),
    "scasb": ("scasb - compare AL with ES:[DI] (repne scasb searches).", "البحث عن AL في سلسلة."),
    "cld": ("cld - DF = 0: string instructions move forward.", "اتجاه السلاسل للأمام."),
    "std": ("std - DF = 1: string instructions move backward.", "اتجاه السلاسل للخلف."),
    "cbw": ("cbw - sign-extend AL into AX.", "توسيع إشارة AL إلى AX."),
    "cwd": ("cwd - sign-extend AX into DX:AX.", "توسيع إشارة AX إلى DX:AX."),
    "hlt": ("hlt - stop the CPU.", "إيقاف المعالج."),
    "nop": ("nop - do nothing.", "لا عملية."),
    "db": ("name db values - define bytes: numbers, 'text', ? (uninitialised), n dup(x).",
           "تعريف بايتات: أرقام أو نص أو ? أو dup."),
    "dw": ("name dw values - define 16-bit words.", "تعريف كلمات 16 بت."),
    "dup": ("n dup(value) - repeat value n times: buf db 20 dup('$').", "تكرار القيمة n مرة."),
    "offset": ("offset name - the address of a variable (mov dx, offset msg).", "عنوان المتغير."),
    "equ": ("name equ value - a constant (no memory is used).", "تعريف ثابت."),
    "proc": ("name proc ... ret ... name endp - a procedure.", "تعريف إجراء."),
    "org": ("org 100h - COM programs start at offset 100h (after the PSP).", "برامج COM تبدأ من 100h."),
    ".model": (".model small - code and data in separate 64 KB segments (EXE). Start with "
               "mov ax, @data / mov ds, ax.", "نموذج الذاكرة؛ ابدأ بـ mov ax, @data ثم mov ds, ax."),
    "ax": ("AX - accumulator (AH high byte, AL low byte). mul / div / in / out use it.", "المركم AX (AH و AL)."),
    "bx": ("BX - base register, can address memory: [bx].", "مسجل الأساس، يستخدم في العنونة."),
    "cx": ("CX - counter: loop, rep and shifts by CL use it.", "مسجل العد للحلقات."),
    "dx": ("DX - data register: high word of mul / div, I/O port, DOS string address.", "مسجل البيانات."),
    "si": ("SI - source index for string instructions and [si] addressing.", "مؤشر المصدر."),
    "di": ("DI - destination index for string instructions and [di] addressing.", "مؤشر الوجهة."),
    "bp": ("BP - base pointer: [bp+n] reads parameters / locals on the stack (segment SS).",
           "مؤشر القاعدة للوصول إلى المكدس."),
    "sp": ("SP - stack pointer (top of the stack in SS).", "مؤشر قمة المكدس."),
}

DOS_FUNCS = {0x01: "read a key with echo -> AL", 0x02: "print the character in DL",
             0x06: "direct console I/O (DL=FFh: read without waiting)", 0x07: "read a key without echo -> AL",
             0x08: "read a key without echo -> AL", 0x09: "print the $-terminated string at DS:DX",
             0x0A: "read a line into the buffer at DS:DX ([max][count][chars])", 0x2C: "get the time",
             0x2A: "get the date", 0x4C: "exit to DOS with code AL"}

TEMPLATES = [
    ("asm86_com", "COM Program (org 100h)", "A tiny .COM program: code and data in one segment, starts at 100h. "
     "Prints a message with INT 21h.", "SP_ComputerIcon"),
    ("asm86_exe", "EXE Program (.model small)", "A .EXE program with .data / .code / .stack segments: reads a "
     "digit and prints the sum of an array.", "SP_DriveHDIcon"),
    ("asm86_inc", "Using emu8086.inc", "PRINT / PRINTN / GOTOXY macros and the SCAN_NUM / PRINT_NUM procedures of "
     "the built-in helper library.", "SP_FileDialogContentsView"),
    ("asm86_colors", "Text-Mode Colours", "Writes coloured text straight into the video memory at B800:0000 "
     "and with INT 10h.", "SP_DesktopIcon"),
    ("asm86_game", "Keyboard Game", "Move a character with the arrow keys (INT 16h), Esc quits.",
     "SP_MediaPlay"),
]

COM_MAIN = """; {name} - an 8086 COM program (RAD IDE 8086 emulator)
; F5: debug (F10 / F11 step, watch the registers), Ctrl+F5: run

org 100h

start:
    mov ah, 09h             ; DOS: print the string at DS:DX
    mov dx, offset msg
    int 21h

    mov ah, 4Ch             ; DOS: exit with code AL
    mov al, 0
    int 21h

msg db 'Hello from {name}!', 13, 10, '$'
"""

EXE_MAIN = """; {name} - an 8086 EXE program (.model small)
.model small
.stack 100h

.data
numbers dw 12, 7, 30, 1, 50
count   equ 5
prompt  db 'Press a digit (0-9): $'
answer  db 13, 10, 'Sum of the array + your digit = $'

.code
main proc
    mov ax, @data           ; DS must point to the data segment
    mov ds, ax

    mov ah, 09h
    lea dx, prompt
    int 21h
    mov ah, 01h             ; read a key -> AL (with echo)
    int 21h
    sub al, '0'
    mov ah, 0
    mov bx, ax              ; BX = the digit

    mov cx, count
    lea si, numbers
add_next:
    add bx, [si]
    add si, 2
    loop add_next

    mov ah, 09h
    lea dx, answer
    int 21h
    mov ax, bx
    call print_number

    mov ax, 4C00h
    int 21h
main endp

; print AX as an unsigned decimal number
print_number proc
    mov bx, 10
    xor cx, cx
divide:
    xor dx, dx
    div bx                  ; AX = AX / 10, DX = digit
    push dx
    inc cx
    or ax, ax
    jnz divide
show:
    pop dx
    add dl, '0'
    mov ah, 02h
    int 21h
    loop show
    ret
print_number endp

end main
"""

INC_MAIN = """; {name} - using the emu8086.inc helper library
include 'emu8086.inc'

org 100h

    PRINTN 'Enter a number:'
    CALL SCAN_NUM           ; CX = the number typed
    MOV AX, CX
    ADD AX, AX
    PRINT 'Twice your number is '
    CALL PRINT_NUM          ; print AX
    GOTOXY 10, 5
    PRINT 'Bye!'
    RET

DEFINE_SCAN_NUM
DEFINE_PRINT_NUM
DEFINE_PRINT_NUM_UNS

END
"""

COLORS_MAIN = """; {name} - text-mode colours: video memory at B800:0000 (character, attribute)
org 100h

    mov ax, 0003h           ; 80x25 colour text mode (clears the screen)
    int 10h
    mov ax, 0B800h
    mov es, ax
    mov di, (2 * 80 + 10) * 2   ; row 2, column 10
    mov si, offset title_
    mov ah, 1Eh             ; yellow on blue
next_char:
    lodsb
    cmp al, 0
    je bars
    stosw                   ; AL = character, AH = attribute
    jmp next_char

bars:                       ; 16 coloured blocks on row 5
    mov di, (5 * 80 + 10) * 2
    mov cx, 16
    mov ah, 0
bar:
    mov al, 0DBh            ; full block
    stosw
    stosw
    inc ah
    loop bar

    mov ah, 02h             ; cursor to row 8
    mov bh, 0
    mov dx, 0800h
    int 10h
    mov ax, 4C00h
    int 21h

title_ db 'Colours in 8086 text mode', 0
"""

GAME_MAIN = """; {name} - move the smiley with the arrow keys, Esc quits
org 100h

    mov ax, 0003h
    int 10h
    mov ah, 01h             ; hide the cursor
    mov cx, 2000h
    int 10h
    mov dh, 12              ; row
    mov dl, 40              ; column
draw:
    call put_smiley
wait_key:
    mov ah, 00h             ; wait for a key: AH = scan code, AL = ASCII
    int 16h
    cmp al, 27              ; Esc
    je quit
    push ax
    mov al, ' '             ; erase the old position
    call put_char
    pop ax
    cmp ah, 48h
    je up
    cmp ah, 50h
    je down
    cmp ah, 4Bh
    je left
    cmp ah, 4Dh
    je right
    jmp draw
up:    cmp dh, 0
       je draw
       dec dh
       jmp draw
down:  cmp dh, 24
       je draw
       inc dh
       jmp draw
left:  cmp dl, 0
       je draw
       dec dl
       jmp draw
right: cmp dl, 79
       je draw
       inc dl
       jmp draw
quit:
    mov ax, 4C00h
    int 21h

put_smiley:
    mov al, 1               ; smiley character
put_char:                   ; AL at row DH, column DL (yellow)
    push ax
    mov ah, 02h
    mov bh, 0
    int 10h
    pop ax
    mov ah, 09h
    mov bl, 0Eh
    mov cx, 1
    int 10h
    ret
"""

SOURCES = {"asm86_com": COM_MAIN, "asm86_exe": EXE_MAIN, "asm86_inc": INC_MAIN, "asm86_colors": COLORS_MAIN,
           "asm86_game": GAME_MAIN}


class Emu8086Plugin(LanguagePlugin):
    id = "emu8086"
    display_name = "8086 Assembly (Emulator)"
    code_ext = ".asm"
    case_sensitive = False
    line_comments = [";"]
    block_comment = None
    string_quotes = ["'", '"']
    keywords = sorted(set(INSTRUCTIONS) | set(DIRECTIVES))
    builtins = REGISTERS + MACROS
    supports_debug = True
    has_forms = False
    project_name_base = "Asm8086_"
    install_hint = "Nothing to install: RAD IDE runs 8086 programs in its own emulator."

    # ------------------------------------------------------------ New Project
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return list(TEMPLATES)

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        src = SOURCES.get(template or "asm86_com", COM_MAIN)
        main = folder / "main.asm"
        if not main.exists():
            main.write_text(src.format(name=name), encoding="utf-8")
        project = Project(folder, name, self.id, [], "main", ["main.asm"])
        project.save()
        return project

    # ------------------------------------------------------------ code files
    def code_file(self, form_name: str) -> str:
        return form_name if form_name.lower().endswith(".asm") else f"{form_name}.asm"

    def designer_file(self, form_name: str) -> str:
        return self.code_file(form_name)

    def generate_designer(self, form, user_code: str) -> str:
        return user_code

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def module_template(self, name: str) -> str:
        return (f"; {name}.asm - include it from main.asm with:  include '{name}.asm'\n"
                f"; (procedures here are assembled where the include line is)\n")

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*{re.escape(name)}\s+proc\b", re.I)

    def add_handler(self, code: str, name: str, form, args=None):
        text = code.rstrip() + f"\n\n{name} proc\n    ret\n{name} endp\n"
        return text, len(text.splitlines()) - 2

    # ------------------------------------------------------------ run / debug
    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable or "python"

    def _startup_file(self, folder: Path, startup: str) -> str:
        folder = Path(folder)
        s = (startup or "main").replace("\\", "/")
        name = s if s.lower().endswith(".asm") else s + ".asm"
        if not (folder / name).exists():
            cands = sorted(folder.glob("*.asm"))
            if (folder / "main.asm").exists():
                return "main.asm"
            if cands:
                return cands[0].name
        return name

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        f = self._startup_file(folder, startup_form)
        return RunSpec(sys.executable, ["-m", "radide.emu8086", f], Path(folder))

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        spec = self.run_spec(folder, startup_form, interpreter)
        spec.breakpoints = list(breakpoints or [])
        return spec

    def make_session(self, win, spec, debug: bool):
        """MainWindow._make_session hook: the program runs in the in-process emulator."""
        project = getattr(win, "project", None)
        if project is None or project.language != self.id:
            return None
        from ..emu8086.ui import Emu8086Session
        folder = Path(project.folder)
        startup = self._startup_file(folder, project.startup)
        bps = getattr(spec, "breakpoints", None)
        if bps is None:
            try:
                bps = win._all_breakpoints()
            except Exception:  # noqa: BLE001
                bps = []
        return Emu8086Session(win, folder, startup, debug, bps)

    # ------------------------------------------------------------ IntelliSense
    @staticmethod
    def _symbols(code: str) -> list[tuple[str, str, int, str]]:
        """(name, kind, 0-based line, detail) of labels, procedures, variables, constants and macros."""
        out = []
        for i, raw in enumerate(code.splitlines()):
            line = raw.split(";", 1)[0]
            m = re.match(r"\s*([A-Za-z_@?$][\w@?$]*)\s*:", line)
            if m and m.group(1).lower() not in REGISTERS:
                out.append((m.group(1), "label", i, "label"))
                continue
            m = re.match(r"\s*([A-Za-z_@?$][\w@?$]*)\s+(proc|db|dw|dd|dq|equ|macro|segment|label)\b(.*)", line, re.I)
            if m:
                kind = m.group(2).lower()
                detail = (m.group(2) + " " + m.group(3).strip())[:60]
                out.append((m.group(1), {"proc": "function", "macro": "function", "segment": "module",
                                         "equ": "constant"}.get(kind, "variable"), i, detail))
        return out

    def completions(self, code, line, col, path, names=None):
        out = [Completion(k, "keyword", DOCS.get(k, ("", ""))[0][:60]) for k in INSTRUCTIONS]
        out += [Completion(d, "keyword") for d in DIRECTIVES if d not in INSTRUCTIONS]
        out += [Completion(r, "variable", "register") for r in REGISTERS]
        out += [Completion(m.upper(), "function", "emu8086.inc") for m in MACROS]
        seen = {c.name.lower() for c in out}
        for name, kind, _i, detail in self._symbols(code):
            if name.lower() not in seen:
                seen.add(name.lower())
                out.append(Completion(name, kind, detail))
        return out

    def hover(self, code, line, col, path, names=None) -> str:
        lines = code.splitlines()
        if line >= len(lines):
            return ""
        text = lines[line]
        m = None
        for mm in re.finditer(r"[A-Za-z0-9_@?$.][\w@?$]*", text):
            if mm.start() <= col <= mm.end():
                m = mm
                break
        if m is None:
            return ""
        word = m.group(0).lower()
        from ..emu8086.messages import ui_language
        ar = ui_language() == "ar"
        if word in DOCS:
            en, arabic = DOCS[word]
            return f"**{word}**  \n{en}" + (f"  \n{arabic}" if ar else "")
        alias = {"jz": "je", "jnz": "jne", "jc": "jb", "jnc": "jae", "jnb": "jae", "jnae": "jb", "jna": "jbe",
                 "jnbe": "ja", "jnl": "jge", "jnge": "jl", "jng": "jle", "jnle": "jg", "loopz": "loop",
                 "movsw": "movsb", "stosw": "stosb", "lodsw": "lodsb", "cmpsw": "cmpsb", "scasw": "scasb",
                 "retf": "ret", "dd": "dw"}
        if word in alias:
            en, arabic = DOCS[alias[word]]
            return f"**{word}** (see {alias[word]})  \n{en}" + (f"  \n{arabic}" if ar else "")
        if word == "21h":
            rows = "  \n".join(f"AH={k:02X}h: {v}" for k, v in sorted(DOS_FUNCS.items()))
            return "**INT 21h** - DOS services (function number in AH)  \n" + rows
        for name, kind, i, detail in self._symbols(code):
            if name.lower() == word:
                return f"**{name}** ({kind}, line {i + 1})  \n`{lines[i].strip()}`"
        return ""

    def definition(self, code, line, col, path, names=None):
        lines = code.splitlines()
        if line >= len(lines):
            return None
        word = ""
        for mm in re.finditer(r"[A-Za-z_@?$][\w@?$]*", lines[line]):
            if mm.start() <= col <= mm.end():
                word = mm.group(0).lower()
        for name, _kind, i, _d in self._symbols(code):
            if name.lower() == word:
                return (str(path), i)
        return None

    def document_symbols(self, code: str) -> list[dict]:
        return [{"name": name, "kind": kind, "line": i, "detail": detail, "children": []}
                for name, kind, i, detail in self._symbols(code)]


PLUGIN = Emu8086Plugin()
