/* rm_kit - shared helpers of the RAD Modern (Rm*) control modules (see rm_kit.h).
 * Linked once into an exe when any rm_*.c module is used (their "RF_REQUIRES: rm_kit.c" line).
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <math.h>
#include <windowsx.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* registration entry point: rm_kit has no control class of its own */
RF_MODULE(rm_kit) {}

/* ================================================================== strings */
int rm_ieq(const char *a, const char *b) {
    if (!a) a = "";
    if (!b) b = "";
    for (; *a && *b; a++, b++) {
        int x = *a >= 'A' && *a <= 'Z' ? *a + 32 : *a, y = *b >= 'A' && *b <= 'Z' ? *b + 32 : *b;
        if (x != y) return 0;
    }
    return *a == *b;
}

int rm_bool(const char *v) {
    if (!v) return 0;
    return rm_ieq(v, "True") || rm_ieq(v, "1") || rm_ieq(v, "-1") || rm_ieq(v, "Yes") || rm_ieq(v, "On");
}

int rm_int(const char *v) {
    double d = rad_num(v ? v : "");
    return (int)(d < 0 ? d - 0.5 : d + 0.5);
}

const char *rm_tf(int b) { return b ? "True" : "False"; }

char *rm_strdup(const char *s) {
    size_t n = s ? strlen(s) : 0;
    char *d = (char *)malloc(n + 1);
    if (d) {
        if (n) memcpy(d, s, n);
        d[n] = 0;
    }
    return d;
}

void rm_setstr(char **dst, const char *v) {
    char *n = rm_strdup(v);
    free(*dst);
    *dst = n;
}

int rm_color(const char *v, unsigned *out) {
    unsigned r = 0, g = 0, b = 0, a = 0;
    if (!v || !*v) return 0;
    while (*v == ' ') v++;
    if (*v == '#') {
        size_t n = strlen(v + 1);
        if (n >= 8 && sscanf(v + 1, "%2x%2x%2x%2x", &a, &r, &g, &b) == 4) { *out = RGB(r, g, b); return 1; }
        if (n >= 6 && sscanf(v + 1, "%2x%2x%2x", &r, &g, &b) == 3) { *out = RGB(r, g, b); return 1; }
        if (n == 3 && sscanf(v + 1, "%1x%1x%1x", &r, &g, &b) == 3) { *out = RGB(r * 17, g * 17, b * 17); return 1; }
        return 0;
    }
    if (sscanf(v, "%u , %u , %u", &r, &g, &b) == 3) { *out = RGB(r, g, b); return 1; }
    if (rm_ieq(v, "White")) { *out = RGB(255, 255, 255); return 1; }
    if (rm_ieq(v, "Black")) { *out = 0; return 1; }
    if (rm_ieq(v, "Red")) { *out = RGB(198, 40, 40); return 1; }
    if (rm_ieq(v, "Green")) { *out = RGB(46, 125, 50); return 1; }
    if (rm_ieq(v, "Blue")) { *out = RGB(21, 101, 192); return 1; }
    if (rm_ieq(v, "Orange")) { *out = RGB(239, 108, 0); return 1; }
    if (rm_ieq(v, "Purple")) { *out = RGB(106, 27, 154); return 1; }
    if (rm_ieq(v, "Teal")) { *out = RGB(0, 121, 107); return 1; }
    if (rm_ieq(v, "Gray") || rm_ieq(v, "Grey")) { *out = RGB(117, 117, 117); return 1; }
    return 0;
}

/* ring of returned strings (like radforms) */
#define RM_RING 16
static char *g_ring[RM_RING];
static size_t g_ringcap[RM_RING];
static int g_ringi;

static char *rm_buf(size_t n) {
    int i = g_ringi = (g_ringi + 1) % RM_RING;
    if (g_ringcap[i] < n + 1) {
        char *p = (char *)realloc(g_ring[i], n + 1);
        if (!p) return (char *)"";
        g_ring[i] = p;
        g_ringcap[i] = n + 1;
    }
    g_ring[i][0] = 0;
    return g_ring[i];
}

const char *rm_colorstr(unsigned c) {
    char *b = rm_buf(8);
    snprintf(b, 8, "#%02X%02X%02X", GetRValue(c), GetGValue(c), GetBValue(c));
    return b;
}

wchar_t *rm_wide(const char *s) {
    int n;
    wchar_t *w;
    if (!s) s = "";
    n = MultiByteToWideChar(CP_UTF8, 0, s, -1, NULL, 0);
    w = (wchar_t *)malloc(sizeof(wchar_t) * (n > 0 ? n : 1));
    if (!w) return NULL;
    if (n <= 0 || !MultiByteToWideChar(CP_UTF8, 0, s, -1, w, n)) w[0] = 0;
    return w;
}

char *rm_utf8(const wchar_t *w) {
    int n;
    char *s;
    if (!w) w = L"";
    n = WideCharToMultiByte(CP_UTF8, 0, w, -1, NULL, 0, NULL, NULL);
    s = (char *)malloc(n > 0 ? n : 1);
    if (!s) return NULL;
    if (n <= 0 || !WideCharToMultiByte(CP_UTF8, 0, w, -1, s, n, NULL, NULL)) s[0] = 0;
    return s;
}

unsigned rm_luma(unsigned c) { return (GetRValue(c) * 299 + GetGValue(c) * 587 + GetBValue(c) * 114) / 1000; }
unsigned rm_on(unsigned back) { return rm_luma(back) > 150 ? RGB(32, 32, 32) : RGB(255, 255, 255); }

const char *rm_arg(const char *args, int n) {
    const char *p = args ? args : "", *e;
    char *b;
    size_t len;
    while (n > 0 && p) {
        p = strchr(p, '\t');
        if (p) p++;
        n--;
    }
    if (!p) return "";
    e = strchr(p, '\t');
    len = e ? (size_t)(e - p) : strlen(p);
    b = rm_buf(len);
    memcpy(b, p, len);
    b[len] = 0;
    return b;
}

void rm_sb_add(rm_sb *b, const char *s) {
    size_t n = s ? strlen(s) : 0;
    if (b->n + n + 1 > b->cap) {
        size_t cap = (b->cap ? b->cap * 2 : 64);
        char *p;
        while (cap < b->n + n + 1) cap *= 2;
        p = (char *)realloc(b->s, cap);
        if (!p) return;
        b->s = p;
        b->cap = cap;
    }
    if (n) memcpy(b->s + b->n, s, n);
    b->n += n;
    b->s[b->n] = 0;
}

void rm_sb_addc(rm_sb *b, char c) {
    char t[2];
    t[0] = c;
    t[1] = 0;
    rm_sb_add(b, t);
}

void rm_sb_json(rm_sb *b, const char *s) {
    rm_sb_addc(b, '"');
    for (; s && *s; s++) {
        unsigned char ch = (unsigned char)*s;
        if (ch == '"' || ch == '\\') { rm_sb_addc(b, '\\'); rm_sb_addc(b, (char)ch); }
        else if (ch == '\n') rm_sb_add(b, "\\n");
        else if (ch == '\r') rm_sb_add(b, "\\r");
        else if (ch == '\t') rm_sb_add(b, "\\t");
        else if (ch < 32) { char u[8]; snprintf(u, sizeof u, "\\u%04x", ch); rm_sb_add(b, u); }
        else rm_sb_addc(b, (char)ch);
    }
    rm_sb_addc(b, '"');
}

const char *rm_sb_ring(rm_sb *b) {
    char *r = rm_buf(b->n);
    if (b->s) memcpy(r, b->s, b->n + 1);
    free(b->s);
    b->s = NULL;
    b->n = b->cap = 0;
    return r;
}

/* ================================================================== lists */
void rm_list_free(rm_list *l) {
    int i;
    for (i = 0; i < l->n; i++) free(l->v[i]);
    free(l->v);
    l->v = NULL;
    l->n = l->cap = 0;
}

void rm_list_add(rm_list *l, const char *s, int at) {
    if (l->n >= l->cap) {
        int cap = l->cap ? l->cap * 2 : 8;
        char **v = (char **)realloc(l->v, sizeof(char *) * cap);
        if (!v) return;
        l->v = v;
        l->cap = cap;
    }
    if (at < 0 || at > l->n) at = l->n;
    memmove(l->v + at + 1, l->v + at, sizeof(char *) * (l->n - at));
    l->v[at] = rm_strdup(s);
    l->n++;
}

void rm_list_remove(rm_list *l, int i) {
    if (i < 0 || i >= l->n) return;
    free(l->v[i]);
    memmove(l->v + i, l->v + i + 1, sizeof(char *) * (l->n - i - 1));
    l->n--;
}

