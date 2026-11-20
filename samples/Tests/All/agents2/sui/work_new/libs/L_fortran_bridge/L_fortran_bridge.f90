! Module L_fortran_bridge: 'use l_fortran_bridge' in a form's module to call its procedures.
! Functions with one argument named args can be called from every language through RAD Hub:
!     Python: radcall("L_fortran_bridge.add", 2, 3)      Fortran: r = radcall('L_fortran_bridge.add', '[2, 3]')
! args(i) is the text of argument i; return JSON text: rad_jnum(x), rad_jstr(s) or 'null'.
module l_fortran_bridge
  use radgui
  implicit none
contains

  function add(args) result(res)
    character(len=*), intent(in) :: args(:)
    character(len=:), allocatable :: res
    res = rad_jnum(rad_num(args(1)) + rad_num(args(2)))
  end function add

end module l_fortran_bridge
! Public functions of L_fortran_bridge go here - projects that reference L_fortran_bridge can call them.
