"""C code generator for DOS: OpenWatcom (``wcl -bt=dos``), Turbo C / Borland C and DJGPP.

Drawing writes straight into the video memory at B800:0000 (a far pointer; DJGPP: ``_farpokew``), keys come
from conio's kbhit / getch, the mouse from INT 33h (int86). C89, /* */ comments only (Turbo C 2.0).

Run-time API for the user code::

    tui_set_text(id, "text");      char *tui_get_text(id);
    tui_set_value(id, v);          int tui_get_value(id);       (check box 0/1, option 1, list index, progress)
    tui_set_visible(id, 0/1);      tui_set_enabled(id, 0/1);
    tui_add_item(id, "text");      tui_clear_list(id);          const char *tui_get_item(id, k);
    tui_show_screen(screen);       tui_msgbox("Title", "Text");  tui_quit();
    tui_key                        the key of a KeyPress event (set it to 0 to cancel the key)
"""
from __future__ import annotations

from .common import App, Regions, build_app, chunks, line_of

CM = ("/* ", " */")
TXLEN = 122
ITLEN = 80


def lit(b: bytes) -> str:
    out = []
    for x in b:
        if 32 <= x < 127 and x not in (34, 92, 63):
            out.append(chr(x))
        else:
            out.append(f"\\{x:03o}")
    return '"' + "".join(out) + '"'


def _arr(name: str, values: list, ctype: str = "int") -> list[str]:
    vals = [str(v) for v in values]
    lines = [f"static {ctype} {name}[{len(vals)}] = {{"]
    for ch in chunks(vals, 20):
        lines.append("    " + ", ".join(ch) + ",")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("};")
    return lines


