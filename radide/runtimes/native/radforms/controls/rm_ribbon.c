/* RAD Modern ribbon: RmRibbon - application button (+ optional application menu), quick access
 * toolbar, tabs, groups, large / small buttons, check (toggle) buttons, drop-down / split buttons,
 * combo items, separators, collapse to the tab row.
 *
 * Tabs (JSON): [{"Text":"Home","Groups":[{"Text":"Clipboard","Items":[
 *                 {"Text":"Paste","Name":"btnPaste","Image":"paste","Size":"Large"},
 *                 {"Text":"Bold","Name":"btnBold","Image":"bold","Kind":"Check"},
 *                 {"Text":"Font","Name":"cboFont","Kind":"Combo","Value":"Segoe UI","Items":[...]},
 *                 {"Text":"More","Name":"mnuMore","Kind":"DropDown","Items":[...]} ]}]}]
 * QuickAccess: "save;undo;redo" (names of items above, or images) or JSON items.
 * Events: ItemClick (rad_arg(0) = item name, rad_arg(1) = index inside its group), TabChanged.
 *
 * RF_CLASSES: RmRibbon
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <windowsx.h>

typedef struct {
    rm_look look;
    rm_item *tabs, *qat, *appmenu;
    int ntabs, nqat, napp, sel, collapsed, full_h, hot_tab, hot_app, hot_collapse;
    rm_item *hot, *pressed;
    char *src, *qsrc, *app_text, *appsrc;
    RECT app, tabr[32], collapse_btn;
} RmRibbon;

static int qat_h(rf_handle h, RmRibbon *r) { return r->nqat ? rm_px(h, 26) : 0; }
static int tab_h(rf_handle h) { return rm_px(h, 30); }
static int body_h(rf_handle h) { return rm_px(h, 96); }

static int RF_CALL rb_create(rf_handle h, void **state) {
    RmRibbon *r = (RmRibbon *)calloc(1, sizeof *r);
    (void)h;
    if (!r) return 0;
    r->hot_tab = -1;
    r->src = rm_strdup("");
    r->qsrc = rm_strdup("");
    r->appsrc = rm_strdup("");
    r->app_text = rm_strdup("File");
    *state = r;
    return 1;
}

static void RF_CALL rb_destroy(rf_handle h, void *state) {
    RmRibbon *r = (RmRibbon *)state;
    (void)h;
    if (!r) return;
    rm_items_free(r->tabs, r->ntabs);
    rm_items_free(r->qat, r->nqat);
    rm_items_free(r->appmenu, r->napp);
    free(r->src); free(r->qsrc); free(r->app_text); free(r->appsrc);
    free(r);
}

static void rb_apply_collapse(rf_handle h, RmRibbon *r) {
    HWND hw = (HWND)rf_hwnd(h);
    RECT cr;
    int small = qat_h(h, r) + tab_h(h);
    if (!hw) return;
    GetClientRect(hw, &cr);
    if (r->collapsed) {
        if (cr.bottom > small + rm_px(h, 4)) r->full_h = rm_unpx(h, cr.bottom);
        rf_prop_set_num(h, "Height", rm_unpx(h, small) + 1);
    } else {
        rf_prop_set_num(h, "Height", r->full_h > 0 ? r->full_h : rm_unpx(h, small + body_h(h)) + 1);
    }
    rf_invalidate(h);
}

static void rb_collapse(rf_handle h, RmRibbon *r, int on) {
    if (on == r->collapsed) return;
    r->collapsed = on;
    rb_apply_collapse(h, r);
    rf_raise(h, "CollapsedChanged", "");
}

static void rb_select(rf_handle h, RmRibbon *r, int i, int notify) {
    if (i < 0 || i >= r->ntabs || i == r->sel) return;
    r->sel = i;
    rf_invalidate(h);
    if (notify) rm_raise_item(h, "TabChanged", r->tabs[i].name, i);
}

#define WM_RM_LATER (WM_APP + 0x5241)

static int RF_CALL rb_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmRibbon *r = (RmRibbon *)state;
    if (rm_look_set(&r->look, prop, v)) return 1;
    if (rm_ieq(prop, "Tabs")) {
        rm_setstr(&r->src, v);
        rm_items_free(r->tabs, r->ntabs);
        r->tabs = rm_items_parse(v, &r->ntabs);
        if (r->sel >= r->ntabs) r->sel = 0;
        return 1;
    }
    if (rm_ieq(prop, "QuickAccess")) {
        rm_setstr(&r->qsrc, v);
        rm_items_free(r->qat, r->nqat);
        r->qat = rm_items_parse(v, &r->nqat);
        return 1;
    }
    if (rm_ieq(prop, "AppMenu")) {
        rm_setstr(&r->appsrc, v);
        rm_items_free(r->appmenu, r->napp);
        r->appmenu = rm_items_parse(v, &r->napp);
        return 1;
    }
    if (rm_ieq(prop, "AppButtonText")) { rm_setstr(&r->app_text, v); return 1; }
    if (rm_ieq(prop, "SelectedTab") || rm_ieq(prop, "SelectedIndex")) {
        int i;
        for (i = 0; i < r->ntabs; i++)
            if (rm_ieq(r->tabs[i].name, v) || rm_ieq(r->tabs[i].text, v)) { rb_select(h, r, i, 1); return 1; }
        rb_select(h, r, rm_int(v), 1);
        return 1;
    }
    if (rm_ieq(prop, "Collapsed")) {
        int on = rm_bool(v);
        HWND hw = (HWND)rf_hwnd(h);
        if (hw && !IsWindowVisible(GetAncestor(hw, GA_ROOT))) { r->collapsed = on; PostMessageW(hw, WM_RM_LATER, 0, 0); return 1; }
        rb_collapse(h, r, on);
        return 1;
    }
    return 0;
}

static const char *RF_CALL rb_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmRibbon *r = (RmRibbon *)state;
    const char *s = rm_look_get(&r->look, prop);
    (void)h;
    if (s) return s;
    if (rm_ieq(prop, "Tabs")) return rm_items_json(r->tabs, r->ntabs);
    if (rm_ieq(prop, "QuickAccess")) return r->qsrc;
    if (rm_ieq(prop, "AppMenu")) return r->appsrc;
    if (rm_ieq(prop, "AppButtonText")) return r->app_text;
    if (rm_ieq(prop, "SelectedTab") || rm_ieq(prop, "SelectedIndex")) return rad_str(r->sel);
    if (rm_ieq(prop, "Collapsed")) return rm_tf(r->collapsed);
    return NULL;
}

static rm_item *rb_find(RmRibbon *r, const char *name) {
    rm_item *it = rm_items_find(r->tabs, r->ntabs, name);
    return it ? it : rm_items_find(r->qat, r->nqat, name);
}

static const char *RF_CALL rb_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmRibbon *r = (RmRibbon *)state;
    rm_item *it = rb_find(r, rm_arg(args, 0));
    if (rm_ieq(m, "SetChecked")) {
        if (it) { it->checked = rm_bool(rm_arg(args, 1)); rf_invalidate(h); }
        return "";
    }
    if (rm_ieq(m, "GetChecked")) return rm_tf(it && it->checked);
    if (rm_ieq(m, "SetEnabled")) {
        if (it) { it->enabled = rm_bool(rm_arg(args, 1)); rf_invalidate(h); }
        return "";
    }
    if (rm_ieq(m, "SetItemText")) {
        if (it) { rm_setstr(&it->text, rm_arg(args, 1)); rf_invalidate(h); }
        return "";
    }
    if (rm_ieq(m, "SetComboText") || rm_ieq(m, "SetValue")) {
        if (it) { rm_setstr(&it->value, rm_arg(args, 1)); rf_invalidate(h); }
        return "";
    }
    if (rm_ieq(m, "GetValue")) return it ? it->value : "";
    if (rm_ieq(m, "SelectTab")) { rb_set(h, r, "SelectedTab", rm_arg(args, 0)); return ""; }
    if (rm_ieq(m, "Toggle")) { rb_collapse(h, r, !r->collapsed); return ""; }
    return NULL;
}

/* ------------------------------------------------------------------ layout (device pixels) */
static int text_w(HDC dc, const char *s) {
    SIZE sz;
    wchar_t *w = rm_wide(s);
    sz.cx = 0;
    if (w) GetTextExtentPoint32W(dc, w, (int)wcslen(w), &sz);
    free(w);
    return sz.cx;
}

