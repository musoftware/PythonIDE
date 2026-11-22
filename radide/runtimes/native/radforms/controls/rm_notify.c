/* RAD Modern notifications (non-visual components):
 *   RmToast        Show(title, text, kind, ms): a notification sliding in at a screen corner (kinds Info /
 *                  Success / Warning / Error), stacked, fades out, Click event, close button
 *   RmSuperTooltip SetToolTip(control, title, text, footer, image): rich hover tips (title, image, text,
 *   RmBalloonTip   footer) attached to any control; Show(control, title, text, ms) points a balloon at it
 *   RmMessageBox   Show(text, title, buttons, icon, heading) -> the pressed button: a themed modal
 *                  message box / task dialog (buttons "OK", "OKCancel", "YesNo", "YesNoCancel",
 *                  "RetryCancel", "AbortRetryIgnore" or your own "Save;Don't Save;Cancel")
 *
 * RF_CLASSES: RmToast RmSuperTooltip RmBalloonTip RmMessageBox
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <windowsx.h>
#include <commctrl.h>

static HWND root_of(rf_handle h) {
    HWND f = (HWND)rf_hwnd(rf_form(h));
    return f ? GetAncestor(f, GA_ROOT) : NULL;
}

static unsigned kind_color(const char *kind, const rf_theme *t) {
    if (rm_ieq(kind, "Success")) return RGB(46, 125, 50);
    if (rm_ieq(kind, "Warning")) return RGB(237, 108, 2);
    if (rm_ieq(kind, "Error")) return RGB(198, 40, 40);
    return t->accent;
}

static const char *kind_icon(const char *kind) {
    if (rm_ieq(kind, "Success")) return "success";
    if (rm_ieq(kind, "Warning")) return "warning";
    if (rm_ieq(kind, "Error")) return "error";
    if (rm_ieq(kind, "Question")) return "help";
    return "info";
}

static int set_alpha(HWND w, int a) {
    return SetLayeredWindowAttributes(w, 0, (BYTE)(a < 0 ? 0 : a > 255 ? 255 : a), LWA_ALPHA);
}

/* ================================================================== RmToast */
typedef struct Toast {
    struct Toast *next;
    HWND hwnd;
    rf_handle owner;
    char *title, *text, *kind;
    int ms, age, alpha, closing, hot_close, dpi;
    const rf_theme *theme;
} Toast;

typedef struct {
    rm_look look;
    char *position;
    int duration, width;
    Toast *list;
} RmToast;

static RmToast *g_toast_owner_state;

