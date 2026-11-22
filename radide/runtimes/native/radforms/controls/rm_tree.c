/* RAD Modern tree: RmTreeView - images, check boxes (with parent / child propagation), connecting
 * lines, lazy nodes (NodeExpanding lets the program add the children), keyboard navigation.
 * Nodes (JSON): [{"Text":"Root","Name":"n1","Image":"folder","Expanded":true,"Nodes":[{"Text":"Child"}]},
 *                {"Text":"Lazy","Lazy":true}]  or a plain "a;b;c" list.
 *
 * RF_CLASSES: RmTreeView
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <windowsx.h>

typedef struct { rm_item *it; int depth; rm_item *parent; int last; unsigned lines; } TRow;

typedef struct {
    rm_look look;
    rm_item *nodes;
    int n, checkboxes, show_lines, top, hot, auto_name;
    char *selected;
    TRow *rows;
    int nrows, cap;
    char *src;
} RmTree;

static int tv_row_h(rf_handle h) { return rm_px(h, 26); }

static void tv_add_rows(RmTree *t, rm_item *items, int n, int depth, rm_item *parent, unsigned lines) {
    int i;
    for (i = 0; i < n; i++) {
        TRow *r;
        if (t->nrows >= t->cap) {
            int cap = t->cap ? t->cap * 2 : 64;
            TRow *nr = (TRow *)realloc(t->rows, sizeof(TRow) * cap);
            if (!nr) return;
            t->rows = nr;
            t->cap = cap;
        }
        r = &t->rows[t->nrows++];
        r->it = &items[i];
        r->depth = depth;
        r->parent = parent;
        r->last = i == n - 1;
        r->lines = lines;
        if (items[i].expanded && items[i].n && depth < 30)
            tv_add_rows(t, items[i].items, items[i].n, depth + 1, &items[i], lines | (r->last ? 0u : (1u << depth)));
    }
}

static void tv_rows(rf_handle h, RmTree *t) {
    SCROLLINFO si;
    RECT cr;
    t->nrows = 0;
    tv_add_rows(t, t->nodes, t->n, 0, NULL, 0);
    if (!rf_hwnd(h)) return;
    GetClientRect((HWND)rf_hwnd(h), &cr);
    if (t->top > t->nrows - 1) t->top = t->nrows - 1;
    if (t->top < 0) t->top = 0;
    memset(&si, 0, sizeof si);
    si.cbSize = sizeof si;
    si.fMask = SIF_RANGE | SIF_PAGE | SIF_POS;
    si.nMax = t->nrows > 0 ? t->nrows - 1 : 0;
    si.nPage = (UINT)(cr.bottom / tv_row_h(h));
    si.nPos = t->top;
    SetScrollInfo((HWND)rf_hwnd(h), SB_VERT, &si, TRUE);
    rf_invalidate(h);
}

static int tv_index(RmTree *t, const char *name) {
    int i;
    for (i = 0; i < t->nrows; i++)
        if (rm_ieq(t->rows[i].it->name, name)) return i;
    return -1;
}

static void name_all(RmTree *t, rm_item *items, int n) {      /* nodes without a Name get node1, node2 ... */
    int i;
    for (i = 0; i < n; i++) {
        if (!items[i].name || !*items[i].name) {
            char nm[32];
            snprintf(nm, sizeof nm, "node%d", ++t->auto_name);
            rm_setstr(&items[i].name, nm);
        }
        name_all(t, items[i].items, items[i].n);
    }
}

static int RF_CALL tv_create(rf_handle h, void **state) {
    RmTree *t = (RmTree *)calloc(1, sizeof *t);
    if (!t) return 0;
    t->show_lines = 1;
    t->hot = -1;
    t->selected = rm_strdup("");
    t->src = rm_strdup("");
    *state = t;
    if (rf_hwnd(h) && rf_theme_current()->dark) {
        typedef HRESULT(WINAPI * swt_t)(HWND, LPCWSTR, LPCWSTR);
        HMODULE m = LoadLibraryW(L"uxtheme.dll");
        swt_t fn = m ? (swt_t)(void *)GetProcAddress(m, "SetWindowTheme") : NULL;
        if (fn) fn((HWND)rf_hwnd(h), L"DarkMode_Explorer", NULL);
    }
    return 1;
}

static void RF_CALL tv_destroy(rf_handle h, void *state) {
    RmTree *t = (RmTree *)state;
    (void)h;
    if (!t) return;
    rm_items_free(t->nodes, t->n);
    free(t->rows);
    free(t->selected);
    free(t->src);
    free(t);
}

