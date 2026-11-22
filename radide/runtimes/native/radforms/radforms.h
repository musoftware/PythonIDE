/* radforms - tiny Win32 forms runtime of RAD IDE native builds (C99, Win32 API only, no Python).
 *
 * It draws the IDE's forms (Form, Button, Label, TextBox, CheckBox, RadioButton, ComboBox, ListBox,
 * GroupBox, Panel, PictureBox, ProgressBar, NumericUpDown, TrackBar, TabControl, LinkLabel, StatusBar,
 * Timer, MenuStrip, ToolStrip, the common dialogs) from a form description (see "Form description"
 * below, made by radide/deploy/native/radforms_gen.py) and reports events to the program. New control
 * classes are added as modules through the class registry (rf_register_class), owner-drawn ones get a
 * double-buffered surface, the current theme and hover / press animation from the core.
 *
 * Plain C ABI for every language (C, C++, FreeBASIC, C# P/Invoke, Go cgo, Rust FFI, Java JNI / Panama,
 * Lua / QuickJS / mruby hosts ...):
 *   - only int, double, UTF-8 char* strings, opaque handles (rf_handle) and plain structs whose first
 *     member is their size; cdecl callbacks with a user pointer; no C++ and no exceptions in the ABI;
 *   - strings are UTF-8 (converted to UTF-16 inside); returned strings live in a ring of 16 buffers:
 *     copy them if you keep them longer than a few calls;
 *   - single-threaded: call it from the thread that runs the event loop.
 * Every function of the ABI is marked RF_API (radforms_api.json lists them for binding generators).
 *
 * Two API layers, both stable:
 *   1. names  - rad_set("lblOut", "Caption", "Hi"): the GUI Bridge client API (radgui.h). Objects are
 *      "Control", "Form" or "Form.Control"; property / method names are case-insensitive VB names.
 *   2. handles - rf_find("Form1.lblOut") -> rf_handle; rf_prop_set / rf_prop_get / rf_invoke; rf_create;
 *      events through rf_run_events(callback, user) with numeric event ids (RF_EV_*).
 *
 * Event loop - one of:
 *   pull:      while (rad_next_event()) { ...rad_obj / rad_ev...; rad_done(); }
 *   key:       return rad_run(dispatch);          dispatch("cmdOk_Click")      (what the IDE generates)
 *   callback:  return rf_run_events(on_event, user);  on_event(handle, RF_EV_CLICK, &args, user)
 * Key and callback loops also support modal forms (rad_show_modal).
 *
 * Licence: part of RAD IDE. Written for RAD IDE (no third-party code).
 */
#ifndef RADFORMS_H
#define RADFORMS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RADFORMS_VERSION 2          /* bumped when the form description changes */
#define RF_ABI_VERSION 1            /* bumped only on incompatible ABI changes (structs grow compatibly) */

#ifndef RF_API
#  if defined(RF_BUILD_DLL)
#    define RF_API __declspec(dllexport)
#  else
#    define RF_API extern
#  endif
#endif
#if defined(_WIN32) && !defined(_WIN64)
#  define RF_CALL __cdecl
#else
#  define RF_CALL
#endif

/* ================================================================== 1. the radgui.h API (GUI Bridge) */
extern char rad_obj[256];           /* object of the current event: control / form / menu item name */
extern char rad_ev[256];            /* event name: Click, TextChanged, Load, Tick ... */
extern char rad_args[1024];         /* "X Y Button KeyCode KeyChar" of mouse / key events */
RF_API const char *rad_arg(int index);    /* word *index* (0-based) of rad_args, "" if missing */

RF_API void rad_init(void);         /* optional: loads the forms (rad_next_event / rad_run call it) */
RF_API int rad_next_event(void);    /* waits for the next event (fills rad_obj/rad_ev/rad_args); 0 = quit */
RF_API void rad_done(void);         /* the current event is handled (shows a form after its Load, ...) */

RF_API void rad_set(const char *obj, const char *prop, const char *value);
RF_API void rad_set_num(const char *obj, const char *prop, double value);
RF_API const char *rad_get(const char *obj, const char *prop);
RF_API double rad_get_num(const char *obj, const char *prop);
RF_API const char *rad_call(const char *obj, const char *method, const char *args);  /* args: \t separated */
RF_API void rad_msgbox(const char *text);
RF_API const char *rad_input(const char *prompt);
RF_API void rad_show(const char *form);
RF_API void rad_hide(const char *form);
RF_API void rad_end(void);          /* quit after the current handler */
RF_API void rad_print(const char *text);  /* a line on stdout (when there is one) and OutputDebugString */

