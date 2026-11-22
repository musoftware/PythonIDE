# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Module TextTools - plain Perl text helpers used by Form1.pl (require './TextTools.pl').
# Other languages of a solution can call them through the RAD Hub: radcall("TextTools.word_count", "a b").
package TextTools;
use strict;
use warnings;

# Number of words, lines and characters of a text.
sub stats {
    my ($text) = @_;
    my @words = ($text =~ /(\w+)/g);
    my $lines = $text eq '' ? 0 : scalar(() = $text =~ /\n/g) + 1;
    return { words => scalar(@words), lines => $lines, chars => length($text) };
}

sub word_count {
    my ($text) = @_;
    return stats($text)->{words};
}

# The $n most frequent words (lower case) as [word, count] pairs, most frequent first.
sub top_words {
    my ($text, $n) = @_;
    my %count;
    $count{lc $1}++ while $text =~ /(\w{3,})/g;
    my @sorted = sort { $count{$b} <=> $count{$a} || $a cmp $b } keys %count;
    splice(@sorted, $n) if @sorted > $n;
    return map { [$_, $count{$_}] } @sorted;
}

# Every match of a regular expression; dies with a readable message when the pattern is invalid.
sub find_all {
    my ($text, $pattern, $ignore_case) = @_;
    my $re = eval { $ignore_case ? qr/$pattern/i : qr/$pattern/ };
    die "Invalid pattern: " . ($@ =~ s/ at .*//sr) . "\n" unless $re;
    my @found;
    my $line_no = 0;
    for my $line (split /\n/, $text) {
        $line_no++;
        push @found, "line $line_no: $&" while $line =~ /$re/g;
    }
    return @found;
}

# GUI Bridge values travel one line at a time; "ESC" commands carry multi-line text with \\ \n \r escaped.
sub get_multiline {
    my ($obj, $prop) = @_;
    RadGUI::_send("ESC GET $obj $prop");
    my $v = RadGUI::_read_line();
    $v =~ s/\\(\\|n|r)/$1 eq 'n' ? "\n" : $1 eq 'r' ? "\r" : "\\"/ge;
    $v =~ s/\r\n/\n/g;
    return $v;
}

sub set_multiline {
    my ($obj, $prop, $value) = @_;
    $value =~ s/\\/\\\\/g;
    $value =~ s/\r?\n/\\n/g;
    RadGUI::_send("ESC SET $obj $prop $value");
    return;
}

1;
