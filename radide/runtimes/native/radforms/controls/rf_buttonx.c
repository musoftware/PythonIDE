/* ButtonX - an owner-drawn button (DotNetBar ButtonX-like): rounded, theme colours, hover / press
 * animation. It is the reference module for new radforms control classes: everything it does goes
 * through the public ABI of radforms.h (rf_register_class, rf_paint, rf_draw_*), nothing touches the core.
 *
 * RF_CLASSES: ButtonX
 * Properties: Style = Default | Accent | Outline | Flat, Radius (-1 = theme), AccentColor
 * Events: Click (from the core), plus everything the core reports (MouseDown, KeyPress, GotFocus ...)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "radforms.h"

typedef struct {
    int style;          /* 0 default 1 accent 2 outline 3 flat */
    int radius;         /* -1 = theme */
    int has_accent;
    unsigned accent;
} ButtonX;

static int ieq(const char *a, const char *b) {
    for (; *a && *b; a++, b++)
        if ((*a | 32) != (*b | 32)) return 0;
    return *a == *b;
}

static int RF_CALL bx_create(rf_handle h, void **state) {
    ButtonX *b = (ButtonX *)calloc(1, sizeof *b);
    (void)h;
    if (!b) return 0;
    b->radius = -1;
    *state = b;
    return 1;
}

static void RF_CALL bx_destroy(rf_handle h, void *state) {
    (void)h;
    free(state);
}

static int RF_CALL bx_set(rf_handle h, void *state, const char *prop, const char *value) {
    ButtonX *b = (ButtonX *)state;
    (void)h;
    if (ieq(prop, "Style")) {
        b->style = ieq(value, "Accent") ? 1 : ieq(value, "Outline") ? 2 : ieq(value, "Flat") ? 3 : 0;
        return 1;
    }
    if (ieq(prop, "Radius")) { b->radius = (int)rad_num(value); return 1; }
    if (ieq(prop, "AccentColor")) {
        unsigned r = 0, g = 0, bl = 0;
        b->has_accent = value && value[0] == '#' && sscanf(value + 1, "%2x%2x%2x", &r, &g, &bl) == 3;
        b->accent = r | (g << 8) | (bl << 16);
        return 1;
    }
    return 0;                       /* Text, colours, fonts, geometry ...: the core */
}

static const char *RF_CALL bx_get(rf_handle h, void *state, const char *prop) {
    ButtonX *b = (ButtonX *)state;
    static const char *const styles[] = {"Default", "Accent", "Outline", "Flat"};
    (void)h;
    if (ieq(prop, "Style")) return styles[b->style];
    if (ieq(prop, "Radius")) return rad_str(b->radius);
    return NULL;
}

static void RF_CALL bx_paint(rf_handle h, void *state, const rf_paint *p) {
    ButtonX *b = (ButtonX *)state;
    const rf_theme *t = p->theme;
    unsigned accent = b->has_accent ? b->accent : t->accent;
    unsigned fill, border, text;
    int radius = rf_px(p, b->radius >= 0 ? b->radius : t->radius), bw = rf_px(p, t->border_width);
    (void)h;
    if (bw < 1) bw = 1;
    switch (b->style) {
    case 1:                         /* accent */
        fill = rf_blend(accent, rf_blend(accent, 0xFFFFFF, 0.25), p->hover);
        fill = rf_blend(fill, rf_blend(accent, 0, 0.25), p->press);
        border = fill;
        text = t->accent_text;
        break;
    case 2:                         /* outline */
        fill = rf_blend(t->window, t->hot, p->hover);
        fill = rf_blend(fill, t->pressed, p->press);
        border = accent;
        text = accent;
        break;
    case 3:                         /* flat */
        fill = p->hover > 0 || p->press > 0 ? rf_blend(rf_blend(t->window, t->hot, p->hover), t->pressed, p->press)
                                           : RF_NONE;
        border = RF_NONE;
        text = p->fore;
        break;
    default:
        fill = rf_blend(p->back, t->hot, p->hover);
        fill = rf_blend(fill, t->pressed, p->press);
        border = rf_blend(t->border, t->hot_border, p->hover > p->press ? p->hover : p->press);
        text = p->fore;
    }
    if (p->has_back && b->style != 3) fill = rf_blend(p->back, t->pressed, p->press);
    if (!p->enabled) {
        text = t->disabled_text;
        border = t->border;
    }
    rf_draw_rect(p, 0, 0, p->width, p->height, fill, border, bw, radius);
    if (p->focused)
        rf_draw_rect(p, bw + 2, bw + 2, p->width - 2 * bw - 4, p->height - 2 * bw - 4, RF_NONE,
                     rf_blend(border, text, 0.5), 1, radius > 2 ? radius - 2 : 0);
    rf_draw_text(p, p->text, rf_px(p, t->padding), 0, p->width - 2 * rf_px(p, t->padding), p->height, text,
                 RF_ALIGN_CENTER | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
}

RF_MODULE(buttonx) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "ButtonX";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.create = bx_create;
    k.destroy = bx_destroy;
    k.set = bx_set;
    k.get = bx_get;
    k.paint = bx_paint;
    k.properties = "Style,Radius,AccentColor";
    k.events = "Click";
    rf_register_class(&k);
}
