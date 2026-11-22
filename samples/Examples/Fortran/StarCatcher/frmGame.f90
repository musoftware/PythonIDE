! (c) 2026 Musoftware - https://musoftwares.com - MIT License
!
! Star Catcher - an arcade game in Fortran (RAD IDE GUI Bridge, module radgui;
! Build > Publish makes a native Win32 exe with gfortran + radforms).
!
! Catch the yellow stars (+10), dodge the red rocks (-1 life); every 5 stars the game gets faster.
! Shows: a derived type (sprite) with a collision function, a Timer game loop, KeyDown / KeyUp on the form
! (rad_arg(4) = key name), MouseMove on a Panel (rad_arg(1) = X), moving controls with Left / Top,
! random_number, a best score in a file (newunit / iostat).
module frmgame_code
  use radgui
  implicit none
  integer, parameter :: FIELD_W = 456, FIELD_H = 330

  type :: sprite
    integer :: x, y, w, h
  end type sprite

  type(sprite) :: player = sprite(190, 300, 76, 14)
  type(sprite) :: star = sprite(100, -24, 24, 24)
  type(sprite) :: rock = sprite(300, -24, 24, 24)
  integer :: star_speed = 4, rock_speed = 5, score = 0, lives = 3, best = 0
  logical :: left_key = .false., right_key = .false., running = .false., paused = .false.
contains

  logical function hits(a, b)
    type(sprite), intent(in) :: a, b
    hits = a%x < b%x + b%w .and. b%x < a%x + a%w .and. a%y < b%y + b%h .and. b%y < a%y + a%h
  end function hits

  integer function rnd(n)
    integer, intent(in) :: n
    real(8) :: r
    call random_number(r)
    rnd = int(r * n)
  end function rnd

  function num(i) result(s)
    integer, intent(in) :: i
    character(len=:), allocatable :: s
    s = rad_str(real(i, 8))
  end function num

  subroutine show_score()
    call rad_set('lblScore', 'Caption', 'Score: ' // num(score))
    call rad_set('lblLives', 'Caption', 'Lives: ' // num(lives))
    call rad_set('lblBest', 'Caption', 'Best: ' // num(best))
  end subroutine show_score

  subroutine message(text)
    character(len=*), intent(in) :: text
    call rad_set('lblMessage', 'Caption', text)
    if (len_trim(text) > 0) then
      call rad_set('lblMessage', 'Visible', 'True')
    else
      call rad_set('lblMessage', 'Visible', 'False')
    end if
  end subroutine message

  subroutine game_over()
    integer :: u, ios
    running = .false.
    call rad_set('tmrGame', 'Enabled', 'False')
    if (score > best) then
      best = score
      open(newunit=u, file='starcatcher.best', status='replace', action='write', iostat=ios)
      if (ios == 0) then
        write(u, '(I0)') best
        close(u)
      end if
      call message('Game over - new best score ' // num(score) // '!')
    else
      call message('Game over - score ' // num(score) // '. Press Start.')
    end if
    call show_score()
    call rad_set('btnStart', 'Caption', 'Start')
  end subroutine game_over

  ! ------------------------------------------------------------------ events
  subroutine frmGame_Load()
    integer :: u, ios
    call random_seed()
    open(newunit=u, file='starcatcher.best', status='old', action='read', iostat=ios)
    if (ios == 0) then
      read(u, *, iostat=ios) best
      if (ios /= 0) best = 0
      close(u)
    end if
    call show_score()
  end subroutine frmGame_Load

  subroutine btnStart_Click()
    score = 0
    lives = 3
    star_speed = 4
    rock_speed = 5
    player%x = (FIELD_W - player%w) / 2
    star%x = rnd(FIELD_W - star%w)
    star%y = -star%h
    rock%x = rnd(FIELD_W - rock%w)
    rock%y = -rock%h - rnd(200)
    running = .true.
    paused = .false.
    call message('')
    call show_score()
    call rad_set('btnStart', 'Caption', 'Restart')
    call rad_set('tmrGame', 'Enabled', 'True')
  end subroutine btnStart_Click

  subroutine btnPause_Click()
    if (.not. running) return
    paused = .not. paused
    if (paused) then
      call rad_set('tmrGame', 'Enabled', 'False')
      call rad_set('btnPause', 'Caption', 'Resume')
      call message('Paused - press P or Resume')
    else
      call rad_set('tmrGame', 'Enabled', 'True')
      call rad_set('btnPause', 'Caption', 'Pause')
      call message('')
    end if
  end subroutine btnPause_Click

  ! one frame of the game loop
  subroutine tmrGame_Tick()
    if (.not. running) return
    if (left_key) player%x = player%x - 9
    if (right_key) player%x = player%x + 9
    player%x = max(0, min(FIELD_W - player%w, player%x))
    star%y = star%y + star_speed
    rock%y = rock%y + rock_speed
    if (hits(star, player)) then
      score = score + 10
      if (mod(score, 50) == 0) then
        star_speed = star_speed + 1
        rock_speed = rock_speed + 1
      end if
      star%x = rnd(FIELD_W - star%w)
      star%y = -star%h
      call show_score()
    else if (star%y > FIELD_H) then
      star%x = rnd(FIELD_W - star%w)
      star%y = -star%h
    end if
    if (hits(rock, player)) then
      lives = lives - 1
      rock%x = rnd(FIELD_W - rock%w)
      rock%y = -rock%h - rnd(200)
      call show_score()
      if (lives <= 0) then
        call game_over()
        return
      end if
    else if (rock%y > FIELD_H) then
      rock%x = rnd(FIELD_W - rock%w)
      rock%y = -rock%h - rnd(200)
    end if
    call rad_set('pnlPlayer', 'Left', num(player%x))
    call rad_set('lblStar', 'Left', num(star%x))
    call rad_set('lblStar', 'Top', num(star%y))
    call rad_set('lblRock', 'Left', num(rock%x))
    call rad_set('lblRock', 'Top', num(rock%y))
  end subroutine tmrGame_Tick

  ! KeyDown / KeyUp: rad_arg(4) = key name (Left, Right, p ...)
  subroutine frmGame_KeyDown()
    character(len=:), allocatable :: k
    k = rad_arg(4)
    if (k == 'Left') then
      left_key = .true.
    else if (k == 'Right') then
      right_key = .true.
    else if (k == 'p' .or. k == 'P') then
      call btnPause_Click()
    end if
  end subroutine frmGame_KeyDown

  subroutine frmGame_KeyUp()
    character(len=:), allocatable :: k
    k = rad_arg(4)
    if (k == 'Left') left_key = .false.
    if (k == 'Right') right_key = .false.
  end subroutine frmGame_KeyUp

  ! the mouse moves the paddle too (X is relative to pnlField)
  subroutine pnlField_MouseMove()
    if (running .and. .not. paused) player%x = nint(rad_num(rad_arg(1))) - player%w / 2
  end subroutine pnlField_MouseMove

end module frmgame_code