static void rb_layout(rf_handle h, RmRibbon *r, HDC dc) {
    HWND hw = (HWND)rf_hwnd(h);
    RECT cr;
    int i, x, top = qat_h(h, r), th = tab_h(h), pad = rm_px(h, 6);
    HGDIOBJ of = SelectObject(dc, (HGDIOBJ)SendMessageW(hw, WM_GETFONT, 0, 0));
    GetClientRect(hw, &cr);
    for (i = 0, x = rm_px(h, 6); i < r->nqat; i++) {     /* quick access toolbar */
        rm_item *q = &r->qat[i];
        q->x = x; q->y = rm_px(h, 2); q->w = rm_px(h, 24); q->h = rm_px(h, 22);
        x += q->w + rm_px(h, 2);
    }
    {   /* application button + tabs */
        int aw = text_w(dc, r->app_text) + rm_px(h, 28);
        SetRect(&r->app, 0, top, *r->app_text ? aw : 0, top + th);
        x = r->app.right + rm_px(h, 4);
        for (i = 0; i < r->ntabs && i < 32; i++) {
            int w = text_w(dc, r->tabs[i].text) + rm_px(h, 28);
            SetRect(&r->tabr[i], x, top, x + w, top + th);
            x += w;
        }
        SetRect(&r->collapse_btn, cr.right - rm_px(h, 26), top + rm_px(h, 4), cr.right - rm_px(h, 4), top + th - rm_px(h, 4));
    }
    if (r->sel >= 0 && r->sel < r->ntabs) {
        rm_item *tab = &r->tabs[r->sel];
        int gy = top + th + rm_px(h, 3), gh = body_h(h) - rm_px(h, 6), label = rm_px(h, 18), gx = rm_px(h, 4);
        int g;
        for (g = 0; g < tab->n; g++) {
            rm_item *grp = &tab->items[g];
            int k = 0, colx = gx + pad, colw = 0, row = 0, small_h = rm_px(h, 24), large_w;
            grp->x = gx; grp->y = gy; grp->h = gh;
            while (k < grp->n) {
                rm_item *it = &grp->items[k];
                if (rm_ieq(it->text, "-") || rm_ieq(it->kind, "Separator")) {
                    if (row) { colx += colw + pad; colw = 0; row = 0; }
                    it->x = colx; it->y = gy + rm_px(h, 4); it->w = rm_px(h, 6); it->h = gh - label - rm_px(h, 8);
                    colx += it->w;
                    k++;
                    continue;
                }
                if (it->large) {
                    if (row) { colx += colw + pad; colw = 0; row = 0; }
                    large_w = text_w(dc, it->text) + rm_px(h, 12);
                    if (large_w < rm_px(h, 48)) large_w = rm_px(h, 48);
                    if (it->n && !rm_ieq(it->kind, "Combo") && large_w < rm_px(h, 56)) large_w = rm_px(h, 56);
                    it->x = colx; it->y = gy + rm_px(h, 2); it->w = large_w; it->h = gh - label - rm_px(h, 4);
                    colx += large_w + rm_px(h, 2);
                    k++;
                    continue;
                }
                {
                    int w = rm_px(h, 16 + 8 + 10) + text_w(dc, it->text) + (it->n ? rm_px(h, 12) : 0);
                    if (rm_ieq(it->kind, "Combo")) w = rm_px(h, it->width > 0 ? it->width : 130);
                    it->x = colx; it->y = gy + rm_px(h, 3) + row * small_h; it->w = w; it->h = small_h - rm_px(h, 2);
                    if (w > colw) colw = w;
                    row++;
                    if (row == 3) { colx += colw + rm_px(h, 2); colw = 0; row = 0; }
                    k++;
                }
            }
            if (row) colx += colw + rm_px(h, 2);
            /* small items of one column share the widest width */
            {
                int a = 0;
                while (a < grp->n) {
                    int b2 = a, mw = 0, j;
                    if (grp->items[a].large || rm_ieq(grp->items[a].text, "-")) { a++; continue; }
                    while (b2 < grp->n && !grp->items[b2].large && !rm_ieq(grp->items[b2].text, "-") && grp->items[b2].x == grp->items[a].x) b2++;
                    for (j = a; j < b2; j++) if (grp->items[j].w > mw) mw = grp->items[j].w;
                    for (j = a; j < b2; j++) grp->items[j].w = mw;
                    a = b2 > a ? b2 : a + 1;
                }
            }
            {
                int lw = text_w(dc, grp->text) + rm_px(h, 16);
                grp->w = colx - gx + pad - rm_px(h, 2);
                if (grp->w < lw) grp->w = lw;
            }
            gx += grp->w + rm_px(h, 3);
        }
    }
    SelectObject(dc, of);
}

