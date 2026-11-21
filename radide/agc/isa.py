"""Apollo Guidance Computer (Block II) reference data for RAD IDE: instructions, pseudo-operations,
interpretive opcodes, special registers, I/O channels and the DSKY verbs / nouns / programs.

Everything here was written for RAD IDE from the public descriptions of the AGC (MIT Instrumentation Lab
documents, the Virtual AGC project's documentation). Each entry is (English, Arabic). The encodings are used
by the built-in assembler (radide/agc/assembler.py) and the emulator (radide/agc/cpu.py).

Operand kinds:  ``addr``  any 12-bit address (erasable 0-1777, fixed 2000-7777)
                ``e10``   erasable address (10 bits, quarter-code instructions)
                ``fixed`` fixed-memory address (TCF / BZF / BZMF)
                ``chan``  I/O channel (9 bits)
                ``dp``    double-precision erasable/fixed operand: the address is encoded +1 (DAS DXCH DCA DCS)
                ``none``  implied address (the whole word is fixed)
"""
from __future__ import annotations

# name: (extracode?, base word, operand kind)
BASIC: dict[str, tuple[bool, int, str]] = {
    "TC": (False, 0o00000, "addr"), "TCR": (False, 0o00000, "addr"),
    "CCS": (False, 0o10000, "e10"),
    "TCF": (False, 0o10000, "fixed"),
    "DAS": (False, 0o20000, "dp"),
    "LXCH": (False, 0o22000, "e10"),
    "INCR": (False, 0o24000, "e10"),
    "ADS": (False, 0o26000, "e10"),
    "CA": (False, 0o30000, "addr"), "CAF": (False, 0o30000, "addr"), "CAE": (False, 0o30000, "addr"),
    "CS": (False, 0o40000, "addr"),
    "INDEX": (False, 0o50000, "e10"), "NDX": (False, 0o50000, "e10"),
    "DXCH": (False, 0o52000, "dp"),
    "TS": (False, 0o54000, "e10"),
    "XCH": (False, 0o56000, "e10"),
    "AD": (False, 0o60000, "addr"),
    "MASK": (False, 0o70000, "addr"), "MSK": (False, 0o70000, "addr"),
}
EXTRACODES: dict[str, tuple[bool, int, str]] = {
    "READ": (True, 0o00000, "chan"), "WRITE": (True, 0o01000, "chan"), "RAND": (True, 0o02000, "chan"),
    "WAND": (True, 0o03000, "chan"), "ROR": (True, 0o04000, "chan"), "WOR": (True, 0o05000, "chan"),
    "RXOR": (True, 0o06000, "chan"), "EDRUPT": (True, 0o07000, "chan"),
    "DV": (True, 0o10000, "e10"), "BZF": (True, 0o10000, "fixed"),
    "MSU": (True, 0o20000, "e10"), "QXCH": (True, 0o22000, "e10"), "AUG": (True, 0o24000, "e10"),
    "DIM": (True, 0o26000, "e10"),
    "DCA": (True, 0o30000, "dp"), "DCS": (True, 0o40000, "dp"),
    "SU": (True, 0o60000, "e10"), "BZMF": (True, 0o60000, "fixed"),
    "MP": (True, 0o70000, "addr"),
}
# implied-address instructions: name -> (extracode?, full word)
IMPLIED: dict[str, tuple[bool, int]] = {
    "XXALQ": (False, 0o00000), "XLQ": (False, 0o00001), "RETURN": (False, 0o00002), "RELINT": (False, 0o00003),
    "INHINT": (False, 0o00004), "EXTEND": (False, 0o00006), "DDOUBL": (False, 0o20001), "ZL": (False, 0o22007),
    "COM": (False, 0o40000), "DOUBLE": (False, 0o60000), "OVSK": (False, 0o54000), "TCAA": (False, 0o54005),
    "DTCF": (False, 0o52005), "DTCB": (False, 0o52006), "RESUME": (False, 0o50017), "NOOP": (False, 0o30000),
    "DCOM": (True, 0o40001), "ZQ": (True, 0o22007), "SQUARE": (True, 0o70000),
}