static void check_down(rm_item *it, int on) {
    int i;
    it->checked = on;
    for (i = 0; i < it->n; i++) check_down(&it->items[i], on);
}

static void tv_select(rf_handle h, RmTree *t, int row, int notify) {
    if (row < 0 || row >= t->nrows) return;
    rm_setstr(&t->selected, t->rows[row].it->name);
    if (row < t->top) t->top = row;
    {
        RECT cr;
        int vis;
        GetClientRect((HWND)rf_hwnd(h), &cr);
        vis = cr.bottom / tv_row_h(h);
        if (vis > 0 && row >= t->top + vis) t->top = row - vis + 1;
    }
    tv_rows(h, t);
    if (notify) {
        rm_raise_item(h, "NodeClick", t->rows[row].it->name, row);
        rf_raise(h, "SelectedIndexChanged", "");
    }
}

static void tv_expand(rf_handle h, RmTree *t, rm_item *it, int on) {
    char *keep;
    if (!it || on == it->expanded) return;
    if (on && (it->n || it->lazy)) {
        keep = rm_strdup(it->name);
        it->expanded = 1;
        if (it->lazy) { it->lazy = 0; rm_raise_item(h, "NodeExpanding", keep, -1); }
        else rm_raise_item(h, "NodeExpanding", keep, -1);
        free(keep);
    } else if (!on) {
        it->expanded = 0;
        rm_raise_item(h, "NodeCollapsed", it->name, -1);
    }
    tv_rows(h, t);
}

static int RF_CALL tv_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmTree *t = (RmTree *)state;
    if (rm_look_set(&t->look, prop, v)) return 1;
    if (rm_ieq(prop, "Nodes") || rm_ieq(prop, "Items")) {
        rm_setstr(&t->src, v);
        rm_items_free(t->nodes, t->n);
        t->nodes = rm_items_parse(v, &t->n);
        name_all(t, t->nodes, t->n);
        tv_rows(h, t);
        return 1;
    }
    if (rm_ieq(prop, "CheckBoxes")) { t->checkboxes = rm_bool(v); return 1; }
    if (rm_ieq(prop, "ShowLines")) { t->show_lines = rm_bool(v); return 1; }
    if (rm_ieq(prop, "SelectedNode")) { int i = tv_index(t, v); if (i >= 0) tv_select(h, t, i, 1); return 1; }
    return 0;
}

static void collect_checked(rm_item *items, int n, rm_list *out) {
    int i;
    for (i = 0; i < n; i++) {
        if (items[i].checked) rm_list_add(out, items[i].name, -1);
        collect_checked(items[i].items, items[i].n, out);
    }
}

static const char *RF_CALL tv_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmTree *t = (RmTree *)state;
    const char *r = rm_look_get(&t->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Nodes") || rm_ieq(prop, "Items")) return rm_items_json(t->nodes, t->n);
    if (rm_ieq(prop, "CheckBoxes")) return rm_tf(t->checkboxes);
    if (rm_ieq(prop, "ShowLines")) return rm_tf(t->show_lines);
    if (rm_ieq(prop, "SelectedNode")) return t->selected;
    if (rm_ieq(prop, "SelectedText") || rm_ieq(prop, "Text")) {
        rm_item *it = rm_items_find(t->nodes, t->n, t->selected);
        return it ? it->text : "";
    }
    if (rm_ieq(prop, "CheckedNodes")) {
        rm_list l = {0, 0, 0};
        const char *s;
        collect_checked(t->nodes, t->n, &l);
        s = rm_list_join(&l, ';');
        rm_list_free(&l);
        return s;
    }
    if (rm_ieq(prop, "NodeCount")) return rad_str(t->nrows);
    return NULL;
}

static int add_child(rm_item **items, int *n, const char *text, const char *name, const char *image) {
    rm_item *ni = (rm_item *)realloc(*items, sizeof(rm_item) * (*n + 1)), *it;
    if (!ni) return 0;
    *items = ni;
    it = &ni[*n];
    memset(it, 0, sizeof *it);
    it->text = rm_strdup(text);
    it->name = rm_strdup(name);
    it->image = rm_strdup(image);
    it->kind = rm_strdup(""); it->tag = rm_strdup(""); it->shortcut = rm_strdup(""); it->tip = rm_strdup(""); it->value = rm_strdup("");
    it->enabled = 1;
    (*n)++;
    return 1;
}

