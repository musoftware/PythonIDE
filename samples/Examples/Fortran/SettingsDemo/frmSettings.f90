! (c) 2026 Musoftware - https://musoftwares.com - MIT License
!
! frmSettings - the modal settings dialog of Greeting Cards. frmMain fills it and calls ShowDialog;
! OK validates, stores the values in app_settings, writes settings.ini and updates frmMain.
module frmsettings_code
  use radgui
  use app_settings
  use frmmain_code, only: apply_settings
  implicit none
contains

  subroutine btnOK_Click()
    character(len=:), allocatable :: user
    user = trim(adjustl(rad_get('txtUser', 'Text')))
    if (len(user) == 0) then
      call rad_msgbox('Please type your name.')
      call rad_call('txtUser', 'SetFocus', '')
      return
    end if
    user_name = user
    arabic = rad_get('cboLang', 'ListIndex') == '1'
    font_size = nint(rad_num(rad_get('nudSize', 'Value')))
    formal = rad_get('chkFormal', 'Value') == '1'
    if (.not. save_settings()) call rad_msgbox('Cannot write settings.ini')
    call rad_call('frmSettings', 'Hide', '')
    call apply_settings()
  end subroutine btnOK_Click

  subroutine btnCancel_Click()
    call rad_call('frmSettings', 'Hide', '')
  end subroutine btnCancel_Click

end module frmsettings_code
