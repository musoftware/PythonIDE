/* RAD Modern dates: RmCalendar (month view), RmDatePicker (date box + drop-down calendar),
 * RmTimePicker (hour / minute / second segments). Month and day names come from the user's locale
 * (Arabic month names in an Arabic Windows); values are ISO text: "2026-11-22", "14:30:00".
 *
 * RF_CLASSES: RmCalendar RmDatePicker RmTimePicker
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <windowsx.h>

#ifndef LOCALE_SSHORTESTDAYNAME1
#define LOCALE_SSHORTESTDAYNAME1 0x00000060
#endif

/* ------------------------------------------------------------------ dates */
static int parse_date(const char *s, SYSTEMTIME *st) {
    int y, m, d;
    memset(st, 0, sizeof *st);
    if (!s || sscanf(s, "%d-%d-%d", &y, &m, &d) != 3) {
        if (!s || sscanf(s, "%d/%d/%d", &d, &m, &y) != 3) return 0;
    }
    if (y < 1601 || y > 9999 || m < 1 || m > 12 || d < 1 || d > 31) return 0;
    st->wYear = (WORD)y;
    st->wMonth = (WORD)m;
    st->wDay = (WORD)d;
    {
        FILETIME ft;
        if (!SystemTimeToFileTime(st, &ft)) return 0;
        FileTimeToSystemTime(&ft, st);
    }
    return 1;
}

static const char *date_iso(const SYSTEMTIME *st) {
    static char b[4][24];
    static int k;
    k = (k + 1) % 4;
    snprintf(b[k], sizeof b[k], "%04d-%02d-%02d", st->wYear % 10000, st->wMonth % 100, st->wDay % 100);
    return b[k];
}

static void add_days(SYSTEMTIME *st, int days) {
    FILETIME ft;
    ULARGE_INTEGER u;
    SystemTimeToFileTime(st, &ft);
    u.LowPart = ft.dwLowDateTime;
    u.HighPart = ft.dwHighDateTime;
    u.QuadPart += (ULONGLONG)((LONGLONG)days * 864000000000LL);
    ft.dwLowDateTime = u.LowPart;
    ft.dwHighDateTime = u.HighPart;
    FileTimeToSystemTime(&ft, st);
}