INSTRUCTION_DOCS: dict[str, tuple[str, str]] = {
    "TC": ("TC K - Transfer Control: Q = return address, jump to K (a subroutine call). Return with RETURN "
           "(TC Q).", "نقل التحكم: يحفظ عنوان الرجوع في Q ويقفز إلى K (استدعاء إجراء). الرجوع بـ RETURN."),
    "TCR": ("TCR K - same as TC.", "مثل TC."),
    "CCS": ("CCS K - Count, Compare and Skip: A = |K| - 1 (or 0) and branch four ways: K > 0 next "
            "instruction, +0 skip 1, < 0 skip 2, -0 skip 3. The classic loop counter.",
            "عدّ ومقارنة وقفز: A = |K| - 1 ثم تفرّع رباعي: موجب ← التالية، +0 تخطّي 1، سالب تخطّي 2، -0 تخطّي 3."),
    "TCF": ("TCF K - Transfer Control to Fixed: jump to K (Q unchanged).", "قفز إلى K في الذاكرة الثابتة دون "
            "تغيير Q."),
    "DAS": ("DAS K - Double Add to Storage: (K, K+1) = (K, K+1) + (A, L); then A = overflow (+1 / -1 / 0), "
            "L = +0.", "جمع مزدوج إلى الذاكرة: (K,K+1) += (A,L) ثم A = الفيضان و L = 0."),
    "LXCH": ("LXCH K - exchange L and K.", "تبديل L مع K."),
    "INCR": ("INCR K - K = K + 1.", "زيادة K بمقدار 1."),
    "ADS": ("ADS K - Add to Storage: A = A + K and K = A (overflow corrected).", "جمع إلى الذاكرة: A = A + K "
            "ثم K = A."),
    "CA": ("CA K - Clear and Add: A = K. CAF (fixed) and CAE (erasable) are the same instruction.",
           "تحميل: A = K. ومثلها CAF للثابتة و CAE للمتغيرة."),
    "CAF": ("CAF K - A = K (K in fixed memory, a constant).", "تحميل ثابت من الذاكرة الثابتة إلى A."),
    "CAE": ("CAE K - A = K (K in erasable memory).", "تحميل من الذاكرة المتغيرة إلى A."),
    "CS": ("CS K - Clear and Subtract: A = -K (ones' complement).", "A = سالب K (المتمم الأحادي)."),
    "INDEX": ("INDEX K - add K to the next instruction word before it runs (table lookups, computed jumps). "
              "INDEX 17 is RESUME.", "إضافة قيمة K إلى كلمة التعليمة التالية قبل تنفيذها (جداول وقفزات "
              "محسوبة)."),
    "NDX": ("NDX K - same as INDEX.", "مثل INDEX."),
    "DXCH": ("DXCH K - exchange (A, L) with (K, K+1). DTCB / DTCF are DXCH Z / DXCH FB.",
             "تبديل الزوج (A,L) مع (K,K+1)."),
    "TS": ("TS K - Transfer to Storage: K = A. If A overflowed, K gets the corrected value, A = +1 / -1 and "
           "the next instruction is skipped.", "تخزين A في K. عند الفيضان تُخزَّن القيمة المصححة و A = ±1 "
           "وتُتخطّى التعليمة التالية."),
    "XCH": ("XCH K - exchange A and K.", "تبديل A مع K."),
    "AD": ("AD K - A = A + K (ones' complement, 16-bit A keeps the overflow).", "جمع: A = A + K (يحتفظ A "
           "بالفيضان)."),
    "MASK": ("MASK K - A = A AND K.", "عملية AND: A = A و K."),
    "MSK": ("MSK K - same as MASK.", "مثل MASK."),
    "READ": ("READ ch - A = channel ch (after EXTEND).", "قراءة القناة إلى A (بعد EXTEND)."),
    "WRITE": ("WRITE ch - channel ch = A. Channel 10 drives the DSKY digits, channel 11 its lamps.",
              "كتابة A إلى القناة. القناة 10 لأرقام DSKY و 11 لمصابيحها."),
    "RAND": ("RAND ch - A = A AND channel.", "A = A و القناة."),
    "WAND": ("WAND ch - A = channel = A AND channel.", "A = القناة = A و القناة."),
    "ROR": ("ROR ch - A = A OR channel.", "A = A أو القناة."),
    "WOR": ("WOR ch - A = channel = A OR channel.", "A = القناة = A أو القناة."),
    "RXOR": ("RXOR ch - A = A XOR channel.", "A = A XOR القناة."),
    "EDRUPT": ("EDRUPT K - for machine checkout only (enters an interrupt).", "لاختبار الجهاز فقط."),
    "DV": ("DV K - Divide: (A, L) / K -> A = quotient, L = remainder (fractions; |K| must exceed |A|).",
           "قسمة: (A,L) / K ← A = الناتج و L = الباقي."),
    "BZF": ("BZF K - Branch to K if A is zero (+0 or -0).", "قفز إلى K إذا كان A صفراً."),
    "MSU": ("MSU K - Modular Subtract: A = K - A in two's complement (CDU angles).",
            "طرح نمطي بالمتمم الثنائي (زوايا CDU)."),
    "QXCH": ("QXCH K - exchange Q and K.", "تبديل Q مع K."),
    "AUG": ("AUG K - augment: add 1 to the magnitude of K.", "زيادة مقدار K بواحد."),
    "DIM": ("DIM K - diminish: subtract 1 from the magnitude of K (zero stays).", "إنقاص مقدار K بواحد."),
    "DCA": ("DCA K - (A, L) = (K, K+1).", "تحميل مزدوج: (A,L) = (K,K+1)."),
    "DCS": ("DCS K - (A, L) = -(K, K+1).", "تحميل مزدوج سالب."),
    "SU": ("SU K - A = A - K.", "طرح: A = A - K."),
    "BZMF": ("BZMF K - Branch to K if A is zero or negative.", "قفز إذا كان A صفراً أو سالباً."),
    "MP": ("MP K - Multiply: (A, L) = A x K (double-precision product).", "ضرب: (A,L) = A × K."),
    "XXALQ": ("XXALQ - TC A: jump to the address in A.", "قفز إلى العنوان الموجود في A."),
    "XLQ": ("XLQ - TC L: jump to the address in L.", "قفز إلى العنوان الموجود في L."),
    "RETURN": ("RETURN - TC Q: return from a subroutine.", "رجوع من الإجراء (TC Q)."),
    "RELINT": ("RELINT - allow interrupts again.", "السماح بالمقاطعات."),
    "INHINT": ("INHINT - inhibit interrupts.", "منع المقاطعات."),
    "EXTEND": ("EXTEND - the next instruction is an extracode (READ, DCA, MP, DV, SU, BZF ...).",
               "التعليمة التالية تعليمة موسَّعة (READ و DCA و MP ...)."),
    "DDOUBL": ("DDOUBL - DAS A: double (A, L).", "مضاعفة الزوج (A,L)."),
    "ZL": ("ZL - LXCH 7: L = 0.", "تصفير L."),
    "ZQ": ("ZQ - QXCH 7: Q = 0.", "تصفير Q."),
    "COM": ("COM - CS A: complement A.", "متمم A."),
    "DCOM": ("DCOM - DCS A: complement (A, L).", "متمم الزوج (A,L)."),
    "DOUBLE": ("DOUBLE - AD A: A = 2A.", "مضاعفة A."),
    "SQUARE": ("SQUARE - MP A: (A, L) = A x A.", "تربيع A."),
    "OVSK": ("OVSK - TS A: skip the next instruction if A overflowed.", "تخطّي التالية عند فيضان A."),
    "TCAA": ("TCAA - TS Z: jump to the address in A.", "قفز إلى العنوان في A."),
    "DTCF": ("DTCF - DXCH FB: double transfer control, switching the fixed bank.", "قفز مع تبديل البنك الثابت."),
    "DTCB": ("DTCB - DXCH Z: double transfer control, switching both banks (BB).", "قفز مع تبديل البنكين."),
    "RESUME": ("RESUME - return from an interrupt (Z = ZRUPT, runs BRUPT).", "الرجوع من المقاطعة."),
    "NOOP": ("NOOP - no operation.", "لا عملية."),
}

