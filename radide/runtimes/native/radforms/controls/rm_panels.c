/* RAD Modern containers: RmPanel (rounded / shadowed / gradient card with optional title bar),
 * RmGroupPanel (collapsible group), RmTabStrip (modern tabs top / left / bottom, closable, overflow
 * arrows, pages = children's TabPage), RmNavigationPane (Outlook-style page buttons + header),
 * RmDockPanel + RmDockWindow (tool windows docked left / right / top / bottom / fill, tabbed when they
 * share a side, auto-hide strips that slide out, floating inside the host, splitters, a layout that
 * can be saved and restored).
 * Children keep the coordinates of the designer (relative to the container's top-left corner).
 *
 * RF_CLASSES: RmPanel RmGroupPanel RmTabStrip RmNavigationPane RmDockPanel RmDockWindow
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <windowsx.h>

#define WM_RM_LATER (WM_APP + 0x5241)

static unsigned theme_face(const rf_theme *t) { return t->dark ? rf_blend(t->window, 0xFFFFFF, 0.06) : t->input; }

static unsigned own_back(const rf_paint *p, const rf_theme *t, unsigned def) {
    (void)t;
    return p->has_back ? p->back : def;
}

/* ================================================================== RmPanel */
typedef struct {
    rm_look look;
    char *title;
    int radius, shadow;
    unsigned grad, border;
    int has_grad, has_border;
} RmPanel;

static int RF_CALL pn_create(rf_handle h, void **state) {
    RmPanel *p = (RmPanel *)calloc(1, sizeof *p);
    (void)h;
    if (!p) return 0;
    p->title = rm_strdup("");
    p->radius = -1;
    *state = p;
    return 1;
}

static void RF_CALL pn_destroy(rf_handle h, void *state) {
    RmPanel *p = (RmPanel *)state;
    (void)h;
    if (p) free(p->title);
    free(p);
}

static int RF_CALL pn_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmPanel *p = (RmPanel *)state;
    (void)h;
    if (rm_look_set(&p->look, prop, v)) return 1;
    if (rm_ieq(prop, "Title")) { rm_setstr(&p->title, v); return 1; }
    if (rm_ieq(prop, "CornerRadius")) { p->radius = rm_int(v); return 1; }
    if (rm_ieq(prop, "Shadow")) { p->shadow = rm_bool(v); return 1; }
    if (rm_ieq(prop, "GradientTo")) { p->has_grad = rm_color(v, &p->grad); return 1; }
    if (rm_ieq(prop, "BorderColor")) { p->has_border = rm_color(v, &p->border); return 1; }
    return 0;
}

static const char *RF_CALL pn_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmPanel *p = (RmPanel *)state;
    const char *r = rm_look_get(&p->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Title")) return p->title;
    if (rm_ieq(prop, "CornerRadius")) return rad_str(p->radius);
    if (rm_ieq(prop, "Shadow")) return rm_tf(p->shadow);
    if (rm_ieq(prop, "GradientTo")) return p->has_grad ? rm_colorstr(p->grad) : "";
    if (rm_ieq(prop, "BorderColor")) return p->has_border ? rm_colorstr(p->border) : "";
    return NULL;
}

static void RF_CALL pn_paint(rf_handle h, void *state, const rf_paint *p) {
    RmPanel *pn = (RmPanel *)state;
    const rf_theme *t = rm_look_theme(&pn->look, p);
    unsigned back = own_back(p, t, theme_face(t)), border = pn->has_border ? pn->border : rf_blend(t->border, back, 0.35);
    int radius = rf_px(p, pn->radius >= 0 ? pn->radius : t->radius * 2 + 2), sh = pn->shadow ? rf_px(p, 6) : 0;
    int x = sh, y = sh / 2, w = p->width - 2 * sh, hh = p->height - sh - sh / 2;
    unsigned parent_back = t->window;
    if (sh) rm_shadow(p, x, y, w, hh, radius, sh, parent_back);
    if (pn->has_grad) {
        HRGN rg = CreateRoundRectRgn(x, y, x + w + 1, y + hh + 1, radius * 2, radius * 2);
        SelectClipRgn((HDC)p->hdc, rg);
        rm_gradient(p, x, y, w, hh, back, pn->grad, 1);
        SelectClipRgn((HDC)p->hdc, NULL);
        DeleteObject(rg);
        rf_draw_rect(p, x, y, w, hh, RF_NONE, border, 1, radius);
    } else {
        rf_draw_rect(p, x, y, w, hh, back, border, 1, radius);
    }
    if (*pn->title) {
        int th = rf_px(p, 30);
        HGDIOBJ o = rm_font_push(p, 1.05, 1);
        rf_draw_text(p, pn->title, x + rf_px(p, 12), y, w - rf_px(p, 24), th, p->has_fore ? p->fore : t->face_text,
                     RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        rm_font_pop(p, o);
        rf_draw_line(p, x + 1, y + th, x + w - 1, y + th, rf_blend(border, back, 0.3), 1);
    }
    rf_set_child_back(h, pn->has_grad ? rf_blend(back, pn->grad, 0.5) : back);
}

/* ================================================================== RmGroupPanel */
typedef struct {
    rm_look look;
    char *title;
    int collapsed, full_h, hot_head;
} RmGroup;

static int RF_CALL gp_create(rf_handle h, void **state) {
    RmGroup *g = (RmGroup *)calloc(1, sizeof *g);
    (void)h;
    if (!g) return 0;
    g->title = rm_strdup("");
    *state = g;
    return 1;
}

static void RF_CALL gp_destroy(rf_handle h, void *state) {
    RmGroup *g = (RmGroup *)state;
    (void)h;
    if (g) free(g->title);
    free(g);
}

static int gp_head(rf_handle h) { return rm_px(h, 30); }

static void gp_apply(rf_handle h, RmGroup *g) {
    HWND hw = (HWND)rf_hwnd(h);
    RECT r;
    if (!hw) return;
    GetClientRect(hw, &r);
    if (g->collapsed) {
        if (r.bottom > gp_head(h)) g->full_h = rm_unpx(h, r.bottom);
        rf_set_page(h, RF_PAGE_NONE);
        rf_prop_set_num(h, "Height", rm_unpx(h, gp_head(h)));
    } else {
        rf_set_page(h, RF_PAGE_ALL);
        if (g->full_h > 0) rf_prop_set_num(h, "Height", g->full_h);
    }
    rf_invalidate(h);
}

static void gp_collapse(rf_handle h, RmGroup *g, int on) {
    if (on == g->collapsed) return;
    g->collapsed = on;
    gp_apply(h, g);
    rf_raise(h, "CollapsedChanged", "");
}

static int RF_CALL gp_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmGroup *g = (RmGroup *)state;
    if (rm_look_set(&g->look, prop, v)) return 1;
    if (rm_ieq(prop, "Title")) { rm_setstr(&g->title, v); return 1; }
    if (rm_ieq(prop, "Collapsed")) {
        int on = rm_bool(v);
        HWND hw = (HWND)rf_hwnd(h);
        if (hw && !IsWindowVisible(GetAncestor(hw, GA_ROOT))) {     /* while the form loads: after the layout */
            g->collapsed = on;
            PostMessageW(hw, WM_RM_LATER, 1, 0);
            return 1;
        }
        gp_collapse(h, g, on);
        return 1;
    }
    return 0;
}

static const char *RF_CALL gp_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmGroup *g = (RmGroup *)state;
    const char *r = rm_look_get(&g->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Title")) return g->title;
    if (rm_ieq(prop, "Collapsed")) return rm_tf(g->collapsed);
    return NULL;
}

static const char *RF_CALL gp_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmGroup *g = (RmGroup *)state;
    (void)args;
    if (rm_ieq(m, "Toggle")) { gp_collapse(h, g, !g->collapsed); return ""; }
    if (rm_ieq(m, "Expand")) { gp_collapse(h, g, 0); return ""; }
    if (rm_ieq(m, "Collapse")) { gp_collapse(h, g, 1); return ""; }
    return NULL;
}

static int RF_CALL gp_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmGroup *g = (RmGroup *)state;
    if (!g) return 0;
    switch (msg) {
    case WM_RM_LATER:
        if (g->collapsed) gp_apply(h, g);
        *res = 0;
        return 1;
    case WM_LBUTTONDOWN:
        if (GET_Y_LPARAM(l) < gp_head(h)) { SetFocus((HWND)rf_hwnd(h)); gp_collapse(h, g, !g->collapsed); *res = 0; return 1; }
        break;
    case WM_MOUSEMOVE: {
        int hot = GET_Y_LPARAM(l) < gp_head(h);
        if (hot != g->hot_head) { g->hot_head = hot; rf_invalidate(h); }
        break;
    }
    case WM_MOUSELEAVE:
        if (g->hot_head) { g->hot_head = 0; rf_invalidate(h); }
        break;
    case WM_KEYDOWN:
        if (w == VK_SPACE || w == VK_RETURN) { gp_collapse(h, g, !g->collapsed); *res = 0; return 1; }
        if (w == VK_LEFT || w == VK_RIGHT) { gp_collapse(h, g, w == VK_LEFT); *res = 0; return 1; }
        break;
    default: break;
    }
    return 0;
}

