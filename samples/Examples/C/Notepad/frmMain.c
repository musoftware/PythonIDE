/* (c) 2026 Musoftware - https://musoftwares.com - MIT License
 *
 * Notepad - a small text editor written in C for the RAD IDE GUI Bridge (radgui.h).
 * The IDE draws frmMain (menu, multi-line text box, status bar, Open / Save / Font dialogs);
 * this file only reacts to events. The same code builds as a native Win32 exe (Build > Publish).
 *
 * Shows: menus, OpenFileDialog / SaveFileDialog / FontDialog, file I/O with stdio, the Windows
 * clipboard (Win32 API), Find / Find Next / Replace with SelStart / SelLength / SelText,
 * a status bar, "save changes?" on New / Open / Exit, multi-line text through the bridge.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#endif
#include "radgui.h"

#define MAX_TEXT 60000          /* a GUI Bridge answer is one line of at most 64 KB */

static char file_name[1024] = "";   /* "" = Untitled */
static char find_what[256] = "";
static int dirty = 0;               /* text changed since the last save */
static int loading = 0;             /* TextChanged caused by our own rad_set */

/* ------------------------------------------------------------------ helpers */
static const char *base_name(const char *path)
{
    const char *p = strrchr(path, '\\'), *q = strrchr(path, '/');
    if (q > p) p = q;
    return p ? p + 1 : path;
}

static void update_title(void)
{
    char title[1200];
    snprintf(title, sizeof title, "%s%s - Notepad", dirty ? "*" : "", *file_name ? base_name(file_name) : "Untitled");
    rad_set("frmMain", "Caption", title);
}

static void status(const char *text) { rad_set("sbStatus", "Text", text); }

/* number of characters (not bytes) in the first n bytes of UTF-8 text - SelStart counts characters */
static int utf8_chars(const char *s, int n)
{
    int i, c = 0;
    for (i = 0; i < n && s[i]; i++)
        if (((unsigned char)s[i] & 0xC0) != 0x80) c++;
    return c;
}

/* byte offset of character number ch */
static int utf8_bytes(const char *s, int ch)
{
    int i = 0, c = 0;
    while (s[i] && c < ch) {
        i++;
        while (((unsigned char)s[i] & 0xC0) == 0x80) i++;
        c++;
    }
    return i;
}

/* ask before throwing changes away: 1 = go on */
static int confirm_discard(void)
{
    const char *a;
    if (!dirty) return 1;
    a = rad_input("The text has changed. Type YES to discard the changes (or Cancel to keep them):");
    return a && (a[0] == 'Y' || a[0] == 'y');
}

static int write_file(const char *path)
{
    const char *text = rad_get("txtDoc", "Text");
    FILE *f = fopen(path, "wb");
    char msg[1200];
    if (!f) {
        snprintf(msg, sizeof msg, "Cannot write %s", path);
        rad_msgbox(msg);
        return 0;
    }
    fwrite(text, 1, strlen(text), f);
    fclose(f);
    strncpy(file_name, path, sizeof file_name - 1);
    dirty = 0;
    update_title();
    snprintf(msg, sizeof msg, "Saved %s (%u bytes)", base_name(path), (unsigned)strlen(text));
    status(msg);
    return 1;
}

static void open_file(const char *path)
{
    FILE *f = fopen(path, "rb");
    char *raw, *text, msg[1200];
    size_t n, i, j;
    if (!f) {
        snprintf(msg, sizeof msg, "Cannot open %s", path);
        rad_msgbox(msg);
        return;
    }
    raw = (char *)malloc(MAX_TEXT + 1);
    text = (char *)malloc(MAX_TEXT * 2 + 1);
    n = fread(raw, 1, MAX_TEXT, f);
    raw[n] = 0;
    fclose(f);
    i = (n >= 3 && (unsigned char)raw[0] == 0xEF && (unsigned char)raw[1] == 0xBB && (unsigned char)raw[2] == 0xBF) ? 3 : 0;
    for (j = 0; i < n; i++) {                 /* LF -> CR LF (a Windows edit box needs CR LF) */
        if (raw[i] == '\n' && (i == 0 || raw[i - 1] != '\r')) text[j++] = '\r';
        text[j++] = raw[i];
    }
    text[j] = 0;
    loading = 1;
    rad_set("txtDoc", "Text", text);
    loading = 0;
    strncpy(file_name, path, sizeof file_name - 1);
    dirty = 0;
    update_title();
    snprintf(msg, sizeof msg, n == MAX_TEXT ? "Opened %s (only the first %u bytes)" : "Opened %s (%u bytes)",
             base_name(path), (unsigned)n);
    status(msg);
    free(raw);
    free(text);
}

