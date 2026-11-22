/* RAD Modern data views:
 *   RmGrid      advanced grid: typed columns (Text, Number, Check, Combo, Date, Image, Progress, Button),
 *               sorting (header click), filter row, grouping by a column (collapsible group rows),
 *               frozen columns, in-place editing, alternating rows, selection modes, own scroll bars
 *   RmListView  modern list: Details (columns), Tiles and Cards views, images, activation
 * Columns: JSON [{"Text":"Name","Type":"Text","Width":120,"Frozen":true,"ReadOnly":false,"Items":"a;b"}] or
 * the short form "Name;Age:Number:60;Done:Check". Rows: "a|b|c;d|e|f" or a JSON array of arrays.
 *
 * RF_CLASSES: RmGrid RmListView
 * RF_REQUIRES: rm_kit.c
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#include "rm_kit.h"
#include <windowsx.h>
#include <commctrl.h>

enum { CT_TEXT, CT_NUMBER, CT_CHECK, CT_COMBO, CT_DATE, CT_IMAGE, CT_PROGRESS, CT_BUTTON };
static const char *const CTYPES[] = {"Text", "Number", "Check", "Combo", "Date", "Image", "Progress", "Button"};

typedef struct {
    char *text, *name, *items;
    int type, width, frozen, readonly;
} Col;

typedef struct {
    char **cells;
    int sel;
} Row;

typedef struct { int group; int row; } ViewRow;       /* group: 1 = a group header (row = first row of it) */

typedef struct {
    rm_look look;
    Col *cols;
    int ncols;
    Row *rows;
    int nrows, cap;
    ViewRow *view;
    int nview;
    int readonly, allow_sort, allow_filter, alternating, multi, cellsel, row_h96;
    int sort_col, sort_desc, cur_row, cur_col, top, hscroll, hot_view, hot_col, hot_head;
    int group_col;
    char **filters;             /* per column */
    char *colsrc, *group_name;
    unsigned char *closed;      /* collapsed groups by first row index */
    HWND edit;
    int edit_row, edit_col, editing_filter;
    rf_handle h;
    /* list view */
    int lv, lv_view;            /* 0 details 1 tiles 2 cards */
} RmGrid;

/* ------------------------------------------------------------------ data */
static void col_free(RmGrid *g) {
    int i;
    for (i = 0; i < g->ncols; i++) { free(g->cols[i].text); free(g->cols[i].name); free(g->cols[i].items); }
    free(g->cols);
    g->cols = NULL;
    if (g->filters) {
        for (i = 0; i < g->ncols; i++) free(g->filters[i]);
        free(g->filters);
        g->filters = NULL;
    }
    g->ncols = 0;
}

static int ctype_of(const char *s) {
    int i;
    for (i = 0; i < 8; i++)
        if (rm_ieq(s, CTYPES[i])) return i;
    if (rm_ieq(s, "CheckBox") || rm_ieq(s, "Bool")) return CT_CHECK;
    if (rm_ieq(s, "ComboBox")) return CT_COMBO;
    return CT_TEXT;
}

static void cols_parse(RmGrid *g, const char *v) {
    const char *p = v ? v : "";
    int i;
    col_free(g);
    while (*p == ' ' || *p == '\n' || *p == '\r') p++;
    if (*p == '[') {
        rm_json *j = rm_json_parse(p);
        if (j && j->type == RMJ_ARR) {
            g->cols = (Col *)calloc((size_t)(j->n ? j->n : 1), sizeof(Col));
            for (i = 0; i < j->n && g->cols; i++) {
                const rm_json *o = &j->kids[i];
                Col *c = &g->cols[i];
                if (o->type == RMJ_STR) { c->text = rm_strdup(o->str); c->name = rm_strdup(o->str); c->items = rm_strdup(""); }
                else {
                    c->text = rm_strdup(rm_json_text(o, "Text", rm_json_text(o, "HeaderText", "")));
                    c->name = rm_strdup(rm_json_text(o, "Name", c->text));
                    c->type = ctype_of(rm_json_text(o, "Type", rm_json_text(o, "Kind", "Text")));
                    c->width = (int)rm_json_num(o, "Width", 0);
                    c->frozen = rm_json_bool(o, "Frozen", 0);
                    c->readonly = rm_json_bool(o, "ReadOnly", 0);
                    {
                        const rm_json *it = rm_json_get(o, "Items");
                        if (it && it->type == RMJ_ARR) {
                            rm_list l = {0, 0, 0};
                            int k;
                            for (k = 0; k < it->n; k++) rm_list_add(&l, it->kids[k].type == RMJ_STR ? it->kids[k].str : rm_json_text(&it->kids[k], "Text", ""), -1);
                            c->items = rm_strdup(rm_list_join(&l, ';'));
                            rm_list_free(&l);
                        } else c->items = rm_strdup(rm_json_text(o, "Items", ""));
                    }
                }
                g->ncols++;
            }
        }
        rm_json_free(j);
    } else if (*p) {
        rm_list l = {0, 0, 0};
        rm_list_parse(&l, p, ';');
        g->cols = (Col *)calloc((size_t)(l.n ? l.n : 1), sizeof(Col));
        for (i = 0; i < l.n && g->cols; i++) {
            rm_list parts = {0, 0, 0};
            Col *c = &g->cols[i];
            rm_list_parse(&parts, l.v[i], ':');
            c->text = rm_strdup(rm_list_get(&parts, 0));
            c->name = rm_strdup(c->text);
            c->type = ctype_of(rm_list_get(&parts, 1));
            c->width = rm_int(rm_list_get(&parts, 2));
            c->items = rm_strdup("");
            rm_list_free(&parts);
            g->ncols++;
        }
        rm_list_free(&l);
    }
    g->filters = (char **)calloc((size_t)(g->ncols + 1), sizeof(char *));
    for (i = 0; i < g->ncols && g->filters; i++) g->filters[i] = rm_strdup("");
}

static void row_free(RmGrid *g, Row *r) {
    int i;
    (void)g;
    if (!r->cells) return;
    for (i = 0; r->cells[i]; i++) free(r->cells[i]);
    free(r->cells);
    r->cells = NULL;
}

static int row_ncells(Row *r) {
    int n = 0;
    while (r->cells && r->cells[n]) n++;
    return n;
}

static const char *cell(RmGrid *g, int row, int col) {
    Row *r;
    if (row < 0 || row >= g->nrows || col < 0) return "";
    r = &g->rows[row];
    return col < row_ncells(r) ? r->cells[col] : "";
}

static void set_cell(RmGrid *g, int row, int col, const char *v) {
    Row *r;
    int n, i;
    if (row < 0 || row >= g->nrows || col < 0) return;
    r = &g->rows[row];
    n = row_ncells(r);
    if (col >= n) {
        char **c = (char **)realloc(r->cells, sizeof(char *) * (col + 2));
        if (!c) return;
        r->cells = c;
        for (i = n; i <= col; i++) c[i] = rm_strdup("");
        c[col + 1] = NULL;
    }
    rm_setstr(&r->cells[col], v);
}

static int add_row_list(RmGrid *g, rm_list *cells, int at) {
    Row nr;
    int i;
    if (g->nrows >= g->cap) {
        int cap = g->cap ? g->cap * 2 : 32;
        Row *rs = (Row *)realloc(g->rows, sizeof(Row) * cap);
        if (!rs) return -1;
        g->rows = rs;
        g->cap = cap;
    }
    nr.sel = 0;
    nr.cells = (char **)calloc((size_t)(cells->n + 1), sizeof(char *));
    if (!nr.cells) return -1;
    for (i = 0; i < cells->n; i++) nr.cells[i] = rm_strdup(cells->v[i]);
    if (at < 0 || at > g->nrows) at = g->nrows;
    memmove(g->rows + at + 1, g->rows + at, sizeof(Row) * (g->nrows - at));
    g->rows[at] = nr;
    g->nrows++;
    return at;
}

static void rows_clear(RmGrid *g) {
    int i;
    for (i = 0; i < g->nrows; i++) row_free(g, &g->rows[i]);
    g->nrows = 0;
    free(g->closed);
    g->closed = NULL;
}

