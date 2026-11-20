use CsLibRef;
use VbLibRef;
use RingLibRef;
use JsLibRef;
use TsLibRef;
use CLibRef;
use CppLibRef;
use RustLibRef;
use FortLibRef;
use PerlLibRef;
use DartLibRef;
use JavaLibRef;
use PhpLibRef;
use PsLibRef;
use PyLibRef;
package PlCons;
use strict;
use warnings;
sub T_CsLib { return CsLib::Add(2, 3); }
sub T_VbLib { return VbLib::Add(2, 3); }
sub T_RingLib { return RingLib::Add(2, 3); }
sub T_JsLib { return JsLib::Add(2, 3); }
sub T_TsLib { return TsLib::Add(2, 3); }
sub T_CLib { return CLib::Add(2, 3); }
sub T_CppLib { return CppLib::Add(2, 3); }
sub T_RustLib { return RustLib::add(2, 3); }
sub T_FortLib { return FortLib::add(2, 3); }
sub T_PerlLib { return PerlLib::Add(2, 3); }
sub T_DartLib { return DartLib::Add(2, 3); }
sub T_JavaLib { return JavaLib::add(2, 3); }
sub T_PhpLib { return PhpLib::Add(2, 3); }
sub T_PsLib { return PsLib::Add(2, 3); }
sub T_PyLib { return PyLib::Add(2, 3); }
1;
