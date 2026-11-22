/* RAD Modern indicators: RmProgress (linear bar / circle / marquee, optional percentage text, smooth
 * value animation) and RmGauge (circular dial or linear scale with coloured ranges, needle, unit).
 *
 * RF_CLASSES: RmProgress RmGauge
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* ================================================================== RmProgress */
enum { PK_BAR, PK_CIRCLE, PK_MARQUEE };
static const char *const PKINDS[] = {"Bar", "Circle", "Marquee"};

typedef struct {
    rm_look look;
    double value, minv, maxv;
    int kind, show_text, phase;
    rm_anim shown;          /* animated value (0..1) */
    char *format;
} RmProgress;

static int RF_CALL pr_create(rf_handle h, void **state) {
    RmProgress *p = (RmProgress *)calloc(1, sizeof *p);
    (void)h;
    if (!p) return 0;
    p->maxv = 100;
    p->format = rm_strdup("");
    *state = p;
    return 1;
}

static void RF_CALL pr_destroy(rf_handle h, void *state) {
    RmProgress *p = (RmProgress *)state;
    rf_set_timer(h, RM_ANIM_TIMER, 0);
    if (p) free(p->format);
    free(p);
}

static double pr_frac(RmProgress *p) {
    double f = p->maxv > p->minv ? (p->value - p->minv) / (p->maxv - p->minv) : 0;
    return f < 0 ? 0 : f > 1 ? 1 : f;
}

static void pr_retarget(rf_handle h, RmProgress *p) {
    HWND hw = (HWND)rf_hwnd(h);
    p->shown.target = pr_frac(p);
    if (p->kind == PK_MARQUEE || (hw && IsWindowVisible(hw) && rf_theme_current()->anim_ms > 0)) rf_set_timer(h, RM_ANIM_TIMER, 16);
    else p->shown.v = p->shown.target;
    rf_invalidate(h);
}

static int RF_CALL pr_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmProgress *p = (RmProgress *)state;
    if (rm_look_set(&p->look, prop, v)) return 1;
    if (rm_ieq(prop, "Value")) { p->value = rad_num(v); pr_retarget(h, p); return 1; }
    if (rm_ieq(prop, "Minimum") || rm_ieq(prop, "Min")) { p->minv = rad_num(v); pr_retarget(h, p); return 1; }
    if (rm_ieq(prop, "Maximum") || rm_ieq(prop, "Max")) { p->maxv = rad_num(v); pr_retarget(h, p); return 1; }
    if (rm_ieq(prop, "Kind")) {
        int i;
        p->kind = PK_BAR;
        for (i = 0; i < 3; i++)
            if (rm_ieq(v, PKINDS[i])) p->kind = i;
        pr_retarget(h, p);
        if (p->kind != PK_MARQUEE && p->shown.v == p->shown.target) rf_set_timer(h, RM_ANIM_TIMER, 0);
        return 1;
    }
    if (rm_ieq(prop, "ShowText")) { p->show_text = rm_bool(v); return 1; }
    if (rm_ieq(prop, "TextFormat")) { rm_setstr(&p->format, v); return 1; }
    return 0;
}

static const char *RF_CALL pr_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmProgress *p = (RmProgress *)state;
    const char *r = rm_look_get(&p->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Value")) return rad_str(p->value);
    if (rm_ieq(prop, "Minimum") || rm_ieq(prop, "Min")) return rad_str(p->minv);
    if (rm_ieq(prop, "Maximum") || rm_ieq(prop, "Max")) return rad_str(p->maxv);
    if (rm_ieq(prop, "Kind")) return PKINDS[p->kind];
    if (rm_ieq(prop, "ShowText")) return rm_tf(p->show_text);
    if (rm_ieq(prop, "TextFormat")) return p->format;
    return NULL;
}

static const char *RF_CALL pr_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmProgress *p = (RmProgress *)state;
    if (rm_ieq(m, "Increment") || rm_ieq(m, "PerformStep")) {
        double d = *rm_arg(args, 0) ? rad_num(rm_arg(args, 0)) : 1;
        p->value += d;
        if (p->value > p->maxv) p->value = p->maxv;
        if (p->value < p->minv) p->value = p->minv;
        pr_retarget(h, p);
        return rad_str(p->value);
    }
    return NULL;
}

