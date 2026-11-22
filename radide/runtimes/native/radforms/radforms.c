/* radforms - tiny Win32 forms runtime of RAD IDE native builds. See radforms.h.
 * C99, Win32 W APIs only (user32 gdi32 comctl32 comdlg32 shell32 ole32; gdiplus.dll is loaded only
 * when a PNG / JPG image is shown). Build: gcc -Os -municode? no: plain main();
 *   gcc -std=c99 -Os -s -mwindows -ffunction-sections -fdata-sections -Wl,--gc-sections
 *       app.c radforms.c app.res -lcomctl32 -lcomdlg32 -lgdi32 -lole32 -luuid -lshell32
 */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0601
#endif
#ifndef WINVER
#define WINVER 0x0601
#endif
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include <windows.h>
#include <windowsx.h>
#include <commctrl.h>
#include <commdlg.h>
#include <shlobj.h>
#include <ole2.h>

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "radforms.h"

#ifdef _MSC_VER                     /* MSVC / NativeAOT users: the system import libraries */
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "comdlg32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "ole32.lib")
#endif

#ifndef WM_DPICHANGED
#define WM_DPICHANGED 0x02E0
#endif
#ifndef SS_REALSIZECONTROL
#define SS_REALSIZECONTROL 0x40
#endif

/* ================================================================== types */
enum {
    T_FORM, T_BUTTON, T_LABEL, T_TEXTBOX, T_CHECKBOX, T_RADIO, T_LISTBOX, T_COMBOBOX, T_PICTURE,
    T_PROGRESS, T_UPDOWN, T_TRACKBAR, T_PANEL, T_GROUPBOX, T_TAB, T_LINK, T_STATUS, T_TIMER,
    T_MENUITEM, T_TOOLBTN, T_DLG_OPEN, T_DLG_SAVE, T_DLG_COLOR, T_DLG_FONT, T_DLG_FOLDER, T_CUSTOM, T_COUNT
};
static const char *const TYPE_NAMES[T_COUNT] = {
    "Form", "Button", "Label", "TextBox", "CheckBox", "RadioButton", "ListBox", "ComboBox", "PictureBox",
    "ProgressBar", "NumericUpDown", "TrackBar", "Panel", "GroupBox", "TabControl", "LinkLabel", "StatusBar",
    "Timer", "MenuItem", "ToolButton", "OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog",
    "FolderBrowserDialog", "Custom"};

#define NONVISUAL(t) ((t) == T_TIMER || ((t) >= T_DLG_OPEN && (t) <= T_DLG_FOLDER) || (t) == T_MENUITEM || (t) == T_TOOLBTN)
#define CONTAINER(t) ((t) == T_PANEL || (t) == T_GROUPBOX || (t) == T_TAB)
/* the same for a control (registered classes have flags) */
#define CNONVIS(c) (NONVISUAL((c)->type) || ((c)->type == T_CUSTOM && ((c)->cls->flags & RF_CLASS_NONVISUAL)))
#define CCONT(c) (CONTAINER((c)->type) || ((c)->type == T_CUSTOM && ((c)->cls->flags & RF_CLASS_CONTAINER)))
#define COWNER(c) ((c)->type == T_CUSTOM && ((c)->cls->flags & RF_CLASS_OWNERDRAW))
#define MAGIC_CTL 0x4C544352     /* "RCTL" */
#define MAGIC_FORM 0x4D524652    /* "RFRM" */

typedef struct KV { struct KV *next; char *key; char *val; } KV;

struct RfForm;
typedef struct RfCtl {
    int magic;                      /* MAGIC_CTL: rf_handle check */
    struct RfCtl *next;
    struct RfForm *form;
    struct RfCtl *parent;           /* container, NULL = the form */
    int type;
    char name[64];
    HWND hwnd, buddy, inner;        /* buddy: up-down arrows; inner: edit of a drop-down combo */
    float pl[8];                    /* x y w h rx ry rw rh */
    int page;                       /* TabControl page of a child */
    int visible, enabled;
    int has_fore, has_back;
    COLORREF fore, back;
    HBRUSH brush;
    wchar_t font_name[LF_FACESIZE];
    float font_size;
    int bold, italic, underline;
    HFONT font;
    HBITMAP image;
    int align;                      /* 0 left 1 center 2 right */
    int multiline, readonly, password, maxlen, dropstyle;
    int minv, maxv, value;          /* progress / trackbar / up-down; timer: interval in value */
    int timer_on, id;
    HMENU menu;                     /* menu item: the menu that holds it */
    int checked, tracking, last_sel;
    KV *kv;                         /* other properties (Tag, dialog properties, ToolTip ...) */
    const rf_class *cls;            /* T_CUSTOM: its registered class */
    void *state;                    /* T_CUSTOM: what cls->create returned */
    int hot, pressed, focused;      /* owner-drawn: mouse / keyboard state */
    double hover, pressv;           /* owner-drawn: animated 0..1 */
    int paged, cpage;               /* registered container: rf_set_page was called / shown page */
    int has_child_back;             /* registered container: rf_set_child_back colour */
    COLORREF child_back;
    HBRUSH child_brush;
} RfCtl;

typedef struct RfForm {
    int magic;                      /* MAGIC_FORM */
    char name[64];
    int first_line, last_line;      /* description lines of the form */
    int loaded, want_visible, shown_once, cancel, modal;
    HWND hwnd, tips, toolbar;
    HMENU menu;
    RfCtl *ctls;
    int dpi;
    int design_w, design_h;
    int center, maximized, unit;    /* unit: 15 = twips (ScaleMode) */
    int has_back;
    COLORREF back;
    HBRUSH brush;
    int next_id;
    int alpha_set;                  /* Opacity was set (layered window) */
    double opacity;
    void *fx;                       /* animations / visual states / layout variants (radforms_motion.inc) */
} RfForm;

typedef struct Ev {
    RfForm *form;
    char obj[64], ev[32], args[160];
    int after, vk, delta;
} Ev;
enum { AFTER_NONE, AFTER_SHOW, AFTER_CLOSE, AFTER_QUIT };

/* ================================================================== globals */
char rad_obj[256] = "";
char rad_ev[256] = "";
char rad_args[1024] = "";

static HINSTANCE g_inst;
static char *g_def;                 /* own copy of the description, split in place */
static char **g_fields;             /* g_fields[line * NF + i] */
static int g_nlines;
#define NF 10
static RfForm *g_forms;
static int g_nforms;
static RfForm *g_startup;
static wchar_t g_app[160] = L"";
static char **g_handlers;
static int g_nhandlers = -1;        /* -1 = report every event */
static rad_dispatch_fn g_dispatch;
static Ev g_q[512];
static int g_qh, g_qn;
static Ev g_cur;
static int g_in_event, g_started, g_quit, g_end_req, g_building, g_inited;
static char g_err[512];
static HBRUSH g_white;

typedef struct Fn { struct Fn *next; char *name; rad_func_fn fn; } Fn;
static Fn *g_funcs;

#define MENU_BASE 40000
#define TIMER_BASE 1000
#define TB_BASE 30000
#define TOOLSTRIP_H 26
#define TAB_PAGE_X 2
#define TAB_PAGE_Y 24

static void rf_layout(RfForm *f, RfCtl *container);
static void rf_set(RfForm *f, RfCtl *c, const char *prop, const char *value);
static const char *rf_get(RfForm *f, RfCtl *c, const char *prop);
static void rf_form_load(RfForm *f, int show);
static void rf_form_show_now(RfForm *f);
static void rf_after(RfForm *f, int after);
static LRESULT CALLBACK rf_form_proc(HWND h, UINT m, WPARAM w, LPARAM l);
static LRESULT CALLBACK rf_sub_proc(HWND h, UINT m, WPARAM w, LPARAM l, UINT_PTR id, DWORD_PTR ref);
static void rf_apply_visible(RfCtl *c);
static LRESULT CALLBACK rf_custom_proc(HWND h, UINT m, WPARAM w, LPARAM l);
static void rf_theme_ctl(RfCtl *c);
static void rf_theme_form(RfForm *f);
static void rf_init_registry(void);
static void rf_init_themes(void);
static void rf_modules(void);
static int rf_has_rtl(const wchar_t *w);
/* radforms_motion.inc (animations, visual states, layout variants) */
static void rf_fx_init(struct RfForm *f);
static void rf_fx_free(struct RfForm *f);
static void rf_fx_start(struct RfForm *f);
static int rf_fx_timer(struct RfForm *f, WPARAM id);
static void rf_fx_event(struct RfForm *f, const char *obj, const char *ev);
static int rf_fx_set_hook(struct RfForm *f, RfCtl *c, const char *p, const char *v);
static void rf_fx_after_set(struct RfForm *f, RfCtl *c, const char *p, const char *v);
static const char *rf_fx_call(struct RfForm *f, RfCtl *c, const char *m, const char *args, int *handled);
static int rf_fx_variants(struct RfForm *f, int notify);
static int rf_is(const char *p, const char *a);
static int g_themed;                /* a theme other than "Light" (the system look) is active */
static const rf_theme *g_theme;
static HBRUSH g_theme_brush, g_input_brush;
static rf_event_fn g_evfn;
static void *g_evuser;

/* ================================================================== small helpers */
static int rf_ieq(const char *a, const char *b) {
    for (; *a && *b; a++, b++) {
        int x = (unsigned char)*a, y = (unsigned char)*b;
        if (x >= 'A' && x <= 'Z') x += 32;
        if (y >= 'A' && y <= 'Z') y += 32;
        if (x != y) return 0;
    }
    return *a == *b;
}

static char *rf_strdup(const char *s) {
    size_t n = strlen(s ? s : "") + 1;
    char *p = (char *)malloc(n);
    if (p) memcpy(p, s ? s : "", n);
    return p;
}

static void rf_copy(char *dst, const char *src, size_t cap) {
    size_t n = strlen(src ? src : "");
    if (n >= cap) n = cap - 1;
    memcpy(dst, src ? src : "", n);
    dst[n] = 0;
}

#define RING 16
static char *g_ring[RING];
static size_t g_ringcap[RING];
static int g_ringpos;

static char *rf_buf(size_t n) {
    int i = g_ringpos;
    g_ringpos = (g_ringpos + 1) % RING;
    if (n < 256) n = 256;
    if (g_ringcap[i] < n) {
        char *p = (char *)realloc(g_ring[i], n);
        if (!p) { static char empty[1]; empty[0] = 0; return empty; }
        g_ring[i] = p;
        g_ringcap[i] = n;
    }
    g_ring[i][0] = 0;
    return g_ring[i];
}

static wchar_t *rf_wide(const char *s) {         /* malloc'd UTF-16 copy; free() it */
    int n;
    wchar_t *w;
    if (!s) s = "";
    n = MultiByteToWideChar(CP_UTF8, 0, s, -1, NULL, 0);
    w = (wchar_t *)malloc(sizeof(wchar_t) * (n > 0 ? n : 1));
    if (!w) return NULL;
    if (n <= 0 || !MultiByteToWideChar(CP_UTF8, 0, s, -1, w, n)) w[0] = 0;
    return w;
}

static char *rf_utf8(const wchar_t *w) {          /* ring buffer UTF-8 copy */
    int n = WideCharToMultiByte(CP_UTF8, 0, w ? w : L"", -1, NULL, 0, NULL, NULL);
    char *s = rf_buf((size_t)(n > 0 ? n : 1));
    if (n <= 0 || !WideCharToMultiByte(CP_UTF8, 0, w ? w : L"", -1, s, n, NULL, NULL)) s[0] = 0;
    return s;
}

static int rf_bool(const char *v) {
    if (!v) return 0;
    while (*v == ' ') v++;
    if (rf_ieq(v, "true") || rf_ieq(v, "yes") || rf_ieq(v, "on")) return 1;
    if (rf_ieq(v, "false") || rf_ieq(v, "no") || rf_ieq(v, "off") || !*v) return 0;
    return rad_num(v) != 0;
}

static int rf_int(const char *v) { double d = rad_num(v); return (int)(d < 0 ? d - 0.5 : d + 0.5); }

static const char *rf_tf(int b) { return b ? "True" : "False"; }

static const char *rf_istr(long long v) {
    char *b = rf_buf(32);
    snprintf(b, 32, "%lld", v);
    return b;
}

/* "#RRGGBB", VB number (&HBBGGRR / decimal, high bit = system colour), "" -> 0 = default */
static int rf_color(const char *v, COLORREF *out) {
    long long n;
    while (v && *v == ' ') v++;
    if (!v || !*v) return 0;
    if (*v == '#') {
        unsigned r = 0, g = 0, b = 0;
        size_t len = strlen(v + 1);
        if (len >= 8) v += 2;                    /* #AARRGGBB */
        if (sscanf(v + 1, "%2x%2x%2x", &r, &g, &b) != 3) return 0;
        *out = RGB(r, g, b);
        return 1;
    }
    if ((v[0] == '&' && (v[1] == 'H' || v[1] == 'h')))
        n = strtoll(v + 2, NULL, 16);
    else if (v[0] == '0' && (v[1] == 'x' || v[1] == 'X'))
        n = strtoll(v + 2, NULL, 16);
    else {
        static const struct { const char *n; COLORREF c; } names[] = {
            {"black", RGB(0, 0, 0)}, {"white", RGB(255, 255, 255)}, {"red", RGB(255, 0, 0)},
            {"green", RGB(0, 128, 0)}, {"blue", RGB(0, 0, 255)}, {"yellow", RGB(255, 255, 0)},
            {"gray", RGB(128, 128, 128)}, {"grey", RGB(128, 128, 128)}, {"orange", RGB(255, 165, 0)},
            {"navy", RGB(0, 0, 128)}, {"silver", RGB(192, 192, 192)}, {"lime", RGB(0, 255, 0)}};
        size_t i;
        for (i = 0; i < sizeof names / sizeof names[0]; i++)
            if (rf_ieq(v, names[i].n)) { *out = names[i].c; return 1; }
        n = (long long)rad_num(v);
    }
    if (n & 0x80000000LL || n < 0) return 0;
    *out = (COLORREF)(n & 0xFFFFFF);
    return 1;
}

/* ================================================================== description */
static void rf_unescape(char *s) {
    char *o = s;
    for (; *s; s++) {
        if (*s == '\\' && s[1]) {
            s++;
            *o++ = *s == 't' ? '\t' : *s == 'n' ? '\n' : *s == 'r' ? '\r' : *s;
        } else {
            *o++ = *s;
        }
    }
    *o = 0;
}

static const char *F(int line, int i) {
    const char *v = g_fields[line * NF + i];
    return v ? v : "";
}

int rad_forms_load(const char *text) {
    char *p;
    int cap = 64, i;
    if (!text || strncmp(text, "RADF", 4) != 0) return 0;
    free(g_def);
    free(g_fields);
    g_def = rf_strdup(text);
    g_fields = (char **)calloc((size_t)cap * NF, sizeof(char *));
    g_nlines = 0;
    for (p = g_def; p && *p;) {
        char *nl = strchr(p, '\n'), *q = p;
        int k = 0;
        if (nl) *nl = 0;
        if (g_nlines >= cap) {
            char **nf = (char **)realloc(g_fields, (size_t)cap * 2 * NF * sizeof(char *));
            if (!nf) break;
            memset(nf + (size_t)cap * NF, 0, (size_t)cap * NF * sizeof(char *));
            g_fields = nf;
            cap *= 2;
        }
        {
            size_t n = strlen(p);
            if (n && p[n - 1] == '\r') p[n - 1] = 0;
        }
        while (q && k < NF) {
            char *tab = strchr(q, '\t');
            if (tab) *tab = 0;
            rf_unescape(q);
            g_fields[g_nlines * NF + k++] = q;
            q = tab ? tab + 1 : NULL;
        }
        g_nlines++;
        p = nl ? nl + 1 : NULL;
    }
    /* forms */
    free(g_forms);
    g_nforms = 0;
    for (i = 0; i < g_nlines; i++)
        if (strcmp(F(i, 0), "F") == 0) g_nforms++;
    g_forms = (RfForm *)calloc((size_t)(g_nforms ? g_nforms : 1), sizeof(RfForm));
    g_nforms = 0;
    g_startup = NULL;
    for (i = 0; i < g_nlines; i++) {
        const char *k = F(i, 0);
        if (strcmp(k, "F") == 0) {
            RfForm *f = &g_forms[g_nforms++];
            f->magic = MAGIC_FORM;
            rf_copy(f->name, F(i, 1), sizeof f->name);
            f->first_line = i + 1;
            f->last_line = g_nlines;
            if (g_nforms > 1) g_forms[g_nforms - 2].last_line = i;
        } else if (strcmp(k, "A") == 0) {
            wchar_t *w = rf_wide(F(i, 1));
            if (w) { wcsncpy(g_app, w, 159); g_app[159] = 0; free(w); }
        }
    }
    for (i = 0; i < g_nlines; i++)
        if (strcmp(F(i, 0), "S") == 0) {
            int j;
            for (j = 0; j < g_nforms; j++)
                if (rf_ieq(g_forms[j].name, F(i, 1))) g_startup = &g_forms[j];
        }
    if (!g_startup && g_nforms) g_startup = &g_forms[0];
    return 1;
}

static void rf_load_resource(void) {
    HRSRC r;
    HGLOBAL g;
    DWORD n;
    char *text;
    if (g_def) return;
    r = FindResourceW(NULL, L"RADFORMS", MAKEINTRESOURCEW(10));      /* RT_RCDATA */
    if (!r || !(g = LoadResource(NULL, r))) return;
    n = SizeofResource(NULL, r);
    text = (char *)malloc(n + 1);
    if (!text) return;
    memcpy(text, LockResource(g), n);
    text[n] = 0;
    rad_forms_load(text);
    free(text);
}

/* ================================================================== handlers / events */
void rad_handlers(const char *csv) {
    const char *p = csv ? csv : "";
    int n = 1, i = 0;
    if (strcmp(p, "*") == 0) { g_nhandlers = -1; return; }
    for (; *p; p++) n += *p == ',';
    g_handlers = (char **)calloc((size_t)n, sizeof(char *));
    g_nhandlers = 0;
    p = csv ? csv : "";
    while (*p && i < n) {
        const char *e = strchr(p, ',');
        size_t len = e ? (size_t)(e - p) : strlen(p);
        char *h = (char *)malloc(len + 1);
        if (!h) break;
        memcpy(h, p, len);
        h[len] = 0;
        while (len && h[len - 1] == ' ') h[--len] = 0;
        if (*h) g_handlers[i++] = h;
        else free(h);
        if (!e) break;
        p = e + 1;
        while (*p == ' ') p++;
    }
    g_nhandlers = i;
}

static int rf_has_handler(const char *obj, const char *ev) {
    char key[128];
    int i;
    if (g_nhandlers < 0) return 1;
    snprintf(key, sizeof key, "%s_%s", obj, ev);
    for (i = 0; i < g_nhandlers; i++)
        if (rf_ieq(g_handlers[i], key)) return 1;
    return 0;
}

static int rf_coalesce(const char *ev) {
    return strcmp(ev, "Tick") == 0 || strcmp(ev, "MouseMove") == 0 || strcmp(ev, "Resize") == 0;
}

/* report an event (when the program has a handler for it); *after* runs when it is done */
static void rf_post_ex(RfForm *f, const char *obj, const char *ev, const char *args, int after, int vk, int delta) {
    Ev *e;
    if (f && f->fx) rf_fx_event(f, obj, ev);
    if ((g_building && after == AFTER_NONE) || !rf_has_handler(obj, ev)) {
        rf_after(f, after);
        return;
    }
    if (rf_coalesce(ev)) {
        int i;
        for (i = 0; i < g_qn; i++) {
            Ev *q = &g_q[(g_qh + i) % 512];
            if (q->form == f && strcmp(q->ev, ev) == 0 && strcmp(q->obj, obj) == 0) {
                rf_copy(q->args, args, sizeof q->args);
                return;
            }
        }
    }
    if (g_qn >= 512) { rf_after(f, after); return; }
    e = &g_q[(g_qh + g_qn) % 512];
    g_qn++;
    e->form = f;
    rf_copy(e->obj, obj, sizeof e->obj);
    rf_copy(e->ev, ev, sizeof e->ev);
    rf_copy(e->args, args ? args : "", sizeof e->args);
    e->after = after;
    e->vk = vk;
    e->delta = delta;
}

static void rf_post(RfForm *f, const char *obj, const char *ev, const char *args, int after) {
    rf_post_ex(f, obj, ev, args, after, 0, 0);
}

static void rf_post_c(RfCtl *c, const char *ev, const char *args) {
    if (c) rf_post(c->form, c->name, ev, args, AFTER_NONE);
}

/* ================================================================== scaling / fonts */
typedef UINT(WINAPI *GetDpiForWindow_t)(HWND);
static int rf_dpi_of(HWND h) {
    static GetDpiForWindow_t fn;
    static int looked;
    int d = 0;
    if (!looked) {
        looked = 1;
        fn = (GetDpiForWindow_t)(void *)GetProcAddress(GetModuleHandleW(L"user32.dll"), "GetDpiForWindow");
    }
    if (fn && h) d = (int)fn(h);
    if (d <= 0) {
        HDC dc = GetDC(NULL);
        d = GetDeviceCaps(dc, LOGPIXELSY);
        ReleaseDC(NULL, dc);
    }
    return d > 0 ? d : 96;
}

static int S(RfForm *f, double v) { return (int)floor(v * f->dpi / 96.0 + 0.5); }
static double U(RfForm *f, int px) { return px * 96.0 / f->dpi; }

static void rf_make_font(RfCtl *c) {
    LOGFONTW lf;
    HFONT old = c->font;
    memset(&lf, 0, sizeof lf);
    lf.lfHeight = -(LONG)floor(c->font_size * c->form->dpi / 72.0 + 0.5);
    lf.lfWeight = c->bold ? FW_BOLD : FW_NORMAL;
    lf.lfItalic = (BYTE)c->italic;
    lf.lfUnderline = (BYTE)(c->underline || c->type == T_LINK);
    lf.lfCharSet = DEFAULT_CHARSET;
    lf.lfQuality = CLEARTYPE_QUALITY;
    wcsncpy(lf.lfFaceName, c->font_name[0] ? c->font_name : L"Segoe UI", LF_FACESIZE - 1);
    c->font = CreateFontIndirectW(&lf);
    if (c->hwnd) {
        SendMessageW(c->hwnd, WM_SETFONT, (WPARAM)c->font, TRUE);
        if (c->inner) SendMessageW(c->inner, WM_SETFONT, (WPARAM)c->font, TRUE);
    }
    if (old) DeleteObject(old);
}

/* ================================================================== objects */
static RfCtl *rf_ctl_in(RfForm *f, const char *name) {
    RfCtl *c;
    for (c = f->ctls; c; c = c->next)
        if (rf_ieq(c->name, name)) return c;
    return NULL;
}

static RfForm *rf_form_named(const char *name) {
    int i;
    for (i = 0; i < g_nforms; i++)
        if (rf_ieq(g_forms[i].name, name)) return &g_forms[i];
    return NULL;
}

static int rf_form_defines(RfForm *f, const char *name) {
    int i;
    for (i = f->first_line; i < f->last_line; i++) {
        const char *k = F(i, 0);
        if ((k[0] == 'C' && rf_ieq(F(i, 2), name)) || (k[0] == 'M' && rf_ieq(F(i, 2), name)) ||
            (k[0] == 'T' && rf_ieq(F(i, 1), name)))
            return 1;
    }
    return 0;
}

/* "Control", "Form" or "Form.Control" -> form (+ control, NULL for the form itself) */
static RfForm *rf_resolve(const char *path, RfCtl **out) {
    char a[128];
    const char *dot;
    RfForm *f;
    int i;
    *out = NULL;
    if (!g_inited) rad_init();
    if (!path) return NULL;
    while (*path == ' ') path++;
    dot = strchr(path, '.');
    rf_copy(a, path, dot && (size_t)(dot - path) < sizeof a ? (size_t)(dot - path) + 1 : sizeof a);
    if ((f = rf_form_named(a)) != NULL) {
        if (!f->loaded) rf_form_load(f, 0);
        if (!dot) return f;
        *out = rf_ctl_in(f, dot + 1);
        return *out ? f : NULL;
    }
    if (g_cur.form && g_cur.form->loaded && (*out = rf_ctl_in(g_cur.form, path)) != NULL) return g_cur.form;
    for (i = 0; i < g_nforms; i++)
        if (g_forms[i].loaded && (*out = rf_ctl_in(&g_forms[i], path)) != NULL) return &g_forms[i];
    for (i = 0; i < g_nforms; i++)
        if (!g_forms[i].loaded && rf_form_defines(&g_forms[i], path)) {
            rf_form_load(&g_forms[i], 0);
            if ((*out = rf_ctl_in(&g_forms[i], path)) != NULL) return &g_forms[i];
        }
    return NULL;
}

static RfCtl *rf_ctl_of(HWND h) {
    if (!h) return NULL;
    return (RfCtl *)GetPropW(h, L"radforms.ctl");
}

static RfForm *rf_form_of(HWND h) {
    HWND root = h ? GetAncestor(h, GA_ROOT) : NULL;
    int i;
    for (i = 0; i < g_nforms; i++)
        if (g_forms[i].hwnd && g_forms[i].hwnd == root) return &g_forms[i];
    return NULL;
}

static const char *rf_kv_get(RfCtl *c, const char *key) {
    KV *k;
    for (k = c->kv; k; k = k->next)
        if (rf_ieq(k->key, key)) return k->val;
    return NULL;
}

static void rf_kv_set(RfCtl *c, const char *key, const char *val) {
    KV *k;
    for (k = c->kv; k; k = k->next)
        if (rf_ieq(k->key, key)) {
            free(k->val);
            k->val = rf_strdup(val);
            return;
        }
    k = (KV *)calloc(1, sizeof *k);
    if (!k) return;
    k->key = rf_strdup(key);
    k->val = rf_strdup(val);
    k->next = c->kv;
    c->kv = k;
}

