package Devel::RadDbg;
# RAD IDE debug agent for Perl (radide/debug_more.py, AgentSession):  perl -d:RadDbg _radmain.pl
# Talks to the IDE over a Windows named pipe (QLocalServer): one handle to write (opened first), one to
# read. Breakpoints come from the file RADDBG_BPFILE ("path<TAB>line<TAB>cond<TAB>hit<TAB>log"), re-read
# when it changes (checked at most every 0.3 s while code runs, and on every resume).
# Locals come from PadWalker when it is installed (Strawberry Perl has it); watch expressions are
# evaluated in the scope of the stopped code (eval from package DB).
use strict;
no warnings;
1;

package DB;
no strict;
no warnings;

our ($single, $trace, $signal, $sub, %sub, @args, $active);
my ($OUT, $IN, $BPFILE, $CWD, $bptext, %bps, $mode, $step_depth, $last_check, $have_pw, @refs);
my %keycache;
my $EXC;                     # (no initializer: BEGIN below sets it before this line would run)

BEGIN {
    $mode = 'run';
    $step_depth = 0;
    $last_check = 0;
    $active = 0;
}

sub _esc { my $s = shift; $s = '' unless defined $s; $s =~ s/\\/\\\\/g; $s =~ s/\t/\\t/g; $s =~ s/\n/\\n/g;
           $s =~ s/\r/\\r/g; return $s }
sub _unesc { my $s = shift; $s =~ s/\\(.)/$1 eq 't' ? "\t" : $1 eq 'n' ? "\n" : $1 eq 'r' ? "\r" : $1/ge; $s }
sub _send { my $l = join("\t", map { _esc($_) } @_) . "\n"; syswrite($OUT, $l) }
sub _recv {
    my $line = '';
    while (1) {
        my $c;
        my $n = sysread($IN, $c, 1);
        return undef unless $n;
        last if $c eq "\n";
        $line .= $c;
    }
    $line =~ s/\r$//;
    return [map { _unesc($_) } split(/\t/, $line, -1)];
}

sub _now { defined &Time::HiRes::time ? Time::HiRes::time() : time() }

