! (c) 2026 Musoftware - https://musoftwares.com - MIT License
!
! app_settings - the settings of the Greeting Cards example (a code module shared by its three forms; the
! IDE compiles it before the forms that "use" it), stored in settings.ini (key=value lines, UTF-8).
module app_settings
  implicit none
  character(len=80) :: user_name = 'Friend'
  logical :: arabic = .false.
  integer :: font_size = 11
  logical :: formal = .false.
  character(len=*), parameter :: SETTINGS_FILE = 'settings.ini'
contains

  subroutine load_settings()
    integer :: u, ios, eq, n
    character(len=200) :: line, key, value
    open(newunit=u, file=SETTINGS_FILE, status='old', action='read', iostat=ios)
    if (ios /= 0) return                       ! no file yet: the defaults
    do
      read(u, '(A)', iostat=ios) line
      if (ios /= 0) exit
      eq = index(line, '=')
      if (eq < 2 .or. line(1:1) == '#' .or. line(1:1) == '[') cycle
      key = adjustl(line(:eq - 1))
      value = line(eq + 1:)
      select case (trim(key))
      case ('user')
        if (len_trim(value) > 0) user_name = value
      case ('language')
        arabic = trim(value) /= 'English'
      case ('font_size')
        read(value, *, iostat=ios) n
        if (ios == 0 .and. n >= 8 .and. n <= 24) font_size = n
      case ('formal')
        formal = trim(value) == '1'
      end select
    end do
    close(u)
  end subroutine load_settings

  logical function save_settings()
    integer :: u, ios
    open(newunit=u, file=SETTINGS_FILE, status='replace', action='write', iostat=ios)
    save_settings = ios == 0
    if (.not. save_settings) return
    write(u, '(A)') '[GreetingCards]'
    write(u, '(A)') 'user=' // trim(user_name)
    if (arabic) then
      write(u, '(A)') 'language=العربية'
    else
      write(u, '(A)') 'language=English'
    end if
    write(u, '(A,I0)') 'font_size=', font_size
    write(u, '(A,I0)') 'formal=', merge(1, 0, formal)
    close(u)
  end function save_settings

end module app_settings