static int remove_node(rm_item **items, int *n, const char *name) {
    int i;
    for (i = 0; i < *n; i++) {
        if (rm_ieq((*items)[i].name, name)) {
            rm_item_clear(&(*items)[i]);
            memmove(*items + i, *items + i + 1, sizeof(rm_item) * (*n - i - 1));
            (*n)--;
            return 1;
        }
        if (remove_node(&(*items)[i].items, &(*items)[i].n, name)) return 1;
    }
    return 0;
}

static void expand_all(rm_item *items, int n, int on) {
    int i;
    for (i = 0; i < n; i++) {
        if (items[i].n) items[i].expanded = on;
        expand_all(items[i].items, items[i].n, on);
    }
}

static const char *RF_CALL tv_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmTree *t = (RmTree *)state;
    rm_item *it = rm_items_find(t->nodes, t->n, rm_arg(args, 0));
    if (rm_ieq(m, "AddNode")) {           /* AddNode(parent, text, name, image) -> name ("" parent = root) */
        const char *parent = rm_arg(args, 0);
        char name[64];
        const char *nm = rm_arg(args, 2);
        int ok;
        if (*nm) snprintf(name, sizeof name, "%s", nm);
        else snprintf(name, sizeof name, "node%d", ++t->auto_name);
        {
            char *nmc = rm_strdup(name), *txt = rm_strdup(rm_arg(args, 1)), *img = rm_strdup(rm_arg(args, 3));
            if (*parent && it) { ok = add_child(&it->items, &it->n, txt, nmc, img); it->lazy = 0; }
            else ok = add_child(&t->nodes, &t->n, txt, nmc, img);
            free(txt); free(img);
            tv_rows(h, t);
            if (!ok) { free(nmc); return ""; }
            {
                static char keep[64];
                snprintf(keep, sizeof keep, "%s", nmc);
                free(nmc);
                return keep;
            }
        }
    }
    if (rm_ieq(m, "RemoveNode")) { remove_node(&t->nodes, &t->n, rm_arg(args, 0)); tv_rows(h, t); return ""; }
    if (rm_ieq(m, "Clear")) { rm_items_free(t->nodes, t->n); t->nodes = NULL; t->n = 0; rm_setstr(&t->selected, ""); tv_rows(h, t); return ""; }
    if (rm_ieq(m, "ExpandNode")) { tv_expand(h, t, it, 1); return ""; }
    if (rm_ieq(m, "CollapseNode")) { tv_expand(h, t, it, 0); return ""; }
    if (rm_ieq(m, "ExpandAll")) { expand_all(t->nodes, t->n, 1); tv_rows(h, t); return ""; }
    if (rm_ieq(m, "CollapseAll")) { expand_all(t->nodes, t->n, 0); tv_rows(h, t); return ""; }
    if (rm_ieq(m, "SetChecked")) { if (it) { check_down(it, rm_bool(rm_arg(args, 1))); rf_invalidate(h); } return ""; }
    if (rm_ieq(m, "GetChecked")) return rm_tf(it && it->checked);
    if (rm_ieq(m, "SelectNode")) { int i = tv_index(t, rm_arg(args, 0)); if (i >= 0) tv_select(h, t, i, 0); return ""; }
    if (rm_ieq(m, "GetNodeText")) return it ? it->text : "";
    if (rm_ieq(m, "SetNodeText")) { if (it) { rm_setstr(&it->text, rm_arg(args, 1)); rf_invalidate(h); } return ""; }
    if (rm_ieq(m, "SetNodeImage")) { if (it) { rm_setstr(&it->image, rm_arg(args, 1)); rf_invalidate(h); } return ""; }
    if (rm_ieq(m, "NodeCount")) return rad_str(it ? it->n : t->n);
    return NULL;
}

/* geometry of row r: x of the expander / check box / image / text */
static void tv_geo(rf_handle h, RmTree *t, TRow *r, int *ex, int *cx, int *ix, int *tx) {
    int indent = rm_px(h, 18), x = rm_px(h, 6) + r->depth * indent;
    *ex = x;
    x += indent;
    *cx = x;
    if (t->checkboxes) x += rm_px(h, 22);
    *ix = x;
    if (rm_has_icon(r->it->image)) x += rm_px(h, 22);
    *tx = x;
}

