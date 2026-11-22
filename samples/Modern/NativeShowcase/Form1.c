/* NativeShowcase - the RAD Modern (Rm*) controls in a native C program.
 *
 * Copyright (c) 2026 Musoftware (https://musoftwares.com)
 * MIT License - see LICENSE in this folder.
 *
 * Written for the GUI Bridge (radgui.h): Run (F5) draws the form with the IDE's Tk runtime, Build > Publish makes
 * one small standalone exe with radforms (Win32, no Python, no extra DLLs). Handlers: void <Control>_<Event>(void).
 * Item events (ItemClick, CellClick ...) put the item into EventItem / EventIndex (grid: EventRow / EventColumn).
 */
#include <stdio.h>
#include <string.h>
#include "radgui.h"

static int ticks = 0;

static void status(const char *text)
{
    rad_set("RmStatusBar1", "Text", text);              /* Text = the first panel */
}

static void set_theme(const char *name)
{
    char args[100];
    rad_set("Form1", "Theme", name);                    /* every Rm control with Style = Inherit follows */
    snprintf(args, sizeof args, "stTheme\tTheme: %s", name);
    rad_call("RmStatusBar1", "SetPanelText", args);
    rad_set("tgDark", "Checked", strcmp(name, "Dark") == 0 ? "True" : "False");
}

void Form1_Load(void)
{
    status("Ready - native RAD Modern controls");
    rad_call("RmGrid1", "AddRow", "Youssef|Egypt|35|True|Team|50|Details");
}

void RmRibbon1_ItemClick(void)
{
    char item[100];
    snprintf(item, sizeof item, "%s", rad_get("RmRibbon1", "EventItem"));
    if (strcmp(item, "thLight") == 0) set_theme("Light");
    else if (strcmp(item, "thDark") == 0) set_theme("Dark");
    else if (strcmp(item, "thOffice") == 0) set_theme("Office");
    else if (strcmp(item, "thMetro") == 0) set_theme("Metro");
    else if (strcmp(item, "btnToast") == 0 || strcmp(item, "btnSave") == 0)
        rad_call("RmToast1", "Show", "Saved\tThe report was saved to Documents.\tSuccess\t3000");
    else if (strcmp(item, "btnMsg") == 0 || strcmp(item, "btnAbout") == 0) {
        const char *r = rad_call("RmMessageBox1", "Show",
                                 "RAD Modern controls: ribbon, side bar, tabs, grid, gauges, toasts ...\n"
                                 "One standalone native exe.\tAbout\tOK\tInfo\tNative showcase");
        status(r);
    } else if (strcmp(item, "btnAddRow") == 0) {
        rad_call("RmGrid1", "AddRow", "New customer|Egypt|30|True|Free|5|Details");
        rad_set("RmTabStrip1", "SelectedIndex", "1");
    } else if (strcmp(item, "chkFilter") == 0) {
        rad_set("RmGrid1", "AllowFilter", rad_call("RmRibbon1", "GetChecked", "chkFilter"));
        rad_set("RmTabStrip1", "SelectedIndex", "1");
    } else if (strcmp(item, "chkGroup") == 0) {
        rad_set("RmGrid1", "GroupBy", strcmp(rad_call("RmRibbon1", "GetChecked", "chkGroup"), "True") == 0 ? "Country" : "");
        rad_set("RmTabStrip1", "SelectedIndex", "1");
    } else if (strcmp(item, "appExit") == 0) {
        rad_end();
    } else {
        char msg[160];
        snprintf(msg, sizeof msg, "Ribbon: %s", item);
        status(msg);
    }
}

void RmSideBar1_ItemClick(void)
{
    const char *item = rad_get("RmSideBar1", "EventItem");
    if (strcmp(item, "navDashboard") == 0) rad_set("RmTabStrip1", "SelectedIndex", "0");
    else if (strcmp(item, "navData") == 0) rad_set("RmTabStrip1", "SelectedIndex", "1");
    else if (strcmp(item, "navSettings") == 0) rad_set("RmTabStrip1", "SelectedIndex", "2");
    else rad_call("RmToast1", "Show", "Not in this demo\tThis page is only an example item.\tInfo\t2000");
}

void RmTabStrip1_SelectedIndexChanged(void)
{
    static const char *const names[] = {"navDashboard", "navData", "navSettings"};
    int i = (int)rad_get_num("RmTabStrip1", "SelectedIndex");
    if (i >= 0 && i < 3) rad_call("RmSideBar1", "SelectItem", names[i]);
}

void RmGrid1_ButtonCellClick(void)
{
    char row[16], args[40], name[100], text[300];
    snprintf(row, sizeof row, "%s", rad_get("RmGrid1", "EventRow"));
    snprintf(args, sizeof args, "%s	0", row);
    snprintf(name, sizeof name, "%s", rad_call("RmGrid1", "GetCell", args));
    snprintf(args, sizeof args, "%s	1", row);
    snprintf(text, sizeof text, "%s	Customer from %s (row %s).	Info	2500", name, rad_call("RmGrid1", "GetCell", args), row);
    rad_call("RmToast1", "Show", text);
}

void RmGrid1_CellValueChanged(void)
{
    status("A cell was changed");
}

void cboTheme_SelectedIndexChanged(void)
{
    set_theme(rad_get("cboTheme", "SelectedItem"));
}

void tgDark_CheckedChanged(void)
{
    int dark = strcmp(rad_get("tgDark", "Checked"), "True") == 0;
    const char *now = rad_get("Form1", "Theme");
    if (dark && strcmp(now, "Dark") != 0) set_theme("Dark");
    else if (!dark && strcmp(now, "Dark") == 0) set_theme("Office");
}

void slVolume_ValueChanged(void)
{
    char args[40];
    rad_set("prSync", "Value", rad_get("slVolume", "Value"));
    snprintf(args, sizeof args, "stProg\t%s", rad_get("slVolume", "Value"));
    rad_call("RmStatusBar1", "SetPanelValue", args);
}

void btnApply_Click(void)
{
    char msg[200];
    snprintf(msg, sizeof msg, "Hello %s\tSettings applied (%s).\tSuccess\t2500", rad_get("txtName", "Text"), rad_get("dpStart", "Text"));
    rad_call("RmToast1", "Show", msg);
}

void btnMore_DropDownItemClicked(void)
{
    char msg[160];
    snprintf(msg, sizeof msg, "More: %s", rad_get("btnMore", "EventItem"));
    status(msg);
}

void tmrLive_Tick(void)
{
    static const int cpu[] = {42, 55, 63, 71, 58, 49, 66, 88, 74, 52};
    static const int speed[] = {88, 96, 110, 124, 131, 118, 102, 140, 155, 92};
    ticks++;
    rad_set("gaCpu", "Value", rad_str(cpu[ticks % 10]));
    rad_set("gaSpeed", "Value", rad_str(speed[ticks % 10]));
    rad_set("gaTemp", "Value", rad_str(30 + (ticks * 7) % 25 + 0.5));
    rad_set("prDisk", "Value", rad_str(60 + ticks % 30));
    rad_set("tileMail", "Count", rad_str(12 + ticks % 5));
}