/* ------------------------------------------------------------------ clipboard (Win32) */
static void clipboard_put(const char *utf8)
{
#ifdef _WIN32
    int n = MultiByteToWideChar(CP_UTF8, 0, utf8, -1, NULL, 0);
    HGLOBAL mem = GlobalAlloc(GMEM_MOVEABLE, (SIZE_T)n * sizeof(wchar_t));
    if (!mem) return;
    MultiByteToWideChar(CP_UTF8, 0, utf8, -1, (wchar_t *)GlobalLock(mem), n);
    GlobalUnlock(mem);
    if (OpenClipboard(NULL)) {
        EmptyClipboard();
        SetClipboardData(CF_UNICODETEXT, mem);
        CloseClipboard();
    } else {
        GlobalFree(mem);
    }
#else
    (void)utf8;
#endif
}

static char *clipboard_get(void)      /* malloc'ed UTF-8 text or NULL */
{
    char *out = NULL;
#ifdef _WIN32
    if (OpenClipboard(NULL)) {
        HANDLE h = GetClipboardData(CF_UNICODETEXT);
        if (h) {
            const wchar_t *w = (const wchar_t *)GlobalLock(h);
            int n = WideCharToMultiByte(CP_UTF8, 0, w, -1, NULL, 0, NULL, NULL);
            out = (char *)malloc((size_t)n + 1);
            WideCharToMultiByte(CP_UTF8, 0, w, -1, out, n, NULL, NULL);
            GlobalUnlock(h);
        }
        CloseClipboard();
    }
#endif
    return out;
}

/* ------------------------------------------------------------------ find */
static int find_next(void)
{
    const char *text = rad_get("txtDoc", "Text");
    int from_ch = (int)rad_get_num("txtDoc", "SelStart") + (int)rad_get_num("txtDoc", "SelLength");
    const char *hit;
    char msg[400];
    if (!*find_what) return 0;
    hit = strstr(text + utf8_bytes(text, from_ch), find_what);
    if (!hit) hit = strstr(text, find_what);           /* wrap around */
    if (!hit) {
        snprintf(msg, sizeof msg, "Cannot find \"%s\"", find_what);
        status(msg);
        return 0;
    }
    rad_set_num("txtDoc", "SelStart", utf8_chars(text, (int)(hit - text)));
    rad_set_num("txtDoc", "SelLength", utf8_chars(find_what, (int)strlen(find_what)));
    rad_call("txtDoc", "SetFocus", "");
    snprintf(msg, sizeof msg, "Found \"%s\" at character %d", find_what, utf8_chars(text, (int)(hit - text)) + 1);
    status(msg);
    return 1;
}

/* ------------------------------------------------------------------ events */
void frmMain_Load(void)
{
    update_title();
    status("Ready - File > Open to load a text file");
}

void txtDoc_TextChanged(void)
{
    if (loading || dirty) return;
    dirty = 1;
    update_title();
}

void mnuNew_Click(void)
{
    if (!confirm_discard()) return;
    loading = 1;
    rad_set("txtDoc", "Text", "");
    loading = 0;
    file_name[0] = 0;
    dirty = 0;
    update_title();
    status("New document");
}

void mnuOpen_Click(void)
{
    char path[1024];
    if (!confirm_discard()) return;
    if (strcmp(rad_call("dlgOpen", "ShowOpen", ""), "OK") != 0) return;
    strncpy(path, rad_get("dlgOpen", "FileName"), sizeof path - 1);
    path[sizeof path - 1] = 0;
    if (*path) open_file(path);
}

void mnuSaveAs_Click(void)
{
    char path[1024];
    rad_set("dlgSave", "FileName", *file_name ? base_name(file_name) : "Untitled.txt");
    if (strcmp(rad_call("dlgSave", "ShowSave", ""), "OK") != 0) return;
    strncpy(path, rad_get("dlgSave", "FileName"), sizeof path - 1);
    path[sizeof path - 1] = 0;
    if (*path) write_file(path);
}

void mnuSave_Click(void)
{
    if (*file_name) write_file(file_name);
    else mnuSaveAs_Click();
}

void mnuExit_Click(void)
{
    if (confirm_discard()) rad_end();
}