static void toast_paint(HWND hwnd, const rf_paint *p, void *user) {
    Toast *t = (Toast *)user;
    const rf_theme *th = t->theme;
    unsigned back = th->dark ? rf_blend(th->window, 0xFFFFFF, 0.08) : th->input, fg = th->window_text;
    unsigned kc = kind_color(t->kind, th);
    int pad = rf_px(p, 14), isz = rf_px(p, 24), bar = rf_px(p, 5), y = pad;
    (void)hwnd;
    rm_fill(p, 0, 0, p->width, p->height, back);
    rf_draw_rect(p, 0, 0, p->width, p->height, RF_NONE, rf_blend(th->border, back, 0.2), 1, 0);
    rm_fill(p, 0, 0, bar, p->height, kc);
    rm_icon(p, kind_icon(t->kind), bar + pad, pad, isz, isz, kc);
    {
        HGDIOBJ o = rm_font_push(p, 1.08, 2);
        int th1 = rm_text_h(p);
        rf_draw_text(p, t->title, bar + 2 * pad + isz, y, p->width - bar - 3 * pad - isz - rf_px(p, 18), th1, fg,
                     RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
        y += th1 + rf_px(p, 4);
        rm_font_pop(p, o);
    }
    rf_draw_text(p, t->text, bar + 2 * pad + isz, y, p->width - bar - 3 * pad - isz, p->height - y - pad,
                 rf_blend(fg, back, 0.2), RF_ALIGN_LEFT | RF_ALIGN_WRAP);
    {
        int cs = rf_px(p, 18), cx = p->width - cs - rf_px(p, 6), cy = rf_px(p, 6);
        if (t->hot_close) rf_draw_rect(p, cx, cy, cs, cs, rf_blend(back, fg, 0.12), RF_NONE, 0, rf_px(p, 3));
        rm_cross(p, cx + cs / 2.0, cy + cs / 2.0, cs * 0.42, rf_blend(fg, back, 0.3), rf_px(p, 1.3));
    }
    if (t->ms > 0) {        /* time left */
        double f = 1.0 - (double)t->age / t->ms;
        if (f < 0) f = 0;
        rm_fill(p, bar, p->height - rf_px(p, 2), (int)((p->width - bar) * f), rf_px(p, 2), rf_blend(kc, back, 0.3));
    }
}

static void toast_restack(RmToast *s);

static void toast_free(RmToast *s, Toast *t) {
    Toast **pp;
    for (pp = &s->list; *pp; pp = &(*pp)->next)
        if (*pp == t) { *pp = t->next; break; }
    if (t->hwnd) { RemovePropW(t->hwnd, L"rm.toast"); DestroyWindow(t->hwnd); }
    free(t->title); free(t->text); free(t->kind);
    free(t);
    toast_restack(s);
}

static LRESULT CALLBACK toast_proc(HWND hw, UINT m, WPARAM w, LPARAM l) {
    Toast *t = (Toast *)GetPropW(hw, L"rm.toast");
    RmToast *s = g_toast_owner_state;
    if (!t) return DefWindowProcW(hw, m, w, l);
    switch (m) {
    case WM_ERASEBKGND: return 1;
    case WM_PAINT: case WM_PRINTCLIENT:
        rm_paint_window(hw, m == WM_PRINTCLIENT ? (HDC)w : NULL, t->theme, t->dpi, t->theme->input, toast_paint, t);
        return 0;
    case WM_MOUSEACTIVATE: return MA_NOACTIVATE;
    case WM_TIMER: {
        if (t->closing) {
            t->alpha -= 40;
            if (t->alpha <= 0) {
                RmToast *st = (RmToast *)GetPropW(hw, L"rm.state");
                if (st) toast_free(st, t);
                return 0;
            }
        } else {
            if (t->alpha < 245) t->alpha += 40;
            t->age += 30;
            if (t->ms > 0 && t->age >= t->ms) {
                POINT pt;
                RECT r;
                GetCursorPos(&pt);
                GetWindowRect(hw, &r);
                if (PtInRect(&r, pt)) t->age = t->ms - 300;     /* stays while the mouse is over it */
                else t->closing = 1;
            }
            InvalidateRect(hw, NULL, FALSE);
        }
        set_alpha(hw, t->alpha);
        return 0;
    }
    case WM_MOUSEMOVE: {
        int cs = MulDiv(18, t->dpi, 96), x = GET_X_LPARAM(l), y = GET_Y_LPARAM(l);
        RECT r;
        TRACKMOUSEEVENT tme;
        int hot;
        GetClientRect(hw, &r);
        hot = x >= r.right - cs - MulDiv(6, t->dpi, 96) && y < cs + MulDiv(6, t->dpi, 96);
        if (hot != t->hot_close) { t->hot_close = hot; InvalidateRect(hw, NULL, FALSE); }
        tme.cbSize = sizeof tme;
        tme.dwFlags = TME_LEAVE;
        tme.hwndTrack = hw;
        tme.dwHoverTime = 0;
        TrackMouseEvent(&tme);
        return 0;
    }
    case WM_MOUSELEAVE:
        if (t->hot_close) { t->hot_close = 0; InvalidateRect(hw, NULL, FALSE); }
        return 0;
    case WM_LBUTTONUP:
        if (!t->hot_close) {
            char args[200];
            snprintf(args, sizeof args, "%s", t->title);
            rf_raise(t->owner, "Click", args);
        }
        t->closing = 1;
        return 0;
    default: break;
    }
    (void)s;
    return DefWindowProcW(hw, m, w, l);
}

static void toast_area(RmToast *s, rf_handle h, RECT *wa) {
    HWND r = root_of(h);
    MONITORINFO mi;
    mi.cbSize = sizeof mi;
    GetMonitorInfoW(MonitorFromWindow(r, MONITOR_DEFAULTTOPRIMARY), &mi);
    *wa = mi.rcWork;
    (void)s;
}

static void toast_restack(RmToast *s) {
    Toast *t;
    int offset = 0;
    for (t = s->list; t; t = t->next) {
        RECT r, wa;
        int w, hh, gap = MulDiv(10, t->dpi, 96), x, y;
        if (!t->hwnd) continue;
        GetWindowRect(t->hwnd, &r);
        w = r.right - r.left;
        hh = r.bottom - r.top;
        toast_area(s, t->owner, &wa);
        if (strstr(s->position, "Left")) x = wa.left + gap;
        else if (strstr(s->position, "Center")) x = (wa.left + wa.right - w) / 2;
        else x = wa.right - w - gap;
        if (strstr(s->position, "Top")) y = wa.top + gap + offset;
        else y = wa.bottom - hh - gap - offset;
        SetWindowPos(t->hwnd, HWND_TOPMOST, x, y, 0, 0, SWP_NOSIZE | SWP_NOACTIVATE);
        offset += hh + gap;
    }
}

static int RF_CALL to_create(rf_handle h, void **state) {
    RmToast *s = (RmToast *)calloc(1, sizeof *s);
    (void)h;
    if (!s) return 0;
    s->position = rm_strdup("BottomRight");
    s->duration = 3000;
    s->width = 340;
    *state = s;
    return 1;
}

static void RF_CALL to_destroy(rf_handle h, void *state) {
    RmToast *s = (RmToast *)state;
    (void)h;
    if (!s) return;
    while (s->list) toast_free(s, s->list);
    free(s->position);
    if (g_toast_owner_state == s) g_toast_owner_state = NULL;
    free(s);
}

static int RF_CALL to_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmToast *s = (RmToast *)state;
    (void)h;
    if (rm_look_set(&s->look, prop, v)) return 1;
    if (rm_ieq(prop, "Position")) { rm_setstr(&s->position, *v ? v : "BottomRight"); return 1; }
    if (rm_ieq(prop, "Duration")) { s->duration = rm_int(v); return 1; }
    if (rm_ieq(prop, "ToastWidth")) { s->width = rm_int(v) > 120 ? rm_int(v) : 120; return 1; }
    return 0;
}

static const char *RF_CALL to_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmToast *s = (RmToast *)state;
    const char *r = rm_look_get(&s->look, prop);
    Toast *t;
    int n = 0;
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Position")) return s->position;
    if (rm_ieq(prop, "Duration")) return rad_str(s->duration);
    if (rm_ieq(prop, "ToastWidth")) return rad_str(s->width);
    if (rm_ieq(prop, "Count")) { for (t = s->list; t; t = t->next) n++; return rad_str(n); }
    return NULL;
}

