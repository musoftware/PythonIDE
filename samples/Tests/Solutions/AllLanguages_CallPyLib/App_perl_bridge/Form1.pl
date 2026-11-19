# Event handlers for Form1. Subs named <Control>_<Event> run when the event happens.
# rad_set / rad_get / rad_call work with the controls, radcall('Module.func', ...)
# calls functions of other project modules (any language).
use strict;
use warnings;
use RadGUI;

sub Form1_Load {
    my ($e) = @_;
    # runs when the form is shown
}

1;
