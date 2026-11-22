/* radforms_motion.inc - animations, visual states and layout variants of radforms (included by radforms.c).
 *
 * The same semantics as the IDE's Python runtime (radide/motion/runtime_py.py _RadFx, features/timeline.py
 * _Storyboard, features/states.py _VisualStates, variants/runtime_py.py _RadVariants), driven by the records
 * radide/motion/native_plan.py adds to a form of the description (after its controls):
 *
 *   XR respect                                  the form respects the reduced-motion setting
 *   X  fx target count forever autorev delay restore   storyboard ("" target = the form)
 *   XT on source interval after leave           its trigger (load click hover timer show hide after manual)
 *   K  prop ms ease kind a b c d                keyframe; kind n number, c colour, b bool, s text,
 *                                               r relative (start*a + b + d*start(c)), p parent colour,
 *                                               v typewriter (start text up to fraction a)
 *   Q  control state prop value                 visual state override ("" control = the form)
 *   V  size minW maxW minH maxH orientation posture span fold     layout size
 *   VL size control "x y w h rx ry rw rh"       place of the control on that size
 *   VP size control prop value                  property on that size
 *
 * Program API (rad_call / rf_invoke on the form): BeginAnimation(name), StopAnimation(name),
 * GoToState(state[, control]) (also on a control: GoToState(state)), ApplySizeVariants(); properties
 * CurrentSizes, CurrentState; events <Form>_SizeVariantChanged, <storyboard>_Completed.
 * RADIDE_REDUCED_MOTION=1 (or Windows "Show animations" off) ends every animation at once when the form
 * respects reduced motion. RADIDE_POSTURE / RADIDE_SPAN / RADIDE_HINGE simulate a foldable. */

#define RF_FX_FRAME 0x7D00
#define RF_FX_DELAY 0x7E00          /* + storyboard index */
#define RF_FX_EVERY 0x7F00          /* + storyboard index */
#define RF_FX_MAX 250

enum { FXK_NUM, FXK_COLOR, FXK_BOOL, FXK_TEXT, FXK_REL, FXK_PARENT, FXK_REVEAL };
enum { FXP_NUM, FXP_COLOR, FXP_BOOL, FXP_TEXT };
enum { FXT_LOAD, FXT_CLICK, FXT_HOVER, FXT_TIMER, FXT_SHOW, FXT_HIDE, FXT_AFTER, FXT_MANUAL };
enum { FXE_LINEAR, FXE_IN, FXE_OUT, FXE_INOUT, FXE_SINE, FXE_BACK, FXE_ELASTIC, FXE_BOUNCE };
#define FXF_OVER 1
#define FXF_PRESSED 2
#define FXF_FOCUSED 4
#define FXF_DISABLED 8

typedef struct RfFxKey {
    int ms, ease, kind, of;          /* of: 0, 'W' (start Width), 'H' (start Height) */
    double a, b, d;
    char *s;                         /* FXK_TEXT */
    double rv;                       /* resolved number / colour */
    wchar_t *rs;                     /* resolved text */
} RfFxKey;

typedef struct RfFxTrack {
    char prop[24];
    int pt, nk;
    RfFxKey *k;
    double s_num;                    /* value at Begin (number / colour / bool) */
    wchar_t *s_text;
    int last_bool;                   /* Visible: last value written (-1 none) */
} RfFxTrack;

typedef struct RfFxSb {
    char fx[64], tname[64], src[64], after[64];
    RfCtl *c;                        /* NULL = the form */
    int count, forever, autorev, delay, restore, on, interval, leave;
    int ntr, dur;
    RfFxTrack *tr;
    int playing, rev, hiding, saved, pending, every;
    double t0, pos;
    float pl0[8];
    int has_pl0;
} RfFxSb;

typedef struct RfFxQ { RfCtl *c; int form; char state[48], prop[24]; char *val; } RfFxQ;
typedef struct RfFxAp { RfCtl *c; char prop[24]; char *saved, *val; } RfFxAp;
typedef struct RfFxFl { RfCtl *c; int flags; char manual[48]; } RfFxFl;
typedef struct RfFxSize { char id[48]; double mnw, mxw, mnh, mxh; char orient[12], posture[16], span[12], fold[12]; } RfFxSize;
typedef struct RfFxVL { int size; RfCtl *c; float pl[8]; } RfFxVL;
typedef struct RfFxVP { int size; RfCtl *c; char prop[24]; char *val; } RfFxVP;
typedef struct RfFxBase { RfCtl *c; float pl[8]; } RfFxBase;
typedef struct RfFxBP { RfCtl *c; char prop[24]; char *val; } RfFxBP;

typedef struct RfFx {
    int respect, reduced, started;
    int nsb; RfFxSb *sb;
    int nq; RfFxQ *q;
    int nap; RfFxAp *ap;
    int nfl; RfFxFl *fl;
    char state[48];
    int nsz; RfFxSize *sz;
    int nvl; RfFxVL *vl;
    int nvp; RfFxVP *vp;
    int nbase; RfFxBase *base;
    int nbp; RfFxBP *bp;
    unsigned char cur[64];
    int has_cur, frame_on;
} RfFx;

static int g_fx_quiet;

#define FX_PUSH(arr, n, T) ((arr) = (T *)realloc((arr), sizeof(T) * (size_t)((n) + 1)), memset(&(arr)[(n)], 0, sizeof(T)), &(arr)[(n)++])

static double rf_fx_now(void) {
    static LARGE_INTEGER fq;
    LARGE_INTEGER t;
    if (!fq.QuadPart) QueryPerformanceFrequency(&fq);
    QueryPerformanceCounter(&t);
    return (double)t.QuadPart * 1000.0 / (double)fq.QuadPart;
}

static int rf_fx_envtrue(const char *name, int *set) {
    char b[32];
    DWORD n = GetEnvironmentVariableA(name, b, sizeof b);
    int i;
    *set = 0;
    if (!n || n >= sizeof b) return 0;
    for (i = 0; b[i]; i++) b[i] = (char)tolower((unsigned char)b[i]);
    for (i = (int)strlen(b); i > 0 && b[i - 1] == ' '; i--) b[i - 1] = 0;
    if (!*b) return 0;
    *set = 1;
    return strcmp(b, "1") == 0 || strcmp(b, "true") == 0 || strcmp(b, "yes") == 0 || strcmp(b, "on") == 0;
}

static int rf_fx_reduced_system(void) {
    int set, v = rf_fx_envtrue("RADIDE_REDUCED_MOTION", &set);
    BOOL on = TRUE;
    if (set) return v;
    if (SystemParametersInfoW(0x1042 /* SPI_GETCLIENTAREAANIMATION */, 0, &on, 0)) return !on;
    return 0;
}

