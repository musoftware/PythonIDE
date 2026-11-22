! RAD IDE GUI Bridge - Fortran helper module (copied into the project when it is built)
! The IDE draws the forms; this module talks to it over standard input/output
! (protocol: docs/CONTRACTS.md section 1).
!
!   call rad_set('lblOut', 'Caption', 'Hello')        set a property
!   s = rad_get('txtA', 'Text')                       read a property (text, trimmed)
!   call rad_call('lstLog', 'AddItem', 'line')        call a method
!   s = rad_callf('lstLog', 'List', '0')              call a method and read its result
!   call rad_msgbox('Hi');  s = rad_input('Name?');  call rad_show('Form2');  call rad_end()
!   x = rad_num(s);  s = rad_str(x)
!   r = radcall('Helpers.add', '[2, 3]')              RAD Hub: JSON args in, JSON result text out
!                                                     (needs radgui.c, linked automatically by the IDE)
module radgui
  use, intrinsic :: iso_c_binding, only: c_char, c_ptr, c_null_char, c_associated, c_f_pointer, c_int, c_size_t
  implicit none
  character(len=256)  :: rad_obj = '', rad_ev = ''
  character(len=1024) :: rad_args = ''
  integer, parameter :: RAD_LINE = 8192

  interface
    function c_radcall(name, args) bind(C, name='radcall') result(p)
      import :: c_char, c_ptr
      character(kind=c_char), dimension(*), intent(in) :: name, args
      type(c_ptr) :: p
    end function c_radcall
    function c_rad_error() bind(C, name='rad_error') result(p)
      import :: c_ptr
      type(c_ptr) :: p
    end function c_rad_error
    function c_strlen(p) bind(C, name='strlen') result(n)
      import :: c_ptr, c_size_t
      type(c_ptr), value :: p
      integer(c_size_t) :: n
    end function c_strlen
    ! worker side (implemented in radgui.c)
    function c_wk_next() bind(C, name='rad_wk_next') result(ok)
      import :: c_int
      integer(c_int) :: ok
    end function c_wk_next
    function c_wk_func() bind(C, name='rad_wk_func') result(p)
      import :: c_ptr
      type(c_ptr) :: p
    end function c_wk_func
    function c_wk_argc() bind(C, name='rad_wk_argc') result(n)
      import :: c_int
      integer(c_int) :: n
    end function c_wk_argc
    function c_wk_arg(i) bind(C, name='rad_wk_arg') result(p)
      import :: c_int, c_ptr
      integer(c_int), value :: i
      type(c_ptr) :: p
    end function c_wk_arg
    subroutine c_wk_reply(json) bind(C, name='rad_wk_reply')
      import :: c_char
      character(kind=c_char), dimension(*), intent(in) :: json
    end subroutine c_wk_reply
    subroutine c_wk_error(msg) bind(C, name='rad_wk_error')
      import :: c_char
      character(kind=c_char), dimension(*), intent(in) :: msg
    end subroutine c_wk_error
  end interface

