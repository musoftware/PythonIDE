# RAD IDE - RAD Hub worker for Perl modules.
#
#   perl radworker.pl <module file>          (cwd = project folder)
#
# Loads the module and serves its subs over stdin/stdout (JSON lines):
#   stdin : {"id": 7, "func": "add", "args": [2, 3]}
#   stdout: {"id": 7, "result": 5}   or   {"id": 7, "error": "message"}
# A sub is looked up in the package named like the file (Helpers.pl -> Helpers::add),
# then in main. Logs and print output go to stderr so stdout stays clean.
use strict;
use warnings;
use FindBin;
use lib $FindBin::Bin, '.';
use JSON::PP;
use File::Basename qw(fileparse);
use RadGUI;

$RadGUI::WORKER = 1;
my $file = shift @ARGV or do { print STDERR "usage: perl radworker.pl <module file>\n"; exit 2; };
my ($stem) = fileparse($file, qr/\.[^.]*/);

open(my $REPLY, '>&', \*STDOUT) or die "cannot dup stdout: $!";
binmode($REPLY);
$REPLY->autoflush(1);
open(STDOUT, '>&', \*STDERR) or die "cannot redirect stdout: $!";   # print -> stderr
STDOUT->autoflush(1);

my $load_error;
{
    my $path = $file =~ m{^(?:[A-Za-z]:)?[/\\]} ? $file : "./$file";
    my $ok = do $path;
    if ($@) { $load_error = "error loading $file: $@"; }
    elsif (!defined $ok && $!) { $load_error = "cannot load $file: $!"; }
    print STDERR "[radworker] $load_error\n" if $load_error;
}

my $JSON = JSON::PP->new->allow_nonref->canonical;

sub find_sub {
    my $name = shift;
    no strict 'refs';
    for my $pkg ($stem, 'main') {
        return \&{"${pkg}::$name"} if defined &{"${pkg}::$name"};
    }
    for my $pkg ($stem, 'main') {          # case-insensitive fallback
        my $table = \%{"${pkg}::"};
        for my $sym (keys %$table) {
            return \&{"${pkg}::$sym"} if lc $sym eq lc $name && defined &{"${pkg}::$sym"};
        }
    }
    return undef;
}

sub octets {        # JSON strings -> UTF-8 octets (Perl code here works on bytes)
    my $v = shift;
    if (ref $v eq 'ARRAY') { return [map { octets($_) } @$v]; }
    if (ref $v eq 'HASH')  { return { map { (octets($_), octets($v->{$_})) } keys %$v }; }
    if (defined $v && !ref $v && utf8::is_utf8($v)) { my $c = $v; utf8::encode($c); return $c; }
    return $v;
}

# {"id": ..., "<key>": ...} - "id" first: the RAD Hub looks for lines starting with {"id"
my $ENC = JSON::PP->new->allow_nonref->canonical->utf8;
sub send_reply {
    my ($id, $key, $value) = @_;
    my $idtext = $ENC->encode(chars($id));
    my $body = eval { $ENC->encode(chars($value)) };
    if (!defined $body) {
        ($key, $body) = ('error', $ENC->encode("result is not JSON: $@"));
    }
    print $REPLY qq({"id":$idtext,"$key":$body}
);
}
sub reply { my $m = shift; send_reply($m->{id}, exists $m->{error} ? ('error', $m->{error}) : ('result', $m->{result})); }

binmode(STDIN);
while (defined(my $line = <STDIN>)) {
    $line =~ s/\r?\n\z//;
    next if $line =~ /^\s*$/;
    my $req = eval { $JSON->decode($line) };
    if (ref $req ne 'HASH') { reply({ id => undef, error => "bad request" }); next; }
    my $id = $req->{id};
    if ($load_error) { reply({ id => $id, error => $load_error }); next; }
    my $func = $req->{func} // '';
    my $sub = find_sub($func);
    if (!$sub) { reply({ id => $id, error => "$stem has no sub '$func'" }); next; }
    my $args = octets(ref $req->{args} eq 'ARRAY' ? $req->{args} : []);
    my @result;
    my $ok = eval { @result = $sub->(@$args); 1 };
    if (!$ok) {
        my $err = "$@";
        $err =~ s/\s+\z//;
        reply({ id => $id, error => $err });
        next;
    }
    my $result = @result == 0 ? undef : @result == 1 ? $result[0] : \@result;
    # strings that look like numbers become JSON numbers
    if (defined $result && !ref $result && $result =~ /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][-+]?\d+)?\z/) {
        $result += 0;
    }
    send_reply($id, 'result', $result);
}

sub chars {
    my $v = shift;
    if (ref $v eq 'ARRAY') { return [map { chars($_) } @$v]; }
    if (ref $v eq 'HASH')  { return { map { (chars($_), chars($v->{$_})) } keys %$v }; }
    if (defined $v && !ref $v && !utf8::is_utf8($v) && $v =~ /[\x80-\xff]/) {
        my $c = $v;
        return utf8::decode($c) ? $c : $v;
    }
    return $v;
}
