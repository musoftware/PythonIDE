//! Geometry helpers (a struct with methods - try F2 rename on `area`).

/// A rectangle.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Rect {
    pub width: f64,
    pub height: f64,
}

impl Rect {
    /// Creates a rectangle.
    pub fn new(width: f64, height: f64) -> Self {
        Self { width, height }
    }

    /// The area (width * height).
    pub fn area(&self) -> f64 {
        self.width * self.height
    }

    /// The perimeter.
    pub fn perimeter(&self) -> f64 {
        2.0 * (self.width + self.height)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn area() {
        assert_eq!(Rect::new(2.0, 3.0).area(), 6.0);
    }

    #[test]
    fn perimeter() {
        assert_eq!(Rect::new(2.0, 3.0).perimeter(), 10.0);
    }
}
