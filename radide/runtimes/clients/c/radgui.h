/* RAD IDE GUI Bridge - C / C++ client (copied into the project when it runs).
 *
 * The IDE draws the forms; this library talks to it over stdin/stdout
 * (protocol: docs/CONTRACTS.md section 1) and to RAD Hub over TCP (radcall).
 *
 *   rad_set("lblOut", "Caption", "Hello");          set a property
 *   const char *s = rad_get("txtA", "Text");         read a property (text)
 *   rad_call("lstLog", "AddItem", "line");           call a method (args separated by \t)
 *   rad_msgbox("Hi");  rad_input("Name?");  rad_show("Form2");  rad_end();
 *   double x = rad_num(s);  const char *t = rad_str(x);
 *   const char *r = radcall("Helpers.add", "[2, 3]"); (JSON in, JSON text out)
 *
 * Returned strings live in a ring of static buffers: copy them if you keep them
 * for longer than a few calls.
 */
#ifndef RADGUI_H
#define RADGUI_H

#ifdef __cplusplus
extern "C" {
#endif

/* event currently being handled (set by the generated main program) */
extern char rad_obj[256];
extern char rad_ev[256];
extern char rad_args[1024];        /* "X Y Button KeyCode KeyChar" for mouse/key events */
const char *rad_arg(int index);    /* one word of rad_args (0-based), "" if missing */

/* GUI bridge */
void rad_set(const char *obj, const char *prop, const char *value);
void rad_set_num(const char *obj, const char *prop, double value);
const char *rad_get(const char *obj, const char *prop);
double rad_get_num(const char *obj, const char *prop);
const char *rad_call(const char *obj, const char *method, const char *args);
void rad_msgbox(const char *text);
const char *rad_input(const char *prompt);
void rad_show(const char *form);
void rad_hide(const char *form);
void rad_end(void);
void rad_print(const char *text);   /* a line in the IDE Output window */

/* text <-> number */
double rad_num(const char *text);
const char *rad_str(double x);

/* RAD Hub cross-language calls: radcall("Module.function", "[json args]") -> JSON text of the
 * result (e.g. "5", "\"text\"", "null"). On error the result is "" and rad_error() says why. */
const char *radcall(const char *name, const char *json_args);
const char *rad_error(void);

/* JSON helpers (also used by workers) */
double rad_json_num(const char *json);             /* 5 -> 5.0, "5" -> 5.0, true -> 1 */
const char *rad_json_str(const char *json);        /* "a\"b" -> a"b ; other values as written */
const char *rad_json_quote(const char *text);      /* text -> "text" (escaped) */
const char *rad_json_numtext(double x);            /* number as JSON */

/* Worker functions (called FROM other languages through RAD Hub) are written as
 *     RADFUNC(add) { return rad_json_numtext(rad_json_num(argv[0]) + rad_json_num(argv[1])); }
 * argv[i] is the JSON text of argument i; the function returns the JSON text of the result. */
#define RADFUNC(name) const char *name(int argc, const char **argv)
const char *rad_fail(const char *message);   /* return rad_fail("msg"); -> error reply to the caller */

/* used by generated code */
int rad_next_event(void);
void rad_done(void);
void rad_init(void);
int rad_worker_main(const char *(*dispatch)(const char *func, int argc, const char **argv, int *found));

#ifdef __cplusplus
}
#endif

#endif