RUNTIME = r"""
/* ===================================================================== RAD IDE text-mode runtime */
int tui_cur = 0, tui_foc = 0, tui_run = 1, tui_key = 0;
static int tui_mouse = 0, tui_hc = 0, tui_mb = 0, tui_mx = 0, tui_my = 0, tui_mp = 0, tui_shape = 0x0607;
static int tui_dump_flag = 0;

#ifdef __DJGPP__
#define VPOKE(o, w) _farpokew(_dos_ds, 0xB8000L + (o) * 2L, (unsigned short)(w))
#define VPEEKB(o) _farpeekb(_dos_ds, 0xB8000L + (o))
#else
static unsigned short far *tui_vid = (unsigned short far *)MK_FP(0xB800, 0);
#define VPOKE(o, w) (tui_vid[o] = (unsigned short)(w))
#define VPEEKB(o) (((unsigned char far *)tui_vid)[o])
#endif

static void tui_int(int n, int ax, int bx, int cx, int dx, union REGS *out)
{
    union REGS r;
    r.x.ax = ax; r.x.bx = bx; r.x.cx = cx; r.x.dx = dx;
    int86(n, &r, &r);
    if (out) *out = r;
}

static void tui_mouse_show(int v)
{
    if (!tui_mouse) return;
    if (v) {
        if (--tui_hc == 0) tui_int(0x33, 1, 0, 0, 0, 0);
    } else {
        if (++tui_hc == 1) tui_int(0x33, 2, 0, 0, 0, 0);
    }
}

static void tui_poll_mouse(void)
{
    union REGS r;
    tui_mb = 0;
    if (!tui_mouse) return;
    tui_int(0x33, 3, 0, 0, 0, &r);
    tui_mb = r.x.bx & 7; tui_mx = r.x.cx >> 3; tui_my = r.x.dx >> 3;
}

static int tui_norm(int c)
{
    if (c == 0 || c == 0xE0) return 256 + getch();
    return c;
}

static int tui_read_key(void)
{
    if (!kbhit()) return 0;
    return tui_norm(getch());
}

/* key (0 = none); *cl = 1 when the left button went down */
static int tui_get_event(int *cl)
{
    int k;
    *cl = 0;
    if (!tui_mouse) return tui_norm(getch());
    k = tui_read_key();
    tui_poll_mouse();
    if (tui_mb & 1) {
        if (!tui_mp) { tui_mp = 1; *cl = 1; }
    } else tui_mp = 0;
    return k;
}

static int tui_alt_key(int k)
{
    static const char *row1 = "QWERTYUIOP", *row2 = "ASDFGHJKL", *row3 = "ZXCVBNM", *digits = "1234567890";
    int s = k - 256;
    if (s >= 16 && s <= 25) return row1[s - 16];
    if (s >= 30 && s <= 38) return row2[s - 30];
    if (s >= 44 && s <= 50) return row3[s - 44];
    if (s >= 120 && s <= 129) return digits[s - 120];
    return 0;
}

static int tui_upper(int k)
{
    return (k >= 'a' && k <= 'z') ? k - 32 : k;
}

/* w cells at x, y: pad spaces, pre, s (from skip; pw: '*') with mask m ('1' = attribute h), spaces */
static void tui_put(int x, int y, int pad, const char *pre, const char *s, int skip, int pw, const char *m,
                    int w, int a, int h)
{
    int o, n, c;
    if (y < 0 || y >= ROWS || x < 0) return;
    n = COLS - x;
    if (n > w) n = w;
    o = y * COLS + x;
    while (n > 0 && pad > 0) { VPOKE(o++, 0x20 | (a << 8)); n--; pad--; }
    if (pre) while (n > 0 && *pre) { VPOKE(o++, (unsigned char)*pre++ | (a << 8)); n--; }
    s += skip;
    while (n > 0 && *s) {
        c = pw ? '*' : (unsigned char)*s;
        s++;
        if (m && *m) {
            VPOKE(o++, c | ((*m == '1' ? h : a) << 8));
            m++;
        } else VPOKE(o++, c | (a << 8));
        n--;
    }
    while (n > 0) { VPOKE(o++, 0x20 | (a << 8)); n--; }
}

static void tui_putc(int x, int y, int c, int a)
{
    if (x >= 0 && x < COLS && y >= 0 && y < ROWS) VPOKE(y * COLS + x, c | (a << 8));
}

static void tui_box(int x, int y, int w, int h, int a, int dbl)
{
    static const unsigned char bs[6] = {218, 196, 191, 179, 192, 217}, bd[6] = {201, 205, 187, 186, 200, 188};
    const unsigned char *b = dbl ? bd : bs;
    int i, r;
    tui_putc(x, y, b[0], a);
    for (i = 1; i < w - 1; i++) tui_putc(x + i, y, b[1], a);
    tui_putc(x + w - 1, y, b[2], a);
    for (r = 1; r < h - 1; r++) {
        tui_putc(x, y + r, b[3], a);
        for (i = 1; i < w - 1; i++) tui_putc(x + i, y + r, ' ', a);
        tui_putc(x + w - 1, y + r, b[3], a);
    }
    tui_putc(x, y + h - 1, b[4], a);
    for (i = 1; i < w - 1; i++) tui_putc(x + i, y + h - 1, b[1], a);
    tui_putc(x + w - 1, y + h - 1, b[5], a);
}

static void tui_blit(const unsigned char *p)
{
    int o = 0, n;
    while ((n = *p++) != 0) {
        int c = p[0], a = p[1];
        p += 2;
        while (n-- > 0) VPOKE(o++, c | (a << 8));
    }
}

static void tui_face(int i)
{
    int t, a, h, x, y, w, len, p;
    if (!ZI[i] || ZT[i] == 9) return;
    tui_mouse_show(0);
    t = ZT[i]; a = ZA[i]; h = ZB[i];
    if (!ZN[i]) { a = (a & 0xF0) | 8; h = a; }
    else if (i == tui_foc && t >= 2 && t <= 5) { a = ZF[i]; h = ZG[i]; }
    x = ZX[i]; y = ZY[i]; w = ZW[i];
    len = strlen(TX[i]);
    if (len > w) len = w;
    switch (t) {
    case 1:
        p = ZJ[i] == 1 ? (w - len) / 2 : (ZJ[i] == 2 ? w - len : 0);
        tui_put(x, y, p, 0, TX[i], 0, 0, HM[i], w, a, h);
        break;
    case 2:
        tui_put(x, y, (w - len) / 2, 0, TX[i], 0, 0, HM[i], w, a, h);
        break;
    case 3:
        len = strlen(TX[i]);
        tui_put(x, y, 0, 0, TX[i], (i == tui_foc && len >= w) ? len - w + 1 : 0, ZJ[i], 0, w, a, a);
        break;
    case 4:
        tui_put(x, y, 0, ZV[i] ? "[X] " : "[ ] ", TX[i], 0, 0, HM[i], w, a, h);
        break;
    case 5:
        tui_put(x, y, 0, ZV[i] ? "(*) " : "( ) ", TX[i], 0, 0, HM[i], w, a, h);
        break;
    case 6: {
        int ix = x, iy = y, iw = w, ih = ZH[i], sel = ZV[i], tp = ZP[i], sa = ZL[i], r, k, b;
        if (ZJ[i]) { ix++; iy++; iw -= 2; ih -= 2; }
        if (sel >= 0) {
            if (sel < tp) tp = sel;
            if (sel >= tp + ih) tp = sel - ih + 1;
        }
        ZP[i] = tp;
        if (!ZN[i]) sa = a;
        for (r = 0; r < ih; r++) {
            k = tp + r;
            b = (k == sel && k < Z2[i]) ? sa : a;
            tui_put(ix, iy + r, 0, 0, k < Z2[i] ? IT[Z1[i] + k] : "", 0, 0, 0, iw, b, b);
        }
        break;
    }
    case 7: {
        int mx = ZM[i] < 1 ? 1 : ZM[i], v = ZV[i], f, k;
        if (v < 0) v = 0;
        if (v > mx) v = mx;
        f = (int)((long)v * w / mx);
        for (k = 0; k < w; k++) tui_putc(x + k, y, k < f ? 0xDB : 0xB0, a);
        break;
    }
    case 8:
        tui_put(x, y, 0, 0, TX[i], 0, 0, HM[i], w, a, h);
        break;
    }
    tui_mouse_show(1);
}

static void tui_cursor(void)
{
    int i = tui_foc, p;
    if (i && ZT[i] == 3) {
        p = strlen(TX[i]);
        if (p > ZW[i] - 1) p = ZW[i] - 1;
        tui_int(0x10, 0x0200, 0, 0, (ZY[i] << 8) | (ZX[i] + p), 0);
        tui_int(0x10, 0x0100, 0, tui_shape, 0, 0);
    } else tui_int(0x10, 0x0100, 0, 0x2000, 0, 0);
}

void tui_redraw(void)
{
    int i;
    tui_mouse_show(0);
    tui_blit(TSP[tui_cur]);
    for (i = 1; i <= NC; i++) if (ZS[i] == tui_cur) tui_face(i);
    tui_cursor();
    tui_mouse_show(1);
}

static int tui_can_focus(int j)
{
    return ZO[j] > 0 && ZI[j] && ZN[j];
}

void tui_show_screen(int s)
{
    int i, best = 0;
    tui_cur = s; tui_foc = 0;
    for (i = 1; i <= NC; i++)
        if (ZS[i] == s && tui_can_focus(i) && (best == 0 || ZO[i] < ZO[best])) best = i;
    tui_foc = best;
    tui_redraw();
    if (SV[s] & 1) tui_fire_screen(s, 4);
}

static void tui_focus(int i)
{
    int o = tui_foc;
    tui_foc = i;
    if (o && o != i) tui_face(o);
    if (i) tui_face(i);
    tui_cursor();
}

static void tui_next(int d)
{
    int c = tui_foc ? ZO[tui_foc] : 0, best = 0, wrap = 0, j;
    for (j = 1; j <= NC; j++) {
        if (ZS[j] != tui_cur || !tui_can_focus(j)) continue;
        if (d > 0) {
            if (ZO[j] > c && (best == 0 || ZO[j] < ZO[best])) best = j;
            if (wrap == 0 || ZO[j] < ZO[wrap]) wrap = j;
        } else {
            if (ZO[j] < c && (best == 0 || ZO[j] > ZO[best])) best = j;
            if (wrap == 0 || ZO[j] > ZO[wrap]) wrap = j;
        }
    }
    if (!best) best = wrap;
    if (best) tui_focus(best);
}

static void tui_activate(int i)
{
    int j;
    switch (ZT[i]) {
    case 2: case 6:
        tui_fire(i, 1);
        break;
    case 4:
        ZV[i] = 1 - ZV[i];
        tui_face(i);
        tui_fire(i, 1);
        break;
    case 5:
        for (j = 1; j <= NC; j++)
            if (ZT[j] == 5 && ZS[j] == ZS[i] && ZR[j] == ZR[i] && j != i && ZV[j]) { ZV[j] = 0; tui_face(j); }
        ZV[i] = 1;
        tui_face(i);
        tui_fire(i, 1);
        break;
    }
}

static void tui_list_move(int i, int d)
{
    int n = Z2[i], v;
    if (!n) return;
    v = ZV[i] + d;
    if (v < 0) v = 0;
    if (v > n - 1) v = n - 1;
    if (v != ZV[i]) { ZV[i] = v; tui_face(i); tui_fire(i, 2); }
}

static int tui_step(int m, int it, int d)
{
    int n = MIC[m], k = it, c;
    if (!n) return -1;
    for (c = 0; c < n; c++) {
        k += d;
        if (k < 0) k = n - 1;
        if (k >= n) k = 0;
        if (!ISP[MI1[m] + k]) return k;
    }
    return -1;
}

static void tui_draw_menu(int m, int it)
{
    int b = SB[MSC[m]], x = MDX[m], y = MDY[m], w = MDW[m], k, j, i;
    tui_mouse_show(0);
    tui_put(MTX[m], ZY[b], 0, 0, MTS[m], 0, 0, MTM[m], strlen(MTS[m]), ZL[b], ZG[b]);
    tui_box(x, y, w, MDH[m], ZA[b], 0);
    for (k = 0; k < MIC[m]; k++) {
        j = MI1[m] + k;
        if (ISP[j]) {
            tui_putc(x, y + 1 + k, 0xC3, ZA[b]);
            for (i = 1; i < w - 1; i++) tui_putc(x + i, y + 1 + k, 0xC4, ZA[b]);
            tui_putc(x + w - 1, y + 1 + k, 0xB4, ZA[b]);
        } else if (k == it)
            tui_put(x + 1, y + 1 + k, 0, 0, IL[j], 0, 0, IM[j], w - 2, ZL[b], ZG[b]);
        else
            tui_put(x + 1, y + 1 + k, 0, 0, IL[j], 0, 0, IM[j], w - 2, ZA[b], ZB[b]);
    }
    tui_mouse_show(1);
}

static void tui_menu(int m)
{
    int it = tui_step(m, -1, 1), fire = 0, done = 0, k, cl, h, m2, k2, x, y, b, j;
    while (!done) {
        tui_redraw();
        tui_draw_menu(m, it);
        do { k = tui_get_event(&cl); } while (!k && !cl);
        done = 0;
        if (cl) {
            x = tui_mx; y = tui_my; b = SB[tui_cur];
            done = 1;
            if (y == ZY[b]) {
                for (m2 = SM[tui_cur]; m2 <= SL[tui_cur]; m2++)
                    if (x >= MTX[m2] && x < MTX[m2] + (int)strlen(MTS[m2])) { m = m2; it = tui_step(m, -1, 1); done = 0; }
            } else if (x > MDX[m] && x < MDX[m] + MDW[m] - 1 && y > MDY[m] && y < MDY[m] + MDH[m] - 1) {
                j = MI1[m] + y - MDY[m] - 1;
                if (!ISP[j]) fire = j; else done = 0;
            }
        } else if (k == 27 || k == 324) done = 1;
        else if (k == 331) { m = m - 1 < SM[tui_cur] ? SL[tui_cur] : m - 1; it = tui_step(m, -1, 1); }
        else if (k == 333) { m = m + 1 > SL[tui_cur] ? SM[tui_cur] : m + 1; it = tui_step(m, -1, 1); }
        else if (k == 328) it = tui_step(m, it, -1);
        else if (k == 336) it = tui_step(m, it, 1);
        else if (k == 13) { if (it >= 0) { fire = MI1[m] + it; done = 1; } }
        else {
            h = 0;
            if (k > 256) {
                h = tui_alt_key(k);
                for (m2 = SM[tui_cur]; m2 <= SL[tui_cur]; m2++)
                    if (h && MKY[m2] == h) { m = m2; it = tui_step(m, -1, 1); h = 0; }
            } else if (k < 256) h = tui_upper(k);
            if (h)
                for (k2 = 0; k2 < MIC[m]; k2++)
                    if (IKY[MI1[m] + k2] == h && !ISP[MI1[m] + k2]) { fire = MI1[m] + k2; done = 1; break; }
        }
        if (fire) done = 1;
    }
    tui_redraw();
    if (fire) tui_fire_menu(fire);
}

static void tui_handle_key(int k)
{
    int i, t, j, h, m, n;
    tui_key = k;
    i = tui_foc;
    if (i && (ZE[i] & 4)) tui_fire(i, 3);
    if (!tui_key) return;
    if (SV[tui_cur] & 4) tui_fire_screen(tui_cur, 3);
    k = tui_key;
    if (!k) return;
    i = tui_foc;
    t = i ? ZT[i] : 0;
    if (t == 3) {
        n = strlen(TX[i]);
        if (k == 8) {
            if (n > 0) {
                TX[i][n - 1] = 0;
                tui_face(i); tui_cursor();
                if (ZE[i] & 2) tui_fire(i, 2);
            }
            return;
        }
        if (k >= 32 && k < 256) {
            if (n < ZM[i]) {
                TX[i][n] = (char)k; TX[i][n + 1] = 0;
                tui_face(i); tui_cursor();
                if (ZE[i] & 2) tui_fire(i, 2);
            }
            return;
        }
    }
    switch (k) {
    case 9: tui_next(1); break;
    case 271: tui_next(-1); break;
    case 336: case 333: if (t == 6) tui_list_move(i, 1); else tui_next(1); break;
    case 328: case 331: if (t == 6) tui_list_move(i, -1); else tui_next(-1); break;
    case 13: if (t == 3) tui_next(1); else if (i) tui_activate(i); break;
    case 32: if (i && t != 6) tui_activate(i); break;
    case 27:
        if (SK[tui_cur]) tui_activate(SK[tui_cur]);
        else if (SE[tui_cur]) tui_run = 0;
        break;
    case 324: if (SM[tui_cur]) tui_menu(SM[tui_cur]); break;
    default:
        h = k > 256 ? tui_alt_key(k) : 0;
        if (h)
            for (m = 1; m <= NM; m++)
                if (MSC[m] == tui_cur && MKY[m] == h) { tui_menu(m); return; }
        if (!h && k < 256 && t != 3) h = tui_upper(k);
        if (h)
            for (j = 1; j <= NC; j++)
                if (ZS[j] == tui_cur && ZK[j] == h && tui_can_focus(j)) {
                    tui_focus(j);
                    if (ZT[j] == 2 || ZT[j] == 4 || ZT[j] == 5) tui_activate(j);
                    return;
                }
    }
}

static void tui_click(int x, int y)
{
    int b = SB[tui_cur], m, j, iy, ih, r;
    if (b && y == ZY[b]) {
        for (m = 1; m <= NM; m++)
            if (MSC[m] == tui_cur && x >= MTX[m] && x < MTX[m] + (int)strlen(MTS[m])) { tui_menu(m); return; }
        return;
    }
    for (j = NC; j >= 1; j--) {
        if (ZS[j] != tui_cur || !tui_can_focus(j)) continue;
        if (x < ZX[j] || x >= ZX[j] + ZW[j] || y < ZY[j] || y >= ZY[j] + ZH[j]) continue;
        tui_focus(j);
        if (ZT[j] == 6) {
            iy = ZY[j]; ih = ZH[j];
            if (ZJ[j]) { iy++; ih -= 2; }
            r = y - iy;
            if (r >= 0 && r < ih && ZP[j] + r < Z2[j]) {
                if (ZV[j] != ZP[j] + r) {
                    ZV[j] = ZP[j] + r; tui_face(j);
                    if (ZE[j] & 2) tui_fire(j, 2);
                }
                tui_fire(j, 1);
            }
        } else if (ZT[j] != 3) tui_activate(j);
        return;
    }
}

void tui_msgbox(const char *title, const char *text)
{
    int tl = strlen(title), w = strlen(text) + 4, x, y, k, cl, n;
    if (tl + 6 > w) w = tl + 6;
    if (w < 12) w = 12;
    if (w > COLS) w = COLS;
    x = (COLS - w) / 2; y = (ROWS - 6) / 2;
    tui_mouse_show(0);
    tui_box(x, y, w, 6, 0x70, 1);
    if (tl) {
        n = tl > w - 6 ? w - 6 : tl;
        tui_put(x + (w - n - 2) / 2, y, 1, 0, title, 0, 0, 0, n + 1, 0x70, 0x70);
        tui_putc(x + (w - n - 2) / 2 + n + 1, y, ' ', 0x70);
    }
    tui_put(x + 2, y + 2, 0, 0, text, 0, 0, 0, w - 4, 0x70, 0x70);
    tui_put(x + (w - 6) / 2, y + 4, 0, 0, "  OK  ", 0, 0, 0, 6, 0x2F, 0x2F);
    tui_int(0x10, 0x0100, 0, 0x2000, 0, 0);
    tui_mouse_show(1);
    do { k = tui_get_event(&cl); } while (!cl && k != 13 && k != 27 && k != 32);
    tui_redraw();
}

void tui_set_text(int i, const char *s)
{
    strncpy(TX[i], s, TXLEN - 1);
    TX[i][TXLEN - 1] = 0;
    HM[i] = 0;
    if (ZS[i] == tui_cur) { tui_face(i); tui_cursor(); }
}

char *tui_get_text(int i) { return TX[i]; }

void tui_set_value(int i, int v)
{
    int j;
    if (ZT[i] == 5 && v) {
        for (j = 1; j <= NC; j++) if (ZT[j] == 5 && ZS[j] == ZS[i] && ZR[j] == ZR[i]) ZV[j] = 0;
        ZV[i] = 1;
    } else ZV[i] = v;
    if (ZS[i] == tui_cur) tui_redraw();
}

int tui_get_value(int i) { return ZV[i]; }

static void tui_set_flag(int i, int v, int *field)
{
    field[i] = v;
    if (!v && tui_foc == i) { tui_next(1); if (tui_foc == i) tui_foc = 0; }
    if (ZS[i] == tui_cur) tui_redraw();
}

void tui_set_visible(int i, int v) { tui_set_flag(i, v, ZI); }
void tui_set_enabled(int i, int v) { tui_set_flag(i, v, ZN); }

void tui_add_item(int i, const char *s)
{
    if (Z2[i] >= Z3[i]) return;
    strncpy(IT[Z1[i] + Z2[i]], s, ITLEN - 1);
    IT[Z1[i] + Z2[i]][ITLEN - 1] = 0;
    Z2[i]++;
    if (ZV[i] < 0) ZV[i] = 0;
    if (ZS[i] == tui_cur) tui_face(i);
}

void tui_clear_list(int i)
{
    Z2[i] = 0; ZV[i] = -1; ZP[i] = 0;
    if (ZS[i] == tui_cur) tui_face(i);
}

const char *tui_get_item(int i, int k) { return (k >= 0 && k < Z2[i]) ? IT[Z1[i] + k] : ""; }

void tui_quit(void) { tui_run = 0; }

static void tui_dump(void)
{
    FILE *f;
    long o;
    tui_mouse_show(0);
    f = fopen("SCREEN.BIN", "wb");
    if (!f) return;
    for (o = 0; o < (long)COLS * ROWS * 2; o++) fputc(VPEEKB(o), f);
    fclose(f);
}

static void tui_init(int argc, char **argv)
{
    union REGS r;
    int i;
    for (i = 1; i < argc; i++)
        if (argv[i][0] == '/' && (argv[i][1] == 'D' || argv[i][1] == 'd')) tui_dump_flag = 1;
    tui_int(0x10, 0x0003, 0, 0, 0, 0);
@ROWSMODE@
    tui_int(0x10, 0x0300, 0, 0, 0, &r);
    tui_shape = r.x.cx;
    tui_int(0x10, 0x0100, 0, 0x2000, 0, 0);
    tui_int(0x33, 0, 0, 0, 0, &r);
    if (r.x.ax == 0xFFFF) { tui_mouse = 1; tui_int(0x33, 1, 0, 0, 0, 0); }
}

static void tui_main(void)
{
    int k, cl;
@SPLASH@
    tui_show_screen(1);
    if (tui_dump_flag) { tui_dump(); tui_run = 0; }
    while (tui_run) {
        k = tui_get_event(&cl);
        if (k) tui_handle_key(k);
        if (cl) tui_click(tui_mx, tui_my);
    }
    tui_mouse_show(0);
    tui_int(0x10, 0x0003, 0, 0, 0, 0);
}
"""

