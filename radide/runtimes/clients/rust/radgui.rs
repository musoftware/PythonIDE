//! RAD IDE GUI Bridge - Rust client (copied into the project when it runs).
//!
//! The IDE draws the forms; this module talks to it over stdin/stdout
//! (docs/CONTRACTS.md section 1) and to RAD Hub over TCP for `radcall`.
//!
//! ```ignore
//! use crate::radgui::*;
//! set("lblOut", "Caption", "Hello");          // any Display value
//! let s = get("txtA", "Text");                // String
//! call("lstLog", "AddItem", &["line"]);       // method call, returns String
//! msgbox("Hi"); let name = input("Name?"); show("Form2"); end();
//! let x = num(&s);                            // text -> f64 (0 if not a number)
//! let r = radcall("Helpers.add", &[2.into(), 3.into()]);   // Result<Json, String>
//! ```
#![allow(dead_code)]

use std::cell::RefCell;
use std::collections::BTreeMap;
use std::fmt;
use std::io::{self, BufRead, BufReader, Write};
use std::net::TcpStream;

// ------------------------------------------------------------------ protocol
thread_local! {
    static ARGS: RefCell<String> = RefCell::new(String::new());
    static HUB: RefCell<Option<(TcpStream, BufReader<TcpStream>, u64)>> = RefCell::new(None);
}

fn send(line: &str) {
    let clean: String = line.chars().map(|c| if c == '\n' || c == '\r' { ' ' } else { c }).collect();
    let out = io::stdout();
    let mut out = out.lock();
    let _ = writeln!(out, "{}", clean);
    let _ = out.flush();
}

fn read_line() -> Option<String> {
    // under the IDE debugger (RAD_BRIDGE_DEBUG) gdb halts the process to change breakpoints, which aborts the
    // pending read of stdin on Windows: read again (only the end of stdin ends the program)
    let debugged = std::env::var_os("RAD_BRIDGE_DEBUG").is_some();
    let mut failed = 0;
    loop {
        let mut s = String::new();
        match io::stdin().lock().read_line(&mut s) {
            Ok(0) => return None,
            Err(_) if debugged && failed < 1000 => failed += 1,
            Err(_) => return None,
            Ok(_) => return Some(s.trim_end_matches(['\r', '\n']).to_string()),
        }
    }
}

/// Started without RAD IDE (double-clicked): there is nobody on stdin to draw the forms - say so.
fn started_alone() -> bool {
    use std::io::IsTerminal;
    if !io::stdin().is_terminal() || std::env::var_os("RAD_HANDLERS").is_some() {
        return false;
    }
    println!("This program is a RAD IDE GUI Bridge client: its forms are drawn by RAD IDE.");
    println!("Run it from the IDE (F5), or make a standalone exe with the forms inside:");
    println!("Build > Build Native Exe (or Build > Publish).");
    println!();
    println!("Press Enter to close.");
    let _ = read_line();
    true
}

/// Used by the generated main program: next "<obj>_<event>" key, None = quit.
pub fn next_event() -> Option<String> {
    thread_local!(static FIRST: std::cell::Cell<bool> = std::cell::Cell::new(true));
    if FIRST.with(|f| f.replace(false)) && started_alone() {
        return None;
    }
    let line = read_line()?;
    if line.starts_with("QUIT") {
        return None;
    }
    let rest = match line.strip_prefix("EVENT ") {
        Some(r) => r,
        None => return Some(String::new()),
    };
    let mut parts = rest.splitn(3, ' ');
    let obj = parts.next().unwrap_or("");
    let ev = parts.next().unwrap_or("");
    let args = parts.next().unwrap_or("").to_string();
    ARGS.with(|a| *a.borrow_mut() = args);
    Some(format!("{}_{}", obj, ev))
}

pub fn done() {
    send("DONE");
}

/// Event arguments of mouse/key events: "X Y Button KeyCode KeyChar".
pub fn event_args() -> String {
    ARGS.with(|a| a.borrow().clone())
}