static int rf_fx_ease_of(const char *s) {
    if (rf_ieq(s, "in")) return FXE_IN;
    if (rf_ieq(s, "out")) return FXE_OUT;
    if (rf_ieq(s, "inout")) return FXE_INOUT;
    if (rf_ieq(s, "sine")) return FXE_SINE;
    if (rf_ieq(s, "back")) return FXE_BACK;
    if (rf_ieq(s, "elastic")) return FXE_ELASTIC;
    if (rf_ieq(s, "bounce")) return FXE_BOUNCE;
    return FXE_LINEAR;
}

static double rf_fx_ease(double f, int e) {
    switch (e) {
    case FXE_IN: return f * f;
    case FXE_OUT: return 1 - (1 - f) * (1 - f);
    case FXE_INOUT: return f < 0.5 ? 2 * f * f : 1 - 2 * (1 - f) * (1 - f);
    case FXE_SINE: return -(cos(3.14159265358979 * f) - 1) / 2;
    case FXE_BACK: return 1 + 2.70158 * pow(f - 1, 3) + 1.70158 * pow(f - 1, 2);
    case FXE_ELASTIC:
        if (f <= 0 || f >= 1) return f >= 1 ? 1.0 : 0.0;
        return pow(2, -10 * f) * sin((f * 10 - 0.75) * (2 * 3.14159265358979 / 3)) + 1;
    case FXE_BOUNCE: {
        double n = 7.5625, d = 2.75;
        if (f < 1 / d) return n * f * f;
        if (f < 2 / d) { f -= 1.5 / d; return n * f * f + 0.75; }
        if (f < 2.5 / d) { f -= 2.25 / d; return n * f * f + 0.9375; }
        f -= 2.625 / d;
        return n * f * f + 0.984375;
    }
    default: return f;
    }
}

static int rf_fx_ptype(const char *p) {
    if (rf_ieq(p, "BackColor") || rf_ieq(p, "ForeColor")) return FXP_COLOR;
    if (rf_ieq(p, "Visible") || rf_ieq(p, "FontBold") || rf_ieq(p, "FontItalic") || rf_ieq(p, "Enabled") ||
        rf_ieq(p, "Checked")) return FXP_BOOL;
    if (rf_ieq(p, "Text") || rf_ieq(p, "Caption")) return FXP_TEXT;
    return FXP_NUM;
}

static int rf_fx_intprop(const char *p) {
    return rf_ieq(p, "Left") || rf_ieq(p, "Top") || rf_ieq(p, "Width") || rf_ieq(p, "Height") ||
           rf_ieq(p, "FontSize") || rf_ieq(p, "Value");
}

static int rf_fx_geo(const char *p) {
    return rf_ieq(p, "Left") || rf_ieq(p, "Top") || rf_ieq(p, "Width") || rf_ieq(p, "Height");
}

static wchar_t *rf_fx_wdup(const wchar_t *s, size_t n) {
    wchar_t *w = (wchar_t *)malloc((n + 1) * sizeof(wchar_t));
    if (!w) return NULL;
    if (n) memcpy(w, s, n * sizeof(wchar_t));
    w[n] = 0;
    return w;
}

/* ------------------------------------------------------------------ property access */
static COLORREF rf_fx_color_get(RfForm *f, RfCtl *c, const char *p) {
    COLORREF col;
    if (rf_ieq(p, "ForeColor")) {
        if (c && c->has_fore) return c->fore;
        return g_themed && g_theme ? (COLORREF)g_theme->window_text : GetSysColor(COLOR_BTNTEXT);
    }
    if (c) {
        rf_brush_for(c, &col);          /* its own colour, else the container's / form's */
        return col;
    }
    if (f->has_back) return f->back;
    return g_themed && g_theme ? (COLORREF)g_theme->window : GetSysColor(COLOR_BTNFACE);
}

static COLORREF rf_fx_parent_color(RfForm *f, RfCtl *c) {
    return rf_fx_color_get(f, c ? c->parent : NULL, "BackColor");
}

static double rf_fx_num_get(RfForm *f, RfCtl *c, const char *p) {
    if (!c && rf_ieq(p, "Opacity")) return f->alpha_set ? f->opacity : 1.0;
    if (c && rf_ieq(p, "Opacity")) return 1.0;
    return rad_num(rf_get(f, c, p));
}

static void rf_fx_write(RfForm *f, RfCtl *c, const char *p, const char *v) {
    g_fx_quiet++;
    rf_set(f, c, p, v);
    g_fx_quiet--;
}

static void rf_fx_num_set(RfForm *f, RfCtl *c, const char *p, double v) {
    char b[48];
    if (rf_ieq(p, "Opacity")) {
        if (c) return;                  /* child windows have no transparency (expand() blends colours) */
        if (v < 0) v = 0;
        if (v > 1) v = 1;
        snprintf(b, sizeof b, "%.4f", v);
    } else if (rf_fx_intprop(p)) {
        snprintf(b, sizeof b, "%d", (int)floor(v + 0.5));
    } else {
        snprintf(b, sizeof b, "%.4f", v);
    }
    rf_fx_write(f, c, p, b);
}

static void rf_fx_color_set(RfForm *f, RfCtl *c, const char *p, COLORREF col) {
    char b[16];
    snprintf(b, sizeof b, "#%02X%02X%02X", GetRValue(col), GetGValue(col), GetBValue(col));
    rf_fx_write(f, c, p, b);
}

static wchar_t *rf_fx_text_get(RfForm *f, RfCtl *c) {
    return rf_wide(rf_get(f, c, "Text"));
}

static void rf_fx_text_set(RfForm *f, RfCtl *c, const wchar_t *w) {
    rf_fx_write(f, c, "Text", rf_utf8(w ? w : L""));
}

/* ------------------------------------------------------------------ storyboards */
static RfFx *FX(RfForm *f) { return (RfFx *)f->fx; }

static void rf_fx_forget(RfFxSb *sb) {
    int i, j;
    for (i = 0; i < sb->ntr; i++) {
        RfFxTrack *t = &sb->tr[i];
        free(t->s_text);
        t->s_text = NULL;
        for (j = 0; j < t->nk; j++) { free(t->k[j].rs); t->k[j].rs = NULL; }
    }
    sb->saved = 0;
}

