module fcons
  use radgui
  use pylib_ref
  implicit none
contains
  real(8) function test()
    test = PyLib_Add_num(2d0, 3d0)
  end function test
end module fcons