RF_API double rad_num(const char *text);  /* "3.5" -> 3.5 ("" / not a number -> 0) */
RF_API const char *rad_str(double x);     /* 5 -> "5", 0.25 -> "0.25" */

/* cross-language calls: inside a native exe only the functions registered with rad_register
 * (the project's own RADFUNC modules) can be called */
RF_API const char *radcall(const char *name, const char *json_args);
RF_API const char *rad_error(void);
RF_API double rad_json_num(const char *json);
RF_API const char *rad_json_str(const char *json);
RF_API const char *rad_json_quote(const char *text);
RF_API const char *rad_json_numtext(double x);
#define RADFUNC(name) const char *name(int argc, const char **argv)
RF_API const char *rad_fail(const char *message);

/* RAD Hub worker entry points of radgui.h (not used by a native GUI program; they report "no input") */
RF_API int rad_wk_next(void);
RF_API const char *rad_wk_func(void);
RF_API int rad_wk_argc(void);
RF_API const char *rad_wk_arg(int i);
RF_API void rad_wk_reply(const char *json);
RF_API void rad_wk_error(const char *message);
RF_API int rad_worker_main(const char *(*dispatch)(const char *func, int argc, const char **argv, int *found));

/* Form description: by default the RCDATA resource "RADFORMS" of the exe; call this before the first
 * rad_next_event / rad_run to use a description in memory instead (the text is copied). 0 = bad text. */
RF_API int rad_forms_load(const char *description);

/* Names of the handlers the program has ("Form1_Load,cmdOk_Click", case-insensitive). Only these
 * events are reported; without this call (or with "*") every event is reported. */
RF_API void rad_handlers(const char *csv);

/* key loop: dispatch(key) is called with key = "<obj>_<event>"; returns the exit code */
typedef int (RF_CALL *rad_dispatch_fn)(const char *key);
RF_API int rad_run(rad_dispatch_fn dispatch);

RF_API void rad_show_modal(const char *form);  /* shows the form, returns when it is closed / hidden
                                                  (key / callback loops; in pull mode it is modeless) */
RF_API int rad_msgbox_ex(const char *text, const char *title, int vbflags);  /* VB MsgBox: vbYesNo +
                                                  vbQuestion ... -> vbOK=1 ... vbYes=6, vbNo=7 */
RF_API const char *rad_input_ex(const char *prompt, const char *title, const char *default_text);

/* register an in-process function for radcall("Module.func", "[json args]") */
typedef const char *(RF_CALL *rad_func_fn)(int argc, const char **argv);
RF_API void rad_register(const char *name, rad_func_fn fn);

/* GUI Bridge protocol in process (for hosts of languages that speak the line protocol):
 *   rad_command("SET lblOut Caption Hi")  -> NULL      rad_command("GET txtA Text") -> "the text"
 *   SET / GET / CALL obj method args / MSGBOX text / INPUT prompt / SHOW f / HIDE f / DONE / END;
 *   any other line is printed (rad_print). Returns the answer line of GET / CALL / MSGBOX / INPUT.
 * rad_event_line() waits for the next event: "EVENT <obj> <event> [args]" or "QUIT"; answer each
 * event with rad_command("DONE"). */
RF_API const char *rad_command(const char *line);
RF_API const char *rad_event_line(void);
/* the same as a pair of "write a line" / "read a line" functions, for a bridge client whose stdin/stdout
 * I/O is replaced (the Fortran module does this): rad_line_out runs a command and keeps its answer;
 * rad_line_in returns that answer, or (none pending) waits for the next event line. */
RF_API void rad_line_out(const char *line);
RF_API const char *rad_line_in(void);

/* ================================================================== 2. handles */
typedef struct rf_object *rf_handle;      /* a form, control, menu item or ToolStrip button (NULL = none) */