static void rows_parse(RmGrid *g, const char *v) {
    const char *p = v ? v : "";
    rows_clear(g);
    while (*p == ' ' || *p == '\n' || *p == '\r') p++;
    if (*p == '[') {
        rm_json *j = rm_json_parse(p);
        int i, k;
        if (j && j->type == RMJ_ARR)
            for (i = 0; i < j->n; i++) {
                rm_list cells = {0, 0, 0};
                const rm_json *r = &j->kids[i];
                if (r->type == RMJ_ARR) {
                    for (k = 0; k < r->n; k++) {
                        const rm_json *c = &r->kids[k];
                        rm_list_add(&cells, c->type == RMJ_STR ? c->str : c->type == RMJ_NUM ? rad_str(c->num) :
                                    c->type == RMJ_BOOL ? rm_tf(c->num != 0) : "", -1);
                    }
                } else if (r->type == RMJ_OBJ) {    /* {"col name": value} */
                    for (k = 0; k < g->ncols; k++) rm_list_add(&cells, rm_json_text(r, g->cols[k].name, rm_json_text(r, g->cols[k].text, "")), -1);
                }
                add_row_list(g, &cells, -1);
                rm_list_free(&cells);
            }
        rm_json_free(j);
        return;
    }
    if (*p) {
        rm_list rows = {0, 0, 0};
        int i;
        rm_list_parse(&rows, p, ';');
        for (i = 0; i < rows.n; i++) {
            rm_list cells = {0, 0, 0};
            rm_list_parse(&cells, rows.v[i], '|');
            add_row_list(g, &cells, -1);
            rm_list_free(&cells);
        }
        rm_list_free(&rows);
    }
}

static const char *rows_text(RmGrid *g) {
    rm_sb b = {0, 0, 0};
    int i, k;
    rm_sb_add(&b, "");
    for (i = 0; i < g->nrows; i++) {
        if (i) rm_sb_addc(&b, ';');
        for (k = 0; k < row_ncells(&g->rows[i]); k++) {
            if (k) rm_sb_addc(&b, '|');
            rm_sb_add(&b, g->rows[i].cells[k]);
        }
    }
    return rm_sb_ring(&b);
}

/* ------------------------------------------------------------------ view (filter + sort + groups) */
static RmGrid *g_sort;
static int cmp_rows(const void *a, const void *b) {
    int ra = *(const int *)a, rb = *(const int *)b, c = 0, col;
    RmGrid *g = g_sort;
    for (col = g->group_col >= 0 ? -1 : 0; col < 1; col++) {
        int k = col < 0 ? g->group_col : g->sort_col;
        const char *x, *y;
        if (k < 0 || k >= g->ncols) continue;
        x = cell(g, ra, k);
        y = cell(g, rb, k);
        if (g->cols[k].type == CT_NUMBER || g->cols[k].type == CT_PROGRESS) {
            double dx = rad_num(x), dy = rad_num(y);
            c = dx < dy ? -1 : dx > dy ? 1 : 0;
        } else if (g->cols[k].type == CT_CHECK) {
            c = rm_bool(x) - rm_bool(y);
        } else {
            wchar_t *wx = rm_wide(x), *wy = rm_wide(y);
            c = CompareStringW(LOCALE_USER_DEFAULT, NORM_IGNORECASE | SORT_DIGITSASNUMBERS, wx ? wx : L"", -1, wy ? wy : L"", -1) - 2;
            free(wx);
            free(wy);
        }
        if (col >= 0 && g->sort_desc) c = -c;
        if (c) return c;
    }
    return ra - rb;
}

static int matches(RmGrid *g, int row) {
    int k;
    if (!g->filters) return 1;
    for (k = 0; k < g->ncols; k++) {
        const char *f = g->filters[k];
        if (f && *f) {
            wchar_t *wc = rm_wide(cell(g, row, k)), *wf = rm_wide(f);
            int ok = wc && wf && FindNLSString(LOCALE_USER_DEFAULT, FIND_FROMSTART | NORM_IGNORECASE, wf, -1, wc, -1, NULL) >= 0;
            free(wc);
            free(wf);
            if (!ok) return 0;
        }
    }
    return 1;
}

static void view_build(RmGrid *g) {
    int *order = (int *)malloc(sizeof(int) * (g->nrows + 1)), n = 0, i;
    free(g->view);
    g->view = (ViewRow *)malloc(sizeof(ViewRow) * (2 * g->nrows + 1));
    g->nview = 0;
    if (!order || !g->view) { free(order); return; }
    for (i = 0; i < g->nrows; i++)
        if (matches(g, i)) order[n++] = i;
    if ((g->sort_col >= 0 && g->sort_col < g->ncols) || (g->group_col >= 0 && g->group_col < g->ncols)) {
        g_sort = g;
        qsort(order, (size_t)n, sizeof(int), cmp_rows);
    }
    if (!g->closed) g->closed = (unsigned char *)calloc((size_t)(g->nrows + 1), 1);
    for (i = 0; i < n; i++) {
        int r = order[i];
        if (g->group_col >= 0 && g->group_col < g->ncols && !g->lv &&
            (i == 0 || !rm_ieq(cell(g, order[i - 1], g->group_col), cell(g, r, g->group_col)))) {
            g->view[g->nview].group = 1;
            g->view[g->nview].row = r;
            g->nview++;
        }
        if (g->group_col >= 0 && g->group_col < g->ncols && !g->lv) {   /* collapsed group: rows hidden */
            int j = g->nview - 1;
            while (j >= 0 && !g->view[j].group) j--;
            if (j >= 0 && g->closed && rm_bool(g->closed[g->view[j].row] ? "1" : "0")) continue;
        }
        g->view[g->nview].group = 0;
        g->view[g->nview].row = r;
        g->nview++;
    }
    free(order);
}

/* ------------------------------------------------------------------ geometry */
static int row_h(RmGrid *g) { return rm_px(g->h, g->row_h96 > 0 ? g->row_h96 : (g->lv && g->lv_view == 2 ? 120 : g->lv && g->lv_view == 1 ? 64 : 28)); }
static int head_h(RmGrid *g) { return g->lv && g->lv_view ? 0 : rm_px(g->h, 30); }
static int filt_h(RmGrid *g) { return g->allow_filter && !g->lv ? rm_px(g->h, 26) : 0; }
static int col_w(RmGrid *g, int k) { return rm_px(g->h, g->cols[k].width > 0 ? g->cols[k].width : 110); }

static int frozen_w(RmGrid *g) {
    int k, w = 0;
    for (k = 0; k < g->ncols && g->cols[k].frozen; k++) w += col_w(g, k);
    return w;
}

static int total_w(RmGrid *g) {
    int k, w = 0;
    for (k = 0; k < g->ncols; k++) w += col_w(g, k);
    return w;
}

/* x of column k on screen (device px), honouring frozen columns and horizontal scroll */
static int col_x(RmGrid *g, int k) {
    int i, x = 0;
    for (i = 0; i < k; i++) x += col_w(g, i);
    return g->cols[k].frozen ? x : x - g->hscroll;
}

static void client(RmGrid *g, RECT *r) { GetClientRect((HWND)rf_hwnd(g->h), r); }

static int lv_per_row(RmGrid *g) {
    RECT r;
    int cw = rm_px(g->h, g->lv_view == 2 ? 236 : 220);
    client(g, &r);
    return r.right / cw > 0 ? r.right / cw : 1;
}

static int visible_rows(RmGrid *g) {
    RECT r;
    client(g, &r);
    if (g->lv && g->lv_view) return ((r.bottom) / (row_h(g) + rm_px(g->h, 8)) + 1) * lv_per_row(g);
    return (r.bottom - head_h(g) - filt_h(g)) / row_h(g);
}