/* the values at Begin; relative keys made absolute against them (_Storyboard._remember) */
static void rf_fx_remember(RfForm *f, RfFxSb *sb) {
    int i, j;
    double sw, sh;
    if (sb->saved) return;
    sb->saved = 1;
    sb->has_pl0 = 0;
    sw = rf_fx_num_get(f, sb->c, "Width");
    sh = rf_fx_num_get(f, sb->c, "Height");
    for (i = 0; i < sb->ntr; i++) {
        RfFxTrack *t = &sb->tr[i];
        t->last_bool = -1;
        if (sb->c && rf_fx_geo(t->prop) && !sb->has_pl0) {
            memcpy(sb->pl0, sb->c->pl, sizeof sb->pl0);      /* Stop gives Anchor / Dock back */
            sb->has_pl0 = 1;
        }
        switch (t->pt) {
        case FXP_COLOR: t->s_num = (double)rf_fx_color_get(f, sb->c, t->prop); break;
        case FXP_BOOL: t->s_num = rf_bool(rf_get(f, sb->c, t->prop)); break;
        case FXP_TEXT: free(t->s_text); t->s_text = rf_fx_text_get(f, sb->c); break;
        default: t->s_num = rf_fx_num_get(f, sb->c, t->prop); break;
        }
        for (j = 0; j < t->nk; j++) {
            RfFxKey *k = &t->k[j];
            free(k->rs);
            k->rs = NULL;
            switch (k->kind) {
            case FXK_PARENT: k->rv = t->pt == FXP_COLOR ? (double)rf_fx_parent_color(f, sb->c) : t->s_num; break;
            case FXK_REL:
                if (t->pt == FXP_NUM) {
                    double v = t->s_num * k->a + k->b + (k->of == 'W' ? k->d * sw : k->of == 'H' ? k->d * sh : 0);
                    if (rf_fx_intprop(t->prop)) v = floor(v + 0.5);
                    if (rf_ieq(t->prop, "Opacity")) v = v < 0 ? 0 : v > 1 ? 1 : v;
                    k->rv = v;
                } else if (t->pt == FXP_TEXT) {
                    k->rs = rf_fx_wdup(t->s_text ? t->s_text : L"", t->s_text ? wcslen(t->s_text) : 0);
                } else {
                    k->rv = t->s_num;               /* colours / bools keep their start value */
                }
                break;
            case FXK_REVEAL: {
                size_t n = t->s_text ? wcslen(t->s_text) : 0;
                double fr = k->a < 0 ? 0 : k->a > 1 ? 1 : k->a;
                k->rs = rf_fx_wdup(t->s_text ? t->s_text : L"", (size_t)floor(n * fr + 0.5));
                break;
            }
            case FXK_TEXT: {
                wchar_t *w = rf_wide(k->s ? k->s : "");
                k->rs = w;
                break;
            }
            default: k->rv = k->a; break;     /* n / c / b */
            }
        }
    }
}

static double rf_fx_mixnum(double a, double b, double fr) { return a + (b - a) * fr; }

static COLORREF rf_fx_mixcol(COLORREF a, COLORREF b, double fr) {
    int r, g, bl;
    if (fr >= 1) return b;
    r = (int)floor(GetRValue(a) + (GetRValue(b) - GetRValue(a)) * fr + 0.5);
    g = (int)floor(GetGValue(a) + (GetGValue(b) - GetGValue(a)) * fr + 0.5);
    bl = (int)floor(GetBValue(a) + (GetBValue(b) - GetBValue(a)) * fr + 0.5);
    r = r < 0 ? 0 : r > 255 ? 255 : r;
    g = g < 0 ? 0 : g > 255 ? 255 : g;
    bl = bl < 0 ? 0 : bl > 255 ? 255 : bl;
    return RGB(r, g, bl);
}

/* text between two keys: typed / erased when one is a prefix of the other, else discrete */
static wchar_t *rf_fx_mixtext(const wchar_t *a, const wchar_t *b, double fr) {
    size_t la = wcslen(a), lb = wcslen(b), n;
    const wchar_t *longer = la > lb ? a : b;
    if (fr <= 0) return rf_fx_wdup(a, la);
    if ((la <= lb && wcsncmp(a, b, la) == 0) || (lb < la && wcsncmp(a, b, lb) == 0)) {
        double x = la + ((double)lb - (double)la) * (fr > 1 ? 1 : fr);
        n = (size_t)(x < 0 ? 0 : floor(x + 0.5));
        return rf_fx_wdup(longer, n);
    }
    return fr >= 1 ? rf_fx_wdup(b, lb) : rf_fx_wdup(a, la);
}

static void rf_fx_apply(RfForm *f, RfFxSb *sb, double ms) {
    int i, j;
    sb->pos = ms;
    for (i = 0; i < sb->ntr; i++) {
        RfFxTrack *t = &sb->tr[i];
        RfFxKey *k = t->k, *k0 = NULL, *k1 = NULL;
        double v0, v1, fr = 1;
        const wchar_t *s0, *s1;
        int lead = t->nk && k[0].ms > 0;      /* the start value is the implicit key at 0 */
        if (!t->nk) continue;
        if (ms <= (lead ? 0 : k[0].ms)) {
            if (lead) { v0 = v1 = t->s_num; s0 = s1 = t->s_text ? t->s_text : L""; fr = 1; }
            else { v0 = v1 = k[0].rv; s0 = s1 = k[0].rs ? k[0].rs : L""; fr = 1; }
        } else {
            for (j = 0; j < t->nk; j++)
                if (ms <= k[j].ms) { k1 = &k[j]; k0 = j ? &k[j - 1] : NULL; break; }
            if (!k1) {
                k1 = &k[t->nk - 1];
                v0 = v1 = k1->rv;
                s0 = s1 = k1->rs ? k1->rs : L"";
                fr = 1;
            } else {
                int t0 = k0 ? k0->ms : 0;
                v0 = k0 ? k0->rv : t->s_num;
                s0 = k0 ? (k0->rs ? k0->rs : L"") : (t->s_text ? t->s_text : L"");
                v1 = k1->rv;
                s1 = k1->rs ? k1->rs : L"";
                fr = k1->ms > t0 ? (ms - t0) / (double)(k1->ms - t0) : 1.0;
                fr = rf_fx_ease(fr, k1->ease);
            }
        }
        switch (t->pt) {
        case FXP_COLOR:
            rf_fx_color_set(f, sb->c, t->prop, fr <= 0 ? (COLORREF)v0 : rf_fx_mixcol((COLORREF)v0, (COLORREF)v1, fr));
            break;
        case FXP_BOOL: {
            int b = fr >= 1 ? (v1 != 0) : (v0 != 0);
            if (t->last_bool == b && rf_ieq(t->prop, "Visible")) break;   /* re-showing every frame re-places */
            t->last_bool = b;
            rf_fx_write(f, sb->c, t->prop, rf_tf(b));
            break;
        }
        case FXP_TEXT: {
            wchar_t *w = rf_fx_mixtext(s0, s1, fr);
            if (w) {
                wchar_t *cur = rf_fx_text_get(f, sb->c);
                if (!cur || wcscmp(cur, w) != 0) rf_fx_text_set(f, sb->c, w);
                free(cur);
                free(w);
            }
            break;
        }
        default:
            rf_fx_num_set(f, sb->c, t->prop, fr <= 0 ? v0 : rf_fx_mixnum(v0, v1, fr));
            break;
        }
    }
}

static void rf_fx_frame(RfForm *f) {
    RfFx *fx = FX(f);
    int i, any = 0;
    if (!fx) return;
    for (i = 0; i < fx->nsb; i++) any |= fx->sb[i].playing;
    if (any && !fx->frame_on) { SetTimer(f->hwnd, RF_FX_FRAME, 15, NULL); fx->frame_on = 1; }
    else if (!any && fx->frame_on) { KillTimer(f->hwnd, RF_FX_FRAME); fx->frame_on = 0; }
}

