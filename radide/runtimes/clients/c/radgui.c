/* RAD IDE GUI Bridge - C / C++ client implementation. See radgui.h.
 * Compiles as C99 or C++ (gcc / g++ / MinGW / MSVC). Windows needs -lws2_32 for radcall. */
#ifndef _CRT_SECURE_NO_WARNINGS
#define _CRT_SECURE_NO_WARNINGS
#endif
#include "radgui.h"

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#ifdef _MSC_VER
#pragma comment(lib, "ws2_32.lib")
#endif
typedef SOCKET rad_sock_t;
#define RAD_BAD_SOCK INVALID_SOCKET
#define rad_closesock closesocket
#else
#include <netdb.h>
#include <sys/socket.h>
#include <unistd.h>
typedef int rad_sock_t;
#define RAD_BAD_SOCK (-1)
#define rad_closesock close
#endif

#define RAD_BUF 65536
#define RAD_RING 16

char rad_obj[256] = "";
char rad_ev[256] = "";
char rad_args[1024] = "";

static char rad_errbuf[1024] = "";
static char rad_ring[RAD_RING][RAD_BUF];
static int rad_ring_pos = 0;

static char *rad_buf(void) {
    char *b = rad_ring[rad_ring_pos];
    rad_ring_pos = (rad_ring_pos + 1) % RAD_RING;
    b[0] = 0;
    return b;
}

static void rad_chomp(char *s) {
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r')) s[--n] = 0;
}

/* read one line from stdin into a ring buffer ("" at end of input) */
static char *rad_readline(int *eof) {
    char *b = rad_buf();
    if (eof) *eof = 0;
    if (!fgets(b, RAD_BUF, stdin)) {
        b[0] = 0;
        if (eof) *eof = 1;
    }
    rad_chomp(b);
    return b;
}

static void rad_send(const char *a, const char *b, const char *c, const char *d) {
    /* one protocol line; newlines inside values would break the protocol */
    const char *parts[4];
    int i;
    parts[0] = a; parts[1] = b; parts[2] = c; parts[3] = d;
    for (i = 0; i < 4; i++) {
        const char *p = parts[i];
        if (!p) break;
        if (i > 0) fputc(' ', stdout);
        for (; *p; p++) fputc((*p == '\n' || *p == '\r') ? ' ' : *p, stdout);
    }
    fputc('\n', stdout);
    fflush(stdout);
}

void rad_init(void) {
    setvbuf(stdout, NULL, _IOLBF, 4096);
}

void rad_print(const char *text) { rad_send(text, NULL, NULL, NULL); }
void rad_done(void) { rad_send("DONE", NULL, NULL, NULL); }
void rad_end(void) { rad_send("END", NULL, NULL, NULL); }

void rad_set(const char *obj, const char *prop, const char *value) {
    rad_send("SET", obj, prop, value ? value : "");
}

void rad_set_num(const char *obj, const char *prop, double value) {
    rad_set(obj, prop, rad_str(value));
}

const char *rad_get(const char *obj, const char *prop) {
    rad_send("GET", obj, prop, NULL);
    return rad_readline(NULL);
}

double rad_get_num(const char *obj, const char *prop) { return rad_num(rad_get(obj, prop)); }

const char *rad_call(const char *obj, const char *method, const char *args) {
    if (args && *args) rad_send("CALL", obj, method, args);
    else rad_send("CALL", obj, method, NULL);
    return rad_readline(NULL);
}

void rad_msgbox(const char *text) {
    rad_send("MSGBOX", text, NULL, NULL);
    rad_readline(NULL);
}

const char *rad_input(const char *prompt) {
    rad_send("INPUT", prompt, NULL, NULL);
    return rad_readline(NULL);
}

void rad_show(const char *form) { rad_send("SHOW", form, NULL, NULL); }
void rad_hide(const char *form) { rad_send("HIDE", form, NULL, NULL); }

const char *rad_arg(int index) {
    char *b = rad_buf();
    const char *p = rad_args;
    int i = 0;
    while (*p) {
        size_t n;
        while (*p == ' ') p++;
        if (!*p) break;
        n = strcspn(p, " ");
        if (i == index) {
            if (n >= RAD_BUF) n = RAD_BUF - 1;
            memcpy(b, p, n);
            b[n] = 0;
            return b;
        }
        p += n;
        i++;
    }
    return b;
}

double rad_num(const char *text) {
    char *end;
    double v;
    if (!text) return 0;
    while (isspace((unsigned char)*text)) text++;
    v = strtod(text, &end);
    return end == text ? 0 : v;
}

