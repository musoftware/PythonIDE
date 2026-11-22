! (c) 2026 Musoftware - https://musoftwares.com - MIT License
!
! Greeting Cards - a multi-form Fortran program (RAD IDE GUI Bridge, module radgui;
! Build > Publish makes a native Win32 exe with gfortran + radforms).
!
! frmMain makes greeting cards, frmSettings is a modal dialog (ShowDialog) for the user name, the language
! (English / Arabic), the font size and a formal style, frmAbout is the About box. The module app_settings
! (app_settings.f90) keeps the settings in settings.ini. Arabic text is right-aligned.
! Shows: several forms, ShowDialog / Hide, "Form.Control" names, a menu, a shared module, a settings file,
! Unicode (Arabic, UTF-8) text in labels, combo boxes and a multi-line text box (achar(13)//achar(10)).
module frmmain_code
  use radgui
  use app_settings
  implicit none
  character(len=2), parameter :: CRLF = achar(13) // achar(10)
contains

  function tr(en, ar) result(s)
    character(len=*), intent(in) :: en, ar
    character(len=:), allocatable :: s
    if (arabic) then
      s = ar
    else
      s = en
    end if
  end function tr

  function greeting() result(s)
    character(len=:), allocatable :: s
    if (formal) then
      s = tr('Good day, ', 'أسعد الله أوقاتك يا ') // trim(user_name)
    else
      s = tr('Hello, ', 'مرحبا يا ') // trim(user_name)
    end if
  end function greeting

  ! show the settings on the main form (frmSettings calls it after OK)
  subroutine apply_settings()
    character(len=5) :: align
    align = merge('Right', 'Left ', arabic)
    call rad_set('frmMain', 'Caption', tr('Greeting Cards', 'بطاقات التهنئة'))
    call rad_set('frmMain.lblTitle', 'Caption', greeting() // '!')
    call rad_set('frmMain.lblMessage', 'Caption', tr('Choose an occasion and press Make card.', &
                                                     'اختر مناسبة ثم اضغط اصنع بطاقة.'))
    call rad_set('frmMain.lblOccasion', 'Caption', tr('Occasion:', 'المناسبة:'))
    call rad_set('frmMain.btnMake', 'Caption', tr('Make card', 'اصنع بطاقة'))
    call rad_set('frmMain.btnSettings', 'Caption', tr('Settings...', 'الإعدادات...'))
    call rad_set('frmMain.btnAbout', 'Caption', tr('About...', 'حول...'))
    call rad_set('frmMain.lblTitle', 'TextAlign', trim(align))
    call rad_set('frmMain.lblMessage', 'TextAlign', trim(align))
    call rad_set('frmMain.txtCard', 'FontSize', rad_str(real(font_size, 8)))
    call rad_set('frmMain.sbStatus', 'Text', tr('Ready', 'جاهز'))
  end subroutine apply_settings

  ! ------------------------------------------------------------------ events
  subroutine frmMain_Load()
    call load_settings()
    call rad_set('cboOccasion', 'ListIndex', '0')
    call apply_settings()
  end subroutine frmMain_Load

  subroutine btnMake_Click()
    integer :: i
    character(len=:), allocatable :: wish
    i = nint(rad_num(rad_get('cboOccasion', 'ListIndex')))
    select case (i)
    case (1)
      wish = tr('Happy New Year! May the year bring you joy and health.', &
                'سنة جديدة سعيدة! أتمنى لك عاماً مليئاً بالفرح والصحة.')
    case (2)
      wish = tr('Eid Mubarak! Wishing you and your family a blessed Eid.', 'عيد مبارك! كل عام وأنتم بخير.')
    case (3)
      wish = tr('Congratulations on your success - well done!', 'مبروك النجاح - أحسنت!')
    case default
      wish = tr('Happy birthday! Many happy returns of the day.', 'عيد ميلاد سعيد! كل عام وأنت بخير.')
    end select
    call rad_set('txtCard', 'Text', greeting() // CRLF // CRLF // wish // CRLF // CRLF // &
                 tr('Best wishes', 'مع أطيب التمنيات'))
    call rad_set('sbStatus', 'Text', tr('Card ready', 'تم إنشاء البطاقة'))
  end subroutine btnMake_Click

  subroutine btnSettings_Click()
    ! fill the dialog, then show it modally; its OK / Cancel handlers (frmSettings.f90) finish the job
    call rad_set('frmSettings.txtUser', 'Text', trim(user_name))
    call rad_set('frmSettings.cboLang', 'ListIndex', merge('1', '0', arabic))
    call rad_set('frmSettings.nudSize', 'Value', rad_str(real(font_size, 8)))
    call rad_set('frmSettings.chkFormal', 'Value', merge('1', '0', formal))
    call rad_call('frmSettings', 'ShowDialog', '')
  end subroutine btnSettings_Click

  subroutine mnuSettings_Click()
    call btnSettings_Click()
  end subroutine mnuSettings_Click

  subroutine btnAbout_Click()
    call rad_call('frmAbout', 'ShowDialog', '')
  end subroutine btnAbout_Click

  subroutine mnuAbout_Click()
    call btnAbout_Click()
  end subroutine mnuAbout_Click

  subroutine mnuExit_Click()
    call rad_end()
  end subroutine mnuExit_Click

end module frmmain_code
