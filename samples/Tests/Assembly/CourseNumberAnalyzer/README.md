# CourseNumberAnalyzer

**asm-nasm, x64, two files** - the final project of the Arabic Assembly course (lesson 15,
`radide/tutorials/assembly/15-final-project.md`), created by its "جرّبه" button.

* `main.asm`: reads a count and the numbers with `scanf`, prints the sorted list, sum, min / max, average,
  the primes and a bar chart; keeps its values in RBX / RSI / RDI / R12 across the C runtime calls.
* `stats.asm`: leaf functions exported with `global`: `arr_sum`, `arr_min`, `arr_max`, `is_prime`,
  `bubble_sort`.

Input (type it in the Program Input bar):

    6
    12 7 33 5 21 9

Output: `Sorted: 5 7 9 12 21 33`, `Sum: 87`, `Min: 5  Max: 33`, `Average: 14 (remainder 3)`, `Primes: 5 7`
and a chart with one star per 3.
