# Hello Perl - event handlers for Form1 (GUI Bridge).
# rad_set / rad_get / rad_call work with the controls drawn by the IDE;
# radcall('Module.func', ...) calls functions of any project module (any language).
use strict;
use warnings;
use RadGUI;

my $clicks = 0;

sub Form1_Load {
    rad_set('lblOut', 'Caption', 'Type a name and press Greet.');
}

sub cmdGreet_Click {
    my ($e) = @_;
    my $name = rad_get('txtName', 'Text');
    $name =~ s/^\s+|\s+$//g;
    if ($name eq '') {
        rad_msgbox('Please type a name first.');
        return;
    }
    $clicks++;
    # Greeter.pl runs in its own worker process, reached through the RAD Hub
    my $text = radcall('Greeter.greet', $name, $clicks);
    rad_set('lblOut', 'Caption', $text);
    rad_call('lstLog', 'AddItem', "$clicks: $text");
}

sub cmdClear_Click {
    rad_call('lstLog', 'Clear');
    $clicks = 0;
    rad_set('lblOut', 'Caption', 'Cleared.');
}

1;
