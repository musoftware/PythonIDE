# Test file: name starts with test_, every func test_* is a test.
load "mathlib.ring"

func test_add
    assertEqual(5, addNumbers(2, 3))

func test_fails_on_purpose
    assertEqual(5, addNumbers(2, 2))