const char *rad_str(double x) {
    char *b = rad_buf();
    if (x == floor(x) && fabs(x) < 1e15) snprintf(b, RAD_BUF, "%.0f", x);
    else snprintf(b, RAD_BUF, "%.15g", x);
    return b;
}

/* ------------------------------------------------------------------ events */
int rad_next_event(void) {
    int eof;
    char *line = rad_readline(&eof);
    char *p, *q;
    if (eof || strncmp(line, "QUIT", 4) == 0) return 0;
    if (strncmp(line, "EVENT ", 6) != 0) return 1;     /* unknown line: empty event */
    p = line + 6;
    rad_obj[0] = rad_ev[0] = rad_args[0] = 0;
    q = strchr(p, ' ');
    if (!q) { strncpy(rad_obj, p, sizeof rad_obj - 1); return 1; }
    *q = 0;
    strncpy(rad_obj, p, sizeof rad_obj - 1);
    p = q + 1;
    q = strchr(p, ' ');
    if (q) { *q = 0; strncpy(rad_args, q + 1, sizeof rad_args - 1); }
    strncpy(rad_ev, p, sizeof rad_ev - 1);
    return 1;
}

/* ------------------------------------------------------------------ JSON */
static const char *js_ws(const char *p) {
    while (*p && isspace((unsigned char)*p)) p++;
    return p;
}

/* pointer just after the JSON value at p */
static const char *js_skip(const char *p) {
    p = js_ws(p);
    if (*p == '"') {
        p++;
        while (*p && *p != '"') { if (*p == '\\' && p[1]) p++; p++; }
        return *p ? p + 1 : p;
    }
    if (*p == '[' || *p == '{') {
        int depth = 0;
        while (*p) {
            if (*p == '"') { p = js_skip(p); continue; }
            if (*p == '[' || *p == '{') depth++;
            else if (*p == ']' || *p == '}') { depth--; if (depth == 0) return p + 1; }
            p++;
        }
        return p;
    }
    while (*p && *p != ',' && *p != ']' && *p != '}' && !isspace((unsigned char)*p)) p++;
    return p;
}

static char *js_copy(const char *a, const char *b) {
    char *out = rad_buf();
    size_t n = (size_t)(b - a);
    if (n >= RAD_BUF) n = RAD_BUF - 1;
    memcpy(out, a, n);
    out[n] = 0;
    return out;
}

/* value text of "key" in a JSON object, or NULL */
static const char *js_key(const char *obj, const char *key) {
    const char *p = js_ws(obj);
    size_t klen = strlen(key);
    if (*p != '{') return NULL;
    p++;
    for (;;) {
        const char *k, *v;
        p = js_ws(p);
        if (*p != '"') return NULL;
        k = p + 1;
        p = js_skip(p);
        p = js_ws(p);
        if (*p != ':') return NULL;
        v = js_ws(p + 1);
        if ((size_t)(p - k) >= klen + 1 && strncmp(k, key, klen) == 0 && k[klen] == '"')
            return js_copy(v, js_skip(v));
        p = js_ws(js_skip(v));
        if (*p != ',') return NULL;
        p++;
    }
}

const char *rad_json_str(const char *json) {
    char *out = rad_buf();
    const char *p = js_ws(json ? json : "");
    size_t n = 0;
    if (*p != '"') {
        const char *e = js_skip(p);
        return js_copy(p, e);
    }
    p++;
    while (*p && *p != '"' && n < RAD_BUF - 8) {
        if (*p == '\\' && p[1]) {
            p++;
            switch (*p) {
            case 'n': out[n++] = '\n'; break;
            case 't': out[n++] = '\t'; break;
            case 'r': out[n++] = '\r'; break;
            case 'b': out[n++] = '\b'; break;
            case 'f': out[n++] = '\f'; break;
            case 'u': {
                unsigned cp = 0;
                int i;
                for (i = 1; i <= 4 && isxdigit((unsigned char)p[i]); i++)
                    cp = cp * 16 + (unsigned)(isdigit((unsigned char)p[i]) ? p[i] - '0' : (tolower(p[i]) - 'a' + 10));
                p += 4;
                if (cp >= 0xD800 && cp < 0xDC00 && p[1] == '\\' && p[2] == 'u') {
                    unsigned lo = (unsigned)strtoul(js_copy(p + 3, p + 7), NULL, 16);
                    cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                    p += 6;
                }
                if (cp < 0x80) out[n++] = (char)cp;
                else if (cp < 0x800) { out[n++] = (char)(0xC0 | (cp >> 6)); out[n++] = (char)(0x80 | (cp & 63)); }
                else if (cp < 0x10000) {
                    out[n++] = (char)(0xE0 | (cp >> 12)); out[n++] = (char)(0x80 | ((cp >> 6) & 63));
                    out[n++] = (char)(0x80 | (cp & 63));
                } else {
                    out[n++] = (char)(0xF0 | (cp >> 18)); out[n++] = (char)(0x80 | ((cp >> 12) & 63));
                    out[n++] = (char)(0x80 | ((cp >> 6) & 63)); out[n++] = (char)(0x80 | (cp & 63));
                }
                break;
            }
            default: out[n++] = *p;
            }
            p++;
        } else {
            out[n++] = *p++;
        }
    }
    out[n] = 0;
    return out;
}

