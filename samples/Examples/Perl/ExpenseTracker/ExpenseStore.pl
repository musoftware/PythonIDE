# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Module ExpenseStore - keeps the expenses in memory and in a CSV file (expenses.csv next to the project).
package ExpenseStore;
use strict;
use warnings;

our $FILE = 'expenses.csv';
our @ROWS;                      # each row: { date, item, category, amount }

sub _csv_field {
    my ($v) = @_;
    return $v unless $v =~ /[",\n]/;
    $v =~ s/"/""/g;
    return qq("$v");
}

sub _csv_split {
    my ($line) = @_;
    my @out;
    while ($line =~ /\G(?:"((?:[^"]|"")*)"|([^,]*))(?:,|$)/g) {
        my $v = defined $1 ? $1 =~ s/""/"/gr : $2;
        push @out, $v;
        last if pos($line) >= length($line);
    }
    return @out;
}

sub load {
    @ROWS = ();
    open(my $fh, '<', $FILE) or return 0;        # no file yet: start empty
    my $header = <$fh>;
    while (my $line = <$fh>) {
        $line =~ s/\r?\n\z//;
        next if $line eq '';
        my ($date, $item, $cat, $amount) = _csv_split($line);
        push @ROWS, { date => $date, item => $item, category => $cat, amount => $amount + 0 };
    }
    close $fh;
    return scalar @ROWS;
}

sub save {
    open(my $fh, '>', $FILE) or die "Cannot write $FILE: $!\n";
    print $fh "Date,Item,Category,Amount\n";
    for my $r (@ROWS) {
        print $fh join(',', map { _csv_field($_) } $r->{date}, $r->{item}, $r->{category},
                       sprintf('%.2f', $r->{amount})), "\n";
    }
    close $fh;
    return scalar @ROWS;
}

# Validates and adds a row; returns an error message or '' when it was added.
sub add {
    my ($date, $item, $cat, $amount) = @_;
    return 'Please type what you bought.' if $item =~ /^\s*$/;
    return 'The date must look like 2026-11-22.' unless $date =~ /^\d{4}-\d{2}-\d{2}$/;
    return 'The amount must be a positive number.' unless $amount =~ /^\s*\d+(?:\.\d+)?\s*$/ && $amount > 0;
    push @ROWS, { date => $date, item => $item, category => ($cat || 'Other'), amount => $amount + 0 };
    return '';
}

sub remove_at {
    my ($i) = @_;
    splice(@ROWS, $i, 1) if $i >= 0 && $i < @ROWS;
}

sub totals_by_category {
    my %t;
    $t{$_->{category}} += $_->{amount} for @ROWS;
    return map { [$_, $t{$_}] } sort { $t{$b} <=> $t{$a} } keys %t;
}

sub total {
    my $sum = 0;
    $sum += $_->{amount} for @ROWS;
    return $sum;
}

1;
