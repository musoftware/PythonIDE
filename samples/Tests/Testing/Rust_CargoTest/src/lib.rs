pub fn add(a: i32, b: i32) -> i32 {
    a + b
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn adds() {
        assert_eq!(add(2, 3), 5);
    }

    #[test]
    fn fails_on_purpose() {
        assert_eq!(add(2, 2), 5, "2 + 2 is not 5");
    }

    #[test]
    #[ignore]
    fn ignored_example() {}
}