PSEUDO_DOCS: dict[str, tuple[str, str]] = {
    "SETLOC": ("SETLOC addr - continue assembling at addr (octal 4000-7777 fixed-fixed, 10000+ bank n at "
               "n x 2000, below 4000 erasable).", "متابعة التجميع عند العنوان المعطى."),
    "BANK": ("BANK n - continue in fixed-memory bank n (octal), after what is already there.",
             "المتابعة في البنك الثابت n."),
    "BLOCK": ("BLOCK n - continue in fixed-fixed bank n (2 or 3).", "المتابعة في البنك الثابت الثابت n."),
    "EBANK=": ("EBANK= sym - tell the assembler which erasable bank EB selects from here on.",
               "إخبار المجمِّع بالبنك المتغير المختار."),
    "SBANK=": ("SBANK= sym - the superbank assumed from here on.", "البنك الفائق المفترض."),
    "ERASE": ("name ERASE [+n] - reserve 1 (or n+1) erasable words.", "حجز كلمة (أو n+1 كلمة) في الذاكرة "
              "المتغيرة."),
    "EQUALS": ("name EQUALS expr - give a name to an address or number (also written =).",
               "تسمية عنوان أو رقم (أو =)."),
    "=": ("name = expr - same as EQUALS.", "مثل EQUALS."),
    "OCT": ("OCT n - one word, octal.", "كلمة بالنظام الثماني."),
    "DEC": ("DEC n [Bs] - one word, decimal: an integer, or a fraction (0.5 -> 20000 octal); B-s scales.",
            "كلمة عشرية: عدد صحيح أو كسر."),
    "2DEC": ("2DEC n [Bs] - a double-precision decimal constant (two words).", "ثابت عشري مزدوج الدقة."),
    "CADR": ("CADR sym - complete address of sym (bank and offset).", "العنوان الكامل (البنك والإزاحة)."),
    "FCADR": ("FCADR sym - complete fixed address.", "العنوان الثابت الكامل."),
    "ECADR": ("ECADR sym - complete erasable address.", "العنوان المتغير الكامل."),
    "GENADR": ("GENADR sym - the 12-bit address an instruction would use.", "العنوان ذو 12 بت."),
    "ADRES": ("ADRES sym - 12-bit address (like GENADR).", "عنوان 12 بت."),
    "REMADR": ("REMADR sym - 12-bit address of a remote (other-bank) location.", "عنوان بعيد."),
    "BBCON": ("BBCON sym - BB register value (fixed bank + current EBANK) for sym.", "قيمة BB للرمز."),
    "2CADR": ("2CADR sym - GENADR then BBCON (two words, for DTCB).", "كلمتان: GENADR ثم BBCON."),
    "2FCADR": ("2FCADR sym - FCADR as two words.", "FCADR في كلمتين."),
    "COUNT": ("COUNT - bank word-count bookkeeping (ignored by the built-in assembler).", "تتبع عدد الكلمات."),
    "COUNT*": ("COUNT* - bank word-count bookkeeping (ignored by the built-in assembler).", "تتبع عدد الكلمات."),
    "BNKSUM": ("BNKSUM n - bank checksum (yaYUL only).", "مجموع تحقق البنك."),
    "CHECK=": ("CHECK= sym - assert that a name has the current address (ignored).", "تحقق من العنوان."),
    "MM": ("MM n - major mode number (decimal).", "رقم البرنامج الرئيسي."),
    "VN": ("VN vvnn - verb and noun packed in one word.", "فعل واسم في كلمة."),
}