static void rf_fx_stop(RfForm *f, RfFxSb *sb) {
    int i;
    RfFx *fx = FX(f);
    sb->playing = sb->rev = 0;
    sb->pos = 0;
    if (sb->pending) { KillTimer(f->hwnd, RF_FX_DELAY + (UINT_PTR)(sb - fx->sb)); sb->pending = 0; }
    if (sb->saved) {
        for (i = 0; i < sb->ntr; i++) {
            RfFxTrack *t = &sb->tr[i];
            if (sb->c && rf_fx_geo(t->prop) && sb->has_pl0) continue;
            switch (t->pt) {
            case FXP_COLOR: rf_fx_color_set(f, sb->c, t->prop, (COLORREF)t->s_num); break;
            case FXP_BOOL: rf_fx_write(f, sb->c, t->prop, rf_tf(t->s_num != 0)); break;
            case FXP_TEXT: rf_fx_text_set(f, sb->c, t->s_text); break;
            default: rf_fx_num_set(f, sb->c, t->prop, t->s_num); break;
            }
        }
        if (sb->c && sb->has_pl0) {          /* Anchor / Dock take the control back */
            memcpy(sb->c->pl, sb->pl0, sizeof sb->pl0);
            rf_place_ctl(sb->c);
        }
        rf_fx_forget(sb);
    }
    rf_fx_frame(f);
}

static void rf_fx_begin_now(RfForm *f, RfFxSb *sb) {
    rf_fx_remember(f, sb);
    sb->playing = 1;
    sb->rev = 0;
    sb->t0 = rf_fx_now();
    rf_fx_apply(f, sb, 0);
    rf_fx_frame(f);
}

static void rf_fx_fx_begin(RfForm *f, RfFxSb *sb);

static int rf_fx_same_name_playing(RfFx *fx, RfFxSb *sb) {
    int i;
    for (i = 0; i < fx->nsb; i++)
        if (&fx->sb[i] != sb && fx->sb[i].playing && rf_ieq(fx->sb[i].fx, sb->fx)) return 1;
    return 0;
}

/* the end of a storyboard: hide / give back / chains / <name>_Completed (_RadFx._done + Completed) */
static void rf_fx_completed(RfForm *f, RfFxSb *sb) {
    RfFx *fx = FX(f);
    int i;
    sb->playing = 0;
    if (sb->hiding) {
        sb->hiding = 0;
        rf_fx_stop(f, sb);
        rf_fx_write(f, sb->c, "Visible", "False");
    } else if (sb->restore) {
        rf_fx_stop(f, sb);
    }
    for (i = 0; i < fx->nsb; i++)
        if (fx->sb[i].on == FXT_AFTER && rf_ieq(fx->sb[i].after, sb->fx)) rf_fx_fx_begin(f, &fx->sb[i]);
    if (!rf_fx_same_name_playing(fx, sb) && strncmp(sb->fx, "_fx_", 4) != 0)
        rf_post(f, sb->fx, "Completed", "", AFTER_NONE);
    rf_fx_frame(f);
}

static void rf_fx_finish(RfForm *f, RfFxSb *sb) {
    rf_fx_remember(f, sb);
    rf_fx_apply(f, sb, sb->autorev ? 0 : sb->dur);
    rf_fx_completed(f, sb);
}

static void rf_fx_tick(RfForm *f, RfFxSb *sb) {
    double ms = rf_fx_now() - sb->t0, span, total;
    int done = 0;
    if (!sb->playing) return;
    if (sb->rev) {
        double pos = sb->dur - ms;
        if (pos <= 0) { rf_fx_stop(f, sb); return; }
        rf_fx_apply(f, sb, pos);
        return;
    }
    span = (double)sb->dur * (sb->autorev ? 2 : 1);
    total = span * sb->count;
    if (span <= 0) { ms = 0; done = 1; }
    else if (sb->forever) {
        if (ms >= span) { sb->t0 += floor(ms / span) * span; ms = fmod(ms, span); }
    } else if (ms >= total) { ms = span; done = 1; }
    else ms = fmod(ms, span);
    rf_fx_apply(f, sb, ms <= sb->dur ? ms : span - ms);
    if (done) rf_fx_completed(f, sb);
}

/* _RadFx.Begin: reduced motion jumps to the end; a delay shows the first frame, then waits */
static void rf_fx_fx_begin(RfForm *f, RfFxSb *sb) {
    RfFx *fx = FX(f);
    if (fx->reduced) {
        if (!sb->playing) rf_fx_forget(sb);
        rf_fx_finish(f, sb);
        return;
    }
    if (!sb->playing) rf_fx_forget(sb);         /* start from the values the control has now */
    if (sb->delay > 0) {
        rf_fx_remember(f, sb);
        rf_fx_apply(f, sb, 0);
        sb->pending = 1;
        SetTimer(f->hwnd, RF_FX_DELAY + (UINT_PTR)(sb - fx->sb), (UINT)sb->delay, NULL);
    } else {
        rf_fx_begin_now(f, sb);
    }
}

static void rf_fx_reverse(RfForm *f, RfFxSb *sb) {
    if (sb->pending) { KillTimer(f->hwnd, RF_FX_DELAY + (UINT_PTR)(sb - FX(f)->sb)); sb->pending = 0; }
    if (FX(f)->reduced) { rf_fx_stop(f, sb); return; }
    if (!sb->saved) return;
    sb->playing = 1;
    sb->rev = 1;
    sb->t0 = rf_fx_now() - (sb->dur - (sb->pos < sb->dur ? sb->pos : sb->dur));
    rf_fx_frame(f);
}

static int rf_fx_by_name(RfForm *f, const char *name, int stop) {
    RfFx *fx = FX(f);
    int i, n = 0;
    char alt[80];
    if (!fx) return 0;
    snprintf(alt, sizeof alt, "_fx_%s", name ? name : "");
    for (i = 0; i < fx->nsb; i++) {
        RfFxSb *sb = &fx->sb[i];
        if (!rf_ieq(sb->fx, name) && !rf_ieq(alt, sb->fx)) continue;
        n++;
        if (stop) {
            if (sb->every) { KillTimer(f->hwnd, RF_FX_EVERY + (UINT_PTR)i); sb->every = 0; }
            sb->hiding = 0;
            rf_fx_stop(f, sb);
        } else {
            rf_fx_fx_begin(f, sb);
        }
    }
    return n;
}

/* ------------------------------------------------------------------ visual states */
static RfFxFl *rf_fx_flags(RfFx *fx, RfCtl *c, int create) {
    int i;
    for (i = 0; i < fx->nfl; i++)
        if (fx->fl[i].c == c) return &fx->fl[i];
    if (!create) return NULL;
    {
        RfFxFl *e = FX_PUSH(fx->fl, fx->nfl, RfFxFl);
        e->c = c;
        return e;
    }
}

