! Event handlers for Form1. Use rad_set / rad_get / rad_call to work with the controls.
! Handlers are subroutines without arguments named <Control>_<Event>.
module form1_code
  use radgui
  implicit none
contains

  subroutine Form1_Load()
    ! runs when the form is shown
  end subroutine Form1_Load

end module form1_code