INTERPRETIVE_DOCS: dict[str, tuple[str, str]] = {
    "VLOAD": ("VLOAD v - load the vector accumulator (MPAC) with the 3-component vector v.", "تحميل متجه."),
    "DLOAD": ("DLOAD x - load MPAC with the double-precision number x.", "تحميل عدد مزدوج الدقة."),
    "TLOAD": ("TLOAD x - load a triple-precision number.", "تحميل عدد ثلاثي الدقة."),
    "SLOAD": ("SLOAD x - load a single-precision number.", "تحميل عدد أحادي الدقة."),
    "STORE": ("STORE x - store MPAC in x.", "تخزين المركم في x."),
    "STODL": ("STODL x, y - store MPAC in x then DLOAD y.", "تخزين ثم تحميل مزدوج."),
    "STOVL": ("STOVL x, y - store MPAC in x then VLOAD y.", "تخزين ثم تحميل متجه."),
    "STCALL": ("STCALL x, routine - store then CALL.", "تخزين ثم استدعاء."),
    "DAD": ("DAD x - double-precision add.", "جمع مزدوج."), "DSU": ("DSU x - double subtract.", "طرح مزدوج."),
    "BDSU": ("BDSU x - MPAC = x - MPAC.", "طرح معكوس."),
    "DMP": ("DMP x - double multiply.", "ضرب مزدوج."), "DMPR": ("DMPR x - double multiply and round.", "ضرب وتقريب."),
    "DDV": ("DDV x - double divide (MPAC / x).", "قسمة مزدوجة."), "BDDV": ("BDDV x - x / MPAC.", "قسمة معكوسة."),
    "DSQ": ("DSQ - square MPAC.", "تربيع."), "SQRT": ("SQRT - square root.", "جذر تربيعي."),
    "SIN": ("SIN / SINE - sine of MPAC (revolutions).", "الجيب."), "COS": ("COS / COSINE - cosine.", "جيب التمام."),
    "ASIN": ("ASIN / ARCSIN - arc sine.", "الجيب العكسي."), "ACOS": ("ACOS / ARCCOS - arc cosine.", "جيب التمام العكسي."),
    "ABS": ("ABS - absolute value.", "القيمة المطلقة."), "DCOMP": ("DCOMP - negate MPAC.", "عكس الإشارة."),
    "VAD": ("VAD v - vector add.", "جمع متجهات."), "VSU": ("VSU v - vector subtract.", "طرح متجهات."),
    "BVSU": ("BVSU v - v - MPAC.", "طرح متجهات معكوس."),
    "DOT": ("DOT v - dot product.", "الضرب القياسي."), "VXV": ("VXV v - cross product.", "الضرب الاتجاهي."),
    "VXSC": ("VXSC x - vector times scalar.", "متجه × عدد."), "V/SC": ("V/SC x - vector / scalar.", "متجه ÷ عدد."),
    "UNIT": ("UNIT - unit vector of MPAC.", "متجه الوحدة."), "ABVAL": ("ABVAL - length of the vector.", "طول المتجه."),
    "VSQ": ("VSQ - square of the vector length.", "مربع طول المتجه."),
    "MXV": ("MXV m - matrix x vector.", "مصفوفة × متجه."), "VXM": ("VXM m - vector x matrix.", "متجه × مصفوفة."),
    "VCOMP": ("VCOMP - negate the vector.", "عكس المتجه."), "VDEF": ("VDEF - make a vector from 3 numbers.", "تكوين متجه."),
    "VPROJ": ("VPROJ v - projection.", "إسقاط."),
    "PUSH": ("PUSH - push MPAC on the push-down list.", "دفع إلى القائمة."),
    "PDDL": ("PDDL x - push, then DLOAD x.", "دفع ثم تحميل."), "PDVL": ("PDVL v - push, then VLOAD v.", "دفع ثم تحميل متجه."),
    "SETPD": ("SETPD n - set the push-down pointer.", "ضبط مؤشر القائمة."),
    "CALL": ("CALL routine - interpretive subroutine call (QPRET = return).", "استدعاء تفسيري."),
    "GOTO": ("GOTO label - interpretive jump.", "قفز تفسيري."), "CGOTO": ("CGOTO - computed GOTO.", "قفز محسوب."),
    "RVQ": ("RVQ - return from an interpretive subroutine.", "رجوع تفسيري."),
    "STQ": ("STQ x - store the return address.", "تخزين عنوان الرجوع."),
    "EXIT": ("EXIT - leave interpretive mode, continue with basic instructions.", "الخروج من النمط التفسيري."),
    "RTB": ("RTB routine - Return To Basic: run a basic-language routine.", "تشغيل روتين أساسي."),
    "BPL": ("BPL label - branch if MPAC is positive.", "قفز إذا موجب."), "BMN": ("BMN label - branch if negative.", "قفز إذا سالب."),
    "BZE": ("BZE label - branch if zero.", "قفز إذا صفر."), "BHIZ": ("BHIZ label - branch if the high word is zero.", "قفز إذا الكلمة العليا صفر."),
    "BOV": ("BOV label - branch on overflow (and clear it).", "قفز عند الفيضان."),
    "BOVB": ("BOVB label - branch on overflow to a basic routine.", "قفز عند الفيضان إلى روتين أساسي."),
    "SET": ("SET flag - set a flag bit.", "رفع علم."), "CLEAR": ("CLEAR flag - clear a flag bit.", "إنزال علم."),
    "INVERT": ("INVERT flag - invert a flag bit.", "عكس علم."),
    "BON": ("BON flag, label - branch if the flag is on.", "قفز إذا العلم مرفوع."),
    "BOFF": ("BOFF flag, label - branch if the flag is off.", "قفز إذا العلم منزل."),
    "SL": ("SL n - shift left.", "إزاحة لليسار."), "SR": ("SR n - shift right (interpretive) / SR register (basic).", "إزاحة لليمين."),
    "VSL": ("VSL n - vector shift left.", "إزاحة متجه لليسار."), "VSR": ("VSR n - vector shift right.", "إزاحة متجه لليمين."),
    "NORM": ("NORM x - normalize MPAC (shift count to x).", "تطبيع."), "ROUND": ("ROUND - round to double precision.", "تقريب."),
    "SIGN": ("SIGN x - negate if x is negative.", "الإشارة."), "SSP": ("SSP x, n - set single precision.", "تعيين أحادي."),
    "AXT,1": ("AXT,1 n - set index register X1.", "ضبط المسجل الفهرسي X1."),
    "AXT,2": ("AXT,2 n - set index register X2.", "ضبط المسجل الفهرسي X2."),
    "TIX,1": ("TIX,1 label - decrement X1 and loop.", "حلقة بالمسجل X1."),
    "TIX,2": ("TIX,2 label - decrement X2 and loop.", "حلقة بالمسجل X2."),
    "LXA,1": ("LXA,1 x - load X1.", "تحميل X1."), "SXA,1": ("SXA,1 x - store X1.", "تخزين X1."),
    "INCR,1": ("INCR,1 n - add to X1.", "زيادة X1."), "XCHX,1": ("XCHX,1 x - exchange X1.", "تبديل X1."),
    "STADR": ("STADR - the next store address is pushed (special store form).", "صيغة تخزين خاصة."),
    "ITA": ("ITA x - store the return address (Interpretive To Address).", "تخزين عنوان الرجوع."),
}
INTERPRETIVE_EXTRA = """ABVAL ACOS ARCCOS ARCSIN ASIN AXC,1 AXC,2 BOFCLR BOFINV BOFSET BONCLR BONINV BONSET CCALL CCLEAR
    CLR CLRGO COSINE DMPR INCR,2 INVGO LXA,2 LXC,1 LXC,2 SETGO SINE SL1 SL2 SL3 SL4 SL1R SL2R SL3R SL4R SLR SR1 SR2
    SR3 SR4 SR1R SR2R SR3R SR4R SRR SXA,2 TAD VSL1 VSL2 VSL3 VSL4 VSL5 VSL6 VSL7 VSL8 VSR1 VSR2 VSR3 VSR4 VSR5 VSR6
    VSR7 VSR8 XAD,1 XAD,2 XCHX,2 XSU,1 XSU,2""".split()
