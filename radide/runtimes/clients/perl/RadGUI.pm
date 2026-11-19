package RadGUI;
# RAD IDE - GUI Bridge client for Perl (copied into the project when it runs).
#
# The IDE draws the forms; this program talks to it over stdin/stdout
# (protocol: docs/CONTRACTS.md section 1). Everything is synchronous.
#
#   rad_set($obj, $prop, $value)       set a property      rad_set("lblOut", "Caption", "Hi")
#   rad_get($obj, $prop)      -> text  read a property     rad_get("txtA", "Text")
#   rad_getnum($obj, $prop)   -> num   read a property as a number
#   rad_call($obj, $method, @args)     call a method       rad_call("lstLog", "AddItem", "line")
#   rad_msgbox($text)                  message box (waits for OK)
#   rad_input($prompt)        -> text  input box
#   rad_show($form) / rad_hide($form)  show or hide a form
#   rad_end()                          quit the program
#   radcall("Module.func", @args) -> value
#                                      call a function of any project module, in any
#                                      language, through the RAD Hub (values are JSON)
# Handlers are subs named <Control>_<Event>; they get one hashref
#   $e = { X, Y, Button, KeyCode, KeyChar, args }   (mouse/key events, zeros otherwise)
use strict;
use warnings;
use Exporter 'import';
use IO::Handle;
use IO::Socket::INET;
use JSON::PP;

our @EXPORT = qw(rad_set rad_get rad_getnum rad_call rad_msgbox rad_input rad_show rad_hide rad_end
                 radcall);
our $WORKER = 0;        # set by radworker.pl: no IDE on stdin/stdout

binmode(STDIN);
binmode(STDOUT);
STDOUT->autoflush(1);
STDERR->autoflush(1);

sub _clean {
    my $v = shift;
    $v = '' unless defined $v;
    $v =~ s/\r?\n/ /g;
    return $v;
}

sub _send {
    my $line = shift;
    if ($WORKER) { print STDERR "$line\n"; return; }
    print STDOUT "$line\n";
}

sub _read_line {
    return '' if $WORKER;
    my $line = <STDIN>;
    if (!defined $line) { exit 0; }        # the IDE went away
    $line =~ s/\r?\n\z//;
    return $line;
}

sub rad_set {
    my ($obj, $prop, $value) = @_;
    _send("SET $obj $prop " . _clean($value));
    return;
}

sub rad_get {
    my ($obj, $prop) = @_;
    _send("GET $obj $prop");
    return _read_line();
}

sub rad_getnum {
    my $v = rad_get(@_);
    return ($v =~ /^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)/) ? $1 + 0 : 0;
}

sub rad_call {
    my ($obj, $method, @args) = @_;
    my $line = "CALL $obj $method";
    $line .= " " . join("\t", map { _clean($_) } @args) if @args;
    _send($line);
    return _read_line();
}

sub rad_msgbox { _send("MSGBOX " . _clean(shift)); return _read_line(); }
sub rad_input  { _send("INPUT " . _clean(shift)); return _read_line(); }
sub rad_show   { _send("SHOW " . shift); return; }
sub rad_hide   { _send("HIDE " . shift); return; }
sub rad_end    { _send("END"); exit 0; }

# ------------------------------------------------------------------ RAD Hub
my $JSON = JSON::PP->new->allow_nonref->canonical;
my ($hub, $hub_id) = (undef, 0);

# strings stay UTF-8 octets everywhere (like the rest of the program)
sub _octets {
    my $v = shift;
    if (ref $v eq 'ARRAY') { return [map { _octets($_) } @$v]; }
    if (ref $v eq 'HASH')  { return { map { (_octets($_), _octets($v->{$_})) } keys %$v }; }
    if (defined $v && !ref $v && utf8::is_utf8($v)) { my $c = $v; utf8::encode($c); return $c; }
    return $v;
}

sub radcall {
    my ($name, @args) = @_;
    my $addr = $ENV{RAD_HUB} or die "radcall($name): RAD Hub is not running (RAD_HUB is not set)\n";
    if (!$hub) {
        my ($host, $port) = $addr =~ /^(.*):(\d+)$/ or die "radcall: bad RAD_HUB '$addr'\n";
        $hub = IO::Socket::INET->new(PeerAddr => $host, PeerPort => $port, Proto => 'tcp')
            or die "radcall($name): cannot connect to RAD Hub at $addr: $!\n";
        binmode($hub);
        $hub->autoflush(1);
    }
    my $id = ++$hub_id;
    print $hub $JSON->encode({ id => $id, call => $name, args => \@args }) . "\n";
    while (1) {
        my $line = <$hub>;
        if (!defined $line) { undef $hub; die "radcall($name): RAD Hub closed the connection\n"; }
        $line =~ s/\r?\n\z//;
        next if $line eq '';
        my $msg = eval { $JSON->decode($line) };
        next unless ref $msg eq 'HASH' && defined $msg->{id} && $msg->{id} == $id;
        die "radcall($name): $msg->{error}\n" if defined $msg->{error};
        return _octets($msg->{result});
    }
}

# ------------------------------------------------------------------ main loop
my %LOWER;      # lower-case handler name -> real name

sub _find_handler {
    my $name = shift;
    no strict 'refs';
    return \&{"main::$name"} if defined &{"main::$name"};
    if (!%LOWER) {
        for my $sym (keys %main::) { $LOWER{lc $sym} = $sym if defined &{"main::$sym"}; }
    }
    my $real = $LOWER{lc $name};
    return ($real && defined &{"main::$real"}) ? \&{"main::$real"} : undef;
}

sub load_file {
    my $file = shift;
    my $path = $file =~ m{^(?:[A-Za-z]:)?[/\\]} ? $file : "./$file";
    my $ok;
    {
        package main;           # form code defines its handlers in package main
        $ok = do $path;
    }
    if ($@) { print STDERR "[Perl] error in $file: $@"; }
    elsif (!defined $ok && $!) { print STDERR "[Perl] cannot load $file: $!\n"; }
    %LOWER = ();
}

sub run {
    while (defined(my $line = <STDIN>)) {
        $line =~ s/\r?\n\z//;
        last if $line eq 'QUIT';
        next unless $line =~ /^EVENT (\S+) (\S+) ?(.*)$/;
        my ($obj, $ev, $rest) = ($1, $2, $3);
        my @a = split / /, $rest, 5;
        no warnings 'numeric';
        my %e = (X => ($a[0] // 0) + 0, Y => ($a[1] // 0) + 0, Button => ($a[2] // 0) + 0,
                 KeyCode => ($a[3] // 0) + 0, KeyChar => $a[4] // '', args => $rest);
        my $h = _find_handler("${obj}_$ev");
        if ($h) {
            eval { $h->(\%e); 1 } or print STDERR "[Perl] error in ${obj}_$ev: $@";
        }
        print STDOUT "DONE\n";
    }
    exit 0;
}

1;
