! Fortran math library
module mathf
  use radgui
  implicit none
  private
  public :: add, greet, twice, is_pos, show, legacy, scale, hyp
  interface
    function ext(x) result(y)
      real(8) :: x, y
    end function ext
  end interface
contains

  ! Add two numbers
  real(8) function add(a, b)
    real(8), intent(in) :: a, b
    add = a + b
  end function add

  ! Greets someone
  function greet(who) result(res)
    character(len=*), intent(in) :: who
    character(len=:), allocatable :: res
    res = 'Hello, ' // trim(who) // '!'
  end function greet

  integer function twice(n)
    integer, intent(in) :: n
    twice = 2 * n
  end function twice

  logical function is_pos(x)
    real, intent(in) :: x
    is_pos = x > 0
  end function is_pos

  subroutine show(msg)
    character(len=*), intent(in) :: msg
    write(0, *) 'show: ', trim(msg)
  end subroutine show

  subroutine scale(x)        ! intent(inout): not exported
    real(8), intent(inout) :: x
    x = 2 * x
  end subroutine scale

  function legacy(args) result(res)
    character(len=*), intent(in) :: args(:)
    character(len=:), allocatable :: res
    res = rad_jnum(rad_num(args(1)) * rad_num(args(2)))
  end function legacy

  pure real(8) function hyp(a, &
                            b)
    real(8), intent(in) :: a, b
    hyp = sqrt(a * a + b * b)
  contains
    pure real(8) function inner(x)
      real(8), intent(in) :: x
      inner = x
    end function inner
  end function hyp

  integer function hidden(n)
    integer, intent(in) :: n
    hidden = n
  end function hidden

end module mathf
