/* radbridge - the native GUI Bridge host of RAD IDE (C + radforms, no Python).
 * (c) 2026 Musoftware - https://musoftwares.com - MIT License
 *
 * Runs a GUI Bridge program of any language (C, C++, Rust, Go, Fortran, Lua, Ruby, Perl, Java, Dart, JavaScript,
 * PowerShell ...) and draws its forms with radforms (Win32) - the job radide/runtimes/bridge.py (Python + Tk) does
 * in GUI Bridge mode. Same line protocol on the program's stdin / stdout (docs/CONTRACTS.md section 1):
 *
 *   host -> program : EVENT <obj> <event> [args] | QUIT          program -> host : SET / GET / CALL / MSGBOX /
 *   INPUT / SHOW / HIDE / DONE / END / ESC <command>; GET, CALL, MSGBOX, INPUT get one answer line; any other
 *   line is program output (passed on to this host's stdout = the IDE's Output window).
 *
 *   radbridge.exe <forms.radf> [--build "<command>"] -- <program> [args ...]
 *
 * forms.radf: the radforms form description (radide/deploy/native/radforms_gen.py description(), written by the
 * IDE at F5); images are files, relative to RAD_BASE_DIR (the project folder). RAD_HANDLERS = the program's
 * handlers (only those events are sent). RAD_BRIDGE_DEBUG=1: prints "@@RADBRIDGE@@pid|<pid>" and waits for a line
 * ("go") on stdin before the first event, so the IDE can attach its debugger (radide/bridgedebug.py).
 * The program runs in a kill-on-close job: when this host ends (Stop in the IDE), the program ends too.
 *
 * Commands the program sends while no event runs (start-up code, threads) are served by a timer on the GUI thread.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "radforms.h"

typedef struct QLine { char *text; struct QLine *next; } QLine;

static HANDLE g_to_child = INVALID_HANDLE_VALUE, g_from_child = INVALID_HANDLE_VALUE, g_proc = NULL;
static CRITICAL_SECTION g_cs;
static HANDLE g_have;                    /* set while lines are queued or the program's output ended */
static QLine *g_head, *g_tail;
static volatile LONG g_eof;
static int g_in_handler, g_busy, g_ended;
/* debugger control lines after "go" (radide/bridgedebug.py simulate): "EVENT <obj> <event>" */
static CRITICAL_SECTION g_ccs;
static QLine *g_ctl_head, *g_ctl_tail;

/* ------------------------------------------------------------------ helpers */
static char *xstrdup(const char *s) { size_t n = strlen(s); char *d = (char *)malloc(n + 1); memcpy(d, s, n + 1); return d; }

static void out_line(const char *s) {
    fputs(s, stdout);
    fputc('\n', stdout);
    fflush(stdout);
}

static void err_line(const char *s) {
    fputs(s, stderr);
    fputc('\n', stderr);
    fflush(stderr);
}

/* a command line argument quoted like the C runtime parses it */
static void quote_arg(wchar_t *dst, size_t cap, const wchar_t *a) {
    size_t n = wcslen(dst);
    int need = !*a || wcspbrk(a, L" \t\"") != NULL;
    if (n && n < cap - 1) dst[n++] = L' ';
    if (!need) { wcsncpy(dst + n, a, cap - n - 1); dst[cap - 1] = 0; return; }
    if (n < cap - 1) dst[n++] = L'"';
    for (;;) {
        size_t bs = 0;
        while (*a == L'\\') { a++; bs++; }
        if (!*a) { while (bs-- && n < cap - 2) dst[n++] = L'\\'; break; }
        if (*a == L'"') { size_t k; for (k = 0; k < bs * 2 + 1 && n < cap - 2; k++) dst[n++] = L'\\'; }
        else { size_t k; for (k = 0; k < bs && n < cap - 2; k++) dst[n++] = L'\\'; }
        if (n < cap - 2) dst[n++] = *a;
        a++;
    }
    if (n < cap - 1) dst[n++] = L'"';
    dst[n] = 0;
}

/* trailing backslashes before the closing quote must be doubled */
static void quote_arg_fix(wchar_t *dst, size_t cap, const wchar_t *a) {
    size_t len = wcslen(a), bs = 0;
    while (bs < len && a[len - 1 - bs] == L'\\') bs++;
    if (bs && (!*a || wcspbrk(a, L" \t\"") != NULL)) {
        wchar_t *tmp = (wchar_t *)malloc((len + bs + 1) * sizeof(wchar_t));
        wcscpy(tmp, a);
        { size_t k; for (k = 0; k < bs; k++) tmp[len + k] = L'\\'; tmp[len + bs] = 0; }
        quote_arg(dst, cap, tmp);
        free(tmp);
    } else quote_arg(dst, cap, a);
}