/* ================================================================== window text */
static const char *rf_wtext(HWND h) {
    int n = GetWindowTextLengthW(h);
    wchar_t *w = (wchar_t *)malloc(sizeof(wchar_t) * (size_t)(n + 1));
    const char *s;
    if (!w) return "";
    w[0] = 0;
    GetWindowTextW(h, w, n + 1);
    s = rf_utf8(w);
    free(w);
    return s;
}

static void rf_set_wtext(HWND h, const char *s, int crlf) {
    wchar_t *w;
    if (crlf) {                                  /* multi-line edit: \n -> \r\n */
        size_t n = strlen(s), i, o = 0;
        char *t = (char *)malloc(n * 2 + 1);
        if (!t) return;
        for (i = 0; i < n; i++) {
            if (s[i] == '\n' && (i == 0 || s[i - 1] != '\r')) t[o++] = '\r';
            t[o++] = s[i];
        }
        t[o] = 0;
        w = rf_wide(t);
        free(t);
    } else {
        w = rf_wide(s);
    }
    if (w) { SetWindowTextW(h, w); free(w); }
}

static const char *rf_list_item(RfCtl *c, int i) {
    UINT getlen = c->type == T_LISTBOX ? LB_GETTEXTLEN : CB_GETLBTEXTLEN;
    UINT get = c->type == T_LISTBOX ? LB_GETTEXT : CB_GETLBTEXT;
    LRESULT n = SendMessageW(c->hwnd, getlen, (WPARAM)i, 0);
    wchar_t *w;
    const char *s;
    if (n < 0) return "";
    w = (wchar_t *)malloc(sizeof(wchar_t) * (size_t)(n + 1));
    if (!w) return "";
    w[0] = 0;
    SendMessageW(c->hwnd, get, (WPARAM)i, (LPARAM)w);
    s = rf_utf8(w);
    free(w);
    return s;
}

static int rf_list_count(RfCtl *c) {
    return (int)SendMessageW(c->hwnd, c->type == T_LISTBOX ? LB_GETCOUNT : CB_GETCOUNT, 0, 0);
}

static int rf_list_index(RfCtl *c) {
    return (int)SendMessageW(c->hwnd, c->type == T_LISTBOX ? LB_GETCURSEL : CB_GETCURSEL, 0, 0);
}

static void rf_list_add(RfCtl *c, const char *s, int at) {
    wchar_t *w = rf_wide(s);
    if (!w) return;
    if (c->type == T_LISTBOX)
        SendMessageW(c->hwnd, at < 0 ? LB_ADDSTRING : LB_INSERTSTRING, (WPARAM)(at < 0 ? 0 : at), (LPARAM)w);
    else
        SendMessageW(c->hwnd, at < 0 ? CB_ADDSTRING : CB_INSERTSTRING, (WPARAM)(at < 0 ? 0 : at), (LPARAM)w);
    free(w);
}

static void rf_list_select(RfCtl *c, int i, int notify) {
    int old = rf_list_index(c);
    SendMessageW(c->hwnd, c->type == T_LISTBOX ? LB_SETCURSEL : CB_SETCURSEL, (WPARAM)i, 0);
    c->last_sel = i;
    if (notify && old != i) {
        rf_post_c(c, "SelectedIndexChanged", "");
        if (c->type == T_COMBOBOX) rf_post_c(c, "TextChanged", "");
    }
}

/* ================================================================== geometry */
static void rf_client_logical(RfForm *f, RfCtl *container, double *cw, double *ch, int *ox, int *oy) {
    RECT r;
    HWND h = container ? container->hwnd : f->hwnd;
    GetClientRect(h, &r);
    *cw = U(f, r.right);
    *ch = U(f, r.bottom);
    *ox = *oy = 0;
    if (!container && f->toolbar) {
        *oy = S(f, TOOLSTRIP_H);
        *ch -= TOOLSTRIP_H;
    }
    if (container && container->type == T_TAB) {
        *ox = S(f, TAB_PAGE_X);
        *oy = S(f, TAB_PAGE_Y);
        *cw -= 2 * TAB_PAGE_X;
        *ch -= TAB_PAGE_Y + TAB_PAGE_X;
    }
}

static void rf_place_ctl(RfCtl *c) {
    RfForm *f = c->form;
    double cw, ch;
    int ox, oy, x, y, w, h;
    if (!c->hwnd) return;
    rf_client_logical(f, c->parent, &cw, &ch, &ox, &oy);
    x = S(f, c->pl[0] + c->pl[4] * cw) + ox;
    y = S(f, c->pl[1] + c->pl[5] * ch) + oy;
    w = S(f, c->pl[2] + c->pl[6] * cw);
    h = S(f, c->pl[3] + c->pl[7] * ch);
    if (w < 0) w = 0;
    if (h < 0) h = 0;
    if (c->type == T_COMBOBOX && c->dropstyle != 2) h += S(f, 200);    /* room for the drop-down list */
    if (c->type == T_UPDOWN && c->buddy) {
        int bw = S(f, 18);
        MoveWindow(c->hwnd, x, y, w > bw ? w - bw : w, h, TRUE);
        MoveWindow(c->buddy, x + (w > bw ? w - bw : w), y, bw, h, TRUE);
        return;
    }
    MoveWindow(c->hwnd, x, y, w, h, TRUE);
}

static void rf_layout(RfForm *f, RfCtl *container) {
    RfCtl *c;
    if (!f->hwnd) return;
    for (c = f->ctls; c; c = c->next)
        if (c->parent == container && c->hwnd && !CNONVIS(c)) rf_place_ctl(c);
}

/* design rectangle of a control right now (logical, relative to its container's client origin) */
static void rf_ctl_rect(RfCtl *c, double *x, double *y, double *w, double *h) {
    RfForm *f = c->form;
    double cw = 0, ch = 0;
    int ox = 0, oy = 0;
    if (f->hwnd) rf_client_logical(f, c->parent, &cw, &ch, &ox, &oy);
    *x = c->pl[0] + c->pl[4] * cw;
    *y = c->pl[1] + c->pl[5] * ch;
    *w = c->pl[2] + c->pl[6] * cw;
    *h = c->pl[3] + c->pl[7] * ch;
}

static void rf_set_geo(RfCtl *c, int which, double v) {
    double r[4];
    int i;
    rf_ctl_rect(c, &r[0], &r[1], &r[2], &r[3]);
    r[which] = v;
    for (i = 0; i < 4; i++) { c->pl[i] = (float)r[i]; c->pl[i + 4] = 0; }
    rf_place_ctl(c);
}

/* ================================================================== brushes / colours */
static HBRUSH rf_brush_for(RfCtl *c, COLORREF *color) {
    /* background behind a control: its own colour, else the nearest container's, else the form's */
    RfCtl *p;
    if (c && c->has_back) {
        if (!c->brush) c->brush = CreateSolidBrush(c->back);
        *color = c->back;
        return c->brush;
    }
    for (p = c ? c->parent : NULL; p; p = p->parent) {
        if (p->type == T_TAB && !g_themed) { *color = GetSysColor(COLOR_WINDOW); return g_white; }
        if (p->has_child_back) {
            if (!p->child_brush) p->child_brush = CreateSolidBrush(p->child_back);
            *color = p->child_back;
            return p->child_brush;
        }
        if (p->has_back) {
            if (!p->brush) p->brush = CreateSolidBrush(p->back);
            *color = p->back;
            return p->brush;
        }
    }
    if (c && c->form->has_back) {
        if (!c->form->brush) c->form->brush = CreateSolidBrush(c->form->back);
        *color = c->form->back;
        return c->form->brush;
    }
    if (g_themed && g_theme_brush) { *color = g_theme->window; return g_theme_brush; }
    *color = GetSysColor(COLOR_BTNFACE);
    return GetSysColorBrush(COLOR_BTNFACE);
}

static LRESULT rf_ctlcolor(RfForm *f, UINT msg, HDC dc, HWND child) {
    RfCtl *c = rf_ctl_of(child);
    COLORREF bg;
    HBRUSH br;
    (void)f;
    if (!c) return 0;
    if ((msg == WM_CTLCOLOREDIT || msg == WM_CTLCOLORLISTBOX ||
         (msg == WM_CTLCOLORSTATIC && (c->type == T_TEXTBOX || c->type == T_UPDOWN))) && !c->has_back) {
        if (g_themed && g_input_brush) {
            SetTextColor(dc, c->has_fore ? c->fore : g_theme->input_text);
            SetBkColor(dc, g_theme->input);
            return (LRESULT)g_input_brush;
        }
        if (c->has_fore) SetTextColor(dc, c->fore);
        if (!c->has_fore) return 0;
        SetBkColor(dc, GetSysColor(msg == WM_CTLCOLORSTATIC ? COLOR_BTNFACE : COLOR_WINDOW));
        return (LRESULT)GetSysColorBrush(msg == WM_CTLCOLORSTATIC ? COLOR_BTNFACE : COLOR_WINDOW);
    }
    br = rf_brush_for(c, &bg);
    if (g_themed) SetTextColor(dc, c->enabled ? g_theme->window_text : g_theme->disabled_text);
    if (c->type == T_LINK && !c->has_fore) SetTextColor(dc, g_themed ? g_theme->accent : RGB(0, 0x66, 0xCC));
    if (c->has_fore) SetTextColor(dc, c->fore);
    SetBkColor(dc, bg);
    return (LRESULT)br;
}

/* ================================================================== images (GDI+ loaded on demand) */
typedef struct { UINT32 ver; void *cb; BOOL nothread, nocodecs; } GpInput;
typedef int(WINAPI *GpStartup_t)(ULONG_PTR *, const GpInput *, void *);
typedef int(WINAPI *GpFromStream_t)(IStream *, void **);
typedef int(WINAPI *GpFromFile_t)(const WCHAR *, void **);
typedef int(WINAPI *GpToHbm_t)(void *, HBITMAP *, DWORD);
typedef int(WINAPI *GpToHicon_t)(void *, HICON *);
typedef int(WINAPI *GpDispose_t)(void *);
static HMODULE g_gp;
static GpFromStream_t gp_stream;
static GpFromFile_t gp_file;
static GpToHbm_t gp_hbm;
static GpToHicon_t gp_hicon;
static GpDispose_t gp_dispose;

static int rf_gdiplus(void) {
    static int tried;
    if (g_gp || tried) return g_gp != NULL;
    tried = 1;
    g_gp = LoadLibraryW(L"gdiplus.dll");
    if (g_gp) {
        GpStartup_t st = (GpStartup_t)(void *)GetProcAddress(g_gp, "GdiplusStartup");
        GpInput in = {1, NULL, FALSE, FALSE};
        ULONG_PTR tok;
        gp_stream = (GpFromStream_t)(void *)GetProcAddress(g_gp, "GdipCreateBitmapFromStream");
        gp_file = (GpFromFile_t)(void *)GetProcAddress(g_gp, "GdipCreateBitmapFromFile");
        gp_hbm = (GpToHbm_t)(void *)GetProcAddress(g_gp, "GdipCreateHBITMAPFromBitmap");
        gp_hicon = (GpToHicon_t)(void *)GetProcAddress(g_gp, "GdipCreateHICONFromBitmap");
        gp_dispose = (GpDispose_t)(void *)GetProcAddress(g_gp, "GdipDisposeImage");
        if (!st || !gp_stream || !gp_file || !gp_hbm || !gp_dispose || st(&tok, &in, NULL) != 0) {
            FreeLibrary(g_gp);
            g_gp = NULL;
        }
    }
    return g_gp != NULL;
}

/* GDI+ bitmap of an image: the embedded resource for *path* (I records), else the file
 * (relative paths: next to the exe) */
static void *rf_gp_image(const char *path) {
    void *bmp = NULL;
    int i;
    if (!path || !*path || !rf_gdiplus()) return NULL;
    for (i = 0; i < g_nlines; i++) {
        if (strcmp(F(i, 0), "I") == 0 && rf_ieq(F(i, 1), path)) {
            wchar_t *rn = rf_wide(F(i, 2));
            HRSRC r = rn ? FindResourceW(NULL, rn, MAKEINTRESOURCEW(10)) : NULL;
            free(rn);
            if (r) {
                DWORD n = SizeofResource(NULL, r);
                HGLOBAL mem = GlobalAlloc(GMEM_MOVEABLE, n);
                IStream *st = NULL;
                if (mem) {
                    memcpy(GlobalLock(mem), LockResource(LoadResource(NULL, r)), n);
                    GlobalUnlock(mem);
                    if (CreateStreamOnHGlobal(mem, TRUE, &st) == S_OK) {
                        gp_stream(st, &bmp);
                        st->lpVtbl->Release(st);
                    } else {
                        GlobalFree(mem);
                    }
                }
                if (bmp) return bmp;
            }
        }
    }
    {
        wchar_t full[MAX_PATH * 2], *w = rf_wide(path);
        if (!w) return NULL;
        if (w[0] && w[1] != L':' && w[0] != L'\\' && w[0] != L'/') {
            wchar_t *slash;
            GetModuleFileNameW(NULL, full, MAX_PATH);
            slash = wcsrchr(full, L'\\');
            if (slash) slash[1] = 0;
            wcsncat(full, w, MAX_PATH - 1);
        } else {
            wcsncpy(full, w, MAX_PATH * 2 - 1);
            full[MAX_PATH * 2 - 1] = 0;
        }
        free(w);
        gp_file(full, &bmp);
    }
    return bmp;
}

static HBITMAP rf_load_bitmap(const char *path, COLORREF bg) {
    void *bmp = rf_gp_image(path);
    HBITMAP h = NULL;
    if (!bmp) return NULL;
    gp_hbm(bmp, &h, 0xFF000000u | ((DWORD)GetRValue(bg) << 16) | ((DWORD)GetGValue(bg) << 8) | GetBValue(bg));
    gp_dispose(bmp);
    return h;
}

static HICON rf_load_icon(const char *path) {
    void *bmp = rf_gp_image(path);
    HICON h = NULL;
    if (!bmp) return NULL;
    if (gp_hicon) gp_hicon(bmp, &h);
    gp_dispose(bmp);
    return h;
}

/* ================================================================== control creation */
static RfCtl *rf_new_ctl(RfForm *f, int type, const char *name, RfCtl *parent) {
    RfCtl *c = (RfCtl *)calloc(1, sizeof *c), **tail;
    if (!c) return NULL;
    c->magic = MAGIC_CTL;
    c->form = f;
    c->type = type;
    c->parent = parent;
    rf_copy(c->name, name, sizeof c->name);
    c->visible = c->enabled = 1;
    c->font_size = 9;
    c->maxv = 100;
    c->value = type == T_TIMER ? 100 : 0;
    c->last_sel = -1;
    c->id = 100 + f->next_id++;
    for (tail = &f->ctls; *tail; tail = &(*tail)->next) {}
    *tail = c;
    return c;
}

#define MAX_CLASSES 128
static rf_class g_classes[MAX_CLASSES];
static int g_nclasses;

/* built-in type code, or T_CUSTOM with *cls = the registered class (a module may replace a built-in) */
static int rf_type_of(const char *name, const rf_class **cls) {
    int i;
    *cls = NULL;
    rf_init_registry();
    for (i = 0; i < g_nclasses; i++)
        if (rf_ieq(g_classes[i].name, name)) {
            if (g_classes[i].flags & RF_CLASS_BUILTIN) break;
            *cls = &g_classes[i];
            return T_CUSTOM;
        }
    for (i = 1; i < T_CUSTOM; i++)
        if (rf_ieq(TYPE_NAMES[i], name)) return i;
    return -1;
}

/* value of a property among the lines [a, b) of a control, or NULL */
static const char *rf_line_prop(int a, int b, const char *key) {
    int i;
    for (i = a; i < b; i++)
        if (strcmp(F(i, 0), "P") == 0 && rf_ieq(F(i, 1), key)) return F(i, 2);
    return NULL;
}

/* "radforms.name" = global atom of the object name: lets test / automation tools of other processes find a
 * control by name (GetPropW + GlobalGetAtomNameW) */
static void rf_name_prop(HWND h, const char *name) {
    wchar_t *w = rf_wide(name);
    if (w) {
        ATOM a = GlobalAddAtomW(w);
        if (a) SetPropW(h, L"radforms.name", (HANDLE)(UINT_PTR)a);
        free(w);
    }
}

static void rf_name_unprop(HWND h) {
    ATOM a = (ATOM)(UINT_PTR)RemovePropW(h, L"radforms.name");
    if (a) GlobalDeleteAtom(a);
}

static void rf_subclass(RfCtl *c, HWND h) {
    SetPropW(h, L"radforms.ctl", (HANDLE)c);
    rf_name_prop(h, c->name);
    SetWindowSubclass(h, rf_sub_proc, 1, (DWORD_PTR)c);
}

/* ------------------------------------------------------------------ accessibility (screen readers, UI Automation)
 * Standard controls are named by Windows (button / check box text, the label before an edit). The owner-drawn
 * registered classes (Rm*) and controls with an AccessibleName / AccessibleDescription get a name, role, value and
 * checked state through Dynamic Annotation (IAccPropServices of oleacc, created through COM - no import library):
 * the MSAA proxy of UI Automation reports them (Narrator, NVDA, JAWS, test tools). Declared here so no oleacc.h /
 * -loleacc is needed by the toolchains that compile radforms (MinGW gcc, Go cgo, Rust cc). */
typedef struct RfAccProps RfAccProps;
typedef struct RfAccPropsVtbl {
    HRESULT (STDMETHODCALLTYPE *QueryInterface)(RfAccProps *, REFIID, void **);
    ULONG (STDMETHODCALLTYPE *AddRef)(RfAccProps *);
    ULONG (STDMETHODCALLTYPE *Release)(RfAccProps *);
    void *SetPropValue, *SetPropServer, *ClearProps;
    HRESULT (STDMETHODCALLTYPE *SetHwndProp)(RfAccProps *, HWND, DWORD, DWORD, GUID, VARIANT);
    HRESULT (STDMETHODCALLTYPE *SetHwndPropStr)(RfAccProps *, HWND, DWORD, DWORD, GUID, LPCWSTR);
    void *SetHwndPropServer;
    HRESULT (STDMETHODCALLTYPE *ClearHwndProps)(RfAccProps *, HWND, DWORD, DWORD, const GUID *, int);
} RfAccPropsVtbl;
struct RfAccProps { const RfAccPropsVtbl *lpVtbl; };

static const GUID RF_CLSID_AccPropServices = {0xb5f8350b, 0x0548, 0x48b1, {0xa6, 0xee, 0x88, 0xbd, 0x00, 0xb4, 0xa5, 0xe7}};
static const GUID RF_IID_IAccPropServices = {0x6e26e776, 0x04f0, 0x495d, {0x80, 0xe4, 0x33, 0x30, 0x35, 0x2e, 0x31, 0x69}};
static const GUID RF_PROPID_NAME = {0x608d3df8, 0x8128, 0x4aa7, {0xa4, 0x28, 0xf5, 0x5e, 0x49, 0x26, 0x72, 0x91}};
static const GUID RF_PROPID_VALUE = {0x123fe443, 0x211a, 0x4615, {0x95, 0x27, 0xc4, 0x5a, 0x7e, 0x93, 0x71, 0x7a}};
static const GUID RF_PROPID_DESCRIPTION = {0x4d48dfe4, 0xbd3f, 0x491f, {0xa6, 0x48, 0x49, 0x2d, 0x6f, 0x20, 0xc5, 0x88}};
static const GUID RF_PROPID_ROLE = {0xcb905ff2, 0x7bd1, 0x4c05, {0xb3, 0xc8, 0xe6, 0xc2, 0x41, 0x36, 0x4d, 0x70}};
static const GUID RF_PROPID_STATE = {0xa8d4d5b0, 0x0a21, 0x42d0, {0xa5, 0xc0, 0x51, 0x4e, 0x98, 0x4f, 0x45, 0x7b}};
#define RF_OBJID_CLIENT ((DWORD)0xFFFFFFFC)
#define RF_ROLE_GROUPING 0x14
#define RF_ROLE_PANE 0x10
#define RF_ROLE_TOOLBAR 0x16
#define RF_ROLE_STATUSBAR 0x17
#define RF_ROLE_TABLE 0x18
#define RF_ROLE_LIST 0x21
#define RF_ROLE_OUTLINE 0x23
#define RF_ROLE_TEXT 0x2A
#define RF_ROLE_PUSHBUTTON 0x2B
#define RF_ROLE_CHECKBUTTON 0x2C
#define RF_ROLE_RADIOBUTTON 0x2D
#define RF_ROLE_COMBOBOX 0x2E
#define RF_ROLE_PROGRESSBAR 0x30
#define RF_ROLE_SLIDER 0x33
#define RF_ROLE_PAGETABLIST 0x3C
#define RF_STATE_CHECKED 0x10
#define RF_STATE_FOCUSABLE 0x100000

static RfAccProps *rf_acc_services(void) {
    static RfAccProps *svc;
    static int tried;
    if (!tried) {
        tried = 1;
        CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);          /* S_FALSE / changed mode: COM is there */
        if (FAILED(CoCreateInstance(&RF_CLSID_AccPropServices, NULL, CLSCTX_INPROC_SERVER, &RF_IID_IAccPropServices,
                                    (void **)&svc)))
            svc = NULL;
    }
    return svc;
}

/* MSAA role of a registered class by its type name (0 = leave the default "client") */
static int rf_acc_role(const char *t) {
    static const struct { const char *name; int role; } map[] = {
        {"RmButton", RF_ROLE_PUSHBUTTON}, {"RmTile", RF_ROLE_PUSHBUTTON}, {"ButtonX", RF_ROLE_PUSHBUTTON},
        {"RmToggle", RF_ROLE_CHECKBUTTON}, {"RmCheckBox", RF_ROLE_CHECKBUTTON}, {"RmRadioButton", RF_ROLE_RADIOBUTTON},
        {"RmProgress", RF_ROLE_PROGRESSBAR}, {"RmGauge", RF_ROLE_PROGRESSBAR}, {"RmSlider", RF_ROLE_SLIDER},
        {"RmComboBox", RF_ROLE_COMBOBOX}, {"RmDatePicker", RF_ROLE_COMBOBOX}, {"RmTimePicker", RF_ROLE_COMBOBOX},
        {"RmCalendar", RF_ROLE_TABLE}, {"RmGrid", RF_ROLE_TABLE}, {"RmListView", RF_ROLE_LIST},
        {"RmTreeView", RF_ROLE_OUTLINE}, {"RmSideBar", RF_ROLE_OUTLINE}, {"RmRibbon", RF_ROLE_TOOLBAR},
        {"RmStatusBar", RF_ROLE_STATUSBAR}, {"RmTabStrip", RF_ROLE_PAGETABLIST}, {"RmNavigationPane", RF_ROLE_PAGETABLIST},
        {"RmTextBox", RF_ROLE_GROUPING}, {"RmGroupPanel", RF_ROLE_GROUPING}, {"RmPanel", RF_ROLE_PANE},
        {"RmDockPanel", RF_ROLE_PANE}, {"RmDockWindow", RF_ROLE_PANE},
    };
    size_t i;
    if (!t) return 0;
    for (i = 0; i < sizeof map / sizeof map[0]; i++)
        if (rf_ieq(map[i].name, t)) return map[i].role;
    return 0;
}

static void rf_acc_str(RfAccProps *s, HWND h, GUID prop, const char *v) {
    wchar_t *w = rf_wide(v ? v : "");
    if (w) {
        s->lpVtbl->SetHwndPropStr(s, h, RF_OBJID_CLIENT, 0, prop, w);
        free(w);
    }
}

static void rf_acc_int(RfAccProps *s, HWND h, GUID prop, int v) {
    VARIANT var;
    memset(&var, 0, sizeof var);              /* (VariantInit would need oleaut32) */
    var.vt = VT_I4;
    var.lVal = v;
    s->lpVtbl->SetHwndProp(s, h, RF_OBJID_CLIENT, 0, prop, var);
}

/* (re)annotate a control: after it is built and when its AccessibleName / Text / Value / Checked change */
static void rf_acc_apply(RfCtl *c) {
    RfAccProps *s;
    const char *nm, *ds, *text = "";
    char *name = NULL;
    int custom, role;
    HWND inner = NULL;
    if (!c || !c->hwnd) return;
    custom = c->type == T_CUSTOM && c->cls && !(c->cls->flags & RF_CLASS_NONVISUAL);
    nm = rf_kv_get(c, "AccessibleName");
    ds = rf_kv_get(c, "AccessibleDescription");
    if (!custom && !(nm && *nm) && !(ds && *ds)) return;     /* Windows names standard controls itself */
    s = rf_acc_services();
    if (!s) return;
    role = custom ? rf_acc_role(c->cls->name) : 0;
    if (nm && *nm) name = rf_strdup(nm);
    else if (custom) {
        /* an input's Text is its content (the value), not its name: its Watermark or control name */
        int input = rf_ieq(c->cls->name, "RmTextBox") || role == RF_ROLE_COMBOBOX || role == RF_ROLE_SLIDER ||
                    role == RF_ROLE_PROGRESSBAR;
        text = rf_get(c->form, c, input ? "Watermark" : "Text");
        name = rf_strdup(text && *text ? text : c->name);
    }
    if (name) rf_acc_str(s, c->hwnd, RF_PROPID_NAME, name);
    if (ds && *ds) rf_acc_str(s, c->hwnd, RF_PROPID_DESCRIPTION, ds);
    if (role) rf_acc_int(s, c->hwnd, RF_PROPID_ROLE, role);
    if (role == RF_ROLE_SLIDER || role == RF_ROLE_PROGRESSBAR) rf_acc_str(s, c->hwnd, RF_PROPID_VALUE, rf_get(c->form, c, "Value"));
    else if (role == RF_ROLE_COMBOBOX) rf_acc_str(s, c->hwnd, RF_PROPID_VALUE, rf_get(c->form, c, "Text"));
    if (role == RF_ROLE_CHECKBUTTON || role == RF_ROLE_RADIOBUTTON) {
        const char *ck = rf_get(c->form, c, "Checked");
        rf_acc_int(s, c->hwnd, RF_PROPID_STATE, RF_STATE_FOCUSABLE | (ck && rf_bool(ck) ? RF_STATE_CHECKED : 0));
    }
    /* the edit inside a modern text box / combo box has the keyboard focus: it carries the name too */
    if (custom) inner = FindWindowExW(c->hwnd, NULL, L"EDIT", NULL);
    else if (c->inner) inner = c->inner;
    if (inner && name) rf_acc_str(s, inner, RF_PROPID_NAME, name);
    free(name);
}