void rm_list_parse(rm_list *l, const char *text, char sep) {
    const char *p = text ? text : "";
    rm_list_free(l);
    if (!*p) return;
    for (;;) {
        const char *e = strchr(p, sep);
        size_t n = e ? (size_t)(e - p) : strlen(p);
        char *t = (char *)malloc(n + 1);
        if (!t) return;
        memcpy(t, p, n);
        t[n] = 0;
        rm_list_add(l, t, -1);
        free(t);
        if (!e) break;
        p = e + 1;
    }
}

const char *rm_list_get(const rm_list *l, int i) { return i >= 0 && i < l->n ? l->v[i] : ""; }

const char *rm_list_join(const rm_list *l, char sep) {
    rm_sb b = {0, 0, 0};
    int i;
    rm_sb_add(&b, "");
    for (i = 0; i < l->n; i++) {
        if (i) rm_sb_addc(&b, sep);
        rm_sb_add(&b, l->v[i]);
    }
    return rm_sb_ring(&b);
}

int rm_list_find(const rm_list *l, const char *s) {
    int i;
    for (i = 0; i < l->n; i++)
        if (rm_ieq(l->v[i], s)) return i;
    return -1;
}

/* ================================================================== JSON */
static const char *jws(const char *p) {
    while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') p++;
    return p;
}

static void jput_utf8(rm_sb *b, unsigned cp) {
    char t[5] = {0};
    if (cp < 0x80) t[0] = (char)cp;
    else if (cp < 0x800) { t[0] = (char)(0xC0 | (cp >> 6)); t[1] = (char)(0x80 | (cp & 63)); }
    else if (cp < 0x10000) {
        t[0] = (char)(0xE0 | (cp >> 12)); t[1] = (char)(0x80 | ((cp >> 6) & 63)); t[2] = (char)(0x80 | (cp & 63));
    } else {
        t[0] = (char)(0xF0 | (cp >> 18)); t[1] = (char)(0x80 | ((cp >> 12) & 63));
        t[2] = (char)(0x80 | ((cp >> 6) & 63)); t[3] = (char)(0x80 | (cp & 63));
    }
    rm_sb_add(b, t);
}

static const char *jstr(const char *p, char **out) {
    rm_sb b = {0, 0, 0};
    rm_sb_add(&b, "");
    p++;                                /* opening quote */
    while (*p && *p != '"') {
        if (*p == '\\' && p[1]) {
            p++;
            switch (*p) {
            case 'n': rm_sb_addc(&b, '\n'); break;
            case 'r': rm_sb_addc(&b, '\r'); break;
            case 't': rm_sb_addc(&b, '\t'); break;
            case 'b': rm_sb_addc(&b, '\b'); break;
            case 'f': rm_sb_addc(&b, '\f'); break;
            case 'u': {
                unsigned cp = 0;
                if (sscanf(p + 1, "%4x", &cp) == 1) {
                    p += 4;
                    if (cp >= 0xD800 && cp < 0xDC00 && p[1] == '\\' && p[2] == 'u') {
                        unsigned lo = 0;
                        if (sscanf(p + 3, "%4x", &lo) == 1 && lo >= 0xDC00 && lo < 0xE000) {
                            cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                            p += 6;
                        }
                    }
                    jput_utf8(&b, cp);
                }
                break;
            }
            default: rm_sb_addc(&b, *p); break;
            }
            p++;
        } else {
            rm_sb_addc(&b, *p++);
        }
    }
    *out = b.s ? b.s : rm_strdup("");
    return *p == '"' ? p + 1 : NULL;
}

static const char *jvalue(const char *p, rm_json *j, int depth);

static int jadd(rm_json *j, rm_json **kid) {
    rm_json *k = (rm_json *)realloc(j->kids, sizeof(rm_json) * (j->n + 1));
    if (!k) return 0;
    j->kids = k;
    memset(&k[j->n], 0, sizeof(rm_json));
    *kid = &k[j->n];
    j->n++;
    return 1;
}

static const char *jvalue(const char *p, rm_json *j, int depth) {
    p = jws(p);
    if (depth > 64) return NULL;
    if (*p == '{' || *p == '[') {
        char close = *p == '{' ? '}' : ']';
        j->type = *p == '{' ? RMJ_OBJ : RMJ_ARR;
        p = jws(p + 1);
        if (*p == close) return p + 1;
        for (;;) {
            rm_json *k;
            char *key = NULL;
            p = jws(p);
            if (j->type == RMJ_OBJ) {
                if (*p != '"') return NULL;
                p = jstr(p, &key);
                if (!p) { free(key); return NULL; }
                p = jws(p);
                if (*p != ':') { free(key); return NULL; }
                p++;
            }
            if (!jadd(j, &k)) { free(key); return NULL; }
            k->key = key;
            p = jvalue(p, k, depth + 1);
            if (!p) return NULL;
            p = jws(p);
            if (*p == ',') { p++; continue; }
            if (*p == close) return p + 1;
            return NULL;
        }
    }
    if (*p == '"') { j->type = RMJ_STR; return jstr(p, &j->str); }
    if (strncmp(p, "true", 4) == 0) { j->type = RMJ_BOOL; j->num = 1; return p + 4; }
    if (strncmp(p, "false", 5) == 0) { j->type = RMJ_BOOL; j->num = 0; return p + 5; }
    if (strncmp(p, "null", 4) == 0) { j->type = RMJ_NULL; return p + 4; }
    if (*p == '-' || (*p >= '0' && *p <= '9')) {
        char *e;
        j->type = RMJ_NUM;
        j->num = strtod(p, &e);
        return e;
    }
    return NULL;
}

static void jclear(rm_json *j) {
    int i;
    for (i = 0; i < j->n; i++) jclear(&j->kids[i]);
    free(j->kids);
    free(j->key);
    free(j->str);
}

void rm_json_free(rm_json *j) {
    if (!j) return;
    jclear(j);
    free(j);
}

rm_json *rm_json_parse(const char *text) {
    rm_json *j;
    const char *e;
    if (!text) return NULL;
    j = (rm_json *)calloc(1, sizeof *j);
    if (!j) return NULL;
    e = jvalue(text, j, 0);
    if (!e || *jws(e)) { rm_json_free(j); return NULL; }
    return j;
}

const rm_json *rm_json_get(const rm_json *obj, const char *key) {
    int i;
    if (!obj || obj->type != RMJ_OBJ) return NULL;
    for (i = 0; i < obj->n; i++)
        if (rm_ieq(obj->kids[i].key, key)) return &obj->kids[i];
    return NULL;
}

const char *rm_json_text(const rm_json *obj, const char *key, const char *def) {
    const rm_json *v = rm_json_get(obj, key);
    if (!v) return def;
    if (v->type == RMJ_STR) return v->str;
    if (v->type == RMJ_NUM) return rad_str(v->num);
    if (v->type == RMJ_BOOL) return v->num ? "True" : "False";
    return def;
}

double rm_json_num(const rm_json *obj, const char *key, double def) {
    const rm_json *v = rm_json_get(obj, key);
    if (!v) return def;
    if (v->type == RMJ_NUM || v->type == RMJ_BOOL) return v->num;
    if (v->type == RMJ_STR && *v->str) return rad_num(v->str);
    return def;
}

int rm_json_bool(const rm_json *obj, const char *key, int def) {
    const rm_json *v = rm_json_get(obj, key);
    if (!v) return def;
    if (v->type == RMJ_BOOL || v->type == RMJ_NUM) return v->num != 0;
    if (v->type == RMJ_STR) return rm_bool(v->str);
    return def;
}

/* ================================================================== items */
static char *rm_nospace(const char *s) {
    char *d = rm_strdup(s), *o = d;
    const char *p;
    if (!d) return NULL;
    for (p = s ? s : ""; *p; p++)
        if (*p != ' ' && *p != '&' && *p != '.' && *p != '-') *o++ = *p;
    *o = 0;
    return d;
}

