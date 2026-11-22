/* RAD Modern input controls: RmTextBox (watermark, clear button, icon, validation border, password,
 * multi-line), RmComboBox (themed drop-down list with images and watermark, editable or list-only),
 * RmSlider (track bar with value tip).
 * The text boxes host a native EDIT inside an owner-drawn frame (IME, clipboard, undo, RTL from Windows).
 *
 * RF_CLASSES: RmTextBox RmComboBox RmSlider
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <windowsx.h>
#include <commctrl.h>
#include <math.h>

#ifndef EM_SETCUEBANNER
#define EM_SETCUEBANNER 0x1501
#endif

/* ------------------------------------------------------------------ shared: inner EDIT */
typedef struct {
    rf_handle h;
    HWND edit;
    HBRUSH brush;
    unsigned brush_color;
    int multiline, readonly, maxlen;
    wchar_t pwchar;
} Inner;

static unsigned input_back(const rf_theme *t, rf_handle h) {
    const char *bc = rf_prop_get(h, "BackColor");
    unsigned c;
    if (bc && *bc && rm_color(bc, &c)) return c;
    return t->input;
}

static LRESULT CALLBACK edit_sub(HWND e, UINT m, WPARAM w, LPARAM l, UINT_PTR id, DWORD_PTR ref) {
    Inner *in = (Inner *)ref;
    (void)id;
    switch (m) {
    case WM_CHAR: {
        char args[96];
        wchar_t ch[2];
        char *u;
        if (w < 32 && w != 13 && w != 8 && w != 27) break;
        ch[0] = (wchar_t)w;
        ch[1] = 0;
        u = rm_utf8(ch);
        if (w == ' ') snprintf(args, sizeof args, "0 0 0 space");
        else snprintf(args, sizeof args, "0 0 0 %s %s", w == 13 ? "Return" : w == 8 ? "BackSpace" : w == 27 ? "Escape" :
                      (u ? u : ""), w < 32 ? "" : (u ? u : ""));
        free(u);
        rf_raise(in->h, "KeyPress", args);
        if (w == 13 && !in->multiline) return 0;        /* no beep */
        break;
    }
    case WM_SETFOCUS:
        rf_raise(in->h, "GotFocus", "");
        rf_invalidate(in->h);
        break;
    case WM_KILLFOCUS:
        rf_raise(in->h, "LostFocus", "");
        rf_invalidate(in->h);
        break;
    case WM_MOUSEMOVE: case WM_MOUSELEAVE:
        rf_invalidate(in->h);
        break;
    case WM_GETDLGCODE: {
        LRESULT r = DefSubclassProc(e, m, w, l);
        if (in->multiline) r |= DLGC_WANTALLKEYS;
        return r & ~(LRESULT)DLGC_HASSETSEL;
    }
    case WM_NCDESTROY:
        RemoveWindowSubclass(e, edit_sub, 1);
        break;
    default: break;
    }
    return DefSubclassProc(e, m, w, l);
}

static void inner_make(Inner *in, HWND parent, const char *keep_text) {
    DWORD st = WS_CHILD | WS_VISIBLE | WS_TABSTOP | ES_AUTOHSCROLL | ES_NOHIDESEL;
    wchar_t *txt = rm_wide(keep_text ? keep_text : "");
    HFONT f = (HFONT)SendMessageW(parent, WM_GETFONT, 0, 0);
    if (in->multiline) st = WS_CHILD | WS_VISIBLE | WS_TABSTOP | ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN | WS_VSCROLL |
                            ES_NOHIDESEL;
    if (in->edit) DestroyWindow(in->edit);
    in->edit = CreateWindowExW(0, L"EDIT", txt ? txt : L"", st, 0, 0, 10, 10, parent, (HMENU)(INT_PTR)1, GetModuleHandleW(NULL),
                               NULL);
    free(txt);
    if (!in->edit) return;
    SetWindowSubclass(in->edit, edit_sub, 1, (DWORD_PTR)in);
    if (f) SendMessageW(in->edit, WM_SETFONT, (WPARAM)f, 0);
    if (in->readonly) SendMessageW(in->edit, EM_SETREADONLY, TRUE, 0);
    if (in->maxlen > 0) SendMessageW(in->edit, EM_LIMITTEXT, (WPARAM)in->maxlen, 0);
    if (in->pwchar && !in->multiline) SendMessageW(in->edit, EM_SETPASSWORDCHAR, in->pwchar, 0);
    {   /* a dark theme gets dark scroll bars */
        typedef HRESULT(WINAPI * swt_t)(HWND, LPCWSTR, LPCWSTR);
        HMODULE m = LoadLibraryW(L"uxtheme.dll");
        swt_t fn = m ? (swt_t)(void *)GetProcAddress(m, "SetWindowTheme") : NULL;
        if (fn && rf_theme_current()->dark) fn(in->edit, L"DarkMode_Explorer", NULL);
    }
}

static const char *inner_text(Inner *in) {
    int n;
    wchar_t *w;
    char *u;
    if (!in->edit) return "";
    n = GetWindowTextLengthW(in->edit);
    w = (wchar_t *)malloc(sizeof(wchar_t) * (n + 1));
    if (!w) return "";
    GetWindowTextW(in->edit, w, n + 1);
    u = rm_utf8(w);
    free(w);
    {
        static char *keep[8];
        static int k;
        k = (k + 1) % 8;
        free(keep[k]);
        keep[k] = u;
        return u ? u : "";
    }
}

static void inner_set_text(Inner *in, const char *v, int crlf) {
    wchar_t *w;
    if (!in->edit) return;
    if (crlf && v && strchr(v, '\n')) {
        rm_sb b = {0, 0, 0};
        const char *p;
        rm_sb_add(&b, "");
        for (p = v; *p; p++) {
            if (*p == '\n' && (p == v || p[-1] != '\r')) rm_sb_addc(&b, '\r');
            rm_sb_addc(&b, *p);
        }
        w = rm_wide(b.s);
        free(b.s);
    } else {
        w = rm_wide(v);
    }
    SetWindowTextW(in->edit, w ? w : L"");
    free(w);
}