/* ------------------------------------------------------------------ the program's output */
static void push(char *text) {
    QLine *q = (QLine *)malloc(sizeof *q);
    q->text = text;
    q->next = NULL;
    EnterCriticalSection(&g_cs);
    if (g_tail) g_tail->next = q; else g_head = q;
    g_tail = q;
    SetEvent(g_have);
    LeaveCriticalSection(&g_cs);
}

static char *pop(void) {
    char *t = NULL;
    EnterCriticalSection(&g_cs);
    if (g_head) {
        QLine *q = g_head;
        g_head = q->next;
        if (!g_head) g_tail = NULL;
        t = q->text;
        free(q);
    }
    if (!g_head && !g_eof) ResetEvent(g_have);
    LeaveCriticalSection(&g_cs);
    return t;
}

static DWORD WINAPI reader(LPVOID p) {
    char *buf = NULL;
    size_t len = 0, cap = 0;
    (void)p;
    for (;;) {
        char *nl;
        DWORD got = 0;
        if (cap - len < 4096) { cap = cap ? cap * 2 : 65536; buf = (char *)realloc(buf, cap); }
        if (!ReadFile(g_from_child, buf + len, (DWORD)(cap - len), &got, NULL) || got == 0) break;
        len += got;
        while ((nl = (char *)memchr(buf, '\n', len)) != NULL) {
            size_t n = (size_t)(nl - buf);
            char *line = (char *)malloc(n + 1);
            memcpy(line, buf, n);
            line[n] = 0;
            if (n && line[n - 1] == '\r') line[n - 1] = 0;
            memmove(buf, nl + 1, len - n - 1);
            len -= n + 1;
            push(line);
        }
    }
    if (len) { char *line = (char *)malloc(len + 1); memcpy(line, buf, len); line[len] = 0; push(line); }
    free(buf);
    EnterCriticalSection(&g_cs);
    InterlockedExchange(&g_eof, 1);
    SetEvent(g_have);
    LeaveCriticalSection(&g_cs);
    return 0;
}

static void to_child(const char *s) {
    DWORD n;
    size_t len = strlen(s);
    char *b = (char *)malloc(len + 2);
    memcpy(b, s, len);
    b[len] = '\n';
    if (g_to_child != INVALID_HANDLE_VALUE) WriteFile(g_to_child, b, (DWORD)len + 1, &n, NULL);
    free(b);
}

/* ------------------------------------------------------------------ protocol */
static int starts(const char *line, const char *cmd) {
    size_t n = strlen(cmd);
    return _strnicmp(line, cmd, n) == 0 && (line[n] == ' ' || line[n] == 0);
}

static int is_command(const char *l) {
    return starts(l, "SET") || starts(l, "GET") || starts(l, "CALL") || starts(l, "MSGBOX") || starts(l, "INPUT") ||
           starts(l, "SHOW") || starts(l, "HIDE") || starts(l, "ESC");
}

static int answers(const char *l) {
    if (starts(l, "ESC")) l += 4;
    return starts(l, "GET") || starts(l, "CALL") || starts(l, "MSGBOX") || starts(l, "INPUT");
}

/* 0 = go on, 1 = DONE, 2 = END */
static int handle(const char *line) {
    if (_stricmp(line, "DONE") == 0) {
        if (g_in_handler) rad_command("DONE");
        return 1;
    }
    if (_stricmp(line, "END") == 0) return 2;
    if (is_command(line)) {
        int want = answers(line);
        const char *r = rad_command(line);
        if (want) to_child(r ? r : "");
        return 0;
    }
    out_line(line);
    return 0;
}

/* the next line of the program; pumps window messages while it waits (repaints, a modal MSGBOX ...) */
static char *next_line(void) {
    for (;;) {
        char *t = pop();
        MSG msg;
        if (t) return t;
        if (g_eof) { t = pop(); return t; }
        MsgWaitForMultipleObjects(1, &g_have, FALSE, INFINITE, QS_ALLINPUT);
        while (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE)) {
            if (msg.message == WM_QUIT) { PostQuitMessage((int)msg.wParam); return pop(); }
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }
}