static int rf_acc_relevant(const char *p) {
    return rf_is(p, "AccessibleName") || rf_is(p, "AccessibleDescription") || rf_is(p, "Text") ||
           rf_is(p, "Caption") || rf_is(p, "Value") || rf_is(p, "Checked") || rf_is(p, "SelectedIndex");
}

static int rf_align_of(const char *v) {
    if (!v) return 0;
    if (strstr(v, "Center") || strstr(v, "center")) return 1;
    if (strstr(v, "Right") || strstr(v, "right")) return 2;
    return 0;
}

static void rf_create_window(RfCtl *c, int a, int b) {
    RfForm *f = c->form;
    HWND parent = c->parent && c->parent->hwnd ? c->parent->hwnd : f->hwnd;
    const wchar_t *cls = L"STATIC";
    DWORD st = WS_CHILD | WS_CLIPSIBLINGS, ex = 0;
    const char *v;
    c->align = rf_align_of(rf_line_prop(a, b, "TextAlign"));
    if (c->type == T_BUTTON && !rf_line_prop(a, b, "TextAlign")) c->align = 1;
    switch (c->type) {
    case T_BUTTON:
        cls = L"BUTTON";
        st |= WS_TABSTOP | BS_PUSHBUTTON | BS_MULTILINE | (c->align == 0 ? BS_LEFT : c->align == 2 ? BS_RIGHT : BS_CENTER);
        break;
    case T_CHECKBOX:
        cls = L"BUTTON";
        st |= WS_TABSTOP | BS_AUTOCHECKBOX;
        break;
    case T_RADIO:
        cls = L"BUTTON";
        st |= WS_TABSTOP | BS_RADIOBUTTON;
        break;
    case T_GROUPBOX:
        cls = L"BUTTON";
        st |= BS_GROUPBOX | WS_CLIPCHILDREN;
        ex |= WS_EX_CONTROLPARENT;
        break;
    case T_LABEL:
    case T_LINK:
        /* a Label's "&Name:" is an access key (UseMnemonic, True by default in VB / WinForms): Alt+N moves the
         * focus to the next control in tab order (IsDialogMessage); "&&" shows "&" */
        v = rf_line_prop(a, b, "UseMnemonic");
        st |= SS_NOTIFY | (c->type == T_LINK || (v && !rf_bool(v)) ? SS_NOPREFIX : 0) |
              (c->align == 1 ? SS_CENTER : c->align == 2 ? SS_RIGHT : SS_LEFT);
        break;
    case T_PICTURE:
        st |= SS_NOTIFY | SS_BITMAP | SS_CENTERIMAGE | SS_REALSIZECONTROL;
        break;
    case T_TEXTBOX:
        cls = L"EDIT";
        ex |= WS_EX_CLIENTEDGE;
        c->multiline = rf_bool(rf_line_prop(a, b, "Multiline"));
        st |= WS_TABSTOP | (c->align == 1 ? ES_CENTER : c->align == 2 ? ES_RIGHT : ES_LEFT);
        if (c->multiline) st |= ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN | WS_VSCROLL;
        else st |= ES_AUTOHSCROLL;
        v = rf_line_prop(a, b, "PasswordChar");
        if (v && *v) st |= ES_PASSWORD;
        break;
    case T_LISTBOX:
        cls = L"LISTBOX";
        ex |= WS_EX_CLIENTEDGE;
        st |= WS_TABSTOP | LBS_NOTIFY | WS_VSCROLL | LBS_NOINTEGRALHEIGHT | LBS_HASSTRINGS;
        break;
    case T_COMBOBOX:
        cls = L"COMBOBOX";
        v = rf_line_prop(a, b, "DropDownStyle");
        c->dropstyle = !v || rf_ieq(v, "DropDownList") ? 0 : rf_ieq(v, "Simple") ? 2 : 1;
        st |= WS_TABSTOP | WS_VSCROLL | CBS_HASSTRINGS | CBS_AUTOHSCROLL |
              (c->dropstyle == 0 ? CBS_DROPDOWNLIST : c->dropstyle == 2 ? CBS_SIMPLE : CBS_DROPDOWN);
        break;
    case T_PROGRESS:
        cls = PROGRESS_CLASSW;
        break;
    case T_TRACKBAR:
        cls = TRACKBAR_CLASSW;
        st |= WS_TABSTOP | TBS_AUTOTICKS | TBS_HORZ;
        break;
    case T_UPDOWN:
        cls = L"EDIT";
        ex |= WS_EX_CLIENTEDGE;
        st |= WS_TABSTOP | ES_AUTOHSCROLL | ES_RIGHT;
        break;
    case T_PANEL:
        cls = L"RadFormsPanel";
        st |= WS_CLIPCHILDREN;
        ex |= WS_EX_CONTROLPARENT;
        v = rf_line_prop(a, b, "BorderStyle");
        if (v && rf_ieq(v, "FixedSingle")) st |= WS_BORDER;
        else if (v && rf_ieq(v, "Fixed3D")) ex |= WS_EX_CLIENTEDGE;
        break;
    case T_TAB:
        cls = WC_TABCONTROLW;
        st |= WS_TABSTOP | WS_CLIPCHILDREN;
        ex |= WS_EX_CONTROLPARENT;
        break;
    case T_STATUS:
        cls = STATUSCLASSNAMEW;
        st |= CCS_NORESIZE | CCS_NOPARENTALIGN | CCS_NODIVIDER;
        break;
    case T_CUSTOM: {
        const rf_class *k = c->cls;
        wchar_t *wc = NULL;
        st |= (DWORD)k->style | ((k->flags & RF_CLASS_FOCUSABLE) ? WS_TABSTOP : 0) |
              ((k->flags & RF_CLASS_CONTAINER) ? WS_CLIPCHILDREN : 0);
        ex |= (DWORD)k->ex_style | ((k->flags & RF_CLASS_CONTAINER) ? WS_EX_CONTROLPARENT : 0);
        if (!(k->flags & RF_CLASS_OWNERDRAW) && k->win_class) wc = rf_wide(k->win_class);
        c->hwnd = CreateWindowExW(ex, wc ? wc : L"RadFormsCustom", L"", st, 0, 0, 10, 10, parent,
                                  (HMENU)(INT_PTR)c->id, g_inst, NULL);
        free(wc);
        if (!c->hwnd) return;
        rf_subclass(c, c->hwnd);
        rf_make_font(c);
        rf_theme_ctl(c);
        if (k->create && !k->create((rf_handle)c, &c->state)) {
            DestroyWindow(c->hwnd);
            c->hwnd = NULL;
        }
        return;
    }
    default:
        break;
    }
    c->hwnd = CreateWindowExW(ex, cls, L"", st, 0, 0, 10, 10, parent, (HMENU)(INT_PTR)c->id, g_inst, NULL);
    if (!c->hwnd) return;
    rf_subclass(c, c->hwnd);
    if (c->type == T_UPDOWN) {
        c->buddy = CreateWindowExW(0, UPDOWN_CLASSW, L"", WS_CHILD | UDS_SETBUDDYINT | UDS_ARROWKEYS |
                                   UDS_NOTHOUSANDS, 0, 0, 10, 10, parent, (HMENU)(INT_PTR)(c->id + 5000), g_inst, NULL);
        SendMessageW(c->buddy, UDM_SETBUDDY, (WPARAM)c->hwnd, 0);
        SendMessageW(c->buddy, UDM_SETRANGE32, 0, 100);
        SetPropW(c->buddy, L"radforms.ctl", (HANDLE)c);
    }
    if (c->type == T_COMBOBOX && c->dropstyle != 0) {
        c->inner = FindWindowExW(c->hwnd, NULL, L"EDIT", NULL);
        if (c->inner) rf_subclass(c, c->inner);
    }
    if (c->type == T_TAB) {
        v = rf_line_prop(a, b, "TabPages");
        if (!v) v = "TabPage1;TabPage2";
        {
            char *pages = rf_strdup(v), *p = pages;
            int i = 0;
            while (p && *p) {
                char *e = strchr(p, ';');
                TCITEMW it;
                wchar_t *w;
                if (e) *e = 0;
                w = rf_wide(p);
                memset(&it, 0, sizeof it);
                it.mask = TCIF_TEXT;
                it.pszText = w;
                SendMessageW(c->hwnd, TCM_INSERTITEMW, (WPARAM)i++, (LPARAM)&it);
                free(w);
                p = e ? e + 1 : NULL;
            }
            free(pages);
        }
    }
    if (c->type == T_STATUS) SendMessageW(c->hwnd, SB_SIMPLE, TRUE, 0);
    if (c->type == T_LINK) SetClassLongPtrW(c->hwnd, GCLP_HCURSOR, (LONG_PTR)LoadCursor(NULL, IDC_HAND));
    rf_make_font(c);
    rf_theme_ctl(c);
}

/* menu bar from the M records of [a, b) */
static void rf_build_menu(RfForm *f, int a, int b) {
    HMENU stack[16];
    int i, depth = -1;
    f->menu = CreateMenu();
    stack[0] = f->menu;
    for (i = a; i < b; i++) {
        int d;
        const char *name, *text;
        if (strcmp(F(i, 0), "M") != 0) continue;
        d = atoi(F(i, 1));
        name = F(i, 2);
        text = F(i, 3);
        if (d < 0 || d > 14) continue;
        if (d > depth + 1) d = depth + 1;
        depth = d;
        {
            int has_kids = i + 1 < b && strcmp(F(i + 1, 0), "M") == 0 && atoi(F(i + 1, 1)) > d;
            HMENU into = stack[d];
            if (strcmp(text, "-") == 0) {
                AppendMenuW(into, MF_SEPARATOR, 0, NULL);
                continue;
            } else {
                wchar_t *w = rf_wide(text);
                RfCtl *c = *name ? rf_new_ctl(f, T_MENUITEM, name, NULL) : NULL;
                if (has_kids) {
                    HMENU sub = CreatePopupMenu();
                    AppendMenuW(into, MF_POPUP | MF_STRING, (UINT_PTR)sub, w);
                    stack[d + 1] = sub;
                    if (c) { c->menu = into; c->id = -(int)GetMenuItemCount(into); }   /* by position */
                } else {
                    UINT id = MENU_BASE + (UINT)f->next_id++;
                    AppendMenuW(into, MF_STRING, id, w);
                    if (c) { c->menu = into; c->id = (int)id; }
                }
                free(w);
            }
        }
    }
    SetMenu(f->hwnd, f->menu);
}

static UINT rf_menu_pos(RfCtl *c, UINT *flag) {
    if (c->id < 0) { *flag = MF_BYPOSITION; return (UINT)(-c->id - 1); }
    *flag = MF_BYCOMMAND;
    return (UINT)c->id;
}

static void rf_build_toolbar(RfForm *f, int a, int b) {
    int i, n = 0;
    f->toolbar = CreateWindowExW(0, TOOLBARCLASSNAMEW, L"", WS_CHILD | WS_VISIBLE | TBSTYLE_FLAT | TBSTYLE_LIST |
                                 CCS_NORESIZE | CCS_NOPARENTALIGN | CCS_NODIVIDER | TBSTYLE_TOOLTIPS,
                                 0, 0, 10, 10, f->hwnd, (HMENU)(INT_PTR)99, g_inst, NULL);
    SendMessageW(f->toolbar, TB_BUTTONSTRUCTSIZE, sizeof(TBBUTTON), 0);
    SendMessageW(f->toolbar, TB_SETBITMAPSIZE, 0, MAKELONG(0, 0));
    SendMessageW(f->toolbar, TB_SETEXTENDEDSTYLE, 0, TBSTYLE_EX_MIXEDBUTTONS);
    for (i = a; i < b; i++) {
        TBBUTTON bt;
        if (strcmp(F(i, 0), "T") != 0) continue;
        memset(&bt, 0, sizeof bt);
        bt.iBitmap = I_IMAGENONE;
        if (strcmp(F(i, 2), "-") == 0) {
            bt.fsStyle = BTNS_SEP;
        } else {
            wchar_t *w = rf_wide(F(i, 2));
            RfCtl *c = rf_new_ctl(f, T_TOOLBTN, F(i, 1), NULL);
            bt.idCommand = TB_BASE + n;
            bt.fsState = TBSTATE_ENABLED;
            bt.fsStyle = BTNS_BUTTON | BTNS_AUTOSIZE | BTNS_SHOWTEXT;
            bt.iString = (INT_PTR)w;
            if (c) c->id = TB_BASE + n;
            SendMessageW(f->toolbar, TB_ADDBUTTONSW, 1, (LPARAM)&bt);
            free(w);
            n++;
            continue;
        }
        SendMessageW(f->toolbar, TB_ADDBUTTONSW, 1, (LPARAM)&bt);
    }
}

static void rf_add_tooltip(RfCtl *c, const char *text) {
    RfForm *f = c->form;
    TOOLINFOW ti;
    wchar_t *w;
    if (!c->hwnd) return;
    if (!f->tips) {
        f->tips = CreateWindowExW(WS_EX_TOPMOST, TOOLTIPS_CLASSW, NULL, WS_POPUP | TTS_ALWAYSTIP | TTS_NOPREFIX,
                                  CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT, CW_USEDEFAULT, f->hwnd, NULL, g_inst, NULL);
        SendMessageW(f->tips, TTM_SETMAXTIPWIDTH, 0, 400);
    }
    w = rf_wide(text);
    memset(&ti, 0, sizeof ti);
    ti.cbSize = sizeof ti;
    ti.uFlags = TTF_IDISHWND | TTF_SUBCLASS;
    ti.hwnd = f->hwnd;
    ti.uId = (UINT_PTR)c->hwnd;
    ti.lpszText = w;
    SendMessageW(f->tips, TTM_DELTOOLW, 0, (LPARAM)&ti);
    if (text && *text) SendMessageW(f->tips, TTM_ADDTOOLW, 0, (LPARAM)&ti);
    free(w);
}

/* ================================================================== forms */
static void rf_register_classes(void) {
    static int done;
    WNDCLASSEXW wc;
    if (done) return;
    done = 1;
    memset(&wc, 0, sizeof wc);
    wc.cbSize = sizeof wc;
    wc.style = CS_DBLCLKS;
    wc.lpfnWndProc = rf_form_proc;
    wc.hInstance = g_inst;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.hIcon = LoadIconW(g_inst, MAKEINTRESOURCEW(1));
    if (!wc.hIcon) wc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
    wc.hbrBackground = NULL;
    wc.lpszClassName = L"RadFormsForm";
    RegisterClassExW(&wc);
    wc.lpfnWndProc = DefWindowProcW;
    wc.hIcon = NULL;
    wc.lpszClassName = L"RadFormsPanel";
    RegisterClassExW(&wc);
    wc.lpfnWndProc = rf_custom_proc;              /* owner-drawn registered classes */
    wc.lpszClassName = L"RadFormsCustom";
    RegisterClassExW(&wc);
}

static void rf_form_size(RfForm *f, int w, int h, int move) {
    RECT r = {0, 0, 0, 0};
    DWORD st = (DWORD)GetWindowLongPtrW(f->hwnd, GWL_STYLE), ex = (DWORD)GetWindowLongPtrW(f->hwnd, GWL_EXSTYLE);
    r.right = S(f, w);
    r.bottom = S(f, h + (f->toolbar ? TOOLSTRIP_H : 0));
    AdjustWindowRectEx(&r, st, f->menu != NULL, ex);
    if (move && f->center) {
        RECT wa;
        HMONITOR mon = MonitorFromWindow(f->hwnd, MONITOR_DEFAULTTOPRIMARY);
        MONITORINFO mi;
        mi.cbSize = sizeof mi;
        GetMonitorInfoW(mon, &mi);
        wa = mi.rcWork;
        SetWindowPos(f->hwnd, NULL, wa.left + ((wa.right - wa.left) - (r.right - r.left)) / 2,
                     wa.top + ((wa.bottom - wa.top) - (r.bottom - r.top)) / 3, r.right - r.left, r.bottom - r.top,
                     SWP_NOZORDER | SWP_NOACTIVATE);
    } else {
        SetWindowPos(f->hwnd, NULL, 0, 0, r.right - r.left, r.bottom - r.top, SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE);
    }
}

static void rf_form_load(RfForm *f, int show) {
    int i, a = f->first_line, b = f->last_line, ctl_start = -1;
    DWORD st = WS_OVERLAPPEDWINDOW | WS_CLIPCHILDREN, ex = WS_EX_CONTROLPARENT;
    const char *v;
    RfCtl *prev_cur = NULL;
    (void)prev_cur;
    if (f->loaded) {
        if (show) { f->want_visible = 1; rf_form_show_now(f); }
        return;
    }
    rf_register_classes();
    f->loaded = 1;
    f->unit = 1;
    f->center = 1;
    f->design_w = 400;
    f->design_h = 300;
    for (i = a; i < b && strcmp(F(i, 0), "C") != 0; i++) {}
    ctl_start = i;
    v = rf_line_prop(a, ctl_start, "FormBorderStyle");
    if (v && (rf_ieq(v, "FixedSingle") || rf_ieq(v, "Fixed3D")))
        st = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_CLIPCHILDREN;
    else if (v && rf_ieq(v, "FixedDialog")) {
        st = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_CLIPCHILDREN;
        ex |= WS_EX_DLGMODALFRAME;
    } else if (v && (rf_ieq(v, "FixedToolWindow") || rf_ieq(v, "SizableToolWindow"))) {
        ex |= WS_EX_TOOLWINDOW;
        st = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_CLIPCHILDREN | (rf_ieq(v, "SizableToolWindow") ? WS_THICKFRAME : 0);
    } else if (v && rf_ieq(v, "None"))
        st = WS_POPUP | WS_CLIPCHILDREN;
    if ((v = rf_line_prop(a, ctl_start, "MaximizeBox")) && !rf_bool(v)) st &= ~(DWORD)WS_MAXIMIZEBOX;
    if ((v = rf_line_prop(a, ctl_start, "MinimizeBox")) && !rf_bool(v)) st &= ~(DWORD)WS_MINIMIZEBOX;
    if ((v = rf_line_prop(a, ctl_start, "ControlBox")) && !rf_bool(v)) st &= ~(DWORD)WS_SYSMENU;
    if ((v = rf_line_prop(a, ctl_start, "TopMost")) && rf_bool(v)) ex |= WS_EX_TOPMOST;
    if ((v = rf_line_prop(a, ctl_start, "RightToLeft")) && (rf_bool(v) || rf_ieq(v, "Yes")))
        ex |= WS_EX_LAYOUTRTL;
    if ((v = rf_line_prop(a, ctl_start, "StartPosition")) && !rf_ieq(v, "CenterScreen") && !rf_ieq(v, "CenterParent"))
        f->center = 0;
    if ((v = rf_line_prop(a, ctl_start, "WindowState")) && rf_ieq(v, "Maximized")) f->maximized = 1;
    if ((v = rf_line_prop(a, ctl_start, "ScaleMode")) && rf_ieq(v, "Twip")) f->unit = 15;
    if ((v = rf_line_prop(a, ctl_start, "Width"))) f->design_w = rf_int(v);
    if ((v = rf_line_prop(a, ctl_start, "Height"))) f->design_h = rf_int(v);
    g_building++;
    f->hwnd = CreateWindowExW(ex, L"RadFormsForm", L"", st, CW_USEDEFAULT, CW_USEDEFAULT, 400, 300,
                              NULL, NULL, g_inst, NULL);
    SetPropW(f->hwnd, L"radforms.form", (HANDLE)f);
    rf_name_prop(f->hwnd, f->name);
    f->dpi = rf_dpi_of(f->hwnd);
    rf_theme_form(f);
    for (i = a; i < ctl_start; i++)
        if (strcmp(F(i, 0), "P") == 0 && !rf_ieq(F(i, 1), "Width") && !rf_ieq(F(i, 1), "Height"))
            rf_set(f, NULL, F(i, 1), F(i, 2));
    for (i = a; i < b; i++)
        if (strcmp(F(i, 0), "M") == 0) { rf_build_menu(f, a, b); break; }
    for (i = a; i < b; i++)
        if (strcmp(F(i, 0), "T") == 0) { rf_build_toolbar(f, a, b); break; }
    rf_form_size(f, f->design_w, f->design_h, 1);
    /* controls */
    for (i = ctl_start; i < b; i++) {
        int t, j, end;
        RfCtl *c, *parent = NULL;
        if (strcmp(F(i, 0), "C") != 0) continue;
        {
            const rf_class *cls;
            t = rf_type_of(F(i, 1), &cls);
            if (t < 0) continue;
            for (end = i + 1; end < b && (strcmp(F(end, 0), "P") == 0 || strcmp(F(end, 0), "L") == 0); end++) {}
            if (*F(i, 3)) parent = rf_ctl_in(f, F(i, 3));
            c = rf_new_ctl(f, t, F(i, 2), parent);
            if (!c) continue;
            c->cls = cls;
        }
        for (j = i + 1; j < end; j++)
            if (strcmp(F(j, 0), "L") == 0) {
                int k;
                for (k = 0; k < 8; k++) c->pl[k] = (float)rad_num(F(j, k + 1));
            }
        if (!CNONVIS(c)) {
            v = rf_line_prop(i + 1, end, "TabPage");
            c->page = v ? rf_int(v) : 0;
            rf_create_window(c, i + 1, end);
        } else if (c->type == T_CUSTOM && c->cls->create) {
            c->cls->create((rf_handle)c, &c->state);
        }
        for (j = i + 1; j < end; j++)
            if (strcmp(F(j, 0), "P") == 0) rf_set(f, c, F(j, 1), F(j, 2));
        if (!CNONVIS(c)) {
            rf_place_ctl(c);
            rf_apply_visible(c);
            rf_acc_apply(c);
        }
        i = end - 1;
    }
    g_building--;
    if (f->toolbar) MoveWindow(f->toolbar, 0, 0, S(f, f->design_w), S(f, TOOLSTRIP_H), TRUE);
    rf_layout(f, NULL);
    rf_fx_init(f);
    if (show) f->want_visible = 1;
    rf_post(f, f->name, "Load", "", show ? AFTER_SHOW : AFTER_NONE);
}

static void rf_form_show_now(RfForm *f) {
    int first = !f->shown_once;
    if (!f->hwnd || !f->want_visible) return;
    f->shown_once = 1;
    if (first && f->maximized) ShowWindow(f->hwnd, SW_SHOWMAXIMIZED);
    else ShowWindow(f->hwnd, SW_SHOW);
    SetForegroundWindow(f->hwnd);
    UpdateWindow(f->hwnd);
    if (first) rf_fx_start(f);
}

static void rf_form_destroy(RfForm *f) {
    RfCtl *c, *n;
    int i, k = 0;
    if (!f->loaded) return;
    rf_fx_free(f);
    for (i = 0; i < g_qn; i++) {         /* drop its queued events (but FormClosed) */
        Ev e = g_q[(g_qh + i) % 512];
        if (e.form != f || strcmp(e.ev, "FormClosed") == 0) g_q[(g_qh + k++) % 512] = e;
    }
    g_qn = k;
    for (c = f->ctls; c; c = n) {
        KV *k, *kn;
        n = c->next;
        if (c->type == T_CUSTOM && c->cls->destroy) c->cls->destroy((rf_handle)c, c->state);
        if (c->timer_on) KillTimer(f->hwnd, TIMER_BASE + (UINT_PTR)c->id);
        if (c->font) DeleteObject(c->font);
        if (c->brush) DeleteObject(c->brush);
        if (c->image) DeleteObject(c->image);
        for (k = c->kv; k; k = kn) { kn = k->next; free(k->key); free(k->val); free(k); }
        free(c);
    }
    f->ctls = NULL;
    if (f->hwnd) DestroyWindow(f->hwnd);
    if (f->brush) DeleteObject(f->brush);
    f->brush = NULL;
    f->hwnd = NULL;
    f->tips = f->toolbar = NULL;
    f->menu = NULL;
    f->loaded = f->want_visible = f->shown_once = 0;
    f->next_id = 0;
}

static void rf_quit_now(void) { g_quit = 1; }

static void rf_form_close_now(RfForm *f) {
    if (f == g_startup) {
        int i;
        for (i = 0; i < g_nforms; i++)
            if (g_forms[i].hwnd) ShowWindow(g_forms[i].hwnd, SW_HIDE);
        f->want_visible = 0;
        rf_post(f, f->name, "FormClosed", "", AFTER_QUIT);
        return;
    }
    if (f->hwnd) ShowWindow(f->hwnd, SW_HIDE);
    f->want_visible = 0;
    rf_post(f, f->name, "FormClosed", "", AFTER_NONE);
    rf_form_destroy(f);
}

static void rf_after(RfForm *f, int after) {
    if (!f) { if (after == AFTER_QUIT) rf_quit_now(); return; }
    switch (after) {
    case AFTER_SHOW: rf_form_show_now(f); break;
    case AFTER_CLOSE:
        if (f->cancel) f->cancel = 0;
        else rf_form_close_now(f);
        break;
    case AFTER_QUIT: rf_quit_now(); break;
    default: break;
    }
}

