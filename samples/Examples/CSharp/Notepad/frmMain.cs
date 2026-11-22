// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Notepad - a text editor in C# (RAD IDE GUI Bridge: the IDE draws frmMain, this class handles its events;
// Build > Publish makes a native WinForms exe without Python).
//
// Shows: menus, OpenFileDialog / SaveFileDialog / FontDialog, System.IO.File with UTF-8, the Windows clipboard
// (P/Invoke to user32 - works in the console bridge program and in the WinForms exe), Find / Find Next /
// Replace with SelStart / SelLength / SelText, a status bar, "discard changes?" and exceptions for file errors.
using System;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;

public static partial class frmMain
{
    const int MaxText = 60000;          // a GUI Bridge answer is one line of at most 64 KB
    static string fileName = "";        // "" = Untitled
    static string findWhat = "";
    static bool dirty, loading;

    // ------------------------------------------------------------------ helpers
    static void UpdateTitle() =>
        Me.Caption = (dirty ? "*" : "") + (fileName == "" ? "Untitled" : Path.GetFileName(fileName)) + " - Notepad";

    static void Status(string text) => sbStatus.Text = text;

    static void SetText(string text)
    {
        loading = true;
        txtDoc.Text = text;
        loading = false;
    }

    static bool ConfirmDiscard()
    {
        if (!dirty) return true;
        var answer = InputBox("The text has changed. Type YES to discard the changes (or Cancel to keep them):");
        return answer.StartsWith("y", StringComparison.OrdinalIgnoreCase);
    }

    static bool WriteFile(string path)
    {
        try
        {
            string text = txtDoc.Text;
            File.WriteAllText(path, text, new UTF8Encoding(false));
            fileName = path;
            dirty = false;
            UpdateTitle();
            Status($"Saved {Path.GetFileName(path)} ({text.Length} characters)");
            return true;
        }
        catch (Exception ex)
        {
            MsgBox($"Cannot write {path}:\n{ex.Message}");
            return false;
        }
    }

    static void OpenFile(string path)
    {
        try
        {
            string text = File.ReadAllText(path, Encoding.UTF8);           // the BOM is removed by .NET
            bool cut = text.Length > MaxText;
            if (cut) text = text.Substring(0, MaxText);
            text = text.Replace("\r\n", "\n").Replace("\n", "\r\n");         // a Windows edit box needs CR LF
            SetText(text);
            fileName = path;
            dirty = false;
            UpdateTitle();
            Status($"Opened {Path.GetFileName(path)}" + (cut ? $" (only the first {MaxText} characters)" : ""));
        }
        catch (Exception ex)
        {
            MsgBox($"Cannot open {path}:\n{ex.Message}");
        }
    }

    static bool FindNext()
    {
        if (findWhat == "") return false;
        string text = txtDoc.Text;
        int from = Math.Min(text.Length, Rad.ToInt(txtDoc["SelStart"]) + Rad.ToInt(txtDoc["SelLength"]));
        int hit = text.IndexOf(findWhat, from, StringComparison.CurrentCultureIgnoreCase);
        if (hit < 0) hit = text.IndexOf(findWhat, StringComparison.CurrentCultureIgnoreCase);    // wrap around
        if (hit < 0)
        {
            Status($"Cannot find \"{findWhat}\"");
            return false;
        }
        txtDoc["SelStart"] = hit.ToString();
        txtDoc["SelLength"] = findWhat.Length.ToString();
        txtDoc.SetFocus();
        Status($"Found \"{findWhat}\" at character {hit + 1}");
        return true;
    }

    // ------------------------------------------------------------------ events
    static void frmMain_Load(RadEvent e)
    {
        UpdateTitle();
        Status("Ready - File > Open to load a text file");
    }

    static void txtDoc_TextChanged(RadEvent e)
    {
        if (loading || dirty) return;
        dirty = true;
        UpdateTitle();
    }

    static void mnuNew_Click(RadEvent e)
    {
        if (!ConfirmDiscard()) return;
        SetText("");
        fileName = "";
        dirty = false;
        UpdateTitle();
        Status("New document");
    }

    static void mnuOpen_Click(RadEvent e)
    {
        if (!ConfirmDiscard()) return;
        if (dlgOpen.Call("ShowOpen") != "OK") return;
        string path = dlgOpen["FileName"];
        if (path != "") OpenFile(path);
    }

    static void mnuSaveAs_Click(RadEvent e)
    {
        dlgSave["FileName"] = fileName == "" ? "Untitled.txt" : Path.GetFileName(fileName);
        if (dlgSave.Call("ShowSave") != "OK") return;
        string path = dlgSave["FileName"];
        if (path != "") WriteFile(path);
    }

    static void mnuSave_Click(RadEvent e)
    {
        if (fileName == "") mnuSaveAs_Click(e);
        else WriteFile(fileName);
    }

    static void mnuExit_Click(RadEvent e)
    {
        if (ConfirmDiscard()) End();
    }

    static void mnuCut_Click(RadEvent e)
    {
        string sel = txtDoc["SelText"];
        if (sel == "") return;
        WinClipboard.SetText(sel);
        txtDoc["SelText"] = "";
        Status("Cut to the clipboard");
    }

