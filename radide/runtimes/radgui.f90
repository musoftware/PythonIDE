! RAD IDE GUI Bridge - Fortran helper module (copied into the project when it is built)
! The IDE draws the forms; this module talks to it over standard input/output.
module radgui
  implicit none
  character(len=256)  :: rad_obj = '', rad_ev = ''
  character(len=1024) :: rad_args = ''
contains

  ! Wait for the next event. Returns .false. when the program must end.
  logical function rad_next_event()
    character(len=2048) :: line
    integer :: ios, p
    read(*, '(A)', iostat=ios) line
    if (ios /= 0) then
      rad_next_event = .false.
      return
    end if
    if (line(1:4) == 'QUIT') then
      rad_next_event = .false.
      return
    end if
    line = adjustl(line(7:))                 ! drop "EVENT "
    p = index(line, ' ')
    rad_obj = line(:p - 1)
    line = adjustl(line(p + 1:))
    p = index(line, ' ')
    if (p == 0) p = len_trim(line) + 1
    rad_ev = line(:p - 1)
    rad_args = adjustl(line(p + 1:))
    rad_next_event = .true.
  end function rad_next_event

  subroutine rad_send(text)
    character(len=*), intent(in) :: text
    write(*, '(A)') trim(text)
    flush(6)
  end subroutine rad_send

  subroutine rad_done()
    call rad_send('DONE')
  end subroutine rad_done

  subroutine rad_end()
    call rad_send('END')
  end subroutine rad_end

  ! Set a property:  call rad_set('lblResult', 'Caption', 'Hello')
  subroutine rad_set(obj, prop, value)
    character(len=*), intent(in) :: obj, prop, value
    call rad_send('SET ' // trim(obj) // ' ' // trim(prop) // ' ' // trim(value))
  end subroutine rad_set

  ! Get a property as text:  s = rad_get('txtA', 'Text')
  function rad_get(obj, prop) result(value)
    character(len=*), intent(in) :: obj, prop
    character(len=1024) :: value
    call rad_send('GET ' // trim(obj) // ' ' // trim(prop))
    read(*, '(A)') value
  end function rad_get

  ! Call a method:  call rad_call('lstLog', 'AddItem', 'text')
  subroutine rad_call(obj, method, arg)
    character(len=*), intent(in) :: obj, method, arg
    character(len=1024) :: reply
    call rad_send('CALL ' // trim(obj) // ' ' // trim(method) // ' ' // trim(arg))
    read(*, '(A)') reply
  end subroutine rad_call

  subroutine rad_msgbox(text)
    character(len=*), intent(in) :: text
    character(len=64) :: reply
    call rad_send('MSGBOX ' // trim(text))
    read(*, '(A)') reply
  end subroutine rad_msgbox

  ! Number <-> text helpers
  real(8) function rad_num(text)
    character(len=*), intent(in) :: text
    integer :: ios
    read(text, *, iostat=ios) rad_num
    if (ios /= 0) rad_num = 0d0
  end function rad_num

  function rad_str(x) result(s)
    real(8), intent(in) :: x
    character(len=64) :: s
    if (x == aint(x) .and. abs(x) < 1d15) then
      write(s, '(I0)') int(x, 8)
    else
      write(s, '(G0.10)') x
    end if
    s = adjustl(s)
  end function rad_str

end module radgui