double rad_json_num(const char *json) {
    const char *p = js_ws(json ? json : "");
    if (strncmp(p, "true", 4) == 0) return 1;
    if (*p == '"') return rad_num(rad_json_str(p));
    return rad_num(p);
}

const char *rad_json_quote(const char *text) {
    char *out = rad_buf();
    size_t n = 0;
    const unsigned char *p = (const unsigned char *)(text ? text : "");
    out[n++] = '"';
    for (; *p && n < RAD_BUF - 8; p++) {
        if (*p == '"' || *p == '\\') { out[n++] = '\\'; out[n++] = (char)*p; }
        else if (*p == '\n') { out[n++] = '\\'; out[n++] = 'n'; }
        else if (*p == '\r') { out[n++] = '\\'; out[n++] = 'r'; }
        else if (*p == '\t') { out[n++] = '\\'; out[n++] = 't'; }
        else if (*p < 0x20) n += (size_t)snprintf(out + n, 8, "\\u%04x", *p);
        else out[n++] = (char)*p;
    }
    out[n++] = '"';
    out[n] = 0;
    return out;
}

const char *rad_json_numtext(double x) {
    if (x != x || x == HUGE_VAL || x == -HUGE_VAL) return "null";
    return rad_str(x);
}

/* ------------------------------------------------------------------ RAD Hub client */
static rad_sock_t rad_hub = RAD_BAD_SOCK;
static long rad_hub_id = 0;
static char rad_hub_in[RAD_BUF];
static size_t rad_hub_len = 0;

const char *rad_error(void) { return rad_errbuf; }

const char *rad_fail(const char *message) {
    snprintf(rad_errbuf, sizeof rad_errbuf, "%s", message && *message ? message : "error");
    return NULL;
}

static int rad_hub_connect(void) {
    const char *addr = getenv("RAD_HUB");
    char host[256];
    const char *colon;
    struct addrinfo hints, *res = NULL;
    if (rad_hub != RAD_BAD_SOCK) return 1;
    if (!addr || !(colon = strrchr(addr, ':'))) {
        snprintf(rad_errbuf, sizeof rad_errbuf, "RAD_HUB is not set (run the program from RAD IDE)");
        return 0;
    }
#ifdef _WIN32
    {
        static int started = 0;
        WSADATA wsa;
        if (!started && WSAStartup(MAKEWORD(2, 2), &wsa) == 0) started = 1;
    }
#endif
    snprintf(host, sizeof host, "%.*s", (int)(colon - addr), addr);
    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    if (getaddrinfo(host, colon + 1, &hints, &res) != 0 || !res) {
        snprintf(rad_errbuf, sizeof rad_errbuf, "cannot resolve RAD Hub address %s", addr);
        return 0;
    }
    rad_hub = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (rad_hub == RAD_BAD_SOCK || connect(rad_hub, res->ai_addr, (int)res->ai_addrlen) != 0) {
        if (rad_hub != RAD_BAD_SOCK) rad_closesock(rad_hub);
        rad_hub = RAD_BAD_SOCK;
        freeaddrinfo(res);
        snprintf(rad_errbuf, sizeof rad_errbuf, "cannot connect to RAD Hub at %s", addr);
        return 0;
    }
    freeaddrinfo(res);
    return 1;
}