static rm_item *rb_item_at(RmRibbon *r, int x, int y, int *gi, int *ii) {
    int g, k;
    *gi = *ii = -1;
    for (k = 0; k < r->nqat; k++) {
        rm_item *q = &r->qat[k];
        if (x >= q->x && x < q->x + q->w && y >= q->y && y < q->y + q->h) { *ii = k; return q; }
    }
    if (r->collapsed || r->sel < 0 || r->sel >= r->ntabs) return NULL;
    for (g = 0; g < r->tabs[r->sel].n; g++) {
        rm_item *grp = &r->tabs[r->sel].items[g];
        for (k = 0; k < grp->n; k++) {
            rm_item *it = &grp->items[k];
            if (rm_ieq(it->text, "-")) continue;
            if (x >= it->x && x < it->x + it->w && y >= it->y && y < it->y + it->h) { *gi = g; *ii = k; return it; }
        }
    }
    return NULL;
}

static void rb_relayout(rf_handle h, RmRibbon *r) {
    HWND hw = (HWND)rf_hwnd(h);
    HDC dc = GetDC(hw);
    rb_layout(h, r, dc);
    ReleaseDC(hw, dc);
}

static rm_item *rb_qat_target(RmRibbon *r, rm_item *q) {
    rm_item *t = rm_items_find(r->tabs, r->ntabs, q->name);
    return t ? t : q;
}