static DWORD WINAPI control_reader(LPVOID p) {
    char buf[1024];
    (void)p;
    while (fgets(buf, sizeof buf, stdin)) {
        QLine *q;
        size_t n = strlen(buf);
        while (n && (buf[n - 1] == '\n' || buf[n - 1] == '\r')) buf[--n] = 0;
        if (_strnicmp(buf, "EVENT ", 6) != 0) continue;
        q = (QLine *)malloc(sizeof *q);
        q->text = xstrdup(buf);
        q->next = NULL;
        EnterCriticalSection(&g_ccs);
        if (g_ctl_tail) g_ctl_tail->next = q; else g_ctl_head = q;
        g_ctl_tail = q;
        LeaveCriticalSection(&g_ccs);
    }
    return 0;
}

static char *pop_control(void) {
    char *t = NULL;
    EnterCriticalSection(&g_ccs);
    if (g_ctl_head) {
        QLine *q = g_ctl_head;
        g_ctl_head = q->next;
        if (!g_ctl_head) g_ctl_tail = NULL;
        t = q->text;
        free(q);
    }
    LeaveCriticalSection(&g_ccs);
    return t;
}

/* one event round trip: EVENT to the program, its commands served until DONE / END */
static void serve_event(const char *ev) {
    g_in_handler = 1;
    to_child(ev);
    for (;;) {
        char *l = next_line();
        int r;
        if (!l) { g_ended = 1; break; }               /* the program has quit */
        r = handle(l);
        free(l);
        if (r == 1) break;
        if (r == 2) { rad_command("DONE"); g_ended = 1; rad_end(); break; }
    }
    g_in_handler = 0;
}

static void CALLBACK idle(HWND h, UINT m, UINT_PTR id, DWORD t) {
    char *l;
    (void)h; (void)m; (void)id; (void)t;
    if (g_in_handler || g_busy || g_ended) return;
    g_busy = 1;
    if ((l = pop_control()) != NULL) {               /* a simulated event (the IDE debugger) */
        serve_event(l);
        free(l);
        if (g_ended) rad_end();
    }
    while ((l = pop()) != NULL) {
        int r = handle(l);
        free(l);
        if (r == 2) { g_ended = 1; rad_end(); break; }
    }
    if (g_eof && !g_head && !g_ended) { g_ended = 1; rad_end(); }    /* the program has quit */
    g_busy = 0;
}