/// One event argument (0-based): 0=X 1=Y 2=Button 3=KeyCode 4=KeyChar.
pub fn event_arg(i: usize) -> String {
    event_args().split_whitespace().nth(i).unwrap_or("").to_string()
}

// ------------------------------------------------------------------ GUI
/// A value for an "ESC" command: \\ newline CR escaped, so multi-line text survives the line protocol.
fn esc(s: &str) -> String {
    s.replace('\\', "\\\\").replace('\n', "\\n").replace('\r', "\\r")
}

/// The answer to an "ESC" command, unescaped.
fn unesc(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut it = s.chars().peekable();
    while let Some(c) = it.next() {
        if c == '\\' {
            let real = match it.peek() {
                Some('n') => Some('\n'),
                Some('r') => Some('\r'),
                Some('\\') => Some('\\'),
                _ => None,
            };
            if let Some(r) = real {
                out.push(r);
                it.next();
                continue;
            }
        }
        out.push(c);
    }
    out
}

/// Send an ESC command and read its (escaped) answer.
fn ask(line: &str) -> String {
    send(line);
    unesc(&read_line().unwrap_or_default())
}

pub fn set(obj: &str, prop: &str, value: impl fmt::Display) {
    send(&format!("ESC SET {} {} {}", obj, prop, esc(&value.to_string())));
}

pub fn get(obj: &str, prop: &str) -> String {
    ask(&format!("ESC GET {} {}", obj, prop))
}

pub fn get_num(obj: &str, prop: &str) -> f64 {
    num(&get(obj, prop))
}

pub fn call(obj: &str, method: &str, args: &[&str]) -> String {
    if args.is_empty() {
        ask(&format!("ESC CALL {} {}", obj, method))
    } else {
        let a: Vec<String> = args.iter().map(|x| esc(x)).collect();
        ask(&format!("ESC CALL {} {} {}", obj, method, a.join("\t")))
    }
}

pub fn msgbox(text: impl fmt::Display) {
    ask(&format!("ESC MSGBOX {}", esc(&text.to_string())));
}

pub fn input(prompt: &str) -> String {
    ask(&format!("ESC INPUT {}", esc(prompt)))
}

pub fn show(form: &str) {
    send(&format!("SHOW {}", form));
}

pub fn hide(form: &str) {
    send(&format!("HIDE {}", form));
}

/// Quit the program.
pub fn end() {
    send("END");
}

/// A line in the IDE's Output window (println! works too).
pub fn print(text: impl fmt::Display) {
    send(&text.to_string());
}

pub fn num(text: &str) -> f64 {
    text.trim().parse::<f64>().unwrap_or(0.0)
}

pub fn str(x: f64) -> String {
    format!("{}", x)
}

// ------------------------------------------------------------------ JSON
#[derive(Clone, Debug, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<Json>),
    Obj(BTreeMap<String, Json>),
}

impl Json {
    pub fn as_f64(&self) -> f64 {
        match self {
            Json::Num(n) => *n,
            Json::Bool(b) => *b as i32 as f64,
            Json::Str(s) => num(s),
            _ => 0.0,
        }
    }
    pub fn as_str(&self) -> String {
        match self {
            Json::Str(s) => s.clone(),
            Json::Null => String::new(),
            other => other.to_string(),
        }
    }
    pub fn as_bool(&self) -> bool {
        match self {
            Json::Bool(b) => *b,
            Json::Num(n) => *n != 0.0,
            Json::Str(s) => !s.is_empty(),
            Json::Null => false,
            _ => true,
        }
    }
    pub fn get(&self, key: &str) -> Json {
        match self {
            Json::Obj(m) => m.get(key).cloned().unwrap_or(Json::Null),
            _ => Json::Null,
        }
    }
    pub fn at(&self, i: usize) -> Json {
        match self {
            Json::Arr(v) => v.get(i).cloned().unwrap_or(Json::Null),
            _ => Json::Null,
        }
    }
    pub fn parse(text: &str) -> Result<Json, String> {
        let chars: Vec<char> = text.chars().collect();
        let mut p = Parser { s: &chars, i: 0 };
        let v = p.value()?;
        p.ws();
        if p.i != chars.len() {
            return Err(format!("unexpected text at {}", p.i));
        }
        Ok(v)
    }
}