static void rb_activate(rf_handle h, RmRibbon *r, rm_item *it, int index) {
    HWND hw = (HWND)rf_hwnd(h);
    POINT pt;
    rm_item *target = it;
    if (!it || !it->enabled) return;
    if (it >= r->qat && it < r->qat + r->nqat) target = rb_qat_target(r, it);
    if (it->n || rm_ieq(it->kind, "Combo") || rm_ieq(it->kind, "DropDown")) {   /* drop-down: a popup menu */
        rm_item *pick;
        pt.x = it->x;
        pt.y = it->y + it->h;
        ClientToScreen(hw, &pt);
        pick = rm_popup_menu(h, it->items, it->n, pt.x, pt.y);
        if (pick) {
            if (rm_ieq(it->kind, "Combo")) {
                rm_setstr(&it->value, pick->text);
                rf_invalidate(h);
                rm_raise_item(h, "ItemClick", it->name, index);
            } else {
                rm_raise_item(h, "ItemClick", pick->name, (int)(pick - it->items));
            }
        }
        return;
    }
    if (rm_ieq(target->kind, "Check") || rm_ieq(target->kind, "Toggle")) { target->checked = !target->checked; rf_invalidate(h); }
    rm_raise_item(h, "ItemClick", target->name, index);
}

static int RF_CALL rb_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmRibbon *r = (RmRibbon *)state;
    int x = GET_X_LPARAM(l), y = GET_Y_LPARAM(l), gi, ii, i;
    POINT pt;
    rm_item *it;
    if (!r) return 0;
    pt.x = x;
    pt.y = y;
    switch (msg) {
    case WM_RM_LATER:
        if (r->collapsed) rb_apply_collapse(h, r);
        *res = 0;
        return 1;
    case WM_LBUTTONDOWN: case WM_LBUTTONDBLCLK:
        rb_relayout(h, r);
        if (PtInRect(&r->app, pt)) {
            if (r->napp) {
                rm_item *pick;
                POINT sp;
                sp.x = r->app.left;
                sp.y = r->app.bottom;
                ClientToScreen((HWND)rf_hwnd(h), &sp);
                pick = rm_popup_menu(h, r->appmenu, r->napp, sp.x, sp.y);
                if (pick) rm_raise_item(h, "ItemClick", pick->name, -1);
            } else {
                rm_raise_item(h, "ItemClick", "AppButton", -1);
            }
            *res = 0;
            return 1;
        }
        if (PtInRect(&r->collapse_btn, pt)) { rb_collapse(h, r, !r->collapsed); *res = 0; return 1; }
        for (i = 0; i < r->ntabs && i < 32; i++)
            if (PtInRect(&r->tabr[i], pt)) {
                if (msg == WM_LBUTTONDBLCLK) rb_collapse(h, r, !r->collapsed);
                else { rb_select(h, r, i, 1); if (r->collapsed) rb_collapse(h, r, 0); }
                *res = 0;
                return 1;
            }
        it = rb_item_at(r, x, y, &gi, &ii);
        if (it && it->enabled) { r->pressed = it; SetCapture((HWND)rf_hwnd(h)); rf_invalidate(h); }
        *res = 0;
        return 1;
    case WM_LBUTTONUP:
        if (r->pressed) {
            rm_item *p0 = r->pressed;
            r->pressed = NULL;
            ReleaseCapture();
            rb_relayout(h, r);
            it = rb_item_at(r, x, y, &gi, &ii);
            rf_invalidate(h);
            if (it == p0) rb_activate(h, r, it, ii);
        }
        *res = 0;
        return 1;
    case WM_CAPTURECHANGED:
        if (r->pressed) { r->pressed = NULL; rf_invalidate(h); }
        break;
    case WM_MOUSEMOVE: {
        int ht = -1, ha;
        it = rb_item_at(r, x, y, &gi, &ii);
        for (i = 0; i < r->ntabs && i < 32; i++)
            if (PtInRect(&r->tabr[i], pt)) ht = i;
        ha = PtInRect(&r->app, pt);
        if (it != r->hot || ht != r->hot_tab || ha != r->hot_app || PtInRect(&r->collapse_btn, pt) != r->hot_collapse) {
            r->hot = it;
            r->hot_tab = ht;
            r->hot_app = ha;
            r->hot_collapse = PtInRect(&r->collapse_btn, pt);
            rf_invalidate(h);
        }
        break;
    }
    case WM_MOUSELEAVE:
        r->hot = NULL;
        r->hot_tab = -1;
        r->hot_app = r->hot_collapse = 0;
        rf_invalidate(h);
        break;
    case WM_MOUSEWHEEL:
        if (r->ntabs) rb_select(h, r, (r->sel + (GET_WHEEL_DELTA_WPARAM(w) > 0 ? r->ntabs - 1 : 1)) % r->ntabs, 1);
        *res = 0;
        return 1;
    case WM_KEYDOWN:
        if (w == VK_RIGHT || w == VK_LEFT) {
            int d = (w == VK_RIGHT) != (rf_rtl(h) != 0) ? 1 : r->ntabs - 1;
            if (r->ntabs) rb_select(h, r, (r->sel + d) % r->ntabs, 1);
            *res = 0;
            return 1;
        }
        if (w == VK_F1 && (GetKeyState(VK_CONTROL) & 0x8000)) { rb_collapse(h, r, !r->collapsed); *res = 0; return 1; }
        break;
    case WM_GETDLGCODE:
        *res = DLGC_WANTARROWS;
        return 1;
    default: break;
    }
    return 0;
}

