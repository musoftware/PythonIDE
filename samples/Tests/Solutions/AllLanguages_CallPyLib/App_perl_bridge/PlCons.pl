package PlCons;
use strict;
use warnings;
use PyLibRef;
sub Test { return PyLib::Add(2, 3) . "|" . PyLib::Greet("Perl"); }
1;
