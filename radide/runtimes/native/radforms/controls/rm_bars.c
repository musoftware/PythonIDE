/* RAD Modern bars: RmSideBar (vertical side bar with groups and items, badges, icon-only collapsed
 * mode, Outlook / VS Code style) and RmStatusBar (panels: text, progress, zoom; spring panels).
 *
 * RF_CLASSES: RmSideBar RmStatusBar
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <windowsx.h>

#define WM_RM_LATER (WM_APP + 0x5241)

/* ================================================================== RmSideBar */
typedef struct { rm_item *it; int group, gi, ii; } SbRow;     /* gi: top-level index, ii: index inside the group */

typedef struct {
    rm_look look;
    rm_item *items;
    int n, collapsed, full_w, hot, sel_row, scroll, show_toggle;
    char *src, *selected;
    SbRow rows[256];
    int nrows;
    unsigned char closed[64];   /* collapsed groups */
} RmSideBar;

static int sb_row_h(rf_handle h) { return rm_px(h, 34); }
static int sb_group_h(rf_handle h) { return rm_px(h, 28); }
static int sb_top(rf_handle h, RmSideBar *s) { return s->show_toggle ? rm_px(h, 40) : rm_px(h, 4); }

static void sb_rows(RmSideBar *s) {
    int i, k;
    s->nrows = 0;
    for (i = 0; i < s->n && s->nrows < 256; i++) {
        rm_item *it = &s->items[i];
        if (it->n) {
            SbRow *r = &s->rows[s->nrows++];
            r->it = it; r->group = 1; r->gi = i; r->ii = -1;
            if (i < 64 && s->closed[i] && !s->collapsed) continue;
            for (k = 0; k < it->n && s->nrows < 256; k++) {
                SbRow *c = &s->rows[s->nrows++];
                c->it = &it->items[k]; c->group = 0; c->gi = i; c->ii = k;
            }
        } else {
            SbRow *r = &s->rows[s->nrows++];
            r->it = it; r->group = 0; r->gi = i; r->ii = -1;
        }
    }
    s->sel_row = -1;
    for (i = 0; i < s->nrows; i++)
        if (!s->rows[i].group && *s->selected && rm_ieq(s->rows[i].it->name, s->selected)) s->sel_row = i;
}

static int sb_row_y(rf_handle h, RmSideBar *s, int row) {
    int y = sb_top(h, s) - s->scroll, i;
    for (i = 0; i < row; i++) y += s->rows[i].group ? (s->collapsed ? rm_px(h, 9) : sb_group_h(h)) : sb_row_h(h);
    return y;
}

static int sb_hit(rf_handle h, RmSideBar *s, int y) {
    int i, top = sb_top(h, s) - s->scroll;
    if (s->show_toggle && y < rm_px(h, 40) && y >= 0) return -2;      /* the toggle button */
    for (i = 0; i < s->nrows; i++) {
        int hh = s->rows[i].group ? (s->collapsed ? rm_px(h, 9) : sb_group_h(h)) : sb_row_h(h);
        if (y >= top && y < top + hh) return i;
        top += hh;
    }
    return -1;
}

static int RF_CALL sb_create(rf_handle h, void **state) {
    RmSideBar *s = (RmSideBar *)calloc(1, sizeof *s);
    (void)h;
    if (!s) return 0;
    s->hot = s->sel_row = -1;
    s->show_toggle = 1;
    s->src = rm_strdup("");
    s->selected = rm_strdup("");
    *state = s;
    return 1;
}

static void RF_CALL sb_destroy(rf_handle h, void *state) {
    RmSideBar *s = (RmSideBar *)state;
    (void)h;
    if (!s) return;
    rm_items_free(s->items, s->n);
    free(s->src);
    free(s->selected);
    free(s);
}

