// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Notepad - a text editor in Java (RAD IDE GUI Bridge: the IDE draws frmMain, this class handles its events;
// Build > Publish makes a native Swing exe with a trimmed Java runtime, no Python).
//
// Shows: menus, OpenFileDialog / SaveFileDialog / FontDialog, java.nio.file.Files with UTF-8, the system
// clipboard (java.awt.Toolkit), Find / Find Next / Replace with SelStart / SelLength / SelText, a status bar,
// "discard changes?" questions and IOException handling.
import java.awt.Toolkit;
import java.awt.datatransfer.DataFlavor;
import java.awt.datatransfer.StringSelection;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class frmMain extends frmMainDesigner {
    static final int MAX_TEXT = 60000;      // a GUI Bridge answer is one line of at most 64 KB
    static String fileName = "";            // "" = Untitled
    static String findWhat = "";
    static boolean dirty, loading;

    // ------------------------------------------------------------------ helpers
    static void updateTitle() {
        String name = fileName.isEmpty() ? "Untitled" : Paths.get(fileName).getFileName().toString();
        me.setCaption((dirty ? "*" : "") + name + " - Notepad");
    }

    static void status(String text) { sbStatus.setText(text); }

    static void setDoc(String text) {
        loading = true;
        txtDoc.setText(text);
        loading = false;
    }

    static boolean confirmDiscard() {
        if (!dirty) return true;
        String a = input("The text has changed. Type YES to discard the changes (or Cancel to keep them):");
        return a.toLowerCase().startsWith("y");
    }

    static boolean writeFile(String path) {
        try {
            String text = txtDoc.getText();
            Files.write(Paths.get(path), text.getBytes(StandardCharsets.UTF_8));
            fileName = path;
            dirty = false;
            updateTitle();
            status("Saved " + Paths.get(path).getFileName() + " (" + text.length() + " characters)");
            return true;
        } catch (IOException ex) {
            msgbox("Cannot write " + path + ":\n" + ex.getMessage());
            return false;
        }
    }

    static void openFile(String path) {
        try {
            String text = new String(Files.readAllBytes(Paths.get(path)), StandardCharsets.UTF_8);
            if (text.startsWith(String.valueOf((char) 0xFEFF))) text = text.substring(1);                    // UTF-8 BOM
            boolean cut = text.length() > MAX_TEXT;
            if (cut) text = text.substring(0, MAX_TEXT);
            setDoc(text.replace("\r\n", "\n").replace("\n", "\r\n"));                 // an edit box needs CR LF
            fileName = path;
            dirty = false;
            updateTitle();
            status("Opened " + Paths.get(path).getFileName() + (cut ? " (only the first " + MAX_TEXT + " characters)" : ""));
        } catch (IOException ex) {
            msgbox("Cannot open " + path + ":\n" + ex.getMessage());
        }
    }

    static boolean findNext() {
        if (findWhat.isEmpty()) return false;
        String text = txtDoc.getText();
        int from = Math.min(text.length(), toInt(txtDoc.get("SelStart")) + toInt(txtDoc.get("SelLength")));
        int hit = text.toLowerCase().indexOf(findWhat.toLowerCase(), from);
        if (hit < 0) hit = text.toLowerCase().indexOf(findWhat.toLowerCase());          // wrap around
        if (hit < 0) {
            status("Cannot find \"" + findWhat + "\"");
            return false;
        }
        txtDoc.set("SelStart", hit);
        txtDoc.set("SelLength", findWhat.length());
        txtDoc.setFocus();
        status("Found \"" + findWhat + "\" at character " + (hit + 1));
        return true;
    }

    static void clipboardPut(String s) {
        Toolkit.getDefaultToolkit().getSystemClipboard().setContents(new StringSelection(s), null);
    }

    static String clipboardGet() {
        try {
            return (String) Toolkit.getDefaultToolkit().getSystemClipboard().getData(DataFlavor.stringFlavor);
        } catch (Exception ex) {        // no text on the clipboard
            return "";
        }
    }

    // ------------------------------------------------------------------ events
    static void frmMain_Load(RadEvent e) {
        updateTitle();
        status("Ready - File > Open to load a text file");
    }

    static void txtDoc_TextChanged(RadEvent e) {
        if (loading || dirty) return;
        dirty = true;
        updateTitle();
    }

    static void mnuNew_Click(RadEvent e) {
        if (!confirmDiscard()) return;
        setDoc("");
        fileName = "";
        dirty = false;
        updateTitle();
        status("New document");
    }

    static void mnuOpen_Click(RadEvent e) {
        if (!confirmDiscard()) return;
        if (!"OK".equals(dlgOpen.call("ShowOpen"))) return;
        String path = dlgOpen.get("FileName");
        if (!path.isEmpty()) openFile(path);
    }

    static void mnuSaveAs_Click(RadEvent e) {
        dlgSave.set("FileName", fileName.isEmpty() ? "Untitled.txt" : Paths.get(fileName).getFileName().toString());
        if (!"OK".equals(dlgSave.call("ShowSave"))) return;
        String path = dlgSave.get("FileName");
        if (!path.isEmpty()) writeFile(path);
    }

    static void mnuSave_Click(RadEvent e) {
        if (fileName.isEmpty()) mnuSaveAs_Click(e);
        else writeFile(fileName);
    }

    static void mnuExit_Click(RadEvent e) {
        if (confirmDiscard()) end();
    }

    static void mnuCut_Click(RadEvent e) {
        String sel = txtDoc.get("SelText");
        if (sel.isEmpty()) return;
        clipboardPut(sel);
        txtDoc.set("SelText", "");
        status("Cut to the clipboard");
    }

    static void mnuCopy_Click(RadEvent e) {
        String sel = txtDoc.get("SelText");
        if (sel.isEmpty()) { status("Nothing selected"); return; }
        clipboardPut(sel);
        status("Copied to the clipboard");
    }

    static void mnuPaste_Click(RadEvent e) {
        String clip = clipboardGet();
        if (clip.isEmpty()) { status("The clipboard has no text"); return; }
        txtDoc.set("SelText", clip);
        status("Pasted");
    }

    static void mnuSelectAll_Click(RadEvent e) {
        txtDoc.set("SelStart", 0);
        txtDoc.set("SelLength", txtDoc.getText().length());
        txtDoc.setFocus();
    }

    static void mnuFind_Click(RadEvent e) {
        String w = input("Find what:");
        if (w.isEmpty()) return;
        findWhat = w;
        txtDoc.set("SelLength", 0);
        findNext();
    }

    static void mnuFindNext_Click(RadEvent e) {
        if (findWhat.isEmpty()) mnuFind_Click(e);
        else findNext();
    }

    static void mnuReplace_Click(RadEvent e) {
        String what = input("Replace what:");
        if (what.isEmpty()) return;
        String with = input("Replace with:");
        String text = txtDoc.getText();
        int count = (text.length() - text.replace(what, "").length()) / what.length();
        if (count > 0) txtDoc.setText(text.replace(what, with));
        status(count + " replacement(s)");
    }

    static void mnuTimeDate_Click(RadEvent e) {
        txtDoc.set("SelText", LocalDateTime.now().format(DateTimeFormatter.ofPattern("HH:mm yyyy-MM-dd")));
    }

    static void mnuFont_Click(RadEvent e) {
        dlgFont.set("FontName", txtDoc.get("FontName"));
        dlgFont.set("FontSize", txtDoc.get("FontSize"));
        if (!"OK".equals(dlgFont.call("ShowFont"))) return;
        txtDoc.set("FontName", dlgFont.get("FontName"));
        txtDoc.set("FontSize", dlgFont.get("FontSize"));
        status("Font: " + txtDoc.get("FontName") + " " + txtDoc.get("FontSize") + " pt");
    }

    static void mnuWordCount_Click(RadEvent e) {
        String text = txtDoc.getText();
        String trimmed = text.trim();
        int words = trimmed.isEmpty() ? 0 : trimmed.split("\\s+").length;
        int lines = text.isEmpty() ? 0 : text.split("\n", -1).length;
        int chars = text.replace("\r", "").replace("\n", "").codePointCount(0, text.replace("\r", "").replace("\n", "").length());
        String msg = words + " words, " + lines + " lines, " + chars + " characters";
        status(msg);
        msgbox(msg);
    }

    static void mnuAbout_Click(RadEvent e) {
        msgbox("Notepad - a RAD IDE example in Java\n(c) 2026 Musoftware - MIT License");
    }
}
