! Event handlers for Form2.
module form2_code
  use radgui
  implicit none
contains

  subroutine Form2_Load()
    call rad_set('txt2', 'Text', 'from Form2 Load')
  end subroutine Form2_Load

  subroutine cmdClose2_Click()
    call rad_set('Form1.lblOut', 'Caption', rad_get('txt2', 'Text'))
    call rad_hide('Form2')
  end subroutine cmdClose2_Click

end module form2_code