static void item_from_json(rm_item *it, const rm_json *o) {
    static const char *const kids_keys[] = {"Items", "Nodes", "Groups", "Pages", "Children", "Panels", "Tabs"};
    const char *s;
    size_t k;
    memset(it, 0, sizeof *it);
    if (o->type == RMJ_STR) {
        it->text = rm_strdup(o->str);
        it->name = rm_nospace(o->str);
        it->image = rm_strdup("");
        it->kind = rm_strdup("");
        it->tag = rm_strdup(""); it->shortcut = rm_strdup(""); it->tip = rm_strdup(""); it->value = rm_strdup("");
        it->enabled = 1;
        return;
    }
    it->text = rm_strdup(rm_json_text(o, "Text", rm_json_text(o, "Title", "")));
    s = rm_json_text(o, "Name", "");
    it->name = *s ? rm_strdup(s) : rm_nospace(it->text);
    it->image = rm_strdup(rm_json_text(o, "Image", rm_json_text(o, "Icon", "")));
    it->kind = rm_strdup(rm_json_text(o, "Kind", rm_json_text(o, "Type", "")));
    it->tag = rm_strdup(rm_json_text(o, "Tag", ""));
    it->shortcut = rm_strdup(rm_json_text(o, "Shortcut", ""));
    it->tip = rm_strdup(rm_json_text(o, "ToolTip", rm_json_text(o, "Tip", rm_json_text(o, "Description", ""))));
    it->value = rm_strdup(rm_json_text(o, "Value", ""));
    it->checked = rm_json_bool(o, "Checked", 0);
    it->expanded = rm_json_bool(o, "Expanded", 0);
    it->enabled = rm_json_bool(o, "Enabled", 1);
    s = rm_json_text(o, "Size", "");
    it->large = rm_json_bool(o, "Large", rm_ieq(s, "Large"));
    it->count = (int)rm_json_num(o, "Count", 0);
    it->width = (int)rm_json_num(o, "Width", 0);
    it->lazy = rm_json_bool(o, "Lazy", 0);
    it->has_color = rm_color(rm_json_text(o, "Color", ""), &it->color);
    for (k = 0; k < sizeof kids_keys / sizeof kids_keys[0]; k++) {
        const rm_json *a = rm_json_get(o, kids_keys[k]);
        if (a && a->type == RMJ_ARR && a->n) {
            int i;
            it->items = (rm_item *)calloc((size_t)a->n, sizeof(rm_item));
            if (!it->items) break;
            it->n = a->n;
            for (i = 0; i < a->n; i++) item_from_json(&it->items[i], &a->kids[i]);
            break;
        }
    }
}

rm_item *rm_items_parse(const char *text, int *count) {
    rm_item *out = NULL;
    const char *p = text ? text : "";
    *count = 0;
    while (*p == ' ' || *p == '\r' || *p == '\n' || *p == '\t') p++;
    if (*p == '[') {
        rm_json *j = rm_json_parse(p);
        if (j && j->type == RMJ_ARR && j->n) {
            int i;
            out = (rm_item *)calloc((size_t)j->n, sizeof(rm_item));
            if (out) {
                for (i = 0; i < j->n; i++) item_from_json(&out[i], &j->kids[i]);
                *count = j->n;
            }
        }
        rm_json_free(j);
        return out;
    }
    if (*p) {
        rm_list l = {0, 0, 0};
        int i;
        rm_list_parse(&l, p, ';');
        out = (rm_item *)calloc((size_t)(l.n ? l.n : 1), sizeof(rm_item));
        if (out) {
            for (i = 0; i < l.n; i++) {
                rm_json fake;
                memset(&fake, 0, sizeof fake);
                fake.type = RMJ_STR;
                fake.str = l.v[i];
                item_from_json(&out[i], &fake);
            }
            *count = l.n;
        }
        rm_list_free(&l);
    }
    return out;
}

void rm_item_clear(rm_item *it) {
    free(it->text); free(it->name); free(it->image); free(it->kind); free(it->tag); free(it->shortcut);
    free(it->tip); free(it->value);
    rm_items_free(it->items, it->n);
    memset(it, 0, sizeof *it);
}

void rm_items_free(rm_item *items, int n) {
    int i;
    if (!items) return;
    for (i = 0; i < n; i++) rm_item_clear(&items[i]);
    free(items);
}

rm_item *rm_items_find(rm_item *items, int n, const char *name) {
    int i;
    for (i = 0; i < n; i++) {
        rm_item *r;
        if (rm_ieq(items[i].name, name) || (!*items[i].name && rm_ieq(items[i].text, name))) return &items[i];
        if ((r = rm_items_find(items[i].items, items[i].n, name)) != NULL) return r;
    }
    return NULL;
}

static void items_json(rm_sb *b, const rm_item *items, int n) {
    int i;
    rm_sb_addc(b, '[');
    for (i = 0; i < n; i++) {
        const rm_item *it = &items[i];
        if (i) rm_sb_addc(b, ',');
        rm_sb_add(b, "{\"Text\":");
        rm_sb_json(b, it->text);
        rm_sb_add(b, ",\"Name\":");
        rm_sb_json(b, it->name);
        if (it->image && *it->image) { rm_sb_add(b, ",\"Image\":"); rm_sb_json(b, it->image); }
        if (it->kind && *it->kind) { rm_sb_add(b, ",\"Kind\":"); rm_sb_json(b, it->kind); }
        if (it->checked) rm_sb_add(b, ",\"Checked\":true");
        if (it->expanded) rm_sb_add(b, ",\"Expanded\":true");
        if (!it->enabled) rm_sb_add(b, ",\"Enabled\":false");
        if (it->n) { rm_sb_add(b, ",\"Items\":"); items_json(b, it->items, it->n); }
        rm_sb_addc(b, '}');
    }
    rm_sb_addc(b, ']');
}

const char *rm_items_json(const rm_item *items, int n) {
    rm_sb b = {0, 0, 0};
    items_json(&b, items, n);
    return rm_sb_ring(&b);
}

/* ================================================================== look */
int rm_look_set(rm_look *k, const char *prop, const char *value) {
    if (rm_ieq(prop, "Style")) {
        snprintf(k->style, sizeof k->style, "%s", value && *value ? value : "Inherit");
        return 1;
    }
    if (rm_ieq(prop, "AccentColor")) {
        k->has_accent = rm_color(value, &k->accent);
        return 1;
    }
    return 0;
}

const char *rm_look_get(const rm_look *k, const char *prop) {
    if (rm_ieq(prop, "Style")) return k->style[0] ? k->style : "Inherit";
    if (rm_ieq(prop, "AccentColor")) return k->has_accent ? rm_colorstr(k->accent) : "";
    return NULL;
}

const rf_theme *rm_look_theme(const rm_look *k, const rf_paint *p) {
    const rf_theme *t = NULL;
    if (k && k->style[0] && !rm_ieq(k->style, "Inherit")) t = rf_theme_find(k->style);
    if (!t) t = p && p->theme ? p->theme : rf_theme_current();
    return t;
}

unsigned rm_look_accent(const rm_look *k, const rf_theme *t) { return k && k->has_accent ? k->accent : t->accent; }

/* ================================================================== GDI+ (loaded on demand) */
typedef struct { float X, Y; } RmPointF;
typedef struct { UINT32 ver; void *cb; BOOL nothread, nocodecs; } RmGpInput;
static struct {
    int ok;
    int(WINAPI *startup)(ULONG_PTR *, const RmGpInput *, void *);
    int(WINAPI *from_hdc)(HDC, void **);
    int(WINAPI *del_g)(void *);
    int(WINAPI *smooth)(void *, int);
    int(WINAPI *pen)(DWORD, float, int, void **);
    int(WINAPI *del_pen)(void *);
    int(WINAPI *start_cap)(void *, int);
    int(WINAPI *end_cap)(void *, int);
    int(WINAPI *join)(void *, int);
    int(WINAPI *solid)(DWORD, void **);
    int(WINAPI *del_brush)(void *);
    int(WINAPI *arc)(void *, void *, float, float, float, float, float, float);
    int(WINAPI *fill_ell)(void *, void *, float, float, float, float);
    int(WINAPI *draw_ell)(void *, void *, float, float, float, float);
    int(WINAPI *pie)(void *, void *, float, float, float, float, float, float);
    int(WINAPI *lines)(void *, void *, const RmPointF *, int);
    int(WINAPI *poly)(void *, void *, const RmPointF *, int, int);
    int(WINAPI *translate)(void *, float, float, int);
    int(WINAPI *scale)(void *, float, float, int);
} gp;