static HBRUSH inner_brush(Inner *in, unsigned color) {
    if (!in->brush || in->brush_color != color) {
        if (in->brush) DeleteObject(in->brush);
        in->brush = CreateSolidBrush(color);
        in->brush_color = color;
    }
    return in->brush;
}

/* ================================================================== RmTextBox */
typedef struct {
    rm_look look;
    Inner in;
    char *watermark, *icon, *error;
    int show_clear, hot_clear, hot_icon;
} RmTextBox;

static void tb_layout(rf_handle h, RmTextBox *t) {
    HWND hw = (HWND)rf_hwnd(h);
    RECT r;
    int pad = rm_px(h, 8), isz = rm_px(h, 16), left, right, eh, top;
    HDC dc;
    TEXTMETRICW tm;
    HGDIOBJ of;
    if (!hw || !t->in.edit) return;
    GetClientRect(hw, &r);
    left = pad + (rm_has_icon(t->icon) ? isz + rm_px(h, 6) : 0);
    right = pad + (t->show_clear ? isz + rm_px(h, 4) : 0) + (*t->error ? isz + rm_px(h, 4) : 0);
    dc = GetDC(t->in.edit);
    of = SelectObject(dc, (HGDIOBJ)SendMessageW(t->in.edit, WM_GETFONT, 0, 0));
    GetTextMetricsW(dc, &tm);
    SelectObject(dc, of);
    ReleaseDC(t->in.edit, dc);
    if (t->in.multiline) {
        top = rm_px(h, 5);
        eh = r.bottom - 2 * top;
    } else {
        eh = tm.tmHeight + 2;
        top = (r.bottom - eh) / 2;
    }
    MoveWindow(t->in.edit, left, top, r.right - left - right > 4 ? r.right - left - right : 4, eh > 4 ? eh : 4, TRUE);
}

static void tb_cue(RmTextBox *t) {
    wchar_t *w = rm_wide(t->watermark);
    if (t->in.edit && w) SendMessageW(t->in.edit, EM_SETCUEBANNER, TRUE, (LPARAM)w);
    free(w);
}

static int RF_CALL tb_create(rf_handle h, void **state) {
    RmTextBox *t = (RmTextBox *)calloc(1, sizeof *t);
    if (!t) return 0;
    t->in.h = h;
    t->watermark = rm_strdup("");
    t->icon = rm_strdup("");
    t->error = rm_strdup("");
    inner_make(&t->in, (HWND)rf_hwnd(h), "");
    *state = t;
    tb_layout(h, t);
    return 1;
}

static void RF_CALL tb_destroy(rf_handle h, void *state) {
    RmTextBox *t = (RmTextBox *)state;
    (void)h;
    if (!t) return;
    if (t->in.brush) DeleteObject(t->in.brush);
    free(t->watermark); free(t->icon); free(t->error);
    free(t);
}

static int RF_CALL tb_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmTextBox *t = (RmTextBox *)state;
    if (rm_look_set(&t->look, prop, v)) return 1;
    if (rm_ieq(prop, "Text")) { inner_set_text(&t->in, v, t->in.multiline); return 1; }
    if (rm_ieq(prop, "Watermark") || rm_ieq(prop, "PlaceholderText")) { rm_setstr(&t->watermark, v); tb_cue(t); return 1; }
    if (rm_ieq(prop, "Icon") || rm_ieq(prop, "Image")) { rm_setstr(&t->icon, v); tb_layout(h, t); return 1; }
    if (rm_ieq(prop, "ErrorText")) { rm_setstr(&t->error, v); tb_layout(h, t); return 1; }
    if (rm_ieq(prop, "ShowClear")) { t->show_clear = rm_bool(v); tb_layout(h, t); return 1; }
    if (rm_ieq(prop, "ReadOnly") || rm_ieq(prop, "Locked")) {
        t->in.readonly = rm_bool(v);
        if (t->in.edit) SendMessageW(t->in.edit, EM_SETREADONLY, (WPARAM)t->in.readonly, 0);
        return 1;
    }
    if (rm_ieq(prop, "MaxLength")) {
        t->in.maxlen = rm_int(v);
        if (t->in.edit) SendMessageW(t->in.edit, EM_LIMITTEXT, (WPARAM)(t->in.maxlen > 0 ? t->in.maxlen : 0), 0);
        return 1;
    }
    if (rm_ieq(prop, "PasswordChar")) {
        wchar_t *w = rm_wide(v);
        t->in.pwchar = w ? w[0] : 0;
        free(w);
        if (t->in.edit && !t->in.multiline) {
            SendMessageW(t->in.edit, EM_SETPASSWORDCHAR, t->in.pwchar, 0);
            InvalidateRect(t->in.edit, NULL, TRUE);
        }
        return 1;
    }
    if (rm_ieq(prop, "MultiLine") || rm_ieq(prop, "Multiline")) {
        int ml = rm_bool(v);
        if (ml != t->in.multiline) {
            char *keep = rm_strdup(inner_text(&t->in));
            t->in.multiline = ml;
            inner_make(&t->in, (HWND)rf_hwnd(h), keep);
            free(keep);
            tb_cue(t);
            tb_layout(h, t);
        }
        return 1;
    }
    if (rm_ieq(prop, "SelStart") || rm_ieq(prop, "SelectionStart")) {
        int s = rm_int(v);
        if (t->in.edit) SendMessageW(t->in.edit, EM_SETSEL, (WPARAM)s, (LPARAM)s);
        return 1;
    }
    return 0;
}

