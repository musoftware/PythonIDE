// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
//! WordStats - a Rust console tool (a plain cargo project): lines / words / characters of text files and the
//! most frequent words.
//!
//!     wordstats [--top N] [--out report.txt] file1.txt [file2.txt ...]
//!
//! Without files it reads sample.txt (F5 / Ctrl+F5 in the IDE run it in the project folder).
//! Exit codes: 0 OK, 1 wrong arguments, 2 a file could not be read, 3 the report could not be written.
//! Shows: File > New Project > Rust (Cargo) > Console App, std::env::args, HashMap, sorting, Result and `?`,
//! unit tests (Test Explorer / cargo test).

use std::collections::HashMap;
use std::fs;
use std::io::{self, Write};
use std::process::ExitCode;

#[derive(Default, Debug, PartialEq)]
struct Totals {
    lines: usize,
    words: usize,
    chars: usize,
}

/// Count one text; the words go into `freq`.
fn count_text(text: &str, freq: &mut HashMap<String, usize>) -> Totals {
    let mut t = Totals::default();
    for line in text.lines() {
        t.lines += 1;
        t.chars += line.chars().count();
        for w in line.split(|c: char| !(c.is_alphanumeric() || c == '\'')).filter(|w| !w.is_empty()) {
            *freq.entry(w.to_lowercase()).or_insert(0) += 1;
            t.words += 1;
        }
    }
    t
}

struct Options {
    top: usize,
    out: Option<String>,
    files: Vec<String>,
}

fn parse_args(args: &[String]) -> Result<Options, String> {
    let mut o = Options { top: 10, out: None, files: vec![] };
    let mut it = args.iter();
    while let Some(a) = it.next() {
        match a.as_str() {
            "--top" | "-top" => {
                o.top = it.next().and_then(|v| v.parse().ok()).filter(|&n| n > 0)
                    .ok_or("--top needs a positive number")?;
            }
            "--out" | "-out" => o.out = Some(it.next().ok_or("--out needs a file name")?.clone()),
            s if s.starts_with('-') => return Err(format!("unknown option {}", s)),
            s => o.files.push(s.to_string()),
        }
    }
    if o.files.is_empty() {
        o.files.push("sample.txt".into());
    }
    Ok(o)
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("usage: wordstats [--top N] [--out report.txt] file1.txt [file2.txt ...]");
        return ExitCode::SUCCESS;
    }
    let opts = match parse_args(&args) {
        Ok(o) => o,
        Err(e) => {
            eprintln!("{}", e);
            return ExitCode::from(1);
        }
    };
    let mut out: Box<dyn Write> = match &opts.out {
        Some(path) => match fs::File::create(path) {
            Ok(f) => Box::new(f),
            Err(_) => {
                eprintln!("cannot write {}", path);
                return ExitCode::from(3);
            }
        },
        None => Box::new(io::stdout()),
    };
    let mut freq = HashMap::new();
    let mut all = Totals::default();
    let mut failed = false;
    let _ = writeln!(out, "   lines    words    chars  file");
    for path in &opts.files {
        match fs::read_to_string(path) {
            Ok(text) => {
                let t = count_text(&text, &mut freq);
                let _ = writeln!(out, "{:8} {:8} {:8}  {}", t.lines, t.words, t.chars, path);
                all.lines += t.lines;
                all.words += t.words;
                all.chars += t.chars;
            }
            Err(_) => {
                eprintln!("cannot read {}", path);
                failed = true;
            }
        }
    }
    if opts.files.len() > 1 {
        let _ = writeln!(out, "{:8} {:8} {:8}  total", all.lines, all.words, all.chars);
    }
    let mut words: Vec<(String, usize)> = freq.into_iter().collect();
    words.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    let _ = writeln!(out, "\nTop {} words:", opts.top);
    for (i, (w, n)) in words.iter().take(opts.top).enumerate() {
        let _ = writeln!(out, "{:4}. {:<20} {}", i + 1, w, n);
    }
    if let Some(path) = &opts.out {
        println!("report written to {}", path);
    }
    if failed { ExitCode::from(2) } else { ExitCode::SUCCESS }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn counts_words_and_lines() {
        let mut freq = HashMap::new();
        let t = count_text("one two\nTwo three\n", &mut freq);
        assert_eq!(t, Totals { lines: 2, words: 4, chars: 16 });
        assert_eq!(freq["two"], 2);
    }

    #[test]
    fn bad_top_is_an_error() {
        assert!(parse_args(&["--top".into(), "0".into()]).is_err());
    }
}