static void scroll_update(RmGrid *g) {
    SCROLLINFO si;
    HWND hw = (HWND)rf_hwnd(g->h);
    RECT r;
    int lines = g->nview;
    if (!hw) return;
    client(g, &r);
    if (g->lv && g->lv_view) lines = (g->nview + lv_per_row(g) - 1) / lv_per_row(g);
    if (g->top > lines - 1) g->top = lines - 1;
    if (g->top < 0) g->top = 0;
    memset(&si, 0, sizeof si);
    si.cbSize = sizeof si;
    si.fMask = SIF_RANGE | SIF_PAGE | SIF_POS | SIF_DISABLENOSCROLL;
    si.nMin = 0;
    si.nMax = lines > 0 ? lines - 1 : 0;
    si.nPage = (UINT)(g->lv && g->lv_view ? r.bottom / (row_h(g) + rm_px(g->h, 8)) : visible_rows(g));
    si.nPos = g->top;
    SetScrollInfo(hw, SB_VERT, &si, TRUE);
    if (!g->lv) {
        int tw = total_w(g);
        si.nMax = tw > 0 ? tw - 1 : 0;
        si.nPage = (UINT)(r.right - frozen_w(g) > 0 ? r.right : 1);
        if (g->hscroll > tw - (int)si.nPage) g->hscroll = tw - (int)si.nPage;
        if (g->hscroll < 0) g->hscroll = 0;
        si.nPos = g->hscroll;
        SetScrollInfo(hw, SB_HORZ, &si, TRUE);
    }
}

static int view_of_row(RmGrid *g, int row) {
    int i;
    for (i = 0; i < g->nview; i++)
        if (!g->view[i].group && g->view[i].row == row) return i;
    return -1;
}

static void ensure_visible(RmGrid *g, int vi) {
    int vis = visible_rows(g);
    if (g->lv && g->lv_view) {
        int line = vi / lv_per_row(g), lines = vis / lv_per_row(g);
        if (line < g->top) g->top = line;
        if (lines > 1 && line >= g->top + lines - 1) g->top = line - lines + 2;
    } else {
        if (vi < g->top) g->top = vi;
        if (vis > 0 && vi >= g->top + vis) g->top = vi - vis + 1;
    }
    scroll_update(g);
}

/* hit test: returns view index (-1 none); *col = column; *area = 0 cells 1 header 2 filter 3 group */
static int hit(RmGrid *g, int x, int y, int *col, int *area) {
    int hh = head_h(g), fh = filt_h(g), k;
    *col = -1;
    *area = 0;
    if (g->lv && g->lv_view) {
        int per = lv_per_row(g), cw = rm_px(g->h, g->lv_view == 2 ? 236 : 220), ch = row_h(g) + rm_px(g->h, 8);
        int c = x / cw, r = y / ch + g->top, vi = r * per + c;
        if (c >= per || vi < 0 || vi >= g->nview) return -1;
        return vi;
    }
    for (k = 0; k < g->ncols; k++) {
        int cx = col_x(g, k);
        if (!g->cols[k].frozen && cx < frozen_w(g)) continue;
        if (x >= cx && x < cx + col_w(g, k)) { *col = k; break; }
    }
    if (y < hh) { *area = 1; return -1; }
    if (y < hh + fh) { *area = 2; return -1; }
    {
        int vi = g->top + (y - hh - fh) / row_h(g);
        if (vi < 0 || vi >= g->nview) return -1;
        if (g->view[vi].group) *area = 3;
        return vi;
    }
}

/* ------------------------------------------------------------------ selection / editing */
static void select_row(RmGrid *g, int row, int col, int add, int range) {
    int i, changed = 0;
    if (!g->multi || (!add && !range)) {
        for (i = 0; i < g->nrows; i++)
            if (g->rows[i].sel && i != row) { g->rows[i].sel = 0; changed = 1; }
    }
    if (range && g->multi && g->cur_row >= 0) {
        int a = view_of_row(g, g->cur_row), b = view_of_row(g, row), lo = a < b ? a : b, hi = a < b ? b : a;
        for (i = lo; i <= hi && i >= 0; i++)
            if (!g->view[i].group && !g->rows[g->view[i].row].sel) { g->rows[g->view[i].row].sel = 1; changed = 1; }
    } else if (row >= 0 && row < g->nrows) {
        int ns = add ? !g->rows[row].sel : 1;
        if (g->rows[row].sel != ns) { g->rows[row].sel = ns; changed = 1; }
    }
    if (row != g->cur_row || col != g->cur_col) changed = 1;
    if (!range) g->cur_row = row;
    else if (!g->multi) g->cur_row = row;
    if (col >= 0) g->cur_col = col;
    if (range && g->multi) g->cur_row = row;
    rf_invalidate(g->h);
    if (changed) rf_raise(g->h, "SelectionChanged", "");
    if (changed && g->lv) rf_raise(g->h, "SelectedIndexChanged", "");
}

static void edit_end(RmGrid *g, int commit) {
    HWND e = g->edit;
    if (!e) return;
    g->edit = NULL;
    if (commit) {
        int n = GetWindowTextLengthW(e);
        wchar_t *w = (wchar_t *)malloc(sizeof(wchar_t) * (n + 1));
        char *u;
        if (w) {
            GetWindowTextW(e, w, n + 1);
            u = rm_utf8(w);
            if (u) {
                if (g->editing_filter) {
                    rm_setstr(&g->filters[g->edit_col], u);
                    view_build(g);
                    scroll_update(g);
                } else if (strcmp(cell(g, g->edit_row, g->edit_col), u) != 0) {
                    set_cell(g, g->edit_row, g->edit_col, u);
                    rm_raise_cell(g->h, "CellValueChanged", g->edit_row, g->edit_col);
                }
                free(u);
            }
            free(w);
        }
    }
    DestroyWindow(e);
    SetFocus((HWND)rf_hwnd(g->h));
    rf_invalidate(g->h);
}

static LRESULT CALLBACK grid_edit_sub(HWND e, UINT m, WPARAM w, LPARAM l, UINT_PTR id, DWORD_PTR ref) {
    RmGrid *g = (RmGrid *)ref;
    (void)id;
    switch (m) {
    case WM_KEYDOWN:
        if (w == VK_RETURN) { edit_end(g, 1); return 0; }
        if (w == VK_ESCAPE) { edit_end(g, 0); return 0; }
        if (w == VK_TAB) { edit_end(g, 1); return 0; }
        break;
    case WM_CHAR:
        if (w == '\r' || w == 27 || w == '\t') return 0;
        if (g->editing_filter) {    /* filter as you type */
            LRESULT r = DefSubclassProc(e, m, w, l);
            int n = GetWindowTextLengthW(e);
            wchar_t *wt = (wchar_t *)malloc(sizeof(wchar_t) * (n + 1));
            if (wt) {
                char *u;
                GetWindowTextW(e, wt, n + 1);
                u = rm_utf8(wt);
                if (u) { rm_setstr(&g->filters[g->edit_col], u); free(u); }
                free(wt);
                view_build(g);
                scroll_update(g);
                rf_invalidate(g->h);
            }
            return r;
        }
        break;
    case WM_GETDLGCODE:
        return DLGC_WANTALLKEYS;
    case WM_KILLFOCUS:
        if (g->edit == e) PostMessageW(GetParent(e), WM_APP + 0x5247, 0, 0);
        break;
    case WM_NCDESTROY:
        RemoveWindowSubclass(e, grid_edit_sub, 1);
        break;
    default: break;
    }
    return DefSubclassProc(e, m, w, l);
}

static void edit_begin(RmGrid *g, int row, int col, int filter, wchar_t first) {
    HWND hw = (HWND)rf_hwnd(g->h);
    int x, y, w, h, vi;
    wchar_t *txt;
    if (col < 0 || col >= g->ncols) return;
    if (!filter && (g->readonly || g->cols[col].readonly)) return;
    edit_end(g, 1);
    x = col_x(g, col);
    w = col_w(g, col);
    if (filter) { y = head_h(g); h = filt_h(g); }
    else {
        vi = view_of_row(g, row);
        if (vi < 0) return;
        ensure_visible(g, vi);
        y = head_h(g) + filt_h(g) + (vi - g->top) * row_h(g);
        h = row_h(g);
    }
    txt = first ? NULL : rm_wide(filter ? g->filters[col] : cell(g, row, col));
    g->edit = CreateWindowExW(0, L"EDIT", txt ? txt : L"", WS_CHILD | WS_VISIBLE | ES_AUTOHSCROLL | WS_BORDER, x, y, w, h, hw,
                              (HMENU)(INT_PTR)7, GetModuleHandleW(NULL), NULL);
    free(txt);
    if (!g->edit) return;
    g->edit_row = row;
    g->edit_col = col;
    g->editing_filter = filter;
    SendMessageW(g->edit, WM_SETFONT, SendMessageW(hw, WM_GETFONT, 0, 0), 0);
    SetWindowSubclass(g->edit, grid_edit_sub, 1, (DWORD_PTR)g);
    SetFocus(g->edit);
    if (first) {
        wchar_t s[2];
        s[0] = first;
        s[1] = 0;
        SetWindowTextW(g->edit, s);
        SendMessageW(g->edit, EM_SETSEL, 1, 1);
    } else {
        SendMessageW(g->edit, EM_SETSEL, 0, -1);
    }
}