RF_API int rf_abi_version(void);          /* RF_ABI_VERSION of the linked library */
RF_API rf_handle rf_find(const char *path);   /* "Control" / "Form" / "Form.Control"; loads the form */
RF_API rf_handle rf_form(rf_handle h);        /* the form of a control (a form: itself) */
RF_API const char *rf_name(rf_handle h);
RF_API const char *rf_type(rf_handle h);      /* class name: "Form", "Button", "ButtonX" ... */
RF_API void *rf_hwnd(rf_handle h);            /* its HWND (NULL for non-visual objects) */
RF_API void *rf_state(rf_handle h);           /* state of a registered class (rf_class.create) */

RF_API int rf_prop_set(rf_handle h, const char *prop, const char *value);   /* 1 = done */
RF_API int rf_prop_set_num(rf_handle h, const char *prop, double value);
RF_API const char *rf_prop_get(rf_handle h, const char *prop);              /* "" when unknown */
RF_API double rf_prop_get_num(rf_handle h, const char *prop);
RF_API const char *rf_invoke(rf_handle h, const char *method, const char *args);    /* args: \t separated */

/* a control made at run time: parent = form or container; (x, y, w, h) in 96-DPI pixels */
RF_API rf_handle rf_create(rf_handle parent, const char *type, const char *name, int x, int y, int w, int h);
RF_API void rf_destroy(rf_handle h);          /* a control: removed; a form: unloaded */
RF_API void rf_show(rf_handle form, int modal);
RF_API void rf_quit(void);                    /* rad_end */

/* ------------------------------------------------------------------ events */
enum {
    RF_EV_NONE = 0, RF_EV_CLICK = 1, RF_EV_DOUBLECLICK = 2, RF_EV_MOUSEDOWN = 3, RF_EV_MOUSEUP = 4,
    RF_EV_MOUSEMOVE = 5, RF_EV_MOUSEENTER = 6, RF_EV_MOUSELEAVE = 7, RF_EV_MOUSEWHEEL = 8, RF_EV_KEYDOWN = 9,
    RF_EV_KEYUP = 10, RF_EV_KEYPRESS = 11, RF_EV_GOTFOCUS = 12, RF_EV_LOSTFOCUS = 13, RF_EV_TEXTCHANGED = 14,
    RF_EV_CHECKEDCHANGED = 15, RF_EV_SELECTEDINDEXCHANGED = 16, RF_EV_VALUECHANGED = 17, RF_EV_TICK = 18,
    RF_EV_LOAD = 19, RF_EV_ACTIVATED = 20, RF_EV_DEACTIVATE = 21, RF_EV_RESIZE = 22, RF_EV_FORMCLOSING = 23,
    RF_EV_FORMCLOSED = 24,
    RF_EV_CUSTOM = 1000                       /* ids of names made by rf_event_id start here */
};

typedef struct rf_event_args {
    int size;                 /* sizeof(rf_event_args): new members are only added at the end */
    const char *object;       /* object name */
    const char *event;        /* event name ("Click", or a custom one) */
    const char *args;         /* raw "X Y Button KeyCode KeyChar" (GUI Bridge form) or custom text */
    int x, y, button, delta;  /* mouse: 96-DPI pixels in the control, button 1 left 2 middle 3 right */
    int key_code;             /* key events: Windows virtual-key code */
    const char *key_name;     /* key events: "Return", "a", "F1" ... */
    const char *key_char;     /* KeyPress: the character (UTF-8) */
    int cancel;               /* FormClosing: set to 1 to keep the form open */
} rf_event_args;

typedef int (RF_CALL *rf_event_fn)(rf_handle h, int event_id, rf_event_args *args, void *user);

RF_API int rf_event_id(const char *name);     /* "Click" -> RF_EV_CLICK; new names get ids >= RF_EV_CUSTOM */
RF_API const char *rf_event_name(int id);
RF_API void rf_set_event_handler(rf_event_fn fn, void *user);   /* called for every event of rad_run /
                                                 rf_run_events / modal loops (before the key dispatch) */
RF_API int rf_run_events(rf_event_fn fn, void *user);   /* the event loop; returns the exit code */
RF_API void rf_raise(rf_handle h, const char *event, const char *args);    /* queue an event (controls) */

