/* radforms handles ABI demo / test program: no IDE project, no form resource - the form description is
 * given in memory, events arrive through rf_run_events(callback), a control class module (ButtonX) and
 * controls made at run time, theme switching, FormClosing cancel. Linked against libradforms.a. */
#include <stdio.h>
#include <string.h>
#include "radforms.h"

RF_MODULE(buttonx);              /* the module's registration function (controls/rf_buttonx.c) */

static const char *FORM =
    "RADF\t1\n"
    "A\tABI demo\n"
    "S\tMain\n"
    "F\tMain\n"
    "P\tText\tradforms ABI demo\n"
    "P\tWidth\t360\n"
    "P\tHeight\t200\n"
    "C\tButtonX\tbx1\t\n"
    "L\t12\t12\t120\t30\t0\t0\t0\t0\n"
    "P\tText\tAccent\n"
    "P\tStyle\tAccent\n"
    "C\tLabel\tlblInfo\t\n"
    "L\t12\t52\t330\t20\t0\t0\t0\t0\n"
    "P\tText\tstart\n"
    "C\tTextBox\ttxtIn\t\n"
    "L\t12\t80\t200\t22\t0\t0\t0\t0\n"
    "P\tText\t\n";

static int clicks = 0, closing = 0;

static int RF_CALL on_event(rf_handle h, int id, rf_event_args *a, void *user) {
    char buf[200];
    rf_handle info = rf_find("lblInfo");
    (void)user;
    if (id == RF_EV_LOAD) {
        rf_handle form = rf_form(h);
        rf_handle bx2 = rf_create(form, "ButtonX", "bx2", 140, 12, 100, 30);
        rf_prop_set(bx2, "Text", "Dark");
        rf_prop_set(bx2, "Style", "Outline");
        snprintf(buf, sizeof buf, "abi %d, %s %s, bx2 %s", rf_abi_version(), rf_type(h), rf_name(h),
                 bx2 ? rf_type(bx2) : "none");
        rf_prop_set(info, "Text", buf);
    } else if (id == RF_EV_CLICK && strcmp(rf_name(h), "bx1") == 0) {
        snprintf(buf, sizeof buf, "bx1 clicked %d", ++clicks);
        rf_prop_set(info, "Text", buf);
        rf_raise(h, "Clicked2", "custom");
    } else if (id == RF_EV_CLICK && strcmp(rf_name(h), "bx2") == 0) {
        rf_theme_set("Dark");
        snprintf(buf, sizeof buf, "theme %s", rf_theme_current()->name);
        rf_prop_set(info, "Text", buf);
    } else if (id == rf_event_id("Clicked2")) {
        snprintf(buf, sizeof buf, "%s | custom event %s (%s)", rf_prop_get(info, "Text"), a->event, a->args);
        rf_prop_set(info, "Text", buf);
    } else if (id == RF_EV_TEXTCHANGED) {
        snprintf(buf, sizeof buf, "typed: %s", rf_prop_get(h, "Text"));
        rf_prop_set(info, "Text", buf);
    } else if (id == RF_EV_FORMCLOSING) {
        if (!closing++) {           /* the first close is cancelled */
            a->cancel = 1;
            rf_prop_set(info, "Text", "close cancelled");
        }
    }
    return 1;
}

int main(void) {
    rfmod_buttonx();
    if (!rad_forms_load(FORM)) return 2;
    return rf_run_events(on_event, NULL);
}