static void rf_form_hide(RfForm *f) {
    if (!f->loaded) return;
    f->want_visible = 0;
    ShowWindow(f->hwnd, SW_HIDE);
}

/* ================================================================== visibility */
static int rf_tab_sel(RfCtl *tab) { return (int)SendMessageW(tab->hwnd, TCM_GETCURSEL, 0, 0); }

static void rf_apply_visible(RfCtl *c) {
    int show = c->visible;
    if (!c->hwnd) return;
    if (c->parent && c->parent->type == T_TAB && rf_tab_sel(c->parent) != c->page) show = 0;
    if (c->parent && c->parent->paged && (c->parent->cpage == RF_PAGE_NONE ||
                                          (c->parent->cpage >= 0 && c->parent->cpage != c->page))) show = 0;
    ShowWindow(c->hwnd, show ? SW_SHOWNA : SW_HIDE);
    if (c->buddy) ShowWindow(c->buddy, show ? SW_SHOWNA : SW_HIDE);
}

static void rf_tab_changed(RfCtl *tab) {
    RfCtl *c;
    for (c = tab->form->ctls; c; c = c->next)
        if (c->parent == tab) rf_apply_visible(c);
}

/* ================================================================== events from windows */
static const char *rf_keysym(WPARAM vk) {
    static char b[8];
    switch (vk) {
    case VK_RETURN: return "Return";
    case VK_ESCAPE: return "Escape";
    case VK_TAB: return "Tab";
    case VK_BACK: return "BackSpace";
    case VK_DELETE: return "Delete";
    case VK_INSERT: return "Insert";
    case VK_LEFT: return "Left";
    case VK_RIGHT: return "Right";
    case VK_UP: return "Up";
    case VK_DOWN: return "Down";
    case VK_HOME: return "Home";
    case VK_END: return "End";
    case VK_PRIOR: return "Prior";
    case VK_NEXT: return "Next";
    case VK_SPACE: return "space";
    case VK_SHIFT: return "Shift_L";
    case VK_CONTROL: return "Control_L";
    case VK_MENU: return "Alt_L";
    default: break;
    }
    if (vk >= VK_F1 && vk <= VK_F24) { snprintf(b, sizeof b, "F%d", (int)(vk - VK_F1 + 1)); return b; }
    if ((vk >= '0' && vk <= '9')) { b[0] = (char)vk; b[1] = 0; return b; }
    if (vk >= 'A' && vk <= 'Z') {
        b[0] = (char)((GetKeyState(VK_SHIFT) & 0x8000) ? vk : vk + 32);
        b[1] = 0;
        return b;
    }
    snprintf(b, sizeof b, "%u", (unsigned)vk);
    return b;
}

static void rf_key_event(RfForm *f, const char *obj, UINT msg, WPARAM w) {
    char args[96];
    if (msg == WM_CHAR) {
        wchar_t ch[2];
        const char *u;
        if (w < 32 && w != 13 && w != 9 && w != 8 && w != 27) return;
        ch[0] = (wchar_t)w;
        ch[1] = 0;
        u = rf_utf8(ch);
        if (w == ' ') snprintf(args, sizeof args, "0 0 0 space");
        else snprintf(args, sizeof args, "0 0 0 %s %s", w == 13 ? "Return" : w == 9 ? "Tab" : w == 8 ? "BackSpace"
                      : w == 27 ? "Escape" : u, w < 32 ? "" : u);
        { size_t n = strlen(args); while (n && args[n - 1] == ' ') args[--n] = 0; }
        rf_post_ex(f, obj, "KeyPress", args, AFTER_NONE, (int)w, 0);
        return;
    }
    snprintf(args, sizeof args, "0 0 0 %s", rf_keysym(w));
    rf_post_ex(f, obj, msg == WM_KEYUP || msg == WM_SYSKEYUP ? "KeyUp" : "KeyDown", args, AFTER_NONE, (int)w, 0);
}

/* mouse message -> MouseDown/Up/Move/Click/DoubleClick/Enter/Leave/Wheel; generic_click: Click and
 * DoubleClick come from the mouse (controls without a native notification) */
static void rf_mouse_event(RfForm *f, HWND h, const char *obj, UINT msg, WPARAM w, LPARAM l, int generic_click,
                           int *tracking) {
    char args[64];
    int btn = 0, x = GET_X_LPARAM(l), y = GET_Y_LPARAM(l);
    (void)w;
    switch (msg) {
    case WM_LBUTTONDOWN: case WM_LBUTTONUP: case WM_LBUTTONDBLCLK: btn = 1; break;
    case WM_MBUTTONDOWN: case WM_MBUTTONUP: btn = 2; break;
    case WM_RBUTTONDOWN: case WM_RBUTTONUP: btn = 3; break;
    default: break;
    }
    snprintf(args, sizeof args, "%d %d %d", (int)floor(U(f, x) + 0.5), (int)floor(U(f, y) + 0.5), btn);
    switch (msg) {
    case WM_LBUTTONDOWN: case WM_MBUTTONDOWN: case WM_RBUTTONDOWN:
        rf_post(f, obj, "MouseDown", args, AFTER_NONE);
        break;
    case WM_LBUTTONDBLCLK:
        rf_post(f, obj, "MouseDown", args, AFTER_NONE);
        if (generic_click) rf_post(f, obj, "DoubleClick", "", AFTER_NONE);
        break;
    case WM_LBUTTONUP: case WM_MBUTTONUP: case WM_RBUTTONUP:
        rf_post(f, obj, "MouseUp", args, AFTER_NONE);
        if (generic_click && msg == WM_LBUTTONUP) rf_post(f, obj, "Click", "", AFTER_NONE);
        break;
    case WM_MOUSEMOVE:
        if (tracking && !*tracking) {
            TRACKMOUSEEVENT t;
            t.cbSize = sizeof t;
            t.dwFlags = TME_LEAVE;
            t.hwndTrack = h;
            t.dwHoverTime = 0;
            TrackMouseEvent(&t);
            *tracking = 1;
            rf_post(f, obj, "MouseEnter", "", AFTER_NONE);
        }
        snprintf(args, sizeof args, "%d %d %d", (int)floor(U(f, x) + 0.5), (int)floor(U(f, y) + 0.5),
                 (w & MK_LBUTTON) ? 1 : (w & MK_MBUTTON) ? 2 : (w & MK_RBUTTON) ? 3 : 0);
        rf_post(f, obj, "MouseMove", args, AFTER_NONE);
        break;
    case WM_MOUSELEAVE:
        if (tracking) *tracking = 0;
        rf_post(f, obj, "MouseLeave", "", AFTER_NONE);
        break;
    case WM_MOUSEWHEEL: {
        POINT p;
        p.x = x;
        p.y = y;
        ScreenToClient(h, &p);
        snprintf(args, sizeof args, "%d %d 0", (int)floor(U(f, p.x) + 0.5), (int)floor(U(f, p.y) + 0.5));
        rf_post_ex(f, obj, "MouseWheel", args, AFTER_NONE, 0, GET_WHEEL_DELTA_WPARAM(w));
        break;
    }
    default: break;
    }
}

static void rf_on_command(RfCtl *c, int code) {
    switch (c->type) {
    case T_BUTTON:
        if (code == BN_CLICKED) rf_post_c(c, "Click", "");
        break;
    case T_CHECKBOX:
        if (code == BN_CLICKED) {
            rf_post_c(c, "Click", "");
            rf_post_c(c, "CheckedChanged", "");
        }
        break;
    case T_RADIO:
        if (code == BN_CLICKED) {
            RfCtl *o;
            int was = (int)SendMessageW(c->hwnd, BM_GETCHECK, 0, 0) == BST_CHECKED;
            for (o = c->form->ctls; o; o = o->next)
                if (o != c && o->type == T_RADIO && o->parent == c->parent && o->hwnd &&
                    SendMessageW(o->hwnd, BM_GETCHECK, 0, 0) == BST_CHECKED) {
                    SendMessageW(o->hwnd, BM_SETCHECK, BST_UNCHECKED, 0);
                    rf_post_c(o, "CheckedChanged", "");
                }
            SendMessageW(c->hwnd, BM_SETCHECK, BST_CHECKED, 0);
            rf_post_c(c, "Click", "");
            if (!was) rf_post_c(c, "CheckedChanged", "");
        }
        break;
    case T_CUSTOM:              /* a wrapped Win32 class: its parent notifications go to message() */
        if (c->cls->message) {
            intptr_t r = 0;
            c->cls->message((rf_handle)c, c->state, WM_COMMAND, (uintptr_t)code, 0, &r);
        }
        break;
    case T_LABEL: case T_LINK: case T_PICTURE:
        break;              /* Click / DoubleClick come from the mouse (rf_generic_click) */
    case T_TEXTBOX:
        if (code == EN_CHANGE) rf_post_c(c, "TextChanged", "");
        break;
    case T_UPDOWN:
        if (code == EN_CHANGE) {
            int v = (int)SendMessageW(c->buddy, UDM_GETPOS32, 0, 0);
            if (v != c->value) { c->value = v; rf_post_c(c, "ValueChanged", ""); }
        }
        break;
    case T_LISTBOX:
        if (code == LBN_SELCHANGE) {
            int i = rf_list_index(c);
            if (i != c->last_sel) { c->last_sel = i; rf_post_c(c, "SelectedIndexChanged", ""); }
        } else if (code == LBN_DBLCLK) {
            rf_post_c(c, "DoubleClick", "");
        }
        break;
    case T_COMBOBOX:
        if (code == CBN_SELCHANGE) {
            int i = rf_list_index(c);
            if (i != c->last_sel) {
                c->last_sel = i;
                rf_post_c(c, "SelectedIndexChanged", "");
                rf_post_c(c, "TextChanged", "");
            }
        } else if (code == CBN_EDITCHANGE) {
            rf_post_c(c, "TextChanged", "");
        } else if (code == CBN_DBLCLK) {
            rf_post_c(c, "DoubleClick", "");
        }
        break;
    default: break;
    }
}

static int rf_generic_click(int t) {
    /* Label / LinkLabel / PictureBox too: the STATIC control sends STN_CLICKED with the button PRESS, which made
     * Click come before MouseUp; from the mouse it is MouseDown, MouseUp, Click like a Button (and VB6) */
    return t == T_PANEL || t == T_GROUPBOX || t == T_TEXTBOX || t == T_LISTBOX || t == T_COMBOBOX ||
           t == T_PROGRESS || t == T_TRACKBAR || t == T_UPDOWN || t == T_TAB || t == T_STATUS ||
           t == T_LABEL || t == T_LINK || t == T_PICTURE;
}

/* WM_COMMAND / WM_NOTIFY / WM_CTLCOLOR* / scrolls of a form or of a container control */
static int rf_child_msg(RfForm *f, UINT m, WPARAM w, LPARAM l, LRESULT *res) {
    switch (m) {
    case WM_COMMAND:
        if (l && (HWND)l == f->toolbar) {
            RfCtl *c;
            for (c = f->ctls; c; c = c->next)
                if (c->type == T_TOOLBTN && c->id == (int)LOWORD(w)) { rf_post_c(c, "Click", ""); break; }
        } else if (l) {
            RfCtl *c = rf_ctl_of((HWND)l);
            if (c) rf_on_command(c, HIWORD(w));
        } else if (HIWORD(w) == 0 && LOWORD(w) >= MENU_BASE) {
            RfCtl *c;
            for (c = f->ctls; c; c = c->next)
                if (c->type == T_MENUITEM && c->id == (int)LOWORD(w)) { rf_post_c(c, "Click", ""); break; }
        }
        *res = 0;
        return 1;
    case WM_NOTIFY: {
        NMHDR *nm = (NMHDR *)l;
        RfCtl *c = rf_ctl_of(nm->hwndFrom);
        if (c && c->type == T_TAB && nm->code == TCN_SELCHANGE) {
            rf_tab_changed(c);
            rf_post_c(c, "SelectedIndexChanged", "");
        } else if (c && c->type == T_STATUS && nm->code == NM_CLICK) {
            rf_post_c(c, "Click", "");
        } else if (c && c->type == T_CUSTOM && c->cls->message) {
            intptr_t r = 0;
            if (c->cls->message((rf_handle)c, c->state, WM_NOTIFY, w, l, &r)) { *res = (LRESULT)r; return 1; }
        } else if (nm->hwndFrom == f->toolbar && nm->code == TTN_GETDISPINFOW) {
            return 0;
        }
        *res = 0;
        return 1;
    }
    case WM_HSCROLL: case WM_VSCROLL: {
        RfCtl *c = rf_ctl_of((HWND)l);
        if (c && c->type == T_TRACKBAR) {
            int v = (int)SendMessageW(c->hwnd, TBM_GETPOS, 0, 0);
            if (v != c->value) { c->value = v; rf_post_c(c, "ValueChanged", ""); }
            *res = 0;
            return 1;
        }
        if (c && c->type == T_UPDOWN) {
            int v = (int)SendMessageW(c->buddy, UDM_GETPOS32, 0, 0);
            if (v != c->value) { c->value = v; rf_post_c(c, "ValueChanged", ""); }
            *res = 0;
            return 1;
        }
        return 0;
    }
    case WM_CTLCOLORSTATIC: case WM_CTLCOLOREDIT: case WM_CTLCOLORLISTBOX: case WM_CTLCOLORBTN:
        *res = rf_ctlcolor(f, m, (HDC)w, (HWND)l);
        return *res != 0;
    default:
        return 0;
    }
}

static void rf_fill_bg(HWND h, HDC dc, HBRUSH br) {
    RECT r;
    GetClientRect(h, &r);
    FillRect(dc, &r, br);
}

static LRESULT CALLBACK rf_sub_proc(HWND h, UINT m, WPARAM w, LPARAM l, UINT_PTR id, DWORD_PTR ref) {
    RfCtl *c = (RfCtl *)ref;
    LRESULT res;
    (void)id;
    if (!c) return DefSubclassProc(h, m, w, l);
    if (c->type == T_CUSTOM && c->cls->message) {
        intptr_t r = 0;
        if (c->cls->message((rf_handle)c, c->state, m, (uintptr_t)w, (intptr_t)l, &r)) return (LRESULT)r;
    }
    if (CCONT(c) && h == c->hwnd && rf_child_msg(c->form, m, w, l, &res)) return res;
    switch (m) {
    case WM_ERASEBKGND:
        if (c->type == T_PANEL || c->type == T_GROUPBOX) {
            COLORREF col;
            rf_fill_bg(h, (HDC)w, rf_brush_for(c, &col));
            return 1;
        }
        break;
    case WM_SIZE:
        if (CCONT(c) && h == c->hwnd) {
            res = DefSubclassProc(h, m, w, l);
            rf_layout(c->form, c);
            return res;
        }
        break;
    case WM_KEYDOWN: case WM_KEYUP: case WM_SYSKEYDOWN: case WM_SYSKEYUP: case WM_CHAR:
        rf_key_event(c->form, c->name, m, w);
        break;
    case WM_SETFOCUS:
        rf_post_c(c, "GotFocus", "");
        break;
    case WM_KILLFOCUS:
        rf_post_c(c, "LostFocus", "");
        break;
    case WM_LBUTTONDOWN: case WM_LBUTTONUP: case WM_LBUTTONDBLCLK: case WM_RBUTTONDOWN: case WM_RBUTTONUP:
    case WM_MBUTTONDOWN: case WM_MBUTTONUP: case WM_MOUSEMOVE: case WM_MOUSELEAVE: case WM_MOUSEWHEEL:
        rf_mouse_event(c->form, h, c->name, m, w, l, rf_generic_click(c->type), &c->tracking);
        break;
    case WM_NCDESTROY:
        RemoveWindowSubclass(h, rf_sub_proc, 1);
        RemovePropW(h, L"radforms.ctl");
        rf_name_unprop(h);
        break;
    default: break;
    }
    return DefSubclassProc(h, m, w, l);
}

static LRESULT CALLBACK rf_form_proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    RfForm *f = (RfForm *)GetPropW(h, L"radforms.form");
    LRESULT res;
    static int tracking;
    if (!f) return DefWindowProcW(h, m, w, l);
    if (rf_child_msg(f, m, w, l, &res)) return res;
    switch (m) {
    case WM_ERASEBKGND: {
        COLORREF col;
        HBRUSH br = g_themed && g_theme_brush ? g_theme_brush : GetSysColorBrush(COLOR_BTNFACE);
        if (f->has_back) {
            if (!f->brush) f->brush = CreateSolidBrush(f->back);
            br = f->brush;
        }
        (void)col;
        rf_fill_bg(h, (HDC)w, br);
        return 1;
    }
    case WM_SIZE:
        if (f->toolbar) {
            RECT r;
            GetClientRect(h, &r);
            MoveWindow(f->toolbar, 0, 0, r.right, S(f, TOOLSTRIP_H), TRUE);
        }
        if (f->fx && w != SIZE_MINIMIZED) rf_fx_variants(f, 1);
        rf_layout(f, NULL);
        if (f->shown_once && w != SIZE_MINIMIZED) rf_post(f, f->name, "Resize", "", AFTER_NONE);
        return 0;
    case WM_TIMER: {
        RfCtl *c;
        if (f->fx && rf_fx_timer(f, w)) return 0;
        for (c = f->ctls; c; c = c->next)
            if (c->type == T_TIMER && TIMER_BASE + (UINT_PTR)c->id == w) { rf_post_c(c, "Tick", ""); break; }
        return 0;
    }
    case WM_ACTIVATE:
        if (f->shown_once) rf_post(f, f->name, LOWORD(w) == WA_INACTIVE ? "Deactivate" : "Activated", "", AFTER_NONE);
        break;
    case WM_CLOSE:
        f->cancel = 0;
        rf_post(f, f->name, "FormClosing", "", AFTER_CLOSE);
        return 0;
    case WM_NCDESTROY:
        rf_name_unprop(h);
        RemovePropW(h, L"radforms.form");
        break;
    case WM_DPICHANGED: {
        RECT *r = (RECT *)l;
        RfCtl *c;
        f->dpi = HIWORD(w);
        g_building++;
        for (c = f->ctls; c; c = c->next)
            if (c->hwnd) rf_make_font(c);
        g_building--;
        SetWindowPos(h, NULL, r->left, r->top, r->right - r->left, r->bottom - r->top, SWP_NOZORDER | SWP_NOACTIVATE);
        rf_layout(f, NULL);
        return 0;
    }
    case WM_LBUTTONDOWN: case WM_LBUTTONUP: case WM_LBUTTONDBLCLK: case WM_RBUTTONDOWN: case WM_RBUTTONUP:
    case WM_MBUTTONDOWN: case WM_MBUTTONUP: case WM_MOUSEMOVE: case WM_MOUSELEAVE: case WM_MOUSEWHEEL:
        rf_mouse_event(f, h, f->name, m, w, l, 1, &tracking);
        break;
    default: break;
    }
    return DefWindowProcW(h, m, w, l);
}

/* ================================================================== message loop */
static void rf_pump_one(MSG *msg) {
    RfForm *f = rf_form_of(msg->hwnd);
    if (f && msg->hwnd != f->hwnd &&
        (msg->message == WM_KEYDOWN || msg->message == WM_KEYUP || msg->message == WM_CHAR ||
         msg->message == WM_SYSKEYDOWN || msg->message == WM_SYSKEYUP))
        rf_key_event(f, f->name, msg->message, msg->wParam);        /* the form sees its controls' keys */
    else if (f && msg->hwnd == f->hwnd &&
             (msg->message == WM_KEYDOWN || msg->message == WM_KEYUP || msg->message == WM_CHAR))
        rf_key_event(f, f->name, msg->message, msg->wParam);
    /* Enter on a focused push button presses it (WinForms / dialogs); IsDialogMessage of a plain window sends IDOK */
    if (f && msg->message == WM_KEYDOWN && msg->wParam == VK_RETURN && msg->hwnd != f->hwnd) {
        wchar_t cls[16];
        RfCtl *bc = (RfCtl *)GetPropW(msg->hwnd, L"radforms.ctl");
        GetClassNameW(msg->hwnd, cls, 16);
        if (bc && bc->hwnd == msg->hwnd && lstrcmpiW(cls, L"BUTTON") == 0 &&
            ((GetWindowLongW(msg->hwnd, GWL_STYLE) & BS_TYPEMASK) <= BS_DEFPUSHBUTTON)) {
            SendMessageW(msg->hwnd, BM_CLICK, 0, 0);
            return;
        }
    }
    if (f && f->hwnd && IsDialogMessageW(f->hwnd, msg)) return;
    TranslateMessage(msg);
    DispatchMessageW(msg);
}

static int rf_any_visible(void) {
    int i;
    for (i = 0; i < g_nforms; i++)
        if (g_forms[i].want_visible) return 1;
    return 0;
}

static int rf_wait(void) {
    MSG msg;
    while (!g_qn) {
        if (g_quit) return 0;
        if (g_started && !rf_any_visible()) return 0;          /* every form closed */
        if (GetMessageW(&msg, NULL, 0, 0) <= 0) { g_quit = 1; return 0; }
        rf_pump_one(&msg);
    }
    return 1;
}

void rad_init(void) {
    INITCOMMONCONTROLSEX icc;
    if (g_inited) return;
    g_inited = 1;
    g_inst = GetModuleHandleW(NULL);
    icc.dwSize = sizeof icc;
    icc.dwICC = ICC_STANDARD_CLASSES | ICC_WIN95_CLASSES | ICC_BAR_CLASSES | ICC_TAB_CLASSES |
                ICC_UPDOWN_CLASS | ICC_PROGRESS_CLASS;
    InitCommonControlsEx(&icc);
    g_white = GetSysColorBrush(COLOR_WINDOW);
    rf_init_registry();
    rf_init_themes();
    rf_modules();
    rf_load_resource();
}

int rad_next_event(void) {
    Ev *e;
    if (!g_inited) rad_init();
    if (!g_started) {
        g_started = 1;
        if (!g_startup) {
            MessageBoxW(NULL, L"No forms: the form description (RADFORMS resource) is missing.", L"radforms", MB_ICONERROR);
            return 0;
        }
        rf_form_load(g_startup, 1);
    }
    if (g_quit || !rf_wait()) {
        rad_obj[0] = rad_ev[0] = rad_args[0] = 0;
        return 0;
    }
    e = &g_q[g_qh];
    g_qh = (g_qh + 1) % 512;
    g_qn--;
    g_cur = *e;
    g_in_event = 1;
    rf_copy(rad_obj, g_cur.obj, sizeof rad_obj);
    rf_copy(rad_ev, g_cur.ev, sizeof rad_ev);
    rf_copy(rad_args, g_cur.args, sizeof rad_args);
    return 1;
}

void rad_done(void) {
    Ev cur = g_cur;
    if (!g_in_event) return;
    g_in_event = 0;
    memset(&g_cur, 0, sizeof g_cur);
    rf_after(cur.form, cur.after);
    if (g_end_req) g_quit = 1;
}

/* the current event to the event callback (handles API) and / or the key dispatcher */
static void rf_dispatch_current(void) {
    if (g_evfn) {
        rf_event_args a;
        RfForm *f = g_cur.form;
        RfCtl *c = f && !rf_ieq(g_cur.obj, f->name) ? rf_ctl_in(f, g_cur.obj) : NULL;
        int id = rf_event_id(g_cur.ev);
        memset(&a, 0, sizeof a);
        a.size = (int)sizeof a;
        a.object = g_cur.obj;
        a.event = g_cur.ev;
        a.args = g_cur.args;
        a.key_name = a.key_char = "";
        if (id >= RF_EV_MOUSEDOWN && id <= RF_EV_MOUSEWHEEL)
            sscanf(g_cur.args, "%d %d %d", &a.x, &a.y, &a.button);
        if (id >= RF_EV_KEYDOWN && id <= RF_EV_KEYPRESS) {
            char *kn = (char *)rad_arg(3), *kc = (char *)rad_arg(4);
            a.key_name = kn;
            a.key_char = id == RF_EV_KEYPRESS ? (*kc ? kc : (strcmp(kn, "space") == 0 ? " " : "")) : "";
        }
        a.key_code = g_cur.vk;
        a.delta = g_cur.delta;
        g_evfn(c ? (rf_handle)c : (rf_handle)f, id, &a, g_evuser);
        if (a.cancel && f && id == RF_EV_FORMCLOSING) f->cancel = 1;
    }
    if (g_dispatch) {
        char key[520];
        snprintf(key, sizeof key, "%s_%s", rad_obj, rad_ev);
        g_dispatch(key);
    }
}

int rad_run(rad_dispatch_fn dispatch) {
    g_dispatch = dispatch;
    while (rad_next_event()) {
        rf_dispatch_current();
        rad_done();
    }
    return 0;
}

void rf_set_event_handler(rf_event_fn fn, void *user) {
    g_evfn = fn;
    g_evuser = user;
}

int rf_run_events(rf_event_fn fn, void *user) {
    rf_set_event_handler(fn, user);
    while (rad_next_event()) {
        rf_dispatch_current();
        rad_done();
    }
    return 0;
}

void rad_end(void) {
    g_end_req = 1;
    if (!g_in_event) g_quit = 1;
    PostQuitMessage(0);
}

/* ================================================================== properties */
static int rf_is(const char *p, const char *a) { return rf_ieq(p, a); }