static int rf_fx_has_states(RfFx *fx, RfCtl *c) {
    int i;
    for (i = 0; i < fx->nq; i++)
        if (!fx->q[i].form && fx->q[i].c == c) return 1;
    return 0;
}

typedef struct { const char *prop, *val; } RfFxWant;

static int rf_fx_want_add(RfFx *fx, RfCtl *c, int form, const char *state, RfFxWant *w, int n) {
    int i, j;
    for (i = 0; i < fx->nq; i++) {
        RfFxQ *q = &fx->q[i];
        if (q->form != form || (!form && q->c != c) || !rf_ieq(q->state, state)) continue;
        for (j = 0; j < n && !rf_ieq(w[j].prop, q->prop); j++) {}
        if (j == n) { if (n >= 32) continue; n++; }
        w[j].prop = q->prop;
        w[j].val = q->val;
    }
    return n;
}

/* _VisualStates._update: the wanted overrides of a control (NULL = the form) are applied, the others given back */
static void rf_fx_vsm_update(RfForm *f, RfCtl *c) {
    RfFx *fx = FX(f);
    RfFxWant w[32];
    int n = 0, i, j;
    RfFxFl *fl = c ? rf_fx_flags(fx, c, 0) : NULL;
    if (fx->state[0]) n = rf_fx_want_add(fx, c, c == NULL, fx->state, w, n);
    if (c) {
        if (fl && fl->manual[0]) n = rf_fx_want_add(fx, c, 0, fl->manual, w, n);
        else if (fl && (fl->flags & FXF_DISABLED)) n = rf_fx_want_add(fx, c, 0, "Disabled", w, n);
        else if (fl) {
            if (fl->flags & FXF_FOCUSED) n = rf_fx_want_add(fx, c, 0, "Focused", w, n);
            if (fl->flags & FXF_OVER) n = rf_fx_want_add(fx, c, 0, "MouseOver", w, n);
            if (fl->flags & FXF_PRESSED) n = rf_fx_want_add(fx, c, 0, "Pressed", w, n);
        }
    }
    for (i = 0; i < fx->nap;) {          /* overrides no longer wanted: the saved value back */
        RfFxAp *a = &fx->ap[i];
        if (a->c == c) {
            for (j = 0; j < n && !rf_ieq(w[j].prop, a->prop); j++) {}
            if (j == n) {
                rf_fx_write(f, c, a->prop, a->saved);
                free(a->saved);
                free(a->val);
                fx->ap[i] = fx->ap[--fx->nap];
                continue;
            }
        }
        i++;
    }
    for (j = 0; j < n; j++) {
        RfFxAp *a = NULL;
        for (i = 0; i < fx->nap; i++)
            if (fx->ap[i].c == c && rf_ieq(fx->ap[i].prop, w[j].prop)) { a = &fx->ap[i]; break; }
        if (a && a->val && strcmp(a->val, w[j].val) == 0) continue;
        if (!a) {
            a = FX_PUSH(fx->ap, fx->nap, RfFxAp);
            a->c = c;
            rf_copy(a->prop, w[j].prop, sizeof a->prop);
            a->saved = rf_strdup(rf_ieq(w[j].prop, "Opacity") && !c ? (f->alpha_set ? rad_str(f->opacity) : "1")
                                                                    : rf_get(f, c, w[j].prop));
        }
        free(a->val);
        a->val = rf_strdup(w[j].val);
        if (!(c && rf_ieq(w[j].prop, "Opacity"))) rf_fx_write(f, c, w[j].prop, w[j].val);
    }
}

static void rf_fx_flag(RfForm *f, RfCtl *c, int flag, int on) {
    RfFx *fx = FX(f);
    RfFxFl *fl;
    if (!c || !rf_fx_has_states(fx, c)) return;
    fl = rf_fx_flags(fx, c, 1);
    if (((fl->flags & flag) != 0) == (on != 0)) return;
    if (on) fl->flags |= flag;
    else fl->flags &= ~flag;
    rf_fx_vsm_update(f, c);
}

static int rf_fx_state_known(RfFx *fx, const char *s) {
    int i;
    for (i = 0; i < fx->nq; i++)
        if (rf_ieq(fx->q[i].state, s)) return 1;
    return 0;
}

static int rf_fx_goto_state(RfForm *f, RfCtl *c, const char *state) {
    RfFx *fx = FX(f);
    RfCtl *k;
    int i;
    const char *s = state && *state && !rf_ieq(state, "Base") ? state : "Normal";
    if (c) {
        RfFxFl *fl = rf_fx_flags(fx, c, 1);
        rf_copy(fl->manual, rf_ieq(s, "Normal") ? "" : s, sizeof fl->manual);
        rf_fx_vsm_update(f, c);
        return 1;
    }
    if (!rf_ieq(s, "Normal") && !rf_fx_state_known(fx, s)) return 0;
    rf_copy(fx->state, rf_ieq(s, "Normal") ? "" : s, sizeof fx->state);
    rf_fx_vsm_update(f, NULL);
    for (k = f->ctls; k; k = k->next) {
        int has = 0;
        for (i = 0; i < fx->nq && !has; i++) has = !fx->q[i].form && fx->q[i].c == k;
        if (has) rf_fx_vsm_update(f, k);
    }
    return 1;
}

/* ------------------------------------------------------------------ layout variants */
static void rf_fx_lower(char *s) { for (; *s; s++) *s = (char)tolower((unsigned char)*s); }

static void rf_fx_posture_norm(const char *in, char *out, size_t cap) {
    char b[32];
    char *p = b;
    const char *q;
    for (q = in ? in : ""; *q && p < b + sizeof b - 1; q++)
        if (*q != '-' && *q != '_' && *q != ' ') *p++ = (char)tolower((unsigned char)*q);
    *p = 0;
    if (!strcmp(b, "halfopened") || !strcmp(b, "halfopen") || !strcmp(b, "half") || !strcmp(b, "tabletop") ||
        !strcmp(b, "book")) rf_copy(out, "half-opened", cap);
    else if (!strcmp(b, "folded") || !strcmp(b, "closed") || !strcmp(b, "fold") || !strcmp(b, "cover"))
        rf_copy(out, "folded", cap);
    else if (!strcmp(b, "flat") || !strcmp(b, "open") || !strcmp(b, "opened")) rf_copy(out, "flat", cap);
    else rf_copy(out, "", cap);
}

