# PHP_PHPUnit

Tests the Test Explorer with **PHPUnit** (`tests/CalcTest.php`, JUnit XML report) and PSR-4 autoloading
from `composer.json`. `testFailsOnPurpose` fails.

**Try it:** run `composer install` once in the Terminal (creates vendor/ - not kept), open the folder,
Test > Run All Tests -> 1 passed, 1 failed. Also: Edit > Format Document on `src/Calc.php` uses
PHP CS Fixer.