static void RF_CALL gp_paint(rf_handle h, void *state, const rf_paint *p) {
    RmGroup *g = (RmGroup *)state;
    const rf_theme *t = rm_look_theme(&g->look, p);
    unsigned back = own_back(p, t, theme_face(t)), head = rf_blend(back, t->window_text, g->hot_head ? 0.08 : 0.04);
    unsigned fg = p->has_fore ? p->fore : t->face_text, border = rf_blend(t->border, back, 0.35);
    int hh = gp_head(h), radius = rf_px(p, t->radius + 2);
    rf_draw_rect(p, 0, 0, p->width, p->height, back, border, 1, radius);
    rf_draw_rect(p, 1, 1, p->width - 2, hh - 1, head, RF_NONE, 0, radius > 1 ? radius - 1 : 0);
    if (!g->collapsed) rf_draw_line(p, 1, hh, p->width - 1, hh, border, 1);
    rm_chevron(p, rf_px(p, 16), hh / 2.0, rf_px(p, 9), g->collapsed ? RM_RIGHT : RM_DOWN, fg, rf_px(p, 1.6));
    {
        HGDIOBJ o = rm_font_push(p, 1.0, 1);
        rf_draw_text(p, *g->title ? g->title : p->text, rf_px(p, 30), 0, p->width - rf_px(p, 40), hh, fg,
                     RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        rm_font_pop(p, o);
    }
    if (p->focused) rf_draw_rect(p, 2, 2, p->width - 4, hh - 4, RF_NONE, rf_blend(head, rm_look_accent(&g->look, t), 0.6), 1,
                                 radius > 2 ? radius - 2 : 0);
    rf_set_child_back(h, back);
}

/* ================================================================== RmTabStrip */
enum { TP_TOP, TP_LEFT, TP_BOTTOM };
typedef struct {
    rm_look look;
    rm_item *tabs;
    int n, sel, pos, closable, autoclose, scroll, hot, hot_close, overflow;
    int *page;              /* page id (TabPage of the children) of each tab */
    char *src;
} RmTabs;

static int RF_CALL ts_create(rf_handle h, void **state) {
    RmTabs *t = (RmTabs *)calloc(1, sizeof *t);
    (void)h;
    if (!t) return 0;
    t->hot = t->hot_close = -1;
    t->autoclose = 1;
    t->src = rm_strdup("");
    *state = t;
    return 1;
}

static void RF_CALL ts_destroy(rf_handle h, void *state) {
    RmTabs *t = (RmTabs *)state;
    (void)h;
    if (!t) return;
    rm_items_free(t->tabs, t->n);
    free(t->page);
    free(t->src);
    free(t);
}

static void ts_show(rf_handle h, RmTabs *t) {
    rf_set_page(h, t->sel >= 0 && t->sel < t->n ? t->page[t->sel] : RF_PAGE_NONE);
    rf_invalidate(h);
}

static void ts_select(rf_handle h, RmTabs *t, int i, int notify) {
    if (i < 0 || i >= t->n) i = t->n ? 0 : -1;
    if (i == t->sel) { ts_show(h, t); return; }
    t->sel = i;
    ts_show(h, t);
    if (notify) rf_raise(h, "SelectedIndexChanged", "");
}

static void ts_parse(RmTabs *t, const char *v) {
    int i;
    rm_items_free(t->tabs, t->n);
    free(t->page);
    t->tabs = rm_items_parse(v, &t->n);
    t->page = (int *)calloc((size_t)(t->n + 1), sizeof(int));
    for (i = 0; i < t->n && t->page; i++) t->page[i] = i;
    if (t->sel >= t->n) t->sel = t->n - 1;
}

static int RF_CALL ts_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmTabs *t = (RmTabs *)state;
    if (rm_look_set(&t->look, prop, v)) return 1;
    if (rm_ieq(prop, "TabPages") || rm_ieq(prop, "Tabs")) { rm_setstr(&t->src, v); ts_parse(t, v); ts_show(h, t); return 1; }
    if (rm_ieq(prop, "SelectedIndex")) { ts_select(h, t, rm_int(v), 1); return 1; }
    if (rm_ieq(prop, "TabPosition")) { t->pos = rm_ieq(v, "Left") ? TP_LEFT : rm_ieq(v, "Bottom") ? TP_BOTTOM : TP_TOP; return 1; }
    if (rm_ieq(prop, "Closable")) { t->closable = rm_bool(v); return 1; }
    if (rm_ieq(prop, "AutoClose")) { t->autoclose = rm_bool(v); return 1; }
    return 0;
}

static const char *RF_CALL ts_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmTabs *t = (RmTabs *)state;
    const char *r = rm_look_get(&t->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "TabPages") || rm_ieq(prop, "Tabs")) {
        rm_list l = {0, 0, 0};
        int i;
        const char *s;
        for (i = 0; i < t->n; i++) rm_list_add(&l, t->tabs[i].text, -1);
        s = rm_list_join(&l, ';');
        rm_list_free(&l);
        return s;
    }
    if (rm_ieq(prop, "SelectedIndex")) return rad_str(t->sel);
    if (rm_ieq(prop, "SelectedTab") || rm_ieq(prop, "Text")) return t->sel >= 0 && t->sel < t->n ? t->tabs[t->sel].text : "";
    if (rm_ieq(prop, "TabCount") || rm_ieq(prop, "Count")) return rad_str(t->n);
    if (rm_ieq(prop, "TabPosition")) return t->pos == TP_LEFT ? "Left" : t->pos == TP_BOTTOM ? "Bottom" : "Top";
    if (rm_ieq(prop, "Closable")) return rm_tf(t->closable);
    if (rm_ieq(prop, "AutoClose")) return rm_tf(t->autoclose);
    return NULL;
}

static void ts_remove(rf_handle h, RmTabs *t, int i) {
    if (i < 0 || i >= t->n) return;
    rm_item_clear(&t->tabs[i]);
    memmove(t->tabs + i, t->tabs + i + 1, sizeof(rm_item) * (t->n - i - 1));
    memmove(t->page + i, t->page + i + 1, sizeof(int) * (t->n - i - 1));
    t->n--;
    if (t->sel > i || t->sel >= t->n) t->sel--;
    if (t->sel < 0 && t->n) t->sel = 0;
    ts_show(h, t);
    rf_raise(h, "SelectedIndexChanged", "");
}

static const char *RF_CALL ts_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmTabs *t = (RmTabs *)state;
    if (rm_ieq(m, "AddTab")) {
        rm_item *nt = (rm_item *)realloc(t->tabs, sizeof(rm_item) * (t->n + 1));
        int *np = (int *)realloc(t->page, sizeof(int) * (t->n + 2)), cnt = 0, maxp = -1, i;
        rm_item *one;
        if (!nt || !np) return "-1";
        t->tabs = nt;
        t->page = np;
        one = rm_items_parse(rm_arg(args, 0), &cnt);
        if (!one || !cnt) { rm_items_free(one, cnt); return "-1"; }
        for (i = 0; i < t->n; i++) if (t->page[i] > maxp) maxp = t->page[i];
        t->tabs[t->n] = one[0];
        free(one);
        t->page[t->n] = maxp + 1;
        t->n++;
        rf_invalidate(h);
        return rad_str(t->n - 1);
    }
    if (rm_ieq(m, "RemoveTab") || rm_ieq(m, "RemoveAt")) { ts_remove(h, t, rm_int(rm_arg(args, 0))); return ""; }
    if (rm_ieq(m, "TabCaption")) {
        int i = rm_int(rm_arg(args, 0));
        if (i >= 0 && i < t->n) {
            if (*rm_arg(args, 1) || strchr(args, '\t')) { rm_setstr(&t->tabs[i].text, rm_arg(args, 1)); rf_invalidate(h); }
            return t->tabs[i].text;
        }
        return "";
    }
    if (rm_ieq(m, "SelectTab")) {
        int i;
        for (i = 0; i < t->n; i++)
            if (rm_ieq(t->tabs[i].name, rm_arg(args, 0)) || rm_ieq(t->tabs[i].text, rm_arg(args, 0))) ts_select(h, t, i, 1);
        return "";
    }
    return NULL;
}

/* geometry of the tabs: rectangles in device pixels */
typedef struct { RECT r[64]; RECT close[64]; int n, overflow; RECT left, right; RECT bar; } TabGeo;

