// RAD Modern showcase (RadIDE.Controls): ribbon, side bar, tabs, grid, gauges, toggles, toasts, docking, themes.
// The Rm* controls are ordinary controls for the code: properties by name (gaugeCpu["Value"] = "50"), methods with
// Call (RmToast1.Call("Show", ...)); item events give the item in e.Args ("name index").
// (c) 2026 Musoftware - https://musoftwares.com - MIT License
public static partial class MainForm
{
    static int added;

    static string Item(RadEvent e) => (e.Args ?? "").Split(' ')[0];

    static void Log(string text)
    {
        lblLog.Text = text;
        RmStatusBar1.Call("SetPanelText", "pnlStatus", text);
    }

    static void MainForm_Load(RadEvent e)
    {
        RmSuperTooltip1.Call("SetTooltip", "btnToast", "Show a toast", "A notification slides in at the bottom right and closes by itself.", "RAD Modern", "icon:bell");
        RmSuperTooltip1.Call("SetTooltip", "tileSales", "Sales", "128 orders this month - click to open the products.", "", "icon:chart");
        Log("Loaded");
    }

    static void SetTheme(string theme)
    {
        Me["Theme"] = theme;
        lblTheme.Text = "Theme: " + theme;
        RmStatusBar1.Call("SetPanelText", "pnlTheme", "Theme: " + theme);
        Log("Theme " + theme);
    }

    static void RmRibbon1_ItemClick(RadEvent e)
    {
        switch (Item(e))
        {
            case "thLight": SetTheme("Light"); break;
            case "thDark": SetTheme("Dark"); break;
            case "thOffice": SetTheme("Office"); break;
            case "thMetro": SetTheme("Metro"); break;
            case "cboAccent":
                var c = RmRibbon1.Call("GetItemText", "cboAccent");
                var hex = c == "Green" ? "#107C10" : c == "Purple" ? "#7A3E9D" : c == "Orange" ? "#D35400" : c == "Red" ? "#C42B1C" : "#0078D7";
                Me["AccentColor"] = hex;
                Log("Accent " + c);
                break;
            case "chkRtl":
                Me["RightToLeft"] = RmRibbon1.Call("GetChecked", "chkRtl");
                Log("Right to left: " + RmRibbon1.Call("GetChecked", "chkRtl"));
                break;
            case "chkCompact": RmRibbon1["Collapsed"] = RmRibbon1.Call("GetChecked", "chkCompact"); break;
            case "rbToast": btnToast_Click(e); break;
            case "rbAsk": btnAsk_Click(e); break;
            case "rbAddRow": btnAddRow_Click(e); break;
            case "rbGroup": btnGroup_Click(e); break;
            case "rbSort": gridProducts.Call("SortBy", "Price", true); Log("Sorted by price"); break;
            case "rbFilter": RmTabStrip1["SelectedIndex"] = "1"; gridProducts.Call("Filter", "Product", "Laptop"); Log("Filter: Laptop"); break;
            case "rbSideBar": RmSideBar1.Call("Toggle"); break;
            case "rbDash": RmTabStrip1["SelectedIndex"] = "0"; break;
            case "rbDock": RmTabStrip1["SelectedIndex"] = "3"; break;
            case "mnuExit": End(); break;
            default: Log("Ribbon: " + Item(e)); break;
        }
    }

    static void RmRibbon1_TabChanged(RadEvent e) => Log("Ribbon tab: " + RmRibbon1.Text);

    static void RmSideBar1_ItemClick(RadEvent e)
    {
        var page = Item(e) switch { "sbDash" => "0", "sbProducts" => "1", "sbControls" => "2", "sbPrefs" => "2", "sbDock" => "3", "sbAbout" => "3", _ => "" };
        if (page != "") RmTabStrip1["SelectedIndex"] = page;
        Log("Side bar: " + Item(e));
    }

    static void RmTabStrip1_SelectedIndexChanged(RadEvent e) => RmStatusBar1.Call("SetPanelText", "pnlStatus", "Page: " + RmTabStrip1.Text);

    static void RmStatusBar1_PanelClick(RadEvent e) => Log("Status panel: " + Item(e) + " (zoom " + RmStatusBar1["Zoom"] + "%)");

