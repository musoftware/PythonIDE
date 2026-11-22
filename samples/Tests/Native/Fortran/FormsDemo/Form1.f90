! Event handlers for Form1 - GUI Bridge Fortran API (module radgui); the native build uses the
! radforms variant of the same module (stdin/stdout replaced by in-process calls).
module form1_code
  use radgui
  implicit none
  integer :: ticks = 0
contains

  subroutine Form1_Load()
    call rad_set('lblOut', 'Caption', 'ready')
    call rad_call('lstLog', 'AddItem', 'Form1 loaded')
  end subroutine Form1_Load

  subroutine cmdAdd_Click()
    real(8) :: a, b
    a = rad_num(rad_get('txtA', 'Text'))
    b = rad_num(rad_get('txtB', 'Text'))
    call rad_set('lblOut', 'Caption', rad_str(a + b))
    call rad_call('lstLog', 'AddItem', rad_str(a) // ' + ' // rad_str(b) // ' = ' // rad_str(a + b))
  end subroutine cmdAdd_Click

  subroutine txtA_TextChanged()
    call rad_set('lblEcho', 'Caption', rad_get('txtA', 'Text'))
  end subroutine txtA_TextChanged

  subroutine chkBig_CheckedChanged()
    if (rad_get('chkBig', 'Value') == '1') then
      call rad_set('lblOut', 'FontSize', '14')
      call rad_set('lblOut', 'Caption', 'big')
    else
      call rad_set('lblOut', 'FontSize', '9')
      call rad_set('lblOut', 'Caption', 'small')
    end if
  end subroutine chkBig_CheckedChanged

  subroutine cboColor_SelectedIndexChanged()
    call rad_set('lblOut', 'Caption', rad_get('cboColor', 'Text'))
  end subroutine cboColor_SelectedIndexChanged

  subroutine tmrTick_Tick()
    ticks = ticks + 1
    call rad_set('lblTicks', 'Caption', rad_str(real(ticks, 8)))
    call rad_set('prgTicks', 'Value', rad_str(real(mod(ticks, 51), 8)))
  end subroutine tmrTick_Tick

  subroutine cmdShow2_Click()
    call rad_show('Form2')
  end subroutine cmdShow2_Click

  subroutine mnuForm2_Click()
    call rad_show('Form2')
  end subroutine mnuForm2_Click

  subroutine mnuExit_Click()
    call rad_end()
  end subroutine mnuExit_Click

  subroutine cmdMsg_Click()
    call rad_msgbox('Hello from radforms')
    call rad_set('lblOut', 'Caption', 'msg done')
  end subroutine cmdMsg_Click

  subroutine cmdArabic_Click()
    call rad_set('lblOut', 'Caption', 'مرحبا بالعالم')
  end subroutine cmdArabic_Click

end module form1_code