static void rf_fx_venv(char *posture, char *span, char *fold) {
    char b[64];
    int hx[4], n = 0;
    DWORD k = GetEnvironmentVariableA("RADIDE_POSTURE", b, sizeof b);
    rf_fx_posture_norm(k && k < sizeof b ? b : "", posture, 16);
    k = GetEnvironmentVariableA("RADIDE_SPAN", b, sizeof b);
    span[0] = fold[0] = 0;
    if (k && k < sizeof b) {
        rf_fx_lower(b);
        rf_copy(span, (!strcmp(b, "dual") || !strcmp(b, "2") || !strcmp(b, "spanned")) ? "dual" : *b ? "single" : "", 12);
    }
    k = GetEnvironmentVariableA("RADIDE_HINGE", b, sizeof b);
    if (k && k < sizeof b) n = sscanf(b, "%d,%d,%d,%d", &hx[0], &hx[1], &hx[2], &hx[3]);
    if (n == 4 && strcmp(posture, "folded") != 0) rf_copy(fold, hx[2] <= hx[3] ? "vertical" : "horizontal", 12);
    if (!span[0])
        rf_copy(span, (!strcmp(posture, "half-opened") ||
                       (n == 4 && strcmp(posture, "folded") != 0 && (hx[2] < hx[3] ? hx[2] : hx[3]) > 0)) ? "dual" : "single", 12);
}

static int rf_fx_match(const RfFxSize *s, double w, double h, const char *posture, const char *span, const char *fold) {
    if (s->mnw >= 0 && w < s->mnw) return 0;
    if (s->mxw >= 0 && w > s->mxw) return 0;
    if (s->mnh >= 0 && h < s->mnh) return 0;
    if (s->mxh >= 0 && h > s->mxh) return 0;
    if (s->orient[0] && strncmp(s->orient, w > h ? "land" : "port", 4) != 0) return 0;
    if (s->posture[0] && strcmp(s->posture, posture) != 0) return 0;
    if (s->span[0] && strcmp(s->span, span[0] ? span : "single") != 0) return 0;
    if (s->fold[0] && strcmp(s->fold, fold) != 0) return 0;
    return 1;
}

static void rf_fx_relayout(RfForm *f) {
    RfCtl *c;
    rf_layout(f, NULL);
    for (c = f->ctls; c; c = c->next)
        if (c->hwnd && CCONT(c)) rf_layout(f, c);
}

/* _RadVariants.update: which sizes apply; restore the designed values, apply the sizes in order */
static int rf_fx_variants(RfForm *f, int notify) {
    RfFx *fx = FX(f);
    unsigned char now[64];
    double cw, ch;
    int ox, oy, i, j;
    char posture[16], span[12], fold[12];
    if (!fx || !fx->nsz || !f->hwnd) return 0;
    rf_client_logical(f, NULL, &cw, &ch, &ox, &oy);
    if (cw <= 1 || ch <= 1) { cw = f->design_w; ch = f->design_h; }
    rf_fx_venv(posture, span, fold);
    memset(now, 0, sizeof now);
    for (i = 0; i < fx->nsz && i < 64; i++) now[i] = (unsigned char)rf_fx_match(&fx->sz[i], cw, ch, posture, span, fold);
    if (fx->has_cur && memcmp(now, fx->cur, sizeof now) == 0) return 0;
    {
        int first = !fx->has_cur;
        memcpy(fx->cur, now, sizeof now);
        fx->has_cur = 1;
        g_fx_quiet++;
        for (i = 0; i < fx->nbase; i++) memcpy(fx->base[i].c->pl, fx->base[i].pl, sizeof fx->base[i].pl);
        for (i = 0; i < fx->nbp; i++) rf_set(f, fx->bp[i].c, fx->bp[i].prop, fx->bp[i].val);
        for (j = 0; j < fx->nsz && j < 64; j++) {
            if (!now[j]) continue;
            for (i = 0; i < fx->nvl; i++)
                if (fx->vl[i].size == j) memcpy(fx->vl[i].c->pl, fx->vl[i].pl, sizeof fx->vl[i].pl);
            for (i = 0; i < fx->nvp; i++)
                if (fx->vp[i].size == j && !rf_ieq(fx->vp[i].prop, "Visible"))
                    rf_set(f, fx->vp[i].c, fx->vp[i].prop, fx->vp[i].val);
            for (i = 0; i < fx->nvp; i++)
                if (fx->vp[i].size == j && rf_ieq(fx->vp[i].prop, "Visible"))
                    rf_set(f, fx->vp[i].c, fx->vp[i].prop, fx->vp[i].val);
        }
        g_fx_quiet--;
        rf_fx_relayout(f);
        if (!first && notify) rf_post(f, f->name, "SizeVariantChanged", "", AFTER_NONE);
    }
    return 1;
}

static const char *rf_fx_current_sizes(RfForm *f) {
    RfFx *fx = FX(f);
    char *b = rf_buf(1024);
    int i;
    b[0] = 0;
    if (!fx) return b;
    for (i = 0; i < fx->nsz && i < 64; i++)
        if (fx->cur[i]) {
            if (b[0]) strncat(b, ",", 1023 - strlen(b));
            strncat(b, fx->sz[i].id, 1023 - strlen(b));
        }
    return b;
}

/* ------------------------------------------------------------------ set-up (rf_form_load / rf_form_destroy) */
static RfCtl *rf_fx_ctl(RfForm *f, const char *name, int *ok) {
    RfCtl *c;
    *ok = 1;
    if (!name || !*name) return NULL;
    c = rf_ctl_in(f, name);
    if (!c) *ok = 0;
    return c;
}

static int rf_fx_on(const char *s) {
    static const char *const n[] = {"load", "click", "hover", "timer", "show", "hide", "after", "manual"};
    int i;
    for (i = 0; i < 8; i++)
        if (rf_ieq(s, n[i])) return i;
    return FXT_MANUAL;
}

static double rf_fx_lim(const char *s) { return s && *s ? rad_num(s) : -1; }

static void rf_fx_add_base(RfFx *fx, RfCtl *c) {
    int i;
    RfFxBase *b;
    for (i = 0; i < fx->nbase; i++)
        if (fx->base[i].c == c) return;
    b = FX_PUSH(fx->base, fx->nbase, RfFxBase);
    b->c = c;
    memcpy(b->pl, c->pl, sizeof b->pl);
}

static void rf_fx_add_bp(RfForm *f, RfFx *fx, RfCtl *c, const char *prop) {
    int i;
    RfFxBP *b;
    for (i = 0; i < fx->nbp; i++)
        if (fx->bp[i].c == c && rf_ieq(fx->bp[i].prop, prop)) return;
    b = FX_PUSH(fx->bp, fx->nbp, RfFxBP);
    b->c = c;
    rf_copy(b->prop, prop, sizeof b->prop);
    b->val = rf_strdup(rf_get(f, c, prop));
}