static int days_in(int y, int m) {
    static const int D[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    if (m == 2 && ((y % 4 == 0 && y % 100 != 0) || y % 400 == 0)) return 29;
    return D[(m - 1) % 12];
}

static void add_months(SYSTEMTIME *st, int months) {
    int m = st->wMonth - 1 + months, y = st->wYear + (m >= 0 ? m / 12 : (m - 11) / 12);
    m = ((m % 12) + 12) % 12 + 1;
    st->wYear = (WORD)y;
    st->wMonth = (WORD)m;
    if (st->wDay > days_in(y, m)) st->wDay = (WORD)days_in(y, m);
    add_days(st, 0);
}

static int cmp_date(const SYSTEMTIME *a, const SYSTEMTIME *b) {
    if (a->wYear != b->wYear) return a->wYear - b->wYear;
    if (a->wMonth != b->wMonth) return a->wMonth - b->wMonth;
    return a->wDay - b->wDay;
}

static const char *locale_text(LCTYPE t) {
    static char b[8][64];
    static int k;
    wchar_t w[64];
    char *u;
    k = (k + 1) % 8;
    b[k][0] = 0;
    if (GetLocaleInfoW(LOCALE_USER_DEFAULT, t, w, 64)) {
        u = rm_utf8(w);
        if (u) { snprintf(b[k], sizeof b[k], "%s", u); free(u); }
    }
    return b[k];
}

static int first_dow(void) {           /* 0 = Sunday ... 6 = Saturday */
    wchar_t w[4];
    if (GetLocaleInfoW(LOCALE_USER_DEFAULT, LOCALE_IFIRSTDAYOFWEEK, w, 4)) return (w[0] - L'0' + 1) % 7;   /* 0 = Monday there */
    return 0;
}

static const char *format_date(const SYSTEMTIME *st, const char *fmt) {
    static char b[4][128];
    static int k;
    wchar_t out[128], *wf = NULL;
    DWORD flags = 0;
    char *u;
    k = (k + 1) % 4;
    b[k][0] = 0;
    if (!fmt || !*fmt || rm_ieq(fmt, "Short")) flags = DATE_SHORTDATE;
    else if (rm_ieq(fmt, "Long")) flags = DATE_LONGDATE;
    else if (rm_ieq(fmt, "ISO")) return date_iso(st);
    else wf = rm_wide(fmt);
    if (GetDateFormatW(LOCALE_USER_DEFAULT, flags, st, wf, out, 128)) {
        u = rm_utf8(out);
        if (u) { snprintf(b[k], sizeof b[k], "%s", u); free(u); }
    }
    free(wf);
    return b[k];
}

/* ------------------------------------------------------------------ month view drawing (shared) */
typedef struct {
    SYSTEMTIME value, shown, minv, maxv, today;
    int has_min, has_max, hot;          /* hot: day cell 0..41, 100 prev, 101 next, -1 none */
    rm_look *look;
} Month;

static void month_init(Month *m) {
    GetLocalTime(&m->today);
    m->today.wHour = m->today.wMinute = m->today.wSecond = m->today.wMilliseconds = 0;
    m->value = m->today;
    m->shown = m->today;
    m->hot = -1;
}

static void month_first_cell(Month *m, SYSTEMTIME *out) {
    SYSTEMTIME first = m->shown;
    int back;
    first.wDay = 1;
    add_days(&first, 0);
    back = (first.wDayOfWeek - first_dow() + 7) % 7;
    add_days(&first, -back);
    *out = first;
}

/* layout inside (x, y, w, h): header 1 row, weekday row, 6 week rows */
static void month_geo(int x, int y, int w, int h, int *cw, int *ch, int *gy) {
    *cw = w / 7;
    *ch = h / 8;
    *gy = y + 2 * *ch;
    (void)x;
}

static int month_hit(Month *m, int x, int y, int w, int h, int px, int py) {
    int cw, ch, gy;
    month_geo(x, y, w, h, &cw, &ch, &gy);
    (void)m;
    if (py >= y && py < y + ch) {
        if (px < x + cw) return 100;
        if (px >= x + w - cw) return 101;
        return -1;
    }
    if (py < gy || px < x || px >= x + 7 * cw) return -1;
    {
        int r = (py - gy) / ch, c = (px - x) / cw;
        if (r > 5) return -1;
        return r * 7 + c;
    }
}

static int month_ok(Month *m, const SYSTEMTIME *d) {
    if (m->has_min && cmp_date(d, &m->minv) < 0) return 0;
    if (m->has_max && cmp_date(d, &m->maxv) > 0) return 0;
    return 1;
}

static void month_paint(const rf_paint *p, Month *m, const rf_theme *t, int x, int y, int w, int h, unsigned back, int focused) {
    unsigned accent = rm_look_accent(m->look, t), fg = t->window_text, dim = rf_blend(fg, back, 0.55);
    int cw, ch, gy, i, fd = first_dow();
    SYSTEMTIME d;
    char title[128];
    month_geo(x, y, w, h, &cw, &ch, &gy);
    snprintf(title, sizeof title, "%s %d", locale_text(LOCALE_SMONTHNAME1 + m->shown.wMonth - 1), m->shown.wYear);
    {
        HGDIOBJ o = rm_font_push(p, 1.1, 1);
        rf_draw_text(p, title, x + cw, y, w - 2 * cw, ch, fg, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
        rm_font_pop(p, o);
    }
    if (m->hot == 100) rm_ellipse(p, x + cw / 2.0 - ch * 0.4, y + ch * 0.1, ch * 0.8, ch * 0.8, rf_blend(back, fg, 0.1), RF_NONE, 0);
    if (m->hot == 101) rm_ellipse(p, x + w - cw / 2.0 - ch * 0.4, y + ch * 0.1, ch * 0.8, ch * 0.8, rf_blend(back, fg, 0.1), RF_NONE, 0);
    rm_chevron(p, x + cw / 2.0, y + ch / 2.0, ch * 0.32, RM_LEFT, fg, rf_px(p, 1.5));
    rm_chevron(p, x + w - cw / 2.0, y + ch / 2.0, ch * 0.32, RM_RIGHT, fg, rf_px(p, 1.5));
    for (i = 0; i < 7; i++) {
        int dow = (fd + i) % 7;                     /* LOCALE_SSHORTESTDAYNAME1 = Monday */
        rf_draw_text(p, locale_text(LOCALE_SSHORTESTDAYNAME1 + (dow + 6) % 7), x + i * cw, y + ch, cw, ch, dim,
                     RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
    }
    month_first_cell(m, &d);
    for (i = 0; i < 42; i++) {
        int cx = x + (i % 7) * cw, cy = gy + (i / 7) * ch, other = d.wMonth != m->shown.wMonth, ok = month_ok(m, &d);
        int sel = cmp_date(&d, &m->value) == 0, today = cmp_date(&d, &m->today) == 0;
        double s = (cw < ch ? cw : ch) * 0.86;
        unsigned c = !ok ? rf_blend(fg, back, 0.8) : other ? dim : fg;
        char num[8];
        if (sel) rm_ellipse(p, cx + (cw - s) / 2, cy + (ch - s) / 2, s, s, accent, RF_NONE, 0);
        else if (i == m->hot && ok) rm_ellipse(p, cx + (cw - s) / 2, cy + (ch - s) / 2, s, s, rf_blend(back, accent, 0.15), RF_NONE, 0);
        if (today && !sel) rm_ellipse(p, cx + (cw - s) / 2, cy + (ch - s) / 2, s, s, RF_NONE, accent, rf_px(p, 1.5));
        if (sel && focused) rm_ellipse(p, cx + (cw - s) / 2 - 2, cy + (ch - s) / 2 - 2, s + 4, s + 4, RF_NONE, rf_blend(back, accent, 0.6), 1);
        snprintf(num, sizeof num, "%d", d.wDay);
        rf_draw_text(p, num, cx, cy, cw, ch, sel ? rm_on(accent) : c, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
        add_days(&d, 1);
    }
}

/* returns 1 when the value changed */
static int month_click(Month *m, int hit) {
    SYSTEMTIME d;
    if (hit == 100) { add_months(&m->shown, -1); return 0; }
    if (hit == 101) { add_months(&m->shown, 1); return 0; }
    if (hit < 0 || hit > 41) return 0;
    month_first_cell(m, &d);
    add_days(&d, hit);
    if (!month_ok(m, &d)) return 0;
    m->shown = d;
    if (cmp_date(&d, &m->value) == 0) return 0;
    m->value = d;
    return 1;
}

static int month_key(Month *m, unsigned vk, int rtl) {
    SYSTEMTIME d = m->value;
    int right = rtl ? VK_LEFT : VK_RIGHT, left = rtl ? VK_RIGHT : VK_LEFT;
    if ((int)vk == right) add_days(&d, 1);
    else if ((int)vk == left) add_days(&d, -1);
    else if (vk == VK_DOWN) add_days(&d, 7);
    else if (vk == VK_UP) add_days(&d, -7);
    else if (vk == VK_NEXT) add_months(&d, 1);
    else if (vk == VK_PRIOR) add_months(&d, -1);
    else if (vk == VK_HOME) d.wDay = 1;
    else if (vk == VK_END) d.wDay = (WORD)days_in(d.wYear, d.wMonth);
    else return -1;
    add_days(&d, 0);
    if (!month_ok(m, &d)) return 0;
    m->value = d;
    m->shown = d;
    return 1;
}

/* ================================================================== RmCalendar / RmDatePicker */
typedef struct {
    rm_look look;
    Month m;
    int picker, open, hot_btn;
    char *format;
} RmDate;

static int RF_CALL dt_create_k(rf_handle h, void **state, int picker) {
    RmDate *d = (RmDate *)calloc(1, sizeof *d);
    (void)h;
    if (!d) return 0;
    month_init(&d->m);
    d->m.look = &d->look;
    d->picker = picker;
    d->format = rm_strdup("Short");
    *state = d;
    return 1;
}
static int RF_CALL cal_create(rf_handle h, void **s) { return dt_create_k(h, s, 0); }
static int RF_CALL dp_create(rf_handle h, void **s) { return dt_create_k(h, s, 1); }

static void RF_CALL dt_destroy(rf_handle h, void *state) {
    RmDate *d = (RmDate *)state;
    (void)h;
    if (d) free(d->format);
    free(d);
}

static int RF_CALL dt_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmDate *d = (RmDate *)state;
    SYSTEMTIME st;
    if (rm_look_set(&d->look, prop, v)) return 1;
    if (rm_ieq(prop, "Value") || rm_ieq(prop, "Text") || rm_ieq(prop, "SelectionStart")) {
        if (rm_ieq(v, "Today") || !*v) { GetLocalTime(&st); st.wHour = st.wMinute = st.wSecond = st.wMilliseconds = 0; }
        else if (!parse_date(v, &st)) return 1;
        if (cmp_date(&st, &d->m.value) != 0) {
            d->m.value = st;
            d->m.shown = st;
            rf_invalidate(h);
            rf_raise(h, "ValueChanged", "");
        }
        return 1;
    }
    if (rm_ieq(prop, "MinDate")) { d->m.has_min = parse_date(v, &d->m.minv); return 1; }
    if (rm_ieq(prop, "MaxDate")) { d->m.has_max = parse_date(v, &d->m.maxv); return 1; }
    if (rm_ieq(prop, "Format") || rm_ieq(prop, "CustomFormat")) { rm_setstr(&d->format, v); return 1; }
    return 0;
}

static const char *RF_CALL dt_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmDate *d = (RmDate *)state;
    const char *r = rm_look_get(&d->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Value") || rm_ieq(prop, "SelectionStart")) return date_iso(&d->m.value);
    if (rm_ieq(prop, "Text")) return format_date(&d->m.value, d->format);
    if (rm_ieq(prop, "MinDate")) return d->m.has_min ? date_iso(&d->m.minv) : "";
    if (rm_ieq(prop, "MaxDate")) return d->m.has_max ? date_iso(&d->m.maxv) : "";
    if (rm_ieq(prop, "Format")) return d->format;
    if (rm_ieq(prop, "Year")) return rad_str(d->m.value.wYear);
    if (rm_ieq(prop, "Month")) return rad_str(d->m.value.wMonth);
    if (rm_ieq(prop, "Day")) return rad_str(d->m.value.wDay);
    if (rm_ieq(prop, "DayOfWeek")) return rad_str(d->m.value.wDayOfWeek);
    return NULL;
}

/* the drop-down of RmDatePicker */
typedef struct { RmDate *d; rf_handle h; int changed; } DpPop;

static void dppop_paint(rm_popup *pp, const rf_paint *p) {
    DpPop *u = (DpPop *)pp->user;
    month_paint(p, &u->d->m, pp->theme, rf_px(p, 6), rf_px(p, 6), p->width - rf_px(p, 12), p->height - rf_px(p, 12), pp->theme->input, 0);
}

static int dppop_mouse(rm_popup *pp, unsigned msg, int x, int y) {
    DpPop *u = (DpPop *)pp->user;
    int pad = MulDiv(6, pp->dpi, 96), hit;
    if (msg == WM_MOUSEWHEEL) { add_months(&u->d->m.shown, y > 0 ? -1 : 1); rm_popup_redraw(pp); return 0; }
    hit = month_hit(&u->d->m, pad, pad, pp->w - 2 * pad, pp->h - 2 * pad, x, y);
    if (hit != u->d->m.hot) { u->d->m.hot = hit; rm_popup_redraw(pp); }
    if (msg == WM_LBUTTONUP && hit >= 0) {
        int ch = month_click(&u->d->m, hit);
        rm_popup_redraw(pp);
        if (hit <= 41) { u->changed |= ch; pp->result = 1; return 1; }
    }
    return 0;
}

static int dppop_key(rm_popup *pp, unsigned vk) {
    DpPop *u = (DpPop *)pp->user;
    int r;
    if (vk == VK_RETURN || vk == VK_SPACE) { pp->result = 1; return 1; }
    r = month_key(&u->d->m, vk, rf_rtl(u->h));
    if (r > 0) u->changed = 1;
    rm_popup_redraw(pp);
    return 0;
}

static void dp_dropdown(rf_handle h, RmDate *d) {
    rm_popup pp;
    DpPop u;
    int x, y, w = rm_px(h, 252), ht = rm_px(h, 236);
    if (d->open) return;
    memset(&pp, 0, sizeof pp);
    u.d = d;
    u.h = h;
    u.changed = 0;
    d->m.shown = d->m.value;
    d->m.hot = -1;
    rm_popup_place(h, w, ht, &x, &y);
    pp.owner = h;
    pp.theme = rm_look_theme(&d->look, NULL);
    pp.user = &u;
    pp.paint = dppop_paint;
    pp.mouse = dppop_mouse;
    pp.key = dppop_key;
    d->open = 1;
    rf_invalidate(h);
    rm_popup_run(&pp, x, y, w, ht);
    d->open = 0;
    d->m.hot = -1;
    rf_invalidate(h);
    if (u.changed) rf_raise(h, "ValueChanged", "");
}

static const char *RF_CALL dt_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmDate *d = (RmDate *)state;
    if (rm_ieq(m, "AddDays")) { add_days(&d->m.value, rm_int(rm_arg(args, 0))); d->m.shown = d->m.value; rf_invalidate(h); rf_raise(h, "ValueChanged", ""); return date_iso(&d->m.value); }
    if (rm_ieq(m, "AddMonths")) { add_months(&d->m.value, rm_int(rm_arg(args, 0))); d->m.shown = d->m.value; rf_invalidate(h); rf_raise(h, "ValueChanged", ""); return date_iso(&d->m.value); }
    if (rm_ieq(m, "Today")) { dt_set(h, d, "Value", "Today"); return date_iso(&d->m.value); }
    if (rm_ieq(m, "ShowDropDown") && d->picker) { dp_dropdown(h, d); return ""; }
    if (rm_ieq(m, "FormatDate")) {
        SYSTEMTIME st;
        if (!parse_date(rm_arg(args, 0), &st)) st = d->m.value;
        return format_date(&st, *rm_arg(args, 1) ? rm_arg(args, 1) : d->format);
    }
    return NULL;
}

static int RF_CALL dt_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmDate *d = (RmDate *)state;
    RECT r;
    int hit, x = GET_X_LPARAM(l), y = GET_Y_LPARAM(l);
    if (!d) return 0;
    GetClientRect((HWND)rf_hwnd(h), &r);
    switch (msg) {
    case WM_LBUTTONDOWN:
        SetFocus((HWND)rf_hwnd(h));
        if (d->picker) { dp_dropdown(h, d); *res = 0; return 1; }
        hit = month_hit(&d->m, rm_px(h, 4), rm_px(h, 4), r.right - rm_px(h, 8), r.bottom - rm_px(h, 8), x, y);
        if (month_click(&d->m, hit)) rf_raise(h, "ValueChanged", "");
        rf_invalidate(h);
        *res = 0;
        return 1;
    case WM_MOUSEMOVE:
        if (d->picker) break;
        hit = month_hit(&d->m, rm_px(h, 4), rm_px(h, 4), r.right - rm_px(h, 8), r.bottom - rm_px(h, 8), x, y);
        if (hit != d->m.hot) { d->m.hot = hit; rf_invalidate(h); }
        break;
    case WM_MOUSELEAVE:
        d->m.hot = -1;
        rf_invalidate(h);
        break;
    case WM_MOUSEWHEEL:
        if (d->picker) {
            if (GetFocus() == (HWND)rf_hwnd(h)) { add_days(&d->m.value, GET_WHEEL_DELTA_WPARAM(w) > 0 ? 1 : -1); rf_invalidate(h); rf_raise(h, "ValueChanged", ""); }
        } else {
            add_months(&d->m.shown, GET_WHEEL_DELTA_WPARAM(w) > 0 ? -1 : 1);
            rf_invalidate(h);
        }
        *res = 0;
        return 1;
    case WM_KEYDOWN:
        if (d->picker && (w == VK_F4 || w == VK_SPACE || w == VK_RETURN || (w == VK_DOWN && (GetKeyState(VK_MENU) & 0x8000)))) {
            dp_dropdown(h, d);
            *res = 0;
            return 1;
        }
        if (d->picker && (w == VK_UP || w == VK_DOWN)) {
            add_days(&d->m.value, w == VK_UP ? 1 : -1);
            rf_invalidate(h);
            rf_raise(h, "ValueChanged", "");
            *res = 0;
            return 1;
        }
        if (!d->picker) {
            int k = month_key(&d->m, (unsigned)w, rf_rtl(h));
            if (k >= 0) { if (k) rf_raise(h, "ValueChanged", ""); rf_invalidate(h); *res = 0; return 1; }
        }
        break;
    case WM_SYSKEYDOWN:
        if (d->picker && w == VK_DOWN) { dp_dropdown(h, d); *res = 0; return 1; }
        break;
    case WM_GETDLGCODE:
        *res = DLGC_WANTARROWS;
        return 1;
    default: break;
    }
    return 0;
}

static void RF_CALL dt_paint(rf_handle h, void *state, const rf_paint *p) {
    RmDate *d = (RmDate *)state;
    const rf_theme *t = rm_look_theme(&d->look, p);
    unsigned accent = rm_look_accent(&d->look, t), back = p->has_back ? p->back : t->input;
    (void)h;
    if (!d->picker) {
        rf_draw_rect(p, 0, 0, p->width, p->height, back, rf_blend(t->border, back, 0.3), 1, rf_px(p, t->radius + 2));
        month_paint(p, &d->m, t, rf_px(p, 4), rf_px(p, 4), p->width - rf_px(p, 8), p->height - rf_px(p, 8), back, p->focused);
        return;
    }
    {
        int focused = p->focused || d->open, isz = rf_px(p, 16), pad = rf_px(p, 8);
        unsigned border = focused ? accent : rf_blend(t->border, t->hot_border, p->hover * 0.6);
        rf_draw_rect(p, 0, 0, p->width, p->height, back, p->enabled ? border : rf_blend(t->border, t->window, 0.4), 1, rf_px(p, t->radius + 1));
        rf_draw_text(p, format_date(&d->m.value, d->format), pad, 0, p->width - 2 * pad - isz - rf_px(p, 6), p->height,
                     p->enabled ? t->input_text : t->disabled_text, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        rm_icon(p, "calendar", p->width - pad - isz, (p->height - isz) / 2, isz, isz, focused ? accent : rf_blend(t->input_text, back, 0.3));
        if (p->focused) rf_draw_rect(p, rf_px(p, 3), rf_px(p, 3), p->width - isz - rf_px(p, 16), p->height - rf_px(p, 6), RF_NONE,
                                     rf_blend(back, accent, 0.4), 1, rf_px(p, t->radius));
    }
}

/* ================================================================== RmTimePicker */
typedef struct {
    rm_look look;
    int hh, mm, ss, seconds, seg, h24, typed;
} RmTime;

static int RF_CALL tp_create(rf_handle h, void **state) {
    RmTime *t = (RmTime *)calloc(1, sizeof *t);
    SYSTEMTIME st;
    (void)h;
    if (!t) return 0;
    GetLocalTime(&st);
    t->hh = st.wHour;
    t->mm = st.wMinute;
    t->h24 = 1;
    *state = t;
    return 1;
}

static void RF_CALL tp_destroy(rf_handle h, void *state) { (void)h; free(state); }

static const char *tp_iso(RmTime *t) {
    static char b[4][24];
    static int k;
    k = (k + 1) % 4;
    snprintf(b[k], sizeof b[k], "%02d:%02d:%02d", t->hh % 100, t->mm % 100, t->ss % 100);
    return b[k];
}

static void tp_changed(rf_handle h) { rf_invalidate(h); rf_raise(h, "ValueChanged", ""); }

static int RF_CALL tp_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmTime *t = (RmTime *)state;
    if (rm_look_set(&t->look, prop, v)) return 1;
    if (rm_ieq(prop, "Value") || rm_ieq(prop, "Text")) {
        int a = 0, b = 0, c = 0;
        if (rm_ieq(v, "Now") || !*v) {
            SYSTEMTIME st;
            GetLocalTime(&st);
            a = st.wHour; b = st.wMinute; c = st.wSecond;
        } else if (sscanf(v, "%d:%d:%d", &a, &b, &c) < 2) return 1;
        if (a < 0 || a > 23 || b < 0 || b > 59 || c < 0 || c > 59) return 1;
        if (a != t->hh || b != t->mm || c != t->ss) { t->hh = a; t->mm = b; t->ss = c; tp_changed(h); }
        return 1;
    }
    if (rm_ieq(prop, "Format")) {
        t->seconds = strstr(v, "ss") != NULL || rm_ieq(v, "Long");
        t->h24 = !strstr(v, "tt") && !strstr(v, "h:");
        if (strstr(v, "HH")) t->h24 = 1;
        return 1;
    }
    if (rm_ieq(prop, "ShowSeconds")) { t->seconds = rm_bool(v); return 1; }
    return 0;
}

static const char *RF_CALL tp_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmTime *t = (RmTime *)state;
    const char *r = rm_look_get(&t->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Value") || rm_ieq(prop, "Text")) return tp_iso(t);
    if (rm_ieq(prop, "Hour")) return rad_str(t->hh);
    if (rm_ieq(prop, "Minute")) return rad_str(t->mm);
    if (rm_ieq(prop, "Second")) return rad_str(t->ss);
    if (rm_ieq(prop, "Format")) return t->seconds ? (t->h24 ? "HH:mm:ss" : "hh:mm:ss tt") : (t->h24 ? "HH:mm" : "hh:mm tt");
    if (rm_ieq(prop, "ShowSeconds")) return rm_tf(t->seconds);
    return NULL;
}

static void tp_step(rf_handle h, RmTime *t, int d) {
    switch (t->seg) {
    case 0: t->hh = (t->hh + d + 24) % 24; break;
    case 1: t->mm = (t->mm + d + 60) % 60; break;
    case 2: t->ss = (t->ss + d + 60) % 60; break;
    default: if (!t->h24) t->hh = (t->hh + 12) % 24; break;
    }
    tp_changed(h);
}

static int tp_nseg(RmTime *t) { return 2 + t->seconds + !t->h24; }

static int RF_CALL tp_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmTime *t = (RmTime *)state;
    int segw = rm_px(h, 26);
    if (!t) return 0;
    switch (msg) {
    case WM_LBUTTONDOWN: {
        int x = GET_X_LPARAM(l) - rm_px(h, 8), s = x / segw;
        RECT r;
        GetClientRect((HWND)rf_hwnd(h), &r);
        SetFocus((HWND)rf_hwnd(h));
        if (GET_X_LPARAM(l) > r.right - rm_px(h, 22)) tp_step(h, t, GET_Y_LPARAM(l) < r.bottom / 2 ? 1 : -1);   /* spin buttons */
        else if (s >= 0 && s < tp_nseg(t)) { t->seg = s == 2 && !t->seconds ? 3 : s; t->typed = 0; rf_invalidate(h); }
        *res = 0;
        return 1;
    }
    case WM_MOUSEWHEEL:
        tp_step(h, t, GET_WHEEL_DELTA_WPARAM(w) > 0 ? 1 : -1);
        *res = 0;
        return 1;
    case WM_KEYDOWN: {
        int rtl = rf_rtl(h), next = rtl ? VK_LEFT : VK_RIGHT, prev = rtl ? VK_RIGHT : VK_LEFT;
        int n = tp_nseg(t), cur = t->seg == 3 ? n - 1 : t->seg;
        if (w == VK_UP) tp_step(h, t, 1);
        else if (w == VK_DOWN) tp_step(h, t, -1);
        else if ((int)w == next) { cur = (cur + 1) % n; t->seg = cur == 2 && !t->seconds ? 3 : (cur == n - 1 && !t->h24 ? 3 : cur); t->typed = 0; rf_invalidate(h); }
        else if ((int)w == prev) { cur = (cur + n - 1) % n; t->seg = cur == 2 && !t->seconds ? 3 : (cur == n - 1 && !t->h24 ? 3 : cur); t->typed = 0; rf_invalidate(h); }
        else break;
        *res = 0;
        return 1;
    }
    case WM_CHAR:
        if (w >= '0' && w <= '9' && t->seg < 3) {
            int *v = t->seg == 0 ? &t->hh : t->seg == 1 ? &t->mm : &t->ss, mx = t->seg == 0 ? 23 : 59, nv;
            nv = t->typed ? *v * 10 + (int)(w - '0') : (int)(w - '0');
            if (nv > mx) nv = (int)(w - '0');
            *v = nv;
            t->typed = nv * 10 <= mx;
            if (!t->typed && t->seg < 1 + t->seconds) t->seg++;
            tp_changed(h);
            *res = 0;
            return 1;
        }
        break;
    case WM_GETDLGCODE:
        *res = DLGC_WANTARROWS | DLGC_WANTCHARS;
        return 1;
    default: break;
    }
    return 0;
}

