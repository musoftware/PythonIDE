/* RAD Modern buttons: RmButton (default / accent / outline / flat / link, image + text, split drop-down),
 * RmToggle (on/off switch), RmCheckBox (with indeterminate), RmRadioButton, RmTile (Metro tile).
 * Owner-drawn on radforms (double buffer, theme, hover / press animation from the core), DPI aware,
 * keyboard: Space / Enter click, Alt+Down / F4 open the drop-down.
 *
 * RF_CLASSES: RmButton RmToggle RmCheckBox RmRadioButton RmTile
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <windowsx.h>

/* ================================================================== RmButton */
enum { BK_DEFAULT, BK_ACCENT, BK_OUTLINE, BK_FLAT, BK_LINK };
static const char *const BKINDS[] = {"Default", "Accent", "Outline", "Flat", "Link"};
enum { IP_LEFT, IP_TOP, IP_RIGHT };
static const char *const IPOS[] = {"Left", "Top", "Right"};

typedef struct {
    rm_look look;
    int kind, radius, imgpos;
    char *image, *dropsrc;
    rm_item *drop;
    int ndrop;
} RmButton;

static int RF_CALL btn_create(rf_handle h, void **state) {
    RmButton *b = (RmButton *)calloc(1, sizeof *b);
    (void)h;
    if (!b) return 0;
    b->radius = -1;
    b->image = rm_strdup("");
    b->dropsrc = rm_strdup("");
    *state = b;
    return 1;
}

static void RF_CALL btn_destroy(rf_handle h, void *state) {
    RmButton *b = (RmButton *)state;
    (void)h;
    if (!b) return;
    free(b->image);
    free(b->dropsrc);
    rm_items_free(b->drop, b->ndrop);
    free(b);
}

static int pick(const char *v, const char *const *names, int n) {
    int i;
    for (i = 0; i < n; i++)
        if (rm_ieq(v, names[i])) return i;
    return 0;
}

static int RF_CALL btn_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmButton *b = (RmButton *)state;
    (void)h;
    if (rm_look_set(&b->look, prop, v)) return 1;
    if (rm_ieq(prop, "Kind")) { b->kind = pick(v, BKINDS, 5); return 1; }
    if (rm_ieq(prop, "CornerRadius")) { b->radius = rm_int(v); return 1; }
    if (rm_ieq(prop, "ImagePosition")) { b->imgpos = pick(v, IPOS, 3); return 1; }
    if (rm_ieq(prop, "Image")) { rm_setstr(&b->image, v); return 1; }
    if (rm_ieq(prop, "DropDownItems")) {
        rm_setstr(&b->dropsrc, v);
        rm_items_free(b->drop, b->ndrop);
        b->drop = rm_items_parse(v, &b->ndrop);
        return 1;
    }
    return 0;
}

static const char *RF_CALL btn_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmButton *b = (RmButton *)state;
    const char *r = rm_look_get(&b->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Kind")) return BKINDS[b->kind];
    if (rm_ieq(prop, "CornerRadius")) return rad_str(b->radius);
    if (rm_ieq(prop, "ImagePosition")) return IPOS[b->imgpos];
    if (rm_ieq(prop, "Image")) return b->image;
    if (rm_ieq(prop, "DropDownItems")) return b->dropsrc;
    return NULL;
}

static int btn_arrow_w(rf_handle h) { return rm_px(h, 22); }

static void btn_dropdown(rf_handle h, RmButton *b) {
    RECT r;
    rm_item *it;
    HWND w = (HWND)rf_hwnd(h);
    if (!b->ndrop || !w) return;
    GetWindowRect(w, &r);
    it = rm_popup_menu(h, b->drop, b->ndrop, r.left, r.bottom);
    if (it) {
        int idx = (int)(it - b->drop);
        if (idx < 0 || idx >= b->ndrop) idx = -1;
        rm_raise_item(h, "DropDownItemClicked", it->name, idx);
    }
}

static const char *RF_CALL btn_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmButton *b = (RmButton *)state;
    (void)args;
    if (rm_ieq(m, "ShowDropDown")) { btn_dropdown(h, b); return ""; }
    if (rm_ieq(m, "PerformClick")) { rf_raise(h, "Click", ""); return ""; }
    return NULL;
}