void mnuCut_Click(void)
{
    char sel[MAX_TEXT];
    strncpy(sel, rad_get("txtDoc", "SelText"), sizeof sel - 1);
    sel[sizeof sel - 1] = 0;
    if (!*sel) return;
    clipboard_put(sel);
    rad_set("txtDoc", "SelText", "");
    status("Cut to the clipboard");
}

void mnuCopy_Click(void)
{
    const char *sel = rad_get("txtDoc", "SelText");
    if (!*sel) { status("Nothing selected"); return; }
    clipboard_put(sel);
    status("Copied to the clipboard");
}

void mnuPaste_Click(void)
{
    char *clip = clipboard_get();
    if (!clip) { status("The clipboard has no text"); return; }
    rad_set("txtDoc", "SelText", clip);
    free(clip);
    status("Pasted");
}

void mnuSelectAll_Click(void)
{
    rad_set_num("txtDoc", "SelStart", 0);
    rad_set_num("txtDoc", "SelLength", utf8_chars(rad_get("txtDoc", "Text"), MAX_TEXT * 2));
    rad_call("txtDoc", "SetFocus", "");
}

void mnuFind_Click(void)
{
    const char *w = rad_input("Find what:");
    if (!w || !*w) return;
    strncpy(find_what, w, sizeof find_what - 1);
    find_what[sizeof find_what - 1] = 0;
    rad_set_num("txtDoc", "SelLength", 0);
    find_next();
}

void mnuFindNext_Click(void)
{
    if (!*find_what) mnuFind_Click();
    else find_next();
}

void mnuReplace_Click(void)
{
    char what[256], with[256], *text, *out, *p, *q, msg[300];
    int count = 0;
    size_t lw, lr;
    strncpy(what, rad_input("Replace what:"), sizeof what - 1);
    what[sizeof what - 1] = 0;
    if (!*what) return;
    strncpy(with, rad_input("Replace with:"), sizeof with - 1);
    with[sizeof with - 1] = 0;
    text = strdup(rad_get("txtDoc", "Text"));
    lw = strlen(what);
    lr = strlen(with);
    out = (char *)malloc(strlen(text) + (strlen(text) / lw + 1) * lr + 1);   /* worst case: every match grows */
    for (p = text, q = out; *p;) {               /* replace every occurrence */
        if (strncmp(p, what, lw) == 0) {
            memcpy(q, with, lr);
            q += lr;
            p += lw;
            count++;
        } else {
            *q++ = *p++;
        }
    }
    *q = 0;
    if (count) rad_set("txtDoc", "Text", out);
    snprintf(msg, sizeof msg, "%d replacement(s)", count);
    status(msg);
    free(text);
    free(out);
}

void mnuTimeDate_Click(void)
{
    char buf[64];
    time_t now = time(NULL);
    strftime(buf, sizeof buf, "%H:%M %Y-%m-%d", localtime(&now));
    rad_set("txtDoc", "SelText", buf);
}

void mnuFont_Click(void)
{
    char msg[300];
    rad_set("dlgFont", "FontName", rad_get("txtDoc", "FontName"));
    rad_set("dlgFont", "FontSize", rad_get("txtDoc", "FontSize"));
    if (strcmp(rad_call("dlgFont", "ShowFont", ""), "OK") != 0) return;
    rad_set("txtDoc", "FontName", rad_get("dlgFont", "FontName"));
    rad_set("txtDoc", "FontSize", rad_get("dlgFont", "FontSize"));
    snprintf(msg, sizeof msg, "Font: %s %s pt", rad_get("txtDoc", "FontName"), rad_get("txtDoc", "FontSize"));
    status(msg);
}

void mnuWordCount_Click(void)
{
    const char *t = rad_get("txtDoc", "Text");
    int words = 0, lines = *t ? 1 : 0, chars = 0, in_word = 0;
    char msg[200];
    for (; *t; t++) {
        if (((unsigned char)*t & 0xC0) != 0x80 && *t != '\r' && *t != '\n') chars++;
        if (*t == '\n') lines++;
        if (*t == ' ' || *t == '\t' || *t == '\r' || *t == '\n') in_word = 0;
        else if (!in_word) { in_word = 1; words++; }
    }
    snprintf(msg, sizeof msg, "%d words, %d lines, %d characters", words, lines, chars);
    status(msg);
    rad_msgbox(msg);
}

void mnuAbout_Click(void)
{
    rad_msgbox("Notepad - a RAD IDE example in C\n(c) 2026 Musoftware - MIT License");
}

void frmMain_FormClosing(void)
{
    if (dirty) rad_print("Notepad closed with unsaved changes");
}