SPLASH = r"""    tui_blit(TSP[0]);
    if (!tui_dump_flag) {
        if (@SECONDS@ > 0) {
            long t;
            for (t = 0; t < @SECONDS@ * 20L && !kbhit(); t++) delay(50);
            if (kbhit()) tui_norm(getch());
        } else tui_norm(getch());
    }"""

ROWSMODE = {25: "", 43: "    tui_int(0x10, 0x1112, 0, 0, 0, 0);", 50: "    tui_int(0x10, 0x1112, 0, 0, 0, 0);"}


def generate(screens, old_text: str = "", app: App | None = None) -> tuple[str, list[str]]:
    app = app or build_app(screens)
    rg = Regions(old_text, CM)
    out: list[str] = []
    w = out.append
    w(f"/* {app.screens[0].name} - DOS text-mode program generated by RAD IDE (Text-Mode Designer)")
    w("   Do not edit outside the USER CODE regions: the rest is rewritten when the screens change.")
    w("   Build: wcl -bt=dos -ms main.c   (OpenWatcom)  |  tcc main.c  (Turbo C)  |  gcc main.c -o main.exe"
      "  (DJGPP) */")
    w("#include <stdio.h>")
    w("#include <string.h>")
    w("#include <stdlib.h>")
    w("#include <dos.h>")
    w("#include <conio.h>")
    w("#ifdef __DJGPP__")
    w("#include <go32.h>")
    w("#include <sys/farptr.h>")
    w("#define far")
    w("#endif")
    w("#ifdef __WATCOMC__")
    w("#include <i86.h>")
    w("#endif")
    w("")
    w(f"#define COLS {app.cols}")
    w(f"#define ROWS {app.rows}")
    w(f"#define NC {len(app.ctls)}")
    w(f"#define NM {len(app.menus)}")
    w(f"#define TXLEN {TXLEN}")
    w(f"#define ITLEN {ITLEN}")
    for s in app.screens:
        w(f"#define {s.name} {s.index}")
    for c in app.ctls:
        w(f"#define {c.name} {c.index}")
    w("")
    w("void tui_fire(int i, int ev);")
    w("void tui_fire_menu(int k);")
    w("void tui_fire_screen(int s, int ev);")
    w("void tui_set_text(int i, const char *s);")
    w("char *tui_get_text(int i);")
    w("void tui_set_value(int i, int v);")
    w("int tui_get_value(int i);")
    w("void tui_set_visible(int i, int v);")
    w("void tui_set_enabled(int i, int v);")
    w("void tui_add_item(int i, const char *s);")
    w("void tui_clear_list(int i);")
    w("const char *tui_get_item(int i, int k);")
    w("void tui_show_screen(int s);")
    w("void tui_msgbox(const char *title, const char *text);")
    w("void tui_quit(void);")
    w("void tui_redraw(void);")
    w("extern int tui_key, tui_cur, tui_foc;")
    for h in app.handlers:
        w(f"void {h.key}(void);")
    w("")
    w(rg.region("declarations", "/* your global variables and #defines */"))
    w("")
    cs = app.ctls
    for name, attr_ in [("ZT", "code"), ("ZS", "screen"), ("ZX", "x"), ("ZY", "y"), ("ZW", "w"), ("ZH", "h"),
                        ("ZA", "a"), ("ZB", "ha"), ("ZF", "fa"), ("ZG", "fha"), ("ZL", "sa"), ("ZV", "value"),
                        ("ZM", "max"), ("ZO", "tab"), ("ZK", "hotkey"), ("ZR", "group"), ("ZE", "events"),
                        ("ZI", "visible"), ("ZN", "enabled"), ("ZJ", "flag"), ("Z1", "first_item"),
                        ("Z3", "capacity")]:
        out.extend(_arr(name, [0] + [getattr(c, attr_) for c in cs]))
    out.extend(_arr("ZP", [0] * (len(cs) + 1)))
    out.extend(_arr("Z2", [0] + [len(c.items) for c in cs]))
    w(f"static char TX[{len(cs) + 1}][TXLEN] = {{")
    w("    " + ",\n    ".join([lit(b"")] + [lit(c.text[:TXLEN - 1]) for c in cs]))
    w("};")
    w(f"static const char *HM[{len(cs) + 1}] = {{")
    w("    " + ",\n    ".join(["0"] + [f'"{c.mask}"' if "1" in c.mask else "0" for c in cs]))
    w("};")
    nslot = app.n_items
    items = {c.first_item + k: it for c in cs for k, it in enumerate(c.items)}
    w(f"static char IT[{nslot + 1}][ITLEN] = {{")
    w("    " + ",\n    ".join(lit(items.get(i, b"")[:ITLEN - 1]) for i in range(0, max(items, default=0) + 1)))
    w("};")
    ms = app.menus
    for name, f in [("MSC", lambda m: m.screen), ("MTX", lambda m: m.title_x), ("MKY", lambda m: m.hotkey),
                    ("MDX", lambda m: m.box[0]), ("MDY", lambda m: m.box[1]), ("MDW", lambda m: m.box[2]),
                    ("MDH", lambda m: m.box[3]), ("MI1", lambda m: m.first_item), ("MIC", lambda m: m.count)]:
        out.extend(_arr(name, [0] + [f(m) for m in ms]))
    w(f"static const char *MTS[{len(ms) + 1}] = {{" + ", ".join(['""'] + [lit(m.title) for m in ms]) + "};")
    w(f"static const char *MTM[{len(ms) + 1}] = {{" + ", ".join(['""'] + [f'"{m.mask}"' for m in ms]) + "};")
    its = app.items
    w(f"static const char *IL[{len(its) + 1}] = {{")
    w("    " + ",\n    ".join(['""'] + [lit(i.line) for i in its]))
    w("};")
    w(f"static const char *IM[{len(its) + 1}] = {{")
    w("    " + ",\n    ".join(['""'] + [f'"{i.mask}"' for i in its]))
    w("};")
    out.extend(_arr("ISP", [0] + [1 if i.sep else 0 for i in its]))
    out.extend(_arr("IKY", [0] + [i.hotkey for i in its]))
    ss = app.screens
    for name, f in [("SE", lambda s: s.esc_quits), ("SK", lambda s: s.cancel), ("SV", lambda s: s.events),
                    ("SB", lambda s: s.bar), ("SM", lambda s: s.menu_first), ("SL", lambda s: s.menu_last)]:
        out.extend(_arr(name, [0] + [f(s) for s in ss]))
    sp = app.splash()
    if sp:
        out.extend(_arr("TS0", [v for run in sp.splash_runs for v in run] + [0], "const unsigned char"))
    for s in ss:
        out.extend(_arr(f"TS{s.index}", [v for run in s.runs for v in run] + [0], "const unsigned char"))
    w(f"static const unsigned char *TSP[{len(ss) + 1}] = {{" +
      ", ".join([("TS0" if sp else "0")] + [f"TS{s.index}" for s in ss]) + "};")
    rt = RUNTIME.replace("@ROWSMODE@", ROWSMODE.get(app.rows, ""))
    rt = rt.replace("@SPLASH@", SPLASH.replace("@SECONDS@", str(sp.splash_seconds)) if sp else "")
    out.append(rt)
    w("/* ===================================================================== event handlers */")
    w(rg.region("general", "/* your own functions */"))
    w("")
    for h in app.handlers:
        w(f"void {h.key}(void)")
        w("{")
        w(rg.region(h.key, ""))
        w("}")
        w("")
    w(rg.orphans("/* ", " */"))
    w("")
    w("void tui_fire(int i, int ev)")
    w("{")
    hs = app.ctl_handlers()
    if hs:
        w("    switch (i * 4 + ev) {")
        for h in hs:
            w(f"    case {h.target * 4 + {'Click': 1, 'Change': 2, 'KeyPress': 3}[h.event]}: {h.key}(); break;")
        w("    }")
    else:
        w("    (void)i; (void)ev;")
    w("}")
    w("")
    w("void tui_fire_menu(int k)")
    w("{")
    hs = app.menu_handlers()
    if hs:
        w("    switch (k) {")
        for h in hs:
            w(f"    case {h.target}: {h.key}(); break;")
        w("    }")
    else:
        w("    (void)k;")
    w("}")
    w("")
    w("void tui_fire_screen(int s, int ev)")
    w("{")
    hs = app.screen_handlers()
    if hs:
        w("    switch (s * 8 + ev) {")
        for h in hs:
            w(f"    case {h.target * 8 + (4 if h.event == 'Load' else 3)}: {h.key}(); break;")
        w("    }")
    else:
        w("    (void)s; (void)ev;")
    w("}")
    w("")
    w("int main(int argc, char **argv)")
    w("{")
    w("    tui_init(argc, argv);")
    w(rg.region("startup", "    /* code that runs before the first screen is shown */"))
    w("    tui_main();")
    w("    return 0;")
    w("}")
    text = "\n".join(out).replace("\r", "") + "\n"
    return text, list(app.warnings)


def handler_line(text: str, key: str) -> int:
    return line_of(text, rf"^void\s+{key}\s*\(void\)\s*$")


def handler_name(key: str) -> str:
    return key