sub _key {
    my $f = shift;
    return $keycache{$f} if exists $keycache{$f};
    my $s = $f;
    if ($s =~ /^\(eval/ || $s =~ /^-e$/) { $keycache{$f} = ''; return '' }
    $s =~ s{\\}{/}g;
    $s = lc $s;
    $s =~ s{^(\./)+}{};
    $s = "$CWD/$s" unless $s =~ m{^[a-z]:/} || $s =~ m{^/};
    $s =~ s{/\./}{/}g;
    $keycache{$f} = $s;
    return $s;
}

sub _skipped {
    my $k = shift;
    return 1 if $k eq '';
    my ($base) = $k =~ m{([^/]+)$};
    return 1 if $base =~ /^(radgui\.pm|raddbg\.pm|radworker\.pl)$/;
    return 1 if $k =~ m{/(perl|site|vendor)/lib/};
    return 0;
}

sub _load_bps {
    my $force = shift;
    return unless $BPFILE;
    open(my $fh, '<', $BPFILE) or return;
    local $/;
    my $text = <$fh>;
    close $fh;
    $text = '' unless defined $text;
    return if !$force && defined $bptext && $text eq $bptext;
    $bptext = $text;
    $EXC = 0;
    my %new;
    for my $l (split /\n/, $text) {
        $l =~ s/\r$//;
        my @p = map { _unesc($_) } split(/\t/, $l, -1);
        if ($p[0] eq '!exc') { $EXC = ($p[1] // '') eq '1'; next }     # Debug > Break on Exceptions
        next unless defined $p[1] && $p[1] =~ /^\d+$/;
        my $old = $bps{$p[1]} && $bps{$p[1]}{$p[0]};
        $new{$p[1]}{$p[0]} = { cond => $p[2] // '', hit => $p[3] // '', log => $p[4] // '',
                               count => ($old && $old->{cond} eq ($p[2] // '')) ? $old->{count} : 0 };
    }
    %bps = %new;
}

sub _show {
    my $v = shift;
    return 'undef' unless defined $v;
    my $r = ref $v;
    if (!$r) { return $v =~ /^-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$/ ? $v : "'" . $v . "'" }
    return 'ARRAY (' . scalar(@$v) . ' items)' if $r eq 'ARRAY';
    return 'HASH (' . scalar(keys %$v) . ' keys)' if $r eq 'HASH';
    return 'SCALAR ref -> ' . _show($$v) if $r eq 'SCALAR' || $r eq 'REF';
    return "$v";
}

sub _ref_of {
    my $v = shift;
    my $r = ref $v;
    return 0 unless $r eq 'ARRAY' || $r eq 'HASH' || $r eq 'SCALAR' || $r eq 'REF'
                    || ($r && eval { UNIVERSAL::isa($v, 'HASH') || UNIVERSAL::isa($v, 'ARRAY') });
    for my $i (0 .. $#refs) { return $i + 1 if $refs[$i] == $v }
    push @refs, $v;
    return scalar @refs;
}

sub _type_of { my $v = shift; my $r = ref $v; return $r ? $r : defined $v ? 'scalar' : 'undef' }

# evaluated in package DB: sees the lexicals of the first non-DB frame (the stopped code)
sub _eval {
    my ($expr, $pkg) = @_;
    my @r = eval "package $pkg; no strict; no warnings; $expr";
    return (0, $@) if $@;
    return (1, @r == 1 ? $r[0] : \@r) if @r <= 1 || ref($r[0]) ne '';
    return (1, \@r);
}

sub _locals {
    my @out;
    return @out unless $have_pw;
    my $my = eval { PadWalker::peek_my(2) } || {};
    for my $name (sort keys %$my) {
        my $ref = $my->{$name};
        my $val;
        if ($name =~ /^\$/) { $val = $$ref } else { $val = $ref }
        push @out, [$name, $val];
    }
    return @out;
}

sub _format_log {
    my ($msg, $pkg) = @_;
    $msg =~ s/\{([^{}]+)\}/my ($ok, $v) = _eval($1, $pkg); $ok ? (ref $v ? _show($v) : (defined $v ? $v : 'undef')) : "<$v>"/ge;
    return $msg;
}

sub _depth {
    my $d = 0;
    $d++ while caller($d);
    return $d;
}

sub _stopped {
    my ($reason, $pkg, $file, $line, $locals) = @_;
    @refs = ();
    _send('stop', $reason, $file, $line);
    my (@names, @sites);
    for (my $i = 1; my @c = caller($i); $i++) {
        my ($cf, $cl, $sn) = @c[1, 2, 3];
        if ($sn eq 'DB::sub') { push @sites, [$cf, $cl] }
        elsif ($sn =~ /^DB::/) { next }
        else { push @names, $sn; push @sites, [$cf, $cl] unless $cf =~ /RadDbg\.pm$/i }
        last if $i > 300;
    }
    my @locs = ([$file, $line], @sites);
    for my $k (0 .. $#locs) {
        my $n = defined $names[$k] ? $names[$k] : '(main)';
        $n =~ s/^main:://;
        _send('frame', $n, $locs[$k][0], $locs[$k][1]) unless _skipped(_key($locs[$k][0]));
    }
    for my $nv (@$locals) {
        my ($n, $v) = @$nv;
        if ($n =~ /^\@/) { _send('var', $n, 'ARRAY', 'ARRAY (' . scalar(@$v) . ' items)', _ref_of($v)) }
        elsif ($n =~ /^%/) { _send('var', $n, 'HASH', 'HASH (' . scalar(keys %$v) . ' keys)', _ref_of($v)) }
        else { _send('var', $n, _type_of($v), _show($v), _ref_of($v)) }
    }
    _send('end');
    my $depth = _depth() - 2;
    while (1) {
        my $cmd = _recv();
        if (!$cmd) { $active = 0; return }
        my $c = $cmd->[0];
        if ($c eq 'c') { $mode = 'run'; last }
        elsif ($c eq 's') { $mode = 'step'; last }
        elsif ($c eq 'n') { $mode = 'next'; $step_depth = $depth; last }
        elsif ($c eq 'o') { $mode = 'out'; $step_depth = $depth; last }
        elsif ($c eq 'q') { $active = 0; return }
        elsif ($c eq 'e') {
            my ($ok, $v) = _eval($cmd->[2], $pkg);
            if ($ok) { _send('result', $cmd->[1], _show($v), _type_of($v), _ref_of($v)) }
            else { my $e = "$v"; $e =~ s/\s+$//; _send('result', $cmd->[1], "error: $e", 'error', 0) }
        }
        elsif ($c eq 'v') {
            my $t = $refs[($cmd->[2] || 0) - 1];
            _send('vars', $cmd->[1]);
            if (UNIVERSAL::isa($t, 'ARRAY')) {
                my $n = 0;
                for my $v (@$t) { _send('var', "[$n]", _type_of($v), _show($v), _ref_of($v)); last if ++$n >= 500 }
            } elsif (UNIVERSAL::isa($t, 'HASH')) {
                my $n = 0;
                for my $k (sort keys %$t) { my $v = $t->{$k}; _send('var', "{$k}", _type_of($v), _show($v), _ref_of($v));
                                            last if ++$n >= 500 }
            } elsif (ref $t eq 'SCALAR' || ref $t eq 'REF') {
                _send('var', '$$', _type_of($$t), _show($$t), _ref_of($$t));
            }
            _send('end');
        }
    }
    _load_bps(1);
}

sub DB {
    return unless $active;
    my ($pkg, $file, $line) = caller;
    my $now = _now();
    if ($now - $last_check > 0.3) { $last_check = $now; _load_bps(0) }
    if ($mode ne 'run') {
        my $k = _key($file);
        if (!_skipped($k)) {
            if ($mode eq 'step') { local $active = 0; _stopped('step', $pkg, $file, $line, [_locals()]); return }
            my $d = _depth() - 1;
            if (($mode eq 'next' && $d <= $step_depth) || ($mode eq 'out' && $d < $step_depth)) {
                local $active = 0;
                _stopped('step', $pkg, $file, $line, [_locals()]);
                return;
            }
        }
    }
    my $bl = $bps{$line} or return;
    my $b = $bl->{_key($file)} or return;
    local $active = 0;
    if ($b->{cond} ne '') {
        my ($ok, $v) = _eval($b->{cond}, $pkg);
        return unless $ok && $v;
    }
    $b->{count}++;
    if ($b->{hit} ne '' && $b->{hit} =~ /^\s*(==|>=|>|%|=)?\s*(\d+)\s*$/) {
        my ($op, $n, $c) = ($1 // '==', $2, $b->{count});
        my $pass = $op eq '>=' ? $c >= $n : $op eq '>' ? $c > $n : $op eq '%' ? ($n > 0 && $c % $n == 0) : $c == $n;
        return unless $pass;
    }
    if ($b->{log} ne '') { _send('out', _format_log($b->{log}, $pkg)); return }
    _stopped('breakpoint', $pkg, $file, $line, [_locals()]);
}

sub sub {
    no strict 'refs';
    return &$sub;
}

# Break on Exceptions: RadGUI.pm runs every handler inside eval { }; a __DIE__ handler still runs where die was
# called (the stack and the lexicals are still there), so the agent stops there first - only for a die in the
# program's own code (not in Perl's libraries, not in a die that an eval of a library catches)
sub _on_die {
    my ($pkg, $file, $line) = caller(0);
    return unless $active && $EXC;
    my $k = _key($file);
    return if _skipped($k) || ($CWD ne '' && index($k, "$CWD/") != 0);
    local $active = 0;
    _stopped('exception', $pkg, $file, $line, [_locals()]);
}

BEGIN {
    my $pipe = $ENV{RADDBG_PIPE};
    if (defined $pipe && $pipe ne '') {
        require Fcntl;
        eval { require Time::HiRes };
        $have_pw = eval { require PadWalker; 1 } ? 1 : 0;
        $BPFILE = $ENV{RADDBG_BPFILE} || '';
        $CWD = lc($ENV{RADDBG_CWD} || '.');
        $CWD =~ s{\\}{/}g;
        $CWD =~ s{/$}{};
        my $ok = 0;
        for (1 .. 2000) {
            if (sysopen($OUT, $pipe, Fcntl::O_WRONLY() | Fcntl::O_BINARY())) { $ok = 1; last }
            select(undef, undef, undef, 0.005);
        }
        if ($ok) {
            $ok = 0;
            for (1 .. 2000) {
                if (sysopen($IN, $pipe, Fcntl::O_RDONLY() | Fcntl::O_BINARY())) { $ok = 1; last }
                select(undef, undef, undef, 0.005);
            }
        }
        if ($ok) {
            binmode $OUT;
            binmode $IN;
            _send('hello', 'perl', $]);
            while (1) {
                my $cmd = _recv();
                last if !$cmd || $cmd->[0] eq 'run';
            }
            _load_bps(1);
            $active = 1;
            $SIG{__DIE__} = \&_on_die;
        } else {
            print STDERR "[debugger] cannot reach the IDE pipe\n";
        }
    }
}

1;