const char *radcall(const char *name, const char *json_args) {
    static char req[RAD_BUF];
    long id;
    int n, sent = 0;
    rad_errbuf[0] = 0;
    if (!rad_hub_connect()) return "";
    id = ++rad_hub_id;
    n = snprintf(req, sizeof req, "{\"id\": %ld, \"call\": %s, \"args\": %s}\n", id, rad_json_quote(name),
                 (json_args && *js_ws(json_args)) ? json_args : "[]");
    if (n >= (int)sizeof req) { snprintf(rad_errbuf, sizeof rad_errbuf, "radcall: arguments too long"); return ""; }
    while (sent < n) {
        int k = (int)send(rad_hub, req + sent, n - sent, 0);
        if (k <= 0) { snprintf(rad_errbuf, sizeof rad_errbuf, "RAD Hub connection lost"); return ""; }
        sent += k;
    }
    for (;;) {
        char *nl = (char *)memchr(rad_hub_in, '\n', rad_hub_len);
        if (nl) {
            char *line = js_copy(rad_hub_in, nl);
            const char *v;
            size_t rest = rad_hub_len - (size_t)(nl + 1 - rad_hub_in);
            memmove(rad_hub_in, nl + 1, rest);
            rad_hub_len = rest;
            rad_chomp(line);
            v = js_key(line, "id");
            if (v && atol(v) != id) continue;          /* stale reply */
            v = js_key(line, "error");
            if (v && strcmp(v, "null") != 0) {
                snprintf(rad_errbuf, sizeof rad_errbuf, "%s", rad_json_str(v));
                return "";
            }
            v = js_key(line, "result");
            return v ? v : "null";
        }
        if (rad_hub_len >= sizeof rad_hub_in - 1) { rad_hub_len = 0; continue; }
        {
            int k = (int)recv(rad_hub, rad_hub_in + rad_hub_len, (int)(sizeof rad_hub_in - 1 - rad_hub_len), 0);
            if (k <= 0) {
                rad_closesock(rad_hub);
                rad_hub = RAD_BAD_SOCK;
                snprintf(rad_errbuf, sizeof rad_errbuf, "RAD Hub connection lost");
                return "";
            }
            rad_hub_len += (size_t)k;
        }
    }
}

/* ------------------------------------------------------------------ worker */
/* One request at a time: rad_wk_next() reads {"id":..,"func":..,"args":[..]} from stdin,
 * rad_wk_reply()/rad_wk_error() answer it. Also used by the Fortran worker (bind(C)). */
#define RAD_MAX_ARGS 64
static char rad_wk_idbuf[64] = "null";
static char rad_wk_fn[256] = "";
static char rad_wk_args[RAD_MAX_ARGS][RAD_BUF / 4];
static const char *rad_wk_argv[RAD_MAX_ARGS];
static int rad_wk_n = 0;

int rad_wk_next(void) {
    for (;;) {
        int eof;
        char *line = rad_readline(&eof);
        const char *id, *func, *args;
        if (eof) return 0;
        if (!*js_ws(line)) continue;
        id = js_key(line, "id");
        func = js_key(line, "func");
        args = js_key(line, "args");
        snprintf(rad_wk_idbuf, sizeof rad_wk_idbuf, "%s", id ? id : "null");
        snprintf(rad_wk_fn, sizeof rad_wk_fn, "%s", func ? rad_json_str(func) : "");
        rad_wk_n = 0;
        if (args) {
            const char *p = js_ws(args);
            if (*p == '[') {
                p = js_ws(p + 1);
                while (*p && *p != ']' && rad_wk_n < RAD_MAX_ARGS) {
                    const char *e = js_skip(p);
                    size_t n = (size_t)(e - p);
                    if (n >= sizeof rad_wk_args[0]) n = sizeof rad_wk_args[0] - 1;
                    memcpy(rad_wk_args[rad_wk_n], p, n);
                    rad_wk_args[rad_wk_n][n] = 0;
                    rad_wk_argv[rad_wk_n] = rad_wk_args[rad_wk_n];
                    rad_wk_n++;
                    if (e == p) break;
                    p = js_ws(e);
                    if (*p == ',') p = js_ws(p + 1);
                }
            }
        }
        if (!func) { rad_wk_error("bad request"); continue; }
        rad_errbuf[0] = 0;
        return 1;
    }
}

const char *rad_wk_func(void) { return rad_wk_fn; }
int rad_wk_argc(void) { return rad_wk_n; }
const char *rad_wk_arg(int i) { return (i >= 0 && i < rad_wk_n) ? rad_wk_args[i] : ""; }

void rad_wk_reply(const char *json) {
    printf("{\"id\": %s, \"result\": %s}\n", rad_wk_idbuf, (json && *js_ws(json)) ? json : "null");
    fflush(stdout);
}

void rad_wk_error(const char *message) {
    printf("{\"id\": %s, \"error\": %s}\n", rad_wk_idbuf, rad_json_quote(message && *message ? message : "error"));
    fflush(stdout);
}

int rad_worker_main(const char *(*dispatch)(const char *func, int argc, const char **argv, int *found)) {
    setvbuf(stdout, NULL, _IOLBF, 4096);
    while (rad_wk_next()) {
        int found = 0;
        const char *res = dispatch(rad_wk_fn, rad_wk_n, rad_wk_argv, &found);
        if (!found) rad_wk_error("unknown function");
        else if (rad_errbuf[0]) rad_wk_error(rad_errbuf);
        else rad_wk_reply(res);
    }
    return 0;
}