static const char *RF_CALL tb_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmTextBox *t = (RmTextBox *)state;
    const char *r = rm_look_get(&t->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Text")) return inner_text(&t->in);
    if (rm_ieq(prop, "Watermark") || rm_ieq(prop, "PlaceholderText")) return t->watermark;
    if (rm_ieq(prop, "Icon") || rm_ieq(prop, "Image")) return t->icon;
    if (rm_ieq(prop, "ErrorText")) return t->error;
    if (rm_ieq(prop, "ShowClear")) return rm_tf(t->show_clear);
    if (rm_ieq(prop, "ReadOnly") || rm_ieq(prop, "Locked")) return rm_tf(t->in.readonly);
    if (rm_ieq(prop, "MultiLine") || rm_ieq(prop, "Multiline")) return rm_tf(t->in.multiline);
    if (rm_ieq(prop, "MaxLength")) return rad_str(t->in.maxlen);
    if (rm_ieq(prop, "PasswordChar")) {
        static char pc[8];
        wchar_t w[2];
        char *u;
        w[0] = t->in.pwchar;
        w[1] = 0;
        u = rm_utf8(w);
        snprintf(pc, sizeof pc, "%s", u ? u : "");
        free(u);
        return pc;
    }
    if (rm_ieq(prop, "Focused")) return rm_tf(GetFocus() == t->in.edit);
    if (rm_ieq(prop, "SelStart") || rm_ieq(prop, "SelectionStart")) {
        DWORD s = 0;
        if (t->in.edit) SendMessageW(t->in.edit, EM_GETSEL, (WPARAM)&s, 0);
        return rad_str(s);
    }
    return NULL;
}

static const char *RF_CALL tb_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmTextBox *t = (RmTextBox *)state;
    (void)h;
    if (rm_ieq(m, "Clear")) { inner_set_text(&t->in, "", 0); return ""; }
    if (rm_ieq(m, "SelectAll")) { if (t->in.edit) SendMessageW(t->in.edit, EM_SETSEL, 0, -1); return ""; }
    if (rm_ieq(m, "AppendText")) {
        wchar_t *w = rm_wide(rm_arg(args, 0));
        if (t->in.edit && w) {
            int n = GetWindowTextLengthW(t->in.edit);
            SendMessageW(t->in.edit, EM_SETSEL, (WPARAM)n, (LPARAM)n);
            SendMessageW(t->in.edit, EM_REPLACESEL, FALSE, (LPARAM)w);
        }
        free(w);
        return "";
    }
    if (rm_ieq(m, "SetFocus") || rm_ieq(m, "Focus")) { if (t->in.edit) SetFocus(t->in.edit); return ""; }
    return NULL;
}

static void tb_zones(rf_handle h, RmTextBox *t, RECT *icon, RECT *clear) {
    HWND hw = (HWND)rf_hwnd(h);
    RECT r;
    int pad = rm_px(h, 8), isz = rm_px(h, 16), cy;
    GetClientRect(hw, &r);
    cy = t->in.multiline ? rm_px(h, 6) : (r.bottom - isz) / 2;
    SetRect(icon, pad, cy, pad + isz, cy + isz);
    SetRect(clear, r.right - pad - isz, cy, r.right - pad, cy + isz);
}

static int RF_CALL tb_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmTextBox *t = (RmTextBox *)state;
    RECT ri, rc;
    POINT pt;
    if (!t) return 0;
    switch (msg) {
    case WM_SIZE: tb_layout(h, t); break;
    case WM_SETFONT:
        if (t->in.edit) SendMessageW(t->in.edit, WM_SETFONT, (WPARAM)w, (LPARAM)l);
        tb_layout(h, t);
        break;
    case WM_SETFOCUS:
        if (t->in.edit) SetFocus(t->in.edit);
        *res = 0;
        return 1;
    case WM_COMMAND:
        if ((HWND)l == t->in.edit) {
            if (HIWORD(w) == EN_CHANGE) {
                rf_raise(h, "TextChanged", "");
                if (t->show_clear) rf_invalidate(h);
            }
            *res = 0;
            return 1;
        }
        break;
    case WM_CTLCOLOREDIT: case WM_CTLCOLORSTATIC: {
        const rf_theme *th = rm_look_theme(&t->look, NULL);
        unsigned back = input_back(th, h), fore = th->input_text;
        const char *fc = rf_prop_get(h, "ForeColor");
        unsigned c;
        if (fc && *fc && rm_color(fc, &c)) fore = c;
        if (!IsWindowEnabled((HWND)rf_hwnd(h))) fore = th->disabled_text;
        SetTextColor((HDC)w, fore);
        SetBkColor((HDC)w, back);
        *res = (intptr_t)inner_brush(&t->in, back);
        return 1;
    }
    case WM_LBUTTONDOWN:
        tb_zones(h, t, &ri, &rc);
        pt.x = GET_X_LPARAM(l);
        pt.y = GET_Y_LPARAM(l);
        if (t->show_clear && PtInRect(&rc, pt) && GetWindowTextLengthW(t->in.edit) > 0) {
            inner_set_text(&t->in, "", 0);
            SetFocus(t->in.edit);
            *res = 0;
            return 1;
        }
        if (rm_has_icon(t->icon) && PtInRect(&ri, pt)) rf_raise(h, "IconClick", "");
        if (t->in.edit) SetFocus(t->in.edit);
        *res = 0;
        return 1;
    case WM_MOUSEMOVE:
        tb_zones(h, t, &ri, &rc);
        pt.x = GET_X_LPARAM(l);
        pt.y = GET_Y_LPARAM(l);
        if (t->hot_clear != PtInRect(&rc, pt)) { t->hot_clear = !t->hot_clear; rf_invalidate(h); }
        break;
    case WM_MOUSELEAVE:
        if (t->hot_clear) { t->hot_clear = 0; rf_invalidate(h); }
        break;
    case WM_ENABLE:
        if (t->in.edit) EnableWindow(t->in.edit, (BOOL)w);
        break;
    default: break;
    }
    return 0;
}