static int rm_gp(void) {
    static int tried;
    HMODULE m;
    ULONG_PTR tok = 0;
    RmGpInput in;
    if (tried) return gp.ok;
    tried = 1;
    m = LoadLibraryW(L"gdiplus.dll");
    if (!m) return 0;
#define RMGP(f, n) do { FARPROC fp_ = GetProcAddress(m, n); memcpy(&gp.f, &fp_, sizeof fp_); } while (0)
    RMGP(startup, "GdiplusStartup"); RMGP(from_hdc, "GdipCreateFromHDC"); RMGP(del_g, "GdipDeleteGraphics");
    RMGP(smooth, "GdipSetSmoothingMode"); RMGP(pen, "GdipCreatePen1"); RMGP(del_pen, "GdipDeletePen");
    RMGP(start_cap, "GdipSetPenStartCap"); RMGP(end_cap, "GdipSetPenEndCap"); RMGP(join, "GdipSetPenLineJoin");
    RMGP(solid, "GdipCreateSolidFill"); RMGP(del_brush, "GdipDeleteBrush"); RMGP(arc, "GdipDrawArc");
    RMGP(fill_ell, "GdipFillEllipse"); RMGP(draw_ell, "GdipDrawEllipse"); RMGP(pie, "GdipFillPie");
    RMGP(lines, "GdipDrawLines"); RMGP(poly, "GdipFillPolygon");
    RMGP(translate, "GdipTranslateWorldTransform"); RMGP(scale, "GdipScaleWorldTransform");
#undef RMGP
    if (!gp.startup || !gp.from_hdc || !gp.del_g || !gp.smooth || !gp.pen || !gp.del_pen || !gp.start_cap ||
        !gp.end_cap || !gp.join || !gp.solid || !gp.del_brush || !gp.arc || !gp.fill_ell || !gp.draw_ell ||
        !gp.pie || !gp.lines || !gp.poly || !gp.translate || !gp.scale)
        return 0;
    memset(&in, 0, sizeof in);
    in.ver = 1;
    if (gp.startup(&tok, &in, NULL) != 0) return 0;
    gp.ok = 1;
    return 1;
}

static DWORD argb(unsigned c) {
    return 0xFF000000u | ((DWORD)GetRValue(c) << 16) | ((DWORD)GetGValue(c) << 8) | GetBValue(c);
}

static void *gp_graphics(const rf_paint *p) {
    void *g = NULL;
    if (!p || !p->hdc || !rm_gp()) return NULL;
    if (gp.from_hdc((HDC)p->hdc, &g) != 0) return NULL;
    gp.smooth(g, 4);
    if (GetLayout((HDC)p->hdc) & LAYOUT_RTL) {      /* mirrored (RightToLeft) DC: mirror like GDI does */
        BITMAP bm;
        HGDIOBJ b = GetCurrentObject((HDC)p->hdc, OBJ_BITMAP);
        if (b && GetObjectW(b, sizeof bm, &bm) && bm.bmWidth > 0) {
            gp.translate(g, (float)bm.bmWidth, 0, 0);
            gp.scale(g, -1, 1, 0);
        }
    }
    return g;
}

static void *gp_pen(unsigned color, double width) {
    void *pen = NULL;
    gp.pen(argb(color), (float)(width > 0 ? width : 1), 2, &pen);
    if (pen) {
        gp.start_cap(pen, 2);
        gp.end_cap(pen, 2);
        gp.join(pen, 2);
    }
    return pen;
}

/* ================================================================== drawing */
int rm_px(rf_handle h, double v) { return (int)floor(v * rf_dpi(h) / 96.0 + 0.5); }
int rm_unpx(rf_handle h, int px) { return (int)floor(px * 96.0 / rf_dpi(h) + 0.5); }

void rm_fill(const rf_paint *p, int x, int y, int w, int h, unsigned color) {
    RECT r;
    HBRUSH br;
    if (!p || !p->hdc || w <= 0 || h <= 0 || color == RF_NONE) return;
    r.left = x; r.top = y; r.right = x + w; r.bottom = y + h;
    br = CreateSolidBrush(color);
    FillRect((HDC)p->hdc, &r, br);
    DeleteObject(br);
}

void rm_ellipse(const rf_paint *p, double x, double y, double w, double h, unsigned fill, unsigned border, double bw) {
    void *g = gp_graphics(p);
    if (w <= 0 || h <= 0) { if (g) gp.del_g(g); return; }
    if (g) {
        if (fill != RF_NONE) {
            void *br = NULL;
            gp.solid(argb(fill), &br);
            gp.fill_ell(g, br, (float)x, (float)y, (float)w, (float)h);
            gp.del_brush(br);
        }
        if (border != RF_NONE && bw > 0) {
            void *pen = gp_pen(border, bw);
            gp.draw_ell(g, pen, (float)(x + bw / 2), (float)(y + bw / 2), (float)(w - bw), (float)(h - bw));
            gp.del_pen(pen);
        }
        gp.del_g(g);
        return;
    }
    if (p && p->hdc) {
        HDC dc = (HDC)p->hdc;
        HBRUSH br = fill != RF_NONE ? CreateSolidBrush(fill) : NULL;
        HPEN pen = border != RF_NONE && bw > 0 ? CreatePen(PS_SOLID, (int)bw, border) : (HPEN)GetStockObject(NULL_PEN);
        HGDIOBJ ob = SelectObject(dc, br ? (HGDIOBJ)br : GetStockObject(NULL_BRUSH)), op = SelectObject(dc, pen);
        Ellipse(dc, (int)x, (int)y, (int)(x + w), (int)(y + h));
        SelectObject(dc, ob);
        SelectObject(dc, op);
        if (br) DeleteObject(br);
        if (border != RF_NONE && bw > 0) DeleteObject(pen);
    }
}

void rm_arc(const rf_paint *p, double x, double y, double w, double h, double start, double sweep, unsigned color,
            double width) {
    void *g;
    if (w <= 0 || h <= 0 || sweep == 0) return;
    g = gp_graphics(p);
    if (g) {
        void *pen = gp_pen(color, width);
        gp.arc(g, pen, (float)x, (float)y, (float)w, (float)h, (float)start, (float)sweep);
        gp.del_pen(pen);
        gp.del_g(g);
        return;
    }
    if (p && p->hdc) {          /* GDI: a polyline along the ellipse */
        double pts[2 * 65];
        int i, n = 64;
        for (i = 0; i <= n; i++) {
            double a = (start + sweep * i / n) * M_PI / 180.0;
            pts[2 * i] = x + w / 2 + cos(a) * w / 2;
            pts[2 * i + 1] = y + h / 2 + sin(a) * h / 2;
        }
        rm_lines(p, pts, n + 1, color, width);
    }
}

void rm_pie(const rf_paint *p, double x, double y, double w, double h, double start, double sweep, unsigned color) {
    void *g;
    if (w <= 0 || h <= 0 || sweep == 0) return;
    g = gp_graphics(p);
    if (g) {
        void *br = NULL;
        gp.solid(argb(color), &br);
        gp.pie(g, br, (float)x, (float)y, (float)w, (float)h, (float)start, (float)sweep);
        gp.del_brush(br);
        gp.del_g(g);
        return;
    }
    {
        double pts[2 * 66];
        int i, n = 64;
        pts[0] = x + w / 2;
        pts[1] = y + h / 2;
        for (i = 0; i <= n; i++) {
            double a = (start + sweep * i / n) * M_PI / 180.0;
            pts[2 * (i + 1)] = x + w / 2 + cos(a) * w / 2;
            pts[2 * (i + 1) + 1] = y + h / 2 + sin(a) * h / 2;
        }
        rm_polygon(p, pts, n + 2, color);
    }
}

void rm_lines(const rf_paint *p, const double *xy, int n, unsigned color, double width) {
    void *g;
    int i;
    if (!p || !p->hdc || n < 2) return;
    g = gp_graphics(p);
    if (g) {
        RmPointF stackpts[64], *pts = n <= 64 ? stackpts : (RmPointF *)malloc(sizeof(RmPointF) * n);
        void *pen;
        if (!pts) { gp.del_g(g); return; }
        for (i = 0; i < n; i++) { pts[i].X = (float)xy[2 * i]; pts[i].Y = (float)xy[2 * i + 1]; }
        pen = gp_pen(color, width);
        gp.lines(g, pen, pts, n);
        gp.del_pen(pen);
        gp.del_g(g);
        if (pts != stackpts) free(pts);
        return;
    }
    {
        HDC dc = (HDC)p->hdc;
        HPEN pen = CreatePen(PS_SOLID, width > 1 ? (int)(width + 0.5) : 1, color), op = (HPEN)SelectObject(dc, pen);
        MoveToEx(dc, (int)xy[0], (int)xy[1], NULL);
        for (i = 1; i < n; i++) LineTo(dc, (int)xy[2 * i], (int)xy[2 * i + 1]);
        SelectObject(dc, op);
        DeleteObject(pen);
    }
}

