# Debugger test (Perl): breakpoint on the "my $text = ..." line of cmdGreet_Click, then F5 and Greet.
use strict;
use warnings;
use RadGUI;

my $clicks = 0;

sub make_greeting {
    my ($name, $n) = @_;
    my $text = "Hello, $name! (click $n)";
    return $text;
}

sub Form1_Load {
    rad_set('lblOut', 'Caption', 'Press Greet.');
}

sub cmdGreet_Click {
    my ($e) = @_;
    my $name = rad_get('txtName', 'Text');
    $clicks++;
    my %info = (name => $name, clicks => $clicks);
    my @tags = ('a', 'b');
    my $text = make_greeting($name, $clicks);
    rad_set('lblOut', 'Caption', $text);
}

1;
