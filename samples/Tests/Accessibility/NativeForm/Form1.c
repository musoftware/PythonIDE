/* NativeForm - accessibility test program (samples/Tests/Accessibility/test_native_a11y.py).
 *
 * Built with radforms into a native Win32 exe and driven with the keyboard (Tab / Space / Enter / Alt+letter) and
 * read with UI Automation: tab order follows TabIndex, standard controls and RAD Modern (Rm*) controls report
 * names, roles and values to screen readers. Handlers: void <Control>_<Event>(void).
 */
#include <stdio.h>
#include "radgui.h"

static int clicks = 0;

void Form1_Load(void)
{
    /* a list has no text of its own: the program names it for screen readers (AccessibleName) */
    rad_set("lstItems", "AccessibleName", "Items list");
    rad_set("lstItems", "AccessibleDescription", "Pick one item");
}

void btnOK_Click(void)
{
    char t[64];
    snprintf(t, sizeof t, "OK %d", ++clicks);
    rad_set("lblOut", "Text", t);
}

void chkAgree_CheckedChanged(void)
{
    rad_set("lblOut", "Text", rad_get("chkAgree", "Checked"));
}

void rmSave_Click(void)
{
    rad_set("lblOut", "Text", "saved");
}

void tgDark_CheckedChanged(void)
{
    rad_set("lblOut", "Text", rad_get("tgDark", "Checked"));
}
