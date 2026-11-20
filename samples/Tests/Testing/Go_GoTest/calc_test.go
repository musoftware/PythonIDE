package calc

import "testing"

func TestAdd(t *testing.T) {
	if Add(2, 3) != 5 {
		t.Fatal("2+3 should be 5")
	}
}

func TestSign(t *testing.T) {
	if Sign(-1) != "negative" {
		t.Errorf("Sign(-1) = %q", Sign(-1))
	}
}

func TestFailsOnPurpose(t *testing.T) {
	if Add(1, 1) != 3 {
		t.Errorf("1+1 is %d, this test expects 3 (fails on purpose)", Add(1, 1))
	}
}