INTERPRETIVE = set(INTERPRETIVE_DOCS) | set(INTERPRETIVE_EXTRA)

# special erasable registers (octal address)
REGISTERS: dict[str, int] = {
    "A": 0, "L": 1, "Q": 2, "EB": 3, "FB": 4, "Z": 5, "BB": 6, "ZERO": 7, "ARUPT": 0o10, "LRUPT": 0o11,
    "QRUPT": 0o12, "ZRUPT": 0o15, "BBRUPT": 0o16, "BRUPT": 0o17, "CYR": 0o20, "SR": 0o21, "CYL": 0o22,
    "EDOP": 0o23, "TIME2": 0o24, "TIME1": 0o25, "TIME3": 0o26, "TIME4": 0o27, "TIME5": 0o30, "TIME6": 0o31,
    "CDUX": 0o32, "CDUY": 0o33, "CDUZ": 0o34, "OPTY": 0o35, "OPTX": 0o36, "PIPAX": 0o37, "PIPAY": 0o40,
    "PIPAZ": 0o41, "INLINK": 0o45, "OUTLINK": 0o57,
}
REGISTER_DOCS: dict[str, tuple[str, str]] = {
    "A": ("A (0) - the accumulator: 16 bits, keeps an overflow.", "المركم A: 16 بت ويحتفظ بالفيضان."),
    "L": ("L (1) - low-order accumulator (double precision, MP / DV results).", "المركم السفلي L."),
    "Q": ("Q (2) - return address register (TC puts the return address here).", "مسجل عنوان الرجوع Q."),
    "EB": ("EB (3) - erasable bank register (bits 11-9 choose E0-E7 for 1400-1777).", "مسجل البنك المتغير."),
    "FB": ("FB (4) - fixed bank register (bits 15-11 choose the bank seen at 2000-3777).", "مسجل البنك الثابت."),
    "Z": ("Z (5) - program counter (12 bits).", "عداد البرنامج Z."),
    "BB": ("BB (6) - both banks: FB and EB in one word.", "البنكان معاً."),
    "ZERO": ("ZERO (7) - always reads 0.", "يقرأ صفراً دائماً."),
    "ARUPT": ("ARUPT (10) - interrupt save area for A.", "حفظ A أثناء المقاطعة."),
    "LRUPT": ("LRUPT (11) - interrupt save area for L.", "حفظ L أثناء المقاطعة."),
    "QRUPT": ("QRUPT (12) - interrupt save area for Q.", "حفظ Q أثناء المقاطعة."),
    "ZRUPT": ("ZRUPT (15) - where the interrupted program continues.", "عنوان الرجوع من المقاطعة."),
    "BBRUPT": ("BBRUPT (16) - interrupt save area for BB.", "حفظ BB."),
    "BRUPT": ("BRUPT (17) - the interrupted instruction word (RESUME runs it).", "كلمة التعليمة المقطوعة."),
    "CYR": ("CYR (20) - cycle right: a value stored here comes back rotated right one bit.", "تدوير لليمين."),
    "SR": ("SR (21) - shift right one bit (sign kept).", "إزاحة لليمين."),
    "CYL": ("CYL (22) - cycle left one bit.", "تدوير لليسار."),
    "EDOP": ("EDOP (23) - shift right 7 bits (interpreter opcode extraction).", "إزاحة 7 بتات لليمين."),
    "TIME1": ("TIME1 (25) - counts centiseconds (overflows into TIME2).", "عداد أجزاء المئة من الثانية."),
    "TIME2": ("TIME2 (24) - high part of the mission clock.", "الجزء الأعلى من الساعة."),
    "TIME3": ("TIME3 (26) - centisecond counter; overflow causes T3RUPT (the WAITLIST timer).",
              "عداد يسبب المقاطعة T3RUPT عند الفيضان."),
    "TIME4": ("TIME4 (27) - centisecond counter; overflow causes T4RUPT (DSKY / IMU housekeeping).",
              "عداد يسبب T4RUPT."),
    "TIME5": ("TIME5 (30) - centisecond counter; overflow causes T5RUPT (digital autopilot).", "عداد يسبب T5RUPT."),
    "TIME6": ("TIME6 (31) - 1/1600 s down-counter for jet timing (T6RUPT).", "عداد T6RUPT."),
}