static void toast_show(rf_handle h, RmToast *s, const char *title, const char *text, const char *kind, int ms) {
    Toast *t = (Toast *)calloc(1, sizeof *t), **tail;
    const wchar_t *cls = rm_window_class(L"RadModernToast", toast_proc, 1);
    HWND root = root_of(h);
    int w, hh;
    if (!t) return;
    g_toast_owner_state = s;
    t->owner = h;
    t->title = rm_strdup(title);
    t->text = rm_strdup(text);
    t->kind = rm_strdup(kind && *kind ? kind : "Info");
    t->ms = ms;
    t->dpi = root ? rm_window_dpi(root) : 96;
    t->theme = rm_look_theme(&s->look, NULL);
    w = MulDiv(s->width, t->dpi, 96);
    {   /* height from the wrapped text */
        HDC dc = GetDC(NULL);
        RECT r;
        wchar_t *wt = rm_wide(text), *face = rm_wide(t->theme->font_name);
        HFONT f = CreateFontW(-MulDiv((int)(t->theme->font_size * 10), t->dpi, 720), 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET,
                              0, 0, CLEARTYPE_QUALITY, 0, face ? face : L"Segoe UI"), of = (HFONT)SelectObject(dc, f);
        SetRect(&r, 0, 0, w - MulDiv(14 * 3 + 24 + 5, t->dpi, 96), 0);
        DrawTextW(dc, wt ? wt : L"", -1, &r, DT_CALCRECT | DT_WORDBREAK | DT_NOPREFIX);
        hh = r.bottom + MulDiv(14 * 2 + 26, t->dpi, 96);
        if (hh < MulDiv(76, t->dpi, 96)) hh = MulDiv(76, t->dpi, 96);
        SelectObject(dc, of);
        DeleteObject(f);
        ReleaseDC(NULL, dc);
        free(wt);
        free(face);
    }
    t->hwnd = CreateWindowExW(WS_EX_TOOLWINDOW | WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_LAYERED, cls, L"", WS_POPUP, 0, 0, w, hh,
                              NULL, NULL, GetModuleHandleW(NULL), NULL);
    if (!t->hwnd) { free(t->title); free(t->text); free(t->kind); free(t); return; }
    SetPropW(t->hwnd, L"rm.toast", (HANDLE)t);
    SetPropW(t->hwnd, L"rm.state", (HANDLE)s);
    {   /* radforms.name: test / automation tools find it as "<component>.toast" */
        char nm[96];
        wchar_t *wn;
        ATOM a;
        snprintf(nm, sizeof nm, "%s.toast", rf_name(h));
        wn = rm_wide(nm);
        a = wn ? GlobalAddAtomW(wn) : 0;
        if (a) SetPropW(t->hwnd, L"radforms.name", (HANDLE)(UINT_PTR)a);
        free(wn);
    }
    for (tail = &s->list; *tail; tail = &(*tail)->next) {}
    *tail = t;                  /* newest last = further from the corner */
    t->alpha = rf_theme_current()->anim_ms > 0 ? 40 : 245;
    set_alpha(t->hwnd, t->alpha);
    toast_restack(s);
    ShowWindow(t->hwnd, SW_SHOWNOACTIVATE);
    SetTimer(t->hwnd, 1, 30, NULL);
}

static const char *RF_CALL to_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmToast *s = (RmToast *)state;
    if (rm_ieq(m, "Show")) {
        const char *ms = rm_arg(args, 3);
        toast_show(h, s, rm_arg(args, 0), rm_arg(args, 1), rm_arg(args, 2), *ms ? rm_int(ms) : s->duration);
        return "";
    }
    if (rm_ieq(m, "CloseAll")) {
        Toast *t;
        for (t = s->list; t; t = t->next) t->closing = 1;
        return "";
    }
    return NULL;
}

/* ================================================================== RmSuperTooltip / RmBalloonTip */
typedef struct Tip {
    struct Tip *next;
    HWND target;
    char *title, *text, *footer, *image;
} Tip;

typedef struct {
    rm_look look;
    int balloon, delay, max_width, shown_ms;
    Tip *tips;
    HWND popup;
    Tip *cur;
    rf_handle self;
    int point_x, point_y, above;
} RmTip;

