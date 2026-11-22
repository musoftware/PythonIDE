// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Notepad - a text editor in Rust (RAD IDE GUI Bridge: module radgui; Build > Publish makes an exe).
//
// Shows: menus, OpenFileDialog / SaveFileDialog / FontDialog, std::fs with UTF-8, the Windows clipboard
// (user32 / kernel32 through extern "system" - no crates), Find / Find Next / Replace with SelStart /
// SelLength / SelText (characters, not bytes), a status bar, "discard changes?" questions.
use crate::radgui::*;
use std::cell::RefCell;
use std::fs;
use std::path::Path;

const MAX_TEXT: usize = 60000; // a GUI Bridge answer is one line of at most 64 KB

#[derive(Default)]
struct Doc {
    file_name: String, // "" = Untitled
    find_what: String,
    dirty: bool,
    loading: bool,
}

thread_local! {
    static DOC: RefCell<Doc> = RefCell::new(Doc::default());
}

fn with_doc<R>(f: impl FnOnce(&mut Doc) -> R) -> R {
    DOC.with(|d| f(&mut d.borrow_mut()))
}

fn base_name(path: &str) -> String {
    Path::new(path).file_name().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default()
}

fn update_title() {
    let (dirty, name) = with_doc(|d| (d.dirty, d.file_name.clone()));
    let name = if name.is_empty() { "Untitled".to_string() } else { base_name(&name) };
    set("frmMain", "Caption", format!("{}{} - Notepad", if dirty { "*" } else { "" }, name));
}

fn status(text: &str) {
    set("sbStatus", "Text", text);
}

fn set_doc(text: &str) {
    with_doc(|d| d.loading = true);
    set("txtDoc", "Text", text);
    with_doc(|d| d.loading = false);
}

fn confirm_discard() -> bool {
    !with_doc(|d| d.dirty)
        || input("The text has changed. Type YES to discard the changes (or Cancel to keep them):")
            .to_lowercase()
            .starts_with('y')
}

fn write_file(path: &str) -> bool {
    let text = get("txtDoc", "Text");
    if let Err(e) = fs::write(path, &text) {
        msgbox(format!("Cannot write {}:\n{}", path, e));
        return false;
    }
    with_doc(|d| {
        d.file_name = path.to_string();
        d.dirty = false;
    });
    update_title();
    status(&format!("Saved {} ({} bytes)", base_name(path), text.len()));
    true
}

fn open_file(path: &str) {
    let bytes = match fs::read(path) {
        Ok(b) => b,
        Err(e) => {
            msgbox(format!("Cannot open {}:\n{}", path, e));
            return;
        }
    };
    let cut = bytes.len() > MAX_TEXT;
    let text = String::from_utf8_lossy(&bytes[..bytes.len().min(MAX_TEXT)]).into_owned();
    let text = text.trim_start_matches('\u{feff}').replace("\r\n", "\n").replace('\n', "\r\n");
    set_doc(&text);
    with_doc(|d| {
        d.file_name = path.to_string();
        d.dirty = false;
    });
    update_title();
    status(&format!("Opened {}{}", base_name(path), if cut { " (only the first 60000 bytes)" } else { "" }));
}

/// byte offset of character number `chars` (SelStart counts characters)
fn byte_at(s: &str, chars: usize) -> usize {
    s.char_indices().nth(chars).map(|(i, _)| i).unwrap_or(s.len())
}

fn find_next() -> bool {
    let what = with_doc(|d| d.find_what.clone());
    if what.is_empty() {
        return false;
    }
    let text = get("txtDoc", "Text");
    let from = (get_num("txtDoc", "SelStart") + get_num("txtDoc", "SelLength")) as usize;
    let (lower, needle) = (text.to_lowercase(), what.to_lowercase());
    let start = byte_at(&text, from).min(lower.len());
    let hit = lower[start..].find(&needle).map(|i| i + start).or_else(|| lower.find(&needle)); // wrap around
    match hit {
        Some(i) => {
            let ch = text[..i].chars().count();
            set("txtDoc", "SelStart", ch);
            set("txtDoc", "SelLength", what.chars().count());
            call("txtDoc", "SetFocus", &[]);
            status(&format!("Found \"{}\" at character {}", what, ch + 1));
            true
        }
        None => {
            status(&format!("Cannot find \"{}\"", what));
            false
        }
    }
}

// ------------------------------------------------------------------ clipboard (Win32)
#[cfg(windows)]
mod clip {
    use std::ffi::c_void;
    #[link(name = "user32")]
    extern "system" {
        fn OpenClipboard(owner: *mut c_void) -> i32;
        fn CloseClipboard() -> i32;
        fn EmptyClipboard() -> i32;
        fn GetClipboardData(format: u32) -> *mut c_void;
        fn SetClipboardData(format: u32, mem: *mut c_void) -> *mut c_void;
    }
    #[link(name = "kernel32")]
    extern "system" {
        fn GlobalAlloc(flags: u32, bytes: usize) -> *mut c_void;
        fn GlobalLock(mem: *mut c_void) -> *mut c_void;
        fn GlobalUnlock(mem: *mut c_void) -> i32;
    }
    const CF_UNICODETEXT: u32 = 13;
    const GMEM_MOVEABLE: u32 = 2;

    pub fn put(text: &str) {
        let wide: Vec<u16> = text.encode_utf16().chain(std::iter::once(0)).collect();
        unsafe {
            if OpenClipboard(std::ptr::null_mut()) == 0 {
                return;
            }
            EmptyClipboard();
            let mem = GlobalAlloc(GMEM_MOVEABLE, wide.len() * 2);
            if !mem.is_null() {
                std::ptr::copy_nonoverlapping(wide.as_ptr(), GlobalLock(mem) as *mut u16, wide.len());
                GlobalUnlock(mem);
                SetClipboardData(CF_UNICODETEXT, mem);
            }
            CloseClipboard();
        }
    }

