"""IntelliSense reference of the DOS projects (no Qt in here). All descriptions were written for RAD IDE.

    INTERRUPTS[0x21].functions[0x09] -> IntFunc("Print string", "DS:DX = string ending in '$'", "-", en, ar)
    QBASIC["LOCATE"] -> ("LOCATE [row][, col][, cursor]", "Moves the text cursor ...")
    PASCAL["GotoXY"] -> ("procedure GotoXY(X, Y: Byte)", "Crt", "...")
    C_FUNCS["gotoxy"] -> ("void gotoxy(int x, int y)", "tcconio.h", "...")
    BATCH["CHOICE"] -> ("CHOICE [/C:keys] [text]", "...")
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class IntFunc:
    name: str
    inputs: str
    outputs: str
    en: str
    ar: str = ""


@dataclass(frozen=True)
class Interrupt:
    number: int
    title: str
    ar: str
    selector: str                         # register holding the function number: "AH" or "AX"
    functions: dict = field(default_factory=dict)


def _f(name, i, o, en, ar=""):
    return IntFunc(name, i, o, en, ar)


INT21 = Interrupt(0x21, "DOS services", "خدمات نظام DOS", "AH", {
    0x00: _f("Terminate program", "CS = PSP segment", "-", "Old way to end a .COM program; use AH=4Ch.",
             "إنهاء البرنامج (الطريقة القديمة)."),
    0x01: _f("Read key with echo", "-", "AL = character", "Waits for a key and shows it. Extended keys give 0 "
             "first, then the scan code on the next call. Ctrl+C breaks.", "ينتظر مفتاحاً ويعرضه."),
    0x02: _f("Print character", "DL = character", "-", "Writes one character to standard output (redirectable).",
             "يطبع حرفاً واحداً."),
    0x05: _f("Print to printer", "DL = character", "-", "Sends a character to PRN.", "يرسل حرفاً إلى الطابعة."),
    0x06: _f("Direct console I/O", "DL = character, or DL = FFh to read", "ZF = 0 and AL = key when a key was "
             "waiting", "Reads without waiting (DL = FFh) or writes DL; no Ctrl+C check.",
             "قراءة دون انتظار أو كتابة مباشرة."),
    0x07: _f("Read key, no echo, no Ctrl+C", "-", "AL = character", "Waits for a key without showing it.",
             "ينتظر مفتاحاً دون عرضه."),
    0x08: _f("Read key, no echo", "-", "AL = character", "Waits for a key without showing it (Ctrl+C breaks).",
             "ينتظر مفتاحاً دون عرضه."),
    0x09: _f("Print string", "DS:DX = string ending in '$'", "-", "Writes characters up to (not including) the "
             "first '$'. Use 13, 10 for a new line.", "يطبع النص حتى علامة $."),
    0x0A: _f("Read line (buffered)", "DS:DX = buffer: [max][count][chars...]", "buffer filled, count = length",
             "Reads a line with editing keys; the first byte is the buffer size, DOS stores the length in the "
             "second and a CR after the text.", "يقرأ سطراً في مخزن مؤقت."),
    0x0B: _f("Key waiting?", "-", "AL = FFh when a key is waiting, else 0", "Checks the keyboard without waiting.",
             "هل يوجد مفتاح بانتظار القراءة؟"),
    0x0C: _f("Flush keyboard, then read", "AL = 01h/06h/07h/08h/0Ah function to call", "as that function",
             "Empties the keyboard buffer first.", "يفرغ مخزن لوحة المفاتيح ثم يقرأ."),
    0x0E: _f("Select drive", "DL = drive (0 = A:)", "AL = number of drives", "Makes DL the current drive.",
             "يختار القرص الحالي."),
    0x19: _f("Current drive", "-", "AL = drive (0 = A:)", "Returns the current drive.", "القرص الحالي."),
    0x1A: _f("Set DTA", "DS:DX = disk transfer area", "-", "Buffer used by find first / next (4Eh / 4Fh).",
             "يحدد منطقة نقل البيانات."),
    0x25: _f("Set interrupt vector", "AL = interrupt, DS:DX = new handler", "-", "Installs an interrupt handler "
             "(save the old one with 35h first).", "يضبط عنوان معالج المقاطعة."),
    0x2A: _f("Get date", "-", "CX = year, DH = month, DL = day, AL = weekday (0 = Sunday)", "Reads the system date.",
             "يقرأ التاريخ."),
    0x2C: _f("Get time", "-", "CH = hour, CL = minute, DH = second, DL = 1/100 s", "Reads the system time.",
             "يقرأ الوقت."),
    0x30: _f("DOS version", "AL = 0", "AL = major, AH = minor", "Returns the DOS version number.",
             "رقم إصدار DOS."),
    0x31: _f("Terminate and stay resident", "AL = exit code, DX = paragraphs to keep", "-", "Ends the program but "
             "keeps DX * 16 bytes in memory (TSR).", "إنهاء مع البقاء في الذاكرة."),
    0x35: _f("Get interrupt vector", "AL = interrupt", "ES:BX = current handler", "Reads an interrupt vector.",
             "يقرأ عنوان معالج المقاطعة."),
    0x39: _f("Make directory", "DS:DX = ASCIIZ path", "CF = 1 on error, AX = error", "Creates a directory.",
             "ينشئ مجلداً."),
    0x3A: _f("Remove directory", "DS:DX = ASCIIZ path", "CF = 1 on error", "Removes an empty directory.",
             "يحذف مجلداً فارغاً."),
    0x3B: _f("Change directory", "DS:DX = ASCIIZ path", "CF = 1 on error", "Changes the current directory.",
             "يغير المجلد الحالي."),
    0x3C: _f("Create file", "DS:DX = ASCIIZ name, CX = attributes (0 = normal)", "AX = handle, CF = 1 on error",
             "Creates (or truncates) a file and opens it for writing.", "ينشئ ملفاً."),
    0x3D: _f("Open file", "DS:DX = ASCIIZ name, AL = mode (0 read, 1 write, 2 both)", "AX = handle, CF on error",
             "Opens an existing file.", "يفتح ملفاً."),
    0x3E: _f("Close file", "BX = handle", "CF = 1 on error", "Closes a file handle.", "يغلق الملف."),
    0x3F: _f("Read file / device", "BX = handle, CX = bytes, DS:DX = buffer", "AX = bytes read, CF on error",
             "Reads from a file; handle 0 is the keyboard (standard input).", "يقرأ من ملف."),
    0x40: _f("Write file / device", "BX = handle, CX = bytes, DS:DX = data", "AX = bytes written, CF on error",
             "Writes to a file; handle 1 = standard output, 2 = standard error, 4 = printer.", "يكتب إلى ملف."),
    0x41: _f("Delete file", "DS:DX = ASCIIZ name", "CF = 1 on error", "Deletes a file.", "يحذف ملفاً."),
    0x42: _f("Seek", "BX = handle, AL = origin (0 start, 1 current, 2 end), CX:DX = offset", "DX:AX = new position",
             "Moves the file pointer.", "يحرك مؤشر الملف."),
    0x43: _f("File attributes", "AL = 0 get / 1 set, DS:DX = name, CX = attributes", "CX = attributes",
             "Reads or changes read-only / hidden / system / archive.", "خصائص الملف."),
    0x47: _f("Current directory", "DL = drive (0 = current), DS:SI = 64-byte buffer", "buffer = path",
             "Gets the current directory without the drive letter.", "المجلد الحالي."),
    0x48: _f("Allocate memory", "BX = paragraphs", "AX = segment, or CF = 1 and BX = largest block",
             "Allocates conventional memory (an EXE must shrink its block with 4Ah first).", "حجز ذاكرة."),
    0x49: _f("Free memory", "ES = segment", "CF = 1 on error", "Frees a block from 48h.", "تحرير الذاكرة."),
    0x4A: _f("Resize memory block", "ES = segment, BX = new size in paragraphs", "CF on error",
             "Shrinks or grows a block (often the program's own, ES = PSP).", "تغيير حجم كتلة الذاكرة."),
    0x4B: _f("Execute program", "DS:DX = program name, ES:BX = parameter block, AL = 0", "CF on error",
             "Runs another program and waits for it.", "تشغيل برنامج آخر."),
    0x4C: _f("Exit program", "AL = exit code", "-", "Ends the program; the code is ERRORLEVEL in batch files. "
             "The usual ending: mov ax, 4C00h / int 21h.", "إنهاء البرنامج برمز الخروج AL."),
    0x4D: _f("Exit code of child", "-", "AL = exit code, AH = how it ended", "After 4Bh.", "رمز خروج البرنامج الابن."),
    0x4E: _f("Find first file", "DS:DX = ASCIIZ mask (*.*), CX = attributes", "DTA filled, CF when none",
             "Starts a directory search; the result is in the DTA (name at offset 1Eh).", "البحث عن أول ملف."),
    0x4F: _f("Find next file", "-", "DTA filled, CF when no more", "Continues the search of 4Eh.",
             "البحث عن الملف التالي."),
    0x56: _f("Rename file", "DS:DX = old name, ES:DI = new name", "CF on error", "Renames or moves a file.",
             "إعادة تسمية ملف."),
    0x62: _f("Get PSP", "-", "BX = PSP segment", "The Program Segment Prefix (command line at offset 80h).",
             "عنوان بادئة البرنامج PSP."),
})

INT10 = Interrupt(0x10, "Video BIOS", "خدمات الشاشة (BIOS)", "AH", {
    0x00: _f("Set video mode", "AL = mode (03h text 80x25, 13h 320x200x256, 12h 640x480x16, 01h text 40x25)", "-",
             "Switches the video mode and clears the screen (add 80h to AL to keep the memory).",
             "يضبط وضع الشاشة: 03h نص، 13h رسوم 256 لوناً."),
    0x01: _f("Cursor shape", "CH = start line, CL = end line (CX = 2000h hides it)", "-",
             "Sets the text cursor's scan lines.", "شكل المؤشر (2000h يخفيه)."),
    0x02: _f("Set cursor position", "BH = page, DH = row, DL = column", "-", "Moves the text cursor (0-based).",
             "يحرك المؤشر إلى الصف DH والعمود DL."),
    0x03: _f("Get cursor position", "BH = page", "DH = row, DL = column, CX = shape", "Reads the cursor position.",
             "يقرأ موقع المؤشر."),
    0x05: _f("Select display page", "AL = page", "-", "Shows another text page.", "يختار صفحة العرض."),
    0x06: _f("Scroll up / clear window", "AL = lines (0 = clear), BH = attribute, CH,CL = top-left, DH,DL = "
             "bottom-right", "-", "Scrolls a window up; AL = 0 clears it with attribute BH.",
             "تمرير نافذة للأعلى أو مسحها."),
    0x07: _f("Scroll down", "as 06h", "-", "Scrolls a window down.", "تمرير نافذة للأسفل."),
    0x08: _f("Read character and attribute", "BH = page", "AL = character, AH = attribute",
             "Reads what is at the cursor.", "يقرأ الحرف ولونه عند المؤشر."),
    0x09: _f("Write character and attribute", "AL = character, BH = page, BL = attribute (colour), CX = count", "-",
             "Writes CX copies at the cursor without moving it. Attribute = background * 16 + foreground.",
             "يكتب حرفاً بلون دون تحريك المؤشر."),
    0x0A: _f("Write character", "AL = character, BH = page, CX = count", "-", "Like 09h, keeps the attribute.",
             "يكتب حرفاً مع الإبقاء على اللون."),
    0x0B: _f("Background / border colour", "BH = 0, BL = colour", "-", "Border colour in text modes, background in "
             "CGA graphics.", "لون الإطار أو الخلفية."),
    0x0C: _f("Write pixel", "AL = colour, BH = page, CX = x, DX = y", "-", "Draws a pixel in a graphics mode "
             "(slow but works in every mode).", "يرسم نقطة."),
    0x0D: _f("Read pixel", "BH = page, CX = x, DX = y", "AL = colour", "Reads a pixel.", "يقرأ لون نقطة."),
    0x0E: _f("Teletype output", "AL = character, BH = page, BL = colour (graphics)", "-",
             "Writes a character and moves the cursor; handles CR, LF, BS and BEL.", "يكتب حرفاً ويحرك المؤشر."),
    0x0F: _f("Get video mode", "-", "AL = mode, AH = columns, BH = page", "Reads the current mode.",
             "يقرأ وضع الشاشة الحالي."),
    0x10: _f("Palette (EGA / VGA)", "AL = 10h: set DAC colour BX to DH = red, CH = green, CL = blue (0-63)", "-",
             "Changes palette registers; AL selects the sub-function.", "تغيير لوحة الألوان."),
    0x13: _f("Write string", "AL = mode, BH = page, BL = attribute, CX = length, DH,DL = position, ES:BP = text",
             "-", "Writes a whole string at a position.", "يكتب نصاً كاملاً."),
})

INT16 = Interrupt(0x16, "Keyboard BIOS", "خدمات لوحة المفاتيح (BIOS)", "AH", {
    0x00: _f("Wait for key", "-", "AH = scan code, AL = ASCII (0 for arrows / F-keys)", "Waits for a key and removes "
             "it from the buffer. Arrows: up 48h, down 50h, left 4Bh, right 4Dh.", "ينتظر مفتاحاً."),
    0x01: _f("Key waiting?", "-", "ZF = 0 and AX = key when one is waiting (it stays in the buffer)",
             "Checks the keyboard without waiting.", "هل يوجد مفتاح؟ دون انتظار."),
    0x02: _f("Shift states", "-", "AL = bits: 0 right Shift, 1 left Shift, 2 Ctrl, 3 Alt, 4 Scroll, 5 Num, 6 Caps",
             "Reads the Shift / Ctrl / Alt keys.", "حالة مفاتيح Shift و Ctrl و Alt."),
    0x05: _f("Store key", "CH = scan code, CL = ASCII", "AL = 0 when stored", "Puts a key into the buffer as if it "
             "was typed (RAD IDE's RADKEYS uses it).", "يضع مفتاحاً في المخزن."),
    0x10: _f("Wait for key (enhanced)", "-", "AH = scan code, AL = ASCII (E0h for grey keys)",
             "Like 00h, also F11 / F12.", "ينتظر مفتاحاً (لوحة موسعة)."),
    0x11: _f("Key waiting? (enhanced)", "-", "ZF = 0 when a key is waiting", "Like 01h for the enhanced keyboard.",
             "هل يوجد مفتاح؟ (لوحة موسعة)."),
})

INT33 = Interrupt(0x33, "Mouse driver", "مشغل الفأرة", "AX", {
    0x00: _f("Reset driver", "-", "AX = FFFFh when a mouse driver is installed, BX = buttons",
             "Resets the mouse and tells whether there is one.", "تهيئة الفأرة."),
    0x01: _f("Show cursor", "-", "-", "Shows the mouse cursor.", "إظهار مؤشر الفأرة."),
    0x02: _f("Hide cursor", "-", "-", "Hides it (do this before drawing under it).", "إخفاء مؤشر الفأرة."),
    0x03: _f("Position and buttons", "-", "CX = x, DX = y (pixels; text: column * 8), BX = buttons (1 left, "
             "2 right, 4 middle)", "Reads the mouse.", "موقع الفأرة والأزرار."),
    0x04: _f("Set position", "CX = x, DX = y", "-", "Moves the mouse cursor.", "تحريك المؤشر."),
    0x05: _f("Button press data", "BX = button", "BX = presses, CX, DX = last press position",
             "Counts presses since the last call.", "عدد الضغطات."),
    0x07: _f("Horizontal range", "CX = min, DX = max", "-", "Limits x.", "حدود الحركة الأفقية."),
    0x08: _f("Vertical range", "CX = min, DX = max", "-", "Limits y.", "حدود الحركة الرأسية."),
    0x0B: _f("Motion counters", "-", "CX, DX = mickeys moved", "Raw movement since the last call.",
             "مقدار الحركة."),
    0x0C: _f("Event handler", "CX = event mask, ES:DX = handler", "-", "Calls a far procedure on mouse events.",
             "إجراء يستدعى عند أحداث الفأرة."),
})

INT1A = Interrupt(0x1A, "Time of day (BIOS)", "الوقت (BIOS)", "AH", {
    0x00: _f("Read tick counter", "-", "CX:DX = ticks since midnight (18.2 per second), AL = midnight flag",
             "The BIOS clock: good for delays and random seeds.", "عداد النبضات منذ منتصف الليل."),
    0x01: _f("Set tick counter", "CX:DX = ticks", "-", "Sets the BIOS clock.", "ضبط العداد."),
    0x02: _f("Read RTC time", "-", "CH = hour, CL = minute, DH = second (BCD)", "The real-time clock (AT).",
             "وقت الساعة الحقيقية."),
    0x04: _f("Read RTC date", "-", "CH = century, CL = year, DH = month, DL = day (BCD)", "The real-time clock date.",
             "تاريخ الساعة الحقيقية."),
})

INT20 = Interrupt(0x20, "Terminate program (old)", "إنهاء البرنامج (قديم)", "-", {})

INTERRUPTS = {i.number: i for i in (INT21, INT10, INT16, INT33, INT1A, INT20)}


def interrupt_doc(number: int, function: int | None = None, arabic: bool = False) -> str:
    """Markdown for INT n (and one function, when known)."""
    it = INTERRUPTS.get(number)
    if it is None:
        return ""
    head = f"**INT {number:02X}h** - {it.title}" + (f" ({it.ar})" if arabic else "")
    if function is not None and function in it.functions:
        f = it.functions[function]
        return (f"{head}  \n**{it.selector}={function:02X}h {f.name}**  \nIn: {f.inputs}  \nOut: {f.outputs}  \n"
                f"{f.en}" + (f"  \n{f.ar}" if arabic and f.ar else ""))
    rows = "  \n".join(f"{it.selector}={k:02X}h {v.name}" for k, v in sorted(it.functions.items()))
    return head + ("  \n" + rows if rows else "")


# ============================================================================ QBasic / QuickBASIC
QBASIC: dict[str, tuple[str, str]] = {
    "PRINT": ("PRINT [expr][; or ,][...]", "Writes to the screen; ';' keeps the cursor, ',' jumps to the next "
              "14-column zone."),
    "INPUT": ("INPUT [\"prompt\";] var[, var...]", "Reads values typed by the user (a ',' prompt hides the '?')."),
    "LINE INPUT": ("LINE INPUT [\"prompt\";] text$", "Reads a whole line including commas."),
    "CLS": ("CLS [0|1|2]", "Clears the screen (or the graphics / text viewport)."),
    "COLOR": ("COLOR [foreground][, background][, border]", "Text colours 0-15 (+16 blinks) and background 0-7; in "
              "SCREEN 13 the drawing colour 0-255."),
    "LOCATE": ("LOCATE [row][, col][, cursor]", "Moves the text cursor (rows 1-25, columns 1-80); cursor 0 hides it."),
    "SCREEN": ("SCREEN mode", "0 = text, 12 = 640x480x16, 13 = 320x200x256 graphics."),
    "WIDTH": ("WIDTH columns[, rows]", "Text width 40 / 80 and rows 25 / 43 / 50."),
    "PSET": ("PSET (x, y)[, colour]", "Draws one pixel."),
    "PRESET": ("PRESET (x, y)[, colour]", "Draws a pixel in the background colour by default."),
    "LINE": ("LINE [(x1, y1)]-(x2, y2)[, colour][, B|BF]", "A line, a box (B) or a filled box (BF)."),
    "CIRCLE": ("CIRCLE (x, y), radius[, colour[, start, end[, aspect]]]", "A circle, arc or ellipse."),
    "PAINT": ("PAINT (x, y)[, fill][, border]", "Flood-fills an area up to the border colour."),
    "DRAW": ("DRAW commands$", "Turtle graphics: U D L R E F G H, M x,y, C colour ..."),
    "PALETTE": ("PALETTE [attribute, colour]", "Changes a palette entry (SCREEN 13: colour = blue*65536 + "
                "green*256 + red, 0-63 each)."),
    "GET": ("GET (x1, y1)-(x2, y2), array", "Copies a screen area into an array (sprites); also file GET."),
    "PUT": ("PUT (x, y), array[, PSET|XOR|...]", "Draws an area saved with GET."),
    "INKEY$": ("k$ = INKEY$", "The key waiting in the buffer, or \"\" (does not wait). Arrows give 2 characters "
               "(CHR$(0) + scan code; FreeBASIC uses CHR$(255))."),
    "SLEEP": ("SLEEP [seconds]", "Waits for the time or a key."),
    "BEEP": ("BEEP", "A short beep on the PC speaker."),
    "SOUND": ("SOUND frequency, duration", "QBasic only (not FreeBASIC): a tone; duration in clock ticks "
              "(18.2 per second)."),
    "PLAY": ("PLAY commands$", "QBasic only (not FreeBASIC): music macro language (O3 L8 C D E ...)."),
    "OUT": ("OUT port, value", "Writes a byte to an I/O port (PC speaker: 42h, 43h, 61h)."),
    "INP": ("v = INP(port)", "Reads a byte from an I/O port."),
    "PEEK": ("v = PEEK(offset)", "Reads a byte of the segment set by DEF SEG."),
    "POKE": ("POKE offset, value", "Writes a byte into the segment set by DEF SEG (&HB800 text, &HA000 VGA)."),
    "DEF SEG": ("DEF SEG = segment", "Selects the memory segment for PEEK / POKE / BLOAD."),
    "DIM": ("DIM [SHARED] name[(bounds)] [AS type]", "Declares a variable or an array."),
    "REDIM": ("REDIM [PRESERVE] array(bounds)", "Changes the size of a dynamic array."),
    "CONST": ("CONST name = value", "A named constant."),
    "TYPE": ("TYPE name ... END TYPE", "A record (user-defined type)."),
    "SUB": ("SUB name [(params)] ... END SUB", "A procedure; call it with name args or CALL name(args)."),
    "FUNCTION": ("FUNCTION name [(params)] ... END FUNCTION", "Returns a value: assign it to the function's name."),
    "DECLARE": ("DECLARE SUB|FUNCTION name (params)", "Declares a procedure before its use."),
    "GOSUB": ("GOSUB label", "Jumps to a subroutine; RETURN comes back."),
    "RETURN": ("RETURN [label]", "Returns from GOSUB."),
    "GOTO": ("GOTO label|line", "Jumps to a label or line number."),
    "IF": ("IF cond THEN ... [ELSEIF ...] [ELSE ...] END IF", "Conditional statement (single-line form too)."),
    "SELECT CASE": ("SELECT CASE expr / CASE values / CASE ELSE / END SELECT", "Chooses a branch by value; CASE 1 TO "
                    "5, CASE IS > 10."),
    "FOR": ("FOR v = a TO b [STEP s] ... NEXT [v]", "A counted loop."),
    "DO": ("DO [WHILE|UNTIL cond] ... LOOP [WHILE|UNTIL cond]", "A loop; EXIT DO leaves it."),
    "WHILE": ("WHILE cond ... WEND", "The old-style loop."),
    "DATA": ("DATA value, value, ...", "Constants read by READ."),
    "READ": ("READ var[, var...]", "Reads the next DATA values."),
    "RESTORE": ("RESTORE [label]", "Makes READ start again (at the DATA after label)."),
    "OPEN": ("OPEN file$ FOR INPUT|OUTPUT|APPEND|BINARY|RANDOM AS #n", "Opens a file."),
    "CLOSE": ("CLOSE [#n]", "Closes files."),
    "RANDOMIZE": ("RANDOMIZE [seed]", "Seeds RND (RANDOMIZE TIMER for different numbers each run)."),
    "RND": ("x = RND", "A random number 0 <= x < 1: INT(RND * 6) + 1 is a dice roll."),
    "TIMER": ("t = TIMER", "Seconds since midnight (as a SINGLE)."),
    "TIME$": ("t$ = TIME$", "The time as \"hh:mm:ss\"."),
    "DATE$": ("d$ = DATE$", "The date as \"mm-dd-yyyy\"."),
    "CHR$": ("c$ = CHR$(code)", "The character of an ASCII / CP437 code (CHR$(219) is a full block)."),
    "ASC": ("n = ASC(text$)", "Code of the first character."),
    "STR$": ("s$ = STR$(n)", "Number to text (a leading space for positive numbers)."),
    "VAL": ("n = VAL(text$)", "Text to number."),
    "LEN": ("n = LEN(text$)", "Length of a string."),
    "MID$": ("s$ = MID$(text$, start[, length])", "Part of a string (also MID$(...) = assignment)."),
    "LEFT$": ("s$ = LEFT$(text$, n)", "The first n characters."),
    "RIGHT$": ("s$ = RIGHT$(text$, n)", "The last n characters."),
    "STRING$": ("s$ = STRING$(n, char)", "n copies of a character."),
    "SPACE$": ("s$ = SPACE$(n)", "n spaces."),
    "UCASE$": ("s$ = UCASE$(text$)", "Upper case."),
    "INSTR": ("n = INSTR([start,] text$, find$)", "Position of find$ in text$ (0 = not found)."),
    "INT": ("n = INT(x)", "Rounds down."),
    "ABS": ("n = ABS(x)", "Absolute value."),
    "SQR": ("n = SQR(x)", "Square root."),
    "END": ("END", "Ends the program."),
    "SYSTEM": ("SYSTEM", "Ends the program (and leaves the QBasic editor)."),
    "SHELL": ("SHELL [command$]", "Runs a DOS command."),
    "DEFINT": ("DEFINT A-Z", "Variables starting with these letters are INTEGER (faster)."),
    "REM": ("REM comment   or   ' comment", "A comment."),
    "SWAP": ("SWAP a, b", "Exchanges two variables."),
    "__GETMOUSE": ("__GETMOUSE x, y[, wheel[, buttons]]", "FreeBASIC (-lang qb spelling of GETMOUSE): mouse position "
                   "in graphics modes; x = -1 when there is no mouse."),
}

# ============================================================================ Turbo Pascal units
PASCAL: dict[str, tuple[str, str, str]] = {
    # Crt
    "ClrScr": ("procedure ClrScr", "Crt", "Clears the window and puts the cursor at the top left."),
    "ClrEol": ("procedure ClrEol", "Crt", "Clears to the end of the line."),
    "GotoXY": ("procedure GotoXY(X, Y: Byte)", "Crt", "Moves the cursor (1-based, inside the window)."),
    "WhereX": ("function WhereX: Byte", "Crt", "Cursor column."),
    "WhereY": ("function WhereY: Byte", "Crt", "Cursor row."),
    "TextColor": ("procedure TextColor(Color: Byte)", "Crt", "Foreground colour 0-15 (+Blink)."),
    "TextBackground": ("procedure TextBackground(Color: Byte)", "Crt", "Background colour 0-7."),
    "NormVideo": ("procedure NormVideo", "Crt", "Back to the colours at program start."),
    "HighVideo": ("procedure HighVideo", "Crt", "Bright foreground."),
    "LowVideo": ("procedure LowVideo", "Crt", "Dim foreground."),
    "Window": ("procedure Window(X1, Y1, X2, Y2: Byte)", "Crt", "Limits output to a rectangle."),
    "KeyPressed": ("function KeyPressed: Boolean", "Crt", "True when a key is waiting (does not wait)."),
    "ReadKey": ("function ReadKey: Char", "Crt", "Waits for a key; arrows / F-keys give #0 then the scan code "
                "(up #72, down #80, left #75, right #77)."),
    "Delay": ("procedure Delay(MS: Word)", "Crt", "Waits MS milliseconds."),
    "Sound": ("procedure Sound(Hz: Word)", "Crt", "Starts a tone on the PC speaker."),
    "NoSound": ("procedure NoSound", "Crt", "Stops the tone."),
    "TextMode": ("procedure TextMode(Mode: Integer)", "Crt", "CO80, BW80, CO40, Font8x8 (43 / 50 lines)."),
    "InsLine": ("procedure InsLine", "Crt", "Inserts a line at the cursor."),
    "DelLine": ("procedure DelLine", "Crt", "Deletes the line at the cursor."),
    # Dos
    "Intr": ("procedure Intr(IntNo: Byte; var Regs: Registers)", "Dos", "Calls a software interrupt with the "
             "registers in Regs (R.AX, R.AH, R.BX, ...)."),
    "MsDos": ("procedure MsDos(var Regs: Registers)", "Dos", "Intr($21, Regs)."),
    "GetTime": ("procedure GetTime(var Hour, Minute, Second, Sec100: Word)", "Dos", "The system time."),
    "GetDate": ("procedure GetDate(var Year, Month, Day, DayOfWeek: Word)", "Dos", "The system date."),
    "SetTime": ("procedure SetTime(Hour, Minute, Second, Sec100: Word)", "Dos", "Sets the time."),
    "FindFirst": ("procedure FindFirst(Path: PathStr; Attr: Word; var S: SearchRec)", "Dos", "Starts a directory "
                  "search; DosError = 0 while files are found."),
    "FindNext": ("procedure FindNext(var S: SearchRec)", "Dos", "Next file of FindFirst."),
    "Exec": ("procedure Exec(Path, CmdLine: string)", "Dos", "Runs another program (DosExitCode afterwards)."),
    "GetEnv": ("function GetEnv(Name: string): string", "Dos", "An environment variable."),
    "DiskFree": ("function DiskFree(Drive: Byte): LongInt", "Dos", "Free bytes (0 = current drive)."),
    "GetIntVec": ("procedure GetIntVec(IntNo: Byte; var Vector: Pointer)", "Dos", "Reads an interrupt vector."),
    "SetIntVec": ("procedure SetIntVec(IntNo: Byte; Vector: Pointer)", "Dos", "Installs an interrupt handler."),
    "Registers": ("type Registers = record AX, BX, CX, DX, BP, SI, DI, DS, ES, Flags: Word ... end", "Dos",
                  "CPU registers for Intr / MsDos (byte halves AH, AL, ...)."),
    # Graph
    "InitGraph": ("procedure InitGraph(var Driver, Mode: Integer; Path: string)", "Graph", "Starts graphics "
                  "(Driver := Detect); Free Pascal needs no .BGI files."),
    "CloseGraph": ("procedure CloseGraph", "Graph", "Back to text mode."),
    "GraphResult": ("function GraphResult: Integer", "Graph", "grOk (0) or an error code."),
    "PutPixel": ("procedure PutPixel(X, Y: Integer; Color: Word)", "Graph", "One pixel."),
    "Line": ("procedure Line(X1, Y1, X2, Y2: Integer)", "Graph", "A line in the current colour."),
    "Rectangle": ("procedure Rectangle(X1, Y1, X2, Y2: Integer)", "Graph", "A rectangle outline."),
    "Bar": ("procedure Bar(X1, Y1, X2, Y2: Integer)", "Graph", "A filled rectangle (SetFillStyle)."),
    "Circle": ("procedure Circle(X, Y: Integer; Radius: Word)", "Graph", "A circle."),
    "SetColor": ("procedure SetColor(Color: Word)", "Graph", "Drawing colour."),
    "SetFillStyle": ("procedure SetFillStyle(Pattern: Word; Color: Word)", "Graph", "Fill pattern and colour."),
    "OutTextXY": ("procedure OutTextXY(X, Y: Integer; S: string)", "Graph", "Text in graphics mode."),
    "GetMaxX": ("function GetMaxX: Integer", "Graph", "Largest x (639 in VGAHi)."),
    "GetMaxY": ("function GetMaxY: Integer", "Graph", "Largest y."),
    "ClearDevice": ("procedure ClearDevice", "Graph", "Clears the graphics screen."),
    # System
    "WriteLn": ("procedure WriteLn([var F: Text;] items)", "System", "Writes items and a new line (X:width:decimals)."),
    "ReadLn": ("procedure ReadLn([var F: Text;] vars)", "System", "Reads a line."),
    "Random": ("function Random(N: Word): Word", "System", "0 .. N-1 (Randomize seeds it)."),
    "Randomize": ("procedure Randomize", "System", "Seeds Random from the clock."),
    "Mem": ("Mem[Segment:Offset]", "System", "A byte of memory (MemW = word): Mem[$A000:Y*320+X] is a mode 13h "
            "pixel."),
    "Port": ("Port[address]", "System", "An I/O port byte (read or assign)."),
    "Halt": ("procedure Halt([ExitCode: Word])", "System", "Ends the program (ERRORLEVEL)."),
}
PASCAL_KEYWORDS = """and array asm begin case const constructor destructor div do downto else end file for function
    goto if implementation in inline interface label mod nil not object of or packed procedure program record repeat
    set shl shr string then to type unit until uses var while with xor absolute external far forward interrupt near
    private public virtual integer word byte shortint longint char boolean real single double extended comp text
    true false""".split()

# ============================================================================ C (conio / dos.h / i86.h / tcgraph)
C_FUNCS: dict[str, tuple[str, str, str]] = {
    "clrscr": ("void clrscr(void)", "tcconio.h", "Clears the text window."),
    "gotoxy": ("void gotoxy(int x, int y)", "tcconio.h", "Moves the cursor (1-based)."),
    "wherex": ("int wherex(void)", "tcconio.h", "Cursor column."),
    "wherey": ("int wherey(void)", "tcconio.h", "Cursor row."),
    "textcolor": ("void textcolor(int color)", "tcconio.h", "Foreground colour for cputs / cprintf / putch."),
    "textbackground": ("void textbackground(int color)", "tcconio.h", "Background colour 0-7."),
    "textattr": ("void textattr(int attr)", "tcconio.h", "Both colours: background * 16 + foreground."),
    "normvideo": ("void normvideo(void)", "tcconio.h", "Light grey on black."),
    "clreol": ("void clreol(void)", "tcconio.h", "Clears to the end of the line."),
    "window": ("void window(int left, int top, int right, int bottom)", "tcconio.h", "Limits the text output."),
    "cputs": ("int cputs(const char *s)", "conio.h", "Writes a string to the console (colour with tcconio.h)."),
    "cprintf": ("int cprintf(const char *fmt, ...)", "conio.h", "printf to the console (use \\r\\n)."),
    "putch": ("int putch(int c)", "conio.h", "Writes one character to the console."),
    "getch": ("int getch(void)", "conio.h", "Waits for a key, no echo; arrows give 0 (or 0xE0) then the scan code."),
    "getche": ("int getche(void)", "conio.h", "Like getch with echo."),
    "kbhit": ("int kbhit(void)", "conio.h", "Non-zero when a key is waiting."),
    "int86": ("int int86(int intno, union REGS *in, union REGS *out)", "i86.h / dos.h", "Calls interrupt intno with "
              "r.h.ah, r.x.ax, ... (int86x for segment registers)."),
    "int86x": ("int int86x(int intno, union REGS *in, union REGS *out, struct SREGS *s)", "i86.h", "int86 with DS / "
               "ES in s."),
    "intdos": ("int intdos(union REGS *in, union REGS *out)", "dos.h", "int86(0x21, ...)."),
    "MK_FP": ("void __far *MK_FP(unsigned seg, unsigned off)", "i86.h", "Builds a far pointer: MK_FP(0xA000, 0) is "
              "the VGA memory."),
    "FP_SEG": ("unsigned FP_SEG(void __far *p)", "i86.h", "Segment part of a far pointer."),
    "FP_OFF": ("unsigned FP_OFF(void __far *p)", "i86.h", "Offset part of a far pointer."),
    "sound": ("void sound(unsigned hz)", "i86.h", "Starts a PC speaker tone."),
    "nosound": ("void nosound(void)", "i86.h", "Stops the tone."),
    "delay": ("void delay(unsigned ms)", "i86.h", "Waits ms milliseconds."),
    "inp": ("int inp(unsigned port)", "conio.h", "Reads an I/O port (Turbo C: inportb)."),
    "outp": ("int outp(unsigned port, int value)", "conio.h", "Writes an I/O port (Turbo C: outportb)."),
    "_dos_gettime": ("void _dos_gettime(struct dostime_t *t)", "dos.h", "hour, minute, second, hsecond."),
    "_dos_getdate": ("void _dos_getdate(struct dosdate_t *d)", "dos.h", "year, month, day, dayofweek."),
    "_dos_setvect": ("void _dos_setvect(unsigned intno, void (__interrupt __far *handler)())", "dos.h",
                     "Installs an interrupt handler."),
    "_dos_getvect": ("void (__interrupt __far *_dos_getvect(unsigned intno))()", "dos.h", "Reads a vector."),
    "_setvideomode": ("short _setvideomode(short mode)", "graph.h", "Open Watcom graphics: _MRES256COLOR = mode 13h, "
                      "_DEFAULTMODE back to text (link graph.lib, automatic)."),
    "initgraph": ("void initgraph(int *driver, int *mode, const char *path)", "tcgraph.h / graphics.h",
                  "BGI subset: 640x480x16; the path is ignored (no .BGI files)."),
    "closegraph": ("void closegraph(void)", "tcgraph.h", "Back to text mode."),
    "putpixel": ("void putpixel(int x, int y, int color)", "tcgraph.h", "One pixel."),
    "line": ("void line(int x1, int y1, int x2, int y2)", "tcgraph.h", "A line in the current colour."),
    "circle": ("void circle(int x, int y, int radius)", "tcgraph.h", "A circle."),
    "rectangle": ("void rectangle(int l, int t, int r, int b)", "tcgraph.h", "A rectangle outline."),
    "bar": ("void bar(int l, int t, int r, int b)", "tcgraph.h", "A filled rectangle (setfillstyle)."),
    "setcolor": ("void setcolor(int color)", "tcgraph.h", "Drawing colour 0-15."),
    "outtextxy": ("void outtextxy(int x, int y, const char *s)", "tcgraph.h", "Text at a pixel position (8x16 "
                  "cells)."),
    "printf": ("int printf(const char *fmt, ...)", "stdio.h", "Formatted output to standard output."),
    "random": ("int random(int n)", "tcconio.h", "Turbo C: 0 .. n-1 (rand() % n)."),
    "randomize": ("void randomize(void)", "tcconio.h", "Turbo C: seeds rand() from the clock."),
}
C_KEYWORDS = """auto break case char const continue default do double else enum extern float for goto if int long
    register return short signed sizeof static struct switch typedef union unsigned void volatile while far near
    huge interrupt __far __near __huge __interrupt _asm cdecl pascal""".split()

# ============================================================================ batch
BATCH: dict[str, tuple[str, str]] = {
    "ECHO": ("ECHO [ON|OFF|text]   ECHO.", "Shows text; ECHO OFF stops showing the commands (@ hides one line)."),
    "SET": ("SET name=value", "An environment variable; use it as %name%."),
    "IF": ("IF [NOT] EXIST file | ERRORLEVEL n | a==b  command", "A condition; ERRORLEVEL n means 'n or more'."),
    "GOTO": ("GOTO label", "Jumps to :label."),
    "CALL": ("CALL other.bat [params]", "Runs another batch file and comes back."),
    "FOR": ("FOR %%v IN (set) DO command", "Repeats a command for every item / file mask."),
    "SHIFT": ("SHIFT", "Moves %2 to %1, %3 to %2, ..."),
    "PAUSE": ("PAUSE", "Waits for a key."),
    "REM": ("REM comment", "A comment."),
    "CHOICE": ("CHOICE [/C:keys] [/N] [/T:key,secs] [text]", "Waits for one of the keys; its position is the "
               "ERRORLEVEL (test the highest first)."),
    "CLS": ("CLS", "Clears the screen."),
    "CD": ("CD [path]", "Changes the current directory."),
    "DIR": ("DIR [mask] [/W] [/P]", "Lists files."),
    "COPY": ("COPY source target", "Copies files."),
    "DEL": ("DEL mask", "Deletes files."),
    "MD": ("MD path", "Creates a directory."),
    "TYPE": ("TYPE file", "Shows a text file."),
    "PATH": ("PATH dir;dir", "Where DOS looks for programs."),
    "VER": ("VER", "The DOS version."),
    "MOUNT": ("MOUNT C path", "DOSBox-X: makes a host folder a DOS drive."),
    "EXIT": ("EXIT", "Leaves COMMAND.COM (closes DOSBox-X)."),
}


def arabic_ui() -> bool:
    try:
        from ...emu8086.messages import ui_language
        return ui_language() == "ar"
    except Exception:  # noqa: BLE001
        return False


__all__ = ["BATCH", "C_FUNCS", "C_KEYWORDS", "INTERRUPTS", "IntFunc", "Interrupt", "PASCAL", "PASCAL_KEYWORDS",
           "QBASIC", "arabic_ui", "interrupt_doc"]