/* ================================================================== 3. themes */
typedef struct rf_theme {
    int size;                 /* sizeof(rf_theme) */
    const char *name;         /* "Light" (system look), "Dark", "Office", "Metro" or your own */
    int dark;                 /* dark title bars / dark scroll bars */
    /* colours 0x00BBGGRR (Win32 COLORREF) */
    unsigned window, window_text, face, face_text, border, hot, hot_border, pressed, accent, accent_text,
        disabled_text, selection, selection_text, input, input_text;
    const char *font_name;    /* default font of owner-drawn controls ("Segoe UI") */
    double font_size;         /* points */
    int radius, border_width, padding;    /* 96-DPI pixels */
    int anim_ms;              /* hover / press animation length (0 = none) */
} rf_theme;

RF_API int rf_theme_set(const char *name);        /* 1 = known; repaints every form */
RF_API const rf_theme *rf_theme_current(void);
RF_API int rf_theme_define(const rf_theme *theme);    /* adds / replaces a theme by name (copied) */
RF_API unsigned rf_theme_color(const char *key);  /* "accent", "window", ... of the current theme */

/* ================================================================== 4. control classes (modules) */
enum {
    RF_CLASS_CONTAINER = 1,   /* can hold child controls */
    RF_CLASS_NONVISUAL = 2,   /* no window (like Timer) */
    RF_CLASS_FOCUSABLE = 4,   /* gets the keyboard focus / Tab stop (Space / Enter = Click when owner-drawn) */
    RF_CLASS_OWNERDRAW = 8,   /* the core makes a double-buffered window and calls paint() */
    RF_CLASS_BUILTIN = 0x100  /* set by the core for its own classes */
};

typedef struct rf_paint {
    int size;                 /* sizeof(rf_paint) */
    rf_handle handle;
    void *hdc;                /* memory DC (double buffer), already filled with the parent background */
    int width, height;        /* client size in device pixels */
    int dpi;                  /* 96 = 100 % */
    const rf_theme *theme;
    int hot, pressed, focused, enabled;
    double hover, press;      /* animated 0..1 versions of hot / pressed */
    void *font;               /* HFONT of the control (selected into hdc) */
    const char *text;         /* the control's Text (UTF-8) */
    unsigned back, fore;      /* the control's BackColor / ForeColor, or the theme's face / face_text */
    int has_back, has_fore;   /* the control has its own colours */
} rf_paint;

typedef struct rf_class {
    int size;                 /* sizeof(rf_class) */
    const char *name;         /* type name used in form descriptions and rf_create, e.g. "ButtonX" */
    unsigned flags;           /* RF_CLASS_* */
    const char *win_class;    /* not owner-drawn: an existing Win32 class to wrap ("BUTTON", ...) */
    unsigned long style, ex_style;   /* extra window styles */
    /* all optional (NULL); the core handles what they leave: geometry, Visible, Enabled, colours,
     * fonts, Text, Tag, focus, mouse / key events and the default Click of owner-drawn classes */
    int (RF_CALL *create)(rf_handle h, void **state);        /* after the window exists; 0 = failed */
    void (RF_CALL *destroy)(rf_handle h, void *state);
    int (RF_CALL *set)(rf_handle h, void *state, const char *prop, const char *value);   /* 1 = handled */
    const char *(RF_CALL *get)(rf_handle h, void *state, const char *prop);     /* NULL = not handled */
    const char *(RF_CALL *invoke)(rf_handle h, void *state, const char *method, const char *args);
    void (RF_CALL *paint)(rf_handle h, void *state, const rf_paint *p);
    int (RF_CALL *message)(rf_handle h, void *state, unsigned msg, uintptr_t wparam, intptr_t lparam,
                           intptr_t *result);                /* 1 = handled (result returned) */
    const char *properties;   /* comma lists for tools: "Style,ColorTable" */
    const char *events;       /* "Click,ExpandedChanged" */
    const char *methods;
} rf_class;

RF_API int rf_register_class(const rf_class *cls);    /* copied; replaces a class of the same name */
RF_API const rf_class *rf_find_class(const char *name);
RF_API int rf_class_count(void);
RF_API const rf_class *rf_class_at(int index);         /* built-in and registered classes */
RF_API void rf_invalidate(rf_handle h);               /* repaint */
RF_API void rf_set_timer(rf_handle h, int id, int ms);    /* WM_TIMER(id) to message(); ms 0 = stop */

