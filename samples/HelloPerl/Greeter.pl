# Module Greeter. Other languages call it through the RAD Hub:
#   radcall("Greeter.greet", "Ali", 1)   (arguments and the result are JSON values)
package Greeter;
use strict;
use warnings;

sub greet {
    my ($name, $count) = @_;
    return $count == 1 ? "Hello, $name!" : "Hello again, $name! (greeting #$count)";
}

1;