static int RF_CALL pr_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmProgress *p = (RmProgress *)state;
    (void)l;
    if (p && msg == WM_TIMER && w == RM_ANIM_TIMER) {
        int moving = rm_anim_step(&p->shown, 0.04);
        if (p->kind == PK_MARQUEE) p->phase = (p->phase + 3) % 200;
        else if (!moving) rf_set_timer(h, RM_ANIM_TIMER, 0);
        rf_invalidate(h);
        *res = 0;
        return 1;
    }
    return 0;
}

static const char *pr_text(RmProgress *p) {
    static char b[64];
    if (*p->format) {
        const char *s = strstr(p->format, "{0}");
        char num[32];
        snprintf(num, sizeof num, "%s", rad_str(floor(pr_frac(p) * 100 + 0.5)));
        if (s) snprintf(b, sizeof b, "%.*s%s%s", (int)(s - p->format), p->format, num, s + 3);
        else snprintf(b, sizeof b, "%s", p->format);
        return b;
    }
    snprintf(b, sizeof b, "%d%%", (int)floor(pr_frac(p) * 100 + 0.5));
    return b;
}

static void RF_CALL pr_paint(rf_handle h, void *state, const rf_paint *pt) {
    RmProgress *p = (RmProgress *)state;
    const rf_theme *t = rm_look_theme(&p->look, pt);
    unsigned accent = rm_look_accent(&p->look, t), back = pt->has_back ? pt->back : t->window;
    unsigned track = rf_blend(back, t->window_text, t->dark ? 0.18 : 0.12), fg = pt->has_fore ? pt->fore : t->window_text;
    double f = p->shown.v;
    (void)h;
    if (pt->has_back) rm_fill(pt, 0, 0, pt->width, pt->height, pt->back);
    if (!pt->enabled) accent = rf_blend(t->border, back, 0.2);
    if (p->kind == PK_CIRCLE) {
        double s = pt->width < pt->height ? pt->width : pt->height, lw = s / 10 < 3 ? 3 : s / 10;
        double x = (pt->width - s) / 2 + lw / 2, y = (pt->height - s) / 2 + lw / 2, d = s - lw;
        rm_ellipse(pt, x, y, d, d, RF_NONE, track, lw);
        if (f > 0) rm_arc(pt, x, y, d, d, -90, 360 * f, accent, lw);
        if (p->show_text || s >= rf_px(pt, 40)) {
            HGDIOBJ o = rm_font_push(pt, s >= rf_px(pt, 80) ? 1.6 : 1.0, 1);
            rf_draw_text(pt, pr_text(p), 0, 0, pt->width, pt->height, fg, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
            rm_font_pop(pt, o);
        }
        return;
    }
    {
        int text_h = p->show_text && pt->height < rf_px(pt, 18) ? 0 : 0;
        int bh = pt->height >= rf_px(pt, 14) && !p->show_text ? rf_px(pt, 6) : pt->height;
        int by = (pt->height - bh) / 2, r = bh / 2;
        (void)text_h;
        if (p->show_text && pt->height >= rf_px(pt, 14)) { bh = pt->height; by = 0; r = rf_px(pt, t->radius + 1); }
        rf_draw_rect(pt, 0, by, pt->width, bh, track, RF_NONE, 0, r);
        if (p->kind == PK_MARQUEE) {
            int seg = pt->width / 3, x = (int)((pt->width + seg) * p->phase / 200.0) - seg;
            int x0 = x < 0 ? 0 : x, x1 = x + seg > pt->width ? pt->width : x + seg;
            if (x1 > x0) rf_draw_rect(pt, x0, by, x1 - x0, bh, accent, RF_NONE, 0, r);
        } else if (f > 0) {
            int w = (int)(pt->width * f + 0.5);
            if (w < 2 * r) w = w < 1 ? 1 : (r > 0 ? (w < 2 * r ? 2 * r : w) : w);
            if (w > pt->width) w = pt->width;
            rf_draw_rect(pt, 0, by, w, bh, accent, RF_NONE, 0, r);
        }
        if (p->show_text && p->kind != PK_MARQUEE) {
            const char *txt = pr_text(p);
            int split = (int)(pt->width * f + 0.5);
            HRGN rg;
            rf_draw_text(pt, txt, 0, 0, pt->width, pt->height, fg, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
            rg = CreateRectRgn(0, 0, split, pt->height);   /* text over the bar in the accent's text colour */
            SelectClipRgn((HDC)pt->hdc, rg);
            rf_draw_text(pt, txt, 0, 0, pt->width, pt->height, rm_on(accent), RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
            SelectClipRgn((HDC)pt->hdc, NULL);
            DeleteObject(rg);
        }
    }
}

/* ================================================================== RmGauge */
typedef struct { double a, b; unsigned c; } Range;
typedef struct {
    rm_look look;
    double value, minv, maxv;
    int linear, nranges, decimals, show_ticks;
    Range ranges[16];
    char *src, *unit, *title;
    rm_anim shown;
} RmGauge;

static int RF_CALL ga_create(rf_handle h, void **state) {
    RmGauge *g = (RmGauge *)calloc(1, sizeof *g);
    (void)h;
    if (!g) return 0;
    g->maxv = 100;
    g->show_ticks = 1;
    g->src = rm_strdup("");
    g->unit = rm_strdup("");
    g->title = rm_strdup("");
    *state = g;
    return 1;
}

static void RF_CALL ga_destroy(rf_handle h, void *state) {
    RmGauge *g = (RmGauge *)state;
    rf_set_timer(h, RM_ANIM_TIMER, 0);
    if (!g) return;
    free(g->src); free(g->unit); free(g->title);
    free(g);
}

static void ga_ranges(RmGauge *g, const char *v) {
    rm_list l = {0, 0, 0};
    int i;
    rm_list_parse(&l, v, ';');
    g->nranges = 0;
    for (i = 0; i < l.n && g->nranges < 16; i++) {
        double a, b;
        char col[32] = "";
        const char *s = l.v[i];
        if (sscanf(s, "%lf-%lf:%31s", &a, &b, col) == 3 || sscanf(s, "%lf - %lf : %31s", &a, &b, col) == 3) {
            Range *r = &g->ranges[g->nranges];
            if (!rm_color(col, &r->c)) continue;
            r->a = a;
            r->b = b;
            g->nranges++;
        }
    }
    rm_list_free(&l);
}

static void ga_retarget(rf_handle h, RmGauge *g) {
    HWND hw = (HWND)rf_hwnd(h);
    g->shown.target = g->value;
    if (hw && IsWindowVisible(hw) && rf_theme_current()->anim_ms > 0) rf_set_timer(h, RM_ANIM_TIMER, 16);
    else g->shown.v = g->value;
    rf_invalidate(h);
}

static int RF_CALL ga_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmGauge *g = (RmGauge *)state;
    if (rm_look_set(&g->look, prop, v)) return 1;
    if (rm_ieq(prop, "Value")) {
        g->value = rad_num(v);
        if (g->value < g->minv) g->value = g->minv;
        if (g->value > g->maxv) g->value = g->maxv;
        ga_retarget(h, g);
        return 1;
    }
    if (rm_ieq(prop, "Minimum") || rm_ieq(prop, "Min")) { g->minv = rad_num(v); return 1; }
    if (rm_ieq(prop, "Maximum") || rm_ieq(prop, "Max")) { g->maxv = rad_num(v); return 1; }
    if (rm_ieq(prop, "Ranges")) { rm_setstr(&g->src, v); ga_ranges(g, v); return 1; }
    if (rm_ieq(prop, "Unit")) { rm_setstr(&g->unit, v); return 1; }
    if (rm_ieq(prop, "Title")) { rm_setstr(&g->title, v); return 1; }
    if (rm_ieq(prop, "Kind")) { g->linear = rm_ieq(v, "Linear"); return 1; }
    if (rm_ieq(prop, "Decimals")) { g->decimals = rm_int(v); return 1; }
    if (rm_ieq(prop, "ShowTicks")) { g->show_ticks = rm_bool(v); return 1; }
    return 0;
}

static const char *RF_CALL ga_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmGauge *g = (RmGauge *)state;
    const char *r = rm_look_get(&g->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Value")) return rad_str(g->value);
    if (rm_ieq(prop, "Minimum") || rm_ieq(prop, "Min")) return rad_str(g->minv);
    if (rm_ieq(prop, "Maximum") || rm_ieq(prop, "Max")) return rad_str(g->maxv);
    if (rm_ieq(prop, "Ranges")) return g->src;
    if (rm_ieq(prop, "Unit")) return g->unit;
    if (rm_ieq(prop, "Title")) return g->title;
    if (rm_ieq(prop, "Kind")) return g->linear ? "Linear" : "Circular";
    if (rm_ieq(prop, "Decimals")) return rad_str(g->decimals);
    if (rm_ieq(prop, "ShowTicks")) return rm_tf(g->show_ticks);
    return NULL;
}

static int RF_CALL ga_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmGauge *g = (RmGauge *)state;
    (void)l;
    if (g && msg == WM_TIMER && w == RM_ANIM_TIMER) {
        double span = g->maxv - g->minv;
        if (!rm_anim_step(&g->shown, (span > 0 ? span : 1) / 40.0)) rf_set_timer(h, RM_ANIM_TIMER, 0);
        rf_invalidate(h);
        *res = 0;
        return 1;
    }
    return 0;
}

static unsigned ga_color_at(RmGauge *g, double v, unsigned def) {
    int i;
    for (i = 0; i < g->nranges; i++)
        if (v >= g->ranges[i].a && v <= g->ranges[i].b) return g->ranges[i].c;
    return def;
}

static void RF_CALL ga_paint(rf_handle h, void *state, const rf_paint *p) {
    RmGauge *g = (RmGauge *)state;
    const rf_theme *t = rm_look_theme(&g->look, p);
    unsigned accent = rm_look_accent(&g->look, t), back = p->has_back ? p->back : t->window;
    unsigned fg = p->has_fore ? p->fore : t->window_text, track = rf_blend(back, t->window_text, t->dark ? 0.18 : 0.1);
    double span = g->maxv - g->minv, v = g->shown.v;
    char val[64];
    int i;
    (void)h;
    if (span <= 0) span = 1;
    if (p->has_back) rm_fill(p, 0, 0, p->width, p->height, p->back);
    snprintf(val, sizeof val, "%.*f", g->decimals < 0 ? 0 : g->decimals > 6 ? 6 : g->decimals, g->value);
    if (g->linear) {
        int pad = rf_px(p, 8), bh = rf_px(p, 10), th = rm_text_h(p);
        int y = p->height - pad - th - bh, x0 = pad, x1 = p->width - pad;
        rf_draw_rect(p, x0, y, x1 - x0, bh, track, RF_NONE, 0, bh / 2);
        for (i = 0; i < g->nranges; i++) {
            double a = (g->ranges[i].a - g->minv) / span, b = (g->ranges[i].b - g->minv) / span;
            int ra = x0 + (int)((x1 - x0) * (a < 0 ? 0 : a)), rb = x0 + (int)((x1 - x0) * (b > 1 ? 1 : b));
            if (rb > ra) rf_draw_rect(p, ra, y + bh - rf_px(p, 3), rb - ra, rf_px(p, 3), g->ranges[i].c, RF_NONE, 0, 0);
        }
        {
            double f = (v - g->minv) / span;
            int x = x0 + (int)((x1 - x0) * (f < 0 ? 0 : f > 1 ? 1 : f));
            double tri[6];
            rf_draw_rect(p, x0, y, x - x0, bh - rf_px(p, 3), ga_color_at(g, g->value, accent), RF_NONE, 0, (bh - rf_px(p, 3)) / 2);
            tri[0] = x - rf_px(p, 6); tri[1] = y - rf_px(p, 9); tri[2] = x + rf_px(p, 6); tri[3] = y - rf_px(p, 9);
            tri[4] = x; tri[5] = y - rf_px(p, 1);
            rm_polygon(p, tri, 3, fg);
        }
        {
            char txt[160];
            HGDIOBJ o = rm_font_push(p, 1.0, 1);
            snprintf(txt, sizeof txt, "%s%s%s", val, *g->unit ? " " : "", g->unit);
            rf_draw_text(p, *g->title ? g->title : p->text, x0, y + bh + rf_px(p, 2), x1 - x0, th, fg, RF_ALIGN_LEFT);
            rf_draw_text(p, txt, x0, y + bh + rf_px(p, 2), x1 - x0, th, fg, RF_ALIGN_RIGHT);
            rm_font_pop(p, o);
        }
        return;
    }
    {
        double s = p->width < p->height * 0.98 ? p->width : p->height * 0.98, lw = s / 12 < 4 ? 4 : s / 12;
        double d = s - lw - rf_px(p, 4), x = (p->width - d) / 2, y = (p->height - d * 0.88) / 2 + rf_px(p, 2);
        double cx = x + d / 2, cy = y + d / 2, start = 135, sweep = 270, f = (v - g->minv) / span;
        if (f < 0) f = 0;
        if (f > 1) f = 1;
        rm_arc(p, x, y, d, d, start, sweep, track, lw);
        for (i = 0; i < g->nranges; i++) {
            double a = (g->ranges[i].a - g->minv) / span, b = (g->ranges[i].b - g->minv) / span;
            if (a < 0) a = 0;
            if (b > 1) b = 1;
            if (b > a) rm_arc(p, x + lw * 0.85, y + lw * 0.85, d - lw * 1.7, d - lw * 1.7, start + sweep * a, sweep * (b - a),
                              g->ranges[i].c, lw * 0.3);
        }
        if (f > 0) rm_arc(p, x, y, d, d, start, sweep * f, ga_color_at(g, g->value, accent), lw);
        if (g->show_ticks) {
            for (i = 0; i <= 10; i++) {
                double a = (start + sweep * i / 10.0) * M_PI / 180, r0 = d / 2 - lw * 1.4, r1 = r0 - (i % 5 ? lw * 0.4 : lw * 0.8);
                double xy[4];
                xy[0] = cx + cos(a) * r0; xy[1] = cy + sin(a) * r0; xy[2] = cx + cos(a) * r1; xy[3] = cy + sin(a) * r1;
                rm_lines(p, xy, 2, rf_blend(fg, back, 0.45), i % 5 ? 1 : rf_px(p, 1.5));
            }
        }
        {   /* needle */
            double a = (start + sweep * f) * M_PI / 180, r = d / 2 - lw * 1.2, nw = lw * 0.45 < 2 ? 2 : lw * 0.45;
            double tri[6];
            tri[0] = cx + cos(a) * r; tri[1] = cy + sin(a) * r;
            tri[2] = cx + cos(a + M_PI / 2) * nw; tri[3] = cy + sin(a + M_PI / 2) * nw;
            tri[4] = cx + cos(a - M_PI / 2) * nw; tri[5] = cy + sin(a - M_PI / 2) * nw;
            rm_polygon(p, tri, 3, fg);
            rm_ellipse(p, cx - nw * 1.6, cy - nw * 1.6, nw * 3.2, nw * 3.2, fg, RF_NONE, 0);
        }
        {
            HGDIOBJ o = rm_font_push(p, d >= rf_px(p, 120) ? 1.7 : 1.15, 1);
            int th = rm_text_h(p), vy = (int)(cy + d * 0.16 + (lw * 0.45 < 2 ? 2 : lw * 0.45) * 1.6);
            char txt[160];
            snprintf(txt, sizeof txt, "%s%s%s", val, *g->unit ? " " : "", g->unit);
            rf_draw_text(p, txt, (int)x, vy, (int)d, th, fg, RF_ALIGN_CENTER);
            rm_font_pop(p, o);
            if (*g->title || *p->text) {
                int ty = vy + th;
                rf_draw_text(p, *g->title ? g->title : p->text, (int)x, ty, (int)d, rm_text_h(p) + 2, rf_blend(fg, back, 0.3),
                             RF_ALIGN_CENTER | RF_ALIGN_ELLIPSIS);
            }
        }
    }
}

RF_MODULE(rm_progress) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmProgress";
    k.flags = RF_CLASS_OWNERDRAW;
    k.create = pr_create; k.destroy = pr_destroy; k.set = pr_set; k.get = pr_get; k.invoke = pr_invoke;
    k.paint = pr_paint; k.message = pr_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Value,Minimum,Maximum,Kind,ShowText,TextFormat";
    k.events = "Click";
    k.methods = "Increment,PerformStep";
    rf_register_class(&k);
    k.name = "RmGauge";
    k.flags = RF_CLASS_OWNERDRAW;
    k.create = ga_create; k.destroy = ga_destroy; k.set = ga_set; k.get = ga_get; k.invoke = NULL;
    k.paint = ga_paint; k.message = ga_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Value,Minimum,Maximum,Ranges,Unit,Title,Kind,Decimals,ShowTicks";
    k.events = "Click";
    k.methods = "";
    rf_register_class(&k);
}
