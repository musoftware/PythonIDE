# Class library PerlLib. Public subs (names not starting with _) can be called from
# every project that references this library, in its own language, e.g.
#   Python: import PerlLib; PerlLib.Add(2, 3)     Perl: use PerlLibRef; PerlLib::Add(2, 3)
package PerlLib;
use strict;
use warnings;

# Add two numbers.
sub Add {
    my ($x, $y) = @_;
    return $x + $y;
}

# Greeting text for who.
sub Greet {
    my ($who) = @_;
    return "Hello, $who!";
}

1;