static void RF_CALL tb_paint(rf_handle h, void *state, const rf_paint *p) {
    RmTextBox *t = (RmTextBox *)state;
    const rf_theme *th = rm_look_theme(&t->look, p);
    unsigned accent = rm_look_accent(&t->look, th), back = input_back(th, h), border;
    int focused = t->in.edit && GetFocus() == t->in.edit, isz = rf_px(p, 16), pad = rf_px(p, 8);
    int cy = t->in.multiline ? rf_px(p, 6) : (p->height - isz) / 2, radius = rf_px(p, th->radius + 1);
    int has_err = *t->error != 0;
    border = has_err ? RGB(198, 40, 40) : focused ? accent : rf_blend(th->border, th->hot_border, p->hover * 0.6);
    if (!p->enabled) border = rf_blend(th->border, th->window, 0.4);
    rf_draw_rect(p, 0, 0, p->width, p->height, back, border, rf_px(p, 1), radius);
    if (focused && !has_err && rm_ieq(th->name, "Metro") == 0)       /* accent underline */
        rf_draw_rect(p, radius / 2, p->height - rf_px(p, 2), p->width - radius, rf_px(p, 2), accent, RF_NONE, 0, 0);
    if (rm_has_icon(t->icon)) rm_icon(p, t->icon, pad, cy, isz, isz, rf_blend(th->input_text, back, 0.35));
    {
        int x = p->width - pad - isz;
        if (t->show_clear && t->in.edit && GetWindowTextLengthW(t->in.edit) > 0) {
            if (t->hot_clear) rm_ellipse(p, x - 2, cy - 2, isz + 4, isz + 4, rf_blend(back, th->input_text, 0.12), RF_NONE, 0);
            rm_cross(p, x + isz / 2.0, cy + isz / 2.0, isz * 0.45, rf_blend(th->input_text, back, 0.3), rf_px(p, 1.4));
        }
        if (t->show_clear) x -= isz + rf_px(p, 4);
        if (has_err) rm_icon(p, "error", x, cy, isz, isz, RGB(198, 40, 40));
    }
}

/* ================================================================== RmComboBox */
typedef struct {
    rm_look look;
    Inner in;                       /* edit of the DropDown style */
    rm_item *items;
    int n, sel, editable, open, hot_row, top_row;
    char *src, *watermark, *text;
} RmCombo;

static void cb_layout(rf_handle h, RmCombo *c) {
    HWND hw = (HWND)rf_hwnd(h);
    RECT r;
    int pad = rm_px(h, 8), aw = rm_px(h, 26), eh;
    HDC dc;
    TEXTMETRICW tm;
    HGDIOBJ of;
    if (!hw || !c->in.edit) return;
    GetClientRect(hw, &r);
    dc = GetDC(c->in.edit);
    of = SelectObject(dc, (HGDIOBJ)SendMessageW(c->in.edit, WM_GETFONT, 0, 0));
    GetTextMetricsW(dc, &tm);
    SelectObject(dc, of);
    ReleaseDC(c->in.edit, dc);
    eh = tm.tmHeight + 2;
    MoveWindow(c->in.edit, pad, (r.bottom - eh) / 2, r.right - pad - aw > 4 ? r.right - pad - aw : 4, eh, TRUE);
}

static int RF_CALL cb_create(rf_handle h, void **state) {
    RmCombo *c = (RmCombo *)calloc(1, sizeof *c);
    (void)h;
    if (!c) return 0;
    c->in.h = h;
    c->sel = -1;
    c->hot_row = -1;
    c->src = rm_strdup("");
    c->watermark = rm_strdup("");
    c->text = rm_strdup("");
    *state = c;
    return 1;
}

static void RF_CALL cb_destroy(rf_handle h, void *state) {
    RmCombo *c = (RmCombo *)state;
    (void)h;
    if (!c) return;
    rm_items_free(c->items, c->n);
    if (c->in.brush) DeleteObject(c->in.brush);
    free(c->src); free(c->watermark); free(c->text);
    free(c);
}

static const char *cb_textof(RmCombo *c) {
    if (c->editable) return inner_text(&c->in);
    return c->sel >= 0 && c->sel < c->n ? c->items[c->sel].text : "";
}

static void cb_select(rf_handle h, RmCombo *c, int i, int notify) {
    if (i < -1 || i >= c->n) i = -1;
    if (i == c->sel) return;
    c->sel = i;
    if (c->editable && i >= 0) inner_set_text(&c->in, c->items[i].text, 0);
    rf_invalidate(h);
    if (notify) {
        rf_raise(h, "SelectedIndexChanged", "");
        if (!c->editable) rf_raise(h, "TextChanged", "");
    }
}

static void cb_items_changed(RmCombo *c) {
    rm_sb b = {0, 0, 0};
    int i;
    rm_sb_add(&b, "");
    for (i = 0; i < c->n; i++) {
        if (i) rm_sb_addc(&b, ';');
        rm_sb_add(&b, c->items[i].text);
    }
    free(c->src);
    c->src = b.s ? b.s : rm_strdup("");
}

static int RF_CALL cb_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmCombo *c = (RmCombo *)state;
    if (rm_look_set(&c->look, prop, v)) return 1;
    if (rm_ieq(prop, "Items") || rm_ieq(prop, "List")) {
        rm_setstr(&c->src, v);
        rm_items_free(c->items, c->n);
        c->items = rm_items_parse(v, &c->n);
        if (c->sel >= c->n) c->sel = -1;
        return 1;
    }
    if (rm_ieq(prop, "SelectedIndex") || rm_ieq(prop, "ListIndex")) { cb_select(h, c, rm_int(v), 1); return 1; }
    if (rm_ieq(prop, "Watermark")) {
        wchar_t *w;
        rm_setstr(&c->watermark, v);
        w = rm_wide(v);
        if (c->in.edit && w) SendMessageW(c->in.edit, EM_SETCUEBANNER, TRUE, (LPARAM)w);
        free(w);
        return 1;
    }
    if (rm_ieq(prop, "DropDownStyle")) {
        int ed = rm_ieq(v, "DropDown") || rm_ieq(v, "Simple") || rm_ieq(v, "0") || rm_ieq(v, "1");
        if (ed != c->editable) {
            c->editable = ed;
            if (ed) {
                wchar_t *w = rm_wide(c->watermark);
                inner_make(&c->in, (HWND)rf_hwnd(h), cb_textof(c));
                if (c->in.edit && w) SendMessageW(c->in.edit, EM_SETCUEBANNER, TRUE, (LPARAM)w);
                free(w);
                cb_layout(h, c);
            } else if (c->in.edit) {
                DestroyWindow(c->in.edit);
                c->in.edit = NULL;
            }
        }
        return 1;
    }
    if (rm_ieq(prop, "Text")) {
        int i;
        if (c->editable) { inner_set_text(&c->in, v, 0); return 1; }
        for (i = 0; i < c->n; i++)
            if (rm_ieq(c->items[i].text, v)) { cb_select(h, c, i, 1); return 1; }
        return 1;
    }
    return 0;
}