static int RF_CALL tv_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmTree *t = (RmTree *)state;
    int x = GET_X_LPARAM(l), y = GET_Y_LPARAM(l), row, ex, cx, ix, tx;
    if (!t) return 0;
    switch (msg) {
    case WM_SIZE: tv_rows(h, t); break;
    case WM_VSCROLL: {
        SCROLLINFO si;
        memset(&si, 0, sizeof si);
        si.cbSize = sizeof si;
        si.fMask = SIF_ALL;
        GetScrollInfo((HWND)rf_hwnd(h), SB_VERT, &si);
        switch (LOWORD(w)) {
        case SB_LINEUP: t->top--; break;
        case SB_LINEDOWN: t->top++; break;
        case SB_PAGEUP: t->top -= (int)si.nPage; break;
        case SB_PAGEDOWN: t->top += (int)si.nPage; break;
        case SB_THUMBTRACK: case SB_THUMBPOSITION: t->top = si.nTrackPos; break;
        default: break;
        }
        tv_rows(h, t);
        *res = 0;
        return 1;
    }
    case WM_MOUSEWHEEL:
        t->top -= GET_WHEEL_DELTA_WPARAM(w) / 40;
        tv_rows(h, t);
        *res = 0;
        return 1;
    case WM_LBUTTONDOWN: case WM_LBUTTONDBLCLK:
        SetFocus((HWND)rf_hwnd(h));
        row = t->top + y / tv_row_h(h);
        if (row < 0 || row >= t->nrows) { *res = 0; return 1; }
        tv_geo(h, t, &t->rows[row], &ex, &cx, &ix, &tx);
        if (x >= ex && x < ex + rm_px(h, 18) && (t->rows[row].it->n || t->rows[row].it->lazy)) {
            tv_expand(h, t, t->rows[row].it, !t->rows[row].it->expanded);
        } else if (t->checkboxes && x >= cx && x < cx + rm_px(h, 20)) {
            rm_item *it = t->rows[row].it;
            check_down(it, !it->checked);
            rf_invalidate(h);
            rm_raise_item(h, "NodeChecked", it->name, row);
        } else {
            tv_select(h, t, row, msg == WM_LBUTTONDOWN);
            if (msg == WM_LBUTTONDBLCLK) {
                rm_item *it = t->rows[row].it;
                rm_raise_item(h, "NodeDoubleClick", it->name, row);
                if (it->n || it->lazy) tv_expand(h, t, it, !it->expanded);
            }
        }
        *res = 0;
        return 1;
    case WM_MOUSEMOVE:
        row = t->top + y / tv_row_h(h);
        if (row >= t->nrows) row = -1;
        if (row != t->hot) { t->hot = row; rf_invalidate(h); }
        break;
    case WM_MOUSELEAVE:
        t->hot = -1;
        rf_invalidate(h);
        break;
    case WM_KEYDOWN: {
        int cur = tv_index(t, t->selected), rtl = rf_rtl(h);
        int right = rtl ? VK_LEFT : VK_RIGHT, left = rtl ? VK_RIGHT : VK_LEFT;
        rm_item *it = cur >= 0 ? t->rows[cur].it : NULL;
        if (w == VK_DOWN) tv_select(h, t, cur + 1 < t->nrows ? cur + 1 : cur, 1);
        else if (w == VK_UP) tv_select(h, t, cur > 0 ? cur - 1 : 0, 1);
        else if (w == VK_HOME) tv_select(h, t, 0, 1);
        else if (w == VK_END) tv_select(h, t, t->nrows - 1, 1);
        else if ((int)w == right && it) {
            if ((it->n || it->lazy) && !it->expanded) tv_expand(h, t, it, 1);
            else if (it->n) tv_select(h, t, cur + 1, 1);
        } else if ((int)w == left && it) {
            if (it->expanded) tv_expand(h, t, it, 0);
            else if (t->rows[cur].parent) tv_select(h, t, tv_index(t, t->rows[cur].parent->name), 1);
        } else if (w == VK_SPACE && it && t->checkboxes) {
            check_down(it, !it->checked);
            rf_invalidate(h);
            rm_raise_item(h, "NodeChecked", it->name, cur);
        } else if (w == VK_RETURN && it) {
            rm_raise_item(h, "NodeDoubleClick", it->name, cur);
        } else break;
        *res = 0;
        return 1;
    }
    case WM_GETDLGCODE:
        *res = DLGC_WANTARROWS | DLGC_WANTCHARS;
        return 1;
    default: break;
    }
    return 0;
}

static int partially(rm_item *it) {
    int i, on = 0, off = 0;
    for (i = 0; i < it->n; i++) {
        if (it->items[i].checked) on++;
        else off++;
        if (partially(&it->items[i])) return 1;
    }
    return on && off;
}

