
module appf
  use radgui
  use pylib_ref
  implicit none
contains
  function run(who) result(res)
    character(len=*), intent(in) :: who
    character(len=:), allocatable :: res
    res = PyLib_Hello_str(trim(who)) // ' | ' // rad_str(PyLib_Mul_num(6, 7.5d0)) // ' | ' // &
          PyLib_Mul('ab', 2) // ' | ' // PyLib_Mul_str(.true., 3)
  end function run
end module appf