static const char *RF_CALL cb_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmCombo *c = (RmCombo *)state;
    const char *r = rm_look_get(&c->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Items") || rm_ieq(prop, "List")) return c->src;
    if (rm_ieq(prop, "SelectedIndex") || rm_ieq(prop, "ListIndex")) return rad_str(c->sel);
    if (rm_ieq(prop, "SelectedItem") || rm_ieq(prop, "Text")) return cb_textof(c);
    if (rm_ieq(prop, "ListCount") || rm_ieq(prop, "Count")) return rad_str(c->n);
    if (rm_ieq(prop, "Watermark")) return c->watermark;
    if (rm_ieq(prop, "DropDownStyle")) return c->editable ? "DropDown" : "DropDownList";
    if (rm_ieq(prop, "DroppedDown")) return rm_tf(c->open);
    return NULL;
}

/* ---- the drop-down list */
typedef struct { RmCombo *c; rf_handle h; int row_h, rows; } CbPop;

static void cbpop_paint(rm_popup *pp, const rf_paint *p) {
    CbPop *u = (CbPop *)pp->user;
    RmCombo *c = u->c;
    const rf_theme *t = pp->theme;
    unsigned accent = rm_look_accent(&c->look, t);
    int i, pad = rf_px(p, 8), isz = rf_px(p, 16);
    for (i = 0; i < u->rows && c->top_row + i < c->n; i++) {
        int k = c->top_row + i, y = i * u->row_h + 1;
        rm_item *it = &c->items[k];
        unsigned fg = t->input_text;
        if (rm_ieq(it->text, "-")) {
            rf_draw_line(p, pad, y + u->row_h / 2, p->width - pad, y + u->row_h / 2, t->border, 1);
            continue;
        }
        if (k == c->hot_row) { rf_draw_rect(p, 2, y, p->width - 4, u->row_h, t->selection, RF_NONE, 0, rf_px(p, 3)); fg = t->selection_text; }
        else if (k == c->sel) rf_draw_rect(p, 2, y, p->width - 4, u->row_h, rf_blend(t->input, accent, 0.12), RF_NONE, 0, rf_px(p, 3));
        if (k == c->sel && k != c->hot_row) rf_draw_rect(p, 2, y + u->row_h / 4, rf_px(p, 3), u->row_h / 2, accent, RF_NONE, 0, 1);
        if (rm_has_icon(it->image)) {
            rm_icon(p, it->image, pad, y + (u->row_h - isz) / 2, isz, isz, fg);
            rf_draw_text(p, it->text, pad + isz + rf_px(p, 6), y, p->width - 2 * pad - isz, u->row_h, fg,
                         RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        } else {
            rf_draw_text(p, it->text, pad, y, p->width - 2 * pad, u->row_h, fg, RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        }
    }
    if (c->n > u->rows) {           /* scroll indicator */
        int track = p->height - 4, th = track * u->rows / c->n, ty = 2 + (track - th) * c->top_row / (c->n - u->rows);
        rf_draw_rect(p, p->width - rf_px(p, 5), ty, rf_px(p, 3), th, rf_blend(t->input, t->input_text, 0.3), RF_NONE, 0, 1);
    }
}

static int cbpop_mouse(rm_popup *pp, unsigned msg, int x, int y) {
    CbPop *u = (CbPop *)pp->user;
    RmCombo *c = u->c;
    (void)x;
    if (msg == WM_MOUSEWHEEL) {
        int t = c->top_row - (y > 0 ? 1 : -1) * 3;
        if (t > c->n - u->rows) t = c->n - u->rows;
        if (t < 0) t = 0;
        c->top_row = t;
        rm_popup_redraw(pp);
        return 0;
    }
    {
        int row = c->top_row + (y - 1) / u->row_h;
        if (row < 0 || row >= c->n || rm_ieq(c->items[row].text, "-") || !c->items[row].enabled) row = -1;
        if (row != c->hot_row) { c->hot_row = row; rm_popup_redraw(pp); }
        if (msg == WM_LBUTTONUP && row >= 0) { pp->result = row; return 1; }
    }
    return 0;
}

static int cbpop_key(rm_popup *pp, unsigned vk) {
    CbPop *u = (CbPop *)pp->user;
    RmCombo *c = u->c;
    int r = c->hot_row < 0 ? c->sel : c->hot_row;
    if (vk == VK_RETURN || vk == VK_SPACE) { pp->result = r; return 1; }
    if (vk == VK_DOWN) r++;
    else if (vk == VK_UP) r--;
    else if (vk == VK_HOME) r = 0;
    else if (vk == VK_END) r = c->n - 1;
    else if (vk == VK_NEXT) r += u->rows;
    else if (vk == VK_PRIOR) r -= u->rows;
    else return 0;
    if (r < 0) r = 0;
    if (r >= c->n) r = c->n - 1;
    c->hot_row = r;
    if (r < c->top_row) c->top_row = r;
    if (r >= c->top_row + u->rows) c->top_row = r - u->rows + 1;
    rm_popup_redraw(pp);
    return 0;
}

static void cb_dropdown(rf_handle h, RmCombo *c) {
    rm_popup pp;
    CbPop u;
    HWND hw = (HWND)rf_hwnd(h);
    RECT r;
    int x, y, w, ht, res;
    if (!hw || c->open || c->n == 0) return;
    memset(&pp, 0, sizeof pp);
    u.c = c;
    u.h = h;
    u.row_h = rm_px(h, 26);
    u.rows = c->n < 8 ? c->n : 8;
    GetWindowRect(hw, &r);
    w = r.right - r.left;
    ht = u.rows * u.row_h + 2;
    rm_popup_place(h, w, ht, &x, &y);
    c->hot_row = c->sel;
    c->top_row = c->sel >= u.rows ? c->sel - u.rows + 1 : 0;
    pp.owner = h;
    pp.theme = rm_look_theme(&c->look, NULL);
    pp.user = &u;
    pp.paint = cbpop_paint;
    pp.mouse = cbpop_mouse;
    pp.key = cbpop_key;
    c->open = 1;
    rf_invalidate(h);
    res = rm_popup_run(&pp, x, y, w, ht);
    c->open = 0;
    c->hot_row = -1;
    rf_invalidate(h);
    if (res >= 0) cb_select(h, c, res, 1);
}

static const char *RF_CALL cb_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmCombo *c = (RmCombo *)state;
    if (rm_ieq(m, "AddItem") || rm_ieq(m, "Add")) {
        rm_item *ni = (rm_item *)realloc(c->items, sizeof(rm_item) * (c->n + 1));
        int cnt = 0;
        rm_item *one;
        if (!ni) return "";
        c->items = ni;
        one = rm_items_parse(rm_arg(args, 0), &cnt);
        if (one && cnt) { c->items[c->n++] = one[0]; free(one); }
        else { rm_items_free(one, cnt); }
        cb_items_changed(c);
        rf_invalidate(h);
        return rad_str(c->n - 1);
    }
    if (rm_ieq(m, "RemoveItem") || rm_ieq(m, "RemoveAt")) {
        int i = rm_int(rm_arg(args, 0));
        if (i >= 0 && i < c->n) {
            rm_item_clear(&c->items[i]);
            memmove(c->items + i, c->items + i + 1, sizeof(rm_item) * (c->n - i - 1));
            c->n--;
            if (c->sel == i) cb_select(h, c, -1, 1);
            else if (c->sel > i) c->sel--;
            cb_items_changed(c);
            rf_invalidate(h);
        }
        return "";
    }
    if (rm_ieq(m, "Clear")) {
        rm_items_free(c->items, c->n);
        c->items = NULL;
        c->n = 0;
        cb_select(h, c, -1, 1);
        cb_items_changed(c);
        return "";
    }
    if (rm_ieq(m, "List") || rm_ieq(m, "Item")) {
        int i = rm_int(rm_arg(args, 0));
        return i >= 0 && i < c->n ? c->items[i].text : "";
    }
    if (rm_ieq(m, "IndexOf") || rm_ieq(m, "FindString")) {
        int i;
        for (i = 0; i < c->n; i++)
            if (rm_ieq(c->items[i].text, rm_arg(args, 0))) return rad_str(i);
        return "-1";
    }
    if (rm_ieq(m, "ShowDropDown")) { cb_dropdown(h, c); return ""; }
    return NULL;
}

static int RF_CALL cb_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmCombo *c = (RmCombo *)state;
    if (!c) return 0;
    switch (msg) {
    case WM_SIZE: cb_layout(h, c); break;
    case WM_SETFONT:
        if (c->in.edit) SendMessageW(c->in.edit, WM_SETFONT, (WPARAM)w, (LPARAM)l);
        cb_layout(h, c);
        break;
    case WM_SETFOCUS:
        if (c->in.edit) { SetFocus(c->in.edit); *res = 0; return 1; }
        break;
    case WM_COMMAND:
        if (c->in.edit && (HWND)l == c->in.edit) {
            if (HIWORD(w) == EN_CHANGE) rf_raise(h, "TextChanged", "");
            *res = 0;
            return 1;
        }
        break;
    case WM_CTLCOLOREDIT: case WM_CTLCOLORSTATIC: {
        const rf_theme *th = rm_look_theme(&c->look, NULL);
        unsigned back = input_back(th, h);
        SetTextColor((HDC)w, IsWindowEnabled((HWND)rf_hwnd(h)) ? th->input_text : th->disabled_text);
        SetBkColor((HDC)w, back);
        *res = (intptr_t)inner_brush(&c->in, back);
        return 1;
    }
    case WM_LBUTTONDOWN:
        SetFocus(c->in.edit ? c->in.edit : (HWND)rf_hwnd(h));
        cb_dropdown(h, c);
        *res = 0;
        return 1;
    case WM_MOUSEWHEEL:
        if (GetFocus() == (HWND)rf_hwnd(h) && c->n) {
            int d = GET_WHEEL_DELTA_WPARAM(w) > 0 ? -1 : 1, i = c->sel + d;
            if (i >= 0 && i < c->n) cb_select(h, c, i, 1);
            *res = 0;
            return 1;
        }
        break;
    case WM_KEYDOWN:
        if (w == VK_F4 || (w == VK_DOWN && (GetKeyState(VK_MENU) & 0x8000)) || (!c->editable && (w == VK_SPACE || w == VK_RETURN))) {
            cb_dropdown(h, c);
            *res = 0;
            return 1;
        }
        if (!c->editable && (w == VK_DOWN || w == VK_UP || w == VK_HOME || w == VK_END)) {
            int i = w == VK_DOWN ? c->sel + 1 : w == VK_UP ? c->sel - 1 : w == VK_HOME ? 0 : c->n - 1;
            if (i >= 0 && i < c->n) cb_select(h, c, i, 1);
            *res = 0;
            return 1;
        }
        break;
    case WM_SYSKEYDOWN:
        if (w == VK_DOWN) { cb_dropdown(h, c); *res = 0; return 1; }
        break;
    case WM_GETDLGCODE:
        *res = DLGC_WANTARROWS | DLGC_WANTCHARS;
        return 1;
    case WM_ENABLE:
        if (c->in.edit) EnableWindow(c->in.edit, (BOOL)w);
        break;
    default: break;
    }
    return 0;
}

