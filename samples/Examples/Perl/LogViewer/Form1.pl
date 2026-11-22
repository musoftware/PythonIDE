# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Log Viewer - event handlers for Form1 (Perl, GUI Bridge).
# Shows: a Timer that tails a growing log file, filtering with a TextBox (TextChanged) and a ComboBox,
#        counting with hashes, InputBox ("Go to line"), menus, CheckBox, StatusBar.
use strict;
use warnings;
use POSIX qw(strftime);
use RadGUI;

my $LOG = 'sample.log';
my @lines;          # every line read so far
my $offset = 0;     # bytes of the file already read (the Timer reads only what was appended)
my @shown;          # indexes into @lines of the lines in the list

sub Form1_Load {
    rad_set('cboLevel', 'ListIndex', 0);
    read_new_lines();
    apply_filter();
    rad_set('tmrTail', 'Enabled', rad_get('chkFollow', 'Value') eq '1' ? 'True' : 'False');
}

# Timer: read the lines appended since the last tick
sub tmrTail_Tick {
    my $before = @lines;
    read_new_lines();
    apply_filter() if @lines != $before;
}

sub chkFollow_CheckedChanged {
    my $on = rad_get('chkFollow', 'Value') eq '1';
    rad_set('tmrTail', 'Enabled', $on ? 'True' : 'False');
    status($on ? 'Following the file (every second)' : 'Paused');
}

sub txtFilter_TextChanged  { apply_filter(); }
sub cboLevel_SelectedIndexChanged { apply_filter(); }

sub cmdReload_Click {
    @lines = ();
    $offset = 0;
    read_new_lines();
    apply_filter();
}

sub mnuFileClear_Click {
    rad_call('lstLog', 'Clear');
    @shown = ();
}

sub mnuFileExit_Click { rad_end(); }

# Appends a few lines to the log, as a running program would
sub mnuToolsSimulate_Click {
    my @levels = qw(INFO INFO INFO WARN ERROR);
    my @what = ('user signed in', 'report exported', 'disk space low', 'cache refreshed', 'payment failed');
    open(my $fh, '>>', $LOG) or do { rad_msgbox("Cannot write $LOG: $!"); return };
    for (1 .. 3) {
        my $i = int(rand(@levels));
        printf $fh "%s [%s] %s\n", strftime('%Y-%m-%d %H:%M:%S', localtime), $levels[$i], $what[$i];
    }
    close $fh;
    tmrTail_Tick();
}

sub mnuToolsGoto_Click {
    my $n = rad_input('Go to which line of the list (1 - ' . scalar(@shown) . ')?');
    return unless defined $n && $n =~ /^\d+$/ && $n >= 1 && $n <= @shown;
    rad_set('lstLog', 'ListIndex', $n - 1);
    status("Line $n: " . $lines[$shown[$n - 1]]);
}

sub read_new_lines {
    open(my $fh, '<', $LOG) or return;
    seek($fh, $offset, 0);
    while (my $l = <$fh>) {
        last unless $l =~ /\n\z/;           # a half-written line is read on the next tick
        $offset = tell($fh);
        $l =~ s/\r?\n\z//;
        push @lines, $l if $l ne '';
    }
    close $fh;
}

sub apply_filter {
    my $text = rad_get('txtFilter', 'Text');
    my $level = rad_get('cboLevel', 'Text') || 'ALL';
    my %count = (INFO => 0, WARN => 0, ERROR => 0);
    @shown = ();
    rad_call('lstLog', 'Clear');
    for my $i (0 .. $#lines) {
        my $l = $lines[$i];
        my ($lv) = $l =~ /\[(INFO|WARN|ERROR)\]/;
        $count{$lv}++ if $lv;
        next if $level ne 'ALL' && (!$lv || $lv ne $level);
        next if $text ne '' && index(lc $l, lc $text) < 0;
        push @shown, $i;
        rad_call('lstLog', 'AddItem', $l);
    }
    rad_set('lblCounts', 'Caption', "INFO $count{INFO}  WARN $count{WARN}  ERROR $count{ERROR}");
    status(scalar(@shown) . ' of ' . scalar(@lines) . ' line(s) shown');
}

sub status { rad_set('sbStatus', 'Text', shift); }

1;
