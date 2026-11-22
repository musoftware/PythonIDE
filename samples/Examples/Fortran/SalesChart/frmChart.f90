! (c) 2026 Musoftware - https://musoftwares.com - MIT License
!
! Sales Chart - a bar chart drawn with Panels, in Fortran (RAD IDE GUI Bridge, module radgui;
! Build > Publish makes a native Win32 exe with gfortran + radforms).
!
! Each bar is a Panel whose Top / Height follow its value (0..100). Shows: arrays and array intrinsics
! (sum, maxloc), MouseDown with coordinates (rad_arg(1) = X, rad_arg(2) = Y: click in the chart to set a bar),
! a Timer animation with the speed from a TrackBar, the ColorDialog, NumericUpDown + ComboBox, CSV file I/O
! with iostat error handling, random_number.
module frmchart_code
  use radgui
  implicit none
  integer, parameter :: BARS = 6, BASE = 280, BAR_W = 44, FIRST_X = 14, STEP_X = 60
  real(8), parameter :: SCALE = 2.4d0                  ! pixels per unit: 100 -> 240 px
  character(len=3), parameter :: MONTHS(BARS) = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
  real(8) :: values(BARS) = [50d0, 65d0, 40d0, 80d0, 70d0, 90d0]
  real(8) :: drawn(BARS) = 0d0
  character(len=16) :: bar_color = '#3B7DD8'
contains

  function bar_name(prefix, i) result(name)
    character(len=*), intent(in) :: prefix
    integer, intent(in) :: i
    character(len=:), allocatable :: name
    character(len=4) :: n
    write(n, '(I0)') i
    name = prefix // trim(n)
  end function bar_name

  subroutine draw_bar(i)
    integer, intent(in) :: i
    integer :: h
    h = max(1, nint(drawn(i) * SCALE))
    call rad_set(bar_name('pnlBar', i), 'Top', rad_str(real(BASE - h, 8)))
    call rad_set(bar_name('pnlBar', i), 'Height', rad_str(real(h, 8)))
    call rad_set(bar_name('lblVal', i), 'Top', rad_str(real(BASE - h - 20, 8)))
    call rad_set(bar_name('lblVal', i), 'Caption', rad_str(real(nint(drawn(i)), 8)))
  end subroutine draw_bar

  subroutine update_stats()
    integer :: best
    character(len=200) :: text
    best = maxloc(values, 1)
    write(text, '(A,A,A,F0.1,A,A,A,A,A)') 'Total: ', rad_str(sum(values)), '   Average: ', sum(values) / BARS, &
      '   Best month: ', MONTHS(best), ' (', rad_str(values(best)), ')'
    call rad_set('lblStats', 'Caption', trim(text))
  end subroutine update_stats

  ! show the data: animated when the check box is on, at once otherwise
  subroutine redraw()
    integer :: i
    call update_stats()
    if (rad_get('chkAnimate', 'Value') == '1') then
      call rad_set('tmrAnim', 'Enabled', 'True')
      return
    end if
    do i = 1, BARS
      drawn(i) = values(i)
      call draw_bar(i)
    end do
  end subroutine redraw

  subroutine set_value(i, v)
    integer, intent(in) :: i
    real(8), intent(in) :: v
    values(i) = anint(min(100d0, max(0d0, v)))
    call rad_set('cboMonth', 'ListIndex', rad_str(real(i - 1, 8)))
    call rad_set('nudValue', 'Value', rad_str(values(i)))
    call redraw()
  end subroutine set_value

  ! ------------------------------------------------------------------ events
  subroutine frmChart_Load()
    call rad_set('chkAnimate', 'Value', '1')
    call rad_set('cboMonth', 'ListIndex', '0')
    call redraw()
  end subroutine frmChart_Load

  subroutine tmrAnim_Tick()
    real(8) :: speed, d
    integer :: i
    logical :: moving
    speed = rad_num(rad_get('trkSpeed', 'Value'))
    moving = .false.
    do i = 1, BARS
      d = values(i) - drawn(i)
      if (d == 0d0) cycle
      drawn(i) = drawn(i) + max(-speed, min(speed, d))
      call draw_bar(i)
      moving = .true.
    end do
    if (.not. moving) call rad_set('tmrAnim', 'Enabled', 'False')
  end subroutine tmrAnim_Tick

  subroutine btnSet_Click()
    integer :: i
    i = nint(rad_num(rad_get('cboMonth', 'ListIndex'))) + 1
    if (i < 1) then
      call rad_msgbox('Choose a month first.')
      return
    end if
    call set_value(i, rad_num(rad_get('nudValue', 'Value')))
  end subroutine btnSet_Click

  subroutine cboMonth_SelectedIndexChanged()
    integer :: i
    i = nint(rad_num(rad_get('cboMonth', 'ListIndex'))) + 1
    if (i >= 1 .and. i <= BARS) call rad_set('nudValue', 'Value', rad_str(values(i)))
  end subroutine cboMonth_SelectedIndexChanged

  subroutine btnRandom_Click()
    real(8) :: r(BARS)
    call random_number(r)
    values = anint(10d0 + r * 90d0)
    call redraw()
  end subroutine btnRandom_Click

  subroutine btnColor_Click()
    integer :: i
    call rad_set('dlgColor', 'Color', trim(bar_color))
    if (rad_callf('dlgColor', 'ShowColor', '') /= 'OK') return
    bar_color = rad_get('dlgColor', 'Color')
    do i = 1, BARS
      call rad_set(bar_name('pnlBar', i), 'BackColor', trim(bar_color))
    end do
  end subroutine btnColor_Click

  ! MouseDown args: X Y Button ... (relative to pnlChart): X picks the bar, Y the value
  subroutine pnlChart_MouseDown()
    integer :: x, y, i
    x = nint(rad_num(rad_arg(1)))
    y = nint(rad_num(rad_arg(2)))
    i = (x - FIRST_X + (STEP_X - BAR_W) / 2) / STEP_X + 1
    if (i >= 1 .and. i <= BARS) call set_value(i, real(BASE - y, 8) / SCALE)
  end subroutine pnlChart_MouseDown

  subroutine btnSave_Click()
    integer :: u, i, ios
    open(newunit=u, file='sales.csv', status='replace', action='write', iostat=ios)
    if (ios /= 0) then
      call rad_msgbox('Cannot write sales.csv')
      return
    end if
    write(u, '(A)') 'month,value'
    do i = 1, BARS
      write(u, '(A,A,A)') MONTHS(i), ',', rad_str(values(i))
    end do
    close(u)
    call rad_msgbox('Saved sales.csv')
  end subroutine btnSave_Click

  subroutine btnLoad_Click()
    integer :: u, i, ios, comma
    character(len=100) :: line
    open(newunit=u, file='sales.csv', status='old', action='read', iostat=ios)
    if (ios /= 0) then
      call rad_msgbox('sales.csv not found - press Save first.')
      return
    end if
    do
      read(u, '(A)', iostat=ios) line
      if (ios /= 0) exit
      comma = index(line, ',')
      if (comma == 0) cycle
      do i = 1, BARS
        if (line(:comma - 1) == MONTHS(i)) values(i) = rad_num(trim(line(comma + 1:)))
      end do
    end do
    close(u)
    call redraw()
  end subroutine btnLoad_Click

  subroutine chkAnimate_CheckedChanged()
    call redraw()
  end subroutine chkAnimate_CheckedChanged

end module frmchart_code
