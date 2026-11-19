! Class library FortLib. Public procedures of module fortlib can be called by the projects that
! reference FortLib as code of their own language (Python: FortLib.add(2, 3), ...).
! Use 'private :: name' (or a 'private' statement + 'public :: ...') to hide procedures.
module fortlib
  use radgui
  implicit none
contains

  ! Add two numbers. Public module procedures (functions and subroutines) with integer,
  ! real, real(8), logical or character arguments can be called by every project that
  ! references this one.
  real(8) function add(a, b)
    real(8), intent(in) :: a, b
    add = a + b
  end function add

end module fortlib