static void rf_fx_init(RfForm *f) {
    RfFx *fx;
    RfFxSb *sb = NULL;
    int i, ok, any = 0;
    for (i = f->first_line; i < f->last_line && !any; i++) {
        const char *k = F(i, 0);
        any = !strcmp(k, "X") || !strcmp(k, "Q") || !strcmp(k, "V");
    }
    if (!any) return;
    fx = (RfFx *)calloc(1, sizeof(RfFx));
    if (!fx) return;
    f->fx = fx;
    fx->respect = 1;
    for (i = f->first_line; i < f->last_line; i++) {
        const char *k = F(i, 0);
        if (!strcmp(k, "XR")) fx->respect = rf_bool(F(i, 1)) || !strcmp(F(i, 1), "1");
        else if (!strcmp(k, "X")) {
            RfCtl *c = rf_fx_ctl(f, F(i, 2), &ok);
            sb = NULL;
            if (!ok || fx->nsb >= RF_FX_MAX) continue;
            sb = FX_PUSH(fx->sb, fx->nsb, RfFxSb);
            rf_copy(sb->fx, F(i, 1), sizeof sb->fx);
            rf_copy(sb->tname, F(i, 2), sizeof sb->tname);
            sb->c = c;
            sb->count = rf_int(F(i, 3));
            if (sb->count < 1) sb->count = 1;
            sb->forever = rf_int(F(i, 4)) != 0;
            sb->autorev = rf_int(F(i, 5)) != 0;
            sb->delay = rf_int(F(i, 6));
            sb->restore = rf_int(F(i, 7)) != 0;
            sb->on = FXT_MANUAL;
        } else if (!strcmp(k, "XT") && sb) {
            sb->on = rf_fx_on(F(i, 1));
            rf_copy(sb->src, *F(i, 2) ? F(i, 2) : sb->tname, sizeof sb->src);
            sb->interval = rf_int(F(i, 3));
            rf_copy(sb->after, F(i, 4), sizeof sb->after);
            sb->leave = rf_ieq(F(i, 5), "stop") ? 1 : rf_ieq(F(i, 5), "none") ? 2 : 0;
        } else if (!strcmp(k, "K") && sb) {
            RfFxTrack *t = sb->ntr ? &sb->tr[sb->ntr - 1] : NULL;
            RfFxKey *key;
            const char *kind = F(i, 4);
            if (!t || !rf_ieq(t->prop, F(i, 1))) {
                t = FX_PUSH(sb->tr, sb->ntr, RfFxTrack);
                rf_copy(t->prop, F(i, 1), sizeof t->prop);
                t->pt = rf_fx_ptype(t->prop);
                t->last_bool = -1;
            }
            key = FX_PUSH(t->k, t->nk, RfFxKey);
            key->ms = rf_int(F(i, 2));
            if (key->ms > sb->dur) sb->dur = key->ms;
            key->ease = rf_fx_ease_of(F(i, 3));
            key->a = rad_num(F(i, 5));
            key->b = rad_num(F(i, 6));
            key->d = rad_num(F(i, 8));
            key->of = rf_ieq(F(i, 7), "Width") ? 'W' : rf_ieq(F(i, 7), "Height") ? 'H' : 0;
            switch (kind[0]) {
            case 'c': { COLORREF col = 0; rf_color(F(i, 5), &col); key->kind = FXK_COLOR; key->a = (double)col; break; }
            case 'b': key->kind = FXK_BOOL; key->a = rf_bool(F(i, 5)) || !strcmp(F(i, 5), "1"); break;
            case 's': key->kind = FXK_TEXT; key->s = rf_strdup(F(i, 5)); break;
            case 'r': key->kind = FXK_REL; break;
            case 'p': key->kind = FXK_PARENT; break;
            case 'v': key->kind = FXK_REVEAL; break;
            default: key->kind = FXK_NUM; break;
            }
        } else if (!strcmp(k, "Q")) {
            RfCtl *c = rf_fx_ctl(f, F(i, 1), &ok);
            RfFxQ *q;
            if (!ok) continue;
            q = FX_PUSH(fx->q, fx->nq, RfFxQ);
            q->c = c;
            q->form = c == NULL;
            rf_copy(q->state, F(i, 2), sizeof q->state);
            rf_copy(q->prop, F(i, 3), sizeof q->prop);
            q->val = rf_strdup(F(i, 4));
        } else if (!strcmp(k, "V")) {
            RfFxSize *s = FX_PUSH(fx->sz, fx->nsz, RfFxSize);
            rf_copy(s->id, F(i, 1), sizeof s->id);
            s->mnw = rf_fx_lim(F(i, 2));
            s->mxw = rf_fx_lim(F(i, 3));
            s->mnh = rf_fx_lim(F(i, 4));
            s->mxh = rf_fx_lim(F(i, 5));
            rf_copy(s->orient, F(i, 6), sizeof s->orient);
            rf_fx_posture_norm(F(i, 7), s->posture, sizeof s->posture);
            rf_copy(s->span, F(i, 8), sizeof s->span);
            rf_copy(s->fold, F(i, 9), sizeof s->fold);
            rf_fx_lower(s->span);
            rf_fx_lower(s->fold);
        } else if (!strcmp(k, "VL") || !strcmp(k, "VP")) {
            int si;
            RfCtl *c = rf_fx_ctl(f, F(i, 2), &ok);
            if (!ok) continue;
            for (si = 0; si < fx->nsz && !rf_ieq(fx->sz[si].id, F(i, 1)); si++) {}
            if (si >= fx->nsz) continue;
            if (!strcmp(k, "VL")) {
                RfFxVL *v;
                float p[8];
                if (!c || sscanf(F(i, 3), "%f %f %f %f %f %f %f %f", &p[0], &p[1], &p[2], &p[3], &p[4], &p[5], &p[6], &p[7]) != 8)
                    continue;
                rf_fx_add_base(fx, c);
                v = FX_PUSH(fx->vl, fx->nvl, RfFxVL);
                v->size = si;
                v->c = c;
                memcpy(v->pl, p, sizeof p);
            } else {
                RfFxVP *v = FX_PUSH(fx->vp, fx->nvp, RfFxVP);
                v->size = si;
                v->c = c;
                rf_copy(v->prop, F(i, 3), sizeof v->prop);
                v->val = rf_strdup(F(i, 4));
                rf_fx_add_bp(f, fx, c, v->prop);
            }
        }
    }
    fx->reduced = fx->respect && rf_fx_reduced_system();
    {
        RfCtl *c;                        /* controls that start disabled are in their Disabled state */
        for (c = f->ctls; c; c = c->next)
            if (rf_fx_has_states(fx, c) && !c->enabled) rf_fx_flag(f, c, FXF_DISABLED, 1);
    }
    rf_fx_variants(f, 0);
}

static void rf_fx_free(RfForm *f) {
    RfFx *fx = FX(f);
    int i, j, k;
    if (!fx) return;
    f->fx = NULL;
    for (i = 0; i < fx->nsb; i++) {
        RfFxSb *sb = &fx->sb[i];
        rf_fx_forget(sb);
        for (j = 0; j < sb->ntr; j++) {
            for (k = 0; k < sb->tr[j].nk; k++) free(sb->tr[j].k[k].s);
            free(sb->tr[j].k);
        }
        free(sb->tr);
    }
    for (i = 0; i < fx->nq; i++) free(fx->q[i].val);
    for (i = 0; i < fx->nap; i++) { free(fx->ap[i].saved); free(fx->ap[i].val); }
    for (i = 0; i < fx->nvp; i++) free(fx->vp[i].val);
    for (i = 0; i < fx->nbp; i++) free(fx->bp[i].val);
    free(fx->sb); free(fx->q); free(fx->ap); free(fx->fl); free(fx->sz); free(fx->vl); free(fx->vp);
    free(fx->base); free(fx->bp);
    free(fx);
}