static void ts_geo(rf_handle h, RmTabs *t, HDC dc, TabGeo *g) {
    RECT cr;
    int i, x, pad = rm_px(h, 14), bh = rm_px(h, 34), cw = t->closable ? rm_px(h, 20) : 0, isz = rm_px(h, 16);
    HWND hw = (HWND)rf_hwnd(h);
    HGDIOBJ of = SelectObject(dc, (HGDIOBJ)SendMessageW(hw, WM_GETFONT, 0, 0));
    GetClientRect(hw, &cr);
    memset(g, 0, sizeof *g);
    g->n = t->n < 64 ? t->n : 64;
    if (t->pos == TP_LEFT) {
        int lw = rm_px(h, 140);
        SetRect(&g->bar, 0, 0, lw, cr.bottom);
        for (i = 0; i < g->n; i++) {
            SetRect(&g->r[i], 0, i * bh, lw, (i + 1) * bh);
            if (cw) SetRect(&g->close[i], lw - cw - rm_px(h, 4), i * bh + (bh - cw) / 2, lw - rm_px(h, 4), i * bh + (bh + cw) / 2);
        }
        SelectObject(dc, of);
        return;
    }
    if (t->pos == TP_BOTTOM) SetRect(&g->bar, 0, cr.bottom - bh, cr.right, cr.bottom);
    else SetRect(&g->bar, 0, 0, cr.right, bh);
    x = 0;
    for (i = 0; i < g->n; i++) {
        SIZE sz;
        wchar_t *w = rm_wide(t->tabs[i].text);
        int tw;
        sz.cx = 0;
        if (w) GetTextExtentPoint32W(dc, w, (int)wcslen(w), &sz);
        free(w);
        tw = sz.cx + sz.cx / 12 + rm_px(h, 2) + 2 * pad + cw + (rm_has_icon(t->tabs[i].image) ? isz + rm_px(h, 6) : 0);   /* bold when selected */
        SetRect(&g->r[i], x, g->bar.top, x + tw, g->bar.bottom);
        x += tw;
    }
    if (x > cr.right) {                 /* overflow: scroll arrows on the right */
        int aw = rm_px(h, 22), off = 0, avail = cr.right - 2 * aw;
        g->overflow = 1;
        if (t->scroll > g->n - 1) t->scroll = g->n - 1;
        if (t->scroll < 0) t->scroll = 0;
        if (g->n) off = g->r[t->scroll].left;
        for (i = 0; i < g->n; i++) {
            OffsetRect(&g->r[i], -off, 0);
            if (g->r[i].right > avail) g->r[i].right = g->r[i].left > avail ? g->r[i].left : avail;
        }
        SetRect(&g->left, avail, g->bar.top, avail + aw, g->bar.bottom);
        SetRect(&g->right, avail + aw, g->bar.top, cr.right, g->bar.bottom);
    }
    for (i = 0; i < g->n && cw; i++) {
        RECT *r = &g->r[i];
        SetRect(&g->close[i], r->right - cw - rm_px(h, 6), r->top + (bh - cw) / 2, r->right - rm_px(h, 6), r->top + (bh + cw) / 2);
    }
    SelectObject(dc, of);
}

static int ts_hit(rf_handle h, RmTabs *t, int x, int y, int *close, int *arrow) {
    TabGeo g;
    POINT pt;
    HDC dc = GetDC((HWND)rf_hwnd(h));
    int i;
    ts_geo(h, t, dc, &g);
    ReleaseDC((HWND)rf_hwnd(h), dc);
    pt.x = x;
    pt.y = y;
    *close = 0;
    *arrow = 0;
    if (g.overflow && PtInRect(&g.left, pt)) { *arrow = -1; return -1; }
    if (g.overflow && PtInRect(&g.right, pt)) { *arrow = 1; return -1; }
    for (i = 0; i < g.n; i++)
        if (g.r[i].right > g.r[i].left && PtInRect(&g.r[i], pt)) {
            if (t->closable && PtInRect(&g.close[i], pt)) *close = 1;
            return i;
        }
    return -1;
}

static void ts_close(rf_handle h, RmTabs *t, int i) {
    rm_raise_item(h, "TabClosing", t->tabs[i].name, i);
    if (t->autoclose) ts_remove(h, t, i);
}

