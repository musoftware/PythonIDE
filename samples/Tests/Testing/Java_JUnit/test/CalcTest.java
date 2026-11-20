import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

public class CalcTest {
    @Test
    void addsTwoNumbers() {
        assertEquals(5, Calc.add(2, 3));
    }

    @Test
    void failsOnPurpose() {
        assertEquals(5, Calc.add(2, 2), "2 + 2");
    }
}
