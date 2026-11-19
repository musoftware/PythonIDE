// Rust math library
use crate::radgui::*;

/// Add two numbers
pub fn add(a: f64, b: f64) -> f64 {
    a + b
}

// Greets someone
pub fn greet(who: &str) -> String {
    format!("Hello, {}!", who)
}

pub fn twice(n: i32) -> i64 { (n as i64) * 2 }

pub fn is_even(n: u64) -> bool { n % 2 == 0 }

pub fn total(xs: Vec<f64>) -> f64 { xs.iter().sum() }

pub fn words(s: String) -> Vec<String> { s.split(' ').map(|w| w.to_string()).collect() }

pub fn safe_div(a: f64, b: f64) -> Result<f64, String> {
    if b == 0.0 { Err("division by zero".to_string()) } else { Ok(a / b) }
}

pub fn legacy(args: &[Json]) -> f64 { args.iter().map(Json::as_f64).sum() }

pub fn log(msg: &str) { eprintln!("log {}", msg); }

fn private_helper() -> i32 { 1 }

pub fn generic<T: Clone>(x: T) -> T { x }

pub struct P { pub x: i32 }
impl P {
    pub fn method(&self) -> i32 { self.x }
}

pub fn cmdGo_Click() {}