void rm_polygon(const rf_paint *p, const double *xy, int n, unsigned fill) {
    void *g;
    int i;
    if (!p || !p->hdc || n < 3) return;
    g = gp_graphics(p);
    if (g) {
        RmPointF stackpts[72], *pts = n <= 72 ? stackpts : (RmPointF *)malloc(sizeof(RmPointF) * n);
        void *br = NULL;
        if (!pts) { gp.del_g(g); return; }
        for (i = 0; i < n; i++) { pts[i].X = (float)xy[2 * i]; pts[i].Y = (float)xy[2 * i + 1]; }
        gp.solid(argb(fill), &br);
        gp.poly(g, br, pts, n, 0);
        gp.del_brush(br);
        gp.del_g(g);
        if (pts != stackpts) free(pts);
        return;
    }
    {
        HDC dc = (HDC)p->hdc;
        POINT stackp[72], *pp = n <= 72 ? stackp : (POINT *)malloc(sizeof(POINT) * n);
        HBRUSH br = CreateSolidBrush(fill);
        HGDIOBJ ob, op;
        if (!pp) { DeleteObject(br); return; }
        for (i = 0; i < n; i++) { pp[i].x = (LONG)xy[2 * i]; pp[i].y = (LONG)xy[2 * i + 1]; }
        ob = SelectObject(dc, br);
        op = SelectObject(dc, GetStockObject(NULL_PEN));
        Polygon(dc, pp, n);
        SelectObject(dc, ob);
        SelectObject(dc, op);
        DeleteObject(br);
        if (pp != stackp) free(pp);
    }
}

void rm_chevron(const rf_paint *p, double cx, double cy, double s, int dir, unsigned color, double width) {
    double pts[6];
    double h = s / 2, q = s / 4;
    switch (dir) {
    case RM_UP: pts[0] = cx - h; pts[1] = cy + q; pts[2] = cx; pts[3] = cy - q; pts[4] = cx + h; pts[5] = cy + q; break;
    case RM_RIGHT: pts[0] = cx - q; pts[1] = cy - h; pts[2] = cx + q; pts[3] = cy; pts[4] = cx - q; pts[5] = cy + h; break;
    case RM_LEFT: pts[0] = cx + q; pts[1] = cy - h; pts[2] = cx - q; pts[3] = cy; pts[4] = cx + q; pts[5] = cy + h; break;
    default: pts[0] = cx - h; pts[1] = cy - q; pts[2] = cx; pts[3] = cy + q; pts[4] = cx + h; pts[5] = cy - q; break;
    }
    rm_lines(p, pts, 3, color, width);
}

void rm_checkmark(const rf_paint *p, double x, double y, double w, double h, unsigned color, double width) {
    double pts[6];
    pts[0] = x + w * 0.18; pts[1] = y + h * 0.52;
    pts[2] = x + w * 0.42; pts[3] = y + h * 0.75;
    pts[4] = x + w * 0.82; pts[5] = y + h * 0.28;
    rm_lines(p, pts, 3, color, width);
}

void rm_cross(const rf_paint *p, double cx, double cy, double s, unsigned color, double width) {
    double a[4], b[4];
    a[0] = cx - s / 2; a[1] = cy - s / 2; a[2] = cx + s / 2; a[3] = cy + s / 2;
    b[0] = cx + s / 2; b[1] = cy - s / 2; b[2] = cx - s / 2; b[3] = cy + s / 2;
    rm_lines(p, a, 2, color, width);
    rm_lines(p, b, 2, color, width);
}

void rm_shadow(const rf_paint *p, int x, int y, int w, int h, int radius, int depth, unsigned back) {
    int i;
    for (i = depth; i >= 1; i--) {
        double t = 0.035 * (depth - i + 1);
        rf_draw_rect(p, x - i + 1, y - i + 1 + depth / 2, w + 2 * i - 2, h + 2 * i - 2, rf_blend(back, 0, t), RF_NONE,
                     0, radius + i);
    }
}

void rm_gradient(const rf_paint *p, int x, int y, int w, int h, unsigned from, unsigned to, int vertical) {
    int i, n = vertical ? h : w, steps = n < 64 ? n : 64;
    if (steps <= 0) return;
    for (i = 0; i < steps; i++) {
        int a = n * i / steps, b = n * (i + 1) / steps;
        unsigned c = rf_blend(from, to, steps > 1 ? (double)i / (steps - 1) : 0);
        if (vertical) rm_fill(p, x, y + a, w, b - a, c);
        else rm_fill(p, x + a, y, b - a, h, c);
    }
}