static void draw_item(const rf_paint *p, RmRibbon *r, const rf_theme *t, rm_item *it, unsigned body, unsigned fg, unsigned accent,
                      rm_item *target) {
    int hot = it == r->hot, pressed = it == r->pressed, isz;
    int checked = target && target->checked;
    unsigned c = it->enabled ? fg : t->disabled_text, fill = RF_NONE, border = RF_NONE;
    if (checked) { fill = rf_blend(body, accent, 0.2); border = rf_blend(body, accent, 0.5); }
    if (hot && it->enabled) { fill = rf_blend(body, accent, checked ? 0.3 : 0.12); border = rf_blend(body, accent, 0.45); }
    if (pressed) { fill = rf_blend(body, accent, 0.35); border = accent; }
    if (rm_ieq(it->kind, "Combo")) {
        int lw = rm_text_w(p, it->text) + rf_px(p, 6), bx = it->x + lw;
        rf_draw_text(p, it->text, it->x, it->y, lw, it->h, c, RF_ALIGN_LEFT | RF_ALIGN_VCENTER);
        rf_draw_rect(p, bx, it->y + 1, it->w - lw, it->h - 2, t->input, hot ? accent : t->border, 1, rf_px(p, 2));
        rf_draw_text(p, it->value, bx + rf_px(p, 5), it->y, it->w - lw - rf_px(p, 22), it->h, t->input_text,
                     RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        rm_chevron(p, it->x + it->w - rf_px(p, 9), it->y + it->h / 2.0, rf_px(p, 7), RM_DOWN, t->input_text, rf_px(p, 1.3));
        return;
    }
    if (fill != RF_NONE) rf_draw_rect(p, it->x, it->y, it->w, it->h, fill, border, 1, rf_px(p, t->radius + 1));
    if (it->large) {
        isz = rf_px(p, 32);
        rm_icon(p, *it->image ? it->image : "star", it->x + (it->w - isz) / 2, it->y + rf_px(p, 6), isz, isz, it->enabled ? accent : c);
        rf_draw_text(p, it->text, it->x + rf_px(p, 2), it->y + rf_px(p, 42), it->w - rf_px(p, 4), it->h - rf_px(p, 42), c,
                     RF_ALIGN_CENTER | RF_ALIGN_WRAP);
        if (it->n) rm_chevron(p, it->x + it->w / 2.0, it->y + it->h - rf_px(p, 6), rf_px(p, 7), RM_DOWN, c, rf_px(p, 1.2));
    } else {
        isz = rf_px(p, 16);
        if (rm_has_icon(it->image)) rm_icon(p, it->image, it->x + rf_px(p, 4), it->y + (it->h - isz) / 2, isz, isz, it->enabled ? accent : c);
        rf_draw_text(p, it->text, it->x + rf_px(p, 26), it->y, it->w - rf_px(p, 28) - (it->n ? rf_px(p, 12) : 0), it->h, c,
                     RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        if (it->n) rm_chevron(p, it->x + it->w - rf_px(p, 8), it->y + it->h / 2.0, rf_px(p, 7), RM_DOWN, c, rf_px(p, 1.2));
    }
}

static void RF_CALL rb_paint(rf_handle h, void *state, const rf_paint *p) {
    RmRibbon *r = (RmRibbon *)state;
    const rf_theme *t = rm_look_theme(&r->look, p);
    unsigned accent = rm_look_accent(&r->look, t);
    unsigned back = p->has_back ? p->back : (t->dark ? rf_blend(t->window, 0, 0.2) : rf_blend(t->window, t->window_text, 0.03));
    unsigned body = t->dark ? rf_blend(t->window, 0xFFFFFF, 0.05) : t->input, fg = p->has_fore ? p->fore : t->window_text;
    unsigned line = rf_blend(t->border, back, 0.45);
    int i, top = qat_h(h, r), th = tab_h(h);
    rb_layout(h, r, (HDC)p->hdc);
    rm_fill(p, 0, 0, p->width, p->height, back);
    for (i = 0; i < r->nqat; i++) {
        rm_item *q = &r->qat[i], *target = rb_qat_target(r, q);
        int isz = rf_px(p, 16);
        if (q == r->hot) rf_draw_rect(p, q->x, q->y, q->w, q->h, rf_blend(back, accent, 0.15), RF_NONE, 0, rf_px(p, 2));
        rm_icon(p, *target->image ? target->image : q->name, q->x + (q->w - isz) / 2, q->y + (q->h - isz) / 2, isz, isz, fg);
    }
    if (r->app.right > r->app.left) {
        unsigned af = r->hot_app ? rf_blend(accent, 0xFFFFFF, 0.15) : accent;
        rf_draw_rect(p, r->app.left, r->app.top + rf_px(p, 2), r->app.right - r->app.left, th - rf_px(p, 2), af, RF_NONE, 0,
                     rf_px(p, t->radius));
        rf_draw_text(p, r->app_text, r->app.left, r->app.top + rf_px(p, 2), r->app.right - r->app.left, th - rf_px(p, 2), rm_on(accent),
                     RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
    }
    if (!r->collapsed) {
        rm_fill(p, 0, top + th, p->width, p->height - top - th, body);
        rf_draw_line(p, 0, top + th, p->width, top + th, line, 1);
    }
    rf_draw_line(p, 0, p->height - 1, p->width, p->height - 1, line, 1);
    for (i = 0; i < r->ntabs && i < 32; i++) {
        RECT tr = r->tabr[i];
        rm_item *tab = &r->tabs[i];
        int sel = i == r->sel;
        unsigned tc = tab->has_color ? tab->color : (sel ? (t->dark ? fg : accent) : fg);
        if (sel && !r->collapsed) {
            rm_fill(p, tr.left, tr.top + rf_px(p, 3), tr.right - tr.left, tr.bottom - tr.top - rf_px(p, 3) + 1, body);
            rf_draw_line(p, tr.left, tr.top + rf_px(p, 3), tr.left, tr.bottom, line, 1);
            rf_draw_line(p, tr.right - 1, tr.top + rf_px(p, 3), tr.right - 1, tr.bottom, line, 1);
            rf_draw_line(p, tr.left, tr.top + rf_px(p, 3), tr.right, tr.top + rf_px(p, 3), line, 1);
        } else if (i == r->hot_tab) {
            rm_fill(p, tr.left + 1, tr.top + rf_px(p, 4), tr.right - tr.left - 2, tr.bottom - tr.top - rf_px(p, 5), rf_blend(back, accent, 0.08));
        }
        if (sel) rf_draw_rect(p, tr.left + rf_px(p, 10), tr.bottom - rf_px(p, 3), tr.right - tr.left - rf_px(p, 20), rf_px(p, 2), tab->has_color ? tab->color : accent,
                              RF_NONE, 0, 1);
        rf_draw_text(p, tab->text, tr.left, tr.top + rf_px(p, 2), tr.right - tr.left, tr.bottom - tr.top - rf_px(p, 2), tc,
                     RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
        if (sel && p->focused) rf_draw_rect(p, tr.left + 3, tr.top + rf_px(p, 6), tr.right - tr.left - 6, tr.bottom - tr.top - rf_px(p, 9),
                                            RF_NONE, rf_blend(body, accent, 0.5), 1, 2);
    }
    if (r->hot_collapse) rf_draw_rect(p, r->collapse_btn.left, r->collapse_btn.top, r->collapse_btn.right - r->collapse_btn.left,
                                      r->collapse_btn.bottom - r->collapse_btn.top, rf_blend(back, accent, 0.15), RF_NONE, 0, rf_px(p, 2));
    rm_chevron(p, (r->collapse_btn.left + r->collapse_btn.right) / 2.0, (r->collapse_btn.top + r->collapse_btn.bottom) / 2.0, rf_px(p, 8),
               r->collapsed ? RM_DOWN : RM_UP, fg, rf_px(p, 1.3));
    if (r->collapsed || r->sel < 0 || r->sel >= r->ntabs) return;
    {
        rm_item *tab = &r->tabs[r->sel];
        int g, k;
        for (g = 0; g < tab->n; g++) {
            rm_item *grp = &tab->items[g];
            int label = rf_px(p, 18);
            for (k = 0; k < grp->n; k++) {
                rm_item *it = &grp->items[k];
                if (rm_ieq(it->text, "-") || rm_ieq(it->kind, "Separator")) {
                    rf_draw_line(p, it->x + it->w / 2, it->y, it->x + it->w / 2, it->y + it->h, rf_blend(line, body, 0.3), 1);
                    continue;
                }
                draw_item(p, r, t, it, body, fg, accent, it);
            }
            rf_draw_text(p, grp->text, grp->x, grp->y + grp->h - label, grp->w, label, rf_blend(fg, body, 0.4),
                         RF_ALIGN_CENTER | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
            rf_draw_line(p, grp->x + grp->w + 1, grp->y + rf_px(p, 4), grp->x + grp->w + 1, grp->y + grp->h - rf_px(p, 4), line, 1);
        }
    }
}

RF_MODULE(rm_ribbon) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmRibbon";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.create = rb_create; k.destroy = rb_destroy; k.set = rb_set; k.get = rb_get; k.invoke = rb_invoke;
    k.paint = rb_paint; k.message = rb_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Tabs,QuickAccess,AppMenu,AppButtonText,SelectedTab,Collapsed";
    k.events = "ItemClick,TabChanged,CollapsedChanged";
    k.methods = "SetChecked,GetChecked,SetEnabled,SetItemText,SetValue,GetValue,SelectTab,Toggle";
    rf_register_class(&k);
}