static int RF_CALL ts_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmTabs *t = (RmTabs *)state;
    int close, arrow, i;
    if (!t) return 0;
    switch (msg) {
    case WM_LBUTTONDOWN: case WM_MBUTTONUP:
        i = ts_hit(h, t, GET_X_LPARAM(l), GET_Y_LPARAM(l), &close, &arrow);
        if (arrow) { t->scroll += arrow; if (t->scroll < 0) t->scroll = 0; if (t->scroll >= t->n) t->scroll = t->n - 1; rf_invalidate(h); }
        else if (i >= 0 && (close || msg == WM_MBUTTONUP) && t->closable) ts_close(h, t, i);
        else if (i >= 0 && msg == WM_LBUTTONDOWN) { SetFocus((HWND)rf_hwnd(h)); ts_select(h, t, i, 1); }
        else break;
        *res = 0;
        return 1;
    case WM_MOUSEMOVE:
        i = ts_hit(h, t, GET_X_LPARAM(l), GET_Y_LPARAM(l), &close, &arrow);
        if (i != t->hot || (close ? i : -1) != t->hot_close) { t->hot = i; t->hot_close = close ? i : -1; rf_invalidate(h); }
        break;
    case WM_MOUSELEAVE:
        t->hot = t->hot_close = -1;
        rf_invalidate(h);
        break;
    case WM_MOUSEWHEEL:
        if (t->n) ts_select(h, t, t->sel + (GET_WHEEL_DELTA_WPARAM(w) > 0 ? -1 : 1), 1);
        *res = 0;
        return 1;
    case WM_KEYDOWN: {
        int next = t->pos == TP_LEFT ? VK_DOWN : (rf_rtl(h) ? VK_LEFT : VK_RIGHT);
        int prev = t->pos == TP_LEFT ? VK_UP : (rf_rtl(h) ? VK_RIGHT : VK_LEFT);
        if ((int)w == next || (w == VK_TAB && (GetKeyState(VK_CONTROL) & 0x8000) && !(GetKeyState(VK_SHIFT) & 0x8000)))
            ts_select(h, t, t->sel + 1 < t->n ? t->sel + 1 : 0, 1);
        else if ((int)w == prev || (w == VK_TAB && (GetKeyState(VK_CONTROL) & 0x8000)))
            ts_select(h, t, t->sel > 0 ? t->sel - 1 : t->n - 1, 1);
        else if (w == VK_HOME) ts_select(h, t, 0, 1);
        else if (w == VK_END) ts_select(h, t, t->n - 1, 1);
        else if (w == VK_DELETE && t->closable && t->sel >= 0) ts_close(h, t, t->sel);
        else break;
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

static void RF_CALL ts_paint(rf_handle h, void *state, const rf_paint *p) {
    RmTabs *t = (RmTabs *)state;
    const rf_theme *th = rm_look_theme(&t->look, p);
    unsigned accent = rm_look_accent(&t->look, th), back = own_back(p, th, th->window);
    unsigned page = theme_face(th), bar = rf_blend(back, th->window_text, th->dark ? 0.04 : 0.03);
    unsigned fg = p->has_fore ? p->fore : th->window_text, dim = rf_blend(fg, back, 0.35);
    TabGeo g;
    int i, isz = rf_px(p, 16), pad = rf_px(p, 14), ul = rf_px(p, 3);
    ts_geo(h, t, (HDC)p->hdc, &g);
    rm_fill(p, 0, 0, p->width, p->height, page);
    rm_fill(p, g.bar.left, g.bar.top, g.bar.right - g.bar.left, g.bar.bottom - g.bar.top, bar);
    if (t->pos == TP_LEFT) rf_draw_line(p, g.bar.right - 1, 0, g.bar.right - 1, p->height, rf_blend(th->border, back, 0.4), 1);
    else if (t->pos == TP_BOTTOM) rf_draw_line(p, 0, g.bar.top, p->width, g.bar.top, rf_blend(th->border, back, 0.4), 1);
    else rf_draw_line(p, 0, g.bar.bottom - 1, p->width, g.bar.bottom - 1, rf_blend(th->border, back, 0.4), 1);
    rf_draw_rect(p, 0, 0, p->width, p->height, RF_NONE, rf_blend(th->border, back, 0.4), 1, 0);
    for (i = 0; i < g.n; i++) {
        RECT r = g.r[i];
        rm_item *it = &t->tabs[i];
        int sel = i == t->sel, x = r.left + pad;
        unsigned c = sel ? (th->dark ? fg : accent) : (i == t->hot ? fg : dim);
        if (r.right <= r.left) continue;
        if (sel) rm_fill(p, r.left, r.top, r.right - r.left, r.bottom - r.top, page);
        else if (i == t->hot) rm_fill(p, r.left, r.top, r.right - r.left, r.bottom - r.top, rf_blend(bar, th->window_text, 0.06));
        if (sel) {
            if (t->pos == TP_LEFT) rf_draw_rect(p, r.left, r.top + rf_px(p, 6), ul, r.bottom - r.top - rf_px(p, 12), accent, RF_NONE, 0, 1);
            else if (t->pos == TP_BOTTOM) rf_draw_rect(p, r.left + rf_px(p, 8), r.bottom - ul, r.right - r.left - rf_px(p, 16), ul, accent, RF_NONE, 0, 1);
            else rf_draw_rect(p, r.left + rf_px(p, 8), r.bottom - ul, r.right - r.left - rf_px(p, 16), ul, accent, RF_NONE, 0, 1);
        }
        if (rm_has_icon(it->image)) {
            rm_icon(p, it->image, x, r.top + (r.bottom - r.top - isz) / 2, isz, isz, c);
            x += isz + rf_px(p, 6);
        }
        {
            HGDIOBJ o = sel ? rm_font_push(p, 1.0, 1) : NULL;
            rf_draw_text(p, it->text, x, r.top, r.right - x - (t->closable ? rf_px(p, 24) : rf_px(p, 6)), r.bottom - r.top, c,
                         RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
            if (o) rm_font_pop(p, o);
        }
        if (t->closable && (sel || i == t->hot)) {
            RECT cr = g.close[i];
            if (i == t->hot_close) rf_draw_rect(p, cr.left, cr.top, cr.right - cr.left, cr.bottom - cr.top,
                                                rf_blend(bar, th->window_text, 0.15), RF_NONE, 0, rf_px(p, 3));
            rm_cross(p, (cr.left + cr.right) / 2.0, (cr.top + cr.bottom) / 2.0, (cr.right - cr.left) * 0.4, c, rf_px(p, 1.3));
        }
    }
    if (g.overflow) {
        rm_fill(p, g.left.left, g.left.top, g.right.right - g.left.left, g.left.bottom - g.left.top, bar);
        rm_chevron(p, (g.left.left + g.left.right) / 2.0, (g.left.top + g.left.bottom) / 2.0, rf_px(p, 8), RM_LEFT, fg, rf_px(p, 1.5));
        rm_chevron(p, (g.right.left + g.right.right) / 2.0, (g.right.top + g.right.bottom) / 2.0, rf_px(p, 8), RM_RIGHT, fg, rf_px(p, 1.5));
    }
    if (p->focused && t->sel >= 0 && t->sel < g.n) {
        RECT r = g.r[t->sel];
        rf_draw_rect(p, r.left + 2, r.top + 2, r.right - r.left - 4, r.bottom - r.top - 4, RF_NONE, rf_blend(page, accent, 0.5), 1, 2);
    }
    rf_set_child_back(h, page);
}

/* ================================================================== RmNavigationPane */
typedef struct {
    rm_look look;
    rm_item *pages;
    int n, sel, hot;
    char *src;
} RmNav;

static int RF_CALL nv_create(rf_handle h, void **state) {
    RmNav *n = (RmNav *)calloc(1, sizeof *n);
    (void)h;
    if (!n) return 0;
    n->hot = -1;
    n->src = rm_strdup("");
    *state = n;
    return 1;
}

static void RF_CALL nv_destroy(rf_handle h, void *state) {
    RmNav *n = (RmNav *)state;
    (void)h;
    if (!n) return;
    rm_items_free(n->pages, n->n);
    free(n->src);
    free(n);
}

static int nv_btn_h(rf_handle h) { return rm_px(h, 34); }
static int nv_head_h(rf_handle h) { return rm_px(h, 34); }

static void nv_select(rf_handle h, RmNav *n, int i, int notify) {
    if (i < 0 || i >= n->n) i = n->n ? 0 : -1;
    if (i != n->sel) {
        n->sel = i;
        if (notify) rf_raise(h, "SelectedIndexChanged", "");
    }
    rf_set_page(h, n->sel >= 0 ? n->sel : RF_PAGE_NONE);
    rf_invalidate(h);
}

static int RF_CALL nv_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmNav *n = (RmNav *)state;
    if (rm_look_set(&n->look, prop, v)) return 1;
    if (rm_ieq(prop, "Pages") || rm_ieq(prop, "Items")) {
        rm_setstr(&n->src, v);
        rm_items_free(n->pages, n->n);
        n->pages = rm_items_parse(v, &n->n);
        if (n->sel >= n->n) n->sel = n->n - 1;
        nv_select(h, n, n->sel, 0);
        return 1;
    }
    if (rm_ieq(prop, "SelectedIndex")) { nv_select(h, n, rm_int(v), 1); return 1; }
    return 0;
}

static const char *RF_CALL nv_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmNav *n = (RmNav *)state;
    const char *r = rm_look_get(&n->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Pages") || rm_ieq(prop, "Items")) return n->src;
    if (rm_ieq(prop, "SelectedIndex")) return rad_str(n->sel);
    if (rm_ieq(prop, "SelectedPage") || rm_ieq(prop, "Text")) return n->sel >= 0 && n->sel < n->n ? n->pages[n->sel].text : "";
    if (rm_ieq(prop, "PageCount")) return rad_str(n->n);
    return NULL;
}

static int nv_hit(rf_handle h, RmNav *n, int y) {
    RECT r;
    int bh = nv_btn_h(h), top;
    GetClientRect((HWND)rf_hwnd(h), &r);
    top = r.bottom - n->n * bh;
    if (y < top) return -1;
    return (y - top) / bh < n->n ? (y - top) / bh : -1;
}

static int RF_CALL nv_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmNav *n = (RmNav *)state;
    int i;
    if (!n) return 0;
    switch (msg) {
    case WM_LBUTTONDOWN:
        i = nv_hit(h, n, GET_Y_LPARAM(l));
        if (i >= 0) { SetFocus((HWND)rf_hwnd(h)); nv_select(h, n, i, 1); *res = 0; return 1; }
        break;
    case WM_MOUSEMOVE:
        i = nv_hit(h, n, GET_Y_LPARAM(l));
        if (i != n->hot) { n->hot = i; rf_invalidate(h); }
        break;
    case WM_MOUSELEAVE:
        n->hot = -1;
        rf_invalidate(h);
        break;
    case WM_KEYDOWN:
        if (w == VK_DOWN || w == VK_RIGHT) nv_select(h, n, n->sel + 1 < n->n ? n->sel + 1 : 0, 1);
        else if (w == VK_UP || w == VK_LEFT) nv_select(h, n, n->sel > 0 ? n->sel - 1 : n->n - 1, 1);
        else break;
        *res = 0;
        return 1;
    case WM_GETDLGCODE:
        *res = DLGC_WANTARROWS;
        return 1;
    default: break;
    }
    return 0;
}

static void RF_CALL nv_paint(rf_handle h, void *state, const rf_paint *p) {
    RmNav *n = (RmNav *)state;
    const rf_theme *t = rm_look_theme(&n->look, p);
    unsigned accent = rm_look_accent(&n->look, t), back = own_back(p, t, theme_face(t));
    unsigned fg = p->has_fore ? p->fore : t->face_text, btn = rf_blend(back, t->window_text, t->dark ? 0.05 : 0.035);
    unsigned line = rf_blend(t->border, back, 0.4);
    int i, bh = nv_btn_h(h), hh = nv_head_h(h), top = p->height - n->n * bh, isz = rf_px(p, 18), pad = rf_px(p, 12);
    rf_draw_rect(p, 0, 0, p->width, p->height, back, line, 1, 0);
    rm_fill(p, 1, 1, p->width - 2, hh - 1, rf_blend(back, accent, 0.10));
    if (n->sel >= 0 && n->sel < n->n) {
        HGDIOBJ o = rm_font_push(p, 1.15, 1);
        rf_draw_text(p, n->pages[n->sel].text, pad, 0, p->width - 2 * pad, hh, fg, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        rm_font_pop(p, o);
    }
    rf_draw_line(p, 0, hh, p->width, hh, line, 1);
    for (i = 0; i < n->n; i++) {
        int y = top + i * bh, sel = i == n->sel;
        rm_item *it = &n->pages[i];
        unsigned f = sel ? rf_blend(btn, accent, 0.22) : i == n->hot ? rf_blend(btn, t->window_text, 0.06) : btn, c = fg;
        rm_fill(p, 1, y, p->width - 2, bh, f);
        rf_draw_line(p, 0, y, p->width, y, line, 1);
        if (sel) rm_fill(p, 1, y + 1, rf_px(p, 3), bh - 1, accent);
        if (rm_has_icon(it->image)) rm_icon(p, it->image, pad, y + (bh - isz) / 2, isz, isz, sel ? accent : c);
        {
            HGDIOBJ o = rm_font_push(p, 1.0, sel ? 1 : 0);
            rf_draw_text(p, it->text, pad + (rm_has_icon(it->image) ? isz + rf_px(p, 10) : 0), y, p->width - 2 * pad - isz, bh, c,
                         RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
            if (o) rm_font_pop(p, o);
        }
    }
    if (p->focused && n->sel >= 0) rf_draw_rect(p, 2, top + n->sel * bh + 2, p->width - 4, bh - 4, RF_NONE, accent, 1, 2);
    rf_set_child_back(h, back);
}

/* ================================================================== RmDockPanel / RmDockWindow */
enum { DS_LEFT, DS_RIGHT, DS_TOP, DS_BOTTOM, DS_FILL, DS_FLOAT };
static const char *const DSIDES[] = {"Left", "Right", "Top", "Bottom", "Fill", "Float"};

typedef struct {
    rm_look look;
    char *title;
    int side, autohide, size, closed, active, slid, hot_btn, drag, fx, fy, fw, fh, dragx, dragy;
} RmDockWin;

typedef struct {
    rm_look look;
    char *layout;
    int zone_sel[6];        /* selected tab per side */
    int split_drag, split_side, drag_start, size_start;
    RECT zone[6];
    rf_handle active;
} RmDock;

static int dock_title_h(rf_handle h) { return rm_px(h, 26); }
static int dock_strip(rf_handle h) { return rm_px(h, 24); }
static int dock_tabs_h(rf_handle h) { return rm_px(h, 24); }

static rf_handle ctl_of(HWND w) { return w ? (rf_handle)GetPropW(w, L"radforms.ctl") : NULL; }

static int dock_windows(rf_handle panel, rf_handle *out, int cap) {
    HWND hw = (HWND)rf_hwnd(panel), k;
    int n = 0;
    if (!hw) return 0;
    for (k = GetWindow(hw, GW_CHILD); k && n < cap; k = GetWindow(k, GW_HWNDNEXT)) {
        rf_handle c = ctl_of(k);
        if (c && rm_ieq(rf_type(c), "RmDockWindow") && rf_state(c)) out[n++] = c;
    }
    return n;
}

static RmDockWin *DW(rf_handle c) { return (RmDockWin *)rf_state(c); }

static int dw_visible(rf_handle c) { return !DW(c)->closed && rm_bool(rf_prop_get(c, "Visible")); }

static void dock_layout(rf_handle panel);

static void dock_place(rf_handle c, int x, int y, int w, int h, int show) {
    HWND hw = (HWND)rf_hwnd(c);
    if (!hw) return;
    SetWindowPos(hw, HWND_TOP, x, y, w > 0 ? w : 0, h > 0 ? h : 0, SWP_NOACTIVATE | (show ? SWP_SHOWWINDOW : SWP_HIDEWINDOW));
}

static void dock_layout(rf_handle panel) {
    RmDock *d = (RmDock *)rf_state(panel);
    HWND hw = (HWND)rf_hwnd(panel);
    rf_handle ws[64];
    int n, i, s, gap = rm_px(panel, 4), strip = dock_strip(panel), tabs = dock_tabs_h(panel);
    RECT cr, rest;
    int has_strip[4] = {0, 0, 0, 0};
    if (!d || !hw) return;
    GetClientRect(hw, &cr);
    n = dock_windows(panel, ws, 64);
    for (i = 0; i < n; i++) {           /* first layout: the designer size is the docked / floating size */
        RmDockWin *w = DW(ws[i]);
        RECT wr;
        if (w->size > 0 && w->fw > 0) continue;
        GetWindowRect((HWND)rf_hwnd(ws[i]), &wr);
        if (wr.right - wr.left <= 0) continue;
        if (!w->fw) { w->fw = rm_unpx(panel, wr.right - wr.left); w->fh = rm_unpx(panel, wr.bottom - wr.top); }
        if (!w->size) w->size = w->side == DS_TOP || w->side == DS_BOTTOM ? w->fh : w->fw;
    }
    for (i = 0; i < n; i++)
        if (dw_visible(ws[i]) && DW(ws[i])->autohide && DW(ws[i])->side < 4) has_strip[DW(ws[i])->side] = 1;
    rest = cr;
    if (has_strip[DS_LEFT]) rest.left += strip;
    if (has_strip[DS_RIGHT]) rest.right -= strip;
    if (has_strip[DS_TOP]) rest.top += strip;
    if (has_strip[DS_BOTTOM]) rest.bottom -= strip;
    memset(d->zone, 0, sizeof d->zone);
    for (s = 0; s < 4; s++) {           /* docked sides (order: left, right, top, bottom) */
        int cnt = 0, size = 0, k = 0, sel;
        rf_handle zw[64];
        for (i = 0; i < n; i++)
            if (dw_visible(ws[i]) && !DW(ws[i])->autohide && DW(ws[i])->side == s) {
                zw[cnt++] = ws[i];
                if (DW(ws[i])->size > size) size = DW(ws[i])->size;
            }
        if (!cnt) continue;
        size = rm_px(panel, size > 0 ? size : 200);
        if (s <= DS_RIGHT && size > (rest.right - rest.left) - rm_px(panel, 60)) size = (rest.right - rest.left) - rm_px(panel, 60);
        if (s >= DS_TOP && size > (rest.bottom - rest.top) - rm_px(panel, 60)) size = (rest.bottom - rest.top) - rm_px(panel, 60);
        if (size < rm_px(panel, 40)) size = rm_px(panel, 40);
        switch (s) {
        case DS_LEFT: SetRect(&d->zone[s], rest.left, rest.top, rest.left + size, rest.bottom); rest.left += size + gap; break;
        case DS_RIGHT: SetRect(&d->zone[s], rest.right - size, rest.top, rest.right, rest.bottom); rest.right -= size + gap; break;
        case DS_TOP: SetRect(&d->zone[s], rest.left, rest.top, rest.right, rest.top + size); rest.top += size + gap; break;
        default: SetRect(&d->zone[s], rest.left, rest.bottom - size, rest.right, rest.bottom); rest.bottom -= size + gap; break;
        }
        sel = d->zone_sel[s] < cnt ? d->zone_sel[s] : 0;
        for (k = 0; k < cnt; k++) {
            RECT z = d->zone[s];
            if (cnt > 1) z.bottom -= tabs;
            dock_place(zw[k], z.left, z.top, z.right - z.left, z.bottom - z.top, k == sel);
        }
    }
    {   /* fill (document) zone: tabbed at the top when several */
        int cnt = 0, k, sel;
        rf_handle zw[64];
        for (i = 0; i < n; i++)
            if (dw_visible(ws[i]) && DW(ws[i])->side == DS_FILL) zw[cnt++] = ws[i];
        d->zone[DS_FILL] = rest;
        sel = d->zone_sel[DS_FILL] < cnt ? d->zone_sel[DS_FILL] : 0;
        for (k = 0; k < cnt; k++) {
            RECT z = rest;
            if (cnt > 1) z.top += tabs;
            dock_place(zw[k], z.left, z.top, z.right - z.left, z.bottom - z.top, k == sel);
        }
    }
    for (i = 0; i < n; i++) {           /* auto-hidden (slid out or hidden) and floating windows */
        RmDockWin *w = DW(ws[i]);
        if (!dw_visible(ws[i])) { dock_place(ws[i], 0, 0, 0, 0, 0); continue; }
        if (w->autohide && w->side < 4) {
            int size = rm_px(panel, w->size > 0 ? w->size : 200);
            RECT z;
            switch (w->side) {
            case DS_LEFT: SetRect(&z, rest.left - (rest.left - cr.left) + strip, cr.top, cr.left + strip + size, cr.bottom); break;
            case DS_RIGHT: SetRect(&z, cr.right - strip - size, cr.top, cr.right - strip, cr.bottom); break;
            case DS_TOP: SetRect(&z, cr.left, cr.top + strip, cr.right, cr.top + strip + size); break;
            default: SetRect(&z, cr.left, cr.bottom - strip - size, cr.right, cr.bottom - strip); break;
            }
            dock_place(ws[i], z.left, z.top, z.right - z.left, z.bottom - z.top, w->slid);
        } else if (w->side == DS_FLOAT) {
            int fw = rm_px(panel, w->fw > 0 ? w->fw : 240), fh = rm_px(panel, w->fh > 0 ? w->fh : 180);
            int fx = w->fx >= 0 ? rm_px(panel, w->fx) : (cr.right - fw) / 2, fy = w->fy >= 0 ? rm_px(panel, w->fy) : (cr.bottom - fh) / 2;
            dock_place(ws[i], fx, fy, fw, fh, 1);
        }
    }
    InvalidateRect(hw, NULL, FALSE);
}

static void dock_activate(rf_handle panel, rf_handle c) {
    RmDock *d = (RmDock *)rf_state(panel);
    if (!d || d->active == c) return;
    if (d->active && rf_state(d->active)) { DW(d->active)->active = 0; rf_invalidate(d->active); }
    d->active = c;
    if (c) { DW(c)->active = 1; rf_invalidate(c); }
    rm_raise_item(panel, "ActiveWindowChanged", c ? rf_name(c) : "", -1);
}

static rf_handle dock_panel_of(rf_handle c) {
    HWND hw = (HWND)rf_hwnd(c);
    rf_handle p = hw ? ctl_of(GetParent(hw)) : NULL;
    return p && rm_ieq(rf_type(p), "RmDockPanel") ? p : NULL;
}

/* ---- the panel */
static int RF_CALL dk_create(rf_handle h, void **state) {
    RmDock *d = (RmDock *)calloc(1, sizeof *d);
    if (!d) return 0;
    d->layout = rm_strdup("");
    *state = d;
    if (rf_hwnd(h)) PostMessageW((HWND)rf_hwnd(h), WM_RM_LATER, 1, 0);    /* after the children are made */
    return 1;
}

static void RF_CALL dk_destroy(rf_handle h, void *state) {
    RmDock *d = (RmDock *)state;
    (void)h;
    if (d) free(d->layout);
    free(d);
}

static void dock_apply_layout(rf_handle h, const char *json) {
    rm_json *j = rm_json_parse(json);
    rf_handle ws[64];
    int n = dock_windows(h, ws, 64), i, k;
    if (!j || j->type != RMJ_ARR) { rm_json_free(j); return; }
    for (k = 0; k < j->n; k++) {
        const rm_json *o = &j->kids[k];
        const char *name = rm_json_text(o, "Name", "");
        for (i = 0; i < n; i++)
            if (rm_ieq(rf_name(ws[i]), name)) {
                RmDockWin *w = DW(ws[i]);
                const char *side = rm_json_text(o, "DockSide", "");
                int s;
                for (s = 0; s < 6; s++) if (rm_ieq(side, DSIDES[s])) w->side = s;
                w->size = (int)rm_json_num(o, "Size", w->size);
                w->autohide = rm_json_bool(o, "AutoHide", w->autohide);
                w->closed = !rm_json_bool(o, "Visible", !w->closed);
                w->fx = (int)rm_json_num(o, "X", w->fx);
                w->fy = (int)rm_json_num(o, "Y", w->fy);
            }
    }
    rm_json_free(j);
    dock_layout(h);
}

static const char *dock_save_layout(rf_handle h) {
    rf_handle ws[64];
    int n = dock_windows(h, ws, 64), i;
    rm_sb b = {0, 0, 0};
    rm_sb_addc(&b, '[');
    for (i = 0; i < n; i++) {
        RmDockWin *w = DW(ws[i]);
        char num[160];
        if (i) rm_sb_addc(&b, ',');
        rm_sb_add(&b, "{\"Name\":");
        rm_sb_json(&b, rf_name(ws[i]));
        snprintf(num, sizeof num, ",\"DockSide\":\"%s\",\"Size\":%d,\"AutoHide\":%s,\"Visible\":%s,\"X\":%d,\"Y\":%d}",
                 DSIDES[w->side], w->size, w->autohide ? "true" : "false", w->closed ? "false" : "true", w->fx, w->fy);
        rm_sb_add(&b, num);
    }
    rm_sb_addc(&b, ']');
    return rm_sb_ring(&b);
}

static int RF_CALL dk_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmDock *d = (RmDock *)state;
    if (rm_look_set(&d->look, prop, v)) return 1;
    if (rm_ieq(prop, "Layout")) {
        rm_setstr(&d->layout, v);
        if (rf_hwnd(h)) PostMessageW((HWND)rf_hwnd(h), WM_RM_LATER, 2, 0);
        return 1;
    }
    return 0;
}

static const char *RF_CALL dk_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmDock *d = (RmDock *)state;
    const char *r = rm_look_get(&d->look, prop);
    if (r) return r;
    if (rm_ieq(prop, "Layout")) return dock_save_layout(h);
    if (rm_ieq(prop, "ActiveWindow")) return d->active ? rf_name(d->active) : "";
    return NULL;
}

static rf_handle dock_find(rf_handle h, const char *name) {
    rf_handle ws[64];
    int n = dock_windows(h, ws, 64), i;
    for (i = 0; i < n; i++)
        if (rm_ieq(rf_name(ws[i]), name)) return ws[i];
    return NULL;
}

static const char *RF_CALL dk_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmDock *d = (RmDock *)state;
    rf_handle c = dock_find(h, rm_arg(args, 0));
    (void)d;
    if (rm_ieq(m, "SaveLayout")) return dock_save_layout(h);
    if (rm_ieq(m, "LoadLayout")) { dock_apply_layout(h, rm_arg(args, 0)); return ""; }
    if (rm_ieq(m, "ShowWindow") && c) { DW(c)->closed = 0; rf_prop_set(c, "Visible", "True"); dock_layout(h); dock_activate(h, c); return ""; }
    if (rm_ieq(m, "CloseWindow") && c) {
        DW(c)->closed = 1;
        dock_layout(h);
        rm_raise_item(h, "WindowClosed", rf_name(c), -1);
        return "";
    }
    if (rm_ieq(m, "DockWindow") && c) {
        int s;
        for (s = 0; s < 6; s++) if (rm_ieq(rm_arg(args, 1), DSIDES[s])) DW(c)->side = s;
        DW(c)->autohide = 0;
        dock_layout(h);
        return "";
    }
    if (rm_ieq(m, "Refresh")) { dock_layout(h); return ""; }
    return NULL;
}