/* ------------------------------------------------------------------ hooks called by radforms.c */
/* the form is shown for the first time (after <Form>_Load): "On load" begins, "On timer" timers start */
static void rf_fx_start(RfForm *f) {
    RfFx *fx = FX(f);
    int i;
    if (!fx || fx->started) return;
    fx->started = 1;
    for (i = 0; i < fx->nsb; i++) {
        RfFxSb *sb = &fx->sb[i];
        if (sb->on == FXT_LOAD) rf_fx_fx_begin(f, sb);
        else if (sb->on == FXT_TIMER && sb->interval > 0) {
            SetTimer(f->hwnd, RF_FX_EVERY + (UINT_PTR)i, (UINT)sb->interval, NULL);
            sb->every = 1;
        }
    }
}

static int rf_fx_timer(RfForm *f, WPARAM id) {
    RfFx *fx = FX(f);
    int i;
    if (!fx) return 0;
    if (id == RF_FX_FRAME) {
        for (i = 0; i < fx->nsb; i++)
            if (fx->sb[i].playing) rf_fx_tick(f, &fx->sb[i]);
        rf_fx_frame(f);
        return 1;
    }
    if (id >= RF_FX_DELAY && id < RF_FX_DELAY + (WPARAM)fx->nsb) {
        RfFxSb *sb = &fx->sb[id - RF_FX_DELAY];
        KillTimer(f->hwnd, id);
        if (sb->pending) { sb->pending = 0; rf_fx_begin_now(f, sb); }
        return 1;
    }
    if (id >= RF_FX_EVERY && id < RF_FX_EVERY + (WPARAM)fx->nsb) {
        rf_fx_fx_begin(f, &fx->sb[id - RF_FX_EVERY]);
        return 1;
    }
    return 0;
}

/* every event radforms reports (before the handler filter): triggers and automatic states */
static void rf_fx_event(RfForm *f, const char *obj, const char *ev) {
    RfFx *fx = FX(f);
    RfCtl *c;
    int i;
    if (!fx || g_building || !obj) return;
    c = rf_ieq(obj, f->name) ? NULL : rf_ctl_in(f, obj);
    if (rf_ieq(ev, "Click") || rf_ieq(ev, "MouseEnter") || rf_ieq(ev, "MouseLeave")) {
        for (i = 0; i < fx->nsb; i++) {
            RfFxSb *sb = &fx->sb[i];
            if (!rf_ieq(sb->src, obj)) continue;
            if (sb->on == FXT_CLICK && rf_ieq(ev, "Click")) rf_fx_fx_begin(f, sb);
            else if (sb->on == FXT_HOVER && rf_ieq(ev, "MouseEnter")) rf_fx_fx_begin(f, sb);
            else if (sb->on == FXT_HOVER && rf_ieq(ev, "MouseLeave")) {
                if (sb->leave == 0) rf_fx_reverse(f, sb);
                else if (sb->leave == 1) { sb->hiding = 0; rf_fx_stop(f, sb); }
            }
        }
    }
    if (!c) return;
    if (rf_ieq(ev, "MouseEnter")) rf_fx_flag(f, c, FXF_OVER, 1);
    else if (rf_ieq(ev, "MouseLeave")) { rf_fx_flag(f, c, FXF_PRESSED, 0); rf_fx_flag(f, c, FXF_OVER, 0); }
    else if (rf_ieq(ev, "MouseDown")) rf_fx_flag(f, c, FXF_PRESSED, 1);
    else if (rf_ieq(ev, "MouseUp")) rf_fx_flag(f, c, FXF_PRESSED, 0);
    else if (rf_ieq(ev, "GotFocus")) rf_fx_flag(f, c, FXF_FOCUSED, 1);
    else if (rf_ieq(ev, "LostFocus")) rf_fx_flag(f, c, FXF_FOCUSED, 0);
}

/* rf_set from the program: Visible plays "On show" / "On hide" (1 = handled here), Enabled -> Disabled state */
static int rf_fx_set_hook(RfForm *f, RfCtl *c, const char *p, const char *v) {
    RfFx *fx = FX(f);
    int i, on, n = 0;
    if (!fx || g_fx_quiet || g_building || !c) return 0;
    if (rf_ieq(p, "Enabled")) return 0;
    if (!rf_ieq(p, "Visible")) return 0;
    on = rf_bool(v);
    if (on == (c->visible != 0)) return 0;
    for (i = 0; i < fx->nsb; i++)
        if (fx->sb[i].c == c && fx->sb[i].on == (on ? FXT_SHOW : FXT_HIDE)) n++;
    if (!n) return 0;
    if (on) rf_fx_write(f, c, "Visible", "True");
    for (i = 0; i < fx->nsb; i++) {
        RfFxSb *sb = &fx->sb[i];
        if (sb->c != c || sb->on != (on ? FXT_SHOW : FXT_HIDE)) continue;
        if (!on) sb->hiding = 1;
        rf_fx_fx_begin(f, sb);
    }
    return 1;
}

static void rf_fx_after_set(RfForm *f, RfCtl *c, const char *p, const char *v) {
    if (!FX(f) || g_fx_quiet || !c) return;
    if (rf_ieq(p, "Enabled")) rf_fx_flag(f, c, FXF_DISABLED, !rf_bool(v));
}

/* rad_call / rf_invoke: BeginAnimation, StopAnimation, GoToState, ApplySizeVariants, CurrentSizes, CurrentState */
static const char *rf_fx_call(RfForm *f, RfCtl *c, const char *m, const char *args, int *handled) {
    RfFx *fx = FX(f);
    *handled = 0;
    if (rf_ieq(m, "BeginAnimation") || rf_ieq(m, "StopAnimation")) {
        *handled = 1;
        return rf_tf(rf_fx_by_name(f, rf_arg_n(args, 0), rf_ieq(m, "StopAnimation")) > 0);
    }
    if (rf_ieq(m, "GoToState")) {
        RfCtl *t = c;
        const char *ctl = rf_arg_n(args, 1);
        *handled = 1;
        if (!fx) return "False";
        if (!t && *ctl) {
            t = rf_ctl_in(f, ctl);
            if (!t) return "False";
        }
        return rf_tf(rf_fx_goto_state(f, t, rf_arg_n(args, 0)));
    }
    if (c) return "";
    if (rf_ieq(m, "ApplySizeVariants")) { *handled = 1; return rf_tf(rf_fx_variants(f, 1)); }
    if (rf_ieq(m, "CurrentSizes")) { *handled = 1; return rf_fx_current_sizes(f); }
    if (rf_ieq(m, "CurrentState")) { *handled = 1; return fx && fx->state[0] ? fx->state : "Normal"; }
    return "";
}
