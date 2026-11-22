/* EventsDemo: every handler logs its event (samples/Tests/Events/make_projects.py) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "radgui.h"

static int closing = 0;

static void evlog(const char *name, const char *rest)
{
    const char *p = getenv("RADEVT_LOG");
    FILE *f;
    if (!p || !*p) return;
    f = fopen(p, "ab");
    if (!f) return;
    fprintf(f, "EVT %s%s%s\n", name, rest && *rest ? " " : "", rest ? rest : "");
    fclose(f);
}

static void evkv(const char *name, const char *k, const char *v)
{
    char b[600];
    snprintf(b, sizeof b, "%s=%s", k, v);
    evlog(name, b);
}

void Form1_Load(void)
{
    evlog("Form1_Load", "");
}

void Form1_Activated(void)
{
    evlog("Form1_Activated", "");
}

void Form1_FormClosed(void)
{
    evlog("Form1_FormClosed", "");
}

void cmdA_MouseDown(void)
{
    evlog("cmdA_MouseDown", rad_args);
}

void cmdA_MouseUp(void)
{
    evlog("cmdA_MouseUp", rad_args);
}

void cmdA_Click(void)
{
    evlog("cmdA_Click", "");
}

void lblA_MouseDown(void)
{
    evlog("lblA_MouseDown", rad_args);
}

void lblA_MouseUp(void)
{
    evlog("lblA_MouseUp", rad_args);
}

void lblA_Click(void)
{
    evlog("lblA_Click", "");
}

void txtA_GotFocus(void)
{
    evlog("txtA_GotFocus", "");
}

void txtA_LostFocus(void)
{
    evlog("txtA_LostFocus", "");
}

void txtA_KeyDown(void)
{
    evlog("txtA_KeyDown", rad_args);
}

void txtA_KeyPress(void)
{
    evlog("txtA_KeyPress", rad_args);
}

void txtA_KeyUp(void)
{
    evlog("txtA_KeyUp", rad_args);
}

void txtA_TextChanged(void)
{
    evkv("txtA_TextChanged", "text", rad_get("txtA", "Text"));
}

void txtB_GotFocus(void)
{
    evlog("txtB_GotFocus", "");
}

void txtB_LostFocus(void)
{
    evlog("txtB_LostFocus", "");
}

void chkA_CheckedChanged(void)
{
    evkv("chkA_CheckedChanged", "value", rad_get("chkA", "Value"));
}

void lstA_SelectedIndexChanged(void)
{
    evkv("lstA_SelectedIndexChanged", "index", rad_get("lstA", "ListIndex"));
}

void Form1_FormClosing(void)
{
    closing++;
    evlog("Form1_FormClosing", "");
    if (closing == 1) rad_set("Form1", "Cancel", "True");
}

void cmdCode_Click(void)
{
    evlog("cmdCode_Click", "begin");
    rad_set("txtA", "Text", "code");
    rad_set("chkA", "Value", "1");
    rad_set("lstA", "ListIndex", "2");
    evlog("cmdCode_Click", "end");
}

void cmdTmr_Click(void)
{
    evlog("cmdTmr_Click", "");
    rad_set("tmrA", "Enabled", "True");
}

void tmrA_Tick(void)
{
    rad_set("tmrA", "Enabled", "False");
    evlog("tmrA_Tick", "");
}
