use strict;
use warnings;
use lib '.';
use PyLibRef;
use DartLibRef qw(Times Range);
use PerlLibRef;
print "PL ", PyLib::Mul(6, 7), " ", PyLib::Hello("Perl"), "\n";
print "PL ", Times(3, 4), " ", join(",", @{ Range(3) }), "\n";
print "PL ", PerlLib::Add(10, 5), "\n";