static void cell_activate(RmGrid *g, int row, int col, int by_mouse) {
    Col *c;
    if (row < 0 || col < 0 || col >= g->ncols) return;
    c = &g->cols[col];
    if (c->type == CT_BUTTON) { rm_raise_cell(g->h, "ButtonCellClick", row, col); return; }
    if (c->type == CT_CHECK && !g->readonly && !c->readonly) {
        set_cell(g, row, col, rm_tf(!rm_bool(cell(g, row, col))));
        rf_invalidate(g->h);
        rm_raise_cell(g->h, "CellValueChanged", row, col);
        return;
    }
    if (c->type == CT_COMBO && !g->readonly && !c->readonly) {
        int n = 0;
        rm_item *items = rm_items_parse(c->items, &n), *pick;
        POINT pt;
        int vi = view_of_row(g, row);
        pt.x = col_x(g, col);
        pt.y = head_h(g) + filt_h(g) + (vi - g->top + 1) * row_h(g);
        ClientToScreen((HWND)rf_hwnd(g->h), &pt);
        pick = rm_popup_menu(g->h, items, n, pt.x, pt.y);
        if (pick && strcmp(pick->text, cell(g, row, col)) != 0) {
            set_cell(g, row, col, pick->text);
            rf_invalidate(g->h);
            rm_raise_cell(g->h, "CellValueChanged", row, col);
        }
        rm_items_free(items, n);
        return;
    }
    if (!by_mouse && c->type != CT_IMAGE && c->type != CT_PROGRESS) edit_begin(g, row, col, 0, 0);
}

/* ------------------------------------------------------------------ class plumbing */
static int RF_CALL grid_create_k(rf_handle h, void **state, int lv) {
    RmGrid *g = (RmGrid *)calloc(1, sizeof *g);
    if (!g) return 0;
    g->h = h;
    g->lv = lv;
    g->allow_sort = !lv;
    g->alternating = 1;
    g->sort_col = g->group_col = -1;
    g->cur_row = g->cur_col = -1;
    g->hot_view = g->hot_col = g->hot_head = -1;
    g->colsrc = rm_strdup("");
    g->group_name = rm_strdup("");
    *state = g;
    if (rf_hwnd(h) && rf_theme_current()->dark) {
        typedef HRESULT(WINAPI * swt_t)(HWND, LPCWSTR, LPCWSTR);
        HMODULE m = LoadLibraryW(L"uxtheme.dll");
        swt_t fn = m ? (swt_t)(void *)GetProcAddress(m, "SetWindowTheme") : NULL;
        if (fn) fn((HWND)rf_hwnd(h), L"DarkMode_Explorer", NULL);
    }
    scroll_update(g);
    return 1;
}
static int RF_CALL grid_create(rf_handle h, void **s) { return grid_create_k(h, s, 0); }
static int RF_CALL lv_create(rf_handle h, void **s) { return grid_create_k(h, s, 1); }

static void RF_CALL grid_destroy(rf_handle h, void *state) {
    RmGrid *g = (RmGrid *)state;
    (void)h;
    if (!g) return;
    if (g->edit) DestroyWindow(g->edit);
    col_free(g);
    rows_clear(g);
    free(g->rows);
    free(g->view);
    free(g->colsrc);
    free(g->group_name);
    free(g);
}

static int col_index(RmGrid *g, const char *s) {
    int k;
    for (k = 0; k < g->ncols; k++)
        if (rm_ieq(g->cols[k].name, s) || rm_ieq(g->cols[k].text, s)) return k;
    if (*s && (*s == '-' || (*s >= '0' && *s <= '9'))) return rm_int(s);
    return -1;
}

static void refresh(RmGrid *g) {
    view_build(g);
    scroll_update(g);
    rf_invalidate(g->h);
}

static void lv_items(RmGrid *g, const char *v) {
    /* list view items: JSON [{"Text","Image","SubItems":[...] or "a;b"}] or rows "a|b;c|d"; column 0 = text,
     * the image is kept in a hidden last cell named "\x01image" */
    const char *p = v ? v : "";
    while (*p == ' ' || *p == '\n' || *p == '\r') p++;
    if (*p == '[' ) {
        rm_json *j = rm_json_parse(p);
        int i, k;
        rows_clear(g);
        if (j && j->type == RMJ_ARR)
            for (i = 0; i < j->n; i++) {
                const rm_json *o = &j->kids[i];
                rm_list cells = {0, 0, 0};
                if (o->type == RMJ_OBJ) {
                    const rm_json *sub = rm_json_get(o, "SubItems");
                    rm_list_add(&cells, rm_json_text(o, "Text", ""), -1);
                    if (sub && sub->type == RMJ_ARR)
                        for (k = 0; k < sub->n; k++) rm_list_add(&cells, sub->kids[k].type == RMJ_STR ? sub->kids[k].str : rad_str(sub->kids[k].num), -1);
                    else if (sub && sub->type == RMJ_STR) {
                        rm_list s2 = {0, 0, 0};
                        rm_list_parse(&s2, sub->str, ';');
                        for (k = 0; k < s2.n; k++) rm_list_add(&cells, s2.v[k], -1);
                        rm_list_free(&s2);
                    }
                    while (cells.n < (g->ncols > 1 ? g->ncols : 1)) rm_list_add(&cells, "", -1);
                    rm_list_add(&cells, rm_json_text(o, "Image", ""), -1);
                } else if (o->type == RMJ_STR) {
                    rm_list_add(&cells, o->str, -1);
                    while (cells.n < (g->ncols > 1 ? g->ncols : 1)) rm_list_add(&cells, "", -1);
                    rm_list_add(&cells, "", -1);
                } else if (o->type == RMJ_ARR) {
                    for (k = 0; k < o->n; k++) rm_list_add(&cells, o->kids[k].type == RMJ_STR ? o->kids[k].str : "", -1);
                    while (cells.n < (g->ncols > 1 ? g->ncols : 1)) rm_list_add(&cells, "", -1);
                    rm_list_add(&cells, "", -1);
                }
                add_row_list(g, &cells, -1);
                rm_list_free(&cells);
            }
        rm_json_free(j);
    } else {
        int i;
        rows_parse(g, p);
        for (i = 0; i < g->nrows; i++) {
            int n = row_ncells(&g->rows[i]);
            while (n < (g->ncols > 1 ? g->ncols : 1)) set_cell(g, i, n++, "");
            set_cell(g, i, n, "");
        }
    }
}

static int img_col(RmGrid *g) { return g->ncols > 1 ? g->ncols : 1; }

static int RF_CALL grid_set(rf_handle h, void *state, const char *prop, const char *v) {
    RmGrid *g = (RmGrid *)state;
    (void)h;
    if (rm_look_set(&g->look, prop, v)) return 1;
    if (rm_ieq(prop, "Columns")) { rm_setstr(&g->colsrc, v); cols_parse(g, v); if (g->group_name[0]) g->group_col = col_index(g, g->group_name); refresh(g); return 1; }
    if (rm_ieq(prop, "Rows") && !g->lv) { rows_parse(g, v); refresh(g); return 1; }
    if (rm_ieq(prop, "Items") && g->lv) { lv_items(g, v); refresh(g); return 1; }
    if (rm_ieq(prop, "ReadOnly")) { g->readonly = rm_bool(v); return 1; }
    if (rm_ieq(prop, "AllowSort")) { g->allow_sort = rm_bool(v); return 1; }
    if (rm_ieq(prop, "AllowFilter")) { g->allow_filter = rm_bool(v); refresh(g); return 1; }
    if (rm_ieq(prop, "AlternatingRows")) { g->alternating = rm_bool(v); return 1; }
    if (rm_ieq(prop, "RowHeight")) { g->row_h96 = rm_int(v); refresh(g); return 1; }
    if (rm_ieq(prop, "GroupBy")) { rm_setstr(&g->group_name, v); g->group_col = *v ? col_index(g, v) : -1; refresh(g); return 1; }
    if (rm_ieq(prop, "SelectionMode")) {
        g->multi = rm_ieq(v, "MultiRow") || rm_ieq(v, "MultiExtended") || rm_ieq(v, "MultiSimple");
        g->cellsel = rm_ieq(v, "CellSelect");
        return 1;
    }
    if (rm_ieq(prop, "View") && g->lv) {
        g->lv_view = rm_ieq(v, "Tiles") || rm_ieq(v, "Tile") || rm_ieq(v, "LargeIcon") ? 1 : rm_ieq(v, "Cards") || rm_ieq(v, "Card") ? 2 : 0;
        g->top = 0;
        refresh(g);
        return 1;
    }
    if (rm_ieq(prop, "SelectedRow") || rm_ieq(prop, "SelectedIndex")) {
        int r = rm_int(v);
        if (r >= -1 && r < g->nrows) { select_row(g, r, g->cur_col, 0, 0); if (r >= 0 && view_of_row(g, r) >= 0) ensure_visible(g, view_of_row(g, r)); }
        return 1;
    }
    return 0;
}