fn quote(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
}

impl fmt::Display for Json {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let mut s = String::new();
        match self {
            Json::Null => s.push_str("null"),
            Json::Bool(b) => s.push_str(if *b { "true" } else { "false" }),
            Json::Num(n) => {
                if n.is_finite() {
                    s.push_str(&format!("{}", n))
                } else {
                    s.push_str("null")
                }
            }
            Json::Str(t) => quote(t, &mut s),
            Json::Arr(v) => {
                s.push('[');
                for (i, x) in v.iter().enumerate() {
                    if i > 0 {
                        s.push_str(", ");
                    }
                    s.push_str(&x.to_string());
                }
                s.push(']');
            }
            Json::Obj(m) => {
                s.push('{');
                for (i, (k, x)) in m.iter().enumerate() {
                    if i > 0 {
                        s.push_str(", ");
                    }
                    quote(k, &mut s);
                    s.push_str(": ");
                    s.push_str(&x.to_string());
                }
                s.push('}');
            }
        }
        f.write_str(&s)
    }
}

impl From<f64> for Json { fn from(x: f64) -> Self { Json::Num(x) } }
impl From<i32> for Json { fn from(x: i32) -> Self { Json::Num(x as f64) } }
impl From<i64> for Json { fn from(x: i64) -> Self { Json::Num(x as f64) } }
impl From<bool> for Json { fn from(x: bool) -> Self { Json::Bool(x) } }
impl From<&str> for Json { fn from(x: &str) -> Self { Json::Str(x.to_string()) } }
impl From<String> for Json { fn from(x: String) -> Self { Json::Str(x) } }
impl From<()> for Json { fn from(_: ()) -> Self { Json::Null } }
macro_rules! rad_json_from_num {
    ($($t:ty),*) => { $(impl From<$t> for Json { fn from(x: $t) -> Self { Json::Num(x as f64) } })* };
}
rad_json_from_num!(f32, i8, i16, isize, u8, u16, u32, u64, usize);
impl From<&String> for Json { fn from(x: &String) -> Self { Json::Str(x.clone()) } }
impl From<&Json> for Json { fn from(x: &Json) -> Self { x.clone() } }
impl<T: Into<Json>> From<Option<T>> for Json {
    fn from(v: Option<T>) -> Self { v.map(Into::into).unwrap_or(Json::Null) }
}
impl Json {
    /// Elements of an array (empty for other values).
    pub fn as_vec(&self) -> Vec<Json> {
        match self {
            Json::Arr(v) => v.clone(),
            _ => Vec::new(),
        }
    }
    pub fn as_i64(&self) -> i64 { self.as_f64() as i64 }
    pub fn is_null(&self) -> bool { *self == Json::Null }
}
impl<T: Into<Json>> From<Vec<T>> for Json {
    fn from(v: Vec<T>) -> Self { Json::Arr(v.into_iter().map(Into::into).collect()) }
}

struct Parser<'a> {
    s: &'a [char],
    i: usize,
}

