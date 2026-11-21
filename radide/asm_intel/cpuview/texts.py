"""English / Arabic texts of the CPU view (they follow the IDE language: radide.i18n.language()).

The view's widgets set the ``i18n_skip_items`` property and pick their own text here, so that switching the IDE
language and reopening the view shows the other language. ``T(key)`` returns the text, ``T(key, a=1)`` fills
``{a}`` placeholders.
"""
from __future__ import annotations

TEXTS: dict[str, tuple[str, str]] = {
    # titles / panes
    "cpu": ("CPU", "المعالج (CPU)"),
    "cpu_title": ("CPU - {where}", "المعالج - {where}"),
    "disasm": ("Disassembly", "التفكيك"),
    "registers": ("Registers", "المسجلات"),
    "dump": ("Dump", "الذاكرة"),
    "stack": ("Stack", "المكدس"),
    "not_running": ("The CPU view fills while a native program (assembly, C, C++, Rust) or the 8086 emulator is "
                    "paused in the debugger. Start debugging (F5) and stop at a breakpoint.",
                    "تمتلئ نافذة المعالج أثناء إيقاف برنامج أصلي (أسمبلي، C، C++، Rust) أو محاكي 8086 مؤقتاً في "
                    "المصحح. ابدأ التصحيح (F5) وتوقف عند نقطة توقف."),
    "running": ("Running...", "قيد التشغيل..."),
    # columns
    "col_address": ("Address", "العنوان"),
    "col_bytes": ("Bytes", "البايتات"),
    "col_instruction": ("Instruction", "التعليمة"),
    "col_comment": ("Comment", "تعليق"),
    "col_value": ("Value", "القيمة"),
    "col_ascii": ("ASCII", "ASCII"),
    "col_hex": ("Hex dump", "عرض سداسي عشري"),
    # register pages
    "page_general": ("General", "عامة"),
    "page_fpu": ("FPU", "الفاصلة العائمة FPU"),
    "page_sse": ("SSE", "SSE"),
    "flags_hint": ("Click a flag to toggle it. Red = changed by the last step.",
                   "انقر على علم لعكس قيمته. الأحمر = تغيّر في آخر خطوة."),
    # disassembly info line
    "jump_taken": ("Jump is taken", "القفزة ستُنفَّذ"),
    "jump_not_taken": ("Jump is NOT taken", "القفزة لن تُنفَّذ"),
    "jump_why": ("{mn}: {cond}. Now {flags}.", "{mn}: {cond}. الآن {flags}."),
    "loop_why": ("{mn}: decrements {cx} ({value} -> {after}) and jumps while it is not zero.",
                 "{mn}: تُنقِص {cx} (من {value} إلى {after}) وتقفز ما دامت لا تساوي صفراً."),
    "dest": ("Destination", "الوجهة"),
    "ea": ("Memory operand address", "عنوان معامل الذاكرة"),
    "return_to": ("Return to {where}", "العودة إلى {where}"),
    "return_from": ("return address (pushed by CALL)", "عنوان رجوع (دفعته تعليمة CALL)"),
    # context menu
    "m_follow": ("Follow", "تتبّع"),
    "m_follow_dump": ("Follow in Dump", "تتبّع في الذاكرة"),
    "m_follow_stack": ("Follow in Stack", "تتبّع في المكدس"),
    "m_follow_disasm": ("Follow in Disassembler", "تتبّع في المفكك"),
    "m_goto": ("Go to Address / Expression...", "انتقال إلى عنوان / تعبير..."),
    "m_origin": ("Go to Current Instruction (*)", "انتقال إلى التعليمة الحالية (*)"),
    "m_bp": ("Toggle Breakpoint", "تبديل نقطة التوقف"),
    "m_run_cursor": ("Run to Cursor", "تشغيل حتى المؤشر"),
    "m_step_into": ("Step Into", "خطوة إلى الداخل"),
    "m_step_over": ("Step Over", "خطوة فوق"),
    "m_till_return": ("Execute till Return", "التنفيذ حتى الرجوع"),
    "m_run": ("Run", "تشغيل"),
    "m_assemble": ("Assemble...", "تجميع..."),
    "m_binary_edit": ("Binary Edit...", "تعديل ثنائي..."),
    "m_search": ("Search for", "بحث عن"),
    "m_search_cmd": ("Command...", "تعليمة..."),
    "m_search_const": ("Constant...", "ثابت..."),
    "m_search_strings": ("All Referenced Strings", "كل النصوص المشار إليها"),
    "m_comment": ("Comment...", "تعليق..."),
    "m_label": ("Label...", "تسمية..."),
    "m_copy": ("Copy", "نسخ"),
    "m_source": ("Go to Source Line", "انتقال إلى سطر المصدر"),
    "m_modify": ("Modify...", "تعديل..."),
    "m_increment": ("Increment", "زيادة"),
    "m_decrement": ("Decrement", "إنقاص"),
    "m_zero": ("Zero", "تصفير"),
    "m_edit_bytes": ("Edit Bytes...", "تعديل البايتات..."),
    # dialogs
    "goto_title": ("Enter expression to follow", "أدخل التعبير المراد تتبّعه"),
    "goto_prompt": ("Address, label, register or expression (0x401000, main, rsp+8, [rbp-8]):",
                    "عنوان أو تسمية أو مسجل أو تعبير (0x401000، main، rsp+8):"),
    "assemble_title": ("Assemble at {addr}", "التجميع عند {addr}"),
    "assemble_prompt": ("Instruction (several: separate with ';'):", "التعليمة (لعدة تعليمات افصل بـ ';'):"),
    "assemble_fill": ("Fill the rest of the old instruction with NOPs", "املأ باقي التعليمة القديمة بـ NOP"),
    "binary_title": ("Edit bytes at {addr}", "تعديل البايتات عند {addr}"),
    "binary_prompt": ("Hex bytes (e.g. 90 90 B8 05 00 00 00):", "بايتات سداسية عشرية (مثلاً 90 90 B8 05 00 00 00):"),
    "comment_title": ("Comment at {addr}", "تعليق عند {addr}"),
    "label_title": ("Label at {addr}", "تسمية عند {addr}"),
    "search_cmd_prompt": ("Command (e.g. 'call', 'add rax' or 'mov .*, 5'):", "التعليمة (مثلاً call أو add rax):"),
    "search_const_prompt": ("Constant (hex 0x.. or decimal):", "الثابت (سداسي عشري 0x.. أو عشري):"),
    "search_results": ("Search results: {what}", "نتائج البحث: {what}"),
    "found_n": ("{n} found", "تم العثور على {n}"),
    "modify_reg": ("New value of {reg}:", "القيمة الجديدة لـ {reg}:"),
    # errors / explanations
    "err_expr": ("Cannot follow '{expr}': {err}", "لا يمكن تتبّع '{expr}': {err}"),
    "err_expr_why": ("Use a number (0x401000), a label of the program, a register (rsp, rip) or register+offset.",
                     "استخدم رقماً (0x401000) أو تسمية من البرنامج أو مسجلاً (rsp, rip) أو مسجلاً+إزاحة."),
    "err_assemble": ("This instruction cannot be assembled:\n{err}", "تعذّر تجميع هذه التعليمة:\n{err}"),
    "err_assemble_why": ("Write one instruction in the assembler's syntax (NASM for native programs, MASM-like for "
                         "the 8086 emulator). Example: mov eax, 5 / jmp 0x401020 / nop",
                         "اكتب تعليمة واحدة بصيغة المجمّع (NASM للبرامج الأصلية، وصيغة MASM لمحاكي 8086). "
                         "مثال: mov eax, 5 أو jmp 0x401020 أو nop"),
    "err_assemble_longer": ("The new code ({new} bytes) is longer than the instruction it replaces ({old} bytes): it "
                            "overwrites the start of the next instruction(s). Continue?",
                            "الكود الجديد ({new} بايت) أطول من التعليمة التي يستبدلها ({old} بايت): سيكتب فوق "
                            "بداية التعليمة التالية. هل تريد المتابعة؟"),
    "err_write": ("Cannot write memory at {addr}: {err}", "تعذّرت الكتابة في الذاكرة عند {addr}: {err}"),
    "err_write_why": ("Code pages of a running Windows program are usually read-only for the program but gdb can "
                      "still patch them; the address may be outside the program's memory.",
                      "صفحات الكود في برنامج ويندوز تكون للقراءة فقط عادة لكن gdb يستطيع تعديلها؛ ربما العنوان "
                      "خارج ذاكرة البرنامج."),
    "err_hex": ("'{text}' is not a list of hex bytes.", "'{text}' ليست قائمة بايتات سداسية عشرية."),
    "err_value": ("'{text}' is not a number.", "'{text}' ليس رقماً."),
    "bp_set": ("Breakpoint at {addr} set", "تم وضع نقطة توقف عند {addr}"),
    "bp_removed": ("Breakpoint at {addr} removed", "تمت إزالة نقطة التوقف عند {addr}"),
    "patched": ("{n} byte(s) written at {addr}", "تمت كتابة {n} بايت عند {addr}"),
    "till_return_note": ("Execute till Return (native): runs until the current function returns (gdb 'finish').",
                         "التنفيذ حتى الرجوع (أصلي): يشغّل حتى ترجع الدالة الحالية (أمر gdb finish)."),
    # hover
    "hover_value": ("Current value", "القيمة الحالية"),
    "hover_hex": ("hex", "سداسي عشري"),
    "hover_dec": ("unsigned", "بدون إشارة"),
    "hover_signed": ("signed", "بإشارة"),
    "hover_char": ("chars", "حروف"),
    "hover_changed": ("changed by the last step (was {old})", "تغيّر في آخر خطوة (كان {old})"),
}


def lang() -> str:
    try:
        from ... import i18n
        return "ar" if i18n.language() == "ar" else "en"
    except Exception:  # noqa: BLE001
        return "en"


def T(key: str, **values) -> str:
    en, ar = TEXTS.get(key, (key, key))
    text = ar if lang() == "ar" else en
    try:
        return text.format(**values) if values else text
    except (KeyError, IndexError):
        return text


def both(key: str, **values) -> str:
    """'English / Arabic' (explanations shown in tooltips)."""
    en, ar = TEXTS.get(key, (key, key))
    try:
        return (en.format(**values) + "\n" + ar.format(**values)) if values else en + "\n" + ar
    except (KeyError, IndexError):
        return en + "\n" + ar