static void RF_CALL tp_paint(rf_handle h, void *state, const rf_paint *p) {
    RmTime *t = (RmTime *)state;
    const rf_theme *th = rm_look_theme(&t->look, p);
    unsigned accent = rm_look_accent(&t->look, th), back = p->has_back ? p->back : th->input, fg = p->enabled ? th->input_text : th->disabled_text;
    int segw = rf_px(p, 26), x = rf_px(p, 8), i, n = 2 + t->seconds;
    int focused = p->focused;
    (void)h;
    rf_draw_rect(p, 0, 0, p->width, p->height, back, focused ? accent : rf_blend(th->border, th->hot_border, p->hover * 0.6), 1,
                 rf_px(p, th->radius + 1));
    for (i = 0; i < n; i++) {
        char num[8];
        int v = i == 0 ? (t->h24 ? t->hh : (t->hh % 12 ? t->hh % 12 : 12)) : i == 1 ? t->mm : t->ss;
        snprintf(num, sizeof num, "%02d", v);
        if (focused && t->seg == i) rf_draw_rect(p, x + i * segw, rf_px(p, 4), segw - rf_px(p, 6), p->height - rf_px(p, 8), accent, RF_NONE, 0, rf_px(p, 3));
        rf_draw_text(p, num, x + i * segw, 0, segw - rf_px(p, 6), p->height, focused && t->seg == i ? rm_on(accent) : fg, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
        if (i < n - 1) rf_draw_text(p, ":", x + i * segw + segw - rf_px(p, 6), 0, rf_px(p, 6), p->height, fg, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
    }
    if (!t->h24) {
        int ax = x + n * segw;
        if (focused && t->seg == 3) rf_draw_rect(p, ax, rf_px(p, 4), segw + rf_px(p, 4), p->height - rf_px(p, 8), accent, RF_NONE, 0, rf_px(p, 3));
        rf_draw_text(p, locale_text(t->hh < 12 ? LOCALE_S1159 : LOCALE_S2359), ax, 0, segw + rf_px(p, 4), p->height,
                     focused && t->seg == 3 ? rm_on(accent) : fg, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
    }
    rm_chevron(p, p->width - rf_px(p, 12), p->height * 0.32, rf_px(p, 7), RM_UP, rf_blend(fg, back, 0.3), rf_px(p, 1.3));
    rm_chevron(p, p->width - rf_px(p, 12), p->height * 0.68, rf_px(p, 7), RM_DOWN, rf_blend(fg, back, 0.3), rf_px(p, 1.3));
}

RF_MODULE(rm_date) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmCalendar";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.create = cal_create; k.destroy = dt_destroy; k.set = dt_set; k.get = dt_get; k.invoke = dt_invoke;
    k.paint = dt_paint; k.message = dt_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Value,MinDate,MaxDate,Format,Year,Month,Day,DayOfWeek";
    k.events = "ValueChanged";
    k.methods = "AddDays,AddMonths,Today,FormatDate";
    rf_register_class(&k);
    k.name = "RmDatePicker";
    k.create = dp_create;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Value,MinDate,MaxDate,Format,Year,Month,Day,DayOfWeek";
    k.events = "ValueChanged";
    k.methods = "AddDays,AddMonths,Today,FormatDate,ShowDropDown";
    rf_register_class(&k);
    k.name = "RmTimePicker";
    k.create = tp_create; k.destroy = tp_destroy; k.set = tp_set; k.get = tp_get; k.invoke = NULL;
    k.paint = tp_paint; k.message = tp_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Value,Format,ShowSeconds,Hour,Minute,Second";
    k.events = "ValueChanged";
    k.methods = "";
    rf_register_class(&k);
}