static const char *RF_CALL grid_get(rf_handle h, void *state, const char *prop) {
    { const char *ev_ = rm_event_get(h, prop); if (ev_) return ev_; }
    RmGrid *g = (RmGrid *)state;
    const char *r = rm_look_get(&g->look, prop);
    (void)h;
    if (r) return r;
    if (rm_ieq(prop, "Columns")) return g->colsrc;
    if (rm_ieq(prop, "Rows") || rm_ieq(prop, "Items")) return rows_text(g);
    if (rm_ieq(prop, "RowCount") || rm_ieq(prop, "ListCount") || rm_ieq(prop, "Count")) return rad_str(g->nrows);
    if (rm_ieq(prop, "ColumnCount")) return rad_str(g->ncols);
    if (rm_ieq(prop, "SelectedRow") || rm_ieq(prop, "SelectedIndex")) return rad_str(g->cur_row);
    if (rm_ieq(prop, "SelectedItem") || rm_ieq(prop, "Text")) return cell(g, g->cur_row, 0);
    if (rm_ieq(prop, "CurrentColumn")) return rad_str(g->cur_col);
    if (rm_ieq(prop, "ReadOnly")) return rm_tf(g->readonly);
    if (rm_ieq(prop, "AllowSort")) return rm_tf(g->allow_sort);
    if (rm_ieq(prop, "AllowFilter")) return rm_tf(g->allow_filter);
    if (rm_ieq(prop, "AlternatingRows")) return rm_tf(g->alternating);
    if (rm_ieq(prop, "GroupBy")) return g->group_name;
    if (rm_ieq(prop, "SelectionMode")) return g->multi ? "MultiRow" : g->cellsel ? "CellSelect" : "FullRowSelect";
    if (rm_ieq(prop, "View")) return g->lv_view == 1 ? "Tiles" : g->lv_view == 2 ? "Cards" : "Details";
    if (rm_ieq(prop, "SortColumn")) return rad_str(g->sort_col);
    if (rm_ieq(prop, "VisibleRowCount")) {
        int i, n = 0;
        for (i = 0; i < g->nview; i++) n += !g->view[i].group;
        return rad_str(n);
    }
    if (rm_ieq(prop, "SelectedRows")) {
        rm_list l = {0, 0, 0};
        int i;
        const char *s;
        for (i = 0; i < g->nrows; i++) if (g->rows[i].sel) rm_list_add(&l, rad_str(i), -1);
        s = rm_list_join(&l, ';');
        rm_list_free(&l);
        return s;
    }
    return NULL;
}

static void split_cells(const char *args, rm_list *out) {
    const char *a0 = rm_arg(args, 0);
    if (strchr(args, '\t')) {          /* several arguments: one per cell */
        int i;
        for (i = 0;; i++) {
            const char *p = args;
            int k;
            for (k = 0; k < i && p; k++) { p = strchr(p, '\t'); if (p) p++; }
            if (!p) break;
            rm_list_add(out, rm_arg(args, i), -1);
        }
    } else if (strchr(a0, '|')) rm_list_parse(out, a0, '|');
    else rm_list_parse(out, a0, ';');
}

static const char *RF_CALL grid_invoke(rf_handle h, void *state, const char *m, const char *args) {
    RmGrid *g = (RmGrid *)state;
    (void)h;
    if (rm_ieq(m, "AddRow") || rm_ieq(m, "AddItem") || rm_ieq(m, "Add")) {
        rm_list cells = {0, 0, 0};
        int r;
        split_cells(args, &cells);
        if (g->lv) {
            while (cells.n < img_col(g)) rm_list_add(&cells, "", -1);
            if (cells.n == img_col(g)) rm_list_add(&cells, "", -1);
        }
        r = add_row_list(g, &cells, -1);
        rm_list_free(&cells);
        free(g->closed);
        g->closed = NULL;
        refresh(g);
        return rad_str(r);
    }
    if (rm_ieq(m, "InsertRow")) {
        rm_list cells = {0, 0, 0};
        int at = rm_int(rm_arg(args, 0)), r;
        rm_list_parse(&cells, strchr(rm_arg(args, 1), '|') ? rm_arg(args, 1) : rm_arg(args, 1), strchr(rm_arg(args, 1), '|') ? '|' : ';');
        r = add_row_list(g, &cells, at);
        rm_list_free(&cells);
        free(g->closed);
        g->closed = NULL;
        refresh(g);
        return rad_str(r);
    }
    if (rm_ieq(m, "RemoveRow") || rm_ieq(m, "RemoveItem") || rm_ieq(m, "RemoveAt")) {
        int r = rm_int(rm_arg(args, 0));
        if (r >= 0 && r < g->nrows) {
            edit_end(g, 0);
            row_free(g, &g->rows[r]);
            memmove(g->rows + r, g->rows + r + 1, sizeof(Row) * (g->nrows - r - 1));
            g->nrows--;
            if (g->cur_row >= g->nrows) g->cur_row = g->nrows - 1;
            free(g->closed);
            g->closed = NULL;
            refresh(g);
        }
        return "";
    }
    if (rm_ieq(m, "Clear")) { edit_end(g, 0); rows_clear(g); g->cur_row = -1; refresh(g); return ""; }
    if (rm_ieq(m, "GetCell")) return cell(g, rm_int(rm_arg(args, 0)), col_index(g, rm_arg(args, 1)));
    if (rm_ieq(m, "SetCell")) {
        set_cell(g, rm_int(rm_arg(args, 0)), col_index(g, rm_arg(args, 1)), rm_arg(args, 2));
        refresh(g);
        return "";
    }
    if (rm_ieq(m, "GetRow")) {
        rm_list l = {0, 0, 0};
        int r = rm_int(rm_arg(args, 0)), k;
        const char *s;
        for (k = 0; k < g->ncols; k++) rm_list_add(&l, cell(g, r, k), -1);
        s = rm_list_join(&l, '|');
        rm_list_free(&l);
        return s;
    }
    if (rm_ieq(m, "SortBy")) {
        g->sort_col = col_index(g, rm_arg(args, 0));
        g->sort_desc = rm_bool(rm_arg(args, 1)) || rm_ieq(rm_arg(args, 1), "Descending");
        refresh(g);
        return "";
    }
    if (rm_ieq(m, "SetFilter")) {
        int k = col_index(g, rm_arg(args, 0));
        if (k >= 0 && k < g->ncols) { rm_setstr(&g->filters[k], rm_arg(args, 1)); refresh(g); }
        return "";
    }
    if (rm_ieq(m, "ClearFilter")) {
        int k;
        for (k = 0; k < g->ncols; k++) rm_setstr(&g->filters[k], "");
        refresh(g);
        return "";
    }
    if (rm_ieq(m, "SetColumnWidth")) {
        int k = col_index(g, rm_arg(args, 0));
        if (k >= 0 && k < g->ncols) { g->cols[k].width = rm_int(rm_arg(args, 1)); refresh(g); }
        return "";
    }
    if (rm_ieq(m, "BeginEdit")) { edit_begin(g, rm_int(rm_arg(args, 0)), col_index(g, rm_arg(args, 1)), 0, 0); return ""; }
    if (rm_ieq(m, "EnsureVisible")) { int vi = view_of_row(g, rm_int(rm_arg(args, 0))); if (vi >= 0) ensure_visible(g, vi); rf_invalidate(g->h); return ""; }
    if (rm_ieq(m, "List") || rm_ieq(m, "Item")) return cell(g, rm_int(rm_arg(args, 0)), 0);
    if (rm_ieq(m, "SetItemImage") && g->lv) { set_cell(g, rm_int(rm_arg(args, 0)), img_col(g), rm_arg(args, 1)); rf_invalidate(g->h); return ""; }
    return NULL;
}

