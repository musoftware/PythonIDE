//! The library crate of the RustWorkspace workspace.

/// A greeting.
pub fn greet(who: &str) -> String {
    format!("Hello, {who}!")
}

/// Summary statistics of a list of numbers.
#[derive(Debug, Default, PartialEq)]
pub struct Stats {
    pub count: usize,
    pub mean: f64,
    pub max: f64,
}

impl Stats {
    /// Computes the statistics (an empty slice gives the default value).
    pub fn from_values(values: &[f64]) -> Self {
        if values.is_empty() {
            return Self::default();
        }
        let sum: f64 = values.iter().sum();
        let max = values.iter().cloned().fold(f64::MIN, f64::max);
        Self { count: values.len(), mean: sum / values.len() as f64, max }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn greets() {
        assert_eq!(greet("x"), "Hello, x!");
    }

    #[test]
    fn stats() {
        let s = Stats::from_values(&[1.0, 2.0, 3.0]);
        assert_eq!(s.count, 3);
        assert_eq!(s.mean, 2.0);
        assert_eq!(s.max, 3.0);
    }
}