static void tip_paint(HWND hwnd, const rf_paint *p, void *user) {
    RmTip *s = (RmTip *)user;
    Tip *t = s->cur;
    const rf_theme *th = rm_look_theme(&s->look, NULL);
    unsigned back = th->dark ? rf_blend(th->window, 0xFFFFFF, 0.1) : th->input, fg = th->window_text;
    int pad = rf_px(p, 10), y, tail = s->balloon ? rf_px(p, 10) : 0, top = s->above ? 0 : tail, bottom = p->height - (s->above ? tail : 0);
    int isz = t && rm_has_icon(t->image) ? rf_px(p, 32) : 0;
    (void)hwnd;
    if (!t) return;
    rm_fill(p, 0, 0, p->width, p->height, s->balloon ? th->window : back);
    if (s->balloon) {
        double tri[6];
        int tx = rf_px(p, 20);
        rf_draw_rect(p, 0, top, p->width, bottom - top, back, rf_blend(th->border, back, 0.1), 1, rf_px(p, 6));
        tri[0] = tx; tri[1] = s->above ? bottom - 1 : top + 1; tri[2] = tx + tail; tri[3] = tri[1];
        tri[4] = tx + tail / 2.0; tri[5] = s->above ? p->height : 0;
        rm_polygon(p, tri, 3, back);
    } else {
        rf_draw_rect(p, 0, 0, p->width, p->height, back, rf_blend(th->border, back, 0.1), 1, 0);
    }
    y = top + pad;
    if (*t->title) {
        HGDIOBJ o = rm_font_push(p, 1.0, 2);
        rf_draw_text(p, t->title, pad, y, p->width - 2 * pad, rm_text_h(p), fg, RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
        y += rm_text_h(p) + rf_px(p, 6);
        rm_font_pop(p, o);
    }
    if (isz) rm_icon(p, t->image, pad, y, isz, isz, th->accent);
    {
        int tx = pad + (isz ? isz + rf_px(p, 10) : 0), fh = *t->footer ? rm_text_h(p) + rf_px(p, 12) : 0;
        rf_draw_text(p, t->text, tx, y, p->width - tx - pad, bottom - y - pad - fh, rf_blend(fg, back, 0.15), RF_ALIGN_LEFT | RF_ALIGN_WRAP);
        if (*t->footer) {
            int fy = bottom - pad - rm_text_h(p);
            rf_draw_line(p, pad, fy - rf_px(p, 6), p->width - pad, fy - rf_px(p, 6), rf_blend(th->border, back, 0.3), 1);
            rm_icon(p, "help", pad, fy, rm_text_h(p), rm_text_h(p), rf_blend(fg, back, 0.4));
            rf_draw_text(p, t->footer, pad + rm_text_h(p) + rf_px(p, 6), fy, p->width - 2 * pad, rm_text_h(p), rf_blend(fg, back, 0.3),
                         RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
        }
    }
}

static LRESULT CALLBACK tip_proc(HWND hw, UINT m, WPARAM w, LPARAM l) {
    RmTip *s = (RmTip *)GetPropW(hw, L"rm.tip");
    if (!s) return DefWindowProcW(hw, m, w, l);
    switch (m) {
    case WM_ERASEBKGND: return 1;
    case WM_PAINT: case WM_PRINTCLIENT:
        rm_paint_window(hw, m == WM_PRINTCLIENT ? (HDC)w : NULL, rm_look_theme(&s->look, NULL), rm_window_dpi(hw),
                        rm_look_theme(&s->look, NULL)->input, tip_paint, s);
        return 0;
    case WM_MOUSEACTIVATE: return MA_NOACTIVATE;
    case WM_LBUTTONDOWN:
        ShowWindow(hw, SW_HIDE);
        return 0;
    case WM_TIMER:
        if (w == 2) { KillTimer(hw, 2); ShowWindow(hw, SW_HIDE); }
        return 0;
    default: break;
    }
    return DefWindowProcW(hw, m, w, l);
}

static void tip_measure(RmTip *s, Tip *t, int dpi, int *w, int *h) {
    HDC dc = GetDC(NULL);
    const rf_theme *th = rm_look_theme(&s->look, NULL);
    wchar_t *face = rm_wide(th->font_name), *wt = rm_wide(t->text), *wtt = rm_wide(t->title);
    HFONT f = CreateFontW(-MulDiv((int)(th->font_size * 10), dpi, 720), 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0,
                          CLEARTYPE_QUALITY, 0, face ? face : L"Segoe UI"), of = (HFONT)SelectObject(dc, f);
    RECT r, rt;
    TEXTMETRICW tm;
    int pad = MulDiv(10, dpi, 96), isz = rm_has_icon(t->image) ? MulDiv(42, dpi, 96) : 0, maxw = MulDiv(s->max_width, dpi, 96);
    GetTextMetricsW(dc, &tm);
    SetRect(&r, 0, 0, maxw - 2 * pad - isz, 0);
    DrawTextW(dc, wt ? wt : L"", -1, &r, DT_CALCRECT | DT_WORDBREAK | DT_NOPREFIX);
    SetRect(&rt, 0, 0, 2000, 0);
    DrawTextW(dc, wtt ? wtt : L"", -1, &rt, DT_CALCRECT | DT_SINGLELINE | DT_NOPREFIX);
    *w = r.right + 2 * pad + isz;
    if (rt.right + 2 * pad + MulDiv(10, dpi, 96) > *w) *w = rt.right + 2 * pad + MulDiv(10, dpi, 96);
    if (*w > maxw) *w = maxw;
    if (*w < MulDiv(120, dpi, 96)) *w = MulDiv(120, dpi, 96);
    *h = 2 * pad + (r.bottom > (isz ? MulDiv(32, dpi, 96) : 0) ? r.bottom : MulDiv(32, dpi, 96)) +
         (*t->title ? tm.tmHeight + MulDiv(6, dpi, 96) : 0) + (*t->footer ? tm.tmHeight + MulDiv(12, dpi, 96) : 0) +
         (s->balloon ? MulDiv(10, dpi, 96) : 0);
    SelectObject(dc, of);
    DeleteObject(f);
    ReleaseDC(NULL, dc);
    free(face); free(wt); free(wtt);
}

static void tip_show_at(RmTip *s, Tip *t, int x, int y, int ms) {
    int dpi = rm_window_dpi(t->target), w, h;
    MONITORINFO mi;
    if (!s->popup) {
        const wchar_t *cls = rm_window_class(L"RadModernTip", tip_proc, 1);
        s->popup = CreateWindowExW(WS_EX_TOOLWINDOW | WS_EX_TOPMOST | WS_EX_NOACTIVATE, cls, L"", WS_POPUP, 0, 0, 10, 10, NULL, NULL,
                                   GetModuleHandleW(NULL), NULL);
        if (!s->popup) return;
        SetPropW(s->popup, L"rm.tip", (HANDLE)s);
    }
    s->cur = t;
    tip_measure(s, t, dpi, &w, &h);
    mi.cbSize = sizeof mi;
    {
        POINT at;
        at.x = x;
        at.y = y;
        GetMonitorInfoW(MonitorFromPoint(at, MONITOR_DEFAULTTONEAREST), &mi);
    }
    s->above = y + h > mi.rcWork.bottom;
    if (s->above) y = y - h - MulDiv(s->balloon ? 0 : 24, dpi, 96);
    if (x + w > mi.rcWork.right) x = mi.rcWork.right - w;
    SetWindowPos(s->popup, HWND_TOPMOST, x, y, w, h, SWP_NOACTIVATE | SWP_SHOWWINDOW);
    InvalidateRect(s->popup, NULL, FALSE);
    KillTimer(s->popup, 2);
    if (ms > 0) SetTimer(s->popup, 2, (UINT)ms, NULL);
}

static LRESULT CALLBACK tip_target_sub(HWND hw, UINT m, WPARAM w, LPARAM l, UINT_PTR id, DWORD_PTR ref) {
    RmTip *s = (RmTip *)ref;
    Tip *t;
    for (t = s->tips; t && t->target != hw; t = t->next) {}
    switch (m) {
    case WM_MOUSEMOVE:
        if (t && !(s->popup && IsWindowVisible(s->popup) && s->cur == t)) {
            TRACKMOUSEEVENT tme;
            tme.cbSize = sizeof tme;
            tme.dwFlags = TME_LEAVE;
            tme.hwndTrack = hw;
            tme.dwHoverTime = 0;
            TrackMouseEvent(&tme);
            SetTimer(hw, 0x5254, (UINT)(s->delay > 0 ? s->delay : 1), NULL);
        }
        break;
    case WM_TIMER:
        if (w == 0x5254) {
            POINT pt;
            KillTimer(hw, 0x5254);
            if (t) {
                GetCursorPos(&pt);
                tip_show_at(s, t, pt.x, pt.y + MulDiv(20, rm_window_dpi(hw), 96), s->shown_ms);
            }
            return 0;
        }
        break;
    case WM_MOUSELEAVE: case WM_LBUTTONDOWN: case WM_KEYDOWN:
        KillTimer(hw, 0x5254);
        if (s->popup && s->cur == t) ShowWindow(s->popup, SW_HIDE);
        break;
    case WM_NCDESTROY:
        RemoveWindowSubclass(hw, tip_target_sub, id);
        for (t = s->tips; t; t = t->next) if (t->target == hw) t->target = NULL;
        break;
    default: break;
    }
    return DefSubclassProc(hw, m, w, l);
}

static int RF_CALL tip_create_k(rf_handle h, void **state, int balloon) {
    RmTip *s = (RmTip *)calloc(1, sizeof *s);
    if (!s) return 0;
    s->balloon = balloon;
    s->delay = 500;
    s->max_width = 320;
    s->shown_ms = balloon ? 0 : 8000;
    s->self = h;
    *state = s;
    return 1;
}
static int RF_CALL tip_create(rf_handle h, void **s) { return tip_create_k(h, s, 0); }
static int RF_CALL bal_create(rf_handle h, void **s) { return tip_create_k(h, s, 1); }

static void RF_CALL tip_destroy(rf_handle h, void *state) {
    RmTip *s = (RmTip *)state;
    (void)h;
    if (!s) return;
    while (s->tips) {
        Tip *t = s->tips;
        s->tips = t->next;
        if (t->target) RemoveWindowSubclass(t->target, tip_target_sub, (UINT_PTR)s);
        free(t->title); free(t->text); free(t->footer); free(t->image);
        free(t);
    }
    if (s->popup) DestroyWindow(s->popup);
    free(s);
}

static int RF_CALL tip_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmTip *s = (RmTip *)state;
    (void)h;
    if (rm_look_set(&s->look, prop, v)) return 1;
    if (rm_ieq(prop, "Delay") || rm_ieq(prop, "InitialDelay")) { s->delay = rm_int(v); return 1; }
    if (rm_ieq(prop, "MaxWidth")) { s->max_width = rm_int(v) > 100 ? rm_int(v) : 100; return 1; }
    if (rm_ieq(prop, "Duration") || rm_ieq(prop, "AutoPopDelay")) { s->shown_ms = rm_int(v); return 1; }
    return 0;
}

static const char *RF_CALL tip_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmTip *s = (RmTip *)state;
    const char *r = rm_look_get(&s->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Delay") || rm_ieq(prop, "InitialDelay")) return rad_str(s->delay);
    if (rm_ieq(prop, "MaxWidth")) return rad_str(s->max_width);
    if (rm_ieq(prop, "Duration") || rm_ieq(prop, "AutoPopDelay")) return rad_str(s->shown_ms);
    if (rm_ieq(prop, "IsShown")) return rm_tf(s->popup && IsWindowVisible(s->popup));
    return NULL;
}

static Tip *tip_for(RmTip *s, rf_handle h, const char *control) {
    rf_handle c = rf_find(control);
    HWND hw;
    Tip *t;
    char path[200];
    if (!c || !rf_hwnd(c)) {
        snprintf(path, sizeof path, "%s.%s", rf_name(rf_form(h)), control);
        c = rf_find(path);
    }
    hw = c ? (HWND)rf_hwnd(c) : NULL;
    if (!hw) return NULL;
    for (t = s->tips; t; t = t->next)
        if (t->target == hw) return t;
    t = (Tip *)calloc(1, sizeof *t);
    if (!t) return NULL;
    t->target = hw;
    t->title = rm_strdup(""); t->text = rm_strdup(""); t->footer = rm_strdup(""); t->image = rm_strdup("");
    t->next = s->tips;
    s->tips = t;
    SetWindowSubclass(hw, tip_target_sub, (UINT_PTR)s, (DWORD_PTR)s);
    return t;
}

static const char *RF_CALL tip_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmTip *s = (RmTip *)state;
    if (rm_ieq(m, "SetToolTip") || (rm_ieq(m, "Show") && s->balloon)) {
        Tip *t = tip_for(s, h, rm_arg(args, 0));
        if (!t) return "";
        rm_setstr(&t->title, rm_arg(args, 1));
        rm_setstr(&t->text, rm_arg(args, 2));
        if (rm_ieq(m, "Show")) {
            RECT r;
            const char *ms = rm_arg(args, 3);
            GetWindowRect(t->target, &r);
            tip_show_at(s, t, r.left + MulDiv(4, rm_window_dpi(t->target), 96), r.bottom, *ms ? rm_int(ms) : 5000);
        } else {
            rm_setstr(&t->footer, rm_arg(args, 3));
            rm_setstr(&t->image, rm_arg(args, 4));
        }
        return "";
    }
    if (rm_ieq(m, "Show")) {        /* super tooltip shown now under the control */
        Tip *t = tip_for(s, h, rm_arg(args, 0));
        RECT r;
        if (!t) return "";
        GetWindowRect(t->target, &r);
        tip_show_at(s, t, r.left, r.bottom + 2, s->shown_ms);
        return "";
    }
    if (rm_ieq(m, "Hide")) { if (s->popup) ShowWindow(s->popup, SW_HIDE); return ""; }
    if (rm_ieq(m, "RemoveToolTip")) {
        Tip *t = tip_for(s, h, rm_arg(args, 0));
        if (t) { rm_setstr(&t->text, ""); rm_setstr(&t->title, ""); }
        return "";
    }
    return NULL;
}

