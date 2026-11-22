/* rm_kit - shared helpers of the RAD Modern (Rm*) control modules of radforms.
 *
 * Every rm_*.c module says "RF_REQUIRES: rm_kit.c" so the IDE builder links rm_kit.c with it (once).
 * Only Win32 + the public radforms ABI are used; GDI+ (gdiplus.dll, a Windows system DLL) is loaded on
 * demand for anti-aliased arcs / ellipses / lines, with plain GDI as the fallback.
 *
 * Contents: strings and colours, ";" lists, a tiny JSON reader, item trees (menus, ribbon tabs, tree
 * nodes, side-bar groups ...), the control look (Style / AccentColor -> theme), drawing (ellipses, arcs,
 * polylines, chevrons, check marks, shadows, gradients, built-in vector glyphs), fonts, popup menus and a
 * double-buffered paint for the modules' own popup windows (toasts, drop-downs).
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#ifndef RM_KIT_H
#define RM_KIT_H

#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "radforms.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ------------------------------------------------------------------ strings / numbers / colours */
int rm_ieq(const char *a, const char *b);                 /* case-insensitive ASCII compare */
int rm_bool(const char *v);                               /* "True" / "1" / "Yes" / "-1" */
int rm_int(const char *v);
const char *rm_tf(int b);                                 /* "True" / "False" */
char *rm_strdup(const char *s);                           /* malloc'd copy ("" for NULL) */
void rm_setstr(char **dst, const char *v);                /* free + copy */
int rm_color(const char *v, unsigned *out);               /* "#RRGGBB" / "R,G,B" -> COLORREF; 0 = none */
const char *rm_colorstr(unsigned c);                      /* "#RRGGBB" */
wchar_t *rm_wide(const char *s);                          /* malloc'd UTF-16 */
char *rm_utf8(const wchar_t *w);                          /* malloc'd UTF-8 */
unsigned rm_luma(unsigned c);                             /* 0..255 */
unsigned rm_on(unsigned back);                            /* black / white text readable on *back* */
const char *rm_arg(const char *args, int n);              /* field n of a \t separated list (ring) */

/* growing text buffer */
typedef struct { char *s; size_t n, cap; } rm_sb;
void rm_sb_add(rm_sb *b, const char *s);
void rm_sb_addc(rm_sb *b, char c);
void rm_sb_json(rm_sb *b, const char *s);                 /* adds "s" with JSON escapes */
const char *rm_sb_ring(rm_sb *b);                         /* copy into a ring buffer, frees b */

/* ------------------------------------------------------------------ lists "a;b;c" */
typedef struct { int n, cap; char **v; } rm_list;
void rm_list_parse(rm_list *l, const char *text, char sep);   /* replaces the content */
void rm_list_free(rm_list *l);
void rm_list_add(rm_list *l, const char *s, int at);          /* at < 0 = append */
void rm_list_remove(rm_list *l, int i);
const char *rm_list_get(const rm_list *l, int i);             /* "" when out of range */
const char *rm_list_join(const rm_list *l, char sep);         /* ring buffer */
int rm_list_find(const rm_list *l, const char *s);            /* case-insensitive, -1 = none */

/* ------------------------------------------------------------------ JSON (read only) */
enum { RMJ_NULL, RMJ_BOOL, RMJ_NUM, RMJ_STR, RMJ_ARR, RMJ_OBJ };
typedef struct rm_json {
    int type;
    char *key;                /* member name inside an object */
    char *str;                /* RMJ_STR */
    double num;               /* RMJ_NUM / RMJ_BOOL */
    struct rm_json *kids;     /* RMJ_ARR / RMJ_OBJ */
    int n;
} rm_json;
rm_json *rm_json_parse(const char *text);                 /* NULL = not JSON */
void rm_json_free(rm_json *j);
const rm_json *rm_json_get(const rm_json *obj, const char *key);    /* case-insensitive */
const char *rm_json_text(const rm_json *obj, const char *key, const char *def);  /* str / number as text */
double rm_json_num(const rm_json *obj, const char *key, double def);
int rm_json_bool(const rm_json *obj, const char *key, int def);

/* ------------------------------------------------------------------ item trees */
typedef struct rm_item {
    char *text, *name, *image, *kind, *tag, *shortcut, *tip, *value;
    int checked, expanded, enabled, large, count, width, lazy, group;
    unsigned color;
    int has_color;
    struct rm_item *items;    /* children ("Items" / "Nodes" / "Groups" / "Pages") */
    int n;
    /* run-time state of the modules (not parsed) */
    int x, y, w, h, hot, depth, visible_row;
} rm_item;
/* JSON array of {Text, Name, Image, Kind, Items ...} or a plain "a;b;c" list (no nesting; an item
 * "-" is a separator). Names default to the text without spaces. */
rm_item *rm_items_parse(const char *text, int *count);
void rm_items_free(rm_item *items, int n);
void rm_item_clear(rm_item *it);                          /* frees what one item owns */
rm_item *rm_items_find(rm_item *items, int n, const char *name);    /* depth-first by Name (or Text) */
const char *rm_items_json(const rm_item *items, int n);  /* back to JSON (ring buffer) */

/* ------------------------------------------------------------------ the look of a control */
typedef struct {
    char style[16];           /* Inherit | Light | Dark | Office | Metro (or any defined theme) */
    unsigned accent;
    int has_accent;
} rm_look;
int rm_look_set(rm_look *k, const char *prop, const char *value);   /* Style / AccentColor -> 1 */
const char *rm_look_get(const rm_look *k, const char *prop);        /* NULL = not a look property */
const rf_theme *rm_look_theme(const rm_look *k, const rf_paint *p); /* the theme to draw with */
unsigned rm_look_accent(const rm_look *k, const rf_theme *t);
#define RM_LOOK_PROPS "Style,AccentColor"

