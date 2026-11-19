package PerlLib;
use strict;
use warnings;

# Add two numbers.
sub Add {
    my ($x, $y) = @_;
    return $x + $y;
}

# Join words with a separator.
sub JoinWords {
    my $sep = shift;
    my $list = shift;
    return join($sep, @$list);
}

sub Stats {
    my ($list) = @_;
    my $s = 0;
    $s += $_ for @$list;
    return { sum => $s, count => scalar @$list };
}

sub _hidden { return 1; }
sub cmdGo_Click { }

1;