static int RF_CALL btn_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmButton *b = (RmButton *)state;
    HWND hw = (HWND)rf_hwnd(h);
    RECT r;
    if (!b || !hw) return 0;
    switch (msg) {
    case WM_LBUTTONDOWN:
        GetClientRect(hw, &r);
        if (b->ndrop && GET_X_LPARAM(l) >= r.right - btn_arrow_w(h)) {
            SetFocus(hw);
            btn_dropdown(h, b);
            *res = 0;
            return 1;           /* no Click for the arrow part */
        }
        break;
    case WM_KEYDOWN:
        if (w == VK_RETURN) { rf_raise(h, "Click", ""); *res = 0; return 1; }
        if ((w == VK_F4 || (w == VK_DOWN && (GetKeyState(VK_MENU) & 0x8000))) && b->ndrop) {
            btn_dropdown(h, b);
            *res = 0;
            return 1;
        }
        break;
    case WM_SYSKEYDOWN:
        if (w == VK_DOWN && b->ndrop) { btn_dropdown(h, b); *res = 0; return 1; }
        break;
    case WM_GETDLGCODE:
        *res = DLGC_WANTCHARS | (l && ((MSG *)l)->message == WM_KEYDOWN && ((MSG *)l)->wParam == VK_RETURN ?
                                 DLGC_WANTMESSAGE : 0);
        return 1;
    default: break;
    }
    return 0;
}

