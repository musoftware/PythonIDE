# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Expense Tracker - event handlers for Form1 (Perl, GUI Bridge).
# Shows: data entry with validation (MsgBox), ComboBox, DataGridView, ListBox, CSV file save/load,
#        menus, a confirmation question (InputBox), StatusBar, a data module (ExpenseStore.pl).
use strict;
use warnings;
use POSIX qw(strftime);
use RadGUI;
require './ExpenseStore.pl';

sub Form1_Load {
    rad_set('txtDate', 'Text', strftime('%Y-%m-%d', localtime));
    rad_set('cboCategory', 'ListIndex', 0);
    my $n = ExpenseStore::load();
    refresh();
    status($n ? "Loaded $n expense(s) from $ExpenseStore::FILE" : 'No saved expenses yet');
}

sub cmdAdd_Click {
    my $err = ExpenseStore::add(rad_get('txtDate', 'Text'), rad_get('txtItem', 'Text'),
                                rad_get('cboCategory', 'Text'), rad_get('txtAmount', 'Text'));
    if ($err) {
        rad_msgbox($err);
        return;
    }
    rad_set('txtItem', 'Text', '');
    rad_set('txtAmount', 'Text', '');
    rad_call('txtItem', 'SetFocus');
    refresh();
    ExpenseStore::save();
    status('Added and saved');
}

# Enter in the amount box adds the expense
sub txtAmount_KeyPress {
    my ($e) = @_;
    cmdAdd_Click() if $e->{args} =~ /^\S+ \S+ \S+ 13\b/ || $e->{args} =~ /\bReturn\b/;
}

sub cmdDelete_Click {
    my $row = rad_get('grdExpenses', 'Row') - 1;            # Row 0 is the header line
    if ($row < 0 || $row >= @ExpenseStore::ROWS) {
        rad_msgbox('Select a row first.');
        return;
    }
    my $r = $ExpenseStore::ROWS[$row];
    my $answer = rad_input("Type YES to delete '$r->{item}' ($r->{amount})");
    return unless uc($answer) eq 'YES';
    ExpenseStore::remove_at($row);
    ExpenseStore::save();
    refresh();
    status('Deleted');
}

sub mnuFileSave_Click {
    my $n = ExpenseStore::save();
    status("Saved $n row(s) to $ExpenseStore::FILE");
}

sub mnuFileReload_Click {
    my $n = ExpenseStore::load();
    refresh();
    status("Reloaded $n row(s)");
}

sub mnuFileExit_Click { rad_end(); }

sub mnuReportTotals_Click {
    my @lines = map { sprintf('%s: %.2f', @$_) } ExpenseStore::totals_by_category();
    rad_msgbox(@lines ? join(' | ', @lines) . sprintf(' || Total: %.2f', ExpenseStore::total()) : 'No expenses yet.');
}

sub refresh {
    rad_call('grdExpenses', 'Clear');
    for my $r (@ExpenseStore::ROWS) {
        rad_call('grdExpenses', 'AddItem', $r->{date}, $r->{item}, $r->{category}, sprintf('%.2f', $r->{amount}));
    }
    rad_call('lstTotals', 'Clear');
    rad_call('lstTotals', 'AddItem', sprintf('%-10s %8.2f', @$_)) for ExpenseStore::totals_by_category();
    rad_set('lblTotal', 'Caption', sprintf('Total: %.2f', ExpenseStore::total()));
}

sub status { rad_set('sbStatus', 'Text', shift); }

1;