CHANNEL_DOCS: dict[int, tuple[str, str]] = {
    1: ("Channel 1 = the L register.", "القناة 1 هي المسجل L."),
    2: ("Channel 2 = the Q register.", "القناة 2 هي المسجل Q."),
    0o7: ("Channel 7 - superbank bits (FEB) for fixed banks 40-43.", "بتات البنك الفائق."),
    0o10: ("Channel 10 - DSKY relay words: bits 15-12 select the word, bit 11 a sign, bits 10-6 and 5-1 two "
           "digit codes.", "كلمات مرحلات DSKY: الأرقام والإشارات."),
    0o11: ("Channel 11 - DSKY lamps: bit 2 COMP ACTY, 3 UPLINK ACTY, 4 TEMP, 5 KEY REL, 6 VERB/NOUN flash, "
           "7 OPR ERR.", "مصابيح DSKY."),
    0o12: ("Channel 12 - IMU / CDU / optics control bits.", "تحكم IMU و CDU."),
    0o13: ("Channel 13 - radar, uplink and T6 control bits.", "تحكم الرادار و T6."),
    0o14: ("Channel 14 - counter drive bits (gyro, CDU commands).", "تشغيل العدادات."),
    0o15: ("Channel 15 - main DSKY keyboard (5-bit key code; KEYRUPT1).", "لوحة مفاتيح DSKY الرئيسية."),
    0o16: ("Channel 16 - navigation DSKY keyboard / mark buttons (KEYRUPT2).", "لوحة الملاحة وأزرار العلامة."),
    0o30: ("Channel 30 - input discretes (inverted): IMU, stage, ...", "مدخلات منفصلة."),
    0o31: ("Channel 31 - hand controller inputs (inverted).", "مدخلات ذراع التحكم."),
    0o32: ("Channel 32 - input discretes; bit 14 = PRO key (0 while pressed).", "مدخلات؛ البت 14 زر PRO."),
    0o33: ("Channel 33 - input discretes (radar, uplink, alarms).", "مدخلات منفصلة."),
    0o34: ("Channel 34 - downlink word 1.", "كلمة الإرسال الأولى."),
    0o35: ("Channel 35 - downlink word 2.", "كلمة الإرسال الثانية."),
    0o163: ("Channel 163 - Virtual AGC's DSKY lamp channel (AGC WARNING, TEMP, KEY REL, V/N flash, OPR ERR, "
            "RESTART, STBY).", "قناة مصابيح DSKY في Virtual AGC."),
}