/* strips + tab rows of the panel: which window is at (x, y) */
static rf_handle dock_tab_at(rf_handle h, int x, int y, int *zone_out, int *index_out) {
    RmDock *d = (RmDock *)rf_state(h);
    rf_handle ws[64];
    int n = dock_windows(h, ws, 64), s, i, tabs = dock_tabs_h(h), strip = dock_strip(h);
    HWND hw = (HWND)rf_hwnd(h);
    RECT cr;
    POINT pt;
    pt.x = x;
    pt.y = y;
    GetClientRect(hw, &cr);
    for (s = 0; s < 5; s++) {
        rf_handle zw[64];
        int cnt = 0, k;
        RECT z = d->zone[s], bar;
        for (i = 0; i < n; i++)
            if (dw_visible(ws[i]) && !DW(ws[i])->autohide && DW(ws[i])->side == s) zw[cnt++] = ws[i];
        if (cnt < 2) continue;
        if (s == DS_FILL) SetRect(&bar, z.left, z.top, z.right, z.top + tabs);
        else SetRect(&bar, z.left, z.bottom - tabs, z.right, z.bottom);
        if (!PtInRect(&bar, pt)) continue;
        k = (x - bar.left) * cnt / (bar.right - bar.left > 0 ? bar.right - bar.left : 1);
        if (k >= cnt) k = cnt - 1;
        *zone_out = s;
        *index_out = k;
        return zw[k];
    }
    {   /* auto-hide strips */
        int pos[4] = {0, 0, 0, 0};
        for (i = 0; i < n; i++) {
            RmDockWin *w = DW(ws[i]);
            RECT r;
            int len = rm_px(h, 110);
            if (!dw_visible(ws[i]) || !w->autohide || w->side > 3) continue;
            switch (w->side) {
            case DS_LEFT: SetRect(&r, 0, pos[0], strip, pos[0] + len); break;
            case DS_RIGHT: SetRect(&r, cr.right - strip, pos[1], cr.right, pos[1] + len); break;
            case DS_TOP: SetRect(&r, strip + pos[2], 0, strip + pos[2] + len, strip); break;
            default: SetRect(&r, strip + pos[3], cr.bottom - strip, strip + pos[3] + len, cr.bottom); break;
            }
            pos[w->side] += len + rm_px(h, 2);
            if (PtInRect(&r, pt)) { *zone_out = -1; *index_out = i; return ws[i]; }
        }
    }
    return NULL;
}