static void sb_apply_collapse(rf_handle h, RmSideBar *s) {
    HWND hw = (HWND)rf_hwnd(h);
    RECT r;
    if (!hw) return;
    GetClientRect(hw, &r);
    if (s->collapsed) {
        if (r.right > rm_px(h, 60)) s->full_w = rm_unpx(h, r.right);
        rf_prop_set_num(h, "Width", 48);
    } else if (s->full_w > 0) {
        rf_prop_set_num(h, "Width", s->full_w);
    }
    sb_rows(s);
    rf_invalidate(h);
}

static void sb_collapse(rf_handle h, RmSideBar *s, int on) {
    if (on == s->collapsed) return;
    s->collapsed = on;
    sb_apply_collapse(h, s);
    rf_raise(h, "CollapsedChanged", "");
}

static void sb_select(rf_handle h, RmSideBar *s, int row, int notify) {
    SbRow *r;
    if (row < 0 || row >= s->nrows || s->rows[row].group || !s->rows[row].it->enabled) return;
    r = &s->rows[row];
    rm_setstr(&s->selected, r->it->name);
    s->sel_row = row;
    rf_invalidate(h);
    if (notify) rm_raise_item(h, "ItemClick", r->it->name, r->ii >= 0 ? r->ii : r->gi);
}

static int RF_CALL sb_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmSideBar *s = (RmSideBar *)state;
    if (rm_look_set(&s->look, prop, v)) return 1;
    if (rm_ieq(prop, "Items")) {
        rm_setstr(&s->src, v);
        rm_items_free(s->items, s->n);
        s->items = rm_items_parse(v, &s->n);
        memset(s->closed, 0, sizeof s->closed);
        {
            int i;
            for (i = 0; i < s->n && i < 64; i++)
                if (s->items[i].n && rm_ieq(s->items[i].kind, "Collapsed")) s->closed[i] = 1;
        }
        sb_rows(s);
        return 1;
    }
    if (rm_ieq(prop, "SelectedItem")) { rm_setstr(&s->selected, v); sb_rows(s); rf_invalidate(h); return 1; }
    if (rm_ieq(prop, "ShowToggle")) { s->show_toggle = rm_bool(v); return 1; }
    if (rm_ieq(prop, "Collapsed")) {
        int on = rm_bool(v);
        HWND hw = (HWND)rf_hwnd(h);
        if (hw && !IsWindowVisible(GetAncestor(hw, GA_ROOT))) { s->collapsed = on; PostMessageW(hw, WM_RM_LATER, 0, 0); return 1; }
        sb_collapse(h, s, on);
        return 1;
    }
    return 0;
}

static const char *RF_CALL sb_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmSideBar *s = (RmSideBar *)state;
    const char *r = rm_look_get(&s->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Items")) return s->src;
    if (rm_ieq(prop, "SelectedItem")) return s->selected;
    if (rm_ieq(prop, "Collapsed")) return rm_tf(s->collapsed);
    if (rm_ieq(prop, "ShowToggle")) return rm_tf(s->show_toggle);
    return NULL;
}

static const char *RF_CALL sb_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmSideBar *s = (RmSideBar *)state;
    if (rm_ieq(m, "SelectItem")) {
        int i;
        for (i = 0; i < s->nrows; i++)
            if (!s->rows[i].group && rm_ieq(s->rows[i].it->name, rm_arg(args, 0))) sb_select(h, s, i, 0);
        return "";
    }
    if (rm_ieq(m, "SetBadge")) {
        rm_item *it = rm_items_find(s->items, s->n, rm_arg(args, 0));
        if (it) { it->count = rm_int(rm_arg(args, 1)); rf_invalidate(h); }
        return "";
    }
    if (rm_ieq(m, "Toggle")) { sb_collapse(h, s, !s->collapsed); return ""; }
    if (rm_ieq(m, "SetItemText")) {
        rm_item *it = rm_items_find(s->items, s->n, rm_arg(args, 0));
        if (it) { rm_setstr(&it->text, rm_arg(args, 1)); rf_invalidate(h); }
        return "";
    }
    return NULL;
}

