! (c) 2026 Musoftware - https://musoftwares.com - MIT License
!
! frmAbout - the About box of Greeting Cards (shown with ShowDialog from frmMain).
module frmabout_code
  use radgui
  use app_settings
  implicit none
contains

  subroutine frmAbout_Load()
    if (arabic) then
      call rad_set('lblAboutTitle', 'Caption', 'بطاقات التهنئة')
    else
      call rad_set('lblAboutTitle', 'Caption', 'Greeting Cards')
    end if
  end subroutine frmAbout_Load

  subroutine btnClose_Click()
    call rad_call('frmAbout', 'Hide', '')
  end subroutine btnClose_Click

end module frmabout_code