impl<'a> Parser<'a> {
    fn ws(&mut self) {
        while self.i < self.s.len() && self.s[self.i].is_whitespace() {
            self.i += 1;
        }
    }
    fn peek(&self) -> char {
        *self.s.get(self.i).unwrap_or(&'\0')
    }
    fn lit(&mut self, word: &str, v: Json) -> Result<Json, String> {
        for c in word.chars() {
            if self.peek() != c {
                return Err(format!("bad literal at {}", self.i));
            }
            self.i += 1;
        }
        Ok(v)
    }
    fn value(&mut self) -> Result<Json, String> {
        self.ws();
        match self.peek() {
            '{' => {
                self.i += 1;
                let mut m = BTreeMap::new();
                self.ws();
                if self.peek() == '}' {
                    self.i += 1;
                    return Ok(Json::Obj(m));
                }
                loop {
                    self.ws();
                    let k = match self.value()? {
                        Json::Str(k) => k,
                        _ => return Err("object key must be a string".into()),
                    };
                    self.ws();
                    if self.peek() != ':' {
                        return Err(format!("':' expected at {}", self.i));
                    }
                    self.i += 1;
                    let v = self.value()?;
                    m.insert(k, v);
                    self.ws();
                    match self.peek() {
                        ',' => self.i += 1,
                        '}' => { self.i += 1; return Ok(Json::Obj(m)); }
                        _ => return Err(format!("',' or '}}' expected at {}", self.i)),
                    }
                }
            }
            '[' => {
                self.i += 1;
                let mut v = Vec::new();
                self.ws();
                if self.peek() == ']' {
                    self.i += 1;
                    return Ok(Json::Arr(v));
                }
                loop {
                    v.push(self.value()?);
                    self.ws();
                    match self.peek() {
                        ',' => self.i += 1,
                        ']' => { self.i += 1; return Ok(Json::Arr(v)); }
                        _ => return Err(format!("',' or ']' expected at {}", self.i)),
                    }
                }
            }
            '"' => {
                self.i += 1;
                let mut out = String::new();
                loop {
                    let c = self.peek();
                    self.i += 1;
                    match c {
                        '\0' => return Err("unterminated string".into()),
                        '"' => return Ok(Json::Str(out)),
                        '\\' => {
                            let e = self.peek();
                            self.i += 1;
                            match e {
                                'n' => out.push('\n'),
                                't' => out.push('\t'),
                                'r' => out.push('\r'),
                                'b' => out.push('\u{8}'),
                                'f' => out.push('\u{c}'),
                                'u' => {
                                    let mut cp = self.hex4()?;
                                    if (0xD800..0xDC00).contains(&cp) && self.peek() == '\\' {
                                        self.i += 2;
                                        let lo = self.hex4()?;
                                        cp = 0x10000 + ((cp - 0xD800) << 10) + (lo.wrapping_sub(0xDC00));
                                    }
                                    out.push(char::from_u32(cp).unwrap_or('\u{fffd}'));
                                }
                                other => out.push(other),
                            }
                        }
                        c => out.push(c),
                    }
                }
            }
            't' => self.lit("true", Json::Bool(true)),
            'f' => self.lit("false", Json::Bool(false)),
            'n' => self.lit("null", Json::Null),
            _ => {
                let start = self.i;
                while self.i < self.s.len() && "+-0123456789.eE".contains(self.s[self.i]) {
                    self.i += 1;
                }
                let t: String = self.s[start..self.i].iter().collect();
                t.parse::<f64>().map(Json::Num).map_err(|_| format!("bad value at {}", start))
            }
        }
    }
    fn hex4(&mut self) -> Result<u32, String> {
        let t: String = self.s.get(self.i..self.i + 4).ok_or("bad \\u escape")?.iter().collect();
        self.i += 4;
        u32::from_str_radix(&t, 16).map_err(|_| "bad \\u escape".to_string())
    }
}

// ------------------------------------------------------------------ RAD Hub
/// Call a function of another module (any language) through RAD Hub:
/// `radcall("Helpers.add", &[2.into(), 3.into()])`.
pub fn radcall(name: &str, args: &[Json]) -> Result<Json, String> {
    HUB.with(|h| {
        let mut h = h.borrow_mut();
        if h.is_none() {
            let addr = std::env::var("RAD_HUB").map_err(|_| "RAD_HUB is not set (run the program from RAD IDE)")?;
            let s = TcpStream::connect(addr.as_str())
                .map_err(|e| format!("cannot connect to RAD Hub at {}: {}", addr, e))?;
            let r = BufReader::new(s.try_clone().map_err(|e| e.to_string())?);
            *h = Some((s, r, 0));
        }
        let result = hub_request(h.as_mut().unwrap(), name, args);
        if let Err(HubError::Lost(_)) = &result {
            *h = None;
        }
        result.map_err(|e| match e { HubError::Lost(m) | HubError::Call(m) => m })
    })
}

enum HubError {
    Lost(String),
    Call(String),
}

