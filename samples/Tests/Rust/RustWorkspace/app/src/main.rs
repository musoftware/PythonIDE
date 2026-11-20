//! The application crate of the RustWorkspace workspace: uses the `core` library crate.
use rustworkspace_core::{greet, Stats};

fn main() {
    println!("{}", greet("workspace"));
    let stats = Stats::from_values(&[3.0, 1.0, 4.0, 1.0, 5.0, 9.0]);
    println!("mean = {:.2}, max = {}", stats.mean, stats.max);
}
