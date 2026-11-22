! (c) 2026 Musoftware - https://musoftwares.com - MIT License
!
! WordStats - a console tool in Fortran: lines / words / characters of text files and the most frequent words.
!
!     WordStats [--top N] [--out report.txt] file1.txt [file2.txt ...]
!
! Without files it reads sample.txt next to the program (F5 in the IDE shows a result).
! Exit codes: 0 OK, 1 wrong arguments, 2 a file could not be read, 3 the report could not be written.
! Shows: a RAD IDE console project (no forms + a module with its own "program"), get_command_argument,
! open/read with iostat, derived types, a simple sort, error stop codes.
module word_table
  implicit none
  integer, parameter :: MAX_WORDS = 5000, WORD_LEN = 40
  type :: entry_t
    character(len=WORD_LEN) :: word = ''
    integer :: count = 0
  end type entry_t
  type(entry_t) :: words(MAX_WORDS)
  integer :: nwords = 0
contains

  subroutine add_word(w)
    character(len=*), intent(in) :: w
    integer :: i
    do i = 1, nwords
      if (words(i)%word == w) then
        words(i)%count = words(i)%count + 1
        return
      end if
    end do
    if (nwords < MAX_WORDS) then
      nwords = nwords + 1
      words(nwords)%word = w
      words(nwords)%count = 1
    end if
  end subroutine add_word

  subroutine sort_words()                 ! most frequent first, then alphabetical (insertion sort)
    integer :: i, j
    type(entry_t) :: t
    do i = 2, nwords
      t = words(i)
      j = i - 1
      do while (j >= 1)
        if (words(j)%count > t%count .or. (words(j)%count == t%count .and. words(j)%word <= t%word)) exit
        words(j + 1) = words(j)
        j = j - 1
      end do
      words(j + 1) = t
    end do
  end subroutine sort_words

  logical function word_char(c)
    character(len=1), intent(in) :: c
    word_char = (c >= 'a' .and. c <= 'z') .or. (c >= 'A' .and. c <= 'Z') .or. (c >= '0' .and. c <= '9') &
                .or. c == "'" .or. iachar(c) >= 128
  end function word_char

  character function lower(c)
    character(len=1), intent(in) :: c
    if (c >= 'A' .and. c <= 'Z') then
      lower = achar(iachar(c) + 32)
    else
      lower = c
    end if
  end function lower
end module word_table

program wordstats
  use word_table
  implicit none
  character(len=512) :: arg, files(64), out_path, line
  character(len=WORD_LEN) :: w
  integer :: nfiles, top, i, k, n, u, out, ios, nl, nw, nc, tl, tw, tc, wl
  logical :: failed

  nfiles = 0
  top = 10
  out_path = ''
  failed = .false.
  i = 1
  do while (i <= command_argument_count())
    call get_command_argument(i, arg)
    select case (trim(arg))
    case ('--help', '-h')
      print '(A)', 'usage: WordStats [--top N] [--out report.txt] file1.txt [file2.txt ...]'
      stop
    case ('--top')
      i = i + 1
      call get_command_argument(i, arg)
      read(arg, *, iostat=ios) top
      if (ios /= 0 .or. top <= 0) then
        write(0, '(A)') '--top needs a positive number'
        error stop 1
      end if
    case ('--out')
      i = i + 1
      call get_command_argument(i, out_path)
    case default
      if (arg(1:1) == '-') then
        write(0, '(A)') 'unknown option ' // trim(arg)
        error stop 1
      end if
      nfiles = nfiles + 1
      files(nfiles) = arg
    end select
    i = i + 1
  end do
  if (nfiles == 0) then
    nfiles = 1
    files(1) = 'sample.txt'
  end if

  out = 6                                  ! standard output
  if (len_trim(out_path) > 0) then
    open(newunit=out, file=trim(out_path), status='replace', action='write', iostat=ios)
    if (ios /= 0) then
      write(0, '(A)') 'cannot write ' // trim(out_path)
      error stop 3
    end if
  end if

  tl = 0; tw = 0; tc = 0
  write(out, '(A)') '   lines    words    chars  file'
  do k = 1, nfiles
    open(newunit=u, file=trim(files(k)), status='old', action='read', iostat=ios)
    if (ios /= 0) then
      write(0, '(A)') 'cannot read ' // trim(files(k))
      failed = .true.
      cycle
    end if
    nl = 0; nw = 0; nc = 0
    do
      read(u, '(A)', iostat=ios) line
      if (ios /= 0) exit
      nl = nl + 1
      wl = 0
      do n = 1, len_trim(line)
        if (iand(iachar(line(n:n)), 192) /= 128 .and. line(n:n) /= achar(13)) nc = nc + 1   ! UTF-8 characters
        if (word_char(line(n:n))) then
          if (wl < WORD_LEN) then
            wl = wl + 1
            w(wl:wl) = lower(line(n:n))
          end if
        else if (wl > 0) then
          call add_word(w(:wl))
          nw = nw + 1
          wl = 0
        end if
      end do
      if (wl > 0) then
        call add_word(w(:wl))
        nw = nw + 1
      end if
    end do
    close(u)
    write(out, '(I8,1X,I8,1X,I8,2X,A)') nl, nw, nc, trim(files(k))
    tl = tl + nl; tw = tw + nw; tc = tc + nc
  end do
  if (nfiles > 1) write(out, '(I8,1X,I8,1X,I8,2X,A)') tl, tw, tc, 'total'

  call sort_words()
  write(out, '(/,A,I0,A)') 'Top ', top, ' words:'
  do i = 1, min(top, nwords)
    write(out, '(I4,A,A20,1X,I0)') i, '. ', words(i)%word, words(i)%count
  end do
  if (out /= 6) then
    close(out)
    print '(A)', 'report written to ' // trim(out_path)
  end if
  if (failed) error stop 2
end program wordstats