static int RF_CALL grid_message(rf_handle h, void *state, unsigned msg, uintptr_t w, intptr_t l, intptr_t *res) {
    RmGrid *g = (RmGrid *)state;
    int x = GET_X_LPARAM(l), y = GET_Y_LPARAM(l), col, area, vi;
    if (!g) return 0;
    switch (msg) {
    case WM_SIZE: scroll_update(g); break;
    case WM_APP + 0x5247: if (g->edit && GetFocus() != g->edit) edit_end(g, 1); *res = 0; return 1;
    case WM_VSCROLL: case WM_HSCROLL: {
        SCROLLINFO si;
        int bar = msg == WM_VSCROLL ? SB_VERT : SB_HORZ, *pos = msg == WM_VSCROLL ? &g->top : &g->hscroll, step = msg == WM_VSCROLL ? 1 : rm_px(h, 40);
        memset(&si, 0, sizeof si);
        si.cbSize = sizeof si;
        si.fMask = SIF_ALL;
        GetScrollInfo((HWND)rf_hwnd(h), bar, &si);
        switch (LOWORD(w)) {
        case SB_LINEUP: *pos -= step; break;
        case SB_LINEDOWN: *pos += step; break;
        case SB_PAGEUP: *pos -= (int)si.nPage; break;
        case SB_PAGEDOWN: *pos += (int)si.nPage; break;
        case SB_THUMBTRACK: case SB_THUMBPOSITION: *pos = si.nTrackPos; break;
        case SB_TOP: *pos = 0; break;
        case SB_BOTTOM: *pos = si.nMax; break;
        default: break;
        }
        edit_end(g, 1);
        scroll_update(g);
        rf_invalidate(h);
        *res = 0;
        return 1;
    }
    case WM_MOUSEWHEEL:
        g->top -= GET_WHEEL_DELTA_WPARAM(w) / 40 > 0 ? 3 : GET_WHEEL_DELTA_WPARAM(w) / 40 < 0 ? -3 : 0;
        if (g->lv && g->lv_view) g->top += (GET_WHEEL_DELTA_WPARAM(w) > 0 ? 2 : -2);
        edit_end(g, 1);
        scroll_update(g);
        rf_invalidate(h);
        *res = 0;
        return 1;
    case WM_LBUTTONDOWN: case WM_LBUTTONDBLCLK:
        SetFocus((HWND)rf_hwnd(h));
        vi = hit(g, x, y, &col, &area);
        if (area == 1 && col >= 0 && g->allow_sort && msg == WM_LBUTTONDOWN) {
            if (g->sort_col == col) g->sort_desc = !g->sort_desc;
            else { g->sort_col = col; g->sort_desc = 0; }
            refresh(g);
            rm_raise_item(h, "ColumnHeaderClick", g->cols[col].name, col);
        } else if (area == 2 && col >= 0) {
            edit_begin(g, -1, col, 1, 0);
        } else if (area == 3 && vi >= 0) {
            int r = g->view[vi].row;
            if (g->closed) g->closed[r] = !g->closed[r];
            refresh(g);
        } else if (vi >= 0) {
            int r = g->view[vi].row;
            int ctrl = (GetKeyState(VK_CONTROL) & 0x8000) != 0, shift = (GetKeyState(VK_SHIFT) & 0x8000) != 0;
            select_row(g, r, col, ctrl, shift);
            if (msg == WM_LBUTTONDOWN) {
                if (g->lv) rm_raise_item(h, "ItemClick", cell(g, r, 0), r);
                else rm_raise_cell(h, "CellClick", r, col);
                if (!g->lv && col >= 0 && (g->cols[col].type == CT_CHECK || g->cols[col].type == CT_BUTTON || g->cols[col].type == CT_COMBO))
                    cell_activate(g, r, col, 1);
            } else {
                if (g->lv) rm_raise_item(h, "ItemActivate", cell(g, r, 0), r);
                else if (col >= 0) { rm_raise_cell(h, "CellDoubleClick", r, col); cell_activate(g, r, col, 0); }
            }
        }
        *res = 0;
        return 1;
    case WM_MOUSEMOVE:
        vi = hit(g, x, y, &col, &area);
        if (vi != g->hot_view || (area == 1 ? col : -1) != g->hot_head || col != g->hot_col) {
            g->hot_view = vi;
            g->hot_head = area == 1 ? col : -1;
            g->hot_col = col;
            rf_invalidate(h);
        }
        break;
    case WM_MOUSELEAVE:
        g->hot_view = g->hot_head = g->hot_col = -1;
        rf_invalidate(h);
        break;
    case WM_KEYDOWN: {
        int cv = view_of_row(g, g->cur_row), nv = cv, vis = visible_rows(g), per = g->lv && g->lv_view ? lv_per_row(g) : 1;
        int shift = (GetKeyState(VK_SHIFT) & 0x8000) != 0;
        switch (w) {
        case VK_DOWN: nv = cv + per; break;
        case VK_UP: nv = cv - per; break;
        case VK_NEXT: nv = cv + (vis > 1 ? vis - 1 : 1); break;
        case VK_PRIOR: nv = cv - (vis > 1 ? vis - 1 : 1); break;
        case VK_HOME: nv = 0; break;
        case VK_END: nv = g->nview - 1; break;
        case VK_RIGHT:
            if (g->lv && g->lv_view) nv = cv + 1;
            else if (g->cur_col < g->ncols - 1) { g->cur_col++; rf_invalidate(h); }
            break;
        case VK_LEFT:
            if (g->lv && g->lv_view) nv = cv - 1;
            else if (g->cur_col > 0) { g->cur_col--; rf_invalidate(h); }
            break;
        case VK_F2: if (!g->lv) edit_begin(g, g->cur_row, g->cur_col < 0 ? 0 : g->cur_col, 0, 0); *res = 0; return 1;
        case VK_RETURN:
            if (g->lv && g->cur_row >= 0) rm_raise_item(h, "ItemActivate", cell(g, g->cur_row, 0), g->cur_row);
            else if (g->cur_row >= 0) cell_activate(g, g->cur_row, g->cur_col < 0 ? 0 : g->cur_col, 0);
            *res = 0;
            return 1;
        case VK_SPACE:
            if (!g->lv && g->cur_row >= 0 && g->cur_col >= 0 && g->cur_col < g->ncols &&
                (g->cols[g->cur_col].type == CT_CHECK || g->cols[g->cur_col].type == CT_BUTTON)) cell_activate(g, g->cur_row, g->cur_col, 1);
            *res = 0;
            return 1;
        case 'A':
            if (g->multi && (GetKeyState(VK_CONTROL) & 0x8000)) {
                int i;
                for (i = 0; i < g->nrows; i++) g->rows[i].sel = 1;
                rf_invalidate(h);
                rf_raise(h, "SelectionChanged", "");
                *res = 0;
                return 1;
            }
            break;
        default: break;
        }
        if (nv != cv) {
            if (nv >= g->nview) nv = g->nview - 1;
            if (nv < 0) nv = 0;
            while (nv < g->nview && nv >= 0 && g->view[nv].group) nv += nv > cv ? 1 : -1;
            if (nv >= 0 && nv < g->nview) {
                select_row(g, g->view[nv].row, g->cur_col, 0, shift);
                ensure_visible(g, nv);
            }
            *res = 0;
            return 1;
        }
        break;
    }
    case WM_CHAR:
        if (!g->lv && w >= 32 && g->cur_row >= 0 && g->cur_col >= 0 && g->cur_col < g->ncols &&
            (g->cols[g->cur_col].type == CT_TEXT || g->cols[g->cur_col].type == CT_NUMBER || g->cols[g->cur_col].type == CT_DATE) &&
            !g->readonly && !g->cols[g->cur_col].readonly && w != ' ') {
            edit_begin(g, g->cur_row, g->cur_col, 0, (wchar_t)w);
            *res = 0;
            return 1;
        }
        break;
    case WM_GETDLGCODE:
        *res = DLGC_WANTARROWS | DLGC_WANTCHARS;
        return 1;
    default: break;
    }
    return 0;
}

