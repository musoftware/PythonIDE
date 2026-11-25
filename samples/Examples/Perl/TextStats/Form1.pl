# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Text Statistics - event handlers for Form1 (Perl, GUI Bridge).
# Shows: menus, OpenFileDialog, multi-line TextBox (ESC protocol), DataGridView rows, ListBox,
#        regular expressions, KeyPress (Enter runs Find), StatusBar, MsgBox, a second code module.
use strict;
use warnings;
use RadGUI;
require './TextTools.pl';

sub Form1_Load {
    TextTools::set_multiline('txtInput', 'Text',
        "RAD IDE runs Perl forms through the GUI Bridge.\n"
      . "Perl is great for text: regular expressions, hashes and lists.\n"
      . "Press Analyze to count words, or Find to search with a pattern.");
    status('Ready - type or open a text file');
}

sub cmdAnalyze_Click {
    my $text = TextTools::get_multiline('txtInput', 'Text');
    my $s = TextTools::stats($text);
    rad_set('lblStats', 'Caption', "Words: $s->{words}   Lines: $s->{lines}   Chars: $s->{chars}");
    rad_call('grdWords', 'Clear');
    my $rank = 0;
    for my $pair (TextTools::top_words($text, 10)) {
        rad_call('grdWords', 'AddItem', ++$rank, $pair->[0], $pair->[1]);   # one argument per cell
    }
    status("Analyzed $s->{words} words");
}

sub cmdFind_Click {
    my $text = TextTools::get_multiline('txtInput', 'Text');
    my $pattern = rad_get('txtPattern', 'Text');
    my $ignore = rad_get('chkIgnoreCase', 'Value') eq '1';
    rad_call('lstMatches', 'Clear');
    my @found = eval { TextTools::find_all($text, $pattern, $ignore) };
    if ($@) {
        rad_msgbox($@);
        status('Invalid pattern');
        return;
    }
    rad_call('lstMatches', 'AddItem', $_) for @found;
    status(scalar(@found) . " match(es) for /$pattern/");
}

# Enter in the pattern box runs Find (KeyCode = the Windows key code, 13 = Enter)
sub txtPattern_KeyPress {
    my ($e) = @_;
    cmdFind_Click() if $e->{args} =~ /^\S+ \S+ \S+ 13\b/ || $e->{args} =~ /\bReturn\b/;
}

sub mnuFileOpen_Click {
    return unless rad_call('dlgOpen', 'ShowOpen') eq 'OK';
    my $file = rad_get('dlgOpen', 'FileName');
    open(my $fh, '<', $file) or do { rad_msgbox("Cannot open $file: $!"); return };
    local $/;
    my $text = <$fh>;
    close $fh;
    TextTools::set_multiline('txtInput', 'Text', $text);
    status("Opened $file");
    cmdAnalyze_Click();
}

sub mnuFileClear_Click {
    rad_set('txtInput', 'Text', '');
    rad_call('lstMatches', 'Clear');
    rad_call('grdWords', 'Clear');
    rad_set('lblStats', 'Caption', 'Words: 0   Lines: 0   Chars: 0');
    status('Cleared');
}

sub mnuFileExit_Click { rad_end(); }

sub mnuHelpAbout_Click {
    rad_msgbox("Text Statistics - a RAD IDE example in Perl $^V. (c) 2026 Musoftware - MIT License");
}

sub status { rad_set('sbStatus', 'Text', shift); }

1;
