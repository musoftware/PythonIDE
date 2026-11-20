//! RustConsole - a Rust console application for the RAD IDE.
//! F5 debugs (breakpoints, locals), Ctrl+F5 runs (cargo run). Output appears in the Output window.

mod geometry;

use std::collections::HashMap;

use geometry::Rect;

/// Counts how often each word occurs.
fn word_counts(text: &str) -> HashMap<&str, i32> {
    let mut counts: HashMap<&str, i32> = HashMap::new();
    for word in text.split_whitespace() {
        *counts.entry(word).or_insert(0) += 1;
    }
    counts
}

fn main() {
    println!("Hello from RustConsole!");
    let counts = word_counts("the quick brown fox jumps over the lazy dog the end");
    let mut words: Vec<_> = counts.into_iter().collect();
    words.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(b.0)));
    for (word, n) in words.iter().take(3) {
        println!("{word}: {n}");
    }
    let r = Rect::new(3.0, 4.0);
    let total = r.area() + r.perimeter();
    println!("area = {}, perimeter = {}, total = {total}", r.area(), r.perimeter());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn counts_words() {
        let c = word_counts("a b a");
        assert_eq!(c["a"], 2);
        assert_eq!(c["b"], 1);
    }
}