    pub fn get() -> String {
        unsafe {
            if OpenClipboard(std::ptr::null_mut()) == 0 {
                return String::new();
            }
            let h = GetClipboardData(CF_UNICODETEXT);
            let mut out = String::new();
            if !h.is_null() {
                let p = GlobalLock(h) as *const u16;
                let mut n = 0;
                while *p.add(n) != 0 {
                    n += 1;
                }
                out = String::from_utf16_lossy(std::slice::from_raw_parts(p, n));
                GlobalUnlock(h);
            }
            CloseClipboard();
            out
        }
    }
}

#[cfg(not(windows))]
mod clip {
    pub fn put(_: &str) {}
    pub fn get() -> String { String::new() }
}

// ------------------------------------------------------------------ events
pub fn frmMain_Load() {
    update_title();
    status("Ready - File > Open to load a text file");
}

pub fn txtDoc_TextChanged() {
    let changed = with_doc(|d| {
        if d.loading || d.dirty {
            return false;
        }
        d.dirty = true;
        true
    });
    if changed {
        update_title();
    }
}

pub fn mnuNew_Click() {
    if !confirm_discard() {
        return;
    }
    set_doc("");
    with_doc(|d| {
        d.file_name.clear();
        d.dirty = false;
    });
    update_title();
    status("New document");
}

pub fn mnuOpen_Click() {
    if !confirm_discard() || call("dlgOpen", "ShowOpen", &[]) != "OK" {
        return;
    }
    let path = get("dlgOpen", "FileName");
    if !path.is_empty() {
        open_file(&path);
    }
}

pub fn mnuSaveAs_Click() {
    let name = with_doc(|d| d.file_name.clone());
    set("dlgSave", "FileName", if name.is_empty() { "Untitled.txt".to_string() } else { base_name(&name) });
    if call("dlgSave", "ShowSave", &[]) != "OK" {
        return;
    }
    let path = get("dlgSave", "FileName");
    if !path.is_empty() {
        write_file(&path);
    }
}

pub fn mnuSave_Click() {
    let name = with_doc(|d| d.file_name.clone());
    if name.is_empty() {
        mnuSaveAs_Click();
    } else {
        write_file(&name);
    }
}

pub fn mnuExit_Click() {
    if confirm_discard() {
        end();
    }
}

pub fn mnuCut_Click() {
    let sel = get("txtDoc", "SelText");
    if sel.is_empty() {
        return;
    }
    clip::put(&sel);
    set("txtDoc", "SelText", "");
    status("Cut to the clipboard");
}

pub fn mnuCopy_Click() {
    let sel = get("txtDoc", "SelText");
    if sel.is_empty() {
        status("Nothing selected");
        return;
    }
    clip::put(&sel);
    status("Copied to the clipboard");
}

pub fn mnuPaste_Click() {
    let text = clip::get();
    if text.is_empty() {
        status("The clipboard has no text");
        return;
    }
    set("txtDoc", "SelText", &text);
    status("Pasted");
}

pub fn mnuSelectAll_Click() {
    set("txtDoc", "SelStart", 0);
    set("txtDoc", "SelLength", get("txtDoc", "Text").chars().count());
    call("txtDoc", "SetFocus", &[]);
}

pub fn mnuFind_Click() {
    let what = input("Find what:");
    if what.is_empty() {
        return;
    }
    with_doc(|d| d.find_what = what);
    set("txtDoc", "SelLength", 0);
    find_next();
}

pub fn mnuFindNext_Click() {
    if with_doc(|d| d.find_what.is_empty()) {
        mnuFind_Click();
    } else {
        find_next();
    }
}

pub fn mnuReplace_Click() {
    let what = input("Replace what:");
    if what.is_empty() {
        return;
    }
    let with = input("Replace with:");
    let text = get("txtDoc", "Text");
    let count = text.matches(&what).count();
    if count > 0 {
        set("txtDoc", "Text", text.replace(&what, &with));
    }
    status(&format!("{} replacement(s)", count));
}

pub fn mnuTimeDate_Click() {
    // seconds since 1970 -> UTC date and time, without a date crate
    let secs = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let (days, rem) = ((secs / 86400) as i64, secs % 86400);
    let (z, era) = (days + 719468, (days + 719468).div_euclid(146097));
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = yoe + era * 400 + if m <= 2 { 1 } else { 0 };
    set("txtDoc", "SelText", format!("{:02}:{:02} {}-{:02}-{:02} UTC", rem / 3600, rem % 3600 / 60, y, m, d));
}

pub fn mnuFont_Click() {
    set("dlgFont", "FontName", get("txtDoc", "FontName"));
    set("dlgFont", "FontSize", get("txtDoc", "FontSize"));
    if call("dlgFont", "ShowFont", &[]) != "OK" {
        return;
    }
    set("txtDoc", "FontName", get("dlgFont", "FontName"));
    set("txtDoc", "FontSize", get("dlgFont", "FontSize"));
    status(&format!("Font: {} {} pt", get("txtDoc", "FontName"), get("txtDoc", "FontSize")));
}

pub fn mnuWordCount_Click() {
    let text = get("txtDoc", "Text");
    let lines = if text.is_empty() { 0 } else { text.matches('\n').count() + 1 };
    let chars = text.chars().filter(|c| *c != '\r' && *c != '\n').count();
    let msg = format!("{} words, {} lines, {} characters", text.split_whitespace().count(), lines, chars);
    status(&msg);
    msgbox(&msg);
}

pub fn mnuAbout_Click() {
    msgbox("Notepad - a RAD IDE example in Rust\n(c) 2026 Musoftware - MIT License");
}
