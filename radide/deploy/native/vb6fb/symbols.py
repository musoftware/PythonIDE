"""Names the generated FreeBASIC code must not reuse for VB identifiers.

FreeBASIC keywords / built-ins are always reserved.  The names declared by the headers the runtime
includes (windows.bi, commctrl.bi, crt ...) are collected once from the installed FreeBASIC (cached in
the tool folder) - a VB variable called ``Msg`` or a Sub called ``Beep`` gets a trailing underscore.
Locals may shadow global declarations in FreeBASIC, but not keywords or #define macros.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

FB_KEYWORDS = set("""
abs abstract access acos add alias allocate alpha and andalso any append as asc asin asm assert assertwarn atan2
atn base beep bin binary bit bitreset bitset bload boolean bsave byref byte byval call callocate case cast cbool
cbyte cdbl cdecl chain chdir chr cint circle class clear clng clngint close cls color com command common
condbroadcast condcreate conddestroy condsignal condwait const constructor continue cos cptr cshort csign csng
csrlin cubyte cuint culng culngint cunsg curdir cushort custom cvd cvi cvl cvlongint cvs cvshort data date
dateadd datediff datepart dateserial datevalue day deallocate declare defbyte defdbl defined defint deflng
deflongint defshort defsng defstr defubyte defuint defulongint defushort delete destructor dim dir do double
draw dylibfree dylibload dylibsymbol dynamic else elseif encoding end endif enum environ eof eqv erase erfn erl
ermn err error event exec exepath exit exp explicit export extends extern false field fileattr filecopy
filedatetime fileexists filelen fix flip for format frac fre freefile function get getjoystick getkey getmouse
gosub goto hex hibyte hiword hour if iif imageconvertrow imagecreate imagedestroy imageinfo imp implements
import inkey inp input instr instrrev int integer is isdate isredirected kill lbound lcase left len let lib line
lobyte loc local locate lock lof log long longint loop loword lpos lprint lpt lset ltrim mid minute mkd mkdir
mki mkl mklongint mks mkshort mod month monthname multikey mutexcreate mutexdestroy mutexlock mutexunlock naked
name namespace new next not now object oct offsetof on once open operator option or orelse out output overload
override paint palette pascal pcopy peek pmap point pointcoord pointer poke pos preserve preset print private
procptr property protected pset ptr public put random randomize read reallocate redim rem reset restore resume
return rgb rgba right rmdir rnd rset rtrim run sadd scope screen screencopy screencontrol screenevent
screeninfo screenglproc screenlist screenlock screenptr screenres screenset screensync screenunlock second seek
select setdate setenviron setmouse settime sgn shared shell shl short shr sin single sizeof sleep space spc sqr
static stdcall step stick stop str strig string strptr sub swap system tab tan then this threadcall threadcreate
threaddetach threadself threadwait time timer timeserial timevalue to trans trim true type typeof ubound ubyte
ucase uinteger ulong ulongint union unlock unsigned until ushort using va_arg va_first va_next val vallng valint
valuint valulng var varptr view virtual wait wbin wchr weekday weekdayname wend while whex width window
windowtitle winput with woct write wspace wstr wstring xor year zstring wchar_t base it fb
""".split())

_RX_DECL = [
    re.compile(r"^\s*#\s*define\s+(\w+)", re.I | re.M),
    re.compile(r"^\s*(?:declare\s+)?(?:function|sub)\s+(\w+)", re.I | re.M),
    re.compile(r"^\s*(?:type|union|enum)\s+(\w+)", re.I | re.M),
    re.compile(r"^\s*(?:const|dim\s+shared|extern(?:\s+import)?)\s+(\w+)", re.I | re.M),
]
_RX_ENUM = re.compile(r"^\s*enum\b.*?$(.*?)^\s*end\s+enum", re.I | re.M | re.S)
_RX_MEMBER = re.compile(r"^\s*(\w+)\s*(?:=|$|,)", re.M)


def _scan(paths) -> tuple[set, set]:
    defines, names = set(), set()
    for p in paths:
        try:
            text = Path(p).read_text(encoding="latin-1")
        except OSError:
            continue
        defines |= {m.lower() for m in _RX_DECL[0].findall(text)}
        for rx in _RX_DECL[1:]:
            names |= {m.lower() for m in rx.findall(text)}
        for body in _RX_ENUM.findall(text):
            names |= {m.lower() for m in _RX_MEMBER.findall(body)}
    return defines, names


def _runtime_files() -> list[Path]:
    return sorted((Path(__file__).parent / "rt").glob("*.bi"))


_CACHE: dict = {}


def reserved(fb_root: str | Path | None = None) -> tuple[set, set]:
    """(macros, global names): lower-case names a VB identifier must not take.

    macros  = keywords + #define names (also unusable as local names)
    names   = everything else declared globally by the included headers / the runtime
    """
    key = str(fb_root or "")
    if key in _CACHE:
        return _CACHE[key]
    defines, names = set(), set()
    if fb_root:
        inc = Path(fb_root) / "inc"
        cache = Path(fb_root) / "radide-reserved.json"
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            defines, names = set(data["defines"]), set(data["names"])
        except (OSError, ValueError, KeyError):
            if inc.is_dir():
                files = [inc / "windows.bi", *(inc / "win").glob("*.bi"), *(inc / "crt").glob("*.bi"),
                         *(inc / "crt" / "win32").glob("*.bi")]
                defines, names = _scan(files)
                try:
                    cache.write_text(json.dumps({"defines": sorted(defines), "names": sorted(names)}),
                                     encoding="utf-8")
                except OSError:
                    pass
    rd, rn = _scan(_runtime_files())
    out = (FB_KEYWORDS | defines | rd, names | rn)
    _CACHE[key] = out
    return out


__all__ = ["FB_KEYWORDS", "reserved"]