/* ------------------------------------------------------------------ built-in glyphs (our own drawings) */
static const struct { const char *name; const char *path; } GLYPHS[] = {
    {"home", "M1 5 L5 1.5 L9 5 M2.5 4 L2.5 9 L7.5 9 L7.5 4 M4.2 9 L4.2 6 L5.8 6 L5.8 9"},
    {"settings", "O5 5 1.6 O5 5 3.4 M5 .6 L5 1.6 M5 8.4 L5 9.4 M.6 5 L1.6 5 M8.4 5 L9.4 5 M1.9 1.9 L2.6 2.6 "
                 "M7.4 7.4 L8.1 8.1 M8.1 1.9 L7.4 2.6 M2.6 7.4 L1.9 8.1"},
    {"user", "O5 3.3 2 A5 9.6 3.6 180 180"},
    {"users", "O3.8 3.6 1.6 A3.8 9 3 180 180 O7.1 3.1 1.3 A7.4 8 2.4 250 110"},
    {"mail", "R1 2.5 8 5.5 M1 2.7 L5 6 L9 2.7"},
    {"search", "O4.2 4.2 2.8 M6.3 6.3 L9 9"},
    {"save", "R1.5 1.5 7 7 M3 1.5 L3 4 L7 4 L7 1.5 R3 6 4 2.5"},
    {"open", "M1 3 L1 8.5 L9 8.5 L9 3.8 L4.8 3.8 L4 2.6 L1 2.6 Z"},
    {"folder", "M1 3 L1 8.5 L9 8.5 L9 3.8 L4.8 3.8 L4 2.6 L1 2.6 Z"},
    {"new", "M2.5 1 L6.5 1 L8 2.5 L8 9 L2.5 9 Z M6.5 1 L6.5 2.5 L8 2.5"},
    {"file", "M2.5 1 L6.5 1 L8 2.5 L8 9 L2.5 9 Z M6.5 1 L6.5 2.5 L8 2.5 M3.8 5 L6.7 5 M3.8 6.8 L6.7 6.8"},
    {"cut", "O3 7.5 1.4 O7 7.5 1.4 M3.8 6.4 L7 1 M6.2 6.4 L3 1"},
    {"copy", "R3.5 3.5 5.5 5.5 M2 6.5 L1.5 6.5 L1.5 1.5 L6.5 1.5 L6.5 2"},
    {"paste", "R2 2 6 7.5 R3.6 1 2.8 1.8 M3.6 5 L6.4 5 M3.6 6.8 L6.4 6.8"},
    {"undo", "M2 3.5 L5.5 3.5 A5.5 6 2.5 270 180 M5.5 8.5 L3.5 8.5 M3.6 1.9 L2 3.5 L3.6 5.1"},
    {"redo", "M8 3.5 L4.5 3.5 A4.5 6 2.5 270 -180 M4.5 8.5 L6.5 8.5 M6.4 1.9 L8 3.5 L6.4 5.1"},
    {"bold", "TB"}, {"italic", "TI"}, {"underline", "TU"},
    {"print", "R2.5 1 5 3 R1 4 8 3.5 R2.5 6 5 3"},
    {"chart", "M1 9 L9 9 B2 5 1.5 4 B4.5 2.5 1.5 6.5 B7 6 1.5 3"},
    {"bell", "M2 7.5 L8 7.5 M2.8 7.5 L2.8 4.5 A5 4.5 2.2 180 180 M7.2 4.5 L7.2 7.5 M4.2 8.8 L5.8 8.8"},
    {"calendar", "R1.5 2 7 7 M1.5 4.2 L8.5 4.2 M3.5 1 L3.5 3 M6.5 1 L6.5 3 B3 5.5 1 1 B5.5 5.5 1 1 B3 7 1 1"},
    {"clock", "O5 5 4 M5 2.5 L5 5 L7 6"},
    {"info", "O5 5 4 M5 4.5 L5 7.3 F5 3 .55"},
    {"warning", "M5 1 L9.5 9 L.5 9 Z M5 4 L5 6.3 F5 7.7 .5"},
    {"error", "O5 5 4 M3.4 3.4 L6.6 6.6 M6.6 3.4 L3.4 6.6"},
    {"success", "O5 5 4 M3 5.2 L4.5 6.7 L7.2 3.8"},
    {"help", "O5 5 4 T?"},
    {"close", "M2.5 2.5 L7.5 7.5 M7.5 2.5 L2.5 7.5"},
    {"plus", "M5 1.5 L5 8.5 M1.5 5 L8.5 5"},
    {"minus", "M1.5 5 L8.5 5"},
    {"menu", "M1.5 2.5 L8.5 2.5 M1.5 5 L8.5 5 M1.5 7.5 L8.5 7.5"},
    {"star", "M5 .8 L6.2 3.6 L9.3 3.9 L7 6 L7.7 9.1 L5 7.5 L2.3 9.1 L3 6 L.7 3.9 L3.8 3.6 Z"},
    {"heart", "M5 8.8 L1.5 5.3 A3.2 3.5 1.85 135 225 M5 3.4 A6.8 3.5 1.85 180 225 M8.5 5.3 L5 8.8"},
    {"grid", "R1.5 1.5 3 3 R5.5 1.5 3 3 R1.5 5.5 3 3 R5.5 5.5 3 3"},
    {"list", "M3.5 2.5 L9 2.5 M3.5 5 L9 5 M3.5 7.5 L9 7.5 F1.6 2.5 .55 F1.6 5 .55 F1.6 7.5 .55"},
    {"table", "R1 1.5 8 7 M1 4 L9 4 M1 6.3 L9 6.3 M4 1.5 L4 8.5"},
    {"filter", "M1 1.5 L9 1.5 L6 5.2 L6 8.8 L4 7.8 L4 5.2 Z"},
    {"refresh", "A5 5 3.5 300 290 M8.6 1.6 L8.1 3.5 L6.2 3.1"},
    {"play", "M3 1.5 L8.5 5 L3 8.5 G"},
    {"pause", "B2.5 1.5 1.8 7 B5.7 1.5 1.8 7"},
    {"stop", "B2 2 6 6"},
    {"lock", "R2 4.5 6 4.5 A5 4.5 2 180 180 F5 6.7 .55"},
    {"cloud", "A3 6.3 2 90 180 A5.3 4.8 2.6 200 160 A7.5 6.5 1.8 270 180 M3 8.3 L7.5 8.3"},
    {"download", "M5 1 L5 6.5 M2.8 4.5 L5 6.7 L7.2 4.5 M1.5 8.8 L8.5 8.8"},
    {"upload", "M5 7 L5 1.5 M2.8 3.7 L5 1.5 L7.2 3.7 M1.5 8.8 L8.5 8.8"},
    {"edit", "M2 8 L2.3 6.3 L7 1.6 L8.4 3 L3.7 7.7 Z M6 2.6 L7.4 4"},
    {"trash", "M1.5 2.5 L8.5 2.5 M4 2.5 L4 1.3 L6 1.3 L6 2.5 M2.5 2.5 L3 9 L7 9 L7.5 2.5 M4.2 4.3 L4.2 7.3 "
              "M5.8 4.3 L5.8 7.3"},
    {"tag", "M1.2 1.2 L5 1.2 L9 5.2 L5.2 9 L1.2 5 Z F3.2 3.2 .6"},
    {"link", "M4.2 5.8 L5.8 4.2 A3.3 6.7 1.6 45 180 M3.3 8.3 L1.7 6.7 A6.7 3.3 1.6 225 180 M4.5 2.4 L6 1"},
    {"phone", "R3 1 4 8 M4.5 7.6 L5.5 7.6"},
    {"globe", "O5 5 4 M1 5 L9 5 E5 5 1.8 4"},
    {"camera", "R1 3 8 5.5 O5 5.8 1.8 M3.5 3 L4.2 1.8 L5.8 1.8 L6.5 3"},
    {"image", "R1 1.5 8 7 M1.5 8 L4 5 L6 7 L7 6 L8.5 7.5 F6.8 3.6 .7"},
    {"music", "M4 7.5 L4 1.8 L8.5 1 L8.5 6.5 F3 7.6 1.1 F7.5 6.6 1.1"},
    {"video", "R1 2.5 5.8 5 M6.8 4.3 L9 3 L9 7 L6.8 5.7 Z"},
    {"database", "E5 2.3 3.5 1.3 M1.5 2.3 L1.5 7.7 M8.5 2.3 L8.5 7.7 Q5 7.7 3.5 1.3 0 180 Q5 5 3.5 1.3 0 180"},
    {"code", "M3.5 2.5 L1 5 L3.5 7.5 M6.5 2.5 L9 5 L6.5 7.5 M5.8 1.5 L4.2 8.5"},
    {"terminal", "R1 1.5 8 7 M2.5 3.8 L4.2 5.2 L2.5 6.6 M5 6.8 L7.5 6.8"},
    {"bug", "E5 5.8 2.2 3 M5 3 L5 8.8 M2.8 5 L1 4 M7.2 5 L9 4 M2.8 7 L1 8 M7.2 7 L9 8 M3.8 2.6 L3 1 M6.2 2.6 L7 1"},
    {"light", "O5 5 2 M5 .8 L5 1.8 M5 8.2 L5 9.2 M.8 5 L1.8 5 M8.2 5 L9.2 5 M2 2 L2.7 2.7 M7.3 7.3 L8 8 "
              "M8 2 L7.3 2.7 M2.7 7.3 L2 8"},
    {"dark", "A5 5 3.8 300 300 A6.9 3.4 2.6 120 -150"},
    {"send", "M1 4.5 L9 1 L5.5 9 L4.5 5.5 Z M4.5 5.5 L9 1"},
    {"attach", "M7 3 L3.5 6.5 A4.3 7.3 1.1 135 180 M5.1 8.1 L8 5.2 A6.8 4 1.7 45 -220"},
    {"flag", "M2 9.5 L2 1 M2 1.5 L8.5 1.5 L7 3.8 L8.5 6 L2 6"},
    {"pin", "O5 3.8 2.7 M5 6.5 L5 9.5 F5 3.8 .9"},
    {"eye", "Q5 5 4.2 2.8 180 180 Q5 5 4.2 2.8 0 180 O5 5 1.3"},
};

int rm_has_icon(const char *image) {
    size_t i;
    if (!image || !*image) return 0;
    if (strchr(image, '.')) return 1;
    for (i = 0; i < sizeof GLYPHS / sizeof GLYPHS[0]; i++)
        if (rm_ieq(GLYPHS[i].name, image)) return 1;
    return 0;
}

static double num(const char **s) {
    char *e;
    double v;
    while (**s == ' ' || **s == ',') (*s)++;
    v = strtod(*s, &e);
    *s = e;
    return v;
}