static void rf_set_form(RfForm *f, const char *p, const char *v) {
    if (rf_is(p, "Text") || rf_is(p, "Caption")) rf_set_wtext(f->hwnd, v, 0);
    else if (rf_is(p, "Width") || rf_is(p, "Height")) {
        RECT r;
        int w, hh;
        GetClientRect(f->hwnd, &r);
        w = (int)floor(U(f, r.right) + 0.5);
        hh = (int)floor(U(f, r.bottom) + 0.5) - (f->toolbar ? TOOLSTRIP_H : 0);
        if (rf_is(p, "Width")) w = (int)(rad_num(v) / f->unit);
        else hh = (int)(rad_num(v) / f->unit);
        rf_form_size(f, w, hh, 0);
    } else if (rf_is(p, "Left") || rf_is(p, "Top")) {
        RECT r;
        GetWindowRect(f->hwnd, &r);
        if (rf_is(p, "Left")) r.left = S(f, rad_num(v) / f->unit);
        else r.top = S(f, rad_num(v) / f->unit);
        f->center = 0;
        SetWindowPos(f->hwnd, NULL, r.left, r.top, 0, 0, SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE);
    } else if (rf_is(p, "BackColor")) {
        f->has_back = rf_color(v, &f->back);
        if (f->brush) DeleteObject(f->brush);
        f->brush = NULL;
        InvalidateRect(f->hwnd, NULL, TRUE);
    } else if (rf_is(p, "Visible")) {
        if (rf_bool(v)) { f->want_visible = 1; rf_form_show_now(f); }
        else rf_form_hide(f);
    } else if (rf_is(p, "WindowState")) {
        int s = rf_int(v);
        if (rf_ieq(v, "Maximized")) s = 2;
        else if (rf_ieq(v, "Minimized")) s = 1;
        if (!f->shown_once) f->maximized = s == 2;
        else ShowWindow(f->hwnd, s == 2 ? SW_MAXIMIZE : s == 1 ? SW_MINIMIZE : SW_RESTORE);
    } else if (rf_is(p, "TopMost")) {
        SetWindowPos(f->hwnd, rf_bool(v) ? HWND_TOPMOST : HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE);
    } else if (rf_is(p, "Icon")) {
        HICON ic = rf_load_icon(v);
        if (ic) {
            SendMessageW(f->hwnd, WM_SETICON, ICON_BIG, (LPARAM)ic);
            SendMessageW(f->hwnd, WM_SETICON, ICON_SMALL, (LPARAM)ic);
        }
    } else if (rf_is(p, "Theme")) {
        rf_theme_set(v);
    } else if (rf_is(p, "Cancel")) {
        f->cancel = rf_bool(v);
    } else if (rf_is(p, "Enabled")) {
        EnableWindow(f->hwnd, rf_bool(v));
    } else if (rf_is(p, "Opacity")) {           /* layered window: animations fade the form */
        double o = rad_num(v);
        LONG_PTR ex = GetWindowLongPtrW(f->hwnd, GWL_EXSTYLE);
        if (o > 1.0 && o <= 100.0 && strchr(v, '%')) o /= 100.0;
        o = o < 0 ? 0 : o > 1 ? 1 : o;
        f->opacity = o;
        f->alpha_set = 1;
        if (!(ex & WS_EX_LAYERED)) SetWindowLongPtrW(f->hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED);
        SetLayeredWindowAttributes(f->hwnd, 0, (BYTE)floor(o * 255 + 0.5), LWA_ALPHA);
    }
    /* StartPosition, FormBorderStyle, ScaleMode, ... are used when the form is created */
}

static const char *rf_get_form(RfForm *f, const char *p) {
    RECT r;
    if (rf_is(p, "Text") || rf_is(p, "Caption")) return rf_wtext(f->hwnd);
    if (rf_is(p, "Name")) return f->name;
    if (rf_is(p, "Width") || rf_is(p, "ScaleWidth")) {
        GetClientRect(f->hwnd, &r);
        return rf_istr((long long)floor(U(f, r.right) + 0.5) * f->unit);
    }
    if (rf_is(p, "Height") || rf_is(p, "ScaleHeight")) {
        GetClientRect(f->hwnd, &r);
        return rf_istr(((long long)floor(U(f, r.bottom) + 0.5) - (f->toolbar ? TOOLSTRIP_H : 0)) * f->unit);
    }
    if (rf_is(p, "Left") || rf_is(p, "Top")) {
        GetWindowRect(f->hwnd, &r);
        return rf_istr((long long)floor(U(f, rf_is(p, "Left") ? r.left : r.top) + 0.5) * f->unit);
    }
    if (rf_is(p, "Visible")) return rf_tf(f->want_visible && IsWindowVisible(f->hwnd));
    if (rf_is(p, "Enabled")) return rf_tf(IsWindowEnabled(f->hwnd));
    if (rf_is(p, "BackColor")) return f->has_back ? rf_istr((long long)f->back) : "2147483663";
    if (rf_is(p, "WindowState")) return IsZoomed(f->hwnd) ? "2" : IsIconic(f->hwnd) ? "1" : "0";
    if (rf_is(p, "hWnd")) return rf_istr((long long)(INT_PTR)f->hwnd);
    if (rf_is(p, "Cancel")) return rf_tf(f->cancel);
    if (rf_is(p, "Theme")) return g_theme ? g_theme->name : "Light";
    if (rf_is(p, "Opacity")) return rad_str(f->alpha_set ? f->opacity : 1.0);
    if (f->fx && (rf_is(p, "CurrentSizes") || rf_is(p, "CurrentState"))) {
        int h;
        return rf_fx_call(f, NULL, p, "", &h);
    }
    return "";
}

static void rf_set_range(RfCtl *c) {
    if (c->type == T_PROGRESS) SendMessageW(c->hwnd, PBM_SETRANGE32, (WPARAM)c->minv, (LPARAM)c->maxv);
    else if (c->type == T_TRACKBAR) {
        SendMessageW(c->hwnd, TBM_SETRANGEMIN, FALSE, c->minv);
        SendMessageW(c->hwnd, TBM_SETRANGEMAX, TRUE, c->maxv);
        SendMessageW(c->hwnd, TBM_SETTICFREQ, (WPARAM)((c->maxv - c->minv) / 10 > 0 ? (c->maxv - c->minv) / 10 : 1), 0);
    } else if (c->type == T_UPDOWN && c->buddy) SendMessageW(c->buddy, UDM_SETRANGE32, (WPARAM)c->minv, (LPARAM)c->maxv);
}

static void rf_set_value(RfCtl *c, int v, int notify) {
    int old = c->value;
    if (v < c->minv) v = c->minv;
    if (v > c->maxv) v = c->maxv;
    c->value = v;                       /* first: the EN_CHANGE of an up-down sees no change */
    if (c->type == T_PROGRESS) SendMessageW(c->hwnd, PBM_SETPOS, (WPARAM)v, 0);
    else if (c->type == T_TRACKBAR) SendMessageW(c->hwnd, TBM_SETPOS, TRUE, v);
    else if (c->type == T_UPDOWN && c->buddy) SendMessageW(c->buddy, UDM_SETPOS32, 0, v);
    if (v != old && notify && c->type != T_PROGRESS) rf_post_c(c, "ValueChanged", "");
}

static void rf_timer_apply(RfCtl *c) {
    RfForm *f = c->form;
    if (!f->hwnd) return;
    KillTimer(f->hwnd, TIMER_BASE + (UINT_PTR)c->id);
    if (c->timer_on && c->value > 0) SetTimer(f->hwnd, TIMER_BASE + (UINT_PTR)c->id, (UINT)c->value, NULL);
}

static void rf_set_items(RfCtl *c, const char *v) {
    char *items = rf_strdup(v), *p = items;
    SendMessageW(c->hwnd, c->type == T_LISTBOX ? LB_RESETCONTENT : CB_RESETCONTENT, 0, 0);
    while (p && *p) {
        char *e = strchr(p, ';');
        if (e) *e = 0;
        while (*p == ' ') p++;
        if (*p) rf_list_add(c, p, -1);
        p = e ? e + 1 : NULL;
    }
    free(items);
    c->last_sel = -1;
}

static void rf_set_one(RfForm *f, RfCtl *c, const char *p, const char *v);

static void rf_set(RfForm *f, RfCtl *c, const char *p, const char *v) {
    if (f && f->fx && rf_fx_set_hook(f, c, p, v)) return;      /* "On show" / "On hide" animations */
    if (c && (rf_is(p, "AccessibleName") || rf_is(p, "AccessibleDescription"))) {
        rf_kv_set(c, p, v ? v : "");
        if (!g_building) rf_acc_apply(c);
        return;
    }
    rf_set_one(f, c, p, v);
    if (c && !g_building && c->hwnd && c->type == T_CUSTOM && rf_acc_relevant(p)) rf_acc_apply(c);
    if (f && f->fx) rf_fx_after_set(f, c, p, v);
}

static void rf_set_one(RfForm *f, RfCtl *c, const char *p, const char *v) {
    if (!v) v = "";
    if (!c) { rf_set_form(f, p, v); return; }
    if (c->type == T_CUSTOM) {
        if (c->cls->set && c->cls->set((rf_handle)c, c->state, p, v)) {
            if (c->hwnd && COWNER(c)) InvalidateRect(c->hwnd, NULL, FALSE);
            return;
        }
        if (!c->hwnd) { rf_kv_set(c, p, v); return; }
        if (COWNER(c)) InvalidateRect(c->hwnd, NULL, FALSE);
    }
    if (rf_is(p, "Tag") || rf_is(p, "Name") || rf_is(p, "TabIndex") || rf_is(p, "Anchor") || rf_is(p, "Dock") ||
        rf_is(p, "Parent") || rf_is(p, "TabPage") || rf_is(p, "TabPages") || rf_is(p, "DropDownStyle") ||
        rf_is(p, "Multiline") || rf_is(p, "BorderStyle")) {
        if (rf_is(p, "Tag")) rf_kv_set(c, p, v);
        if (rf_is(p, "TabPage") && !g_building) { c->page = rf_int(v); rf_apply_visible(c); }
        return;
    }
    switch (c->type) {                      /* non-visual objects */
    case T_TIMER:
        if (rf_is(p, "Interval")) { c->value = rf_int(v); rf_timer_apply(c); }
        else if (rf_is(p, "Enabled")) { c->timer_on = rf_bool(v); rf_timer_apply(c); }
        return;
    case T_MENUITEM: {
        UINT flag, pos = rf_menu_pos(c, &flag);
        if (rf_is(p, "Text") || rf_is(p, "Caption")) {
            MENUITEMINFOW mi;
            wchar_t *w = rf_wide(v);
            memset(&mi, 0, sizeof mi);
            mi.cbSize = sizeof mi;
            mi.fMask = MIIM_STRING;
            mi.dwTypeData = w;
            SetMenuItemInfoW(c->menu, pos, flag == MF_BYPOSITION, &mi);
            free(w);
        } else if (rf_is(p, "Enabled")) {
            EnableMenuItem(c->menu, pos, flag | (rf_bool(v) ? MF_ENABLED : MF_GRAYED));
        } else if (rf_is(p, "Checked")) {
            c->checked = rf_bool(v);
            CheckMenuItem(c->menu, pos, flag | (c->checked ? MF_CHECKED : MF_UNCHECKED));
        } else {
            rf_kv_set(c, p, v);
        }
        DrawMenuBar(f->hwnd);
        return;
    }
    case T_TOOLBTN:
        if (rf_is(p, "Enabled")) SendMessageW(f->toolbar, TB_ENABLEBUTTON, (WPARAM)c->id, MAKELONG(rf_bool(v), 0));
        else if (rf_is(p, "Visible")) SendMessageW(f->toolbar, TB_HIDEBUTTON, (WPARAM)c->id, MAKELONG(!rf_bool(v), 0));
        else if (rf_is(p, "Text") || rf_is(p, "Caption")) {
            TBBUTTONINFOW bi;
            wchar_t *w = rf_wide(v);
            memset(&bi, 0, sizeof bi);
            bi.cbSize = sizeof bi;
            bi.dwMask = TBIF_TEXT;
            bi.pszText = w;
            SendMessageW(f->toolbar, TB_SETBUTTONINFOW, (WPARAM)c->id, (LPARAM)&bi);
            free(w);
        } else rf_kv_set(c, p, v);
        return;
    case T_DLG_OPEN: case T_DLG_SAVE: case T_DLG_COLOR: case T_DLG_FONT: case T_DLG_FOLDER:
        rf_kv_set(c, p, v);
        return;
    default: break;
    }
    if (!c->hwnd) return;
    if (rf_is(p, "Text") || rf_is(p, "Caption") || rf_is(p, "SimpleText")) {
        if (c->type == T_LISTBOX || (c->type == T_COMBOBOX && c->dropstyle == 0)) {
            int i, n = rf_list_count(c);
            for (i = 0; i < n; i++)
                if (strcmp(rf_list_item(c, i), v) == 0) { rf_list_select(c, i, 1); break; }
        } else if (c->type == T_STATUS) {
            wchar_t *w = rf_wide(v);
            SendMessageW(c->hwnd, SB_SETTEXTW, 255 | SBT_NOBORDERS, (LPARAM)w);
            free(w);
            rf_kv_set(c, "Text", v);
        } else if (c->type == T_UPDOWN) {
            rf_set_value(c, rf_int(v), 1);
        } else if (c->type == T_TAB || c->type == T_PROGRESS || c->type == T_TRACKBAR || c->type == T_PICTURE) {
            rf_kv_set(c, "Text", v);
        } else {
            rf_set_wtext(c->hwnd, v, c->multiline);
        }
    } else if (rf_is(p, "Left")) rf_set_geo(c, 0, rad_num(v) / f->unit);
    else if (rf_is(p, "Top")) rf_set_geo(c, 1, rad_num(v) / f->unit);
    else if (rf_is(p, "Width")) rf_set_geo(c, 2, rad_num(v) / f->unit);
    else if (rf_is(p, "Height")) rf_set_geo(c, 3, rad_num(v) / f->unit);
    else if (rf_is(p, "Visible")) { c->visible = rf_bool(v); rf_apply_visible(c); }
    else if (rf_is(p, "Enabled")) {
        c->enabled = rf_bool(v);
        EnableWindow(c->hwnd, c->enabled);
        if (c->buddy) EnableWindow(c->buddy, c->enabled);
    } else if (rf_is(p, "BackColor") || rf_is(p, "ForeColor") || rf_is(p, "LinkColor")) {
        COLORREF col = 0;
        int ok = rf_color(v, &col);
        if (rf_is(p, "BackColor")) {
            c->has_back = ok;
            c->back = col;
            if (c->brush) DeleteObject(c->brush);
            c->brush = NULL;
            if (c->type == T_PROGRESS && ok) SendMessageW(c->hwnd, PBM_SETBKCOLOR, 0, (LPARAM)col);
        } else {
            c->has_fore = ok;
            c->fore = col;
            if (c->type == T_PROGRESS && ok) SendMessageW(c->hwnd, PBM_SETBARCOLOR, 0, (LPARAM)col);
        }
        InvalidateRect(c->hwnd, NULL, TRUE);
    } else if (rf_is(p, "FontName") || rf_is(p, "FontSize") || rf_is(p, "FontBold") || rf_is(p, "FontItalic") ||
               rf_is(p, "FontUnderline") || rf_is(p, "Size") || rf_is(p, "Bold") || rf_is(p, "Italic")) {
        if (rf_is(p, "FontName")) {
            wchar_t *w = rf_wide(v);
            if (w) { wcsncpy(c->font_name, w, LF_FACESIZE - 1); free(w); }
        } else if (rf_is(p, "FontSize") || rf_is(p, "Size")) {
            c->font_size = (float)rad_num(v);
            if (c->font_size <= 0) c->font_size = 9;
        } else if (rf_is(p, "FontBold") || rf_is(p, "Bold")) c->bold = rf_bool(v);
        else if (rf_is(p, "FontItalic") || rf_is(p, "Italic")) c->italic = rf_bool(v);
        else c->underline = rf_bool(v);
        rf_make_font(c);
    } else if (rf_is(p, "Checked") || rf_is(p, "Value")) {
        if (c->type == T_CHECKBOX || c->type == T_RADIO) {
            int on = rf_bool(v), was = (int)SendMessageW(c->hwnd, BM_GETCHECK, 0, 0) == BST_CHECKED;
            if (on && c->type == T_RADIO) {
                RfCtl *o;
                for (o = f->ctls; o; o = o->next)
                    if (o != c && o->type == T_RADIO && o->parent == c->parent && o->hwnd &&
                        SendMessageW(o->hwnd, BM_GETCHECK, 0, 0) == BST_CHECKED) {
                        SendMessageW(o->hwnd, BM_SETCHECK, BST_UNCHECKED, 0);
                        rf_post_c(o, "CheckedChanged", "");
                    }
            }
            SendMessageW(c->hwnd, BM_SETCHECK, on ? BST_CHECKED : BST_UNCHECKED, 0);
            if (on != was) rf_post_c(c, "CheckedChanged", "");
        } else if (c->type == T_PROGRESS || c->type == T_TRACKBAR || c->type == T_UPDOWN) {
            rf_set_value(c, rf_int(v), 1);
        }
    } else if (rf_is(p, "Minimum") || rf_is(p, "Min")) { c->minv = rf_int(v); rf_set_range(c); rf_set_value(c, c->value, 0); }
    else if (rf_is(p, "Maximum") || rf_is(p, "Max")) { c->maxv = rf_int(v); rf_set_range(c); rf_set_value(c, c->value, 0); }
    else if (rf_is(p, "Items") || rf_is(p, "List")) {
        if (c->type == T_LISTBOX || c->type == T_COMBOBOX) rf_set_items(c, v);
    } else if (rf_is(p, "ListIndex") || rf_is(p, "SelectedIndex")) {
        if (c->type == T_LISTBOX || c->type == T_COMBOBOX) rf_list_select(c, rf_int(v), 1);
        else if (c->type == T_TAB) {
            int old = rf_tab_sel(c);
            SendMessageW(c->hwnd, TCM_SETCURSEL, (WPARAM)rf_int(v), 0);
            rf_tab_changed(c);
            if (old != rf_tab_sel(c)) rf_post_c(c, "SelectedIndexChanged", "");
        }
    } else if (rf_is(p, "ReadOnly") || rf_is(p, "Locked")) {
        c->readonly = rf_bool(v);
        if (c->type == T_TEXTBOX || c->type == T_UPDOWN) SendMessageW(c->hwnd, EM_SETREADONLY, (WPARAM)c->readonly, 0);
    } else if (rf_is(p, "MaxLength")) {
        c->maxlen = rf_int(v);
        if (c->type == T_TEXTBOX) SendMessageW(c->hwnd, EM_SETLIMITTEXT, (WPARAM)c->maxlen, 0);
    } else if (rf_is(p, "PasswordChar")) {
        if (c->type == T_TEXTBOX) {
            wchar_t *w = rf_wide(v);
            SendMessageW(c->hwnd, EM_SETPASSWORDCHAR, (WPARAM)(w && *w ? w[0] : 0), 0);
            free(w);
            InvalidateRect(c->hwnd, NULL, TRUE);
        }
    } else if (rf_is(p, "TextAlign") || rf_is(p, "Alignment")) {
        LONG_PTR st = GetWindowLongPtrW(c->hwnd, GWL_STYLE);
        c->align = rf_align_of(v);
        if (isdigit((unsigned char)*v)) c->align = rf_int(v) == 2 ? 1 : rf_int(v) == 1 ? 2 : 0;    /* VB Alignment */
        if (c->type == T_LABEL || c->type == T_LINK) st = (st & ~(LONG_PTR)(SS_CENTER | SS_RIGHT)) | (c->align == 1 ? SS_CENTER : c->align == 2 ? SS_RIGHT : SS_LEFT);
        else if (c->type == T_BUTTON) st = (st & ~(LONG_PTR)(BS_CENTER)) | (c->align == 0 ? BS_LEFT : c->align == 2 ? BS_RIGHT : BS_CENTER);
        else if (c->type == T_TEXTBOX) st = (st & ~(LONG_PTR)(ES_CENTER | ES_RIGHT)) | (c->align == 1 ? ES_CENTER : c->align == 2 ? ES_RIGHT : ES_LEFT);
        SetWindowLongPtrW(c->hwnd, GWL_STYLE, st);
        InvalidateRect(c->hwnd, NULL, TRUE);
    } else if (rf_is(p, "Image") || rf_is(p, "Picture")) {
        if (c->type == T_PICTURE) {
            COLORREF bg;
            HBITMAP old = c->image;
            rf_brush_for(c, &bg);
            c->image = *v ? rf_load_bitmap(v, bg) : NULL;
            SendMessageW(c->hwnd, STM_SETIMAGE, IMAGE_BITMAP, (LPARAM)c->image);
            if (old) DeleteObject(old);
            rf_kv_set(c, "Image", v);
        }
    } else if (rf_is(p, "ToolTip") || rf_is(p, "ToolTipText")) {
        rf_kv_set(c, "ToolTip", v);
        rf_add_tooltip(c, v);
    } else if (rf_is(p, "SelStart") || rf_is(p, "SelectionStart")) {
        int s = rf_int(v);
        SendMessageW(c->hwnd, EM_SETSEL, (WPARAM)s, s);
    } else if (rf_is(p, "SelLength") || rf_is(p, "SelectionLength")) {
        DWORD a = 0;
        SendMessageW(c->hwnd, EM_GETSEL, (WPARAM)&a, 0);
        SendMessageW(c->hwnd, EM_SETSEL, a, (LPARAM)(a + (DWORD)rf_int(v)));
    } else if (rf_is(p, "SelText") || rf_is(p, "SelectedText")) {
        wchar_t *w = rf_wide(v);
        SendMessageW(c->hwnd, EM_REPLACESEL, TRUE, (LPARAM)w);
        free(w);
    } else {
        rf_kv_set(c, p, v);           /* accepted and remembered (Tag-like) */
    }
}

static const char *rf_get(RfForm *f, RfCtl *c, const char *p) {
    const char *kv;
    if (!c) return rf_get_form(f, p);
    if (rf_is(p, "Name")) return c->name;
    if (c->type == T_CUSTOM && c->cls->get) {
        const char *r = c->cls->get((rf_handle)c, c->state, p);
        if (r) return r;
    }
    switch (c->type) {
    case T_TIMER:
        if (rf_is(p, "Interval")) return rf_istr(c->value);
        if (rf_is(p, "Enabled")) return rf_tf(c->timer_on);
        break;
    case T_MENUITEM: {
        UINT flag, pos = rf_menu_pos(c, &flag);
        if (rf_is(p, "Text") || rf_is(p, "Caption")) {
            wchar_t w[512];
            w[0] = 0;
            GetMenuStringW(c->menu, pos, w, 511, flag);
            return rf_utf8(w);
        }
        if (rf_is(p, "Enabled")) return rf_tf(!(GetMenuState(c->menu, pos, flag) & (MF_GRAYED | MF_DISABLED)));
        if (rf_is(p, "Checked")) return rf_tf(c->checked);
        break;
    }
    case T_TOOLBTN:
        if (rf_is(p, "Enabled")) return rf_tf((int)SendMessageW(f->toolbar, TB_ISBUTTONENABLED, (WPARAM)c->id, 0));
        if (rf_is(p, "Visible")) return rf_tf(!(int)SendMessageW(f->toolbar, TB_ISBUTTONHIDDEN, (WPARAM)c->id, 0));
        break;
    case T_DLG_OPEN: case T_DLG_SAVE:
        if (rf_is(p, "FileTitle")) {
            const char *fn = rf_kv_get(c, "FileName"), *s;
            if (!fn) return "";
            s = strrchr(fn, '\\');
            if (!s) s = strrchr(fn, '/');
            return s ? s + 1 : fn;
        }
        break;
    default: break;
    }
    if (CNONVIS(c) || !c->hwnd) {
        kv = rf_kv_get(c, p);
        return kv ? kv : "";
    }
    if (rf_is(p, "Text") || rf_is(p, "Caption") || rf_is(p, "SimpleText")) {
        if (c->type == T_LISTBOX) {
            int i = rf_list_index(c);
            return i >= 0 ? rf_list_item(c, i) : "";
        }
        if (c->type == T_UPDOWN) return rf_istr(c->value);
        if (c->type == T_STATUS || c->type == T_TAB || c->type == T_PROGRESS || c->type == T_TRACKBAR || c->type == T_PICTURE) {
            kv = rf_kv_get(c, "Text");
            return kv ? kv : "";
        }
        return rf_wtext(c->hwnd);
    }
    if (rf_is(p, "Left") || rf_is(p, "Top") || rf_is(p, "Width") || rf_is(p, "Height")) {
        double r[4];
        int k = rf_is(p, "Left") ? 0 : rf_is(p, "Top") ? 1 : rf_is(p, "Width") ? 2 : 3;
        rf_ctl_rect(c, &r[0], &r[1], &r[2], &r[3]);
        return rf_istr((long long)floor(r[k] + 0.5) * f->unit);
    }
    if (rf_is(p, "Visible")) return rf_tf(c->visible);
    if (rf_is(p, "Enabled")) return rf_tf(c->enabled);
    if (rf_is(p, "Checked")) {
        if (c->type == T_CHECKBOX || c->type == T_RADIO)
            return rf_tf((int)SendMessageW(c->hwnd, BM_GETCHECK, 0, 0) == BST_CHECKED);
    }
    if (rf_is(p, "Value")) {
        if (c->type == T_CHECKBOX) return SendMessageW(c->hwnd, BM_GETCHECK, 0, 0) == BST_CHECKED ? "1" : "0";
        if (c->type == T_RADIO) return rf_tf((int)SendMessageW(c->hwnd, BM_GETCHECK, 0, 0) == BST_CHECKED);
        if (c->type == T_UPDOWN) c->value = (int)SendMessageW(c->buddy, UDM_GETPOS32, 0, 0);
        if (c->type == T_TRACKBAR) c->value = (int)SendMessageW(c->hwnd, TBM_GETPOS, 0, 0);
        return rf_istr(c->value);
    }
    if (rf_is(p, "Minimum") || rf_is(p, "Min")) return rf_istr(c->minv);
    if (rf_is(p, "Maximum") || rf_is(p, "Max")) return rf_istr(c->maxv);
    if (rf_is(p, "ListCount") || rf_is(p, "Count") || rf_is(p, "ItemCount")) {
        if (c->type == T_LISTBOX || c->type == T_COMBOBOX) return rf_istr(rf_list_count(c));
        if (c->type == T_TAB) return rf_istr(SendMessageW(c->hwnd, TCM_GETITEMCOUNT, 0, 0));
    }
    if (rf_is(p, "ListIndex") || rf_is(p, "SelectedIndex")) {
        if (c->type == T_LISTBOX || c->type == T_COMBOBOX) return rf_istr(rf_list_index(c));
        if (c->type == T_TAB) return rf_istr(rf_tab_sel(c));
    }
    if (rf_is(p, "NewIndex")) return rf_istr(rf_list_count(c) - 1);
    if (rf_is(p, "Items") || rf_is(p, "List")) {
        if (c->type == T_LISTBOX || c->type == T_COMBOBOX) {
            int i, n = rf_list_count(c);
            size_t total = 1;
            char *out;
            for (i = 0; i < n; i++) total += strlen(rf_list_item(c, i)) + 1;
            out = rf_buf(total);
            for (i = 0; i < n; i++) {
                if (i) strcat(out, ";");
                strcat(out, rf_list_item(c, i));
            }
            return out;
        }
    }
    if (rf_is(p, "SelectedItem")) {
        int i = rf_list_index(c);
        return i >= 0 ? rf_list_item(c, i) : "";
    }
    if (rf_is(p, "BackColor")) return c->has_back ? rf_istr((long long)c->back) : "2147483663";
    if (rf_is(p, "ForeColor")) return c->has_fore ? rf_istr((long long)c->fore) : "0";
    if (rf_is(p, "FontName")) return c->font_name[0] ? rf_utf8(c->font_name) : "Segoe UI";
    if (rf_is(p, "FontSize") || rf_is(p, "Size")) return rad_str(c->font_size);
    if (rf_is(p, "FontBold") || rf_is(p, "Bold")) return rf_tf(c->bold);
    if (rf_is(p, "FontItalic") || rf_is(p, "Italic")) return rf_tf(c->italic);
    if (rf_is(p, "FontUnderline")) return rf_tf(c->underline);
    if (rf_is(p, "Multiline")) return rf_tf(c->multiline);
    if (rf_is(p, "ReadOnly") || rf_is(p, "Locked")) return rf_tf(c->readonly);
    if (rf_is(p, "MaxLength")) return rf_istr(c->maxlen);
    if (rf_is(p, "hWnd")) return rf_istr((long long)(INT_PTR)c->hwnd);
    if (rf_is(p, "SelStart") || rf_is(p, "SelectionStart") || rf_is(p, "SelLength") || rf_is(p, "SelectionLength")) {
        DWORD a = 0, b = 0;
        SendMessageW(c->hwnd, EM_GETSEL, (WPARAM)&a, (LPARAM)&b);
        return rf_istr(rf_is(p, "SelStart") || rf_is(p, "SelectionStart") ? a : b - a);
    }
    if (rf_is(p, "Focused")) return rf_tf(GetFocus() == c->hwnd || (c->inner && GetFocus() == c->inner));
    kv = rf_kv_get(c, p);
    if (kv) return kv;
    if (rf_is(p, "ToolTip") || rf_is(p, "ToolTipText") || rf_is(p, "Tag")) return "";
    return "";
}