/* ------------------------------------------------------------------ drawing (device pixels) */
int rm_px(rf_handle h, double v96);                       /* outside paint(): 96-DPI -> device pixels */
int rm_unpx(rf_handle h, int px);
void rm_ellipse(const rf_paint *p, double x, double y, double w, double h, unsigned fill, unsigned border, double bw);
void rm_arc(const rf_paint *p, double x, double y, double w, double h, double start, double sweep, unsigned color,
            double width);                                /* degrees, 0 = 3 o'clock, clockwise */
void rm_pie(const rf_paint *p, double x, double y, double w, double h, double start, double sweep, unsigned color);
void rm_lines(const rf_paint *p, const double *xy, int npoints, unsigned color, double width);   /* polyline */
void rm_polygon(const rf_paint *p, const double *xy, int npoints, unsigned fill);
void rm_chevron(const rf_paint *p, double cx, double cy, double size, int dir, unsigned color, double width);
enum { RM_DOWN, RM_UP, RM_RIGHT, RM_LEFT };
void rm_checkmark(const rf_paint *p, double x, double y, double w, double h, unsigned color, double width);
void rm_cross(const rf_paint *p, double cx, double cy, double size, unsigned color, double width);
void rm_shadow(const rf_paint *p, int x, int y, int w, int h, int radius, int depth, unsigned back);
void rm_gradient(const rf_paint *p, int x, int y, int w, int h, unsigned from, unsigned to, int vertical);
void rm_fill(const rf_paint *p, int x, int y, int w, int h, unsigned color);      /* plain rectangle */
/* an image file / embedded image (a value with a "." extension) or a built-in vector glyph by name:
 * home settings user users mail search save open new folder file cut copy paste undo redo bold italic
 * underline print chart bell calendar clock info warning error success help close plus minus menu star
 * heart grid list table filter refresh play pause stop lock cloud download upload edit trash tag link
 * phone globe camera image music video database code terminal bug light dark send attach flag pin eye */
void rm_icon(const rf_paint *p, const char *image, int x, int y, int w, int h, unsigned color);
int rm_has_icon(const char *image);

/* fonts: the control's font scaled (1.0 = same) and / or bold; restore with rm_font_pop */
HGDIOBJ rm_font_push(const rf_paint *p, double scale, int bold);
void rm_font_pop(const rf_paint *p, HGDIOBJ old);
int rm_text_w(const rf_paint *p, const char *text);      /* width of *text* with the selected font */
int rm_text_h(const rf_paint *p);                         /* line height of the selected font */
/* text that follows the reading direction: RF_ALIGN_LEFT becomes right-aligned in an RTL form */
void rm_text(const rf_paint *p, const char *text, int x, int y, int w, int h, unsigned color, int align);

/* ------------------------------------------------------------------ popups */
/* a native popup menu of the items at screen point (x, y); returns the chosen item (NULL = none) */
rm_item *rm_popup_menu(rf_handle owner, rm_item *items, int n, int x, int y);
/* double-buffered paint of a module's own window (toast, drop-down): fn draws with *p* */
typedef void (*rm_paint_fn)(HWND hwnd, const rf_paint *p, void *user);
void rm_paint_window(HWND hwnd, HDC target, const rf_theme *t, int dpi, unsigned back, rm_paint_fn fn, void *user);
int rm_window_dpi(HWND h);
/* registers (once) a window class whose WndProc is *proc*; returns the class name */
const wchar_t *rm_window_class(const wchar_t *name, WNDPROC proc, int shadow);

/* a modal drop-down window (combo list, date picker): runs its own message loop until a pick, Escape or
 * a click outside; *paint* draws it, *mouse* gets WM_MOUSEMOVE / WM_LBUTTONDOWN / WM_LBUTTONUP /
 * WM_MOUSEWHEEL (x, y in the popup's client pixels; for the wheel y = delta) and *key* the keys of the
 * owner; both return 1 to close (set pp->result first). Screen rectangle in device pixels. */
typedef struct rm_popup {
    HWND hwnd;
    rf_handle owner;
    const rf_theme *theme;
    int dpi, w, h, result, done;
    void *user;
    void (*paint)(struct rm_popup *pp, const rf_paint *p);
    int (*mouse)(struct rm_popup *pp, unsigned msg, int x, int y);
    int (*key)(struct rm_popup *pp, unsigned vk);
} rm_popup;
int rm_popup_run(rm_popup *pp, int x, int y, int w, int h);       /* returns pp->result (-1 = cancelled) */
void rm_popup_redraw(rm_popup *pp);
/* (x, y, w, h) below (or above, when there is no room) the owner's window, in screen pixels */
void rm_popup_place(rf_handle owner, int w, int h, int *x, int *y);

/* ------------------------------------------------------------------ animation */
typedef struct { double v, target; } rm_anim;
int rm_anim_step(rm_anim *a, double step);                /* 1 = still moving */
#define RM_ANIM_TIMER 0x524D                              /* timer id the modules use ("RM") */

/* ------------------------------------------------------------------ common module plumbing */
/* raise "ItemClick" etc. with "<name> <index>" args (GUI Bridge style: rad_arg(0), rad_arg(1)) */
void rm_raise_item(rf_handle h, const char *event, const char *name, int index);
void rm_raise_cell(rf_handle h, const char *event, int row, int col);
/* EventItem / EventIndex / EventRow / EventColumn of the last item event of *h* (NULL = another property);
 * every Rm class's get() asks it first */
const char *rm_event_get(rf_handle h, const char *prop);

#ifdef __cplusplus
}
#endif
#endif