contains

  ! ---------------------------------------------------------------- low level
  subroutine rad_readline(line, ok)
    character(len=*), intent(out) :: line
    logical, intent(out) :: ok
    integer :: ios, n
    line = ''
    read(*, '(A)', iostat=ios) line
    ok = (ios == 0)
    n = len_trim(line)
    if (n > 0) then
      if (line(n:n) == achar(13)) line(n:n) = ' '
    end if
  end subroutine rad_readline

  function rad_reply() result(value)
    character(len=:), allocatable :: value
    character(len=RAD_LINE) :: line
    logical :: ok
    call rad_readline(line, ok)
    value = trim(line)
  end function rad_reply

  subroutine rad_send(text)
    character(len=*), intent(in) :: text
    write(*, '(A)') text
    flush(6)
  end subroutine rad_send

  function rad_lower(s) result(r)
    character(len=*), intent(in) :: s
    character(len=len(s)) :: r
    integer :: i, c
    r = s
    do i = 1, len(s)
      c = iachar(s(i:i))
      if (c >= 65 .and. c <= 90) r(i:i) = achar(c + 32)
    end do
  end function rad_lower

  ! ---------------------------------------------------------------- events
  ! Wait for the next event. Returns .false. when the program must end.
  logical function rad_next_event()
    character(len=RAD_LINE) :: line
    logical :: ok
    integer :: p
    rad_obj = ''
    rad_ev = ''
    rad_args = ''
    call rad_readline(line, ok)
    rad_next_event = .false.
    if (.not. ok) return
    if (line(1:4) == 'QUIT') return
    rad_next_event = .true.
    if (line(1:6) /= 'EVENT ') return
    line = adjustl(line(7:))
    p = index(line, ' ')
    rad_obj = line(:p - 1)
    line = adjustl(line(p + 1:))
    p = index(line, ' ')
    if (p == 0) p = len_trim(line) + 1
    rad_ev = line(:p - 1)
    if (p < len(line)) rad_args = adjustl(line(p + 1:))
  end function rad_next_event

  ! word i (1-based) of rad_args: X Y Button KeyCode KeyChar
  function rad_arg(i) result(w)
    integer, intent(in) :: i
    character(len=:), allocatable :: w
    character(len=1024) :: s
    integer :: k, p
    s = adjustl(rad_args)
    do k = 1, i - 1
      p = index(trim(s), ' ')
      if (p == 0) then
        w = ''
        return
      end if
      s = adjustl(s(p + 1:))
    end do
    p = index(trim(s), ' ')
    if (p == 0) p = len_trim(s) + 1
    w = s(:p - 1)
  end function rad_arg

  subroutine rad_done()
    call rad_send('DONE')
  end subroutine rad_done

  subroutine rad_end()
    call rad_send('END')
  end subroutine rad_end

  subroutine rad_print(text)
    character(len=*), intent(in) :: text
    call rad_send(trim(text))
  end subroutine rad_print

  ! ---------------------------------------------------------------- GUI
  ! "ESC <command>" (radide/runtimes/bridge.py): \ newline CR escaped in the values, so multi-line text survives
  function rad_esc(s) result(r)
    character(len=*), intent(in) :: s
    character(len=:), allocatable :: r
    integer :: i
    r = ''
    do i = 1, len(s)
      if (s(i:i) == achar(92)) then
        r = r // achar(92) // achar(92)
      else if (s(i:i) == achar(10)) then
        r = r // achar(92) // 'n'
      else if (s(i:i) == achar(13)) then
        r = r // achar(92) // 'r'
      else
        r = r // s(i:i)
      end if
    end do
  end function rad_esc

  function rad_unesc(s) result(r)
    character(len=*), intent(in) :: s
    character(len=:), allocatable :: r
    integer :: i
    r = ''
    i = 1
    do while (i <= len(s))
      if (s(i:i) == achar(92) .and. i < len(s)) then
        if (s(i + 1:i + 1) == 'n') then
          r = r // achar(10)
          i = i + 2
          cycle
        else if (s(i + 1:i + 1) == 'r') then
          r = r // achar(13)
          i = i + 2
          cycle
        else if (s(i + 1:i + 1) == achar(92)) then
          r = r // achar(92)
          i = i + 2
          cycle
        end if
      end if
      r = r // s(i:i)
      i = i + 1
    end do
  end function rad_unesc

  ! Set a property:  call rad_set('lblResult', 'Caption', 'Hello')   (multi-line text: lines joined with achar(10))
  subroutine rad_set(obj, prop, value)
    character(len=*), intent(in) :: obj, prop, value
    if (index(value, achar(10)) > 0 .or. index(value, achar(13)) > 0) then
      call rad_send('ESC SET ' // trim(obj) // ' ' // trim(prop) // ' ' // rad_esc(trim(value)))
    else
      call rad_send('SET ' // trim(obj) // ' ' // trim(prop) // ' ' // trim(value))
    end if
  end subroutine rad_set

  ! Get a property as text:  s = rad_get('txtA', 'Text')   (lines of a multi-line text separated by achar(10))
  function rad_get(obj, prop) result(value)
    character(len=*), intent(in) :: obj, prop
    character(len=:), allocatable :: value
    call rad_send('ESC GET ' // trim(obj) // ' ' // trim(prop))
    value = rad_unesc(rad_reply())
  end function rad_get

  ! Call a method:  call rad_call('lstLog', 'AddItem', 'text')   (several args: separate with achar(9))
  subroutine rad_call(obj, method, arg)
    character(len=*), intent(in) :: obj, method, arg
    character(len=:), allocatable :: reply
    reply = rad_callf(obj, method, arg)
  end subroutine rad_call

  ! Call a method and return its result as text:  s = rad_callf('lstLog', 'List', '0')
  function rad_callf(obj, method, arg) result(reply)
    character(len=*), intent(in) :: obj, method, arg
    character(len=:), allocatable :: reply
    if (len_trim(arg) > 0) then
      call rad_send('CALL ' // trim(obj) // ' ' // trim(method) // ' ' // trim(arg))
    else
      call rad_send('CALL ' // trim(obj) // ' ' // trim(method))
    end if
    reply = rad_reply()
  end function rad_callf

  subroutine rad_msgbox(text)
    character(len=*), intent(in) :: text
    character(len=:), allocatable :: reply
    call rad_send('MSGBOX ' // trim(text))
    reply = rad_reply()
  end subroutine rad_msgbox

  function rad_input(prompt) result(value)
    character(len=*), intent(in) :: prompt
    character(len=:), allocatable :: value
    call rad_send('INPUT ' // trim(prompt))
    value = rad_reply()
  end function rad_input

  subroutine rad_show(form)
    character(len=*), intent(in) :: form
    call rad_send('SHOW ' // trim(form))
  end subroutine rad_show

  subroutine rad_hide(form)
    character(len=*), intent(in) :: form
    call rad_send('HIDE ' // trim(form))
  end subroutine rad_hide

  ! ---------------------------------------------------------------- numbers <-> text
  real(8) function rad_num(text)
    character(len=*), intent(in) :: text
    integer :: ios
    rad_num = 0d0
    if (len_trim(text) == 0) return
    read(text, *, iostat=ios) rad_num
    if (ios /= 0) rad_num = 0d0
  end function rad_num

  function rad_str(x) result(s)
    real(8), intent(in) :: x
    character(len=:), allocatable :: s
    character(len=64) :: b
    integer :: n, e
    if (x == aint(x) .and. abs(x) < 1d15) then
      write(b, '(I0)') int(x, 8)
    else
      write(b, '(ES23.15E3)') x
      b = adjustl(b)
      e = index(b, 'E')
      if (abs(x) >= 1d-4 .and. abs(x) < 1d15) then
        write(b, '(F0.12)') x
        b = adjustl(b)
        e = len_trim(b) + 1
      end if
      ! strip trailing zeros of the mantissa
      n = e - 1
      do while (n > 1 .and. b(n:n) == '0')
        n = n - 1
      end do
      if (b(n:n) == '.') n = n - 1
      b = b(:n) // b(e:)
      if (b(1:1) == '.') b = '0' // b
      if (b(1:2) == '-.') b = '-0' // b(2:)
    end if
    s = trim(adjustl(b))
  end function rad_str

  ! ---------------------------------------------------------------- C strings
  function rad_cstr(p) result(s)
    type(c_ptr), intent(in) :: p
    character(len=:), allocatable :: s
    character(kind=c_char), pointer :: a(:)
    integer :: n, i
    s = ''
    if (.not. c_associated(p)) return
    n = int(c_strlen(p))
    call c_f_pointer(p, a, [n])
    s = repeat(' ', n)                 ! (re)allocates s with length n
    do i = 1, n
      s(i:i) = a(i)
    end do
  end function rad_cstr

  ! ---------------------------------------------------------------- RAD Hub (cross-language calls)
  ! r = radcall('Helpers.add', '[2, 3]')  -> '5'  (JSON text; '' on error, see rad_error())
  function radcall(name, json_args) result(r)
    character(len=*), intent(in) :: name, json_args
    character(len=:), allocatable :: r
    r = rad_cstr(c_radcall(trim(name) // c_null_char, trim(json_args) // c_null_char))
  end function radcall

  function rad_error() result(r)
    character(len=:), allocatable :: r
    r = rad_cstr(c_rad_error())
  end function rad_error

  ! ---------------------------------------------------------------- JSON helpers
  function rad_jnum(x) result(s)          ! number -> JSON
    real(8), intent(in) :: x
    character(len=:), allocatable :: s
    s = rad_str(x)
  end function rad_jnum

  function rad_jstr(text) result(s)       ! text -> JSON string (trailing blanks removed)
    character(len=*), intent(in) :: text
    character(len=:), allocatable :: s
    integer :: i, c
    s = '"'
    do i = 1, len_trim(text)
      c = iachar(text(i:i))
      if (text(i:i) == '"' .or. text(i:i) == '\') then
        s = s // '\' // text(i:i)
      else if (c == 10) then
        s = s // '\n'
      else if (c == 13) then
        s = s // '\r'
      else if (c == 9) then
        s = s // '\t'
      else if (c < 32) then
        s = s // ' '
      else
        s = s // text(i:i)
      end if
    end do
    s = s // '"'
  end function rad_jstr

  function rad_jtext(json) result(s)      ! JSON string -> text ('"a\"b"' -> 'a"b'); others unchanged
    character(len=*), intent(in) :: json
    character(len=:), allocatable :: s
    character(len=:), allocatable :: j
    integer :: i
    j = trim(adjustl(json))
    if (len(j) < 2 .or. j(1:1) /= '"') then
      s = j
      return
    end if
    s = ''
    i = 2
    do while (i < len(j))
      if (j(i:i) == '\' .and. i + 1 < len(j)) then
        i = i + 1
        select case (j(i:i))
        case ('n')
          s = s // achar(10)
        case ('t')
          s = s // achar(9)
        case ('r')
          s = s // achar(13)
        case default
          s = s // j(i:i)
        end select
      else
        s = s // j(i:i)
      end if
      i = i + 1
    end do
  end function rad_jtext

  function rad_jbool(x) result(s)         ! logical -> JSON
    logical, intent(in) :: x
    character(len=:), allocatable :: s
    if (x) then
      s = 'true'
    else
      s = 'false'
    end if
  end function rad_jbool

  logical function rad_tbool(text)       ! argument text -> logical ('true', non-zero number)
    character(len=*), intent(in) :: text
    character(len=:), allocatable :: t
    t = rad_lower(trim(adjustl(text)))
    if (t == 'true' .or. t == '.true.' .or. t == 't') then
      rad_tbool = .true.
    else if (t == 'false' .or. t == '.false.' .or. t == '' .or. t == 'null') then
      rad_tbool = .false.
    else
      rad_tbool = rad_num(t) /= 0d0
    end if
  end function rad_tbool

  function rad_jany(x) result(s)          ! any scalar (integer, real, logical, text) -> JSON
    class(*), intent(in) :: x
    character(len=:), allocatable :: s
    select type (x)
    type is (integer)
      s = rad_str(real(x, 8))
    type is (integer(8))
      s = rad_str(real(x, 8))
    type is (real)
      s = rad_str(real(x, 8))
    type is (real(8))
      s = rad_str(x)
    type is (logical)
      s = rad_jbool(x)
    type is (character(len=*))
      s = rad_jstr(x)
    class default
      s = 'null'
    end select
  end function rad_jany

  ! ---------------------------------------------------------------- worker (used by generated code)
  ! Worker functions look like:
  !   function add(args) result(res)
  !     character(len=*), intent(in) :: args(:)       ! args(i): text of argument i (strings decoded)
  !     character(len=:), allocatable :: res          ! JSON text: rad_jnum(x), rad_jstr(s), 'null'
  logical function rad_wk_next(func, args)
    character(len=:), allocatable, intent(out) :: func
    character(len=RAD_LINE), allocatable, intent(out) :: args(:)
    integer :: i, n
    rad_wk_next = c_wk_next() /= 0
    if (.not. rad_wk_next) return
    func = rad_cstr(c_wk_func())
    n = c_wk_argc()
    allocate(args(n))
    do i = 1, n
      args(i) = rad_jtext(rad_cstr(c_wk_arg(int(i - 1, c_int))))
    end do
  end function rad_wk_next

  subroutine rad_wk_reply(json)
    character(len=*), intent(in) :: json
    call c_wk_reply(trim(json) // c_null_char)
  end subroutine rad_wk_reply

  subroutine rad_wk_fail(message)
    character(len=*), intent(in) :: message
    call c_wk_error(trim(message) // c_null_char)
  end subroutine rad_wk_fail

end module radgui