/* ================================================================== dialogs */
static HWND rf_owner(void) {
    HWND a = GetActiveWindow();
    if (a && rf_form_of(a)) return a;
    if (g_cur.form && g_cur.form->hwnd) return g_cur.form->hwnd;
    return g_startup && g_startup->hwnd ? g_startup->hwnd : NULL;
}

static int rf_has_rtl(const wchar_t *w) {
    for (; w && *w; w++)
        if ((*w >= 0x0590 && *w <= 0x08FF) || (*w >= 0xFB1D && *w <= 0xFEFC)) return 1;
    return 0;
}

int rad_msgbox_ex(const char *text, const char *title, int flags) {
    wchar_t *w = rf_wide(text), *t = title && *title ? rf_wide(title) : NULL;
    UINT extra = rf_has_rtl(w) ? (MB_RTLREADING | MB_RIGHT) : 0;
    int r = MessageBoxW(rf_owner(), w ? w : L"", t ? t : (g_app[0] ? g_app : L" "), (UINT)flags | extra | MB_SETFOREGROUND);
    free(w);
    free(t);
    return r;
}

void rad_msgbox(const char *text) { rad_msgbox_ex(text, NULL, MB_OK); }

/* a small modal input box (Win32 has no built-in one) */
static struct { HWND edit; int done, ok; } g_inp;

static LRESULT CALLBACK rf_input_proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    switch (m) {
    case WM_COMMAND:
        if (LOWORD(w) == IDOK || LOWORD(w) == IDCANCEL) {
            g_inp.ok = LOWORD(w) == IDOK;
            g_inp.done = 1;
            return 0;
        }
        break;
    case WM_CLOSE:
        g_inp.done = 1;
        g_inp.ok = 0;
        return 0;
    case WM_ERASEBKGND:
        rf_fill_bg(h, (HDC)w, GetSysColorBrush(COLOR_BTNFACE));
        return 1;
    default: break;
    }
    return DefWindowProcW(h, m, w, l);
}