/* ================================================================== RmMessageBox */
typedef struct {
    rm_look look;
    char *last;
} RmMsg;

typedef struct {
    RmMsg *s;
    const rf_theme *theme;
    rm_list buttons;
    char *text, *heading, *icon, *result;
    int hot, focus, done, dpi, pressed;
    RECT btn[8];
} MsgDlg;

static void msg_layout(MsgDlg *d, int w, int h) {
    int i, bw = MulDiv(92, d->dpi, 96), bh = MulDiv(30, d->dpi, 96), gap = MulDiv(8, d->dpi, 96), pad = MulDiv(16, d->dpi, 96);
    int x = w - pad;
    for (i = d->buttons.n - 1; i >= 0 && i < 8; i--) {
        SetRect(&d->btn[i], x - bw, h - pad - bh + MulDiv(4, d->dpi, 96), x, h - pad + MulDiv(4, d->dpi, 96));
        x -= bw + gap;
    }
}

static void msg_paint(HWND hwnd, const rf_paint *p, void *user) {
    MsgDlg *d = (MsgDlg *)user;
    const rf_theme *t = d->theme;
    unsigned back = t->window, fg = t->window_text, foot = rf_blend(back, fg, 0.05), accent = rm_look_accent(&d->s->look, t);
    int pad = rf_px(p, 16), isz = *d->icon && !rm_ieq(d->icon, "None") ? rf_px(p, 36) : 0, x = pad + (isz ? isz + pad : 0), y = pad, i;
    int footer_h = rf_px(p, 30) + 2 * rf_px(p, 12);
    (void)hwnd;
    rm_fill(p, 0, 0, p->width, p->height, back);
    rm_fill(p, 0, p->height - footer_h, p->width, footer_h, foot);
    rf_draw_line(p, 0, p->height - footer_h, p->width, p->height - footer_h, rf_blend(t->border, back, 0.4), 1);
    if (isz) {
        const char *ic = rm_ieq(d->icon, "Question") ? "help" : kind_icon(d->icon);
        rm_icon(p, ic, pad, pad, isz, isz, rm_ieq(d->icon, "Question") ? accent : kind_color(d->icon, t));
    }
    if (*d->heading) {
        HGDIOBJ o = rm_font_push(p, 1.35, 1);
        int th = rm_text_h(p);
        rf_draw_text(p, d->heading, x, y, p->width - x - pad, th, rf_blend(fg, accent, t->dark ? 0.2 : 0.55), RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
        y += th + rf_px(p, 8);
        rm_font_pop(p, o);
    }
    rf_draw_text(p, d->text, x, y, p->width - x - pad, p->height - footer_h - y - pad / 2, fg, RF_ALIGN_LEFT | RF_ALIGN_WRAP);
    msg_layout(d, p->width, p->height);
    for (i = 0; i < d->buttons.n && i < 8; i++) {
        RECT r = d->btn[i];
        int primary = i == 0;
        unsigned fill = primary ? accent : t->face, tc = primary ? rm_on(accent) : t->face_text;
        if (i == d->hot) fill = primary ? rf_blend(accent, 0xFFFFFF, 0.15) : t->hot;
        if (i == d->pressed) fill = primary ? rf_blend(accent, 0, 0.2) : t->pressed;
        rf_draw_rect(p, r.left, r.top, r.right - r.left, r.bottom - r.top, fill, primary ? fill : t->border, 1, rf_px(p, t->radius + 2));
        if (i == d->focus) rf_draw_rect(p, r.left + 3, r.top + 3, r.right - r.left - 6, r.bottom - r.top - 6, RF_NONE, rf_blend(fill, tc, 0.6), 1,
                                        rf_px(p, t->radius));
        rf_draw_text(p, d->buttons.v[i], r.left, r.top, r.right - r.left, r.bottom - r.top, tc, RF_ALIGN_CENTER | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
    }
}

static int msg_hit(MsgDlg *d, HWND hw, int x, int y) {
    RECT r;
    POINT pt;
    int i;
    GetClientRect(hw, &r);
    msg_layout(d, r.right, r.bottom);
    pt.x = x;
    pt.y = y;
    for (i = 0; i < d->buttons.n && i < 8; i++)
        if (PtInRect(&d->btn[i], pt)) return i;
    return -1;
}

static void msg_finish(MsgDlg *d, int i) {
    if (i < 0 || i >= d->buttons.n) return;
    rm_setstr(&d->result, d->buttons.v[i]);
    d->done = 1;
}

static int msg_cancel_index(MsgDlg *d) {
    int i;
    static const char *const C[] = {"Cancel", "No", "Close", "Abort", "OK"};
    size_t k;
    for (k = 0; k < sizeof C / sizeof C[0]; k++)
        for (i = 0; i < d->buttons.n; i++)
            if (rm_ieq(d->buttons.v[i], C[k])) return i;
    return d->buttons.n - 1;
}

static LRESULT CALLBACK msg_proc(HWND hw, UINT m, WPARAM w, LPARAM l) {
    MsgDlg *d = (MsgDlg *)GetPropW(hw, L"rm.msg");
    int i;
    if (!d) return DefWindowProcW(hw, m, w, l);
    switch (m) {
    case WM_ERASEBKGND: return 1;
    case WM_PAINT: case WM_PRINTCLIENT:
        rm_paint_window(hw, m == WM_PRINTCLIENT ? (HDC)w : NULL, d->theme, d->dpi, d->theme->window, msg_paint, d);
        return 0;
    case WM_MOUSEMOVE:
        i = msg_hit(d, hw, GET_X_LPARAM(l), GET_Y_LPARAM(l));
        if (i != d->hot) {
            TRACKMOUSEEVENT tme;
            d->hot = i;
            InvalidateRect(hw, NULL, FALSE);
            tme.cbSize = sizeof tme;
            tme.dwFlags = TME_LEAVE;
            tme.hwndTrack = hw;
            tme.dwHoverTime = 0;
            TrackMouseEvent(&tme);
        }
        return 0;
    case WM_MOUSELEAVE:
        d->hot = -1;
        InvalidateRect(hw, NULL, FALSE);
        return 0;
    case WM_LBUTTONDOWN:
        d->pressed = msg_hit(d, hw, GET_X_LPARAM(l), GET_Y_LPARAM(l));
        InvalidateRect(hw, NULL, FALSE);
        return 0;
    case WM_LBUTTONUP:
        i = msg_hit(d, hw, GET_X_LPARAM(l), GET_Y_LPARAM(l));
        if (i >= 0 && i == d->pressed) msg_finish(d, i);
        d->pressed = -1;
        InvalidateRect(hw, NULL, FALSE);
        return 0;
    case WM_KEYDOWN:
        if (w == VK_RETURN || w == VK_SPACE) msg_finish(d, d->focus);
        else if (w == VK_ESCAPE) msg_finish(d, msg_cancel_index(d));
        else if (w == VK_TAB || w == VK_RIGHT || w == VK_LEFT) {
            int back = (w == VK_TAB && (GetKeyState(VK_SHIFT) & 0x8000)) || w == VK_LEFT;
            d->focus = (d->focus + (back ? d->buttons.n - 1 : 1)) % (d->buttons.n ? d->buttons.n : 1);
            InvalidateRect(hw, NULL, FALSE);
        } else {        /* the first letter of a button */
            for (i = 0; i < d->buttons.n; i++)
                if (d->buttons.v[i][0] && ((d->buttons.v[i][0] | 32) == ((int)w | 32))) { msg_finish(d, i); break; }
        }
        return 0;
    case WM_CLOSE:
        msg_finish(d, msg_cancel_index(d));
        return 0;
    default: break;
    }
    return DefWindowProcW(hw, m, w, l);
}

static const char *msg_show(rf_handle h, RmMsg *s, const char *text, const char *title, const char *buttons, const char *icon,
                            const char *heading) {
    MsgDlg d;
    HWND owner = root_of(h), hw;
    const wchar_t *cls = rm_window_class(L"RadModernMessageBox", msg_proc, 0);
    wchar_t *wt;
    RECT wr, cr;
    int w, hh, dpi, textw;
    MSG msg;
    const char *b = buttons && *buttons ? buttons : "OK";
    memset(&d, 0, sizeof d);
    d.s = s;
    d.theme = rm_look_theme(&s->look, NULL);
    d.hot = d.pressed = -1;
    d.text = rm_strdup(text);
    d.heading = rm_strdup(heading);
    d.icon = rm_strdup(icon && *icon ? icon : "None");
    d.result = rm_strdup("");
    if (rm_ieq(b, "OK")) rm_list_parse(&d.buttons, "OK", ';');
    else if (rm_ieq(b, "OKCancel")) rm_list_parse(&d.buttons, "OK;Cancel", ';');
    else if (rm_ieq(b, "YesNo")) rm_list_parse(&d.buttons, "Yes;No", ';');
    else if (rm_ieq(b, "YesNoCancel")) rm_list_parse(&d.buttons, "Yes;No;Cancel", ';');
    else if (rm_ieq(b, "RetryCancel")) rm_list_parse(&d.buttons, "Retry;Cancel", ';');
    else if (rm_ieq(b, "AbortRetryIgnore")) rm_list_parse(&d.buttons, "Abort;Retry;Ignore", ';');
    else rm_list_parse(&d.buttons, b, ';');
    dpi = d.dpi = owner ? rm_window_dpi(owner) : 96;
    {   /* size from the text */
        HDC dc = GetDC(NULL);
        RECT r;
        wchar_t *wtx = rm_wide(text), *face = rm_wide(d.theme->font_name);
        HFONT f = CreateFontW(-MulDiv((int)(d.theme->font_size * 10), dpi, 720), 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0,
                              CLEARTYPE_QUALITY, 0, face ? face : L"Segoe UI"), of = (HFONT)SelectObject(dc, f);
        int isz = rm_ieq(d.icon, "None") ? 0 : MulDiv(52, dpi, 96);
        textw = MulDiv(360, dpi, 96);
        SetRect(&r, 0, 0, textw, 0);
        DrawTextW(dc, wtx ? wtx : L"", -1, &r, DT_CALCRECT | DT_WORDBREAK | DT_NOPREFIX);
        w = r.right + isz + MulDiv(32, dpi, 96);
        if (w < MulDiv(100 * (d.buttons.n < 3 ? 3 : d.buttons.n) + 24, dpi, 96)) w = MulDiv(100 * (d.buttons.n < 3 ? 3 : d.buttons.n) + 24, dpi, 96);
        hh = r.bottom + MulDiv(16 * 2 + 54 + 10, dpi, 96) + (*d.heading ? MulDiv(32, dpi, 96) : 0);
        if (isz && hh < MulDiv(36 + 32 + 64, dpi, 96)) hh = MulDiv(36 + 32 + 64, dpi, 96);
        SelectObject(dc, of);
        DeleteObject(f);
        ReleaseDC(NULL, dc);
        free(wtx);
        free(face);
    }
    SetRect(&cr, 0, 0, w, hh);
    AdjustWindowRectEx(&cr, WS_CAPTION | WS_SYSMENU, FALSE, WS_EX_DLGMODALFRAME);
    if (owner) GetWindowRect(owner, &wr);
    else SetRect(&wr, 0, 0, GetSystemMetrics(SM_CXSCREEN), GetSystemMetrics(SM_CYSCREEN));
    wt = rm_wide(title && *title ? title : "");
    hw = CreateWindowExW(WS_EX_DLGMODALFRAME | (rf_rtl(h) ? WS_EX_LAYOUTRTL : 0), cls, wt ? wt : L"", WS_CAPTION | WS_SYSMENU | WS_POPUP,
                         (wr.left + wr.right - (cr.right - cr.left)) / 2, (wr.top + wr.bottom - (cr.bottom - cr.top)) / 2,
                         cr.right - cr.left, cr.bottom - cr.top, owner, NULL, GetModuleHandleW(NULL), NULL);
    free(wt);
    if (!hw) goto out;
    SetPropW(hw, L"rm.msg", (HANDLE)&d);
    {
        wchar_t *wn = rm_wide("RmMessageBox");
        ATOM a = wn ? GlobalAddAtomW(wn) : 0;
        if (a) SetPropW(hw, L"radforms.name", (HANDLE)(UINT_PTR)a);
        free(wn);
    }
    {   /* dark title bar in dark themes */
        typedef HRESULT(WINAPI * dwm_t)(HWND, DWORD, LPCVOID, DWORD);
        HMODULE m = LoadLibraryW(L"dwmapi.dll");
        dwm_t fn = m ? (dwm_t)(void *)GetProcAddress(m, "DwmSetWindowAttribute") : NULL;
        BOOL dark = d.theme->dark;
        if (fn) fn(hw, 20, &dark, sizeof dark);
    }
    if (rm_ieq(d.icon, "Error")) MessageBeep(MB_ICONHAND);
    else if (rm_ieq(d.icon, "Warning")) MessageBeep(MB_ICONEXCLAMATION);
    if (owner) EnableWindow(owner, FALSE);
    ShowWindow(hw, SW_SHOW);
    SetForegroundWindow(hw);
    SetFocus(hw);
    while (!d.done && GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
    if (!d.done && msg.message == WM_QUIT) PostQuitMessage((int)msg.wParam);
    if (owner) EnableWindow(owner, TRUE);
    RemovePropW(hw, L"rm.msg");
    {
        ATOM a = (ATOM)(UINT_PTR)RemovePropW(hw, L"radforms.name");
        if (a) GlobalDeleteAtom(a);
    }
    DestroyWindow(hw);
    if (owner) SetForegroundWindow(owner);
out:
    rm_setstr(&s->last, d.result);
    rm_list_free(&d.buttons);
    free(d.text); free(d.heading); free(d.icon); free(d.result);
    return s->last;
}

static int RF_CALL mb_create(rf_handle h, void **state) {
    RmMsg *s = (RmMsg *)calloc(1, sizeof *s);
    (void)h;
    if (!s) return 0;
    s->last = rm_strdup("");
    *state = s;
    return 1;
}

static void RF_CALL mb_destroy(rf_handle h, void *state) {
    RmMsg *s = (RmMsg *)state;
    (void)h;
    if (s) free(s->last);
    free(s);
}

static int RF_CALL mb_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmMsg *s = (RmMsg *)state;
    (void)h;
    return rm_look_set(&s->look, prop, v);
}

static const char *RF_CALL mb_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmMsg *s = (RmMsg *)state;
    const char *r = rm_look_get(&s->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Result")) return s->last;
    return NULL;
}

static const char *RF_CALL mb_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmMsg *s = (RmMsg *)state;
    if (rm_ieq(m, "Show")) {
        char *text = rm_strdup(rm_arg(args, 0)), *title = rm_strdup(rm_arg(args, 1)), *buttons = rm_strdup(rm_arg(args, 2));
        char *icon = rm_strdup(rm_arg(args, 3)), *heading = rm_strdup(rm_arg(args, 4));
        const char *r = msg_show(h, s, text, title, buttons, icon, heading);
        free(text); free(title); free(buttons); free(icon); free(heading);
        return r;
    }
    return NULL;
}

/* ================================================================== registration */
RF_MODULE(rm_notify) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmToast";
    k.flags = RF_CLASS_NONVISUAL;
    k.create = to_create; k.destroy = to_destroy; k.set = to_set; k.get = to_get; k.invoke = to_invoke;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Position,Duration,ToastWidth,Count";
    k.events = "Click";
    k.methods = "Show,CloseAll";
    rf_register_class(&k);
    k.name = "RmSuperTooltip";
    k.flags = RF_CLASS_NONVISUAL;
    k.create = tip_create; k.destroy = tip_destroy; k.set = tip_set; k.get = tip_get; k.invoke = tip_invoke;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Delay,MaxWidth,Duration,IsShown";
    k.events = "";
    k.methods = "SetToolTip,Show,Hide,RemoveToolTip";
    rf_register_class(&k);
    k.name = "RmBalloonTip";
    k.flags = RF_CLASS_NONVISUAL;
    k.create = bal_create;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Delay,MaxWidth,Duration,IsShown";
    k.events = "";
    k.methods = "SetToolTip,Show,Hide,RemoveToolTip";
    rf_register_class(&k);
    k.name = "RmMessageBox";
    k.flags = RF_CLASS_NONVISUAL;
    k.create = mb_create; k.destroy = mb_destroy; k.set = mb_set; k.get = mb_get; k.invoke = mb_invoke;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Result";
    k.events = "";
    k.methods = "Show";
    rf_register_class(&k);
}