static int dock_splitter_at(rf_handle h, int x, int y) {
    RmDock *d = (RmDock *)rf_state(h);
    int s, gap = rm_px(h, 4);
    for (s = 0; s < 4; s++) {
        RECT z = d->zone[s];
        if (IsRectEmpty(&z)) continue;
        if (s == DS_LEFT && x >= z.right && x < z.right + gap && y >= z.top && y < z.bottom) return s;
        if (s == DS_RIGHT && x < z.left && x >= z.left - gap && y >= z.top && y < z.bottom) return s;
        if (s == DS_TOP && y >= z.bottom && y < z.bottom + gap && x >= z.left && x < z.right) return s;
        if (s == DS_BOTTOM && y < z.top && y >= z.top - gap && x >= z.left && x < z.right) return s;
    }
    return -1;
}

static void dock_hide_slid(rf_handle h, rf_handle except) {
    rf_handle ws[64];
    int n = dock_windows(h, ws, 64), i, any = 0;
    for (i = 0; i < n; i++)
        if (ws[i] != except && DW(ws[i])->slid) { DW(ws[i])->slid = 0; any = 1; }
    if (any) dock_layout(h);
}

static int RF_CALL dk_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmDock *d = (RmDock *)state;
    int x = GET_X_LPARAM(l), y = GET_Y_LPARAM(l), zone, idx;
    rf_handle c;
    if (!d) return 0;
    switch (msg) {
    case WM_SIZE:
        dock_layout(h);
        *res = 0;
        return 1;               /* the panel places its windows itself */
    case WM_RM_LATER:
        if (w == 2 && *d->layout) dock_apply_layout(h, d->layout);
        else dock_layout(h);
        *res = 0;
        return 1;
    case WM_SETCURSOR: {
        POINT pt;
        int s;
        GetCursorPos(&pt);
        ScreenToClient((HWND)rf_hwnd(h), &pt);
        s = d->split_drag ? d->split_side : dock_splitter_at(h, pt.x, pt.y);
        if (s >= 0 && (HWND)w == (HWND)rf_hwnd(h)) {
            SetCursor(LoadCursor(NULL, s <= DS_RIGHT ? IDC_SIZEWE : IDC_SIZENS));
            *res = TRUE;
            return 1;
        }
        break;
    }
    case WM_LBUTTONDOWN: {
        int s = dock_splitter_at(h, x, y);
        if (s >= 0) {
            rf_handle ws[64];
            int n = dock_windows(h, ws, 64), i;
            d->split_drag = 1;
            d->split_side = s;
            d->drag_start = s <= DS_RIGHT ? x : y;
            d->size_start = 0;
            for (i = 0; i < n; i++)
                if (DW(ws[i])->side == s && !DW(ws[i])->autohide && DW(ws[i])->size > d->size_start) d->size_start = DW(ws[i])->size;
            if (!d->size_start) d->size_start = 200;
            SetCapture((HWND)rf_hwnd(h));
            *res = 0;
            return 1;
        }
        c = dock_tab_at(h, x, y, &zone, &idx);
        if (c && zone >= 0) { d->zone_sel[zone] = idx; dock_layout(h); dock_activate(h, c); }
        else if (c) { int was = DW(c)->slid; dock_hide_slid(h, c); DW(c)->slid = !was; dock_layout(h); if (!was) dock_activate(h, c); }
        else dock_hide_slid(h, NULL);
        *res = 0;
        return 1;
    }
    case WM_MOUSEMOVE:
        if (d->split_drag) {
            int delta = (d->split_side <= DS_RIGHT ? x : y) - d->drag_start, sz;
            rf_handle ws[64];
            int n = dock_windows(h, ws, 64), i;
            if (d->split_side == DS_RIGHT || d->split_side == DS_BOTTOM) delta = -delta;
            sz = d->size_start + rm_unpx(h, delta);
            if (sz < 40) sz = 40;
            for (i = 0; i < n; i++)
                if (DW(ws[i])->side == d->split_side && !DW(ws[i])->autohide) DW(ws[i])->size = sz;
            dock_layout(h);
            *res = 0;
            return 1;
        }
        break;
    case WM_LBUTTONUP: case WM_CAPTURECHANGED:
        if (d->split_drag) {
            d->split_drag = 0;
            if (msg == WM_LBUTTONUP) ReleaseCapture();
            *res = 0;
            return 1;
        }
        break;
    default: break;
    }
    return 0;
}