fn hub_request(c: &mut (TcpStream, BufReader<TcpStream>, u64), name: &str, args: &[Json]) -> Result<Json, HubError> {
    let (s, r, id) = c;
    *id += 1;
    let mut req = BTreeMap::new();
    req.insert("id".to_string(), Json::Num(*id as f64));
    req.insert("call".to_string(), Json::Str(name.to_string()));
    req.insert("args".to_string(), Json::Arr(args.to_vec()));
    let line = format!("{}
", Json::Obj(req));
    s.write_all(line.as_bytes()).map_err(|e| HubError::Lost(format!("RAD Hub connection lost: {}", e)))?;
    loop {
        let mut reply = String::new();
        match r.read_line(&mut reply) {
            Ok(0) | Err(_) => return Err(HubError::Lost("RAD Hub connection lost".into())),
            Ok(_) => {}
        }
        let v = Json::parse(reply.trim()).map_err(HubError::Call)?;
        if v.get("id").as_f64() as u64 != *id {
            continue;
        }
        return match v.get("error") {
            Json::Null => Ok(v.get("result")),
            e => Err(HubError::Call(e.as_str())),
        };
    }
}

// ------------------------------------------------------------------ worker
/// Result types a worker function may return.
pub trait Reply {
    fn reply(self) -> Result<Json, String>;
}
impl Reply for Json { fn reply(self) -> Result<Json, String> { Ok(self) } }
impl Reply for f64 { fn reply(self) -> Result<Json, String> { Ok(self.into()) } }
impl Reply for i64 { fn reply(self) -> Result<Json, String> { Ok(self.into()) } }
impl Reply for i32 { fn reply(self) -> Result<Json, String> { Ok(self.into()) } }
impl Reply for bool { fn reply(self) -> Result<Json, String> { Ok(self.into()) } }
impl Reply for String { fn reply(self) -> Result<Json, String> { Ok(self.into()) } }
impl Reply for &str { fn reply(self) -> Result<Json, String> { Ok(self.into()) } }
impl Reply for () { fn reply(self) -> Result<Json, String> { Ok(Json::Null) } }
macro_rules! rad_reply_into {
    ($($t:ty),*) => { $(impl Reply for $t { fn reply(self) -> Result<Json, String> { Ok(self.into()) } })* };
}
rad_reply_into!(f32, i8, i16, isize, u8, u16, u32, u64, usize);
impl<T: Into<Json>> Reply for Vec<T> { fn reply(self) -> Result<Json, String> { Ok(self.into()) } }
impl<T: Into<Json>> Reply for Option<T> { fn reply(self) -> Result<Json, String> { Ok(self.into()) } }
impl<T: Into<Json>, E: fmt::Display> Reply for Result<T, E> {
    fn reply(self) -> Result<Json, String> { self.map(Into::into).map_err(|e| e.to_string()) }
}

/// Used by the generated worker: serve {"id","func","args"} lines from stdin.
pub fn worker_main(dispatch: fn(&str, &[Json]) -> Option<Result<Json, String>>) {
    while let Some(line) = read_line() {
        if line.trim().is_empty() {
            continue;
        }
        // the hub expects every reply line to start with {"id"
        let (id, reply) = match Json::parse(&line) {
            Err(e) => (Json::Null, Err(format!("bad request: {}", e))),
            Ok(req) => {
                let args = match req.get("args") {
                    Json::Arr(v) => v,
                    _ => Vec::new(),
                };
                let func = req.get("func").as_str();
                let called = std::panic::catch_unwind(|| dispatch(&func, &args));
                let called = called.unwrap_or_else(|_| Some(Err(format!("{} panicked", func))));
                (req.get("id"), called.unwrap_or_else(|| Err(format!("unknown function '{}'", func))))
            }
        };
        let text = match reply {
            Ok(v) => format!("{{\"id\": {}, \"result\": {}}}", id, v),
            Err(e) => format!("{{\"id\": {}, \"error\": {}}}", id, Json::Str(e)),
        };
        let o = io::stdout();
        let mut o = o.lock();
        let _ = writeln!(o, "{}", text);
        let _ = o.flush();
    }
}