static void glyph(const rf_paint *p, const char *path, double x, double y, double size, unsigned color) {
    double k = size / 10.0, lw = size / 11.0 < 1.2 ? 1.2 : size / 11.0;
    double pts[64];
    int n = 0;
    const char *s = path;
#define GX(v) (x + (v) * k)
#define GY(v) (y + (v) * k)
#define FLUSH() do { if (n >= 2) rm_lines(p, pts, n, color, lw); n = 0; } while (0)
    while (*s) {
        char c = *s++;
        if (c == ' ') continue;
        if (c == 'M') {
            FLUSH();
            pts[0] = GX(num(&s));
            pts[1] = GY(num(&s));
            n = 1;
        } else if (c == 'L') {
            double a = GX(num(&s)), b = GY(num(&s));
            if (n < 32) { pts[2 * n] = a; pts[2 * n + 1] = b; n++; }
        } else if (c == 'Z') {
            if (n >= 2 && n < 32) { pts[2 * n] = pts[0]; pts[2 * n + 1] = pts[1]; n++; }
            FLUSH();
        } else if (c == 'G') {
            if (n >= 3) rm_polygon(p, pts, n, color);
            n = 0;
        } else if (c == 'O' || c == 'F') {
            double cx = num(&s), cy = num(&s), r = num(&s);
            FLUSH();
            if (c == 'O') rm_ellipse(p, GX(cx - r), GY(cy - r), 2 * r * k, 2 * r * k, RF_NONE, color, lw);
            else rm_ellipse(p, GX(cx - r), GY(cy - r), 2 * r * k, 2 * r * k, color, RF_NONE, 0);
        } else if (c == 'E') {
            double cx = num(&s), cy = num(&s), rx = num(&s), ry = num(&s);
            FLUSH();
            rm_ellipse(p, GX(cx - rx), GY(cy - ry), 2 * rx * k, 2 * ry * k, RF_NONE, color, lw);
        } else if (c == 'R' || c == 'B') {
            double rx = num(&s), ry = num(&s), rw = num(&s), rh = num(&s);
            FLUSH();
            if (c == 'R') {
                double q[10];
                q[0] = GX(rx); q[1] = GY(ry); q[2] = GX(rx + rw); q[3] = GY(ry); q[4] = GX(rx + rw); q[5] = GY(ry + rh);
                q[6] = GX(rx); q[7] = GY(ry + rh); q[8] = GX(rx); q[9] = GY(ry);
                rm_lines(p, q, 5, color, lw);
            } else {
                rf_draw_rect(p, (int)GX(rx), (int)GY(ry), (int)(rw * k + 0.5), (int)(rh * k + 0.5), color, RF_NONE, 0, 0);
            }
        } else if (c == 'A' || c == 'Q') {
            double cx = num(&s), cy = num(&s), rx = num(&s), ry = c == 'Q' ? num(&s) : rx;
            double st = num(&s), sw = num(&s);
            FLUSH();
            rm_arc(p, GX(cx - rx), GY(cy - ry), 2 * rx * k, 2 * ry * k, st, sw, color, lw);
        } else if (c == 'T') {
            HGDIOBJ old;
            FLUSH();
            old = rm_font_push(p, size / (rm_text_h(p) > 0 ? rm_text_h(p) : size) * 0.95, 1);
            rf_draw_text(p, s, (int)x, (int)y, (int)size, (int)size, color, RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
            rm_font_pop(p, old);
            break;
        } else {
            break;
        }
    }
    FLUSH();
#undef GX
#undef GY
#undef FLUSH
}

void rm_icon(const rf_paint *p, const char *image, int x, int y, int w, int h, unsigned color) {
    size_t i;
    double size;
    if (!image || !*image || w <= 0 || h <= 0) return;
    if (strchr(image, '.')) { rf_draw_image(p, image, x, y, w, h); return; }
    size = w < h ? w : h;
    for (i = 0; i < sizeof GLYPHS / sizeof GLYPHS[0]; i++)
        if (rm_ieq(GLYPHS[i].name, image)) {
            glyph(p, GLYPHS[i].path, x + (w - size) / 2, y + (h - size) / 2, size, color);
            return;
        }
}

/* ================================================================== fonts / text */
HGDIOBJ rm_font_push(const rf_paint *p, double scale, int bold) {
    LOGFONTW lf;
    HFONT f;
    HGDIOBJ cur;
    if (!p || !p->hdc) return NULL;
    cur = GetCurrentObject((HDC)p->hdc, OBJ_FONT);
    memset(&lf, 0, sizeof lf);
    if (!GetObjectW(p->font ? (HGDIOBJ)p->font : cur, sizeof lf, &lf)) return NULL;
    if (scale > 0 && scale != 1) lf.lfHeight = (LONG)(lf.lfHeight * scale + (lf.lfHeight < 0 ? -0.5 : 0.5));
    if (bold == 1) lf.lfWeight = FW_SEMIBOLD;
    else if (bold == 2) lf.lfWeight = FW_BOLD;
    else if (bold == -1) lf.lfWeight = FW_NORMAL;
    lf.lfQuality = CLEARTYPE_QUALITY;
    f = CreateFontIndirectW(&lf);
    if (!f) return NULL;
    return SelectObject((HDC)p->hdc, f);
}

void rm_font_pop(const rf_paint *p, HGDIOBJ old) {
    if (!p || !p->hdc || !old) return;
    DeleteObject(SelectObject((HDC)p->hdc, old));
}

int rm_text_w(const rf_paint *p, const char *text) {
    SIZE sz;
    wchar_t *w;
    if (!p || !p->hdc || !text || !*text) return 0;
    w = rm_wide(text);
    if (!w) return 0;
    sz.cx = 0;
    GetTextExtentPoint32W((HDC)p->hdc, w, (int)wcslen(w), &sz);
    free(w);
    return sz.cx;
}

int rm_text_h(const rf_paint *p) {
    TEXTMETRICW tm;
    if (!p || !p->hdc) return 0;
    if (!GetTextMetricsW((HDC)p->hdc, &tm)) return 0;
    return tm.tmHeight;
}

void rm_text(const rf_paint *p, const char *text, int x, int y, int w, int h, unsigned color, int align) {
    rf_draw_text(p, text, x, y, w, h, color, align);
}

/* ================================================================== popups */
static int menu_fill(HMENU m, rm_item *items, int n, rm_item **map, int *next, int cap) {
    int i;
    for (i = 0; i < n; i++) {
        rm_item *it = &items[i];
        wchar_t *w;
        if (rm_ieq(it->text, "-")) { AppendMenuW(m, MF_SEPARATOR, 0, NULL); continue; }
        w = rm_wide(it->text);
        if (it->n) {
            HMENU sub = CreatePopupMenu();
            menu_fill(sub, it->items, it->n, map, next, cap);
            AppendMenuW(m, MF_POPUP | (it->enabled ? 0 : MF_GRAYED), (UINT_PTR)sub, w ? w : L"");
        } else if (*next < cap) {
            map[*next] = it;
            AppendMenuW(m, MF_STRING | (it->checked ? MF_CHECKED : 0) | (it->enabled ? 0 : MF_GRAYED),
                        (UINT_PTR)(*next + 1), w ? w : L"");
            (*next)++;
        }
        free(w);
    }
    return *next;
}

rm_item *rm_popup_menu(rf_handle owner, rm_item *items, int n, int x, int y) {
    rm_item *map[256];
    int next = 0, cmd;
    HMENU m;
    HWND hw = (HWND)rf_hwnd(owner);
    if (!items || n <= 0) return NULL;
    m = CreatePopupMenu();
    menu_fill(m, items, n, map, &next, 256);
    cmd = (int)TrackPopupMenuEx(m, TPM_RETURNCMD | TPM_NONOTIFY | TPM_LEFTALIGN | TPM_TOPALIGN, x, y,
                                hw ? GetAncestor(hw, GA_ROOT) : NULL, NULL);
    DestroyMenu(m);
    return cmd >= 1 && cmd <= next ? map[cmd - 1] : NULL;
}

int rm_window_dpi(HWND h) {
    typedef UINT(WINAPI * fn_t)(HWND);
    static fn_t fn;
    static int looked;
    int d = 0;
    if (!looked) {
        looked = 1;
        fn = (fn_t)(void *)GetProcAddress(GetModuleHandleW(L"user32.dll"), "GetDpiForWindow");
    }
    if (fn && h) d = (int)fn(h);
    if (d <= 0) {
        HDC dc = GetDC(NULL);
        d = GetDeviceCaps(dc, LOGPIXELSY);
        ReleaseDC(NULL, dc);
    }
    return d > 0 ? d : 96;
}

void rm_paint_window(HWND hwnd, HDC target, const rf_theme *t, int dpi, unsigned back, rm_paint_fn fn, void *user) {
    PAINTSTRUCT ps;
    HDC dc = target ? target : BeginPaint(hwnd, &ps), mem;
    RECT r;
    HBITMAP bmp, oldb;
    HFONT font, oldf;
    rf_paint p;
    wchar_t *face;
    GetClientRect(hwnd, &r);
    if (r.right > 0 && r.bottom > 0) {
        mem = CreateCompatibleDC(dc);
        bmp = CreateCompatibleBitmap(dc, r.right, r.bottom);
        oldb = (HBITMAP)SelectObject(mem, bmp);
        face = rm_wide(t && t->font_name ? t->font_name : "Segoe UI");
        font = CreateFontW(-(int)((t && t->font_size > 0 ? t->font_size : 9) * dpi / 72.0 + 0.5), 0, 0, 0, FW_NORMAL,
                           0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, face ? face : L"Segoe UI");
        free(face);
        oldf = (HFONT)SelectObject(mem, font);
        SetBkMode(mem, TRANSPARENT);
        memset(&p, 0, sizeof p);
        p.size = (int)sizeof p;
        p.hdc = mem;
        p.width = r.right;
        p.height = r.bottom;
        p.dpi = dpi;
        p.theme = t ? t : rf_theme_current();
        p.enabled = 1;
        p.font = font;
        p.text = "";
        p.back = back;
        p.fore = p.theme->window_text;
        rm_fill(&p, 0, 0, r.right, r.bottom, back);
        if (fn) fn(hwnd, &p, user);
        BitBlt(dc, 0, 0, r.right, r.bottom, mem, 0, 0, SRCCOPY);
        SelectObject(mem, oldf);
        DeleteObject(font);
        SelectObject(mem, oldb);
        DeleteObject(bmp);
        DeleteDC(mem);
    }
    if (!target) EndPaint(hwnd, &ps);
}

const wchar_t *rm_window_class(const wchar_t *name, WNDPROC proc, int shadow) {
    WNDCLASSEXW wc;
    if (GetClassInfoExW(GetModuleHandleW(NULL), name, &wc)) return name;
    memset(&wc, 0, sizeof wc);
    wc.cbSize = sizeof wc;
    wc.style = CS_DBLCLKS | (shadow ? CS_DROPSHADOW : 0);
    wc.lpfnWndProc = proc;
    wc.hInstance = GetModuleHandleW(NULL);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    wc.lpszClassName = name;
    RegisterClassExW(&wc);
    return name;
}

/* ================================================================== modal drop-down popups */
static LRESULT CALLBACK popup_proc(HWND h, UINT m, WPARAM w, LPARAM l) {
    rm_popup *pp = (rm_popup *)GetPropW(h, L"rm.popup");
    if (!pp) return DefWindowProcW(h, m, w, l);
    switch (m) {
    case WM_ERASEBKGND: return 1;
    case WM_PAINT: case WM_PRINTCLIENT: {
        struct { rm_popup *pp; } u;
        u.pp = pp;
        rm_paint_window(h, m == WM_PRINTCLIENT ? (HDC)w : NULL, pp->theme, pp->dpi, pp->theme->input, NULL, NULL);
        (void)u;
        return 0;
    }
    case WM_MOUSEACTIVATE: return MA_NOACTIVATE;
    default: break;
    }
    return DefWindowProcW(h, m, w, l);
}

static void popup_paint_fn(HWND h, const rf_paint *p, void *user) {
    rm_popup *pp = (rm_popup *)user;
    (void)h;
    rf_draw_rect(p, 0, 0, p->width, p->height, RF_NONE, pp->theme->border, 1, 0);
    if (pp->paint) pp->paint(pp, p);
}

static LRESULT CALLBACK popup_proc2(HWND h, UINT m, WPARAM w, LPARAM l) {
    rm_popup *pp = (rm_popup *)GetPropW(h, L"rm.popup");
    if (pp && (m == WM_PAINT || m == WM_PRINTCLIENT)) {
        rm_paint_window(h, m == WM_PRINTCLIENT ? (HDC)w : NULL, pp->theme, pp->dpi, pp->theme->input, popup_paint_fn, pp);
        return 0;
    }
    return popup_proc(h, m, w, l);
}

void rm_popup_redraw(rm_popup *pp) {
    if (pp && pp->hwnd) InvalidateRect(pp->hwnd, NULL, FALSE);
}

void rm_popup_place(rf_handle owner, int w, int h, int *x, int *y) {
    RECT r, wa;
    HWND hw = (HWND)rf_hwnd(owner);
    HMONITOR mon;
    MONITORINFO mi;
    GetWindowRect(hw, &r);
    mon = MonitorFromWindow(hw, MONITOR_DEFAULTTONEAREST);
    mi.cbSize = sizeof mi;
    GetMonitorInfoW(mon, &mi);
    wa = mi.rcWork;
    *x = (GetWindowLongW(GetAncestor(hw, GA_ROOT), GWL_EXSTYLE) & WS_EX_LAYOUTRTL) ? r.right - w : r.left;
    *y = r.bottom + 1;
    if (*y + h > wa.bottom && r.top - h - 1 >= wa.top) *y = r.top - h - 1;
    if (*x + w > wa.right) *x = wa.right - w;
    if (*x < wa.left) *x = wa.left;
}

int rm_popup_run(rm_popup *pp, int x, int y, int w, int h) {
    HWND owner = (HWND)rf_hwnd(pp->owner), root = owner ? GetAncestor(owner, GA_ROOT) : NULL;
    MSG msg;
    const wchar_t *cls = rm_window_class(L"RadModernPopup", popup_proc2, 1);
    pp->result = -1;
    pp->done = 0;
    pp->w = w;
    pp->h = h;
    if (!pp->theme) pp->theme = rf_theme_current();
    if (!pp->dpi) pp->dpi = rf_dpi(pp->owner);
    pp->hwnd = CreateWindowExW(WS_EX_TOOLWINDOW | WS_EX_TOPMOST | WS_EX_NOACTIVATE, cls, L"", WS_POPUP, x, y, w, h,
                               root, NULL, GetModuleHandleW(NULL), NULL);
    if (!pp->hwnd) return -1;
    SetPropW(pp->hwnd, L"rm.popup", (HANDLE)pp);
    ShowWindow(pp->hwnd, SW_SHOWNOACTIVATE);
    UpdateWindow(pp->hwnd);
    SetCapture(pp->hwnd);
    while (!pp->done && GetMessageW(&msg, NULL, 0, 0)) {
        if (GetCapture() != pp->hwnd) { pp->done = 1; break; }
        if (msg.message == WM_KEYDOWN || msg.message == WM_SYSKEYDOWN) {
            if (msg.wParam == VK_ESCAPE || (msg.message == WM_SYSKEYDOWN && msg.wParam == VK_UP) ||
                msg.wParam == VK_TAB) { pp->result = -1; pp->done = 1; break; }
            if (pp->key && pp->key(pp, (unsigned)msg.wParam)) { pp->done = 1; break; }
            continue;
        }
        if (msg.message == WM_CHAR || msg.message == WM_SYSCHAR || msg.message == WM_KEYUP) continue;
        if (msg.hwnd == pp->hwnd && msg.message >= WM_MOUSEFIRST && msg.message <= WM_MOUSELAST) {
            int mx = GET_X_LPARAM(msg.lParam), my = GET_Y_LPARAM(msg.lParam);
            if (msg.message == WM_MOUSEWHEEL) {
                if (pp->mouse && pp->mouse(pp, WM_MOUSEWHEEL, 0, GET_WHEEL_DELTA_WPARAM(msg.wParam))) pp->done = 1;
                continue;
            }
            if ((msg.message == WM_LBUTTONDOWN || msg.message == WM_RBUTTONDOWN) &&
                (mx < 0 || my < 0 || mx >= w || my >= h)) { pp->result = -1; pp->done = 1; break; }
            if (pp->mouse && (msg.message == WM_MOUSEMOVE || msg.message == WM_LBUTTONDOWN || msg.message == WM_LBUTTONUP))
                if (pp->mouse(pp, msg.message, mx, my)) { pp->done = 1; break; }
            continue;
        }
        if (msg.message == WM_QUIT) { PostQuitMessage((int)msg.wParam); break; }
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
        if (root && GetForegroundWindow() != root && GetForegroundWindow() != pp->hwnd) { pp->result = -1; pp->done = 1; }
    }
    if (GetCapture() == pp->hwnd) ReleaseCapture();
    RemovePropW(pp->hwnd, L"rm.popup");
    DestroyWindow(pp->hwnd);
    pp->hwnd = NULL;
    return pp->result;
}

/* ================================================================== animation / events */
int rm_anim_step(rm_anim *a, double step) {
    if (a->v < a->target) a->v = a->v + step > a->target ? a->target : a->v + step;
    else if (a->v > a->target) a->v = a->v - step < a->target ? a->target : a->v - step;
    return a->v != a->target;
}

/* last item event per control (a small table: controls with item events are few) */
typedef struct { rf_handle h; char item[96]; int index, row, col; } EvLast;
static EvLast g_ev[64];
static int g_nev;

static EvLast *ev_slot(rf_handle h, int create) {
    int i;
    for (i = 0; i < g_nev; i++)
        if (g_ev[i].h == h) return &g_ev[i];
    if (!create) return NULL;
    i = g_nev < 64 ? g_nev++ : (int)(((uintptr_t)h >> 4) % 64);
    memset(&g_ev[i], 0, sizeof g_ev[i]);
    g_ev[i].h = h;
    g_ev[i].index = g_ev[i].row = g_ev[i].col = -1;
    return &g_ev[i];
}

const char *rm_event_get(rf_handle h, const char *prop) {
    EvLast *e;
    if (!prop || (prop[0] != 'E' && prop[0] != 'e')) return NULL;
    if (!rm_ieq(prop, "EventItem") && !rm_ieq(prop, "EventIndex") && !rm_ieq(prop, "EventRow") && !rm_ieq(prop, "EventColumn"))
        return NULL;
    e = ev_slot(h, 0);
    if (rm_ieq(prop, "EventItem")) return e ? e->item : "";
    if (rm_ieq(prop, "EventIndex")) return rad_str(e ? e->index : -1);
    if (rm_ieq(prop, "EventRow")) return rad_str(e ? e->row : -1);
    return rad_str(e ? e->col : -1);
}

void rm_raise_item(rf_handle h, const char *event, const char *name, int index) {
    char args[160];
    EvLast *e = ev_slot(h, 1);
    snprintf(e->item, sizeof e->item, "%s", name ? name : "");
    e->index = index;
    snprintf(args, sizeof args, "%s %d", name && *name ? name : "-", index);
    rf_raise(h, event, args);
}

void rm_raise_cell(rf_handle h, const char *event, int row, int col) {
    char args[48];
    EvLast *e = ev_slot(h, 1);
    e->row = e->index = row;
    e->col = col;
    snprintf(args, sizeof args, "%d %d", row, col);
    rf_raise(h, event, args);
}