static void RF_CALL dk_paint(rf_handle h, void *state, const rf_paint *p) {
    RmDock *d = (RmDock *)state;
    const rf_theme *t = rm_look_theme(&d->look, p);
    unsigned accent = rm_look_accent(&d->look, t), back = own_back(p, t, rf_blend(t->window, t->window_text, 0.06));
    unsigned fg = t->window_text, tabbar = rf_blend(back, t->window_text, 0.04);
    rf_handle ws[64];
    int n = dock_windows(h, ws, 64), s, i, tabs = dock_tabs_h(h), strip = dock_strip(h);
    int pos[4] = {0, 0, 0, 0};
    rm_fill(p, 0, 0, p->width, p->height, back);
    for (s = 0; s < 5; s++) {           /* tab rows of shared zones */
        rf_handle zw[64];
        int cnt = 0, k, sel;
        RECT z = d->zone[s], bar;
        for (i = 0; i < n; i++)
            if (dw_visible(ws[i]) && !DW(ws[i])->autohide && DW(ws[i])->side == s) zw[cnt++] = ws[i];
        if (cnt < 2) continue;
        sel = d->zone_sel[s] < cnt ? d->zone_sel[s] : 0;
        if (s == DS_FILL) SetRect(&bar, z.left, z.top, z.right, z.top + tabs);
        else SetRect(&bar, z.left, z.bottom - tabs, z.right, z.bottom);
        rm_fill(p, bar.left, bar.top, bar.right - bar.left, bar.bottom - bar.top, tabbar);
        for (k = 0; k < cnt; k++) {
            int x0 = bar.left + (bar.right - bar.left) * k / cnt, x1 = bar.left + (bar.right - bar.left) * (k + 1) / cnt;
            if (k == sel) {
                rm_fill(p, x0, bar.top, x1 - x0, bar.bottom - bar.top, t->window);
                rm_fill(p, x0, s == DS_FILL ? bar.top : bar.bottom - rf_px(p, 2), x1 - x0, rf_px(p, 2), accent);
            }
            rf_draw_text(p, DW(zw[k])->title && *DW(zw[k])->title ? DW(zw[k])->title : rf_name(zw[k]), x0 + rf_px(p, 6), bar.top,
                         x1 - x0 - rf_px(p, 12), bar.bottom - bar.top, k == sel ? fg : rf_blend(fg, back, 0.35),
                         RF_ALIGN_CENTER | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        }
    }
    for (i = 0; i < n; i++) {           /* auto-hide strips */
        RmDockWin *w = DW(ws[i]);
        int len = rf_px(p, 110);
        RECT r;
        const char *title = w->title && *w->title ? w->title : rf_name(ws[i]);
        if (!dw_visible(ws[i]) || !w->autohide || w->side > 3) continue;
        switch (w->side) {
        case DS_LEFT: SetRect(&r, 0, pos[0], strip, pos[0] + len); break;
        case DS_RIGHT: SetRect(&r, p->width - strip, pos[1], p->width, pos[1] + len); break;
        case DS_TOP: SetRect(&r, strip + pos[2], 0, strip + pos[2] + len, strip); break;
        default: SetRect(&r, strip + pos[3], p->height - strip, strip + pos[3] + len, p->height); break;
        }
        pos[w->side] += len + rf_px(p, 2);
        rf_draw_rect(p, r.left + 1, r.top + 1, r.right - r.left - 2, r.bottom - r.top - 2, w->slid ? rf_blend(back, accent, 0.25) : tabbar,
                     RF_NONE, 0, rf_px(p, 2));
        if (w->side <= DS_RIGHT) {      /* vertical text */
            LOGFONTW lf;
            HFONT f, of;
            wchar_t *wt = rm_wide(title);
            GetObjectW((HGDIOBJ)p->font, sizeof lf, &lf);
            lf.lfEscapement = lf.lfOrientation = 2700;
            f = CreateFontIndirectW(&lf);
            of = (HFONT)SelectObject((HDC)p->hdc, f);
            SetTextColor((HDC)p->hdc, fg);
            if (wt) TextOutW((HDC)p->hdc, r.right - rf_px(p, 5), r.top + rf_px(p, 8), wt, (int)wcslen(wt));
            free(wt);
            SelectObject((HDC)p->hdc, of);
            DeleteObject(f);
        } else {
            rf_draw_text(p, title, r.left, r.top, r.right - r.left, r.bottom - r.top, fg, RF_ALIGN_CENTER | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        }
    }
}

/* ---- a dock window */
static int RF_CALL dw_create(rf_handle h, void **state) {
    RmDockWin *w = (RmDockWin *)calloc(1, sizeof *w);
    (void)h;
    if (!w) return 0;
    w->title = rm_strdup("");
    w->hot_btn = -1;
    w->fx = w->fy = -1;
    *state = w;
    return 1;
}

static void RF_CALL dw_destroy(rf_handle h, void *state) {
    RmDockWin *w = (RmDockWin *)state;
    (void)h;
    if (w) free(w->title);
    free(w);
}

static void dw_relayout(rf_handle h) {
    rf_handle p = dock_panel_of(h);
    if (p) dock_layout(p);
}

static int RF_CALL dw_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmDockWin *w = (RmDockWin *)state;
    if (rm_look_set(&w->look, prop, v)) return 1;
    if (rm_ieq(prop, "Title")) { rm_setstr(&w->title, v); dw_relayout(h); return 1; }
    if (rm_ieq(prop, "DockSide")) {
        int s;
        w->side = DS_LEFT;
        for (s = 0; s < 6; s++) if (rm_ieq(v, DSIDES[s])) w->side = s;
        dw_relayout(h);
        return 1;
    }
    if (rm_ieq(prop, "AutoHide")) { w->autohide = rm_bool(v); w->slid = 0; dw_relayout(h); return 1; }
    if (rm_ieq(prop, "DockSize")) { w->size = rm_int(v); dw_relayout(h); return 1; }
    return 0;
}

static const char *RF_CALL dw_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmDockWin *w = (RmDockWin *)state;
    const char *r = rm_look_get(&w->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Title")) return w->title;
    if (rm_ieq(prop, "DockSide")) return DSIDES[w->side];
    if (rm_ieq(prop, "AutoHide")) return rm_tf(w->autohide);
    if (rm_ieq(prop, "DockSize")) return rad_str(w->size);
    if (rm_ieq(prop, "IsClosed")) return rm_tf(w->closed);
    return NULL;
}

/* title bar buttons: 0 close, 1 pin (auto-hide), 2 menu */
static int dw_btn_at(rf_handle h, int x, int y) {
    RECT r;
    int th = dock_title_h(h), bw = rm_px(h, 22);
    GetClientRect((HWND)rf_hwnd(h), &r);
    if (y >= th) return -2;
    if (x >= r.right - bw) return 0;
    if (x >= r.right - 2 * bw) return 1;
    if (x >= r.right - 3 * bw) return 2;
    return -1;
}

static void dw_close(rf_handle h, RmDockWin *w) {
    rf_handle p = dock_panel_of(h);
    w->closed = 1;
    w->slid = 0;
    if (p) {
        dock_layout(p);
        rm_raise_item(p, "WindowClosed", rf_name(h), -1);
    } else {
        rf_prop_set(h, "Visible", "False");
    }
}

static void dw_menu(rf_handle h, RmDockWin *w) {
    static const char *const items = "[{\"Text\":\"Dock Left\",\"Name\":\"Left\"},{\"Text\":\"Dock Right\",\"Name\":\"Right\"},"
        "{\"Text\":\"Dock Top\",\"Name\":\"Top\"},{\"Text\":\"Dock Bottom\",\"Name\":\"Bottom\"},{\"Text\":\"Document\",\"Name\":\"Fill\"},"
        "{\"Text\":\"Float\",\"Name\":\"Float\"},{\"Text\":\"-\"},{\"Text\":\"Auto Hide\",\"Name\":\"AutoHide\"},{\"Text\":\"-\"},"
        "{\"Text\":\"Close\",\"Name\":\"Close\"}]";
    int n = 0, s;
    rm_item *it = rm_items_parse(items, &n), *pick;
    RECT r;
    GetWindowRect((HWND)rf_hwnd(h), &r);
    if (it) {
        rm_item *ah = rm_items_find(it, n, "AutoHide");
        if (ah) ah->checked = w->autohide;
        for (s = 0; s < 6; s++) {
            rm_item *x = rm_items_find(it, n, DSIDES[s]);
            if (x) x->checked = !w->autohide && w->side == s;
        }
    }
    pick = rm_popup_menu(h, it, n, r.right - rm_px(h, 66), r.top + dock_title_h(h));
    if (pick) {
        if (rm_ieq(pick->name, "Close")) dw_close(h, w);
        else if (rm_ieq(pick->name, "AutoHide")) { w->autohide = !w->autohide; w->slid = 0; dw_relayout(h); }
        else {
            for (s = 0; s < 6; s++) if (rm_ieq(pick->name, DSIDES[s])) w->side = s;
            w->autohide = 0;
            dw_relayout(h);
        }
    }
    rm_items_free(it, n);
}

static int RF_CALL dw_message(rf_handle h, void *state, unsigned msg, uintptr_t wp, intptr_t l, intptr_t *res) {
    RmDockWin *w = (RmDockWin *)state;
    int x = GET_X_LPARAM(l), y = GET_Y_LPARAM(l), b;
    rf_handle panel;
    if (!w) return 0;
    switch (msg) {
    case WM_LBUTTONDOWN:
        panel = dock_panel_of(h);
        if (panel) dock_activate(panel, h);
        b = dw_btn_at(h, x, y);
        if (b == 0) { dw_close(h, w); *res = 0; return 1; }
        if (b == 1) { w->autohide = !w->autohide; w->slid = 0; dw_relayout(h); *res = 0; return 1; }
        if (b == 2) { dw_menu(h, w); *res = 0; return 1; }
        if (b == -1 && w->side == DS_FLOAT) {   /* move a floating window by its title */
            w->drag = 1;
            w->dragx = x;
            w->dragy = y;
            SetCapture((HWND)rf_hwnd(h));
            *res = 0;
            return 1;
        }
        break;
    case WM_RBUTTONUP:
        if (y < dock_title_h(h)) { dw_menu(h, w); *res = 0; return 1; }
        break;
    case WM_LBUTTONDBLCLK:
        if (y < dock_title_h(h)) {      /* double-click the title: float <-> dock */
            w->side = w->side == DS_FLOAT ? DS_LEFT : DS_FLOAT;
            w->autohide = 0;
            dw_relayout(h);
            *res = 0;
            return 1;
        }
        break;
    case WM_MOUSEMOVE:
        if (w->drag) {
            RECT r;
            HWND hw = (HWND)rf_hwnd(h);
            POINT pt;
            GetWindowRect(hw, &r);
            pt.x = r.left;
            pt.y = r.top;
            ScreenToClient(GetParent(hw), &pt);
            w->fx = rm_unpx(h, pt.x + x - w->dragx);
            w->fy = rm_unpx(h, pt.y + y - w->dragy);
            if (w->fy < 0) w->fy = 0;
            dw_relayout(h);
            *res = 0;
            return 1;
        }
        b = dw_btn_at(h, x, y);
        if (b != w->hot_btn) { w->hot_btn = b; rf_invalidate(h); }
        break;
    case WM_LBUTTONUP: case WM_CAPTURECHANGED:
        if (w->drag) { w->drag = 0; if (msg == WM_LBUTTONUP) ReleaseCapture(); *res = 0; return 1; }
        break;
    case WM_MOUSELEAVE:
        if (w->hot_btn != -1) { w->hot_btn = -1; rf_invalidate(h); }
        break;
    default: break;
    }
    (void)wp;
    return 0;
}

static void RF_CALL dw_paint(rf_handle h, void *state, const rf_paint *p) {
    RmDockWin *w = (RmDockWin *)state;
    const rf_theme *t = rm_look_theme(&w->look, p);
    unsigned accent = rm_look_accent(&w->look, t), back = own_back(p, t, t->window);
    unsigned head = w->active ? accent : rf_blend(back, t->window_text, 0.07), fg = w->active ? rm_on(accent) : t->window_text;
    int th = dock_title_h(h), bw = rf_px(p, 22), i;
    rm_fill(p, 0, 0, p->width, p->height, back);
    rf_draw_rect(p, 0, 0, p->width, p->height, RF_NONE, w->side == DS_FLOAT ? accent : rf_blend(t->border, back, 0.3), 1, 0);
    rm_fill(p, 1, 1, p->width - 2, th - 1, head);
    {
        HGDIOBJ o = rm_font_push(p, 1.0, 1);
        rf_draw_text(p, *w->title ? w->title : p->text, rf_px(p, 8), 0, p->width - 3 * bw - rf_px(p, 10), th, fg,
                     RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        rm_font_pop(p, o);
    }
    for (i = 0; i < 3; i++) {
        int x = p->width - (i + 1) * bw, cy = th / 2;
        if (w->hot_btn == i) rf_draw_rect(p, x + 2, 3, bw - 4, th - 6, rf_blend(head, fg, 0.2), RF_NONE, 0, rf_px(p, 2));
        if (i == 0) rm_cross(p, x + bw / 2.0, cy, rf_px(p, 8), fg, rf_px(p, 1.3));
        else if (i == 1) {          /* pin: upright when docked, sideways when auto-hidden */
            if (w->autohide) {
                double a[4];
                rf_draw_rect(p, x + bw / 2 - rf_px(p, 2), cy - rf_px(p, 4), rf_px(p, 6), rf_px(p, 8), RF_NONE, fg, rf_px(p, 1.2), 0);
                a[0] = x + rf_px(p, 4); a[1] = cy; a[2] = x + bw / 2.0 - rf_px(p, 2); a[3] = cy;
                rm_lines(p, a, 2, fg, rf_px(p, 1.2));
            } else {
                double a[4];
                rf_draw_rect(p, x + bw / 2 - rf_px(p, 4), cy - rf_px(p, 6), rf_px(p, 8), rf_px(p, 6), RF_NONE, fg, rf_px(p, 1.2), 0);
                a[0] = x + bw / 2.0; a[1] = cy; a[2] = x + bw / 2.0; a[3] = cy + rf_px(p, 5);
                rm_lines(p, a, 2, fg, rf_px(p, 1.2));
            }
        } else rm_chevron(p, x + bw / 2.0, cy, rf_px(p, 8), RM_DOWN, fg, rf_px(p, 1.3));
    }
    rf_set_child_back(h, back);
}

/* ================================================================== registration */
RF_MODULE(rm_panels) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmPanel";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_CONTAINER;
    k.create = pn_create; k.destroy = pn_destroy; k.set = pn_set; k.get = pn_get; k.paint = pn_paint;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Title,CornerRadius,Shadow,GradientTo,BorderColor";
    k.events = "Click";
    k.methods = "";
    rf_register_class(&k);
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmGroupPanel";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_CONTAINER | RF_CLASS_FOCUSABLE;
    k.create = gp_create; k.destroy = gp_destroy; k.set = gp_set; k.get = gp_get; k.invoke = gp_invoke;
    k.paint = gp_paint; k.message = gp_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Title,Collapsed";
    k.events = "CollapsedChanged";
    k.methods = "Toggle,Expand,Collapse";
    rf_register_class(&k);
    k.name = "RmTabStrip";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_CONTAINER | RF_CLASS_FOCUSABLE;
    k.create = ts_create; k.destroy = ts_destroy; k.set = ts_set; k.get = ts_get; k.invoke = ts_invoke;
    k.paint = ts_paint; k.message = ts_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,TabPages,SelectedIndex,SelectedTab,TabCount,TabPosition,Closable,AutoClose";
    k.events = "SelectedIndexChanged,TabClosing";
    k.methods = "AddTab,RemoveTab,TabCaption,SelectTab";
    rf_register_class(&k);
    k.name = "RmNavigationPane";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_CONTAINER | RF_CLASS_FOCUSABLE;
    k.create = nv_create; k.destroy = nv_destroy; k.set = nv_set; k.get = nv_get; k.invoke = NULL;
    k.paint = nv_paint; k.message = nv_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Pages,SelectedIndex,SelectedPage,PageCount";
    k.events = "SelectedIndexChanged";
    k.methods = "";
    rf_register_class(&k);
    k.name = "RmDockPanel";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_CONTAINER;
    k.create = dk_create; k.destroy = dk_destroy; k.set = dk_set; k.get = dk_get; k.invoke = dk_invoke;
    k.paint = dk_paint; k.message = dk_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Layout,ActiveWindow";
    k.events = "WindowClosed,ActiveWindowChanged";
    k.methods = "SaveLayout,LoadLayout,ShowWindow,CloseWindow,DockWindow,Refresh";
    rf_register_class(&k);
    k.name = "RmDockWindow";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_CONTAINER;
    k.create = dw_create; k.destroy = dw_destroy; k.set = dw_set; k.get = dw_get; k.invoke = NULL;
    k.paint = dw_paint; k.message = dw_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Title,DockSide,AutoHide,DockSize,IsClosed";
    k.events = "Click";
    k.methods = "";
    rf_register_class(&k);
}
