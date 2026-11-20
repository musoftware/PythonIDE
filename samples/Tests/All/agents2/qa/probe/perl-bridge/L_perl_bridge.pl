# Class library L_perl_bridge. Public subs (names not starting with _) can be called from
# every project that references this library, in its own language, e.g.
#   Python: import L_perl_bridge; L_perl_bridge.Add(2, 3)     Perl: use L_perl_bridgeRef; L_perl_bridge::Add(2, 3)
package L_perl_bridge;
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