static int RF_CALL sb_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmSideBar *s = (RmSideBar *)state;
    int row;
    if (!s) return 0;
    switch (msg) {
    case WM_RM_LATER:
        if (s->collapsed) sb_apply_collapse(h, s);
        *res = 0;
        return 1;
    case WM_LBUTTONDOWN:
        SetFocus((HWND)rf_hwnd(h));
        row = sb_hit(h, s, GET_Y_LPARAM(l));
        if (row == -2) sb_collapse(h, s, !s->collapsed);
        else if (row >= 0 && s->rows[row].group && !s->collapsed && s->rows[row].gi < 64) {
            s->closed[s->rows[row].gi] = !s->closed[s->rows[row].gi];
            sb_rows(s);
            rf_invalidate(h);
        } else if (row >= 0) sb_select(h, s, row, 1);
        *res = 0;
        return 1;
    case WM_MOUSEMOVE:
        row = sb_hit(h, s, GET_Y_LPARAM(l));
        if (row != s->hot) { s->hot = row; rf_invalidate(h); }
        break;
    case WM_MOUSELEAVE:
        s->hot = -1;
        rf_invalidate(h);
        break;
    case WM_MOUSEWHEEL: {
        RECT r;
        int total = sb_row_y(h, s, s->nrows) + s->scroll;
        GetClientRect((HWND)rf_hwnd(h), &r);
        s->scroll -= GET_WHEEL_DELTA_WPARAM(w) / 120 * sb_row_h(h);
        if (s->scroll > total - r.bottom) s->scroll = total - r.bottom;
        if (s->scroll < 0) s->scroll = 0;
        rf_invalidate(h);
        *res = 0;
        return 1;
    }
    case WM_KEYDOWN: {
        int r = s->sel_row, d = w == VK_DOWN ? 1 : w == VK_UP ? -1 : 0;
        if (d) {
            for (r += d; r >= 0 && r < s->nrows && s->rows[r].group; r += d) {}
            if (r >= 0 && r < s->nrows) sb_select(h, s, r, 0);
            *res = 0;
            return 1;
        }
        if ((w == VK_RETURN || w == VK_SPACE) && s->sel_row >= 0) { sb_select(h, s, s->sel_row, 1); *res = 0; return 1; }
        break;
    }
    case WM_GETDLGCODE:
        *res = DLGC_WANTARROWS;
        return 1;
    default: break;
    }
    return 0;
}