static void draw_image_text(const rf_paint *p, const char *image, const char *text, int x, int y, int w, int h,
                            int imgpos, unsigned color, int align) {
    int has = rm_has_icon(image), pad = rf_px(p, 6);
    int big = imgpos == IP_TOP && h >= rf_px(p, 56);
    int isz = has ? rf_px(p, big ? 32 : 16) : 0;
    if (!has) {
        rf_draw_text(p, text, x, y, w, h, color, align | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        return;
    }
    if (!text || !*text) {
        rm_icon(p, image, x + (w - isz) / 2, y + (h - isz) / 2, isz, isz, color);
        return;
    }
    if (imgpos == IP_TOP) {
        int th = rm_text_h(p), total = isz + rf_px(p, 4) + th, top = y + (h - total) / 2;
        rm_icon(p, image, x + (w - isz) / 2, top, isz, isz, color);
        rf_draw_text(p, text, x, top + isz + rf_px(p, 4), w, th, color, RF_ALIGN_CENTER | RF_ALIGN_ELLIPSIS);
        return;
    }
    {
        int tw = rm_text_w(p, text), total = isz + pad + tw, left;
        if (total > w) total = w;
        left = (align & 3) == RF_ALIGN_LEFT ? x : x + (w - total) / 2;
        if (imgpos == IP_RIGHT) {
            rf_draw_text(p, text, left, y, total - isz - pad, h, color, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
            rm_icon(p, image, left + total - isz, y + (h - isz) / 2, isz, isz, color);
        } else {
            rm_icon(p, image, left, y + (h - isz) / 2, isz, isz, color);
            rf_draw_text(p, text, left + isz + pad, y, total - isz - pad, h, color,
                         RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        }
    }
}

static void RF_CALL btn_paint(rf_handle h, void *state, const rf_paint *p) {
    RmButton *b = (RmButton *)state;
    const rf_theme *t = rm_look_theme(&b->look, p);
    unsigned accent = rm_look_accent(&b->look, t), fill, border, text;
    unsigned face = p->has_back ? p->back : t->face, fore = p->has_fore ? p->fore : t->face_text;
    int radius = rf_px(p, b->radius >= 0 ? b->radius : t->radius + 2), bw = rf_px(p, 1);
    int aw = b->ndrop ? btn_arrow_w(h) : 0;
    double act = p->hover > p->press ? p->hover : p->press;
    switch (b->kind) {
    case BK_ACCENT:
        fill = rf_blend(rf_blend(accent, rf_blend(accent, 0xFFFFFF, 0.18), p->hover), rf_blend(accent, 0, 0.22), p->press);
        border = fill;
        text = rm_on(accent);
        break;
    case BK_OUTLINE:
        fill = rf_blend(rf_blend(t->window, rf_blend(t->window, accent, 0.08), p->hover), rf_blend(t->window, accent, 0.2),
                        p->press);
        if (p->hover == 0 && p->press == 0) fill = RF_NONE;
        border = accent;
        text = accent;
        break;
    case BK_FLAT:
        fill = act > 0 ? rf_blend(rf_blend(t->window, t->hot, p->hover), t->pressed, p->press) : RF_NONE;
        border = RF_NONE;
        text = fore;
        break;
    case BK_LINK:
        fill = RF_NONE;
        border = RF_NONE;
        text = rf_blend(accent, rf_blend(accent, 0, 0.3), p->press);
        break;
    default:
        fill = rf_blend(rf_blend(face, t->hot, p->hover), t->pressed, p->press);
        border = rf_blend(t->border, t->hot_border, act);
        text = fore;
    }
    if (!p->enabled) {
        text = t->disabled_text;
        if (b->kind == BK_ACCENT) { fill = rf_blend(t->face, t->border, 0.4); border = fill; text = t->window; }
        else if (border != RF_NONE) border = rf_blend(t->border, t->window, 0.4);
    }
    rf_draw_rect(p, 0, 0, p->width, p->height, fill, border, bw, radius);
    if (b->kind == BK_LINK) {
        HGDIOBJ old = p->hover > 0.5 ? NULL : NULL;
        LOGFONTW lf;
        HFONT f = NULL;
        if (p->hover > 0.5 && p->font && GetObjectW((HGDIOBJ)p->font, sizeof lf, &lf)) {
            lf.lfUnderline = TRUE;
            f = CreateFontIndirectW(&lf);
            old = SelectObject((HDC)p->hdc, f);
        }
        draw_image_text(p, b->image, p->text, rf_px(p, 4), 0, p->width - rf_px(p, 8), p->height, b->imgpos, text,
                        RF_ALIGN_LEFT);
        if (f) { SelectObject((HDC)p->hdc, old); DeleteObject(f); }
    } else {
        int pad = rf_px(p, 8);
        draw_image_text(p, b->image, p->text, pad, 0, p->width - 2 * pad - aw, p->height, b->imgpos, text, RF_ALIGN_CENTER);
    }
    if (aw) {
        int x = p->width - aw;
        rf_draw_line(p, x, rf_px(p, 6), x, p->height - rf_px(p, 6), rf_blend(fill == RF_NONE ? t->window : fill, text, 0.35), 1);
        rm_chevron(p, x + aw / 2.0, p->height / 2.0, rf_px(p, 8), RM_DOWN, text, rf_px(p, 1.4));
    }
    if (p->focused && b->kind != BK_LINK)
        rf_draw_rect(p, rf_px(p, 3), rf_px(p, 3), p->width - rf_px(p, 6), p->height - rf_px(p, 6), RF_NONE,
                     rf_blend(fill == RF_NONE ? t->window : fill, text, 0.55), 1, radius > 3 ? radius - 3 : 0);
    else if (p->focused)
        rf_draw_rect(p, 0, 0, p->width, p->height, RF_NONE, rf_blend(t->window, text, 0.5), 1, 0);
}

/* ================================================================== RmToggle / RmCheckBox / RmRadioButton */
typedef struct {
    rm_look look;
    int kind;               /* 0 toggle 1 check 2 radio */
    int checked, indeterminate, down, align_right;
    char *on_text, *off_text;
    rm_anim knob;
} RmCheck;

static int RF_CALL chk_create_k(rf_handle h, void **state, int kind) {
    RmCheck *c = (RmCheck *)calloc(1, sizeof *c);
    (void)h;
    if (!c) return 0;
    c->kind = kind;
    c->on_text = rm_strdup("");
    c->off_text = rm_strdup("");
    *state = c;
    return 1;
}
static int RF_CALL tog_create(rf_handle h, void **s) { return chk_create_k(h, s, 0); }
static int RF_CALL chk_create(rf_handle h, void **s) { return chk_create_k(h, s, 1); }
static int RF_CALL rad_create(rf_handle h, void **s) { return chk_create_k(h, s, 2); }

static void RF_CALL chk_destroy(rf_handle h, void *state) {
    RmCheck *c = (RmCheck *)state;
    (void)h;
    if (!c) return;
    free(c->on_text);
    free(c->off_text);
    free(c);
}

static void radio_siblings_off(rf_handle h) {
    HWND me = (HWND)rf_hwnd(h), parent = me ? GetParent(me) : NULL, k;
    if (!parent) return;
    for (k = GetWindow(parent, GW_CHILD); k; k = GetWindow(k, GW_HWNDNEXT)) {
        rf_handle o = (rf_handle)GetPropW(k, L"radforms.ctl");
        if (k == me || !o) continue;
        if (rm_ieq(rf_type(o), "RmRadioButton") && rm_bool(rf_prop_get(o, "Checked"))) rf_prop_set(o, "Checked", "False");
    }
}

static void chk_change(rf_handle h, RmCheck *c, int checked) {
    int was = c->checked, wasind = c->indeterminate;
    c->checked = checked;
    if (c->kind == 1 && checked) c->indeterminate = 0;
    if (c->kind == 2 && checked) radio_siblings_off(h);
    c->knob.target = c->checked ? 1 : 0;
    if (c->kind == 0 && rf_theme_current()->anim_ms > 0 && rf_hwnd(h) && IsWindowVisible((HWND)rf_hwnd(h)))
        rf_set_timer(h, RM_ANIM_TIMER, 15);
    else
        c->knob.v = c->knob.target;
    rf_invalidate(h);
    if (was != c->checked || wasind != c->indeterminate) rf_raise(h, "CheckedChanged", "");
}

static int RF_CALL chk_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmCheck *c = (RmCheck *)state;
    if (rm_look_set(&c->look, prop, v)) return 1;
    if (rm_ieq(prop, "Checked") || (rm_ieq(prop, "Value") && c->kind != 0)) {
        int on = rm_bool(v) || rm_ieq(v, "Checked");
        if (c->kind == 1 && rm_ieq(v, "Indeterminate")) { c->indeterminate = 1; rf_invalidate(h); return 1; }
        chk_change(h, c, on);
        return 1;
    }
    if (rm_ieq(prop, "Indeterminate") && c->kind == 1) {
        int was = c->indeterminate;
        c->indeterminate = rm_bool(v);
        if (was != c->indeterminate) rf_raise(h, "CheckedChanged", "");
        return 1;
    }
    if (rm_ieq(prop, "OnText")) { rm_setstr(&c->on_text, v); return 1; }
    if (rm_ieq(prop, "OffText")) { rm_setstr(&c->off_text, v); return 1; }
    if (rm_ieq(prop, "CheckAlign")) { c->align_right = rm_ieq(v, "Right") || rm_ieq(v, "MiddleRight"); return 1; }
    return 0;
}

static const char *RF_CALL chk_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmCheck *c = (RmCheck *)state;
    const char *r = rm_look_get(&c->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Checked")) return rm_tf(c->checked);
    if (rm_ieq(prop, "Value")) return c->indeterminate ? "2" : c->checked ? "1" : "0";
    if (rm_ieq(prop, "Indeterminate")) return rm_tf(c->indeterminate);
    if (rm_ieq(prop, "CheckState")) return c->indeterminate ? "Indeterminate" : c->checked ? "Checked" : "Unchecked";
    if (rm_ieq(prop, "OnText")) return c->on_text;
    if (rm_ieq(prop, "OffText")) return c->off_text;
    if (rm_ieq(prop, "CheckAlign")) return c->align_right ? "Right" : "Left";
    return NULL;
}

static void chk_toggle(rf_handle h, RmCheck *c) {
    if (c->kind == 2) { if (!c->checked) chk_change(h, c, 1); }
    else if (c->kind == 1 && c->indeterminate) chk_change(h, c, 1);
    else chk_change(h, c, !c->checked);
}

static const char *RF_CALL chk_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmCheck *c = (RmCheck *)state;
    (void)args;
    if (rm_ieq(m, "Toggle") || rm_ieq(m, "PerformClick")) { chk_toggle(h, c); rf_raise(h, "Click", ""); return ""; }
    return NULL;
}

static int RF_CALL chk_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmCheck *c = (RmCheck *)state;
    HWND hw = (HWND)rf_hwnd(h);
    RECT r;
    POINT pt;
    if (!c || !hw) return 0;
    switch (msg) {
    case WM_LBUTTONDOWN: case WM_LBUTTONDBLCLK:
        c->down = 1;
        break;
    case WM_LBUTTONUP:
        GetClientRect(hw, &r);
        pt.x = GET_X_LPARAM(l);
        pt.y = GET_Y_LPARAM(l);
        if (c->down && PtInRect(&r, pt)) chk_toggle(h, c);
        c->down = 0;
        break;
    case WM_KEYDOWN:
        if (w == VK_SPACE) chk_toggle(h, c);
        break;
    case WM_TIMER:
        if (w == RM_ANIM_TIMER) {
            double ms = rf_theme_current()->anim_ms;
            if (!rm_anim_step(&c->knob, ms > 0 ? 15.0 / (ms * 1.3) : 1)) rf_set_timer(h, RM_ANIM_TIMER, 0);
            rf_invalidate(h);
            *res = 0;
            return 1;
        }
        break;
    default: break;
    }
    return 0;
}