/* ------------------------------------------------------------------ painting */
static void paint_cell(const rf_paint *p, RmGrid *g, const rf_theme *t, int row, int k, int x, int y, int w, int h, unsigned fg,
                       unsigned back, unsigned accent, int hot) {
    const char *v = cell(g, row, k);
    Col *c = &g->cols[k];
    int pad = rf_px(p, 8);
    switch (c->type) {
    case CT_CHECK: {
        int s = rf_px(p, 16), bx = x + (w - s) / 2, by = y + (h - s) / 2, on = rm_bool(v);
        rf_draw_rect(p, bx, by, s, s, on ? accent : t->input, on ? RF_NONE : rf_blend(t->border, fg, 0.2), 1, rf_px(p, 3));
        if (on) rm_checkmark(p, bx, by, s, s, rm_on(accent), rf_px(p, 1.8));
        break;
    }
    case CT_PROGRESS: {
        double f = rad_num(v) / 100.0;
        int bh = rf_px(p, 8), bw = w - 2 * pad - rf_px(p, 34);
        if (f < 0) f = 0;
        if (f > 1) f = 1;
        rf_draw_rect(p, x + pad, y + (h - bh) / 2, bw, bh, rf_blend(back, fg, 0.15), RF_NONE, 0, bh / 2);
        if (f > 0) rf_draw_rect(p, x + pad, y + (h - bh) / 2, (int)(bw * f) > bh ? (int)(bw * f) : bh, bh, accent, RF_NONE, 0, bh / 2);
        rf_draw_text(p, v, x + pad + bw + rf_px(p, 4), y, rf_px(p, 30), h, fg, RF_ALIGN_RIGHT | RF_ALIGN_VCENTER);
        break;
    }
    case CT_BUTTON: {
        int bw = w - rf_px(p, 10), bh = h - rf_px(p, 8);
        rf_draw_rect(p, x + rf_px(p, 5), y + rf_px(p, 4), bw, bh, hot ? t->hot : t->face, hot ? t->hot_border : t->border, 1, rf_px(p, t->radius + 1));
        rf_draw_text(p, *v ? v : c->text, x + rf_px(p, 5), y + rf_px(p, 4), bw, bh, t->face_text, RF_ALIGN_CENTER | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        break;
    }
    case CT_IMAGE: {
        int s = h - rf_px(p, 8);
        if (s > rf_px(p, 20)) s = rf_px(p, 20);
        rm_icon(p, v, x + (w - s) / 2, y + (h - s) / 2, s, s, accent);
        break;
    }
    case CT_COMBO:
        rf_draw_text(p, v, x + pad, y, w - 2 * pad - rf_px(p, 14), h, fg, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        if (hot && !g->readonly && !c->readonly) rm_chevron(p, x + w - rf_px(p, 12), y + h / 2.0, rf_px(p, 7), RM_DOWN, fg, rf_px(p, 1.2));
        break;
    case CT_NUMBER:
        rf_draw_text(p, v, x + pad, y, w - 2 * pad, h, fg, RF_ALIGN_RIGHT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        break;
    default:
        rf_draw_text(p, v, x + pad, y, w - 2 * pad, h, fg, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
        break;
    }
}

static void paint_lv_cards(const rf_paint *p, RmGrid *g, const rf_theme *t, unsigned accent, unsigned back) {
    int per = lv_per_row(g), cw = rf_px(p, g->lv_view == 2 ? 236 : 220), ch = row_h(g), gap = rf_px(p, 8), i;
    unsigned fg = p->has_fore ? p->fore : t->window_text, card = t->dark ? rf_blend(t->window, 0xFFFFFF, 0.07) : t->input;
    for (i = g->top * per; i < g->nview; i++) {
        int r = g->view[i].row, slot = i - g->top * per, x = (slot % per) * cw + gap / 2, y = (slot / per) * (ch + gap) + gap / 2;
        int w = cw - gap, sel = g->rows[r].sel || r == g->cur_row, hot = i == g->hot_view, isz, k;
        const char *img = cell(g, r, img_col(g));
        if (y > p->height) break;
        if (g->lv_view == 2) rm_shadow(p, x, y, w, ch, rf_px(p, 6), rf_px(p, 4), back);
        rf_draw_rect(p, x, y, w, ch, sel ? rf_blend(card, accent, 0.12) : hot ? rf_blend(card, fg, 0.04) : card,
                     sel ? accent : rf_blend(t->border, card, 0.4), sel ? rf_px(p, 1.5) : 1, rf_px(p, g->lv_view == 2 ? 6 : t->radius + 1));
        if (g->lv_view == 1) {
            isz = rf_px(p, 32);
            if (rm_has_icon(img)) rm_icon(p, img, x + rf_px(p, 12), y + (ch - isz) / 2, isz, isz, accent);
            {
                int tx = x + rf_px(p, 12) + (rm_has_icon(img) ? isz + rf_px(p, 10) : 0);
                HGDIOBJ o = rm_font_push(p, 1.0, 1);
                rf_draw_text(p, cell(g, r, 0), tx, y + rf_px(p, 10), x + w - tx - rf_px(p, 8), rf_px(p, 20), fg, RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
                rm_font_pop(p, o);
                rf_draw_text(p, cell(g, r, 1), tx, y + rf_px(p, 32), x + w - tx - rf_px(p, 8), rf_px(p, 20), rf_blend(fg, card, 0.35),
                             RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
            }
        } else {
            int ty = y + rf_px(p, 12);
            isz = rf_px(p, 24);
            if (rm_has_icon(img)) rm_icon(p, img, x + w - isz - rf_px(p, 12), ty, isz, isz, accent);
            {
                HGDIOBJ o = rm_font_push(p, 1.12, 2);
                rf_draw_text(p, cell(g, r, 0), x + rf_px(p, 12), ty, w - rf_px(p, 24) - isz, rf_px(p, 24), fg, RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
                rm_font_pop(p, o);
            }
            ty += rf_px(p, 30);
            for (k = 1; k < g->ncols && ty + rf_px(p, 18) <= y + ch; k++) {
                rf_draw_text(p, g->cols[k].text, x + rf_px(p, 12), ty, rf_px(p, 80), rf_px(p, 18), rf_blend(fg, card, 0.45), RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
                rf_draw_text(p, cell(g, r, k), x + rf_px(p, 96), ty, w - rf_px(p, 108), rf_px(p, 18), fg, RF_ALIGN_LEFT | RF_ALIGN_ELLIPSIS);
                ty += rf_px(p, 19);
            }
        }
        if (p->focused && r == g->cur_row) rf_draw_rect(p, x + 2, y + 2, w - 4, ch - 4, RF_NONE, rf_blend(card, accent, 0.6), 1, rf_px(p, 4));
    }
}

static void RF_CALL grid_paint(rf_handle h, void *state, const rf_paint *p) {
    RmGrid *g = (RmGrid *)state;
    const rf_theme *t = rm_look_theme(&g->look, p);
    unsigned accent = rm_look_accent(&g->look, t), back = p->has_back ? p->back : t->input;
    unsigned fg = p->has_fore ? p->fore : t->input_text, line = rf_blend(t->border, back, 0.55);
    unsigned head = rf_blend(back, t->window_text, t->dark ? 0.08 : 0.045), alt = rf_blend(back, t->window_text, t->dark ? 0.035 : 0.022);
    int hh = head_h(g), fh = filt_h(g), rh = row_h(g), i, k, fz = frozen_w(g);
    (void)h;
    rm_fill(p, 0, 0, p->width, p->height, back);
    if (g->lv && g->lv_view) { paint_lv_cards(p, g, t, accent, back); return; }
    for (i = g->top; i < g->nview; i++) {           /* rows */
        int y = hh + fh + (i - g->top) * rh, r = g->view[i].row, sel, hot = i == g->hot_view;
        if (y > p->height) break;
        if (g->view[i].group) {
            char txt[300];
            int n = 0, j, closed = g->closed && g->closed[r];
            for (j = 0; j < g->nrows; j++) if (matches(g, j) && rm_ieq(cell(g, j, g->group_col), cell(g, r, g->group_col))) n++;
            rm_fill(p, 0, y, p->width, rh, rf_blend(back, accent, 0.08));
            rm_chevron(p, rf_px(p, 14), y + rh / 2.0, rf_px(p, 8), closed ? RM_RIGHT : RM_DOWN, fg, rf_px(p, 1.4));
            snprintf(txt, sizeof txt, "%s: %s  (%d)", g->cols[g->group_col].text, cell(g, r, g->group_col), n);
            {
                HGDIOBJ o = rm_font_push(p, 1.0, 1);
                rf_draw_text(p, txt, rf_px(p, 28), y, p->width - rf_px(p, 36), rh, fg, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
                rm_font_pop(p, o);
            }
            rf_draw_line(p, 0, y + rh - 1, p->width, y + rh - 1, line, 1);
            continue;
        }
        sel = g->rows[r].sel || (!g->multi && r == g->cur_row);
        {
            unsigned rb = sel && !g->cellsel ? rf_blend(back, accent, t->dark ? 0.35 : 0.16) : hot ? rf_blend(back, t->window_text, 0.04) :
                          (g->alternating && (i % 2)) ? alt : back;
            int pass;
            rm_fill(p, 0, y, p->width, rh, rb);
            for (pass = 0; pass < 2; pass++)        /* scrolling columns first, frozen ones over them */
                for (k = 0; k < g->ncols; k++) {
                    int x = col_x(g, k), w = col_w(g, k);
                    if ((pass == 0) == (g->cols[k].frozen != 0)) continue;
                    if (x + w < 0 || x > p->width) continue;
                    if (pass == 1) rm_fill(p, x, y, w, rh, rb);
                    if (g->cellsel && r == g->cur_row && k == g->cur_col)
                        rf_draw_rect(p, x, y, w, rh, rf_blend(back, accent, 0.2), accent, 1, 0);
                    if (pass == 0 && x < fz) {
                        HRGN rg = CreateRectRgn(fz, y, p->width, y + rh);
                        SelectClipRgn((HDC)p->hdc, rg);
                        paint_cell(p, g, t, r, k, x, y, w, rh, fg, rb, accent, hot && g->hot_col == k);
                        SelectClipRgn((HDC)p->hdc, NULL);
                        DeleteObject(rg);
                    } else {
                        paint_cell(p, g, t, r, k, x, y, w, rh, fg, rb, accent, hot && g->hot_col == k);
                    }
                }
            if (sel && !g->cellsel) rm_fill(p, 0, y, rf_px(p, 3), rh, accent);
            if (p->focused && r == g->cur_row && !g->cellsel) rf_draw_rect(p, 1, y, p->width - 2, rh, RF_NONE, rf_blend(rb, accent, 0.7), 1, 0);
        }
        rf_draw_line(p, 0, y + rh - 1, p->width, y + rh - 1, line, 1);
    }
    if (fz > 0) rf_draw_line(p, fz - 1, hh, fz - 1, p->height, rf_blend(t->border, back, 0.2), rf_px(p, 1.5));
    if (hh) {                                       /* header */
        int pass;
        rm_fill(p, 0, 0, p->width, hh, head);
        for (pass = 0; pass < 2; pass++)
            for (k = 0; k < g->ncols; k++) {
                int x = col_x(g, k), w = col_w(g, k);
                if ((pass == 0) == (g->cols[k].frozen != 0)) continue;
                if (pass == 0 && x + w <= fz) continue;
                if (pass == 1 || k == g->hot_head) rm_fill(p, x, 0, w, hh, k == g->hot_head ? rf_blend(head, accent, 0.12) : head);
                {
                    HGDIOBJ o = rm_font_push(p, 1.0, 1);
                    int al = g->cols[k].type == CT_NUMBER ? RF_ALIGN_RIGHT : g->cols[k].type == CT_CHECK || g->cols[k].type == CT_IMAGE ? RF_ALIGN_CENTER : RF_ALIGN_LEFT;
                    rf_draw_text(p, g->cols[k].text, x + rf_px(p, 8), 0, w - rf_px(p, 16) - (k == g->sort_col ? rf_px(p, 12) : 0), hh, fg,
                                 al | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
                    rm_font_pop(p, o);
                }
                if (k == g->sort_col) rm_chevron(p, x + w - rf_px(p, 12), hh / 2.0, rf_px(p, 7), g->sort_desc ? RM_DOWN : RM_UP, accent, rf_px(p, 1.4));
                rf_draw_line(p, x + w - 1, rf_px(p, 6), x + w - 1, hh - rf_px(p, 6), line, 1);
            }
        rf_draw_line(p, 0, hh - 1, p->width, hh - 1, rf_blend(t->border, back, 0.3), 1);
    }
    if (fh) {                                       /* filter row */
        rm_fill(p, 0, hh, p->width, fh, back);
        for (k = 0; k < g->ncols; k++) {
            int x = col_x(g, k), w = col_w(g, k);
            const char *f = g->filters ? g->filters[k] : "";
            if (!g->cols[k].frozen && x + w <= fz) continue;
            if (g->cols[k].frozen) rm_fill(p, x, hh, w, fh, back);
            rm_icon(p, "filter", x + rf_px(p, 6), hh + (fh - rf_px(p, 12)) / 2, rf_px(p, 12), rf_px(p, 12), *f ? accent : rf_blend(fg, back, 0.55));
            rf_draw_text(p, *f ? f : "", x + rf_px(p, 22), hh, w - rf_px(p, 26), fh, fg, RF_ALIGN_LEFT | RF_ALIGN_VCENTER | RF_ALIGN_ELLIPSIS);
            rf_draw_line(p, x + w - 1, hh + rf_px(p, 4), x + w - 1, hh + fh - rf_px(p, 4), line, 1);
        }
        rf_draw_line(p, 0, hh + fh - 1, p->width, hh + fh - 1, line, 1);
    }
    if (g->nview == 0 && hh) rf_draw_text(p, g->nrows ? "(no matching rows)" : "", 0, hh + fh, p->width, rh * 2, rf_blend(fg, back, 0.5),
                                          RF_ALIGN_CENTER | RF_ALIGN_VCENTER);
    rf_draw_rect(p, 0, 0, p->width, p->height, RF_NONE, rf_blend(t->border, back, 0.3), 1, 0);
}

RF_MODULE(rm_grid) {
    rf_class k;
    memset(&k, 0, sizeof k);
    k.size = (int)sizeof k;
    k.name = "RmGrid";
    k.flags = RF_CLASS_OWNERDRAW | RF_CLASS_FOCUSABLE;
    k.style = WS_VSCROLL | WS_HSCROLL;
    k.create = grid_create; k.destroy = grid_destroy; k.set = grid_set; k.get = grid_get; k.invoke = grid_invoke;
    k.paint = grid_paint; k.message = grid_message;
    k.properties = "Style,AccentColor,EventItem,EventIndex,EventRow,EventColumn,Columns,Rows,ReadOnly,AllowSort,AllowFilter,GroupBy,SelectionMode,AlternatingRows,RowHeight,"
                   "SelectedRow,SelectedRows,RowCount,ColumnCount,CurrentColumn,SortColumn,VisibleRowCount";
    k.events = "CellClick,CellDoubleClick,CellValueChanged,SelectionChanged,ButtonCellClick,ColumnHeaderClick";
    k.methods = "AddRow,InsertRow,RemoveRow,Clear,GetCell,SetCell,GetRow,SortBy,SetFilter,ClearFilter,SetColumnWidth,BeginEdit,EnsureVisible";
    rf_register_class(&k);
    k.name = "RmListView";
    k.style = WS_VSCROLL;
    k.create = lv_create;
    k.properties = "Style,AccentColor,EventItem,EventIndex,Columns,Items,View,SelectedIndex,SelectedItem,RowHeight,Count";
    k.events = "ItemClick,ItemActivate,SelectedIndexChanged";
    k.methods = "AddItem,RemoveItem,Clear,List,SetItemImage,EnsureVisible";
    rf_register_class(&k);
}