static void RF_CALL tv_paint(rf_handle h, void *state, const rf_paint *p) {
    RmTree *t = (RmTree *)state;
    const rf_theme *th = rm_look_theme(&t->look, p);
    unsigned accent = rm_look_accent(&t->look, th), back = p->has_back ? p->back : th->input;
    unsigned fg = p->has_fore ? p->fore : th->input_text, line = rf_blend(th->border, back, 0.35);
    int i, rh = tv_row_h(h), indent = rf_px(p, 18);
    rm_fill(p, 0, 0, p->width, p->height, back);
    for (i = t->top; i < t->nrows; i++) {
        TRow *r = &t->rows[i];
        int y = (i - t->top) * rh, ex, cx, ix, tx, sel = rm_ieq(r->it->name, t->selected), d;
        unsigned c = r->it->enabled ? fg : th->disabled_text;
        if (y > p->height) break;
        tv_geo(h, t, r, &ex, &cx, &ix, &tx);
        if (sel) rf_draw_rect(p, rf_px(p, 2), y + 1, p->width - rf_px(p, 4), rh - 2, rf_blend(back, accent, th->dark ? 0.35 : 0.16), RF_NONE, 0,
                              rf_px(p, th->radius + 1));
        else if (i == t->hot) rf_draw_rect(p, rf_px(p, 2), y + 1, p->width - rf_px(p, 4), rh - 2, rf_blend(back, fg, 0.05), RF_NONE, 0,
                                           rf_px(p, th->radius + 1));
        if (t->show_lines) {
            for (d = 0; d < r->depth; d++)
                if (r->lines & (1u << d)) {
                    int lx = rf_px(p, 6) + d * indent + indent / 2;
                    rf_draw_line(p, lx, y, lx, y + rh, line, 1);
                }
            if (r->depth > 0) {
                int lx = ex - indent + indent / 2;
                rf_draw_line(p, lx, y, lx, r->last ? y + rh / 2 : y + rh, line, 1);
                rf_draw_line(p, lx, y + rh / 2, ex + (r->it->n || r->it->lazy ? rf_px(p, 3) : indent - rf_px(p, 2)), y + rh / 2, line, 1);
            }
        }
        if (r->it->n || r->it->lazy)
            rm_chevron(p, ex + indent / 2.0, y + rh / 2.0, rf_px(p, 8), r->it->expanded ? RM_DOWN : RM_RIGHT, rf_blend(fg, back, 0.3), rf_px(p, 1.4));
        if (t->checkboxes) {
            int s = rf_px(p, 15), by = y + (rh - s) / 2, part = !r->it->checked && partially(r->it);
            rf_draw_rect(p, cx, by, s, s, r->it->checked ? accent : th->input, r->it->checked ? RF_NONE : rf_blend(th->border, fg, 0.2), 1,
                         rf_px(p, 3));
            if (r->it->checked) rm_checkmark(p, cx, by, s, s, rm_on(accent), rf_px(p, 1.7));
            else if (part) rf_draw_rect(p, cx + s / 4, by + s / 4, s / 2, s / 2, accent, RF_NONE, 0, 1);
        }
        if (rm_has_icon(r->it->image)) {
            int s = rf_px(p, 16);
            rm_icon(p, r->it->image, ix, y + (rh - s) / 2, s, s, sel ? accent : rf_blend(accent, fg, 0.3));
        }
        {
            HGDIOBJ o = sel ? rm_font_push(p, 1.0, 1) : NULL;
            rf_draw_text(p, r->it->text, tx, y, p->width - tx - rf_px(p, 4), rh, c, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
            if (o) rm_font_pop(p, o);
        }
        if (sel && p->focused) rf_draw_rect(p, rf_px(p, 2), y + 1, p->width - rf_px(p, 4), rh - 2, RF_NONE, rf_blend(back, accent, 0.6), 1,
                                            rf_px(p, th->radius + 1));
    }
    rf_draw_rect(p, 0, 0, p->width, p->height, RF_NONE, rf_blend(th->border, back, 0.3), 1, 0);
}

RF_MODULE(rm_tree) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmTreeView";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.style = WS_VSCROLL;
    k.create = tv_create; k.destroy = tv_destroy; k.set = tv_set; k.get = tv_get; k.invoke = tv_invoke;
    k.paint = tv_paint; k.message = tv_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Nodes,CheckBoxes,ShowLines,SelectedNode,SelectedText,CheckedNodes,NodeCount";
    k.events = "NodeClick,NodeDoubleClick,NodeExpanding,NodeCollapsed,NodeChecked,SelectedIndexChanged";
    k.methods = "AddNode,RemoveNode,Clear,ExpandNode,CollapseNode,ExpandAll,CollapseAll,SetChecked,GetChecked,SelectNode,GetNodeText,"
                "SetNodeText,SetNodeImage";
    rf_register_class(&k);
}