    static void mnuCopy_Click(RadEvent e)
    {
        string sel = txtDoc["SelText"];
        if (sel == "") { Status("Nothing selected"); return; }
        WinClipboard.SetText(sel);
        Status("Copied to the clipboard");
    }

    static void mnuPaste_Click(RadEvent e)
    {
        string clip = WinClipboard.GetText();
        if (clip == "") { Status("The clipboard has no text"); return; }
        txtDoc["SelText"] = clip;
        Status("Pasted");
    }

    static void mnuSelectAll_Click(RadEvent e)
    {
        txtDoc["SelStart"] = "0";
        txtDoc["SelLength"] = txtDoc.Text.Length.ToString();
        txtDoc.SetFocus();
    }

    static void mnuFind_Click(RadEvent e)
    {
        string what = InputBox("Find what:");
        if (what == "") return;
        findWhat = what;
        txtDoc["SelLength"] = "0";
        FindNext();
    }

    static void mnuFindNext_Click(RadEvent e)
    {
        if (findWhat == "") mnuFind_Click(e);
        else FindNext();
    }

    static void mnuReplace_Click(RadEvent e)
    {
        string what = InputBox("Replace what:");
        if (what == "") return;
        string with = InputBox("Replace with:");
        string text = txtDoc.Text;
        int count = 0;
        for (int p = text.IndexOf(what, StringComparison.Ordinal); p >= 0;
             p = text.IndexOf(what, p + with.Length, StringComparison.Ordinal))
        {
            text = text.Substring(0, p) + with + text.Substring(p + what.Length);
            count++;
        }
        if (count > 0) txtDoc.Text = text;
        Status($"{count} replacement(s)");
    }

    static void mnuTimeDate_Click(RadEvent e) => txtDoc["SelText"] = DateTime.Now.ToString("HH:mm yyyy-MM-dd");

    static void mnuFont_Click(RadEvent e)
    {
        dlgFont["FontName"] = txtDoc["FontName"];
        dlgFont["FontSize"] = txtDoc["FontSize"];
        if (dlgFont.Call("ShowFont") != "OK") return;
        txtDoc["FontName"] = dlgFont["FontName"];
        txtDoc["FontSize"] = dlgFont["FontSize"];
        Status($"Font: {txtDoc["FontName"]} {txtDoc["FontSize"]} pt");
    }

    static void mnuWordCount_Click(RadEvent e)
    {
        string text = txtDoc.Text;
        int words = text.Split(new[] { ' ', '\t', '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries).Length;
        int lines = text.Length == 0 ? 0 : text.Count(ch => ch == '\n') + 1;
        int chars = text.Count(ch => ch != '\r' && ch != '\n');
        string msg = $"{words} words, {lines} lines, {chars} characters";
        Status(msg);
        MsgBox(msg);
    }

    static void mnuAbout_Click(RadEvent e) => MsgBox("Notepad - a RAD IDE example in C#\n(c) 2026 Musoftware - MIT License");
}

/// <summary>The Windows clipboard through user32 / kernel32 (no WinForms needed in the bridge program).</summary>
static class WinClipboard
{
    [DllImport("user32.dll", SetLastError = true)] static extern bool OpenClipboard(IntPtr owner);
    [DllImport("user32.dll")] static extern bool CloseClipboard();
    [DllImport("user32.dll")] static extern bool EmptyClipboard();
    [DllImport("user32.dll")] static extern IntPtr GetClipboardData(uint format);
    [DllImport("user32.dll")] static extern IntPtr SetClipboardData(uint format, IntPtr mem);
    [DllImport("kernel32.dll")] static extern IntPtr GlobalAlloc(uint flags, UIntPtr bytes);
    [DllImport("kernel32.dll")] static extern IntPtr GlobalLock(IntPtr mem);
    [DllImport("kernel32.dll")] static extern bool GlobalUnlock(IntPtr mem);
    const uint CF_UNICODETEXT = 13, GMEM_MOVEABLE = 2;

    public static void SetText(string text)
    {
        if (!OpenClipboard(IntPtr.Zero)) return;
        try
        {
            EmptyClipboard();
            byte[] bytes = Encoding.Unicode.GetBytes(text + "\0");
            IntPtr mem = GlobalAlloc(GMEM_MOVEABLE, (UIntPtr)bytes.Length);
            Marshal.Copy(bytes, 0, GlobalLock(mem), bytes.Length);
            GlobalUnlock(mem);
            SetClipboardData(CF_UNICODETEXT, mem);
        }
        finally { CloseClipboard(); }
    }

    public static string GetText()
    {
        if (!OpenClipboard(IntPtr.Zero)) return "";
        try
        {
            IntPtr h = GetClipboardData(CF_UNICODETEXT);
            if (h == IntPtr.Zero) return "";
            string s = Marshal.PtrToStringUni(GlobalLock(h)) ?? "";
            GlobalUnlock(h);
            return s;
        }
        finally { CloseClipboard(); }
    }
}