# interrupt vectors (fixed-fixed bank 2): index -> (name, address)
INTERRUPTS = [("GOJAM", 0o4000), ("T6RUPT", 0o4004), ("T5RUPT", 0o4010), ("T3RUPT", 0o4014), ("T4RUPT", 0o4020),
              ("KEYRUPT1", 0o4024), ("KEYRUPT2", 0o4030), ("UPRUPT", 0o4034), ("DOWNRUPT", 0o4040),
              ("RADARUPT", 0o4044), ("HANDRUPT", 0o4050)]

# ----------------------------------------------------------------------------------------- DSKY
# key codes on channel 15 (octal) - PRO is channel 32 bit 14
KEY_CODES: dict[str, int] = {"0": 0o20, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 0o10,
                             "9": 0o11, "VERB": 0o21, "RSET": 0o22, "KEY REL": 0o31, "+": 0o32, "-": 0o33,
                             "ENTR": 0o34, "CLR": 0o36, "NOUN": 0o37}
# 5-bit digit codes of the DSKY relay words
DIGIT_CODES: dict[int, str] = {0: " ", 0o25: "0", 0o03: "1", 0o31: "2", 0o33: "3", 0o17: "4", 0o36: "5",
                               0o34: "6", 0o23: "7", 0o35: "8", 0o37: "9"}
DIGIT_OF: dict[str, int] = {v: k for k, v in DIGIT_CODES.items()}

