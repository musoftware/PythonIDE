module fcons
  use radgui
  use cslib_ref
  use vblib_ref
  use ringlib_ref
  use jslib_ref
  use tslib_ref
  use clib_ref
  use cpplib_ref
  use rustlib_ref
  use fortlib_ref
  use perllib_ref
  use dartlib_ref
  use javalib_ref
  use phplib_ref
  use pslib_ref
  use pylib_ref
  implicit none
contains
  real(8) function t_cslib()
    t_cslib = CsLib_Add_num(2d0, 3d0)
  end function t_cslib
  real(8) function t_vblib()
    t_vblib = VbLib_Add_num(2d0, 3d0)
  end function t_vblib
  real(8) function t_ringlib()
    t_ringlib = RingLib_Add_num(2d0, 3d0)
  end function t_ringlib
  real(8) function t_jslib()
    t_jslib = JsLib_Add_num(2d0, 3d0)
  end function t_jslib
  real(8) function t_tslib()
    t_tslib = TsLib_Add_num(2d0, 3d0)
  end function t_tslib
  real(8) function t_clib()
    t_clib = CLib_Add_num(2d0, 3d0)
  end function t_clib
  real(8) function t_cpplib()
    t_cpplib = CppLib_Add_num(2d0, 3d0)
  end function t_cpplib
  real(8) function t_rustlib()
    t_rustlib = RustLib_add_num(2d0, 3d0)
  end function t_rustlib
  real(8) function t_fortlib()
    t_fortlib = FortLib_add_num(2d0, 3d0)
  end function t_fortlib
  real(8) function t_perllib()
    t_perllib = PerlLib_Add_num(2d0, 3d0)
  end function t_perllib
  real(8) function t_dartlib()
    t_dartlib = DartLib_Add_num(2d0, 3d0)
  end function t_dartlib
  real(8) function t_javalib()
    t_javalib = JavaLib_add_num(2d0, 3d0)
  end function t_javalib
  real(8) function t_phplib()
    t_phplib = PhpLib_Add_num(2d0, 3d0)
  end function t_phplib
  real(8) function t_pslib()
    t_pslib = PsLib_Add_num(2d0, 3d0)
  end function t_pslib
  real(8) function t_pylib()
    t_pylib = PyLib_Add_num(2d0, 3d0)
  end function t_pylib
end module fcons
