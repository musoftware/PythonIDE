! (c) 2026 Musoftware - https://musoftwares.com - MIT License
!
! Calculator - a pocket calculator in modern Fortran (RAD IDE GUI Bridge, module radgui;
! Build > Publish makes a native Win32 exe with gfortran + radforms, no Python).
!
! Shows: many buttons sharing one routine, keyboard input on the form (KeyPress: rad_arg(4) = key name,
! rad_arg(5) = character), error handling (division by zero, square root of a negative number, overflow)
! without exceptions, real(8) arithmetic, a memory register, Fortran strings (trim / adjustl / index).
module frmcalc_code
  use radgui
  implicit none
  character(len=64) :: display = '0'     ! what is typed / the last result
  character(len=64) :: expr = ''         ! "12 +" shown above the display
  real(8) :: acc = 0d0, memory = 0d0
  character(len=1) :: op = ' '           ! pending operator or blank
  logical :: fresh = .true., failed = .false.
contains

  subroutine refresh()
    call rad_set('lblDisplay', 'Caption', trim(display))
    call rad_set('lblExpr', 'Caption', trim(expr))
    if (memory /= 0d0) then
      call rad_set('lblMemory', 'Caption', 'M')
    else
      call rad_set('lblMemory', 'Caption', ' ')
    end if
  end subroutine refresh

  subroutine fail(why)
    character(len=*), intent(in) :: why
    display = 'Error: ' // why
    expr = ''
    failed = .true.
    op = ' '
    fresh = .true.
  end subroutine fail

  ! the display shows x (or an overflow error)
  subroutine show_number(x)
    real(8), intent(in) :: x
    if (x /= x .or. abs(x) > 1d15) then          ! x /= x: NaN
      call fail('overflow')
    else
      display = rad_str(x)
    end if
  end subroutine show_number

  subroutine digit(d)
    character(len=*), intent(in) :: d
    if (failed) call clear_all()
    if (fresh) then
      display = merge('0', ' ', d == '.')
      fresh = .false.
    end if
    if (d == '.' .and. index(display, '.') > 0) return
    if (len_trim(display) >= 16) return
    if (trim(display) == '0' .and. d /= '.') display = ''
    display = trim(display) // d
    call refresh()
  end subroutine digit

  ! apply the pending operator; .false. = an error was shown
  logical function apply_op()
    real(8) :: x
    x = rad_num(trim(display))
    apply_op = .true.
    select case (op)
    case ('+')
      acc = acc + x
    case ('-')
      acc = acc - x
    case ('*')
      acc = acc * x
    case ('/')
      if (x == 0d0) then
        call fail('division by zero')
        apply_op = .false.
        return
      end if
      acc = acc / x
    case default
      acc = x
    end select
    call show_number(acc)
    apply_op = .not. failed
  end function apply_op

  subroutine operation(o)
    character(len=1), intent(in) :: o
    if (failed) return
    if (.not. fresh .or. op == ' ') then
      if (.not. apply_op()) then
        call refresh()
        return
      end if
    end if
    op = o
    fresh = .true.
    expr = rad_str(acc) // ' ' // o
    call refresh()
  end subroutine operation

  subroutine equals()
    if (failed .or. op == ' ') return
    if (apply_op()) then
      op = ' '
      fresh = .true.
      expr = ''
    end if
    call refresh()
  end subroutine equals

  subroutine clear_all()
    display = '0'
    expr = ''
    acc = 0d0
    op = ' '
    fresh = .true.
    failed = .false.
    call refresh()
  end subroutine clear_all

  subroutine back_space()
    integer :: n
    if (failed .or. fresh) return
    n = len_trim(display)
    if (n <= 1 .or. (n == 2 .and. display(1:1) == '-')) then
      display = '0'
    else
      display = display(1:n - 1)
    end if
    call refresh()
  end subroutine back_space

  ! ------------------------------------------------------------------ events
  subroutine frmCalc_Load()
    call refresh()
  end subroutine frmCalc_Load

  subroutine btn0_Click()
    call digit('0')
  end subroutine btn0_Click
  subroutine btn1_Click()
    call digit('1')
  end subroutine btn1_Click
  subroutine btn2_Click()
    call digit('2')
  end subroutine btn2_Click
  subroutine btn3_Click()
    call digit('3')
  end subroutine btn3_Click
  subroutine btn4_Click()
    call digit('4')
  end subroutine btn4_Click
  subroutine btn5_Click()
    call digit('5')
  end subroutine btn5_Click
  subroutine btn6_Click()
    call digit('6')
  end subroutine btn6_Click
  subroutine btn7_Click()
    call digit('7')
  end subroutine btn7_Click
  subroutine btn8_Click()
    call digit('8')
  end subroutine btn8_Click
  subroutine btn9_Click()
    call digit('9')
  end subroutine btn9_Click
  subroutine btnDot_Click()
    call digit('.')
  end subroutine btnDot_Click
  subroutine btnAdd_Click()
    call operation('+')
  end subroutine btnAdd_Click
  subroutine btnSub_Click()
    call operation('-')
  end subroutine btnSub_Click
  subroutine btnMul_Click()
    call operation('*')
  end subroutine btnMul_Click
  subroutine btnDiv_Click()
    call operation('/')
  end subroutine btnDiv_Click
  subroutine btnEquals_Click()
    call equals()
  end subroutine btnEquals_Click
  subroutine btnClear_Click()
    call clear_all()
  end subroutine btnClear_Click
  subroutine btnBack_Click()
    call back_space()
  end subroutine btnBack_Click

  subroutine btnSign_Click()
    if (failed) return
    call show_number(-rad_num(trim(display)))
    call refresh()
  end subroutine btnSign_Click

  subroutine btnSqrt_Click()
    real(8) :: x
    if (failed) return
    x = rad_num(trim(display))
    if (x < 0d0) then
      call fail('negative square root')
    else
      call show_number(sqrt(x))
      fresh = .true.
    end if
    call refresh()
  end subroutine btnSqrt_Click

  subroutine btnPercent_Click()
    real(8) :: x
    if (failed) return
    x = rad_num(trim(display))
    if (op /= ' ') then
      call show_number(acc * x / 100d0)
    else
      call show_number(x / 100d0)
    end if
    call refresh()
  end subroutine btnPercent_Click

  subroutine btnMC_Click()
    memory = 0d0
    call refresh()
  end subroutine btnMC_Click

  subroutine btnMR_Click()
    if (failed) return
    call show_number(memory)
    fresh = .true.
    call refresh()
  end subroutine btnMR_Click

  subroutine btnMPlus_Click()
    if (failed) return
    memory = memory + rad_num(trim(display))
    fresh = .true.
    call refresh()
  end subroutine btnMPlus_Click

  ! KeyPress: rad_arg(4) = Windows key code (13 Enter, 27 Esc, 8 Backspace), rad_arg(5) = the character
  subroutine frmCalc_KeyPress()
    character(len=:), allocatable :: key, ch
    key = rad_arg(4)
    ch = rad_arg(5)
    if (len(ch) == 1 .and. index('0123456789', ch) > 0) then
      call digit(ch)
    else if (ch == '.' .or. ch == ',') then
      call digit('.')
    else if (len(ch) == 1 .and. index('+-*/', ch) > 0) then
      call operation(ch)
    else if (ch == '=' .or. key == '13' .or. key == 'Return') then
      call equals()
    else if (key == '27' .or. key == 'Escape') then
      call clear_all()
    else if (key == '8' .or. key == 'BackSpace') then
      call back_space()
    end if
  end subroutine frmCalc_KeyPress

end module frmcalc_code