VERBS: dict[int, tuple[str, str]] = {
    1: ("Display octal component 1 in R1", "عرض المكوّن 1 بالثماني في R1"),
    2: ("Display octal component 2 in R1", "عرض المكوّن 2 بالثماني في R1"),
    3: ("Display octal component 3 in R1", "عرض المكوّن 3 بالثماني في R1"),
    4: ("Display octal components 1, 2 in R1, R2", "عرض المكوّنين 1 و 2 بالثماني"),
    5: ("Display octal components 1, 2, 3 in R1, R2, R3", "عرض المكوّنات 1 و 2 و 3 بالثماني"),
    6: ("Display decimal in R1 or R1, R2 or R1, R2, R3", "عرض عشري"),
    11: ("Monitor octal component 1 in R1 (updated each second)", "مراقبة المكوّن 1 بالثماني"),
    15: ("Monitor octal components 1, 2, 3", "مراقبة المكوّنات 1 و 2 و 3 بالثماني"),
    16: ("Monitor decimal (e.g. V16 N65 = the AGC clock)", "مراقبة عشرية (مثل V16 N65 ساعة الحاسوب)"),
    21: ("Load component 1 into R1", "إدخال المكوّن 1 في R1"),
    22: ("Load component 2 into R2", "إدخال المكوّن 2 في R2"),
    23: ("Load component 3 into R3", "إدخال المكوّن 3 في R3"),
    24: ("Load components 1, 2 into R1, R2", "إدخال المكوّنين 1 و 2"),
    25: ("Load components 1, 2, 3 into R1, R2, R3", "إدخال المكوّنات 1 و 2 و 3"),
    27: ("Display fixed memory", "عرض الذاكرة الثابتة"),
    30: ("Request executive", "طلب المنفّذ"),
    31: ("Request waitlist", "طلب قائمة الانتظار"),
    32: ("Recycle program", "إعادة تشغيل البرنامج"),
    33: ("Proceed without DSKY inputs", "المتابعة دون إدخال"),
    34: ("Terminate function", "إنهاء الوظيفة"),
    35: ("Test lights (all digits show 8, every lamp on)", "اختبار المصابيح (كل الأرقام 8)"),
    36: ("Request fresh start", "طلب بداية جديدة"),
    37: ("Change program (major mode): V37 E nn E", "تغيير البرنامج: V37 E nn E"),
    40: ("Zero CDUs", "تصفير CDU"), 41: ("Coarse align", "محاذاة خشنة"), 42: ("Fine align IMU", "محاذاة دقيقة"),
    48: ("Request DAP data load (R03)", "إدخال بيانات الطيار الآلي"),
    49: ("Crew-defined maneuver (R62)", "مناورة يحددها الطاقم"),
    50: ("Please perform (crew action requested)", "رجاءً نفِّذ"),
    82: ("Request orbit parameter display (R30)", "عرض معاملات المدار"),
    83: ("Request rendezvous parameter display (R31)", "عرض معاملات الالتقاء"),
    99: ("Please enable engine ignition", "رجاءً اسمح بإشعال المحرك"),
}
NOUNS: dict[int, tuple[str, str]] = {
    1: ("Specify address (fractional)", "تحديد عنوان (كسري)"), 2: ("Specify address (whole)", "تحديد عنوان (صحيح)"),
    6: ("Option code", "رمز الخيار"), 9: ("Alarm codes", "رموز الإنذار"), 10: ("Channel to be specified", "تحديد قناة"),
    15: ("Increment address", "زيادة العنوان"), 16: ("Time of event", "زمن الحدث"),
    17: ("Astronaut total attitude", "الوضع الكلي"), 18: ("Auto maneuver ball angles", "زوايا المناورة"),
    20: ("Present ICDU angles", "زوايا ICDU الحالية"), 22: ("New ICDU angles", "زوايا ICDU الجديدة"),
    25: ("Checklist", "قائمة التحقق"), 26: ("Priority/delay, address, BBCON", "الأولوية والعنوان و BBCON"),
    33: ("Time of ignition", "زمن الإشعال"), 34: ("Time of event", "زمن الحدث"),
    36: ("Time of AGC clock (hours, minutes, seconds)", "زمن ساعة الحاسوب"),
    40: ("Time from ignition/cutoff, VG, accumulated delta V", "الزمن من الإشعال و VG و ΔV"),
    42: ("Apogee, perigee, delta V", "الأوج والحضيض و ΔV"), 43: ("Latitude, longitude, altitude", "خط العرض والطول والارتفاع"),
    44: ("Apogee, perigee, time to free fall", "الأوج والحضيض وزمن السقوط الحر"),
    62: ("Inertial velocity, altitude rate, altitude", "السرعة القصورية ومعدل الارتفاع والارتفاع"),
    65: ("Sampled AGC time (hours, minutes, seconds)", "زمن الحاسوب المأخوذ"),
    80: ("Data indicator, omega, time", "مؤشر البيانات"), 81: ("Delta V (local vertical)", "ΔV المحلية"),
    85: ("VG (body axes)", "VG في محاور المركبة"),
}
PROGRAMS: dict[int, tuple[str, str]] = {
    0: ("P00 - CMC/LGC idling", "P00 - الخمول"), 1: ("P01 - Prelaunch initialization", "P01 - تهيئة ما قبل الإطلاق"),
    11: ("P11 - Earth orbit insertion monitor (CM)", "P11 - مراقبة الدخول إلى المدار"),
    15: ("P15 - TLI initiate/cutoff (CM)", "P15 - الحقن نحو القمر"),
    20: ("P20 - Rendezvous navigation", "P20 - ملاحة الالتقاء"), 21: ("P21 - Ground track determination", "P21 - المسار الأرضي"),
    22: ("P22 - Orbital navigation", "P22 - الملاحة المدارية"), 23: ("P23 - Cislunar midcourse navigation (CM)", "P23 - ملاحة منتصف الطريق"),
    30: ("P30 - External delta V", "P30 - ΔV خارجي"), 37: ("P37 - Return to Earth (CM)", "P37 - العودة إلى الأرض"),
    40: ("P40 - SPS thrusting (CM) / DPS thrusting (LM)", "P40 - دفع المحرك"), 41: ("P41 - RCS thrusting", "P41 - دفع RCS"),
    47: ("P47 - Thrust monitor", "P47 - مراقبة الدفع"), 51: ("P51 - IMU orientation determination", "P51 - تحديد اتجاه IMU"),
    52: ("P52 - IMU realign", "P52 - إعادة محاذاة IMU"),
    61: ("P61 - Entry preparation (CM)", "P61 - التحضير للدخول"),
    63: ("P63 - Braking phase (LM landing) / Entry initialization (CM)", "P63 - مرحلة الكبح (الهبوط)"),
    64: ("P64 - Approach phase (LM) / post-0.05g (CM)", "P64 - مرحلة الاقتراب"),
    66: ("P66 - Rate of descent (LM manual landing)", "P66 - معدل الهبوط اليدوي"),
}


def doc_for(word: str) -> tuple[str, str] | None:
    """(English, Arabic) description of an instruction, pseudo-op, interpretive opcode or register."""
    w = word.upper()
    for table in (INSTRUCTION_DOCS, PSEUDO_DOCS, REGISTER_DOCS, INTERPRETIVE_DOCS):
        if w in table:
            return table[w]
    if w in INTERPRETIVE:
        base = w.rstrip("0123456789R").rstrip(",")
        if base in INTERPRETIVE_DOCS:
            return INTERPRETIVE_DOCS[base]
        return (f"{w} - interpretive opcode (assembled by yaYUL).", "تعليمة تفسيرية (يجمّعها yaYUL).")
    return None


def all_opcodes() -> set[str]:
    return set(BASIC) | set(EXTRACODES) | set(IMPLIED)


PSEUDO_OPS = set(PSEUDO_DOCS) | {"2CADR", "2FCADR", "2BCADR", "DEC*", "2DEC*", "XCADR", "NV", "DNCHAN", "DNPTR",
                                 "1DNADR", "2DNADR", "3DNADR", "4DNADR", "5DNADR", "6DNADR", "BBCON*", "CADR*",
                                 "OCTAL", "SECSIZ", "SUBRO", "MEMORY", "LOC", "EBANK", "=MINUS", "=ECADR"}