const char *rad_input_ex(const char *prompt, const char *title, const char *def) {
    static int reg;
    HWND owner = rf_owner(), h, lbl, ok, cancel;
    wchar_t *wp = rf_wide(prompt), *wt = title && *title ? rf_wide(title) : NULL, *wd = rf_wide(def ? def : "");
    int dpi = rf_dpi_of(owner), rtl = rf_has_rtl(wp);
    RfForm tmp;
    RECT r = {0, 0, 0, 0};
    HFONT font;
    LOGFONTW lf;
    MSG msg;
    const char *result = "";
    memset(&tmp, 0, sizeof tmp);
    tmp.dpi = dpi;
    if (!g_inited) rad_init();
    if (!reg) {
        WNDCLASSEXW wc;
        memset(&wc, 0, sizeof wc);
        wc.cbSize = sizeof wc;
        wc.lpfnWndProc = rf_input_proc;
        wc.hInstance = g_inst;
        wc.hCursor = LoadCursor(NULL, IDC_ARROW);
        wc.lpszClassName = L"RadFormsInput";
        RegisterClassExW(&wc);
        reg = 1;
    }
    r.right = S(&tmp, 360);
    r.bottom = S(&tmp, 130);
    AdjustWindowRectEx(&r, WS_CAPTION | WS_SYSMENU, FALSE, WS_EX_DLGMODALFRAME);
    h = CreateWindowExW(WS_EX_DLGMODALFRAME | WS_EX_CONTROLPARENT | (rtl ? WS_EX_LAYOUTRTL : 0), L"RadFormsInput",
                        wt ? wt : (g_app[0] ? g_app : L" "), WS_POPUP | WS_CAPTION | WS_SYSMENU,
                        CW_USEDEFAULT, CW_USEDEFAULT, r.right - r.left, r.bottom - r.top, owner, NULL, g_inst, NULL);
    memset(&lf, 0, sizeof lf);
    lf.lfHeight = -MulDiv(9, dpi, 72);
    lf.lfCharSet = DEFAULT_CHARSET;
    wcscpy(lf.lfFaceName, L"Segoe UI");
    font = CreateFontIndirectW(&lf);
    lbl = CreateWindowExW(0, L"STATIC", wp, WS_CHILD | WS_VISIBLE | SS_NOPREFIX, S(&tmp, 12), S(&tmp, 10),
                          S(&tmp, 250), S(&tmp, 60), h, NULL, g_inst, NULL);
    ok = CreateWindowExW(0, L"BUTTON", L"OK", WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON, S(&tmp, 272),
                         S(&tmp, 10), S(&tmp, 76), S(&tmp, 25), h, (HMENU)IDOK, g_inst, NULL);
    cancel = CreateWindowExW(0, L"BUTTON", L"Cancel", WS_CHILD | WS_VISIBLE | WS_TABSTOP, S(&tmp, 272), S(&tmp, 40),
                             S(&tmp, 76), S(&tmp, 25), h, (HMENU)IDCANCEL, g_inst, NULL);
    g_inp.edit = CreateWindowExW(WS_EX_CLIENTEDGE, L"EDIT", wd, WS_CHILD | WS_VISIBLE | WS_TABSTOP | ES_AUTOHSCROLL,
                                 S(&tmp, 12), S(&tmp, 96), S(&tmp, 336), S(&tmp, 23), h, NULL, g_inst, NULL);
    SendMessageW(lbl, WM_SETFONT, (WPARAM)font, 0);
    SendMessageW(ok, WM_SETFONT, (WPARAM)font, 0);
    SendMessageW(cancel, WM_SETFONT, (WPARAM)font, 0);
    SendMessageW(g_inp.edit, WM_SETFONT, (WPARAM)font, 0);
    SendMessageW(g_inp.edit, EM_SETSEL, 0, -1);
    {   /* centre on the owner */
        RECT o, me;
        if (owner) GetWindowRect(owner, &o);
        else SystemParametersInfoW(SPI_GETWORKAREA, 0, &o, 0);
        GetWindowRect(h, &me);
        SetWindowPos(h, NULL, o.left + ((o.right - o.left) - (me.right - me.left)) / 2,
                     o.top + ((o.bottom - o.top) - (me.bottom - me.top)) / 2, 0, 0, SWP_NOSIZE | SWP_NOZORDER);
    }
    if (owner) EnableWindow(owner, FALSE);
    ShowWindow(h, SW_SHOW);
    SetFocus(g_inp.edit);
    g_inp.done = g_inp.ok = 0;
    while (!g_inp.done && GetMessageW(&msg, NULL, 0, 0) > 0) {
        if (IsDialogMessageW(h, &msg)) continue;
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    if (g_inp.ok) result = rf_wtext(g_inp.edit);
    if (owner) EnableWindow(owner, TRUE);
    DestroyWindow(h);
    if (owner) SetActiveWindow(owner);
    DeleteObject(font);
    free(wp);
    free(wt);
    free(wd);
    return result;
}

const char *rad_input(const char *prompt) { return rad_input_ex(prompt, NULL, ""); }

static wchar_t *rf_filter(const char *f) {           /* "Text|*.txt|All|*.*" -> "Text\0*.txt\0All\0*.*\0\0" */
    wchar_t *w = rf_wide(f && *f ? f : "All files|*.*"), *p;
    size_t n;
    if (!w) return NULL;
    n = wcslen(w);
    p = (wchar_t *)realloc(w, (n + 2) * sizeof(wchar_t));
    if (!p) { free(w); return NULL; }
    for (w = p; *w; w++)
        if (*w == L'|') *w = 0;
    p[n] = 0;
    p[n + 1] = 0;
    return p;
}

static const char *rf_dialog(RfCtl *c, int kind) {
    HWND owner = rf_owner();
    if (kind == T_DLG_OPEN || kind == T_DLG_SAVE) {
        OPENFILENAMEW o;
        wchar_t file[MAX_PATH * 4], *filter = rf_filter(rf_kv_get(c, "Filter")), *title = NULL, *dir = NULL, *ext = NULL;
        const char *fn = rf_kv_get(c, "FileName"), *v;
        BOOL ok;
        memset(&o, 0, sizeof o);
        file[0] = 0;
        if (fn) {
            wchar_t *w = rf_wide(fn);
            if (w) { wcsncpy(file, w, MAX_PATH * 4 - 1); file[MAX_PATH * 4 - 1] = 0; free(w); }
        }
        if ((v = rf_kv_get(c, "Title")) && *v) title = rf_wide(v);
        if ((v = rf_kv_get(c, "InitialDirectory")) && *v) dir = rf_wide(v);
        if (kind == T_DLG_SAVE && filter) {         /* default extension from the first pattern "*.txt" */
            wchar_t *pat = filter + wcslen(filter) + 1;
            if (pat[0] == L'*' && pat[1] == L'.' && pat[2] && !wcschr(pat + 2, L'*')) ext = pat + 2;
        }
        o.lStructSize = sizeof o;
        o.hwndOwner = owner;
        o.lpstrFilter = filter;
        o.lpstrFile = file;
        o.nMaxFile = MAX_PATH * 4;
        o.lpstrTitle = title;
        o.lpstrInitialDir = dir;
        o.lpstrDefExt = ext;
        o.Flags = OFN_EXPLORER | OFN_HIDEREADONLY | OFN_NOCHANGEDIR |
                  (kind == T_DLG_OPEN ? OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST : OFN_OVERWRITEPROMPT);
        ok = kind == T_DLG_OPEN ? GetOpenFileNameW(&o) : GetSaveFileNameW(&o);
        if (ok) rf_kv_set(c, "FileName", rf_utf8(file));
        free(filter);
        free(title);
        free(dir);
        return ok ? "OK" : "Cancel";
    }
    if (kind == T_DLG_COLOR) {
        static COLORREF custom[16];
        CHOOSECOLORW cc;
        COLORREF col = 0;
        memset(&cc, 0, sizeof cc);
        rf_color(rf_kv_get(c, "Color"), &col);
        cc.lStructSize = sizeof cc;
        cc.hwndOwner = owner;
        cc.rgbResult = col;
        cc.lpCustColors = custom;
        cc.Flags = CC_RGBINIT | CC_FULLOPEN;
        if (!ChooseColorW(&cc)) return "Cancel";
        {
            char b[16];
            snprintf(b, sizeof b, "#%02X%02X%02X", GetRValue(cc.rgbResult), GetGValue(cc.rgbResult), GetBValue(cc.rgbResult));
            rf_kv_set(c, "Color", b);
        }
        return "OK";
    }
    if (kind == T_DLG_FONT) {
        CHOOSEFONTW cf;
        LOGFONTW lf;
        HDC dc = GetDC(NULL);
        const char *v = rf_kv_get(c, "FontName");
        double size = rad_num(rf_kv_get(c, "FontSize"));
        memset(&cf, 0, sizeof cf);
        memset(&lf, 0, sizeof lf);
        if (size <= 0) size = 9;
        lf.lfHeight = -(LONG)(size * GetDeviceCaps(dc, LOGPIXELSY) / 72.0 + 0.5);
        lf.lfWeight = rf_bool(rf_kv_get(c, "FontBold")) ? FW_BOLD : FW_NORMAL;
        lf.lfItalic = (BYTE)rf_bool(rf_kv_get(c, "FontItalic"));
        {
            wchar_t *w = rf_wide(v && *v ? v : "Segoe UI");
            if (w) { wcsncpy(lf.lfFaceName, w, LF_FACESIZE - 1); free(w); }
        }
        cf.lStructSize = sizeof cf;
        cf.hwndOwner = owner;
        cf.lpLogFont = &lf;
        cf.Flags = CF_SCREENFONTS | CF_INITTOLOGFONTSTRUCT;
        if (!ChooseFontW(&cf)) { ReleaseDC(NULL, dc); return "Cancel"; }
        ReleaseDC(NULL, dc);
        rf_kv_set(c, "FontName", rf_utf8(lf.lfFaceName));
        rf_kv_set(c, "FontSize", rad_str(cf.iPointSize / 10.0));
        rf_kv_set(c, "FontBold", rf_tf(lf.lfWeight >= FW_BOLD));
        rf_kv_set(c, "FontItalic", rf_tf(lf.lfItalic));
        return "OK";
    }
    if (kind == T_DLG_FOLDER) {
        BROWSEINFOW bi;
        wchar_t path[MAX_PATH], *title = NULL;
        LPITEMIDLIST id;
        const char *v = rf_kv_get(c, "Description");
        static int ole;
        if (!ole) { OleInitialize(NULL); ole = 1; }
        if (!v || !*v) v = rf_kv_get(c, "Title");
        if (v && *v) title = rf_wide(v);
        memset(&bi, 0, sizeof bi);
        bi.hwndOwner = owner;
        bi.lpszTitle = title;
        bi.ulFlags = BIF_RETURNONLYFSDIRS | BIF_NEWDIALOGSTYLE;
        id = SHBrowseForFolderW(&bi);
        free(title);
        if (!id) return "Cancel";
        path[0] = 0;
        SHGetPathFromIDListW(id, path);
        CoTaskMemFree(id);
        rf_kv_set(c, "SelectedPath", rf_utf8(path));
        return "OK";
    }
    return "Cancel";
}

/* ================================================================== methods */
static const char *rf_arg_n(const char *args, int n) {     /* field n of a \t separated list */
    const char *p = args ? args : "";
    char *out;
    int i;
    for (i = 0; i < n && p; i++) {
        p = strchr(p, '\t');
        if (p) p++;
    }
    if (!p) return "";
    {
        const char *e = strchr(p, '\t');
        size_t len = e ? (size_t)(e - p) : strlen(p);
        out = rf_buf(len + 1);
        memcpy(out, p, len);
        out[len] = 0;
    }
    return out;
}

static const char *rf_call_form(RfForm *f, const char *m, const char *args) {
    {
        int handled;
        const char *r = rf_fx_call(f, NULL, m, args, &handled);
        if (handled) return r;
    }
    if (rf_is(m, "Show")) {
        if (rf_int(rf_arg_n(args, 0)) == 1) rad_show_modal(f->name);
        else rf_form_load(f, 1);
        return "";
    }
    if (rf_is(m, "ShowDialog")) { rad_show_modal(f->name); return "OK"; }
    if (rf_is(m, "Hide")) { rf_form_hide(f); return ""; }
    if (rf_is(m, "Load")) { rf_form_load(f, 0); return ""; }
    if (rf_is(m, "Close") || rf_is(m, "Unload")) {
        if (rf_is(m, "Close")) PostMessageW(f->hwnd, WM_CLOSE, 0, 0);
        else rf_form_close_now(f);
        return "";
    }
    if (rf_is(m, "Refresh")) { InvalidateRect(f->hwnd, NULL, TRUE); UpdateWindow(f->hwnd); return ""; }
    if (rf_is(m, "SetFocus") || rf_is(m, "Activate")) { SetForegroundWindow(f->hwnd); return ""; }
    if (rf_is(m, "Move")) {
        static const char *const k[4] = {"Left", "Top", "Width", "Height"};
        int i;
        for (i = 0; i < 4; i++) {
            const char *v = rf_arg_n(args, i);
            if (*v) rf_set_form(f, k[i], v);
        }
        return "";
    }
    return rf_get_form(f, m);
}

static const char *rf_call(RfForm *f, RfCtl *c, const char *m, const char *args) {
    const char *a0 = rf_arg_n(args, 0);
    if (!c) return rf_call_form(f, m, args);
    if (rf_is(m, "GoToState")) {
        int handled;
        const char *r = rf_fx_call(f, c, m, args, &handled);
        if (handled) return r;
    }
    if (c->type == T_CUSTOM && c->cls->invoke) {
        const char *r = c->cls->invoke((rf_handle)c, c->state, m, args);
        if (r) return r;
    }
    if (c->type >= T_DLG_OPEN && c->type <= T_DLG_FOLDER) {
        int kind = c->type;
        if (rf_is(m, "ShowOpen")) kind = T_DLG_OPEN;
        else if (rf_is(m, "ShowSave")) kind = T_DLG_SAVE;
        else if (rf_is(m, "ShowColor")) kind = T_DLG_COLOR;
        else if (rf_is(m, "ShowFont")) kind = T_DLG_FONT;
        else if (rf_is(m, "ShowFolder")) kind = T_DLG_FOLDER;
        else if (!rf_is(m, "ShowDialog")) return rf_get(f, c, m);
        return rf_dialog(c, kind);
    }
    if (c->type == T_TIMER) {
        if (rf_is(m, "Start") || rf_is(m, "Stop")) { c->timer_on = rf_is(m, "Start"); rf_timer_apply(c); return ""; }
        return rf_get(f, c, m);
    }
    if (c->type == T_MENUITEM || c->type == T_TOOLBTN) {
        if (rf_is(m, "PerformClick")) { rf_post_c(c, "Click", ""); return ""; }
        return rf_get(f, c, m);
    }
    if (c->type == T_LISTBOX || c->type == T_COMBOBOX) {
        if (rf_is(m, "AddItem") || rf_is(m, "Add") || rf_is(m, "Items.Add")) {
            const char *at = rf_arg_n(args, 1);
            rf_list_add(c, a0, *at ? rf_int(at) : -1);
            if (c->type == T_LISTBOX) SendMessageW(c->hwnd, LB_SETTOPINDEX, (WPARAM)(rf_list_count(c) - 1), 0);
            return "";
        }
        if (rf_is(m, "RemoveItem") || rf_is(m, "RemoveAt")) {
            int i = rf_int(a0);
            SendMessageW(c->hwnd, c->type == T_LISTBOX ? LB_DELETESTRING : CB_DELETESTRING, (WPARAM)i, 0);
            if (c->last_sel == i) c->last_sel = -1;
            return "";
        }
        if (rf_is(m, "Clear") || rf_is(m, "Items.Clear")) {
            SendMessageW(c->hwnd, c->type == T_LISTBOX ? LB_RESETCONTENT : CB_RESETCONTENT, 0, 0);
            if (c->type == T_COMBOBOX && c->dropstyle) SetWindowTextW(c->hwnd, L"");
            c->last_sel = -1;
            return "";
        }
        if (rf_is(m, "List") || rf_is(m, "Item") || rf_is(m, "Items")) {
            if (!*a0) return rf_get(f, c, "Items");
            return rf_list_item(c, rf_int(a0));
        }
        if (rf_is(m, "IndexOf") || rf_is(m, "FindString")) {
            int i, n = rf_list_count(c);
            for (i = 0; i < n; i++)
                if (strcmp(rf_list_item(c, i), a0) == 0) return rf_istr(i);
            return "-1";
        }
    }
    if (c->type == T_TEXTBOX) {
        if (rf_is(m, "Clear")) { rf_set_wtext(c->hwnd, "", 0); return ""; }
        if (rf_is(m, "AppendText")) {
            int n = GetWindowTextLengthW(c->hwnd);
            SendMessageW(c->hwnd, EM_SETSEL, (WPARAM)n, n);
            rf_set(f, c, "SelText", a0);
            return "";
        }
        if (rf_is(m, "SelectAll")) { SendMessageW(c->hwnd, EM_SETSEL, 0, -1); return ""; }
    }
    if (c->type == T_TAB && rf_is(m, "TabCaption")) {
        wchar_t w[256];
        TCITEMW it;
        memset(&it, 0, sizeof it);
        it.mask = TCIF_TEXT;
        it.pszText = w;
        it.cchTextMax = 255;
        w[0] = 0;
        SendMessageW(c->hwnd, TCM_GETITEMW, (WPARAM)rf_int(a0), (LPARAM)&it);
        return rf_utf8(w);
    }
    if (rf_is(m, "PerformClick") && c->hwnd) { SendMessageW(c->hwnd, BM_CLICK, 0, 0); return ""; }
    if (rf_is(m, "SetFocus") || rf_is(m, "Focus")) { if (c->hwnd) SetFocus(c->inner ? c->inner : c->hwnd); return ""; }
    if (rf_is(m, "Refresh")) { if (c->hwnd) { InvalidateRect(c->hwnd, NULL, TRUE); UpdateWindow(c->hwnd); } return ""; }
    if (rf_is(m, "Move")) {
        static const char *const k[4] = {"Left", "Top", "Width", "Height"};
        int i;
        for (i = 0; i < 4; i++) {
            const char *v = rf_arg_n(args, i);
            if (*v) rf_set(f, c, k[i], v);
        }
        return "";
    }
    if (rf_is(m, "ZOrder") || rf_is(m, "BringToFront") || rf_is(m, "SendToBack")) {
        int back = rf_is(m, "SendToBack") || (rf_is(m, "ZOrder") && rf_int(a0) == 1);
        if (c->hwnd) SetWindowPos(c->hwnd, back ? HWND_BOTTOM : HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE);
        return "";
    }
    if (rf_is(m, "Show")) { rf_set(f, c, "Visible", "True"); return ""; }
    if (rf_is(m, "Hide")) { rf_set(f, c, "Visible", "False"); return ""; }
    return rf_get(f, c, m);
}

/* ================================================================== public API */
void rad_set(const char *obj, const char *prop, const char *value) {
    RfCtl *c;
    RfForm *f = rf_resolve(obj, &c);
    if (f && prop) rf_set(f, c, prop, value);
}

void rad_set_num(const char *obj, const char *prop, double value) { rad_set(obj, prop, rad_str(value)); }

const char *rad_get(const char *obj, const char *prop) {
    RfCtl *c;
    RfForm *f = rf_resolve(obj, &c);
    return f && prop ? rf_get(f, c, prop) : "";
}

double rad_get_num(const char *obj, const char *prop) { return rad_num(rad_get(obj, prop)); }

const char *rad_call(const char *obj, const char *method, const char *args) {
    RfCtl *c;
    RfForm *f = rf_resolve(obj, &c);
    return f && method ? rf_call(f, c, method, args ? args : "") : "";
}

void rad_show(const char *form) {
    RfForm *f;
    if (!g_inited) rad_init();
    f = rf_form_named(form ? form : "");
    if (f) {
        f->want_visible = 1;
        rf_form_load(f, 1);
    }
}

void rad_hide(const char *form) {
    RfForm *f = rf_form_named(form ? form : "");
    if (f) rf_form_hide(f);
}

void rad_show_modal(const char *form) {
    RfForm *f = rf_form_named(form ? form : "");
    Ev saved;
    char so[256], se[256], sa[1024];
    int saved_in, i, *was_enabled;
    if (!f) return;
    if (!g_inited) rad_init();
    rf_form_load(f, 1);
    f->want_visible = 1;
    if (!g_dispatch && !g_evfn) return;          /* pull mode: modeless */
    was_enabled = (int *)calloc((size_t)g_nforms, sizeof(int));
    for (i = 0; i < g_nforms; i++)
        if (&g_forms[i] != f && g_forms[i].hwnd && was_enabled) {
            was_enabled[i] = IsWindowEnabled(g_forms[i].hwnd);
            EnableWindow(g_forms[i].hwnd, FALSE);
        }
    saved = g_cur;
    saved_in = g_in_event;
    memcpy(so, rad_obj, sizeof so);
    memcpy(se, rad_ev, sizeof se);
    memcpy(sa, rad_args, sizeof sa);
    g_in_event = 0;
    f->modal = 1;
    while (f->loaded && f->want_visible && !g_quit) {
        if (!rad_next_event()) break;
        rf_dispatch_current();
        rad_done();
    }
    f->modal = 0;
    for (i = 0; i < g_nforms; i++)
        if (&g_forms[i] != f && g_forms[i].hwnd && was_enabled && was_enabled[i]) EnableWindow(g_forms[i].hwnd, TRUE);
    free(was_enabled);
    g_cur = saved;
    g_in_event = saved_in;
    memcpy(rad_obj, so, sizeof so);
    memcpy(rad_ev, se, sizeof se);
    memcpy(rad_args, sa, sizeof sa);
    if (g_cur.form && g_cur.form->hwnd) SetForegroundWindow(g_cur.form->hwnd);
}

void rad_print(const char *text) {
    HANDLE out = GetStdHandle(STD_OUTPUT_HANDLE);
    wchar_t *w = rf_wide(text);
    if (w) { OutputDebugStringW(w); OutputDebugStringW(L"\n"); free(w); }
    if (out && out != INVALID_HANDLE_VALUE) {
        DWORD n;
        WriteFile(out, text ? text : "", (DWORD)strlen(text ? text : ""), &n, NULL);
        WriteFile(out, "\r\n", 2, &n, NULL);
    }
}

const char *rad_arg(int index) {
    const char *p = rad_args;
    int i = 0;
    while (*p) {
        size_t n;
        while (*p == ' ') p++;
        if (!*p) break;
        n = strcspn(p, " ");
        if (i == index) {
            char *b = rf_buf(n + 1);
            memcpy(b, p, n);
            b[n] = 0;
            return b;
        }
        p += n;
        i++;
    }
    return "";
}

double rad_num(const char *text) {
    char *end;
    double v;
    if (!text) return 0;
    while (*text == ' ' || *text == '\t') text++;
    v = strtod(text, &end);
    return end == text ? 0 : v;
}

const char *rad_str(double x) {
    char *b = rf_buf(40);
    if (x == floor(x) && fabs(x) < 1e15) snprintf(b, 40, "%.0f", x);
    else snprintf(b, 40, "%.15g", x);
    return b;
}

/* ------------------------------------------------------------------ protocol in process */
static char g_reply[1];
static const char *rf_command(const char *line, int trim);

/* "ESC <command>" (radide/runtimes/bridge.py): \\ \n \r escaped in the values (multi-line text); the answer is
   escaped the same way */
static char *rf_unesc(const char *s) {
    char *b = rf_buf(strlen(s) + 1), *o = b;
    while (*s) {
        if (s[0] == '\\' && (s[1] == '\\' || s[1] == 'n' || s[1] == 'r')) {
            *o++ = s[1] == 'n' ? '\n' : (s[1] == 'r' ? '\r' : '\\');
            s += 2;
        } else {
            *o++ = *s++;
        }
    }
    *o = 0;
    return b;
}

static const char *rf_esc(const char *s) {
    char *b = rf_buf(2 * strlen(s) + 1), *o = b;
    for (; *s; s++) {
        if (*s == '\\') { *o++ = '\\'; *o++ = '\\'; }
        else if (*s == '\n') { *o++ = '\\'; *o++ = 'n'; }
        else if (*s == '\r') { *o++ = '\\'; *o++ = 'r'; }
        else *o++ = *s;
    }
    *o = 0;
    return b;
}

const char *rad_command(const char *line) {
    if (line && strncmp(line, "ESC ", 4) == 0) {
        char *raw = rf_buf(strlen(line) + 1);
        const char *r;
        size_t k;
        strcpy(raw, line + 4);
        k = strlen(raw);
        while (k && (raw[k - 1] == '\n' || raw[k - 1] == '\r')) raw[--k] = 0;
        r = rf_command(rf_unesc(raw), 0);
        return r ? rf_esc(r) : NULL;
    }
    return rf_command(line, 1);
}

static const char *rf_command(const char *line, int trim) {
    char cmd[16], *rest, *copy, *a, *b;
    size_t n = 0;
    if (!line) return NULL;
    while (line[n] && line[n] != ' ' && n < sizeof cmd - 1) { cmd[n] = line[n]; n++; }
    cmd[n] = 0;
    copy = rf_buf(strlen(line) + 1);
    strcpy(copy, line);
    if (trim) { size_t k = strlen(copy); while (k && (copy[k - 1] == '\n' || copy[k - 1] == '\r')) copy[--k] = 0; }
    rest = copy + n + (copy[n] == ' ');
    if (rf_ieq(cmd, "DONE")) { rad_done(); return NULL; }
    if (rf_ieq(cmd, "END")) { rad_end(); return NULL; }
    if (rf_ieq(cmd, "MSGBOX")) { rad_msgbox(rest); return "1"; }
    if (rf_ieq(cmd, "INPUT")) return rad_input(rest);
    if (rf_ieq(cmd, "SHOW")) { rad_show(rest); return NULL; }
    if (rf_ieq(cmd, "HIDE")) { rad_hide(rest); return NULL; }
    if (rf_ieq(cmd, "SET") || rf_ieq(cmd, "GET") || rf_ieq(cmd, "CALL")) {
        a = strchr(rest, ' ');
        if (a) *a++ = 0;
        else a = g_reply;
        b = rf_ieq(cmd, "GET") ? NULL : strchr(a, ' ');
        if (b) *b++ = 0;
        else b = g_reply;
        if (rf_ieq(cmd, "SET")) { rad_set(rest, a, b); return NULL; }
        if (rf_ieq(cmd, "GET")) {
            size_t k = strlen(a);
            while (k && a[k - 1] == ' ') a[--k] = 0;
            return rad_get(rest, a);
        }
        return rad_call(rest, a, b);
    }
    rad_print(line);
    return NULL;
}

const char *rad_event_line(void) {
    char *b;
    if (!rad_next_event()) return "QUIT";
    b = rf_buf(strlen(rad_obj) + strlen(rad_ev) + strlen(rad_args) + 16);
    sprintf(b, "EVENT %s %s%s%s", rad_obj, rad_ev, rad_args[0] ? " " : "", rad_args);
    return b;
}

static char *g_pending;
void rad_line_out(const char *line) {
    const char *r = rad_command(line);
    if (r) {
        free(g_pending);
        g_pending = rf_strdup(r);
    }
}

const char *rad_line_in(void) {
    if (g_pending) {
        char *b = rf_buf(strlen(g_pending) + 1);
        strcpy(b, g_pending);
        free(g_pending);
        g_pending = NULL;
        return b;
    }
    return rad_event_line();
}

/* ------------------------------------------------------------------ in-process radcall */
void rad_register(const char *name, rad_func_fn fn) {
    Fn *f = (Fn *)calloc(1, sizeof *f);
    if (!f) return;
    f->name = rf_strdup(name);
    f->fn = fn;
    f->next = g_funcs;
    g_funcs = f;
}

const char *rad_error(void) { return g_err; }

const char *rad_fail(const char *message) {
    snprintf(g_err, sizeof g_err, "%s", message && *message ? message : "error");
    return NULL;
}

static const char *js_ws(const char *p) {
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') p++;
    return p;
}

static const char *js_skip(const char *p) {
    p = js_ws(p);
    if (*p == '"') {
        p++;
        while (*p && *p != '"') { if (*p == '\\' && p[1]) p++; p++; }
        return *p ? p + 1 : p;
    }
    if (*p == '[' || *p == '{') {
        int depth = 0;
        while (*p) {
            if (*p == '"') { p = js_skip(p); continue; }
            if (*p == '[' || *p == '{') depth++;
            else if (*p == ']' || *p == '}') { depth--; if (depth == 0) return p + 1; }
            p++;
        }
        return p;
    }
    while (*p && *p != ',' && *p != ']' && *p != '}' && *p != ' ') p++;
    return p;
}

const char *radcall(const char *name, const char *json_args) {
    Fn *f;
    const char *argv[64];
    char *store;
    int argc = 0;
    const char *p, *res;
    g_err[0] = 0;
    for (f = g_funcs; f; f = f->next)
        if (rf_ieq(f->name, name ? name : "")) break;
    if (!f) {
        snprintf(g_err, sizeof g_err, "%s is not available in this program", name ? name : "");
        return "";
    }
    store = rf_strdup(json_args ? json_args : "[]");
    p = js_ws(store);
    if (*p == '[') {
        p = js_ws(p + 1);
        while (*p && *p != ']' && argc < 64) {
            const char *e = js_skip(p);
            argv[argc++] = p;
            if (e == p) break;
            p = js_ws(e);
            if (*p == ',') { *(char *)p = 0; p = js_ws(p + 1); }
            else if (*p == ']') *(char *)p = 0;
        }
        if (argc) {         /* cut trailing blanks of each argument */
            int i;
            for (i = 0; i < argc; i++) {
                char *e = (char *)js_skip(argv[i]);
                if (*e) *e = 0;
            }
        }
    }
    res = f->fn(argc, argv);
    free(store);
    if (!res) { if (!g_err[0]) rad_fail("error"); return ""; }
    if (g_err[0]) return "";
    {
        char *out = rf_buf(strlen(res) + 1);
        strcpy(out, res);
        return *out ? out : "null";
    }
}

const char *rad_json_str(const char *json) {
    const char *p = js_ws(json ? json : "");
    char *out;
    size_t n = 0;
    if (*p != '"') {
        const char *e = js_skip(p);
        out = rf_buf((size_t)(e - p) + 1);
        memcpy(out, p, (size_t)(e - p));
        out[e - p] = 0;
        return out;
    }
    out = rf_buf(strlen(p) + 1);
    p++;
    while (*p && *p != '"') {
        if (*p == '\\' && p[1]) {
            p++;
            switch (*p) {
            case 'n': out[n++] = '\n'; break;
            case 't': out[n++] = '\t'; break;
            case 'r': out[n++] = '\r'; break;
            case 'b': out[n++] = '\b'; break;
            case 'f': out[n++] = '\f'; break;
            case 'u': {
                unsigned cp = 0;
                int i;
                for (i = 1; i <= 4 && p[i]; i++) {
                    char ch = p[i];
                    cp = cp * 16 + (unsigned)(ch >= '0' && ch <= '9' ? ch - '0' : (ch | 32) - 'a' + 10);
                }
                p += 4;
                if (cp < 0x80) out[n++] = (char)cp;
                else if (cp < 0x800) { out[n++] = (char)(0xC0 | (cp >> 6)); out[n++] = (char)(0x80 | (cp & 63)); }
                else {
                    out[n++] = (char)(0xE0 | (cp >> 12)); out[n++] = (char)(0x80 | ((cp >> 6) & 63));
                    out[n++] = (char)(0x80 | (cp & 63));
                }
                break;
            }
            default: out[n++] = *p;
            }
            p++;
        } else {
            out[n++] = *p++;
        }
    }
    out[n] = 0;
    return out;
}

double rad_json_num(const char *json) {
    const char *p = js_ws(json ? json : "");
    if (strncmp(p, "true", 4) == 0) return 1;
    if (*p == '"') return rad_num(rad_json_str(p));
    return rad_num(p);
}

const char *rad_json_quote(const char *text) {
    const unsigned char *p = (const unsigned char *)(text ? text : "");
    char *out = rf_buf(strlen((const char *)p) * 6 + 3);
    size_t n = 0;
    out[n++] = '"';
    for (; *p; p++) {
        if (*p == '"' || *p == '\\') { out[n++] = '\\'; out[n++] = (char)*p; }
        else if (*p == '\n') { out[n++] = '\\'; out[n++] = 'n'; }
        else if (*p == '\r') { out[n++] = '\\'; out[n++] = 'r'; }
        else if (*p == '\t') { out[n++] = '\\'; out[n++] = 't'; }
        else if (*p < 0x20) n += (size_t)sprintf(out + n, "\\u%04x", *p);
        else out[n++] = (char)*p;
    }
    out[n++] = '"';
    out[n] = 0;
    return out;
}

const char *rad_json_numtext(double x) {
    if (x != x || x > 1.7e308 || x < -1.7e308) return "null";
    return rad_str(x);
}

/* RAD Hub worker entry points: a native GUI program is never a worker */
int rad_wk_next(void) { return 0; }
const char *rad_wk_func(void) { return ""; }
int rad_wk_argc(void) { return 0; }
const char *rad_wk_arg(int i) { (void)i; return ""; }
void rad_wk_reply(const char *json) { (void)json; }
void rad_wk_error(const char *message) { (void)message; }
int rad_worker_main(const char *(*dispatch)(const char *, int, const char **, int *)) { (void)dispatch; return 0; }

/* ================================================================== class registry */
static void rf_init_registry(void) {
    static int done;
    static const struct { int t; unsigned flags; const char *events; } B[] = {
        {T_BUTTON, RF_CLASS_FOCUSABLE, "Click"}, {T_LABEL, 0, "Click,DoubleClick"},
        {T_TEXTBOX, RF_CLASS_FOCUSABLE, "TextChanged"}, {T_CHECKBOX, RF_CLASS_FOCUSABLE, "CheckedChanged,Click"},
        {T_RADIO, RF_CLASS_FOCUSABLE, "CheckedChanged,Click"},
        {T_LISTBOX, RF_CLASS_FOCUSABLE, "SelectedIndexChanged,DoubleClick"},
        {T_COMBOBOX, RF_CLASS_FOCUSABLE, "SelectedIndexChanged,TextChanged"}, {T_PICTURE, 0, "Click,DoubleClick"},
        {T_PROGRESS, 0, ""}, {T_UPDOWN, RF_CLASS_FOCUSABLE, "ValueChanged"},
        {T_TRACKBAR, RF_CLASS_FOCUSABLE, "ValueChanged"}, {T_PANEL, RF_CLASS_CONTAINER, "Click"},
        {T_GROUPBOX, RF_CLASS_CONTAINER, ""}, {T_TAB, RF_CLASS_CONTAINER | RF_CLASS_FOCUSABLE, "SelectedIndexChanged"},
        {T_LINK, 0, "Click"}, {T_STATUS, 0, "Click"}, {T_TIMER, RF_CLASS_NONVISUAL, "Tick"},
        {T_DLG_OPEN, RF_CLASS_NONVISUAL, ""}, {T_DLG_SAVE, RF_CLASS_NONVISUAL, ""},
        {T_DLG_COLOR, RF_CLASS_NONVISUAL, ""}, {T_DLG_FONT, RF_CLASS_NONVISUAL, ""},
        {T_DLG_FOLDER, RF_CLASS_NONVISUAL, ""}};
    size_t i;
    if (done) return;
    done = 1;
    for (i = 0; i < sizeof B / sizeof B[0] && g_nclasses < MAX_CLASSES; i++) {
        rf_class *k = &g_classes[g_nclasses++];
        memset(k, 0, sizeof *k);
        k->size = (int)sizeof *k;
        k->name = TYPE_NAMES[B[i].t];
        k->flags = B[i].flags | RF_CLASS_BUILTIN;
        k->events = B[i].events;
    }
}

int rf_register_class(const rf_class *cls) {
    rf_class k;
    int i;
    if (!cls || !cls->name || !*cls->name || cls->size < (int)sizeof(int)) return 0;
    rf_init_registry();
    memset(&k, 0, sizeof k);
    memcpy(&k, cls, (size_t)cls->size < sizeof k ? (size_t)cls->size : sizeof k);
    k.size = (int)sizeof k;
    k.flags &= ~(unsigned)RF_CLASS_BUILTIN;
    for (i = 0; i < g_nclasses; i++)
        if (rf_ieq(g_classes[i].name, k.name)) { g_classes[i] = k; return 1; }
    if (g_nclasses >= MAX_CLASSES) return 0;
    g_classes[g_nclasses++] = k;
    return 1;
}

const rf_class *rf_find_class(const char *name) {
    int i;
    rf_init_registry();
    for (i = 0; i < g_nclasses; i++)
        if (rf_ieq(g_classes[i].name, name ? name : "")) return &g_classes[i];
    return NULL;
}

int rf_class_count(void) { rf_init_registry(); return g_nclasses; }
const rf_class *rf_class_at(int i) { rf_init_registry(); return i >= 0 && i < g_nclasses ? &g_classes[i] : NULL; }

/* modules linked into the exe register their classes here (the IDE builder generates it; weak = optional) */
#if defined(__GNUC__)
extern void rad_modules_init(void) __attribute__((weak));
static void rf_modules(void) { if (rad_modules_init) rad_modules_init(); }
#else
void rf_no_modules(void) {}
void rad_modules_init(void);
#pragma comment(linker, "/alternatename:rad_modules_init=rf_no_modules")
static void rf_modules(void) { rad_modules_init(); }
#endif

/* ================================================================== themes */
#define MAX_THEMES 16
static rf_theme g_themes[MAX_THEMES];
static int g_nthemes;

static void rf_init_themes(void) {
    static int done;
    rf_theme t;
    if (done) return;
    done = 1;
    memset(&t, 0, sizeof t);
    t.size = (int)sizeof t;
    t.font_name = "Segoe UI";
    t.font_size = 9;
    t.border_width = 1;
    t.padding = 6;
    t.anim_ms = 120;
    /* Light: the system look for standard controls; these colours are for owner-drawn ones */
    t.name = "Light"; t.dark = 0; t.radius = 3;
    t.window = RGB(240, 240, 240); t.window_text = RGB(0, 0, 0); t.face = RGB(225, 225, 225);
    t.face_text = RGB(0, 0, 0); t.border = RGB(173, 173, 173); t.hot = RGB(229, 241, 251);
    t.hot_border = RGB(0, 120, 215); t.pressed = RGB(204, 228, 247); t.accent = RGB(0, 120, 215);
    t.accent_text = RGB(255, 255, 255); t.disabled_text = RGB(160, 160, 160); t.selection = RGB(0, 120, 215);
    t.selection_text = RGB(255, 255, 255); t.input = RGB(255, 255, 255); t.input_text = RGB(0, 0, 0);
    rf_theme_define(&t);
    t.name = "Dark"; t.dark = 1; t.radius = 4;
    t.window = RGB(32, 32, 32); t.window_text = RGB(240, 240, 240); t.face = RGB(51, 51, 51);
    t.face_text = RGB(240, 240, 240); t.border = RGB(85, 85, 85); t.hot = RGB(69, 69, 69);
    t.hot_border = RGB(0, 120, 215); t.pressed = RGB(90, 90, 90); t.accent = RGB(0, 120, 215);
    t.accent_text = RGB(255, 255, 255); t.disabled_text = RGB(120, 120, 120); t.selection = RGB(0, 95, 184);
    t.selection_text = RGB(255, 255, 255); t.input = RGB(25, 25, 25); t.input_text = RGB(240, 240, 240);
    rf_theme_define(&t);
    t.name = "Office"; t.dark = 0; t.radius = 2;              /* Office 2016 blue */
    t.window = RGB(243, 243, 243); t.window_text = RGB(38, 38, 38); t.face = RGB(255, 255, 255);
    t.face_text = RGB(38, 38, 38); t.border = RGB(171, 171, 171); t.hot = RGB(213, 225, 242);
    t.hot_border = RGB(43, 87, 154); t.pressed = RGB(163, 189, 227); t.accent = RGB(43, 87, 154);
    t.accent_text = RGB(255, 255, 255); t.disabled_text = RGB(165, 165, 165); t.selection = RGB(43, 87, 154);
    t.selection_text = RGB(255, 255, 255); t.input = RGB(255, 255, 255); t.input_text = RGB(38, 38, 38);
    rf_theme_define(&t);
    t.name = "Metro"; t.dark = 0; t.radius = 0; t.border_width = 2;   /* flat, square */
    t.window = RGB(255, 255, 255); t.window_text = RGB(30, 30, 30); t.face = RGB(230, 230, 230);
    t.face_text = RGB(30, 30, 30); t.border = RGB(204, 204, 204); t.hot = RGB(218, 218, 218);
    t.hot_border = RGB(0, 120, 215); t.pressed = RGB(0, 120, 215); t.accent = RGB(0, 120, 215);
    t.accent_text = RGB(255, 255, 255); t.disabled_text = RGB(170, 170, 170); t.selection = RGB(0, 120, 215);
    t.selection_text = RGB(255, 255, 255); t.input = RGB(255, 255, 255); t.input_text = RGB(30, 30, 30);
    rf_theme_define(&t);
    g_theme = &g_themes[0];
}

int rf_theme_define(const rf_theme *theme) {
    rf_theme t;
    int i;
    if (!theme || !theme->name || theme->size < (int)sizeof(int)) return 0;
    memset(&t, 0, sizeof t);
    memcpy(&t, theme, (size_t)theme->size < sizeof t ? (size_t)theme->size : sizeof t);
    t.size = (int)sizeof t;
    if (!t.font_name) t.font_name = "Segoe UI";
    if (t.font_size <= 0) t.font_size = 9;
    for (i = 0; i < g_nthemes; i++)
        if (rf_ieq(g_themes[i].name, t.name)) {
            int cur = g_theme == &g_themes[i];
            g_themes[i] = t;
            if (cur) rf_theme_set(t.name);
            return 1;
        }
    if (g_nthemes >= MAX_THEMES) return 0;
    g_themes[g_nthemes++] = t;
    return 1;
}

const rf_theme *rf_theme_current(void) { rf_init_themes(); return g_theme; }

unsigned rf_theme_color(const char *key) {
    const rf_theme *t = rf_theme_current();
    static const char *const K[] = {"window", "window_text", "face", "face_text", "border", "hot", "hot_border",
                                    "pressed", "accent", "accent_text", "disabled_text", "selection",
                                    "selection_text", "input", "input_text"};
    const unsigned *v = &t->window;
    size_t i;
    for (i = 0; i < sizeof K / sizeof K[0]; i++)
        if (rf_ieq(K[i], key ? key : "")) return v[i];
    return 0;
}

typedef HRESULT(WINAPI *SetWindowTheme_t)(HWND, LPCWSTR, LPCWSTR);
typedef HRESULT(WINAPI *DwmSetAttr_t)(HWND, DWORD, LPCVOID, DWORD);
static int g_theme_touched;          /* rf_theme_set was called: standard controls get their theme set */

static void rf_win_theme(HWND h, const wchar_t *app, const wchar_t *idlist) {
    static SetWindowTheme_t fn;
    static int looked;
    if (!looked) {
        HMODULE m = LoadLibraryW(L"uxtheme.dll");
        looked = 1;
        fn = m ? (SetWindowTheme_t)(void *)GetProcAddress(m, "SetWindowTheme") : NULL;
    }
    if (fn && h) fn(h, app, idlist);
}

static void rf_theme_form(RfForm *f) {
    static DwmSetAttr_t fn;
    static int looked;
    BOOL dark;
    if (!f->hwnd || !g_theme_touched) return;
    if (!looked) {
        HMODULE m = LoadLibraryW(L"dwmapi.dll");
        looked = 1;
        fn = m ? (DwmSetAttr_t)(void *)GetProcAddress(m, "DwmSetWindowAttribute") : NULL;
    }
    dark = g_theme && g_theme->dark;
    if (fn) fn(f->hwnd, 20, &dark, sizeof dark);       /* DWMWA_USE_IMMERSIVE_DARK_MODE */
}

static void rf_theme_ctl(RfCtl *c) {
    int dark;
    if (!c->hwnd || !g_theme_touched) return;
    dark = g_theme && g_theme->dark;
    switch (c->type) {
    case T_CHECKBOX: case T_RADIO: case T_GROUPBOX:
        /* themed check boxes ignore WM_CTLCOLOR text colours: classic look in dark themes */
        if (dark) rf_win_theme(c->hwnd, L"", L"");
        else rf_win_theme(c->hwnd, NULL, NULL);
        break;
    case T_BUTTON: case T_LISTBOX: case T_TAB: case T_TRACKBAR:
        rf_win_theme(c->hwnd, dark ? L"DarkMode_Explorer" : NULL, NULL);
        break;
    case T_TEXTBOX: case T_COMBOBOX: case T_UPDOWN:
        rf_win_theme(c->hwnd, dark ? L"DarkMode_CFD" : NULL, NULL);
        if (c->buddy) rf_win_theme(c->buddy, dark ? L"DarkMode_Explorer" : NULL, NULL);
        break;
    default: break;
    }
}

int rf_theme_set(const char *name) {
    int i;
    rf_init_themes();
    for (i = 0; i < g_nthemes; i++)
        if (rf_ieq(g_themes[i].name, name ? name : "")) break;
    if (i >= g_nthemes) return 0;
    g_theme = &g_themes[i];
    g_themed = !rf_ieq(g_theme->name, "Light");
    g_theme_touched = 1;
    if (g_theme_brush) DeleteObject(g_theme_brush);
    if (g_input_brush) DeleteObject(g_input_brush);
    g_theme_brush = CreateSolidBrush(g_theme->window);
    g_input_brush = CreateSolidBrush(g_theme->input);
    for (i = 0; i < g_nforms; i++) {
        RfForm *f = &g_forms[i];
        RfCtl *c;
        if (!f->hwnd) continue;
        rf_theme_form(f);
        for (c = f->ctls; c; c = c->next) {
            rf_theme_ctl(c);
            if (c->type == T_PICTURE && rf_kv_get(c, "Image")) rf_set(f, c, "Image", rf_kv_get(c, "Image"));
        }
        RedrawWindow(f->hwnd, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN | RDW_FRAME);
    }
    return 1;
}

/* ================================================================== events by id */
static const char *const EV_NAMES[] = {
    "", "Click", "DoubleClick", "MouseDown", "MouseUp", "MouseMove", "MouseEnter", "MouseLeave", "MouseWheel",
    "KeyDown", "KeyUp", "KeyPress", "GotFocus", "LostFocus", "TextChanged", "CheckedChanged",
    "SelectedIndexChanged", "ValueChanged", "Tick", "Load", "Activated", "Deactivate", "Resize", "FormClosing",
    "FormClosed"};
static char *g_custom_ev[256];
static int g_ncustom_ev;

int rf_event_id(const char *name) {
    int i;
    if (!name || !*name) return RF_EV_NONE;
    for (i = 1; i < (int)(sizeof EV_NAMES / sizeof EV_NAMES[0]); i++)
        if (rf_ieq(EV_NAMES[i], name)) return i;
    for (i = 0; i < g_ncustom_ev; i++)
        if (rf_ieq(g_custom_ev[i], name)) return RF_EV_CUSTOM + i;
    if (g_ncustom_ev >= 256) return RF_EV_NONE;
    g_custom_ev[g_ncustom_ev] = rf_strdup(name);
    return RF_EV_CUSTOM + g_ncustom_ev++;
}

const char *rf_event_name(int id) {
    if (id > 0 && id < (int)(sizeof EV_NAMES / sizeof EV_NAMES[0])) return EV_NAMES[id];
    if (id >= RF_EV_CUSTOM && id < RF_EV_CUSTOM + g_ncustom_ev) return g_custom_ev[id - RF_EV_CUSTOM];
    return "";
}

/* ================================================================== handles */
static RfCtl *HC(rf_handle h) { return h && ((RfCtl *)(void *)h)->magic == MAGIC_CTL ? (RfCtl *)(void *)h : NULL; }
static RfForm *HF(rf_handle h) { return h && ((RfForm *)(void *)h)->magic == MAGIC_FORM ? (RfForm *)(void *)h : NULL; }

int rf_abi_version(void) { return RF_ABI_VERSION; }

rf_handle rf_find(const char *path) {
    RfCtl *c;
    RfForm *f = rf_resolve(path, &c);
    return c ? (rf_handle)c : (rf_handle)f;
}

rf_handle rf_form(rf_handle h) {
    RfCtl *c = HC(h);
    return c ? (rf_handle)c->form : HF(h) ? h : NULL;
}

const char *rf_name(rf_handle h) {
    RfCtl *c = HC(h);
    RfForm *f = HF(h);
    return c ? c->name : f ? f->name : "";
}

const char *rf_type(rf_handle h) {
    RfCtl *c = HC(h);
    if (c) return c->type == T_CUSTOM ? c->cls->name : TYPE_NAMES[c->type];
    return HF(h) ? "Form" : "";
}

void *rf_hwnd(rf_handle h) {
    RfCtl *c = HC(h);
    RfForm *f = HF(h);
    return c ? (void *)c->hwnd : f ? (void *)f->hwnd : NULL;
}

void *rf_state(rf_handle h) { RfCtl *c = HC(h); return c ? c->state : NULL; }

int rf_prop_set(rf_handle h, const char *prop, const char *value) {
    RfCtl *c = HC(h);
    RfForm *f = HF(h);
    if (!prop || (!c && !f)) return 0;
    rf_set(c ? c->form : f, c, prop, value ? value : "");
    return 1;
}

int rf_prop_set_num(rf_handle h, const char *prop, double value) { return rf_prop_set(h, prop, rad_str(value)); }

const char *rf_prop_get(rf_handle h, const char *prop) {
    RfCtl *c = HC(h);
    RfForm *f = HF(h);
    if (!prop || (!c && !f)) return "";
    return rf_get(c ? c->form : f, c, prop);
}

double rf_prop_get_num(rf_handle h, const char *prop) { return rad_num(rf_prop_get(h, prop)); }

const char *rf_invoke(rf_handle h, const char *method, const char *args) {
    RfCtl *c = HC(h);
    RfForm *f = HF(h);
    if (!method || (!c && !f)) return "";
    return rf_call(c ? c->form : f, c, method, args ? args : "");
}

rf_handle rf_create(rf_handle parent, const char *type, const char *name, int x, int y, int w, int h) {
    RfCtl *pc = HC(parent), *c;
    RfForm *f = pc ? pc->form : HF(parent);
    const rf_class *cls;
    int t;
    if (!f || !type || !name || !*name) return NULL;
    if (!f->loaded) rf_form_load(f, 0);
    if (rf_ctl_in(f, name)) return NULL;               /* names are unique in a form */
    t = rf_type_of(type, &cls);
    if (t < 0 || t == T_MENUITEM || t == T_TOOLBTN) return NULL;
    c = rf_new_ctl(f, t, name, pc && CCONT(pc) ? pc : NULL);
    if (!c) return NULL;
    c->cls = cls;
    c->pl[0] = (float)x;
    c->pl[1] = (float)y;
    c->pl[2] = (float)w;
    c->pl[3] = (float)h;
    if (!CNONVIS(c)) {
        rf_create_window(c, 0, 0);
        rf_place_ctl(c);
        rf_apply_visible(c);
        rf_acc_apply(c);
    } else if (c->type == T_CUSTOM && c->cls->create) {
        c->cls->create((rf_handle)c, &c->state);
    }
    return (rf_handle)c;
}

void rf_destroy(rf_handle h) {
    RfCtl *c = HC(h), **pp;
    RfForm *f = HF(h);
    if (f) { rf_form_close_now(f); return; }
    if (!c) return;
    f = c->form;
    for (;;) {                              /* children first */
        RfCtl *k;
        for (k = f->ctls; k && k->parent != c; k = k->next) {}
        if (!k) break;
        rf_destroy((rf_handle)k);
    }
    for (pp = &f->ctls; *pp && *pp != c; pp = &(*pp)->next) {}
    if (*pp) *pp = c->next;
    if (c->type == T_CUSTOM && c->cls->destroy) c->cls->destroy((rf_handle)c, c->state);
    if (c->timer_on && f->hwnd) KillTimer(f->hwnd, TIMER_BASE + (UINT_PTR)c->id);
    if (c->buddy) DestroyWindow(c->buddy);
    if (c->hwnd) DestroyWindow(c->hwnd);
    if (c->font) DeleteObject(c->font);
    if (c->brush) DeleteObject(c->brush);
    if (c->child_brush) DeleteObject(c->child_brush);
    if (c->image) DeleteObject(c->image);
    while (c->kv) { KV *k = c->kv; c->kv = k->next; free(k->key); free(k->val); free(k); }
    c->magic = 0;
    free(c);
}

void rf_show(rf_handle form, int modal) {
    RfForm *f = HF(rf_form(form));
    if (!f) return;
    if (modal) rad_show_modal(f->name);
    else rad_show(f->name);
}

void rf_quit(void) { rad_end(); }

void rf_raise(rf_handle h, const char *event, const char *args) {
    RfCtl *c = HC(h);
    RfForm *f = HF(h);
    /* the user changed a registered control (toggle, slider, text ...): screen readers see the new state */
    if (c && event && (rf_is(event, "CheckedChanged") || rf_is(event, "ValueChanged") || rf_is(event, "TextChanged") ||
                       rf_is(event, "SelectedIndexChanged")))
        rf_acc_apply(c);
    if (c) rf_post(c->form, c->name, event, args ? args : "", AFTER_NONE);
    else if (f) rf_post(f, f->name, event, args ? args : "", AFTER_NONE);
}

void rf_invalidate(rf_handle h) {
    HWND w = (HWND)rf_hwnd(h);
    if (w) InvalidateRect(w, NULL, FALSE);
}

void rf_set_timer(rf_handle h, int id, int ms) {
    HWND w = (HWND)rf_hwnd(h);
    if (!w) return;
    if (ms > 0) SetTimer(w, (UINT_PTR)id, (UINT)ms, NULL);
    else KillTimer(w, (UINT_PTR)id);
}

void rf_set_page(rf_handle h, int page) {
    RfCtl *c = HC(h), *k;
    if (!c) return;
    c->paged = 1;
    c->cpage = page < RF_PAGE_NONE ? RF_PAGE_ALL : page;
    for (k = c->form->ctls; k; k = k->next)
        if (k->parent == c) rf_apply_visible(k);
}

int rf_get_page(rf_handle h) { RfCtl *c = HC(h); return c && c->paged ? c->cpage : RF_PAGE_ALL; }

int rf_child_page(rf_handle h) { RfCtl *c = HC(h); return c ? c->page : 0; }

void rf_set_child_back(rf_handle h, unsigned color) {
    RfCtl *c = HC(h);
    int had;
    if (!c) return;
    had = c->has_child_back;
    if (had && color != RF_NONE && c->child_back == (COLORREF)color) return;
    if (!had && color == RF_NONE) return;
    if (c->child_brush) DeleteObject(c->child_brush);
    c->child_brush = NULL;
    c->has_child_back = color != RF_NONE;
    c->child_back = (COLORREF)color;
    if (c->hwnd) RedrawWindow(c->hwnd, NULL, NULL, RDW_INVALIDATE | RDW_ERASE | RDW_ALLCHILDREN);
}

int rf_dpi(rf_handle h) {
    RfCtl *c = HC(h);
    RfForm *f = c ? c->form : HF(h);
    return f && f->dpi > 0 ? f->dpi : 96;
}

int rf_rtl(rf_handle h) {
    RfCtl *c = HC(h);
    RfForm *f = c ? c->form : HF(h);
    return f && f->hwnd && (GetWindowLongW(f->hwnd, GWL_EXSTYLE) & WS_EX_LAYOUTRTL) ? 1 : 0;
}

const rf_theme *rf_theme_find(const char *name) {
    int i;
    rf_init_themes();
    for (i = 0; i < g_nthemes; i++)
        if (rf_ieq(g_themes[i].name, name ? name : "")) return &g_themes[i];
    return NULL;
}

/* ================================================================== owner-drawn windows */
#define RF_ANIM_TIMER 0x5246

static void rf_anim(RfCtl *c) {
    const rf_theme *t = rf_theme_current();
    if (!c->hwnd) return;
    if (t->anim_ms <= 0) {
        c->hover = c->hot;
        c->pressv = c->pressed;
    } else {
        SetTimer(c->hwnd, RF_ANIM_TIMER, 15, NULL);
    }
    InvalidateRect(c->hwnd, NULL, FALSE);
}

static double rf_toward(double v, double target, double step) {
    if (v < target) return v + step > target ? target : v + step;
    return v - step < target ? target : v - step;
}

static void rf_anim_step(RfCtl *c) {
    const rf_theme *t = rf_theme_current();
    double step = t->anim_ms > 0 ? 15.0 / t->anim_ms : 1;
    c->hover = rf_toward(c->hover, c->hot ? 1 : 0, step);
    c->pressv = rf_toward(c->pressv, c->pressed ? 1 : 0, step * 2);
    if (c->hover == (c->hot ? 1 : 0) && c->pressv == (c->pressed ? 1 : 0)) KillTimer(c->hwnd, RF_ANIM_TIMER);
    InvalidateRect(c->hwnd, NULL, FALSE);
}

static void rf_custom_paint(RfCtl *c, HDC target) {
    PAINTSTRUCT ps;
    HDC dc = target ? target : BeginPaint(c->hwnd, &ps), mem;
    RECT r;
    HBITMAP bmp, oldb;
    HGDIOBJ oldf;
    COLORREF bg;
    rf_paint p;
    const rf_theme *t = rf_theme_current();
    GetClientRect(c->hwnd, &r);
    if (r.right <= 0 || r.bottom <= 0) { if (!target) EndPaint(c->hwnd, &ps); return; }
    mem = CreateCompatibleDC(dc);
    bmp = CreateCompatibleBitmap(dc, r.right, r.bottom);
    oldb = (HBITMAP)SelectObject(mem, bmp);
    if (c->parent && c->parent->has_child_back) {
        if (!c->parent->child_brush) c->parent->child_brush = CreateSolidBrush(c->parent->child_back);
        FillRect(mem, &r, c->parent->child_brush);
    } else
        FillRect(mem, &r, rf_brush_for(c->parent ? c->parent : NULL, &bg));
    if (!c->parent) FillRect(mem, &r, c->form->has_back ? (c->form->brush ? c->form->brush :
                         (c->form->brush = CreateSolidBrush(c->form->back))) : (g_themed && g_theme_brush ?
                         g_theme_brush : GetSysColorBrush(COLOR_BTNFACE)));
    oldf = SelectObject(mem, c->font);
    SetBkMode(mem, TRANSPARENT);
    memset(&p, 0, sizeof p);
    p.size = (int)sizeof p;
    p.handle = (rf_handle)c;
    p.hdc = mem;
    p.width = r.right;
    p.height = r.bottom;
    p.dpi = c->form->dpi;
    p.theme = t;
    p.hot = c->hot;
    p.pressed = c->pressed;
    p.focused = c->focused;
    p.enabled = IsWindowEnabled(c->hwnd) != 0;
    p.hover = c->hover;
    p.press = c->pressv;
    p.font = c->font;
    p.text = rf_wtext(c->hwnd);
    p.has_back = c->has_back;
    p.has_fore = c->has_fore;
    p.back = c->has_back ? c->back : t->face;
    p.fore = c->has_fore ? c->fore : t->face_text;
    if (c->cls->paint) c->cls->paint((rf_handle)c, c->state, &p);
    BitBlt(dc, 0, 0, r.right, r.bottom, mem, 0, 0, SRCCOPY);
    SelectObject(mem, oldf);
    SelectObject(mem, oldb);
    DeleteObject(bmp);
    DeleteDC(mem);
    if (!target) EndPaint(c->hwnd, &ps);
}

static LRESULT CALLBACK rf_custom_proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    RfCtl *c = rf_ctl_of(h);
    int focusable;
    if (!c || c->type != T_CUSTOM) return DefWindowProcW(h, m, w, l);
    focusable = (c->cls->flags & RF_CLASS_FOCUSABLE) != 0;
    switch (m) {
    case WM_ERASEBKGND: return 1;
    case WM_PAINT: rf_custom_paint(c, NULL); return 0;
    case WM_PRINTCLIENT: rf_custom_paint(c, (HDC)w); return 0;
    case WM_MOUSEMOVE:
        if (!c->hot) { c->hot = 1; rf_anim(c); }
        break;
    case WM_MOUSELEAVE:
        c->hot = 0;
        rf_anim(c);
        break;
    case WM_LBUTTONDOWN: case WM_LBUTTONDBLCLK:
        c->pressed = 1;
        SetCapture(h);
        if (focusable) SetFocus(h);
        if (m == WM_LBUTTONDBLCLK) rf_post_c(c, "DoubleClick", "");
        rf_anim(c);
        return 0;
    case WM_LBUTTONUP:
        if (c->pressed) {
            POINT pt;
            RECT r;
            pt.x = GET_X_LPARAM(l);
            pt.y = GET_Y_LPARAM(l);
            c->pressed = 0;
            ReleaseCapture();
            GetClientRect(h, &r);
            if (PtInRect(&r, pt)) rf_post_c(c, "Click", "");
            else c->hot = 0;
            rf_anim(c);
        }
        return 0;
    case WM_CAPTURECHANGED:
        if (c->pressed) { c->pressed = 0; rf_anim(c); }
        break;
    case WM_KEYDOWN:
        if (focusable && w == VK_SPACE) rf_post_c(c, "Click", "");
        break;
    case WM_GETDLGCODE:
        return focusable ? DLGC_WANTCHARS : 0;
    case WM_SETFOCUS: case WM_KILLFOCUS:
        c->focused = m == WM_SETFOCUS;
        InvalidateRect(h, NULL, FALSE);
        break;
    case WM_ENABLE:
        InvalidateRect(h, NULL, FALSE);
        break;
    case WM_SETTEXT: {
        LRESULT r = DefWindowProcW(h, m, w, l);
        InvalidateRect(h, NULL, FALSE);
        return r;
    }
    case WM_SETFONT:
        InvalidateRect(h, NULL, FALSE);
        return 0;
    case WM_GETFONT:
        return (LRESULT)c->font;
    case WM_TIMER:
        if (w == RF_ANIM_TIMER) { rf_anim_step(c); return 0; }
        break;
    default: break;
    }
    return DefWindowProcW(h, m, w, l);
}