/* ------------------------------------------------------------------ build step / program */
static int run_build(const wchar_t *cmd) {
    wchar_t *line = (wchar_t *)malloc((wcslen(cmd) + 32) * sizeof(wchar_t));
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    DWORD code = 1;
    {
        int n = WideCharToMultiByte(CP_UTF8, 0, cmd, -1, NULL, 0, NULL, NULL);
        char *c = (char *)malloc(n > 0 ? n : 1);
        if (n > 0) WideCharToMultiByte(CP_UTF8, 0, cmd, -1, c, n, NULL, NULL); else c[0] = 0;
        printf("------ Build: %s\n", c);
        fflush(stdout);
        free(c);
    }
    swprintf(line, wcslen(cmd) + 32, L"cmd.exe /d /s /c \"%ls\"", cmd);
    memset(&si, 0, sizeof si);
    si.cb = sizeof si;
    if (!CreateProcessW(NULL, line, NULL, NULL, TRUE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        err_line("radbridge: the build command could not be started");
        free(line);
        return 1;
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    GetExitCodeProcess(pi.hProcess, &code);
    if (code != 0) {
        char m[96];
        snprintf(m, sizeof m, "------ Build failed (exit code %lu)", (unsigned long)code);
        err_line(m);
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    free(line);
    return (int)code;
}

static HANDLE kill_on_close_job(void) {
    HANDLE job = CreateJobObjectW(NULL, NULL);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION info;
    if (!job) return NULL;
    memset(&info, 0, sizeof info);
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    SetInformationJobObject(job, JobObjectExtendedLimitInformation, &info, sizeof info);
    return job;
}

static int start_program(wchar_t *cmdline) {
    SECURITY_ATTRIBUTES sa = { sizeof sa, NULL, TRUE };
    HANDLE in_r, in_w, out_r, out_w, err_dup = NULL, job;
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    if (!CreatePipe(&in_r, &in_w, &sa, 0) || !CreatePipe(&out_r, &out_w, &sa, 0)) return 0;
    SetHandleInformation(in_w, HANDLE_FLAG_INHERIT, 0);
    SetHandleInformation(out_r, HANDLE_FLAG_INHERIT, 0);
    DuplicateHandle(GetCurrentProcess(), GetStdHandle(STD_ERROR_HANDLE), GetCurrentProcess(), &err_dup, 0, TRUE,
                    DUPLICATE_SAME_ACCESS);
    memset(&si, 0, sizeof si);
    si.cb = sizeof si;
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdInput = in_r;
    si.hStdOutput = out_w;
    si.hStdError = err_dup ? err_dup : out_w;
    job = kill_on_close_job();
    if (!CreateProcessW(NULL, cmdline, NULL, NULL, TRUE, CREATE_NO_WINDOW | CREATE_SUSPENDED, NULL, NULL, &si, &pi)) {
        char msg[256];
        snprintf(msg, sizeof msg, "radbridge: the program could not be started (Windows error %lu)",
                 (unsigned long)GetLastError());
        err_line(msg);
        return 0;
    }
    if (job) AssignProcessToJobObject(job, pi.hProcess);
    ResumeThread(pi.hThread);
    CloseHandle(pi.hThread);
    CloseHandle(in_r);
    CloseHandle(out_w);
    if (err_dup) CloseHandle(err_dup);
    g_proc = pi.hProcess;
    g_to_child = in_w;
    g_from_child = out_r;
    return 1;
}

static char *read_file(const wchar_t *path) {
    HANDLE f = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    DWORD n, got = 0;
    char *s;
    if (f == INVALID_HANDLE_VALUE) return NULL;
    n = GetFileSize(f, NULL);
    s = (char *)malloc(n + 1);
    if (!ReadFile(f, s, n, &got, NULL)) got = 0;
    s[got] = 0;
    CloseHandle(f);
    if (got >= 3 && (unsigned char)s[0] == 0xEF && (unsigned char)s[1] == 0xBB && (unsigned char)s[2] == 0xBF)
        memmove(s, s + 3, got - 2);
    return s;
}

int main(void) {
    int argc = 0, i, sep = -1, code = 0;
    wchar_t **argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    const wchar_t *build = NULL;
    wchar_t *cmdline;
    char *forms, *handlers;
    size_t cap = 32768;
    DWORD exit_code = 0;

    for (i = 2; i < argc; i++) {
        if (wcscmp(argv[i], L"--") == 0) { sep = i; break; }
        if (wcscmp(argv[i], L"--build") == 0 && i + 1 < argc) build = argv[++i];
    }
    if (argc < 2 || sep < 0 || sep + 1 >= argc) {
        err_line("usage: radbridge <forms.radf> [--build \"<command>\"] -- <program> [args ...]");
        return 2;
    }
    if (build && *build) {
        int b = run_build(build);
        if (b != 0) return b;
    }
    forms = read_file(argv[1]);
    if (!forms || !rad_forms_load(forms)) {
        err_line("radbridge: the form description could not be read");
        return 1;
    }
    free(forms);
    handlers = getenv("RAD_HANDLERS");
    if (handlers && *handlers) rad_handlers(handlers);

    cmdline = (wchar_t *)calloc(cap, sizeof(wchar_t));
    for (i = sep + 1; i < argc; i++) quote_arg_fix(cmdline, cap, argv[i]);
    InitializeCriticalSection(&g_cs);
    InitializeCriticalSection(&g_ccs);
    g_have = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!start_program(cmdline)) return 1;
    CreateThread(NULL, 0, reader, NULL, 0, NULL);

    if (getenv("RAD_BRIDGE_DEBUG") && *getenv("RAD_BRIDGE_DEBUG")) {
        char go[64];
        printf("@@RADBRIDGE@@pid|%lu\n", (unsigned long)GetProcessId(g_proc));
        fflush(stdout);
        if (fgets(go, sizeof go, stdin)) CreateThread(NULL, 0, control_reader, NULL, 0, NULL);
    }
    SetTimer(NULL, 0, 10, idle);
    for (;;) {
        const char *ev = rad_event_line();
        char *e;
        if (strcmp(ev, "QUIT") == 0 || g_ended) break;
        e = xstrdup(ev);
        serve_event(e);
        free(e);
        if (g_ended) break;
    }
    to_child("QUIT");
    if (g_to_child != INVALID_HANDLE_VALUE) { CloseHandle(g_to_child); g_to_child = INVALID_HANDLE_VALUE; }
    if (WaitForSingleObject(g_proc, 3000) != WAIT_OBJECT_0) TerminateProcess(g_proc, 0);
    { char *l; Sleep(50); while ((l = pop()) != NULL) { if (!is_command(l) && _stricmp(l, "DONE") && _stricmp(l, "END")) out_line(l); free(l); } }
    GetExitCodeProcess(g_proc, &exit_code);
    code = (int)exit_code;
    return code;
}