static void RF_CALL cb_paint(rf_handle h, void *state, const rf_paint *p) {
    RmCombo *c = (RmCombo *)state;
    const rf_theme *th = rm_look_theme(&c->look, p);
    unsigned accent = rm_look_accent(&c->look, th), back = input_back(th, h), fg = th->input_text, border;
    int focused = GetFocus() == (HWND)rf_hwnd(h) || (c->in.edit && GetFocus() == c->in.edit);
    int pad = rf_px(p, 8), aw = rf_px(p, 26), isz = rf_px(p, 16), radius = rf_px(p, th->radius + 1);
    border = focused || c->open ? accent : rf_blend(th->border, th->hot_border, p->hover * 0.6);
    if (!p->enabled) { border = rf_blend(th->border, th->window, 0.4); fg = th->disabled_text; }
    rf_draw_rect(p, 0, 0, p->width, p->height, rf_blend(back, th->hot, c->editable ? 0 : p->hover * 0.5), border,
                 rf_px(p, 1), radius);
    if (!c->editable) {
        if (c->sel >= 0 && c->sel < c->n) {
            rm_item *it = &c->items[c->sel];
            int x = pad;
            if (rm_has_icon(it->image)) {
                rm_icon(p, it->image, pad, (p->height - isz) / 2, isz, isz, fg);
                x += isz + rf_px(p, 6);
            }
            rf_draw_text(p, it->text, x, 0, p->width - x - aw, p->height, fg, RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        } else if (*c->watermark) {
            rf_draw_text(p, c->watermark, pad, 0, p->width - pad - aw, p->height, rf_blend(fg, back, 0.5),
                         RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        }
        if (focused) rf_draw_rect(p, rf_px(p, 3), rf_px(p, 3), p->width - aw - rf_px(p, 3), p->height - rf_px(p, 6),
                                  RF_NONE, rf_blend(back, accent, 0.45), 1, radius > 2 ? radius - 2 : 0);
    }
    rm_chevron(p, p->width - aw / 2.0, p->height / 2.0 + (c->open ? -1 : 0), rf_px(p, 9), c->open ? RM_UP : RM_DOWN,
               rf_blend(fg, back, 0.2), rf_px(p, 1.5));
}

/* ================================================================== RmSlider */
typedef struct {
    rm_look look;
    int value, minv, maxv, tick, small, large, drag, show_value;
} RmSlider;

static int RF_CALL sl_create(rf_handle h, void **state) {
    RmSlider *s = (RmSlider *)calloc(1, sizeof *s);
    (void)h;
    if (!s) return 0;
    s->maxv = 100;
    s->small = 1;
    s->large = 10;
    *state = s;
    return 1;
}

static void RF_CALL sl_destroy(rf_handle h, void *state) { (void)h; free(state); }

static void sl_value(rf_handle h, RmSlider *s, int v) {
    if (v < s->minv) v = s->minv;
    if (v > s->maxv) v = s->maxv;
    if (v == s->value) return;
    s->value = v;
    rf_invalidate(h);
    rf_raise(h, "ValueChanged", "");
}

static int RF_CALL sl_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmSlider *s = (RmSlider *)state;
    if (rm_look_set(&s->look, prop, v)) return 1;
    if (rm_ieq(prop, "Value")) { sl_value(h, s, rm_int(v)); return 1; }
    if (rm_ieq(prop, "Minimum") || rm_ieq(prop, "Min")) { s->minv = rm_int(v); if (s->value < s->minv) s->value = s->minv; return 1; }
    if (rm_ieq(prop, "Maximum") || rm_ieq(prop, "Max")) { s->maxv = rm_int(v); if (s->value > s->maxv) s->value = s->maxv; return 1; }
    if (rm_ieq(prop, "TickFrequency")) { s->tick = rm_int(v); return 1; }
    if (rm_ieq(prop, "SmallChange")) { s->small = rm_int(v) > 0 ? rm_int(v) : 1; return 1; }
    if (rm_ieq(prop, "LargeChange")) { s->large = rm_int(v) > 0 ? rm_int(v) : 1; return 1; }
    if (rm_ieq(prop, "ShowValue")) { s->show_value = rm_bool(v); return 1; }
    return 0;
}

static const char *RF_CALL sl_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmSlider *s = (RmSlider *)state;
    const char *r = rm_look_get(&s->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Value")) return rad_str(s->value);
    if (rm_ieq(prop, "Minimum") || rm_ieq(prop, "Min")) return rad_str(s->minv);
    if (rm_ieq(prop, "Maximum") || rm_ieq(prop, "Max")) return rad_str(s->maxv);
    if (rm_ieq(prop, "TickFrequency")) return rad_str(s->tick);
    if (rm_ieq(prop, "SmallChange")) return rad_str(s->small);
    if (rm_ieq(prop, "LargeChange")) return rad_str(s->large);
    if (rm_ieq(prop, "ShowValue")) return rm_tf(s->show_value);
    return NULL;
}

static void sl_track(rf_handle h, int *x0, int *x1, int *ty) {
    RECT r;
    int th = rm_px(h, 18);
    GetClientRect((HWND)rf_hwnd(h), &r);
    *x0 = th / 2 + 1;
    *x1 = r.right - th / 2 - 1;
    *ty = r.bottom - rm_px(h, 14);
    if (*ty < th / 2) *ty = r.bottom / 2;
}

static void sl_from_x(rf_handle h, RmSlider *s, int x) {
    int x0, x1, ty;
    sl_track(h, &x0, &x1, &ty);
    if (x1 <= x0) return;
    sl_value(h, s, s->minv + (int)floor((double)(x - x0) * (s->maxv - s->minv) / (x1 - x0) + 0.5));
}

static int RF_CALL sl_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmSlider *s = (RmSlider *)state;
    if (!s) return 0;
    switch (msg) {
    case WM_LBUTTONDOWN:
        s->drag = 1;
        sl_from_x(h, s, GET_X_LPARAM(l));
        break;
    case WM_MOUSEMOVE:
        if (s->drag && (w & MK_LBUTTON)) sl_from_x(h, s, GET_X_LPARAM(l));
        break;
    case WM_LBUTTONUP: case WM_CAPTURECHANGED:
        if (s->drag) { s->drag = 0; rf_invalidate(h); }
        break;
    case WM_MOUSEWHEEL:
        sl_value(h, s, s->value + (GET_WHEEL_DELTA_WPARAM(w) > 0 ? s->small : -s->small));
        *res = 0;
        return 1;
    case WM_KEYDOWN: {
        int rtl = rf_rtl(h), v = s->value;
        if (w == VK_RIGHT) v += rtl ? -s->small : s->small;
        else if (w == VK_LEFT) v += rtl ? s->small : -s->small;
        else if (w == VK_UP) v += s->small;
        else if (w == VK_DOWN) v -= s->small;
        else if (w == VK_PRIOR) v += s->large;
        else if (w == VK_NEXT) v -= s->large;
        else if (w == VK_HOME) v = s->minv;
        else if (w == VK_END) v = s->maxv;
        else break;
        sl_value(h, s, v);
        *res = 0;
        return 1;
    }
    case WM_GETDLGCODE:
        *res = DLGC_WANTARROWS;
        return 1;
    default: break;
    }
    return 0;
}