static void RF_CALL chk_paint(rf_handle h, void *state, const rf_paint *p) {
    RmCheck *c = (RmCheck *)state;
    const rf_theme *t = rm_look_theme(&c->look, p);
    unsigned accent = rm_look_accent(&c->look, t);
    unsigned fore = p->has_fore ? p->fore : t->window_text, back;
    unsigned off_border = rf_blend(t->border, t->window_text, 0.25 + 0.25 * p->hover);
    const char *text = p->text;
    int bx, by, bs, tx, tw;
    (void)h;
    if (p->has_back) rm_fill(p, 0, 0, p->width, p->height, p->back);
    back = p->has_back ? p->back : t->window;
    if (!p->enabled) { fore = t->disabled_text; accent = rf_blend(t->border, back, 0.2); off_border = rf_blend(t->border, back, 0.3); }
    if (c->kind == 0) {                     /* switch */
        int tw0 = rf_px(p, 40), th = rf_px(p, 20), ty = (p->height - th) / 2, knob = th - rf_px(p, 6);
        double k = c->knob.v;
        unsigned track = rf_blend(back, accent, k);
        unsigned kc = k > 0.5 ? rm_on(accent) : rf_blend(t->window_text, back, 0.35);
        bx = c->align_right ? p->width - tw0 : 0;
        if (p->press > 0) knob += rf_px(p, 2) * p->press;
        rf_draw_rect(p, bx, ty, tw0, th, k > 0 ? rf_blend(track, rf_blend(accent, 0xFFFFFF, 0.15), p->hover * k) : RF_NONE,
                     k >= 1 ? RF_NONE : off_border, rf_px(p, 1.2), th / 2);
        if (k > 0 && k < 1) rf_draw_rect(p, bx, ty, tw0, th, RF_NONE, off_border, 1, th / 2);
        rm_ellipse(p, bx + rf_px(p, 3) + (tw0 - knob - rf_px(p, 6)) * k, ty + (th - knob) / 2.0, knob, knob, kc, RF_NONE, 0);
        if (p->focused) rf_draw_rect(p, bx - 2, ty - 2, tw0 + 4, th + 4, RF_NONE, rf_blend(back, accent, 0.6), 1, th / 2 + 2);
        if (c->checked && *c->on_text) text = c->on_text;
        if (!c->checked && *c->off_text) text = c->off_text;
        tx = c->align_right ? 0 : tw0 + rf_px(p, 8);
        tw = p->width - tw0 - rf_px(p, 8);
        rf_draw_text(p, text, tx, 0, tw, p->height, fore, (c->align_right ? RF_ALIGN_RIGHT : RF_ALIGN_LEFT) |
                     RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        return;
    }
    bs = rf_px(p, 16);
    by = (p->height - bs) / 2;
    bx = c->align_right ? p->width - bs - 1 : 1;
    if (c->kind == 1) {
        int on = c->checked || c->indeterminate;
        unsigned fill = on ? rf_blend(accent, rf_blend(accent, 0xFFFFFF, 0.15), p->hover) : rf_blend(t->input, t->hot, p->hover);
        if (p->press > 0) fill = rf_blend(fill, on ? rf_blend(accent, 0, 0.2) : t->pressed, p->press);
        rf_draw_rect(p, bx, by, bs, bs, fill, on ? RF_NONE : off_border, rf_px(p, 1.2), rf_px(p, t->radius > 0 ? 3 : 0));
        if (c->indeterminate)
            rf_draw_rect(p, bx + bs / 4, by + bs / 2 - rf_px(p, 1), bs / 2, rf_px(p, 2), rm_on(accent), RF_NONE, 0, 0);
        else if (c->checked)
            rm_checkmark(p, bx, by, bs, bs, rm_on(accent), rf_px(p, 1.8));
    } else {
        unsigned ring = c->checked ? accent : off_border;
        rm_ellipse(p, bx, by, bs, bs, rf_blend(t->input, t->hot, p->hover), ring, rf_px(p, c->checked ? 1.6 : 1.2));
        if (c->checked) {
            double d = bs * (0.5 - 0.08 * p->press);
            rm_ellipse(p, bx + (bs - d) / 2.0, by + (bs - d) / 2.0, d, d, accent, RF_NONE, 0);
        }
    }
    if (p->focused) rf_draw_rect(p, bx - 2, by - 2, bs + 4, bs + 4, RF_NONE, rf_blend(back, accent, 0.6), 1,
                                 c->kind == 2 ? bs / 2 + 2 : rf_px(p, 4));
    tx = c->align_right ? 0 : bs + rf_px(p, 8);
    tw = p->width - bs - rf_px(p, 9);
    rf_draw_text(p, text, tx, 0, tw, p->height, fore, (c->align_right ? RF_ALIGN_RIGHT : RF_ALIGN_LEFT) |
                 RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
}

/* ================================================================== RmTile */
typedef struct {
    rm_look look;
    char *title, *count, *image, *size;
    unsigned color;
    int has_color;
} RmTile;

static int RF_CALL tile_create(rf_handle h, void **state) {
    RmTile *t = (RmTile *)calloc(1, sizeof *t);
    (void)h;
    if (!t) return 0;
    t->title = rm_strdup("");
    t->count = rm_strdup("");
    t->image = rm_strdup("");
    t->size = rm_strdup("Medium");
    *state = t;
    return 1;
}

static void RF_CALL tile_destroy(rf_handle h, void *state) {
    RmTile *t = (RmTile *)state;
    (void)h;
    if (!t) return;
    free(t->title); free(t->count); free(t->image); free(t->size);
    free(t);
}

static int RF_CALL tile_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmTile *t = (RmTile *)state;
    (void)h;
    if (rm_look_set(&t->look, prop, v)) return 1;
    if (rm_ieq(prop, "Title")) { rm_setstr(&t->title, v); return 1; }
    if (rm_ieq(prop, "Count")) { rm_setstr(&t->count, v); return 1; }
    if (rm_ieq(prop, "Image")) { rm_setstr(&t->image, v); return 1; }
    if (rm_ieq(prop, "Size") || rm_ieq(prop, "TileSize")) { rm_setstr(&t->size, v); return 1; }
    if (rm_ieq(prop, "TileColor")) { t->has_color = rm_color(v, &t->color); return 1; }
    return 0;
}

static const char *RF_CALL tile_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmTile *t = (RmTile *)state;
    const char *r = rm_look_get(&t->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Title")) return t->title;
    if (rm_ieq(prop, "Count")) return t->count;
    if (rm_ieq(prop, "Image")) return t->image;
    if (rm_ieq(prop, "Size") || rm_ieq(prop, "TileSize")) return t->size;
    if (rm_ieq(prop, "TileColor")) return t->has_color ? rm_colorstr(t->color) : "";
    return NULL;
}

static void RF_CALL tile_paint(rf_handle h, void *state, const rf_paint *p) {
    RmTile *tl = (RmTile *)state;
    const rf_theme *t = rm_look_theme(&tl->look, p);
    unsigned base = tl->has_color ? tl->color : rm_look_accent(&tl->look, t), fill, fg;
    int inset = (int)(rf_px(p, 3) * p->press + 0.5), pad = rf_px(p, 10);
    int small = rm_ieq(tl->size, "Small") || p->height < rf_px(p, 90);
    const char *title = *tl->title ? tl->title : p->text;
    (void)h;
    fill = rf_blend(base, rf_blend(base, 0xFFFFFF, 0.14), p->hover);
    if (!p->enabled) fill = rf_blend(base, t->window, 0.55);
    fg = rm_on(base);
    rf_draw_rect(p, inset, inset, p->width - 2 * inset, p->height - 2 * inset, fill,
                 p->focused ? rf_blend(fill, fg, 0.7) : RF_NONE, rf_px(p, 2), rf_px(p, t->radius > 0 ? 4 : 0));
    if (small) {
        int isz = p->height / 2;
        if (rm_has_icon(tl->image)) rm_icon(p, tl->image, (p->width - isz) / 2, (p->height - isz) / 2, isz, isz, fg);
        else rf_draw_text(p, title, 0, 0, p->width, p->height, fg, RF_ALIGN_CENTER | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        if (*tl->count) {
            HGDIOBJ o = rm_font_push(p, 0.9, 2);
            rf_draw_text(p, tl->count, 0, rf_px(p, 3), p->width - rf_px(p, 5), rf_px(p, 16), fg, RF_ALIGN_RIGHT);
            rm_font_pop(p, o);
        }
        return;
    }
    if (rm_has_icon(tl->image)) {
        int isz = rf_px(p, p->height >= rf_px(p, 200) ? 64 : 40);
        rm_icon(p, tl->image, (p->width - isz) / 2, (p->height - isz) / 2 - rf_px(p, 8), isz, isz, fg);
    }
    if (*tl->count) {
        HGDIOBJ o = rm_font_push(p, 2.4, 1);
        rf_draw_text(p, tl->count, pad, rf_px(p, 4), p->width - 2 * pad, rm_text_h(p) + rf_px(p, 4), fg, RF_ALIGN_RIGHT);
        rm_font_pop(p, o);
    }
    {
        HGDIOBJ o = rm_font_push(p, 1.05, 1);
        int th = rm_text_h(p);
        rf_draw_text(p, title, pad, p->height - pad - th, p->width - 2 * pad, th, fg, RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
        rm_font_pop(p, o);
    }
}

static const char *RF_CALL tile_invoke(rf_handle h, void *state, const char *m, const char *args) {
    (void)state;
    (void)args;
    if (rm_ieq(m, "PerformClick")) { rf_raise(h, "Click", ""); return ""; }
    return NULL;
}

/* ================================================================== registration */
static void reg(const char *name, unsigned flags, int (RF_CALL *create)(rf_handle, void **),
                void (RF_CALL *destroy)(rf_handle, void *),
                int (RF_CALL *set)(rf_handle, void *, const char *, const char *),
                const char *(RF_CALL *get)(rf_handle, void *, const char *),
                const char *(RF_CALL *invoke)(rf_handle, void *, const char *, const char *),
                void (RF_CALL *paint)(rf_handle, void *, const rf_paint *),
                int (RF_CALL *message)(rf_handle, void *, unsigned, uintptr_t, intptr_t, intptr_t *),
                const char *props, const char *events, const char *methods) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = name;
    k.flags = flags;
    k.create = create;
    k.destroy = destroy;
    k.set = set;
    k.get = get;
    k.invoke = invoke;
    k.paint = paint;
    k.message = message;
    k.properties = props;
    k.events = events;
    k.methods = methods;
    rf_register_class(&k);
}

RF_MODULE(rm_buttons) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmButton";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Kind,CornerRadius,Image,ImagePosition,DropDownItems";
    k.events = "Click,DropDownItemClicked";
    k.methods = "PerformClick,ShowDropDown";
    reg(k.name, k.flags, btn_create, btn_destroy, btn_set, btn_get, btn_invoke, btn_paint, btn_message, k.properties,
        k.events, k.methods);
    k.name = "RmToggle";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Checked,OnText,OffText,CheckAlign";
    k.events = "CheckedChanged,Click";
    k.methods = "Toggle,PerformClick";
    reg(k.name, k.flags, tog_create, chk_destroy, chk_set, chk_get, chk_invoke, chk_paint, chk_message, k.properties,
        k.events, k.methods);
    k.name = "RmCheckBox";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Checked,Indeterminate,CheckState,Value,CheckAlign";
    k.events = "CheckedChanged,Click";
    k.methods = "Toggle,PerformClick";
    reg(k.name, k.flags, chk_create, chk_destroy, chk_set, chk_get, chk_invoke, chk_paint, chk_message, k.properties,
        k.events, k.methods);
    k.name = "RmRadioButton";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Checked,Value,CheckAlign";
    k.events = "CheckedChanged,Click";
    k.methods = "PerformClick";
    reg(k.name, k.flags, rad_create, chk_destroy, chk_set, chk_get, chk_invoke, chk_paint, chk_message, k.properties,
        k.events, k.methods);
    k.name = "RmTile";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Title,Count,Image,TileColor,Size";
    k.events = "Click";
    k.methods = "PerformClick";
    reg(k.name, k.flags, tile_create, tile_destroy, tile_set, tile_get, tile_invoke, tile_paint,
        NULL, k.properties, k.events, k.methods);
}