/* ================================================================== drawing helpers */
typedef int(WINAPI *GpFromHdc_t)(HDC, void **);
typedef int(WINAPI *GpDelete_t)(void *);
typedef int(WINAPI *GpSmooth_t)(void *, int);
typedef int(WINAPI *GpNewPath_t)(int, void **);
typedef int(WINAPI *GpArc_t)(void *, float, float, float, float, float, float);
typedef int(WINAPI *GpSolid_t)(DWORD, void **);
typedef int(WINAPI *GpFillPath_t)(void *, void *, void *);
typedef int(WINAPI *GpPen_t)(DWORD, float, int, void **);
typedef int(WINAPI *GpDrawPath_t)(void *, void *, void *);
typedef int(WINAPI *GpLine_t)(void *, void *, float, float, float, float);
typedef int(WINAPI *GpImgRect_t)(void *, void *, int, int, int, int);
typedef int(WINAPI *GpXform_t)(void *, float, float, int);
static struct {
    int ok;
    GpFromHdc_t from_hdc; GpDelete_t del_g, del_path, del_brush, del_pen, close_fig; GpSmooth_t smooth;
    GpNewPath_t new_path; GpArc_t arc; GpSolid_t solid; GpFillPath_t fill; GpPen_t pen; GpDrawPath_t draw;
    GpLine_t line; GpImgRect_t img; GpXform_t translate, scale;
} gd;

static int rf_gd(void) {
    static int tried;
    if (tried) return gd.ok;
    tried = 1;
    if (!rf_gdiplus()) return 0;
#define GP(f, n) do { FARPROC fp_ = GetProcAddress(g_gp, n); memcpy(&gd.f, &fp_, sizeof fp_); } while (0)
    GP(from_hdc, "GdipCreateFromHDC"); GP(del_g, "GdipDeleteGraphics"); GP(del_path, "GdipDeletePath");
    GP(del_brush, "GdipDeleteBrush"); GP(del_pen, "GdipDeletePen"); GP(close_fig, "GdipClosePathFigure");
    GP(smooth, "GdipSetSmoothingMode"); GP(new_path, "GdipCreatePath"); GP(arc, "GdipAddPathArc");
    GP(solid, "GdipCreateSolidFill"); GP(fill, "GdipFillPath"); GP(pen, "GdipCreatePen1");
    GP(draw, "GdipDrawPath"); GP(line, "GdipDrawLine"); GP(img, "GdipDrawImageRectI");
    GP(translate, "GdipTranslateWorldTransform"); GP(scale, "GdipScaleWorldTransform");
#undef GP
    gd.ok = gd.from_hdc && gd.del_g && gd.del_path && gd.del_brush && gd.del_pen && gd.close_fig && gd.smooth &&
            gd.new_path && gd.arc && gd.solid && gd.fill && gd.pen && gd.draw && gd.line && gd.img;
    return gd.ok;
}

/* GDI+ ignores the layout of a mirrored (RightToLeft) DC: mirror its drawing like GDI's */
static void rf_gp_layout(void *g, HDC dc) {
    if ((GetLayout(dc) & LAYOUT_RTL) && gd.translate && gd.scale) {
        BITMAP bm;
        HGDIOBJ b = GetCurrentObject(dc, OBJ_BITMAP);
        if (b && GetObjectW(b, sizeof bm, &bm) && bm.bmWidth > 0) {
            gd.translate(g, (float)bm.bmWidth, 0, 0);
            gd.scale(g, -1, 1, 0);
        }
    }
}

static DWORD rf_argb(unsigned c) {
    return 0xFF000000u | ((DWORD)GetRValue(c) << 16) | ((DWORD)GetGValue(c) << 8) | GetBValue(c);
}

int rf_px(const rf_paint *p, double v) { return (int)floor(v * (p && p->dpi ? p->dpi : 96) / 96.0 + 0.5); }

unsigned rf_blend(unsigned a, unsigned b, double t) {
    if (t <= 0) return a;
    if (t >= 1) return b;
    return RGB((int)(GetRValue(a) + (GetRValue(b) - GetRValue(a)) * t + 0.5),
               (int)(GetGValue(a) + (GetGValue(b) - GetGValue(a)) * t + 0.5),
               (int)(GetBValue(a) + (GetBValue(b) - GetBValue(a)) * t + 0.5));
}

void rf_draw_rect(const rf_paint *p, int x, int y, int w, int h, unsigned fill, unsigned border, int bw, int radius) {
    HDC dc;
    if (!p || !p->hdc || w <= 0 || h <= 0) return;
    dc = (HDC)p->hdc;
    if (radius > 0 && rf_gd()) {
        void *g = NULL, *path = NULL;
        float fx = (float)x, fy = (float)y, fw = (float)w, fh = (float)h, d = (float)(radius * 2), inset;
        if (gd.from_hdc(dc, &g) != 0) goto gdi;
        gd.smooth(g, 4);                                     /* anti-alias */
        rf_gp_layout(g, dc);
        inset = border != RF_NONE && bw > 0 ? bw / 2.0f : 0;
        fx += inset; fy += inset; fw -= 2 * inset + 1; fh -= 2 * inset + 1;
        if (d > fw) d = fw;
        if (d > fh) d = fh;
        gd.new_path(0, &path);
        gd.arc(path, fx, fy, d, d, 180, 90);
        gd.arc(path, fx + fw - d, fy, d, d, 270, 90);
        gd.arc(path, fx + fw - d, fy + fh - d, d, d, 0, 90);
        gd.arc(path, fx, fy + fh - d, d, d, 90, 90);
        gd.close_fig(path);
        if (fill != RF_NONE) {
            void *br = NULL;
            gd.solid(rf_argb(fill), &br);
            gd.fill(g, br, path);
            gd.del_brush(br);
        }
        if (border != RF_NONE && bw > 0) {
            void *pen = NULL;
            gd.pen(rf_argb(border), (float)bw, 2, &pen);        /* UnitPixel */
            gd.draw(g, pen, path);
            gd.del_pen(pen);
        }
        gd.del_path(path);
        gd.del_g(g);
        return;
    }
gdi:
    {
        RECT r;
        r.left = x; r.top = y; r.right = x + w; r.bottom = y + h;
        if (fill != RF_NONE) {
            HBRUSH br = CreateSolidBrush(fill);
            FillRect(dc, &r, br);
            DeleteObject(br);
        }
        if (border != RF_NONE && bw > 0) {
            HPEN pen = CreatePen(PS_INSIDEFRAME, bw, border), op = (HPEN)SelectObject(dc, pen);
            HGDIOBJ ob = SelectObject(dc, GetStockObject(NULL_BRUSH));
            if (radius > 0) RoundRect(dc, x, y, x + w, y + h, radius * 2, radius * 2);
            else Rectangle(dc, x, y, x + w, y + h);
            SelectObject(dc, ob);
            SelectObject(dc, op);
            DeleteObject(pen);
        }
    }
}

void rf_draw_line(const rf_paint *p, int x1, int y1, int x2, int y2, unsigned color, int width) {
    HDC dc;
    if (!p || !p->hdc) return;
    dc = (HDC)p->hdc;
    if (rf_gd()) {
        void *g = NULL, *pen = NULL;
        if (gd.from_hdc(dc, &g) == 0) {
            gd.smooth(g, 4);
            rf_gp_layout(g, dc);
            gd.pen(rf_argb(color), (float)(width > 0 ? width : 1), 2, &pen);
            gd.line(g, pen, (float)x1, (float)y1, (float)x2, (float)y2);
            gd.del_pen(pen);
            gd.del_g(g);
            return;
        }
    }
    {
        HPEN pen = CreatePen(PS_SOLID, width > 0 ? width : 1, color), op = (HPEN)SelectObject(dc, pen);
        MoveToEx(dc, x1, y1, NULL);
        LineTo(dc, x2, y2);
        SelectObject(dc, op);
        DeleteObject(pen);
    }
}

void rf_draw_text(const rf_paint *p, const char *text, int x, int y, int w, int h, unsigned color, int align) {
    RECT r;
    UINT fl = DT_NOPREFIX;
    wchar_t *t;
    if (!p || !p->hdc || !text) return;
    t = rf_wide(text);
    if (!t) return;
    r.left = x; r.top = y; r.right = x + w; r.bottom = y + h;
    fl |= (align & 3) == RF_ALIGN_CENTER ? DT_CENTER : (align & 3) == RF_ALIGN_RIGHT ? DT_RIGHT : DT_LEFT;
    if (align & RF_ALIGN_WRAP) fl |= DT_WORDBREAK;
    else fl |= DT_SINGLELINE | ((align & RF_ALIGN_VCENTER) ? DT_VCENTER : (align & RF_ALIGN_BOTTOM) ? DT_BOTTOM : 0);
    if (align & RF_ALIGN_ELLIPSIS) fl |= DT_END_ELLIPSIS;
    if (rf_has_rtl(t)) fl |= DT_RTLREADING;
    SetBkMode((HDC)p->hdc, TRANSPARENT);
    SetTextColor((HDC)p->hdc, color);
    DrawTextW((HDC)p->hdc, t, -1, &r, fl);
    free(t);
}

void rf_draw_image(const rf_paint *p, const char *path, int x, int y, int w, int h) {
    void *img, *g = NULL;
    if (!p || !p->hdc || !rf_gd() || !(img = rf_gp_image(path))) return;
    if (gd.from_hdc((HDC)p->hdc, &g) == 0) {
        gd.smooth(g, 4);
        rf_gp_layout(g, (HDC)p->hdc);
        gd.img(g, img, x, y, w, h);
        gd.del_g(g);
    }
    gp_dispose(img);
}

/* ================================================================== animations, visual states, layout variants */
#include "radforms_motion.inc"