static void RF_CALL sl_paint(rf_handle h, void *state, const rf_paint *p) {
    RmSlider *s = (RmSlider *)state;
    const rf_theme *t = rm_look_theme(&s->look, p);
    unsigned accent = rm_look_accent(&s->look, t), back = p->has_back ? p->back : t->window;
    int x0, x1, ty, th = rf_px(p, 18), tr = rf_px(p, 4), x;
    double f = s->maxv > s->minv ? (double)(s->value - s->minv) / (s->maxv - s->minv) : 0;
    if (p->has_back) rm_fill(p, 0, 0, p->width, p->height, p->back);
    if (!p->enabled) accent = rf_blend(t->border, back, 0.2);
    sl_track(h, &x0, &x1, &ty);
    x = x0 + (int)((x1 - x0) * f + 0.5);
    if (s->tick > 0 && s->maxv > s->minv) {
        int v;
        for (v = s->minv; v <= s->maxv; v += s->tick) {
            int tx = x0 + (int)((double)(x1 - x0) * (v - s->minv) / (s->maxv - s->minv) + 0.5);
            rf_draw_line(p, tx, ty + th / 2, tx, ty + th / 2 + rf_px(p, 3), rf_blend(t->border, back, 0.2), 1);
        }
    }
    rf_draw_rect(p, x0, ty - tr / 2, x1 - x0, tr, rf_blend(t->border, back, 0.25), RF_NONE, 0, tr / 2);
    rf_draw_rect(p, x0, ty - tr / 2, x - x0, tr, accent, RF_NONE, 0, tr / 2);
    {
        double k = th * (0.9 + 0.1 * p->hover), cx = x, cy = ty;
        rm_ellipse(p, cx - k / 2, cy - k / 2, k, k, t->input, rf_blend(t->border, accent, 0.4 + 0.6 * p->hover), rf_px(p, 1.2));
        rm_ellipse(p, cx - k / 4.5, cy - k / 4.5, k / 2.25, k / 2.25, accent, RF_NONE, 0);
        if (p->focused) rm_ellipse(p, cx - k / 2 - 2, cy - k / 2 - 2, k + 4, k + 4, RF_NONE, rf_blend(back, accent, 0.5), 1);
    }
    if (s->drag || s->show_value || p->hover > 0.5) {      /* value tip */
        const char *txt = rad_str(s->value);
        int tw = rm_text_w(p, txt) + rf_px(p, 12), tht = rm_text_h(p) + rf_px(p, 4);
        int bx = x - tw / 2, by = ty - th / 2 - tht - rf_px(p, 4);
        if (by >= 0) {
            if (bx < 0) bx = 0;
            if (bx + tw > p->width) bx = p->width - tw;
            if (s->drag || p->hover > 0.5) {
                rf_draw_rect(p, bx, by, tw, tht, rf_blend(t->window_text, back, 0.15), RF_NONE, 0, rf_px(p, 3));
                rf_draw_text(p, txt, bx, by, tw, tht, back, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
            } else {
                rf_draw_text(p, txt, bx, by, tw, tht, t->window_text, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
            }
        }
    }
}

/* ================================================================== registration */
RF_MODULE(rm_input) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmTextBox";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.create = tb_create; k.destroy = tb_destroy; k.set = tb_set; k.get = tb_get; k.invoke = tb_invoke;
    k.paint = tb_paint; k.message = tb_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Watermark,Icon,ShowClear,PasswordChar,MultiLine,ReadOnly,ErrorText,MaxLength,SelStart";
    k.events = "TextChanged,KeyPress,IconClick,GotFocus,LostFocus";
    k.methods = "Clear,SelectAll,AppendText,Focus";
    rf_register_class(&k);
    k.name = "RmComboBox";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.create = cb_create; k.destroy = cb_destroy; k.set = cb_set; k.get = cb_get; k.invoke = cb_invoke;
    k.paint = cb_paint; k.message = cb_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Items,SelectedIndex,SelectedItem,ListCount,Watermark,DropDownStyle,DroppedDown";
    k.events = "SelectedIndexChanged,TextChanged";
    k.methods = "AddItem,RemoveItem,Clear,List,IndexOf,ShowDropDown";
    rf_register_class(&k);
    k.name = "RmSlider";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.create = sl_create; k.destroy = sl_destroy; k.set = sl_set; k.get = sl_get; k.invoke = NULL;
    k.paint = sl_paint; k.message = sl_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Value,Minimum,Maximum,TickFrequency,SmallChange,LargeChange,ShowValue";
    k.events = "ValueChanged";
    k.methods = "";
    rf_register_class(&k);
}