/* containers of registered classes (added in RADFORMS_VERSION 2, ABI 1 compatible):
 * rf_set_page - children whose TabPage property is *page* are shown, the others hidden (paged
 *   containers: tab strips, navigation panes); RF_PAGE_ALL (default) shows every child, RF_PAGE_NONE
 *   hides them all (a collapsed group);
 * rf_set_child_back - the background colour standard child controls (Label, CheckBox ...) and
 *   owner-drawn children get inside this container (RF_NONE = the container's / form's colour). */
enum { RF_PAGE_ALL = -1, RF_PAGE_NONE = -2 };
RF_API void rf_set_page(rf_handle h, int page);
RF_API int rf_get_page(rf_handle h);
RF_API void rf_set_child_back(rf_handle h, unsigned color);
RF_API int rf_child_page(rf_handle h);                /* TabPage of a control (0 = first page) */
RF_API int rf_dpi(rf_handle h);                       /* DPI of the form of a control (96 = 100 %) */
RF_API const rf_theme *rf_theme_find(const char *name);   /* a defined theme by name (NULL = none) */
RF_API int rf_rtl(rf_handle h);                       /* 1 = the form is mirrored (RightToLeft) */

/* Modules: a file in radforms/controls/ declares RF_MODULE(name) { rf_register_class(...); } and the
 * line "RF_CLASSES: Name1 Name2" in a comment; the IDE builder links the modules a project uses and
 * calls their registration from rad_modules_init(). Static-library users call rfmod_<name>(). */
#define RF_MODULE(name) void rfmod_##name(void)

/* ================================================================== 5. drawing helpers (rf_paint) */
enum { RF_ALIGN_LEFT = 0, RF_ALIGN_CENTER = 1, RF_ALIGN_RIGHT = 2, RF_ALIGN_TOP = 0, RF_ALIGN_VCENTER = 4,
       RF_ALIGN_BOTTOM = 8, RF_ALIGN_WRAP = 16, RF_ALIGN_ELLIPSIS = 32 };
RF_API int rf_px(const rf_paint *p, double v96);      /* 96-DPI pixels -> device pixels */
RF_API unsigned rf_blend(unsigned a, unsigned b, double t);   /* colour between a (t=0) and b (t=1) */
/* rectangle (rounded when radius > 0, anti-aliased with GDI+ when present); fill / border = colour or
 * RF_NONE; all values in device pixels */
#define RF_NONE 0xFFFFFFFFu
RF_API void rf_draw_rect(const rf_paint *p, int x, int y, int w, int h, unsigned fill, unsigned border,
                         int border_width, int radius);
RF_API void rf_draw_line(const rf_paint *p, int x1, int y1, int x2, int y2, unsigned color, int width);
RF_API void rf_draw_text(const rf_paint *p, const char *text, int x, int y, int w, int h, unsigned color, int align);
RF_API void rf_draw_image(const rf_paint *p, const char *path, int x, int y, int w, int h);

/* ================================================================== Form description (text, UTF-8)
 * One record per line, fields separated by TAB; in fields \t \n \r \\ are escapes.
 *   RADF  1                      header (version)
 *   A     <application title>    title of message boxes
 *   S     <form>                 startup form
 *   F     <form>                 a form; the P lines after it are its properties (Theme = app theme)
 *   C     <type> <name> <parent> a control (parent "" = the form); its P / L lines follow
 *   L     x y w h rx ry rw rh    geometry relative to the container's client size (cw, ch) in 96-DPI
 *                                pixels: left = x + rx*cw, width = w + rw*cw ... (Anchor / Dock)
 *   P     <property> <value>     a property, applied like rad_set (Text, Left, BackColor, Items "a;b")
 *   M     <depth> <name> <text>  menu item of the form's MenuStrip (depth 0 = menu bar, "-" separator)
 *   T     <name> <text>          ToolStrip button ("-" separator)
 *   I     <path> <resource>      image file *path* is embedded as RCDATA *resource*
 * Types: Button Label TextBox CheckBox RadioButton ListBox ComboBox PictureBox ProgressBar
 * NumericUpDown TrackBar Panel GroupBox TabControl LinkLabel StatusBar Timer OpenFileDialog
 * SaveFileDialog ColorDialog FontDialog FolderBrowserDialog + every registered class. */

#ifdef __cplusplus
}
#endif

#endif