static void RF_CALL sb_paint(rf_handle h, void *state, const rf_paint *p) {
    RmSideBar *s = (RmSideBar *)state;
    const rf_theme *t = rm_look_theme(&s->look, p);
    unsigned accent = rm_look_accent(&s->look, t);
    unsigned back = p->has_back ? p->back : (t->dark ? rf_blend(t->window, 0, 0.25) : rf_blend(t->window, t->window_text, 0.035));
    unsigned fg = p->has_fore ? p->fore : t->window_text, dim = rf_blend(fg, back, 0.4);
    int i, rh = sb_row_h(h), isz = rf_px(p, 18), pad = rf_px(p, 14);
    rm_fill(p, 0, 0, p->width, p->height, back);
    rf_draw_line(p, p->width - 1, 0, p->width - 1, p->height, rf_blend(t->border, back, 0.5), 1);
    for (i = 0; i < s->nrows; i++) {
        SbRow *r = &s->rows[i];
        int y = sb_row_y(h, s, i);
        if (y > p->height) break;
        if (r->group) {
            if (s->collapsed) {
                rf_draw_line(p, rf_px(p, 10), y + rf_px(p, 4), p->width - rf_px(p, 10), y + rf_px(p, 4), rf_blend(t->border, back, 0.3), 1);
                continue;
            }
            {
                HGDIOBJ o = rm_font_push(p, 0.85, 2);
                int closed = r->gi < 64 && s->closed[r->gi];
                rm_chevron(p, pad + rf_px(p, 3), y + sb_group_h(h) / 2.0, rf_px(p, 7), closed ? RM_RIGHT : RM_DOWN, dim, rf_px(p, 1.3));
                rf_draw_text(p, r->it->text, pad + rf_px(p, 12), y, p->width - 2 * pad, sb_group_h(h), i == s->hot ? fg : dim,
                             RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
                rm_font_pop(p, o);
            }
            continue;
        }
        {
            int sel = i == s->sel_row, x = s->collapsed ? (p->width - isz) / 2 : pad + (r->ii >= 0 ? rf_px(p, 4) : 0);
            unsigned c = r->it->enabled ? fg : t->disabled_text;
            if (sel) rf_draw_rect(p, rf_px(p, 4), y + 2, p->width - rf_px(p, 9), rh - 4, rf_blend(back, accent, t->dark ? 0.35 : 0.16),
                                  RF_NONE, 0, rf_px(p, t->radius + 1));
            else if (i == s->hot) rf_draw_rect(p, rf_px(p, 4), y + 2, p->width - rf_px(p, 9), rh - 4,
                                               rf_blend(back, t->window_text, 0.07), RF_NONE, 0, rf_px(p, t->radius + 1));
            if (sel) rf_draw_rect(p, rf_px(p, 4), y + rh / 4, rf_px(p, 3), rh / 2, accent, RF_NONE, 0, 1);
            if (rm_has_icon(r->it->image)) rm_icon(p, r->it->image, x, y + (rh - isz) / 2, isz, isz, sel ? accent : c);
            else if (s->collapsed) {
                char first[8] = {0};
                const char *tx = r->it->text;
                int k = 0;
                if (*tx) { first[k++] = *tx++; while (*tx && ((unsigned char)*tx & 0xC0) == 0x80 && k < 6) first[k++] = *tx++; }
                rf_draw_text(p, first, 0, y, p->width, rh, sel ? accent : c, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
            }
            if (!s->collapsed) {
                int tx = x + (rm_has_icon(r->it->image) ? isz + rf_px(p, 10) : 0);
                HGDIOBJ o = sel ? rm_font_push(p, 1.0, 1) : NULL;
                rf_draw_text(p, r->it->text, tx, y, p->width - tx - pad - (r->it->count ? rf_px(p, 30) : 0), rh, c,
                             RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
                if (o) rm_font_pop(p, o);
            }
            if (r->it->count) {
                const char *num = rad_str(r->it->count);
                HGDIOBJ o = rm_font_push(p, 0.8, 2);
                int bw = rm_text_w(p, num) + rf_px(p, 10), bh = rf_px(p, 16);
                int bx = s->collapsed ? p->width - bw - rf_px(p, 3) : p->width - pad - bw, by = s->collapsed ? y + rf_px(p, 2) : y + (rh - bh) / 2;
                rf_draw_rect(p, bx, by, bw, bh, accent, RF_NONE, 0, bh / 2);
                rf_draw_text(p, num, bx, by, bw, bh, rm_on(accent), RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
                rm_font_pop(p, o);
            }
            if (p->focused && sel) rf_draw_rect(p, rf_px(p, 4), y + 2, p->width - rf_px(p, 9), rh - 4, RF_NONE, accent, 1, rf_px(p, 3));
        }
    }
    if (s->show_toggle) {       /* drawn last: stays on top when scrolled */
        int th = rf_px(p, 40), x = s->collapsed ? (p->width - isz) / 2 : pad;
        rm_fill(p, 0, 0, p->width - 1, th, back);
        if (s->hot == -2) rf_draw_rect(p, x - rf_px(p, 6), rf_px(p, 5), isz + rf_px(p, 12), th - rf_px(p, 10),
                                       rf_blend(back, t->window_text, 0.08), RF_NONE, 0, rf_px(p, 3));
        rm_icon(p, "menu", x, (th - isz) / 2, isz, isz, fg);
        if (!s->collapsed && *p->text) {
            HGDIOBJ o = rm_font_push(p, 1.05, 1);
            rf_draw_text(p, p->text, x + isz + rf_px(p, 12), 0, p->width - x - isz - pad, th, fg, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
            rm_font_pop(p, o);
        }
    }
}

/* ================================================================== RmStatusBar */
enum { SP_TEXT, SP_PROGRESS, SP_ZOOM };
typedef struct {
    rm_look look;
    rm_item *panels;
    int n, hot, accent_bar;
    double *values;
    char *src;
} RmStatus;

static int RF_CALL st_create(rf_handle h, void **state) {
    RmStatus *s = (RmStatus *)calloc(1, sizeof *s);
    (void)h;
    if (!s) return 0;
    s->hot = -1;
    s->src = rm_strdup("");
    *state = s;
    return 1;
}

static void RF_CALL st_destroy(rf_handle h, void *state) {
    RmStatus *s = (RmStatus *)state;
    (void)h;
    if (!s) return;
    rm_items_free(s->panels, s->n);
    free(s->values);
    free(s->src);
    free(s);
}

static int st_kind(rm_item *it) {
    if (rm_ieq(it->kind, "Progress")) return SP_PROGRESS;
    if (rm_ieq(it->kind, "Zoom")) return SP_ZOOM;
    return SP_TEXT;
}

static void st_parse(RmStatus *s, const char *v) {
    int i;
    rm_items_free(s->panels, s->n);
    free(s->values);
    s->panels = rm_items_parse(v, &s->n);
    s->values = (double *)calloc((size_t)(s->n + 1), sizeof(double));
    for (i = 0; i < s->n && s->values; i++)
        s->values[i] = *s->panels[i].value ? rad_num(s->panels[i].value) : (st_kind(&s->panels[i]) == SP_ZOOM ? 100 : 0);
}

/* x ranges of the panels (device pixels): a Width of 0 = spring (shares the rest) */
static void st_geo(rf_handle h, RmStatus *s, int width, int *x0, int *x1) {
    int i, fixed = 0, springs = 0, x = 0, pad = rm_px(h, 4);
    for (i = 0; i < s->n; i++) {
        int w = s->panels[i].width;
        if (w <= 0 && st_kind(&s->panels[i]) == SP_ZOOM) w = 160;
        if (w <= 0 && st_kind(&s->panels[i]) == SP_PROGRESS) w = 120;
        if (w > 0) fixed += rm_px(h, w);
        else springs++;
    }
    for (i = 0; i < s->n; i++) {
        int w = s->panels[i].width;
        if (w <= 0 && st_kind(&s->panels[i]) == SP_ZOOM) w = 160;
        if (w <= 0 && st_kind(&s->panels[i]) == SP_PROGRESS) w = 120;
        w = w > 0 ? rm_px(h, w) : (springs ? (width - fixed - pad) / springs : 0);
        if (w < 0) w = 0;
        x0[i] = x;
        x1[i] = x + w;
        x += w;
    }
}

static int st_hit(rf_handle h, RmStatus *s, int x) {
    int x0[64], x1[64], i;
    RECT r;
    GetClientRect((HWND)rf_hwnd(h), &r);
    if (s->n > 64) return -1;
    st_geo(h, s, r.right, x0, x1);
    for (i = 0; i < s->n; i++)
        if (x >= x0[i] && x < x1[i]) return i;
    return -1;
}

static int RF_CALL st_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmStatus *s = (RmStatus *)state;
    if (rm_look_set(&s->look, prop, v)) return 1;
    if (rm_ieq(prop, "Panels") || rm_ieq(prop, "Items")) { rm_setstr(&s->src, v); st_parse(s, v); return 1; }
    if (rm_ieq(prop, "AccentBar")) { s->accent_bar = rm_bool(v); return 1; }
    if (rm_ieq(prop, "Text") && s->n > 0) { rm_setstr(&s->panels[0].text, v); rf_invalidate(h); return 0; }
    return 0;
}

static const char *RF_CALL st_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmStatus *s = (RmStatus *)state;
    const char *r = rm_look_get(&s->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Panels") || rm_ieq(prop, "Items")) return rm_items_json(s->panels, s->n);
    if (rm_ieq(prop, "AccentBar")) return rm_tf(s->accent_bar);
    if (rm_ieq(prop, "PanelCount")) return rad_str(s->n);
    return NULL;
}

static int st_index(RmStatus *s, const char *a) {
    int i;
    for (i = 0; i < s->n; i++)
        if (rm_ieq(s->panels[i].name, a)) return i;
    return rm_int(a);
}

static const char *RF_CALL st_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmStatus *s = (RmStatus *)state;
    int i = st_index(s, rm_arg(args, 0));
    if (rm_ieq(m, "SetPanelText") && i >= 0 && i < s->n) { rm_setstr(&s->panels[i].text, rm_arg(args, 1)); rf_invalidate(h); return ""; }
    if (rm_ieq(m, "GetPanelText")) return i >= 0 && i < s->n ? s->panels[i].text : "";
    if (rm_ieq(m, "SetPanelValue") && i >= 0 && i < s->n) { s->values[i] = rad_num(rm_arg(args, 1)); rf_invalidate(h); return ""; }
    if (rm_ieq(m, "GetPanelValue")) return i >= 0 && i < s->n ? rad_str(s->values[i]) : "0";
    return NULL;
}

static int RF_CALL st_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmStatus *s = (RmStatus *)state;
    int i;
    if (!s) return 0;
    switch (msg) {
    case WM_LBUTTONDOWN:
        i = st_hit(h, s, GET_X_LPARAM(l));
        if (i >= 0 && st_kind(&s->panels[i]) == SP_ZOOM) {      /* - / + buttons and the track */
            int x0[64], x1[64], x = GET_X_LPARAM(l), bw = rm_px(h, 18);
            RECT r;
            double v = s->values[i];
            GetClientRect((HWND)rf_hwnd(h), &r);
            st_geo(h, s, r.right, x0, x1);
            if (x < x0[i] + bw) v -= 10;
            else if (x >= x1[i] - bw - rm_px(h, 40) && x < x1[i] - rm_px(h, 40)) v += 10;
            else if (x < x1[i] - rm_px(h, 40)) {
                int t0 = x0[i] + bw, t1 = x1[i] - bw - rm_px(h, 40);
                v = 10 + (x - t0) * 390.0 / (t1 - t0 > 1 ? t1 - t0 : 1);
            }
            if (v < 10) v = 10;
            if (v > 400) v = 400;
            s->values[i] = (double)(int)(v + 0.5);
            rf_invalidate(h);
            rf_raise(h, "ValueChanged", rad_str(s->values[i]));
        }
        if (i >= 0) rm_raise_item(h, "PanelClick", s->panels[i].name, i);
        *res = 0;
        return 1;
    case WM_MOUSEMOVE:
        i = st_hit(h, s, GET_X_LPARAM(l));
        if (i != s->hot) { s->hot = i; rf_invalidate(h); }
        break;
    case WM_MOUSELEAVE:
        s->hot = -1;
        rf_invalidate(h);
        break;
    default: break;
    }
    (void)w;
    return 0;
}

static void RF_CALL st_paint(rf_handle h, void *state, const rf_paint *p) {
    RmStatus *s = (RmStatus *)state;
    const rf_theme *t = rm_look_theme(&s->look, p);
    unsigned accent = rm_look_accent(&s->look, t);
    unsigned back = p->has_back ? p->back : s->accent_bar ? accent : rf_blend(t->window, t->window_text, t->dark ? 0.05 : 0.04);
    unsigned fg = p->has_fore ? p->fore : s->accent_bar ? rm_on(accent) : t->window_text;
    int x0[64], x1[64], i, pad = rf_px(p, 8);
    rm_fill(p, 0, 0, p->width, p->height, back);
    if (!s->accent_bar) rf_draw_line(p, 0, 0, p->width, 0, rf_blend(t->border, back, 0.4), 1);
    if (s->n > 64) return;
    if (s->n == 0) {
        rf_draw_text(p, p->text, pad, 0, p->width - 2 * pad, p->height, fg, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        return;
    }
    st_geo(h, s, p->width, x0, x1);
    for (i = 0; i < s->n; i++) {
        rm_item *it = &s->panels[i];
        int w = x1[i] - x0[i], k = st_kind(it), x = x0[i];
        if (w <= 0) continue;
        if (i == s->hot) rm_fill(p, x, 1, w, p->height - 1, rf_blend(back, fg, 0.08));
        if (i > 0) rf_draw_line(p, x, rf_px(p, 5), x, p->height - rf_px(p, 5), rf_blend(back, fg, 0.25), 1);
        if (k == SP_PROGRESS) {
            int bh = rf_px(p, 6), bx = x + pad, bw = w - 2 * pad;
            double f = s->values[i] / 100.0;
            if (f < 0) f = 0;
            if (f > 1) f = 1;
            rf_draw_rect(p, bx, (p->height - bh) / 2, bw, bh, rf_blend(back, fg, 0.18), RF_NONE, 0, bh / 2);
            if (f > 0) rf_draw_rect(p, bx, (p->height - bh) / 2, (int)(bw * f) > bh ? (int)(bw * f) : bh, bh,
                                    s->accent_bar ? fg : accent, RF_NONE, 0, bh / 2);
        } else if (k == SP_ZOOM) {
            int bw = rf_px(p, 18), tx0 = x + bw, tx1 = x1[i] - bw - rf_px(p, 40), cy = p->height / 2;
            double f = (s->values[i] - 10) / 390.0;
            char pct[16];
            if (f < 0) f = 0;
            if (f > 1) f = 1;
            rf_draw_line(p, x + rf_px(p, 5), cy, x + bw - rf_px(p, 5), cy, fg, rf_px(p, 1.3));
            rf_draw_line(p, tx1 + rf_px(p, 5), cy, tx1 + bw - rf_px(p, 5), cy, fg, rf_px(p, 1.3));
            rf_draw_line(p, tx1 + bw / 2, cy - rf_px(p, 4), tx1 + bw / 2, cy + rf_px(p, 4), fg, rf_px(p, 1.3));
            rf_draw_line(p, tx0 + rf_px(p, 2), cy, tx1 - rf_px(p, 2), cy, rf_blend(back, fg, 0.4), 1);
            rf_draw_rect(p, tx0 + (int)((tx1 - tx0) * f) - rf_px(p, 3), cy - rf_px(p, 6), rf_px(p, 6), rf_px(p, 12), fg, RF_NONE, 0, rf_px(p, 2));
            snprintf(pct, sizeof pct, "%d%%", (int)s->values[i]);
            rf_draw_text(p, pct, tx1 + bw, 0, x1[i] - tx1 - bw - rf_px(p, 4), p->height, fg, RF_ALIGN_RIGHT | RF_ALIGN_VCENTER);
        } else {
            int tx = x + pad, isz = rf_px(p, 14);
            if (rm_has_icon(it->image)) { rm_icon(p, it->image, tx, (p->height - isz) / 2, isz, isz, fg); tx += isz + rf_px(p, 5); }
            rf_draw_text(p, it->text, tx, 0, x1[i] - tx - pad, p->height, fg, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        }
    }
}

RF_MODULE(rm_bars) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmSideBar";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.create = sb_create; k.destroy = sb_destroy; k.set = sb_set; k.get = sb_get; k.invoke = sb_invoke;
    k.paint = sb_paint; k.message = sb_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Items,SelectedItem,Collapsed,ShowToggle";
    k.events = "ItemClick,CollapsedChanged";
    k.methods = "SelectItem,SetBadge,SetItemText,Toggle";
    rf_register_class(&k);
    k.name = "RmStatusBar";
    k.flags = RF_CLASS_OWNERDRAW;
    k.create = st_create; k.destroy = st_destroy; k.set = st_set; k.get = st_get; k.invoke = st_invoke;
    k.paint = st_paint; k.message = st_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Panels,AccentBar,PanelCount";
    k.events = "PanelClick,ValueChanged";
    k.methods = "SetPanelText,GetPanelText,SetPanelValue,GetPanelValue";
    rf_register_class(&k);
}
