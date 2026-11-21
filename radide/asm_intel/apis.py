"""Win32 API and C runtime functions commonly called from assembly (signatures + short original notes).

Format: ``name | dll | header | return type | parameters | description``.  ``header`` builds the Microsoft
Learn link (``.../api/<header>/nf-<header>-<name>``); CRT functions (dll ``crt``) link to the C runtime
reference. ``A``/``W`` pairs: only the ``A`` form is listed - the ``W`` form is derived (LPCSTR -> LPCWSTR).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

WIN32_URL = "https://learn.microsoft.com/en-us/windows/win32/api/{header}/nf-{header}-{lname}"
CRT_URL = "https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/{lname}"
X64_ABI_URL = "https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention"
SYSV_ABI_URL = "https://gitlab.com/x86-psABIs/x86-64-ABI"


@dataclass
class Api:
    name: str
    dll: str
    header: str
    ret: str
    params: list[tuple[str, str]]      # (type, name)
    doc: str
    variadic: bool = False

    @property
    def is_crt(self) -> bool:
        return self.dll == "crt"

    def url(self) -> str:
        if self.is_crt:
            return CRT_URL.format(lname=self.name.lower().lstrip("_"))
        return WIN32_URL.format(header=self.header, lname=self.name.lower())

    def signature(self) -> str:
        ps = [f"{t} {n}".strip() for t, n in self.params]
        if self.variadic:
            ps.append("...")
        return f"{self.ret} {self.name}({', '.join(ps)})"


_TABLE = r"""
ExitProcess|kernel32|processthreadsapi|void|UINT uExitCode|End the process and all its threads with the given exit code.
GetStdHandle|kernel32|processenv|HANDLE|DWORD nStdHandle|Handle of standard input (-10), output (-11) or error (-12).
WriteConsoleA|kernel32|consoleapi|BOOL|HANDLE hConsoleOutput, const VOID* lpBuffer, DWORD nNumberOfCharsToWrite, LPDWORD lpNumberOfCharsWritten, LPVOID lpReserved|Write characters to a console screen buffer at the cursor.
ReadConsoleA|kernel32|consoleapi|BOOL|HANDLE hConsoleInput, LPVOID lpBuffer, DWORD nNumberOfCharsToRead, LPDWORD lpNumberOfCharsRead, LPVOID pInputControl|Read typed characters from the console input buffer.
WriteFile|kernel32|fileapi|BOOL|HANDLE hFile, LPCVOID lpBuffer, DWORD nNumberOfBytesToWrite, LPDWORD lpNumberOfBytesWritten, LPOVERLAPPED lpOverlapped|Write bytes to a file, pipe or console handle.
ReadFile|kernel32|fileapi|BOOL|HANDLE hFile, LPVOID lpBuffer, DWORD nNumberOfBytesToRead, LPDWORD lpNumberOfBytesRead, LPOVERLAPPED lpOverlapped|Read bytes from a file, pipe or console handle.
CreateFileA|kernel32|fileapi|HANDLE|LPCSTR lpFileName, DWORD dwDesiredAccess, DWORD dwShareMode, LPSECURITY_ATTRIBUTES lpSecurityAttributes, DWORD dwCreationDisposition, DWORD dwFlagsAndAttributes, HANDLE hTemplateFile|Open or create a file or device; returns INVALID_HANDLE_VALUE (-1) on failure.
CloseHandle|kernel32|handleapi|BOOL|HANDLE hObject|Close an open object handle.
GetLastError|kernel32|errhandlingapi|DWORD|void|Error code of the last failed API call in this thread.
SetLastError|kernel32|errhandlingapi|void|DWORD dwErrCode|Set the last-error code of this thread.
Sleep|kernel32|synchapi|void|DWORD dwMilliseconds|Suspend the thread for the given number of milliseconds.
GetTickCount|kernel32|sysinfoapi|DWORD|void|Milliseconds since the system started (wraps after 49.7 days).
GetTickCount64|kernel32|sysinfoapi|ULONGLONG|void|Milliseconds since the system started (64-bit).
GetModuleHandleA|kernel32|libloaderapi|HMODULE|LPCSTR lpModuleName|Handle of a loaded module; NULL = the program itself (the hInstance of WinMain).
LoadLibraryA|kernel32|libloaderapi|HMODULE|LPCSTR lpLibFileName|Load a DLL into the process.
GetProcAddress|kernel32|libloaderapi|FARPROC|HMODULE hModule, LPCSTR lpProcName|Address of an exported function of a DLL.
FreeLibrary|kernel32|libloaderapi|BOOL|HMODULE hLibModule|Release a DLL loaded with LoadLibrary.
VirtualAlloc|kernel32|memoryapi|LPVOID|LPVOID lpAddress, SIZE_T dwSize, DWORD flAllocationType, DWORD flProtect|Reserve and / or commit pages of memory (MEM_COMMIT or MEM_RESERVE, PAGE_READWRITE ...).
VirtualFree|kernel32|memoryapi|BOOL|LPVOID lpAddress, SIZE_T dwSize, DWORD dwFreeType|Release or decommit pages allocated with VirtualAlloc.
VirtualProtect|kernel32|memoryapi|BOOL|LPVOID lpAddress, SIZE_T dwSize, DWORD flNewProtect, PDWORD lpflOldProtect|Change the protection of committed pages.
GetProcessHeap|kernel32|heapapi|HANDLE|void|Handle of the default heap of the process (for HeapAlloc).
HeapAlloc|kernel32|heapapi|LPVOID|HANDLE hHeap, DWORD dwFlags, SIZE_T dwBytes|Allocate a block from a heap (HEAP_ZERO_MEMORY = 8 zeroes it).
HeapFree|kernel32|heapapi|BOOL|HANDLE hHeap, DWORD dwFlags, LPVOID lpMem|Free a block allocated with HeapAlloc.
GetCommandLineA|kernel32|processenv|LPSTR|void|The command line of the current process.
GetEnvironmentVariableA|kernel32|processenv|DWORD|LPCSTR lpName, LPSTR lpBuffer, DWORD nSize|Read an environment variable into a buffer.
lstrlenA|kernel32|winbase|int|LPCSTR lpString|Length of a zero-terminated string (without the terminator).
lstrcpyA|kernel32|winbase|LPSTR|LPSTR lpString1, LPCSTR lpString2|Copy a zero-terminated string (no length check).
lstrcatA|kernel32|winbase|LPSTR|LPSTR lpString1, LPCSTR lpString2|Append a zero-terminated string (no length check).
lstrcmpA|kernel32|winbase|int|LPCSTR lpString1, LPCSTR lpString2|Compare two strings (negative, 0, positive).
CreateThread|kernel32|processthreadsapi|HANDLE|LPSECURITY_ATTRIBUTES lpThreadAttributes, SIZE_T dwStackSize, LPTHREAD_START_ROUTINE lpStartAddress, LPVOID lpParameter, DWORD dwCreationFlags, LPDWORD lpThreadId|Start a new thread at a function.
ExitThread|kernel32|processthreadsapi|void|DWORD dwExitCode|End the calling thread.
WaitForSingleObject|kernel32|synchapi|DWORD|HANDLE hHandle, DWORD dwMilliseconds|Wait until an object (thread, process, event ...) is signalled or the timeout (INFINITE = -1) ends.
CreateProcessA|kernel32|processthreadsapi|BOOL|LPCSTR lpApplicationName, LPSTR lpCommandLine, LPSECURITY_ATTRIBUTES lpProcessAttributes, LPSECURITY_ATTRIBUTES lpThreadAttributes, BOOL bInheritHandles, DWORD dwCreationFlags, LPVOID lpEnvironment, LPCSTR lpCurrentDirectory, LPSTARTUPINFOA lpStartupInfo, LPPROCESS_INFORMATION lpProcessInformation|Start a new program.
SetConsoleTitleA|kernel32|consoleapi2|BOOL|LPCSTR lpConsoleTitle|Set the title of the console window.
SetConsoleTextAttribute|kernel32|consoleapi2|BOOL|HANDLE hConsoleOutput, WORD wAttributes|Set the text colour of characters written next (FOREGROUND_RED = 4, GREEN = 2, BLUE = 1, INTENSITY = 8).
SetConsoleCursorPosition|kernel32|consoleapi2|BOOL|HANDLE hConsoleOutput, COORD dwCursorPosition|Move the console cursor (COORD packed as X in the low word, Y in the high word).
AllocConsole|kernel32|consoleapi|BOOL|void|Create a console for a GUI process.
FreeConsole|kernel32|consoleapi|BOOL|void|Detach the process from its console.
GetSystemTime|kernel32|sysinfoapi|void|LPSYSTEMTIME lpSystemTime|Current UTC date and time into a SYSTEMTIME structure.
GetLocalTime|kernel32|sysinfoapi|void|LPSYSTEMTIME lpSystemTime|Current local date and time into a SYSTEMTIME structure.
QueryPerformanceCounter|kernel32|profileapi|BOOL|LARGE_INTEGER* lpPerformanceCount|High-resolution timer value (for measuring time).
QueryPerformanceFrequency|kernel32|profileapi|BOOL|LARGE_INTEGER* lpFrequency|Ticks per second of the performance counter.
OutputDebugStringA|kernel32|debugapi|void|LPCSTR lpOutputString|Send a string to the debugger's output.
MultiByteToWideChar|kernel32|stringapiset|int|UINT CodePage, DWORD dwFlags, LPCCH lpMultiByteStr, int cbMultiByte, LPWSTR lpWideCharStr, int cchWideChar|Convert ANSI / UTF-8 (CP_UTF8 = 65001) text to UTF-16.
WideCharToMultiByte|kernel32|stringapiset|int|UINT CodePage, DWORD dwFlags, LPCWCH lpWideCharStr, int cchWideChar, LPSTR lpMultiByteStr, int cbMultiByte, LPCCH lpDefaultChar, LPBOOL lpUsedDefaultChar|Convert UTF-16 text to ANSI / UTF-8.
FormatMessageA|kernel32|winbase|DWORD|DWORD dwFlags, LPCVOID lpSource, DWORD dwMessageId, DWORD dwLanguageId, LPSTR lpBuffer, DWORD nSize, va_list* Arguments|Build a message string (for example the text of an error code).
GetFileSize|kernel32|fileapi|DWORD|HANDLE hFile, LPDWORD lpFileSizeHigh|Size of a file (low 32 bits returned).
SetFilePointer|kernel32|fileapi|DWORD|HANDLE hFile, LONG lDistanceToMove, PLONG lpDistanceToMoveHigh, DWORD dwMoveMethod|Move the file position (FILE_BEGIN 0, FILE_CURRENT 1, FILE_END 2).
DeleteFileA|kernel32|fileapi|BOOL|LPCSTR lpFileName|Delete a file.
CopyFileA|kernel32|winbase|BOOL|LPCSTR lpExistingFileName, LPCSTR lpNewFileName, BOOL bFailIfExists|Copy a file.
CreateDirectoryA|kernel32|fileapi|BOOL|LPCSTR lpPathName, LPSECURITY_ATTRIBUTES lpSecurityAttributes|Create a folder.
GetCurrentDirectoryA|kernel32|processenv|DWORD|DWORD nBufferLength, LPSTR lpBuffer|Current folder of the process.
Beep|kernel32|utilapiset|BOOL|DWORD dwFreq, DWORD dwDuration|Play a tone (frequency in Hz, duration in ms).
MessageBoxA|user32|winuser|int|HWND hWnd, LPCSTR lpText, LPCSTR lpCaption, UINT uType|Show a modal message box; returns the button pressed (IDOK 1, IDCANCEL 2, IDYES 6, IDNO 7). uType: MB_OK 0, MB_OKCANCEL 1, MB_YESNO 4, MB_ICONERROR 10h, MB_ICONQUESTION 20h, MB_ICONWARNING 30h, MB_ICONINFORMATION 40h.
MessageBeep|user32|winuser|BOOL|UINT uType|Play a system sound.
RegisterClassExA|user32|winuser|ATOM|const WNDCLASSEXA* lpwcx|Register a window class (WNDCLASSEX: cbSize, style, lpfnWndProc, ..., lpszClassName, hIconSm).
CreateWindowExA|user32|winuser|HWND|DWORD dwExStyle, LPCSTR lpClassName, LPCSTR lpWindowName, DWORD dwStyle, int X, int Y, int nWidth, int nHeight, HWND hWndParent, HMENU hMenu, HINSTANCE hInstance, LPVOID lpParam|Create a window or a control (class "BUTTON", "EDIT", "STATIC" ...). 12 arguments: on Win64, 8 go on the stack above the shadow space.
DefWindowProcA|user32|winuser|LRESULT|HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam|Default processing for messages your window procedure does not handle.
ShowWindow|user32|winuser|BOOL|HWND hWnd, int nCmdShow|Show, hide, minimise or maximise a window (SW_SHOWNORMAL 1, SW_SHOW 5).
UpdateWindow|user32|winuser|BOOL|HWND hWnd|Send WM_PAINT now if the window has an invalid region.
GetMessageA|user32|winuser|BOOL|LPMSG lpMsg, HWND hWnd, UINT wMsgFilterMin, UINT wMsgFilterMax|Wait for the next message; returns 0 on WM_QUIT (end of the message loop).
PeekMessageA|user32|winuser|BOOL|LPMSG lpMsg, HWND hWnd, UINT wMsgFilterMin, UINT wMsgFilterMax, UINT wRemoveMsg|Check for a message without waiting (game loops).
TranslateMessage|user32|winuser|BOOL|const MSG* lpMsg|Turn key messages into WM_CHAR messages.
DispatchMessageA|user32|winuser|LRESULT|const MSG* lpMsg|Send a message to its window procedure.
PostQuitMessage|user32|winuser|void|int nExitCode|Ask the message loop to end (posts WM_QUIT).
LoadIconA|user32|winuser|HICON|HINSTANCE hInstance, LPCSTR lpIconName|Load an icon (NULL, IDI_APPLICATION = 32512 for the standard one).
LoadCursorA|user32|winuser|HCURSOR|HINSTANCE hInstance, LPCSTR lpCursorName|Load a cursor (NULL, IDC_ARROW = 32512 for the arrow).
SendMessageA|user32|winuser|LRESULT|HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam|Send a message and wait for the window procedure to handle it.
PostMessageA|user32|winuser|BOOL|HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam|Queue a message and return at once.
SetWindowTextA|user32|winuser|BOOL|HWND hWnd, LPCSTR lpString|Change the caption of a window or the text of a control.
GetWindowTextA|user32|winuser|int|HWND hWnd, LPSTR lpString, int nMaxCount|Read the caption / text of a window or control.
DestroyWindow|user32|winuser|BOOL|HWND hWnd|Destroy a window (sends WM_DESTROY).
BeginPaint|user32|winuser|HDC|HWND hWnd, LPPAINTSTRUCT lpPaint|Start painting in WM_PAINT; returns the device context.
EndPaint|user32|winuser|BOOL|HWND hWnd, const PAINTSTRUCT* lpPaint|Finish painting started with BeginPaint.
InvalidateRect|user32|winuser|BOOL|HWND hWnd, const RECT* lpRect, BOOL bErase|Mark an area to be repainted (NULL = whole client area).
GetClientRect|user32|winuser|BOOL|HWND hWnd, LPRECT lpRect|Size of the client area.
SetTimer|user32|winuser|UINT_PTR|HWND hWnd, UINT_PTR nIDEvent, UINT uElapse, TIMERPROC lpTimerFunc|Start a timer that sends WM_TIMER every uElapse ms.
KillTimer|user32|winuser|BOOL|HWND hWnd, UINT_PTR uIDEvent|Stop a timer.
GetDlgItem|user32|winuser|HWND|HWND hDlg, int nIDDlgItem|Window handle of a dialog control.
DialogBoxParamA|user32|winuser|INT_PTR|HINSTANCE hInstance, LPCSTR lpTemplateName, HWND hWndParent, DLGPROC lpDialogFunc, LPARAM dwInitParam|Show a modal dialog from a resource template.
EndDialog|user32|winuser|BOOL|HWND hDlg, INT_PTR nResult|Close a modal dialog.
GetDC|user32|winuser|HDC|HWND hWnd|Device context for drawing in a window outside WM_PAINT.
ReleaseDC|user32|winuser|int|HWND hWnd, HDC hDC|Release a device context from GetDC.
MoveWindow|user32|winuser|BOOL|HWND hWnd, int X, int Y, int nWidth, int nHeight, BOOL bRepaint|Move and resize a window.
EnableWindow|user32|winuser|BOOL|HWND hWnd, BOOL bEnable|Enable or disable a window / control.
SetFocus|user32|winuser|HWND|HWND hWnd|Give the keyboard focus to a window.
GetAsyncKeyState|user32|winuser|SHORT|int vKey|Whether a key is down right now (top bit set).
wsprintfA|user32|winuser|int|LPSTR lpOut, LPCSTR lpFmt|Format a string like sprintf (variadic: cdecl - the caller removes the arguments, unlike other Win32 APIs).|...
TextOutA|gdi32|wingdi|BOOL|HDC hdc, int x, int y, LPCSTR lpString, int c|Draw text at a position.
SetTextColor|gdi32|wingdi|COLORREF|HDC hdc, COLORREF color|Text colour (0x00BBGGRR).
SetBkColor|gdi32|wingdi|COLORREF|HDC hdc, COLORREF color|Background colour behind text.
SetBkMode|gdi32|wingdi|int|HDC hdc, int mode|TRANSPARENT (1) or OPAQUE (2) text background.
CreateSolidBrush|gdi32|wingdi|HBRUSH|COLORREF color|Create a brush of one colour.
CreatePen|gdi32|wingdi|HPEN|int iStyle, int cWidth, COLORREF color|Create a pen for lines.
SelectObject|gdi32|wingdi|HGDIOBJ|HDC hdc, HGDIOBJ h|Select a pen, brush, font or bitmap into a DC; returns the previous one.
DeleteObject|gdi32|wingdi|BOOL|HGDIOBJ ho|Delete a pen, brush, font, bitmap or region.
GetStockObject|gdi32|wingdi|HGDIOBJ|int i|A predefined pen / brush / font (WHITE_BRUSH 0, BLACK_BRUSH 4).
Rectangle|gdi32|wingdi|BOOL|HDC hdc, int left, int top, int right, int bottom|Draw a rectangle with the current pen and brush.
Ellipse|gdi32|wingdi|BOOL|HDC hdc, int left, int top, int right, int bottom|Draw an ellipse in a bounding rectangle.
MoveToEx|gdi32|wingdi|BOOL|HDC hdc, int x, int y, LPPOINT lppt|Move the current drawing position.
LineTo|gdi32|wingdi|BOOL|HDC hdc, int x, int y|Draw a line from the current position.
SetPixel|gdi32|wingdi|COLORREF|HDC hdc, int x, int y, COLORREF color|Set one pixel.
BitBlt|gdi32|wingdi|BOOL|HDC hdc, int x, int y, int cx, int cy, HDC hdcSrc, int x1, int y1, DWORD rop|Copy a block of pixels between DCs (SRCCOPY = 00CC0020h).
CreateCompatibleDC|gdi32|wingdi|HDC|HDC hdc|Memory DC for off-screen drawing.
DeleteDC|gdi32|wingdi|BOOL|HDC hdc|Delete a DC created with CreateCompatibleDC.
CreateFontA|gdi32|wingdi|HFONT|int cHeight, int cWidth, int cEscapement, int cOrientation, int cWeight, DWORD bItalic, DWORD bUnderline, DWORD bStrikeOut, DWORD iCharSet, DWORD iOutPrecision, DWORD iClipPrecision, DWORD iQuality, DWORD iPitchAndFamily, LPCSTR pszFaceName|Create a logical font.
ShellExecuteA|shell32|shellapi|HINSTANCE|HWND hwnd, LPCSTR lpOperation, LPCSTR lpFile, LPCSTR lpParameters, LPCSTR lpDirectory, INT nShowCmd|Open a file, URL or program with its associated application.
printf|crt|stdio|int|const char* format|Formatted output to stdout (%d %u %x %s %c %f %lld %p). Variadic: on Win64 copy float arguments to both the XMM and the integer register; on System V set AL to the number of vector registers used.|...
scanf|crt|stdio|int|const char* format|Formatted input from stdin; pass addresses of the variables.|...
sprintf|crt|stdio|int|char* buffer, const char* format|Formatted output into a buffer (no length check - prefer snprintf).|...
snprintf|crt|stdio|int|char* buffer, size_t count, const char* format|Formatted output into a buffer of a given size.|...
sscanf|crt|stdio|int|const char* buffer, const char* format|Formatted input from a string.|...
fprintf|crt|stdio|int|FILE* stream, const char* format|Formatted output to a stream.|...
puts|crt|stdio|int|const char* str|Write a string and a newline to stdout.
putchar|crt|stdio|int|int c|Write one character to stdout.
getchar|crt|stdio|int|void|Read one character from stdin (EOF = -1).
fgets|crt|stdio|char*|char* str, int numChars, FILE* stream|Read a line (up to numChars-1 characters) from a stream.
fopen|crt|stdio|FILE*|const char* filename, const char* mode|Open a file ("r", "w", "a", "rb" ...); NULL on failure.
fclose|crt|stdio|int|FILE* stream|Close a stream.
fread|crt|stdio|size_t|void* buffer, size_t size, size_t count, FILE* stream|Read count items of size bytes.
fwrite|crt|stdio|size_t|const void* buffer, size_t size, size_t count, FILE* stream|Write count items of size bytes.
fseek|crt|stdio|int|FILE* stream, long offset, int origin|Move the file position (SEEK_SET 0, SEEK_CUR 1, SEEK_END 2).
ftell|crt|stdio|long|FILE* stream|Current file position.
fputs|crt|stdio|int|const char* str, FILE* stream|Write a string to a stream (no newline added).
malloc|crt|stdlib|void*|size_t size|Allocate size bytes (NULL on failure).
calloc|crt|stdlib|void*|size_t number, size_t size|Allocate a zeroed array.
realloc|crt|stdlib|void*|void* memblock, size_t size|Resize an allocated block (may move it).
free|crt|stdlib|void|void* memblock|Free a block from malloc / calloc / realloc.
exit|crt|stdlib|void|int status|End the program after flushing streams and running atexit functions.
atoi|crt|stdlib|int|const char* str|Convert a decimal string to int.
atol|crt|stdlib|long|const char* str|Convert a decimal string to long.
atof|crt|stdlib|double|const char* str|Convert a string to double (returned in XMM0 on x64, ST(0) on x86).
strtol|crt|stdlib|long|const char* strSource, char** endptr, int base|Convert a string to long in any base.
abs|crt|stdlib|int|int n|Absolute value.
rand|crt|stdlib|int|void|Pseudo-random number 0..RAND_MAX (32767 on Windows).
srand|crt|stdlib|void|unsigned int seed|Seed the pseudo-random generator.
qsort|crt|stdlib|void|void* base, size_t number, size_t width, int (*compare)(const void*, const void*)|Sort an array with a compare callback.
system|crt|process|int|const char* command|Run a shell command (system("pause")).
getenv|crt|stdlib|char*|const char* varname|Value of an environment variable.
memcpy|crt|string|void*|void* dest, const void* src, size_t count|Copy count bytes (regions must not overlap).
memmove|crt|string|void*|void* dest, const void* src, size_t count|Copy count bytes (regions may overlap).
memset|crt|string|void*|void* dest, int c, size_t count|Fill count bytes with a value.
memcmp|crt|string|int|const void* buffer1, const void* buffer2, size_t count|Compare count bytes.
strlen|crt|string|size_t|const char* str|Length of a zero-terminated string.
strcpy|crt|string|char*|char* strDestination, const char* strSource|Copy a string (no length check).
strncpy|crt|string|char*|char* strDest, const char* strSource, size_t count|Copy at most count characters.
strcat|crt|string|char*|char* strDestination, const char* strSource|Append a string (no length check).
strcmp|crt|string|int|const char* string1, const char* string2|Compare two strings (negative, 0, positive).
strncmp|crt|string|int|const char* string1, const char* string2, size_t count|Compare at most count characters.
toupper|crt|ctype|int|int c|Upper-case letter.
tolower|crt|ctype|int|int c|Lower-case letter.
isdigit|crt|ctype|int|int c|Non-zero if c is '0'..'9'.
isalpha|crt|ctype|int|int c|Non-zero if c is a letter.
time|crt|time|time_t|time_t* destTime|Seconds since 1970-01-01 UTC.
clock|crt|time|clock_t|void|Processor time used (CLOCKS_PER_SEC per second).
sqrt|crt|math|double|double x|Square root (argument and result in XMM0 on x64).
sin|crt|math|double|double x|Sine (radians).
cos|crt|math|double|double x|Cosine (radians).
pow|crt|math|double|double x, double y|x raised to the power y (x in XMM0, y in XMM1 on x64).
fabs|crt|math|double|double x|Absolute value of a double.
floor|crt|math|double|double x|Largest integer not greater than x.
ceil|crt|math|double|double x|Smallest integer not less than x.
"""


def _parse() -> dict[str, Api]:
    out: dict[str, Api] = {}
    for raw in _TABLE.strip().splitlines():
        parts = raw.split("|")
        if len(parts) < 6:
            continue
        name, dll, header, ret, params, doc = (p.strip() for p in parts[:6])
        variadic = len(parts) > 6 and parts[6].strip() == "..."
        plist: list[tuple[str, str]] = []
        if params and params != "void":
            for p in _split(params):
                m = re.match(r"(.*?)([A-Za-z_]\w*)\s*$", p)
                if m and m.group(1).strip():
                    plist.append((m.group(1).strip(), m.group(2)))
                else:
                    plist.append((p, ""))
        api = Api(name, dll, header, ret, plist, doc, variadic)
        out[name.lower()] = api
        if name.endswith("A") and dll != "crt":
            wname = name[:-1] + "W"
            wparams = [(t.replace("LPCSTR", "LPCWSTR").replace("LPSTR", "LPWSTR"), n) for t, n in plist]
            out[wname.lower()] = Api(wname, dll, header, ret, wparams, doc + " (UTF-16 'W' version.)", variadic)
            # the plain name (MessageBox) is what FASM / MASM include files map to the A or W form
            out.setdefault(name[:-1].lower(), Api(name[:-1], dll, header, ret, plist,
                                                  doc + f" (Include files map it to {name} or {wname}.)", variadic))
    return out


def _split(params: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in params:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
            continue
        cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


APIS: dict[str, Api] = _parse()


def lookup(name: str) -> Api | None:
    """MessageBoxA / MessageBox / __imp_MessageBoxA / _MessageBoxA@16 / [MessageBoxA] -> the Api."""
    n = name.strip().strip("[]")
    n = re.sub(r"^(?:__imp_|_imp__|imp_)", "", n)
    n = re.sub(r"@\d+$", "", n)
    hit = APIS.get(n.lower())
    if hit is None and n.startswith("_"):
        hit = APIS.get(n[1:].lower())
    return hit


FLOAT_TYPES = {"double", "float"}


def arg_locations(api: Api, abi: str) -> list[str]:
    """Where each argument goes: 'rcx', 'xmm1', '[rsp+20h]' (win64), 'rdi'... (sysv), 'push #3' (x86)."""
    out = []
    if abi == "win64":
        ints = ["rcx", "rdx", "r8", "r9"]
        for i, (t, _n) in enumerate(api.params):
            if i < 4:
                out.append(f"xmm{i}" if t in FLOAT_TYPES else ints[i])
            else:
                out.append(f"[rsp+{0x20 + 8 * (i - 4):X}h]")
        return out
    if abi == "sysv":
        ints = ["rdi", "rsi", "rdx", "rcx", "r8", "r9"]
        ni = nf = 0
        stack = 0
        for t, _n in api.params:
            if t in FLOAT_TYPES and nf < 8:
                out.append(f"xmm{nf}")
                nf += 1
            elif t not in FLOAT_TYPES and ni < 6:
                out.append(ints[ni])
                ni += 1
            else:
                out.append(f"[rsp+{8 * stack}]")
                stack += 1
        return out
    n = len(api.params)
    return [f"push #{n - i}" for i in range(n)]       # x86: pushed right to left (the last argument first)


def convention(api: Api, abi: str) -> str:
    if abi == "win64":
        return ("Microsoft x64: first 4 arguments in RCX, RDX, R8, R9 (floats in XMM0-XMM3), the rest on the stack; "
                "reserve 32 bytes of shadow space (sub rsp, 28h at entry keeps RSP 16-byte aligned); result in "
                "RAX / XMM0. RAX RCX RDX R8-R11 XMM0-XMM5 are volatile.")
    if abi == "sysv":
        return ("System V AMD64: integer arguments in RDI, RSI, RDX, RCX, R8, R9; floats in XMM0-XMM7; RSP 16-byte "
                "aligned at the call; variadic calls set AL = number of vector registers used. Result in RAX / XMM0.")
    if api.is_crt or api.variadic:
        return ("cdecl (32-bit): push the arguments right to left; the caller removes them afterwards "
                f"(add esp, {4 * len(api.params)}{' + 4 per extra argument' if api.variadic else ''}). Result in EAX.")
    return (f"stdcall (32-bit): push the arguments right to left; the function removes them itself "
            f"(ret {4 * len(api.params)}). Decorated name _{api.name}@{4 * len(api.params)}. Result in EAX.")