    static void tileSales_Click(RadEvent e) { RmTabStrip1["SelectedIndex"] = "1"; Log("Tile: Sales"); }
    static void tileOrders_Click(RadEvent e) => Log("Tile: Orders");
    static void tileUsers_Click(RadEvent e) => Log("Tile: Customers");
    static void tileMail_Click(RadEvent e) { tileMail["Count"] = "0"; Log("Tile: Mail (read)"); }

    static void sldCpu_ValueChanged(RadEvent e)
    {
        gaugeCpu["Value"] = sldCpu.Value;
        prgBar["Value"] = sldCpu.Value;
        RmStatusBar1.Call("SetPanelValue", "pnlProgress", sldCpu.Value);
        lblDash.Text = "CPU " + sldCpu.Value + "%";
    }

    static void btnToast_Click(RadEvent e)
    {
        RmToast1.Call("Show", "Saved", "Your changes were saved.", "Success", 4000);
        Log("Toast shown");
    }

    static void RmToast1_Click(RadEvent e) => Log("Toast clicked");

    static void btnAsk_Click(RadEvent e)
    {
        var answer = RmMessageBox1.Call("Show", "Do you want to keep these settings?", "RAD Modern", "YesNo", "Question");
        Log("Answer: " + answer);
    }

    static void btnExport_DropDownItemClicked(RadEvent e) => Log("Export: " + Item(e));
    static void btnExport_Click(RadEvent e) => Log("Export: default");
    static void btnFlat_Click(RadEvent e) => Log("Flat button");
    static void btnLink_Click(RadEvent e) => Log("Link clicked");

    static void tglDark_CheckedChanged(RadEvent e) => SetTheme(tglDark["Checked"] == "True" ? "Dark" : "Light");

    static void chkNotify_CheckedChanged(RadEvent e) => Log("Notifications: " + chkNotify["Checked"]);
    static void optComfort_CheckedChanged(RadEvent e) => Log("Comfortable: " + optComfort["Checked"]);

    static void txtName_TextChanged(RadEvent e) => Log("Hello, " + txtName.Text);

    static void txtEmail_TextChanged(RadEvent e)
    {
        var t = txtEmail.Text;
        txtEmail["ErrorText"] = t.Length == 0 || t.Contains("@") ? "" : "Not a valid e-mail address";
    }

    static void cboCity_SelectedIndexChanged(RadEvent e) => Log("City: " + cboCity.Text);
    static void dtpDate_ValueChanged(RadEvent e) => Log("Date: " + dtpDate["Value"]);
    static void calMain_ValueChanged(RadEvent e) => dtpDate["Value"] = calMain["Value"];
    static void grpMore_CollapsedChanged(RadEvent e) => Log("Group collapsed: " + grpMore["Collapsed"]);

    static void btnAddRow_Click(RadEvent e)
    {
        added++;
        gridProducts.Call("AddRow", "New item " + added + ";Accessory;" + (9.5 + added) + ";" + (20 + 10 * added) + ";True;");
        lblRows.Text = gridProducts["Count"] + " rows";
        Log("Row added");
    }

    static void btnGroup_Click(RadEvent e)
    {
        var on = gridProducts["GroupBy"] == "";
        gridProducts["GroupBy"] = on ? "Category" : "";
        btnGroup.Text = on ? "Ungroup" : "Group by category";
        Log(on ? "Grouped by category" : "Ungrouped");
    }

    static void gridProducts_ButtonCellClick(RadEvent e) => Log("Edit row " + e.Args.Split(' ')[1] + ": " + gridProducts.Call("GetCell", e.Args.Split(' ')[1], "Product"));

    static void treeCats_NodeClick(RadEvent e) => Log("Node: " + Item(e));
    static void treeCats_NodeChecked(RadEvent e) => Log("Checked nodes: " + treeCats.Call("CheckedNodes"));

    static void treeCats_NodeExpanding(RadEvent e)
    {
        if (Item(e) == "ndAccessories" && treeCats.Call("GetNodeText", "ndHubs") == "")
        {
            treeCats.Call("AddNode", "ndAccessories", "Hubs", "ndHubs", "icon:tag");
            treeCats.Call("AddNode", "ndAccessories", "Mice", "ndMice", "icon:tag");
        }
    }

    static void dockMain_WindowClosed(RadEvent e) => lblOutput.Text = "Closed: " + Item(e);
    static void dockMain_ActiveWindowChanged(RadEvent e) => lblOutput.Text = "Active: " + Item(e);
    static void lstCards_ItemClick(RadEvent e) => lblOutput.Text = "Card: " + lstCards.Text;
}
